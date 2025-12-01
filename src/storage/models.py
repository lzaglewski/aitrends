from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)  # blog/rss/sitemap
    last_scraped = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    articles = relationship("Article", back_populates="source")

    def __repr__(self):
        return f"<Source(name='{self.name}', type='{self.source_type}')>"


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    url = Column(String(512), nullable=False, unique=True, index=True)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA256 for deduplication
    published_date = Column(DateTime, nullable=True, index=True)
    scraped_date = Column(DateTime, default=datetime.utcnow)
    word_count = Column(Integer, nullable=False, default=0)
    author = Column(String(255), nullable=True)

    source = relationship("Source", back_populates="articles")
    keywords = relationship("Keyword", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_published_date', 'published_date'),
        Index('idx_content_hash', 'content_hash'),
    )

    def __repr__(self):
        return f"<Article(title='{self.title[:50]}...', url='{self.url}')>"


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    keyword = Column(String(255), nullable=False, index=True)
    score = Column(Float, nullable=False)
    extraction_method = Column(String(50), nullable=False)  # yake/tfidf/spacy
    created_at = Column(DateTime, default=datetime.utcnow)

    article = relationship("Article", back_populates="keywords")

    __table_args__ = (
        Index('idx_keyword', 'keyword'),
        Index('idx_article_keyword', 'article_id', 'keyword'),
    )

    def __repr__(self):
        return f"<Keyword(keyword='{self.keyword}', score={self.score:.3f})>"


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    count = Column(Integer, nullable=False)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    growth_rate = Column(Float, nullable=False)
    is_trending = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_period', 'period_start', 'period_end'),
        Index('idx_keyword_period', 'keyword', 'period_start', 'period_end'),
    )

    def __repr__(self):
        return f"<Trend(keyword='{self.keyword}', growth_rate={self.growth_rate:.2%})>"


class FailedUrl(Base):
    __tablename__ = "failed_urls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(512), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FailedUrl(url='{self.url}', retries={self.retry_count})>"
