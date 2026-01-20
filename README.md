# AI Trends Monitor v2.1

Monitor advertising and marketing industry trends using **semantic topic modeling** with BERTopic + **LLM-enhanced trend identification**. Automatically identifies emerging themes and tracks topic evolution over time.

## 🎯 What's New in v2.1

**LLM Enhancement** - Hybrid BERTopic + GPT-4o-mini for better trend identification:

- ✅ **Context Understanding**: LLM distinguishes real trends from company news
- ✅ **Better Naming**: Natural language trend names instead of keyword combinations
- ✅ **Quality Filtering**: Filters out noise topics (Polish declensions, stopwords)
- ✅ **Cost Effective**: ~$0.12/month using gpt-4o-mini

## 🎯 What's New in v2.0

**Completely refactored** from keyword-based to topic-based trend detection:

- ✅ **BERTopic**: Semantic topic modeling instead of keyword extraction
- ✅ **Multilingual Support**: Handles English, Polish, and mixed sources
- ✅ **Named Entity Filtering**: Removes company/person names from trends
- ✅ **Better Insights**: Detects thematic concepts, not just word frequencies
- ✅ **Email/Slack Formatters**: Ready for automated delivery

### Before vs. After

**v1.0 (Keyword-Based)**:
```
Trending:
- Google (15 occurrences)
- CEO John Doe (8 occurrences)
- Search Console (12 occurrences)
```

**v2.0 (Topic-Based with BERTopic only)**:
```
Trending Topics:
- Search + Content + Business (+156%)
- Ponad + Kampanii + Rynku (NEW)  ← Polish declensions
- Google + Gemini + AI (+89%)    ← Company names
```

**v2.1 (LLM-Enhanced)**:
```
Trending Topics:
- AI-Powered Content Generation in Advertising (+156%)
  Description: Major platforms integrating generative AI for ad creation

- Privacy-First Marketing Strategies (NEW)
  Description: Industry shift toward cookieless tracking and consent management
```

## 🚀 Features

- **LLM-Enhanced Trend Analysis**: GPT-4o-mini validates and names trends with context understanding
- **Semantic Topic Modeling**: Uses BERTopic to identify thematic clusters
- **RSS Feed Monitoring**: Automatically fetch articles from marketing/AI sources
- **Trend Detection**: Identify trending, new, and declining topics
- **Multi-format Output**: Console, Email (HTML), Slack, JSON
- **SQLite Database**: Local storage with deduplication
- **Automated Scheduling**: Periodic scraping with configurable intervals

## 📁 Project Structure

```
AI_TRENDS/
├── src/
│   ├── scrapers/           # RSS fetcher and web scrapers
│   ├── processors/         # Text extraction (TopicExtractor)
│   ├── analyzers/          # Topic modeling (BERTopic), trend detection
│   ├── formatters/         # Output formatters (console, email, slack)
│   ├── storage/            # Database models and operations
│   └── config.py           # Configuration
├── data/
│   ├── sources.yaml        # List of RSS sources to monitor
│   ├── trends.db           # SQLite database (auto-created)
│   └── models/             # Saved BERTopic models
├── logs/                   # Application logs
├── main.py                 # Main scheduler
├── requirements.txt        # Python dependencies
└── IMPLEMENTATION.md       # Detailed technical documentation
```

## 🏃 Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repo-url>
cd AI_TRENDS

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 1.5 Configure OpenAI API (for LLM Enhancement)

Create a `.env` file in the project root:

```bash
# OpenAI API Key for LLM Enhancement
OPENAI_API_KEY=sk-proj-your-api-key-here
```

**Note**: LLM enhancement is optional. Set `USE_LLM_ENHANCEMENT=False` in [src/config.py](src/config.py#L30) to disable.

### 2. Initialize Database

```bash
# Create database tables
python main.py --init-db

# Load sources from sources.yaml
python main.py --init-sources
```

### 3. Run the System

#### One-Time Run
```bash
python main.py --once
```
Scrapes sources, runs topic modeling, calculates trends, and exits.

#### Continuous Mode (Scheduler)
```bash
python main.py
```
Runs continuously, scraping every 6 hours (configurable).

#### Re-run Topic Modeling
```bash
python main.py --remodel
```
Re-analyzes all articles with BERTopic. Use when changing topic modeling parameters.

## ⚙️ Configuration

Edit [src/config.py](src/config.py) or create `.env` file:

```env
# Database
DATABASE_URL=sqlite:///./data/trends.db

# Scraping
SCRAPE_INTERVAL_HOURS=6
MIN_ARTICLE_LENGTH=30

# Topic Modeling
TOPIC_MODEL_LANGUAGE=multilingual  # 'multilingual', 'en', 'pl'
TOPIC_MIN_TOPIC_SIZE=8              # Minimum articles per topic
TOPIC_MIN_DOCUMENT_LENGTH=50        # Minimum text length

# LLM Enhancement (v2.1)
USE_LLM_ENHANCEMENT=True            # Enable LLM-based trend analysis
OPENAI_API_KEY=sk-proj-...          # OpenAI API key (or set in .env)
LLM_MODEL=gpt-4o-mini               # Model to use
LLM_MAX_ARTICLES_PER_TOPIC=5        # Cost control: max articles per topic
LLM_TEMPERATURE=0.3                 # Lower = more focused

# Trend Detection
TREND_WINDOW_DAYS=30                # Compare last 30 vs. previous 30 days
TREND_MIN_GROWTH_RATE=0.2           # 20% growth = trending

# Output
TREND_OUTPUT_FORMAT=console         # 'console', 'email', 'slack', 'json'
TREND_MAX_DISPLAY=10                # Max trends to display
```

## 📊 Example Output

### Console

```
================================================================================
🔥 MARKETING & AI TRENDS (30 days)
Generated: 2025-12-09 15:30 UTC
================================================================================

1. 🌟 Nowe AI + Content + Generation
   Keywords: ai, content, generation, advertising, automation
   Articles: 23 (previous: 0) | Growth: NEW
   ----------------------------------------------------------------------------

2. ⬆️ Rosnące Privacy + Marketing + Strategies
   Keywords: privacy, cookies, tracking, gdpr, consent
   Articles: 18 (previous: 10) | Growth: +80%
   ----------------------------------------------------------------------------

3. ⬆️ Rosnące Influencer + Marketing + ROI
   Keywords: influencer, roi, measurement, analytics, performance
   Articles: 15 (previous: 8) | Growth: +88%
   ----------------------------------------------------------------------------
```

### Email (HTML)

Set `TREND_OUTPUT_FORMAT=email` for formatted HTML tables suitable for newsletters.

### Slack

Set `TREND_OUTPUT_FORMAT=slack` for markdown-formatted messages.

### JSON

Set `TREND_OUTPUT_FORMAT=json` for structured data export.

## 🔧 How It Works

### Architecture

```
RSS Sources → Scrape Articles → Clean Text → BERTopic Clustering
                                                      ↓
                                              LLM Analysis (GPT-4o-mini)
                                                      ↓
                                              Validated Trends
                                                      ↓
                                              Database Storage
                                                      ↓
                                    Trend Detector (Compare Periods)
                                                      ↓
                                    Formatters (Console/Email/Slack)
```

### Hybrid BERTopic + LLM Pipeline

1. **Embedding**: Convert articles to semantic vectors (Sentence Transformers)
2. **Dimensionality Reduction**: UMAP to 5 dimensions
3. **Clustering**: HDBSCAN to find topic clusters
4. **Representation**: c-TF-IDF to extract topic keywords
5. **LLM Analysis**: GPT-4o-mini validates trends and generates natural language names
6. **Filtering**: Only real trends (not company news) are saved

### Trend Detection

- Compare topic frequencies: **last 30 days** vs. **previous 30 days**
- Calculate growth rate: `(current - previous) / previous`
- Mark as **trending** if growth ≥ 20%
- Mark as **new** if topic didn't exist before

## 📚 Documentation

For detailed technical documentation, see [IMPLEMENTATION.md](IMPLEMENTATION.md):
- Problem statement (why we replaced keywords with topics)
- Architecture deep-dive
- Database schema
- Configuration options
- Performance considerations
- Future enhancements

## 🧪 Testing

```bash
# Run on existing data (if database populated)
python main.py --once

# Re-run topic modeling
python main.py --remodel

# Debug LLM decisions (shows full prompts and responses)
python main.py --remodel --debug

# View LLM analysis in readable format
./debug_llm_decisions.sh

# Check database
sqlite3 data/trends.db "SELECT * FROM topics LIMIT 5;"
```

### Debugging LLM Decisions

To understand why topics were classified as trends or rejected:

1. **Enable debug mode:**
   ```bash
   python main.py --remodel --debug
   ```

2. **View formatted analysis:**
   ```bash
   ./debug_llm_decisions.sh
   ```

   This shows:
   - Articles sent to LLM for each topic
   - BERTopic keywords
   - Full LLM response with reasoning
   - Summary of accepted/rejected trends

3. **Check raw logs:**
   ```bash
   tail -f logs/ad_trends_$(date +%Y-%m-%d).log
   ```

📖 **Full debugging guide:** See [DEBUG_GUIDE.md](DEBUG_GUIDE.md) for detailed examples and troubleshooting.

## 🛠️ Development

### Adding New Sources

Edit [data/sources.yaml](data/sources.yaml):

```yaml
sources:
  - name: "Your Source Name"
    url: "https://example.com/rss"
    type: rss
```

Then reload:
```bash
python main.py --init-sources
```

### Customizing Topic Modeling

Edit parameters in `src/config.py`:

- `TOPIC_MIN_TOPIC_SIZE`: Smaller = more granular topics
- `TOPIC_MODEL_LANGUAGE`:
  - `'multilingual'`: Best for mixed sources (default)
  - `'en'`: Faster for English-only
  - `'pl'`: Optimized for Polish

### Output Formats

Create custom formatters in `src/formatters/trend_summarizer.py`:

```python
def format_for_custom(trends, **kwargs):
    # Your custom formatting logic
    return formatted_output
```

## 🐛 Troubleshooting

### Issue: No topics detected
- Check `MIN_ARTICLE_LENGTH` - may be filtering too many articles
- Lower `TOPIC_MIN_TOPIC_SIZE` to allow smaller topics
- Verify articles are being scraped: `sqlite3 data/trends.db "SELECT COUNT(*) FROM articles;"`

### Issue: Poor topic quality
- Increase `TOPIC_MIN_TOPIC_SIZE` for broader topics
- Use language-specific model (`'en'` or `'pl'`) instead of multilingual
- Run `--remodel` after changing parameters

### Issue: Too many "new" topics
- Increase `TREND_WINDOW_DAYS` for longer comparison window
- Increase `TREND_MIN_COUNT` to filter low-frequency topics

## 📦 Requirements

- Python 3.9+
- ~2GB RAM for topic modeling (100-200 articles)
- ~500MB disk space (including models)

### Key Dependencies

- `bertopic>=0.16.0` - Topic modeling
- `sentence-transformers>=2.2.0` - Semantic embeddings
- `umap-learn>=0.5.5` - Dimensionality reduction
- `hdbscan>=0.8.33` - Clustering
- `scikit-learn>=1.3.0` - Utilities
- `openai>=1.0.0` - LLM enhancement (v2.1)

See [requirements.txt](requirements.txt) for complete list.

## 📝 License

[Your License]

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📧 Contact

- Issues: [GitHub Issues]
- Documentation: See [IMPLEMENTATION.md](IMPLEMENTATION.md)

---

**Version**: 2.1 (LLM-Enhanced)
**Last Updated**: December 9, 2025
**Status**: Production Ready ✅
