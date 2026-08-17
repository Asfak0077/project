import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc, func
from database import get_db
from models.product import Product, ProductSpec, ProductFeature, Brand, Category
from schemas.product import (
    ProductSchema,
    ProductListResponse,
    FilterMetaResponse,
    FPSBenchmark,
)

from services.product_data_validator import format_product_response

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("", response_model=ProductListResponse)
def get_products(
    search: Optional[str] = Query(None, description="Search keyword in name, brand, processor"),
    category: Optional[str] = Query(None, description="Category filter (e.g. Laptop)"),
    brand: Optional[str] = Query(None, description="Brand filter (e.g. Asus, HP, Dell)"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_ram: Optional[float] = Query(None, ge=0),
    min_rating: Optional[float] = Query(None, ge=0, le=5.0),
    sort: Optional[str] = Query("match", description="Sort by: 'match' | 'score' | 'price-low' | 'price-high' | 'rating'"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve filtered, searched, and paginated product items."""
    query = db.query(Product).join(ProductSpec, isouter=True).filter(Product.is_active == True)

    if category and category.lower() != "all":
        query = query.filter(Product.category.ilike(f"%{category}%"))

    if brand and brand.lower() != "all":
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None and max_price > 0:
        query = query.filter(Product.price <= max_price)

    if min_ram is not None and min_ram > 0:
        query = query.filter(ProductSpec.ram_gb >= min_ram)

    if min_rating is not None and min_rating > 0:
        query = query.filter(Product.rating >= min_rating)

    if search:
        search_terms = search.strip().split()
        for term in search_terms:
            query = query.filter(
                or_(
                    Product.name.ilike(f"%{term}%"),
                    Product.brand.ilike(f"%{term}%"),
                    Product.model.ilike(f"%{term}%"),
                    ProductSpec.cpu.ilike(f"%{term}%"),
                    ProductSpec.gpu.ilike(f"%{term}%")
                )
            )

    # Sorting
    if sort == "price-low":
        query = query.order_by(asc(Product.price))
    elif sort == "price-high":
        query = query.order_by(desc(Product.price))
    elif sort == "rating":
        query = query.order_by(desc(Product.rating), desc(Product.total_ratings))
    elif sort == "score":
        query = query.order_by(desc(Product.score))
    else:  # 'match' default
        query = query.order_by(desc(Product.score), desc(Product.rating))

    total = query.count()
    pages = math.ceil(total / limit) if total > 0 else 1
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()

    return ProductListResponse(
        items=[format_product_response(p) for p in products],
        total=total,
        page=page,
        limit=limit,
        pages=pages
    )

@router.get("/filters/meta", response_model=FilterMetaResponse)
def get_filters_meta(db: Session = Depends(get_db)):
    """Retrieve dynamic filter metadata (available brands, categories, price bounds)."""
    brands = [b[0] for b in db.query(Product.brand).distinct().order_by(Product.brand).all() if b[0]]
    categories = [c[0] for c in db.query(Product.category).distinct().order_by(Product.category).all() if c[0]]
    
    price_stats = db.query(
        func.min(Product.price),
        func.max(Product.price)
    ).filter(Product.is_active == True).first()

    min_p = float(price_stats[0]) if price_stats and price_stats[0] is not None else 10000.0
    max_p = float(price_stats[1]) if price_stats and price_stats[1] is not None else 250000.0

    return FilterMetaResponse(
        brands=brands if brands else ["Asus", "HP", "Lenovo", "Dell", "Apple", "Acer", "MSI"],
        categories=categories if categories else ["Laptop", "Mobile", "Camera"],
        min_price=min_p,
        max_price=max_p,
        ram_options=[4.0, 8.0, 16.0, 24.0, 32.0, 64.0]
    )

@router.get("/{product_id}", response_model=ProductSchema)
def get_product_by_id(product_id: str, db: Session = Depends(get_db)):
    """Fetch complete product specification by product code or numeric ID."""
    if product_id.isdigit():
        prod = db.query(Product).filter(Product.id == int(product_id)).first()
    else:
        prod = db.query(Product).filter(Product.product_code == product_id).first()

    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found."
        )

    return format_product_response(prod)
