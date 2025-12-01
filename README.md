# Ad Trends Monitor

Monitor advertising industry trends from public sources (blogs, RSS feeds) and identify emerging topics using NLP and trend analysis.

## Features

- **RSS Feed Monitoring**: Automatically fetch articles from RSS feeds
- **Keyword Extraction**: Multi-method keyword extraction (YAKE, spaCy NER)
- **Trend Detection**: Identify trending, emerging, and declining topics
- **REST API**: FastAPI-based API for accessing trends and articles
- **SQLite Database**: Local storage with deduplication
- **Automated Scheduling**: Periodic scraping with configurable intervals

## Project Structure

```
ad-trends-monitor/
├── src/
│   ├── scrapers/         # RSS fetcher and web scrapers
│   ├── processors/       # Text processing and keyword extraction
│   ├── analyzers/        # Trend detection and analysis
│   ├── storage/          # Database models and operations
│   ├── api/              # FastAPI routes
│   └── config.py         # Configuration
├── data/
│   ├── sources.yaml      # List of sources to monitor
│   └── trends.db         # SQLite database (created automatically)
├── logs/                 # Application logs
├── main.py               # Main scheduler
└── requirements.txt      # Python dependencies
```

## Quick Start

### Szybkie uruchomienie (jeden terminal)

```bash
# 1. Stwórz środowisko wirtualne
python3 -m venv venv  # macOS/Linux
# lub: python -m venv venv  # Windows
source venv/bin/activate  # Linux/Mac
# lub: venv\Scripts\activate  # Windows

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Pobierz model spaCy dla języka polskiego (około 573 MB)
python3 -m spacy download pl_core_news_lg

# 4. Zainicjuj bazę danych
python3 main.py --init-db

# 5. Załaduj źródła z YAML do bazy
python3 main.py --init-sources

# 6. Uruchom pierwszy scraping (test)
python3 main.py --once

# 7. Uruchom API w osobnym oknie terminala
uvicorn src.api.routes:app --reload --port 8000
```

Otwórz przeglądarkę: **http://localhost:8000/docs** aby zobaczyć dokumentację API.

### Alternatywnie: Docker

```bash
# Zbuduj i uruchom całą aplikację w jednym kroku
docker-compose up --build

# API dostępne na: http://localhost:8000/docs
```

## Szczegółowa instalacja

### 1. Stwórz środowisko wirtualne

```bash
python3 -m venv venv  # macOS/Linux
# lub: python -m venv venv  # Windows
source venv/bin/activate  # Linux/Mac
# lub: venv\Scripts\activate  # Windows
```

### 2. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

**Uwaga**: Instalacja może potrwać kilka minut ze względu na biblioteki NLP (spaCy, gensim).

### 3. Pobierz model spaCy

```bash
python -m spacy download pl_core_news_lg
```

Ten model (około 800MB) jest wymagany do analizy tekstu w języku polskim.

### 4. Konfiguracja środowiska (opcjonalnie)

```bash
cp .env.example .env
```

Edytuj plik `.env` aby zmienić ustawienia:
- Interval scrapingu
- Limity artykułów
- Parametry detekcji trendów

Plik `data/sources.yaml` już zawiera 20 gotowych źródeł RSS. Możesz go edytować aby dodać własne źródła.

## Użycie

### 1. Inicjalizacja bazy danych

```bash
python main.py --init-db
```

Tworzy tabele w bazie SQLite (`data/trends.db`).

### 2. Załadowanie źródeł

```bash
python main.py --init-sources
```

Ładuje źródła z pliku `data/sources.yaml` do bazy danych.

### 3. Uruchomienie scrapingu

#### Tryb testowy (jednorazowo)

```bash
python main.py --once
```

Wykonuje jeden cykl scrapingu i kończy działanie. Użyteczne do testowania.

#### Tryb ciągły (scheduler)

```bash
python main.py
```

Uruchamia scheduler, który:
- Wykonuje scraping natychmiast
- Planuje kolejne uruchomienia co N godzin (domyślnie: 6h)
- Działa w nieskończoność (zatrzymaj przez Ctrl+C)

**Logi zapisywane są w**: `logs/ad_trends_YYYY-MM-DD.log`

### 4. Uruchomienie API

W osobnym oknie terminala:

```bash
# Tryb development z hot reload
uvicorn src.api.routes:app --reload --port 8000

# Tryb produkcyjny
uvicorn src.api.routes:app --host 0.0.0.0 --port 8000
```

**Dokumentacja API**: http://localhost:8000/docs
**Alternatywna dokumentacja**: http://localhost:8000/redoc

### 5. Przykładowe zapytania API

```bash
# Pobierz trendy z ostatnich 30 dni
curl http://localhost:8000/trends?days=30&limit=20

# Wyszukaj artykuły po słowie kluczowym
curl http://localhost:8000/articles?keyword=marketing&limit=10

# Statystyki systemu
curl http://localhost:8000/stats

# Health check
curl http://localhost:8000/health
```

## API Endpoints

### Get Trends
```bash
GET /trends?days=30&limit=20
```

Returns keywords with growing frequency.

### Get Emerging Keywords
```bash
GET /trends/emerging?days=30&limit=20
```

Returns completely new keywords.

### Get Declining Keywords
```bash
GET /trends/declining?days=30&limit=20
```

Returns keywords decreasing in frequency.

### Get Top Keywords
```bash
GET /keywords?limit=50
```

Returns most frequent keywords.

### Search Articles
```bash
GET /articles?keyword=marketing&limit=20
```

Search articles by keyword.

### List Sources
```bash
GET /sources
```

List all monitored sources.

### Add Source
```bash
POST /sources
{
  "name": "Example Blog",
  "url": "https://example.com/feed",
  "source_type": "rss"
}
```

### Get Statistics
```bash
GET /stats
```

Returns system statistics.

## Configuration

Edit `.env` or modify `src/config.py`:

- `DATABASE_URL`: Database connection string
- `SCRAPE_INTERVAL_HOURS`: Hours between scraping runs (default: 6)
- `MAX_ARTICLES_PER_SOURCE`: Max articles to fetch per source (default: 50)
- `MIN_ARTICLE_LENGTH`: Minimum article length in words (default: 200)
- `TREND_WINDOW_DAYS`: Analysis window for trends (default: 30)
- `TOP_KEYWORDS_COUNT`: Keywords to extract per article (default: 20)
- `REQUEST_DELAY_SECONDS`: Delay between requests (default: 2)

## Docker

### Uruchomienie z Docker Compose (zalecane)

```bash
# Zbuduj i uruchom w tle
docker-compose up --build -d

# Zobacz logi
docker-compose logs -f

# Zatrzymaj
docker-compose down
```

Docker Compose automatycznie:
- Buduje kontener aplikacji
- Uruchamia scheduler i API w jednym kontenerze
- Eksponuje API na porcie 8000
- Montuje katalogi `./data` i `./logs` dla trwałości danych
- Automatycznie restartuje przy awarii

**API dostępne na**: http://localhost:8000/docs

### Ręczne uruchomienie Docker

```bash
# Zbuduj obraz
docker build -t ad-trends-monitor .

# Uruchom kontener
docker run -d \
  --name ad-trends \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  ad-trends-monitor
```

### Przydatne komendy Docker

```bash
# Zobacz logi kontenera
docker logs -f ad-trends-monitor

# Wejdź do kontenera
docker exec -it ad-trends-monitor bash

# Zatrzymaj kontener
docker stop ad-trends-monitor

# Usuń kontener
docker rm ad-trends-monitor
```

## Development

### Run tests

```bash
pytest tests/ -v --cov=src
```

### Code style

```bash
black src/ tests/
flake8 src/ tests/
```

## Trend Detection Algorithm

The trend detector compares keyword frequencies between two time periods:

1. **Current Period**: Last N days (default: 30)
2. **Previous Period**: N days before that

**Growth Rate** = (Current Count - Previous Count) / Previous Count

Keywords with growth rate > 20% are marked as **trending**.

## Keyword Extraction Methods

1. **YAKE**: Unsupervised keyword extraction
2. **spaCy**: Named Entity Recognition (NER) + noun chunks
3. **Combined**: Aggregates results from all methods

## License

MIT License - Open source and free to use.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## Rozwiązywanie problemów

### Problem: "spaCy model not found"

```bash
# Upewnij się, że model jest pobrany
python -m spacy download pl_core_news_lg

# Sprawdź zainstalowane modele
python -m spacy info
```

### Problem: "Database locked"

SQLite może mieć problemy z współbieżnością. Rozwiązania:
1. Nie uruchamiaj wielu instancji `main.py` jednocześnie
2. Dla produkcji rozważ PostgreSQL (instrukcje w `docker-compose.yml`)

### Problem: "Too many requests" / Rate limiting

```bash
# Zwiększ opóźnienie między requestami w .env
REQUEST_DELAY_SECONDS=5
```

### Problem: Brak artykułów w bazie

1. Sprawdź czy źródła zostały załadowane: `curl http://localhost:8000/sources`
2. Zobacz logi: `tail -f logs/ad_trends_*.log`
3. Niektóre RSS feedy mogą blokować boty - sprawdź User-Agent w konfiguracji

## Panel Administracyjny

Projekt zawiera w pełni funkcjonalny panel administracyjny w HTML/CSS/JavaScript.

### Dostęp do panelu

Po uruchomieniu FastAPI, panel dostępny jest pod adresem:

**http://localhost:8000/admin/**

### Funkcje panelu

- **Dashboard** (`/admin/index.html`)
  - Statystyki systemu
  - Ręczne uruchamianie scrapingu
  - Top trendy i ostatnie artykuły

- **Źródła** (`/admin/sources.html`)
  - Dodawanie nowych źródeł RSS
  - Edycja istniejących źródeł
  - Usuwanie źródeł (soft delete)
  - Filtrowanie aktywnych/nieaktywnych

- **Artykuły** (`/admin/articles.html`)
  - Wyszukiwanie po słowach kluczowych
  - Filtrowanie po źródle i dacie
  - Linkowanie do oryginalnych artykułów

- **Trendy** (`/admin/trends.html`)
  - Rosnące słowa kluczowe (wzrost > 20%)
  - Nowe słowa kluczowe
  - Malejące słowa kluczowe
  - Top 50 najpopularniejszych słów

Szczegółowa dokumentacja: `admin-panel/README.md`

## Roadmap

### Faza 2
- [ ] Blog scraper (trafilatura + BeautifulSoup)
- [ ] Sitemap crawler
- [ ] Zaawansowana deduplikacja (fuzzy matching)

### Faza 3
- [ ] Topic modeling (LDA z gensim)
- [ ] Sentiment analysis
- [x] Web dashboard - **GOTOWE!** (HTML/CSS/JavaScript)

### Faza 4
- [ ] Export do CSV/JSON/Excel z panelu
- [ ] Email/Slack alerty dla nowych trendów
- [ ] PostgreSQL support
- [ ] Elasticsearch dla full-text search
- [ ] Caching (Redis)

## Licencja

MIT License - Projekt open source, darmowy do użytku komercyjnego i niekomercyjnego.

## Contributing

Kontrybucje mile widziane! Proszę:

1. Forkuj repozytorium
2. Stwórz branch dla nowej funkcji (`git checkout -b feature/nowa-funkcja`)
3. Dodaj testy dla nowych funkcji
4. Commituj zmiany (`git commit -m 'Dodaj nową funkcję'`)
5. Push do brancha (`git push origin feature/nowa-funkcja`)
6. Otwórz Pull Request

## Wsparcie

Dla pytań i problemów, proszę otworzyć GitHub Issue.

## Autorzy

Projekt stworzony z wykorzystaniem Claude Code na podstawie specyfikacji IMPL.md.
