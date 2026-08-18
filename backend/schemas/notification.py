from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class NotificationBase(BaseModel):
    title: str = Field(..., description="Short title of notification")
    message: str = Field(..., description="Body of notification")
    type: str = Field(default="SYSTEM", description="AUTH, AI_CHAT, RAG, COMPARISON, PRODUCT, SYSTEM")
    reference_id: Optional[str] = Field(default=None, description="Reference entity ID")

class NotificationCreate(NotificationBase):
    user_id: int
    status: str = Field(default="unread")

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    status: str
    reference_id: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    success: bool = True
    notifications: List[NotificationResponse] = []
    total: int = 0
    unread_count: int = 0

class UnreadCountResponse(BaseModel):
    success: bool = True
    count: int = 0
