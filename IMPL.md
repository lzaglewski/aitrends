# Ad Trends Monitor - Instrukcje dla Claude Code

## Cel projektu

Zbuduj aplikację Python do monitorowania publicznych źródeł (blogi, RSS, strony www) agencji reklamowych i identyfikacji trendów w branży. Aplikacja ma być w pełni open source i bezkosztowa.

---

## Architektura

```
ad-trends-monitor/
├── src/
│   ├── __init__.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── blog_scraper.py      # Scraping blogów agencji
│   │   ├── rss_fetcher.py       # Pobieranie RSS
│   │   └── sitemap_crawler.py   # Crawling sitemap
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── text_extractor.py    # Ekstrakcja treści z HTML
│   │   ├── nlp_processor.py     # Analiza NLP
│   │   └── keyword_extractor.py # Ekstrakcja słów kluczowych
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── trend_detector.py    # Wykrywanie trendów
│   │   └── topic_modeler.py     # Modelowanie tematów
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py          # Operacje na bazie
│   │   └── models.py            # Modele SQLAlchemy
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # FastAPI endpoints
│   └── config.py                # Konfiguracja
├── data/
│   ├── sources.yaml             # Lista źródeł do monitorowania
│   └── stopwords_pl.txt         # Polskie stopwords
├── tests/
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── main.py
```

---

## Wymagania techniczne

### Biblioteki Python (requirements.txt)

```
# Scraping
scrapy>=2.11.0
beautifulsoup4>=4.12.0
requests>=2.31.0
trafilatura>=1.6.0
newspaper3k>=0.2.8
feedparser>=6.0.10
lxml>=4.9.0

# NLP
spacy>=3.7.0
gensim>=4.3.0
scikit-learn>=1.3.0
yake>=0.4.8
nltk>=3.8.0

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0

# API
fastapi>=0.104.0
uvicorn>=0.24.0

# Utils
pyyaml>=6.0.0
schedule>=1.2.0
python-dotenv>=1.0.0
pandas>=2.1.0
tqdm>=4.66.0
```

### Model językowy

Po instalacji spaCy, pobierz polski model:
```bash
python -m spacy download pl_core_news_lg
```

---

## Szczegółowa implementacja

### 1. Konfiguracja (src/config.py)

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/trends.db"
    SCRAPE_INTERVAL_HOURS: int = 6
    MAX_ARTICLES_PER_SOURCE: int = 50
    MIN_ARTICLE_LENGTH: int = 200
    TREND_WINDOW_DAYS: int = 30
    TOP_KEYWORDS_COUNT: int = 20
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 2. Modele bazy danych (src/storage/models.py)

Stwórz modele SQLAlchemy:

- **Source**: id, name, url, source_type (blog/rss/sitemap), last_scraped, active
- **Article**: id, source_id, url, title, content, published_date, scraped_date, word_count
- **Keyword**: id, article_id, keyword, score, extraction_method
- **Trend**: id, keyword, count, period_start, period_end, growth_rate

Dodaj indeksy na: url (unique), published_date, keyword.

### 3. Scraper blogów (src/scrapers/blog_scraper.py)

Użyj `trafilatura` jako głównej biblioteki do ekstrakcji:

```python
import trafilatura
from trafilatura.settings import use_config

def scrape_article(url: str) -> dict:
    """
    Pobierz artykuł z URL.
    
    Returns:
        dict z kluczami: title, content, date, author
    """
    # Konfiguracja trafilatura
    config = use_config()
    config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
    
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    
    # Ekstrakcja z metadanymi
    result = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        output_format='json',
        with_metadata=True
    )
    
    return json.loads(result) if result else None
```

Dodaj:
- Obsługę robots.txt (biblioteka `robotexclusionrulesparser`)
- Rate limiting (1 request/2 sekundy na domenę)
- Retry logic z exponential backoff
- User-Agent rotation

### 4. RSS Fetcher (src/scrapers/rss_fetcher.py)

```python
import feedparser

def fetch_rss_feed(feed_url: str) -> list[dict]:
    """
    Pobierz artykuły z RSS feed.
    """
    feed = feedparser.parse(feed_url)
    
    articles = []
    for entry in feed.entries:
        articles.append({
            'title': entry.get('title', ''),
            'url': entry.get('link', ''),
            'summary': entry.get('summary', ''),
            'published': entry.get('published_parsed'),
        })
    
    return articles
```

### 5. Ekstraktor słów kluczowych (src/processors/keyword_extractor.py)

Implementuj trzy metody i agreguj wyniki:

#### a) YAKE (unsupervised)
```python
import yake

def extract_yake(text: str, language: str = 'pl', max_keywords: int = 20):
    kw_extractor = yake.KeywordExtractor(
        lan=language,
        n=3,  # max n-gram size
        dedupLim=0.7,
        top=max_keywords
    )
    return kw_extractor.extract_keywords(text)
```

#### b) TF-IDF
```python
from sklearn.feature_extraction.text import TfidfVectorizer

def extract_tfidf(documents: list[str], max_features: int = 100):
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 3),
        stop_words=load_polish_stopwords()
    )
    tfidf_matrix = vectorizer.fit_transform(documents)
    # Zwróć top keywords per document
```

#### c) spaCy NER + noun chunks
```python
import spacy

nlp = spacy.load('pl_core_news_lg')

def extract_entities_and_nouns(text: str):
    doc = nlp(text)
    
    # Named entities
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    
    # Noun chunks
    nouns = [chunk.text for chunk in doc.noun_chunks]
    
    return entities, nouns
```

### 6. Detektor trendów (src/analyzers/trend_detector.py)

```python
import pandas as pd
from datetime import datetime, timedelta

class TrendDetector:
    def __init__(self, db_session):
        self.session = db_session
    
    def calculate_trends(self, window_days: int = 30) -> list[dict]:
        """
        Oblicz trendy na podstawie częstotliwości słów kluczowych.
        
        Metoda:
        1. Pobierz wszystkie keywords z ostatnich window_days
        2. Pogrupuj po keyword i policz wystąpienia
        3. Porównaj z poprzednim okresem
        4. Oblicz growth_rate = (current - previous) / previous
        5. Oznacz jako trend jeśli growth_rate > 0.2 (20% wzrost)
        """
        
        current_period = self._get_keyword_counts(
            start=datetime.now() - timedelta(days=window_days),
            end=datetime.now()
        )
        
        previous_period = self._get_keyword_counts(
            start=datetime.now() - timedelta(days=window_days*2),
            end=datetime.now() - timedelta(days=window_days)
        )
        
        trends = []
        for keyword, count in current_period.items():
            prev_count = previous_period.get(keyword, 1)
            growth = (count - prev_count) / prev_count
            
            trends.append({
                'keyword': keyword,
                'count': count,
                'growth_rate': growth,
                'is_trending': growth > 0.2
            })
        
        return sorted(trends, key=lambda x: x['growth_rate'], reverse=True)
```

### 7. Topic Modeling (src/analyzers/topic_modeler.py)

Użyj LDA z gensim:

```python
from gensim import corpora
from gensim.models import LdaMulticore

class TopicModeler:
    def __init__(self, num_topics: int = 10):
        self.num_topics = num_topics
        self.dictionary = None
        self.model = None
    
    def train(self, documents: list[list[str]]):
        """
        Trenuj model LDA.
        
        Args:
            documents: Lista dokumentów, każdy jako lista tokenów
        """
        self.dictionary = corpora.Dictionary(documents)
        
        # Filtruj ekstremalne wartości
        self.dictionary.filter_extremes(no_below=5, no_above=0.5)
        
        corpus = [self.dictionary.doc2bow(doc) for doc in documents]
        
        self.model = LdaMulticore(
            corpus,
            num_topics=self.num_topics,
            id2word=self.dictionary,
            passes=10,
            workers=4
        )
    
    def get_topics(self) -> list[tuple]:
        """Zwróć tematy z top słowami."""
        return self.model.print_topics(num_words=10)
    
    def get_document_topics(self, tokens: list[str]) -> list[tuple]:
        """Przypisz dokument do tematów."""
        bow = self.dictionary.doc2bow(tokens)
        return self.model.get_document_topics(bow)
```

### 8. API (src/api/routes.py)

FastAPI endpoints:

```python
from fastapi import FastAPI, Depends, Query
from datetime import datetime

app = FastAPI(title="Ad Trends Monitor")

@app.get("/trends")
def get_trends(
    days: int = Query(30, description="Okres analizy w dniach"),
    limit: int = Query(20, description="Liczba trendów do zwrócenia")
):
    """Pobierz aktualne trendy."""
    pass

@app.get("/keywords")
def get_top_keywords(
    start_date: datetime = None,
    end_date: datetime = None,
    limit: int = 50
):
    """Pobierz najczęstsze słowa kluczowe."""
    pass

@app.get("/topics")
def get_topics():
    """Pobierz zidentyfikowane tematy (topic modeling)."""
    pass

@app.get("/articles")
def get_articles(
    keyword: str = None,
    source_id: int = None,
    limit: int = 20
):
    """Wyszukaj artykuły."""
    pass

@app.get("/sources")
def get_sources():
    """Lista monitorowanych źródeł."""
    pass

@app.post("/sources")
def add_source(url: str, name: str, source_type: str):
    """Dodaj nowe źródło do monitorowania."""
    pass

@app.get("/stats")
def get_stats():
    """Statystyki systemu."""
    pass
```

### 9. Główny scheduler (main.py)

```python
import schedule
import time
from src.scrapers import BlogScraper, RSSFetcher
from src.processors import KeywordExtractor
from src.analyzers import TrendDetector
from src.storage import Database
from src.config import settings

def run_scraping_job():
    """Główne zadanie scrapingu."""
    db = Database()
    scraper = BlogScraper()
    extractor = KeywordExtractor()
    
    sources = db.get_active_sources()
    
    for source in sources:
        articles = scraper.scrape_source(source)
        
        for article in articles:
            # Zapisz artykuł
            article_id = db.save_article(article)
            
            # Ekstrahuj keywords
            keywords = extractor.extract_all(article['content'])
            db.save_keywords(article_id, keywords)
    
    # Przelicz trendy
    detector = TrendDetector(db.session)
    trends = detector.calculate_trends()
    db.save_trends(trends)

def main():
    # Uruchom raz na start
    run_scraping_job()
    
    # Zaplanuj cykliczne uruchamianie
    schedule.every(settings.SCRAPE_INTERVAL_HOURS).hours.do(run_scraping_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
```

---

## Lista źródeł do monitorowania (data/sources.yaml)

```yaml
sources:
  # Polskie agencje reklamowe
  - name: "Publicis Groupe Polska"
    url: "https://www.publicisgroupe.pl/blog"
    type: blog
    
  - name: "VMLY&R Poland"
    url: "https://www.vmlyr.com/pl/insights"
    type: blog
    
  - name: "Saatchi & Saatchi"
    url: "https://saatchi.pl/blog"
    type: blog
    
  # Branżowe portale
  - name: "Wirtualne Media"
    url: "https://www.wirtualnemedia.pl/rss/wirtualnemedia_reklama.xml"
    type: rss
    
  - name: "Marketing przy Kawie"
    url: "https://marketingprzykawie.pl/feed/"
    type: rss
    
  - name: "NowyMarketing"
    url: "https://nowymarketing.pl/feed"
    type: rss
    
  - name: "Brief.pl"
    url: "https://brief.pl/feed/"
    type: rss
    
  # Międzynarodowe źródła
  - name: "AdAge"
    url: "https://adage.com/feed"
    type: rss
    
  - name: "Marketing Week"
    url: "https://www.marketingweek.com/feed/"
    type: rss
    
  - name: "The Drum"
    url: "https://www.thedrum.com/feeds/all"
    type: rss
```

---

## Docker (docker-compose.yml)

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/trends.db
    restart: unless-stopped
    
  # Opcjonalnie: PostgreSQL dla produkcji
  # db:
  #   image: postgres:15
  #   environment:
  #     POSTGRES_DB: adtrends
  #     POSTGRES_USER: user
  #     POSTGRES_PASSWORD: password
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
```

---

## Polecenia do uruchomienia

```bash
# 1. Stwórz środowisko
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub: venv\Scripts\activate  # Windows

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Pobierz model spaCy
python -m spacy download pl_core_news_lg

# 4. Zainicjuj bazę danych
python -c "from src.storage.database import init_db; init_db()"

# 5. Uruchom scraping (jednorazowo)
python main.py --once

# 6. Uruchom API
uvicorn src.api.routes:app --reload --port 8000

# 7. Lub uruchom wszystko przez Docker
docker-compose up --build
```

---

## Dodatkowe uwagi

### Obsługa błędów
- Każdy scraper musi mieć try/except i logowanie błędów
- Użyj `loguru` lub `structlog` do logowania
- Zapisuj failed URLs do osobnej tabeli do późniejszego retry

### Rate limiting
- Implementuj delay między requestami (min 2 sekundy)
- Użyj `ratelimit` decorator
- Respektuj Crawl-delay z robots.txt

### Deduplikacja
- Hashuj content artykułów (SHA256)
- Sprawdzaj przed zapisem czy artykuł już istnieje
- Aktualizuj istniejące zamiast duplikować

### Rozszerzenia (opcjonalne)
1. **Sentiment analysis** - dodaj analizę sentymentu artykułów
2. **Embeddingi** - użyj sentence-transformers do semantic search
3. **Alerty** - powiadomienia gdy pojawi się nowy trend
4. **Export** - eksport do CSV/JSON/n8n webhook

---

## Testowanie

Napisz testy jednostkowe dla:
- `test_blog_scraper.py` - mockuj requesty
- `test_keyword_extractor.py` - testuj na przykładowych tekstach
- `test_trend_detector.py` - testuj obliczenia growth_rate
- `test_api.py` - użyj TestClient z FastAPI

```bash
pytest tests/ -v --cov=src
```

---

## Priorytety implementacji

1. **Faza 1** (MVP): RSS fetcher + keyword extraction + SQLite storage
2. **Faza 2**: Blog scraper + trend detection + basic API
3. **Faza 3**: Topic modeling + dashboard + Docker
4. **Faza 4**: Rozszerzenia i optymalizacje