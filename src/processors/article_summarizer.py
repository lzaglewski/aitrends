"""
Article Summarizer - Uses LLM to generate concise summaries for better clustering.
"""

from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from loguru import logger
import json
import os
import time

from ..config import settings
from ..storage.database import Database


class ArticleSummarizer:
    """
    Generates LLM-based summaries for articles to improve BERTopic clustering.

    The embedding model used by BERTopic has a 128 token limit, so full articles
    get truncated. By generating 2-3 sentence summaries focused on the topic/trend,
    we can capture the essential meaning within the token limit.
    """

    SYSTEM_PROMPT = """You are an expert at summarizing articles about AI, marketing, and technology trends.

Your task:
1. Create a 2-3 sentence summary focused on the main topic or trend discussed
2. Determine if the article is relevant for trend analysis

Mark is_trend_relevant=false if the article is:
- A job posting or hiring announcement
- An event invitation or conference announcement
- A press release about company financials without broader industry implications
- Product documentation or how-to guide without trend context
- Purely promotional content with no industry insights

Output JSON: {"summary": "...", "is_trend_relevant": true/false, "reason": "..."}"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the ArticleSummarizer.

        Args:
            api_key: OpenAI API key (if None, reads from env/config)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning("No OpenAI API key provided. Article summarization will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"ArticleSummarizer initialized with model: {settings.LLM_MODEL}")

    def summarize_article(
        self,
        title: str,
        content: str,
        max_retries: int = None
    ) -> Tuple[Optional[str], bool, Optional[str]]:
        """
        Generate a summary for a single article.

        Args:
            title: Article title
            content: Article content
            max_retries: Maximum retry attempts (default from config)

        Returns:
            Tuple of (summary, is_trend_relevant, reason)
            Returns (None, True, None) on failure
        """
        if not self.client:
            logger.warning("LLM client not initialized, skipping summarization")
            return None, True, None

        max_retries = max_retries or settings.LLM_SUMMARY_MAX_RETRIES

        # Truncate content if too long
        truncated_content = content[:settings.LLM_SUMMARY_MAX_CONTENT_CHARS]
        if len(content) > settings.LLM_SUMMARY_MAX_CONTENT_CHARS:
            truncated_content += "..."

        user_prompt = f"""Article Title: {title}

Article Content:
{truncated_content}

Generate a 2-3 sentence summary and determine trend relevance."""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=300,
                    response_format={"type": "json_object"}
                )

                result = response.choices[0].message.content
                parsed = json.loads(result)

                summary = parsed.get("summary", "")
                is_trend_relevant = parsed.get("is_trend_relevant", True)
                reason = parsed.get("reason", "")

                logger.debug(f"Summarized: '{title[:50]}...' -> relevant={is_trend_relevant}")

                return summary, is_trend_relevant, reason

            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Brief delay before retry
                continue

            except Exception as e:
                logger.warning(f"Error summarizing article (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff
                    delay = (2 ** attempt) * settings.LLM_SUMMARY_DELAY_SECONDS
                    time.sleep(delay)
                continue

        logger.error(f"Failed to summarize article after {max_retries} attempts: {title[:50]}")
        return None, True, None

    def batch_summarize(
        self,
        db: Database,
        batch_size: int = None,
        delay_seconds: float = None
    ) -> Dict[str, int]:
        """
        Process a batch of articles that don't have summaries yet.

        Args:
            db: Database instance
            batch_size: Number of articles to process (default from config)
            delay_seconds: Delay between API calls (default from config)

        Returns:
            Dict with processing statistics
        """
        if not self.client:
            logger.warning("LLM client not initialized, skipping batch summarization")
            return {"processed": 0, "summarized": 0, "filtered": 0, "failed": 0}

        batch_size = batch_size or settings.LLM_SUMMARY_BATCH_SIZE
        delay_seconds = delay_seconds or settings.LLM_SUMMARY_DELAY_SECONDS

        # Get articles without summaries
        articles = db.get_articles_without_summary(limit=batch_size)

        if not articles:
            logger.info("No articles need summarization")
            return {"processed": 0, "summarized": 0, "filtered": 0, "failed": 0}

        logger.info(f"Processing {len(articles)} articles for summarization...")

        stats = {
            "processed": 0,
            "summarized": 0,
            "filtered": 0,  # Articles marked as not trend-relevant
            "failed": 0
        }

        for i, article in enumerate(articles):
            try:
                # Generate summary
                summary, is_trend_relevant, reason = self.summarize_article(
                    title=article.title,
                    content=article.content
                )

                stats["processed"] += 1

                if summary:
                    # Update article in database
                    db.update_article_summary(
                        article_id=article.id,
                        summary=summary,
                        is_trend_relevant=is_trend_relevant
                    )

                    if is_trend_relevant:
                        stats["summarized"] += 1
                        logger.debug(f"[{i+1}/{len(articles)}] Summarized: {article.title[:50]}...")
                    else:
                        stats["filtered"] += 1
                        logger.info(f"[{i+1}/{len(articles)}] Filtered (not trend): {article.title[:50]}... - {reason}")
                else:
                    stats["failed"] += 1
                    logger.warning(f"[{i+1}/{len(articles)}] Failed: {article.title[:50]}...")

                # Rate limiting delay
                if i < len(articles) - 1:
                    time.sleep(delay_seconds)

            except Exception as e:
                stats["failed"] += 1
                logger.error(f"Error processing article {article.id}: {e}")
                continue

        logger.info(f"Summarization complete: {stats['summarized']} summarized, "
                   f"{stats['filtered']} filtered, {stats['failed']} failed")

        return stats


def run_summarization_pipeline(db: Database) -> Dict[str, int]:
    """
    Convenience function to run the summarization pipeline.
    Processes ALL articles without summaries (in batches).

    Args:
        db: Database instance

    Returns:
        Processing statistics (totals across all batches)
    """
    if not settings.USE_LLM_SUMMARIZATION:
        logger.info("LLM summarization disabled in config")
        return {"processed": 0, "summarized": 0, "filtered": 0, "failed": 0}

    summarizer = ArticleSummarizer()

    if not summarizer.client:
        logger.warning("LLM client not initialized, skipping summarization")
        return {"processed": 0, "summarized": 0, "filtered": 0, "failed": 0}

    # Process all articles in batches until none left
    total_stats = {"processed": 0, "summarized": 0, "filtered": 0, "failed": 0}
    batch_num = 0

    while True:
        batch_num += 1
        articles = db.get_articles_without_summary(limit=settings.LLM_SUMMARY_BATCH_SIZE)

        if not articles:
            break

        logger.info(f"📦 Batch {batch_num}: Processing {len(articles)} articles...")
        batch_stats = summarizer.batch_summarize(db, batch_size=len(articles))

        # Accumulate stats
        for key in total_stats:
            total_stats[key] += batch_stats[key]

        # Safety check - if no progress, break to avoid infinite loop
        if batch_stats["processed"] == 0:
            break

    return total_stats
