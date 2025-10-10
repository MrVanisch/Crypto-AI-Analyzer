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
        
        # Analysis weights - more rigorous
        self.analysis_weights = {
            'market_impact': 0.35,      # Market impact - most important
            'information_novelty': 0.3, # Information novelty - very important
            'source_credibility': 0.2,  # Source credibility
            'sentiment_strength': 0.1,  # Sentiment strength - less important
            'urgency_level': 0.05       # Urgency - least important
        }
        
        # Thresholds for really important news
        self.critical_threshold = 0.75
        self.high_threshold = 0.6
        self.medium_threshold = 0.4
        
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
        """Load crypto-specific knowledge base - SOLANA FOCUSED"""
        return {
            'tier_1_cryptos': {
                'solana': {'weight': 1.0, 'keywords': ['sol', 'solana', 'phantom', 'solana price', 'sol price', 'solana network', 'solana labs', 'solana ecosystem']},
            },
            'tier_2_cryptos': {
                'bitcoin': {'weight': 0.8, 'keywords': ['btc', 'bitcoin', 'satoshi', 'bitcoin price', 'btc price']},
                'ethereum': {'weight': 0.8, 'keywords': ['eth', 'ethereum', 'vitalik', 'gas', 'ethereum price', 'eth price', 'eip']},
                'cardano': {'weight': 0.6, 'keywords': ['ada', 'cardano', 'charles hoskinson']},
                'polygon': {'weight': 0.6, 'keywords': ['matic', 'polygon', 'layer 2']},
                'binance': {'weight': 0.6, 'keywords': ['bnb', 'binance coin', 'bsc']},
            },
            'market_events': {
                'regulation': {'impact': 1.0, 'keywords': ['sec', 'cftc', 'regulation', 'ban', 'legal', 'lawsuit', 'fine', 'regulatory', 'government']},
                'institutional': {'impact': 0.95, 'keywords': ['etf', 'institutional', 'tesla', 'microstrategy', 'blackrock', 'grayscale', 'approval', 'wall street']},
                'technical': {'impact': 0.7, 'keywords': ['upgrade', 'fork', 'halving', 'merge', 'update', 'protocol', 'network']},
                'exchange': {'impact': 0.85, 'keywords': ['exchange', 'binance', 'coinbase', 'hack', 'listing', 'delisting', 'trading']},
                'market_manipulation': {'impact': 0.9, 'keywords': ['manipulation', 'whale', 'pump', 'dump', 'insider']},
                'adoption': {'impact': 0.8, 'keywords': ['adoption', 'partnership', 'integration', 'mainstream', 'corporate']}
            },
            'sentiment_indicators': {
                'very_positive': ['moon', 'bullish', 'surge', 'breakthrough', 'adoption', 'pump', 'skyrocket', 'all-time high', 'ath', 'breakout'],
                'positive': ['rise', 'gain', 'growth', 'up', 'increase', 'rally', 'green', 'profit', 'bull', 'upward'],
                'negative': ['drop', 'fall', 'down', 'crash', 'decline', 'bear', 'red', 'loss', 'correction', 'dip'],
                'very_negative': ['hack', 'scam', 'ban', 'collapse', 'plunge', 'dump', 'exploit', 'rug pull', 'investigation', 'fraud']
            },
            'critical_keywords': {
                'regulatory_action': ['sec action', 'lawsuit filed', 'investigation', 'enforcement', 'fine', 'penalty'],
                'major_hack': ['exchange hacked', 'funds stolen', 'security breach', 'exploit', 'millions lost'],
                'institutional_news': ['etf approved', 'etf rejected', 'blackrock', 'institutional adoption'],
                'market_moving': ['halving', 'merge completed', 'major upgrade', 'partnership announcement'],
                'solana_critical': ['solana hack', 'solana outage', 'solana exploit', 'phantom hack', 'solana validator', 'solana consensus', 'solana mainnet']
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
        score = 0.2  # Lower base score - more rigorous
        text_lower = text.lower()
        
        # Check critical keywords - highest priority
        for category, keywords in self.crypto_knowledge['critical_keywords'].items():
            if any(keyword in text_lower for keyword in keywords):
                score += 0.4  # Big boost for critical words
        
        # Check for high-impact crypto mentions
        for crypto, info in self.crypto_knowledge['tier_1_cryptos'].items():
            if any(keyword in text_lower for keyword in info['keywords']):
                score += info['weight'] * 0.25
        
        # Tier 2 cryptos - smaller impact
        for crypto, info in self.crypto_knowledge['tier_2_cryptos'].items():
            if any(keyword in text_lower for keyword in info['keywords']):
                score += info['weight'] * 0.15
        
        # Check for market events - increased weights
        for event, info in self.crypto_knowledge['market_events'].items():
            if any(keyword in text_lower for keyword in info['keywords']):
                score += info['impact'] * 0.3
        
        # Check for price/volume mentions - konkretne liczby
        price_patterns = [
            r'\$\d{1,3}[,.]?\d*[kmb]?',  # $50k, $1.2M, etc
            r'\d+%',                      # percentages
            r'\d+x',                      # multipliers
            r'market cap.*\$\d+',         # market cap mentions
            r'volume.*\$\d+',             # volume mentions
        ]
        
        for pattern in price_patterns:
            if re.search(pattern, text_lower):
                score += 0.1
        
        # Penalty for opinion pieces and analysis
        opinion_indicators = ['i think', 'i believe', 'opinion', 'analysis', 'prediction', 'forecast']
        if any(indicator in text_lower for indicator in opinion_indicators):
            score *= 0.7  # 30% reduction
        
        return min(1.0, max(0.0, score))
    
    async def _analyze_information_novelty(self, text: str, title: str) -> float:
        """Analyze how novel/new the information is"""
        score = 0.3  # Lower base score
        title_lower = title.lower()
        text_lower = text.lower()
        
        # Breaking/urgent indicators - bardzo wysokie znaczenie
        urgent_indicators = ['breaking', 'just in', 'urgent', 'alert', 'developing', 'first time', 'exclusive']
        urgent_count = sum(1 for indicator in urgent_indicators if indicator in title_lower)
        if urgent_count > 0:
            score += 0.4 + (urgent_count - 1) * 0.1  # Bonus za multiple indicators
        
        # Konkretne akcje/wydarzenia - wysokie znaczenie
        action_indicators = [
            'announces', 'launches', 'introduces', 'reveals', 'confirms', 'unveils',
            'files', 'submits', 'approves', 'rejects', 'implements', 'completes'
        ]
        action_count = sum(1 for indicator in action_indicators if indicator in text_lower)
        if action_count > 0:
            score += 0.25 + (action_count - 1) * 0.05
        
        # Dates and concrete numbers - indicate actual events
        concrete_indicators = [
            r'\b(today|yesterday|this week|this month)',
            r'\b20\d{2}\b',  # years
            r'\b\d{1,2}/\d{1,2}(/\d{2,4})?\b',  # dates
            r'\$\d+\s*(million|billion|trillion)',  # specific amounts
            r'\d+%',  # percentages
        ]
        
        for pattern in concrete_indicators:
            if re.search(pattern, text_lower):
                score += 0.1
        
        # Very high penalty for opinion/analysis pieces
        opinion_indicators = [
            'opinion', 'analysis', 'think', 'believe', 'predict', 'forecast',
            'could', 'might', 'may', 'possibly', 'speculation', 'rumor'
        ]
        opinion_count = sum(1 for indicator in opinion_indicators if indicator in text_lower)
        if opinion_count > 0:
            score *= 0.5  # 50% reduction for opinion pieces
        
        # Penalty for old news
        old_indicators = ['last week', 'last month', 'weeks ago', 'months ago']
        if any(indicator in text_lower for indicator in old_indicators):
            score *= 0.6
        
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
            return 0.3
        
        source_lower = source.lower()
        
        # Tier 1 sources (highest credibility) - traditional financial media
        tier_1 = [
            'reuters.com', 'bloomberg.com', 'wsj.com', 'ft.com', 'cnbc.com',
            'ap.org', 'bbc.com/business', 'sec.gov', 'cftc.gov'
        ]
        if any(domain in source_lower for domain in tier_1):
            return 1.0
        
        # Tier 2 sources - specialized crypto media
        tier_2 = [
            'coindesk.com', 'theblock.co', 'decrypt.co', 'cointelegraph.com',
            'blockworks.co', 'coinbase.com/blog'
        ]
        if any(domain in source_lower for domain in tier_2):
            return 0.85
        
        # Tier 3 sources - popular financial media
        tier_3 = [
            'marketwatch.com', 'investing.com', 'yahoo.com/finance',
            'techcrunch.com', 'forbes.com'
        ]
        if any(domain in source_lower for domain in tier_3):
            return 0.7
        
        # Tier 4 - other known media
        tier_4 = [
            'reddit.com', 'twitter.com', 'medium.com', 'substack.com'
        ]
        if any(domain in source_lower for domain in tier_4):
            return 0.4
        
        # Unknown sources - very low score
        return 0.2
    
    def _calculate_confidence(self, analysis_results: List[float]) -> float:
        """Calculate confidence in the analysis"""
        market_impact, novelty, sentiment_strength, urgency, source_cred = analysis_results
        
        # Base confidence
        confidence = 0.5
        
        # Boost for high source credibility
        if source_cred >= 0.8:
            confidence += 0.3
        elif source_cred >= 0.6:
            confidence += 0.2
        elif source_cred < 0.4:
            confidence -= 0.2
        
        # Boost for consistency between components
        high_scores = sum(1 for score in analysis_results if score >= 0.7)
        if high_scores >= 3:
            confidence += 0.2
        elif high_scores >= 2:
            confidence += 0.1
        
        # Boost for very high or very low values (confidence in extremes)
        mean_val = np.mean(analysis_results)
        if mean_val >= 0.8:
            confidence += 0.2
        elif mean_val <= 0.3:
            confidence += 0.1
        
        # Penalty for medium values (uncertainty)
        if 0.4 <= mean_val <= 0.6:
            confidence -= 0.1
        
        return min(1.0, max(0.1, confidence))
    
    def _generate_explanation(self, results: List[float], final_score: float) -> str:
        """Generate human-readable explanation"""
        market_impact, novelty, sentiment_strength, urgency, source_cred = results
        
        explanations = []
        
        # More rigorous thresholds
        if final_score >= 0.75:
            explanations.append("🔥 CRITICAL: High market impact event")
        elif final_score >= 0.6:
            explanations.append("📈 HIGH: Significant for crypto market")
        elif final_score >= 0.45:
            explanations.append("📊 MEDIUM: Moderate importance")
        else:
            explanations.append("📉 LOW: Limited impact")
        
        # Specific explanations for high scores
        if market_impact >= 0.8:
            explanations.append("Very strong market impact")
        elif market_impact >= 0.6:
            explanations.append("Significant market impact")
        
        if novelty >= 0.8:
            explanations.append("New breakthrough information")
        elif novelty >= 0.6:
            explanations.append("Fresh information")
        
        if urgency >= 0.7:
            explanations.append("Urgent/breaking news")
        
        if source_cred >= 0.85:
            explanations.append("Very credible source")
        elif source_cred >= 0.7:
            explanations.append("Credible source")
        
        # Add warnings for low scores
        if source_cred < 0.5:
            explanations.append("⚠️ Unverified source")
        
        if novelty < 0.4:
            explanations.append("📰 May be old information")
        
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
        
        # Simple rule-based analysis - more rigorous
        text = f"{title} {content}".lower()
        
        # Very conservative scoring
        importance = 0.2
        
        # Check only most critical keywords
        critical_keywords = [
            'sec action', 'etf approved', 'etf rejected', 'hack', 'billions lost',
            'regulation ban', 'bitcoin halving', 'ethereum merge', 'major partnership'
        ]
        
        for keyword in critical_keywords:
            if keyword in text:
                importance += 0.2
        
        # Check source credibility
        source_score = 0.3
        if any(domain in source.lower() for domain in ['reuters', 'bloomberg', 'sec.gov', 'coindesk']):
            source_score = 0.8
            importance += 0.2
        elif any(domain in source.lower() for domain in ['cnbc', 'wsj', 'ft.com']):
            source_score = 0.7
            importance += 0.1
        
        # Very rigorous - fallback should give low scores
        importance = min(0.6, importance)  # Max 60% for fallback
        
        return {
            'importance_score': importance,
            'confidence': 0.3,  # Low confidence for fallback
            'components': {
                'market_impact': min(0.6, importance),
                'information_novelty': 0.4,
                'sentiment_strength': 0.3,
                'urgency_level': 0.3,
                'source_credibility': source_score
            },
            'explanation': '⚠️ Fallback analysis - limited accuracy',
            'crypto_mentions': self._extract_crypto_mentions(text),
            'key_themes': [],
            'analyzed_at': datetime.now().isoformat(),
            'model_version': 'fallback_conservative'
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