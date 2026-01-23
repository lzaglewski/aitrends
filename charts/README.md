# Diagramy systemu AI Trends Monitor

Zbiór wizualizacji wyjaśniających działanie systemu dla osób mniej technicznych.

## Spis treści

| # | Plik | Opis |
|---|------|------|
| 1 | [01_main_pipeline.md](01_main_pipeline.md) | Pełny proces od pobrania do trendu |
| 2 | [02_summarization_process.md](02_summarization_process.md) | Jak AI podsumowuje artykuły |
| 3 | [03_trend_detection.md](03_trend_detection.md) | Jak wykrywamy trendy |
| 4 | [04_clustering_explained.md](04_clustering_explained.md) | Jak grupujemy artykuły w tematy |
| 5 | [05_system_overview.md](05_system_overview.md) | Architektura i koszty systemu |
| 6 | [06_data_quality.md](06_data_quality.md) | Filtrowanie i jakość danych |
| 7 | [07_how_to_use.md](07_how_to_use.md) | Instrukcja użycia komend |

## Jak przeglądać diagramy?

### Opcja 1: GitHub
Po pushu na GitHub, diagramy Mermaid renderują się automatycznie.

### Opcja 2: VS Code
Zainstaluj rozszerzenie "Markdown Preview Mermaid Support":
```
ext install bierner.markdown-mermaid
```

### Opcja 3: Online
Skopiuj kod Mermaid do [mermaid.live](https://mermaid.live)

## Kluczowe koncepty

### Pipeline w skrócie
```
RSS → Artykuły → Streszczenia AI → Grupowanie → Trendy → Raport
```

### Co robi każdy etap?

| Etap | Wejście | Wyjście | Narzędzie |
|------|---------|---------|-----------|
| Scraping | URL źródła | Artykuły | RSS Parser |
| Streszczenia | Pełny tekst | 2-3 zdania | GPT-4o-mini |
| Grupowanie | Streszczenia | Tematy | BERTopic |
| Walidacja | Tematy | Trendy | GPT-4o-mini |
| Raport | Trendy | Tekst/Email | Python |

## Słownik pojęć

| Termin | Wyjaśnienie |
|--------|-------------|
| **Trend** | Temat który rośnie w liczbie artykułów |
| **Embedding** | Tekst zamieniony na liczby (wektor) |
| **Klastrowanie** | Grupowanie podobnych rzeczy razem |
| **BERTopic** | Narzędzie do automatycznego grupowania tekstów |
| **LLM** | Duży model językowy (np. GPT-4) |
