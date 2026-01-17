"""Authentication and authorization utilities.

Validates: Requirements 10.3, 10.6
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.database import get_db
from src.models.entities import User


# Bearer token security
security = HTTPBearer()


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: uuid.UUID
    role: str
    exp: datetime


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """Hash password."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """Create JWT access token.
    
    Args:
        user_id: User ID
        role: User role
        
    Returns:
        JWT token string
    """
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData with user info
        
    Raises:
        HTTPException: If token is invalid
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload.get("sub"))
        role = payload.get("role")
        exp = datetime.fromtimestamp(payload.get("exp"))
        
        return TokenData(user_id=user_id, role=role, exp=exp)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user.
    
    Validates: Requirements 10.3, 10.6
    """
    token_data = decode_token(credentials.credentials)
    
    query = select(User).where(User.id == token_data.user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current user and verify admin role.
    
    Validates: Requirements 10.3, 10.6
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_role(allowed_roles: list[str]):
    """Dependency factory for role-based access control.
    
    Args:
        allowed_roles: List of allowed roles
        
    Returns:
        Dependency function
        
    Validates: Requirements 10.3
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}",
            )
        return current_user
    
    return role_checker


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise.
    
    Used for endpoints that work both with and without auth.
    """
    if not credentials:
        return None
    
    try:
        token_data = decode_token(credentials.credentials)
        query = select(User).where(User.id == token_data.user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    except HTTPException:
        return None
