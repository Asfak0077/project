"""
RAG Service Package (VER2)
Exports all modular RAG components: loader, chunking, embeddings, retriever, pipeline.
"""
from services.rag.loader import RAGLoader
from services.rag.chunking import RAGChunker, detect_section_title
from services.rag.embeddings import RAGEmbeddings, get_embedding_model
from services.rag.retriever import RAGRetriever
from services.rag.pipeline import RAGPipeline

__all__ = [
    "RAGLoader",
    "RAGChunker",
    "detect_section_title",
    "RAGEmbeddings",
    "get_embedding_model",
    "RAGRetriever",
    "RAGPipeline",
]
