"""
Semantic drift detector for tracking topic evolution over time.

Detects when a topic's content has significantly changed by comparing
current centroid embeddings with historical snapshots.
"""

from typing import Optional, Dict, List
from datetime import datetime, timedelta
import numpy as np
from loguru import logger
import json

from ..storage.database import Database
from ..storage.models import TrendSnapshot
from .llm_trend_analyzer import LLMTrendAnalyzer


class SemanticDriftDetector:
    """
    Detects semantic drift in topics over time.

    Drift occurs when a topic's content evolves significantly, which can indicate:
    - Topic evolution/maturation
    - Scope creep
    - Merging of related concepts
    - Shift in public discourse
    """

    def __init__(
        self,
        db: Database,
        llm_analyzer: Optional[LLMTrendAnalyzer] = None,
        drift_threshold: float = 0.3
    ):
        """
        Initialize the drift detector.

        Args:
            db: Database instance
            llm_analyzer: LLM analyzer for describing drift (optional)
            drift_threshold: Minimum drift score (1 - similarity) to flag as drift
        """
        self.db = db
        self.llm_analyzer = llm_analyzer or LLMTrendAnalyzer()
        self.drift_threshold = drift_threshold

    def detect_drift(
        self,
        topic_id: int,
        current_centroid: np.ndarray,
        lookback_days: int = 14,
        current_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        Detect semantic drift for a topic.

        Args:
            topic_id: Topic ID to analyze
            current_centroid: Current centroid embedding
            lookback_days: How many days to look back for comparison
            current_date: Reference date (default: now)

        Returns:
            Dict with drift info if drift detected, None otherwise
        """
        if current_date is None:
            current_date = datetime.utcnow()

        # Get closest historical snapshot
        target_date = current_date - timedelta(days=lookback_days)
        previous_snapshot = self._get_closest_snapshot(topic_id, target_date)

        if not previous_snapshot:
            logger.debug(f"No historical snapshot found for topic {topic_id}")
            return None

        # Deserialize previous centroid
        previous_centroid = self.db.deserialize_centroid(previous_snapshot)

        if previous_centroid is None:
            logger.debug(f"Could not deserialize centroid for topic {topic_id}")
            return None

        # Calculate drift score (1 - cosine similarity)
        similarity = self._cosine_similarity(current_centroid, previous_centroid)
        drift_score = 1.0 - similarity

        logger.debug(
            f"Topic {topic_id} drift: {drift_score:.3f} "
            f"(similarity: {similarity:.3f}, threshold: {self.drift_threshold:.3f})"
        )

        # Check if drift is significant
        if drift_score < self.drift_threshold:
            return None  # No significant drift

        # Drift detected - describe it
        logger.info(
            f"Semantic drift detected for topic {topic_id}: "
            f"drift_score={drift_score:.3f}"
        )

        drift_info = {
            'topic_id': topic_id,
            'drift_score': drift_score,
            'similarity': similarity,
            'comparison_date': previous_snapshot.snapshot_date,
            'days_apart': (current_date - previous_snapshot.snapshot_date).days
        }

        # Use LLM to describe the drift
        if self.llm_analyzer:
            try:
                description = self._describe_drift(
                    topic_id,
                    previous_snapshot,
                    current_date
                )
                drift_info['evolution_description'] = description
            except Exception as e:
                logger.warning(f"Failed to generate drift description: {e}")
                drift_info['evolution_description'] = "Content has evolved significantly."

        return drift_info

    def _get_closest_snapshot(
        self,
        topic_id: int,
        target_date: datetime
    ) -> Optional[TrendSnapshot]:
        """
        Get the snapshot closest to target date.

        Args:
            topic_id: Topic ID
            target_date: Target date to find snapshot near

        Returns:
            TrendSnapshot or None
        """
        # Get historical snapshots
        snapshots = self.db.get_trend_history(topic_id, limit=30)

        if not snapshots:
            return None

        # Find snapshot closest to target date
        closest_snapshot = None
        min_diff = float('inf')

        for snapshot in snapshots:
            diff = abs((snapshot.snapshot_date - target_date).total_seconds())
            if diff < min_diff:
                min_diff = diff
                closest_snapshot = snapshot

        return closest_snapshot

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1)
        """
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Clip to [0, 1]
            return float(max(0.0, min(1.0, similarity)))

        except Exception as e:
            logger.warning(f"Failed to calculate similarity: {e}")
            return 0.0

    def _describe_drift(
        self,
        topic_id: int,
        previous_snapshot: TrendSnapshot,
        current_date: datetime
    ) -> str:
        """
        Use LLM to describe how the topic has evolved.

        Args:
            topic_id: Topic ID
            previous_snapshot: Historical snapshot
            current_date: Current date

        Returns:
            Description of evolution
        """
        # Get topic metadata
        all_topics = self.db.get_all_topics()
        topic_metadata = {t.topic_id: t for t in all_topics}
        topic = topic_metadata.get(topic_id)

        if not topic:
            return "Topic content has evolved."

        # Get old articles (from snapshot period)
        old_articles = self.db.get_articles_by_topic(
            topic_id,
            start_date=previous_snapshot.period_start,
            end_date=previous_snapshot.period_end,
            limit=5
        )

        # Get recent articles
        recent_start = current_date - timedelta(days=7)
        recent_articles = self.db.get_articles_by_topic(
            topic_id,
            start_date=recent_start,
            end_date=current_date,
            limit=5
        )

        # Build LLM prompt
        prompt = self._build_drift_prompt(
            topic.topic_name,
            previous_snapshot.snapshot_date,
            [a.title for a in old_articles],
            current_date,
            [a.title for a in recent_articles]
        )

        try:
            # Get LLM response
            response = self.llm_analyzer._call_llm(prompt, max_tokens=200, temperature=0.4)

            # Parse JSON response
            result = json.loads(response)
            description = result.get('evolution_description', 'Content has evolved.')

            return description

        except json.JSONDecodeError:
            # Fallback: try to extract description from response
            logger.warning("LLM response not valid JSON, using raw response")
            return response[:200] if response else "Content has evolved significantly."

        except Exception as e:
            logger.error(f"Failed to describe drift: {e}")
            return "Topic content has evolved significantly."

    def _build_drift_prompt(
        self,
        topic_name: str,
        old_date: datetime,
        old_titles: List[str],
        new_date: datetime,
        new_titles: List[str]
    ) -> str:
        """
        Build LLM prompt for drift description.

        Args:
            topic_name: Topic name
            old_date: Date of old articles
            old_titles: Old article titles
            new_date: Date of new articles
            new_titles: New article titles

        Returns:
            Prompt string
        """
        prompt = f"""A topic has evolved over time. Describe how it has changed.

Topic: "{topic_name}"

Articles from {old_date.strftime('%Y-%m-%d')} ({len(old_titles)} samples):
{chr(10).join(f'  - {title[:100]}' for title in old_titles[:5])}

Recent articles from {new_date.strftime('%Y-%m-%d')} ({len(new_titles)} samples):
{chr(10).join(f'  - {title[:100]}' for title in new_titles[:5])}

Describe how this topic's focus or content has evolved in 1-2 sentences.

Respond ONLY with valid JSON (no markdown, no code blocks):
{{
  "evolution_description": "1-2 sentence description of how the topic evolved"
}}
"""
        return prompt

    def batch_detect_drift(
        self,
        topics_with_centroids: Dict[int, np.ndarray],
        lookback_days: int = 14
    ) -> Dict[int, Dict]:
        """
        Detect drift for multiple topics.

        Args:
            topics_with_centroids: Dict mapping topic_id to current centroid
            lookback_days: Days to look back

        Returns:
            Dict mapping topic_id to drift info (only topics with drift)
        """
        drift_results = {}

        for topic_id, centroid in topics_with_centroids.items():
            try:
                drift_info = self.detect_drift(
                    topic_id,
                    centroid,
                    lookback_days
                )

                if drift_info:
                    drift_results[topic_id] = drift_info

            except Exception as e:
                logger.warning(f"Failed to detect drift for topic {topic_id}: {e}")

        logger.info(f"Detected drift in {len(drift_results)} out of {len(topics_with_centroids)} topics")

        return drift_results
