import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from schemas.product import ProductSchema
from schemas.recommendation import RecommendedProductItem


class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant'
    content: str


class SourceCitation(BaseModel):
    filename: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    snippet: str = ""
    score: Optional[float] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    product_id: Optional[Any] = None
    active_product_id: Optional[Any] = None
    shortlisted_ids: Optional[List[str]] = []
    context_products: Optional[List[Dict[str, Any]]] = []
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    message: str
    answer: Optional[str] = None
    intent: str
    type: Optional[str] = "general"  # "specification" | "comparison" | "recommendation" | "document" | "explanation" | "general"
    field: Optional[str] = None  # "ram" | "price" | "storage" | "processor" | "gpu" | "battery" | "display" etc.
    verified: bool = True
    source_type: Optional[str] = "database"  # "database" | "documents" | "hybrid" | "general"
    product: Optional[Dict[str, Any]] = None
    products: List[Any] = []
    compared_products: List[Any] = []
    ignored_products: List[Any] = []
    recommendations: List[Any] = []
    comparison: Optional[Dict[str, Any]] = None
    rag_sources: List[Dict[str, Any]] = []
    sources: List[SourceCitation] = []
    retrieved_documents: List[Dict[str, Any]] = []
    suggested_followups: List[str] = []
    confidence: str = "Database Verified"
    context_used: str = "database"  # "database" | "documents" | "hybrid" | "general"
    rag_used: bool = False
    database_used: bool = True
    source: Optional[str] = "Verified Product Database"
    show_recommendations: bool = False
    show_comparison: bool = False
    show_sources: bool = True
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    rag_version: Optional[str] = "ver2"
    debug_trace: Optional[Dict[str, Any]] = None
    response_mode: Optional[str] = "FAST"  # "FAST" | "AI" | "RAG"
