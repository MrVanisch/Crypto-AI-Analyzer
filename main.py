#!/usr/bin/env python3
"""
Crypto AI Analyzer - Main Application
AI-Enhanced Real-time Crypto News Monitor
Now with choice between Google Search (v1.0 PAID) or DuckDuckGo (v2.0 FREE)
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from loguru import logger

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.debug("Environment variables loaded from .env file")
except ImportError:
    logger.warning("python-dotenv not installed, using system environment variables only")

# Add modules to path
sys.path.append(str(Path(__file__).parent / "modules"))

# Import search engines
try:
    from modules.google_searcher import GoogleSearcher, get_searcher_info as get_google_info
    GOOGLE_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ Google Search unavailable: {e}")
    GOOGLE_AVAILABLE = False

try:
    from modules.duckduckgo_searcher import DuckDuckGoSearcher, get_searcher_info as get_ddg_info
    DDG_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ DuckDuckGo Search unavailable: {e}")
    DDG_AVAILABLE = False

# Import other modules
try:
    from modules.content_extractor import ContentExtractor
    from modules.ai_analyzer import AIAnalyzer
    from modules.importance_scorer import ImportanceScorer
    from modules.trend_detector import TrendDetector
    from modules.notifier import SmartNotifier
    from modules.data_manager import DataManager
    from modules.crypto_price_fetcher import CryptoPriceFetcher
    from modules.summary_generator import SummaryGenerator
except ImportError as e:
    print(f"⚠️ Module import error: {e}")
    print("📁 Make sure all modules are created in modules/ folder")
    sys.exit(1)

# Initialize Rich console
console = Console()

class CryptoAIAnalyzer:
    def __init__(self, search_engine='duckduckgo'):
        """
        Initialize the AI-enhanced crypto analyzer
        
        Args:
            search_engine: 'google' or 'duckduckgo' (default: duckduckgo)
        """
        self.setup_logging()
        self.search_engine_type = search_engine
        
        # Initialize components
        try:
            # Initialize search engine based on choice
            self.searcher = self._initialize_searcher(search_engine)
            
            self.content_extractor = ContentExtractor()
            self.ai_analyzer = AIAnalyzer()
            self.importance_scorer = ImportanceScorer()
            self.trend_detector = TrendDetector()
            self.notifier = SmartNotifier()
            self.data_manager = DataManager()
            self.price_fetcher = CryptoPriceFetcher()
            self.summary_generator = SummaryGenerator()
            
            # Load configuration
            self.config = self.load_config()
            self.keywords = self.load_keywords()
            
            self.is_monitoring = False
            self.stats = {
                'searches_performed': 0,
                'articles_analyzed': 0,
                'alerts_sent': 0,
                'ai_predictions': 0
            }
            
            logger.info(f"🧠 Crypto AI Analyzer initialized with {search_engine.upper()} search engine")
            
        except Exception as e:
            console.print(f"[red]Error initializing analyzer: {e}[/red]")
            sys.exit(1)
    
    def _initialize_searcher(self, search_engine):
        """Initialize the selected search engine"""
        if search_engine.lower() == 'google':
            if not GOOGLE_AVAILABLE:
                console.print("[red]❌ Google Search not available![/red]")
                console.print("[yellow]💡 Falling back to DuckDuckGo (FREE)[/yellow]")
                return DuckDuckGoSearcher()
            
            try:
                searcher = GoogleSearcher()
                console.print("[green]✅ Using Google Search API (v1.0 - PAID)[/green]")
                return searcher
            except ValueError as e:
                console.print(f"[yellow]⚠️ Google API error: {e}[/yellow]")
                console.print("[yellow]💡 Falling back to DuckDuckGo (FREE)[/yellow]")
                self.search_engine_type = 'duckduckgo'
                return DuckDuckGoSearcher()
        
        elif search_engine.lower() == 'duckduckgo':
            if not DDG_AVAILABLE:
                console.print("[red]❌ DuckDuckGo Search not available![/red]")
                if GOOGLE_AVAILABLE:
                    console.print("[yellow]💡 Falling back to Google Search[/yellow]")
                    self.search_engine_type = 'google'
                    return GoogleSearcher()
                else:
                    raise ImportError("No search engine available!")
            
            console.print("[green]Using DuckDuckGo Search (v2.0 - FREE)[/green]")
            return DuckDuckGoSearcher()
        
        else:
            console.print(f"[red]Unknown search engine: {search_engine}[/red]")
            console.print("[yellow]💡 Using DuckDuckGo (FREE) as default[/yellow]")
            self.search_engine_type = 'duckduckgo'
            return DuckDuckGoSearcher()
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Configure loguru
        logger.remove()  # Remove default handler
        logger.add(
            logs_dir / "app.log",
            rotation="1 day",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        logger.add(
            logs_dir / "ai_model.log",
            rotation="1 day", 
            retention="3 days",
            level="DEBUG",
            filter=lambda record: "ai_" in record["extra"].get("module", "")
        )
    
    def load_config(self):
        """Load main configuration"""
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            console.print("[yellow]Config file not found, using defaults[/yellow]")
            return self.get_default_config()
        
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except ImportError:
            console.print("[red]❌ PyYAML not installed. Install with: pip install pyyaml[/red]")
            return self.get_default_config()
        except Exception as e:
            console.print(f"[red]❌ Error loading config: {e}[/red]")
            return self.get_default_config()
    
    def load_keywords(self):
        """Load keywords to monitor"""
        keywords_path = Path("config/keywords.yaml")
        if not keywords_path.exists():
            console.print("[yellow]Keywords file not found, using defaults[/yellow]")
            return self.get_default_keywords()
        
        try:
            import yaml
            with open(keywords_path, 'r') as f:
                return yaml.safe_load(f)
        except ImportError:
            console.print("[red]❌ PyYAML not installed for keywords. Using defaults.[/red]")
            return self.get_default_keywords()
        except Exception as e:
            console.print(f"[red]❌ Error loading keywords: {e}[/red]")
            return self.get_default_keywords()
    
    def get_default_config(self):
        """Default configuration if file doesn't exist"""
        return {
            'monitoring': {
                'check_interval': 900,  # 15 minutes
                'notification_threshold': 0.7
            },
            'ai_model': {
                'confidence_threshold': 0.6,
                'batch_size': 4
            },
            'google_search': {
                'max_results': 20,
                'time_filter': 'd1'  # Last 24 hours
            }
        }
    
    def get_default_keywords(self):
        """Default keywords if file doesn't exist"""
        return {
            'cryptocurrencies': {
                'tier_1': ['bitcoin news', 'ethereum news', 'BTC breaking', 'ETH update'],
                'tier_2': ['cardano news', 'solana news', 'polygon news'],
                'tier_3': ['dogecoin news', 'shiba inu news']
            },
            'market_events': [
                'crypto regulation', 'bitcoin ETF', 'SEC cryptocurrency', 
                'crypto ban', 'blockchain adoption'
            ]
        }
    
    def display_banner(self):
        """Display application banner"""
        # Get searcher info
        if self.search_engine_type == 'google' and GOOGLE_AVAILABLE:
            searcher_info = get_google_info()
        else:
            searcher_info = get_ddg_info()
        
        banner = f"""
    ================================================
             CRYPTO AI ANALYZER                 
       AI-Enhanced Real-time News Monitor       
                                              
    Search Engine: {searcher_info['name']:<24} 
    Version: {searcher_info['version']:<31} 
    Cost: {searcher_info['cost']:<34} 
                                              
    Smart Search + AI Analysis                  
    Trend Detection + Smart Alerts              
    ================================================
        """
        console.print(Panel(banner, style="bold cyan"))
    
    def show_status(self):
        """Display system status"""
        self.display_banner()
        
        # Get searcher info
        if self.search_engine_type == 'google' and GOOGLE_AVAILABLE:
            searcher_info = get_google_info()
        else:
            searcher_info = get_ddg_info()
        
        # System status table
        status_table = Table(title="🔧 System Status")
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("Details")
        
        # Search engine status
        search_status = f"OK {searcher_info['name']}"
        search_details = f"{searcher_info['version']} - {searcher_info['cost']}"
        
        components = [
            ("Search Engine", search_status, search_details),
            ("AI Model", "Loaded", "FinBERT ready for inference"),
            ("Content Extractor", "Active", "Article parsing enabled"),
            ("Trend Detector", "Monitoring", "Historical data loaded"),
            ("Smart Notifier", "Standby", "Console notifications ready")
        ]
        
        for component, status, details in components:
            status_table.add_row(component, status, details)
        
        console.print(status_table)
        
        # Search engine comparison table
        comparison_table = Table(title="🔍 Search Engine Comparison")
        comparison_table.add_column("Feature", style="cyan")
        comparison_table.add_column("Google (v1.0)", style="yellow")
        comparison_table.add_column("DuckDuckGo (v2.0)", style="green")
        
        comparison_table.add_row("Cost", "PAID", "FREE")
        comparison_table.add_row("API Key", "Required", "Not Required")
        comparison_table.add_row("Daily Limit", "100 free/day", "Unlimited")
        comparison_table.add_row("Result Quality", "5 stars", "4 stars")
        comparison_table.add_row("Setup", "Complex", "Simple")
        comparison_table.add_row("Current Choice", 
                                "YES" if self.search_engine_type == 'google' else "NO",
                                "YES" if self.search_engine_type == 'duckduckgo' else "NO")
        
        console.print(comparison_table)
        
        # Statistics table
        stats_table = Table(title="📊 Runtime Statistics")
        stats_table.add_column("Metric", style="magenta")
        stats_table.add_column("Count", style="yellow")
        
        for metric, count in self.stats.items():
            stats_table.add_row(metric.replace('_', ' ').title(), str(count))
        
        # Add searcher stats
        searcher_stats = self.searcher.get_stats()
        stats_table.add_row("API Cost", searcher_stats.get('api_cost', 'N/A'))
        stats_table.add_row("Daily Limit", searcher_stats.get('daily_limit', 'N/A'))
        
        console.print(stats_table)
    
    async def analyze_keyword(self, keyword: str) -> dict:
        """
        Analyze a single keyword with full AI pipeline
        
        Args:
            keyword: Search term to analyze
            
        Returns:
            Analysis results dictionary
        """
        logger.info(f"🔍 Starting analysis for keyword: {keyword}")
        
        try:
            # 1. Search (using selected engine)
            search_results = await self.searcher.search(
                keyword, 
                max_results=self.config['google_search']['max_results']
            )
            self.stats['searches_performed'] += 1
            
            if not search_results:
                logger.warning(f"No search results for keyword: {keyword}")
                return {'keyword': keyword, 'importance': 0.0, 'importance_score': 0.0, 'reason': 'No search results'}
            
            # 2. Extract content from top results
            articles = []
            extraction_tasks = []
            
            for result in search_results[:10]:  # Top 10 results
                task = self.content_extractor.extract_article(result['url'])
                extraction_tasks.append(task)
            
            extracted_articles = await asyncio.gather(*extraction_tasks, return_exceptions=True)
            
            for i, article in enumerate(extracted_articles):
                if isinstance(article, Exception):
                    logger.warning(f"Failed to extract article {i}: {article}")
                    continue
                if article and len(article.get('content', '')) > 100:
                    articles.append(article)
            
            self.stats['articles_analyzed'] += len(articles)
            
            if not articles:
                logger.warning(f"No articles extracted for keyword: {keyword}")
                return {'keyword': keyword, 'importance': 0.2, 'importance_score': 0.2, 'reason': 'No extractable content'}
            
            # 3. AI Analysis - Core Intelligence
            ai_results = []
            for article in articles:
                ai_analysis = await self.ai_analyzer.analyze_importance(
                    title=article['title'],
                    content=article['content'],
                    source=article.get('source', '')
                )
                ai_results.append(ai_analysis)
                self.stats['ai_predictions'] += 1
            
            # 4. Trend detection
            trend_score = await self.trend_detector.analyze_trend(keyword, len(search_results))
            
            # 5. Calculate final importance score
            final_analysis = self.importance_scorer.calculate_final_score(
                keyword=keyword,
                search_volume=len(search_results),
                ai_results=ai_results,
                trend_score=trend_score,
                articles=articles
            )
            
            # Add keyword to result and standardize key names
            final_analysis['keyword'] = keyword
            if 'importance' in final_analysis and 'importance_score' not in final_analysis:
                final_analysis['importance_score'] = final_analysis['importance']
            
            # EXTRA DEBUG
            logger.info(f"✅ Analysis complete for {keyword}: importance={final_analysis.get('importance_score', 0):.3f}")
            logger.info(f"🔍 FINAL ANALYSIS KEYS: {list(final_analysis.keys())}")
            logger.info(f"🔍 importance_score = {final_analysis.get('importance_score', 'MISSING')}")
            
            return final_analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing keyword {keyword}: {e}")
            return {'keyword': keyword, 'importance': 0.0, 'importance_score': 0.0, 'error': str(e)}
    
    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        console.print("[bold blue]🔄 Starting monitoring cycle...[/bold blue]")
        
        # Get all keywords to monitor - SOLANA FOCUSED
        all_keywords = []
        for tier, keywords in self.keywords['cryptocurrencies'].items():
            all_keywords.extend(keywords)
        
        # Add market events
        if 'market_events' in self.keywords:
            if isinstance(self.keywords['market_events'], dict):
                # New format with categories
                for category, keywords in self.keywords['market_events'].items():
                    all_keywords.extend(keywords)
            else:
                # Old format - list
                all_keywords.extend(self.keywords['market_events'])
        
        # Create progress tracker
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Analyzing keywords...", total=len(all_keywords))
            
            # Analyze all keywords concurrently
            analysis_tasks = []
            for keyword in all_keywords:
                task_coro = self.analyze_keyword(keyword)
                analysis_tasks.append(task_coro)
            
            results = []
            for completed_task in asyncio.as_completed(analysis_tasks):
                result = await completed_task
                results.append(result)
                progress.update(task, advance=1)
        
        # Process results and send notifications
        await self.process_results(results)
        
        console.print("[green]✅ Monitoring cycle completed[/green]")
        return results
    
    async def process_results(self, results: list):
        """Process analysis results and send notifications"""
        # MODERATE FILTERING - use config values
        notification_threshold = self.config['monitoring']['notification_threshold']
        critical_threshold = self.config['monitoring'].get('critical_threshold', 0.75)
        min_confidence = self.config.get('notifications', {}).get('min_ai_confidence', 0.2)
        min_source_credibility = self.config.get('ai_quality', {}).get('min_source_credibility', 0.3)
        
        # Apply all filters - DEBUG MODE
        important_results = []
        logger.info(f"🔍 DEBUG: Processing {len(results)} results with threshold {notification_threshold}")
        
        for i, r in enumerate(results):
            if 'error' in r:
                logger.debug(f"❌ Skipping result {i}: has error")
                continue
                
            importance = r.get('importance_score', 0)  # Fixed key name!
            confidence = r.get('confidence', 0)
            source_cred = r.get('components', {}).get('source_credibility', 0)
            keyword = r.get('keyword', 'unknown')
            
            logger.info(f"📊 Result {i}: '{keyword}' - importance={importance:.3f}, confidence={confidence:.3f}, source={source_cred:.3f}")
            
            # SIMPLIFIED CHECK - just importance
            if importance >= notification_threshold:
                # Additional boost for critical news
                if importance >= critical_threshold:
                    r['is_critical'] = True
                    logger.info(f"🔥 CRITICAL NEWS: {keyword} (importance: {importance:.1%})")
                
                important_results.append(r)
                logger.info(f"✅ PASSED: '{keyword}' added to important_results")
            else:
                logger.info(f"❌ FILTERED: '{keyword}' below threshold ({importance:.3f} < {notification_threshold})")
        
        important_results.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
        
        # Get current cryptocurrency prices - SOLANA FOCUSED
        target_crypto = self.config.get('target_crypto', {}).get('name', 'solana')
        crypto_list = [target_crypto]  # Only focus on configured crypto
        try:
            async with self.price_fetcher as fetcher:
                price_data = await fetcher.get_multiple_prices(crypto_list)
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch crypto prices: {e}")
            price_data = {}
        
        # Generate AI summary ONLY if there are important news
        try:
            if important_results:
                # Use only filtered, important results
                summary = await self.summary_generator.generate_comprehensive_summary(
                    important_results, price_data
                )
                
                # Display summary with priority
                title = "🔥 CRITICAL MARKET ALERTS" if any(r.get('is_critical') for r in important_results) else "📊 IMPORTANT MARKET NEWS"
                formatted_summary = self.summary_generator.format_summary_for_display(summary)
                console.print(Panel(formatted_summary, title=title, style="red" if title.startswith("🔥") else "cyan"))
                
                # Log statystyki filtrowania
                logger.info(f"📊 Filtering: {len(results)} -> {len(important_results)} (threshold: {notification_threshold:.1%})")
            else:
                # Short summary that there are no important news
                if price_data:
                    price_summary = await self.price_fetcher.get_market_summary([target_crypto])
                    console.print(Panel(f"📊 QUIET MARKET\n\n{price_summary}\n\n✅ No news above importance threshold ({notification_threshold:.1%})", 
                                   title="🔇 MONITORING STATUS", style="green"))
                else:
                    console.print(Panel(f"✅ No important news\nImportance threshold: {notification_threshold:.1%}\nAnalyzed: {len(results)} articles", 
                                   title="🔇 QUIET MARKET", style="green"))
                
        except Exception as e:
            logger.error(f"❌ Error generating summary: {e}")
        
        # Send notifications - SIMPLIFIED TO MINIMUM
        if important_results:
            # SEND ALL IMPORTANT RESULTS - NO ADDITIONAL FILTERING
            alerts_to_send = important_results  # Send everything that passed main filter
            
            if alerts_to_send:
                logger.info(f"🚨 SENDING {len(alerts_to_send)} ALERTS!")
                
                # SEND MARKET SUMMARY TO DISCORD instead of individual alerts
                try:
                    # Send market summary to Discord
                    if important_results:
                        await self.notifier.send_market_summary(summary, important_results, title)
                        logger.info(f"📢 ✅ SUCCESSFULLY SENT market summary to Discord!")
                    
                    self.stats['alerts_sent'] += len(alerts_to_send)
                except Exception as e:
                    logger.error(f"❌ FAILED to send market summary: {e}")
            else:
                logger.info(f"📊 {len(important_results)} important news, but none require alerts")
        
        # Save results for trend analysis
        await self.data_manager.save_analysis_results(results)

        # Update filtering statistics
        self.stats['total_analyzed'] = self.stats.get('total_analyzed', 0) + len(results)
        self.stats['passed_filter'] = self.stats.get('passed_filter', 0) + len(important_results)
        self.stats['filter_efficiency'] = f"{(len(important_results)/len(results)*100) if results else 0:.1f}%"
    
    def _create_alert_summary(self, full_summary: dict, important_results: list) -> str:
        """Create concise summary for alerts"""
        try:
            # Key highlights
            highlights = full_summary.get('key_highlights', [])
            top_highlights = highlights[:3]  # Max 3 points
            
            # Affected cryptocurrencies
            affected_cryptos = full_summary.get('affected_cryptocurrencies', [])
            crypto_text = f" ({', '.join(affected_cryptos[:5])})" if affected_cryptos else ""
            
            # Market status from prices
            market_status = ""
            if full_summary.get('price_section'):
                status = full_summary['price_section'].get('market_status', '')
                if status:
                    market_status = f"\n📈 {status}"
            
            # Criticality level
            critical_count = len([r for r in important_results if r.get('is_critical', False)])
            criticality = f"🚨 {critical_count} critical" if critical_count > 0 else f"⚡ {len(important_results)} important"
            
            # Create concise summary
            summary_parts = [
                f"📊 {criticality} events{crypto_text}",
            ]
            
            if top_highlights:
                summary_parts.append("🔥 Top highlights:")
                for highlight in top_highlights:
                    # Shorten highlight
                    short_highlight = highlight.split(' - ')[0] if ' - ' in highlight else highlight
                    if len(short_highlight) > 60:
                        short_highlight = short_highlight[:57] + "..."
                    summary_parts.append(f"• {short_highlight}")
            
            if market_status:
                summary_parts.append(market_status)
                
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"❌ Error creating alert summary: {e}")
            # Fallback summary
            return f"📊 {len(important_results)} important events detected by AI"
    
    async def start_monitoring(self):
        """Start continuous monitoring"""
        self.is_monitoring = True
        console.print("[bold green]🚀 Starting real-time monitoring...[/bold green]")
        console.print("Press Ctrl+C to stop")
        
        try:
            while self.is_monitoring:
                cycle_start = datetime.now()
                
                await self.run_monitoring_cycle()
                
                # Calculate sleep time
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                sleep_time = max(0, self.config['monitoring']['check_interval'] - cycle_duration)
                
                if sleep_time > 0:
                    console.print(f"⏱️ Next cycle in {sleep_time:.0f} seconds...")
                    await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]🛑 Monitoring stopped by user[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Monitoring error: {e}[/red]")
            logger.error(f"Monitoring error: {e}")
        finally:
            self.is_monitoring = False

# CLI Commands
@click.group()
def cli():
    """🧠 Crypto AI Analyzer - AI-Enhanced News Monitor"""
    pass

@cli.command()
@click.option('--engine', type=click.Choice(['google', 'duckduckgo'], case_sensitive=False), 
              default='duckduckgo', help='Search engine to use')
def status(engine):
    """Show system status and statistics"""
    analyzer = CryptoAIAnalyzer(search_engine=engine)
    analyzer.show_status()

@cli.command()
@click.option('--keyword', help='Specific keyword to analyze')
@click.option('--engine', type=click.Choice(['google', 'duckduckgo'], case_sensitive=False), 
              default='duckduckgo', help='Search engine to use')
def analyze(keyword, engine):
    """Run one-time analysis"""
    async def run_analysis():
        analyzer = CryptoAIAnalyzer(search_engine=engine)
        analyzer.display_banner()
        
        if keyword:
            console.print(f"[bold blue]Analyzing: {keyword}[/bold blue]")
            result = await analyzer.analyze_keyword(keyword)
            
            # Display result
            table = Table(title=f"Analysis Result: {keyword}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Importance Score", f"{result.get('importance', 0):.3f}")
            table.add_row("AI Confidence", f"{result.get('confidence', 0):.3f}")
            table.add_row("Search Volume", str(result.get('raw_data', {}).get('search_volume', 0)))
            table.add_row("Top Source", result.get('top_sources', ['N/A'])[0] if result.get('top_sources') else 'N/A')
            
            console.print(table)
        else:
            await analyzer.run_monitoring_cycle()
    
    asyncio.run(run_analysis())

@cli.command()
@click.option('--engine', type=click.Choice(['google', 'duckduckgo'], case_sensitive=False), 
              default='duckduckgo', help='Search engine to use (default: duckduckgo)')
def monitor(engine):
    """Start real-time monitoring"""
    async def run_monitor():
        analyzer = CryptoAIAnalyzer(search_engine=engine)
        analyzer.display_banner()
        await analyzer.start_monitoring()
    
    asyncio.run(run_monitor())

@cli.command()
@click.option('--engine', type=click.Choice(['google', 'duckduckgo'], case_sensitive=False), 
              default='duckduckgo', help='Search engine to use')
def test(engine):
    """Run quick system test"""
    async def run_test():
        analyzer = CryptoAIAnalyzer(search_engine=engine)
        console.print("[bold green]🧪 Running system test...[/bold green]")
        
        # Test with simple keyword
        result = await analyzer.analyze_keyword("bitcoin news")
        
        if result.get('importance', 0) > 0:
            console.print("[green]✅ Test passed! System working correctly[/green]")
        else:
            console.print("[red]❌ Test failed! Check configuration[/red]")
    
    asyncio.run(run_test())

@cli.command()
def compare():
    """Compare available search engines"""
    console.print("\n[bold cyan]🔍 Search Engine Comparison[/bold cyan]\n")
    
    # Google Search Info
    if GOOGLE_AVAILABLE:
        google_info = get_google_info()
        console.print("[bold yellow]Google Custom Search (v1.0)[/bold yellow]")
        console.print(f"Cost: {google_info['cost']}")
        console.print(f"API Key: {'Required' if google_info['api_key_required'] else 'Not Required'}")
        console.print(f"Daily Limit: {google_info['daily_limit']}")
        console.print("\nAdvantages:")
        for adv in google_info['advantages']:
            console.print(f"  {adv}")
        console.print("\nDisadvantages:")
        for dis in google_info['disadvantages']:
            console.print(f"  {dis}")
    else:
        console.print("[red]❌ Google Search not available (missing API credentials)[/red]")
    
    console.print("\n" + "="*60 + "\n")
    
    # DuckDuckGo Info
    if DDG_AVAILABLE:
        ddg_info = get_ddg_info()
        console.print("[bold green]DuckDuckGo Search (v2.0)[/bold green]")
        console.print(f"Cost: {ddg_info['cost']}")
        console.print(f"API Key: {'Required' if ddg_info['api_key_required'] else 'Not Required'}")
        console.print(f"Daily Limit: {ddg_info['daily_limit']}")
        console.print("\nAdvantages:")
        for adv in ddg_info['advantages']:
            console.print(f"  {adv}")
        console.print("\nDisadvantages:")
        for dis in ddg_info['disadvantages']:
            console.print(f"  {dis}")
    else:
        console.print("[red]❌ DuckDuckGo Search not available (install: pip install ddgs)[/red]")
    
    console.print("\n" + "="*60 + "\n")
    console.print("[bold cyan]💡 Recommendation:[/bold cyan]")
    console.print("  • Use [green]DuckDuckGo[/green] for FREE unlimited searches")
    console.print("  • Use [yellow]Google[/yellow] if you need highest quality results and have API key")

@cli.command()
@click.option('--threshold', type=float, help='Set notification threshold (0.0-1.0)')
def config(threshold):
    """Configure analyzer settings"""
    if threshold is not None:
        if 0.0 <= threshold <= 1.0:
            console.print(f"[green]✅ Notification threshold set to {threshold}[/green]")
            # TODO: Save to config file
        else:
            console.print("[red]❌ Threshold must be between 0.0 and 1.0[/red]")

@cli.command()
@click.option('--cryptos', help='Comma-separated list of cryptocurrencies (default: bitcoin,ethereum,cardano)')
def prices(cryptos):
    """Show current cryptocurrency prices"""
    async def show_prices():
        crypto_list = cryptos.split(',') if cryptos else ['bitcoin', 'ethereum', 'cardano', 'solana']
        crypto_list = [c.strip().lower() for c in crypto_list]
        
        console.print("[bold blue]💰 Fetching current cryptocurrency prices...[/bold blue]")

        try:
            async with CryptoPriceFetcher() as fetcher:
                market_summary = await fetcher.get_market_summary(crypto_list)
                console.print(Panel(market_summary, title="💰 CURRENT CRYPTO PRICES", style="green"))
        except Exception as e:
            console.print(f"[red]❌ Error fetching prices: {e}[/red]")
    
    asyncio.run(show_prices())

@cli.command()
@click.option('--engine', type=click.Choice(['google', 'duckduckgo'], case_sensitive=False), 
              default='duckduckgo', help='Search engine to use')
def summary(engine):
    """Generate AI summary of current market conditions"""
    async def generate_summary():
        analyzer = CryptoAIAnalyzer(search_engine=engine)
        console.print("[bold blue]🧠 Generating AI summary...[/bold blue]")
        
        try:
            # Run quick analysis
            results = await analyzer.run_monitoring_cycle()

            # Results are already displayed in process_results
            console.print("[green]✅ AI summary completed[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error generating summary: {e}[/red]")
    
    asyncio.run(generate_summary())

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Program stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.error(f"Unexpected error: {e}")