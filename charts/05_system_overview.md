# Przegląd systemu AI Trends Monitor

## Architektura wysokopoziomowa

```mermaid
flowchart TB
    subgraph ŹRÓDŁA["ŹRÓDŁA DANYCH"]
        S1["Blog 1"]
        S2["Blog 2"]
        S3["Portal branżowy"]
        S4["RSS Feed"]
    end

    subgraph SYSTEM["AI TRENDS MONITOR"]
        subgraph ZBIERANIE["Zbieranie"]
            A["Scraper RSS"]
        end

        subgraph PRZETWARZANIE["Przetwarzanie"]
            B["Deduplikacja"]
            C["Podsumowania AI"]
        end

        subgraph ANALIZA["Analiza"]
            D["Grupowanie BERTopic"]
            E["Walidacja AI"]
            F["Wykrywanie trendów"]
        end

        subgraph BAZA["Baza danych"]
            G[("SQLite")]
        end
    end

    subgraph WYJŚCIE["WYNIKI"]
        H["Raport w konsoli"]
        I["Email"]
        J["Slack"]
    end

    S1 & S2 & S3 & S4 --> A
    A --> B --> C --> D --> E --> F
    C --> G
    F --> G
    F --> H & I & J

    style ŹRÓDŁA fill:#e3f2fd
    style SYSTEM fill:#f5f5f5
    style ZBIERANIE fill:#fff8e1
    style PRZETWARZANIE fill:#fff3e0
    style ANALIZA fill:#e8f5e9
    style BAZA fill:#fce4ec
    style WYJŚCIE fill:#f3e5f5
```

## Harmonogram działania

```mermaid
gantt
    title Cykl pracy systemu (co 6 godzin)
    dateFormat HH:mm
    axisFormat %H:%M

    section Zbieranie
    Pobieranie artykułów     :a1, 00:00, 5m
    Usuwanie duplikatów      :a2, after a1, 2m

    section AI Processing
    Generowanie streszczeń   :b1, after a2, 15m
    Filtrowanie nie-trendów  :b2, after a2, 15m

    section Analiza
    Grupowanie tematyczne    :c1, after b1, 3m
    Walidacja przez AI       :c2, after c1, 5m
    Wykrywanie trendów       :c3, after c2, 2m

    section Raport
    Generowanie raportu      :d1, after c3, 1m
```

## Koszty operacyjne

```mermaid
pie title Podział kosztów na 1000 artykułów
    "Streszczenia AI ($0.30)" : 30
    "Walidacja trendów ($0.12)" : 12
    "Hosting/Infra ($0)" : 1
```

| Operacja | Koszt | Częstotliwość |
|----------|-------|---------------|
| Streszczenie artykułu | ~$0.0003 | Raz na artykuł |
| Walidacja tematu | ~$0.001 | Raz na temat |
| **Miesięcznie (1000 art.)** | **~$0.50** | - |

## Kluczowe metryki

```mermaid
flowchart LR
    subgraph INPUT["WEJŚCIE"]
        A["230 artykułów"]
    end

    subgraph FILTROWANIE["FILTROWANIE"]
        B["201 trend-relevant\n(87%)"]
        C["29 odrzuconych\n(13%)"]
    end

    subgraph CLUSTERING["GRUPOWANIE"]
        D["2 tematy"]
        E["0 outlierów"]
    end

    subgraph OUTPUT["WYNIK"]
        F["1 trending\n1 stabilny"]
    end

    A --> B & C
    B --> D & E
    D --> F

    style INPUT fill:#e3f2fd
    style FILTROWANIE fill:#fff8e1
    style CLUSTERING fill:#f3e5f5
    style OUTPUT fill:#e8f5e9
    style C fill:#ffcdd2
    style F fill:#4caf50,color:#fff
```
