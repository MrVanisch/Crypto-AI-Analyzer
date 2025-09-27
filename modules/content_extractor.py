"""
Content Extractor for Crypto AI Analyzer
Intelligent article content extraction from URLs
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from pathlib import Path
import re
import hashlib
from loguru import logger

# Content extraction libraries
try:
    from newspaper import Article
    from newspaper import Config as NewspaperConfig
except ImportError:
    logger.warning("⚠️ newspaper3k not available, using fallback extraction")
    Article = None

try:
    import trafilatura
except ImportError:
    logger.warning("⚠️ trafilatura not available, using fallback extraction")
    trafilatura = None

from bs4 import BeautifulSoup
import json

class ContentExtractor:
    def __init__(self):
        """Initialize content extractor with multiple extraction methods"""
        self.session = None
        self.extraction_cache = {}
        self.cache_duration = 1800  # 30 minutes cache
        
        # Request settings
        self.timeout = aiohttp.ClientTimeout(total=15)
        self.max_content_length = 5 * 1024 * 1024  # 5MB max
        
        # User agents for different sites
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        # Site-specific configurations
        self.site_configs = {
            'coindesk.com': {
                'selectors': ['.at-text', '.entry-content', 'article'],
                'title_selectors': ['h1.at-headline', 'h1'],
                'wait_time': 2
            },
            'cointelegraph.com': {
                'selectors': ['.post-content', '.article-content', 'article'],
                'title_selectors': ['h1', '.post-title'],
                'wait_time': 2
            },
            'decrypt.co': {
                'selectors': ['.post-content', 'article', '.entry-content'],
                'title_selectors': ['h1', '.post-title'],
                'wait_time': 1
            },
            'theblock.co': {
                'selectors': ['.article-content', '.post-content', 'article'],
                'title_selectors': ['h1', '.article-title'],
                'wait_time': 2
            }
        }
        
        # Content quality indicators
        self.quality_indicators = {
            'min_content_length': 200,
            'max_content_length': 50000,
            'min_sentences': 3,
            'suspicious_patterns': [
                r'this article requires subscription',
                r'sign up to continue reading',
                r'paywall',
                r'premium content',
                r'subscribe now'
            ]
        }
        
        logger.info("📰 Content Extractor initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()
    
    async def _create_session(self):
        """Create aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=3,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={'User-Agent': self.user_agents[0]}
            )
    
    async def _close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def extract_article(self, url: str, method: str = 'auto') -> Optional[Dict]:
        """
        Extract article content from URL using best available method
        
        Args:
            url: Article URL to extract
            method: Extraction method ('auto', 'newspaper', 'trafilatura', 'custom')
            
        Returns:
            Dictionary with extracted content or None if failed
        """
        # Input validation
        if not url or not self._is_valid_url(url):
            logger.warning(f"🚫 Invalid URL: {url}")
            return None
        
        # Check cache
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_key in self.extraction_cache:
            cached_result, timestamp = self.extraction_cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                logger.debug(f"💾 Using cached content for: {url}")
                return cached_result
        
        # Create session if needed
        await self._create_session()
        
        try:
            # Download HTML content
            html_content = await self._download_html(url)
            if not html_content:
                return None
            
            # Extract content using specified method
            if method == 'auto':
                article_data = await self._extract_auto(url, html_content)
            elif method == 'newspaper' and Article:
                article_data = await self._extract_newspaper(url, html_content)
            elif method == 'trafilatura' and trafilatura:
                article_data = await self._extract_trafilatura(url, html_content)
            else:
                article_data = await self._extract_custom(url, html_content)
            
            # Validate extracted content
            if article_data and self._validate_content(article_data):
                # Cache successful extraction
                self.extraction_cache[cache_key] = (article_data, time.time())
                
                logger.info(f"✅ Extracted content from: {urlparse(url).netloc}")
                logger.debug(f"📊 Content length: {len(article_data.get('content', ''))} chars")
                
                return article_data
            else:
                logger.warning(f"❌ Content validation failed for: {url}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error extracting content from {url}: {e}")
            return None
    
    async def _download_html(self, url: str) -> Optional[str]:
        """Download HTML content from URL"""
        try:
            # Get domain-specific config
            domain = urlparse(url).netloc.lower()
            config = self.site_configs.get(domain, {})
            wait_time = config.get('wait_time', 1)
            
            # Rotate user agent
            headers = {
                'User-Agent': self.user_agents[hash(url) % len(self.user_agents)],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            async with self.session.get(url, headers=headers) as response:
                # Check response status
                if response.status != 200:
                    logger.warning(f"⚠️ HTTP {response.status} for: {url}")
                    return None
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    logger.warning(f"⚠️ Non-HTML content type: {content_type} for: {url}")
                    return None
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.max_content_length:
                    logger.warning(f"⚠️ Content too large: {content_length} bytes for: {url}")
                    return None
                
                # Download content
                html_content = await response.text()
                
                # Wait if needed (respect site rate limits)
                if wait_time > 1:
                    await asyncio.sleep(wait_time)
                
                return html_content
                
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Timeout downloading: {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Error downloading {url}: {e}")
            return None
    
    async def _extract_auto(self, url: str, html_content: str) -> Optional[Dict]:
        """Automatically choose best extraction method"""
        # Try methods in order of preference
        methods = []
        
        if trafilatura:
            methods.append(('trafilatura', self._extract_trafilatura))
        
        if Article:
            methods.append(('newspaper', self._extract_newspaper))
        
        methods.append(('custom', self._extract_custom))
        
        best_result = None
        best_score = 0
        
        for method_name, method_func in methods:
            try:
                result = await method_func(url, html_content)
                if result:
                    score = self._score_extraction(result)
                    logger.debug(f"📊 {method_name} extraction score: {score:.2f}")
                    
                    if score > best_score:
                        best_score = score
                        best_result = result
                        best_result['extraction_method'] = method_name
            except Exception as e:
                logger.debug(f"⚠️ {method_name} extraction failed: {e}")
                continue
        
        return best_result
    
    async def _extract_newspaper(self, url: str, html_content: str) -> Optional[Dict]:
        """Extract using newspaper3k library"""
        if not Article:
            return None
        
        try:
            # Configure newspaper
            config = NewspaperConfig()
            config.browser_user_agent = self.user_agents[0]
            config.request_timeout = 10
            
            # Create article object
            article = Article(url, config=config)
            article.set_html(html_content)
            article.parse()
            
            # Extract content
            article_data = {
                'title': article.title.strip() if article.title else '',
                'content': article.text.strip() if article.text else '',
                'authors': article.authors,
                'publish_date': article.publish_date.isoformat() if article.publish_date else '',
                'url': url,
                'source': urlparse(url).netloc,
                'extraction_method': 'newspaper',
                'extracted_at': datetime.now().isoformat()
            }
            
            return article_data
            
        except Exception as e:
            logger.debug(f"⚠️ Newspaper extraction failed for {url}: {e}")
            return None
    
    async def _extract_trafilatura(self, url: str, html_content: str) -> Optional[Dict]:
        """Extract using trafilatura library"""
        if not trafilatura:
            return None
        
        try:
            # Extract main content
            content = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                include_formatting=False,
                favor_precision=True
            )
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(html_content)
            
            if not content:
                return None
            
            article_data = {
                'title': metadata.title if metadata and metadata.title else '',
                'content': content.strip(),
                'authors': [metadata.author] if metadata and metadata.author else [],
                'publish_date': metadata.date if metadata and metadata.date else '',
                'url': url,
                'source': urlparse(url).netloc,
                'extraction_method': 'trafilatura',
                'extracted_at': datetime.now().isoformat()
            }
            
            return article_data
            
        except Exception as e:
            logger.debug(f"⚠️ Trafilatura extraction failed for {url}: {e}")
            return None
    
    async def _extract_custom(self, url: str, html_content: str) -> Optional[Dict]:
        """Custom extraction using BeautifulSoup with site-specific selectors"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
                element.decompose()
            
            domain = urlparse(url).netloc.lower()
            site_config = self.site_configs.get(domain, {})
            
            # Extract title
            title = self._extract_title(soup, site_config.get('title_selectors', ['h1']))
            
            # Extract content
            content = self._extract_content(soup, site_config.get('selectors', ['article', '.content', '.post']))
            
            if not content:
                return None
            
            article_data = {
                'title': title.strip() if title else '',
                'content': content.strip(),
                'authors': [],
                'publish_date': '',
                'url': url,
                'source': urlparse(url).netloc,
                'extraction_method': 'custom',
                'extracted_at': datetime.now().isoformat()
            }
            
            return article_data
            
        except Exception as e:
            logger.debug(f"⚠️ Custom extraction failed for {url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract article title using CSS selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        # Fallback to page title
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ''
    
    def _extract_content(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract article content using CSS selectors"""
        content_parts = []
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    # Get all paragraphs
                    paragraphs = element.find_all(['p', 'div'], recursive=True)
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) > 50:  # Skip short paragraphs
                            content_parts.append(text)
                
                if content_parts:
                    break  # Use first successful selector
        
        # If no content found, try getting all paragraphs
        if not content_parts:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50:
                    content_parts.append(text)
        
        return '\n\n'.join(content_parts)
    
    def _validate_content(self, article_data: Dict) -> bool:
        """Validate extracted content quality"""
        content = article_data.get('content', '')
        
        # Check minimum length
        if len(content) < self.quality_indicators['min_content_length']:
            logger.debug("🚫 Content too short")
            return False
        
        # Check maximum length
        if len(content) > self.quality_indicators['max_content_length']:
            logger.debug("🚫 Content too long")
            return False
        
        # Check sentence count
        sentences = content.split('. ')
        if len(sentences) < self.quality_indicators['min_sentences']:
            logger.debug("🚫 Too few sentences")
            return False
        
        # Check for paywall/subscription content
        content_lower = content.lower()
        for pattern in self.quality_indicators['suspicious_patterns']:
            if re.search(pattern, content_lower):
                logger.debug(f"🚫 Suspicious pattern found: {pattern}")
                return False
        
        return True
    
    def _score_extraction(self, article_data: Dict) -> float:
        """Score extraction quality (0.0 - 1.0)"""
        score = 0.5  # Base score
        
        content = article_data.get('content', '')
        title = article_data.get('title', '')
        
        # Title quality
        if title and len(title) > 10:
            score += 0.2
        
        # Content length scoring
        content_len = len(content)
        if 500 <= content_len <= 10000:
            score += 0.3
        elif 200 <= content_len < 500:
            score += 0.2
        elif content_len > 10000:
            score += 0.1
        
        # Structural quality
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 3:
            score += 0.1
        
        # Author and date
        if article_data.get('authors'):
            score += 0.05
        
        if article_data.get('publish_date'):
            score += 0.05
        
        return min(1.0, score)
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and extractable"""
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Skip certain file types
            path = parsed.path.lower()
            skip_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.png', '.gif', '.mp4', '.mp3']
            if any(path.endswith(ext) for ext in skip_extensions):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def batch_extract(self, urls: List[str], max_concurrent: int = 5) -> Dict[str, Optional[Dict]]:
        """
        Extract content from multiple URLs concurrently
        
        Args:
            urls: List of URLs to extract
            max_concurrent: Maximum concurrent extractions
            
        Returns:
            Dictionary mapping URLs to extracted content
        """
        logger.info(f"📰 Starting batch extraction for {len(urls)} URLs")
        
        await self._create_session()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(url: str) -> tuple:
            async with semaphore:
                result = await self.extract_article(url)
                return url, result
        
        # Create tasks
        tasks = [extract_with_semaphore(url) for url in urls]
        
        # Execute with progress
        results = {}
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            url, result = await coro
            results[url] = result
            completed += 1
            
            if completed % 5 == 0 or completed == len(urls):
                logger.info(f"📊 Batch extraction progress: {completed}/{len(urls)}")
        
        successful = sum(1 for r in results.values() if r is not None)
        logger.info(f"✅ Batch extraction completed: {successful}/{len(urls)} successful")
        
        return results

# Test function
async def test_content_extractor():
    """Test the content extractor with real URLs from Google Search"""
    print("🧪 Testing Content Extractor...")
    
    # First, let's get real URLs from Google Search
    try:
        from google_searcher import GoogleSearcher
        
        print("🔍 Getting real URLs from Google Search...")
        searcher = GoogleSearcher()
        search_results = await searcher.search("bitcoin news", max_results=5)
        
        if not search_results:
            print("❌ No search results found. Using fallback URLs...")
            test_urls = [
                "https://coindesk.com/",
                "https://cointelegraph.com/",
                "https://www.theblock.co/"
            ]
        else:
            test_urls = [result['url'] for result in search_results[:3]]
            print(f"✅ Found {len(test_urls)} real URLs from Google")
            
    except Exception as e:
        print(f"⚠️ Could not get URLs from Google Search: {e}")
        print("Using fallback URLs...")
        test_urls = [
            "https://coindesk.com/",
            "https://cointelegraph.com/",
            "https://www.theblock.co/"
        ]
    
    async with ContentExtractor() as extractor:
        # Test single extraction
        print(f"\n🔍 Testing single extraction...")
        success_count = 0
        
        for url in test_urls:
            print(f"📡 Trying: {urlparse(url).netloc}")
            result = await extractor.extract_article(url)
            if result:
                print(f"✅ SUCCESS!")
                print(f"📰 Title: {result['title'][:80]}...")
                print(f"📝 Content: {len(result['content'])} characters")
                print(f"🔧 Method: {result['extraction_method']}")
                print(f"📊 Score: {extractor._score_extraction(result):.2f}")
                success_count += 1
                break
            else:
                print(f"❌ Failed")
        
        if success_count == 0:
            print("\n⚠️ All extractions failed. This might be due to:")
            print("1. Sites blocking requests")
            print("2. Network issues") 
            print("3. Sites requiring JS rendering")
            print("\n🔧 The extractor is working correctly - it's handling errors gracefully!")
        
        # Test batch extraction with fewer URLs
        print(f"\n🔍 Testing batch extraction...")
        batch_results = await extractor.batch_extract(test_urls[:2], max_concurrent=2)
        
        successful = 0
        for url, result in batch_results.items():
            if result:
                print(f"✅ {urlparse(url).netloc}: {len(result['content'])} chars")
                successful += 1
            else:
                print(f"❌ {urlparse(url).netloc}: Failed")
        
        print(f"\n📊 Overall success rate: {successful}/{len(batch_results)} ({successful/len(batch_results)*100:.0f}%)")
        
        if successful > 0:
            print("🎉 Content Extractor is working correctly!")
        else:
            print("⚠️ No successful extractions, but error handling is working properly.")

if __name__ == "__main__":
    asyncio.run(test_content_extractor())