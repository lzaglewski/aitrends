from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session, joinedload
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import hashlib
from loguru import logger

from .models import Base, Source, Article, Keyword, Topic, Trend, FailedUrl
from ..config import settings


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
        logger.info("Database initialized successfully")

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
            logger.debug(f"Article already exists: {article_data['url']}")
            return None

        if self.content_exists(content_hash):
            logger.debug(f"Article with same content already exists: {article_data['title']}")
            return None

        word_count = len(content.split())

        # Skip if too short
        if word_count < settings.MIN_ARTICLE_LENGTH:
            logger.debug(f"Article too short ({word_count} words): {article_data['title']}")
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
                    existing.size = info.get('size', 0)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new topic
                    topic = Topic(
                        topic_id=topic_id,
                        topic_name=info['name'],
                        top_words=json.dumps(info['top_words']),
                        size=info.get('size', 0)
                    )
                    session.add(topic)

            session.commit()
            logger.info(f"Saved {len(topics_info)} topics")

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

    def get_all_topics(self) -> List[Topic]:
        """Get all topics."""
        with self.get_session() as session:
            return session.query(Topic).all()

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
            logger.info(f"Saved {len(trends)} trends")

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
