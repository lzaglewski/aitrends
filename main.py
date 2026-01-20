#!/usr/bin/env python3
"""
Ad Trends Monitor - Main Scheduler
Periodically scrapes sources and analyzes trends using BERTopic.
"""

import schedule
import time
import argparse
from datetime import datetime
from loguru import logger
import sys
import yaml
import os

from src.scrapers.rss_fetcher import RSSFetcher
from src.processors.keyword_extractor import TopicExtractor
from src.analyzers.topic_modeler import TopicModeler
from src.analyzers.trend_detector import TrendDetector
from src.analyzers.llm_trend_analyzer import enhance_topics_with_llm
from src.formatters.trend_summarizer import format_trends_for_output
from src.storage.database import Database, init_db
from src.config import settings


# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/ad_trends_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG"
)


def load_sources_from_yaml(yaml_path: str = "data/sources.yaml"):
    """Load sources from YAML file."""
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('sources', [])
    except FileNotFoundError:
        logger.warning(f"Sources file not found: {yaml_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading sources from YAML: {e}")
        return []


def initialize_sources():
    """Initialize sources from YAML into database."""
    logger.info("Initializing sources from YAML")

    db = Database()
    sources_data = load_sources_from_yaml()

    if not sources_data:
        logger.warning("No sources found in YAML file")
        return

    for source_data in sources_data:
        try:
            # Check if source already exists
            with db.get_session() as session:
                from src.storage.models import Source
                existing = session.query(Source).filter(Source.url == source_data['url']).first()

                if not existing:
                    db.add_source(
                        name=source_data['name'],
                        url=source_data['url'],
                        source_type=source_data['type']
                    )
                    logger.info(f"Added source: {source_data['name']}")
                else:
                    logger.debug(f"Source already exists: {source_data['name']}")

        except Exception as e:
            logger.error(f"Error adding source {source_data.get('name')}: {e}")


def run_topic_modeling(db: Database, topic_modeler: TopicModeler):
    """
    Run topic modeling on articles that don't have topics assigned yet.

    Args:
        db: Database instance
        topic_modeler: TopicModeler instance
    """
    logger.info("Running topic modeling...")

    # Get articles without topic assignment
    with db.get_session() as session:
        from src.storage.models import Article
        articles = (
            session.query(Article)
            .filter(Article.topic_id == None)
            .all()
        )

    if not articles:
        logger.info("No articles need topic modeling")
        return

    logger.info(f"Found {len(articles)} articles without topics")

    # Extract cleaned content
    text_extractor = TopicExtractor()
    documents = []
    article_ids = []

    for article in articles:
        cleaned = text_extractor.extract_text(article.content)
        if len(cleaned) >= settings.TOPIC_MIN_DOCUMENT_LENGTH:
            documents.append(cleaned)
            article_ids.append(article.id)

    if not documents:
        logger.warning("No valid documents for topic modeling")
        return

    logger.info(f"Processing {len(documents)} documents with BERTopic...")

    # Extract topics
    topic_ids, topic_info = topic_modeler.extract_topics(
        documents,
        min_document_length=settings.TOPIC_MIN_DOCUMENT_LENGTH
    )

    logger.info(f"BERTopic completed: {len(topic_info)} raw topics identified")

    # LLM Enhancement (if enabled)
    if settings.USE_LLM_ENHANCEMENT and topic_info:
        logger.info("Enhancing topics with LLM analysis...")

        # Group articles by topic_id
        articles_by_topic = {}
        for i, (article_id, topic_id) in enumerate(zip(article_ids, topic_ids)):
            if topic_id == -1:  # Skip outliers
                continue

            if topic_id not in articles_by_topic:
                articles_by_topic[topic_id] = []

            # Get original article from DB
            with db.get_session() as session:
                from src.storage.models import Article
                article = session.query(Article).filter(Article.id == article_id).first()
                if article:
                    articles_by_topic[topic_id].append({
                        'id': article.id,
                        'title': article.title,
                        'content': article.content[:500]  # First 500 chars
                    })

        # Enhance with LLM
        topic_info = enhance_topics_with_llm(topic_info, articles_by_topic)

        logger.info(f"LLM Enhancement completed: {len(topic_info)} trends identified")

    # Save topics to database
    if topic_info:
        db.save_topics(topic_info)

    # Update article topic assignments
    for i, article_id in enumerate(article_ids):
        if i < len(topic_ids):
            db.update_article_topic(article_id, topic_ids[i], documents[i])

    logger.info(f"Topic modeling completed: {len(topic_info)} final topics")


def run_scraping_job():
    """Main scraping and analysis job."""
    logger.info("=" * 80)
    logger.info(f"Starting scraping job at {datetime.now()}")
    logger.info("=" * 80)

    db = Database()
    rss_fetcher = RSSFetcher()
    text_extractor = TopicExtractor()

    # Initialize topic modeler
    # Check if model exists
    model_path = settings.TOPIC_MODEL_PATH
    topic_modeler = TopicModeler(
        language=settings.TOPIC_MODEL_LANGUAGE,
        min_topic_size=settings.TOPIC_MIN_TOPIC_SIZE,
        nr_topics=settings.TOPIC_NR_TOPICS
    )

    if os.path.exists(model_path):
        try:
            topic_modeler.load_model(model_path)
            logger.info("Loaded existing topic model")
        except Exception as e:
            logger.warning(f"Could not load model: {e}, will create new one")

    sources = db.get_active_sources()
    logger.info(f"Found {len(sources)} active sources")

    total_articles = 0
    new_articles_count = 0

    for source in sources:
        try:
            logger.info(f"Processing source: {source.name} ({source.source_type})")

            articles = []

            # Fetch articles based on source type
            if source.source_type == 'rss':
                articles = rss_fetcher.fetch_feed(source.url)
            elif source.source_type == 'blog':
                logger.warning(f"Blog scraping not yet implemented for: {source.name}")
                continue
            elif source.source_type == 'sitemap':
                logger.warning(f"Sitemap crawling not yet implemented for: {source.name}")
                continue
            else:
                logger.warning(f"Unknown source type: {source.source_type}")
                continue

            logger.info(f"Fetched {len(articles)} articles from {source.name}")

            # Process each article
            for article_data in articles:
                try:
                    # Add source_id
                    article_data['source_id'] = source.id

                    # Save article (with deduplication)
                    article_id = db.save_article(article_data)

                    if not article_id:
                        # Article was duplicate or too short
                        continue

                    total_articles += 1
                    new_articles_count += 1

                    logger.debug(f"Saved article {article_id}: {article_data.get('title', '')[:50]}")

                except Exception as e:
                    logger.error(f"Error processing article {article_data.get('url')}: {e}")
                    db.save_failed_url(
                        article_data.get('url', ''),
                        source.id,
                        str(e)
                    )

            # Update source last_scraped time
            db.update_source_scraped_time(source.id)

        except Exception as e:
            logger.error(f"Error processing source {source.name}: {e}")
            continue

    logger.info(f"Scraping completed: {total_articles} total articles ({new_articles_count} new)")

    # Run topic modeling on new articles
    if new_articles_count > 0:
        try:
            run_topic_modeling(db, topic_modeler)

            # Save model if we processed enough new articles
            if new_articles_count >= settings.TOPIC_REMODEL_THRESHOLD:
                os.makedirs(os.path.dirname(settings.TOPIC_MODEL_PATH), exist_ok=True)
                topic_modeler.save_model(settings.TOPIC_MODEL_PATH)

        except Exception as e:
            logger.error(f"Error in topic modeling: {e}")

    # Calculate trends
    try:
        logger.info("Calculating trends...")
        detector = TrendDetector(db)
        trends = detector.calculate_trends(
            window_days=settings.TREND_WINDOW_DAYS,
            min_count=settings.TREND_MIN_COUNT,
            min_growth_rate=settings.TREND_MIN_GROWTH_RATE
        )

        # Save trends to database
        db.save_trends(trends)

        trending_count = sum(1 for t in trends if t['is_trending'])
        new_count = sum(1 for t in trends if t.get('is_new', False))
        logger.info(f"Found {trending_count} trending topics ({new_count} new)")

        # Display trends
        if trends:
            output = format_trends_for_output(
                trends,
                output_format=settings.TREND_OUTPUT_FORMAT,
                max_trends=settings.TREND_MAX_DISPLAY,
                period_days=settings.TREND_WINDOW_DAYS
            )
            print(output)

    except Exception as e:
        logger.error(f"Error calculating trends: {e}")

    logger.info("=" * 80)
    logger.info(f"Scraping job completed at {datetime.now()}")
    logger.info("=" * 80)


def run_once():
    """Run scraping job once and exit."""
    logger.info("Running in single-run mode")
    run_scraping_job()
    logger.info("Single run completed, exiting")


def run_scheduler():
    """Run continuous scheduler."""
    logger.info("Starting scheduler mode")
    logger.info(f"Scraping interval: {settings.SCRAPE_INTERVAL_HOURS} hours")

    # Run immediately on start
    run_scraping_job()

    # Schedule periodic runs
    schedule.every(settings.SCRAPE_INTERVAL_HOURS).hours.do(run_scraping_job)

    logger.info("Scheduler started, waiting for next run...")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ad Trends Monitor with BERTopic")
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run scraping once and exit (instead of continuous mode)'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database and exit'
    )
    parser.add_argument(
        '--init-sources',
        action='store_true',
        help='Initialize sources from YAML and exit'
    )
    parser.add_argument(
        '--remodel',
        action='store_true',
        help='Re-run topic modeling on all articles'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable DEBUG logging (shows LLM prompts and responses)'
    )

    args = parser.parse_args()

    # Configure DEBUG logging if requested
    if args.debug:
        logger.remove()
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )
        logger.add(
            "logs/ad_trends_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="30 days",
            level="DEBUG"
        )
        logger.debug("DEBUG logging enabled")

    # Initialize database if needed
    if args.init_db:
        logger.info("Initializing database...")
        init_db()
        logger.success("Database initialized")
        return

    # Initialize sources if needed
    if args.init_sources:
        logger.info("Initializing sources...")
        initialize_sources()
        logger.success("Sources initialized")
        return

    # Remodel all articles
    if args.remodel:
        logger.info("Re-running topic modeling on all articles...")
        db = Database()

        # Reset topic_id for all articles
        with db.get_session() as session:
            from src.storage.models import Article
            session.query(Article).update({Article.topic_id: None})
            session.commit()

        topic_modeler = TopicModeler(
            language=settings.TOPIC_MODEL_LANGUAGE,
            min_topic_size=settings.TOPIC_MIN_TOPIC_SIZE,
            nr_topics=settings.TOPIC_NR_TOPICS
        )

        run_topic_modeling(db, topic_modeler)

        # Save new model
        os.makedirs(os.path.dirname(settings.TOPIC_MODEL_PATH), exist_ok=True)
        topic_modeler.save_model(settings.TOPIC_MODEL_PATH)

        logger.success("Topic modeling completed")
        return

    # Ensure database is initialized
    try:
        db = Database()
        db.init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

    # Load sources
    initialize_sources()

    # Run mode
    if args.once:
        run_once()
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
