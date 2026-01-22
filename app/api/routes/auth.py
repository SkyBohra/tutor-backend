"""
Authentication API Routes
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from loguru import logger

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    TokenResponse,
    PasswordChange,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserCreate):
    """Register a new user"""
    
    # Check if email already exists
    existing_user = await User.find_one(User.email == request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        role=request.role,
        grade_level=request.grade_level,
        preferred_language=request.preferred_language,
    )
    await user.insert()
    
    # Generate token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            grade_level=user.grade_level,
            preferred_language=user.preferred_language,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin):
    """Login and get access token"""
    
    # Find user
    user = await User.find_one(User.email == request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await user.save()
    
    # Generate token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            grade_level=user.grade_level,
            preferred_language=user.preferred_language,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile"""
    
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        grade_level=current_user.grade_level,
        preferred_language=current_user.preferred_language,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
    )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user's profile"""
    
    # Update fields if provided
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.grade_level is not None:
        current_user.grade_level = request.grade_level
    if request.preferred_language is not None:
        current_user.preferred_language = request.preferred_language
    if request.avatar_preference is not None:
        current_user.avatar_preference = request.avatar_preference
    if request.voice_preference is not None:
        current_user.voice_preference = request.voice_preference
    if request.learning_style is not None:
        current_user.learning_style = request.learning_style
    
    current_user.updated_at = datetime.utcnow()
    await current_user.save()
    
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        grade_level=current_user.grade_level,
        preferred_language=current_user.preferred_language,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
    )


@router.post("/change-password")
async def change_password(
    request: PasswordChange,
    current_user: User = Depends(get_current_user)
):
    """Change current user's password"""
    
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.updated_at = datetime.utcnow()
    await current_user.save()
    
    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout current user (client should discard token)"""
    
    # In a stateless JWT system, logout is handled client-side
    # Here we could add token to a blacklist if needed
    
    return {"message": "Logged out successfully"}
