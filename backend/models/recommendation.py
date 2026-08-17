import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    query = Column(Text, nullable=False)
    user_intent = Column(String(100), nullable=True)
    extracted_specs = Column(JSON, nullable=True)
    priorities = Column(JSON, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", back_populates="recommendations")
    items = relationship("RecommendationItem", back_populates="recommendation", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="recommendation", cascade="all, delete-orphan")

class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    match_score = Column(Float, nullable=False)
    rank_position = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True)  # List of string pros
    weaknesses = Column(JSON, nullable=True)  # List of string cons

    recommendation = relationship("Recommendation", back_populates="items")
    product = relationship("Product", back_populates="recommendation_items")
