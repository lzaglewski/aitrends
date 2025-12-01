from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/trends.db"
    SCRAPE_INTERVAL_HOURS: int = 6
    MAX_ARTICLES_PER_SOURCE: int = 50
    MIN_ARTICLE_LENGTH: int = 200
    TREND_WINDOW_DAYS: int = 30
    TOP_KEYWORDS_COUNT: int = 20

    # Rate limiting
    REQUEST_DELAY_SECONDS: int = 2
    REQUEST_TIMEOUT: int = 30

    # User agent
    USER_AGENT: str = "Ad-Trends-Monitor/1.0 (Educational purpose)"

    class Config:
        env_file = ".env"


settings = Settings()
