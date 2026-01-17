"""Authentication API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_user,
)
from src.api.schemas import TokenResponse, UserCreate, UserResponse
from src.models.database import get_db
from src.models.entities import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    # Check if email exists
    query = select(User).where(User.email == request.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        id=uuid.uuid4(),
        name=request.name,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        role=request.role,
        language=request.language,
        stt_provider=request.stt_provider,
        tts_provider=request.tts_provider,
    )
    db.add(user)
    await db.flush()

    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login and get access token."""
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse.model_validate(current_user)
