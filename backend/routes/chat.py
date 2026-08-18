import logging
import re
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from database import get_db
from models.user import User
from models.product import Product
from schemas.chat import ChatRequest, ChatResponse, SourceCitation
from services.nlp_service import NLPService, IntentType
from services.product_service import ProductService
from services.query_router import QueryRouter
from services.rag_service import RAGService
from services.conversation_memory_service import ConversationMemoryService
from services.user_storage_service import UserStorageService
from services.product_data_validator import (
    get_normalized_product_facts,
    get_data_quality_report,
)
from utils.security import get_optional_user, get_current_user
from services.notification_service import NotificationService

logger = logging.getLogger("backend.chat")

router = APIRouter(prefix="", tags=["AI Chat"])


class NLPAnalyzeRequest(BaseModel):
    message: str


class RAGSearchRequest(BaseModel):
    query: str
    product_id: Optional[Any] = None
    top_k: Optional[int] = 5


class SaveContextRequest(BaseModel):
    conversation_id: str
    active_products: Optional[List[Any]] = []
    selected_products: Optional[List[Any]] = []
    last_intent: Optional[str] = "general"


def _resolve_contextual_products(
    db: Session,
    nlp_data: Dict[str, Any],
    direct_product_id: Optional[Any],
    shortlisted_ids: Optional[List[str]],
    context_products: Optional[List[Dict[str, Any]]],
    selected_products: Optional[List[Dict[str, Any]]],
    history: Optional[List[Any]],
    session_id: Optional[str] = None,
    user_id: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Deterministically resolve active products from:
    1. Direct context_products or selected_products array from request
    2. User-specific database conversation_context
    3. Direct active_product_id or product_id
    4. Named product entities in query (e.g. 'MSI GL62M', 'iPhone 15')
    5. Session Memory State / previous comparison set
    6. Direct shortlisted_ids
    7. Conversation history
    """
    resolved: List[Dict[str, Any]] = []

    # 1. Direct context_products or selected_products list from API request
    raw_products = context_products or selected_products or []
    if raw_products:
        sorted_cp = sorted(raw_products, key=lambda x: x.get("index", 999))
        for idx, cp in enumerate(sorted_cp, start=1):
            c_index = cp.get("index") or idx
            cp_id = cp.get("id") or cp.get("product_id")
            p_facts = None
            if cp_id:
                p_facts = ProductService.get_by_id(db, cp_id)
            if not p_facts and cp.get("name"):
                found = ProductService.search_by_name(db, cp["name"], limit=1)
                if found:
                    p_facts = found[0]
            if not p_facts and (cp.get("name") or cp.get("price")):
                p_facts = cp

            if p_facts:
                p_copy = dict(p_facts)
                p_copy["context_index"] = c_index
                resolved.append(p_copy)

    # 2. Database persistent conversation context for logged-in user
    if not resolved and user_id and session_id:
        db_context = UserStorageService.get_conversation_context(db, user_id, session_id)
        if db_context and db_context.get("active_products"):
            for idx, p in enumerate(db_context["active_products"], start=1):
                if isinstance(p, dict):
                    p_copy = dict(p)
                    p_copy["context_index"] = p.get("context_index") or idx
                    resolved.append(p_copy)

    # 3. Direct active product ID from request (only if not already resolved from context_products)
    if direct_product_id and not resolved:
        p_facts = ProductService.get_by_id(db, direct_product_id)
        if p_facts:
            p_copy = dict(p_facts)
            p_copy["context_index"] = 1
            resolved.append(p_copy)

    # 4. Named product entities from query (e.g. 'MSI GL62M', 'Redmi Note 5')
    named_entities = nlp_data.get("product_names", [])
    if not resolved and named_entities:
        seen_ids = set()
        for idx, name_query in enumerate(named_entities, start=1):
            matches = ProductService.search_by_name(db, name_query, limit=2)
            for m in matches:
                if m["id"] not in seen_ids:
                    p_copy = dict(m)
                    p_copy["context_index"] = idx
                    resolved.append(p_copy)
                    seen_ids.add(m["id"])

    # 5. Session memory context (if follow-up or comparison)
    if not resolved and session_id:
        mem_session = ConversationMemoryService.get_or_create(session_id)
        if nlp_data.get("is_comparison") and mem_session.current_comparison_set:
            for idx, p in enumerate(mem_session.current_comparison_set, start=1):
                p_copy = dict(p)
                p_copy["context_index"] = idx
                resolved.append(p_copy)
        elif mem_session.active_product:
            p_copy = dict(mem_session.active_product)
            p_copy["context_index"] = 1
            resolved.append(p_copy)

    # 6. Shortlisted IDs
    if not resolved and shortlisted_ids:
        seen_ids = set()
        for idx, sid in enumerate(shortlisted_ids, start=1):
            p_facts = ProductService.get_by_id(db, sid)
            if p_facts and p_facts["id"] not in seen_ids:
                p_copy = dict(p_facts)
                p_copy["context_index"] = idx
                resolved.append(p_copy)
                seen_ids.add(p_facts["id"])

    # 7. History extraction fallback if still empty
    if not resolved and history and nlp_data.get("is_followup"):
        seen_ids = set()
        for msg in reversed(history[-6:]):
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            matches = re.findall(r"\*\*([^*]+)\*\*", content)
            for m in matches:
                if len(m.split()) >= 2 and not any(kw in m.lower() for kw in ["verdict", "score", "spec", "analysis"]):
                    found_list = ProductService.search_by_name(db, m.strip(), limit=1)
                    if found_list and found_list[0]["id"] not in seen_ids:
                        p_copy = dict(found_list[0])
                        p_copy["context_index"] = len(resolved) + 1
                        resolved.append(p_copy)
                        seen_ids.add(found_list[0]["id"])
                        if len(resolved) >= 2:
                            break

    return resolved


@router.post("/chat", response_model=ChatResponse)
def handle_chat_message(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Authoritative AI Chat & Analysis Endpoint.
    Dispatches query strictly via QueryRouter according to detected intent.
    Maintains user-isolated database chat history & conversation context in MySQL.
    """
    user_query = data.message.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")

    sid = data.conversation_id or data.session_id or "default_session"
    user_id = current_user.id if current_user else None

    try:
        import time as _time
        _t0 = _time.monotonic()

        # 1. NLP Intent & Entity Extraction
        mem = ConversationMemoryService.get_or_create(sid)
        if data.battle_result:
            mem.update_battle_result(data.battle_result)
        if data.selected_products:
            mem.update_comparison_set(data.selected_products)

        nlp_data = NLPService.parse_query_heuristics(
            user_query,
            conversation_context={"active_product_name": mem.active_product_name, "category": mem.active_category}
        )
        _t_nlp = _time.monotonic()

        # 2. Contextual Product Resolution
        direct_pid = data.product_id or data.active_product_id
        active_products = _resolve_contextual_products(
            db,
            nlp_data,
            direct_pid,
            data.shortlisted_ids,
            data.context_products,
            data.selected_products,
            data.history,
            session_id=sid,
            user_id=user_id
        )
        _t_resolve = _time.monotonic()

        # 3. Central Query Routing
        route_result = QueryRouter.route_query(
            db=db,
            user_query=user_query,
            nlp_data=nlp_data,
            active_products=active_products,
            history=data.history,
            session_id=sid
        )
        _t_route = _time.monotonic()

        # 4. Format Sources Citations
        sources_citations: List[SourceCitation] = []
        raw_sources = route_result.get("sources", [])
        for s in raw_sources:
            sources_citations.append(
                SourceCitation(
                    filename=s.get("filename", "Verified Database"),
                    page_number=s.get("page_number"),
                    section_title=s.get("section_title"),
                    snippet=s.get("snippet", ""),
                    score=s.get("score"),
                )
            )

        ans_msg = route_result.get("answer") or route_result.get("message", "")
        rag_used = route_result.get("context_used") in ["documents", "hybrid"] or route_result.get("intent") in [IntentType.DOCUMENT_QUERY, IntentType.RAG_DOCUMENT_QUERY]
        database_used = route_result.get("context_used") == "database" or not rag_used
        primary_source_str = raw_sources[0].get("filename", "Verified Product Database") if raw_sources else "Verified Product Database"

        # 5. Update In-Memory Session
        res_product = route_result.get("product") or (active_products[0] if active_products else None)
        res_category = route_result.get("category") or nlp_data.get("category")
        comp_products = route_result.get("products") if (route_result.get("intent") == IntentType.PRODUCT_COMPARISON and len(route_result.get("products", [])) >= 2) else None

        ConversationMemoryService.update_session(
            session_id=sid,
            product=res_product,
            category=res_category,
            query=user_query,
            answer=ans_msg,
            intent=route_result.get("intent"),
            comparison_products=comp_products,
        )

        # 6. Authoritative Database Storage for Logged-In User (non-blocking)
        if user_id:
            try:
                # Save user turn
                UserStorageService.save_chat_message(
                    db=db,
                    user_id=user_id,
                    conversation_id=sid,
                    role="user",
                    message=user_query,
                    intent=str(route_result.get("intent", "user_query")),
                    product_context=active_products
                )
                # Save assistant turn
                UserStorageService.save_chat_message(
                    db=db,
                    user_id=user_id,
                    conversation_id=sid,
                    role="assistant",
                    message=ans_msg,
                    intent=str(route_result.get("intent")),
                    product_context=route_result.get("products") or ([res_product] if res_product else [])
                )
                # Save persistent active context
                UserStorageService.save_conversation_context(
                    db=db,
                    user_id=user_id,
                    conversation_id=sid,
                    active_products=active_products,
                    selected_products=data.context_products or active_products,
                    last_intent=str(route_result.get("intent"))
                )
            except Exception as save_err:
                logger.error(f"Failed to persist chat message to MySQL for user #{user_id}: {save_err}")

        _t_end = _time.monotonic()

        # Inject performance timing into debug_trace
        timing = {
            "nlp_ms": round((_t_nlp - _t0) * 1000, 1),
            "resolve_ms": round((_t_resolve - _t_nlp) * 1000, 1),
            "route_ms": round((_t_route - _t_resolve) * 1000, 1),
            "storage_ms": round((_t_end - _t_route) * 1000, 1),
            "total_ms": round((_t_end - _t0) * 1000, 1),
        }
        debug_trace = route_result.get("debug_trace") or {}
        debug_trace["timing"] = timing
        response_mode = route_result.get("response_mode", "FAST")

        response = ChatResponse(
            message=ans_msg,
            answer=ans_msg,
            intent=route_result.get("intent", IntentType.UNKNOWN),
            type=route_result.get("type", "specification" if route_result.get("intent") in [IntentType.PRODUCT_SPECIFICATION, IntentType.PRODUCT_PRICE] else "general"),
            field=route_result.get("field", nlp_data.get("spec_field")),
            verified=route_result.get("verified", True),
            source_type=route_result.get("source_type", route_result.get("context_used", "database")),
            product=res_product,
            products=route_result.get("products", []),
            compared_products=route_result.get("compared_products", []),
            ignored_products=route_result.get("ignored_products", []),
            recommendations=route_result.get("recommendations", []),
            comparison=route_result.get("comparison"),
            rag_sources=raw_sources,
            sources=sources_citations,
            retrieved_documents=raw_sources,
            suggested_followups=route_result.get("suggested_followups", []),
            confidence=route_result.get("confidence", "Database Verified"),
            context_used=route_result.get("context_used", "database"),
            rag_used=rag_used,
            database_used=database_used,
            source=primary_source_str,
            show_recommendations=route_result.get("show_recommendations", False),
            show_comparison=route_result.get("show_comparison", False),
            show_sources=route_result.get("show_sources", True),
            session_id=sid,
            conversation_id=sid,
            rag_version=route_result.get("rag_version", "ver2"),
            debug_trace=debug_trace,
            response_mode=response_mode,
        )

        if current_user:
            notif_title = "AI Analysis Completed" if response_mode == "FAST" else ("RAG Document Analysis Ready" if response_mode == "RAG" else "AI Chat Response Ready")
            notif_type = "RAG" if response_mode == "RAG" else "AI_CHAT"
            NotificationService.create_notification(
                db=db,
                user_id=current_user.id,
                title=notif_title,
                message=f"Analysis completed for query: '{user_query[:60]}'",
                type=notif_type,
                reference_id=sid,
            )

        return response
    except Exception as e:
        logger.error(f"Error in handle_chat_message for query '{user_query}': {e}", exc_info=True)
        fallback_msg = "I couldn't complete the product analysis. Please try again."
        return ChatResponse(
            message=fallback_msg,
            answer=fallback_msg,
            intent=IntentType.UNKNOWN,
            type="error",
            field=None,
            verified=False,
            source_type="database",
            product=None,
            products=[],
            recommendations=[],
            sources=[],
            confidence="Low",
            context_used="general",
            show_recommendations=False,
            show_comparison=False,
            show_sources=False,
            suggested_followups=[
                "Tell me about ASUS ROG",
                "Explain product 1",
                "Compare ASUS and MSI",
            ],
            session_id=sid,
            conversation_id=sid,
            rag_version="ver2",
        )


# =========================================================================
# CONVERSATIONS & HISTORY ENDPOINTS (STRICT USER ISOLATION)
# =========================================================================

@router.get("/chat/conversations")
def get_user_conversations(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    List all saved AI conversations for the logged-in user.
    Returns empty list for guest users without error.
    """
    if not current_user:
        return []
    return UserStorageService.get_user_conversations(db=db, user_id=current_user.id)


@router.get("/chat/conversations/{conversation_id}")
@router.get("/chat/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieve all messages in a specific conversation for the logged-in user.
    """
    if not current_user:
        return []
    return UserStorageService.get_conversation_messages(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id
    )


@router.delete("/chat/conversations/{conversation_id}")
def delete_user_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a conversation from chat_history and conversation_context.
    """
    UserStorageService.delete_conversation(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id
    )
    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/chat/context/{conversation_id}")
def get_user_chat_context(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieve stored active product context for the logged-in user.
    """
    if not current_user:
        return {"conversation_id": conversation_id, "active_products": [], "selected_products": []}

    ctx = UserStorageService.get_conversation_context(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id
    )
    if not ctx:
        return {"conversation_id": conversation_id, "active_products": [], "selected_products": []}
    return ctx


@router.post("/chat/context")
def save_user_chat_context(
    req: SaveContextRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Save active product context directly to MySQL.
    """
    if not current_user:
        return {
            "status": "guest",
            "conversation_id": req.conversation_id,
            "product_count": len(req.active_products or []),
        }

    ctx = UserStorageService.save_conversation_context(
        db=db,
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        active_products=req.active_products,
        selected_products=req.selected_products,
        last_intent=req.last_intent
    )
    prod_cnt = len(req.active_products or [])
    return {
        "status": "saved",
        "conversation_id": ctx.conversation_id,
        "product_count": prod_cnt,
    }


@router.post("/nlp/analyze")
def analyze_nlp_intent(req: NLPAnalyzeRequest):
    """
    Dedicated NLP Intent & Entity Analysis Endpoint.
    """
    return NLPService.parse_query_heuristics(req.message)


@router.get("/rag/health")
def get_rag_health_status():
    """
    RAG Health Check Endpoint verifying RAG VER2 pipeline status.
    """
    return RAGService.check_health()
