#!/usr/bin/env python3
"""
Ad Trends Monitor - Main Scheduler
Periodically scrapes sources and analyzes trends.
"""

import schedule
import time
import argparse
from datetime import datetime
from loguru import logger
import sys
import yaml

from src.scrapers.rss_fetcher import RSSFetcher
from src.processors.keyword_extractor import KeywordExtractor
from src.analyzers.trend_detector import TrendDetector
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


def run_scraping_job():
    """Main scraping and analysis job."""
    logger.info("=" * 80)
    logger.info(f"Starting scraping job at {datetime.now()}")
    logger.info("=" * 80)

    db = Database()
    rss_fetcher = RSSFetcher()
    keyword_extractor = KeywordExtractor()

    sources = db.get_active_sources()
    logger.info(f"Found {len(sources)} active sources")

    total_articles = 0
    total_keywords = 0

    for source in sources:
        try:
            logger.info(f"Processing source: {source.name} ({source.source_type})")

            articles = []

            # Fetch articles based on source type
            if source.source_type == 'rss':
                articles = rss_fetcher.fetch_feed(source.url)
            elif source.source_type == 'blog':
                # Blog scraper would go here (not implemented in MVP)
                logger.warning(f"Blog scraping not yet implemented for: {source.name}")
                continue
            elif source.source_type == 'sitemap':
                # Sitemap crawler would go here (not implemented in MVP)
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

                    # Extract keywords
                    content = article_data.get('content', '')
                    if content:
                        keywords = keyword_extractor.extract_all(content)

                        if keywords:
                            # Get top keywords
                            top_keywords = keyword_extractor.get_top_keywords(
                                keywords,
                                top_n=settings.TOP_KEYWORDS_COUNT
                            )

                            # Save keywords
                            db.save_keywords(article_id, top_keywords)
                            total_keywords += len(top_keywords)

                            logger.debug(f"Extracted {len(top_keywords)} keywords for article {article_id}")

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

    logger.info(f"Scraping completed: {total_articles} new articles, {total_keywords} keywords extracted")

    # Calculate trends
    try:
        logger.info("Calculating trends...")
        detector = TrendDetector(db)
        trends = detector.calculate_trends(
            window_days=settings.TREND_WINDOW_DAYS
        )

        # Save trends to database
        db.save_trends(trends)

        trending_count = sum(1 for t in trends if t['is_trending'])
        logger.info(f"Found {trending_count} trending keywords")

        # Log top 5 trending
        top_trending = [t for t in trends if t['is_trending']][:5]
        if top_trending:
            logger.info("Top 5 trending keywords:")
            for trend in top_trending:
                logger.info(f"  - {trend['keyword']}: {trend['growth_rate']:.1%} growth ({trend['count']} occurrences)")

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
    parser = argparse.ArgumentParser(description="Ad Trends Monitor")
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

    args = parser.parse_args()

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
