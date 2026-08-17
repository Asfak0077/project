import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class SearchHistoryItem(BaseModel):
    id: int
    query_text: str
    extracted_requirements: Optional[Dict[str, Any]] = None
    filters_applied: Optional[Dict[str, Any]] = None
    results_count: int = 0
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ComparisonHistoryItem(BaseModel):
    id: int
    compared_products: List[Dict[str, Any]]
    summary: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class HistoryResponse(BaseModel):
    searches: List[SearchHistoryItem]
    comparisons: List[ComparisonHistoryItem]
