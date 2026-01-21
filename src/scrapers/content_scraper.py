"""
Full content scraper for fetching complete article text.

Uses trafilatura to extract clean article content from web pages when
RSS feeds provide only summaries or truncated content.
"""

from typing import List, Dict, Optional
import trafilatura
import requests
from loguru import logger
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class FullContentScraper:
    """
    Fetches full article content from URLs when RSS feeds provide insufficient content.

    Uses trafilatura for high-quality content extraction and includes rate limiting
    to be respectful to source servers.
    """

    def __init__(
        self,
        timeout: int = 30,
        rate_limit_delay: float = 1.0,
        user_agent: Optional[str] = None
    ):
        """
        Initialize the content scraper.

        Args:
            timeout: Request timeout in seconds
            rate_limit_delay: Minimum delay between requests to same domain (seconds)
            user_agent: Custom user agent string
        """
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = user_agent or "Ad-Trends-Monitor/1.0 (Educational purpose)"
        self.last_request_time = {}  # Domain -> timestamp

    def fetch_full_content(
        self,
        url: str,
        fallback_content: str,
        min_rss_length: int = 500
    ) -> Dict[str, any]:
        """
        Fetch full content from a URL if RSS content is too short.

        Args:
            url: Article URL
            fallback_content: RSS feed content to use as fallback
            min_rss_length: Minimum length to consider RSS content sufficient

        Returns:
            Dict with keys: content, success, error (if any)
        """
        # Check if RSS content is already sufficient
        if not self._should_fetch_full_content(fallback_content, min_rss_length):
            return {
                'content': fallback_content,
                'success': True,
                'used_full_scrape': False
            }

        # Extract domain for rate limiting
        domain = self._extract_domain(url)

        # Rate limiting
        self._rate_limit_check(domain)

        try:
            # Fetch HTML
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, timeout=self.timeout, headers=headers)
            response.raise_for_status()

            # Extract content with trafilatura
            extracted = trafilatura.extract(
                response.content,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )

            if extracted and len(extracted) > min_rss_length:
                logger.debug(f"Successfully scraped full content from {url[:50]}...")
                return {
                    'content': extracted,
                    'success': True,
                    'used_full_scrape': True
                }
            else:
                # Extraction failed or too short, use fallback
                logger.warning(f"Trafilatura extraction insufficient for {url[:50]}..., using RSS content")
                return {
                    'content': fallback_content,
                    'success': True,
                    'used_full_scrape': False
                }

        except requests.Timeout:
            logger.warning(f"Timeout fetching {url[:50]}..., using RSS content")
            return {
                'content': fallback_content,
                'success': True,
                'used_full_scrape': False,
                'error': 'timeout'
            }

        except requests.RequestException as e:
            logger.warning(f"Request error for {url[:50]}...: {e}, using RSS content")
            return {
                'content': fallback_content,
                'success': True,
                'used_full_scrape': False,
                'error': str(e)
            }

        except Exception as e:
            logger.error(f"Unexpected error scraping {url[:50]}...: {e}, using RSS content")
            return {
                'content': fallback_content,
                'success': True,
                'used_full_scrape': False,
                'error': str(e)
            }

    def _should_fetch_full_content(self, rss_content: str, min_length: int) -> bool:
        """
        Determine if full content fetching is needed.

        Args:
            rss_content: Content from RSS feed
            min_length: Minimum length threshold

        Returns:
            True if full content should be fetched
        """
        if not rss_content:
            return True

        # Check length
        if len(rss_content) < min_length:
            return True

        # Check for common truncation indicators
        truncation_indicators = [
            '...',
            '[...]',
            'Read more',
            'Continue reading',
            'Full article at'
        ]

        content_lower = rss_content.lower()
        for indicator in truncation_indicators:
            if indicator.lower() in content_lower:
                return True

        return False

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL for rate limiting.

        Args:
            url: Full URL

        Returns:
            Domain string
        """
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

    def _rate_limit_check(self, domain: str):
        """
        Enforce rate limiting for a domain.

        Args:
            domain: Domain to check
        """
        if domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {domain}")
                time.sleep(sleep_time)

        self.last_request_time[domain] = time.time()

    def batch_fetch(
        self,
        articles: List[Dict],
        max_workers: int = 5,
        min_rss_length: int = 500
    ) -> List[Dict]:
        """
        Fetch full content for a batch of articles in parallel.

        Args:
            articles: List of article dicts with 'url' and 'content' keys
            max_workers: Maximum number of parallel workers
            min_rss_length: Minimum RSS content length threshold

        Returns:
            List of articles with updated content
        """
        if not articles:
            return []

        logger.info(f"Fetching full content for {len(articles)} articles...")

        # Track statistics
        stats = {
            'total': len(articles),
            'full_scraped': 0,
            'rss_used': 0,
            'errors': 0
        }

        updated_articles = []

        # Process articles with thread pool
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_article = {
                executor.submit(
                    self.fetch_full_content,
                    article['url'],
                    article.get('content', ''),
                    min_rss_length
                ): article
                for article in articles
            }

            # Collect results as they complete
            for future in as_completed(future_to_article):
                article = future_to_article[future]

                try:
                    result = future.result()

                    # Update article content
                    article['content'] = result['content']

                    # Update stats
                    if result.get('used_full_scrape'):
                        stats['full_scraped'] += 1
                    else:
                        stats['rss_used'] += 1

                    if 'error' in result:
                        stats['errors'] += 1

                    updated_articles.append(article)

                except Exception as e:
                    logger.error(f"Error processing article {article['url'][:50]}...: {e}")
                    stats['errors'] += 1
                    updated_articles.append(article)  # Keep original

        logger.info(
            f"Full content scraping complete: "
            f"{stats['full_scraped']} scraped, "
            f"{stats['rss_used']} RSS used, "
            f"{stats['errors']} errors"
        )

        return updated_articles
