import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False, default="SYSTEM", index=True)  # AUTH, AI_CHAT, RAG, COMPARISON, PRODUCT, SYSTEM
    status = Column(String(20), nullable=False, default="unread", index=True)  # 'unread', 'read'
    reference_id = Column(String(255), nullable=True, index=True)  # Optional target id (e.g. conv_id, doc_id, product_id)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Relationship to User
    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_status", "user_id", "status"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )
