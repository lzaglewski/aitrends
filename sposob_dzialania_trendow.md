# Szczegółowy proces: Od pobrania artykułów do trendu

## 🔄 Pełny pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TREND DETECTION PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │   RSS Sources   │  ← KROK 1: Pobieranie
    │  (50 art/źródło)│
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   Clean Text    │  ← KROK 2: Czyszczenie
    │ (min 50 znaków) │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────────────────────┐
    │            BERTopic Clustering              │  ← KROK 3: Grupowanie semantyczne
    │  ┌───────────────────────────────────────┐  │
    │  │ SentenceTransformer (tekst → 384D)    │  │  Embedding: "rozumienie" tekstu
    │  │            ↓                          │  │
    │  │ UMAP (384D → 5D)                      │  │  Redukcja: kompresja wymiarów
    │  │            ↓                          │  │
    │  │ HDBSCAN (5D → grupy)                  │  │  Clustering: znajdowanie grup
    │  │            ↓                          │  │
    │  │ c-TF-IDF (grupy → słowa kluczowe)     │  │  Reprezentacja: nazwanie tematów
    │  └───────────────────────────────────────┘  │
    └────────────────────┬────────────────────────┘
                         │
                         ▼
    ┌─────────────────────┐
    │   Named Entity      │  ← KROK 4: Filtrowanie nazw
    │   Filter            │     (Google, Elon Musk → OUT)
    └────────┬────────────┘
             │
             ▼
    ┌─────────────────────┐
    │   LLM Analysis      │  ← KROK 5: Walidacja przez AI
    │   (GPT-4o-mini)     │     (Czy to TREND czy NEWS?)
    └────────┬────────────┘
             │
             ▼
    ┌─────────────────────┐
    │   Trend Detector    │  ← KROK 6: Porównanie okresów
    │   (30d vs 30d)      │     (Wzrost ≥20% = TRENDING)
    └────────┬────────────┘
             │
             ▼
    ┌─────────────────────┐
    │   Database Storage  │  ← KROK 7: Zapis do bazy
    │   + Formatters      │     (Console/Email/Slack)
    └─────────────────────┘

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

### 🎯 Cel: Zrozumieć CO mówią artykuły, nie tylko JAKIE słowa zawierają

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  BERTopic Pipeline - 4 komponenty współpracujące                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TEKST ARTYKUŁU                                                             │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────┐                                                    │
│  │ 1. SentenceTransformer │  ← "Tłumacz" tekstu na liczby                  │
│  │    (Embedding Model)    │     Zamienia tekst → wektor 384 liczb         │
│  └─────────────────────┘                                                    │
│       │                                                                     │
│       │  384 wymiary (za dużo do analizy!)                                  │
│       ▼                                                                     │
│  ┌─────────────────────┐                                                    │
│  │ 2. UMAP             │  ← "Kompresor" wymiarów                           │
│  │    (Redukcja)       │     Zmniejsza 384D → 5D zachowując strukturę      │
│  └─────────────────────┘                                                    │
│       │                                                                     │
│       │  5 wymiarów (można wizualizować!)                                   │
│       ▼                                                                     │
│  ┌─────────────────────┐                                                    │
│  │ 3. HDBSCAN          │  ← "Grupowacz" artykułów                          │
│  │    (Clustering)     │     Znajduje naturalne skupiska podobnych        │
│  └─────────────────────┘                                                    │
│       │                                                                     │
│       │  Grupy artykułów (tematy)                                           │
│       ▼                                                                     │
│  ┌─────────────────────┐                                                    │
│  │ 4. c-TF-IDF         │  ← "Nazywacz" tematów                             │
│  │    (Reprezentacja)  │     Wyciąga słowa kluczowe z każdej grupy        │
│  └─────────────────────┘                                                    │
│       │                                                                     │
│       ▼                                                                     │
│  NAZWANE TEMATY: "AI Content", "Privacy Marketing", "Influencer ROI"       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Faza 1: EMBEDDING - Zamiana tekstu na wektory (SentenceTransformer)

#### 🤔 Problem: Komputer nie rozumie słów
Komputer widzi tylko cyfry. "Marketing" dla niego to ciąg bajtów `77 97 114 107...`
Jak powiedzieć komputerowi, że "Marketing" i "Reklama" są podobne?

#### 💡 Rozwiązanie: Semantic Embeddings
Każde słowo/zdanie zamieniamy na **wektor liczb** (listę 384 liczb),
gdzie **podobne znaczeniowo teksty mają podobne wektory**.

```
┌─────────────────────────────────────────────────────────────────┐
│  ANALOGIA: Mapa GPS dla tekstu                                  │
│                                                                 │
│  Tak jak GPS zamienia adres na współrzędne (lat, lng):         │
│    "Warszawa" → [52.23, 21.01]                                  │
│    "Kraków"   → [50.06, 19.94]                                  │
│                                                                 │
│  Tak SentenceTransformer zamienia tekst na "współrzędne":      │
│    "AI marketing" → [0.12, -0.34, 0.56, ..., 0.89]  (384 liczb)│
│    "AI reklama"   → [0.11, -0.33, 0.57, ..., 0.88]  (podobne!) │
│    "Przepis na pierogi" → [-0.87, 0.12, ..., -0.45] (inne!)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Jak to działa pod spodem?**
```
Artykuł: "AI is transforming digital marketing strategies..."
                    │
                    ▼
    ┌─────────────────────────────────┐
    │   SentenceTransformer           │
    │   (sieć neuronowa BERT)         │
    │                                 │
    │   1. Tokenizacja tekstu         │
    │   2. Przejście przez 12 warstw  │
    │   3. Pooling (średnia)          │
    └─────────────────────────────────┘
                    │
                    ▼
    Wektor: [0.023, -0.156, 0.789, ..., 0.234]
            ↑_________________________________↑
                    384 wymiary
```

**Modele w zależności od języka:**
```python
multilingual → 'paraphrase-multilingual-MiniLM-L12-v2'  # Domyślnie, 12 warstw
english      → 'all-MiniLM-L6-v2'                       # Szybciej, 6 warstw
polish       → 'sdadas/mmlw-retrieval-roberta-base'     # Optymalizowany dla PL
```

**Wymiarowość:** Każdy model produkuje wektor o **stałej długości 384** (MiniLM) lub 768 (RoBERTa).

**Dlaczego 384 wymiary?**
- Wystarczająco dużo, żeby uchwycić niuanse znaczenia
- Wystarczająco mało, żeby było wydajne obliczeniowo
- Każdy wymiar reprezentuje jakiś "aspekt" znaczenia (trudny do interpretacji dla człowieka)

---

### Faza 2: DIMENSIONALITY REDUCTION - UMAP

#### 🤔 Problem: 384 wymiary to za dużo
- Nie da się tego zwizualizować (człowiek widzi max 3D)
- "Klątwa wymiarowości" - w wielu wymiarach wszystko wydaje się równie odległe
- Algorytmy klastrowania źle działają w wysokich wymiarach

#### 💡 Rozwiązanie: UMAP (Uniform Manifold Approximation and Projection)
Kompresujemy 384D → 5D, **zachowując strukturę sąsiedztwa**.

```
┌─────────────────────────────────────────────────────────────────┐
│  ANALOGIA: Spłaszczanie globusa do mapy                        │
│                                                                 │
│  Glob ziemski jest 3D, ale mapa jest 2D.                       │
│  Mimo to mapa zachowuje relatywne odległości:                  │
│    - Warszawa nadal jest blisko Krakowa                        │
│    - Australia nadal jest daleko od Europy                     │
│                                                                 │
│  UMAP robi to samo: spłaszcza 384D do 5D,                      │
│  zachowując "kto jest blisko kogo".                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

```
PRZED (384D - nie da się narysować):
Artykuł 1: [0.12, -0.34, 0.56, ..., 0.89]  ─┐
Artykuł 2: [0.11, -0.33, 0.57, ..., 0.88]  ─┼─ Podobne (blisko w 384D)
Artykuł 3: [-0.87, 0.12, ..., -0.45]       ─── Inny (daleko w 384D)

                    │
                    │  UMAP
                    ▼

PO (5D - można analizować):
Artykuł 1: [2.3, -1.2, 0.8, 0.1, -0.5]   ─┐
Artykuł 2: [2.4, -1.1, 0.9, 0.2, -0.4]   ─┼─ Nadal blisko!
Artykuł 3: [-3.1, 2.4, -1.8, 1.2, 0.9]   ─── Nadal daleko!
```

**Parametry UMAP:**
```python
umap_model = UMAP(
    n_neighbors=15,      # Patrz na 15 najbliższych sąsiadów
    n_components=5,      # Wynik: 5 wymiarów (zamiast 384!)
    min_dist=0.0,        # Pozwól punktom być bardzo blisko siebie
    metric='cosine',     # Mierz podobieństwo kątem, nie odległością
    random_state=42      # Dla powtarzalności
)
```

**Dlaczego akurat 5 wymiarów?**
- 2-3D: Za mało informacji, tracimy niuanse
- 5D: Dobry kompromis między informacją a wydajnością
- 10+D: Mało zyskujemy, a tracimy na wydajności

---

### Faza 3: CLUSTERING - HDBSCAN

#### 🤔 Problem: Mamy punkty w 5D, ale nie wiemy które są "razem"
Artykuły to teraz punkty w przestrzeni 5-wymiarowej.
Które z nich tworzą "grupy" (czyli tematy)?

#### 💡 Rozwiązanie: HDBSCAN (Hierarchical Density-Based Spatial Clustering)
Znajduje **gęste skupiska** punktów - naturalne grupy bez określania z góry ile ich ma być.

```
┌─────────────────────────────────────────────────────────────────┐
│  ANALOGIA: Szukanie grup ludzi na placu                        │
│                                                                 │
│  Wyobraź sobie plac z setkami osób:                            │
│    ○ ○ ○         ○   ○            ○ ○                          │
│    ○ ○ ○ ○       ○                ○ ○ ○                        │
│      ○ ○                          ○ ○                          │
│                    ○                                            │
│                      ○    ○                                     │
│                                                                 │
│  HDBSCAN znajduje "naturalne" grupy:                           │
│    [GRUPA 1]      [samotni]       [GRUPA 2]                    │
│    ● ● ●         ○   ○            ● ●                          │
│    ● ● ● ●       ○                ● ● ●                        │
│      ● ●                          ● ●                          │
│                    ○  ← outlier                                 │
│                      ○    ○  ← outlierzy                        │
│                                                                 │
│  Samotne osoby = OUTLIERZY (topic -1)                          │
│  Nie pasują do żadnej grupy.                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Dlaczego HDBSCAN a nie K-Means?**

| Cecha | K-Means | HDBSCAN |
|-------|---------|---------|
| Wymaga liczby klastrów | ✅ TAK (trzeba zgadnąć) | ❌ NIE (sam znajduje) |
| Kształt klastrów | Tylko kuliste | Dowolne kształty |
| Obsługa outlierów | ❌ Każdy punkt gdzieś trafia | ✅ Outlierzy to topic -1 |
| Gęstość | Ignoruje | Szuka gęstych obszarów |

**Parametry HDBSCAN:**
```python
hdbscan_model = HDBSCAN(
    min_cluster_size=3,          # Minimum 3 artykuły, żeby był temat
    min_samples=3,               # Minimum 3 sąsiadów w gęstym regionie
    metric='euclidean',          # Odległość euklidesowa w 5D
    cluster_selection_method='eom',  # "Excess of Mass" - preferuje mniejsze, gęstsze klastry
    prediction_data=True         # Zachowaj dane do późniejszych predykcji
)
```

**Co to znaczy `min_cluster_size=3`?**
```
✅ Akceptowane jako temat:
   ○ ○ ○     (3 artykuły o AI w marketingu)
   ○ ○ ○ ○   (4 artykuły o prywatności)

❌ Za małe - idzie do outlierów:
   ○ ○       (tylko 2 artykuły o Elon Musku)
   ○         (1 artykuł o piernikach)
```

**Wynik HDBSCAN:**
```python
topics = [0, 0, 0, 1, 1, 1, 1, -1, 2, 2, 2, -1, -1]
           │  │  │  │  │  │  │  │   │  │  │   │   │
           └──┴──┴──┘  └──┴──┴──┘   └──┴──┘   └───┘
           Temat 0     Temat 1       Temat 2   Outlierzy
           (3 art.)    (4 art.)      (3 art.)  (3 art.)
```

---

### Faza 4: REPRESENTATION - c-TF-IDF (Class-based TF-IDF)

#### 🤔 Problem: Mamy grupy, ale jak je NAZWAĆ?
Wiemy, że artykuły 1, 2, 3 są w grupie razem.
Ale o czym ta grupa? Jaki to temat?

#### 💡 Rozwiązanie: c-TF-IDF
Dla każdej grupy znajdujemy słowa, które są **częste w tej grupie**
ale **rzadkie w innych grupach**.

```
┌─────────────────────────────────────────────────────────────────┐
│  ANALOGIA: Co wyróżnia gazetę sportową od finansowej?          │
│                                                                 │
│  Gazeta sportowa:  "gol", "mecz", "liga", "trener"             │
│  Gazeta finansowa: "akcje", "giełda", "indeks", "bank"         │
│                                                                 │
│  Słowo "jest" występuje w obu - NIE wyróżnia.                  │
│  Słowo "gol" występuje tylko w sportowej - WYRÓŻNIA!           │
│                                                                 │
│  c-TF-IDF znajduje takie "wyróżniające" słowa dla każdej grupy.│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Jak działa c-TF-IDF:**
```
Krok 1: Połącz wszystkie artykuły z grupy w jeden "super-dokument"
        Topic 0: "AI marketing AI content generation AI tools..."
        Topic 1: "privacy cookies GDPR consent tracking..."

Krok 2: Policz słowa (TF - Term Frequency)
        Topic 0: AI=15, marketing=8, content=7, the=50...
        Topic 1: privacy=12, cookies=9, GDPR=6, the=45...

Krok 3: Zmniejsz wagę słów częstych wszędzie (IDF - Inverse Document Frequency)
        "the" jest wszędzie → niska waga
        "AI" jest głównie w Topic 0 → wysoka waga dla Topic 0
        "privacy" jest głównie w Topic 1 → wysoka waga dla Topic 1

Krok 4: TF × IDF = wynik końcowy
```

**Parametry CountVectorizer:**
```python
vectorizer_model = CountVectorizer(
    ngram_range=(1, 2),      # Słowa pojedyncze i pary: "ai", "ai marketing"
    stop_words=stopwords,     # Usuń "the", "a", "i", "w" itd.
    min_df=2,                 # Słowo musi być w min. 2 dokumentach
    max_df=0.95,              # Słowo może być w max 95% dokumentów
    lowercase=True            # Zamień na małe litery
)

top_n_words = 5              # Weź 5 najlepszych słów na temat
```

**Rezultat:**
```
Topic 0 (15 artykułów): ['ai', 'content', 'generation', 'automation', 'tools']
                         ↑ Najwyższy score c-TF-IDF

Topic 1 (12 artykułów): ['privacy', 'cookies', 'tracking', 'gdpr', 'consent']

Topic 2 (8 artykułów):  ['influencer', 'marketing', 'roi', 'analytics', 'creator']

Topic -1 (outlierzy):   NIE MA REPREZENTACJI (to nie jest spójny temat)
```

---

### 📊 Podsumowanie całego pipeline'u BERTopic

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAŁY PROCES W PIGUŁCE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  100 artykułów                                                              │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ SentenceTransformer: 100 tekstów → 100 wektorów × 384 wymiary      │   │
│  │ "Każdy artykuł ma teraz swoje 'współrzędne GPS w przestrzeni idei'" │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       │  Macierz 100 × 384                                                  │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ UMAP: 100 × 384 → 100 × 5                                          │   │
│  │ "Kompresja z zachowaniem sąsiedztwa - podobne artykuły nadal blisko"│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       │  Macierz 100 × 5                                                    │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ HDBSCAN: 100 punktów w 5D → grupy                                  │   │
│  │ "Znajdź gęste skupiska - to są nasze tematy"                        │   │
│  │                                                                     │   │
│  │ Wynik: Topic 0: 25 art. | Topic 1: 18 art. | Topic 2: 12 art.      │   │
│  │        Topic 3: 8 art.  | Outlierzy (-1): 37 art.                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ c-TF-IDF: Dla każdego tematu → 5 słów kluczowych                   │   │
│  │ "Co wyróżnia tę grupę od innych?"                                   │   │
│  │                                                                     │   │
│  │ Topic 0: ['ai', 'content', 'generation', 'automation', 'tools']    │   │
│  │ Topic 1: ['privacy', 'cookies', 'tracking', 'gdpr', 'consent']     │   │
│  │ Topic 2: ['influencer', 'marketing', 'roi', 'analytics']           │   │
│  │ Topic 3: ['video', 'tiktok', 'short', 'form', 'engagement']        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  🎯 WYNIK: 4 tematy z nazwami i słowami kluczowymi                         │
│            + 37 outlierów (artykuły bez wyraźnego wzorca)                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 🔸 Co to są OUTLIERZY (Topic -1) i dlaczego to dobrze?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DLACZEGO NIEKTÓRE ARTYKUŁY NIE MAJĄ TEMATU?                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Outlier (topic -1) to artykuł, który:                                      │
│                                                                             │
│  1. Jest ZBYT UNIKALNY                                                      │
│     └─ Jedyny artykuł o "AI w rolnictwie" wśród 100 o marketingu           │
│                                                                             │
│  2. Jest POMIĘDZY tematami                                                  │
│     └─ Artykuł o "Privacy w AI Marketing" - pasuje trochę do obu tematów   │
│                                                                             │
│  3. Ma ZA MAŁO podobnych artykułów                                          │
│     └─ 2 artykuły o Elonie Musku, ale min_cluster_size=3                   │
│                                                                             │
│  4. Jest NEWSEM, nie TRENDEM                                                │
│     └─ "Google ogłosił nowy produkt" - jednorazowe wydarzenie              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  DLACZEGO TO DOBRZE?                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✅ FILTRUJE SZUM                                                           │
│     Nie każdy artykuł to trend. Outlierzy to często:                        │
│     - Jednorazowe ogłoszenia firm                                           │
│     - Opinie pojedynczych autorów                                           │
│     - Tematy poza głównym nurtem                                            │
│                                                                             │
│  ✅ POPRAWIA JAKOŚĆ TEMATÓW                                                 │
│     Tematy są "czystsze" - zawierają tylko artykuły naprawdę podobne        │
│                                                                             │
│  ✅ WSKAZUJE BRAK TRENDU                                                    │
│     Wysoki % outlierów = branża jest "rozdrobniona"                         │
│     Niski % outlierów = wyraźne trendy dominują                             │
│                                                                             │
│  📊 TYPOWE PROPORCJE:                                                       │
│     20-40% outlierów = normalne                                             │
│     50%+ outlierów = albo za mało danych, albo brak trendów                 │
│     <10% outlierów = bardzo spójna tematyka (rzadkie)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
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

## 🗺️ BONUS: Wizualizacja przestrzeni tematów

### Jak zobaczyć przestrzeń 5D?

Problem: UMAP redukuje embeddingi do 5 wymiarów, ale człowiek widzi max 3D.
Rozwiązanie: **Kolejny UMAP** redukuje 5D → 2D dla wizualizacji.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE WIZUALIZACJI                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Artykuły z bazy                                                            │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────┐                               │
│  │ SentenceTransformer                     │                               │
│  │ Tekst → Embedding 384D                  │                               │
│  └─────────────────────────────────────────┘                               │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────┐                               │
│  │ UMAP (wizualizacja)                     │                               │
│  │ 384D → 2D (bezpośrednio!)               │                               │
│  │                                         │                               │
│  │ n_neighbors=15                          │                               │
│  │ n_components=2  ← dla wykresu           │                               │
│  │ min_dist=0.1    ← trochę rozrzutu       │                               │
│  └─────────────────────────────────────────┘                               │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────┐                               │
│  │ Plotly.js                               │                               │
│  │ Interaktywny wykres scatter             │                               │
│  │ - Kolory = tematy                       │                               │
│  │ - Hover = tytuł artykułu                │                               │
│  │ - Click = otwórz artykuł                │                               │
│  └─────────────────────────────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Jak czytać wizualizację?

```
                    ┌─────────────────────────────────────┐
                    │  🔴 Temat 1: AI Content            │
                    │      ●●●                           │
                    │     ●●●●●                          │
                    │      ●●●              🟢 Temat 2   │
                    │                       ●●●         │
                    │                      ●●●●         │
                    │         ○                         │
                    │       ○   ○     🔵 Temat 3        │
                    │            ○      ●●              │
                    │                   ●●●             │
                    │  ○ = outlierzy (szare)            │
                    └─────────────────────────────────────┘

Interpretacja:
- Punkty blisko siebie = artykuły o podobnej treści
- Punkty tego samego koloru = ten sam temat
- Gęste skupiska = wyraźne tematy
- Rozrzucone punkty = tematy niejednorodne
- Szare outlierzy = artykuły unikalne, bez grupy
```

### Dostęp do wizualizacji

- **Admin Panel**: http://localhost:8000/admin/visualization.html
- **API Endpoint**: `GET /topics/visualization?days=60&max_articles=500`

---

## 💡 Kluczowe wnioski

1. **Embedding** → Rozumienie semantyki tekstu (znaczenia, nie słów)
2. **Clustering** → Naturalne grupy artykułów o podobnym temacie
3. **LLM Validation** → Ludzka inteligencja sprawdza czy to trend
4. **Time Comparison** → Trendy to wzrost, nie pojedyncze artykuły
5. **Confidence Score** → Nie wszystkie trendy mają 100% pewności
6. **Wizualizacja** → Możliwość "zobaczenia" przestrzeni semantycznej w 2D

**Rezultat**: Rzeczywiste trendy branżowe zamiast szumu! 🎉
