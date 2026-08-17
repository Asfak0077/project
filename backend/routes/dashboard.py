"""
Dashboard Analytics Router
Provides real database metrics, category distributions, brand shares, and price segmentations
across Laptops, Phones, and Tablets.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db
from models.user import User
from models.product import Product
from models.favorite import Favorite
from models.history import SearchHistory, ComparisonHistory
from models.recommendation import Recommendation
from utils.security import get_optional_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Retrieve top-level metric counters calculated from real database records."""
    user_id = current_user.id if current_user else None

    # Total and category-specific product counts
    total_products = db.query(Product).count()
    laptop_count = db.query(Product).filter(Product.category.ilike("%laptop%")).count()
    phone_count = db.query(Product).filter(Product.category.ilike("%phone%")).count()
    tablet_count = db.query(Product).filter(Product.category.ilike("%tablet%")).count()

    # User-specific or system counts
    if user_id:
        wishlist_count = db.query(Favorite).filter(Favorite.user_id == user_id).count()
        comparison_count = db.query(ComparisonHistory).filter(ComparisonHistory.user_id == user_id).count()
        recommendation_count = db.query(Recommendation).filter(Recommendation.user_id == user_id).count()
        recent_search_count = db.query(SearchHistory).filter(SearchHistory.user_id == user_id).count()
    else:
        wishlist_count = db.query(Favorite).count()
        comparison_count = db.query(ComparisonHistory).count()
        recommendation_count = db.query(Recommendation).count()
        recent_search_count = db.query(SearchHistory).count()

    return {
        "total_products": total_products,
        "laptop_count": laptop_count,
        "phone_count": phone_count,
        "tablet_count": tablet_count,
        "wishlist_count": wishlist_count,
        "comparison_count": comparison_count,
        "recommendation_count": recommendation_count,
        "recent_search_count": recent_search_count,
    }


@router.get("/category-distribution")
def get_category_distribution(db: Session = Depends(get_db)):
    """Retrieve real category breakdown from the database."""
    counts = db.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    total = sum(c[1] for c in counts) or 1
    
    return [
        {
            "category": c[0] or "Unknown",
            "count": c[1],
            "percentage": round((c[1] / total) * 100, 1),
            "color": "#3B82F6" if "laptop" in str(c[0]).lower() else ("#10B981" if "phone" in str(c[0]).lower() else "#8B5CF6")
        }
        for c in counts
    ]


@router.get("/price-segmentation")
def get_price_segmentation(
    category: Optional[str] = Query(None, description="Optional category filter"),
    db: Session = Depends(get_db)
):
    """Retrieve dynamic price distribution from the product catalog."""
    query = db.query(Product)
    if category and category.lower() != "all":
        query = query.filter(Product.category.ilike(f"%{category}%"))

    b_under_25 = query.filter(Product.price < 25000).count()
    b_25_50 = query.filter(Product.price >= 25000, Product.price < 50000).count()
    b_50_75 = query.filter(Product.price >= 50000, Product.price < 75000).count()
    b_75_100 = query.filter(Product.price >= 75000, Product.price < 100000).count()
    b_above_100 = query.filter(Product.price >= 100000).count()

    return [
        {"range": "Under ₹25k", "count": b_under_25, "segment": "< 25K"},
        {"range": "₹25k - ₹50k", "count": b_25_50, "segment": "25K - 50K"},
        {"range": "₹50k - ₹75k", "count": b_50_75, "segment": "50K - 75K"},
        {"range": "₹75k - ₹100k", "count": b_75_100, "segment": "75K - 100K"},
        {"range": "Above ₹100k", "count": b_above_100, "segment": "> 100K"},
    ]


@router.get("/brand-market-share")
def get_brand_market_share(
    category: Optional[str] = Query(None, description="Optional category filter"),
    db: Session = Depends(get_db)
):
    """Retrieve brand market distribution from the database."""
    query = db.query(Product.brand, func.count(Product.id)).filter(Product.brand != None)
    if category and category.lower() != "all":
        query = query.filter(Product.category.ilike(f"%{category}%"))

    brand_counts = query.group_by(Product.brand).order_by(desc(func.count(Product.id))).limit(6).all()
    total = sum(b[1] for b in brand_counts) or 1
    return [
        {"name": b[0] or "Other", "count": b[1], "percentage": round((b[1] / total) * 100, 1)}
        for b in brand_counts
    ]


@router.get("")
@router.get("/analytics")
def get_user_dashboard_analytics(
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Retrieve full combined analytics for dashboard."""
    stats = get_dashboard_stats(current_user, db)
    price_dist = get_price_segmentation(category=None, db=db)
    popular_brands = get_brand_market_share(category=None, db=db)
    category_dist = get_category_distribution(db)

    user_id = current_user.id if current_user else None
    if user_id:
        searches = db.query(SearchHistory).filter(SearchHistory.user_id == user_id).order_by(SearchHistory.created_at.desc()).limit(6).all()
    else:
        searches = db.query(SearchHistory).order_by(SearchHistory.created_at.desc()).limit(6).all()

    recent_searches = [
        {"id": s.id, "query": s.query_text, "results": s.results_count, "time": s.created_at.strftime("%b %d, %H:%M")}
        for s in searches
    ]

    return {
        **stats,
        "total_favorites": stats["wishlist_count"],
        "total_comparisons": stats["comparison_count"],
        "total_recommendations": stats["recommendation_count"],
        "category_distribution": category_dist,
        "price_distribution": price_dist,
        "popular_brands": popular_brands,
        "recent_searches": recent_searches,
    }
