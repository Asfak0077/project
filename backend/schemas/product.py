from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class FPSBenchmark(BaseModel):
    game: str
    fps: int
    resolution: str

class ProductSpecSchema(BaseModel):
    cpu: Optional[str] = None
    ram_gb: Optional[float] = None
    storage: Optional[str] = None
    gpu: Optional[str] = None
    display_size_inch: Optional[float] = None
    resolution: Optional[str] = None
    os: Optional[str] = None
    weight_kg: Optional[float] = None
    battery: Optional[str] = None
    base_clock_speed_ghz: Optional[float] = None
    touch_screen: Optional[bool] = False
    ports: Optional[str] = None
    raw_specs: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class ProductSchema(BaseModel):
    id: str  # Product code or ID
    numeric_id: int
    brand: str
    name: str
    category: str = "Laptop"
    model: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    cpu: str
    ram: float
    storage: str
    gpu: Optional[str] = "Integrated"
    score: float = 85.0
    image: str
    rating: float = 4.0
    reviews: int = 0
    badge: Optional[str] = None
    specsSummary: Optional[str] = None
    pros: List[str] = []
    cons: List[str] = []
    fpsData: List[FPSBenchmark] = []
    specs: Optional[ProductSpecSchema] = None

    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    items: List[ProductSchema]
    total: int
    page: int
    limit: int
    pages: int

class FilterMetaResponse(BaseModel):
    brands: List[str]
    categories: List[str]
    min_price: float
    max_price: float
    ram_options: List[float]

class ProductCreateRequest(BaseModel):
    brand: str
    name: str
    category: str = "Laptop"
    model: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    cpu: str
    ram: float
    storage: str
    gpu: Optional[str] = "Integrated"
    score: Optional[float] = 85.0
    image_url: Optional[str] = None
    badge: Optional[str] = None
    specs_summary: Optional[str] = None
    rating: Optional[float] = 4.0
    pros: Optional[List[str]] = []
    cons: Optional[List[str]] = []

class ProductUpdateRequest(BaseModel):
    brand: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    model: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    cpu: Optional[str] = None
    ram: Optional[float] = None
    storage: Optional[str] = None
    gpu: Optional[str] = None
    score: Optional[float] = None
    image_url: Optional[str] = None
    badge: Optional[str] = None
    specs_summary: Optional[str] = None
    rating: Optional[float] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
