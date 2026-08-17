import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from services.conversation_memory_service import ConversationMemoryService

logger = logging.getLogger("backend.session")

router = APIRouter(prefix="/session", tags=["Session Persistence"])


class SaveSessionRequest(BaseModel):
    conversation_id: str
    comparison_products: Optional[List[Any]] = []
    selected_products: Optional[List[Any]] = []
    active_product: Optional[Any] = None
    messages: Optional[List[Dict[str, Any]]] = []
    last_intent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SaveSessionResponse(BaseModel):
    status: str = "saved"
    conversation_id: str
    product_count: Optional[int] = 0
    expires_at: Optional[str] = None


@router.post("/save", response_model=SaveSessionResponse)
def save_session(data: SaveSessionRequest, db: Session = Depends(get_db)):
    """
    Save or update temporary conversation session, active products, and comparison state.
    """
    cid = (data.conversation_id or "").strip()
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversation_id is required"
        )

    comp_items = data.comparison_products or data.selected_products or []

    res = ConversationMemoryService.save_session_state(
        db=db,
        session_id=cid,
        comparison_products=comp_items,
        active_product=data.active_product,
        messages=data.messages,
        last_intent=data.last_intent,
        metadata=data.metadata
    )

    return SaveSessionResponse(
        status="saved",
        conversation_id=cid,
        product_count=res.get("product_count", 0),
        expires_at=res.get("expires_at"),
    )


@router.get("/{conversation_id}")
def get_session(conversation_id: str, db: Session = Depends(get_db)):
    """
    Retrieve active temporary session with MySQL database validation on all products.
    Returns empty session dictionary if not found yet (preventing 404 console errors).
    """
    cid = (conversation_id or "").strip()
    if not cid:
        return {
            "conversation_id": "",
            "comparison_products": [],
            "selected_products": [],
            "active_product": None,
            "messages": [],
            "status": "empty",
        }

    state = ConversationMemoryService.get_session_state(db=db, session_id=cid)
    if not state:
        return {
            "conversation_id": cid,
            "comparison_products": [],
            "selected_products": [],
            "active_product": None,
            "messages": [],
            "status": "empty",
        }

    return state


@router.delete("/{conversation_id}")
def delete_session(conversation_id: str):
    """
    Delete temporary session from memory.
    """
    cid = (conversation_id or "").strip()
    ConversationMemoryService.clear_session(cid)
    return {"status": "deleted", "conversation_id": cid}
