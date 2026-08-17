from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr

class UserRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str

class UserAuthInfo(BaseModel):
    id: int
    name: str
    email: str
    role: str = "user"
    avatar: Optional[str] = None
    profile_image: Optional[str] = None
    auth_provider: str = "local"

class TokenResponse(BaseModel):
    token: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user_id: int
    name: str
    email: str
    role: str = "user"
    avatar: Optional[str] = None
    user: Optional[UserAuthInfo] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

class SetPasswordRequest(BaseModel):
    new_password: str
    confirm_password: Optional[str] = None

