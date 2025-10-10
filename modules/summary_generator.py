"""
AI Summary Generator
Generates intelligent summaries of cryptocurrency news findings
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
import json
import re

class SummaryGenerator:
    def __init__(self):
        """Initialize AI summary generator"""
        self.summary_templates = {
            'market_alert': {
                'title': '🚨 MARKET ALERT',
                'format': 'critical'
            },
            'price_update': {
                'title': '💰 PRICE UPDATE',
                'format': 'informational'
            },
            'news_digest': {
                'title': '📰 NEWS DIGEST',
                'format': 'digest'
            },
            'trend_analysis': {
                'title': '📈 TREND ANALYSIS',
                'format': 'analytical'
            }
        }

        # Priorities for different information types
        self.content_priorities = {
            'regulation': 0.9,      # Regulations
            'institutional': 0.8,   # Institutional adoption
            'technology': 0.7,      # Technology updates
            'exchange': 0.6,        # Exchange news
            'market': 0.8,          # Market movements
            'security': 0.9         # Security/hacks
        }

        # Keywords for categorization
        self.category_keywords = {
            'regulation': ['sec', 'cftc', 'regulation', 'law', 'legal', 'ban', 'prohibited', 'regula'],
            'institutional': ['etf', 'tesla', 'microstrategy', 'fund', 'bank', 'institution', 'corporate'],
            'technology': ['upgrade', 'fork', 'merge', 'update', 'blockchain', 'protocol', 'aktualizacja'],
            'exchange': ['binance', 'coinbase', 'kraken', 'exchange', 'trading', 'giełda'],
            'market': ['price', 'drop', 'rise', 'rally', 'crash', 'pump', 'dump', 'cena', 'spadek', 'wzrost'],
            'security': ['hack', 'attack', 'security', 'theft', 'exploit', 'atak', 'bezpieczeństwo', 'kradzież']
        }

        logger.info("📝 Summary Generator initialized")

    async def generate_comprehensive_summary(self, analysis_results: List[Dict],
                                           price_data: Dict = None) -> Dict:
        """
        Generate comprehensive summary of all findings

        Args:
            analysis_results: List of AI analysis results
            price_data: Optional cryptocurrency price data

        Returns:
            Dictionary with summary
        """
        try:
            # Filter and sort results by importance
            important_results = [
                r for r in analysis_results
                if r.get('importance', 0) >= 0.5 and 'error' not in r
            ]

            important_results.sort(key=lambda x: x.get('importance', 0), reverse=True)

            if not important_results:
                return self._generate_no_news_summary(price_data)

            # Categorize news
            categorized_news = self._categorize_news(important_results)

            # Generate summary for each category
            category_summaries = {}
            for category, news_items in categorized_news.items():
                if news_items:
                    category_summaries[category] = self._generate_category_summary(category, news_items)

            # Find top news
            top_news = important_results[:3]

            # Generate main summary
            main_summary = self._generate_main_summary(top_news, category_summaries)

            # Add price data if available
            if price_data:
                price_summary = self._generate_price_summary(price_data)
                main_summary['price_section'] = price_summary

            # Add metadata
            main_summary['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'total_articles_analyzed': len(analysis_results),
                'important_articles': len(important_results),
                'categories_found': list(category_summaries.keys()),
                'confidence_score': self._calculate_summary_confidence(important_results)
            }

            # Add statistics for Discord notifier compatibility
            main_summary['statistics'] = {
                'analyzed_articles': len(analysis_results),
                'important_articles': len(important_results),
                'confidence_level': self._calculate_summary_confidence(important_results)
            }

            logger.info(f"📝 Generated comprehensive summary with {len(important_results)} important articles")
            return main_summary

        except Exception as e:
            logger.error(f"❌ Error generating summary: {e}")
            return self._generate_error_summary(str(e))

    def _categorize_news(self, news_items: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize news by type"""
        categories = {cat: [] for cat in self.category_keywords.keys()}
        categories['other'] = []

        for item in news_items:
            # Check title and main themes
            title = item.get('keyword', '').lower()
            themes = item.get('key_themes', [])

            categorized = False

            # Check AI themes
            for theme in themes:
                if theme in categories:
                    categories[theme].append(item)
                    categorized = True
                    break

            # If not categorized, check keywords
            if not categorized:
                for category, keywords in self.category_keywords.items():
                    if any(keyword in title for keyword in keywords):
                        categories[category].append(item)
                        categorized = True
                        break

            # If still not categorized, add to "other"
            if not categorized:
                categories['other'].append(item)

        # Remove empty categories
        return {cat: items for cat, items in categories.items() if items}

    def _generate_category_summary(self, category: str, news_items: List[Dict]) -> Dict:
        """Generate summary for specific category"""
        category_names = {
            'regulation': 'Regulation & Legal',
            'institutional': 'Institutional Adoption',
            'technology': 'Technology & Development',
            'exchange': 'Exchanges & Trading',
            'market': 'Market Movements',
            'security': 'Security',
            'other': 'Other News'
        }

        # Sort by importance
        news_items.sort(key=lambda x: x.get('importance', 0), reverse=True)

        # Select most important
        top_items = news_items[:3]

        # Generate summary
        summary_points = []
        crypto_mentions = set()

        for item in top_items:
            # Add cryptocurrencies to set
            for crypto in item.get('crypto_mentions', []):
                crypto_mentions.add(crypto)

            # Generate summary point
            keyword = item.get('keyword', 'Unknown news')
            importance = item.get('importance', 0)
            explanation = item.get('explanation', 'No explanation')

            # Shorten explanation
            short_explanation = explanation.split('•')[0].strip()

            summary_points.append({
                'title': keyword,
                'importance': importance,
                'explanation': short_explanation,
                'crypto_mentions': item.get('crypto_mentions', [])
            })

        return {
            'category_name': category_names.get(category, category.title()),
            'item_count': len(news_items),
            'priority': self.content_priorities.get(category, 0.5),
            'summary_points': summary_points,
            'affected_cryptos': list(crypto_mentions),
            'average_importance': sum(item.get('importance', 0) for item in news_items) / len(news_items)
        }

    def _generate_main_summary(self, top_news: List[Dict], category_summaries: Dict) -> Dict:
        """Generate main summary"""
        # Sort categories by priority
        sorted_categories = sorted(
            category_summaries.items(),
            key=lambda x: x[1]['priority'],
            reverse=True
        )

        # Generate header
        if not top_news:
            header = "📰 No significant news in this period"
        else:
            top_importance = top_news[0].get('importance', 0)
            if top_importance >= 0.8:
                header = "🚨 CRITICAL CRYPTO MARKET EVENTS"
            elif top_importance >= 0.6:
                header = "📈 IMPORTANT CRYPTO MARKET NEWS"
            else:
                header = "📰 CRYPTO MARKET OVERVIEW"

        # Generate key highlights
        key_highlights = []
        all_cryptos = set()

        for item in top_news:
            keyword = item.get('keyword', '')
            importance = item.get('importance', 0)
            crypto_mentions = item.get('crypto_mentions', [])

            # Add cryptocurrencies
            all_cryptos.update(crypto_mentions)

            # Generate highlight
            crypto_str = f" ({', '.join(crypto_mentions)})" if crypto_mentions else ""
            highlight = f"• {keyword}{crypto_str} - Importance: {importance:.1%}"
            key_highlights.append(highlight)

        # Generate category summary
        category_overview = []
        for category, summary in sorted_categories:
            count = summary['item_count']
            avg_importance = summary['average_importance']
            name = summary['category_name']

            category_overview.append(f"• {name}: {count} articles (avg importance: {avg_importance:.1%})")

        return {
            'header': header,
            'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'summary_type': 'comprehensive',
            'key_highlights': key_highlights,
            'category_overview': category_overview,
            'category_breakdown': {cat: {'count': summary['item_count'], 'average_importance': summary['average_importance']} for cat, summary in sorted_categories},
            'affected_cryptocurrencies': list(all_cryptos),
            'total_news_count': len(top_news),
            'categories': dict(sorted_categories)
        }

    def _generate_price_summary(self, price_data: Dict) -> Dict:
        """Generate price summary"""
        price_highlights = []
        significant_moves = []
        current_prices = {}

        for crypto_name, data in price_data.items():
            if not data:
                continue

            price_usd = data.get('price_usd') or data.get('usd')
            change_24h = data.get('change_24h') or data.get('usd_24h_change')
            symbol = data.get('symbol', crypto_name.upper())

            if price_usd:
                # Store for Discord
                current_prices[crypto_name] = {
                    'price': price_usd,
                    'change_24h': change_24h or 0,
                    'symbol': symbol
                }

                price_str = f"${price_usd:,.2f}" if price_usd >= 1 else f"${price_usd:.6f}"

                if change_24h is not None:
                    change_str = f"{change_24h:+.2f}%"

                    # Significant moves (above 5%)
                    if abs(change_24h) >= 5:
                        direction = "📈 RISE" if change_24h > 0 else "📉 DROP"
                        significant_moves.append(f"{symbol}: {direction} {abs(change_24h):.1f}%")

                    price_highlights.append(f"{symbol}: {price_str} ({change_str})")
                else:
                    price_highlights.append(f"{symbol}: {price_str}")

        return {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'price_highlights': price_highlights,
            'significant_moves': significant_moves,
            'current_prices': current_prices,
            'market_status': self._assess_market_status(price_data)
        }

    def _assess_market_status(self, price_data: Dict) -> str:
        """Assess market status based on price changes"""
        changes = []

        for data in price_data.values():
            if data:
                change = data.get('change_24h') or data.get('usd_24h_change')
                if change is not None:
                    changes.append(change)

        if not changes:
            return "No change data available"

        avg_change = sum(changes) / len(changes)
        positive_count = sum(1 for c in changes if c > 0)
        total_count = len(changes)

        if avg_change > 2 and positive_count / total_count > 0.7:
            return "🟢 Market in uptrend"
        elif avg_change < -2 and positive_count / total_count < 0.3:
            return "🔴 Market in downtrend"
        else:
            return "🟡 Market consolidating"

    def _calculate_summary_confidence(self, results: List[Dict]) -> float:
        """Calculate summary confidence level"""
        if not results:
            return 0.0

        confidences = [r.get('confidence', 0.5) for r in results]
        return sum(confidences) / len(confidences)

    def _generate_no_news_summary(self, price_data: Dict = None) -> Dict:
        """Generate summary when no important news"""
        summary = {
            'header': '📊 QUIET DAY IN CRYPTO MARKET',
            'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'summary_type': 'no_significant_news',
            'key_highlights': ['• No significant news in monitored period'],
            'category_overview': ['• Routine market activity'],
            'affected_cryptocurrencies': [],
            'total_news_count': 0,
            'categories': {}
        }

        if price_data:
            summary['price_section'] = self._generate_price_summary(price_data)

        return summary

    def _generate_error_summary(self, error_msg: str) -> Dict:
        """Generate error summary"""
        return {
            'header': '❌ SUMMARY GENERATION ERROR',
            'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'summary_type': 'error',
            'key_highlights': [f'• Error occurred: {error_msg}'],
            'category_overview': [],
            'affected_cryptocurrencies': [],
            'total_news_count': 0,
            'categories': {},
            'error': error_msg
        }

    def format_summary_for_display(self, summary: Dict) -> str:
        """
        Format summary for console display

        Args:
            summary: Summary dictionary

        Returns:
            Formatted text for display
        """
        lines = []

        # Header
        lines.append("=" * 60)
        lines.append(summary['header'])
        lines.append(f"🕐 {summary['generated_at']}")
        lines.append("=" * 60)
        lines.append("")

        # Key highlights
        if summary.get('key_highlights'):
            lines.append("🔥 TOP EVENTS:")
            for highlight in summary['key_highlights']:
                lines.append(highlight)
            lines.append("")

        # Category overview
        if summary.get('category_overview'):
            lines.append("📊 CATEGORY BREAKDOWN:")
            for category in summary['category_overview']:
                lines.append(category)
            lines.append("")

        # Affected cryptocurrencies
        if summary.get('affected_cryptocurrencies'):
            cryptos = ', '.join(summary['affected_cryptocurrencies'])
            lines.append(f"🪙 AFFECTED CRYPTOCURRENCIES: {cryptos}")
            lines.append("")

        # Price section
        if summary.get('price_section'):
            price_section = summary['price_section']
            lines.append("💰 CURRENT PRICES:")

            for price_line in price_section.get('price_highlights', []):
                lines.append(f"• {price_line}")

            if price_section.get('significant_moves'):
                lines.append("")
                lines.append("⚡ SIGNIFICANT MOVES:")
                for move in price_section['significant_moves']:
                    lines.append(f"• {move}")

            lines.append("")
            lines.append(f"📈 MARKET STATUS: {price_section.get('market_status', 'Unknown')}")
            lines.append("")

        # Metadata
        if summary.get('metadata'):
            meta = summary['metadata']
            lines.append("📋 STATISTICS:")
            lines.append(f"• Analyzed articles: {meta.get('total_articles_analyzed', 0)}")
            lines.append(f"• Important articles: {meta.get('important_articles', 0)}")
            lines.append(f"• Confidence level: {meta.get('confidence_score', 0):.1%}")

        # Get statistics from summary
        stats = summary.get('statistics', {})
        if stats:
            lines.append("📋 STATISTICS:")
            if 'analyzed_articles' in stats:
                lines.append(f"• Analyzed articles: {stats['analyzed_articles']}")
            if 'important_articles' in stats:
                lines.append(f"• Important articles: {stats['important_articles']}")
            if 'confidence_level' in stats:
                lines.append(f"• Confidence level: {stats['confidence_level']:.1%}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

# Test function
async def test_summary_generator():
    """Test summary generator"""
    print("📝 Testing Summary Generator...")

    generator = SummaryGenerator()

    # Test data
    sample_results = [
        {
            'keyword': 'SEC Bitcoin ETF approval',
            'importance': 0.95,
            'confidence': 0.8,
            'crypto_mentions': ['bitcoin'],
            'key_themes': ['regulation'],
            'explanation': '🔥 CRITICAL: High importance content • Strong market impact potential'
        },
        {
            'keyword': 'Ethereum network upgrade',
            'importance': 0.7,
            'confidence': 0.9,
            'crypto_mentions': ['ethereum'],
            'key_themes': ['technology'],
            'explanation': '📈 HIGH: Significant market relevance • Contains new information'
        }
    ]

    sample_prices = {
        'bitcoin': {
            'price_usd': 45000,
            'change_24h': 5.2,
            'symbol': 'BTC'
        },
        'ethereum': {
            'price_usd': 3200,
            'change_24h': -2.1,
            'symbol': 'ETH'
        }
    }

    # Generate summary
    summary = await generator.generate_comprehensive_summary(sample_results, sample_prices)

    # Display formatted summary
    formatted = generator.format_summary_for_display(summary)
    print(formatted)

if __name__ == "__main__":
    asyncio.run(test_summary_generator())
