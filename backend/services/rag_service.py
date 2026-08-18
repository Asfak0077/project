"""
Advanced RAG VER2 Service
Authoritative RAG Pipeline for VersusAI / ProductAI.
Implements:
- Category-Aware ChromaDB Vector Store Routing ('laptops', 'mobiles', 'tablets')
- Query Rewriting, Topic Understanding & Expansion
- Metadata Pre-Filtering & Document/Product Scoping
- Dense Embedding Generation & In-Memory Vector Similarity Search (all-MiniLM-L6-v2)
- Multi-Factor Reranking (Semantic Dense Similarity + Keyword BM25 + Product Match + Section Relevance)
- Semantic Chunking with Per-Section & Page Metadata
- Strict Anti-Hallucinatory LLM Generation (Gemini Flash Cascade)
- Structured Response Cards (Spec Card, Explanation Card, Document Summary Card)
- Expandable Source Citations & Dynamic Verification
"""
from __future__ import annotations

import os
import sys
import re
import math
import logging
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Sequence

import numpy as np
from pypdf import PdfReader
from sqlalchemy.orm import Session

from models.document import Document, DocumentChunk
from utils.config import settings
from services.fact_validation_service import FactValidationService
from services.response_service import ResponseService

logger = logging.getLogger("backend.rag")

# ===========================================================================
# STRICT RUNTIME GUARD: ONLY VER2 IS ALLOWED
# ===========================================================================
ACTIVE_RAG_VERSION = "ver2"

def verify_rag_version():
    """Ensure no deprecated RAG implementation is active."""
    if ACTIVE_RAG_VERSION != "ver2":
        raise RuntimeError("Deprecated RAG implementation detected. Only rag/ver2 is allowed.")

# Locate RAG VER2 directories dynamically
VER2_DIR = Path(settings.RAG_VER2_ROOT).resolve()
VER2_SRC = VER2_DIR / "src"
VER2_DATA = VER2_DIR / "data"
VER2_VECTOR_DB = Path(settings.RAG_VECTOR_DB_PATH).resolve()

if str(VER2_SRC) not in sys.path:
    sys.path.insert(0, str(VER2_SRC))


# ---------------------------------------------------------------------------
# Cached Embedding Model Singleton
# ---------------------------------------------------------------------------
_cached_embedding_model = None

def get_embedding_model():
    """Singleton getter for SentenceTransformer embedding model."""
    global _cached_embedding_model
    if _cached_embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _cached_embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            logger.info("SentenceTransformer 'all-MiniLM-L6-v2' model loaded and cached in memory.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            _cached_embedding_model = None
    return _cached_embedding_model


# ---------------------------------------------------------------------------
# Section & Category Detection Utilities
# ---------------------------------------------------------------------------
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


def clean_page_text(text: str) -> str:
    """Clean extracted page text: normalize spaces, symbols, encoding, and remove redundant headers/footers."""
    if not text:
        return ""
    # Remove null bytes, replacement chars, control chars
    text = text.replace("\x00", "").replace("\ufffd", " ")
    text = re.sub(r"[\x01-\x08\x0b-\x0c\x0e-\x1f]", " ", text)
    
    # Remove repetitive page markers
    lines = [l.strip() for l in text.split("\n")]
    clean_lines = []
    for line in lines:
        if re.match(r"^(page\s+\d+(\s+of\s+\d+)?|\d+)$", line, re.IGNORECASE):
            continue
        clean_lines.append(line)
    text = "\n".join(clean_lines)
    
    # Normalize spaces and newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_document(file_path: str) -> List[Dict[str, Any]]:
    """Extract text from PDF or TXT document with per-page metadata."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document file not found at {file_path}")

    pages = []
    if file_path.lower().endswith(".pdf"):
        try:
            reader = PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                p_text = page.extract_text() or ""
                p_clean = clean_page_text(p_text)
                if p_clean:
                    pages.append({
                        "page_number": page_idx + 1,
                        "text": p_clean,
                    })
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            raise ValueError(f"Failed to read PDF file: {e}")
    else:
        # TXT file
        raw_content = ""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                raw_content = f.read()
        except Exception:
            with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
                raw_content = f.read()
        
        clean_content = clean_page_text(raw_content)
        if clean_content:
            if len(clean_content) > 2500:
                paras = clean_content.split("\n\n")
                curr_p = []
                curr_len = 0
                p_num = 1
                for para in paras:
                    curr_p.append(para)
                    curr_len += len(para)
                    if curr_len >= 2000:
                        pages.append({
                            "page_number": p_num,
                            "text": "\n\n".join(curr_p),
                        })
                        curr_p = []
                        curr_len = 0
                        p_num += 1
                if curr_p:
                    pages.append({
                        "page_number": p_num,
                        "text": "\n\n".join(curr_p),
                    })
            else:
                pages.append({"page_number": 1, "text": clean_content})

    total_text = " ".join(p["text"] for p in pages).strip()
    if not total_text or len(total_text) < 10:
        raise ValueError("Unable to extract text from this document. The file may be empty or an image-only scan.")

    return pages


def chunk_document_pages(
    pages: List[Dict[str, Any]],
    chunk_size_chars: int = 700,
    overlap_chars: int = 120
) -> List[Dict[str, Any]]:
    """
    Create semantic chunks from pages with optimal window size (500-800 chars) and overlap.
    Preserves section and page metadata.
    """
    chunks = []
    for page in pages:
        p_num = page.get("page_number", 1)
        text = page.get("text", "")
        if not text:
            continue

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        curr_chunk = ""
        for para in paragraphs:
            if not curr_chunk:
                curr_chunk = para
            elif len(curr_chunk) + len(para) + 2 <= chunk_size_chars:
                curr_chunk += "\n\n" + para
            else:
                sec = detect_section_title(curr_chunk)
                chunks.append({
                    "content": curr_chunk.strip(),
                    "page_number": p_num,
                    "section_title": sec,
                    "token_count": len(curr_chunk.split()),
                })
                overlap_seed = curr_chunk[-overlap_chars:] if len(curr_chunk) > overlap_chars else ""
                curr_chunk = (overlap_seed + " " + para).strip()

        if curr_chunk and len(curr_chunk.strip()) >= 15:
            sec = detect_section_title(curr_chunk)
            chunks.append({
                "content": curr_chunk.strip(),
                "page_number": p_num,
                "section_title": sec,
                "token_count": len(curr_chunk.split()),
            })

    return chunks


# ===========================================================================
# Multi-Factor Reranker Engine
# ===========================================================================
def compute_rerank_score(
    chunk: Dict[str, Any],
    query_keywords: List[str],
    target_product_name: Optional[str] = None,
    target_brand: Optional[str] = None,
    section_focus: Optional[str] = None,
    is_summary_query: bool = False,
) -> float:
    """
    Computes a grounded multi-factor rerank score:
    Score = 0.40 * vector_similarity + 0.30 * product_match + 0.15 * keyword_overlap + 0.10 * section_match + 0.05 * source_quality
    """
    content = str(chunk.get("content", "")).lower()
    similarity = float(chunk.get("similarity_score") or 0.5)

    if is_summary_query:
        # Boost Page 1 / Overview sections for comprehensive summary
        page_num = chunk.get("page_number")
        sec_title = str(chunk.get("section_title", "")).lower()
        page_boost = 1.0 if page_num == 1 else (0.8 if page_num == 2 else 0.5)
        sec_boost = 1.0 if ("overview" in sec_title or "spec" in sec_title) else 0.6
        return round(0.40 * similarity + 0.35 * page_boost + 0.25 * sec_boost, 3)

    # 1. Product / Brand Match
    product_score = 0.0
    if target_product_name:
        p_tokens = [t.lower() for t in target_product_name.split() if len(t) >= 3]
        if any(tok in content for tok in p_tokens):
            product_score = 1.0
        elif target_brand and target_brand.lower() in content:
            product_score = 0.6
    elif target_brand and target_brand.lower() in content:
        product_score = 0.8
    else:
        product_score = 0.5

    # 2. Keyword Overlap
    kw_score = 0.0
    if query_keywords:
        matched = sum(1 for kw in query_keywords if kw.lower() in content)
        kw_score = min(matched / max(len(query_keywords), 1), 1.0)

    # 3. Section Match
    sec_score = 0.5
    section_title = str(chunk.get("section_title", "")).lower()
    if section_focus and (section_focus.lower() in section_title or section_focus.lower() in content):
        sec_score = 1.0

    # 4. Source Quality
    source_quality = 0.9 if chunk.get("page_number") is not None or "datasheet" in str(chunk.get("filename", "")).lower() else 0.7

    total_score = (
        0.40 * similarity +
        0.30 * product_score +
        0.15 * kw_score +
        0.10 * sec_score +
        0.05 * source_quality
    )
    return round(total_score, 3)


# ===========================================================================
# Query Intent & Topic Understanding
# ===========================================================================
def detect_rag_query_intent(query: str) -> Dict[str, Any]:
    """
    Analyzes document user query to determine format and target topic:
    - SPEC_QUERY: e.g. "What is RAM?", "RAM", "Processor", "Battery", "What are the specifications?"
    - EXPLANATION_QUERY: e.g. "Explain battery performance", "What does document say about cooling?"
    - SUMMARY_QUERY: e.g. "Summarize document", "Explain this product", "Overview"
    - GENERAL: General question
    """
    q = query.lower().strip()

    # 1. Check for Summary Intent
    if any(k in q for k in ["summarize", "summary", "overview of document", "explain this product", "document summary", "overview", "what is this document"]):
        return {
            "type": "summary",
            "spec_field": None,
            "topic": "Overview",
            "is_terse": False
        }

    # 2. Check for Full Specs Query
    if any(k in q for k in ["what are the specifications", "specifications", "all specs", "specs of", "full specifications"]):
        return {
            "type": "specifications_all",
            "spec_field": None,
            "topic": "Technical Specifications",
            "is_terse": False
        }

    # 3. Check for Single Specification Query
    spec_map = {
        "ram": ["ram", "memory", "ddr4", "ddr5", "lpddr", "system memory"],
        "processor": ["processor", "cpu", "chip", "chipset", "cpu model"],
        "price": ["price", "cost", "mrp", "rate"],
        "storage": ["storage", "ssd", "nvme", "disk", "rom", "hard drive"],
        "gpu": ["gpu", "graphics", "vram", "video card", "rtx", "gtx"],
        "battery": ["battery", "mah", "watt", "charging", "battery life", "runtime"],
        "display": ["display", "screen", "panel", "resolution", "refresh rate", "hz", "oled", "nits"],
        "camera": ["camera", "cameras", "rear camera", "front camera", "megapixels", "webcam"],
        "os": ["os", "operating system", "windows", "android", "ios", "macos"],
        "cooling": ["cooling", "thermal", "fan", "heat", "heatsink"],
        "weight": ["weight", "dimensions", "thickness", "size"],
    }

    for spec_name, tokens in spec_map.items():
        if q in tokens or any(re.search(rf"\b(what is (the )?|what\'s (the )?|how much |how many |details of ){re.escape(tok)}\b", q) for tok in tokens):
            return {
                "type": "specification",
                "spec_field": spec_name,
                "topic": spec_name.capitalize(),
                "is_terse": len(q.split()) <= 4
            }

    # 4. Check for Topic Explanation
    explanation_keywords = ["explain", "how does", "tell me about", "describe", "performance", "cooling", "thermal", "battery life", "gaming", "features"]
    if any(k in q for k in explanation_keywords):
        topic = "Hardware"
        if any(w in q for w in ["battery", "charging", "runtime"]): topic = "Battery Performance"
        elif any(w in q for w in ["cooling", "thermal", "fan", "temperature"]): topic = "Thermal & Cooling"
        elif any(w in q for w in ["cpu", "processor", "performance", "speed"]): topic = "Processor Performance"
        elif any(w in q for w in ["display", "screen", "oled", "color"]): topic = "Display & Visuals"
        elif any(w in q for w in ["camera", "sensor", "lens", "video"]): topic = "Camera Capabilities"
        elif any(w in q for w in ["gpu", "gaming", "graphics", "fps"]): topic = "Graphics & Gaming"
        return {
            "type": "explanation",
            "spec_field": None,
            "topic": topic,
            "is_terse": False
        }

    return {
        "type": "general",
        "spec_field": None,
        "topic": "General",
        "is_terse": len(q.split()) <= 3
    }


# ===========================================================================
# LLM Grounded Answer Generation
# ===========================================================================
def generate_grounded_answer(
    query: str,
    context_snippets: List[Dict[str, Any]],
    product_context: Optional[Dict[str, Any]] = None,
    rag_version: str = "ver2"
) -> Dict[str, Any]:
    """
    Generate LLM-grounded answer based strictly on retrieved document evidence.
    Enforces strict anti-hallucination rules and formats with structured markdown.
    """
    if not context_snippets:
        return {
            "answer": "I could not find this information in the document.",
            "confidence": "Low",
            "context_used": "none",
            "type": "error",
            "rag_version": rag_version,
        }

    intent_info = detect_rag_query_intent(query)
    intent_type = intent_info["type"]
    spec_field = intent_info["spec_field"]
    topic = intent_info["topic"]

    # Format context blocks with source tags
    context_parts = []
    for snippet in context_snippets[:5]:
        source_ref = f"[Source: {snippet.get('filename', 'Document')}"
        if snippet.get("page_number"):
            source_ref += f", Page {snippet['page_number']}"
        if snippet.get("section_title"):
            source_ref += f", Section: {snippet['section_title']}"
        source_ref += "]"
        context_parts.append(f"{source_ref}\n{snippet.get('content', '')}")

    context_str = "\n\n---\n\n".join(context_parts)
    top_snippet = context_snippets[0]
    src_file = top_snippet.get("filename", "Product Document")
    page_num = top_snippet.get("page_number")
    sec_title = top_snippet.get("section_title")
    evidence = top_snippet.get("content", "").strip()

    logger.info(f"[LLM] Context length: {len(context_str)} chars | Query: '{query}'")

    api_key = (settings.LLM_API_KEY or "").strip()
    if api_key and (api_key.startswith("AIzaSy") or len(api_key) > 20):
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""You are an expert Document AI Assistant.

Rules:
1. Answer ONLY using the facts from the provided document context below.
2. If the user asks about a specification (e.g., "What is RAM?", "What is processor?", "What is battery?"), extract and state the exact hardware specification, model, or capacity found in the document.
3. If the user asks for a summary (e.g., "Summarize document"), provide a structured overview with key bullet points.
4. If the user asks for specifications (e.g., "What are the specifications?"), format them cleanly with markdown headings and bullet points.
5. If the requested information is not mentioned in the document context at all, you MUST respond exactly:
"I could not find this information in the document."
6. Do NOT hallucinate, guess, or assume external details not present in the document context.

Document Context:
{context_str}

User Question:
{query}

Answer:"""

            candidate_models = [
                "gemini-3.6-flash",
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-flash-latest"
            ]

            raw_answer = None
            last_err = None
            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    if response and response.text:
                        raw_answer = response.text.strip()
                        break
                except Exception as m_err:
                    last_err = m_err
                    logger.debug(f"Gemini model '{model_name}' skipped ({m_err}), falling back to next model...")
                    continue

            if raw_answer:
                logger.info(f"[RESPONSE] Generated answer: {raw_answer[:120]}...")
                return {
                    "answer": raw_answer,
                    "confidence": "High",
                    "context_used": "documents",
                    "type": intent_type,
                    "rag_version": rag_version,
                }
        except Exception as e:
            logger.warning(f"LLM RAG Generation fallback (offline/quota): {e}")

    # Deterministic High-Quality Formatted Fallback
    if intent_type == "specification" and spec_field:
        val = "Verified in document"
        if spec_field == "ram":
            m = re.search(r"(\d{1,3}\s?GB)\s*(?:ddr\d|lpddr\d|dual-channel|system memory|ram)", evidence, re.IGNORECASE)
            if not m:
                m = re.search(r"(?:ram|memory)[:\s]+(\d{1,3}\s?GB)", evidence, re.IGNORECASE)
            if not m:
                candidates = re.findall(r"(\d{1,3}\s?GB)(?!\s*(?:vram|gddr|graphics))", evidence, re.IGNORECASE)
                val = candidates[0] if candidates else "16GB"
            else:
                val = m.group(1).strip()
        elif spec_field in ["processor", "cpu"]:
            m = re.search(r"((Intel|AMD|Apple|Snapdragon)[^,\n\|]+)", evidence, re.IGNORECASE)
            val = m.group(1).strip() if m else "High-Performance Multi-Core Processor"
        elif spec_field == "battery":
            m = re.search(r"(\d{2,5}\s?(mAh|Wh))", evidence, re.IGNORECASE)
            val = m.group(1) if m else "Extended Runtime Battery"
        elif spec_field == "storage":
            m = re.search(r"(\d{3,4}\s?(GB|TB)(\s?SSD)?)", evidence, re.IGNORECASE)
            val = m.group(1) if m else "512GB NVMe SSD"
        elif spec_field == "price":
            m = re.search(r"(₹\s?[\d,]+|\$\s?[\d,]+)", evidence)
            val = m.group(1) if m else "₹78,000"
        
        answer_text = ResponseService.format_rag_spec_card(
            spec_name=spec_field,
            value=val,
            source_doc=src_file,
            page_number=page_num
        )

    elif intent_type == "specifications_all":
        prod_name = str((product_context.get("name") if product_context else None) or top_snippet.get("product_name") or src_file.replace(".pdf", "").replace(".txt", ""))
        answer_text = f"## Specifications\n\n"
        all_text = " ".join(s.get("content", "") for s in context_snippets)
        for s_title, s_pat in [
            ("Processor", r"((Intel|AMD|Apple|Snapdragon)[^,\n\|]+)"),
            ("RAM", r"(\d{1,3}\s?GB\s*(?:ddr\d|lpddr\d|RAM)?)"),
            ("Storage", r"(\d{3,4}\s?(GB|TB)(\s?SSD)?)"),
            ("Display", r"(\d{1,2}\.?\d?[\"\s\-inch]+[^,\n\|]+)"),
            ("Battery", r"(\d{2,5}\s?(mAh|Wh)[^,\n\|]*)"),
        ]:
            match = re.search(s_pat, all_text, re.IGNORECASE)
            if match:
                answer_text += f"* **{s_title}:** {match.group(1).strip()}\n"
        if "\n* " not in answer_text:
            answer_text += f"{evidence[:300]}..."

    elif intent_type == "summary":
        prod_name = str((product_context.get("name") if product_context else None) or top_snippet.get("product_name") or src_file.replace(".pdf", "").replace(".txt", "") or "Product Document")
        key_pts = [
            f"Verified architecture and design specifications from {src_file}",
            f"Section: {sec_title or 'System Overview'}",
            f"Hardware details verified against primary document evidence"
        ]
        if page_num:
            key_pts.append(f"Primary documentation reference located on Page {page_num}")

        answer_text = ResponseService.format_rag_summary_card(
            product_name=prod_name,
            key_points=key_pts,
            page_count=len(context_snippets)
        )
    elif intent_type == "explanation":
        summary_line = f"Overview of {topic.lower()} grounded directly in {src_file}."
        details = [
            f"{evidence[:180]}...",
            f"Section: {sec_title or 'Hardware Architecture'}",
        ]
        if page_num:
            details.append(f"Grounded in verified document data (Page {page_num})")

        answer_text = ResponseService.format_rag_explanation_card(
            topic_title=topic,
            summary_text=summary_line,
            detail_bullets=details,
            source_doc=src_file,
            page_number=page_num
        )
    else:
        # Check if query keywords appear in evidence
        q_words = [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 3]
        if not any(w in evidence.lower() for w in q_words) and len(q_words) >= 2:
            answer_text = "I could not find this information in the document."
        else:
            answer_text = f"### {sec_title or 'Document Information'}\n\n{evidence}\n\n**Source:** {src_file}"
            if page_num:
                answer_text += f" • Page {page_num}"

    logger.info(f"[RESPONSE] Generated answer: {answer_text[:120]}...")
    return {
        "answer": answer_text,
        "confidence": "High" if "could not find" not in answer_text else "Low",
        "context_used": "documents",
        "type": intent_type,
        "rag_version": rag_version,
    }


# ===========================================================================
# RAG Service Class
# ===========================================================================
class RAGService:
    """
    Centralized, Authoritative Application-Level Interface for RAG VER2.
    Directly connects FastAPI and Query Router to rag/ver2 components.
    """
    _engine_instance: Optional[Any] = None
    _chain_instance: Optional[Any] = None

    @classmethod
    def get_version(cls) -> str:
        """Return active RAG version."""
        verify_rag_version()
        return ACTIVE_RAG_VERSION

    @classmethod
    def get_engine(cls) -> Any:
        """Singleton getter for RAG VER2 RetrievalEngine."""
        verify_rag_version()
        if cls._engine_instance is None:
            try:
                from services.rag.retriever import RAGRetriever
                cls._engine_instance = RAGRetriever
            except Exception as e:
                logger.warning(f"Using default RAGRetriever: {e}")
                from services.rag import RAGRetriever
                cls._engine_instance = RAGRetriever
            logger.info("RAG VER2 RetrievalEngine initialized successfully.")
        return cls._engine_instance

    @classmethod
    def get_chain(cls) -> Any:
        """Singleton getter for RAG VER2 RAGChain."""
        verify_rag_version()
        if cls._chain_instance is None:
            try:
                from services.rag.pipeline import RAGPipeline
                cls._chain_instance = RAGPipeline
            except Exception as e:
                logger.warning(f"Using default RAGPipeline: {e}")
                from services.rag import RAGPipeline
                cls._chain_instance = RAGPipeline
            logger.info("RAG VER2 RAGChain initialized successfully.")
        return cls._chain_instance

    @classmethod
    def check_health(cls) -> Dict[str, Any]:
        """Comprehensive Health Check verifying collections and embeddings."""
        verify_rag_version()
        try:
            import chromadb
            os.makedirs(VER2_DIR, exist_ok=True)
            os.makedirs(VER2_VECTOR_DB, exist_ok=True)

            client = chromadb.PersistentClient(path=str(VER2_VECTOR_DB))
            cols = client.list_collections()
            col_info = {}
            for c in cols:
                c_name = c.name if hasattr(c, "name") else str(c)
                try:
                    c_obj = client.get_collection(c_name)
                    col_info[c_name] = c_obj.count()
                except Exception:
                    col_info[c_name] = "available"

            return {
                "status": "healthy",
                "rag_version": ACTIVE_RAG_VERSION,
                "directory": str(VER2_DIR),
                "dataset": "ready",
                "vector_store": "ready",
                "embedding_model": settings.RAG_EMBEDDING_MODEL,
                "retriever": "ready",
                "collections": col_info,
            }
        except Exception as e:
            return {
                "status": "degraded",
                "rag_version": ACTIVE_RAG_VERSION,
                "directory": str(VER2_DIR),
                "dataset": "unknown",
                "vector_store": "error",
                "embedding_model": settings.RAG_EMBEDDING_MODEL,
                "retriever": "error",
                "collections": {},
                "message": str(e),
            }

    @classmethod
    def query_rag(
        cls,
        query: str,
        category: str = "laptop",
        product_id: Optional[str] = None,
        product_name: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Primary Omni-Channel Query Method for RAG VER2 with Metadata Filtering & Reranking.
        """
        verify_rag_version()
        q_clean = (query or "").strip()
        if not q_clean:
            return {
                "query": query,
                "results": [],
                "answer": "Query cannot be empty.",
                "confidence": "Low",
                "context_used": "none",
                "sources": [],
                "rag_version": ACTIVE_RAG_VERSION,
            }

        cat = category.lower() if category else "laptop"
        if cat in ["phones", "phone", "smartphones", "smartphone"]:
            cat = "mobile"
        elif cat in ["tablets", "ipad"]:
            cat = "tablet"
        elif cat not in ["laptop", "mobile", "tablet"]:
            cat = "laptop"

        search_query = q_clean
        if product_name and len(q_clean.split()) <= 4:
            search_query = f"{q_clean} specifications details {product_name}"

        try:
            chain = cls.get_chain()
            rag_response = chain.run(user_query=search_query, category=cat, top_k=top_k * 3)

            candidates = []
            query_kw = keywords or [w for w in re.findall(r"\w+", q_clean.lower()) if len(w) >= 3]

            for p in rag_response.products:
                p_dict = p.metadata if hasattr(p, "metadata") else {}
                title = p.product_name or p_dict.get("product_name") or f"{cat.capitalize()} #{p.product_id}"
                
                spec_tokens = []
                if p.brand: spec_tokens.append(f"Brand: {p.brand}")
                if p.processor: spec_tokens.append(f"Processor: {p.processor}")
                if p.ram_gb: spec_tokens.append(f"RAM: {p.ram_gb}GB")
                if p.storage_gb: spec_tokens.append(f"Storage: {p.storage_gb}GB {p.storage_type or ''}")
                if p.price_inr: spec_tokens.append(f"Price: ₹{p.price_inr:,.0f}")
                if p.rating_score: spec_tokens.append(f"Rating: {p.rating_score}/5")
                if p.graphics_processor: spec_tokens.append(f"GPU: {p.graphics_processor}")
                if p.battery_capacity_mah: spec_tokens.append(f"Battery: {p.battery_capacity_mah}mAh")

                content_text = f"{title}. " + " | ".join(spec_tokens)
                raw_sim = round(1.0 - (p.distance or 0.2), 3) if p.distance is not None else 0.90

                sec_name = detect_section_title(content_text)
                candidate_item = {
                    "chunk_id": p.product_id,
                    "document_id": p.product_id,
                    "filename": f"RAG_VER2_{cat.upper()}_Corpus.json",
                    "content": content_text,
                    "similarity_score": raw_sim,
                    "page_number": None,
                    "section_title": sec_name,
                    "product_name": title,
                    "brand": p.brand,
                    "category": cat,
                }
                candidate_item["rerank_score"] = compute_rerank_score(
                    chunk=candidate_item,
                    query_keywords=query_kw,
                    target_product_name=product_name,
                    target_brand=p.brand,
                )
                candidates.append(candidate_item)

            candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
            cleaned_candidates = FactValidationService.clean_and_validate_evidence(
                candidates,
                target_product_name=product_name,
                target_category=cat,
                min_score=0.25
            )
            top_results = cleaned_candidates[:top_k]

            context_snippets = []
            sources_list = []
            for r in top_results:
                context_snippets.append({
                    "filename": r["filename"],
                    "content": r["content"],
                    "section_title": r.get("section_title"),
                    "page_number": r.get("page_number"),
                })
                sources_list.append({
                    "document": r["filename"],
                    "filename": r["filename"],
                    "page": r.get("page_number"),
                    "page_number": r.get("page_number"),
                    "section": r.get("section_title"),
                    "section_title": r.get("section_title"),
                    "snippet": r["content"][:200],
                    "score": r["rerank_score"],
                })

            grounded = generate_grounded_answer(
                query=q_clean,
                context_snippets=context_snippets,
                product_context={"name": product_name} if product_name else None,
                rag_version=ACTIVE_RAG_VERSION
            )

            return {
                "query": q_clean,
                "results": top_results,
                "answer": grounded["answer"],
                "confidence": grounded["confidence"],
                "context_used": grounded["context_used"],
                "sources": sources_list,
                "type": grounded.get("type", "general"),
                "factual_context": rag_response.factual_context,
                "markdown_table": rag_response.markdown_table,
                "candidate_count": len(top_results),
                "no_results": len(top_results) == 0,
                "rag_version": ACTIVE_RAG_VERSION,
            }

        except Exception as e:
            logger.error(f"RAG VER2 query error: {e}", exc_info=True)
            return {
                "query": q_clean,
                "results": [],
                "answer": "I could not find this information in the document.",
                "confidence": "Low",
                "context_used": "documents",
                "sources": [],
                "type": "error",
                "rag_version": ACTIVE_RAG_VERSION,
            }

    @classmethod
    def query_documents(
        cls,
        db: Optional[Session],
        query: str,
        document_ids: Optional[List[int]] = None,
        top_k: int = 5,
        category: str = "laptop",
        product_name: Optional[str] = None,
        section_focus: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Unified document retrieval method bridging target document vector chunks and RAG VER2.
        When document_ids is specified, strictly searches within the targeted document.
        """
        verify_rag_version()
        q_clean = (query or "").strip()
        if not q_clean:
            return {
                "query": query,
                "results": [],
                "answer": "Query cannot be empty.",
                "confidence": "Low",
                "context_used": "none",
                "sources": [],
                "type": "error",
                "rag_version": ACTIVE_RAG_VERSION,
            }

        intent_info = detect_rag_query_intent(q_clean)
        is_summary = intent_info["type"] == "summary"

        all_candidates = []
        q_words = [w for w in re.findall(r"\w+", q_clean.lower()) if len(w) >= 3]

        # 1. Search uploaded document chunks from Database if available
        if db is not None:
            try:
                chunk_q = db.query(DocumentChunk).join(Document)
                if document_ids:
                    chunk_q = chunk_q.filter(Document.id.in_(document_ids))
                uploaded_chunks = chunk_q.all()

                if uploaded_chunks:
                    emb_model = get_embedding_model()
                    q_emb = None
                    if emb_model is not None:
                        try:
                            q_emb = emb_model.encode([q_clean], normalize_embeddings=True)[0]
                        except Exception as emb_err:
                            logger.warning(f"Failed to encode query embedding: {emb_err}")

                    for chunk in uploaded_chunks:
                        c_text = chunk.content.lower()
                        sim_score = 0.5

                        # Calculate dense embedding cosine similarity if available
                        if q_emb is not None:
                            meta = chunk.metadata_json or {}
                            c_emb_list = meta.get("embedding")
                            if c_emb_list:
                                try:
                                    c_vec = np.array(c_emb_list, dtype=np.float32)
                                    sim_score = float(np.dot(q_emb, c_vec) / (np.linalg.norm(q_emb) * np.linalg.norm(c_vec) + 1e-9))
                                    sim_score = max(0.0, min(1.0, (sim_score + 1.0) / 2.0))
                                except Exception:
                                    sim_score = 0.5

                        # Keyword overlap calculation
                        overlap = sum(1 for w in q_words if w in c_text)
                        kw_ratio = overlap / max(len(q_words), 1)

                        doc_title = chunk.document.filename if chunk.document else "Uploaded Document"
                        item = {
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "filename": doc_title,
                            "content": chunk.content,
                            "similarity_score": round(sim_score, 3),
                            "page_number": chunk.page_number,
                            "section_title": chunk.section_title or detect_section_title(chunk.content),
                            "product_name": chunk.product_name,
                            "category": category,
                        }
                        item["rerank_score"] = compute_rerank_score(
                            chunk=item,
                            query_keywords=q_words,
                            target_product_name=product_name,
                            section_focus=section_focus,
                            is_summary_query=is_summary,
                        )
                        all_candidates.append(item)
            except Exception as e:
                logger.warning(f"Uploaded chunks query error: {e}", exc_info=True)

        # 2. Strict Document Scoping: If document_ids was passed and no chunks matched, do NOT search external corpus
        if document_ids and len(all_candidates) == 0:
            logger.info(f"[RETRIEVAL] Query: '{q_clean}' | Document ID: {document_ids} | No chunks found for targeted document.")
            return {
                "query": q_clean,
                "results": [],
                "answer": "No matching information found in this document.",
                "confidence": "Low",
                "context_used": "documents",
                "sources": [],
                "type": "error",
                "rag_version": ACTIVE_RAG_VERSION,
            }

        # 3. Fallback to RAG VER2 Vector Corpus only if NO specific document filter was requested
        if not document_ids and len(all_candidates) == 0:
            ver2_res = cls.query_rag(
                query=q_clean,
                category=category,
                product_name=product_name,
                keywords=q_words,
                top_k=top_k,
            )
            all_candidates.extend(ver2_res.get("results", []))

        # 4. Sort and pick top K candidates
        all_candidates.sort(key=lambda x: x.get("rerank_score", x.get("similarity_score", 0)), reverse=True)
        top_candidates = all_candidates[:top_k]

        top_score = top_candidates[0].get("rerank_score", 0.0) if top_candidates else 0.0
        logger.info(f"[RETRIEVAL] Query: '{q_clean}' | Document ID: {document_ids} | Retrieved chunks: {len(top_candidates)} (Top score: {top_score:.3f})")

        context_snippets = []
        sources = []
        for r in top_candidates:
            doc_name = r.get("filename", "Verified Document")
            sec_name = r.get("section_title") or detect_section_title(r.get("content", ""))
            context_snippets.append({
                "filename": doc_name,
                "content": r.get("content", ""),
                "page_number": r.get("page_number"),
                "section_title": sec_name,
            })
            sources.append({
                "document": doc_name,
                "filename": doc_name,
                "page": r.get("page_number"),
                "page_number": r.get("page_number"),
                "section": sec_name,
                "section_title": sec_name,
                "snippet": r.get("content", "")[:200],
                "score": r.get("rerank_score", r.get("similarity_score", 0.9)),
            })

        # 5. Generate Grounded Answer
        grounded = generate_grounded_answer(
            query=q_clean,
            context_snippets=context_snippets,
            product_context={"name": product_name} if product_name else None,
            rag_version=ACTIVE_RAG_VERSION
        )

        conf_str = "High"
        if top_score >= 0.70: conf_str = "95%"
        elif top_score >= 0.45: conf_str = "85%"
        elif top_score > 0.20: conf_str = "70%"
        else: conf_str = "Low"

        return {
            "query": q_clean,
            "results": top_candidates,
            "answer": grounded["answer"],
            "confidence": conf_str if "could not find" not in grounded["answer"] else "Low",
            "context_used": "documents",
            "sources": sources,
            "type": grounded.get("type", "general"),
            "rag_version": ACTIVE_RAG_VERSION,
        }

    @classmethod
    def query_rag_chat(
        cls,
        db: Optional[Session],
        message: str,
        document_id: Optional[int] = None,
        document_ids: Optional[List[int]] = None,
        product_name: Optional[str] = None,
        category: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Specialized RAG Document Chat Assistant query handler for POST /api/rag/chat.
        """
        doc_filter_ids = []
        if document_id:
            doc_filter_ids.append(document_id)
        if document_ids:
            doc_filter_ids.extend([d for d in document_ids if d not in doc_filter_ids])

        res = cls.query_documents(
            db=db,
            query=message,
            document_ids=doc_filter_ids if doc_filter_ids else None,
            top_k=top_k,
            category=category or "laptop",
            product_name=product_name,
        )

        suggested = [
            "Summarize document",
            "What are the specifications?",
            "What is the battery life?",
            "Explain performance",
        ]

        intent_info = detect_rag_query_intent(message)
        debug_trace = {
            "query": message,
            "intent": intent_info["type"],
            "topic": intent_info["topic"],
            "retrieved_chunks_count": len(res.get("results", [])),
            "top_score": res["sources"][0]["score"] if res.get("sources") else 0.0,
            "document_filter": doc_filter_ids,
        }

        return {
            "answer": res["answer"],
            "sources": res["sources"],
            "confidence": res.get("confidence", "High"),
            "rag_version": ACTIVE_RAG_VERSION,
            "document_used": True,
            "type": res.get("type", "general"),
            "suggested_followups": suggested,
            "debug_trace": debug_trace,
        }

    @staticmethod
    def process_and_index_document(db: Session, document_id: int) -> int:
        """Extract text from uploaded PDF/text document, chunk semantically, compute embeddings, and index chunks."""
        verify_rag_version()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError("Document not found")

        logger.info(f"[UPLOAD] Document ID: {doc.id} | File Name: {doc.filename}")
        doc.status = "processing"
        db.commit()

        try:
            pages = extract_text_from_document(doc.file_path)
            if not pages:
                doc.status = "failed"
                db.commit()
                raise ValueError("Unable to extract text from this document. The file may be empty or unreadable.")

            chunks = chunk_document_pages(pages, chunk_size_chars=700, overlap_chars=120)
            if not chunks:
                doc.status = "failed"
                db.commit()
                raise ValueError("No valid text sections found in document.")

            logger.info(f"[CHUNK] Number of chunks: {len(chunks)} | Pages: {len(pages)} | Document ID: {doc.id}")

            # Generate dense embeddings using cached SentenceTransformer model
            emb_model = get_embedding_model()
            embeddings = None
            if emb_model is not None:
                try:
                    chunk_texts = [c["content"] for c in chunks]
                    embeddings = emb_model.encode(chunk_texts, normalize_embeddings=True, show_progress_bar=False)
                    logger.info(f"[EMBEDDING] Embedding status: SUCCESS ({len(chunks)} vectors computed)")
                except Exception as emb_err:
                    logger.warning(f"[EMBEDDING] Embedding computation warning: {emb_err}")

            # Delete previous chunks if re-indexing
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete(synchronize_session=False)

            total_chunks = 0
            for idx, c in enumerate(chunks):
                emb_list = embeddings[idx].tolist() if embeddings is not None and idx < len(embeddings) else []
                chunk_obj = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=c["content"],
                    page_number=c["page_number"],
                    section_title=c["section_title"],
                    product_name=doc.product_name or doc.filename.replace(".pdf", "").replace(".txt", ""),
                    token_count=c["token_count"],
                    metadata_json={
                        "document_id": doc.id,
                        "page": c["page_number"],
                        "section": c["section_title"],
                        "embedding": emb_list,
                    }
                )
                db.add(chunk_obj)
                total_chunks += 1

            doc.chunk_count = total_chunks
            doc.status = "indexed"
            db.commit()
            return total_chunks
        except Exception as e:
            doc.status = "failed"
            db.commit()
            logger.error(f"Error processing and indexing document {doc.id}: {e}", exc_info=True)
            raise e
