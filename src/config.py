from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/trends.db"
    SCRAPE_INTERVAL_HOURS: int = 6
    MAX_ARTICLES_PER_SOURCE: int = 50
    MIN_ARTICLE_LENGTH: int = 30
    TREND_WINDOW_DAYS: int = 30
    TOP_KEYWORDS_COUNT: int = 20  # Deprecated - kept for backward compatibility

    # Topic Modeling (BERTopic) settings
    TOPIC_MODEL_LANGUAGE: str = "multilingual"  # 'multilingual', 'en', 'pl'
    TOPIC_MIN_TOPIC_SIZE: int = 8  # Minimum articles per topic (increased to reduce noise)
    TOPIC_MIN_SAMPLES: int = 3  # Minimum samples for HDBSCAN core points
    TOPIC_NR_TOPICS: int | None = None  # Auto-detect number of topics
    TOPIC_MIN_DOCUMENT_LENGTH: int = 50  # Minimum characters for topic modeling
    TOPIC_MODEL_PATH: str = "./data/models/topic_model"  # Path to save/load model
    TOPIC_REMODEL_THRESHOLD: int = 100  # Re-train model after N new articles

    # Trend detection settings
    TREND_MIN_COUNT: int = 3  # Minimum topic occurrences to be considered trending
    TREND_MIN_GROWTH_RATE: float = 0.2  # Minimum growth rate (20%)

    # Output settings
    TREND_OUTPUT_FORMAT: str = "console"  # 'console', 'email', 'slack', 'json'
    TREND_MAX_DISPLAY: int = 10  # Max trends to display in summaries

    # LLM Enhancement settings
    USE_LLM_ENHANCEMENT: bool = True  # Enable LLM-based trend naming and filtering
    LLM_MODEL: str = "gpt-4o-mini"  # Model to use (gpt-4o-mini is cheapest)
    OPENAI_API_KEY: str = ""  # OpenAI API key (set in .env)
    LLM_MAX_ARTICLES_PER_TOPIC: int = 5  # Max articles to send to LLM per topic
    LLM_MAX_TOKENS: int = 500  # Max tokens for LLM response
    LLM_TEMPERATURE: float = 0.3  # Lower = more focused/deterministic

    # LLM Summarization Pipeline settings
    USE_LLM_SUMMARIZATION: bool = True  # Enable LLM-based article summarization before clustering
    LLM_SUMMARY_DELAY_SECONDS: float = 0.5  # Delay between LLM calls (rate limiting)
    LLM_SUMMARY_MAX_CONTENT_CHARS: int = 4000  # Max article content to send to LLM
    LLM_SUMMARY_MAX_RETRIES: int = 3  # Max retries for failed LLM calls
    LLM_SUMMARY_BATCH_SIZE: int = 50  # Number of articles to process per batch

    # Deduplication settings
    DEDUP_ENABLED: bool = True  # Enable fuzzy deduplication of articles
    DEDUP_SIMILARITY_THRESHOLD: float = 0.85  # Similarity threshold (0-1) for duplicates

    # Embedding Cache settings
    EMBEDDING_CACHE_ENABLED: bool = True  # Enable embedding caching for performance
    EMBEDDING_CACHE_TTL_DAYS: int = 90  # Time-to-live for cached embeddings (days)

    # Full Content Scraping settings
    FULL_CONTENT_ENABLED: bool = True  # Fetch full article content from URLs
    FULL_CONTENT_MIN_RSS_LENGTH: int = 500  # Minimum RSS content length to skip scraping
    FULL_CONTENT_TIMEOUT: int = 30  # Request timeout in seconds
    FULL_CONTENT_RATE_LIMIT: float = 1.0  # Delay between requests to same domain (seconds)
    FULL_CONTENT_MAX_WORKERS: int = 5  # Max parallel workers for content fetching

    # Source Weighting settings
    SOURCE_WEIGHTS_ENABLED: bool = True  # Enable source credibility weighting
    SOURCE_WEIGHTS_CONFIG: str = "data/source_weights.yaml"  # Path to weights config

    # Temporal Weighting settings
    USE_TEMPORAL_WEIGHTING: bool = True  # Apply temporal decay to embeddings
    TEMPORAL_LAMBDA_DECAY: float = 0.05  # Decay rate (0.05 = ~14 day half-life)

    # Multi-period Trend Analysis settings
    USE_MULTIPERIOD_ANALYSIS: bool = True  # Enable lifecycle stage analysis
    MULTIPERIOD_WEEKS: int = 2  # Length of each analysis period in weeks
    MULTIPERIOD_COUNT: int = 4  # Number of periods to analyze

    # Topic Merging settings
    USE_TOPIC_MERGING: bool = True  # Enable automatic topic merging
    TOPIC_MERGE_SIMILARITY: float = 0.75  # Minimum similarity for merge candidates
    TOPIC_MERGE_USE_LLM: bool = True  # Use LLM to validate merge decisions

    # Cross-topic Correlation settings
    USE_CORRELATION_ANALYSIS: bool = True  # Enable cross-topic correlation analysis
    CORRELATION_MIN_THRESHOLD: float = 0.3  # Minimum correlation to include in results

    # Semantic Drift Detection settings
    USE_DRIFT_DETECTION: bool = True  # Enable semantic drift detection
    DRIFT_THRESHOLD: float = 0.3  # Minimum drift score (1 - similarity) to flag
    DRIFT_LOOKBACK_DAYS: int = 14  # Days to look back for comparison

    # Rate limiting
    REQUEST_DELAY_SECONDS: int = 2
    REQUEST_TIMEOUT: int = 30

    # User agent
    USER_AGENT: str = "Ad-Trends-Monitor/1.0 (Educational purpose)"

    class Config:
        env_file = ".env"


settings = Settings()
