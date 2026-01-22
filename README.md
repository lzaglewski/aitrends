# AI Trends Monitor v3.1

Monitor advertising and marketing industry trends using **semantic topic modeling** with BERTopic + **LLM-enhanced trend identification** + **advanced temporal intelligence**. Automatically identifies emerging themes, tracks topic evolution, and detects semantic drift over time.

## 🎯 What's New in v3.1

**LLM Summarization Pipeline** - Dramatically improved clustering quality:

### 📝 FAZA 5: Pre-Clustering Summarization
- ✅ **LLM Article Summarization**: 2-3 sentence summaries before BERTopic clustering
- ✅ **Trend Relevance Filtering**: Auto-filters job posts, events, press releases
- ✅ **128 Token Optimization**: Summaries fit perfectly in embedding model limit
- ✅ **New CLI Commands**: `--summarize` and `--topics` for granular control

### Problem Solved
BERTopic's embedding model (MiniLM) has a **128 token limit**. Full articles get truncated, losing meaning.

**Before (v3.0)**: Full article → Truncated to 128 tokens → Poor embeddings → Weak clusters
**After (v3.1)**: Full article → LLM Summary (2-3 sentences) → Full meaning captured → Strong clusters

### New Pipeline Flow
```
Scraping → Save Articles → LLM Summarization → BERTopic (uses summary) → LLM Validation → Trends
                                  ↓
                    Filters: job posts, events, press releases
                    Output: 2-3 sentence trend-focused summary
```

### Cost & Performance
- ~$0.0003 per article (gpt-4o-mini)
- 1000 articles ≈ $0.30
- Processing: ~0.5s delay per article (rate limiting)

---

## 🎯 What's New in v3.0

**Major Intelligence Upgrade** - 12 new features across 4 phases:

### 📊 FAZA 1: Quick Wins
- ✅ **Fuzzy Deduplication**: 10-20% reduction in duplicate articles (rapidfuzz)
- ✅ **Embedding Cache**: 50-70% faster reruns with 90-day TTL cache
- ✅ **BERTopic Tuning**: Enhanced clustering (min_topic_size=10, min_samples=3)

### 🎯 FAZA 2: Data Quality
- ✅ **Full Article Scraping**: Complete content extraction when RSS truncates (trafilatura)
- ✅ **Source Credibility Weighting**: YAML-based source weights with blacklist support
- ✅ **Weighted Trend Detection**: High-quality sources have more influence

### ⏰ FAZA 3: Temporal Intelligence
- ✅ **Time-Weighted Embeddings**: Recent articles prioritized (14-day half-life)
- ✅ **Trend History Tracking**: Historical snapshots with centroid embeddings
- ✅ **Multi-Period Analysis**: Lifecycle stages (🌱 emerging → 📈 growing → ⭐ peak → 📉 declining)

### 🧠 FAZA 4: Advanced Analytics
- ✅ **Topic Merging**: LLM-validated automatic duplicate topic consolidation
- ✅ **Cross-Topic Correlation**: Source overlap + temporal + semantic proximity
- ✅ **Semantic Drift Detection**: LLM-described topic evolution alerts

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

**v3.0 (Advanced Intelligence)**:
```
Trending Topics:
- 🔥 Trending · 📈 Growing AI-Powered Content Generation (+156%)
  Description: Major platforms integrating generative AI for ad creation
  Stage: Growing | Velocity: +0.15 | Articles: 23 (weighted: 31.5)

  Related Topics:
    • Marketing Automation Tools (correlation: 0.68)
    • Generative AI Ethics (correlation: 0.54)

  Semantic Drift: ⚠️ Topic evolved (drift: 0.32)
    Evolution: Shifted from basic AI tools to enterprise-level integration platforms

  Historical Trend: [3 → 5 → 9 → 23 articles over 8 weeks]

- 🌟 New · 🌱 Emerging Privacy-First Marketing Strategies (NEW)
  Description: Industry shift toward cookieless tracking and consent management
  Stage: Emerging | Velocity: +0.28 | Articles: 12 (weighted: 15.0)

  Historical Trend: [0 → 0 → 2 → 12 articles over 8 weeks]
```

## 🚀 Features

### Core Intelligence
- **LLM-Enhanced Trend Analysis**: GPT-4o-mini validates and names trends with context understanding
- **Semantic Topic Modeling**: BERTopic identifies thematic clusters
- **Time-Weighted Analysis**: Recent articles prioritized with exponential decay
- **Multi-Period Lifecycle**: Track trends through emerging → growing → peak → declining stages

### Data Processing
- **Fuzzy Deduplication**: Automatic removal of duplicate articles (85% similarity threshold)
- **Full Content Scraping**: Extract complete article text when RSS truncates (trafilatura)
- **Source Credibility Weighting**: YAML-configured weights for high-quality sources
- **Embedding Cache**: 50-70% performance improvement on reruns

### Advanced Analytics
- **Topic Merging**: LLM-validated consolidation of duplicate topics
- **Cross-Topic Correlation**: Identify related trends (source overlap + temporal + semantic)
- **Semantic Drift Detection**: Alert when topics evolve significantly
- **Trend History**: Historical snapshots with centroid embeddings

### Infrastructure
- **RSS Feed Monitoring**: Automatically fetch articles from marketing/AI sources
- **Multi-format Output**: Console, Email (HTML), Slack, JSON
- **SQLite Database**: Local storage with deduplication
- **Automated Scheduling**: Periodic scraping with configurable intervals

## 📁 Project Structure

```
AI_TRENDS/
├── src/
│   ├── scrapers/
│   │   ├── rss_fetcher.py        # RSS feed scraper
│   │   └── content_scraper.py    # Full content extraction (NEW v3.0)
│   ├── processors/
│   │   ├── keyword_extractor.py  # Text extraction
│   │   ├── deduplicator.py       # Fuzzy deduplication (NEW v3.0)
│   │   └── article_summarizer.py # LLM summarization pipeline (NEW v3.1)
│   ├── analyzers/
│   │   ├── topic_modeler.py      # BERTopic + temporal weighting
│   │   ├── trend_detector.py     # Multi-period analysis (v3.0)
│   │   ├── lifecycle_analyzer.py # Lifecycle stages (NEW v3.0)
│   │   ├── topic_merger.py       # LLM-validated merging (NEW v3.0)
│   │   ├── correlation_analyzer.py # Cross-topic correlations (NEW v3.0)
│   │   ├── drift_detector.py     # Semantic drift detection (NEW v3.0)
│   │   ├── temporal_weighting.py # Time-weighted embeddings (NEW v3.0)
│   │   └── llm_trend_analyzer.py # LLM enhancement
│   ├── formatters/         # Output formatters (console, email, slack)
│   ├── storage/
│   │   ├── models.py             # Database schema + 2 new tables (v3.0)
│   │   ├── database.py           # Database operations
│   │   └── embedding_cache.py    # Embedding cache manager (NEW v3.0)
│   ├── utils/
│   │   └── source_weights.py     # Source credibility manager (NEW v3.0)
│   └── config.py           # Configuration (24 new parameters in v3.0)
├── data/
│   ├── sources.yaml        # List of RSS sources to monitor
│   ├── source_weights.yaml # Source credibility weights (NEW v3.0)
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
Re-analyzes all articles with BERTopic. Runs summarization first if enabled.

#### Run Only Summarization (NEW v3.1)
```bash
python main.py --summarize
```
Generates LLM summaries for articles without them. Use to pre-process before clustering.

#### Run Only Topic Modeling (NEW v3.1)
```bash
python main.py --topics
```
Runs BERTopic clustering and trend detection only (skips scraping and summarization).
Use when summaries already exist and you want to re-cluster.

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
TOPIC_MIN_TOPIC_SIZE=10             # Minimum articles per topic (v3.0: increased)
TOPIC_MIN_SAMPLES=3                 # Minimum samples for HDBSCAN core points (NEW v3.0)
TOPIC_MIN_DOCUMENT_LENGTH=50        # Minimum text length

# LLM Enhancement (v2.1)
USE_LLM_ENHANCEMENT=True            # Enable LLM-based trend analysis
OPENAI_API_KEY=sk-proj-...          # OpenAI API key (or set in .env)
LLM_MODEL=gpt-4o-mini               # Model to use
LLM_MAX_ARTICLES_PER_TOPIC=5        # Cost control: max articles per topic
LLM_TEMPERATURE=0.3                 # Lower = more focused

# LLM Summarization Pipeline (NEW v3.1)
USE_LLM_SUMMARIZATION=True          # Enable pre-clustering summarization
LLM_SUMMARY_DELAY_SECONDS=0.5       # Rate limiting delay between calls
LLM_SUMMARY_MAX_CONTENT_CHARS=4000  # Max article content to send to LLM
LLM_SUMMARY_MAX_RETRIES=3           # Retry attempts for failed calls
LLM_SUMMARY_BATCH_SIZE=50           # Articles per processing batch

# Quick Wins (NEW v3.0)
DEDUP_ENABLED=True                  # Fuzzy deduplication
DEDUP_SIMILARITY_THRESHOLD=0.85     # Similarity threshold for duplicates
EMBEDDING_CACHE_ENABLED=True        # Cache embeddings for performance
EMBEDDING_CACHE_TTL_DAYS=90         # Cache time-to-live

# Data Quality (NEW v3.0)
FULL_CONTENT_ENABLED=True           # Scrape full article content
FULL_CONTENT_MIN_RSS_LENGTH=500     # Min RSS length before full scraping
SOURCE_WEIGHTS_ENABLED=True         # Use source credibility weights
SOURCE_WEIGHTS_CONFIG=data/source_weights.yaml

# Temporal Intelligence (NEW v3.0)
USE_TEMPORAL_WEIGHTING=True         # Time-weighted embeddings
TEMPORAL_LAMBDA_DECAY=0.05          # Decay rate (~14-day half-life)
USE_MULTIPERIOD_ANALYSIS=True       # Multi-period lifecycle analysis
MULTIPERIOD_WEEKS=2                 # Period length in weeks
MULTIPERIOD_COUNT=4                 # Number of periods to analyze

# Advanced Analytics (NEW v3.0)
USE_TOPIC_MERGING=True              # Automatic topic merging
TOPIC_MERGE_SIMILARITY=0.85         # Merge threshold
TOPIC_MERGE_USE_LLM=True            # LLM-validated merging
USE_CORRELATION_ANALYSIS=True       # Cross-topic correlations
CORRELATION_MIN_THRESHOLD=0.3       # Min correlation to report
USE_DRIFT_DETECTION=True            # Semantic drift detection
DRIFT_THRESHOLD=0.3                 # Min drift score to alert
DRIFT_LOOKBACK_DAYS=14              # Days to compare for drift

# Trend Detection
TREND_WINDOW_DAYS=30                # Compare last 30 vs. previous 30 days (legacy)
TREND_MIN_GROWTH_RATE=0.2           # 20% growth = trending
TREND_MIN_COUNT=3                   # Minimum articles to be trending

# Output
TREND_OUTPUT_FORMAT=console         # 'console', 'email', 'slack', 'json'
TREND_MAX_DISPLAY=10                # Max trends to display
```

## 📊 Example Output

### Console (v3.0)

```
================================================================================
🔥 MARKETING & AI TRENDS (8 weeks, multi-period analysis)
Generated: 2025-12-09 15:30 UTC | Cache Hit Rate: 73% | Duplicates Removed: 15%
================================================================================

1. 🔥 Trending · 📈 Growing AI-Powered Content Generation
   Description: Major platforms integrating generative AI for ad creation
   Keywords: ai, content, generation, advertising, automation

   📊 Metrics:
   - Articles: 23 (weighted: 31.5) | Growth: +156%
   - Stage: Growing | Velocity: +0.15
   - Historical: [3 → 5 → 9 → 23] over 4 periods

   🔗 Related Topics (correlation):
   - Marketing Automation Tools (0.68 - strong)
   - Generative AI Ethics (0.54 - moderate)

   ⚠️  Semantic Drift Detected (score: 0.32):
   "Shifted from basic AI tools to enterprise-level integration platforms"
   ----------------------------------------------------------------------------

2. 🌟 New · 🌱 Emerging Privacy-First Marketing Strategies
   Description: Industry shift toward cookieless tracking and consent management
   Keywords: privacy, cookies, tracking, gdpr, consent

   📊 Metrics:
   - Articles: 12 (weighted: 15.0) | Growth: NEW
   - Stage: Emerging | Velocity: +0.28
   - Historical: [0 → 0 → 2 → 12] over 4 periods

   🔗 Related Topics (correlation):
   - Data Privacy Regulations (0.75 - very strong)
   ----------------------------------------------------------------------------

3. ⬆️ Trending · ⭐ Peak Influencer Marketing ROI
   Description: Measurement and analytics for influencer campaigns
   Keywords: influencer, roi, measurement, analytics, performance

   📊 Metrics:
   - Articles: 18 (weighted: 22.5) | Growth: +88%
   - Stage: Peak | Velocity: -0.05 (slowing)
   - Historical: [5 → 8 → 12 → 18] over 4 periods
   ----------------------------------------------------------------------------

📈 Summary: 15 topics analyzed | 7 trending | 2 new | 3 declining | 3 topics merged
⚡ Performance: Embedding cache 73% hit rate | Full scraping: 65% of articles
```

### Email (HTML)

Set `TREND_OUTPUT_FORMAT=email` for formatted HTML tables suitable for newsletters.

### Slack

Set `TREND_OUTPUT_FORMAT=slack` for markdown-formatted messages.

### JSON

Set `TREND_OUTPUT_FORMAT=json` for structured data export.

## 🔧 How It Works

### Architecture (v3.1)

```
                    RSS Sources
                         ↓
                  Full Content Scraper (trafilatura)
                         ↓
                  Fuzzy Deduplication (rapidfuzz)
                         ↓
                   Save to Database
                         ↓
         ┌────────────────────────────────┐
         │  LLM Summarization (NEW v3.1)  │ ← GPT-4o-mini
         ├────────────────────────────────┤
         │ • 2-3 sentence summaries       │
         │ • Trend relevance filtering    │
         │ • Filters: jobs, events, PR    │
         └────────────────────────────────┘
                         ↓
              ┌──────────────────────┐
              │  BERTopic Clustering │
              ├──────────────────────┤
              │ • Uses SUMMARY text  │ ← Not full content!
              │ • Embedding (cache)  │
              │ • Temporal weighting │
              │ • UMAP + HDBSCAN     │
              │ • c-TF-IDF           │
              └──────────────────────┘
                         ↓
              ┌──────────────────────┐
              │   Topic Merging      │ ← LLM validates duplicates
              └──────────────────────┘
                         ↓
              ┌──────────────────────┐
              │  LLM Analysis        │ ← Validates + names trends
              │  (GPT-4o-mini)       │
              └──────────────────────┘
                         ↓
              ┌──────────────────────┐
              │  Database Storage    │
              │  + Trend Snapshots   │
              └──────────────────────┘
                         ↓
              ┌──────────────────────┐
              │  Multi-Period        │ ← Lifecycle analysis
              │  Trend Detector      │   (4 periods of 2 weeks)
              └──────────────────────┘
                         ↓
         ┌────────────────────────────────┐
         │   Advanced Analytics           │
         ├────────────────────────────────┤
         │ • Correlation analysis         │
         │ • Semantic drift detection     │
         │ • Historical comparison        │
         └────────────────────────────────┘
                         ↓
         ┌────────────────────────────────┐
         │   Formatters                   │
         │   (Console/Email/Slack/JSON)   │
         └────────────────────────────────┘
```

### LLM Summarization Pipeline (NEW v3.1)

**Why summarization?**
- BERTopic's embedding model (MiniLM) has a **128 token limit**
- Full articles (500-2000 words) get truncated → loss of meaning
- Short summaries (2-3 sentences) capture the essence within the limit

**Process:**
1. **Article Input**: Full content (up to 4000 chars) sent to GPT-4o-mini
2. **Summary Generation**: LLM creates 2-3 sentence trend-focused summary
3. **Relevance Check**: LLM determines if article is trend-relevant
4. **Filtering**: Non-trend content marked as `is_trend_relevant=False`

**What gets filtered out:**
- Job postings / hiring announcements
- Event invitations / conference announcements
- Press releases about company financials (without industry implications)
- Product documentation / how-to guides (without trend context)
- Purely promotional content

**Database fields:**
```sql
ALTER TABLE articles ADD COLUMN summary TEXT;
ALTER TABLE articles ADD COLUMN is_trend_relevant BOOLEAN DEFAULT TRUE;
ALTER TABLE articles ADD COLUMN summary_generated_at DATETIME;
```

### Hybrid BERTopic + LLM Pipeline

1. **Summarization (NEW)**: LLM generates 2-3 sentence summaries, filters non-trends
2. **Embedding**: Convert **summaries** (not full articles) to semantic vectors
3. **Dimensionality Reduction**: UMAP to 5 dimensions
4. **Clustering**: HDBSCAN to find topic clusters
5. **Representation**: c-TF-IDF to extract topic keywords
6. **LLM Validation**: GPT-4o-mini validates trends and generates natural language names
7. **Filtering**: Only real trends (not company news) are saved

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

### Basic Testing

```bash
# Run on existing data (if database populated)
python main.py --once

# Re-run topic modeling
python main.py --remodel

# Debug LLM decisions (shows full prompts and responses)
python main.py --remodel --debug

# Check database
sqlite3 data/trends.db "SELECT * FROM topics LIMIT 5;"
```

### Testing v3.1 Features (Summarization)

```bash
# Run summarization only (generates summaries for all articles without them)
python main.py --summarize
# Check logs for: "Summarized: X articles, Filtered: Y articles"

# Run topic modeling only (uses existing summaries, skips scraping)
python main.py --topics
# Check logs for: "Using LLM summaries for X/Y articles"

# Check summaries in database
sqlite3 data/trends.db "SELECT id, title, summary, is_trend_relevant FROM articles LIMIT 5;"

# Check filtered articles (not trend-relevant)
sqlite3 data/trends.db "SELECT COUNT(*) FROM articles WHERE is_trend_relevant = 0;"

# Check articles with summaries
sqlite3 data/trends.db "SELECT COUNT(*) FROM articles WHERE summary IS NOT NULL;"
```

### Testing v3.0 Features

```bash
# Test deduplication
python main.py --once
# Check logs for: "Deduplication metrics: X duplicates removed"

# Test embedding cache (run twice)
python main.py --remodel  # First run (cold cache)
python main.py --remodel  # Second run (should be 50-70% faster)
# Check logs for: "Embedding cache: X/Y hits (Z% hit rate)"

# Test full content scraping
python main.py --once
# Check logs for: "Full content scraping complete: X scraped, Y RSS used"

# Test source weighting
sqlite3 data/trends.db "SELECT name, url, credibility_weight FROM sources;"
# Verify weights loaded from source_weights.yaml

# Test lifecycle analysis
python main.py --once
# Output should show stages: 🌱 Emerging, 📈 Growing, ⭐ Peak, etc.

# Test topic merging (need multiple similar topics)
python main.py --once
# Check logs for: "Merged X topic pairs"

# Test correlation analysis (need multiple trending topics)
python main.py --once
# Output should show "Related Topics" section for each trend

# Test semantic drift (need historical data - run for 2+ weeks)
python main.py --once
# Check logs for: "Detected semantic drift in X topics"
# Output shows: "⚠️ Semantic Drift Detected"

# View all snapshots for a topic
sqlite3 data/trends.db "SELECT * FROM trend_snapshots WHERE topic_id=1 ORDER BY snapshot_date DESC;"

# View embedding cache statistics
sqlite3 data/trends.db "SELECT COUNT(*), MIN(created_at), MAX(last_accessed) FROM embedding_cache;"
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

### Configuring Source Weights (NEW v3.0)

Edit [data/source_weights.yaml](data/source_weights.yaml) to set credibility weights:

```yaml
# Default weight for unlisted sources
default_weight: 1.0

# High credibility sources (weight: 1.5)
high_credibility:
  - adage.com
  - marketingweek.com
  - thinkwithgoogle.com
  weight: 1.5

# Medium credibility (weight: 1.0)
medium_credibility:
  - contentmarketinginstitute.com
  weight: 1.0

# Low credibility (weight: 0.5)
low_credibility:
  - content-farm-example.com
  weight: 0.5

# Blacklist (weight: 0 - filtered out)
blacklist:
  - spam-site.com
  weight: 0
```

**How it works:**
- Higher weights = more influence on trending topics
- Blacklisted sources are completely filtered out
- Weighted counts shown in output: `Articles: 23 (weighted: 31.5)`

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

## 📈 Performance & Metrics (v3.0)

### Expected Improvements

**Performance:**
- **First Run**: Normal speed (establishes cache)
- **Second Run**: 50-70% faster (embedding cache)
- **Third+ Runs**: Consistent fast performance

**Data Quality:**
- **Deduplication**: 10-20% reduction in duplicate articles
- **Full Content**: 65-80% of articles enhanced with complete text
- **Source Weighting**: High-quality sources influence trends more

**Intelligence:**
- **Lifecycle Classification**: 100% of trends categorized (emerging/growing/peak/declining)
- **Related Topics**: Average 2-4 correlations per trending topic
- **Drift Detection**: Typically 5-10% of topics show significant evolution

### Monitoring

Check logs for performance metrics:
```bash
tail -f logs/ad_trends_*.log | grep -E "(cache|dedup|merge|correlation|drift)"
```

Example metrics output:
```
Embedding cache: 730/1000 hits (73% hit rate)
Deduplication: 150/1000 removed (15% reduction)
Full content scraping: 650/1000 successful (65%)
Source weighting: raw=1000, weighted=1250 (25% boost)
Topic merging: 5 candidates, 2 merged
Correlation analysis: 45 pairs, 8 strong correlations
Semantic drift: 33 topics checked, 3 drifts detected
```

## 🐛 Troubleshooting

### Issue: Summarization not running (v3.1)
- Check `USE_LLM_SUMMARIZATION=True` in config
- Verify `OPENAI_API_KEY` is set in `.env` file
- Check logs for: "ArticleSummarizer initialized with model: gpt-4o-mini"
- Run standalone: `python main.py --summarize`

### Issue: Too many articles filtered as "not trend-relevant" (v3.1)
- Review the filtered articles: `sqlite3 data/trends.db "SELECT title FROM articles WHERE is_trend_relevant = 0;"`
- The LLM may be too aggressive - check if legitimate trend articles are being filtered
- Consider adjusting the prompt in `src/processors/article_summarizer.py`

### Issue: BERTopic "max_df corresponds to < documents than min_df" error
- This happens when summaries are too short/similar
- The system auto-retries with relaxed vectorizer settings
- If persistent, check summary quality in database

### Issue: No topics detected
- Check `MIN_ARTICLE_LENGTH` - may be filtering too many articles
- Lower `TOPIC_MIN_TOPIC_SIZE` to allow smaller topics
- Verify articles are being scraped: `sqlite3 data/trends.db "SELECT COUNT(*) FROM articles;"`
- Check if articles have summaries: `sqlite3 data/trends.db "SELECT COUNT(*) FROM articles WHERE summary IS NOT NULL;"`

### Issue: Poor topic quality
- Increase `TOPIC_MIN_TOPIC_SIZE` for broader topics
- Use language-specific model (`'en'` or `'pl'`) instead of multilingual
- Run `--remodel` after changing parameters

### Issue: Too many "new" topics
- Increase `TREND_WINDOW_DAYS` for longer comparison window
- Increase `TREND_MIN_COUNT` to filter low-frequency topics

### Issue: Slow performance (v3.0)
- **First run is slow**: Normal - building embedding cache
- **Still slow on second run**: Check `EMBEDDING_CACHE_ENABLED=True` in config
- **Cache not working**: Check logs for cache hit rate, may need to clear old cache
- **Full scraping too slow**: Reduce `FULL_CONTENT_MAX_WORKERS` or disable with `FULL_CONTENT_ENABLED=False`

### Issue: Too many/few topic merges (v3.0)
- **Too aggressive**: Increase `TOPIC_MERGE_SIMILARITY` (default: 0.85)
- **Not merging duplicates**: Lower threshold or check LLM is enabled (`TOPIC_MERGE_USE_LLM=True`)
- **Disable merging**: Set `USE_TOPIC_MERGING=False`

### Issue: No correlations detected (v3.0)
- Lower `CORRELATION_MIN_THRESHOLD` (default: 0.3)
- Ensure you have enough trending topics (need at least 2)
- Check that centroids are being computed (look for "Computing centroid" in logs)

### Issue: No drift detected (v3.0)
- Topics may be stable (good thing!)
- Lower `DRIFT_THRESHOLD` for more sensitivity (default: 0.3)
- Increase `DRIFT_LOOKBACK_DAYS` for longer comparison window
- Ensure historical snapshots exist (run system for 2+ weeks)

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
- `rapidfuzz>=3.0.0` - Fuzzy deduplication (v3.0)
- `trafilatura>=1.6.0` - Full content extraction (v3.0)

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

## 🎉 Version History

- **v3.1** (January 22, 2026) - LLM Summarization Pipeline: Pre-clustering article summarization for dramatically improved clustering quality
- **v3.0** (January 21, 2026) - Advanced Intelligence: Multi-period analysis, temporal weighting, topic merging, correlation analysis, drift detection
- **v2.1** (December 9, 2025) - LLM Enhancement: GPT-4o-mini integration for better trend identification
- **v2.0** (November 2025) - Major Refactor: BERTopic semantic topic modeling
- **v1.0** (October 2025) - Initial Release: Keyword-based trend detection

---

**Version**: 3.1 (LLM Summarization Pipeline)
**Last Updated**: January 22, 2026
**Status**: Production Ready ✅

**Key Metrics v3.1**:
- LLM-generated summaries optimize 128-token embedding limit
- Auto-filters non-trend content (jobs, events, press releases)
- New CLI commands: `--summarize`, `--topics`
- 3 new database fields: `summary`, `is_trend_relevant`, `summary_generated_at`
- 5 new configuration parameters

**Key Metrics v3.0**:
- 12 new features across 4 phases
- 9 new modules (2,391 lines of code)
- 2 new database tables
- 24 new configuration parameters
- 50-70% performance improvement on reruns
- 10-20% reduction in duplicate articles
