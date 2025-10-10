# 🧠 Crypto AI Analyzer

**AI-Enhanced Real-time Cryptocurrency News Monitor**

An intelligent cryptocurrency monitoring system that uses advanced AI analysis to track, analyze, and alert on important crypto market developments. Specifically optimized for Solana (SOL) ecosystem monitoring with comprehensive Discord notifications.

## ✨ Features

### 🔍 **Smart Search & Analysis**
- **Dual Search Engines**: DuckDuckGo (FREE) or Google Custom Search API (PAID)
- **AI-Powered Analysis**: FinBERT model for financial sentiment analysis
- **Real-time Monitoring**: Continuous monitoring with configurable intervals
- **Importance Scoring**: Advanced multi-factor scoring algorithm

### 🎯 **Solana-Focused Monitoring**
- **Ecosystem Coverage**: Solana news, partnerships, DeFi, NFTs, validators
- **Price Integration**: Real-time SOL price tracking with multiple API fallbacks
- **Network Events**: Outage detection, upgrades, consensus issues
- **DeFi Tracking**: Raydium, Orca, Serum DEX, Phantom wallet

### 🚨 **Smart Notifications**
- **Console Alerts**: Beautiful Rich console interface with color-coded alerts
- **Discord Integration**: Detailed market summaries with formatted embeds
- **Priority Levels**: CRITICAL, HIGH, MEDIUM, LOW with visual indicators
- **Rate Limiting**: Intelligent filtering to prevent notification spam

### 📊 **Comprehensive Analysis**
- **Multi-Factor Scoring**: AI importance + search volume + trend momentum + source quality
- **Source Quality Rating**: Tier-based credibility system (Reuters, Bloomberg, CoinDesk, etc.)
- **Market Summaries**: AI-generated comprehensive market overviews
- **Historical Tracking**: Trend detection and alert logging

## 🚀 Quick Start

### Step-by-Step Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/crypto-ai-analyzer.git
cd crypto-ai-analyzer
```

#### 2. Install Python Dependencies
```bash
# Install all required packages
pip install -r requirements.txt
```

**Required Dependencies:**
- `transformers` - FinBERT AI model for sentiment analysis
- `torch` - PyTorch deep learning framework
- `aiohttp` - Async HTTP client for fast API requests
- `rich` - Beautiful terminal formatting
- `click` - Command-line interface framework
- `loguru` - Advanced logging system
- `pyyaml` - YAML configuration parser
- `ddgs` - DuckDuckGo search API (FREE, no API key needed)

**Optional Dependencies:**
- `python-dotenv` - Environment variable management
- Google Custom Search API credentials (for paid enhanced search)

#### 3. Set Up Configuration Files

**Create config directory structure:**
```bash
mkdir -p config data/alerts logs
```

**Create `config/config.yaml`:**
```yaml
monitoring:
  check_interval: 120              # Check every 2 minutes (120 seconds)
  notification_threshold: 0.2      # Alert threshold: 20% importance
  critical_threshold: 0.75         # Critical alert: 75% importance

target_crypto:
  name: "solana"                   # Main cryptocurrency to monitor
  symbol: "SOL"                    # Ticker symbol

ai_model:
  confidence_threshold: 0.6        # Minimum AI confidence
  batch_size: 4                    # Articles per batch

google_search:
  max_results: 20                  # Max search results per query
  time_filter: 'd1'                # Last 24 hours (d1 = 1 day)

notifications:
  min_importance_score: 0.2        # Minimum score for alerts
  max_notifications_per_hour: 12   # Rate limiting
```

**Create `config/keywords.yaml`:**
```yaml
cryptocurrencies:
  tier_1:  # Highest priority - checked most frequently
    - "solana news"
    - "SOL price breaking"
    - "solana breaking news"
    - "phantom wallet update"

  tier_2:  # Medium priority
    - "solana partnership"
    - "solana DeFi"
    - "raydium news"
    - "orca protocol"

  tier_3:  # Lower priority
    - "solana NFT"
    - "solana validator"
    - "solana ecosystem"

market_events:
  critical:  # Immediate alerts
    - "solana hack"
    - "solana outage"
    - "solana network down"
    - "phantom wallet hack"

  high_priority:  # Important updates
    - "solana upgrade"
    - "solana SEC"
    - "solana regulation"

  standard:  # Regular monitoring
    - "solana adoption"
    - "solana developer"
    - "solana conference"
```

#### 4. Set Up Discord Notifications (Optional but Recommended)

**Get Discord Webhook URL:**
1. Open your Discord server
2. Go to Server Settings → Integrations → Webhooks
3. Click "New Webhook"
4. Copy the webhook URL

**Create `.env` file in project root:**
```env
# Discord Webhook for notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# Optional: Google Custom Search API (if using paid search)
# GOOGLE_API_KEY=your_google_api_key
# GOOGLE_CSE_ID=your_custom_search_engine_id
```

⚠️ **Important:** Add `.env` to your `.gitignore` to protect your webhook URL!

#### 5. Test Your Installation
```bash
# Run system test
python main.py test

# Check system status
python main.py status

# Try a single analysis
python main.py analyze --keyword "solana news"
```

### First Run

Start monitoring with default settings (DuckDuckGo, free):
```bash
python main.py monitor
```

You should see:
- Console output showing search progress
- AI analysis results
- Price updates for Solana
- Discord notifications (if webhook configured)

## 🎮 Usage

### Available Commands

#### `status` - System Health Check
Check if all components are working correctly:
```bash
python main.py status
```
**Output:**
- Search engine status (Google/DuckDuckGo)
- AI model status (FinBERT)
- Component health
- Runtime statistics
- Search engine comparison table

#### `test` - Quick System Test
Run a quick test to verify everything works:
```bash
# Test with DuckDuckGo (default, FREE)
python main.py test

# Test with Google Search (requires API key)
python main.py test --engine google
```

#### `analyze` - Single Keyword Analysis
Analyze a specific keyword or run one monitoring cycle:
```bash
# Analyze specific keyword
python main.py analyze --keyword "solana breaking news"

# Run one full cycle with all configured keywords
python main.py analyze

# Use Google Search instead of DuckDuckGo
python main.py analyze --keyword "bitcoin ETF" --engine google
```

**What it does:**
1. Searches for the keyword
2. Extracts article content
3. AI analyzes importance
4. Displays results in formatted table

#### `monitor` - Continuous Monitoring (Main Feature)
Start real-time cryptocurrency news monitoring:
```bash
# Start monitoring with DuckDuckGo (FREE - recommended)
python main.py monitor

# Start monitoring with Google Search (PAID - better quality)
python main.py monitor --engine google
```

**Monitoring Features:**
- ✅ Runs continuously every 2 minutes (configurable)
- ✅ Analyzes all keywords from `keywords.yaml`
- ✅ Sends Discord notifications for important news
- ✅ Updates cryptocurrency prices
- ✅ Filters out low-importance noise
- ✅ Logs all events to `logs/app.log`

**Console Output Example:**
```
================================================
         CRYPTO AI ANALYZER
   AI-Enhanced Real-time News Monitor

Search Engine: DuckDuckGo Search (FREE)
Version: v2.0
Cost: FREE - No API key required
================================================

🔄 Starting monitoring cycle...
Analyzing keywords... ━━━━━━━━━━━━━━━━━━━━ 100%

╔══════════════════════════════════════════════════════╗
║       🔥 CRITICAL MARKET ALERTS                      ║
╠══════════════════════════════════════════════════════╣
║ 🚨 CRITICAL CRYPTO MARKET EVENTS                     ║
║ 🕐 10.10.2025 14:30                                  ║
╠══════════════════════════════════════════════════════╣
║                                                       ║
║ 🔥 TOP EVENTS:                                       ║
║ • solana breaking - Importance: 85.3% 🔥             ║
║ • phantom wallet update - Importance: 78.2% 🔥       ║
║ • solana partnership - Importance: 65.1% ⚡          ║
║                                                       ║
║ 📊 CATEGORY BREAKDOWN:                               ║
║ • Technology & Development: 8 articles (avg: 72.3%)  ║
║ • Market Movements: 5 articles (avg: 58.1%)          ║
║                                                       ║
║ 💰 CURRENT PRICES:                                   ║
║ • SOL: $142.35 (+5.23%)                              ║
║                                                       ║
║ 📈 MARKET STATUS: 🟢 Market in uptrend              ║
║                                                       ║
║ 📋 STATISTICS:                                       ║
║ • Analyzed articles: 45                              ║
║ • Important articles: 13                             ║
║ • Confidence level: 89.2%                            ║
╚══════════════════════════════════════════════════════╝

⏱️ Next cycle in 120 seconds...
```

#### `prices` - Check Cryptocurrency Prices
Get current prices without full analysis:
```bash
# Check default cryptos (bitcoin, ethereum, cardano, solana)
python main.py prices

# Check specific cryptocurrencies
python main.py prices --cryptos "solana,bitcoin,ethereum"

# Just Solana price
python main.py prices --cryptos "solana"
```

#### `compare` - Compare Search Engines
See detailed comparison of Google vs DuckDuckGo:
```bash
python main.py compare
```

**Comparison Output:**
```
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Feature       ┃ Google (v1.0)    ┃ DuckDuckGo (v2.0)┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ Cost          │ PAID             │ FREE             │
│ API Key       │ Required         │ Not Required     │
│ Daily Limit   │ 100 free/day     │ Unlimited        │
│ Result Quality│ ★★★★★            │ ★★★★☆            │
│ Setup         │ Complex          │ Simple           │
└───────────────┴──────────────────┴──────────────────┘

💡 Recommendation:
  • Use DuckDuckGo for FREE unlimited searches
  • Use Google if you need highest quality results
```

#### `summary` - Generate AI Market Summary
Generate comprehensive AI summary of current market:
```bash
python main.py summary
```

### Usage Examples

**Example 1: Monitor Solana 24/7**
```bash
# Set up for Solana monitoring
# 1. Edit config/config.yaml
target_crypto:
  name: "solana"
  symbol: "SOL"

# 2. Start monitoring
python main.py monitor

# 3. Let it run in background (Linux/Mac)
nohup python main.py monitor > output.log 2>&1 &

# 3. Let it run in background (Windows)
start /B python main.py monitor
```

**Example 2: Test New Keywords**
```bash
# Test a new keyword before adding to config
python main.py analyze --keyword "solana NFT marketplace"

# If importance score is good, add to keywords.yaml
```

**Example 3: Multi-Crypto Monitoring**
```yaml
# Edit config/keywords.yaml
cryptocurrencies:
  tier_1:
    - "solana news"
    - "bitcoin breaking"
    - "ethereum update"
```

**Example 4: Low-Noise Setup (Only Critical Alerts)**
```yaml
# Edit config/config.yaml
monitoring:
  notification_threshold: 0.7  # 70% threshold (only important news)
  critical_threshold: 0.85     # 85% for critical
```

## 📱 Discord Notifications

The system sends detailed market summaries to Discord with:

### **Format Example:**
```
[NEWS] IMPORTANT MARKET NEWS

🔥 TOP EVENTS:
• solana breaking - Importance: 61.3% 🔥
• solana partnership - Importance: 60.5% ⚡
• phantom wallet - Importance: 53.1%

💰 CURRENT PRICES:
• SOL: $219.11 (-3.84%) 🔴

📈 MARKET STATUS: 🔴 RED: Market in downtrend

📋 STATISTICS:
• Analyzed articles: 45
• Important articles: 12
• Confidence level: 92.6% 🎯

Crypto AI Analyzer • 12 important articles • Today at 20:34
```

## 🎯 Advanced Configuration

### Search Engine Selection
```bash
# Use DuckDuckGo (FREE)
python main.py monitor --engine duckduckgo

# Use Google Custom Search (PAID - requires API key)
python main.py monitor --engine google
```

### Notification Thresholds
```yaml
# config/config.yaml
monitoring:
  notification_threshold: 0.2    # Low threshold (20%)
  critical_threshold: 0.75       # Critical events (75%)

notifications:
  min_importance_score: 0.2      # Minimum for alerts
  max_notifications_per_hour: 12 # Rate limiting
```

### Keywords Customization
Edit `config/keywords.yaml`:
```yaml
cryptocurrencies:
  tier_1:  # Highest priority
    - "solana news"
    - "SOL price"
    - "solana breaking"
    
market_events:
  critical:
    - "solana hack"
    - "solana outage"
    - "phantom hack"
```

## 🔧 Architecture

### Core Components
- **Search Engines**: DuckDuckGo + Google Custom Search
- **Content Extractor**: Smart article parsing
- **AI Analyzer**: FinBERT-based importance scoring
- **Trend Detector**: Historical pattern analysis
- **Smart Notifier**: Multi-channel alert system
- **Price Fetcher**: Real-time crypto prices (CoinGecko, Coinbase)

### AI Analysis Pipeline
1. **Search** → Find relevant articles
2. **Extract** → Parse article content
3. **Analyze** → AI importance scoring
4. **Score** → Multi-factor final score
5. **Filter** → Apply thresholds
6. **Notify** → Send alerts

## 📈 Monitoring Metrics

### Importance Scoring Factors
- **AI Importance** (40%): FinBERT model assessment
- **Search Volume** (25%): Number of search results
- **Trend Momentum** (20%): Historical comparison
- **Source Quality** (10%): News source credibility
- **Time Decay** (5%): Content freshness

### Alert Levels
- **🔥 CRITICAL** (80%+): Immediate attention required
- **⚡ HIGH** (70%+): High priority review
- **📈 MEDIUM** (60%+): Monitor closely
- **📊 LOW** (40%+): Background information

## 🛠️ Development

### Project Structure
```
crypto-ai-analyzer/
├── main.py                 # CLI interface
├── modules/
│   ├── ai_analyzer.py      # FinBERT AI analysis
│   ├── crypto_price_fetcher.py  # Price APIs
│   ├── notifier.py         # Discord + console alerts
│   ├── importance_scorer.py # Multi-factor scoring
│   └── ...
├── config/
│   ├── config.yaml         # Main configuration
│   └── keywords.yaml       # Monitoring keywords
└── data/
    └── alerts/             # Alert history logs
```

### Adding New Features
1. **New Search Engine**: Extend `modules/` with new searcher
2. **Custom Notifications**: Modify `notifier.py` 
3. **AI Models**: Replace FinBERT in `ai_analyzer.py`
4. **Price Sources**: Add APIs in `crypto_price_fetcher.py`

## 🔍 Troubleshooting

### Common Issues

#### **1. No Discord Notifications**

**Problem:** Monitoring runs but no Discord messages appear

**Solutions:**
```bash
# Check webhook URL is correct in .env
cat .env  # Linux/Mac
type .env  # Windows

# Test webhook manually
curl -X POST -H "Content-Type: application/json" \
  -d '{"content": "Test message"}' \
  YOUR_WEBHOOK_URL

# Check logs for errors
tail -f logs/app.log  # Linux/Mac
type logs\app.log     # Windows

# Verify notification threshold isn't too high
# Edit config/config.yaml
monitoring:
  notification_threshold: 0.2  # Lower = more notifications
```

#### **2. Getting Too Many/Few Notifications**

**Too Many Notifications:**
```yaml
# config/config.yaml
monitoring:
  notification_threshold: 0.6  # Increase (0.0-1.0)

notifications:
  max_notifications_per_hour: 5  # Limit per hour
```

**Too Few Notifications:**
```yaml
# config/config.yaml
monitoring:
  notification_threshold: 0.2  # Decrease (20% threshold)
```

**Check what's being filtered:**
```bash
# Watch logs in real-time
tail -f logs/app.log | grep "FILTERED"
```

#### **3. Unicode/Encoding Errors on Windows**

**Problem:** Weird characters in console output

**Solution:** System handles this automatically, but if issues persist:
```bash
# Set console encoding (Windows CMD)
chcp 65001

# Or use PowerShell instead of CMD
powershell
python main.py monitor
```

#### **4. AI Model Download Issues**

**Problem:** FinBERT model fails to download

**Solutions:**
```bash
# Download model manually
python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
  AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
  AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"

# If behind firewall/proxy, set environment variables
export HF_ENDPOINT=https://hf-mirror.com  # Alternative Hugging Face mirror
```

#### **5. Search Engine Not Working**

**DuckDuckGo Issues:**
```bash
# Reinstall ddgs package
pip uninstall ddgs
pip install ddgs

# Try with Google instead
python main.py monitor --engine google
```

**Google Search Issues:**
```bash
# Verify API credentials in .env
GOOGLE_API_KEY=your_key_here
GOOGLE_CSE_ID=your_cse_id_here

# Test Google API directly
python -c "from modules.google_searcher import GoogleSearcher; \
  searcher = GoogleSearcher(); print('Google OK')"
```

#### **6. High Memory Usage**

**Problem:** Program uses too much RAM (~500MB+)

**This is normal** - FinBERT AI model requires ~500MB

**To reduce memory:**
- Close other applications
- Use lighter AI model (requires code modification)
- Increase `check_interval` to reduce frequency

#### **7. Rate Limiting / API Errors**

**CoinGecko Rate Limits:**
```
⚠️ Could not fetch crypto prices: 429 Too Many Requests
```

**Solution:** Wait 60 seconds, automatic retry implemented

**Google Search Daily Limit:**
```
❌ Google API error: Daily limit exceeded
```

**Solution:**
```bash
# Switch to DuckDuckGo (unlimited)
python main.py monitor --engine duckduckgo

# Or wait until tomorrow for Google quota reset
```

#### **8. Import Errors**

**Problem:** `ModuleNotFoundError: No module named 'X'`

**Solutions:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall

# Install missing package individually
pip install transformers torch aiohttp rich click loguru pyyaml ddgs

# Check Python version (requires 3.8+)
python --version
```

#### **9. Program Crashes on Start**

**Check logs:**
```bash
cat logs/app.log  # Linux/Mac
type logs\app.log # Windows
```

**Common fixes:**
```bash
# Create required directories
mkdir -p config data/alerts logs

# Verify config files exist
ls config/  # Should show config.yaml and keywords.yaml

# Run test command
python main.py test
```

## ❓ FAQ (Frequently Asked Questions)

### General Questions

**Q: Is this free to use?**
A: Yes! With DuckDuckGo search engine (default), everything is completely free. Google Search requires API key (100 free queries/day, then paid).

**Q: Do I need coding knowledge?**
A: Basic command-line knowledge is helpful, but you can follow the step-by-step setup guide. No coding required for normal use.

**Q: Can I monitor multiple cryptocurrencies?**
A: Yes! Add keywords for any crypto to `config/keywords.yaml`. The system works with Bitcoin, Ethereum, Cardano, Solana, and any other cryptocurrency.

**Q: How accurate is the AI analysis?**
A: The FinBERT model has ~75-85% accuracy for financial sentiment. Combined with multi-factor scoring, the system achieves good reliability. Always verify important news manually.

**Q: Does this work on Windows/Mac/Linux?**
A: Yes! Tested on all three platforms. Windows users may see Unicode warnings (handled automatically).

### Technical Questions

**Q: What's the difference between Google and DuckDuckGo search?**
A:
- **DuckDuckGo (FREE):** Unlimited searches, no API key, slightly lower quality results
- **Google (PAID):** 100 free/day then paid, requires setup, higher quality results

**Q: How much data does this use?**
A: Approximately 50-200MB per hour depending on:
- Number of keywords (more keywords = more data)
- Check interval (shorter interval = more data)
- Article sizes

**Q: Can I run this 24/7?**
A: Yes! Designed for continuous operation. Use process managers like:
- **Linux/Mac:** `nohup`, `screen`, `tmux`, `systemd`
- **Windows:** Run as background service or use Task Scheduler
- **Cloud:** Deploy on AWS, Google Cloud, Heroku, DigitalOcean

**Q: How do I monitor multiple Discord servers?**
A: Create multiple webhook URLs (one per server) and modify `modules/notifier.py` to send to multiple webhooks.

**Q: Can I customize the AI model?**
A: Yes! Edit `modules/ai_analyzer.py` to use different Hugging Face models. Popular alternatives:
- `distilbert-base-uncased-finetuned-sst-2-english` (faster, lighter)
- `nlptown/bert-base-multilingual-uncased-sentiment` (multilingual)

**Q: What's the importance score based on?**
A: Multi-factor algorithm:
- 40% AI sentiment (FinBERT)
- 25% Search volume
- 20% Trend momentum (historical comparison)
- 10% Source credibility (Reuters > random blog)
- 5% Content freshness

**Q: Can I export data to Excel/CSV?**
A: Alert logs are saved in `data/alerts/` as JSON. You can write a simple script to convert to CSV:
```python
import json, csv
with open('data/alerts/alert_log.json') as f:
    alerts = json.load(f)
# Convert to CSV here
```

### Setup Questions

**Q: Do I need a Discord webhook?**
A: No, it's optional. Without webhook, you'll get console notifications only.

**Q: How do I get Google Search API credentials?**
A:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable "Custom Search API"
4. Create credentials (API key)
5. Set up Custom Search Engine at [cse.google.com](https://cse.google.com/)

**Q: Where do I find my Discord webhook URL?**
A: Discord Server → Server Settings → Integrations → Webhooks → New Webhook

**Q: Can I monitor coins not on CoinGecko?**
A: Price fetching only works with CoinGecko-listed coins. News monitoring works with ANY keyword.

### Performance Questions

**Q: Why is it slow on first run?**
A: First run downloads the FinBERT AI model (~500MB). Subsequent runs are much faster.

**Q: How many keywords can I monitor?**
A: Tested with 50+ keywords. More keywords = slower cycles. Recommended: 10-30 keywords.

**Q: Can I speed it up?**
A: Yes:
- Reduce keywords in `keywords.yaml`
- Increase `check_interval` (e.g., 300 seconds = 5 minutes)
- Reduce `max_results` in `config.yaml`
- Use Google Search (faster than DuckDuckGo)

**Q: Does it support multiple languages?**
A: Search works in any language. AI analysis is optimized for English financial text. For other languages, change the AI model.

### Advanced Questions

**Q: Can I integrate this with trading bots?**
A: Not directly, but you can:
1. Parse Discord webhooks from your trading bot
2. Modify `modules/notifier.py` to call your bot's API
3. Read alert logs from `data/alerts/` programmatically

**Q: How do I deploy to cloud?**
A: Example for Heroku:
```bash
# Create Procfile
echo "worker: python main.py monitor" > Procfile

# Deploy
heroku create my-crypto-analyzer
git push heroku main
heroku ps:scale worker=1
```

**Q: Can I use this commercially?**
A: Yes, MIT License. Free for commercial use. No warranty provided.

**Q: How do I contribute?**
A:
1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request
See CONTRIBUTING.md for details.

## 📊 Performance

### Typical Performance
- **Search Speed**: 2-5 seconds per keyword
- **AI Analysis**: 1-3 seconds per article
- **Memory Usage**: ~500MB (FinBERT model)
- **CPU Usage**: Moderate during analysis bursts

### Optimization Tips
- Use DuckDuckGo for better performance
- Adjust `check_interval` for less frequent monitoring
- Reduce `max_keywords_per_cycle` for faster cycles

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and informational purposes only. Not financial advice. Always do your own research before making investment decisions.

## 🎯 Roadmap

- [ ] **Multi-Chain Support**: Ethereum, BSC, Polygon
- [ ] **Telegram Integration**: Alternative to Discord
- [ ] **Web Dashboard**: Real-time monitoring interface  
- [ ] **Mobile Notifications**: Push notifications
- [ ] **ML Improvements**: Custom trained models
- [ ] **API Integration**: Trading platform alerts

---

**Made with ❤️ for the Solana community**

*Star ⭐ this repository if you find it useful!*
