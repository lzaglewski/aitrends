# Jak wykrywamy trendy?

## Porównanie okresów czasowych

```mermaid
flowchart TD
    subgraph DANE["ZBIERAMY DANE"]
        A["Wszystkie artykuły\nz ostatnich 8 tygodni"]
    end

    subgraph OKRESY["DZIELIMY NA OKRESY"]
        A --> B["Okres 1\n(najstarszy)"]
        A --> C["Okres 2"]
        A --> D["Okres 3"]
        A --> E["Okres 4\n(najnowszy)"]
    end

    subgraph LICZENIE["LICZYMY ARTYKUŁY W KAŻDYM TEMACIE"]
        B --> F["AI w marketingu:\n5 artykułów"]
        C --> G["AI w marketingu:\n8 artykułów"]
        D --> H["AI w marketingu:\n15 artykułów"]
        E --> I["AI w marketingu:\n25 artykułów"]
    end

    subgraph ANALIZA["ANALIZUJEMY WZROST"]
        F --> J["5 → 8 → 15 → 25"]
        J --> K{"Rośnie\nponad 20%?"}
        K -->|"TAK"| L["TREND!"]
        K -->|"NIE"| M["Temat stabilny"]
    end

    style DANE fill:#e3f2fd
    style OKRESY fill:#fff8e1
    style LICZENIE fill:#f3e5f5
    style ANALIZA fill:#e8f5e9
    style L fill:#4caf50,color:#fff
```

## Etapy życia trendu

```mermaid
flowchart LR
    A["NOWY\n(0 → kilka)"] --> B["WSCHODZĄCY\n(rośnie wolno)"]
    B --> C["ROSNĄCY\n(rośnie szybko)"]
    C --> D["SZCZYT\n(najwyższy poziom)"]
    D --> E["SPADAJĄCY\n(maleje)"]
    E --> F["STABILNY\n(bez zmian)"]

    style A fill:#e1f5fe,stroke:#01579b
    style B fill:#b3e5fc,stroke:#0288d1
    style C fill:#4fc3f7,stroke:#0288d1
    style D fill:#ffd54f,stroke:#f57f17
    style E fill:#ffcc80,stroke:#ef6c00
    style F fill:#e0e0e0,stroke:#616161
```

## Przykład wykrywania trendu

```mermaid
gantt
    title Wzrost tematu "AI w content marketingu"
    dateFormat  YYYY-MM-DD
    section Artykuły
    Okres 1 (3 artykuły)    :a1, 2026-01-01, 14d
    Okres 2 (7 artykułów)   :a2, 2026-01-15, 14d
    Okres 3 (12 artykułów)  :a3, 2026-01-29, 14d
    Okres 4 (22 artykuły)   :a4, 2026-02-12, 14d
```

| Okres | Liczba artykułów | Zmiana | Status |
|-------|------------------|--------|--------|
| Styczeń 1-14 | 3 | - | Początek |
| Styczeń 15-28 | 7 | +133% | Rośnie |
| Luty 1-14 | 12 | +71% | Rośnie |
| Luty 15-28 | 22 | +83% | **TREND!** |

**Wniosek:** Temat "AI w content marketingu" jest wyraźnym trendem - liczba artykułów rośnie z okresu na okres o ponad 20%.
