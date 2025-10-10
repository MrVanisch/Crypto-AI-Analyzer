"""
Smart Notifier for Crypto AI Analyzer
Intelligent notification system for important crypto news alerts with Discord integration
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
import aiohttp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SmartNotifier:
    def __init__(self, discord_webhook_url: Optional[str] = None):
        """Initialize smart notification system
        
        Args:
            discord_webhook_url: Discord webhook URL (or set DISCORD_WEBHOOK_URL env variable)
        """
        
        # Rich console for beautiful output
        self.console = Console()
        
        # Discord webhook configuration
        self.discord_webhook_url = discord_webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        self.discord_enabled = bool(self.discord_webhook_url)
        
        if self.discord_enabled:
            logger.info(f"💬 Discord notifications enabled")
        else:
            logger.info("📴 Discord notifications disabled (no webhook URL)")
        
        # Notification settings - LOW THRESHOLDS
        self.notification_config = {
            'min_importance_score': 0.2,     # Low importance (20%+)
            'min_ai_confidence': 0.2,        # Low AI confidence (20%+)
            'min_source_credibility': 0.3,   # Low source credibility (30%+)
            'min_trend_score': 0.0,          # Minimum trend score
            'rate_limit_minutes': 1,         # Very frequent rate limit
            'max_notifications_per_hour': 20, # Max 20 notifications per hour
            'require_crypto_mention': False,  # Don't require crypto mention
            'consolidate_critical': True      # Consolidate critical alerts
        }
        
        # Alert levels with different formatting
        self.alert_levels = {
            'CRITICAL': {
                'threshold': 0.8,
                'color': 'red',
                'icon': '[!]',
                'priority': 1,
                'style': 'bold red on white',
                'discord_color': 0xFF0000
            },
            'HIGH': {
                'threshold': 0.7,
                'color': 'yellow',
                'icon': '[H]',
                'priority': 2,
                'style': 'bold yellow',
                'discord_color': 0xFFFF00
            },
            'MEDIUM': {
                'threshold': 0.6,
                'color': 'blue',
                'icon': '[M]',
                'priority': 3,
                'style': 'bold blue',
                'discord_color': 0x0099FF
            },
            'LOW': {
                'threshold': 0.4,
                'color': 'green',
                'icon': '[L]',
                'priority': 4,
                'style': 'green',
                'discord_color': 0x00FF00
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
        logger.info(f"🔔 NOTIFIER: Received {len(analysis_results)} results to process")
        
        if not analysis_results:
            logger.info("🔔 NOTIFIER: No results provided, returning")
            return
        
        # Reset hourly counter if needed
        self._reset_hourly_counter()
        
        # Filter and sort results by importance
        logger.info(f"🔔 NOTIFIER: Filtering results with threshold {self.notification_config['min_importance_score']}")
        filtered_results = self._filter_results(analysis_results)
        
        logger.info(f"🔔 NOTIFIER: After filtering: {len(filtered_results)} results remain")
        
        if not filtered_results:
            logger.info("📴 NOTIFIER: No results meet notification criteria - NO ALERTS SENT")
            return
        
        # Sort by importance (most important first)
        filtered_results.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
        
        # Send notifications - NO RATE LIMITING FOR DEBUG
        for result in filtered_results:
            logger.info(f"🔔 SENDING NOTIFICATION: {result.get('keyword', 'unknown')}")
            await self._send_notification(result)
    
    async def send_market_summary(self, summary: Dict, important_results: List[Dict], title: str):
        """Send detailed market summary to Discord - SAME AS CONSOLE OUTPUT"""
        if not self.discord_enabled:
            logger.info("Discord not enabled, skipping market summary")
            return
            
        try:
            # Create Discord embed for detailed market summary
            embed_color = 0xFF0000 if "CRITICAL" in title else 0x0099FF  # Red for critical, blue for news
            
            # Build detailed description like console output
            description_parts = []
            
            # TOP EVENTS with exact formatting from console
            if important_results:
                # Sort by importance (highest first)
                sorted_results = sorted(important_results, key=lambda x: x.get('importance_score', 0), reverse=True)
                
                description_parts.append("**🔥 TOP EVENTS:**")
                for result in sorted_results[:10]:  # Top 10 events
                    keyword = result.get('keyword', 'unknown')
                    importance = result.get('importance_score', 0)
                    # Bold highlighting for high importance
                    if importance >= 0.7:
                        description_parts.append(f"• **{keyword}** - Importance: **{importance*100:.1f}%** 🔥")
                    elif importance >= 0.6:
                        description_parts.append(f"• **{keyword}** - Importance: **{importance*100:.1f}%** ⚡")
                    else:
                        description_parts.append(f"• {keyword} - Importance: **{importance*100:.1f}%**")
                description_parts.append("")

            # CATEGORY BREAKDOWN from summary
            categories = summary.get('category_breakdown', {})
            if categories:
                description_parts.append("**📊 CATEGORY BREAKDOWN:**")
                for category, info in categories.items():
                    count = info.get('count', 0)
                    avg_importance = info.get('average_importance', 0)
                    # Bold for high importance categories
                    if avg_importance >= 0.6:
                        description_parts.append(f"• **{category}**: **{count} articles** (avg: **{avg_importance*100:.1f}%**)")
                    else:
                        description_parts.append(f"• {category}: {count} articles (avg: **{avg_importance*100:.1f}%**)")
                description_parts.append("")

            # CURRENT PRICES - ALWAYS FETCH SOLANA PRICE
            description_parts.append("**💰 CURRENT PRICES:**")
            
            # Try to get price from summary first
            price_added = False
            price_info = summary.get('price_section', {})
            if price_info and 'current_prices' in price_info:
                for crypto_name, price_data in price_info['current_prices'].items():
                    if isinstance(price_data, dict):
                        price = price_data.get('price', 0)
                        change = price_data.get('change_24h', 0)
                        
                        if price > 0:  # Valid price
                            if change >= 0:
                                description_parts.append(f"• **{crypto_name.upper()}**: **${price:.2f}** (**+{change:.2f}%**) 🟢")
                            else:
                                description_parts.append(f"• **{crypto_name.upper()}**: **${price:.2f}** (**{change:.2f}%**) 🔴")
                            price_added = True
                    else:
                        if price_data > 0:  # Valid price
                            description_parts.append(f"• **{crypto_name.upper()}**: **${price_data:.2f}**")
                            price_added = True
            
            # If no price from summary, fetch SOL price directly
            if not price_added:
                try:
                    # Direct CoinGecko API call for reliability
                    async with aiohttp.ClientSession() as session:
                        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd&include_24hr_change=true"
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                if 'solana' in data:
                                    price = data['solana'].get('usd', 0)
                                    change = data['solana'].get('usd_24h_change', 0)
                                    
                                    if price > 0:  # Valid price
                                        if change >= 0:
                                            description_parts.append(f"• **SOL**: **${price:.2f}** (**+{change:.2f}%**) 🟢")
                                        else:
                                            description_parts.append(f"• **SOL**: **${price:.2f}** (**{change:.2f}%**) 🔴")
                                        price_added = True
                    
                    # Fallback if direct API call failed
                    if not price_added:
                        description_parts.append(f"• **SOL**: Price temporarily unavailable")

                except Exception as e:
                    description_parts.append(f"• **SOL**: Error fetching price")
                    logger.warning(f"Failed to fetch SOL price for Discord: {e}")

            description_parts.append("")

            # MARKET STATUS from summary
            if price_info and 'market_status' in price_info:
                market_status = price_info['market_status']
                # Bold and emphasize market status
                if 'spadkowy' in market_status or 'RED' in market_status or '🔴' in market_status or 'down' in market_status.lower():
                    clean_status = market_status.replace('🔴', '🔴 **RED:**').replace('🟢', '🟢 **GREEN:**').replace('📈', '').replace('📉', '**📉**').replace('spadkowy', 'downtrend').replace('Rynek w trendzie spadkowym', 'Market in downtrend').strip()
                    description_parts.append(f"**📈 MARKET STATUS:** **{clean_status}**")
                elif 'wzrostowy' in market_status or 'GREEN' in market_status or '🟢' in market_status or 'up' in market_status.lower():
                    clean_status = market_status.replace('🔴', '🔴 **RED:**').replace('🟢', '🟢 **GREEN:**').replace('📈', '**📈**').replace('📉', '').replace('wzrostowy', 'uptrend').replace('Rynek w trendzie wzrostowym', 'Market in uptrend').strip()
                    description_parts.append(f"**📈 MARKET STATUS:** **{clean_status}**")
                else:
                    clean_status = market_status.replace('🔴', 'RED:').replace('🟢', 'GREEN:').replace('📈', '').replace('📉', '').strip()
                    description_parts.append(f"**📈 MARKET STATUS:** **{clean_status}**")
                description_parts.append("")

            # DETAILED STATISTICS from summary
            stats = summary.get('statistics', {})
            if stats:
                description_parts.append("**📋 STATISTICS:**")
                if 'analyzed_articles' in stats:
                    description_parts.append(f"• Analyzed articles: **{stats['analyzed_articles']}**")
                if 'important_articles' in stats:
                    description_parts.append(f"• Important articles: **{stats['important_articles']}**")
                if 'confidence_level' in stats:
                    confidence = stats['confidence_level']
                    if confidence >= 0.8:
                        description_parts.append(f"• Confidence level: **{confidence:.1%}** 🎯")
                    else:
                        description_parts.append(f"• Confidence level: **{confidence:.1%}**")
                if 'filter_efficiency' in stats:
                    description_parts.append(f"• Filter efficiency: **{stats['filter_efficiency']}**")
            
            # Join description with proper formatting
            description = "\n".join(description_parts)
            
            # Discord has a 2048 character limit for description
            if len(description) > 2048:
                description = description[:2045] + "..."
            
            # Create embed with detailed info
            embed = {
                "title": title.replace('🔥', '[CRITICAL]').replace('📊', '[NEWS]'),
                "description": description,
                "color": embed_color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": f"Crypto AI Analyzer • {len(important_results)} important articles • Today at {datetime.now().strftime('%H:%M')}"
                }
            }

            # Add additional fields if needed (for very detailed breakdown)
            fields = []

            # Add top sources if available
            all_sources = set()
            for result in important_results:
                top_sources = result.get('top_sources', [])
                all_sources.update(top_sources[:3])  # Top 3 from each

            if all_sources:
                sources_text = ", ".join(list(all_sources)[:8])  # Max 8 sources
                if len(sources_text) > 1024:
                    sources_text = sources_text[:1020] + "..."
                fields.append({
                    "name": "Top Sources",
                    "value": sources_text,
                    "inline": False
                })

            # Add alert levels breakdown
            alert_levels = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
            for result in important_results:
                importance = result.get('importance_score', 0)
                if importance >= 0.8:
                    alert_levels['CRITICAL'] += 1
                elif importance >= 0.7:
                    alert_levels['HIGH'] += 1
                elif importance >= 0.6:
                    alert_levels['MEDIUM'] += 1
                else:
                    alert_levels['LOW'] += 1

            levels_text = []
            for level, count in alert_levels.items():
                if count > 0:
                    levels_text.append(f"{level}: {count}")

            if levels_text:
                fields.append({
                    "name": "Alert Levels",
                    "value": " | ".join(levels_text),
                    "inline": False
                })
            
            if fields:
                embed["fields"] = fields
            
            payload = {
                "username": "Crypto Market Bot",
                "embeds": [embed]
            }
            
            # Send to Discord
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.discord_webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 204:
                        logger.info(f"💬 Detailed market summary sent to Discord successfully!")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Discord market summary error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"❌ Error sending detailed market summary to Discord: {e}")
    
    def _filter_results(self, results: List[Dict]) -> List[Dict]:
        """Filter results that meet notification criteria"""
        filtered = []
        threshold = self.notification_config['min_importance_score']
        
        logger.info(f"🔍 FILTER: Processing {len(results)} results with threshold {threshold}")
        
        for i, result in enumerate(results):
            importance = result.get('importance_score', 0)  # Fixed key name!
            keyword = result.get('keyword', 'unknown')
            
            logger.info(f"🔍 FILTER {i}: '{keyword}' importance={importance:.3f}")
            
            # SIMPLIFIED FILTERS - just check importance
            if importance >= threshold:
                filtered.append(result)
                logger.info(f"✅ FILTER: '{keyword}' PASSED ({importance:.3f} >= {threshold})")
            else:
                logger.info(f"❌ FILTER: '{keyword}' BLOCKED ({importance:.3f} < {threshold})")
                
        logger.info(f"🔍 FILTER: Result = {len(filtered)}/{len(results)} passed")
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
            alert_level = self._get_alert_level(result.get('importance_score', 0))
            alert_config = self.alert_levels[alert_level]
            
            # Display console alert
            self._display_console_alert(result, alert_level, alert_config)
            
            # Send Discord notification if enabled
            if self.discord_enabled:
                await self._send_discord_notification(result, alert_level, alert_config)
            
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
        importance = result.get('importance_score', 0)
        confidence = result.get('confidence', 0)
        explanation = result.get('explanation', 'No explanation available')
        recommendation = result.get('recommendation', 'No recommendation')
        components = result.get('components', {})
        raw_data = result.get('raw_data', {})
        top_sources = result.get('top_sources', [])
        
        # Create alert header - SIMPLE TEXT ONLY
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        header_text = f"[{alert_level}] CRYPTO ALERT"
        header = Text(header_text, style=alert_config['style'])
        
        # Create main content table
        content_table = Table(show_header=False, box=None, padding=(0, 1))
        content_table.add_column("Label", style="bold cyan", width=18)
        content_table.add_column("Value", style="white")
        
        content_table.add_row("Keyword:", f"[bold]{keyword}[/bold]")
        content_table.add_row("Importance:", f"[{alert_config['color']}]{importance:.3f}[/{alert_config['color']}] ({importance*100:.1f}%)")
        content_table.add_row("Confidence:", f"{confidence:.3f} ({confidence*100:.1f}%)")
        content_table.add_row("Time:", timestamp)
        content_table.add_row("", "")  # Spacer
        
        # Add components breakdown
        content_table.add_row("AI Analysis:", f"{components.get('ai_importance', 0):.3f}")
        content_table.add_row("Search Volume:", f"{components.get('search_volume', 0):.3f}")
        content_table.add_row("Trend Score:", f"{components.get('trend_momentum', 0):.3f}")
        content_table.add_row("Source Quality:", f"{components.get('source_quality', 0):.3f}")
        content_table.add_row("", "")  # Spacer
        
        # Add raw data
        search_vol = raw_data.get('search_volume', 0)
        ai_results = raw_data.get('ai_results_count', 0)
        articles = raw_data.get('articles_count', 0)
        best_ai = raw_data.get('best_ai_score', 0)
        
        content_table.add_row("Search Results:", f"{search_vol:,}")
        content_table.add_row("AI Analyses:", f"{ai_results}")
        content_table.add_row("Articles Found:", f"{articles}")
        content_table.add_row("Best AI Score:", f"{best_ai:.3f}")
        
        # Add top sources
        if top_sources:
            sources_text = ", ".join(top_sources[:3])
            if len(sources_text) > 60:
                sources_text = sources_text[:57] + "..."
            content_table.add_row("Top Sources:", sources_text)
        
        # Create explanation panel
        explanation_panel = Panel(
            explanation,
            title="Analysis Explanation",
            title_align="left",
            border_style=alert_config['color']
        )
        
        # Create recommendation panel
        recommendation_panel = Panel(
            recommendation,
            title="Recommended Action",
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
    
    async def _send_discord_notification(self, result: Dict, alert_level: str, alert_config: Dict):
        """Send notification to Discord webhook"""
        try:
            keyword = result.get('keyword', 'Unknown')
            importance = result.get('importance_score', 0)
            confidence = result.get('confidence', 0)
            explanation = result.get('explanation', 'No explanation available')
            recommendation = result.get('recommendation', 'No recommendation')
            components = result.get('components', {})
            raw_data = result.get('raw_data', {})
            top_sources = result.get('top_sources', [])
            
            # Get Discord color from alert config
            embed_color = alert_config['discord_color']
            
            # Build the embed - SIMPLIFIED WITHOUT EMOJIS
            embed = {
                "title": f"{alert_level} CRYPTO ALERT",
                "description": f"**{keyword}**",
                "color": embed_color,
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [
                    {
                        "name": "Importance Score",
                        "value": f"**{importance:.3f}** ({importance*100:.1f}%)",
                        "inline": True
                    },
                    {
                        "name": "AI Confidence",
                        "value": f"**{confidence:.3f}** ({confidence*100:.1f}%)",
                        "inline": True
                    },
                    {
                        "name": "Alert Time",
                        "value": datetime.now().strftime("%H:%M:%S"),
                        "inline": True
                    },
                    {
                        "name": "\u200b",
                        "value": "**Component Breakdown**",
                        "inline": False
                    },
                    {
                        "name": "AI Analysis",
                        "value": f"`{components.get('ai_importance', 0):.3f}`",
                        "inline": True
                    },
                    {
                        "name": "Search Volume",
                        "value": f"`{components.get('search_volume', 0):.3f}`",
                        "inline": True
                    },
                    {
                        "name": "Trend Score",
                        "value": f"`{components.get('trend_momentum', 0):.3f}`",
                        "inline": True
                    },
                    {
                        "name": "Source Quality",
                        "value": f"`{components.get('source_quality', 0):.3f}`",
                        "inline": True
                    },
                    {
                        "name": "Time Decay",
                        "value": f"`{components.get('time_decay', 0):.3f}`",
                        "inline": True
                    },
                    {
                        "name": "\u200b",
                        "value": "\u200b",
                        "inline": True
                    },
                    {
                        "name": "\u200b",
                        "value": "**Raw Data**",
                        "inline": False
                    },
                    {
                        "name": "Search Results",
                        "value": f"`{raw_data.get('search_volume', 0):,}`",
                        "inline": True
                    },
                    {
                        "name": "AI Analyses",
                        "value": f"`{raw_data.get('ai_results_count', 0)}`",
                        "inline": True
                    },
                    {
                        "name": "Articles",
                        "value": f"`{raw_data.get('articles_count', 0)}`",
                        "inline": True
                    },
                    {
                        "name": "Analysis",
                        "value": explanation[:1024],  # Discord limit
                        "inline": False
                    },
                    {
                        "name": "Recommendation",
                        "value": recommendation[:1024],  # Discord limit
                        "inline": False
                    }
                ]
            }
            
            # Skip crypto mentions and market summary for now - these variables are not defined
            # These would be added if available in the result data
            
            embed["footer"] = {
                "text": "Crypto AI Analyzer • Smart Notifier"
            }
            
            # Add top sources if available
            if top_sources:
                sources_text = " • ".join(top_sources[:5])
                if len(sources_text) > 1024:
                    sources_text = sources_text[:1020] + "..."
                embed["fields"].append({
                    "name": "Top Sources",
                    "value": sources_text,
                    "inline": False
                })
            
            # Prepare the webhook payload
            payload = {
                "username": "Crypto Alert Bot",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/6001/6001368.png",
                "embeds": [embed]
            }
            
            # Send to Discord
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.discord_webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 204:
                        logger.info(f"💬 Discord notification sent successfully for: {keyword}")
                    elif response.status == 429:
                        # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 5))
                        logger.warning(f"⚠️ Discord rate limited. Retry after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        # Retry once
                        async with session.post(self.discord_webhook_url, json=payload) as retry_response:
                            if retry_response.status == 204:
                                logger.info(f"💬 Discord notification sent on retry")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Discord webhook error {response.status}: {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ Network error sending Discord notification: {e}")
        except Exception as e:
            logger.error(f"❌ Error sending Discord notification: {e}")
    
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
                'importance': result.get('importance_score', 0),
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
        """Play notification sound (if available) - DISABLED"""
        # Sound disabled per user request
        pass
    
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
        
        summary_table.add_row("Discord Enabled", "✅ Yes" if self.discord_enabled else "❌ No")
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
    
    def set_discord_webhook(self, webhook_url: str):
        """Update Discord webhook URL"""
        self.discord_webhook_url = webhook_url
        self.discord_enabled = bool(webhook_url)
        if self.discord_enabled:
            logger.info(f"💬 Discord webhook updated and enabled")
        else:
            logger.info(f"📴 Discord notifications disabled")
    
    def disable_discord(self):
        """Disable Discord notifications"""
        self.discord_enabled = False
        logger.info(f"📴 Discord notifications disabled")
    
    def enable_discord(self):
        """Enable Discord notifications (if webhook URL is set)"""
        if self.discord_webhook_url:
            self.discord_enabled = True
            logger.info(f"💬 Discord notifications enabled")
        else:
            logger.warning(f"⚠️ Cannot enable Discord - no webhook URL set")
    
    async def test_discord_webhook(self):
        """Test Discord webhook with a sample message"""
        if not self.discord_enabled:
            logger.warning("⚠️ Discord notifications are disabled")
            self.console.print("[yellow]⚠️ Discord notifications are disabled. Set DISCORD_WEBHOOK_URL first.[/yellow]")
            return False
        
        test_embed = {
            "title": "🧪 Test Alert",
            "description": "This is a test notification from Crypto AI Analyzer",
            "color": 0x00FF00,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "Status",
                    "value": "✅ Webhook is working correctly!",
                    "inline": False
                },
                {
                    "name": "Test Time",
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "inline": False
                }
            ],
            "footer": {
                "text": "Crypto AI Analyzer • Test Message"
            }
        }
        
        payload = {
            "username": "Crypto Alert Bot",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/6001/6001368.png",
            "embeds": [test_embed]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.discord_webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 204:
                        logger.info("✅ Discord webhook test successful!")
                        self.console.print("[green]✅ Discord webhook test successful![/green]")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Discord webhook test failed: {response.status} - {error_text}")
                        self.console.print(f"[red]❌ Discord webhook test failed: {response.status}[/red]")
                        return False
        except Exception as e:
            logger.error(f"❌ Discord webhook test error: {e}")
            self.console.print(f"[red]❌ Discord webhook test error: {e}[/red]")
            return False

# Test function
async def test_notifier():
    """Test the smart notifier"""
    print("🧪 Testing Smart Notifier...")
    
    # You can pass webhook URL directly or set DISCORD_WEBHOOK_URL environment variable
    # Example: notifier = SmartNotifier(discord_webhook_url="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL")
    notifier = SmartNotifier()
    
    # Show current status
    print("\n📊 Current notification settings:")
    notifier.display_notification_summary()
    
    # Test Discord webhook if enabled
    if notifier.discord_enabled:
        print("\n🧪 Testing Discord webhook...")
        await notifier.test_discord_webhook()
    else:
        print("\n⚠️ Discord webhook not configured. Set DISCORD_WEBHOOK_URL environment variable.")
        print("Example: export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN'")
    
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