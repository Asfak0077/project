import datetime
from typing import List, Optional
from pydantic import BaseModel
from schemas.product import ProductSchema

class FavoriteCreateRequest(BaseModel):
    product_id: str  # Product code or ID

class FavoriteItemResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    product: ProductSchema
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class FavoriteListResponse(BaseModel):
    items: List[ProductSchema]
    total: int
