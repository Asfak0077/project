"""
RAG Semantic Chunking & Section Detection
Splits text into meaningful semantic chunks with metadata attribution.
"""
from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("backend.rag.chunking")

# Section Classification Heuristic Patterns
_SECTION_PATTERNS = [
    (r"\b(battery|power|charging|watt|mah|runtime|adapter|cell)\b", "Battery & Power"),
    (r"\b(thermal|cooling|fan|heatsink|heat|airflow|vapor)\b", "Thermal & Cooling Architecture"),
    (r"\b(processor|cpu|chipset|ghz|core|thread|ryzen|intel|bionic|snapdragon)\b", "Processor & CPU"),
    (r"\b(memory|ram|ddr4|ddr5|lpddr|vram)\b", "Memory & RAM"),
    (r"\b(storage|ssd|nvme|pcie|hdd|emmc|disk)\b", "Storage & Drives"),
    (r"\b(display|screen|oled|ips|panel|resolution|hz|refresh|brightness|nits)\b", "Display & Screen"),
    (r"\b(graphics|gpu|rtx|gtx|geforce|radeon|adreno|integrated|dedicated)\b", "Graphics & GPU"),
    (r"\b(camera|sensor|lens|megapixels|mp|webcam|hdr|aperture)\b", "Camera Systems"),
    (r"\b(connectivity|ports|wifi|bluetooth|thunderbolt|usb|hdmi|type-c|ethernet)\b", "Connectivity & Ports"),
    (r"\b(specifications|specs|technical data|datasheet|sheet)\b", "Technical Specifications"),
    (r"\b(overview|introduction|highlights|features|summary)\b", "Overview & Highlights"),
]


def detect_section_title(text: str) -> str:
    """Classify text snippet into an architectural hardware section."""
    text_lower = text.lower()
    for pattern, section_name in _SECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return section_name
    return "Overview & Specifications"


class RAGChunker:
    """Semantic Document Chunker with sliding window and section tagging."""

    DEFAULT_CHUNK_SIZE = 500      # Target characters per chunk
    DEFAULT_CHUNK_OVERLAP = 100   # Overlap characters between chunks
    MIN_CHUNK_SIZE = 60           # Ignore micro fragments

    @classmethod
    def chunk_document_pages(
        cls,
        pages: List[Dict[str, Any]],
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> List[Dict[str, Any]]:
        """
        Split a list of page dicts [{"page_number": 1, "text": "..."}] into chunks.
        """
        all_chunks: List[Dict[str, Any]] = []
        global_chunk_idx = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            raw_text = page.get("text", "")
            if not raw_text.strip():
                continue

            # Split text by paragraphs first
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            
            # If paragraph splitting gave reasonable sizes, chunk by paragraphs/sentences
            page_chunks = cls._chunk_text(raw_text, chunk_size, chunk_overlap)
            
            for chunk_str in page_chunks:
                if len(chunk_str) < cls.MIN_CHUNK_SIZE:
                    continue
                
                section = detect_section_title(chunk_str)
                all_chunks.append({
                    "chunk_index": global_chunk_idx,
                    "page_number": page_num,
                    "section_title": section,
                    "content": chunk_str,
                    "char_count": len(chunk_str),
                    "token_estimate": len(chunk_str) // 4
                })
                global_chunk_idx += 1

        return all_chunks

    @classmethod
    def _chunk_text(cls, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Sliding window text chunker respecting paragraph and sentence boundaries."""
        if len(text) <= chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunks.append(text[start:].strip())
                break

            # Find nearest sentence or paragraph boundary before end
            boundary = -1
            lookback = text[max(start, end - 150):end + 50]
            for delim in ["\n\n", ".\n", ". ", "? ", "! "]:
                idx = text.rfind(delim, start + 50, end + 50)
                if idx != -1:
                    boundary = idx + len(delim)
                    break

            if boundary != -1 and boundary > start:
                chunk = text[start:boundary].strip()
                start = max(start + 1, boundary - overlap)
            else:
                chunk = text[start:end].strip()
                start = end - overlap

            if chunk and len(chunk) >= cls.MIN_CHUNK_SIZE:
                chunks.append(chunk)

        return chunks
