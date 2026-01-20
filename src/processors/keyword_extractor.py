"""
Topic Extractor - Replaces keyword extraction with topic-based extraction.

This module extracts semantic topics from article content instead of
individual keywords, focusing on thematic trends rather than specific terms.
"""

from typing import List, Tuple
from loguru import logger
from bs4 import BeautifulSoup
import re


class TopicExtractor:
    """
    Extracts topics from article content using simple text analysis.

    Note: This is a lightweight version for individual articles.
    The main topic modeling happens in TopicModeler using BERTopic across
    multiple articles at once.
    """

    def __init__(self, language: str = 'multilingual'):
        """
        Initialize the topic extractor.

        Args:
            language: Language for processing ('multilingual', 'en', 'pl')
        """
        self.language = language

    def _clean_text(self, text: str) -> str:
        """
        Clean HTML and extra whitespace from text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove HTML tags
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()

        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove RSS feed artifacts
        text = re.sub(r'\bappeared\s+(?:in|on|at)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bpost\s+appeared\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bsource:\s*\S+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bvia\s+\S+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bread more:?\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bcontinue reading\b', '', text, flags=re.IGNORECASE)

        # Remove standalone dates (e.g., "December 9", "Dec 9, 2025")
        text = re.sub(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,\s*\d{4})?\b', '', text, flags=re.IGNORECASE)

        # Remove standalone numbers (likely metadata)
        text = re.sub(r'\b\d{4}\b', '', text)  # Years
        text = re.sub(r'\b\d{1,2}:\d{2}\b', '', text)  # Times

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def extract_text(self, content: str) -> str:
        """
        Extract and clean text from article content.

        Args:
            content: Raw article content

        Returns:
            Cleaned text ready for topic modeling
        """
        cleaned = self._clean_text(content)

        logger.debug(f"Extracted {len(cleaned)} characters of clean text")

        return cleaned

    def get_article_preview(self, content: str, max_length: int = 500) -> str:
        """
        Get a preview of the article for display purposes.

        Args:
            content: Article content
            max_length: Maximum preview length

        Returns:
            Preview text
        """
        cleaned = self._clean_text(content)

        if len(cleaned) <= max_length:
            return cleaned

        # Truncate at word boundary
        truncated = cleaned[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > 0:
            truncated = truncated[:last_space]

        return truncated + '...'


# Backward compatibility - keep the old name but with deprecation warning
class KeywordExtractor(TopicExtractor):
    """
    DEPRECATED: Use TopicExtractor instead.

    This class is kept for backward compatibility but just wraps TopicExtractor.
    """

    def __init__(self, language: str = 'multilingual'):
        logger.warning(
            "KeywordExtractor is deprecated. Use TopicExtractor instead. "
            "The system now uses BERTopic for semantic topic modeling."
        )
        super().__init__(language=language)

    def extract_all(self, text: str, max_keywords: int = 20) -> List[Tuple[str, float, str]]:
        """
        DEPRECATED: Returns empty list.

        Topic extraction now happens in TopicModeler across multiple documents.
        Use TopicExtractor.extract_text() to prepare text for topic modeling.
        """
        logger.warning(
            "extract_all() is deprecated. Use TopicExtractor.extract_text() "
            "to prepare text for topic modeling with TopicModeler."
        )
        return []

    def get_top_keywords(self, keywords: List, top_n: int = 20) -> List:
        """DEPRECATED: Returns empty list."""
        logger.warning("get_top_keywords() is deprecated.")
        return []
