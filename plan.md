# Plan implementacji ulepszeń Trend Analyzer dla Claude Code

## Kontekst projektu

Projekt to POC analizy trendów z artykułów RSS. Obecny pipeline:
```
RSS → Scrape → Clean → BERTopic → LLM Validation → Trend Detection → Output
```

Celem jest poprawa jakości wykrywania trendów poprzez serię ulepszeń.

---

## FAZA 1: Quick wins (fundament)

### Task 1.1: Deduplication artykułów

**Cel**: Usunięcie duplikatów przed clusteringiem

**Implementacja**:
1. Znajdź miejsce w kodzie gdzie artykuły są zbierane przed przekazaniem do BERTopic
2. Dodaj funkcję `deduplicate_articles()`:
   - Użyj fuzzy matching na tytułach (biblioteka `rapidfuzz`, threshold 85%)
   - Dla duplikatów zachowaj artykuł z najbardziej wiarygodnego źródła
   - Loguj ile duplikatów usunięto
3. Dodaj testy jednostkowe

**Pliki do modyfikacji**: prawdopodobnie `topic_extractor.py` lub podobny

### Task 1.2: Cache embeddings

**Cel**: Nie przeliczaj embeddings dla tych samych artykułów

**Implementacja**:
1. Stwórz `EmbeddingCache` class:
   - Klucz: hash(url + content[:500])
   - Wartość: embedding vector
   - Storage: SQLite tabela `embedding_cache`
2. Przed wywołaniem SentenceTransformer sprawdź cache
3. Po obliczeniu zapisz do cache
4. Dodaj TTL (np. 90 dni) i cleanup stale entries

### Task 1.3: Dostrojenie parametrów BERTopic

**Cel**: Silniejsze sygnały, mniej szumu

**Implementacja**:
1. Znajdź konfigurację BERTopic (prawdopodobnie w config lub bezpośrednio w kodzie)
2. Zmień parametry:
   ```python
   min_cluster_size = 10  # było 8
   min_samples = 3        # dodaj jeśli brak
   ```
3. Dodaj te parametry do pliku konfiguracyjnego jeśli jeszcze nie są konfigurowalne

---

## FAZA 2: Jakość danych wejściowych

### Task 2.1: Full article scraping

**Cel**: Pobieranie pełnej treści zamiast tylko RSS summary

**Implementacja**:
1. Dodaj zależność: `trafilatura` (lepsza od newspaper3k)
2. Stwórz `FullContentScraper` class:
   ```python
   def fetch_full_content(url: str, rss_content: str) -> str:
       if len(rss_content) >= 500:
           return rss_content
       try:
           full = trafilatura.fetch_url(url)
           extracted = trafilatura.extract(full)
           return extracted if extracted else rss_content
       except:
           return rss_content
   ```
3. Zintegruj z istniejącym RSS fetcher
4. Dodaj rate limiting (1 req/sec per domain)
5. Dodaj timeout i retry logic

### Task 2.2: Source credibility weighting

**Cel**: Ważniejsze źródła mają większy wpływ

**Implementacja**:
1. Stwórz plik `config/source_weights.yaml`:
   ```yaml
   high_credibility:  # weight 1.5
     - techcrunch.com
     - wired.com
     - marketingweek.com
   medium_credibility:  # weight 1.0
     - default
   low_credibility:  # weight 0.5
     - aggregators
   blacklist:  # weight 0, ignoruj
     - content-farm.com
   ```
2. Stwórz `SourceWeightManager` class
3. Użyj wag przy:
   - Liczeniu artykułów w trendzie (weighted_count)
   - Decyzji który duplikat zachować

### Task 2.3: Source blacklist dla agregatorów

**Cel**: Filtrowanie źródeł które tylko kopiują treść

**Implementacja**:
1. Dodaj do konfiguracji listę agregatorów do ignorowania
2. Filtruj na etapie RSS fetch (przed jakimkolwiek przetwarzaniem)
3. Loguj odfiltrowane źródła

---

## FAZA 3: Temporal intelligence

### Task 3.1: Time-weighted embeddings

**Cel**: Nowsze artykuły mają większy wpływ na clustering

**Implementacja**:
1. Dodaj funkcję obliczającą wagę czasową:
   ```python
   def time_weight(published_date: datetime, lambda_decay: float = 0.05) -> float:
       days_ago = (datetime.now() - published_date).days
       return math.exp(-lambda_decay * days_ago)
   ```
2. Zmodyfikuj proces przed HDBSCAN:
   - Przemnóż embeddings przez time_weight
   - Lub użyj sample_weight w HDBSCAN jeśli wspiera
3. Dodaj `lambda_decay` do konfiguracji

### Task 3.2: Multi-period trend analysis

**Cel**: Analiza więcej niż 2 okresów dla lepszego lifecycle tracking

**Implementacja**:
1. Zmień `TrendDetector` aby obsługiwał N okresów (domyślnie 4 x 2 tygodnie = 8 tygodni)
2. Dodaj obliczanie:
   ```python
   velocity = growth_rate_current - growth_rate_previous  # przyspieszenie
   ```
3. Dodaj klasyfikację lifecycle:
   ```python
   stages = {
       'emerging': velocity > 0.3 and count < 10,
       'growing': velocity > 0 and growth_rate > 0.2,
       'peak': velocity < 0 and growth_rate > 0,
       'declining': growth_rate < -0.2,
       'stable': abs(growth_rate) < 0.1
   }
   ```
4. Dodaj stage do outputu trendu

### Task 3.3: Trend history tracking

**Cel**: Śledzenie jak trend ewoluuje w czasie

**Implementacja**:
1. Rozszerz schemat bazy danych:
   ```sql
   CREATE TABLE trend_snapshots (
       trend_id INTEGER,
       snapshot_date DATE,
       article_count INTEGER,
       growth_rate REAL,
       stage TEXT,
       centroid_embedding BLOB
   );
   ```
2. Przy każdym renderze zapisuj snapshot
3. Dodaj endpoint/funkcję do pobierania historii trendu

---

## FAZA 4: Zaawansowana analityka

### Task 4.1: Topic merging (podobne tematy)

**Cel**: Łączenie tematów które są semantycznie blisko

**Implementacja**:
1. Po BERTopic clustering, oblicz odległość między centroidami
2. Jeśli cosine_similarity > 0.85, zaproponuj merge
3. Użyj LLM do decyzji czy mergować:
   ```
   "Are these two topics about the same trend?"
   Topic A: [keywords]
   Topic B: [keywords]
   ```
4. Zachowaj mapping merged_topics dla spójności

### Task 4.2: Cross-topic correlation

**Cel**: Wykrywanie powiązań między trendami

**Implementacja**:
1. Stwórz `TopicCorrelationAnalyzer`:
   - Oblicz source overlap (te same źródła piszą o obu)
   - Oblicz temporal correlation (rosną/maleją razem)
   - Oblicz semantic proximity (odległość centroidów)
2. Stwórz graf korelacji:
   ```python
   correlations = {
       ('ai_marketing', 'privacy_regulations'): {
           'source_overlap': 0.4,
           'temporal_correlation': 0.7,
           'semantic_proximity': 0.3
       }
   }
   ```
3. Dodaj do outputu "related trends"

### Task 4.3: Semantic drift detection

**Cel**: Wykrywanie ewolucji znaczenia trendu

**Implementacja**:
1. Przy każdym renderze zapisuj centroid trendu
2. Porównuj z poprzednim centroidem:
   ```python
   drift = 1 - cosine_similarity(current_centroid, previous_centroid)
   if drift > 0.3:
       flag_as_evolving()
   ```
3. Użyj LLM do opisania jak trend się zmienił:
   ```
   "Topic shifted from [old_keywords] to [new_keywords]. Describe the evolution."
   ```

---

## FAZA 5: Output i monitoring (dashboard juz jest. w admin-panel wiec zrob to tak jak jest a tymi wskazówkami się tylko inspiruj)

### Task 5.1: Dashboard data API

**Cel**: Przygotowanie danych dla przyszłego dashboardu

**Implementacja**:
1. Stwórz `TrendAPIFormatter` zwracający JSON:
   ```python
   {
       "trends": [...],
       "correlations": {...},
       "timeline": [...],
       "metadata": {
           "generated_at": "...",
           "articles_processed": 1234,
           "sources_count": 45
       }
   }
   ```
2. Zapisuj do pliku `output/trends_api.json`

### Task 5.2: Alerting dla nowych trendów

**Cel**: Powiadomienia o emerging trends

**Implementacja**:
1. Stwórz `TrendAlertManager`:
   - Wykryj nowe trendy (stage='emerging', confidence > 0.8)
   - Wykryj nagłe skoki (velocity > 0.5)
2. Zintegruj z istniejącym systemem powiadomień (jeśli jest) lub przygotuj webhook

### Task 5.3: Quality metrics i logging

**Cel**: Monitorowanie jakości systemu

**Implementacja**:
1. Dodaj metryki:
   - Liczba artykułów przed/po deduplication
   - Procent artykułów odrzuconych przez LLM jako "news not trend"
   - Średni confidence score
   - Cache hit rate dla embeddings
2. Loguj do pliku `logs/quality_metrics.json`
3. Dodaj alerting jeśli metryki spadną poniżej thresholdu

---

## Kolejność implementacji (rekomendowana)

```
Tydzień 1: Faza 1 (quick wins) - fundamenty
Tydzień 2: Faza 2 (jakość danych) - lepsze inputy
Tydzień 3: Faza 3 (temporal) - inteligencja czasowa
Tydzień 4: Faza 4 (analityka) - zaawansowane features
```
