# Crypto AI Analyzer

AI-Enhanced Real-time Cryptocurrency News Monitor that intelligently analyzes crypto market trends and sends smart alerts for important developments.

## Features

- **Google Search Integration** - Monitors search volume for trending crypto topics
- **AI-Powered Analysis** - Uses FinBERT model to assess news importance 
- **Trend Detection** - Compares current activity vs historical data to detect viral moments
- **Smart Notifications** - Console alerts for critical crypto developments
- **Source Quality Assessment** - Weights news based on source credibility
- **Real-time Monitoring** - Continuous monitoring with configurable intervals

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd crypto_ai_analyzer

# Create virtual environment  
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Download NLTK data (one-time)
python -c "import nltk; nltk.download('punkt'); nltk.download('vader_lexicon')"

# Download spaCy model (one-time)
python -m spacy download en_core_web_sm
```

### 2. Configuration

**Set up Google Search API:**
1. Get API key from [Google Cloud Console](https://console.cloud.google.com/)
2. Enable "Custom Search API"
3. Create Custom Search Engine at [Google CSE](https://cse.google.com/)

**Create .env file:**
```bash
cp .env.template .env
# Edit .env and add your API credentials:
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id
```

### 3. Usage

**Check system status:**
```bash
python main.py status
```

**Analyze specific keyword:**
```bash
python main.py analyze --keyword "bitcoin news"
python main.py analyze --keyword "SEC cryptocurrency"
```

**Start real-time monitoring:**
```bash
python main.py monitor
# Press Ctrl+C to stop
```

**Quick system test:**
```bash
python main.py test
```

## Configuration

### Keywords Configuration

Create `config/keywords.yaml` to customize monitored topics:

```yaml
cryptocurrencies:
  tier_1:  # Checked every cycle (highest priority)
    - "bitcoin news"
    - "ethereum news"
    - "BTC breaking"
    
  tier_2:  # Checked every 2 cycles
    - "cardano news"
    - "solana news"
    
market_events:
  - "crypto regulation"
  - "bitcoin ETF"
  - "SEC cryptocurrency"
```

### Main Configuration

Edit `config/config.yaml` for system settings:

```yaml
monitoring:
  check_interval: 1800          # 30 minutes between cycles
  notification_threshold: 0.5   # Score threshold for alerts
  
google_search:
  max_results: 10              # Results per search
  time_filter: "d1"            # Last 24 hours
  
notifications:
  min_importance_score: 0.4    # Minimum score to notify
  min_ai_confidence: 0.4       # Minimum AI confidence
```

## How It Works

### 1. Google Search Volume Detection
- Monitors search volume for configured keywords
- Detects trending topics based on result count
- Filters results by time (last 24 hours by default)

### 2. AI Content Analysis  
- Extracts article content from search results
- Uses FinBERT (financial BERT) to analyze importance
- Assesses market impact, novelty, sentiment strength

### 3. Trend Detection
- Stores historical search volumes in SQLite database
- Compares current vs historical data to detect viral spikes
- Calculates trend momentum scores

### 4. Smart Scoring Algorithm
```
Final Score = (
    AI Importance × 40% +
    Search Volume × 25% + 
    Trend Momentum × 20% +
    Source Quality × 10% +
    Time Freshness × 5%
)
```

### 5. Intelligent Notifications
- Beautiful console alerts with color coding
- Rate limiting to prevent spam
- Different alert levels (CRITICAL, HIGH, MEDIUM, LOW)
- Saves alert history to JSON files

## Project Structure

```
crypto_ai_analyzer/
├── main.py                    # Main application
├── requirements.txt           # Dependencies
├── .env                      # API keys (create from template)
├── README.md                 # This file
│
├── config/
│   ├── config.yaml           # Main configuration
│   └── keywords.yaml         # Keywords to monitor
│
├── modules/
│   ├── google_searcher.py    # Google Search API integration
│   ├── content_extractor.py  # Article content extraction
│   ├── ai_analyzer.py        # AI importance analysis
│   ├── importance_scorer.py  # Final scoring algorithm  
│   ├── trend_detector.py     # Trend detection engine
│   ├── notifier.py          # Smart notification system
│   └── data_manager.py      # Data storage management
│
├── data/
│   ├── historical/          # Trend history database
│   ├── alerts/              # Alert logs
│   └── processed/           # Analysis results
│
└── logs/
    ├── app.log             # Application logs
    └── ai_model.log        # AI model logs
```

## API Limits

**Google Custom Search API:**
- **Free tier**: 100 searches/day
- **Paid tier**: $5 per 1000 searches
- Monitor usage with: `python -c "from modules.google_searcher import GoogleSearcher; print(GoogleSearcher().get_quota_status())"`

## Example Output

```
🔥 CRITICAL CRYPTO ALERT 🔥
┌─────────────────────────────────────────┐
│ 🎯 Keyword:      bitcoin ETF approval   │
│ 📊 Importance:    0.891 (89.1%)        │ 
│ 🎯 Confidence:    0.923 (92.3%)        │
│ 📈 Trend Score:   0.850 (viral)        │
│ 🌐 Top Sources:   reuters.com, ...     │
└─────────────────────────────────────────┘

💡 Analysis: CRITICAL IMPORTANCE • AI models indicate 
high significance • High search volume • Strong trending

📋 Recommendation: 🚨 IMMEDIATE ATTENTION REQUIRED
```

## Troubleshooting

**"No search results" errors:**
- Check API key configuration in .env
- Verify Google Custom Search API is enabled
- Check daily quota usage

**"AI model loading" issues:**
- Ensure internet connection for model download
- Check disk space (models are ~400MB)
- Try clearing cache: `rm -rf ~/.cache/huggingface/`

**"Content extraction failed":**
- Normal for some sites (paywall, anti-bot)
- System handles gracefully and tries multiple articles

## Advanced Usage

**Custom notification thresholds:**
```bash
python main.py config --threshold 0.8  # Only critical alerts
```

**Analyze trending keywords:**
```python
from modules.trend_detector import TrendDetector
detector = TrendDetector()
trending = await detector.get_trending_keywords(limit=10)
```

**View alert history:**
```python  
from modules.notifier import SmartNotifier
notifier = SmartNotifier()
notifier.display_alert_history()
```

## Contributing

The system is modular and extensible:

- Add new AI models in `ai_analyzer.py`
- Extend notification channels in `notifier.py`  
- Add new data sources beyond Google Search
- Implement additional scoring factors

## License

This project is for educational and research purposes. Please respect API terms of service and rate limits.

## Disclaimer

This tool is for informational purposes only. Do not use for financial decisions without additional research and professional advice. Cryptocurrency markets are highly volatile and risky.