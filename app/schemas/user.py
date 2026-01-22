from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field("student", pattern="^(student|teacher|admin)$")
    grade_level: Optional[str] = None
    preferred_language: str = "en"


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (excludes password)"""
    id: str
    email: str
    full_name: str
    role: str
    grade_level: Optional[str] = None
    preferred_language: str
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = None
    grade_level: Optional[str] = None
    preferred_language: Optional[str] = None
    avatar_preference: Optional[str] = None
    voice_preference: Optional[str] = None
    learning_style: Optional[str] = None


class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordChange(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: str = Field(..., min_length=8)
