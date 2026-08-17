import os
import shutil
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.document import Document, DocumentChunk
from schemas.document import (
    DocumentResponse,
    DocumentChunkResponse,
    DocumentQueryRequest,
    DocumentQueryResponse,
    DocumentQueryResult,
    RAGChatRequest,
    RAGChatResponse,
    SourceCitationItem,
)
from services.rag_service import RAGService
from utils.security import get_optional_user, get_current_user
from utils.config import settings

logger = logging.getLogger("backend.documents")

router = APIRouter(tags=["Documents & RAG"])

@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """List all indexed PDF manuals, datasheets, and articles."""
    query = db.query(Document)
    if current_user and not current_user.is_admin:
        query = query.filter((Document.user_id == current_user.id) | Document.user_id.is_(None))
    docs = query.order_by(Document.created_at.desc()).all()
    return docs

@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Upload PDF or Text document and index chunks with rich metadata."""
    fname = file.filename or "uploaded_document.pdf"
    if not fname.lower().endswith((".pdf", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a PDF or TXT file."
        )

    os.makedirs(settings.DOCUMENTS_STORAGE_PATH, exist_ok=True)
    file_path = os.path.join(settings.DOCUMENTS_STORAGE_PATH, fname)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)
    if file_size > 25 * 1024 * 1024:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 25MB."
        )

    file_type = file.content_type or ("application/pdf" if fname.endswith(".pdf") else "text/plain")

    doc = Document(
        user_id=current_user.id if current_user else None,
        filename=fname,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        status="uploading"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process and index document chunks with semantic chunking
    try:
        doc_id_val = int(getattr(doc, "id"))
        total_chunks = RAGService.process_and_index_document(db, doc_id_val)
        setattr(doc, "chunk_count", total_chunks)
        db.commit()
    except Exception as e:
        logger.error(f"Error indexing document {getattr(doc, 'id', 'unknown')}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"I could not process this document request. Please try again."
        )

    db.refresh(doc)
    return doc

@router.get("/documents/health")
@router.get("/rag/health")
def get_documents_rag_health():
    """RAG VER2 health status endpoint."""
    return RAGService.check_health()

@router.post("/documents/query", response_model=DocumentQueryResponse)
def query_documents(
    data: DocumentQueryRequest,
    db: Session = Depends(get_db)
):
    """Hybrid retrieval search across indexed document datasheets and RAG VER2 vector corpus."""
    if not data.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty.")

    rag_res = RAGService.query_documents(
        db=db,
        query=data.query.strip(),
        document_ids=data.document_ids,
        top_k=data.top_k or 5,
    )

    return DocumentQueryResponse(
        query=data.query,
        results=[
            DocumentQueryResult(
                chunk_id=r["chunk_id"],
                document_id=r.get("document_id"),
                filename=r["filename"],
                content=r["content"],
                similarity_score=r.get("similarity_score", 0.5),
                page_number=r.get("page_number"),
                section_title=r.get("section_title"),
                product_name=r.get("product_name"),
            ) for r in rag_res.get("results", [])
        ],
        answer=rag_res.get("answer", ""),
        confidence=rag_res.get("confidence", "High"),
        context_used=rag_res.get("context_used", "documents"),
        sources=rag_res.get("sources", []),
        rag_version=rag_res.get("rag_version", "ver2"),
        document_used=True,
        type=rag_res.get("type", "general"),
    )

@router.post("/rag/chat", response_model=RAGChatResponse)
@router.post("/documents/chat", response_model=RAGChatResponse)
def rag_chat(
    data: RAGChatRequest,
    db: Session = Depends(get_db)
):
    """
    Dedicated RAG Document Chat Assistant API.
    Returns structured answer cards, source citations, confidence rating, and debug trace.
    """
    msg = data.message.strip()
    if not msg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")

    try:
        res = RAGService.query_rag_chat(
            db=db,
            message=msg,
            document_id=data.document_id,
            document_ids=data.document_ids,
            product_name=data.product_name,
            category=data.category,
            history=data.history,
            top_k=data.top_k or 5,
        )

        sources_out = [
            SourceCitationItem(
                document=s.get("document") or s.get("filename") or "Product Document",
                page=s.get("page") or s.get("page_number"),
                section=s.get("section") or s.get("section_title"),
                snippet=s.get("snippet"),
                score=s.get("score"),
            ) for s in res.get("sources", [])
        ]

        return RAGChatResponse(
            answer=res.get("answer", "I could not find this information in the document."),
            sources=sources_out,
            confidence=res.get("confidence", "High"),
            rag_version="ver2",
            document_used=True,
            type=res.get("type", "general"),
            suggested_followups=res.get("suggested_followups", []),
            debug_trace=res.get("debug_trace"),
        )
    except Exception as e:
        logger.error(f"Error in RAG chat: {e}", exc_info=True)
        return RAGChatResponse(
            answer="I could not process this document request. Please try again.",
            sources=[],
            confidence="Low",
            rag_version="ver2",
            document_used=False,
            type="error",
            suggested_followups=["What are the specifications?", "Explain performance"],
            debug_trace={"error": str(e)},
        )

@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Delete an indexed document and its vector chunks."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Delete all associated document chunks explicitly
    try:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)
    except Exception as e:
        logger.warning(f"Failed to delete chunks for doc {document_id}: {e}")

    # Remove physical file on disk if exists
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete physical file {doc.file_path}: {e}")

    db.delete(doc)
    db.commit()

    return {"success": True, "message": f"Document '{doc.filename}' deleted successfully."}
