import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    product_name: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    product_name: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class DocumentQueryRequest(BaseModel):
    query: str
    document_ids: Optional[List[int]] = None
    top_k: Optional[int] = 5

class DocumentQueryResult(BaseModel):
    chunk_id: Any
    document_id: Optional[Any] = None
    filename: str
    content: str
    similarity_score: float
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    product_name: Optional[str] = None

class DocumentQueryResponse(BaseModel):
    query: str
    results: List[DocumentQueryResult]
    answer: str
    confidence: str = "High"
    context_used: str = "documents"
    sources: List[Dict[str, Any]] = []
    rag_version: Optional[str] = "ver2"
    document_used: bool = True
    type: Optional[str] = "general"
    suggested_followups: Optional[List[str]] = []
    debug_trace: Optional[Dict[str, Any]] = None

class SourceCitationItem(BaseModel):
    document: str
    page: Optional[Any] = None
    section: Optional[str] = None
    snippet: Optional[str] = None
    score: Optional[float] = None

class RAGChatRequest(BaseModel):
    message: str
    document_id: Optional[int] = None
    document_ids: Optional[List[int]] = None
    product_name: Optional[str] = None
    category: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None
    top_k: Optional[int] = 5

class RAGChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitationItem] = []
    confidence: str = "High"
    rag_version: str = "ver2"
    document_used: bool = True
    type: str = "general"
    suggested_followups: List[str] = []
    debug_trace: Optional[Dict[str, Any]] = None

class RAGHealthResponse(BaseModel):
    status: str
    rag_version: str = "ver2"
    directory: str
    dataset: str
    vector_store: str
    embedding_model: str
    retriever: str
    collections: Dict[str, int] = {}
    llm: Optional[str] = "configured"
    message: Optional[str] = None
