from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from schemas.user import UserProfileResponse
from schemas.product import ProductSchema

class CSVImportResult(BaseModel):
    total_rows: int
    new_products: int
    updated_products: int
    duplicates: int
    invalid_rows: int
    message: str

class AdminAnalyticsResponse(BaseModel):
    total_users: int
    total_products: int
    total_favorites: int
    total_comparisons: int
    total_recommendations: int
    total_documents: int
    recent_searches: List[Dict[str, Any]]
    popular_categories: List[Dict[str, Any]]
    popular_brands: List[Dict[str, Any]]
    price_distribution: List[Dict[str, Any]]
    ai_metrics: Dict[str, Any]

class UserRoleUpdateRequest(BaseModel):
    is_admin: bool
    role_name: Optional[str] = "user"
