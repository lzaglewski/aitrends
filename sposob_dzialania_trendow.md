# Szczegółowy proces: Od pobrania artykułów do trendu

## 🔄 Pełny pipeline

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

---

## KROK 1: Pobieranie artykułów (RSS Fetcher) 📥

### Co pobieramy?
- **Maksymalnie**: 50 artykułów na źródło
- **Minimalnie**: 30 znaków tekstu (MIN_ARTICLE_LENGTH)
- **Delay**: 2 sekundy między żądaniami (rate limiting)
- **Timeout**: 30 sekund na żądanie

### Jakie dane?
```python
{
    'url': 'https://example.com/article',
    'title': 'AI Changes Marketing',
    'content': 'Full article text or summary...',  # Content lub Summary lub Description
    'published_date': datetime.now(),
    'author': 'John Doe'
}
```

### Gdzie dane?
- Próbujemy pobrać w kolejności: `content[0].value` → `summary` → `description`
- Każde źródło RSS ma swój format, system obsługuje wszystkie

---

## KROK 2: Czyszczenie tekstu (TopicExtractor) 🧹

### Co usuwamy?

| Element | Regex | Cel |
|---------|-------|-----|
| HTML tags | `<.*?>` | BeautifulSoup.get_text() |
| URLs | `http\S+\|www\S+` | Linki nie są treścią |
| Emaile | `\S+@\S+` | Prywatne dane |
| RSS artefakty | `appeared in\|via\|read more` | Boilerplate |
| Daty | `December 9\|Dec 9, 2025` | Metadane |
| Lata samotne | `\b\d{4}\b` | Metadane |
| Czasy | `\d{2}:\d{2}` | Metadane |
| Whitespace | `\s+` → ` ` | Normalizacja |

### Rezultat
```
Przed:
"AI Marketing <span>buzzword</span> - appeared in https://example.com
Date: December 9, 2025 15:30"

Po:
"AI Marketing buzzword"
```

### Wymóg dla Topic Modeling
- **Minimum 50 znaków** (TOPIC_MIN_DOCUMENT_LENGTH)
- Artykuły poniżej tego limitu są odrzucane

---

## KROK 3: BERTopic - Semantic Topic Modeling 🧠

### Faza 1: EMBEDDING - Zamiana tekstu na wektory

```
Tekst artykułu → SentenceTransformer → Wektor 384-wymiarowy
```

**Modele w zależności od języka:**
```python
multilingual → 'paraphrase-multilingual-MiniLM-L12-v2'  # Domyślnie
english      → 'all-MiniLM-L6-v2'                       # Szybciej
polish       → 'sdadas/mmlw-retrieval-roberta-base'     # Optimized
```

**Efekt**: Każdy artykuł to wektor liczb reprezentujący jego znaczenie (semantyka)

---

### Faza 2: DIMENSIONALITY REDUCTION - UMAP

```
384 wymiary → UMAP → 5 wymiarów
```

**Parametry:**
- `n_neighbors=15` - Ile najbliższych sąsiadów
- `n_components=5` - Wyjściowe wymiary
- `metric='cosine'` - Miara odległości

**Efekt**: Zmniejszenie szumu, zachowanie struktury semantycznej

---

### Faza 3: CLUSTERING - HDBSCAN

```
5-wymiarowe punkty → HDBSCAN → Grupy (topics)
```

**Parametry:**
```python
min_cluster_size = 8  # Minimum 8 artykułów w temacie (TOPIC_MIN_TOPIC_SIZE)
metric = 'euclidean'  # Odległość między punktami
cluster_selection_method = 'eom'  # End of moment
```

**Efekt**: Znajdujemy naturalne grupy artykułów o podobnym znaczeniu
- Artykuły bez grupy → topic -1 (outliers)

---

### Faza 4: REPRESENTATION - c-TF-IDF

```
Artykuły w grupie → CountVectorizer → Top słowa
```

**Jak działa:**
```python
# 1. N-gramy (kombinacje słów)
ngram_range = (1, 3)  # "ai", "content generation", "ai powered content"

# 2. Stopwords (usuwamy słowa bez sensu)
stopwords = ['the', 'a', 'and', ...] + polish_stopwords

# 3. Filtrowanie
min_df = 2      # Słowo w minimum 2 dokumentach
max_df = 0.8    # Słowo w max 80% dokumentów

# 4. Top 5 słów dla każdego tematu
top_n_words = 5
```

**Rezultat:**
```
Topic 0: ['ai', 'content', 'generation', 'advertising', 'automation']
Topic 1: ['privacy', 'cookies', 'tracking', 'gdpr', 'consent']
Topic 2: ['influencer', 'marketing', 'roi', 'analytics', 'performance']
```

---

## KROK 4: Filtrowanie Named Entity (Named Entity Filter) 🚫

### Co filtrujemy?

**1. Nazwy firm** (company_blacklist)
```python
Companies: google, facebook, meta, microsoft, openai, adobe, hubspot...
Brands: chatgpt, gemini, claude, copilot...
```

**2. Nazwy osób** (regex patterns)
```
"CEO John Doe"  → Matches: (ceo|cto|vp) \w+
"Mr. Smith"     → Matches: (mr|mrs|dr) \w+
```

**3. Akronimy** (uppercase)
```
Topic zawierający: "IBM" lub "GDPR" (ale nie "AI", "ROI", "SEO" - te są OK)
```

**4. Announcement patterns**
```
"Google announced..."    → Matches: \w+ (announced|launches|reveals)
"Facebook says..."       → Matches: (according to|says) \w+
```

### Rezultat
```
❌ Filtered out: ["Google AI Announcement"]
❌ Filtered out: ["CEO John Doe Strategy"]
✅ Kept: ["AI-Powered Content Generation"]
✅ Kept: ["Privacy Marketing Strategies"]
```

---

## KROK 5: LLM Enhancement - Validacja trendu (GPT-4o-mini) 🤖

### Prompt wysyłany do LLM

```
System Role: "You are an expert marketing and AI industry analyst"

Dane wejściowe:
1. Do 5 artykułów (limit kosztowy)
2. Pierwsze 200 znaków z każdego
3. BERTopic keywords (np. ['ai', 'content', 'generation', ...])

Pytanie do LLM:
"Analyze these marketing/AI articles clustered together.
Determine if they represent an emerging TREND (pattern across multiple contexts)
or just NEWS (single event/announcement)."
```

### Konkretny przykład promptu:

```markdown
Analyze these 5 marketing/AI industry articles that were clustered together:

1. **How AI is transforming content creation**
   AI tools like GPT-4o are enabling marketers to generate...

2. **Adobe launches GenAI features for creators**
   The marketing suite now includes AI-powered tools for...

3. **Generative AI adoption in marketing hits 40%**
   New survey shows marketers increasingly using AI for...

4. **How to use LLMs for personalized ad campaigns**
   With large language models, agencies can now create...

5. **The future of AI-assisted marketing workflows**
   Industry experts predict AI will transform how teams...

**BERTopic Keywords**: ai, content, generation, advertising, automation

**Task**: Determine if these articles represent an emerging TREND

**Instructions**:
1. If TREND: Provide trend name (3-6 words), description, 3-5 keywords, confidence
2. If NEWS: Explain why (single company, isolated event)

**Output Format** (JSON):
{
  "is_trend": true/false,
  "trend_name": "AI-Generated Content in Advertising" (if true),
  "description": "Major platforms integrating generative AI for ad creation" (if true),
  "keywords": ["ai", "content", "generation", ...] (if true),
  "confidence": 0.85 (if true),
  "reason": "Why not a trend" (if false)
}
```

### Parametry LLM

```python
model = "gpt-4o-mini"            # Najtańszy model
temperature = 0.3                # Niska = fokusowany, mniej randomowy
max_tokens = 500                 # Limit na odpowiedź
max_articles_per_topic = 5       # Cost control (~$0.12/month)
response_format = "json_object"  # Wymuszamy JSON
```

### Odpowiedź LLM

```json
{
  "is_trend": true,
  "trend_name": "AI-Powered Content Generation in Advertising",
  "description": "Major advertising platforms integrating generative AI for automated ad creation, copy generation, and personalization",
  "keywords": ["ai", "content", "generation", "personalization", "automation"],
  "confidence": 0.89
}
```

### Filtrowanie

- Jeśli `is_trend = false` → **Temat ODRZUCONY** (nie jest trendem)
- Jeśli `is_trend = true` → **Temat ZACHOWANY** z nazwą i opisem LLM

**Przykład odrzucenia:**
```json
{
  "is_trend": false,
  "reason": "This is a single announcement from Google about one product launch, not a broader industry trend"
}
```

---

## KROK 6: Trend Detection - Porównanie okresów 📊

### Porównanie: Last 30 days vs. Previous 30 days

```
Timeline:
├── Początek (60 dni temu)
├── Previous Period (30-60 dni temu)
├── Previous → Current boundary
└── Current Period (ostatnie 30 dni)
```

### Obliczanie trendu

```python
# Dla każdego tematu:
current_count = 18      # Artykuły w ostatnich 30 dniach
previous_count = 10     # Artykuły w poprzednich 30 dniach

# Growth Rate Formula
if previous_count > 0:
    growth_rate = (current_count - previous_count) / previous_count
    # (18 - 10) / 10 = 0.8 = +80%
else:
    # Temat nie istniał wcześniej
    growth_rate = 1.0  # +100% (new topic)

# Klasyfikacja
if growth_rate >= 0.2 and current_count >= 3:  # TREND_MIN_GROWTH_RATE = 20%
    status = "🔥 TRENDING"
elif previous_count == 0:
    status = "⭐ NEW"
elif growth_rate < -0.2:
    status = "⬇️ DECLINING"
else:
    status = "➡️ STABLE"
```

### Rezultat dla każdego tematu:

```python
{
    'topic_id': 42,
    'topic_name': 'AI-Powered Content Generation in Advertising',
    'top_words': ['ai', 'content', 'generation', 'automation', 'ads'],
    'current_count': 18,           # Artykuły w ostatnich 30 dniach
    'previous_count': 10,          # Artykuły w poprzednich 30 dniach
    'growth_rate': 0.8,            # +80%
    'is_trending': True,           # growth_rate >= 0.2
    'is_new': False,               # Istniał wcześniej
    'status': '⬆️ Rosnące',
    'period_start': datetime(...), # Początek Current Period
    'period_end': datetime(...)    # Koniec Current Period
}
```

---

## KROK 7: Ostateczny Trend - Forma i prezentacja 🎯

### Struktura finalnego trendu

```python
{
    'id': 42,                                          # Topic ID
    'name': 'AI-Powered Content Generation in Advertising',  # LLM name
    'description': 'Major platforms integrating generative AI...',  # LLM description
    'keywords': ['ai', 'content', 'generation', 'automation', 'ads'],
    'status': '🔥 Trending',                           # NEW / TRENDING / DECLINING
    'articles': 18,                                    # Current period count
    'previous_articles': 10,                           # Previous period count
    'growth_rate': 0.80,                               # +80%
    'growth_percentage': '80%',                        # Formatted
    'confidence': 0.89,                                # LLM confidence
    'bertopic_keywords': ['ai', 'content', 'gen...'],  # Original BERTopic
    'period': '30 days',
    'timestamp': '2025-12-09 15:30 UTC'
}
```

### Przykład z konsoli

```
================================================================================
🔥 MARKETING & AI TRENDS (30 days)
Generated: 2025-12-09 15:30 UTC
================================================================================

1. 🌟 AI-Powered Content Generation in Advertising
   Keywords: ai, content, generation, automation, advertising
   Articles: 18 (previous: 10) | Growth: +80%
   Confidence: 89% | Status: Rosnące
   Description: Major platforms integrating generative AI for ad creation
   ---------------------------------------------------------------------------

2. ⬆️ Privacy-First Marketing Strategies
   Keywords: privacy, cookies, tracking, consent, gdpr
   Articles: 15 (previous: 8) | Growth: +88%
   Confidence: 76% | Status: Rosnące
   Description: Industry shift toward cookieless tracking and consent management
   ---------------------------------------------------------------------------

3. 🌟 Influencer Marketing ROI Measurement
   Keywords: influencer, roi, analytics, measurement, performance
   Articles: 12 (previous: 0) | Growth: NEW
   Confidence: 82% | Status: Nowe
   Description: Focus on measuring and optimizing influencer campaign performance
   ---------------------------------------------------------------------------
```

---

## 📈 Czego się nauczyliśmy?

### Co jest trendem?
✅ **TREND**: Pattern across multiple articles/sources
✅ **TREND**: Industry-wide shift or adoption
✅ **TREND**: Technology or strategy gaining traction

### Co NIE jest trendem?
❌ **NEWS**: Single company announcement
❌ **NEWS**: One-off event
❌ **NEWS**: Personal names or brand announcements

### Jak zmierzyć trend?
1. **Frequency**: Musi być minimum 3 artykuły w okresie
2. **Growth**: Wzrost ≥ 20% vs. poprzedni okres
3. **Context**: LLM sprawdza czy to rzeczywisty trend
4. **Confidence**: Model podaje ocenę pewności (0-100%)

---

## 🎯 Podsumowanie: Ewolucja wersji

| Aspekt | v1.0 | v2.0 | v2.1 |
|--------|------|------|------|
| Metoda | Słowa kluczowe | BERTopic | BERTopic + LLM |
| Problem | "Google" (15x), "John Doe" (8x) | Tematy bez kontekstu | - |
| Rozwiązanie | - | Topic modeling | LLM validacja |
| Przykład | Google (15x) | Privacy + Marketing + Strategies | Privacy-First Marketing |
| Dokładność | 20% | 70% | 85%+ |
| Koszt | $0 | $0 | $0.12/month |

---

## 💡 Kluczowe wnioski

1. **Embedding** → Rozumienie semantyki tekstu (znaczenia, nie słów)
2. **Clustering** → Naturalne grupy artykułów o podobnym temacie
3. **LLM Validation** → Ludzka inteligencja sprawdza czy to trend
4. **Time Comparison** → Trendy to wzrost, nie pojedyncze artykuły
5. **Confidence Score** → Nie wszystkie trendy mają 100% pewności

**Rezultat**: Rzeczywiste trendy branżowe zamiast szumu! 🎉
