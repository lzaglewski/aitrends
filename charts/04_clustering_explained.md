# Jak grupujemy artykuły w tematy?

## Proces krok po kroku

```mermaid
flowchart TD
    subgraph KROK1["KROK 1: ZAMIANA TEKSTU NA LICZBY"]
        A["Artykuł:\n'AI zmienia marketing...'"] --> B["Model AI czyta tekst"]
        B --> C["Tworzy 'odcisk palca'\n(384 liczby)"]
    end

    subgraph KROK2["KROK 2: ZNAJDOWANIE PODOBIEŃSTW"]
        C --> D["Porównujemy odciski\nwszystkich artykułów"]
        D --> E["Podobne artykuły\nsą 'blisko siebie'"]
    end

    subgraph KROK3["KROK 3: TWORZENIE GRUP"]
        E --> F["Algorytm znajduje\ngęste skupiska"]
        F --> G["Każde skupisko\n= jeden temat"]
    end

    subgraph KROK4["KROK 4: NAZYWANIE TEMATÓW"]
        G --> H["AI analizuje\nartykuły w grupie"]
        H --> I["Nadaje nazwę:\n'AI w marketingu'"]
    end

    style KROK1 fill:#e3f2fd
    style KROK2 fill:#fff8e1
    style KROK3 fill:#f3e5f5
    style KROK4 fill:#e8f5e9
```

## Wizualizacja grupowania

```mermaid
flowchart TD
    subgraph PRZED["PRZED GRUPOWANIEM\n(200 oddzielnych artykułów)"]
        A1["Art. o AI"]
        A2["Art. o SEO"]
        A3["Art. o AI"]
        A4["Art. o social media"]
        A5["Art. o SEO"]
        A6["Art. o AI"]
    end

    subgraph PO["PO GRUPOWANIU\n(3 tematy)"]
        subgraph T1["TEMAT 1: AI w marketingu\n(89 artykułów)"]
            B1["Art. o AI"]
            B2["Art. o AI"]
            B3["Art. o AI"]
        end

        subgraph T2["TEMAT 2: SEO i pozycjonowanie\n(45 artykułów)"]
            C1["Art. o SEO"]
            C2["Art. o SEO"]
        end

        subgraph T3["TEMAT 3: Social media marketing\n(66 artykułów)"]
            D1["Art. o social"]
        end
    end

    PRZED --> PO

    style PRZED fill:#ffebee
    style PO fill:#e8f5e9
    style T1 fill:#bbdefb
    style T2 fill:#c8e6c9
    style T3 fill:#ffe0b2
```

## Dlaczego używamy streszczeń?

```mermaid
flowchart LR
    subgraph STARY["STARA METODA"]
        A["Pełny artykuł\n2000 słów"] --> B["Obcięte do\n128 słów"]
        B --> C["Utracony sens"]
    end

    subgraph NOWY["NOWA METODA"]
        D["Pełny artykuł\n2000 słów"] --> E["AI streszczenie\n50 słów"]
        E --> F["Pełny sens\nzachowany"]
    end

    style STARY fill:#ffebee
    style NOWY fill:#e8f5e9
    style C fill:#ef5350,color:#fff
    style F fill:#4caf50,color:#fff
```

## Analogia: Biblioteka

Wyobraź sobie bibliotekę z 1000 książek rozrzuconych losowo:

| Przed grupowaniem | Po grupowaniu |
|-------------------|---------------|
| Książki leżą wszędzie | Książki na półkach tematycznych |
| Trudno znaleźć temat | Łatwo znaleźć podobne książki |
| Chaos | Porządek |

**Nasz system robi to samo z artykułami!**
