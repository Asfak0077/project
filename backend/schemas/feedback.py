import datetime
from typing import Optional
from pydantic import BaseModel

class FeedbackCreateRequest(BaseModel):
    recommendation_id: Optional[int] = None
    product_id: Optional[str] = None  # product code or ID
    rating: str  # 'positive', 'negative', or '1'..'5'
    reason: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    recommendation_id: Optional[int] = None
    product_id: Optional[int] = None
    rating: str
    reason: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True
