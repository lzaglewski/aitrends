# Panel Administracyjny AI Trends Monitor

Panel administracyjny w czystym HTML/CSS/JavaScript do zarządzania systemem monitorowania trendów.

## Funkcje

### 📊 Dashboard (index.html)
- Statystyki systemu (źródła, artykuły, słowa kluczowe)
- Ręczne uruchamianie scrapingu
- Top 10 trendów
- Ostatnie artykuły
- Status źródeł

### 📡 Źródła (sources.html)
- **CRUD źródeł RSS**:
  - Dodawanie nowego źródła (nazwa, URL, typ)
  - Edycja istniejącego źródła (modal)
  - Usuwanie źródła (soft delete)
  - Filtrowanie aktywnych/nieaktywnych
- Tabela ze wszystkimi źródłami
- Status i ostatni scraping

### 📰 Artykuły (articles.html)
- Wyszukiwanie artykułów
- Filtry:
  - Słowo kluczowe
  - Źródło
  - Okres (7, 30, 90 dni)
  - Limit wyników
- Tabela z linkami do artykułów

### 📈 Trendy (trends.html)
- Wybór okresu analizy (7, 30, 90 dni)
- **Rosnące słowa kluczowe** - wzrost > 20%
- **Nowe słowa kluczowe** - całkowicie nowe
- **Malejące słowa kluczowe** - spadek popularności
- **Top 50 słów kluczowych**

## Struktura

```
admin-panel/
├── index.html          # Dashboard
├── sources.html        # Zarządzanie źródłami
├── articles.html       # Przeglądanie artykułów
├── trends.html         # Analiza trendów
├── css/
│   └── style.css      # Style (custom CSS)
└── js/
    └── api.js         # API client (fetch wrapper)
```

## Uruchomienie

Panel jest serwowany przez FastAPI jako static files:

```bash
# Uruchom FastAPI (z głównego katalogu projektu)
uvicorn src.api.routes:app --reload --port 8000
```

## Dostęp

- **Panel administracyjny**: http://localhost:8000/admin/
- **Dashboard**: http://localhost:8000/admin/index.html
- **Źródła**: http://localhost:8000/admin/sources.html
- **Artykuły**: http://localhost:8000/admin/articles.html
- **Trendy**: http://localhost:8000/admin/trends.html
- **API Docs**: http://localhost:8000/docs

## Technologia

- **Frontend**: Vanilla HTML5, CSS3, JavaScript (ES6+)
- **API Client**: Fetch API
- **Styling**: Custom CSS (bez frameworków)
- **Backend**: FastAPI (Python)

## Nowe endpointy API

Panel korzysta z nowych endpointów dodanych do FastAPI:

- `PUT /sources/{id}` - Aktualizacja źródła
- `POST /scrape/trigger` - Manualne uruchomienie scrapingu

## Rozwój

Panel nie wymaga budowania ani kompilacji. Edytuj pliki HTML/CSS/JS bezpośrednio, odśwież przeglądarkę aby zobaczyć zmiany.

### Dodawanie nowych funkcji

1. Dodaj nową metodę w `js/api.js` jeśli potrzebny nowy endpoint
2. Stwórz nową stronę HTML lub rozszerz istniejącą
3. Użyj stylów z `css/style.css` lub dodaj własne

### Komponenty CSS

Dostępne klasy:
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-sm`
- `.card`, `.card-header`, `.card-title`
- `.form-group`, `.form-label`, `.form-input`, `.form-select`
- `.badge`, `.badge-success`, `.badge-danger`, `.badge-info`
- `.alert`, `.alert-success`, `.alert-error`
- `.table-container`, `table`, `thead`, `tbody`
- `.spinner` - loading indicator

## Wsparcie przeglądarek

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Wymaga wsparcia dla ES6+ (fetch, async/await, template literals).
