"""
Embedding cache manager for efficient reuse of computed embeddings.
"""

from typing import List, Dict, Tuple, Optional
import hashlib
import pickle
import numpy as np
from loguru import logger

from .database import Database


class EmbeddingCacheManager:
    """
    Manages caching of article embeddings to speed up topic modeling.

    Embeddings are expensive to compute (requires neural network forward pass),
    so caching based on content can provide significant performance improvements
    when reprocessing articles.
    """

    def __init__(self, db: Database, ttl_days: int = 90):
        """
        Initialize the cache manager.

        Args:
            db: Database instance
            ttl_days: Time-to-live for cache entries in days
        """
        self.db = db
        self.ttl_days = ttl_days

    def get_cache_key(self, url: str, content_preview: str) -> str:
        """
        Generate a cache key from URL and content preview.

        Args:
            url: Article URL
            content_preview: First ~500 chars of article content

        Returns:
            SHA256 hex digest as cache key
        """
        # Combine URL and content preview for unique identification
        combined = f"{url}|{content_preview}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def get_embeddings(
        self,
        cache_keys: List[str]
    ) -> Dict[str, np.ndarray]:
        """
        Retrieve embeddings from cache.

        Args:
            cache_keys: List of cache keys to look up

        Returns:
            Dict mapping cache_key to numpy embedding array
        """
        if not cache_keys:
            return {}

        # Query database
        cached_data = self.db.get_embeddings_from_cache(cache_keys)

        # Deserialize embeddings
        embeddings = {}
        for cache_key, embedding_bytes in cached_data.items():
            try:
                embedding = pickle.loads(embedding_bytes)
                if isinstance(embedding, np.ndarray):
                    embeddings[cache_key] = embedding
                else:
                    logger.warning(f"Invalid embedding type in cache: {type(embedding)}")
            except Exception as e:
                logger.warning(f"Failed to deserialize embedding for key {cache_key[:16]}...: {e}")

        return embeddings

    def save_embeddings(
        self,
        cache_data: List[Tuple[str, np.ndarray, Optional[int]]]
    ):
        """
        Save embeddings to cache.

        Args:
            cache_data: List of tuples (cache_key, embedding_array, article_id)
        """
        if not cache_data:
            return

        # Serialize embeddings
        serialized_data = []
        for cache_key, embedding, article_id in cache_data:
            try:
                if not isinstance(embedding, np.ndarray):
                    logger.warning(f"Skipping non-numpy embedding: {type(embedding)}")
                    continue

                embedding_bytes = pickle.dumps(embedding)
                serialized_data.append((cache_key, embedding_bytes, article_id))

            except Exception as e:
                logger.warning(f"Failed to serialize embedding: {e}")

        # Save to database
        if serialized_data:
            self.db.save_embeddings_to_cache(serialized_data)

    def cleanup_stale(self):
        """Remove stale cache entries based on TTL."""
        self.db.cleanup_old_embeddings(self.ttl_days)

    def get_embeddings_with_cache(
        self,
        documents: List[str],
        article_ids: List[int],
        article_urls: List[str],
        embedding_function: callable
    ) -> np.ndarray:
        """
        Get embeddings using cache when available, computing when necessary.

        Args:
            documents: List of document texts
            article_ids: List of article IDs
            article_urls: List of article URLs
            embedding_function: Function to compute embeddings for documents

        Returns:
            Numpy array of embeddings
        """
        if not documents:
            return np.array([])

        # Generate cache keys
        cache_keys = []
        for url, doc in zip(article_urls, documents):
            content_preview = doc[:500]
            cache_key = self.get_cache_key(url, content_preview)
            cache_keys.append(cache_key)

        # Try to get from cache
        cached_embeddings = self.get_embeddings(cache_keys)

        # Identify which documents need computation
        embeddings = [None] * len(documents)
        docs_to_compute = []
        compute_indices = []

        for i, cache_key in enumerate(cache_keys):
            if cache_key in cached_embeddings:
                embeddings[i] = cached_embeddings[cache_key]
            else:
                docs_to_compute.append(documents[i])
                compute_indices.append(i)

        cache_hits = len(documents) - len(docs_to_compute)
        cache_hit_rate = cache_hits / len(documents) if len(documents) > 0 else 0.0

        logger.info(
            f"💾 Embedding cache: {cache_hits}/{len(documents)} hits "
            f"({cache_hit_rate*100:.1f}% hit rate)"
        )

        # Compute missing embeddings
        if docs_to_compute:
            logger.info(f"🧮 Computing {len(docs_to_compute)} new embeddings...")
            new_embeddings = embedding_function(docs_to_compute)

            # Store in embeddings list
            for idx, embedding in zip(compute_indices, new_embeddings):
                embeddings[idx] = embedding

            # Save to cache
            cache_data = []
            for idx in compute_indices:
                cache_key = cache_keys[idx]
                embedding = embeddings[idx]
                article_id = article_ids[idx] if idx < len(article_ids) else None
                cache_data.append((cache_key, embedding, article_id))

            self.save_embeddings(cache_data)

        # Convert to numpy array
        return np.array(embeddings)
