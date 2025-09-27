"""
Smart Notifier for Crypto AI Analyzer
Intelligent notification system for important crypto news alerts
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import hashlib
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from loguru import logger
import time

class SmartNotifier:
    def __init__(self):
        """Initialize smart notification system"""
        
        # Rich console for beautiful output
        self.console = Console()
        
        # Notification settings
        self.notification_config = {
            'min_importance_score': 0.6,     # Minimum importance to notify
            'min_ai_confidence': 0.5,        # Minimum AI confidence
            'min_trend_score': 0.0,          # Minimum trend score (0 = always notify if other criteria met)
            'rate_limit_minutes': 5,         # Don't spam same keyword
            'max_notifications_per_hour': 20 # Global rate limit
        }
        
        # Alert levels with different formatting
        self.alert_levels = {
            'CRITICAL': {
                'threshold': 0.8,
                'color': 'red',
                'icon': '🚨',
                'priority': 1,
                'style': 'bold red on white'
            },
            'HIGH': {
                'threshold': 0.7,
                'color': 'yellow',
                'icon': '⚡',
                'priority': 2,
                'style': 'bold yellow'
            },
            'MEDIUM': {
                'threshold': 0.6,
                'color': 'blue',
                'icon': '📈',
                'priority': 3,
                'style': 'bold blue'
            },
            'LOW': {
                'threshold': 0.4,
                'color': 'green',
                'icon': '📊',
                'priority': 4,
                'style': 'green'
            }
        }
        
        # Notification history for rate limiting
        self.notification_history = {}
        self.hourly_count = 0
        self.last_hour_reset = datetime.now()
        
        # Alert log
        self.alerts_log_path = Path("data/alerts")
        self.alerts_log_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("🔔 Smart Notifier initialized")
    
    async def send_alerts(self, analysis_results: List[Dict]):
        """
        Send smart alerts for important analysis results
        
        Args:
            analysis_results: List of final analysis results from importance_scorer
        """
        if not analysis_results:
            return
        
        # Reset hourly counter if needed
        self._reset_hourly_counter()
        
        # Filter and sort results by importance
        filtered_results = self._filter_results(analysis_results)
        
        if not filtered_results:
            logger.debug("📴 No results meet notification criteria")
            return
        
        # Sort by importance (most important first)
        filtered_results.sort(key=lambda x: x.get('importance', 0), reverse=True)
        
        # Send notifications
        for result in filtered_results:
            if self._should_notify(result):
                await self._send_notification(result)
                self._update_rate_limiting(result)
    
    def _filter_results(self, results: List[Dict]) -> List[Dict]:
        """Filter results that meet notification criteria"""
        filtered = []
        
        for result in results:
            importance = result.get('importance', 0)
            confidence = result.get('confidence', 0)
            components = result.get('components', {})
            trend_score = components.get('trend_momentum', 0)
            
            # Check minimum thresholds
            if (importance >= self.notification_config['min_importance_score'] and
                confidence >= self.notification_config['min_ai_confidence'] and
                trend_score >= self.notification_config['min_trend_score']):
                filtered.append(result)
                
        return filtered
    
    def _should_notify(self, result: Dict) -> bool:
        """Check if we should send notification for this result"""
        keyword = result.get('keyword', '')
        
        # Check global rate limit
        if self.hourly_count >= self.notification_config['max_notifications_per_hour']:
            logger.warning(f"⚠️ Hourly notification limit reached ({self.hourly_count})")
            return False
        
        # Check keyword-specific rate limiting
        now = datetime.now()
        rate_limit_key = hashlib.md5(keyword.encode()).hexdigest()
        
        if rate_limit_key in self.notification_history:
            last_notification = self.notification_history[rate_limit_key]
            time_diff = (now - last_notification).total_seconds() / 60  # minutes
            
            if time_diff < self.notification_config['rate_limit_minutes']:
                logger.debug(f"🔇 Rate limiting notification for: {keyword}")
                return False
        
        return True
    
    async def _send_notification(self, result: Dict):
        """Send a single notification"""
        try:
            # Determine alert level
            alert_level = self._get_alert_level(result.get('importance', 0))
            alert_config = self.alert_levels[alert_level]
            
            # Create notification
            self._display_console_alert(result, alert_level, alert_config)
            
            # Log alert
            await self._log_alert(result, alert_level)
            
            # Play sound effect (if available)
            self._play_notification_sound(alert_level)
            
            logger.info(f"🔔 {alert_level} alert sent for: {result.get('keyword', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Error sending notification: {e}")
    
    def _display_console_alert(self, result: Dict, alert_level: str, alert_config: Dict):
        """Display rich console alert"""
        keyword = result.get('keyword', 'Unknown')
        importance = result.get('importance', 0)
        confidence = result.get('confidence', 0)
        explanation = result.get('explanation', 'No explanation available')
        recommendation = result.get('recommendation', 'No recommendation')
        components = result.get('components', {})
        raw_data = result.get('raw_data', {})
        top_sources = result.get('top_sources', [])
        
        # Create alert header
        icon = alert_config['icon']
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        header_text = f"{icon} {alert_level} CRYPTO ALERT {icon}"
        header = Text(header_text, style=alert_config['style'])
        
        # Create main content table
        content_table = Table(show_header=False, box=None, padding=(0, 1))
        content_table.add_column("Label", style="bold cyan", width=18)
        content_table.add_column("Value", style="white")
        
        content_table.add_row("🎯 Keyword:", f"[bold]{keyword}[/bold]")
        content_table.add_row("📊 Importance:", f"[{alert_config['color']}]{importance:.3f}[/{alert_config['color']}] ({importance*100:.1f}%)")
        content_table.add_row("🎯 Confidence:", f"{confidence:.3f} ({confidence*100:.1f}%)")
        content_table.add_row("⏰ Time:", timestamp)
        content_table.add_row("", "")  # Spacer
        
        # Add components breakdown
        content_table.add_row("🧠 AI Analysis:", f"{components.get('ai_importance', 0):.3f}")
        content_table.add_row("🔍 Search Volume:", f"{components.get('search_volume', 0):.3f}")
        content_table.add_row("📈 Trend Score:", f"{components.get('trend_momentum', 0):.3f}")
        content_table.add_row("🏆 Source Quality:", f"{components.get('source_quality', 0):.3f}")
        content_table.add_row("", "")  # Spacer
        
        # Add raw data
        search_vol = raw_data.get('search_volume', 0)
        ai_results = raw_data.get('ai_results_count', 0)
        articles = raw_data.get('articles_count', 0)
        best_ai = raw_data.get('best_ai_score', 0)
        
        content_table.add_row("📡 Search Results:", f"{search_vol:,}")
        content_table.add_row("🧠 AI Analyses:", f"{ai_results}")
        content_table.add_row("📰 Articles Found:", f"{articles}")
        content_table.add_row("🎯 Best AI Score:", f"{best_ai:.3f}")
        
        # Add top sources
        if top_sources:
            sources_text = ", ".join(top_sources[:3])
            if len(sources_text) > 60:
                sources_text = sources_text[:57] + "..."
            content_table.add_row("🌐 Top Sources:", sources_text)
        
        # Create explanation panel
        explanation_panel = Panel(
            explanation,
            title="💡 Analysis Explanation",
            title_align="left",
            border_style=alert_config['color']
        )
        
        # Create recommendation panel
        recommendation_panel = Panel(
            recommendation,
            title="📋 Recommended Action",
            title_align="left",
            border_style=alert_config['color']
        )
        
        # Create main alert panel
        main_panel = Panel(
            content_table,
            title=header,
            title_align="center",
            border_style=alert_config['color'],
            padding=(1, 2)
        )
        
        # Display the alert
        self.console.print()  # Blank line
        self.console.print("=" * 80, style=alert_config['color'])
        self.console.print(main_panel)
        self.console.print(explanation_panel)
        self.console.print(recommendation_panel)
        self.console.print("=" * 80, style=alert_config['color'])
        self.console.print()  # Blank line
    
    def _get_alert_level(self, importance_score: float) -> str:
        """Determine alert level based on importance score"""
        if importance_score >= self.alert_levels['CRITICAL']['threshold']:
            return 'CRITICAL'
        elif importance_score >= self.alert_levels['HIGH']['threshold']:
            return 'HIGH'
        elif importance_score >= self.alert_levels['MEDIUM']['threshold']:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    async def _log_alert(self, result: Dict, alert_level: str):
        """Log alert to file for history"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'alert_level': alert_level,
                'keyword': result.get('keyword', ''),
                'importance': result.get('importance', 0),
                'confidence': result.get('confidence', 0),
                'components': result.get('components', {}),
                'raw_data': result.get('raw_data', {}),
                'explanation': result.get('explanation', ''),
                'recommendation': result.get('recommendation', ''),
                'top_sources': result.get('top_sources', [])
            }
            
            # Save to daily log file
            log_file = self.alerts_log_path / f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
            
            # Read existing log or create new
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                log_data = {'alerts': []}
            
            # Add new entry
            log_data['alerts'].append(log_entry)
            
            # Write back to file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"📝 Alert logged to: {log_file}")
            
        except Exception as e:
            logger.error(f"❌ Error logging alert: {e}")
    
    def _play_notification_sound(self, alert_level: str):
        """Play notification sound (if available)"""
        try:
            # Different sounds for different alert levels
            if alert_level == 'CRITICAL':
                # Could play urgent sound
                print("\a\a\a")  # System beep (3x for critical)
            elif alert_level == 'HIGH':
                print("\a\a")  # System beep (2x for high)
            elif alert_level == 'MEDIUM':
                print("\a")  # System beep (1x for medium)
            # No sound for LOW
            
        except Exception as e:
            logger.debug(f"⚠️ Could not play notification sound: {e}")
    
    def _update_rate_limiting(self, result: Dict):
        """Update rate limiting counters"""
        keyword = result.get('keyword', '')
        now = datetime.now()
        
        # Update keyword-specific rate limiting
        rate_limit_key = hashlib.md5(keyword.encode()).hexdigest()
        self.notification_history[rate_limit_key] = now
        
        # Update hourly counter
        self.hourly_count += 1
        
        logger.debug(f"📊 Notification sent. Hourly count: {self.hourly_count}")
    
    def _reset_hourly_counter(self):
        """Reset hourly notification counter if needed"""
        now = datetime.now()
        if (now - self.last_hour_reset).total_seconds() >= 3600:  # 1 hour
            self.hourly_count = 0
            self.last_hour_reset = now
            logger.debug("🔄 Hourly notification counter reset")
    
    def display_notification_summary(self):
        """Display current notification status"""
        self._reset_hourly_counter()
        
        summary_table = Table(title="🔔 Notification System Status")
        summary_table.add_column("Setting", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Min Importance Score", f"{self.notification_config['min_importance_score']:.2f}")
        summary_table.add_row("Min AI Confidence", f"{self.notification_config['min_ai_confidence']:.2f}")
        summary_table.add_row("Rate Limit (minutes)", str(self.notification_config['rate_limit_minutes']))
        summary_table.add_row("Max Notifications/Hour", str(self.notification_config['max_notifications_per_hour']))
        summary_table.add_row("Current Hour Count", f"{self.hourly_count}/{self.notification_config['max_notifications_per_hour']}")
        summary_table.add_row("Recent Keywords", str(len(self.notification_history)))
        
        self.console.print(summary_table)
    
    def get_alert_history(self, days_back: int = 7) -> List[Dict]:
        """Get alert history for the last N days"""
        alerts = []
        
        for i in range(days_back):
            date = datetime.now() - timedelta(days=i)
            log_file = self.alerts_log_path / f"alerts_{date.strftime('%Y%m%d')}.json"
            
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                        alerts.extend(log_data.get('alerts', []))
                except Exception as e:
                    logger.warning(f"⚠️ Error reading alert log {log_file}: {e}")
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return alerts
    
    def display_alert_history(self, limit: int = 10):
        """Display recent alert history"""
        alerts = self.get_alert_history()
        
        if not alerts:
            self.console.print("[yellow]📭 No recent alerts found[/yellow]")
            return
        
        history_table = Table(title=f"📊 Recent Alerts (Last {min(limit, len(alerts))})")
        history_table.add_column("Time", style="cyan")
        history_table.add_column("Level", style="bold")
        history_table.add_column("Keyword", style="green")
        history_table.add_column("Score", style="yellow")
        history_table.add_column("Action", style="blue")
        
        for alert in alerts[:limit]:
            timestamp = datetime.fromisoformat(alert['timestamp']).strftime("%m/%d %H:%M")
            level = alert['alert_level']
            keyword = alert['keyword']
            importance = alert['importance']
            action = alert['recommendation'].split(' - ')[0] if ' - ' in alert['recommendation'] else alert['recommendation']
            
            # Color code the level
            level_style = self.alert_levels.get(level, {}).get('color', 'white')
            level_text = f"[{level_style}]{level}[/{level_style}]"
            
            history_table.add_row(
                timestamp,
                level_text,
                keyword[:30] + "..." if len(keyword) > 30 else keyword,
                f"{importance:.3f}",
                action[:25] + "..." if len(action) > 25 else action
            )
        
        self.console.print(history_table)
    
    def update_notification_config(self, **kwargs):
        """Update notification configuration"""
        for key, value in kwargs.items():
            if key in self.notification_config:
                old_value = self.notification_config[key]
                self.notification_config[key] = value
                logger.info(f"⚙️ Updated {key}: {old_value} → {value}")
            else:
                logger.warning(f"⚠️ Unknown config key: {key}")

# Test function
async def test_notifier():
    """Test the smart notifier"""
    print("🧪 Testing Smart Notifier...")
    
    notifier = SmartNotifier()
    
    # Show current status
    print("\n📊 Current notification settings:")
    notifier.display_notification_summary()
    
    # Test notifications with different importance levels
    test_results = [
        {
            'keyword': 'bitcoin etf sec approval',
            'importance': 0.89,
            'confidence': 0.92,
            'components': {
                'ai_importance': 0.91,
                'search_volume': 0.95,
                'trend_momentum': 0.85,
                'source_quality': 0.90,
                'time_decay': 0.88
            },
            'raw_data': {
                'search_volume': 15000,
                'ai_results_count': 5,
                'articles_count': 12,
                'best_ai_score': 0.91,
                'avg_ai_confidence': 0.89
            },
            'explanation': '🔥 CRITICAL IMPORTANCE • AI models indicate high significance • High search volume detected • Strong trending momentum • Premium sources reporting',
            'recommendation': '🚨 IMMEDIATE ATTENTION REQUIRED - Major regulatory development',
            'top_sources': ['reuters.com', 'coindesk.com', 'bloomberg.com']
        },
        {
            'keyword': 'ethereum price analysis',
            'importance': 0.35,
            'confidence': 0.67,
            'components': {
                'ai_importance': 0.42,
                'search_volume': 0.30,
                'trend_momentum': 0.25,
                'source_quality': 0.45,
                'time_decay': 0.60
            },
            'raw_data': {
                'search_volume': 245,
                'ai_results_count': 2,
                'articles_count': 4,
                'best_ai_score': 0.42,
                'avg_ai_confidence': 0.67
            },
            'explanation': '📉 LOW IMPORTANCE • Limited market impact • Routine analysis content',
            'recommendation': '📝 BACKGROUND INFO - No action needed',
            'top_sources': ['cryptoblog.com', 'tradingview.com']
        },
        {
            'keyword': 'major exchange hack breaking',
            'importance': 0.94,
            'confidence': 0.96,
            'components': {
                'ai_importance': 0.95,
                'search_volume': 0.88,
                'trend_momentum': 0.92,
                'source_quality': 0.85,
                'time_decay': 0.98
            },
            'raw_data': {
                'search_volume': 8500,
                'ai_results_count': 8,
                'articles_count': 15,
                'best_ai_score': 0.95,
                'avg_ai_confidence': 0.96
            },
            'explanation': '🚨 CRITICAL IMPORTANCE • Breaking security incident • Strong market impact potential • Urgent reporting from premium sources',
            'recommendation': '🚨 IMMEDIATE ATTENTION REQUIRED - Security incident affecting market',
            'top_sources': ['coindesk.com', 'theblock.co', 'decrypt.co']
        }
    ]
    
    print(f"\n🔔 Testing notifications with {len(test_results)} results...")
    await notifier.send_alerts(test_results)
    
    print(f"\n📊 Alert history:")
    notifier.display_alert_history()

if __name__ == "__main__":
    asyncio.run(test_notifier())