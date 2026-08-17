from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.history import SearchHistory, ComparisonHistory
from schemas.history import HistoryResponse, SearchHistoryItem, ComparisonHistoryItem
from utils.security import get_current_user

router = APIRouter(prefix="/history", tags=["History"])

@router.get("", response_model=HistoryResponse)
def get_user_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve search and comparison history for the authenticated user."""
    searches = db.query(SearchHistory).filter(
        SearchHistory.user_id == current_user.id
    ).order_by(SearchHistory.created_at.desc()).limit(20).all()

    comparisons = db.query(ComparisonHistory).filter(
        ComparisonHistory.user_id == current_user.id
    ).order_by(ComparisonHistory.created_at.desc()).limit(20).all()

    return HistoryResponse(
        searches=[
            SearchHistoryItem(
                id=s.id,
                query_text=s.query_text,
                extracted_requirements=s.extracted_requirements,
                filters_applied=s.filters_applied,
                results_count=s.results_count,
                created_at=s.created_at
            ) for s in searches
        ],
        comparisons=[
            ComparisonHistoryItem(
                id=c.id,
                compared_products=c.compared_products if isinstance(c.compared_products, list) else [],
                summary=c.summary,
                created_at=c.created_at
            ) for c in comparisons
        ]
    )

@router.delete("/{history_id}")
def delete_search_history_item(
    history_id: int,
    history_type: str = Query("search", description="'search' or 'comparison'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific history entry."""
    if history_type == "comparison":
        record = db.query(ComparisonHistory).filter(
            ComparisonHistory.id == history_id,
            ComparisonHistory.user_id == current_user.id
        ).first()
    else:
        record = db.query(SearchHistory).filter(
            SearchHistory.id == history_id,
            SearchHistory.user_id == current_user.id
        ).first()

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found.")

    db.delete(record)
    db.commit()

    return {"message": "History entry deleted successfully."}

@router.delete("")
def clear_all_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all search and comparison history for user."""
    db.query(SearchHistory).filter(SearchHistory.user_id == current_user.id).delete()
    db.query(ComparisonHistory).filter(ComparisonHistory.user_id == current_user.id).delete()
    db.commit()

    return {"message": "All history successfully cleared."}
