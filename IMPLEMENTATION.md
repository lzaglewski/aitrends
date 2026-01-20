# Implementation Documentation: Topic-Based Trend Detection System

**Date**: December 9, 2025
**Version**: 2.1 (LLM-Enhanced)
**Author**: AI Trends Monitor Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Architecture](#solution-architecture)
4. [Technical Implementation](#technical-implementation)
5. [Key Components](#key-components)
6. [Database Schema Changes](#database-schema-changes)
7. [Configuration](#configuration)
8. [Usage Guide](#usage-guide)
9. [Migration from v1.0](#migration-from-v10)
10. [Performance Considerations](#performance-considerations)
11. [Future Enhancements](#future-enhancements)

---

## Executive Summary

The AI Trends Monitor system has been completely refactored from a **keyword-based trend detection system** to a **semantic topic modeling system** using BERTopic. This change addresses the fundamental flaw in v1.0 where the system extracted named entities (companies, people, products) instead of meaningful thematic trends.

### Key Changes:
- ❌ **Removed**: YAKE keyword extraction, spaCy NER
- ✅ **Added**: BERTopic for semantic topic modeling
- ✅ **Added**: Named entity filtering
- ✅ **Added**: Multi-language support (multilingual embeddings)
- ✅ **Added**: Topic-based trend tracking
- ✅ **Added**: Email/Slack formatters for trend summaries
- ✅ **Added**: LLM-based trend identification and naming (v2.1)

### Results:
**Before (v1.0):**
```
Trending Keywords:
- Google (15 occurrences, +50% growth)
- CEO Sundar Pichai (8 occurrences, NEW)
- Search Console (12 occurrences, +33% growth)
```

**After (v2.0):**
```
Trending Topics:
- AI-Generated Advertising Content (+156% growth)
  Keywords: ai, content, generation, advertising, automation

- Privacy-First Marketing Strategies (NEW topic)
  Keywords: privacy, cookies, tracking, gdpr, consent

- Influencer Marketing ROI (+89% growth)
  Keywords: influencer, roi, measurement, analytics, performance
```

---

## Problem Statement

### Issues with v1.0 (Keyword-Based System)

The original implementation used YAKE (statistical keyword extraction) and spaCy NER (Named Entity Recognition) to extract "keywords" from articles. This approach had several critical flaws:

#### 1. **Entity Extraction vs. Concept Extraction**

The system extracted:
- **Named entities**: "Google", "Microsoft", "CEO John Doe"
- **Noun chunks**: "CREATORS TRIBE pochodzi", "Search Console appeared"
- **Product names**: "ChatGPT", "Gemini", "GPT-4"

But **NOT** abstract concepts like:
- "AI-powered marketing automation"
- "Personalization in digital advertising"
- "Privacy-focused advertising strategies"

#### 2. **No Semantic Understanding**

YAKE and spaCy treat each mention independently:
- "Google launches AI tool" → keyword: "Google"
- "Microsoft announces AI feature" → keyword: "Microsoft"
- System doesn't recognize the underlying trend: "AI tool launches by tech companies"

#### 3. **Language Mismatch**

- Sources were primarily English (AdAge, Marketing Week, etc.)
- System was configured for Polish (`language='pl'`)
- Result: Mixed-language fragments, poor extraction quality

#### 4. **Overly Simplistic Trend Logic**

Trends were calculated purely by frequency growth:
```python
growth_rate = (current_count - previous_count) / previous_count
```

If "Google" appeared 10 times last month and 15 times this month:
- ✅ System marks it as "trending" (+50%)
- ❌ But "Google" is not a trend, it's just a company mentioned more often

#### 5. **No Post-Processing**

After extraction, keywords were simply:
1. Combined from both methods (YAKE + spaCy)
2. Sorted by score
3. Saved to database

No filtering for:
- Domain relevance (marketing/AI terms only)
- Named entity removal
- Semantic deduplication
- Conceptual abstraction

---

## Solution Architecture

### High-Level Overview

```
┌─────────────────┐
│  RSS Sources    │
└────────┬────────┘
         │ scrape
         ▼
┌─────────────────┐
│  Raw Articles   │
└────────┬────────┘
         │ clean text
         ▼
┌─────────────────┐
│ Text Extractor  │ (TopicExtractor)
└────────┬────────┘
         │ cleaned documents
         ▼
┌─────────────────┐
│  BERTopic       │ (TopicModeler)
│  Topic Modeling │
└────────┬────────┘
         │ topic assignments + metadata
         ▼
┌─────────────────┐
│   Database      │
│ (topics, trends)│
└────────┬────────┘
         │ query
         ▼
┌─────────────────┐
│ Trend Detector  │
└────────┬────────┘
         │ trending topics
         ▼
┌─────────────────┐
│ Trend Formatter │ (Email/Slack/Console)
└─────────────────┘
```

### BERTopic Pipeline

BERTopic uses a multi-stage pipeline:

```
Documents
    │
    ▼
┌─────────────────────┐
│ Sentence Embeddings │ (Sentence Transformers)
└──────────┬──────────┘
           │ 384-dim vectors
           ▼
┌─────────────────────┐
│ UMAP Reduction      │ (5 dimensions)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ HDBSCAN Clustering  │ (Find topic clusters)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ c-TF-IDF           │ (Extract representative words)
└──────────┬──────────┘
           │
           ▼
      Topic Names + Keywords
```

### Key Differences from v1.0

| Aspect | v1.0 (Keywords) | v2.0 (Topics) |
|--------|----------------|---------------|
| **Extraction Method** | YAKE + spaCy NER | BERTopic (semantic clustering) |
| **Unit of Analysis** | Individual words/phrases | Semantic topic clusters |
| **Language Support** | Polish only | Multilingual |
| **Filtering** | None | Named entity filtering |
| **Concept Understanding** | No | Yes (via embeddings) |
| **Trend Tracking** | Keyword frequency | Topic frequency |
| **Output Quality** | Named entities, noise | Thematic concepts |

---

## Technical Implementation

### Core Technologies

#### 1. **BERTopic**
- **Purpose**: Unsupervised topic modeling
- **Version**: >=0.16.0
- **Key Features**:
  - Transformer-based embeddings (contextual understanding)
  - HDBSCAN clustering (density-based, handles outliers)
  - c-TF-IDF for topic representation
  - Dynamic topic modeling (tracks topics over time)

#### 2. **Sentence Transformers**
- **Purpose**: Generate semantic embeddings
- **Model**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Why**: Supports 50+ languages, 384-dim embeddings
- **Alternatives**:
  - English-only: `all-MiniLM-L6-v2` (faster, smaller)
  - Polish: `sdadas/mmlw-retrieval-roberta-base`

#### 3. **UMAP** (Uniform Manifold Approximation and Projection)
- **Purpose**: Dimensionality reduction
- **Parameters**:
  - `n_neighbors=15`: Local neighborhood size
  - `n_components=5`: Target dimensions
  - `metric='cosine'`: Similarity metric for text

#### 4. **HDBSCAN** (Hierarchical Density-Based Spatial Clustering)
- **Purpose**: Clustering documents into topics
- **Parameters**:
  - `min_cluster_size=3`: Minimum articles per topic
  - `metric='euclidean'`: After UMAP reduction
  - `cluster_selection_method='eom'`: Excess of mass

---

## Key Components

### 1. `src/analyzers/topic_modeler.py`

**Purpose**: Wrapper around BERTopic for topic extraction

**Key Methods**:
```python
class TopicModeler:
    def __init__(
        self,
        language: str = 'multilingual',
        min_topic_size: int = 3,
        nr_topics: Optional[int] = None,
        diversity: float = 0.3
    )

    def extract_topics(
        self,
        documents: List[str],
        min_document_length: int = 50
    ) -> Tuple[List[int], Dict[int, Dict]]

    def get_topic_trends(
        self,
        topic_assignments: List[Tuple[int, int, str]],
        window_days: int = 30
    ) -> List[Dict]
```

**How it works**:
1. Preprocesses text (removes URLs, emails, extra whitespace)
2. Generates embeddings using Sentence Transformers
3. Reduces dimensions with UMAP
4. Clusters with HDBSCAN
5. Extracts topic keywords with c-TF-IDF
6. Generates human-readable topic names

**Topic Naming Strategy**:
```python
def _generate_topic_name(self, top_words: List[str]) -> str:
    # Example: ["ai", "marketing", "automation"]
    # Returns: "Ai + Marketing + Automation"
    name_words = [word.capitalize() for word in top_words[:3]]
    return " + ".join(name_words)
```

### 2. `src/analyzers/semantic_clustering.py`

**Purpose**: Filter named entities and normalize concepts

**Components**:

#### a. `NamedEntityFilter`
Blacklists known companies, products, and people:
```python
company_blacklist = {
    'google', 'facebook', 'meta', 'microsoft', ...
}

person_patterns = [
    r'\b(ceo|cto|cfo|cmo)\s+\w+',  # CEO John Doe
    r'\b(mr|mrs|ms|dr)\.\s+\w+',   # Dr. Smith
]
```

#### b. `ConceptNormalizer`
Merges synonyms and normalizes concepts:
```python
synonyms = {
    'artificial intelligence': 'ai',
    'machine learning': 'ml',
    'digital marketing': 'marketing',
    'personalisation': 'personalization',
}
```

### 3. `src/analyzers/trend_detector.py`

**Purpose**: Calculate trending topics based on frequency changes

**Key Changes from v1.0**:
- Uses `get_topic_counts()` instead of `get_keyword_counts()`
- Retrieves topic metadata (names, keywords) from database
- Tracks both "trending" (growth) and "new" (didn't exist before) topics

**Trend Calculation**:
```python
def calculate_trends(self, window_days=30, min_count=3, min_growth_rate=0.2):
    # Compare last 30 days vs. previous 30 days
    current_counts = db.get_topic_counts(current_start, current_end)
    previous_counts = db.get_topic_counts(previous_start, previous_end)

    for topic_id, current_count in current_counts.items():
        previous_count = previous_counts.get(topic_id, 0)

        if previous_count > 0:
            growth_rate = (current_count - previous_count) / previous_count
        else:
            growth_rate = 1.0  # New topic

        is_trending = growth_rate >= min_growth_rate
        is_new = previous_count == 0
```

### 4. `src/formatters/trend_summarizer.py`

**Purpose**: Format trends for different output channels

**Supported Formats**:
- **Console**: Rich text table with colors/emojis
- **Email**: HTML table with styling
- **Slack**: Markdown-formatted message
- **JSON**: Structured data for APIs

**Example Output** (Console):
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
```

### 5. `src/processors/keyword_extractor.py` → `TopicExtractor`

**Renamed and Simplified**:
- ❌ **Removed**: YAKE extraction, spaCy NER, keyword scoring
- ✅ **Kept**: Text cleaning (HTML removal, whitespace normalization)
- ✅ **Added**: Backward compatibility wrapper for `KeywordExtractor`

**New Responsibility**:
```python
class TopicExtractor:
    def extract_text(self, content: str) -> str:
        """Clean and prepare text for topic modeling."""
        # Remove HTML, URLs, emails
        # Normalize whitespace
        return cleaned_text

    def get_article_preview(self, content: str, max_length: int = 500) -> str:
        """Get preview for display purposes."""
```

---

## Database Schema Changes

### New Tables

#### 1. `topics` Table
Stores metadata about each topic discovered by BERTopic:

```sql
CREATE TABLE topics (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER UNIQUE NOT NULL,  -- BERTopic's topic ID
    topic_name VARCHAR(512) NOT NULL,  -- Human-readable name
    top_words TEXT NOT NULL,            -- JSON array of keywords
    size INTEGER NOT NULL DEFAULT 0,    -- Number of articles
    created_at DATETIME,
    updated_at DATETIME
);
```

**Example Record**:
```json
{
    "id": 1,
    "topic_id": 0,
    "topic_name": "AI + Marketing + Automation",
    "top_words": "[\"ai\", \"marketing\", \"automation\", \"tools\", \"platforms\"]",
    "size": 45,
    "created_at": "2025-12-01 10:00:00",
    "updated_at": "2025-12-09 15:30:00"
}
```

### Modified Tables

#### 1. `articles` Table - Added Columns
```sql
ALTER TABLE articles ADD COLUMN topic_id INTEGER;
ALTER TABLE articles ADD COLUMN cleaned_content TEXT;

CREATE INDEX idx_article_topic ON articles(topic_id);
```

- `topic_id`: BERTopic topic assignment (-1 = outlier/noise)
- `cleaned_content`: Preprocessed text used for topic modeling

#### 2. `trends` Table - Added Columns
```sql
ALTER TABLE trends ADD COLUMN topic_id INTEGER;
ALTER TABLE trends ADD COLUMN is_new BOOLEAN DEFAULT FALSE;
```

- `topic_id`: Links trend to topic metadata
- `is_new`: Flags topics that didn't exist in previous period

### Database Workflow

```
1. Scrape articles → Save to `articles` table
2. Run topic modeling → Assign `topic_id` to articles
3. Save topic metadata → Insert/update `topics` table
4. Calculate trends → Compare topic frequencies
5. Save trends → Insert into `trends` table with `topic_id`
```

---

## Configuration

### Environment Variables (`.env`)

```env
# Database
DATABASE_URL=sqlite:///./data/trends.db

# Scraping
SCRAPE_INTERVAL_HOURS=6
MAX_ARTICLES_PER_SOURCE=50
MIN_ARTICLE_LENGTH=30

# Topic Modeling
TOPIC_MODEL_LANGUAGE=multilingual  # 'multilingual', 'en', 'pl'
TOPIC_MIN_TOPIC_SIZE=3
TOPIC_MIN_DOCUMENT_LENGTH=50
TOPIC_MODEL_PATH=./data/models/topic_model
TOPIC_REMODEL_THRESHOLD=100

# Trend Detection
TREND_WINDOW_DAYS=30
TREND_MIN_COUNT=3
TREND_MIN_GROWTH_RATE=0.2

# Output
TREND_OUTPUT_FORMAT=console  # 'console', 'email', 'slack', 'json'
TREND_MAX_DISPLAY=10
```

### Config Explanation

**Topic Modeling**:
- `TOPIC_MODEL_LANGUAGE`:
  - `'multilingual'`: Best for mixed English/Polish sources (default)
  - `'en'`: Faster, English-only sources
  - `'pl'`: Polish-optimized embeddings

- `TOPIC_MIN_TOPIC_SIZE`: Minimum articles to form a topic
  - Lower = more granular topics (but may include noise)
  - Higher = broader topics (but may miss emerging trends)
  - Recommended: 3-5

- `TOPIC_REMODEL_THRESHOLD`: Re-train model after N new articles
  - Lower = more frequent updates (resource-intensive)
  - Higher = less frequent updates (may miss new topics)
  - Recommended: 100-200

**Trend Detection**:
- `TREND_MIN_GROWTH_RATE`: Minimum growth to be "trending"
  - `0.2` = 20% growth required
  - Lower = more trends flagged (including noise)
  - Higher = only significant trends

---

## Usage Guide

### Installation

```bash
# Clone repository
git clone <repo-url>
cd AI_TRENDS

# Install dependencies
pip install -r requirements.txt

# Initialize database
python main.py --init-db

# Add sources
python main.py --init-sources
```

### Running the System

#### 1. **One-Time Run**
```bash
python main.py --once
```
Scrapes sources, runs topic modeling, calculates trends, and exits.

#### 2. **Continuous Mode** (Scheduler)
```bash
python main.py
```
Runs continuously, scraping every `SCRAPE_INTERVAL_HOURS`.

#### 3. **Re-run Topic Modeling**
```bash
python main.py --remodel
```
Resets all topic assignments and re-runs BERTopic on all articles.
**Use when**: Changing topic modeling parameters or adding/removing sources.

### Output Examples

#### Console Output
```
================================================================================
Starting scraping job at 2025-12-09 15:30:00
================================================================================
INFO: Found 12 active sources
INFO: Processing source: AdAge (rss)
INFO: Fetched 25 articles from AdAge
INFO: Saved article 1234: New AI Tools for Marketing...
...
INFO: Scraping completed: 150 total articles (45 new)
INFO: Running topic modeling...
INFO: Processing 45 documents with BERTopic...
INFO: Topic modeling completed: 8 topics identified
INFO: Calculating trends...
INFO: Found 5 trending topics (2 new)

================================================================================
🔥 MARKETING & AI TRENDS (30 days)
Generated: 2025-12-09 15:30 UTC
================================================================================

1. 🌟 Nowe AI + Content + Generation
   Keywords: ai, content, generation, advertising, automation
   Articles: 23 (previous: 0) | Growth: NEW
   ----------------------------------------------------------------------------

...
```

#### JSON Output
```json
{
  "generated_at": "2025-12-09T15:30:00",
  "period_days": 30,
  "total_trends": 8,
  "trending_count": 5,
  "new_count": 2,
  "trending": [
    {
      "topic_id": 0,
      "topic_name": "AI + Content + Generation",
      "top_words": ["ai", "content", "generation", "advertising", "automation"],
      "count": 23,
      "previous_count": 0,
      "growth_rate": 1.0,
      "is_trending": true,
      "is_new": true,
      "status": "🌟 Nowe"
    }
  ]
}
```

---

## Migration from v1.0

### For Existing Databases

If you have an existing database with keyword-based data:

#### Option 1: Clean Slate (Recommended)
```bash
# Backup old database
cp data/trends.db data/trends_backup.db

# Re-initialize with new schema
python main.py --init-db

# Re-scrape sources (they're still in sources.yaml)
python main.py --once
```

#### Option 2: Preserve Articles
```python
# Manual migration script (example)
from src.storage.database import Database

db = Database()

# Keep articles, remove old keywords/trends
with db.get_session() as session:
    session.query(Keyword).delete()
    session.query(Trend).delete()
    session.commit()

# Re-run topic modeling
python main.py --remodel
```

### Updating Custom Integrations

If you have custom code using the old API:

**Before (v1.0)**:
```python
from src.processors.keyword_extractor import KeywordExtractor

extractor = KeywordExtractor(language='pl')
keywords = extractor.extract_all(text, max_keywords=20)
top = extractor.get_top_keywords(keywords, top_n=10)
```

**After (v2.0)** - Backward Compatible:
```python
from src.processors.keyword_extractor import TopicExtractor

extractor = TopicExtractor(language='multilingual')
cleaned_text = extractor.extract_text(text)

# For topic modeling, use TopicModeler instead:
from src.analyzers.topic_modeler import TopicModeler

modeler = TopicModeler()
topic_ids, topic_info = modeler.extract_topics([cleaned_text])
```

---

## Performance Considerations

### Computational Cost

#### BERTopic Pipeline Breakdown:
| Stage | Time (100 articles) | Scaling |
|-------|---------------------|---------|
| Embedding Generation | ~10s | O(n) |
| UMAP Reduction | ~5s | O(n log n) |
| HDBSCAN Clustering | ~3s | O(n log n) |
| c-TF-IDF | ~1s | O(n) |
| **Total** | ~20s | O(n log n) |

#### Optimization Strategies:

1. **Batch Processing**: Process articles in batches of 100-200
   ```python
   # Instead of one-by-one
   for article in articles:
       modeler.extract_topics([article])  # Slow!

   # Batch all at once
   modeler.extract_topics(articles)  # Fast!
   ```

2. **Model Persistence**: Save/load trained models
   ```python
   # First run: Train and save
   modeler.extract_topics(documents)
   modeler.save_model('./data/models/topic_model')

   # Subsequent runs: Load existing
   modeler.load_model('./data/models/topic_model')
   ```

3. **Incremental Updates**: Only process new articles
   ```python
   # Filter articles without topic_id
   new_articles = session.query(Article).filter(Article.topic_id == None)
   ```

4. **GPU Acceleration** (optional):
   ```python
   # If GPU available, sentence-transformers will use it automatically
   import torch
   print(f"CUDA available: {torch.cuda.is_available()}")
   ```

### Memory Usage

**Estimated Memory per 1000 articles**:
- Embeddings (384-dim): ~1.5 MB
- UMAP reduction: ~200 KB
- HDBSCAN: ~500 KB
- **Total**: ~2-3 MB per 1000 articles

For large datasets (>10,000 articles), consider:
- Periodic model retraining (not all articles at once)
- Database partitioning by date
- Archiving old articles

---

## LLM Enhancement (v2.1)

### Overview

After initial implementation of BERTopic, we discovered that pure statistical clustering cannot distinguish between **trends** (industry-wide patterns) and **news** (single company announcements). Polish language declensions also created noise in topic keywords.

**Solution**: Hybrid approach where BERTopic handles clustering and LLM provides semantic understanding.

### Architecture

```
Articles → BERTopic Clustering → LLM Analysis → Filtered Trends
           (5-10 clusters)         (GPT-4o-mini)   (2-5 real trends)
```

### Implementation

#### 1. **LLM Trend Analyzer** (`src/analyzers/llm_trend_analyzer.py`)

```python
class LLMTrendAnalyzer:
    def analyze_topic_cluster(
        self,
        topic_id: int,
        articles: List[Dict],
        bert_topic_words: List[str]
    ) -> Optional[Dict]:
        """Determines if cluster represents a real trend"""

        # Sample up to 5 articles (cost control)
        sample_articles = articles[:settings.LLM_MAX_ARTICLES_PER_TOPIC]

        # Build prompt with article titles + 200 char snippets
        prompt = self._build_analysis_prompt(sample_articles, bert_topic_words)

        # Call GPT-4o-mini with structured JSON output
        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": """You are a marketing analyst.
                Identify TRENDS (patterns across multiple organizations)
                not NEWS (single company events)."""},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Low = more focused
            response_format={"type": "json_object"}
        )

        parsed = json.loads(response.choices[0].message.content)

        if parsed.get("is_trend", False):
            return {
                "trend_name": parsed["trend_name"],
                "description": parsed["description"],
                "keywords": parsed["keywords"],
                "confidence": parsed["confidence"]
            }
        return None  # Not a trend - filter it out
```

#### 2. **Prompt Engineering**

The prompt asks LLM to:
- Analyze article titles + content snippets
- Use BERTopic keywords as hints
- Distinguish TREND vs NEWS
- Return structured JSON

**Example Prompt**:
```
Analyze these 5 marketing/AI articles:

1. **Google Announces New AI Features**
   Google launched several new AI-powered features for advertisers including automated bidding...

2. **Microsoft Integrates AI into Advertising Platform**
   Microsoft is bringing generative AI capabilities to its ad platform...

3. **Meta Tests AI-Generated Ad Copy**
   Meta is testing AI-generated ad copy across Facebook and Instagram...

BERTopic Keywords: ai, advertising, automation, platform

Task: Is this a TREND or just NEWS?

Output Format (JSON):
{
  "is_trend": true/false,
  "trend_name": "Concise name" (if trend),
  "description": "Brief explanation" (if trend),
  "keywords": ["keyword1", "keyword2"] (if trend),
  "confidence": 0.0-1.0 (if trend),
  "reason": "Why not a trend" (if not trend)
}
```

**Example Response**:
```json
{
  "is_trend": true,
  "trend_name": "AI-Powered Ad Platform Integration",
  "description": "Major advertising platforms integrating generative AI for automated content creation and bidding optimization",
  "keywords": ["ai integration", "ad automation", "generative advertising", "platform tools"],
  "confidence": 0.85
}
```

#### 3. **Integration into Pipeline** ([main.py:137-164](main.py#L137-L164))

```python
# Run BERTopic clustering
topic_ids, topic_info = topic_modeler.extract_topics(documents)
logger.info(f"BERTopic: {len(topic_info)} raw topics")

# LLM Enhancement
if settings.USE_LLM_ENHANCEMENT:
    # Group articles by topic_id
    articles_by_topic = {}
    for article_id, topic_id in zip(article_ids, topic_ids):
        if topic_id == -1:  # Skip outliers
            continue

        # Get article from DB (title + 500 chars)
        article = db.get_article(article_id)
        articles_by_topic[topic_id].append({
            'title': article.title,
            'content': article.content[:500]
        })

    # Enhance with LLM
    topic_info = enhance_topics_with_llm(topic_info, articles_by_topic)
    logger.info(f"LLM: {len(topic_info)} trends identified")
```

### Configuration

Add to [.env](.env):
```bash
OPENAI_API_KEY=sk-proj-...
```

Add to [src/config.py](src/config.py#L29-L35):
```python
USE_LLM_ENHANCEMENT: bool = True
LLM_MODEL: str = "gpt-4o-mini"
LLM_MAX_ARTICLES_PER_TOPIC: int = 5
LLM_MAX_TOKENS: int = 500
LLM_TEMPERATURE: float = 0.3
```

### Cost Analysis

**Per Run Estimate**:
- BERTopic identifies ~10 topics
- LLM analyzes 5 articles × 10 topics = 50 articles
- Average: 200 tokens input + 150 tokens output per topic
- Total: ~3,500 tokens ≈ $0.001 (gpt-4o-mini)

**Monthly** (4 runs/day × 30 days): ~$0.12

### Results

**Before LLM** (BERTopic only):
```
Topics:
1. Search + Content + Business
2. Ponad + Kampanii + Rynku  (Polish declensions)
3. Google + Gemini + AI
4. Na + Się + Że  (Polish stopwords)
```

**After LLM** (Hybrid):
```
Trends:
1. AI-Powered Content Generation in Advertising (+156% growth)
   Description: Major platforms integrating generative AI for ad creation

2. Privacy-First Marketing Strategies (NEW)
   Description: Industry shift toward cookieless tracking and consent management
```

### Benefits

1. **Context Understanding**: LLM distinguishes trends from news
2. **Better Naming**: Natural language names instead of keyword combinations
3. **Quality Filtering**: Filters out noise topics (Polish declensions, company names)
4. **Cost Effective**: GPT-4o-mini costs ~$0.001 per run

---

## Future Enhancements

### Planned Features

#### 1. **Dynamic Topic Tracking**
Track how topics evolve over time:
```python
# Topics over time (BERTopic feature)
topics_over_time = modeler.model.topics_over_time(
    documents, timestamps, nr_bins=30
)
```

#### 2. **Multi-Model LLM Support**
Support alternative LLM providers:
- Anthropic Claude
- Local models (Llama, Mistral)
- Azure OpenAI

#### 3. **Email/Slack Integration**
Automated delivery of trend summaries:
```python
# Send weekly email digest
def send_email_digest():
    trends = detector.calculate_trends(window_days=7)
    html = format_trends_for_output(trends, format='email')
    send_email(to="team@company.com", subject="Weekly Trends", body=html)
```

#### 4. **Interactive Dashboard**
Web UI for exploring trends:
- Trend timeline visualization
- Topic clustering map (t-SNE/UMAP projection)
- Article search by topic
- Customizable filters (date range, sources, growth rate)

#### 5. **Multi-Source Topic Comparison**
Compare topics across different source categories:
```python
# Marketing publications vs. Tech publications
marketing_topics = get_topics(sources=['AdAge', 'Marketing Week'])
tech_topics = get_topics(sources=['TechCrunch', 'The Verge'])
overlap = compare_topic_distributions(marketing_topics, tech_topics)
```

### Research Directions

- **Zero-shot Topic Labeling**: Use pre-trained models to classify topics without manual intervention
- **Cross-lingual Topic Alignment**: Align topics across different languages
- **Sentiment Analysis per Topic**: Track sentiment changes for each topic
- **Predictive Trending**: Predict which topics will trend before they peak

---

## Conclusion

The refactor from keyword-based to topic-based trend detection represents a fundamental shift in how the system understands content. By using semantic embeddings and clustering, we now detect **meaningful thematic trends** rather than just tracking word frequencies.

### Key Takeaways:

1. **BERTopic** provides semantic understanding that YAKE/spaCy cannot
2. **Named entity filtering** prevents noise from company/person names
3. **Multilingual embeddings** handle mixed-language sources
4. **Topic-based tracking** reveals actual trends, not just popular mentions

### Technical Decisions:

| Decision | Rationale |
|----------|-----------|
| BERTopic over LDA/LSA | Better topic coherence, modern embeddings |
| Multilingual model | Handles English + Polish sources |
| HDBSCAN over K-Means | No need to specify topic count, handles outliers |
| Sentence Transformers | State-of-the-art semantic embeddings |
| Hybrid BERTopic + LLM | BERTopic clusters, LLM provides context understanding |

---

## Appendix

### Dependencies Overview

```
# Core Topic Modeling
bertopic>=0.16.0          # Topic modeling framework
sentence-transformers>=2.2.0  # Semantic embeddings
umap-learn>=0.5.5         # Dimensionality reduction
hdbscan>=0.8.33           # Density-based clustering
scikit-learn>=1.3.0       # c-TF-IDF, utilities

# LLM Enhancement
openai>=1.0.0             # GPT-4o-mini for trend analysis

# Scraping
scrapy>=2.11.0
beautifulsoup4>=4.12.0
requests>=2.31.0
feedparser>=6.0.10

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0

# API
fastapi>=0.104.0
uvicorn>=0.24.0

# Utilities
pyyaml>=6.0.0
schedule>=1.2.0
pandas>=2.1.0
loguru>=0.7.0
```

### Contact & Support

For questions or issues:
- GitHub Issues: [Repository URL]
- Email: [Support Email]
- Documentation: This file

---

**Last Updated**: December 9, 2025
**Version**: 2.1 (LLM-Enhanced)
**Status**: Production Ready ✅
