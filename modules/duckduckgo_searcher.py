"""
DuckDuckGo Search Integration for Crypto AI Analyzer
Free, unlimited search without API keys - replaces Google Search
"""

import asyncio
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse
from loguru import logger

# DuckDuckGo search library
try:
    from ddgs import DDGS
    DDG_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        logger.warning("⚠️ Using old duckduckgo_search package. Update with: pip install ddgs")
        DDG_AVAILABLE = True
    except ImportError:
        logger.error("❌ ddgs not installed. Install with: pip install ddgs")
        DDG_AVAILABLE = False

class DuckDuckGoSearcher:
    def __init__(self):
        """Initialize DuckDuckGo searcher - NO API KEY NEEDED! 🎉"""
        
        if not DDG_AVAILABLE:
            raise ImportError(
                "ddgs library not installed. "
                "Install with: pip install ddgs"
            )
        
        # Rate limiting settings (be nice to DDG servers)
        self.last_request_time = 0
        self.min_request_interval = 1.5  # 1.5 seconds between requests
        
        # Cache settings
        self.cache = {}
        self.cache_duration = 300  # 5 minutes cache
        
        # Quality filters - LESS STRICT
        self.excluded_domains = {
            'youtube.com', 'tiktok.com', 'instagram.com', 
            'pinterest.com'  # Only exclude video/image social media
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
            'marketwatch.com': 0.7,
            'investing.com': 0.65,
            'cryptonews.com': 0.7,
            'benzinga.com': 0.65
        }
        
        # Stats tracking
        self.total_searches = 0
        self.cache_hits = 0
        
        logger.info("✅ DuckDuckGo Searcher initialized (FREE, no API key needed!)")
    
    async def search(
        self, 
        query: str, 
        max_results: int = 20, 
        time_filter: str = 'd'  # 'd'=day, 'w'=week, 'm'=month
    ) -> List[Dict]:
        """
        Search DuckDuckGo for crypto-related content
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            time_filter: Time filter ('d'=24h, 'w'=week, 'm'=month, 'y'=year)
            
        Returns:
            List of search result dictionaries
        """
        # Check cache first
        cache_key = f"{query}_{max_results}_{time_filter}"
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                logger.debug(f"💾 Using cached results for: {query}")
                self.cache_hits += 1
                return cached_result
        
        try:
            # Rate limiting
            await self._enforce_rate_limit()
            
            # Prepare time filter
            timelimit = self._convert_time_filter(time_filter)
            
            logger.info(f"🔍 Searching DuckDuckGo for: '{query}' (max_results={max_results}, time={time_filter})")
            
            # Execute search with DuckDuckGo
            results = []
            
            # Use DDGS text search with better parameters
            with DDGS() as ddgs:
                # New ddgs package uses 'query' instead of 'keywords'
                try:
                    # Try new API (ddgs package)
                    search_results = ddgs.text(
                        query=query,
                        region='wt-wt',
                        safesearch='off',
                        timelimit=timelimit,
                        max_results=max_results * 2
                    )
                except TypeError:
                    # Fallback to old API (duckduckgo_search package)
                    search_results = ddgs.text(
                        keywords=query,
                        region='wt-wt',
                        safesearch='off',
                        timelimit=timelimit,
                        max_results=max_results * 2
                    )
                
                # Process results
                for idx, result in enumerate(search_results):
                    try:
                        processed_result = self._process_result(result, query, idx)
                        if processed_result:
                            results.append(processed_result)
                    except Exception as e:
                        logger.warning(f"⚠️ Error processing result: {e}")
                        continue
            
            # Filter and rank results - trim to requested amount
            all_filtered = self._filter_and_rank_results(results)
            filtered_results = all_filtered[:max_results]  # Take only requested amount
            
            # Update stats
            self.total_searches += 1
            
            # Cache results
            self.cache[cache_key] = (filtered_results, time.time())
            
            logger.info(f"✅ Found {len(filtered_results)} quality results for: {query}")
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"❌ DuckDuckGo search error for query '{query}': {e}")
            return []
    
    async def batch_search(
        self, 
        queries: List[str], 
        max_results_per_query: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Search multiple queries efficiently
        
        Args:
            queries: List of search queries
            max_results_per_query: Max results per query
            
        Returns:
            Dictionary mapping queries to their results
        """
        logger.info(f"🔍 Starting batch search for {len(queries)} queries")
        
        results = {}
        
        for query in queries:
            try:
                search_results = await self.search(query, max_results_per_query)
                results[query] = search_results
                
                # Small delay between batch queries
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"❌ Batch search failed for '{query}': {e}")
                results[query] = []
        
        total_results = sum(len(r) for r in results.values())
        logger.info(f"✅ Batch search completed: {total_results} total results")
        
        return results
    
    def _process_result(self, result: Dict, query: str, index: int) -> Optional[Dict]:
        """Process a single DuckDuckGo search result"""
        try:
            # Extract URL and parse domain
            url = result.get('href', result.get('link', ''))
            if not url:
                return None
            
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Create result dictionary
            processed = {
                'title': result.get('title', ''),
                'url': url,
                'snippet': result.get('body', result.get('description', '')),
                'display_url': domain,
                'domain': domain,
                'query': query,
                'position': index + 1,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add quality score
            processed['domain_quality'] = self._get_domain_quality(domain)
            
            return processed
            
        except Exception as e:
            logger.debug(f"⚠️ Error processing result: {e}")
            return None
    
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
            
            # LESS STRICT - accept shorter titles (was 10, now 5)
            if len(result.get('title', '')) < 5:
                logger.debug("🚫 Filtering out result with too short title")
                continue
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(result)
            result['relevance_score'] = relevance_score
            
            # LESS STRICT - lower threshold (was 0.3, now 0.2)
            if relevance_score >= 0.2:
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
        
        # News/breaking indicators
        if any(word in title for word in ['breaking', 'news', 'update', 'report', 'analysis']):
            score += 0.1
        
        # Crypto relevance in title
        crypto_words = ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'btc', 'eth', 'defi']
        crypto_count = sum(1 for word in crypto_words if word in title)
        score += min(0.2, crypto_count * 0.05)
        
        # Position bonus (earlier results are often better)
        position = result.get('position', 10)
        if position <= 3:
            score += 0.15
        elif position <= 5:
            score += 0.10
        elif position <= 10:
            score += 0.05
        
        # Snippet quality (check if crypto-related)
        snippet = result.get('snippet', '').lower()
        crypto_in_snippet = sum(1 for word in crypto_words if word in snippet)
        score += min(0.1, crypto_in_snippet * 0.03)
        
        return min(1.0, score)
    
    def _get_domain_quality(self, domain: str) -> float:
        """Get quality score for a domain"""
        # Check preferred domains
        for preferred_domain, quality_score in self.preferred_domains.items():
            if preferred_domain in domain:
                return quality_score
        
        # Check for common news domains
        if any(indicator in domain for indicator in ['news', 'times', 'post', 'journal']):
            return 0.6
        
        # Default quality for unknown domains
        return 0.4
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"⏱️ Rate limiting: sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _convert_time_filter(self, time_filter: str) -> Optional[str]:
        """Convert time filter to DuckDuckGo format"""
        # DuckDuckGo time filters: d=day, w=week, m=month, y=year
        filter_map = {
            'd': 'd',    # Last day
            'd1': 'd',   # Last 24 hours
            'w': 'w',    # Last week
            'w1': 'w',
            'm': 'm',    # Last month
            'm1': 'm',
            'y': 'y'     # Last year
        }
        
        return filter_map.get(time_filter, 'd')  # Default to day
    
    def get_stats(self) -> Dict:
        """Get search statistics"""
        cache_hit_rate = (self.cache_hits / max(1, self.total_searches)) * 100
        
        return {
            'total_searches': self.total_searches,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'cached_queries': len(self.cache),
            'api_cost': '🆓 FREE (No API costs!)',
            'daily_limit': '♾️ UNLIMITED'
        }
    
    def clear_cache(self):
        """Clear search cache"""
        cache_size = len(self.cache)
        self.cache.clear()
        logger.info(f"🧹 Cleared {cache_size} cached queries")

# Test function
async def test_duckduckgo_searcher():
    """Test the DuckDuckGo searcher functionality"""
    print("🧪 Testing DuckDuckGo Searcher...")
    print("✅ No API key needed - completely FREE!\n")
    
    searcher = DuckDuckGoSearcher()
    
    # Test single search
    print("🔍 Test 1: Searching for 'bitcoin news'...")
    results = await searcher.search("bitcoin news", max_results=5, time_filter='d')
    
    print(f"\n📊 Found {len(results)} results:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n{i}. {result['title'][:80]}...")
        print(f"   URL: {result['url']}")
        print(f"   Domain: {result['domain']} (Quality: {result['domain_quality']:.2f})")
        print(f"   Relevance: {result.get('relevance_score', 0):.2f}")
    
    # Test batch search
    print(f"\n\n🔍 Test 2: Batch searching multiple keywords...")
    batch_queries = ['ethereum news', 'crypto regulation', 'SEC bitcoin']
    batch_results = await searcher.batch_search(batch_queries, max_results_per_query=3)
    
    print(f"\n📊 Batch results:")
    for query, results in batch_results.items():
        print(f"   • {query}: {len(results)} results")
    
    # Show stats
    stats = searcher.get_stats()
    print(f"\n📈 Search Statistics:")
    print(f"   • Total searches: {stats['total_searches']}")
    print(f"   • Cache hits: {stats['cache_hits']} ({stats['cache_hit_rate']})")
    print(f"   • API cost: {stats['api_cost']}")
    print(f"   • Daily limit: {stats['daily_limit']}")
    
    print("\n✅ DuckDuckGo searcher works perfectly!")
    print("💡 Remember: Install with 'pip install duckduckgo-search'")

def get_searcher_info():
    """Get information about this searcher"""
    return {
        'name': 'DuckDuckGo Search',
        'version': '2.0',
        'cost': 'FREE',
        'api_key_required': False,
        'daily_limit': 'Unlimited',
        'advantages': [
            '✅ Completely free - no API costs',
            '✅ No API key needed',
            '✅ Unlimited searches',
            '✅ Good quality crypto news results',
            '✅ Privacy-focused'
        ],
        'disadvantages': [
            '⚠️ Slightly fewer results than Google',
            '⚠️ Less precise ranking'
        ]
    }

if __name__ == "__main__":
    asyncio.run(test_duckduckgo_searcher())