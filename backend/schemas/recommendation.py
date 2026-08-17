from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from schemas.product import ProductSchema

class NLPRequirementSchema(BaseModel):
    intent: str = "recommendation"
    category: str = "laptop"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    brand: Optional[str] = None
    min_ram: Optional[float] = None
    purpose: Optional[str] = None
    requirements: Dict[str, Any] = {}
    priorities: Dict[str, float] = {
        "performance": 0.4,
        "price": 0.3,
        "battery": 0.2,
        "display": 0.1
    }

class RecommendationRequest(BaseModel):
    query: str
    category: Optional[str] = "Laptop"
    top_k: Optional[int] = 5

class RecommendedProductItem(BaseModel):
    product: ProductSchema
    match_score: int  # 0 to 100
    rank: int
    reason: str
    strengths: List[str] = []
    weaknesses: List[str] = []

class RecommendationResponse(BaseModel):
    query: str
    nlp_extracted: NLPRequirementSchema
    recommendations: List[RecommendedProductItem]
    summary: str
