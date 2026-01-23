# Jak działa AI Trends Monitor?

## Pełny proces od pobrania artykułów do wykrycia trendów

```mermaid
flowchart TD
    subgraph ETAP1["1. ZBIERANIE DANYCH"]
        A[/"Źródła RSS\n(blogi, portale branżowe)"/] --> B["Pobieranie artykułów\n(tytuł, treść, data)"]
        B --> C["Usuwanie duplikatów\n(podobne artykuły)"]
    end

    subgraph ETAP2["2. PRZYGOTOWANIE TREŚCI"]
        C --> D["Podsumowanie przez AI\n(2-3 zdania na artykuł)"]
        D --> E{"Czy artykuł\ndotyczy trendu?"}
        E -->|"TAK\n(np. nowa technologia)"| F["Zachowaj do analizy"]
        E -->|"NIE\n(np. oferta pracy)"| G["Pomiń"]
    end

    subgraph ETAP3["3. GRUPOWANIE TEMATYCZNE"]
        F --> H["Zamiana tekstu na liczby\n(embeddingi)"]
        H --> I["Grupowanie podobnych\nartykułów razem"]
        I --> J["Nadanie nazwy\nkażdej grupie"]
    end

    subgraph ETAP4["4. WYKRYWANIE TRENDÓW"]
        J --> K["Porównanie:\nTeraz vs. 2 tygodnie temu"]
        K --> L{"Czy temat\nrośnie?"}
        L -->|"TAK (+20%)"| M["TREND!"]
        L -->|"NIE"| N["Temat stabilny"]
    end

    subgraph ETAP5["5. RAPORT"]
        M --> O["Lista trendów\nz opisami"]
        N --> O
        O --> P[/"Wyświetl na ekranie\nlub wyślij email"/]
    end

    style ETAP1 fill:#e1f5fe
    style ETAP2 fill:#fff3e0
    style ETAP3 fill:#f3e5f5
    style ETAP4 fill:#e8f5e9
    style ETAP5 fill:#fce4ec
    style M fill:#4caf50,color:#fff
    style G fill:#ffcdd2
```

## Wyjaśnienie prostym językiem

| Etap | Co się dzieje? | Po co? |
|------|----------------|--------|
| 1 | System pobiera artykuły z blogów i portali | Zbieramy dane do analizy |
| 2 | AI czyta każdy artykuł i pisze krótkie streszczenie | Krótsze teksty = lepsza analiza |
| 3 | Podobne artykuły trafiają do jednej grupy | Znajdujemy wspólne tematy |
| 4 | Sprawdzamy które tematy rosną | Wykrywamy co jest "na fali" |
| 5 | Generujemy raport z trendami | Wiemy co jest ważne w branży |
