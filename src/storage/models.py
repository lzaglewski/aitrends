from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Index, LargeBinary
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
    credibility_weight = Column(Float, default=1.0, nullable=False)  # Source credibility weight
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
    topic_id = Column(Integer, nullable=True, index=True)  # BERTopic topic ID (-1 = outlier)
    cleaned_content = Column(Text, nullable=True)  # Preprocessed content for topic modeling
    summary = Column(Text, nullable=True)  # LLM-generated summary for clustering
    is_trend_relevant = Column(Boolean, default=True)  # False = skip in clustering
    summary_generated_at = Column(DateTime, nullable=True)

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


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, nullable=False, unique=True, index=True)  # BERTopic topic ID
    topic_name = Column(String(512), nullable=False)
    top_words = Column(Text, nullable=False)  # JSON array of top words
    size = Column(Integer, nullable=False, default=0)  # Number of articles
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Topic(id={self.topic_id}, name='{self.topic_name}', size={self.size})>"


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, nullable=True, index=True)  # Reference to Topic (nullable for backward compat)
    keyword = Column(String(255), nullable=False, index=True)  # Topic name or legacy keyword
    count = Column(Integer, nullable=False)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    growth_rate = Column(Float, nullable=False)
    is_trending = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)  # New topic that didn't exist before
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


class EmbeddingCache(Base):
    """
    Cache for article embeddings to speed up topic modeling on reruns.

    Embeddings are expensive to compute, so caching them based on content
    can significantly speed up reprocessing of articles.
    """
    __tablename__ = "embedding_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(64), unique=True, index=True, nullable=False)  # SHA256(url + content[:500])
    embedding = Column(LargeBinary, nullable=False)  # Pickled numpy array
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_accessed = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_cache_key', 'cache_key'),
        Index('idx_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<EmbeddingCache(cache_key='{self.cache_key[:16]}...', created={self.created_at})>"


class TrendSnapshot(Base):
    """
    Historical snapshot of topic trends for tracking evolution over time.

    Stores periodic snapshots of topic metrics and centroids to enable
    trend lifecycle analysis and semantic drift detection.
    """
    __tablename__ = "trend_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.topic_id"), nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    article_count = Column(Integer, nullable=False)
    weighted_count = Column(Float, nullable=True)  # Source-weighted count
    growth_rate = Column(Float, nullable=False)
    velocity = Column(Float, nullable=True)  # Rate of change of growth rate
    stage = Column(String(50), nullable=True)  # emerging/growing/peak/declining/stable
    centroid_embedding = Column(LargeBinary, nullable=True)  # Pickled numpy centroid
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_topic_snapshot_date', 'topic_id', 'snapshot_date'),
        Index('idx_snapshot_date', 'snapshot_date'),
    )

    def __repr__(self):
        return f"<TrendSnapshot(topic_id={self.topic_id}, stage='{self.stage}', date={self.snapshot_date})>"
