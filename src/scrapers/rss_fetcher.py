import feedparser
import time
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
import requests
from time import mktime

from ..config import settings


class RSSFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': settings.USER_AGENT
        }

    def fetch_feed(self, feed_url: str, max_entries: Optional[int] = None) -> List[Dict]:
        """
        Fetch articles from RSS feed.

        Args:
            feed_url: URL of the RSS feed
            max_entries: Maximum number of entries to return

        Returns:
            List of article dictionaries
        """
        logger.info(f"Fetching RSS feed: {feed_url}")

        try:
            # Add custom headers if possible
            response = requests.get(
                feed_url,
                headers=self.headers,
                timeout=settings.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(f"RSS feed has issues: {feed_url}")
                if hasattr(feed, 'bozo_exception'):
                    logger.debug(f"Feed error: {feed.bozo_exception}")

            articles = []
            max_entries = max_entries or settings.MAX_ARTICLES_PER_SOURCE

            for entry in feed.entries[:max_entries]:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from {feed_url}")
            return articles

        except requests.RequestException as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing RSS feed {feed_url}: {e}")
            return []

    def _parse_entry(self, entry) -> Optional[Dict]:
        """
        Parse RSS entry into article dictionary.

        Args:
            entry: feedparser entry object

        Returns:
            Article dictionary or None
        """
        try:
            # Extract URL
            url = entry.get('link', '')
            if not url:
                return None

            # Extract title
            title = entry.get('title', 'Untitled')

            # Extract content (try multiple fields)
            content = ''
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value
            elif hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description

            # Extract published date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_date = datetime.fromtimestamp(mktime(entry.updated_parsed))

            # Extract author
            author = entry.get('author', None)

            article = {
                'url': url,
                'title': title,
                'content': content,
                'published_date': published_date,
                'author': author
            }

            return article

        except Exception as e:
            logger.debug(f"Error parsing RSS entry: {e}")
            return None

    def fetch_multiple_feeds(
        self,
        feed_urls: List[str],
        delay_seconds: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        Fetch multiple RSS feeds with rate limiting.

        Args:
            feed_urls: List of RSS feed URLs
            delay_seconds: Delay between requests (default from settings)

        Returns:
            Dict mapping feed URL to list of articles
        """
        delay = delay_seconds or settings.REQUEST_DELAY_SECONDS
        results = {}

        for i, feed_url in enumerate(feed_urls):
            articles = self.fetch_feed(feed_url)
            results[feed_url] = articles

            # Rate limiting (except for last request)
            if i < len(feed_urls) - 1:
                time.sleep(delay)

        return results
