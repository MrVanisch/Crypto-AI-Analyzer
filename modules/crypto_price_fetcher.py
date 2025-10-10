"""
Crypto Price Fetcher
Fetches current cryptocurrency prices from various sources
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
import json

class CryptoPriceFetcher:
    def __init__(self):
        """Initialize price fetcher with multiple data sources"""
        self.apis = {
            'coingecko': {
                'base_url': 'https://api.coingecko.com/api/v3',
                'rate_limit': 1,  # requests per second
                'active': True
            },
            'coinbase': {
                'base_url': 'https://api.coinbase.com/v2',
                'rate_limit': 10,
                'active': True
            },
            'binance': {
                'base_url': 'https://api.binance.com/api/v3',
                'rate_limit': 10,
                'active': True
            }
        }
        
        # Cryptocurrency mapping - SOLANA FOCUSED
        self.crypto_mapping = {
            'solana': {'coingecko': 'solana', 'symbol': 'SOL'},
            # Keep others for reference but focus on Solana
            'bitcoin': {'coingecko': 'bitcoin', 'symbol': 'BTC'},
            'ethereum': {'coingecko': 'ethereum', 'symbol': 'ETH'},
            'cardano': {'coingecko': 'cardano', 'symbol': 'ADA'},
            'polygon': {'coingecko': 'matic-network', 'symbol': 'MATIC'},
            'dogecoin': {'coingecko': 'dogecoin', 'symbol': 'DOGE'},
            'shiba': {'coingecko': 'shiba-inu', 'symbol': 'SHIB'}
        }
        
        self.session = None
        logger.info("💰 Crypto Price Fetcher initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_crypto_price(self, crypto_name: str) -> Optional[Dict]:
        """
        Get price of a single cryptocurrency

        Args:
            crypto_name: Cryptocurrency name (e.g. 'bitcoin', 'ethereum')

        Returns:
            Dictionary with price data or None if error
        """
        crypto_name = crypto_name.lower()
        
        if crypto_name not in self.crypto_mapping:
            logger.warning(f"⚠️ Unknown cryptocurrency: {crypto_name}")
            return None
        
        try:
            # Try CoinGecko as primary source
            price_data = await self._fetch_from_coingecko(crypto_name)
            if price_data:
                return price_data
            
            # Fallback to Coinbase
            price_data = await self._fetch_from_coinbase(crypto_name)
            if price_data:
                return price_data
            
            logger.warning(f"⚠️ Could not fetch price for {crypto_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching price for {crypto_name}: {e}")
            return None
    
    async def get_multiple_prices(self, crypto_list: List[str]) -> Dict[str, Dict]:
        """
        Get prices of multiple cryptocurrencies at once

        Args:
            crypto_list: List of cryptocurrency names

        Returns:
            Dictionary with prices {crypto_name: price_data}
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        tasks = []
        for crypto in crypto_list:
            task = self.get_crypto_price(crypto)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        price_data = {}
        for crypto, result in zip(crypto_list, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Error fetching {crypto}: {result}")
                continue
            if result:
                price_data[crypto] = result
        
        return price_data
    
    async def _fetch_from_coingecko(self, crypto_name: str) -> Optional[Dict]:
        """Fetch price from CoinGecko API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            coingecko_id = self.crypto_mapping[crypto_name]['coingecko']
            symbol = self.crypto_mapping[crypto_name]['symbol']
            
            url = f"{self.apis['coingecko']['base_url']}/simple/price"
            params = {
                'ids': coingecko_id,
                'vs_currencies': 'usd,eur',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true',
                'include_market_cap': 'true'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if coingecko_id in data:
                        coin_data = data[coingecko_id]
                        
                        return {
                            'name': crypto_name,
                            'symbol': symbol,
                            'price_usd': coin_data.get('usd'),
                            'price_eur': coin_data.get('eur'),
                            'change_24h': coin_data.get('usd_24h_change'),
                            'volume_24h': coin_data.get('usd_24h_vol'),
                            'market_cap': coin_data.get('usd_market_cap'),
                            'source': 'coingecko',
                            'timestamp': datetime.now().isoformat(),
                            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                else:
                    logger.warning(f"⚠️ CoinGecko API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ CoinGecko fetch error: {e}")
        
        return None
    
    async def _fetch_from_coinbase(self, crypto_name: str) -> Optional[Dict]:
        """Fetch price from Coinbase API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            symbol = self.crypto_mapping[crypto_name]['symbol']
            
            # Coinbase endpoint
            url = f"{self.apis['coinbase']['base_url']}/exchange-rates"
            params = {'currency': symbol}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'data' in data and 'rates' in data['data']:
                        rates = data['data']['rates']
                        
                        return {
                            'name': crypto_name,
                            'symbol': symbol,
                            'price_usd': float(rates.get('USD', 0)),
                            'price_eur': float(rates.get('EUR', 0)),
                            'change_24h': None,  # Coinbase doesn't provide this in this endpoint
                            'volume_24h': None,
                            'market_cap': None,
                            'source': 'coinbase',
                            'timestamp': datetime.now().isoformat(),
                            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                else:
                    logger.warning(f"⚠️ Coinbase API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ Coinbase fetch error: {e}")
        
        return None
    
    def format_price_display(self, price_data: Dict) -> str:
        """
        Format price data for display

        Args:
            price_data: Price data from get_crypto_price

        Returns:
            Formatted string with price
        """
        if not price_data:
            return "Price unavailable"

        name = price_data['name'].title()
        symbol = price_data['symbol']
        price_usd = price_data.get('price_usd')
        change_24h = price_data.get('change_24h')

        if not price_usd:
            return f"{name} ({symbol}): Price unavailable"

        # Format price
        if price_usd >= 1:
            price_str = f"${price_usd:,.2f}"
        else:
            price_str = f"${price_usd:.6f}"
        
        # Add 24h change if available
        change_str = ""
        if change_24h is not None:
            change_icon = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
            change_str = f" {change_icon} {change_24h:+.2f}%"
        
        return f"{name} ({symbol}): {price_str}{change_str}"
    
    async def get_market_summary(self, crypto_list: List[str]) -> str:
        """
        Generate market summary for list of cryptocurrencies

        Args:
            crypto_list: List of cryptocurrency names

        Returns:
            Formatted market summary
        """
        prices = await self.get_multiple_prices(crypto_list)

        if not prices:
            return "❌ Failed to fetch price data"

        summary_lines = ["💰 **CURRENT CRYPTOCURRENCY PRICES**", ""]
        
        for crypto_name, price_data in prices.items():
            if price_data:
                price_line = self.format_price_display(price_data)
                summary_lines.append(f"• {price_line}")
        
        summary_lines.append("")
        summary_lines.append(f"🕐 Last updated: {datetime.now().strftime('%H:%M:%S')}")
        
        return "\n".join(summary_lines)

# Test function
async def test_price_fetcher():
    """Test crypto price fetcher"""
    print("💰 Testing Crypto Price Fetcher...")

    async with CryptoPriceFetcher() as fetcher:
        # Test single cryptocurrency
        print("\n📊 Testing single crypto...")
        btc_price = await fetcher.get_crypto_price('bitcoin')
        if btc_price:
            print(f"✅ Bitcoin: {fetcher.format_price_display(btc_price)}")

        # Test multiple cryptocurrencies
        print("\n📊 Testing multiple cryptos...")
        crypto_list = ['bitcoin', 'ethereum', 'cardano']
        prices = await fetcher.get_multiple_prices(crypto_list)

        for crypto, data in prices.items():
            if data:
                print(f"✅ {fetcher.format_price_display(data)}")

        # Test market summary
        print("\n📊 Testing market summary...")
        summary = await fetcher.get_market_summary(crypto_list)
        print(summary)

if __name__ == "__main__":
    asyncio.run(test_price_fetcher())