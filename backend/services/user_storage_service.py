"""
User Storage Service
Authoritative MySQL persistence layer for:
- User AI Chat Messages & Multi-turn Conversations (chat_history)
- Product Comparisons & Generated Matrices (product_comparisons)
- User-specific Active Context & Shortlists (conversation_context)
- Aggregated User Profile Metrics
"""
from __future__ import annotations

import datetime
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from models.chat_history import ChatHistory, ProductComparison, ConversationContext
from models.favorite import Favorite
from models.user import User

logger = logging.getLogger("backend.user_storage")


def _sanitize_for_json(data: Any) -> Any:
    """Recursively convert Pydantic models, ORM models, dates, sets into JSON primitives."""
    if data is None:
        return None
    if isinstance(data, (str, int, float, bool)):
        return data
    if isinstance(data, (datetime.datetime, datetime.date)):
        return data.isoformat()
    if hasattr(data, "model_dump"):
        return _sanitize_for_json(data.model_dump())
    if hasattr(data, "dict") and callable(getattr(data, "dict")):
        return _sanitize_for_json(data.dict())
    if hasattr(data, "__dict__"):
        clean_dict = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        return _sanitize_for_json(clean_dict)
    if isinstance(data, dict):
        return {str(k): _sanitize_for_json(v) for k, v in data.items()}
    if isinstance(data, (list, tuple, set)):
        return [_sanitize_for_json(item) for item in data]
    return str(data)


def _extract_uid(user_id: Any) -> int:
    """Safely extracts integer user_id from integer, string, or SQLAlchemy User model."""
    if user_id is None:
        return 0
    if hasattr(user_id, "id"):
        val = getattr(user_id, "id")
        return int(val) if val is not None else 0
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return 0


class UserStorageService:
    # =========================================================================
    # 1. AI CHAT HISTORY & CONVERSATIONS
    # =========================================================================

    @staticmethod
    def save_chat_message(
        db: Session,
        user_id: Any,
        conversation_id: str,
        role: str,
        message: str,
        intent: Optional[str] = None,
        product_context: Optional[List[Any]] = None
    ) -> ChatHistory:
        """Persist a single chat turn (user or assistant) linked to user_id in MySQL."""
        cleaned_context = _sanitize_for_json(product_context) if product_context else []
        uid = _extract_uid(user_id)
        record = ChatHistory(
            user_id=uid,
            conversation_id=conversation_id.strip(),
            role=str(role),
            message=str(message),
            intent=str(intent) if intent else None,
            product_context=cleaned_context,
            created_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_conversation_messages(
        db: Session,
        user_id: Any,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Retrieve all chronological messages for a conversation belonging to user_id."""
        uid = _extract_uid(user_id)
        rows = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == uid, ChatHistory.conversation_id == conversation_id.strip())
            .order_by(ChatHistory.created_at.asc())
            .all()
        )

        results = []
        for r in rows:
            results.append({
                "id": str(r.id),
                "role": r.role,
                "content": r.message,
                "message": r.message,
                "intent": r.intent,
                "product_context": r.product_context or [],
                "products": r.product_context or [],
                "timestamp": r.created_at.isoformat() if r.created_at else None,
            })
        return results

    @staticmethod
    def get_user_conversations(
        db: Session,
        user_id: Any,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List all distinct conversations for the user with topic title, last message,
        and timestamp.
        """
        uid = _extract_uid(user_id)
        subq = (
            db.query(
                ChatHistory.conversation_id,
                func.max(ChatHistory.created_at).label("max_created"),
                func.count(ChatHistory.id).label("msg_count"),
            )
            .filter(ChatHistory.user_id == uid)
            .group_by(ChatHistory.conversation_id)
            .subquery()
        )

        rows = (
            db.query(ChatHistory, subq.c.msg_count)
            .join(
                subq,
                (ChatHistory.conversation_id == subq.c.conversation_id)
                & (ChatHistory.created_at == subq.c.max_created),
            )
            .filter(ChatHistory.user_id == uid)
            .order_by(desc(ChatHistory.created_at))
            .limit(limit)
            .all()
        )

        conversations = []
        for last_msg, count in rows:
            first_user_msg = (
                db.query(ChatHistory)
                .filter(
                    ChatHistory.user_id == uid,
                    ChatHistory.conversation_id == last_msg.conversation_id,
                    ChatHistory.role == "user",
                )
                .order_by(ChatHistory.created_at.asc())
                .first()
            )

            title = first_user_msg.message[:60] if first_user_msg else f"Chat {last_msg.conversation_id[:8]}"
            if first_user_msg and len(first_user_msg.message) > 60:
                title += "..."

            conversations.append({
                "conversation_id": last_msg.conversation_id,
                "title": title,
                "last_message": last_msg.message[:120],
                "last_role": last_msg.role,
                "message_count": count,
                "last_intent": last_msg.intent or "general",
                "products_discussed": [p.get("name") for p in (last_msg.product_context or []) if isinstance(p, dict) and p.get("name")],
                "updated_at": last_msg.created_at.isoformat() if last_msg.created_at else None,
            })

        return conversations

    @staticmethod
    def delete_conversation(
        db: Session,
        user_id: Any,
        conversation_id: str
    ) -> bool:
        """Delete conversation messages and stored context for user_id."""
        cid = conversation_id.strip()
        uid = _extract_uid(user_id)
        db.query(ChatHistory).filter(
            ChatHistory.user_id == uid,
            ChatHistory.conversation_id == cid
        ).delete(synchronize_session=False)

        db.query(ConversationContext).filter(
            ConversationContext.user_id == uid,
            ConversationContext.conversation_id == cid
        ).delete(synchronize_session=False)

        db.commit()
        return True

    # =========================================================================
    # 2. PRODUCT COMPARISONS
    # =========================================================================

    @staticmethod
    def save_product_comparison(
        db: Session,
        user_id: Any,
        comparison_id: str,
        product_ids: List[Any],
        comparison_result: Optional[Dict[str, Any]] = None
    ) -> ProductComparison:
        """Persist a product comparison matrix for user_id in MySQL."""
        cid = comparison_id.strip()
        uid = _extract_uid(user_id)
        clean_pids = _sanitize_for_json(product_ids)
        clean_res = _sanitize_for_json(comparison_result)

        existing = (
            db.query(ProductComparison)
            .filter(ProductComparison.user_id == uid, ProductComparison.comparison_id == cid)
            .first()
        )

        if existing:
            existing.product_ids = clean_pids
            existing.comparison_result = clean_res
            existing.created_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            db.commit()
            db.refresh(existing)
            return existing

        record = ProductComparison(
            user_id=uid,
            comparison_id=cid,
            product_ids=clean_pids,
            comparison_result=clean_res,
            created_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_user_comparisons(
        db: Session,
        user_id: Any,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve all saved comparisons for user_id."""
        uid = _extract_uid(user_id)
        rows = (
            db.query(ProductComparison)
            .filter(ProductComparison.user_id == uid)
            .order_by(desc(ProductComparison.created_at))
            .limit(limit)
            .all()
        )

        results = []
        for r in rows:
            results.append({
                "id": r.id,
                "comparison_id": r.comparison_id,
                "product_ids": r.product_ids or [],
                "comparison_result": r.comparison_result or {},
                "summary": (r.comparison_result or {}).get("winner_summary") if isinstance(r.comparison_result, dict) else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return results

    @staticmethod
    def delete_product_comparison(
        db: Session,
        user_id: Any,
        comparison_id: str
    ) -> bool:
        """Delete a saved comparison for user_id."""
        uid = _extract_uid(user_id)
        db.query(ProductComparison).filter(
            ProductComparison.user_id == uid,
            ProductComparison.comparison_id == comparison_id.strip()
        ).delete(synchronize_session=False)
        db.commit()
        return True

    # =========================================================================
    # 3. USER CONVERSATION CONTEXT & ACTIVE PRODUCTS
    # =========================================================================

    @staticmethod
    def save_conversation_context(
        db: Session,
        user_id: Any,
        conversation_id: str,
        active_products: Optional[List[Any]] = None,
        selected_products: Optional[List[Any]] = None,
        last_intent: Optional[str] = None
    ) -> ConversationContext:
        """Upsert user's active products context in MySQL."""
        cid = conversation_id.strip()
        uid = _extract_uid(user_id)
        clean_active = _sanitize_for_json(active_products) if active_products is not None else []
        clean_selected = _sanitize_for_json(selected_products) if selected_products is not None else []

        row = (
            db.query(ConversationContext)
            .filter(ConversationContext.user_id == uid, ConversationContext.conversation_id == cid)
            .first()
        )

        if row:
            if active_products is not None:
                row.active_products = clean_active
            if selected_products is not None:
                row.selected_products = clean_selected
            if last_intent is not None:
                row.last_intent = str(last_intent)
            row.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        else:
            row = ConversationContext(
                user_id=uid,
                conversation_id=cid,
                active_products=clean_active,
                selected_products=clean_selected,
                last_intent=str(last_intent) if last_intent else None,
                updated_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
            )
            db.add(row)

        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_conversation_context(
        db: Session,
        user_id: Any,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve active products and context for user_id and conversation_id."""
        uid = _extract_uid(user_id)
        row = (
            db.query(ConversationContext)
            .filter(ConversationContext.user_id == uid, ConversationContext.conversation_id == conversation_id.strip())
            .first()
        )

        if not row:
            row = (
                db.query(ConversationContext)
                .filter(ConversationContext.user_id == uid)
                .order_by(desc(ConversationContext.updated_at))
                .first()
            )

        if not row:
            return None

        return {
            "conversation_id": row.conversation_id,
            "active_products": row.active_products or [],
            "selected_products": row.selected_products or [],
            "last_intent": row.last_intent or "general",
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    # =========================================================================
    # 4. USER METRICS & STATS
    # =========================================================================

    @staticmethod
    def get_user_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """Aggregate total counts from MySQL tables for user profile."""
        uid = int(user_id)
        total_chats = db.query(ChatHistory).filter(ChatHistory.user_id == uid).count()
        total_conversations = (
            db.query(ChatHistory.conversation_id)
            .filter(ChatHistory.user_id == uid)
            .distinct()
            .count()
        )
        total_comparisons = db.query(ProductComparison).filter(ProductComparison.user_id == uid).count()
        saved_products_count = db.query(Favorite).filter(Favorite.user_id == uid).count()

        return {
            "total_chats": total_chats,
            "total_conversations": total_conversations,
            "total_comparisons": total_comparisons,
            "saved_products_count": saved_products_count,
            "wishlist_count": saved_products_count,
        }
