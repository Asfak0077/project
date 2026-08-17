"""
SQLAlchemy Models for Multi-User AI Chat History, Product Comparisons, and Context Persistence
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    message = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    product_context = Column(JSON, nullable=True)  # List of product snapshots/IDs referenced in this turn
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", backref="chat_histories")


class ProductComparison(Base):
    __tablename__ = "product_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    comparison_id = Column(String(255), nullable=False, index=True)
    product_ids = Column(JSON, nullable=False)  # List of product IDs [45, 67, 101]
    comparison_result = Column(JSON, nullable=True)  # Winner summary, compared products, spec rows
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", backref="product_comparisons")


class ConversationContext(Base):
    __tablename__ = "conversation_context"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String(255), nullable=False, index=True)
    active_products = Column(JSON, nullable=True)  # List of full active product dictionaries
    selected_products = Column(JSON, nullable=True)  # Shortlisted/selected products for comparison
    last_intent = Column(String(100), nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, index=True)

    user = relationship("User", backref="conversation_contexts")
