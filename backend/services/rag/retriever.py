"""
RAG Hybrid Retriever & Multi-Factor Reranker
Performs dense semantic vector search + sparse keyword reranking.
"""
from __future__ import annotations

import re
import math
import logging
from collections import Counter
from typing import List, Dict, Any, Optional, Sequence
import numpy as np

from services.rag.embeddings import RAGEmbeddings

logger = logging.getLogger("backend.rag.retriever")


class RAGRetriever:
    """Hybrid Retriever for RAG VER2."""

    @classmethod
    def search_chunks(
        cls,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 4,
        category: Optional[str] = None,
        product_scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid vector + keyword retrieval across chunk records.
        """
        if not chunks or not query.strip():
            return []

        # 1. Embed query
        query_vec = RAGEmbeddings.embed_text(query)
        query_tokens = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]

        scored_chunks: List[Dict[str, Any]] = []

        for chunk in chunks:
            content = chunk.get("content", "")
            if not content:
                continue

            # Dense similarity
            chunk_vec = chunk.get("embedding")
            if chunk_vec is None:
                chunk_vec = RAGEmbeddings.embed_text(content)
                chunk["embedding"] = chunk_vec

            dense_score = RAGEmbeddings.cosine_similarity(query_vec, chunk_vec)

            # Sparse keyword overlap
            content_lower = content.lower()
            matching_tokens = sum(1 for t in query_tokens if t in content_lower)
            keyword_score = matching_tokens / max(1, len(query_tokens))

            # Product match boost
            product_boost = 0.0
            if product_scope and product_scope.lower() in content_lower:
                product_boost = 0.20

            # Section header relevance boost
            section = chunk.get("section_title", "")
            section_boost = 0.0
            if any(t in section.lower() for t in query_tokens):
                section_boost = 0.15

            # Composite Rerank Score (0.0 to 1.0)
            composite_score = (
                dense_score * 0.45 +
                keyword_score * 0.25 +
                product_boost * 0.15 +
                section_boost * 0.15
            )

            scored_chunks.append({
                **chunk,
                "score": round(composite_score, 4),
                "dense_score": round(dense_score, 4),
                "keyword_score": round(keyword_score, 4),
            })

        # Sort descending by composite score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]

    @classmethod
    def format_context_block(cls, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved snippets into a clean, numbered context block for LLM prompting."""
        if not retrieved_chunks:
            return "No specific document evidence retrieved."

        blocks: List[str] = []
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            src = chunk.get("filename") or chunk.get("source") or "Technical Manual"
            page = chunk.get("page_number")
            sec = chunk.get("section_title") or "General Specification"
            content = chunk.get("content", "").strip()

            page_info = f" (Page {page})" if page else ""
            blocks.append(f"[{idx}] Source: {src}{page_info} | Section: {sec}\n{content}")

        return "\n\n".join(blocks)
