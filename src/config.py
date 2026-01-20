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

    # Rate limiting
    REQUEST_DELAY_SECONDS: int = 2
    REQUEST_TIMEOUT: int = 30

    # User agent
    USER_AGENT: str = "Ad-Trends-Monitor/1.0 (Educational purpose)"

    class Config:
        env_file = ".env"


settings = Settings()
