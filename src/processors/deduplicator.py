"""
Article deduplicator using fuzzy string matching.
Identifies and removes duplicate articles based on title/content similarity.
"""

from typing import List, Dict, Tuple, Optional
from rapidfuzz import fuzz
from loguru import logger
from collections import defaultdict


class ArticleDeduplicator:
    """
    Identifies and removes duplicate articles using fuzzy matching.

    Uses title + content preview similarity to find near-duplicates that
    might have slightly different formatting or minor content variations.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the deduplicator.

        Args:
            similarity_threshold: Minimum similarity score (0-1) to consider duplicates
        """
        self.similarity_threshold = similarity_threshold

    def find_duplicates(self, articles: List[Dict]) -> Dict[int, List[int]]:
        """
        Find groups of duplicate articles.

        Args:
            articles: List of article dictionaries with 'title' and 'content'

        Returns:
            Dictionary mapping representative article index to list of duplicate indices
        """
        if not articles:
            return {}

        duplicate_groups = defaultdict(list)
        processed = set()

        for i, article1 in enumerate(articles):
            if i in processed:
                continue

            # Create comparison string (title + first 200 chars of content)
            text1 = self._create_comparison_text(article1)

            # Find all similar articles
            duplicates = []
            for j, article2 in enumerate(articles):
                if i >= j or j in processed:
                    continue

                text2 = self._create_comparison_text(article2)
                similarity = fuzz.ratio(text1, text2) / 100.0

                if similarity >= self.similarity_threshold:
                    duplicates.append(j)
                    processed.add(j)

            if duplicates:
                duplicate_groups[i] = duplicates

        return dict(duplicate_groups)

    def _create_comparison_text(self, article: Dict) -> str:
        """
        Create normalized text for comparison.

        Args:
            article: Article dictionary

        Returns:
            Normalized comparison string
        """
        title = article.get('title', '').strip().lower()
        content = article.get('content', '').strip().lower()

        # Use title + first 200 chars of content for comparison
        comparison_text = f"{title} {content[:200]}"

        # Remove extra whitespace
        comparison_text = ' '.join(comparison_text.split())

        return comparison_text

    def select_best_duplicate(
        self,
        articles: List[Dict],
        duplicate_indices: List[int],
        source_weights: Optional[Dict[int, float]] = None
    ) -> int:
        """
        Select the best article from a group of duplicates.

        Selection criteria (in order of priority):
        1. Highest source credibility weight
        2. Longest content
        3. Earliest published date

        Args:
            articles: List of all articles
            duplicate_indices: Indices of duplicate articles (including representative)
            source_weights: Optional mapping of source_id to credibility weight

        Returns:
            Index of the best article to keep
        """
        if not duplicate_indices:
            return -1

        if len(duplicate_indices) == 1:
            return duplicate_indices[0]

        # Score each duplicate
        best_idx = duplicate_indices[0]
        best_score = self._score_article(articles[best_idx], source_weights)

        for idx in duplicate_indices[1:]:
            score = self._score_article(articles[idx], source_weights)
            if score > best_score:
                best_score = score
                best_idx = idx

        return best_idx

    def _score_article(
        self,
        article: Dict,
        source_weights: Optional[Dict[int, float]] = None
    ) -> float:
        """
        Calculate a quality score for an article.

        Args:
            article: Article dictionary
            source_weights: Optional source credibility weights

        Returns:
            Quality score (higher is better)
        """
        score = 0.0

        # Source credibility weight (most important - 10x multiplier)
        if source_weights and 'source_id' in article:
            source_id = article['source_id']
            weight = source_weights.get(source_id, 1.0)
            score += weight * 10.0
        else:
            score += 10.0  # Default weight

        # Content length (secondary - prefer longer content)
        content_length = len(article.get('content', ''))
        score += min(content_length / 1000.0, 5.0)  # Cap at 5 points

        # Earlier publication date (tertiary - small bonus)
        # Note: This would require datetime comparison, keeping simple for now

        return score

    def deduplicate_batch(
        self,
        articles: List[Dict],
        source_weights: Optional[Dict[int, float]] = None
    ) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Remove duplicates from a batch of articles.

        Args:
            articles: List of article dictionaries
            source_weights: Optional source credibility weights

        Returns:
            Tuple of (deduplicated articles, metrics dict)
        """
        if not articles:
            return [], {'before': 0, 'after': 0, 'removed': 0, 'rate': 0.0}

        original_count = len(articles)
        logger.info(f"Deduplicating {original_count} articles...")

        # Find duplicate groups
        duplicate_groups = self.find_duplicates(articles)

        # Identify articles to keep
        indices_to_keep = set(range(len(articles)))

        for representative_idx, duplicate_indices in duplicate_groups.items():
            # All articles in this group (including representative)
            all_duplicates = [representative_idx] + duplicate_indices

            # Select best article to keep
            best_idx = self.select_best_duplicate(articles, all_duplicates, source_weights)

            # Remove all others
            for idx in all_duplicates:
                if idx != best_idx:
                    indices_to_keep.discard(idx)

        # Create deduplicated list
        deduplicated = [articles[i] for i in sorted(indices_to_keep)]

        removed_count = original_count - len(deduplicated)
        rate = removed_count / original_count if original_count > 0 else 0.0

        metrics = {
            'before': original_count,
            'after': len(deduplicated),
            'removed': removed_count,
            'rate': rate
        }

        logger.info(
            f"Deduplication complete: {removed_count} duplicates removed "
            f"({rate*100:.1f}% reduction)"
        )

        return deduplicated, metrics
