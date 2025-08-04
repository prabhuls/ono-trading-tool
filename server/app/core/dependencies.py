"""
Common dependencies for FastAPI endpoints
"""
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db as _get_db


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database dependency that can be used in endpoints.
    This is a wrapper around the core get_db that provides better error messages.
    """
    try:
        async for session in _get_db():
            yield session
    except RuntimeError as e:
        if "Database is not enabled" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="This feature requires database access, but the database is not enabled."
            )
        raise


def require_database(func):
    """
    Decorator to ensure endpoint requires database access.
    Use this on endpoints that absolutely need database functionality.
    
    Usage:
        @router.get("/users")
        @require_database
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    if not settings.enable_database:
        async def disabled_endpoint(*args, **kwargs):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="This endpoint requires database access, but the database is not enabled."
            )
        return disabled_endpoint
    return func


def require_cache(func):
    """
    Decorator to ensure endpoint requires cache access.
    Use this on endpoints that absolutely need cache functionality.
    
    Usage:
        @router.get("/cached-data")
        @require_cache
        async def get_cached_data():
            ...
    """
    if not settings.enable_caching:
        async def disabled_endpoint(*args, **kwargs):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="This endpoint requires cache access, but caching is not enabled."
            )
        return disabled_endpoint
    return func


class OptionalDatabase:
    """
    Dependency that provides database session if available, None otherwise.
    Use this for endpoints that can work with or without database.
    
    Usage:
        @router.get("/data")
        async def get_data(db: Optional[AsyncSession] = Depends(OptionalDatabase())):
            if db:
                # Use database
            else:
                # Fallback logic
    """
    
    async def __call__(self) -> AsyncSession | None:
        if not settings.enable_database:
            return None
        
        try:
            async for session in _get_db():
                return session
        except RuntimeError:
            return None