from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.product import Product
from models.favorite import Favorite
from schemas.favorite import FavoriteCreateRequest, FavoriteListResponse
from routes.products import format_product_response
from utils.security import get_current_user
from services.notification_service import NotificationService

router = APIRouter(prefix="/favorites", tags=["Favorites"])

@router.get("", response_model=FavoriteListResponse)
def get_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all favorited products for the authenticated user."""
    favs = db.query(Favorite).filter(Favorite.user_id == current_user.id).order_by(Favorite.created_at.desc()).all()
    prods = [f.product for f in favs if f.product and f.product.is_active]
    return FavoriteListResponse(
        items=[format_product_response(p) for p in prods],
        total=len(prods)
    )

@router.post("", status_code=status.HTTP_201_CREATED)
def add_favorite(
    data: FavoriteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a product to user favorites."""
    pid = data.product_id.strip()
    if pid.isdigit():
        prod = db.query(Product).filter(Product.id == int(pid)).first()
    else:
        prod = db.query(Product).filter(Product.product_code == pid).first()

    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == prod.id
    ).first()

    if existing:
        return {"message": "Product is already in your favorites.", "favorite_id": existing.id}

    fav = Favorite(user_id=current_user.id, product_id=prod.id)
    db.add(fav)
    db.commit()
    db.refresh(fav)

    NotificationService.create_notification(
        db=db,
        user_id=current_user.id,
        title="Saved to Favorites",
        message=f"'{prod.name}' was added to your favorites wishlist.",
        type="PRODUCT",
        reference_id=str(prod.id),
    )

    return {"message": "Product added to favorites successfully.", "favorite_id": fav.id}

@router.delete("/{product_id}")
def remove_favorite(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a product from user favorites."""
    pid = product_id.strip()
    if pid.isdigit():
        prod = db.query(Product).filter(Product.id == int(pid)).first()
    else:
        prod = db.query(Product).filter(Product.product_code == pid).first()

    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    fav = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == prod.id
    ).first()

    if not fav:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite record not found.")

    db.delete(fav)
    db.commit()

    return {"message": "Product removed from favorites."}
