from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session, joinedload
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import hashlib
from loguru import logger

from .models import Base, Source, Article, Keyword, Topic, Trend, FailedUrl, EmbeddingCache, TrendSnapshot
from ..config import settings
import pickle
import numpy as np


class Database:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def init_db(self):
        """Initialize database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("✅ Database initialized successfully")

    # Source operations
    def get_active_sources(self) -> List[Source]:
        """Get all active sources."""
        with self.get_session() as session:
            return session.query(Source).filter(Source.active == True).all()

    def add_source(self, name: str, url: str, source_type: str) -> Source:
        """Add a new source."""
        with self.get_session() as session:
            source = Source(name=name, url=url, source_type=source_type)
            session.add(source)
            session.commit()
            session.refresh(source)
            logger.info(f"Added new source: {name} ({url})")
            return source

    def update_source_scraped_time(self, source_id: int):
        """Update last_scraped timestamp for a source."""
        with self.get_session() as session:
            source = session.query(Source).filter(Source.id == source_id).first()
            if source:
                source.last_scraped = datetime.utcnow()
                session.commit()

    # Article operations
    def article_exists(self, url: str) -> bool:
        """Check if article already exists by URL."""
        with self.get_session() as session:
            return session.query(Article).filter(Article.url == url).first() is not None

    def content_exists(self, content_hash: str) -> bool:
        """Check if article with same content hash exists."""
        with self.get_session() as session:
            return session.query(Article).filter(Article.content_hash == content_hash).first() is not None

    def save_article(self, article_data: Dict) -> Optional[int]:
        """
        Save article to database with deduplication.

        Args:
            article_data: Dict with keys: source_id, url, title, content, published_date, author

        Returns:
            Article ID or None if duplicate
        """
        content = article_data.get('content', '')
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check for duplicates
        if self.article_exists(article_data['url']):
            logger.debug(f"Article already exists (URL): {article_data['url']}")
            return None

        if self.content_exists(content_hash):
            logger.debug(f"Article already exists (content hash): {article_data['title'][:60]}")
            return None

        word_count = len(content.split())

        # Skip if too short
        if word_count < settings.MIN_ARTICLE_LENGTH:
            logger.warning(f"Article too short ({word_count} words, min {settings.MIN_ARTICLE_LENGTH}): {article_data['title'][:60]}")
            return None

        with self.get_session() as session:
            article = Article(
                source_id=article_data['source_id'],
                url=article_data['url'],
                title=article_data['title'],
                content=content,
                content_hash=content_hash,
                published_date=article_data.get('published_date'),
                word_count=word_count,
                author=article_data.get('author')
            )
            session.add(article)
            session.commit()
            session.refresh(article)
            logger.info(f"Saved article: {article.title[:50]}... (ID: {article.id})")
            return article.id

    def get_articles(
        self,
        keyword: Optional[str] = None,
        source_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Article]:
        """Get articles with optional filters."""
        with self.get_session() as session:
            query = session.query(Article).options(joinedload(Article.source))

            if source_id:
                query = query.filter(Article.source_id == source_id)

            if start_date:
                query = query.filter(Article.published_date >= start_date)

            if end_date:
                query = query.filter(Article.published_date <= end_date)

            if keyword:
                query = query.join(Keyword).filter(Keyword.keyword.ilike(f"%{keyword}%"))

            articles = query.order_by(Article.published_date.desc()).limit(limit).all()

            # Explicitly access source.name to ensure it's loaded
            for article in articles:
                _ = article.source.name

            return articles

    # Summary operations
    def get_articles_without_summary(self, limit: int = 100) -> List[Article]:
        """
        Get articles that don't have LLM-generated summaries yet.

        Args:
            limit: Maximum number of articles to return

        Returns:
            List of Article objects without summaries
        """
        with self.get_session() as session:
            articles = (
                session.query(Article)
                .filter(Article.summary == None)
                .order_by(Article.published_date.desc())
                .limit(limit)
                .all()
            )
            # Detach from session to avoid lazy loading issues
            for article in articles:
                session.expunge(article)
            return articles

    def update_article_summary(
        self,
        article_id: int,
        summary: str,
        is_trend_relevant: bool = True
    ):
        """
        Update article's LLM-generated summary.

        Args:
            article_id: Article ID
            summary: LLM-generated summary text
            is_trend_relevant: Whether article should be included in clustering
        """
        with self.get_session() as session:
            article = session.query(Article).filter(Article.id == article_id).first()
            if article:
                article.summary = summary
                article.is_trend_relevant = is_trend_relevant
                article.summary_generated_at = datetime.utcnow()
                session.commit()
                logger.debug(f"Updated summary for article {article_id}")

    def get_trend_relevant_articles(
        self,
        with_summary: bool = True,
        limit: Optional[int] = None
    ) -> List[Article]:
        """
        Get articles marked as trend-relevant.

        Args:
            with_summary: If True, only return articles that have summaries
            limit: Optional limit on number of articles

        Returns:
            List of trend-relevant Article objects
        """
        with self.get_session() as session:
            query = (
                session.query(Article)
                .filter(Article.is_trend_relevant == True)
            )

            if with_summary:
                query = query.filter(Article.summary != None)

            query = query.order_by(Article.published_date.desc())

            if limit:
                query = query.limit(limit)

            articles = query.all()
            # Detach from session
            for article in articles:
                session.expunge(article)
            return articles

    # Keyword operations
    def save_keywords(self, article_id: int, keywords: List[tuple]):
        """
        Save keywords for an article.

        Args:
            article_id: Article ID
            keywords: List of tuples (keyword, score, method)
        """
        with self.get_session() as session:
            for keyword, score, method in keywords:
                kw = Keyword(
                    article_id=article_id,
                    keyword=keyword,
                    score=score,
                    extraction_method=method
                )
                session.add(kw)
            session.commit()
            logger.debug(f"Saved {len(keywords)} keywords for article {article_id}")

    def get_keyword_counts(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """
        Get keyword counts for a time period.

        Returns:
            Dict mapping keyword to count
        """
        with self.get_session() as session:
            results = (
                session.query(Keyword.keyword, func.count(Keyword.id))
                .join(Article)
                .filter(Article.published_date >= start_date)
                .filter(Article.published_date <= end_date)
                .group_by(Keyword.keyword)
                .all()
            )
            return {keyword: count for keyword, count in results}

    def get_top_keywords(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[tuple]:
        """Get most frequent keywords."""
        with self.get_session() as session:
            query = (
                session.query(Keyword.keyword, func.count(Keyword.id).label('count'))
                .join(Article)
            )

            if start_date:
                query = query.filter(Article.published_date >= start_date)

            if end_date:
                query = query.filter(Article.published_date <= end_date)

            results = (
                query.group_by(Keyword.keyword)
                .order_by(func.count(Keyword.id).desc())
                .limit(limit)
                .all()
            )
            return results

    # Topic operations
    def save_topics(self, topics_info: Dict[int, Dict]):
        """
        Save or update topic metadata.

        Args:
            topics_info: Dict mapping topic_id to topic metadata
        """
        import json

        with self.get_session() as session:
            for topic_id, info in topics_info.items():
                # Check if topic already exists
                existing = session.query(Topic).filter(Topic.topic_id == topic_id).first()

                if existing:
                    # Update existing topic
                    existing.topic_name = info['name']
                    existing.top_words = json.dumps(info['top_words'])
                    existing.size = int(info.get('size', 0))  # Ensure int type
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new topic
                    topic = Topic(
                        topic_id=topic_id,
                        topic_name=info['name'],
                        top_words=json.dumps(info['top_words']),
                        size=int(info.get('size', 0))  # Ensure int type
                    )
                    session.add(topic)

            session.commit()
            logger.info(f"💾 Saved {len(topics_info)} topics")

    def update_article_topic(self, article_id: int, topic_id: int, cleaned_content: str = None):
        """
        Update article's topic assignment.

        Args:
            article_id: Article ID
            topic_id: Topic ID from BERTopic
            cleaned_content: Optional cleaned content
        """
        with self.get_session() as session:
            article = session.query(Article).filter(Article.id == article_id).first()
            if article:
                article.topic_id = topic_id
                if cleaned_content:
                    article.cleaned_content = cleaned_content
                session.commit()

    def get_articles_by_topic(self, topic_id: int, limit: int = 20) -> List[Article]:
        """Get articles assigned to a specific topic."""
        with self.get_session() as session:
            return (
                session.query(Article)
                .options(joinedload(Article.source))
                .filter(Article.topic_id == topic_id)
                .order_by(Article.published_date.desc())
                .limit(limit)
                .all()
            )

    def get_topic_counts(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[int, int]:
        """
        Get topic counts for a time period.

        Returns:
            Dict mapping topic_id to count
        """
        with self.get_session() as session:
            results = (
                session.query(Article.topic_id, func.count(Article.id))
                .filter(Article.published_date >= start_date)
                .filter(Article.published_date <= end_date)
                .filter(Article.topic_id != None)
                .filter(Article.topic_id != -1)  # Exclude outliers
                .group_by(Article.topic_id)
                .all()
            )
            return {topic_id: count for topic_id, count in results}

    def get_weighted_topic_counts(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[int, float]:
        """
        Get weighted topic counts for a time period.

        Uses source credibility weights to calculate weighted counts.

        Returns:
            Dict mapping topic_id to weighted count
        """
        with self.get_session() as session:
            results = (
                session.query(
                    Article.topic_id,
                    func.sum(Source.credibility_weight).label('weighted_count')
                )
                .join(Source, Article.source_id == Source.id)
                .filter(Article.published_date >= start_date)
                .filter(Article.published_date <= end_date)
                .filter(Article.topic_id != None)
                .filter(Article.topic_id != -1)  # Exclude outliers
                .group_by(Article.topic_id)
                .all()
            )
            return {topic_id: float(weighted_count) for topic_id, weighted_count in results}

    def get_all_topics(self) -> List[Topic]:
        """Get all topics."""
        with self.get_session() as session:
            return session.query(Topic).all()

    # Embedding Cache operations
    def get_embeddings_from_cache(self, cache_keys: List[str]) -> Dict[str, bytes]:
        """
        Retrieve cached embeddings by cache keys.

        Args:
            cache_keys: List of cache keys to look up

        Returns:
            Dict mapping cache_key to pickled embedding bytes
        """
        if not cache_keys:
            return {}

        with self.get_session() as session:
            results = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.cache_key.in_(cache_keys))
                .all()
            )

            # Update last_accessed for cache hits
            for cache_entry in results:
                cache_entry.last_accessed = datetime.utcnow()
            session.commit()

            return {entry.cache_key: entry.embedding for entry in results}

    def save_embeddings_to_cache(self, cache_data: List[tuple]):
        """
        Save embeddings to cache.

        Args:
            cache_data: List of tuples (cache_key, embedding_bytes, article_id)
        """
        if not cache_data:
            return

        with self.get_session() as session:
            for cache_key, embedding_bytes, article_id in cache_data:
                # Check if cache entry already exists
                existing = session.query(EmbeddingCache).filter(
                    EmbeddingCache.cache_key == cache_key
                ).first()

                if not existing:
                    cache_entry = EmbeddingCache(
                        cache_key=cache_key,
                        embedding=embedding_bytes,
                        article_id=article_id
                    )
                    session.add(cache_entry)

            session.commit()
            logger.debug(f"Saved {len(cache_data)} embeddings to cache")

    def cleanup_old_embeddings(self, ttl_days: int):
        """
        Remove stale embeddings from cache.

        Args:
            ttl_days: Time-to-live in days
        """
        cutoff_date = datetime.utcnow() - timedelta(days=ttl_days)

        with self.get_session() as session:
            deleted = (
                session.query(EmbeddingCache)
                .filter(EmbeddingCache.created_at < cutoff_date)
                .delete()
            )
            session.commit()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} stale embeddings from cache")

    # Trend Snapshot operations
    def save_trend_snapshot(
        self,
        topic_id: int,
        snapshot_data: Dict,
        centroid_embedding: Optional[np.ndarray] = None
    ):
        """
        Save a trend snapshot for historical tracking.

        Args:
            topic_id: Topic ID
            snapshot_data: Dict with trend metrics
            centroid_embedding: Optional topic centroid embedding
        """
        # Serialize centroid if provided
        centroid_bytes = None
        if centroid_embedding is not None:
            try:
                centroid_bytes = pickle.dumps(centroid_embedding)
            except Exception as e:
                logger.warning(f"Failed to serialize centroid for topic {topic_id}: {e}")

        with self.get_session() as session:
            snapshot = TrendSnapshot(
                topic_id=topic_id,
                snapshot_date=datetime.utcnow(),
                period_start=snapshot_data['period_start'],
                period_end=snapshot_data['period_end'],
                article_count=snapshot_data['count'],
                weighted_count=snapshot_data.get('weighted_count'),
                growth_rate=snapshot_data['growth_rate'],
                velocity=snapshot_data.get('velocity'),
                stage=snapshot_data.get('stage'),
                centroid_embedding=centroid_bytes
            )
            session.add(snapshot)
            session.commit()

    def get_trend_history(self, topic_id: int, limit: int = 30) -> List[TrendSnapshot]:
        """
        Get historical snapshots for a topic.

        Args:
            topic_id: Topic ID
            limit: Maximum number of snapshots to retrieve

        Returns:
            List of TrendSnapshot objects (most recent first)
        """
        with self.get_session() as session:
            return (
                session.query(TrendSnapshot)
                .filter(TrendSnapshot.topic_id == topic_id)
                .order_by(TrendSnapshot.snapshot_date.desc())
                .limit(limit)
                .all()
            )

    def deserialize_centroid(self, snapshot: TrendSnapshot) -> Optional[np.ndarray]:
        """
        Deserialize centroid embedding from a snapshot.

        Args:
            snapshot: TrendSnapshot object

        Returns:
            Numpy array or None
        """
        if not snapshot.centroid_embedding:
            return None

        try:
            return pickle.loads(snapshot.centroid_embedding)
        except Exception as e:
            logger.warning(f"Failed to deserialize centroid: {e}")
            return None

    def get_article_ids_by_topic(
        self,
        topic_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[int]:
        """
        Get article IDs for a specific topic.

        Args:
            topic_id: Topic ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Optional limit on number of articles

        Returns:
            List of article IDs
        """
        with self.get_session() as session:
            query = (
                session.query(Article.id)
                .filter(Article.topic_id == topic_id)
            )

            if start_date:
                query = query.filter(Article.published_date >= start_date)

            if end_date:
                query = query.filter(Article.published_date <= end_date)

            query = query.order_by(Article.published_date.desc())

            if limit:
                query = query.limit(limit)

            results = query.all()
            return [r[0] for r in results]

    # Trend operations
    def save_trends(self, trends: List[Dict]):
        """Save calculated trends."""
        with self.get_session() as session:
            for trend_data in trends:
                trend = Trend(
                    keyword=trend_data['keyword'],
                    count=trend_data['count'],
                    period_start=trend_data['period_start'],
                    period_end=trend_data['period_end'],
                    growth_rate=trend_data['growth_rate'],
                    is_trending=trend_data.get('is_trending', False)
                )
                session.add(trend)
            session.commit()
            logger.info(f"💾 Saved {len(trends)} trends")

    def get_trends(self, days: int = 30, limit: int = 20) -> List[Trend]:
        """Get recent trends."""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            return (
                session.query(Trend)
                .filter(Trend.period_end >= cutoff_date)
                .filter(Trend.is_trending == True)
                .order_by(Trend.growth_rate.desc())
                .limit(limit)
                .all()
            )

    # Failed URL operations
    def save_failed_url(self, url: str, source_id: Optional[int], error: str):
        """Save failed URL for retry."""
        with self.get_session() as session:
            failed = session.query(FailedUrl).filter(FailedUrl.url == url).first()

            if failed:
                failed.retry_count += 1
                failed.last_attempt = datetime.utcnow()
                failed.error_message = error
            else:
                failed = FailedUrl(
                    url=url,
                    source_id=source_id,
                    error_message=error
                )
                session.add(failed)

            session.commit()
            logger.warning(f"Saved failed URL: {url} (retries: {failed.retry_count})")

    # Statistics
    def get_stats(self) -> Dict:
        """Get system statistics."""
        with self.get_session() as session:
            total_sources = session.query(Source).count()
            active_sources = session.query(Source).filter(Source.active == True).count()
            total_articles = session.query(Article).count()
            total_keywords = session.query(Keyword).count()
            unique_keywords = session.query(Keyword.keyword).distinct().count()

            return {
                "total_sources": total_sources,
                "active_sources": active_sources,
                "total_articles": total_articles,
                "total_keywords": total_keywords,
                "unique_keywords": unique_keywords,
                "last_update": datetime.utcnow()
            }


def init_db():
    """Initialize database - convenience function."""
    db = Database()
    db.init_db()
    logger.success("Database tables created successfully")
