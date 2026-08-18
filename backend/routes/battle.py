import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from database import get_db
from models.user import User
from models.battle import ProductBattleHistory
from services.product_service import ProductService
from services.battle_service import BattleService
from utils.security import get_optional_user, get_current_user

logger = logging.getLogger("backend.battle")

router = APIRouter(prefix="", tags=["AI Product Battle"])


class BattleRequest(BaseModel):
    product_ids: List[Any] = Field(..., min_length=2, description="List of exactly 2 product IDs to battle")


class BattleResponse(BaseModel):
    success: bool
    battle_id: Optional[int] = None
    product_1: Dict[str, Any]
    product_2: Dict[str, Any]
    product_1_name: str
    product_2_name: str
    product_1_score: float
    product_2_score: float
    winner_id: Optional[Any] = None
    winner_name: str
    winner_score: float
    rounds: List[Dict[str, Any]]
    ai_verdict: Dict[str, Any]
    key_reasons: List[str]
    confidence: str
    markdown: str


@router.post("/product/battle", response_model=BattleResponse)
def start_product_battle(
    req: BattleRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    Launch an AI Product Comparison Battle between 2 products.
    Evaluates 5 rounds (Performance, Price Value, Display, Battery, Rating)
    and delivers an AI Judge verdict.
    """
    if len(req.product_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select 2 valid products for battle."
        )

    p1_id, p2_id = req.product_ids[0], req.product_ids[1]

    if str(p1_id) == str(p2_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot battle a product against itself. Please select 2 distinct products."
        )

    # Fetch products from database
    p1 = ProductService.get_by_id(db, p1_id)
    p2 = ProductService.get_by_id(db, p2_id)

    if not p1 or not p2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more products could not be found in the catalog."
        )

    try:
        user_id = int(str(getattr(user, "id", 0))) if user and getattr(user, "id", None) is not None else None
        battle_result = BattleService.run_battle(db, p1, p2, user_id=user_id)
        return {
            "success": True,
            **battle_result
        }
    except ValueError as ve:
        logger.warning(f"Validation error in battle: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running product battle: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process battle request. Please try again."
        )


@router.get("/product/battle/history")
def get_user_battle_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve the battle history for the logged-in user."""
    try:
        uid = int(str(getattr(user, "id", 0))) if getattr(user, "id", None) is not None else 0
        history = BattleService.get_battle_history(db, uid, limit=limit, offset=offset)
        return {
            "success": True,
            "total": len(history),
            "battles": history
        }
    except Exception as e:
        logger.error(f"Error fetching battle history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch battle history."
        )


@router.get("/product/battle/{battle_id}")
def get_battle_detail(
    battle_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """Retrieve details for a specific battle record."""
    record = db.query(ProductBattleHistory).filter(ProductBattleHistory.id == battle_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Battle not found.")

    res = dict(record.battle_result) if isinstance(record.battle_result, dict) else {}
    res["id"] = record.id
    res["created_at"] = record.created_at.isoformat() if record.created_at else None
    return {
        "success": True,
        "battle": res
    }
