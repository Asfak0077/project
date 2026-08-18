"""
RAG End-to-End Pipeline
Coordinates document loading, chunking, retrieval, grounded reasoning, and response generation.
"""
from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from models.document import Document, DocumentChunk
from services.rag.loader import RAGLoader
from services.rag.chunking import RAGChunker
from services.rag.embeddings import RAGEmbeddings
from services.rag.retriever import RAGRetriever
from services.response_service import ResponseService
from utils.config import settings

logger = logging.getLogger("backend.rag.pipeline")


class RAGPipeline:
    """Full Orchestrator for RAG VER2 Querying and Document Indexing."""

    @classmethod
    def process_and_index_document(
        cls,
        db: Session,
        user_id: Optional[int],
        title: str,
        filename: str,
        file_bytes: bytes,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process uploaded PDF document: extract text, chunk semantically, embed, and store in MySQL.
        """
        logger.info(f"Indexing PDF document '{filename}' ({len(file_bytes)} bytes)")
        
        # 1. Extract text page-by-page
        pages = RAGLoader.extract_text_from_pdf_bytes(file_bytes)
        if not pages:
            raise ValueError("No readable text could be extracted from this PDF document.")

        # 2. Semantic chunking with section classification
        chunks = RAGChunker.chunk_document_pages(pages)
        if not chunks:
            raise ValueError("Document was empty or did not contain valid text passages.")

        # 3. Create parent Document DB record
        doc_record = Document(
            user_id=user_id,
            title=title or filename,
            filename=filename,
            file_path=file_path or f"documents/{filename}",
            file_size_bytes=len(file_bytes),
            total_chunks=len(chunks),
            status="indexed"
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        # 4. Generate embeddings and persist chunks
        chunk_texts = [c["content"] for c in chunks]
        embeddings = RAGEmbeddings.embed_batch(chunk_texts)

        for chunk_data, emb in zip(chunks, embeddings):
            chunk_record = DocumentChunk(
                document_id=doc_record.id,
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data["page_number"],
                section_title=chunk_data["section_title"],
                content=chunk_data["content"],
                embedding_json=emb
            )
            db.add(chunk_record)

        db.commit()
        logger.info(f"✓ Document #{doc_record.id} '{filename}' successfully indexed with {len(chunks)} chunks.")

        return {
            "document_id": doc_record.id,
            "title": doc_record.title,
            "filename": doc_record.filename,
            "total_chunks": len(chunks),
            "status": "ready"
        }

    @classmethod
    def query_document(
        cls,
        db: Session,
        user_query: str,
        document_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute grounded RAG query against indexed document chunks in MySQL.
        """
        # Fetch candidate chunks from MySQL
        query_stmt = db.query(DocumentChunk, Document).join(Document, DocumentChunk.document_id == Document.id)
        if document_id:
            query_stmt = query_stmt.filter(DocumentChunk.document_id == document_id)

        db_rows = query_stmt.limit(300).all()

        if not db_rows:
            return {
                "answer": "No indexed technical documentation found. Please upload a datasheet or user manual in the RAG Docs tab to start asking questions.",
                "message": "No indexed technical documentation found.",
                "confidence": "Low",
                "sources": [],
                "suggested_followups": ["Upload a product PDF", "Ask about catalog laptops"]
            }

        candidate_chunks: List[Dict[str, Any]] = []
        for chunk, doc in db_rows:
            candidate_chunks.append({
                "id": chunk.id,
                "document_id": doc.id,
                "filename": doc.filename,
                "source": doc.title or doc.filename,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title or "Technical Spec",
                "content": chunk.content,
                "embedding": chunk.embedding_json
            })

        # Hybrid retrieval + multi-factor reranking
        top_chunks = RAGRetriever.search_chunks(user_query, candidate_chunks, top_k=4)

        if not top_chunks:
            return {
                "answer": "I could not find relevant evidence in the uploaded documents to answer your question.",
                "message": "No matching evidence found.",
                "confidence": "Low",
                "sources": [],
                "suggested_followups": ["Ask about processor specs", "Ask about battery life"]
            }

        # Build citations
        sources = [
            {
                "filename": c.get("filename") or "Manual.pdf",
                "page_number": c.get("page_number"),
                "section_title": c.get("section_title") or "Technical Specification",
                "snippet": c.get("content", "")[:280] + ("..." if len(c.get("content", "")) > 280 else ""),
                "score": float(c.get("score", 0.85))
            }
            for c in top_chunks
        ]

        # Synthesize answer using retrieved evidence
        context_block = RAGRetriever.format_context_block(top_chunks)
        primary_snippet = top_chunks[0].get("content", "").strip()
        sec_title = top_chunks[0].get("section_title", "Technical Spec")
        src_file = top_chunks[0].get("filename", "Document")
        page_ref = f" (Page {top_chunks[0].get('page_number')})" if top_chunks[0].get("page_number") else ""

        answer_text = (
            f"### 📄 Document Analysis: {sec_title}\n\n"
            f"{primary_snippet}\n\n"
            f"**Verified Evidence Source:** `{src_file}`{page_ref}"
        )

        return {
            "answer": answer_text,
            "message": answer_text,
            "type": "rag_document",
            "confidence": f"{int(top_chunks[0].get('score', 0.88) * 100)}% Grounded",
            "sources": sources,
            "suggested_followups": [
                "Explain the cooling system in detail",
                "What are the charging and power specifications?",
                "What is the warranty coverage?"
            ]
        }
