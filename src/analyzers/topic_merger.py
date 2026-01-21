"""
Topic merger for consolidating duplicate or highly similar topics.

Uses semantic similarity and LLM validation to identify and merge topics
that represent the same underlying trend.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from loguru import logger
import json

from ..storage.database import Database
from .llm_trend_analyzer import LLMTrendAnalyzer


class TopicMerger:
    """
    Identifies and merges duplicate or highly similar topics.

    Uses two-stage approach:
    1. Semantic similarity: Find candidates based on centroid cosine similarity
    2. LLM validation: Use LLM to decide if topics should actually be merged
    """

    def __init__(
        self,
        db: Database,
        llm_analyzer: Optional[LLMTrendAnalyzer] = None,
        similarity_threshold: float = 0.85
    ):
        """
        Initialize the topic merger.

        Args:
            db: Database instance
            llm_analyzer: LLM analyzer for merge decisions (optional)
            similarity_threshold: Minimum cosine similarity for merge candidates
        """
        self.db = db
        self.llm_analyzer = llm_analyzer or LLMTrendAnalyzer()
        self.similarity_threshold = similarity_threshold

    def find_merge_candidates(
        self,
        topic_centroids: Dict[int, np.ndarray]
    ) -> List[Tuple[int, int, float]]:
        """
        Find topic pairs that are candidates for merging based on similarity.

        Args:
            topic_centroids: Dict mapping topic_id to centroid embedding

        Returns:
            List of tuples (topic_id_1, topic_id_2, similarity_score)
        """
        if not topic_centroids or len(topic_centroids) < 2:
            return []

        candidates = []
        topic_ids = list(topic_centroids.keys())

        # Compare all pairs
        for i in range(len(topic_ids)):
            for j in range(i + 1, len(topic_ids)):
                topic_id_1 = topic_ids[i]
                topic_id_2 = topic_ids[j]

                centroid_1 = topic_centroids[topic_id_1]
                centroid_2 = topic_centroids[topic_id_2]

                # Calculate cosine similarity
                similarity = self._cosine_similarity(centroid_1, centroid_2)

                if similarity >= self.similarity_threshold:
                    candidates.append((topic_id_1, topic_id_2, similarity))

        # Sort by similarity (highest first)
        candidates.sort(key=lambda x: x[2], reverse=True)

        logger.info(
            f"🔍 Found {len(candidates)} merge candidates "
            f"(similarity >= {self.similarity_threshold:.2f})"
        )

        return candidates

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def should_merge_topics(
        self,
        topic1_id: int,
        topic2_id: int
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Use LLM to decide if two topics should be merged.

        Args:
            topic1_id: First topic ID
            topic2_id: Second topic ID

        Returns:
            Tuple of (should_merge, reason, merged_name)
        """
        # Get topic metadata
        all_topics = self.db.get_all_topics()
        topic_metadata = {t.topic_id: t for t in all_topics}

        topic1 = topic_metadata.get(topic1_id)
        topic2 = topic_metadata.get(topic2_id)

        if not topic1 or not topic2:
            logger.warning(f"Topic metadata not found for {topic1_id} or {topic2_id}")
            return False, "Missing metadata", None

        # Get sample articles from each topic
        articles1 = self.db.get_articles_by_topic(topic1_id, limit=5)
        articles2 = self.db.get_articles_by_topic(topic2_id, limit=5)

        # Parse top words
        try:
            words1 = json.loads(topic1.top_words)
        except:
            words1 = []

        try:
            words2 = json.loads(topic2.top_words)
        except:
            words2 = []

        # Build LLM prompt
        prompt = self._build_merge_prompt(
            topic1.topic_name, words1, topic1.size, [a.title for a in articles1],
            topic2.topic_name, words2, topic2.size, [a.title for a in articles2]
        )

        try:
            # Get LLM decision
            response = self.llm_analyzer._call_llm(prompt, max_tokens=300, temperature=0.3)

            # Parse JSON response
            result = json.loads(response)

            should_merge = result.get('should_merge', False)
            reason = result.get('reason', 'No reason provided')
            merged_name = result.get('merged_name', None)

            logger.info(
                f"LLM merge decision for topics {topic1_id} & {topic2_id}: "
                f"{'MERGE' if should_merge else 'KEEP SEPARATE'} - {reason}"
            )

            return should_merge, reason, merged_name

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return False, "LLM response parsing failed", None

        except Exception as e:
            logger.error(f"LLM merge decision failed: {e}")
            return False, f"LLM error: {str(e)}", None

    def _build_merge_prompt(
        self,
        name1: str, words1: List[str], size1: int, titles1: List[str],
        name2: str, words2: List[str], size2: int, titles2: List[str]
    ) -> str:
        """
        Build LLM prompt for merge decision.

        Args:
            name1, words1, size1, titles1: Topic 1 info
            name2, words2, size2, titles2: Topic 2 info

        Returns:
            Prompt string
        """
        prompt = f"""Are these two topics about the same underlying trend and should be merged?

Topic A:
- Name: {name1}
- Keywords: {', '.join(words1[:5])}
- Size: {size1} articles
- Sample titles:
{chr(10).join(f'  - {title[:80]}' for title in titles1[:3])}

Topic B:
- Name: {name2}
- Keywords: {', '.join(words2[:5])}
- Size: {size2} articles
- Sample titles:
{chr(10).join(f'  - {title[:80]}' for title in titles2[:3])}

Respond ONLY with valid JSON (no markdown, no code blocks):
{{
  "should_merge": true or false,
  "reason": "brief explanation (1-2 sentences)",
  "merged_name": "suggested name if merging" or null
}}

Consider:
1. Do they discuss the same core concept/trend?
2. Are the keywords and article titles conceptually aligned?
3. Could these be different aspects of the same trend, or truly separate trends?
"""
        return prompt

    def merge_topics(
        self,
        source_topic_id: int,
        target_topic_id: int,
        merged_name: Optional[str] = None
    ):
        """
        Merge source topic into target topic.

        Updates all articles from source_topic_id to point to target_topic_id,
        updates target topic metadata, and marks source as merged.

        Args:
            source_topic_id: Topic to merge from (will be deprecated)
            target_topic_id: Topic to merge into (will be updated)
            merged_name: Optional new name for merged topic
        """
        logger.info(f"🔀 Merging topic {source_topic_id} into {target_topic_id}")

        try:
            with self.db.get_session() as session:
                from ..storage.models import Article, Topic

                # Update all articles from source to target
                articles_updated = (
                    session.query(Article)
                    .filter(Article.topic_id == source_topic_id)
                    .update({Article.topic_id: target_topic_id})
                )

                # Update target topic size
                target_topic = session.query(Topic).filter(
                    Topic.topic_id == target_topic_id
                ).first()

                if target_topic:
                    # Recalculate size
                    new_size = (
                        session.query(Article)
                        .filter(Article.topic_id == target_topic_id)
                        .count()
                    )
                    target_topic.size = int(new_size)  # Ensure int type

                    # Update name if provided
                    if merged_name:
                        target_topic.topic_name = merged_name

                # Mark source topic as merged (by setting size to 0)
                source_topic = session.query(Topic).filter(
                    Topic.topic_id == source_topic_id
                ).first()

                if source_topic:
                    source_topic.size = 0
                    source_topic.topic_name = f"[MERGED INTO {target_topic_id}] {source_topic.topic_name}"

                session.commit()

                logger.info(
                    f"Merged {articles_updated} articles from topic {source_topic_id} "
                    f"to {target_topic_id}"
                )

        except Exception as e:
            logger.error(f"Failed to merge topics {source_topic_id} -> {target_topic_id}: {e}")
            raise

    def auto_merge_topics(
        self,
        topic_centroids: Dict[int, np.ndarray],
        use_llm: bool = True,
        dry_run: bool = False
    ) -> List[Dict]:
        """
        Automatically find and merge similar topics.

        Args:
            topic_centroids: Dict of topic centroids
            use_llm: Whether to use LLM for validation
            dry_run: If True, only report what would be merged without merging

        Returns:
            List of merge actions performed
        """
        # Find candidates
        candidates = self.find_merge_candidates(topic_centroids)

        if not candidates:
            logger.info("✅ No merge candidates found")
            return []

        merge_actions = []
        merged_sources = set()  # Track already-merged source topics

        for topic1_id, topic2_id, similarity in candidates:
            # Skip if either topic has already been merged
            if topic1_id in merged_sources or topic2_id in merged_sources:
                continue

            # LLM validation
            if use_llm:
                should_merge, reason, merged_name = self.should_merge_topics(
                    topic1_id, topic2_id
                )

                if not should_merge:
                    logger.info(
                        f"LLM rejected merge of {topic1_id} & {topic2_id}: {reason}"
                    )
                    continue
            else:
                # Without LLM, just use similarity
                should_merge = True
                reason = f"High similarity ({similarity:.3f})"
                merged_name = None

            # Decide which topic to keep (keep larger one as target)
            all_topics = self.db.get_all_topics()
            topic_metadata = {t.topic_id: t for t in all_topics}

            # Get sizes safely (handle bytes from DB)
            topic1 = topic_metadata.get(topic1_id)
            topic2 = topic_metadata.get(topic2_id)

            def safe_size(topic):
                """Safely convert topic size to int, handling bytes from DB."""
                if not topic or not topic.size:
                    return 0
                if isinstance(topic.size, bytes):
                    return int.from_bytes(topic.size, 'big') if topic.size else 0
                return int(topic.size)

            size1 = safe_size(topic1)
            size2 = safe_size(topic2)

            if size1 >= size2:
                source_id, target_id = topic2_id, topic1_id
            else:
                source_id, target_id = topic1_id, topic2_id

            # Perform merge
            if not dry_run:
                try:
                    self.merge_topics(source_id, target_id, merged_name)
                except Exception as e:
                    logger.error(f"Merge failed: {e}")
                    continue

            # Record action
            merge_actions.append({
                'source_id': source_id,
                'target_id': target_id,
                'similarity': similarity,
                'reason': reason,
                'merged_name': merged_name,
                'dry_run': dry_run
            })

            merged_sources.add(source_id)

        logger.info(
            f"{'[DRY RUN] Would merge' if dry_run else 'Merged'} "
            f"{len(merge_actions)} topic pairs"
        )

        return merge_actions
