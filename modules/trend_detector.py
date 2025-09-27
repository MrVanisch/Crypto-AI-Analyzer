"""
Trend Detector for Crypto AI Analyzer
Detects trending topics by comparing current vs historical search volumes
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics
import numpy as np
from loguru import logger
from dataclasses import dataclass
import hashlib

@dataclass
class TrendDataPoint:
    """Single trend measurement"""
    keyword: str
    search_volume: int
    timestamp: datetime
    ai_importance: float
    articles_count: int
    top_sources: List[str]

class TrendDetector:
    def __init__(self):
        """Initialize trend detection system"""
        
        # Database setup
        self.db_path = Path("data/historical/trends.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Trend analysis settings
        self.trend_config = {
            'lookback_hours': [1, 6, 24, 72, 168],  # 1h, 6h, 1d, 3d, 1w
            'min_data_points': 3,                    # Minimum points for trend analysis
            'volatility_threshold': 0.5,             # High volatility = trending
            'growth_thresholds': {
                'declining': -0.30,    # -30% or more
                'stable': 0.20,        # -30% to +20%
                'growing': 1.00,       # +20% to +100%
                'trending': 3.00,      # +100% to +300%
                'viral': 10.00,        # +300%+
                'mega_viral': 50.00    # +5000%+
            }
        }
        
        # Cache for recent calculations
        self.trend_cache = {}
        self.cache_duration = 300  # 5 minutes
        
        logger.info("📈 Trend Detector initialized")
    
    def _init_database(self):
        """Initialize SQLite database for trend storage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trend_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keyword TEXT NOT NULL,
                        search_volume INTEGER NOT NULL,
                        ai_importance REAL NOT NULL,
                        articles_count INTEGER NOT NULL,
                        top_sources TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        date_created TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_keyword_timestamp 
                    ON trend_data(keyword, timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON trend_data(timestamp)
                """)
                
                conn.commit()
                logger.info("✅ Trend database initialized")
                
        except Exception as e:
            logger.error(f"❌ Error initializing trend database: {e}")
            raise
    
    async def analyze_trend(self, keyword: str, current_volume: int, current_ai_importance: float = 0.5, articles: List[Dict] = None) -> float:
        """
        Analyze trend for a keyword by comparing with historical data
        
        Args:
            keyword: Search keyword
            current_volume: Current search volume
            current_ai_importance: Current AI importance score
            articles: Current articles found
            
        Returns:
            Trend score (0.0 - 1.0)
        """
        # Check cache
        cache_key = f"{keyword}_{current_volume}_{int(datetime.now().timestamp() // 300)}"  # 5-min buckets
        if cache_key in self.trend_cache:
            logger.debug(f"💾 Using cached trend analysis for: {keyword}")
            return self.trend_cache[cache_key]
        
        try:
            # Store current data point
            await self._store_data_point(keyword, current_volume, current_ai_importance, articles or [])
            
            # Get historical data
            historical_data = self._get_historical_data(keyword)
            
            if len(historical_data) < self.trend_config['min_data_points']:
                logger.debug(f"📊 Insufficient historical data for {keyword} ({len(historical_data)} points)")
                trend_score = 0.5  # Neutral score for new keywords
            else:
                # Calculate trend score
                trend_score = self._calculate_trend_score(current_volume, historical_data)
            
            # Cache result
            self.trend_cache[cache_key] = trend_score
            
            logger.info(f"📈 Trend analysis for '{keyword}': {trend_score:.3f} (volume: {current_volume})")
            return trend_score
            
        except Exception as e:
            logger.error(f"❌ Error analyzing trend for {keyword}: {e}")
            return 0.5  # Neutral fallback
    
    async def _store_data_point(self, keyword: str, volume: int, ai_importance: float, articles: List[Dict]):
        """Store current data point in database"""
        try:
            # Prepare data
            top_sources = [article.get('source', '') for article in articles[:5]]
            top_sources_json = json.dumps(top_sources)
            timestamp = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO trend_data 
                    (keyword, search_volume, ai_importance, articles_count, top_sources, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (keyword, volume, ai_importance, len(articles), top_sources_json, timestamp))
                
                conn.commit()
                
            logger.debug(f"💾 Stored trend data: {keyword} -> {volume} results")
            
        except Exception as e:
            logger.error(f"❌ Error storing trend data: {e}")
    
    def _get_historical_data(self, keyword: str, hours_back: int = 168) -> List[TrendDataPoint]:
        """Get historical data for keyword"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            cutoff_iso = cutoff_time.isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT keyword, search_volume, ai_importance, articles_count, top_sources, timestamp
                    FROM trend_data 
                    WHERE keyword = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                """, (keyword, cutoff_iso))
                
                rows = cursor.fetchall()
                
                data_points = []
                for row in rows:
                    try:
                        top_sources = json.loads(row[4]) if row[4] else []
                        timestamp = datetime.fromisoformat(row[5])
                        
                        data_point = TrendDataPoint(
                            keyword=row[0],
                            search_volume=row[1],
                            ai_importance=row[2],
                            articles_count=row[3],
                            top_sources=top_sources,
                            timestamp=timestamp
                        )
                        data_points.append(data_point)
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing data point: {e}")
                        continue
                
                logger.debug(f"📊 Retrieved {len(data_points)} historical points for {keyword}")
                return data_points
                
        except Exception as e:
            logger.error(f"❌ Error retrieving historical data: {e}")
            return []
    
    def _calculate_trend_score(self, current_volume: int, historical_data: List[TrendDataPoint]) -> float:
        """Calculate trend score based on historical comparison"""
        if not historical_data:
            return 0.5
        
        # Get volumes for different time periods
        trend_scores = []
        
        for hours_back in self.trend_config['lookback_hours']:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            # Get data within this time period
            period_data = [
                dp for dp in historical_data 
                if dp.timestamp >= cutoff_time
            ]
            
            if len(period_data) >= 2:  # Need at least 2 points for comparison
                # Calculate average volume for this period
                avg_volume = statistics.mean([dp.search_volume for dp in period_data])
                
                if avg_volume > 0:
                    # Calculate percentage change
                    pct_change = (current_volume - avg_volume) / avg_volume
                    
                    # Convert to trend score
                    period_score = self._pct_change_to_score(pct_change)
                    trend_scores.append((period_score, hours_back))
                    
                    logger.debug(f"📊 {hours_back}h trend: {pct_change:+.1%} -> score {period_score:.3f}")
        
        if not trend_scores:
            return 0.5
        
        # Weight recent trends more heavily
        weighted_score = 0
        total_weight = 0
        
        for score, hours_back in trend_scores:
            # Recent trends get higher weight
            weight = 1.0 / (1 + hours_back / 24)  # 24h gets weight 0.5, 1h gets weight 1.0
            weighted_score += score * weight
            total_weight += weight
        
        final_score = weighted_score / total_weight if total_weight > 0 else 0.5
        
        # Apply volatility bonus
        volatility_bonus = self._calculate_volatility_bonus(historical_data)
        final_score = min(1.0, final_score + volatility_bonus)
        
        return final_score
    
    def _pct_change_to_score(self, pct_change: float) -> float:
        """Convert percentage change to trend score (0-1)"""
        thresholds = self.trend_config['growth_thresholds']
        
        if pct_change <= thresholds['declining']:
            return 0.1  # Declining trend
        elif pct_change <= thresholds['stable']:
            # Linear interpolation between 0.1 and 0.5
            return 0.1 + (pct_change - thresholds['declining']) / (thresholds['stable'] - thresholds['declining']) * 0.4
        elif pct_change <= thresholds['growing']:
            # Linear interpolation between 0.5 and 0.7
            return 0.5 + (pct_change - thresholds['stable']) / (thresholds['growing'] - thresholds['stable']) * 0.2
        elif pct_change <= thresholds['trending']:
            # Linear interpolation between 0.7 and 0.9
            return 0.7 + (pct_change - thresholds['growing']) / (thresholds['trending'] - thresholds['growing']) * 0.2
        elif pct_change <= thresholds['viral']:
            # Linear interpolation between 0.9 and 0.95
            return 0.9 + (pct_change - thresholds['trending']) / (thresholds['viral'] - thresholds['trending']) * 0.05
        else:
            # Mega viral
            return min(1.0, 0.95 + (pct_change - thresholds['viral']) / thresholds['mega_viral'] * 0.05)
    
    def _calculate_volatility_bonus(self, historical_data: List[TrendDataPoint]) -> float:
        """Calculate volatility bonus (high volatility = trending)"""
        if len(historical_data) < 3:
            return 0.0
        
        # Get recent volumes
        recent_volumes = [dp.search_volume for dp in historical_data[-10:]]  # Last 10 points
        
        if len(recent_volumes) < 3:
            return 0.0
        
        # Calculate coefficient of variation (std dev / mean)
        mean_vol = statistics.mean(recent_volumes)
        if mean_vol == 0:
            return 0.0
        
        std_vol = statistics.stdev(recent_volumes)
        cv = std_vol / mean_vol
        
        # High volatility gets bonus (up to 0.1)
        volatility_bonus = min(0.1, cv * 0.2)
        
        logger.debug(f"📊 Volatility bonus: {volatility_bonus:.3f} (CV: {cv:.3f})")
        return volatility_bonus
    
    async def get_trending_keywords(self, limit: int = 10, hours_back: int = 24) -> List[Dict]:
        """Get currently trending keywords"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            cutoff_iso = cutoff_time.isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT keyword, 
                           COUNT(*) as data_points,
                           AVG(search_volume) as avg_volume,
                           AVG(ai_importance) as avg_ai_importance,
                           MAX(timestamp) as latest_timestamp
                    FROM trend_data 
                    WHERE timestamp >= ?
                    GROUP BY keyword
                    HAVING COUNT(*) >= ?
                    ORDER BY avg_volume DESC, avg_ai_importance DESC
                    LIMIT ?
                """, (cutoff_iso, self.trend_config['min_data_points'], limit))
                
                rows = cursor.fetchall()
                
                trending = []
                for row in rows:
                    keyword = row[0]
                    
                    # Get trend score for this keyword
                    historical_data = self._get_historical_data(keyword, hours_back)
                    if historical_data:
                        latest_volume = historical_data[-1].search_volume
                        trend_score = self._calculate_trend_score(latest_volume, historical_data)
                        
                        trending.append({
                            'keyword': keyword,
                            'trend_score': trend_score,
                            'current_volume': latest_volume,
                            'avg_volume': row[2],
                            'avg_ai_importance': row[3],
                            'data_points': row[1],
                            'latest_update': row[4]
                        })
                
                # Sort by trend score
                trending.sort(key=lambda x: x['trend_score'], reverse=True)
                
                logger.info(f"📈 Found {len(trending)} trending keywords")
                return trending
                
        except Exception as e:
            logger.error(f"❌ Error getting trending keywords: {e}")
            return []
    
    async def get_keyword_history(self, keyword: str, hours_back: int = 168) -> Dict:
        """Get detailed history for a specific keyword"""
        historical_data = self._get_historical_data(keyword, hours_back)
        
        if not historical_data:
            return {
                'keyword': keyword,
                'data_points': 0,
                'history': [],
                'trend_analysis': 'No historical data available'
            }
        
        # Prepare history data
        history = []
        for dp in historical_data:
            history.append({
                'timestamp': dp.timestamp.isoformat(),
                'search_volume': dp.search_volume,
                'ai_importance': dp.ai_importance,
                'articles_count': dp.articles_count,
                'top_sources': dp.top_sources
            })
        
        # Calculate trend analysis
        current_volume = historical_data[-1].search_volume
        trend_score = self._calculate_trend_score(current_volume, historical_data)
        
        # Generate trend description
        if trend_score >= 0.9:
            trend_desc = "🚀 VIRAL - Massive trending activity"
        elif trend_score >= 0.7:
            trend_desc = "📈 TRENDING - Strong upward momentum"
        elif trend_score >= 0.6:
            trend_desc = "📊 GROWING - Moderate increase"
        elif trend_score >= 0.4:
            trend_desc = "📉 STABLE - Normal activity levels"
        else:
            trend_desc = "📉 DECLINING - Decreasing interest"
        
        return {
            'keyword': keyword,
            'data_points': len(historical_data),
            'history': history,
            'current_trend_score': trend_score,
            'trend_analysis': trend_desc,
            'volume_range': {
                'min': min(dp.search_volume for dp in historical_data),
                'max': max(dp.search_volume for dp in historical_data),
                'current': current_volume
            },
            'ai_importance_avg': statistics.mean([dp.ai_importance for dp in historical_data])
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old trend data to save space"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            cutoff_iso = cutoff_time.isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM trend_data WHERE timestamp < ?", (cutoff_iso,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"🧹 Cleaned up {deleted_count} old trend data points")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up old data: {e}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total records
                cursor = conn.execute("SELECT COUNT(*) FROM trend_data")
                total_records = cursor.fetchone()[0]
                
                # Unique keywords
                cursor = conn.execute("SELECT COUNT(DISTINCT keyword) FROM trend_data")
                unique_keywords = cursor.fetchone()[0]
                
                # Date range
                cursor = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM trend_data")
                date_range = cursor.fetchone()
                
                # Top keywords by volume
                cursor = conn.execute("""
                    SELECT keyword, AVG(search_volume) as avg_vol
                    FROM trend_data 
                    WHERE timestamp >= datetime('now', '-7 days')
                    GROUP BY keyword 
                    ORDER BY avg_vol DESC 
                    LIMIT 5
                """)
                top_keywords = [{'keyword': row[0], 'avg_volume': row[1]} for row in cursor.fetchall()]
                
                return {
                    'total_records': total_records,
                    'unique_keywords': unique_keywords,
                    'date_range': {
                        'earliest': date_range[0],
                        'latest': date_range[1]
                    },
                    'top_keywords_7d': top_keywords,
                    'database_size_mb': self.db_path.stat().st_size / (1024 * 1024)
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}

# Test function
async def test_trend_detector():
    """Test the trend detector"""
    print("🧪 Testing Trend Detector...")
    
    detector = TrendDetector()
    
    # Test data storage and trend analysis
    test_keywords = ['bitcoin news', 'ethereum update', 'crypto regulation']
    
    print("\n📊 Simulating trend data...")
    
    # Simulate historical data (declining trend)
    for i in range(5):
        timestamp_offset = timedelta(hours=i)
        volume = 1000 - (i * 150)  # Declining volume
        
        for keyword in test_keywords:
            await detector.analyze_trend(keyword, volume, 0.5 + (i * 0.1))
        
        await asyncio.sleep(0.1)  # Small delay
    
    # Current data (sudden spike)
    print("\n🚀 Testing viral trend detection...")
    for keyword in test_keywords:
        # Simulate viral spike
        viral_volume = 5000 if 'bitcoin' in keyword else 2000
        trend_score = await detector.analyze_trend(keyword, viral_volume, 0.8)
        
        print(f"📈 {keyword}: trend_score={trend_score:.3f} (volume: {viral_volume})")
    
    # Get trending keywords
    print("\n📈 Current trending keywords:")
    trending = await detector.get_trending_keywords(limit=5)
    for item in trending:
        print(f"🔥 {item['keyword']}: score={item['trend_score']:.3f}, volume={item['current_volume']}")
    
    # Get database stats
    print(f"\n📊 Database Stats:")
    stats = detector.get_database_stats()
    print(f"   Records: {stats.get('total_records', 0)}")
    print(f"   Keywords: {stats.get('unique_keywords', 0)}")
    print(f"   Size: {stats.get('database_size_mb', 0):.2f} MB")

if __name__ == "__main__":
    asyncio.run(test_trend_detector())