import os
import shutil
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, UserPreference
from schemas.user import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserPreferencesSchema,
    UserPreferencesUpdateRequest,
    PasswordChangeRequest,
)
from utils.security import get_current_user
from services.auth_service import hash_password, verify_password
from utils.config import settings

from services.user_storage_service import UserStorageService

router = APIRouter(prefix="/users", tags=["Users"])

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

def map_user_profile(user: User, db: Optional[Session] = None) -> UserProfileResponse:
    """Helper to convert User ORM model to UserProfileResponse with live database stats."""
    prefs = user.preferences
    prefs_schema = UserPreferencesSchema(
        defaultCategory=prefs.default_category if prefs else "Laptop",
        aiStyle=prefs.ai_style if prefs else "performance",
        currency=prefs.currency if prefs else "INR",
        notificationsEmail=prefs.notifications_email if prefs else True,
        notificationsPriceDrops=prefs.notifications_price_drops if prefs else True,
        darkMode=prefs.dark_mode if prefs else False,
        budgetMin=prefs.budget_min if prefs else 0.0,
        budgetMax=prefs.budget_max if prefs else 150000.0,
        preferredBrands=prefs.preferred_brands if (prefs and prefs.preferred_brands) else [],
        priorityFeatures=prefs.priority_features if (prefs and prefs.priority_features) else ["High Performance", "OLED Display"]
    )

    stats = UserStorageService.get_user_stats(db, user.id) if db else {
        "total_chats": 0,
        "total_conversations": 0,
        "total_comparisons": 0,
        "wishlist_count": 0
    }

    avatar_url = user.avatar or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80"

    return UserProfileResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        avatar=avatar_url,
        profile_image=avatar_url,
        title=user.title or "Product Architecture Enthusiast",
        location=user.location or "Bengaluru, India",
        bio=user.bio or "Comparing next-gen silicon and laptop hardware with verified RAG datasheets.",
        authMethod=user.auth_provider or "email",
        twoFactorEnabled=True,
        isAdmin=user.is_admin,
        role="admin" if user.is_admin else "user",
        totalChats=stats.get("total_chats", 0),
        totalConversations=stats.get("total_conversations", 0),
        totalComparisons=stats.get("total_comparisons", 0),
        wishlistCount=stats.get("wishlist_count", 0),
        preferences=prefs_schema
    )

@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve logged-in user profile with preferences and aggregated database stats."""
    return map_user_profile(current_user, db=db)

@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update profile attributes and password."""
    if data.name is not None:
        current_user.name = data.name.strip()
    if data.phone is not None:
        current_user.phone = data.phone.strip()
    if data.avatar is not None:
        current_user.avatar = data.avatar.strip()
    if data.title is not None:
        current_user.title = data.title.strip()
    if data.location is not None:
        current_user.location = data.location.strip()
    if data.bio is not None:
        current_user.bio = data.bio.strip()

    # Password change / set password check
    if data.newPassword:
        if current_user.password_hash:
            if not data.currentPassword or not verify_password(data.currentPassword, current_user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect."
                )
        current_user.password_hash = hash_password(data.newPassword)
        if current_user.auth_provider == "google":
            current_user.auth_provider = "local+google"

    db.commit()
    db.refresh(current_user)
    return map_user_profile(current_user)

@router.post("/profile/image", response_model=UserProfileResponse)
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and save user avatar image (JPG, PNG, WEBP)."""
    # 1. Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        )

    # 2. Ensure target directory exists
    avatar_dir = os.path.join(settings.UPLOAD_STORAGE_PATH, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)

    filename = f"user_{current_user.id}_{int(time.time())}{ext}"
    file_path = os.path.join(avatar_dir, filename)

    # 3. Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile photo must be less than 5 MB in size."
        )

    # 4. Save to disk
    with open(file_path, "wb") as f:
        f.write(contents)

    # 5. Update user avatar URL in database (relative URL mounted under /uploads)
    avatar_url = f"/uploads/avatars/{filename}"
    current_user.avatar = avatar_url
    db.commit()
    db.refresh(current_user)

    return map_user_profile(current_user)

@router.delete("/profile/image", response_model=UserProfileResponse)
def remove_profile_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove custom avatar and reset to default."""
    current_user.avatar = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80"
    db.commit()
    db.refresh(current_user)
    return map_user_profile(current_user)

@router.put("/password")
def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change account password with verification."""
    if not current_user.password_hash or not verify_password(data.currentPassword, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    if len(data.newPassword) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long."
        )

    current_user.password_hash = hash_password(data.newPassword)
    db.commit()

    return {"message": "Password changed successfully."}

@router.get("/preferences", response_model=UserPreferencesSchema)
def get_preferences(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve current user preferences."""
    prefs = current_user.preferences
    if not prefs:
        prefs = UserPreference(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return UserPreferencesSchema(
        defaultCategory=prefs.default_category,
        aiStyle=prefs.ai_style,
        currency=prefs.currency,
        notificationsEmail=prefs.notifications_email,
        notificationsPriceDrops=prefs.notifications_price_drops,
        darkMode=prefs.dark_mode,
        budgetMin=prefs.budget_min,
        budgetMax=prefs.budget_max,
        preferredBrands=prefs.preferred_brands or [],
        priorityFeatures=prefs.priority_features or ["High Performance", "OLED Display"]
    )

@router.put("/preferences", response_model=UserPreferencesSchema)
def update_preferences(
    data: UserPreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user customization and notification preferences."""
    prefs = current_user.preferences
    if not prefs:
        prefs = UserPreference(user_id=current_user.id)
        db.add(prefs)
        db.flush()

    if data.defaultCategory is not None:
        prefs.default_category = data.defaultCategory
    if data.aiStyle is not None:
        prefs.ai_style = data.aiStyle
    if data.currency is not None:
        prefs.currency = data.currency
    if data.notificationsEmail is not None:
        prefs.notifications_email = data.notificationsEmail
    if data.notificationsPriceDrops is not None:
        prefs.notifications_price_drops = data.notificationsPriceDrops
    if data.darkMode is not None:
        prefs.dark_mode = data.darkMode
    if data.budgetMin is not None:
        prefs.budget_min = data.budgetMin
    if data.budgetMax is not None:
        prefs.budget_max = data.budgetMax
    if data.preferredBrands is not None:
        prefs.preferred_brands = data.preferredBrands
    if data.priorityFeatures is not None:
        prefs.priority_features = data.priorityFeatures

    db.commit()
    db.refresh(prefs)

    return UserPreferencesSchema(
        defaultCategory=prefs.default_category,
        aiStyle=prefs.ai_style,
        currency=prefs.currency,
        notificationsEmail=prefs.notifications_email,
        notificationsPriceDrops=prefs.notifications_price_drops,
        darkMode=prefs.dark_mode,
        budgetMin=prefs.budget_min,
        budgetMax=prefs.budget_max,
        preferredBrands=prefs.preferred_brands or [],
        priorityFeatures=prefs.priority_features or ["High Performance", "OLED Display"]
    )

@router.get("/settings")
def get_settings(current_user: User = Depends(get_current_user)):
    """Retrieve full settings structure."""
    return map_user_profile(current_user)
