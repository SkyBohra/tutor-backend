from datetime import datetime
from typing import Optional, List
from beanie import Document
from pydantic import EmailStr, Field


class User(Document):
    """User model for authentication and profiles"""
    
    email: EmailStr
    hashed_password: str
    full_name: str
    avatar_url: Optional[str] = None
    
    # Role: student, teacher, admin
    role: str = "student"
    
    # Student-specific fields
    grade_level: Optional[str] = None  # e.g., "10th", "college"
    preferred_language: str = "en"
    learning_style: Optional[str] = None  # visual, auditory, kinesthetic
    
    # Preferences
    avatar_preference: str = "default"  # Which avatar style user prefers
    voice_preference: str = "default"  # Which voice style user prefers
    
    # Status
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    class Settings:
        name = "users"
        
    class Config:
        json_schema_extra = {
            "example": {
                "email": "student@example.com",
                "full_name": "John Doe",
                "role": "student",
                "grade_level": "10th",
                "preferred_language": "en",
            }
        }
