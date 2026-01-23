# Jakość danych - jak filtrujemy śmieci?

## Wielowarstwowe filtrowanie

```mermaid
flowchart TD
    subgraph INPUT["WEJŚCIE: Surowe artykuły"]
        A["1000 artykułów\nz RSS"]
    end

    subgraph F1["FILTR 1: Duplikaty URL"]
        B{"Ten sam\nadres URL?"}
        B -->|TAK| C["Odrzuć"]
        B -->|NIE| D["Przepuść"]
    end

    subgraph F2["FILTR 2: Duplikaty treści"]
        D --> E{"Podobna treść\n(>85%)?"}
        E -->|TAK| F["Odrzuć"]
        E -->|NIE| G["Przepuść"]
    end

    subgraph F3["FILTR 3: Za krótkie"]
        G --> H{"Mniej niż\n30 słów?"}
        H -->|TAK| I["Odrzuć"]
        H -->|NIE| J["Przepuść"]
    end

    subgraph F4["FILTR 4: Nie-trendy"]
        J --> K{"Oferta pracy?\nEvent? Reklama?"}
        K -->|TAK| L["Odrzuć"]
        K -->|NIE| M["Przepuść"]
    end

    subgraph OUTPUT["WYNIK: Czyste dane"]
        M --> N["~700 artykułów\ndo analizy"]
    end

    A --> B
    C --> X["Kosz"]
    F --> X
    I --> X
    L --> X

    style INPUT fill:#ffebee
    style F1 fill:#fff8e1
    style F2 fill:#fff3e0
    style F3 fill:#fce4ec
    style F4 fill:#f3e5f5
    style OUTPUT fill:#e8f5e9
    style X fill:#ef5350,color:#fff
    style N fill:#4caf50,color:#fff
```

## Statystyki filtrowania

```mermaid
pie title Co się dzieje z 1000 artykułów?
    "Przechodzi do analizy (70%)" : 700
    "Duplikaty URL (5%)" : 50
    "Duplikaty treści (10%)" : 100
    "Za krótkie (5%)" : 50
    "Nie-trendy (10%)" : 100
```

## Przykłady odrzuconych artykułów

```mermaid
flowchart LR
    subgraph ODRZUCONE["ODRZUCONE JAKO 'NIE-TREND'"]
        A["Szukamy Marketing\nManagera w Warszawie"]
        B["Zapraszamy na\nAI Summit 2026"]
        C["Firma X kupiła\nfirmę Y za $10M"]
        D["Jak skonfigurować\nGoogle Analytics"]
    end

    subgraph POWÓD["POWÓD"]
        A --> E["Oferta pracy"]
        B --> F["Event"]
        C --> G["Press release"]
        D --> H["Dokumentacja"]
    end

    style ODRZUCONE fill:#ffebee
    style POWÓD fill:#fff8e1
```

## Porównanie: Przed i po filtrach

| Metryka | Bez filtrów | Z filtrami |
|---------|-------------|------------|
| Liczba artykułów | 1000 | 700 |
| Duplikaty | 15% | 0% |
| Śmieci (oferty, eventy) | 10% | 0% |
| Jakość trendów | Niska | Wysoka |
| Czas analizy | Dłuższy | Krótszy |

## Wiarygodność źródeł

```mermaid
flowchart TD
    subgraph ŹRÓDŁA["ŹRÓDŁA Z WAGAMI"]
        A["AdAge.com\n(waga: 1.5x)"]
        B["Marketing Week\n(waga: 1.5x)"]
        C["Blog firmowy\n(waga: 1.0x)"]
        D["Nieznane źródło\n(waga: 0.5x)"]
    end

    subgraph WPŁYW["WPŁYW NA TRENDY"]
        A --> E["Większy wpływ\nna wykrywanie trendów"]
        B --> E
        C --> F["Standardowy wpływ"]
        D --> G["Mniejszy wpływ"]
    end

    style A fill:#4caf50,color:#fff
    style B fill:#4caf50,color:#fff
    style C fill:#fff8e1
    style D fill:#ffcdd2
```

**Dlaczego wagi źródeł są ważne?**

Artykuł z AdAge.com (prestiżowy portal branżowy) powinien mieć większy wpływ na wykrywanie trendów niż artykuł z nieznanego bloga.
