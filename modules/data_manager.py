"""
Data Manager for Crypto AI Analyzer
Handles data storage, caching, and persistence
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

class DataManager:
    def __init__(self):
        """Initialize data management system"""
        
        # Create data directories
        self.data_root = Path("data")
        self.processed_path = self.data_root / "processed"
        self.raw_path = self.data_root / "raw_articles"
        
        for path in [self.data_root, self.processed_path, self.raw_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Database for analysis results
        self.db_path = self.data_root / "analysis_results.db"
        self._init_database()
        
        logger.info("💾 Data Manager initialized")
    
    def _init_database(self):
        """Initialize SQLite database for analysis results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keyword TEXT NOT NULL,
                        importance_score REAL NOT NULL,
                        confidence REAL NOT NULL,
                        ai_importance REAL,
                        search_volume INTEGER,
                        trend_momentum REAL,
                        source_quality REAL,
                        explanation TEXT,
                        recommendation TEXT,
                        top_sources TEXT,
                        timestamp TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_keyword_timestamp 
                    ON analysis_results(keyword, timestamp)
                """)
                
                conn.commit()
                
            logger.debug("✅ Analysis results database initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")
            raise
    
    async def save_analysis_results(self, results: List[Dict]):
        """Save analysis results to database"""
        if not results:
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for result in results:
                    conn.execute("""
                        INSERT INTO analysis_results 
                        (keyword, importance_score, confidence, ai_importance, 
                         search_volume, trend_momentum, source_quality, 
                         explanation, recommendation, top_sources, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        result.get('keyword', ''),
                        result.get('importance', 0),
                        result.get('confidence', 0),
                        result.get('components', {}).get('ai_importance', 0),
                        result.get('raw_data', {}).get('search_volume', 0),
                        result.get('components', {}).get('trend_momentum', 0),
                        result.get('components', {}).get('source_quality', 0),
                        result.get('explanation', ''),
                        result.get('recommendation', ''),
                        json.dumps(result.get('top_sources', [])),
                        result.get('analyzed_at', datetime.now().isoformat())
                    ))
                
                conn.commit()
                
            logger.info(f"💾 Saved {len(results)} analysis results")
            
        except Exception as e:
            logger.error(f"❌ Error saving analysis results: {e}")

if __name__ == "__main__":
    manager = DataManager()
    print("💾 Data Manager ready")