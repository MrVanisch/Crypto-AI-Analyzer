"""
AI Analyzer for Crypto News Content
Intelligent content analysis using PyTorch and pre-trained models
"""

import os
import asyncio
import torch
import torch.nn as nn
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import numpy as np
from loguru import logger
import re
import hashlib

# Import transformers
try:
    from transformers import (
        AutoTokenizer, AutoModel, AutoModelForSequenceClassification,
        pipeline, logging as transformers_logging
    )
    transformers_logging.set_verbosity_error()  # Reduce transformer warnings
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Transformers not available, using fallback analysis")
    TRANSFORMERS_AVAILABLE = False

# Sklearn for fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class AIAnalyzer:
    def __init__(self):
        """Initialize AI content analyzer"""
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"🧠 AI Analyzer initializing on device: {self.device}")
        
        # Model configurations
        self.model_config = {
            'base_model': 'ProsusAI/finbert',  # Financial BERT
            'backup_model': 'nlptown/bert-base-multilingual-uncased-sentiment',
            'max_length': 512,
            'batch_size': 4
        }
        
        # Initialize models
        self.sentiment_model = None
        self.tokenizer = None
        self.custom_classifier = None
        
        # Analysis cache
        self.analysis_cache = {}
        self.cache_duration = 3600  # 1 hour
        
        # Crypto-specific knowledge base
        self.crypto_knowledge = self._load_crypto_knowledge()
        
        # Initialize models
        self._initialize_models()
        
        # Analysis weights
        self.analysis_weights = {
            'market_impact': 0.3,      # How much this affects crypto market
            'information_novelty': 0.25, # Is this new information?
            'source_credibility': 0.2,  # How credible is the source?
            'sentiment_strength': 0.15, # How strong is the sentiment?
            'urgency_level': 0.1       # How urgent/breaking is this?
        }
        
        logger.info("🧠 AI Analyzer initialized successfully")
    
    def _initialize_models(self):
        """Initialize AI models (sentiment, classification)"""
        try:
            if TRANSFORMERS_AVAILABLE:
                self._load_transformer_models()
            else:
                self._load_fallback_models()
                
        except Exception as e:
            logger.error(f"❌ Error initializing AI models: {e}")
            self._load_fallback_models()
    
    def _load_transformer_models(self):
        """Load transformer-based models"""
        try:
            # Try to load FinBERT for financial analysis
            logger.info("📥 Loading FinBERT model...")
            self.sentiment_model = pipeline(
                'sentiment-analysis',
                model=self.model_config['base_model'],
                device=0 if self.device.type == 'cuda' else -1,
                return_all_scores=True
            )
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_config['base_model'])
            logger.info("✅ FinBERT loaded successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ FinBERT failed, trying backup model: {e}")
            try:
                self.sentiment_model = pipeline(
                    'sentiment-analysis',
                    model=self.model_config['backup_model'],
                    device=0 if self.device.type == 'cuda' else -1,
                    return_all_scores=True
                )
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_config['backup_model'])
                logger.info("✅ Backup sentiment model loaded")
            except Exception as e2:
                logger.error(f"❌ All transformer models failed: {e2}")
                raise
    
    def _load_fallback_models(self):
        """Load non-transformer fallback models"""
        logger.info("📥 Loading fallback analysis models...")
        
        # Simple keyword-based analysis
        self.sentiment_model = None
        self.tokenizer = None
        
        # Initialize TF-IDF for similarity analysis
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
        
        logger.info("✅ Fallback models loaded")
    
    def _load_crypto_knowledge(self) -> Dict:
        """Load crypto-specific knowledge base"""
        return {
            'tier_1_cryptos': {
                'bitcoin': {'weight': 1.0, 'keywords': ['btc', 'bitcoin', 'satoshi']},
                'ethereum': {'weight': 0.9, 'keywords': ['eth', 'ethereum', 'vitalik', 'gas']},
            },
            'tier_2_cryptos': {
                'cardano': {'weight': 0.7, 'keywords': ['ada', 'cardano']},
                'solana': {'weight': 0.7, 'keywords': ['sol', 'solana']},
                'polygon': {'weight': 0.6, 'keywords': ['matic', 'polygon']},
            },
            'market_events': {
                'regulation': {'impact': 0.9, 'keywords': ['sec', 'cftc', 'regulation', 'ban', 'legal']},
                'institutional': {'impact': 0.8, 'keywords': ['etf', 'institutional', 'tesla', 'microstrategy']},
                'technical': {'impact': 0.6, 'keywords': ['upgrade', 'fork', 'halving', 'merge']},
                'exchange': {'impact': 0.7, 'keywords': ['exchange', 'binance', 'coinbase', 'hack']},
            },
            'sentiment_indicators': {
                'very_positive': ['moon', 'bullish', 'surge', 'breakthrough', 'adoption', 'pump'],
                'positive': ['rise', 'gain', 'growth', 'up', 'increase', 'rally'],
                'negative': ['drop', 'fall', 'down', 'crash', 'decline', 'bear'],
                'very_negative': ['hack', 'scam', 'ban', 'collapse', 'plunge', 'dump']
            }
        }
    
    async def analyze_importance(self, title: str, content: str, source: str = '') -> Dict:
        """
        Main AI analysis function - determines content importance
        
        Args:
            title: Article title
            content: Article content  
            source: Source domain
            
        Returns:
            Analysis results with importance score and explanations
        """
        # Check cache
        cache_key = hashlib.md5(f"{title}{content}".encode()).hexdigest()
        if cache_key in self.analysis_cache:
            cached_result, timestamp = self.analysis_cache[cache_key]
            if (datetime.now().timestamp() - timestamp) < self.cache_duration:
                logger.debug("💾 Using cached AI analysis")
                return cached_result
        
        try:
            # Prepare input text
            input_text = self._prepare_text(title, content)
            
            # Run analysis components
            analysis_tasks = [
                self._analyze_market_impact(input_text),
                self._analyze_information_novelty(input_text, title),
                self._analyze_sentiment_strength(input_text),
                self._analyze_urgency_level(input_text, title),
                self._analyze_source_credibility(source)
            ]
            
            # Execute analysis
            results = await asyncio.gather(*analysis_tasks)
            
            market_impact, novelty, sentiment_strength, urgency, source_cred = results
            
            # Calculate final importance score
            final_score = (
                market_impact * self.analysis_weights['market_impact'] +
                novelty * self.analysis_weights['information_novelty'] +
                source_cred * self.analysis_weights['source_credibility'] +
                sentiment_strength * self.analysis_weights['sentiment_strength'] +
                urgency * self.analysis_weights['urgency_level']
            )
            
            # Create comprehensive analysis result
            analysis_result = {
                'importance_score': min(1.0, max(0.0, final_score)),
                'confidence': self._calculate_confidence(results),
                'components': {
                    'market_impact': market_impact,
                    'information_novelty': novelty,
                    'sentiment_strength': sentiment_strength,
                    'urgency_level': urgency,
                    'source_credibility': source_cred
                },
                'explanation': self._generate_explanation(results, final_score),
                'crypto_mentions': self._extract_crypto_mentions(input_text),
                'key_themes': self._extract_key_themes(input_text),
                'analyzed_at': datetime.now().isoformat(),
                'model_version': 'v1.0'
            }
            
            # Cache result
            self.analysis_cache[cache_key] = (analysis_result, datetime.now().timestamp())
            
            logger.info(f"🧠 AI Analysis complete: importance={final_score:.3f}, confidence={analysis_result['confidence']:.3f}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ AI analysis error: {e}")
            return self._get_fallback_analysis(title, content, source)
    
    def _prepare_text(self, title: str, content: str) -> str:
        """Prepare text for analysis (cleaning, truncation)"""
        # Combine title and content with emphasis on title
        full_text = f"{title}. {content}"
        
        # Clean text
        full_text = re.sub(r'\s+', ' ', full_text)  # Normalize whitespace
        full_text = re.sub(r'[^\w\s\.,!?-]', '', full_text)  # Remove special chars
        
        # Truncate to model max length (accounting for tokenization)
        if self.tokenizer:
            tokens = self.tokenizer.encode(full_text, truncation=True, max_length=self.model_config['max_length'])
            full_text = self.tokenizer.decode(tokens, skip_special_tokens=True)
        else:
            # Simple truncation
            words = full_text.split()
            if len(words) > 200:  # Rough token estimation
                full_text = ' '.join(words[:200])
        
        return full_text.strip()
    
    async def _analyze_market_impact(self, text: str) -> float:
        """Analyze potential market impact of the content"""
        score = 0.5  # Base score
        text_lower = text.lower()
        
        # Check for high-impact crypto mentions
        for crypto, info in self.crypto_knowledge['tier_1_cryptos'].items():
            if any(keyword in text_lower for keyword in info['keywords']):
                score += info['weight'] * 0.3
        
        # Check for market events
        for event, info in self.crypto_knowledge['market_events'].items():
            if any(keyword in text_lower for keyword in info['keywords']):
                score += info['impact'] * 0.2
        
        # Check for price/volume mentions
        if re.search(r'\$\d+|\d+%|volume|price|market cap', text_lower):
            score += 0.15
        
        # Check for institutional/regulatory keywords
        institutional_keywords = ['sec', 'etf', 'federal reserve', 'regulation', 'ban', 'approval']
        if any(keyword in text_lower for keyword in institutional_keywords):
            score += 0.25
        
        return min(1.0, score)
    
    async def _analyze_information_novelty(self, text: str, title: str) -> float:
        """Analyze how novel/new the information is"""
        score = 0.5  # Base score
        
        # Check for breaking/urgent indicators
        urgent_indicators = ['breaking', 'just in', 'urgent', 'alert', 'developing', 'first time']
        if any(indicator in title.lower() for indicator in urgent_indicators):
            score += 0.3
        
        # Check for new developments
        new_indicators = ['announces', 'launches', 'introduces', 'reveals', 'confirms', 'unveils']
        if any(indicator in text.lower() for indicator in new_indicators):
            score += 0.2
        
        # Check for specific events/numbers (often indicates concrete news)
        if re.search(r'\b(20\d{2}|\d{1,2}/\d{1,2}|\d+\s*(million|billion|trillion))', text):
            score += 0.15
        
        # Penalty for opinion/analysis pieces
        opinion_indicators = ['opinion', 'analysis', 'think', 'believe', 'predict', 'forecast']
        if any(indicator in text.lower() for indicator in opinion_indicators):
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    async def _analyze_sentiment_strength(self, text: str) -> float:
        """Analyze strength of sentiment (extreme = more important)"""
        if self.sentiment_model and TRANSFORMERS_AVAILABLE:
            try:
                # Use transformer model
                result = self.sentiment_model(text[:512])  # Truncate for model
                
                if isinstance(result[0], list):  # Multiple labels
                    # Find highest confidence score
                    max_confidence = max(item['score'] for item in result[0])
                    return max_confidence
                else:  # Single prediction
                    return result[0]['score']
                    
            except Exception as e:
                logger.debug(f"⚠️ Transformer sentiment analysis failed: {e}")
        
        # Fallback: keyword-based sentiment
        return self._keyword_sentiment_analysis(text)
    
    def _keyword_sentiment_analysis(self, text: str) -> float:
        """Fallback keyword-based sentiment analysis"""
        text_lower = text.lower()
        
        positive_count = 0
        negative_count = 0
        
        # Count sentiment indicators
        for sentiment_words in self.crypto_knowledge['sentiment_indicators']['very_positive']:
            positive_count += text_lower.count(sentiment_words) * 2
        
        for sentiment_words in self.crypto_knowledge['sentiment_indicators']['positive']:
            positive_count += text_lower.count(sentiment_words)
        
        for sentiment_words in self.crypto_knowledge['sentiment_indicators']['very_negative']:
            negative_count += text_lower.count(sentiment_words) * 2
        
        for sentiment_words in self.crypto_knowledge['sentiment_indicators']['negative']:
            negative_count += text_lower.count(sentiment_words)
        
        # Calculate sentiment strength (extremity)
        total_sentiment = positive_count + negative_count
        if total_sentiment == 0:
            return 0.3  # Neutral = low importance
        
        # Return sentiment strength (not direction)
        strength = min(1.0, total_sentiment / 10)  # Normalize
        return 0.3 + (strength * 0.7)  # Scale to 0.3-1.0
    
    async def _analyze_urgency_level(self, text: str, title: str) -> float:
        """Analyze urgency/breaking news level"""
        score = 0.2  # Base score
        
        title_lower = title.lower()
        text_lower = text.lower()
        
        # Breaking news indicators
        breaking_indicators = ['breaking', 'urgent', 'alert', 'live', 'just in', 'developing']
        if any(indicator in title_lower for indicator in breaking_indicators):
            score += 0.5
        
        # Time-sensitive indicators
        time_indicators = ['today', 'this morning', 'minutes ago', 'hours ago', 'now', 'currently']
        if any(indicator in text_lower for indicator in time_indicators):
            score += 0.3
        
        # Market action words
        action_words = ['surges', 'plunges', 'spikes', 'crashes', 'jumps', 'soars']
        if any(word in text_lower for word in action_words):
            score += 0.2
        
        return min(1.0, score)
    
    async def _analyze_source_credibility(self, source: str) -> float:
        """Analyze credibility of the source"""
        if not source:
            return 0.5
        
        source_lower = source.lower()
        
        # Tier 1 sources (highest credibility)
        tier_1 = ['reuters.com', 'bloomberg.com', 'coindesk.com', 'wsj.com']
        if any(domain in source_lower for domain in tier_1):
            return 1.0
        
        # Tier 2 sources
        tier_2 = ['cointelegraph.com', 'decrypt.co', 'theblock.co', 'cnbc.com']
        if any(domain in source_lower for domain in tier_2):
            return 0.8
        
        # Tier 3 sources
        tier_3 = ['yahoo.com', 'marketwatch.com', 'investing.com']
        if any(domain in source_lower for domain in tier_3):
            return 0.6
        
        # Unknown sources
        return 0.4
    
    def _calculate_confidence(self, analysis_results: List[float]) -> float:
        """Calculate confidence in the analysis"""
        # Higher confidence when components agree
        std_dev = np.std(analysis_results)
        mean_val = np.mean(analysis_results)
        
        # Lower std dev = higher confidence
        confidence = 1.0 - min(0.5, std_dev)
        
        # Boost confidence for extreme values
        if mean_val > 0.8 or mean_val < 0.2:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_explanation(self, results: List[float], final_score: float) -> str:
        """Generate human-readable explanation"""
        market_impact, novelty, sentiment_strength, urgency, source_cred = results
        
        explanations = []
        
        if final_score > 0.8:
            explanations.append("🔥 CRITICAL: High importance content")
        elif final_score > 0.6:
            explanations.append("📈 HIGH: Significant market relevance")
        elif final_score > 0.4:
            explanations.append("📊 MEDIUM: Moderate importance")
        else:
            explanations.append("📉 LOW: Limited market impact")
        
        if market_impact > 0.7:
            explanations.append("Strong market impact potential")
        
        if novelty > 0.7:
            explanations.append("Contains new information")
        
        if urgency > 0.7:
            explanations.append("Breaking/urgent news")
        
        if sentiment_strength > 0.7:
            explanations.append("Strong sentiment indicators")
        
        if source_cred > 0.8:
            explanations.append("Highly credible source")
        
        return " • ".join(explanations)
    
    def _extract_crypto_mentions(self, text: str) -> List[str]:
        """Extract mentioned cryptocurrencies"""
        mentions = []
        text_lower = text.lower()
        
        # Check all known cryptos
        for crypto, info in {**self.crypto_knowledge['tier_1_cryptos'], 
                            **self.crypto_knowledge['tier_2_cryptos']}.items():
            if any(keyword in text_lower for keyword in info['keywords']):
                mentions.append(crypto)
        
        return mentions
    
    def _extract_key_themes(self, text: str) -> List[str]:
        """Extract key themes from content"""
        themes = []
        text_lower = text.lower()
        
        # Check for major themes
        for theme, info in self.crypto_knowledge['market_events'].items():
            if any(keyword in text_lower for keyword in info['keywords']):
                themes.append(theme)
        
        return themes
    
    def _get_fallback_analysis(self, title: str, content: str, source: str) -> Dict:
        """Fallback analysis when AI models fail"""
        logger.warning("🔄 Using fallback analysis due to AI model failure")
        
        # Simple rule-based analysis
        text = f"{title} {content}".lower()
        
        # Basic importance scoring
        importance = 0.5
        
        # Check for important keywords
        important_keywords = ['bitcoin', 'ethereum', 'regulation', 'sec', 'etf', 'hack', 'crash']
        importance += min(0.3, sum(0.1 for keyword in important_keywords if keyword in text))
        
        # Check source
        if any(domain in source.lower() for domain in ['reuters', 'bloomberg', 'coindesk']):
            importance += 0.2
        
        return {
            'importance_score': min(1.0, importance),
            'confidence': 0.5,
            'components': {
                'market_impact': 0.5,
                'information_novelty': 0.5,
                'sentiment_strength': 0.5,
                'urgency_level': 0.5,
                'source_credibility': 0.5
            },
            'explanation': '⚠️ Fallback analysis - AI models unavailable',
            'crypto_mentions': self._extract_crypto_mentions(text),
            'key_themes': [],
            'analyzed_at': datetime.now().isoformat(),
            'model_version': 'fallback'
        }

# Test function
async def test_ai_analyzer():
    """Test the AI analyzer"""
    print("🧪 Testing AI Analyzer...")
    
    analyzer = AIAnalyzer()
    
    # Test cases
    test_cases = [
        {
            'title': 'SEC Approves First Bitcoin ETF',
            'content': 'The Securities and Exchange Commission has approved the first Bitcoin exchange-traded fund, marking a major milestone for cryptocurrency adoption in traditional finance.',
            'source': 'reuters.com'
        },
        {
            'title': 'Bitcoin Price Analysis for Today',
            'content': 'Technical analysis shows Bitcoin might test resistance levels. This is just our opinion based on chart patterns.',
            'source': 'cryptoblog.com'
        },
        {
            'title': 'Breaking: Major Exchange Hacked',
            'content': 'A major cryptocurrency exchange reported a security breach with millions in losses. Users are advised to check their accounts immediately.',
            'source': 'coindesk.com'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['title'][:50]}...")
        
        result = await analyzer.analyze_importance(
            test_case['title'],
            test_case['content'],
            test_case['source']
        )
        
        print(f"🎯 Importance: {result['importance_score']:.3f}")
        print(f"🎯 Confidence: {result['confidence']:.3f}")
        print(f"💡 Explanation: {result['explanation']}")
        print(f"🪙 Crypto mentions: {result['crypto_mentions']}")
        print(f"🎨 Themes: {result['key_themes']}")

if __name__ == "__main__":
    asyncio.run(test_ai_analyzer())