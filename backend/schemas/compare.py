from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from schemas.product import ProductSchema

class CompareRequest(BaseModel):
    product_ids: List[str]  # e.g., ["LAP_001", "LAP_002"] or numeric IDs

class SpecComparisonRow(BaseModel):
    label: str
    key: str
    values: Dict[str, Any]
    winner_product_id: Optional[str] = None
    is_different: bool = False

class CompareResponse(BaseModel):
    products: List[ProductSchema]
    spec_rows: List[SpecComparisonRow]
    overall_winner_id: Optional[str] = None
    winner_summary: Optional[str] = None
