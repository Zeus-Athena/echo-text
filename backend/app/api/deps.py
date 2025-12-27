"""
API Dependencies
共用的依赖注入
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserConfig

# Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user if admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, None otherwise"""
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        return None

    # Note: This should be async but for optional user we return None on error
    return None  # TODO: Implement async version


def verify_token(token: str) -> dict:
    """Verify token and return payload (for WebSocket auth)"""
    payload = decode_token(token)
    if payload is None:
        raise ValueError("Invalid token")
    return payload


async def get_effective_config(user: User, db: AsyncSession) -> UserConfig | None:
    """
    Get the effective config for a user.
    If user has can_use_admin_key=true, returns admin's config for API keys.
    Otherwise returns user's own config.
    """
    # Get user's own config first
    result = await db.execute(select(UserConfig).where(UserConfig.user_id == user.id))
    user_config = result.scalar_one_or_none()

    # If user can use admin key, get admin's config
    if user.can_use_admin_key and user.role != "admin":
        admin_result = await db.execute(select(User).where(User.role == "admin").limit(1))
        admin_user = admin_result.scalar_one_or_none()

        if admin_user:
            admin_config_result = await db.execute(
                select(UserConfig).where(UserConfig.user_id == admin_user.id)
            )
            admin_config = admin_config_result.scalar_one_or_none()
            if admin_config:
                return admin_config

    return user_config
