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

# Disable tokenizers parallelism warning (occurs when forking after using transformers)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

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

    # Load source weights if enabled
    weight_manager = None
    if settings.SOURCE_WEIGHTS_ENABLED:
        from src.utils.source_weights import SourceWeightManager
        weight_manager = SourceWeightManager(settings.SOURCE_WEIGHTS_CONFIG)

    for source_data in sources_data:
        try:
            url = source_data['url']

            # Check if source is blacklisted
            if weight_manager and weight_manager.is_blacklisted(url):
                logger.warning(f"Skipping blacklisted source: {source_data['name']} ({url})")
                continue

            # Get credibility weight
            weight = weight_manager.get_weight(url) if weight_manager else 1.0

            # Check if source already exists
            with db.get_session() as session:
                from src.storage.models import Source
                existing = session.query(Source).filter(Source.url == url).first()

                if not existing:
                    # Add new source with weight
                    source = Source(
                        name=source_data['name'],
                        url=url,
                        source_type=source_data['type'],
                        credibility_weight=weight
                    )
                    session.add(source)
                    session.commit()
                    logger.info(f"Added source: {source_data['name']} (weight: {weight})")
                else:
                    # Update weight if changed
                    if existing.credibility_weight != weight:
                        existing.credibility_weight = weight
                        session.commit()
                        logger.info(f"Updated weight for {source_data['name']}: {weight}")
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
    article_urls = []
    published_dates = []
    article_dicts = []

    for article in articles:
        cleaned = text_extractor.extract_text(article.content)
        if len(cleaned) >= settings.TOPIC_MIN_DOCUMENT_LENGTH:
            documents.append(cleaned)
            article_ids.append(article.id)
            article_urls.append(article.url)
            published_dates.append(article.published_date or article.scraped_date)
            # Prepare dict for potential deduplication
            article_dicts.append({
                'id': article.id,
                'title': article.title,
                'content': article.content,
                'source_id': article.source_id,
                'url': article.url
            })

    if not documents:
        logger.warning("No valid documents for topic modeling")
        return

    # Fuzzy deduplication (if enabled)
    if settings.DEDUP_ENABLED and len(documents) > 1:
        from src.processors.deduplicator import ArticleDeduplicator

        logger.info("Running fuzzy deduplication...")
        deduplicator = ArticleDeduplicator(settings.DEDUP_SIMILARITY_THRESHOLD)

        # Get source weights (empty for now, will be populated in FAZA 2)
        source_weights = {}

        # Deduplicate
        deduplicated_articles, dedup_metrics = deduplicator.deduplicate_batch(
            article_dicts, source_weights
        )

        # Update documents and article_ids to match deduplicated articles
        if dedup_metrics['removed'] > 0:
            deduplicated_ids = {a['id'] for a in deduplicated_articles}
            new_documents = []
            new_article_ids = []
            new_article_urls = []
            new_published_dates = []

            for i, article_id in enumerate(article_ids):
                if article_id in deduplicated_ids:
                    new_documents.append(documents[i])
                    new_article_ids.append(article_id)
                    new_article_urls.append(article_urls[i])
                    new_published_dates.append(published_dates[i])

            documents = new_documents
            article_ids = new_article_ids
            article_urls = new_article_urls
            published_dates = new_published_dates

            logger.info(
                f"Deduplication metrics: {dedup_metrics['removed']} duplicates removed "
                f"({dedup_metrics['rate']*100:.1f}% reduction)"
            )

    logger.info(f"Processing {len(documents)} documents with BERTopic...")

    # Extract topics (with embedding cache and temporal weighting if enabled)
    topic_ids, topic_info = topic_modeler.extract_topics(
        documents,
        article_ids=article_ids,
        article_urls=article_urls,
        published_dates=published_dates,
        min_document_length=settings.TOPIC_MIN_DOCUMENT_LENGTH,
        use_cache=settings.EMBEDDING_CACHE_ENABLED
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
        # Create set of valid topic IDs (those that passed LLM filtering)
        valid_topic_ids = set(topic_info.keys())
    else:
        valid_topic_ids = set()

    # Update article topic assignments
    for i, article_id in enumerate(article_ids):
        if i < len(topic_ids):
            # If topic was filtered out by LLM, mark as outlier
            final_topic_id = topic_ids[i] if topic_ids[i] in valid_topic_ids else -1
            db.update_article_topic(article_id, final_topic_id, documents[i])

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
        min_samples=settings.TOPIC_MIN_SAMPLES,
        nr_topics=settings.TOPIC_NR_TOPICS,
        use_temporal_weighting=settings.USE_TEMPORAL_WEIGHTING,
        temporal_lambda=settings.TEMPORAL_LAMBDA_DECAY
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

            # Fetch full content (if enabled)
            if settings.FULL_CONTENT_ENABLED and articles:
                from src.scrapers.content_scraper import FullContentScraper

                content_scraper = FullContentScraper(
                    timeout=settings.FULL_CONTENT_TIMEOUT,
                    rate_limit_delay=settings.FULL_CONTENT_RATE_LIMIT,
                    user_agent=settings.USER_AGENT
                )

                articles = content_scraper.batch_fetch(
                    articles,
                    max_workers=settings.FULL_CONTENT_MAX_WORKERS,
                    min_rss_length=settings.FULL_CONTENT_MIN_RSS_LENGTH
                )

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

    # Topic merging (if enabled)
    if settings.USE_TOPIC_MERGING:
        try:
            logger.info("Running topic merging...")
            from src.analyzers.topic_merger import TopicMerger
            from src.analyzers.llm_trend_analyzer import LLMTrendAnalyzer

            # Get all topics
            all_topics = db.get_all_topics()

            if len(all_topics) >= 2:
                # Compute centroids for all topics
                centroids = {}
                for topic in all_topics:
                    # Safely convert size to int (handle bytes from DB)
                    topic_size = int(topic.size) if topic.size and not isinstance(topic.size, bytes) else (
                        int.from_bytes(topic.size, 'big') if isinstance(topic.size, bytes) and topic.size else 0
                    )
                    if topic_size > 0:  # Skip empty topics
                        article_ids = db.get_article_ids_by_topic(topic.topic_id, limit=100)
                        if article_ids:
                            centroid = topic_modeler.compute_topic_centroid(
                                topic.topic_id, article_ids, db
                            )
                            if centroid is not None:
                                centroids[topic.topic_id] = centroid

                if len(centroids) >= 2:
                    # Initialize merger
                    llm_analyzer = LLMTrendAnalyzer() if settings.TOPIC_MERGE_USE_LLM else None
                    merger = TopicMerger(
                        db,
                        llm_analyzer=llm_analyzer,
                        similarity_threshold=settings.TOPIC_MERGE_SIMILARITY
                    )

                    # Auto-merge topics
                    merge_actions = merger.auto_merge_topics(
                        centroids,
                        use_llm=settings.TOPIC_MERGE_USE_LLM,
                        dry_run=False
                    )

                    if merge_actions:
                        logger.info(f"Merged {len(merge_actions)} topic pairs")
                    else:
                        logger.info("No topics needed merging")
                else:
                    logger.info("Not enough topics with centroids for merging")
            else:
                logger.info("Not enough topics for merging")

        except Exception as e:
            logger.error(f"Error in topic merging: {e}")

    # Calculate trends
    try:
        logger.info("Calculating trends...")
        detector = TrendDetector(db)

        # Use multi-period analysis if enabled, otherwise use standard analysis
        if settings.USE_MULTIPERIOD_ANALYSIS:
            trends = detector.calculate_trends_multiperiod(
                period_weeks=settings.MULTIPERIOD_WEEKS,
                num_periods=settings.MULTIPERIOD_COUNT,
                min_count=settings.TREND_MIN_COUNT,
                min_growth_rate=settings.TREND_MIN_GROWTH_RATE
            )
        else:
            trends = detector.calculate_trends(
                window_days=settings.TREND_WINDOW_DAYS,
                min_count=settings.TREND_MIN_COUNT,
                min_growth_rate=settings.TREND_MIN_GROWTH_RATE
            )

        # Save trends to database
        db.save_trends(trends)

        # Save trend snapshots for historical tracking
        logger.info("Saving trend snapshots...")
        centroids = {}  # Store for correlation analysis
        for trend in trends:
            try:
                topic_id = trend['topic_id']

                # Get article IDs for this topic in the current period
                article_ids = db.get_article_ids_by_topic(
                    topic_id,
                    start_date=trend['period_start'],
                    end_date=trend['period_end'],
                    limit=100
                )

                # Compute topic centroid
                centroid = None
                if article_ids:
                    centroid = topic_modeler.compute_topic_centroid(
                        topic_id, article_ids, db
                    )
                    if centroid is not None:
                        centroids[topic_id] = centroid

                # Save snapshot
                db.save_trend_snapshot(topic_id, trend, centroid)

            except Exception as e:
                logger.warning(f"Failed to save snapshot for topic {topic_id}: {e}")

        # Cross-topic correlation analysis (if enabled)
        if settings.USE_CORRELATION_ANALYSIS and len(trends) >= 2:
            try:
                logger.info("Analyzing cross-topic correlations...")
                from src.analyzers.correlation_analyzer import CrossTopicCorrelationAnalyzer

                corr_analyzer = CrossTopicCorrelationAnalyzer(db)

                # Get trending topic IDs
                trending_ids = [t['topic_id'] for t in trends if t.get('is_trending', False)]

                if len(trending_ids) >= 2:
                    # Calculate correlations
                    correlations = corr_analyzer.calculate_correlations(
                        trending_ids,
                        trends[0]['period_start'],
                        trends[0]['period_end'],
                        centroids,
                        min_correlation=settings.CORRELATION_MIN_THRESHOLD
                    )

                    if correlations:
                        # Build correlation graph
                        correlation_graph = corr_analyzer.build_correlation_graph(
                            correlations, top_n_per_topic=5
                        )

                        # Add related_trends to each trend
                        for trend in trends:
                            if trend['topic_id'] in correlation_graph:
                                trend['related_trends'] = correlation_graph[trend['topic_id']]

                        logger.info(f"Added correlation data to {len(correlation_graph)} topics")
                    else:
                        logger.info("No significant correlations found")
                else:
                    logger.info("Not enough trending topics for correlation analysis")

            except Exception as e:
                logger.error(f"Error in correlation analysis: {e}")

        # Semantic drift detection (if enabled)
        if settings.USE_DRIFT_DETECTION and centroids:
            try:
                logger.info("Detecting semantic drift...")
                from src.analyzers.drift_detector import SemanticDriftDetector

                drift_detector = SemanticDriftDetector(
                    db,
                    llm_analyzer=LLMTrendAnalyzer() if settings.USE_LLM_ENHANCEMENT else None,
                    drift_threshold=settings.DRIFT_THRESHOLD
                )

                # Detect drift for all topics with centroids
                drift_results = drift_detector.batch_detect_drift(
                    centroids,
                    lookback_days=settings.DRIFT_LOOKBACK_DAYS
                )

                if drift_results:
                    # Add drift info to trends
                    for trend in trends:
                        if trend['topic_id'] in drift_results:
                            trend['semantic_drift'] = drift_results[trend['topic_id']]

                    logger.info(f"Detected semantic drift in {len(drift_results)} topics")
                else:
                    logger.info("No significant semantic drift detected")

            except Exception as e:
                logger.error(f"Error in drift detection: {e}")

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
