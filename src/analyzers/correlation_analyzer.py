"""
Cross-topic correlation analyzer.

Identifies relationships between topics based on:
- Source overlap (same sources cover both topics)
- Temporal correlation (topics trend together over time)
- Semantic proximity (topics have similar content)
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from loguru import logger
from collections import defaultdict

from ..storage.database import Database


class CrossTopicCorrelationAnalyzer:
    """
    Analyzes correlations and relationships between topics.

    Helps identify:
    - Related trends that often appear together
    - Topics that are semantically similar but not duplicates
    - Emerging topic clusters
    """

    def __init__(self, db: Database):
        """
        Initialize the correlation analyzer.

        Args:
            db: Database instance
        """
        self.db = db

    def calculate_correlations(
        self,
        topic_ids: List[int],
        period_start: datetime,
        period_end: datetime,
        centroids: Optional[Dict[int, np.ndarray]] = None,
        min_correlation: float = 0.3
    ) -> Dict[Tuple[int, int], Dict]:
        """
        Calculate correlations between all topic pairs.

        Args:
            topic_ids: List of topic IDs to analyze
            period_start: Start of analysis period
            period_end: End of analysis period
            centroids: Optional dict of topic centroids for semantic similarity
            min_correlation: Minimum combined correlation to include

        Returns:
            Dict mapping (topic_id_1, topic_id_2) to correlation metrics
        """
        if len(topic_ids) < 2:
            logger.warning("Need at least 2 topics for correlation analysis")
            return {}

        logger.info(f"🔗 Analyzing correlations for {len(topic_ids)} topics...")

        correlations = {}

        # Analyze all pairs
        for i in range(len(topic_ids)):
            for j in range(i + 1, len(topic_ids)):
                topic1_id = topic_ids[i]
                topic2_id = topic_ids[j]

                # Calculate different correlation metrics
                source_overlap = self._calculate_source_overlap(
                    topic1_id, topic2_id, period_start, period_end
                )

                temporal_corr = self._calculate_temporal_correlation(
                    topic1_id, topic2_id, period_start, period_end
                )

                semantic_prox = 0.0
                if centroids and topic1_id in centroids and topic2_id in centroids:
                    semantic_prox = self._calculate_semantic_proximity(
                        centroids[topic1_id], centroids[topic2_id]
                    )

                # Combined correlation (weighted average)
                combined = (
                    source_overlap * 0.3 +
                    temporal_corr * 0.4 +
                    semantic_prox * 0.3
                )

                # Only include if above threshold
                if combined >= min_correlation:
                    correlations[(topic1_id, topic2_id)] = {
                        'source_overlap': source_overlap,
                        'temporal_correlation': temporal_corr,
                        'semantic_proximity': semantic_prox,
                        'combined_score': combined
                    }

        logger.info(f"✅ Found {len(correlations)} correlated topic pairs")

        return correlations

    def _calculate_source_overlap(
        self,
        topic1_id: int,
        topic2_id: int,
        start: datetime,
        end: datetime
    ) -> float:
        """
        Calculate overlap in sources that cover both topics.

        Args:
            topic1_id: First topic ID
            topic2_id: Second topic ID
            start: Period start
            end: Period end

        Returns:
            Overlap score (0-1)
        """
        with self.db.get_session() as session:
            from ..storage.models import Article

            # Get source IDs for each topic
            sources1 = set(
                row[0] for row in session.query(Article.source_id).filter(
                    Article.topic_id == topic1_id,
                    Article.published_date >= start,
                    Article.published_date <= end
                ).distinct().all()
            )

            sources2 = set(
                row[0] for row in session.query(Article.source_id).filter(
                    Article.topic_id == topic2_id,
                    Article.published_date >= start,
                    Article.published_date <= end
                ).distinct().all()
            )

            if not sources1 or not sources2:
                return 0.0

            # Jaccard similarity
            intersection = len(sources1 & sources2)
            union = len(sources1 | sources2)

            overlap = intersection / union if union > 0 else 0.0

            return overlap

    def _calculate_temporal_correlation(
        self,
        topic1_id: int,
        topic2_id: int,
        start: datetime,
        end: datetime
    ) -> float:
        """
        Calculate Pearson correlation of daily article counts.

        Args:
            topic1_id: First topic ID
            topic2_id: Second topic ID
            start: Period start
            end: Period end

        Returns:
            Correlation coefficient (0-1, absolute value)
        """
        # Get daily counts for both topics
        counts1 = self._get_daily_counts(topic1_id, start, end)
        counts2 = self._get_daily_counts(topic2_id, start, end)

        if not counts1 or not counts2:
            return 0.0

        # Align dates
        all_dates = sorted(set(counts1.keys()) | set(counts2.keys()))

        if len(all_dates) < 3:
            return 0.0  # Need at least 3 points for meaningful correlation

        # Build aligned count series
        series1 = [counts1.get(date, 0) for date in all_dates]
        series2 = [counts2.get(date, 0) for date in all_dates]

        # Calculate Pearson correlation
        try:
            corr_matrix = np.corrcoef(series1, series2)
            correlation = abs(corr_matrix[0, 1])  # Use absolute value

            # Handle NaN (happens when one series has no variance)
            if np.isnan(correlation):
                return 0.0

            return float(correlation)

        except Exception as e:
            logger.warning(f"Failed to calculate temporal correlation: {e}")
            return 0.0

    def _get_daily_counts(
        self,
        topic_id: int,
        start: datetime,
        end: datetime
    ) -> Dict[str, int]:
        """
        Get daily article counts for a topic.

        Args:
            topic_id: Topic ID
            start: Period start
            end: Period end

        Returns:
            Dict mapping date string to count
        """
        # Ensure start and end are datetime objects
        if isinstance(start, str):
            start = datetime.fromisoformat(start.replace('Z', '+00:00'))
        if isinstance(end, str):
            end = datetime.fromisoformat(end.replace('Z', '+00:00'))

        with self.db.get_session() as session:
            from ..storage.models import Article
            from sqlalchemy import func, cast, Date

            results = (
                session.query(
                    cast(Article.published_date, Date).label('date'),
                    func.count(Article.id).label('count')
                )
                .filter(
                    Article.topic_id == topic_id,
                    Article.published_date >= start,
                    Article.published_date <= end
                )
                .group_by(cast(Article.published_date, Date))
                .all()
            )

            counts = {
                str(date): count
                for date, count in results
            }

            return counts

    def _calculate_semantic_proximity(
        self,
        centroid1: np.ndarray,
        centroid2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between topic centroids.

        Args:
            centroid1: First topic centroid
            centroid2: Second topic centroid

        Returns:
            Similarity score (0-1)
        """
        try:
            dot_product = np.dot(centroid1, centroid2)
            norm1 = np.linalg.norm(centroid1)
            norm2 = np.linalg.norm(centroid2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Clip to [0, 1] range
            return float(max(0.0, min(1.0, similarity)))

        except Exception as e:
            logger.warning(f"Failed to calculate semantic proximity: {e}")
            return 0.0

    def build_correlation_graph(
        self,
        correlations: Dict[Tuple[int, int], Dict],
        top_n_per_topic: int = 5
    ) -> Dict[int, List[Dict]]:
        """
        Build a graph of correlated topics.

        For each topic, list its top N most correlated topics.

        Args:
            correlations: Correlation dict from calculate_correlations()
            top_n_per_topic: Max number of related topics per topic

        Returns:
            Dict mapping topic_id to list of related topic dicts
        """
        # Build adjacency structure
        adjacency = defaultdict(list)

        # Get topic metadata
        all_topics = self.db.get_all_topics()
        topic_metadata = {t.topic_id: t for t in all_topics}

        for (topic1_id, topic2_id), metrics in correlations.items():
            # Add edge in both directions
            topic2_name = topic_metadata.get(topic2_id)
            if topic2_name:
                adjacency[topic1_id].append({
                    'topic_id': topic2_id,
                    'topic_name': topic2_name.topic_name,
                    'correlation_strength': metrics['combined_score'],
                    'source_overlap': metrics['source_overlap'],
                    'temporal_correlation': metrics['temporal_correlation'],
                    'semantic_proximity': metrics['semantic_proximity']
                })

            topic1_name = topic_metadata.get(topic1_id)
            if topic1_name:
                adjacency[topic2_id].append({
                    'topic_id': topic1_id,
                    'topic_name': topic1_name.topic_name,
                    'correlation_strength': metrics['combined_score'],
                    'source_overlap': metrics['source_overlap'],
                    'temporal_correlation': metrics['temporal_correlation'],
                    'semantic_proximity': metrics['semantic_proximity']
                })

        # Sort each topic's related topics by correlation strength
        correlation_graph = {}
        for topic_id, related in adjacency.items():
            sorted_related = sorted(
                related,
                key=lambda x: x['correlation_strength'],
                reverse=True
            )[:top_n_per_topic]

            correlation_graph[topic_id] = sorted_related

        logger.info(
            f"Built correlation graph: {len(correlation_graph)} topics "
            f"with related topics"
        )

        return correlation_graph

    def get_topic_clusters(
        self,
        correlations: Dict[Tuple[int, int], Dict],
        min_cluster_size: int = 2
    ) -> List[List[int]]:
        """
        Identify clusters of highly correlated topics.

        Uses simple connected components algorithm.

        Args:
            correlations: Correlation dict
            min_cluster_size: Minimum topics per cluster

        Returns:
            List of clusters (each cluster is a list of topic IDs)
        """
        # Build adjacency list
        adjacency = defaultdict(set)
        for (topic1_id, topic2_id), _ in correlations.items():
            adjacency[topic1_id].add(topic2_id)
            adjacency[topic2_id].add(topic1_id)

        # Find connected components
        visited = set()
        clusters = []

        def dfs(node, cluster):
            visited.add(node)
            cluster.append(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, cluster)

        for topic_id in adjacency.keys():
            if topic_id not in visited:
                cluster = []
                dfs(topic_id, cluster)
                if len(cluster) >= min_cluster_size:
                    clusters.append(cluster)

        logger.info(f"Identified {len(clusters)} topic clusters")

        return clusters
