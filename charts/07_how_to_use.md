# Jak używać systemu?

## Dostępne komendy

```mermaid
flowchart TD
    subgraph FULL["PEŁNY PIPELINE"]
        A["python main.py --once"]
        A --> A1["Pobierz artykuły"]
        A1 --> A2["Generuj streszczenia"]
        A2 --> A3["Grupuj tematy"]
        A3 --> A4["Wykryj trendy"]
        A4 --> A5["Pokaż raport"]
    end

    subgraph PARTIAL["CZĘŚCIOWE URUCHOMIENIE"]
        B["python main.py --summarize"]
        B --> B1["Tylko generuj\nstreszczenia"]

        C["python main.py --topics"]
        C --> C1["Tylko grupuj\ni wykryj trendy"]

        D["python main.py --remodel"]
        D --> D1["Przebuduj wszystko\nod nowa"]
    end

    subgraph CONTINUOUS["TRYB CIĄGŁY"]
        E["python main.py"]
        E --> E1["Uruchom raz"]
        E1 --> E2["Czekaj 6h"]
        E2 --> E1
    end

    style FULL fill:#e8f5e9
    style PARTIAL fill:#fff8e1
    style CONTINUOUS fill:#e3f2fd
```

## Kiedy użyć której komendy?

```mermaid
flowchart TD
    START["Chcę uruchomić system"] --> Q1{"Pierwszy raz?"}

    Q1 -->|TAK| INIT["python main.py --init-db\npython main.py --init-sources\npython main.py --once"]

    Q1 -->|NIE| Q2{"Co chcę zrobić?"}

    Q2 -->|"Pełna analiza"| ONCE["python main.py --once"]
    Q2 -->|"Tylko streszczenia"| SUMM["python main.py --summarize"]
    Q2 -->|"Tylko trendy"| TOPICS["python main.py --topics"]
    Q2 -->|"Tryb ciągły"| CONT["python main.py"]

    style START fill:#e3f2fd
    style INIT fill:#fff8e1
    style ONCE fill:#e8f5e9
    style SUMM fill:#f3e5f5
    style TOPICS fill:#fce4ec
    style CONT fill:#bbdefb
```

## Typowy workflow

```mermaid
sequenceDiagram
    participant U as Użytkownik
    participant S as System
    participant AI as OpenAI API
    participant DB as Baza danych

    Note over U,DB: Pierwsze uruchomienie
    U->>S: python main.py --once
    S->>S: Pobierz artykuły z RSS
    S->>DB: Zapisz artykuły
    S->>AI: Wygeneruj streszczenia
    AI-->>S: 200 streszczeń
    S->>DB: Zapisz streszczenia
    S->>S: Grupuj tematy (BERTopic)
    S->>AI: Zwaliduj tematy
    AI-->>S: 2 trendy potwierdzone
    S->>DB: Zapisz trendy
    S-->>U: Raport z trendami

    Note over U,DB: Kolejne uruchomienia
    U->>S: python main.py --topics
    S->>DB: Pobierz streszczenia
    S->>S: Grupuj tematy
    S-->>U: Raport z trendami
```

## Przykładowe użycie

### Scenariusz 1: Codzienna analiza
```bash
# Rano - pełna analiza
python main.py --once

# Wieczorem - tylko sprawdzenie trendów (bez nowych artykułów)
python main.py --topics
```

### Scenariusz 2: Debugowanie
```bash
# Sprawdź ile artykułów ma streszczenia
sqlite3 data/trends.db "SELECT COUNT(*) FROM articles WHERE summary IS NOT NULL;"

# Wygeneruj brakujące streszczenia
python main.py --summarize

# Przebuduj klastry
python main.py --topics
```

### Scenariusz 3: Tryb produkcyjny
```bash
# Uruchom w tle (co 6 godzin)
nohup python main.py > logs/output.log 2>&1 &
```
