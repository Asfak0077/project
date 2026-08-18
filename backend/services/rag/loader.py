"""
RAG Document & Corpus Loader
Handles PDF extraction, document reading, and corpus ingestion.
"""
from __future__ import annotations

import os
import io
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from pypdf import PdfReader

logger = logging.getLogger("backend.rag.loader")


class RAGLoader:
    """Document and Corpus Loader for RAG VER2 Pipeline."""

    @staticmethod
    def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extract text from PDF byte stream page-by-page.
        Returns a list of dicts with page_number and extracted text.
        """
        pages_content: List[Dict[str, Any]] = []
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for idx, page in enumerate(reader.pages, start=1):
                raw_text = page.extract_text() or ""
                cleaned = RAGLoader.clean_extracted_text(raw_text)
                if cleaned:
                    pages_content.append({
                        "page_number": idx,
                        "text": cleaned,
                    })
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise ValueError(f"Could not parse PDF document: {e}")

        return pages_content

    @staticmethod
    def extract_text_from_file(file_path: str | Path) -> List[Dict[str, Any]]:
        """Extract text from local PDF or text file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        if path.suffix.lower() == ".pdf":
            with open(path, "rb") as f:
                return RAGLoader.extract_text_from_pdf_bytes(f.read())
        elif path.suffix.lower() in [".txt", ".md", ".json"]:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                cleaned = RAGLoader.clean_extracted_text(text)
                return [{"page_number": 1, "text": cleaned}]
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    @staticmethod
    def clean_extracted_text(text: str) -> str:
        """Normalize whitespace, remove invalid characters and header/footer artifacts."""
        if not text:
            return ""
        # Remove null bytes
        text = text.replace("\x00", "")
        # Normalize multiple spaces and linebreaks
        import re
        text = re.sub(r"\r\n|\r", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    @staticmethod
    def load_corpus_json(json_path: str | Path) -> List[Dict[str, Any]]:
        """Load preprocessed product corpus JSON."""
        path = Path(json_path)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to load corpus from {json_path}: {e}")
            return []
