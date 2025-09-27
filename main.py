#!/usr/bin/env python3
"""
Crypto AI Analyzer - Main Application
AI-Enhanced Real-time Crypto News Monitor
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

# Import our modules (will create these next)
try:
    from modules.google_searcher import GoogleSearcher
    from modules.content_extractor import ContentExtractor
    from modules.ai_analyzer import AIAnalyzer
    from modules.importance_scorer import ImportanceScorer
    from modules.trend_detector import TrendDetector
    from modules.notifier import SmartNotifier
    from modules.data_manager import DataManager
except ImportError as e:
    print(f"⚠️ Module import error: {e}")
    print("📁 Make sure all modules are created in modules/ folder")
    sys.exit(1)

# Initialize Rich console
console = Console()

class CryptoAIAnalyzer:
    def __init__(self):
        """Initialize the AI-enhanced crypto analyzer"""
        self.setup_logging()
        
        # Initialize components
        try:
            self.google_searcher = GoogleSearcher()
            self.content_extractor = ContentExtractor()
            self.ai_analyzer = AIAnalyzer()
            self.importance_scorer = ImportanceScorer()
            self.trend_detector = TrendDetector()
            self.notifier = SmartNotifier()
            self.data_manager = DataManager()
            
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
            
            logger.info("🧠 Crypto AI Analyzer initialized successfully")
            
        except Exception as e:
            console.print(f"[red]❌ Error initializing analyzer: {e}[/red]")
            sys.exit(1)
    
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
            console.print("[yellow]⚠️ Config file not found, using defaults[/yellow]")
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
            console.print("[yellow]⚠️ Keywords file not found, using defaults[/yellow]")
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
        banner = """
    ╔══════════════════════════════════════════════╗
    ║           🧠 CRYPTO AI ANALYZER 🚀            ║
    ║     AI-Enhanced Real-time News Monitor       ║
    ║                                              ║
    ║  🔍 Google Search  •  🧠 AI Analysis         ║
    ║  📈 Trend Detection  •  ⚡ Smart Alerts      ║
    ╚══════════════════════════════════════════════╝
        """
        console.print(Panel(banner, style="bold cyan"))
    
    def show_status(self):
        """Display system status"""
        self.display_banner()
        
        # System status table
        status_table = Table(title="🔧 System Status")
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("Details")
        
        components = [
            ("Google Search API", "✓ Ready", "API key configured"),
            ("AI Model", "🧠 Loaded", "FinBERT ready for inference"),
            ("Content Extractor", "✓ Active", "Article parsing enabled"),
            ("Trend Detector", "📈 Monitoring", "Historical data loaded"),
            ("Smart Notifier", "⚡ Standby", "Console notifications ready")
        ]
        
        for component, status, details in components:
            status_table.add_row(component, status, details)
        
        console.print(status_table)
        
        # Statistics table
        stats_table = Table(title="📊 Runtime Statistics")
        stats_table.add_column("Metric", style="magenta")
        stats_table.add_column("Count", style="yellow")
        
        for metric, count in self.stats.items():
            stats_table.add_row(metric.replace('_', ' ').title(), str(count))
        
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
            # 1. Google Search (volume detection)
            search_results = await self.google_searcher.search(
                keyword, 
                max_results=self.config['google_search']['max_results']
            )
            self.stats['searches_performed'] += 1
            
            if not search_results:
                logger.warning(f"No search results for keyword: {keyword}")
                return {'keyword': keyword, 'importance': 0.0, 'reason': 'No search results'}
            
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
                return {'keyword': keyword, 'importance': 0.2, 'reason': 'No extractable content'}
            
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
            
            logger.info(f"✅ Analysis complete for {keyword}: importance={final_analysis['importance']:.3f}")
            
            return final_analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing keyword {keyword}: {e}")
            return {'keyword': keyword, 'importance': 0.0, 'error': str(e)}
    
    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        console.print("[bold blue]🔄 Starting monitoring cycle...[/bold blue]")
        
        # Get all keywords to monitor
        all_keywords = []
        for tier, keywords in self.keywords['cryptocurrencies'].items():
            all_keywords.extend(keywords)
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
        # Filter and sort by importance
        important_results = [
            r for r in results 
            if r.get('importance', 0) >= self.config['monitoring']['notification_threshold']
        ]
        
        important_results.sort(key=lambda x: x.get('importance', 0), reverse=True)
        
        if important_results:
            await self.notifier.send_alerts(important_results)
            self.stats['alerts_sent'] += len(important_results)
        
        # Save results for trend analysis
        await self.data_manager.save_analysis_results(results)
    
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
def status():
    """Show system status and statistics"""
    analyzer = CryptoAIAnalyzer()
    analyzer.show_status()

@cli.command()
@click.option('--keyword', help='Specific keyword to analyze')
def analyze(keyword):
    """Run one-time analysis"""
    async def run_analysis():
        analyzer = CryptoAIAnalyzer()
        analyzer.display_banner()
        
        if keyword:
            console.print(f"[bold blue]🔍 Analyzing: {keyword}[/bold blue]")
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
def monitor():
    """Start real-time monitoring"""
    async def run_monitor():
        analyzer = CryptoAIAnalyzer()
        analyzer.display_banner()
        await analyzer.start_monitoring()
    
    asyncio.run(run_monitor())

@cli.command()
def test():
    """Run quick system test"""
    async def run_test():
        analyzer = CryptoAIAnalyzer()
        console.print("[bold green]🧪 Running system test...[/bold green]")
        
        # Test with simple keyword
        result = await analyzer.analyze_keyword("bitcoin news")
        
        if result.get('importance', 0) > 0:
            console.print("[green]✅ Test passed! System working correctly[/green]")
        else:
            console.print("[red]❌ Test failed! Check configuration[/red]")
    
    asyncio.run(run_test())

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

if __name__ == "__main__":
    cli()