"""
Importance Scorer for Crypto AI Analyzer
Combines AI analysis with search volume, trends, and source quality for final scoring
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import statistics
import math

class ImportanceScorer:
    def __init__(self):
        """Initialize the importance scoring engine"""
        
        # Scoring weights - how much each factor contributes to final score
        self.scoring_weights = {
            'ai_importance': 0.40,        # AI model assessment (most important)
            'search_volume': 0.25,        # Google search volume
            'trend_momentum': 0.20,       # Trending vs historical
            'source_quality': 0.10,       # Source credibility
            'time_decay': 0.05           # Freshness factor
        }
        
        # Search volume scoring thresholds
        self.volume_thresholds = {
            'minimal': 10,      # 0-10 results
            'low': 50,          # 11-50 results
            'moderate': 200,    # 51-200 results
            'high': 1000,       # 201-1000 results
            'viral': 5000,      # 1000+ results
            'mega_viral': 50000 # 5000+ results
        }
        
        # Trend momentum thresholds (percentage change)
        self.trend_thresholds = {
            'declining': -30,   # -30% or more
            'stable': 20,       # -30% to +20%
            'growing': 100,     # +20% to +100%
            'trending': 300,    # +100% to +300%
            'viral': 1000       # +300%+
        }
        
        # Source quality tiers
        self.source_tiers = {
            'tier_1': {
                'domains': ['reuters.com', 'bloomberg.com', 'coindesk.com', 'wsj.com', 'ft.com'],
                'multiplier': 1.0
            },
            'tier_2': {
                'domains': ['cointelegraph.com', 'decrypt.co', 'theblock.co', 'cnbc.com', 'yahoo.com'],
                'multiplier': 0.85
            },
            'tier_3': {
                'domains': ['marketwatch.com', 'investing.com', 'benzinga.com', 'cryptonews.com'],
                'multiplier': 0.7
            },
            'tier_4': {
                'domains': ['medium.com', 'reddit.com', 'twitter.com', 'telegram.org'],
                'multiplier': 0.5
            }
        }
        
        # Historical data for trend analysis
        self.historical_data_path = Path("data/historical")
        self.historical_data_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("🎯 Importance Scorer initialized")
    
    def calculate_final_score(
        self, 
        keyword: str,
        search_volume: int,
        ai_results: List[Dict],
        trend_score: float,
        articles: List[Dict]
    ) -> Dict:
        """
        Calculate final importance score combining all factors
        
        Args:
            keyword: Search keyword used
            search_volume: Number of Google search results
            ai_results: List of AI analysis results for articles
            trend_score: Trend momentum score (0-1)
            articles: List of article data
            
        Returns:
            Comprehensive scoring result
        """
        logger.info(f"🎯 Calculating final score for: {keyword}")
        
        try:
            # 1. AI Importance Score (most important factor)
            ai_score = self._calculate_ai_score(ai_results)
            
            # 2. Search Volume Score
            volume_score = self._calculate_volume_score(search_volume)
            
            # 3. Source Quality Score
            source_score = self._calculate_source_score(articles)
            
            # 4. Time Decay Score (how fresh is the content)
            time_score = self._calculate_time_decay(articles)
            
            # 5. Calculate weighted final score
            final_score = (
                ai_score * self.scoring_weights['ai_importance'] +
                volume_score * self.scoring_weights['search_volume'] +
                trend_score * self.scoring_weights['trend_momentum'] +
                source_score * self.scoring_weights['source_quality'] +
                time_score * self.scoring_weights['time_decay']
            )
            
            # Apply bonus multipliers
            final_score = self._apply_bonus_multipliers(
                final_score, keyword, search_volume, ai_results, articles
            )
            
            # Ensure score is within bounds
            final_score = max(0.0, min(1.0, final_score))
            
            # Calculate confidence level
            confidence = self._calculate_confidence(ai_results, search_volume, articles)
            
            # Generate explanation
            explanation = self._generate_explanation(
                final_score, ai_score, volume_score, trend_score, source_score, keyword
            )
            
            # Create result
            result = {
                'keyword': keyword,
                'importance': final_score,
                'confidence': confidence,
                'components': {
                    'ai_importance': ai_score,
                    'search_volume': volume_score,
                    'trend_momentum': trend_score,
                    'source_quality': source_score,
                    'time_decay': time_score
                },
                'raw_data': {
                    'search_volume': search_volume,
                    'ai_results_count': len(ai_results),
                    'articles_count': len(articles),
                    'best_ai_score': max((r.get('importance_score', 0) for r in ai_results), default=0),
                    'avg_ai_confidence': statistics.mean([r.get('confidence', 0) for r in ai_results]) if ai_results else 0
                },
                'explanation': explanation,
                'recommendation': self._get_recommendation(final_score, confidence),
                'top_sources': self._get_top_sources(articles),
                'analyzed_at': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Final score calculated: {final_score:.3f} (confidence: {confidence:.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculating final score: {e}")
            return self._get_fallback_score(keyword, search_volume)
    
    def _calculate_ai_score(self, ai_results: List[Dict]) -> float:
        """Calculate aggregate AI importance score"""
        if not ai_results:
            return 0.0
        
        # Get all AI importance scores
        ai_scores = [result.get('importance_score', 0) for result in ai_results]
        ai_confidences = [result.get('confidence', 0) for result in ai_results]
        
        if not ai_scores:
            return 0.0
        
        # Weight by confidence and take best scores
        weighted_scores = []
        for score, confidence in zip(ai_scores, ai_confidences):
            weighted_score = score * (0.5 + confidence * 0.5)  # Boost high-confidence scores
            weighted_scores.append(weighted_score)
        
        # Take top 3 scores (ignore outliers)
        top_scores = sorted(weighted_scores, reverse=True)[:3]
        
        # Calculate final AI score
        if len(top_scores) == 1:
            return top_scores[0]
        elif len(top_scores) == 2:
            return statistics.mean(top_scores)
        else:
            # Weight: 50% best score, 30% second, 20% third
            return (top_scores[0] * 0.5 + top_scores[1] * 0.3 + top_scores[2] * 0.2)
    
    def _calculate_volume_score(self, search_volume: int) -> float:
        """Calculate score based on Google search volume"""
        if search_volume <= self.volume_thresholds['minimal']:
            return 0.1
        elif search_volume <= self.volume_thresholds['low']:
            return 0.3
        elif search_volume <= self.volume_thresholds['moderate']:
            return 0.5
        elif search_volume <= self.volume_thresholds['high']:
            return 0.7
        elif search_volume <= self.volume_thresholds['viral']:
            return 0.9
        else:  # Mega viral
            return 1.0
    
    def _calculate_source_score(self, articles: List[Dict]) -> float:
        """Calculate aggregate source quality score"""
        if not articles:
            return 0.5
        
        source_scores = []
        
        for article in articles:
            source = article.get('source', '').lower()
            score = 0.4  # Default for unknown sources
            
            # Check which tier the source belongs to
            for tier_name, tier_info in self.source_tiers.items():
                if any(domain in source for domain in tier_info['domains']):
                    score = tier_info['multiplier']
                    break
            
            source_scores.append(score)
        
        # Return weighted average (give more weight to top sources)
        source_scores.sort(reverse=True)
        
        if len(source_scores) == 1:
            return source_scores[0]
        elif len(source_scores) >= 3:
            # Weight top 3 sources: 50%, 30%, 20%
            return (source_scores[0] * 0.5 + source_scores[1] * 0.3 + source_scores[2] * 0.2)
        else:
            return statistics.mean(source_scores)
    
    def _calculate_time_decay(self, articles: List[Dict]) -> float:
        """Calculate freshness score based on article age"""
        if not articles:
            return 0.5
        
        current_time = datetime.now()
        time_scores = []
        
        for article in articles:
            # Try to get article timestamp
            extracted_at = article.get('extracted_at', '')
            if extracted_at:
                try:
                    article_time = datetime.fromisoformat(extracted_at.replace('Z', ''))
                    hours_old = (current_time - article_time).total_seconds() / 3600
                    
                    # Scoring based on age
                    if hours_old <= 1:
                        score = 1.0  # Very fresh
                    elif hours_old <= 6:
                        score = 0.9  # Fresh
                    elif hours_old <= 24:
                        score = 0.7  # Recent
                    elif hours_old <= 72:
                        score = 0.5  # Somewhat old
                    else:
                        score = 0.3  # Old
                    
                    time_scores.append(score)
                except:
                    time_scores.append(0.6)  # Default if parsing fails
            else:
                time_scores.append(0.6)  # Default if no timestamp
        
        return statistics.mean(time_scores) if time_scores else 0.6
    
    def _apply_bonus_multipliers(
        self, 
        base_score: float, 
        keyword: str, 
        search_volume: int, 
        ai_results: List[Dict], 
        articles: List[Dict]
    ) -> float:
        """Apply bonus multipliers for special conditions"""
        multiplier = 1.0
        
        # Breaking news bonus
        if any('breaking' in article.get('title', '').lower() for article in articles):
            multiplier += 0.15
            logger.debug("📈 Breaking news bonus applied")
        
        # Regulatory news bonus
        regulatory_keywords = ['sec', 'regulation', 'ban', 'etf', 'legal']
        if any(keyword in keyword.lower() for keyword in regulatory_keywords):
            multiplier += 0.20
            logger.debug("📈 Regulatory news bonus applied")
        
        # High search volume + high AI score bonus
        if search_volume > 1000 and base_score > 0.7:
            multiplier += 0.10
            logger.debug("📈 Viral + high AI bonus applied")
        
        # Multiple high-quality sources bonus
        tier_1_count = sum(1 for article in articles 
                          if any(domain in article.get('source', '').lower() 
                                for domain in self.source_tiers['tier_1']['domains']))
        if tier_1_count >= 3:
            multiplier += 0.10
            logger.debug("📈 Multiple tier-1 sources bonus applied")
        
        # Consensus bonus (multiple AI models agree)
        if ai_results:
            ai_scores = [r.get('importance_score', 0) for r in ai_results]
            if len(ai_scores) >= 3:
                std_dev = statistics.stdev(ai_scores)
                if std_dev < 0.1:  # Low deviation = consensus
                    multiplier += 0.05
                    logger.debug("📈 AI consensus bonus applied")
        
        return base_score * multiplier
    
    def _calculate_confidence(self, ai_results: List[Dict], search_volume: int, articles: List[Dict]) -> float:
        """Calculate confidence in the final score"""
        confidence = 0.5  # Base confidence
        
        # AI confidence contribution
        if ai_results:
            avg_ai_confidence = statistics.mean([r.get('confidence', 0) for r in ai_results])
            confidence += avg_ai_confidence * 0.3
        
        # Search volume confidence (more results = more confident)
        if search_volume > 100:
            confidence += 0.2
        elif search_volume > 20:
            confidence += 0.1
        
        # Source diversity confidence
        unique_sources = len(set(article.get('source', '') for article in articles))
        if unique_sources >= 3:
            confidence += 0.15
        elif unique_sources >= 2:
            confidence += 0.10
        
        # Multiple AI results confidence
        if len(ai_results) >= 3:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_explanation(
        self, 
        final_score: float, 
        ai_score: float, 
        volume_score: float, 
        trend_score: float, 
        source_score: float, 
        keyword: str
    ) -> str:
        """Generate human-readable explanation of the score"""
        explanations = []
        
        # Overall assessment
        if final_score >= 0.8:
            explanations.append("🔥 CRITICAL IMPORTANCE")
        elif final_score >= 0.6:
            explanations.append("📈 HIGH IMPORTANCE")
        elif final_score >= 0.4:
            explanations.append("📊 MODERATE IMPORTANCE")
        elif final_score >= 0.2:
            explanations.append("📉 LOW IMPORTANCE")
        else:
            explanations.append("🔍 MINIMAL IMPORTANCE")
        
        # Component explanations
        if ai_score >= 0.7:
            explanations.append("AI models indicate high significance")
        
        if volume_score >= 0.7:
            explanations.append("High search volume detected")
        elif volume_score <= 0.3:
            explanations.append("Limited search interest")
        
        if trend_score >= 0.7:
            explanations.append("Strong trending momentum")
        elif trend_score <= 0.3:
            explanations.append("Declining trend")
        
        if source_score >= 0.8:
            explanations.append("Premium sources reporting")
        elif source_score <= 0.5:
            explanations.append("Lower-tier sources mainly")
        
        # Special keyword insights
        if 'bitcoin' in keyword.lower():
            explanations.append("Bitcoin-related (tier-1 crypto)")
        elif 'ethereum' in keyword.lower():
            explanations.append("Ethereum-related (tier-1 crypto)")
        
        return " • ".join(explanations)
    
    def _get_recommendation(self, score: float, confidence: float) -> str:
        """Get action recommendation based on score and confidence"""
        if score >= 0.8 and confidence >= 0.7:
            return "🚨 IMMEDIATE ATTENTION REQUIRED"
        elif score >= 0.7 and confidence >= 0.6:
            return "⚡ HIGH PRIORITY - Review quickly"
        elif score >= 0.6 and confidence >= 0.5:
            return "📋 MEDIUM PRIORITY - Monitor closely"
        elif score >= 0.4:
            return "👁️ LOW PRIORITY - Keep watching"
        else:
            return "📝 BACKGROUND INFO - No action needed"
    
    def _get_top_sources(self, articles: List[Dict]) -> List[str]:
        """Get list of top sources for this analysis"""
        sources = []
        for article in articles:
            source = article.get('source', '')
            if source and source not in sources:
                sources.append(source)
        
        # Sort by tier (best sources first)
        def get_source_tier(source):
            source_lower = source.lower()
            for tier_num, (tier_name, tier_info) in enumerate(self.source_tiers.items(), 1):
                if any(domain in source_lower for domain in tier_info['domains']):
                    return tier_num
            return 5  # Unknown sources last
        
        sources.sort(key=get_source_tier)
        return sources[:5]  # Top 5 sources
    
    def _get_fallback_score(self, keyword: str, search_volume: int) -> Dict:
        """Fallback scoring when main calculation fails"""
        logger.warning("🔄 Using fallback scoring")
        
        # Simple fallback based on search volume
        if search_volume > 1000:
            score = 0.7
        elif search_volume > 100:
            score = 0.5
        elif search_volume > 10:
            score = 0.3
        else:
            score = 0.1
        
        return {
            'keyword': keyword,
            'importance': score,
            'confidence': 0.4,
            'components': {
                'ai_importance': 0.5,
                'search_volume': self._calculate_volume_score(search_volume),
                'trend_momentum': 0.5,
                'source_quality': 0.5,
                'time_decay': 0.5
            },
            'raw_data': {
                'search_volume': search_volume,
                'ai_results_count': 0,
                'articles_count': 0,
                'best_ai_score': 0,
                'avg_ai_confidence': 0
            },
            'explanation': f"⚠️ Fallback analysis - {search_volume} search results",
            'recommendation': "🔍 Manual review recommended",
            'top_sources': [],
            'analyzed_at': datetime.now().isoformat()
        }
    
    def update_scoring_weights(self, new_weights: Dict[str, float]):
        """Update scoring weights (for tuning)"""
        if abs(sum(new_weights.values()) - 1.0) > 0.01:
            raise ValueError("Scoring weights must sum to 1.0")
        
        self.scoring_weights.update(new_weights)
        logger.info(f"📊 Scoring weights updated: {self.scoring_weights}")
    
    def get_scoring_stats(self) -> Dict:
        """Get current scoring configuration stats"""
        return {
            'weights': self.scoring_weights,
            'volume_thresholds': self.volume_thresholds,
            'trend_thresholds': self.trend_thresholds,
            'source_tiers': {tier: info['domains'] for tier, info in self.source_tiers.items()}
        }

# Test function
async def test_importance_scorer():
    """Test the importance scorer"""
    print("🧪 Testing Importance Scorer...")
    
    scorer = ImportanceScorer()
    
    # Mock test data
    test_cases = [
        {
            'keyword': 'bitcoin etf sec approval',
            'search_volume': 15000,
            'ai_results': [
                {'importance_score': 0.89, 'confidence': 0.92},
                {'importance_score': 0.85, 'confidence': 0.88},
                {'importance_score': 0.91, 'confidence': 0.95}
            ],
            'trend_score': 0.85,
            'articles': [
                {'source': 'reuters.com', 'title': 'SEC Approves Bitcoin ETF', 'extracted_at': datetime.now().isoformat()},
                {'source': 'coindesk.com', 'title': 'Breaking: Bitcoin ETF Gets Green Light', 'extracted_at': datetime.now().isoformat()},
                {'source': 'bloomberg.com', 'title': 'Bitcoin ETF Approval Sends Markets Soaring', 'extracted_at': datetime.now().isoformat()}
            ]
        },
        {
            'keyword': 'dogecoin price prediction',
            'search_volume': 245,
            'ai_results': [
                {'importance_score': 0.32, 'confidence': 0.45},
                {'importance_score': 0.28, 'confidence': 0.41}
            ],
            'trend_score': 0.25,
            'articles': [
                {'source': 'cryptoblog.com', 'title': 'Dogecoin Price Analysis', 'extracted_at': datetime.now().isoformat()},
                {'source': 'random-crypto-site.com', 'title': 'DOGE to the moon?', 'extracted_at': datetime.now().isoformat()}
            ]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['keyword']}")
        
        result = scorer.calculate_final_score(
            test_case['keyword'],
            test_case['search_volume'],
            test_case['ai_results'],
            test_case['trend_score'],
            test_case['articles']
        )
        
        print(f"🎯 Final Score: {result['importance']:.3f}")
        print(f"🎯 Confidence: {result['confidence']:.3f}")
        print(f"💡 Explanation: {result['explanation']}")
        print(f"📋 Recommendation: {result['recommendation']}")
        print(f"📊 Components:")
        for component, score in result['components'].items():
            print(f"   • {component}: {score:.3f}")
        print(f"🌐 Top Sources: {', '.join(result['top_sources'][:3])}")

if __name__ == "__main__":
    asyncio.run(test_importance_scorer())