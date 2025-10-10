"""
Google Search API Integration for Crypto AI Analyzer
Version 1.0 - Paid API with high quality results
"""

import os
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger
import time
from urllib.parse import urlparse
import json

def get_searcher_info():
    """Get information about this searcher"""
    return {
        'name': 'Google Custom Search',
        'version': '1.0',
        'cost': 'PAID ($5 per 1000 searches after 100 free)',
        'api_key_required': True,
        'daily_limit': '100 searches/day (free tier)',
        'advantages': [
            '✅ Highest quality search results',
            '✅ Best relevance ranking',
            '✅ Most comprehensive coverage',
            '✅ Precise time filtering'
        ],
        'disadvantages': [
            '❌ Requires API key setup',
            '❌ Limited free tier (100/day)',
            '❌ Costs money after free tier',
            '❌ More complex setup'
        ]
    }

class GoogleSearcher:
    def __init__(self):
        """Initialize Google Search API client"""
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_CSE_ID')
        
        if not self.api_key or not self.search_engine_id:
            logger.error("❌ Google API credentials not found in environment variables")
            raise ValueError(
                "Missing Google API credentials. Set GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables"
            )
        
        # Initialize Google Custom Search service
        try:
            self.service = build("customsearch", "v1", developerKey=self.api_key)
            logger.info("✅ Google Search API initialized successfully (v1.0 - PAID)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Search API: {e}")
            raise
        
        # Rate limiting settings
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests
        self.daily_quota_used = 0
        self.daily_quota_limit = 100  # Google CSE free tier limit
        
        # Cache settings
        self.cache = {}
        self.cache_duration = 300  # 5 minutes cache
        
        # Quality filters
        self.excluded_domains = {
            'youtube.com', 'tiktok.com', 'instagram.com', 'facebook.com',
            'pinterest.com', 'twitter.com'  # Social media - often low quality for news
        }
        
        self.preferred_domains = {
            'coindesk.com': 1.0,
            'cointelegraph.com': 0.9,
            'decrypt.co': 0.9,
            'theblock.co': 0.95,
            'reuters.com': 1.0,
            'bloomberg.com': 1.0,
            'cnbc.com': 0.8,
            'yahoo.com': 0.6,
            'marketwatch.com': 0.7
        }
    
    async def search(self, query: str, max_results: int = 20, time_filter: str = 'd1') -> List[Dict]:
        """
        Search Google for crypto-related content
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            time_filter: Time filter ('d1'=24h, 'w1'=week, 'm1'=month)
            
        Returns:
            List of search result dictionaries
        """
        # Check cache first
        cache_key = f"{query}_{max_results}_{time_filter}"
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                logger.debug(f"💾 Using cached results for: {query}")
                return cached_result
        
        # Check daily quota
        if self.daily_quota_used >= self.daily_quota_limit:
            logger.warning(f"⚠️ Daily Google API quota exceeded ({self.daily_quota_limit})")
            logger.warning("🛡️ No charges will be incurred - API will just stop working until tomorrow")
            return []
        
        try:
            # Rate limiting
            await self._enforce_rate_limit()
            
            # Prepare search parameters
            search_params = {
                'q': query,
                'cx': self.search_engine_id,
                'num': min(max_results, 10),  # Google CSE max is 10 per request
                'sort': f'date:r:{self._get_date_range(time_filter)}',
                'lr': 'lang_en',  # English results only
                'safe': 'medium',
                'fileType': '',  # Exclude file downloads
                'siteSearch': '',  # Can be used to search specific sites
            }
            
            results = []
            start_index = 1
            
            # Make multiple requests if needed (max_results > 10)
            while len(results) < max_results and start_index <= 91:  # Google CSE limit
                if start_index > 1:
                    await self._enforce_rate_limit()
                
                search_params['start'] = start_index
                search_params['num'] = min(10, max_results - len(results))
                
                # Execute search
                logger.info(f"🔍 Searching Google for: '{query}' (results {start_index}-{start_index + search_params['num'] - 1})")
                
                response = self.service.cse().list(**search_params).execute()
                self.daily_quota_used += 1
                
                # Process results
                batch_results = self._process_search_response(response, query)
                results.extend(batch_results)
                
                # Check if more results available
                if len(batch_results) < search_params['num']:
                    break  # No more results
                
                start_index += 10
            
            # Filter and rank results
            filtered_results = self._filter_and_rank_results(results)
            
            # Cache results
            self.cache[cache_key] = (filtered_results, time.time())
            
            logger.info(f"✅ Found {len(filtered_results)} quality results for: {query}")
            return filtered_results
            
        except HttpError as e:
            logger.error(f"❌ Google API error for query '{query}': {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error searching for '{query}': {e}")
            return []
    
    async def batch_search(self, queries: List[str], max_results_per_query: int = 10) -> Dict[str, List[Dict]]:
        """
        Search multiple queries efficiently
        
        Args:
            queries: List of search queries
            max_results_per_query: Max results per query
            
        Returns:
            Dictionary mapping queries to their results
        """
        logger.info(f"🔍 Starting batch search for {len(queries)} queries")
        
        # Create tasks for concurrent searching
        tasks = []
        for query in queries:
            task = asyncio.create_task(
                self.search(query, max_results_per_query)
            )
            tasks.append((query, task))
        
        # Execute searches with controlled concurrency
        results = {}
        for query, task in tasks:
            try:
                search_results = await task
                results[query] = search_results
            except Exception as e:
                logger.error(f"❌ Batch search failed for '{query}': {e}")
                results[query] = []
        
        total_results = sum(len(r) for r in results.values())
        logger.info(f"✅ Batch search completed: {total_results} total results")
        
        return results
    
    def _process_search_response(self, response: Dict, query: str) -> List[Dict]:
        """Process raw Google search API response"""
        results = []
        
        items = response.get('items', [])
        search_info = response.get('searchInformation', {})
        
        logger.debug(f"📊 Google returned {len(items)} items for '{query}'")
        logger.debug(f"📊 Total estimated results: {search_info.get('totalResults', 'unknown')}")
        
        for item in items:
            try:
                # Extract basic information
                result = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'display_url': item.get('displayLink', ''),
                    'query': query,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Extract additional metadata
                if 'pagemap' in item:
                    pagemap = item['pagemap']
                    
                    # Try to get article metadata
                    if 'metatags' in pagemap and pagemap['metatags']:
                        metatag = pagemap['metatags'][0]
                        result.update({
                            'description': metatag.get('og:description', result['snippet']),
                            'published_time': metatag.get('article:published_time', ''),
                            'author': metatag.get('article:author', ''),
                            'site_name': metatag.get('og:site_name', result['display_url'])
                        })
                
                # Parse domain for quality scoring
                parsed_url = urlparse(result['url'])
                result['domain'] = parsed_url.netloc.lower()
                
                # Add quality score
                result['domain_quality'] = self._get_domain_quality(result['domain'])
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"⚠️ Error processing search result: {e}")
                continue
        
        return results
    
    def _filter_and_rank_results(self, results: List[Dict]) -> List[Dict]:
        """Filter out low-quality results and rank by relevance"""
        filtered = []
        
        for result in results:
            # Skip excluded domains
            domain = result.get('domain', '')
            if any(excluded in domain for excluded in self.excluded_domains):
                logger.debug(f"🚫 Filtering out excluded domain: {domain}")
                continue
            
            # Skip if no title or URL
            if not result.get('title') or not result.get('url'):
                logger.debug("🚫 Filtering out result with missing title/URL")
                continue
            
            # Skip very short titles (likely not articles)
            if len(result.get('title', '')) < 10:
                logger.debug("🚫 Filtering out result with too short title")
                continue
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(result)
            result['relevance_score'] = relevance_score
            
            # Only keep results with minimum relevance
            if relevance_score >= 0.3:
                filtered.append(result)
        
        # Sort by relevance score (highest first)
        filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        logger.debug(f"📊 Filtered {len(results)} → {len(filtered)} quality results")
        return filtered
    
    def _calculate_relevance_score(self, result: Dict) -> float:
        """Calculate relevance score for a search result"""
        score = 0.5  # Base score
        
        # Domain quality bonus
        domain_quality = result.get('domain_quality', 0.5)
        score += domain_quality * 0.3
        
        # Title quality indicators
        title = result.get('title', '').lower()
        if any(word in title for word in ['breaking', 'news', 'update', 'report']):
            score += 0.1
        
        # Crypto relevance in title
        crypto_words = ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'btc', 'eth']
        crypto_count = sum(1 for word in crypto_words if word in title)
        score += min(0.2, crypto_count * 0.05)
        
        # Recent publication bonus (if available)
        published_time = result.get('published_time', '')
        if published_time:
            try:
                pub_date = datetime.fromisoformat(published_time.replace('Z', '+00:00'))
                age_hours = (datetime.now() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
                if age_hours < 24:
                    score += 0.1  # Bonus for recent articles
            except:
                pass
        
        return min(1.0, score)
    
    def _get_domain_quality(self, domain: str) -> float:
        """Get quality score for a domain"""
        # Check preferred domains
        for preferred_domain, quality_score in self.preferred_domains.items():
            if preferred_domain in domain:
                return quality_score
        
        # Default quality for unknown domains
        return 0.5
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"⏱️ Rate limiting: sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_date_range(self, time_filter: str) -> str:
        """Convert time filter to Google date range format"""
        now = datetime.now()
        
        if time_filter == 'd1':  # Last 24 hours
            start_date = now - timedelta(days=1)
        elif time_filter == 'w1':  # Last week
            start_date = now - timedelta(weeks=1)
        elif time_filter == 'm1':  # Last month
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=1)  # Default to 24 hours
        
        # Format: YYYYMMDD:YYYYMMDD
        return f"{start_date.strftime('%Y%m%d')}:{now.strftime('%Y%m%d')}"
    
    def get_quota_status(self) -> Dict:
        """Get current API quota usage status"""
        return {
            'daily_used': self.daily_quota_used,
            'daily_limit': self.daily_quota_limit,
            'remaining': self.daily_quota_limit - self.daily_quota_used,
            'percentage_used': (self.daily_quota_used / self.daily_quota_limit) * 100
        }
    
    def reset_daily_quota(self):
        """Reset daily quota counter (call this daily)"""
        self.daily_quota_used = 0
        logger.info("🔄 Daily API quota reset")
    
    def get_stats(self) -> Dict:
        """Get search statistics"""
        quota = self.get_quota_status()
        return {
            'total_searches': self.daily_quota_used,
            'cache_hits': 0,  # Not tracked in v1.0
            'cache_hit_rate': 'N/A',
            'cached_queries': len(self.cache),
            'api_cost': f"💰 PAID (${(max(0, self.daily_quota_used - 100) * 0.005):.2f} today)",
            'daily_limit': f"{quota['remaining']}/{quota['daily_limit']} remaining"
        }

# Test function
async def test_google_searcher():
    """Test the Google searcher functionality"""
    print("🧪 Testing Google Searcher (v1.0)...")
    
    try:
        searcher = GoogleSearcher()
    except ValueError as e:
        print(f"❌ {e}")
        print("\n📝 To use Google Search:")
        print("1. Create .env file with:")
        print("   GOOGLE_API_KEY=your_api_key")
        print("   GOOGLE_CSE_ID=your_cse_id")
        print("2. Get API key from: https://console.cloud.google.com/")
        return
    
    # Test single search
    results = await searcher.search("bitcoin news", max_results=5)
    
    print(f"📊 Found {len(results)} results")
    for i, result in enumerate(results[:3], 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Domain Quality: {result['domain_quality']:.2f}")
        print(f"   Relevance: {result.get('relevance_score', 0):.2f}")
    
    # Test quota status
    stats = searcher.get_stats()
    print(f"\n📈 Stats: {stats}")

if __name__ == "__main__":
    import sys
    sys.path.append(str(__file__).replace('google_searcher.py', ''))
    
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_google_searcher())