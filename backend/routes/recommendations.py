from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.product import Product
from models.favorite import Favorite
from models.history import SearchHistory
from schemas.recommendation import RecommendationRequest, RecommendationResponse
from services.recommendation_service import RecommendationService
from utils.security import get_optional_user, get_current_user

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.post("", response_model=RecommendationResponse)
def get_recommendations(
    data: RecommendationRequest,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Analyze natural language query, extract requirements, and return ranked recommendations."""
    if not data.query or not data.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A non-empty query string is required."
        )

    user_id = current_user.id if current_user else None

    # Call recommendation engine
    rec_result = RecommendationService.get_recommendations(
        db=db,
        query=data.query.strip(),
        user_id=user_id,
        category=data.category or "Laptop",
        top_k=data.top_k or 5
    )

    # Log search to search_history
    if current_user:
        try:
            search_record = SearchHistory(
                user_id=current_user.id,
                query_text=data.query.strip(),
                extracted_requirements=rec_result.get("nlp_extracted"),
                results_count=len(rec_result.get("recommendations", []))
            )
            db.add(search_record)
            db.commit()
        except Exception:
            db.rollback()

    return RecommendationResponse(**rec_result)

@router.get("/personalized")
def get_personalized_recommendations(
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Generate tailored product recommendations based on user preferences, wishlist, and past activity."""
    category = "Laptop"
    budget_max = 120000.0
    persona = "balanced"
    brand = None

    if current_user and current_user.preferences:
        prefs = current_user.preferences
        category = prefs.default_category or "Laptop"
        budget_max = prefs.budget_max or 120000.0
        persona = prefs.ai_style or "performance"
        if prefs.preferred_brands and len(prefs.preferred_brands) > 0:
            brand = prefs.preferred_brands[0]

    # Formulate contextual recommendation query
    query_parts = [f"{persona} {category.lower()}"]
    if budget_max:
        query_parts.append(f"under {int(budget_max)}")
    if brand:
        query_parts.append(f"by {brand}")

    contextual_query = " ".join(query_parts)

    rec_result = RecommendationService.get_recommendations(
        db=db,
        query=contextual_query,
        user_id=current_user.id if current_user else None,
        category=category,
        top_k=4
    )

    return {
        "personalized_for": current_user.name if current_user else "Guest Explorer",
        "preferences_applied": {
            "category": category,
            "ai_style": persona,
            "budget_max": budget_max,
            "preferred_brand": brand,
        },
        "recommendations": rec_result.get("recommendations", []),
        "explanation": f"Ranked for {persona} use cases under ₹{budget_max:,.0f} from verified MySQL database inventory."
    }
