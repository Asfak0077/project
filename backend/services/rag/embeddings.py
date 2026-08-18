"""
RAG Embedding Service
Handles dense vector embedding generation and vector similarity calculations.
"""
from __future__ import annotations

import logging
from typing import List, Sequence, Union, Optional
import numpy as np

logger = logging.getLogger("backend.rag.embeddings")

_cached_embedding_model = None


def get_embedding_model():
    """Singleton getter for SentenceTransformer embedding model."""
    global _cached_embedding_model
    if _cached_embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _cached_embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            logger.info("Loaded SentenceTransformer 'sentence-transformers/all-MiniLM-L6-v2'")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer: {e}")
            _cached_embedding_model = None
    return _cached_embedding_model


class RAGEmbeddings:
    """Dense Vector Embeddings generator."""

    EMBEDDING_DIM = 384

    @classmethod
    def embed_text(cls, text: str) -> List[float]:
        """Embed a single text string into a dense 384-dim vector."""
        return cls.embed_batch([text])[0]

    @classmethod
    def embed_batch(cls, texts: Sequence[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        if not texts:
            return []

        model = get_embedding_model()
        if model is not None:
            try:
                embeddings = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
                return [e.tolist() for e in embeddings]
            except Exception as e:
                logger.error(f"Error during batch embedding generation: {e}")

        # Deterministic fallback embedding for testing / resilience
        logger.warning("Using deterministic fallback vector embedding.")
        return [cls._fallback_embed(t) for t in texts]

    @classmethod
    def _fallback_embed(cls, text: str) -> List[float]:
        """Generate deterministic pseudo-embedding vector based on character hash."""
        vec = np.zeros(cls.EMBEDDING_DIM, dtype=np.float32)
        words = text.lower().split()
        for idx, word in enumerate(words):
            h = hash(word) % cls.EMBEDDING_DIM
            vec[h] += 1.0 / (idx + 1.0)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def cosine_similarity(vec_a: Union[List[float], np.ndarray], vec_b: Union[List[float], np.ndarray]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
