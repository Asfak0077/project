from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.product import Product
from models.feedback import Feedback
from schemas.feedback import FeedbackCreateRequest, FeedbackResponse
from utils.security import get_optional_user

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    data: FeedbackCreateRequest,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Submit user feedback / rating on a recommendation or product."""
    prod_id = None
    if data.product_id:
        if str(data.product_id).isdigit():
            p = db.query(Product).filter(Product.id == int(data.product_id)).first()
        else:
            p = db.query(Product).filter(Product.product_code == str(data.product_id)).first()
        if p:
            prod_id = p.id

    fb = Feedback(
        user_id=current_user.id if current_user else None,
        recommendation_id=data.recommendation_id,
        product_id=prod_id,
        rating=data.rating,
        reason=data.reason
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    return fb
