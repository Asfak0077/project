from typing import Optional, List
from pydantic import BaseModel, EmailStr

class UserPreferencesSchema(BaseModel):
    defaultCategory: str = "Laptop"
    aiStyle: str = "performance"  # 'balanced', 'performance', 'budget', 'battery'
    currency: str = "INR"
    notificationsEmail: bool = True
    notificationsPriceDrops: bool = True
    darkMode: bool = False
    budgetMin: float = 0.0
    budgetMax: float = 150000.0
    preferredBrands: List[str] = []
    priorityFeatures: List[str] = []

    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    profile_image: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    authMethod: str = "email"
    twoFactorEnabled: bool = True
    isAdmin: bool = False
    role: str = "user"
    totalChats: Optional[int] = 0
    totalConversations: Optional[int] = 0
    totalComparisons: Optional[int] = 0
    wishlistCount: Optional[int] = 0
    preferences: UserPreferencesSchema

    class Config:
        from_attributes = True

class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    currentPassword: Optional[str] = None
    newPassword: Optional[str] = None
    twoFactorEnabled: Optional[bool] = None

class PasswordChangeRequest(BaseModel):
    currentPassword: str
    newPassword: str

class UserPreferencesUpdateRequest(BaseModel):
    defaultCategory: Optional[str] = None
    aiStyle: Optional[str] = None
    currency: Optional[str] = None
    notificationsEmail: Optional[bool] = None
    notificationsPriceDrops: Optional[bool] = None
    darkMode: Optional[bool] = None
    budgetMin: Optional[float] = None
    budgetMax: Optional[float] = None
    preferredBrands: Optional[List[str]] = None
    priorityFeatures: Optional[List[str]] = None
