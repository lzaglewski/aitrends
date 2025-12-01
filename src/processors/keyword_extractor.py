import yake
import spacy
from typing import List, Tuple, Dict
from collections import Counter
from loguru import logger
from bs4 import BeautifulSoup
import re


class KeywordExtractor:
    def __init__(self, language: str = 'pl'):
        self.language = language
        self.nlp = None
        self._load_spacy_model()

    def _load_spacy_model(self):
        """Load spaCy model for Polish."""
        try:
            self.nlp = spacy.load('pl_core_news_lg')
            logger.info("Loaded spaCy model: pl_core_news_lg")
        except OSError:
            logger.warning("Polish spaCy model not found. Install with: python -m spacy download pl_core_news_lg")
            self.nlp = None

    def _clean_text(self, text: str) -> str:
        """Clean HTML and extra whitespace from text."""
        # Remove HTML tags
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def extract_yake(
        self,
        text: str,
        max_keywords: int = 20,
        max_ngram_size: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Extract keywords using YAKE (unsupervised).

        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords
            max_ngram_size: Maximum n-gram size (1-3)

        Returns:
            List of tuples (keyword, score)
        """
        text = self._clean_text(text)

        try:
            kw_extractor = yake.KeywordExtractor(
                lan=self.language,
                n=max_ngram_size,
                dedupLim=0.7,
                top=max_keywords,
                features=None
            )

            keywords = kw_extractor.extract_keywords(text)

            # YAKE returns lower scores for better keywords, so invert them
            normalized = [(kw, 1.0 - score) for kw, score in keywords]

            logger.debug(f"Extracted {len(normalized)} keywords with YAKE")
            return normalized

        except Exception as e:
            logger.error(f"Error extracting keywords with YAKE: {e}")
            return []

    def extract_spacy(
        self,
        text: str,
        max_keywords: int = 20
    ) -> List[Tuple[str, float]]:
        """
        Extract keywords using spaCy (entities and noun chunks).

        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords

        Returns:
            List of tuples (keyword, score)
        """
        if not self.nlp:
            logger.warning("spaCy model not loaded, skipping spaCy extraction")
            return []

        text = self._clean_text(text)

        try:
            doc = self.nlp(text[:1000000])  # Limit text length for performance

            # Extract named entities
            entities = [ent.text.lower().strip() for ent in doc.ents]

            # Extract noun chunks
            noun_chunks = [chunk.text.lower().strip() for chunk in doc.noun_chunks]

            # Combine and count
            all_keywords = entities + noun_chunks
            keyword_counts = Counter(all_keywords)

            # Filter out single characters and too long phrases
            filtered = {
                kw: count for kw, count in keyword_counts.items()
                if len(kw) > 2 and len(kw.split()) <= 4
            }

            # Get most common
            top_keywords = Counter(filtered).most_common(max_keywords)

            # Normalize scores
            max_count = max([count for _, count in top_keywords]) if top_keywords else 1
            normalized = [(kw, count / max_count) for kw, count in top_keywords]

            logger.debug(f"Extracted {len(normalized)} keywords with spaCy")
            return normalized

        except Exception as e:
            logger.error(f"Error extracting keywords with spaCy: {e}")
            return []

    def extract_all(
        self,
        text: str,
        max_keywords: int = 20
    ) -> List[Tuple[str, float, str]]:
        """
        Extract keywords using all methods and combine results.

        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords per method

        Returns:
            List of tuples (keyword, score, method)
        """
        all_keywords = []

        # YAKE extraction
        yake_keywords = self.extract_yake(text, max_keywords)
        for kw, score in yake_keywords:
            all_keywords.append((kw, score, 'yake'))

        # spaCy extraction
        spacy_keywords = self.extract_spacy(text, max_keywords)
        for kw, score in spacy_keywords:
            all_keywords.append((kw, score, 'spacy'))

        logger.debug(f"Total keywords extracted: {len(all_keywords)}")
        return all_keywords

    def get_top_keywords(
        self,
        keywords: List[Tuple[str, float, str]],
        top_n: int = 20
    ) -> List[Tuple[str, float, str]]:
        """
        Get top N keywords by aggregating scores across methods.

        Args:
            keywords: List of tuples (keyword, score, method)
            top_n: Number of top keywords to return

        Returns:
            List of top keywords
        """
        # Aggregate scores by keyword
        keyword_scores: Dict[str, List[float]] = {}

        for kw, score, method in keywords:
            if kw not in keyword_scores:
                keyword_scores[kw] = []
            keyword_scores[kw].append(score)

        # Calculate average score
        avg_scores = {
            kw: sum(scores) / len(scores)
            for kw, scores in keyword_scores.items()
        }

        # Sort by score
        sorted_keywords = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)

        # Return top N with their best method
        result = []
        for kw, avg_score in sorted_keywords[:top_n]:
            # Find which method gave this keyword
            method = next(m for k, s, m in keywords if k == kw)
            result.append((kw, avg_score, method))

        return result


def load_polish_stopwords() -> List[str]:
    """Load Polish stopwords."""
    # Common Polish stopwords
    stopwords = [
        'i', 'w', 'na', 'z', 'do', 'się', 'nie', 'to', 'o', 'a',
        'ale', 'jak', 'że', 'po', 'dla', 'by', 'ze', 'od', 'przy',
        'czy', 'lub', 'oraz', 'za', 'tak', 'też', 'bardzo', 'już',
        'może', 'można', 'więc', 'bo', 'jest', 'są', 'będzie', 'był',
        'była', 'było', 'były', 'być', 'ma', 'mają', 'ma'
    ]

    try:
        # Try to load from file if exists
        with open('data/stopwords_pl.txt', 'r', encoding='utf-8') as f:
            file_stopwords = [line.strip() for line in f if line.strip()]
            stopwords.extend(file_stopwords)
    except FileNotFoundError:
        pass

    return list(set(stopwords))
