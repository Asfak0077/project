"""
Conversation Memory & Temporary Session Service
Maintains stateful context (active product, active category, last intent, previous products, current comparison set, messages)
across multi-turn user conversations and supports temporary backend persistence with 24-hour expiration and MySQL product validation.
"""
from __future__ import annotations

import time
import datetime
import logging
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session

logger = logging.getLogger("backend.memory")

SESSION_TTL_SECONDS = 86400  # 24 Hours


class SessionState:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.created_at: float = time.time()
        self.expires_at: float = self.created_at + SESSION_TTL_SECONDS
        self.active_product: Optional[Dict[str, Any]] = None
        self.active_product_id: Optional[str] = None
        self.active_product_name: Optional[str] = None
        self.active_category: Optional[str] = "Laptop"
        self.last_intent: Optional[str] = None
        self.last_query: Optional[str] = None
        self.last_battle_result: Optional[Dict[str, Any]] = None
        self.previous_products: List[Dict[str, Any]] = []
        self.current_comparison_set: List[Dict[str, Any]] = []
        self.shortlisted_products: List[Dict[str, Any]] = []
        self.history: List[Dict[str, str]] = []
        self.messages: List[Dict[str, Any]] = []
        self.last_updated: float = time.time()

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def touch(self):
        self.last_updated = time.time()
        self.expires_at = time.time() + SESSION_TTL_SECONDS

    def update_product(self, product: Optional[Dict[str, Any]]):
        if product:
            # If replacing an existing product, push old to previous_products
            if self.active_product and self.active_product.get("id") != product.get("id"):
                if not any(p.get("id") == self.active_product.get("id") for p in self.previous_products):
                    self.previous_products.append(self.active_product)
                    if len(self.previous_products) > 10:
                        self.previous_products = self.previous_products[-10:]

            self.active_product = product
            self.active_product_id = str(product.get("id", ""))
            self.active_product_name = product.get("name", "")
            if product.get("category"):
                self.active_category = product.get("category")
            self.touch()

    def update_comparison_set(self, products: List[Dict[str, Any]]):
        """Update active comparison products set."""
        if products:
            # Deduplicate by ID
            seen_ids = set()
            unique_set = []
            for p in products:
                if p and p.get("id") is not None and p.get("id") not in seen_ids:
                    unique_set.append(p)
                    seen_ids.add(p.get("id"))
            self.current_comparison_set = unique_set
            self.touch()

    def update_battle_result(self, battle_result: Optional[Dict[str, Any]]):
        """Store last AI battle verdict / match object."""
        if battle_result:
            self.last_battle_result = battle_result
            self.touch()

    def update_category(self, category: Optional[str]):
        if category:
            self.active_category = category
            self.touch()

    def add_turn(self, query: str, answer: str, intent: Optional[str] = None):
        self.last_query = query
        self.last_intent = intent
        self.history.append({"user": query, "assistant": answer})
        if len(self.history) > 20:
            self.history = self.history[-20:]
        self.touch()

    def set_messages(self, msgs: List[Dict[str, Any]]):
        if msgs:
            self.messages = msgs[-50:]  # Keep last 50 messages
            self.touch()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "conversation_id": self.session_id,
            "created_at": datetime.datetime.fromtimestamp(self.created_at, datetime.timezone.utc).isoformat(),
            "expires_at": datetime.datetime.fromtimestamp(self.expires_at, datetime.timezone.utc).isoformat(),
            "active_product_id": self.active_product_id,
            "active_product_name": self.active_product_name,
            "active_product": self.active_product,
            "active_category": self.active_category,
            "last_intent": self.last_intent,
            "last_query": self.last_query,
            "last_battle_result": self.last_battle_result,
            "battle_result": self.last_battle_result,
            "previous_products": self.previous_products,
            "comparison_products": self.current_comparison_set,
            "selected_products": self.current_comparison_set,
            "shortlisted_count": len(self.shortlisted_products),
            "history_turns": len(self.history),
            "messages": self.messages,
        }


class ConversationMemoryService:
    _sessions: Dict[str, SessionState] = {}

    @classmethod
    def cleanup_expired_sessions(cls):
        """Remove sessions older than 24 hours."""
        now = time.time()
        expired_keys = [sid for sid, s in cls._sessions.items() if now > s.expires_at]
        for sid in expired_keys:
            del cls._sessions[sid]

    @classmethod
    def get_or_create(cls, session_id: Optional[str]) -> SessionState:
        cls.cleanup_expired_sessions()
        sid = session_id or "default_session"
        if sid not in cls._sessions:
            cls._sessions[sid] = SessionState(sid)
        session = cls._sessions[sid]
        if session.is_expired():
            cls._sessions[sid] = SessionState(sid)
            return cls._sessions[sid]
        return session

    @classmethod
    def update_session(
        cls,
        session_id: Optional[str],
        product: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        query: Optional[str] = None,
        answer: Optional[str] = None,
        intent: Optional[str] = None,
        comparison_products: Optional[List[Dict[str, Any]]] = None,
        battle_result: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> SessionState:
        session = cls.get_or_create(session_id)
        if product:
            session.update_product(product)
        if comparison_products is not None:
            session.update_comparison_set(comparison_products)
        if battle_result is not None:
            session.update_battle_result(battle_result)
        if category:
            session.update_category(category)
        if query and answer:
            session.add_turn(query, answer, intent)
        if messages:
            session.set_messages(messages)
        return session

    @classmethod
    def save_session_state(
        cls,
        db: Session,
        session_id: str,
        comparison_products: Optional[List[Any]] = None,
        active_product: Optional[Any] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        last_intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Explicitly persist temporary session state into memory and validate product objects.
        """
        from services.product_service import ProductService

        session = cls.get_or_create(session_id)

        # 1. Resolve and validate comparison products
        resolved_comp: List[Dict[str, Any]] = []
        if comparison_products:
            seen_ids = set()
            for item in comparison_products:
                pid = item.get("id") if isinstance(item, dict) else item
                if pid and pid not in seen_ids:
                    p_facts = ProductService.get_by_id(db, pid)
                    if p_facts:
                        resolved_comp.append(p_facts)
                        seen_ids.add(p_facts["id"])
                    elif isinstance(item, dict) and item.get("name"):
                        # Fallback for structured item
                        resolved_comp.append(item)
                        seen_ids.add(item.get("id", pid))

        if resolved_comp:
            session.update_comparison_set(resolved_comp)

        # 2. Resolve active product
        resolved_active = None
        if active_product:
            act_id = active_product.get("id") if isinstance(active_product, dict) else active_product
            if act_id:
                p_facts = ProductService.get_by_id(db, act_id)
                if p_facts:
                    resolved_active = p_facts
                elif isinstance(active_product, dict):
                    resolved_active = active_product

        if resolved_active:
            session.update_product(resolved_active)
        elif resolved_comp:
            session.update_product(resolved_comp[0])

        if messages:
            session.set_messages(messages)
        if last_intent:
            session.last_intent = last_intent

        session.touch()
        return {
            "status": "saved",
            "conversation_id": session_id,
            "product_count": len(session.current_comparison_set),
            "expires_at": datetime.datetime.fromtimestamp(session.expires_at, datetime.timezone.utc).isoformat(),
        }

    @classmethod
    def get_session_state(cls, db: Session, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session state with strict database validation (removes missing/deleted products).
        """
        from services.product_service import ProductService

        cls.cleanup_expired_sessions()
        if session_id not in cls._sessions:
            return None

        session = cls._sessions[session_id]
        if session.is_expired():
            del cls._sessions[session_id]
            return None

        # Re-validate comparison products against MySQL Database
        validated_comparison: List[Dict[str, Any]] = []
        for p in session.current_comparison_set:
            pid = p.get("id")
            if pid:
                db_prod = ProductService.get_by_id(db, pid)
                if db_prod:
                    validated_comparison.append(db_prod)

        # Update in-memory set with validated records
        session.current_comparison_set = validated_comparison

        # Re-validate active product
        validated_active = None
        if session.active_product:
            act_id = session.active_product.get("id")
            if act_id:
                validated_active = ProductService.get_by_id(db, act_id)

        session.active_product = validated_active
        if not session.active_product and validated_comparison:
            session.active_product = validated_comparison[0]

        return {
            "conversation_id": session.session_id,
            "session_id": session.session_id,
            "created_at": datetime.datetime.fromtimestamp(session.created_at, datetime.timezone.utc).isoformat(),
            "expires_at": datetime.datetime.fromtimestamp(session.expires_at, datetime.timezone.utc).isoformat(),
            "comparison_products": validated_comparison,
            "selected_products": validated_comparison,
            "active_product": session.active_product,
            "messages": session.messages or [{"role": h.get("user") and "user" or "assistant", "content": h.get("user") or h.get("assistant", "")} for h in session.history],
            "last_intent": session.last_intent,
            "active_category": session.active_category,
        }

    @classmethod
    def clear_session(cls, session_id: str):
        if session_id in cls._sessions:
            del cls._sessions[session_id]
