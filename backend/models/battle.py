import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class ProductBattleHistory(Base):
    __tablename__ = "product_battle_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    product_1_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    product_2_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    winner_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_1_score = Column(Float, nullable=False, default=0.0)
    product_2_score = Column(Float, nullable=False, default=0.0)
    battle_result = Column(JSON, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        index=True
    )

    user = relationship("User", back_populates="battle_histories")
    product_1 = relationship("Product", foreign_keys=[product_1_id])
    product_2 = relationship("Product", foreign_keys=[product_2_id])
    winner = relationship("Product", foreign_keys=[winner_id])
