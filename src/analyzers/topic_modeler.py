"""
Topic Modeler using BERTopic for semantic trend detection.
"""

from typing import List, Dict, Tuple, Optional
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from loguru import logger
import re

from .semantic_clustering import NamedEntityFilter


class TopicModeler:
    """
    Detects semantic topics from article content using BERTopic.

    Unlike keyword extraction which finds individual words/phrases,
    topic modeling identifies broader thematic concepts across documents.
    """

    def __init__(
        self,
        language: str = 'multilingual',
        min_topic_size: int = 3,
        nr_topics: Optional[int] = None
    ):
        """
        Initialize the topic modeler.

        Args:
            language: Language for the model ('multilingual', 'en', 'pl')
            min_topic_size: Minimum number of documents per topic
            nr_topics: Number of topics to extract (None = auto)
        """
        self.language = language
        self.min_topic_size = min_topic_size
        self.nr_topics = nr_topics
        self.model = None
        self.entity_filter = NamedEntityFilter()
        self._initialize_model()

    def _initialize_model(self):
        """Initialize BERTopic model with custom components."""
        logger.info(f"Initializing BERTopic model (language: {self.language})")

        # Select embedding model based on language
        if self.language == 'multilingual':
            embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        elif self.language == 'en':
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        elif self.language == 'pl':
            embedding_model = SentenceTransformer('sdadas/mmlw-retrieval-roberta-base')
        else:
            logger.warning(f"Unknown language {self.language}, using multilingual")
            embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # UMAP for dimensionality reduction
        umap_model = UMAP(
            n_neighbors=15,
            n_components=5,
            min_dist=0.0,
            metric='cosine',
            random_state=42
        )

        # HDBSCAN for clustering
        hdbscan_model = HDBSCAN(
            min_cluster_size=self.min_topic_size,
            metric='euclidean',
            cluster_selection_method='eom',
            prediction_data=True
        )

        # Combined Polish + English stopwords
        polish_stopwords = [
            'i', 'w', 'na', 'z', 'do', 'się', 'nie', 'to', 'o', 'a', 'jest', 'że',
            'ale', 'jak', 'po', 'dla', 'by', 'ze', 'od', 'przy', 'czy', 'lub', 'oraz',
            'za', 'tak', 'też', 'bardzo', 'już', 'może', 'można', 'więc', 'bo',
            'są', 'będzie', 'był', 'była', 'było', 'były', 'być', 'ma', 'mają',
            'tego', 'tej', 'ten', 'ta', 'te', 'tym', 'który', 'która', 'które',
            'jego', 'jej', 'ich', 'swoje', 'oraz', 'albo', 'lecz', 'gdyby', 'jeśli',
            'tylko', 'nawet', 'jednak', 'przez', 'pod', 'nad', 'bez', 'przed', 'około',
            'co', 'gdy', 'gdzie', 'kiedy', 'kto', 'dlaczego', 'jak', 'jakie'
        ]

        english_stopwords = [
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
            'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'just', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once'
        ]

        combined_stopwords = list(set(polish_stopwords + english_stopwords))

        # Vectorizer with custom settings
        vectorizer_model = CountVectorizer(
            ngram_range=(1, 3),
            stop_words=combined_stopwords,
            min_df=2,  # Word must appear in at least 2 documents
            max_df=0.8,
            lowercase=True
        )

        # Create BERTopic model
        self.model = BERTopic(
            embedding_model=embedding_model,
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            top_n_words=5,
            nr_topics=self.nr_topics,
            calculate_probabilities=False,  # Faster without probabilities
            verbose=False
        )

        logger.info("BERTopic model initialized successfully")

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before topic modeling.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def extract_topics(
        self,
        documents: List[str],
        min_document_length: int = 50
    ) -> Tuple[List[int], Dict[int, Dict]]:
        """
        Extract topics from a list of documents.

        Args:
            documents: List of document texts
            min_document_length: Minimum character length for documents

        Returns:
            Tuple of (topic_ids, topic_info)
            - topic_ids: List of topic IDs for each document (-1 = outlier)
            - topic_info: Dictionary mapping topic_id to topic metadata
        """
        if not documents:
            logger.warning("No documents provided for topic extraction")
            return [], {}

        # Preprocess documents
        processed_docs = [
            self._preprocess_text(doc)
            for doc in documents
        ]

        # Filter out too-short documents
        valid_docs = []
        valid_indices = []
        for i, doc in enumerate(processed_docs):
            if len(doc) >= min_document_length:
                valid_docs.append(doc)
                valid_indices.append(i)

        if not valid_docs:
            logger.warning("No valid documents after filtering")
            return [], {}

        logger.info(f"Extracting topics from {len(valid_docs)} documents...")

        try:
            # Fit model and predict topics
            topics, _ = self.model.fit_transform(valid_docs)

            # Get topic information
            topic_info = self._get_topic_info()

            # Map back to original document indices
            full_topics = [-1] * len(documents)
            for i, orig_idx in enumerate(valid_indices):
                full_topics[orig_idx] = topics[i]

            logger.info(f"Extracted {len(topic_info)} topics (excluding outliers)")

            return full_topics, topic_info

        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return [], {}

    def _get_topic_info(self) -> Dict[int, Dict]:
        """
        Get detailed information about each topic.

        Returns:
            Dictionary mapping topic_id to topic metadata
        """
        if not self.model:
            return {}

        topic_info = {}

        for topic_id in self.model.get_topics().keys():
            if topic_id == -1:  # Skip outlier topic
                continue

            # Get top words for this topic
            words = self.model.get_topic(topic_id)

            if not words:
                continue

            # Extract word list and scores
            top_words = [word for word, score in words[:10]]
            word_scores = {word: score for word, score in words[:10]}

            # Filter out named entities from top words
            filtered_words = [
                word for word in top_words
                if not self.entity_filter.is_named_entity(word)
            ]

            # If too many words filtered, keep some for context (but mark as potential noise)
            if len(filtered_words) < 3:
                filtered_words = top_words[:5]  # Fallback to original

            # Generate human-readable topic name
            topic_name = self._generate_topic_name(filtered_words[:5])

            topic_info[topic_id] = {
                'id': topic_id,
                'name': topic_name,
                'top_words': filtered_words[:5],  # Use filtered words, not originals
                'word_scores': word_scores,
                'size': self.model.get_topic_info()[
                    self.model.get_topic_info()['Topic'] == topic_id
                ]['Count'].values[0] if len(self.model.get_topic_info()) > 0 else 0
            }

        return topic_info

    def _generate_topic_name(self, top_words: List[str]) -> str:
        """
        Generate a human-readable name for a topic from its top words.

        Args:
            top_words: List of top words for the topic

        Returns:
            Topic name
        """
        if not top_words:
            return "Unknown Topic"

        # Filter out very short words (likely stopwords that slipped through)
        meaningful_words = [
            word for word in top_words
            if len(word) > 2  # At least 3 characters
        ]

        if not meaningful_words:
            meaningful_words = top_words  # Fallback

        # Capitalize and join top 3 meaningful words
        name_words = [word.capitalize() for word in meaningful_words[:3]]
        return " + ".join(name_words)

    def get_topic_trends(
        self,
        topic_assignments: List[Tuple[int, int, str]],  # (article_id, topic_id, date)
        window_days: int = 30
    ) -> List[Dict]:
        """
        Calculate trending topics based on growth over time.

        Args:
            topic_assignments: List of (article_id, topic_id, date_str)
            window_days: Time window for trend calculation

        Returns:
            List of trending topics with metadata
        """
        from datetime import datetime, timedelta
        from collections import defaultdict

        if not topic_assignments:
            return []

        # Group by topic and time window
        now = datetime.now()
        current_window_start = now - timedelta(days=window_days)
        previous_window_start = now - timedelta(days=window_days * 2)

        current_counts = defaultdict(int)
        previous_counts = defaultdict(int)

        for article_id, topic_id, date_str in topic_assignments:
            if topic_id == -1:  # Skip outliers
                continue

            try:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                continue

            if date >= current_window_start:
                current_counts[topic_id] += 1
            elif date >= previous_window_start:
                previous_counts[topic_id] += 1

        # Calculate trends
        trends = []
        topic_info = self._get_topic_info()

        for topic_id in set(list(current_counts.keys()) + list(previous_counts.keys())):
            current = current_counts.get(topic_id, 0)
            previous = previous_counts.get(topic_id, 0)

            # Calculate growth rate
            if previous > 0:
                growth_rate = (current - previous) / previous
            elif current > 0:
                growth_rate = 1.0  # New topic
            else:
                continue

            # Determine trend status
            is_trending = growth_rate > 0.2 and current >= 3
            is_new = previous == 0 and current >= 2

            topic_data = topic_info.get(topic_id, {})

            trends.append({
                'topic_id': topic_id,
                'topic_name': topic_data.get('name', f'Topic {topic_id}'),
                'top_words': topic_data.get('top_words', []),
                'current_count': current,
                'previous_count': previous,
                'growth_rate': growth_rate,
                'is_trending': is_trending,
                'is_new': is_new,
                'status': '🌟 Nowe' if is_new else ('⬆️ Rosnące' if is_trending else '➡️ Stabilne')
            })

        # Sort by growth rate
        trends.sort(key=lambda x: x['growth_rate'], reverse=True)

        return trends

    def save_model(self, path: str):
        """Save the trained model to disk."""
        if self.model:
            self.model.save(path)
            logger.info(f"Model saved to {path}")

    def load_model(self, path: str):
        """Load a trained model from disk."""
        self.model = BERTopic.load(path)
        logger.info(f"Model loaded from {path}")
