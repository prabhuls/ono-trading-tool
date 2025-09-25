"""
Authentication dependencies for FastAPI endpoints
"""
from typing import Optional, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import verify_jwt_token, extract_token_from_header, JWTPayload, validate_subscription
from app.core.logging import get_logger
from app.core.database import get_db
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Only import User model if database is enabled
if settings.enable_database:
    from app.models.user import User
else:
    # Dummy User class for type hints when database is disabled
    class User:
        pass

logger = get_logger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


async def get_optional_db():
    """
    Optional database dependency - returns None if database is disabled
    
    Returns:
        Database session if enabled, None otherwise
    """
    if not settings.enable_database:
        yield None
        return
    
    # Use the standard get_db dependency when database is enabled
    async for db in get_db():
        yield db


async def get_current_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token_from_query: Optional[str] = Query(None, alias="token")
) -> Optional[str]:
    """
    Extract JWT token from request (supports both Authorization header and query param)
    
    Args:
        credentials: HTTP Bearer credentials
        token_from_query: Token from query parameter (?token=...)
        
    Returns:
        Token string if present, None otherwise
    """
    # First check query parameter (for OCT redirect flow)
    if token_from_query:
        return token_from_query
    
    # Then check Authorization header
    if credentials:
        return credentials.credentials
    
    return None


async def get_current_user_jwt(
    token: Optional[str] = Depends(get_current_token)
) -> Optional[JWTPayload]:
    """
    Get current user from JWT token (no database lookup)

    Args:
        token: JWT token from request

    Returns:
        JWTPayload if valid, None otherwise

    Raises:
        HTTPException: If auth is enabled and token is missing/invalid
    """
    # If auth is enabled, require valid token
    if settings.enable_auth:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jwt_payload = verify_jwt_token(token)

        if not jwt_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return jwt_payload

    # If auth is disabled, return None (no authentication required)
    return None


async def get_current_user(
    jwt_payload: Optional[JWTPayload] = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token with database lookup
    Creates user if doesn't exist (first login from trading service)
    
    Args:
        jwt_payload: Verified JWT payload
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not jwt_payload:
        return None
    
    # Look up user by external auth ID
    result = await db.execute(
        select(User).where(User.external_auth_id == jwt_payload.user_id)
    )
    user = result.scalar_one_or_none()
    
    # Create user if doesn't exist (first login)
    # OCT tokens don't have email, so create user with just the sub ID
    if not user:
        user = User(
            external_auth_id=jwt_payload.user_id,
            email=f"{jwt_payload.user_id}@oct.user",  # Placeholder email for OCT users
            username=jwt_payload.username or f"user_{jwt_payload.user_id[:8]}",
            full_name=jwt_payload.full_name,
            is_active=jwt_payload.is_active,
            is_verified=True,  # Verified through trading service
            subscription_data=jwt_payload.subscriptions,
            hashed_password="external_auth"  # Placeholder for external auth
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Created new user from external auth: {user.id}")
    
    # Update last login time and subscription data
    if user:
        from datetime import datetime
        user.last_login_at = datetime.utcnow()
        user.subscription_data = jwt_payload.subscriptions
        await db.commit()
    
    return user


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Get current active user (requires authentication)
    
    Args:
        current_user: User from JWT token
        
    Returns:
        User object if active
        
    Raises:
        HTTPException: If not authenticated or user is inactive
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current superuser (requires superuser privileges)
    
    Args:
        current_user: Active user
        
    Returns:
        User object if superuser
        
    Raises:
        HTTPException: If not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def require_auth(f: Callable) -> Callable:
    """
    Decorator to require authentication for an endpoint
    
    Usage:
        @router.get("/protected")
        @require_auth
        async def protected_endpoint(request: Request):
            user = request.state.user
            return {"user_id": user.id}
    """
    @wraps(f)
    async def decorated_function(request: Request, *args, **kwargs):
        # Get token from header
        auth_header = request.headers.get("Authorization", "")
        token = extract_token_from_header(auth_header)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify token
        jwt_payload = verify_jwt_token(token)
        if not jwt_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Add user to request state
        request.state.jwt_payload = jwt_payload
        
        return await f(request, *args, **kwargs)
    
    return decorated_function


def optional_auth(f: Callable) -> Callable:
    """
    Decorator for optional authentication
    
    Usage:
        @router.get("/public")
        @optional_auth
        async def public_endpoint(request: Request):
            user = getattr(request.state, 'jwt_payload', None)
            if user:
                return {"message": f"Hello {user.user_id}"}
            return {"message": "Hello anonymous"}
    """
    @wraps(f)
    async def decorated_function(request: Request, *args, **kwargs):
        # Get token from header
        auth_header = request.headers.get("Authorization", "")
        token = extract_token_from_header(auth_header)
        
        if token:
            # Verify token if present
            jwt_payload = verify_jwt_token(token)
            if jwt_payload:
                request.state.jwt_payload = jwt_payload
        
        return await f(request, *args, **kwargs)
    
    return decorated_function


def require_subscription(subscription: str) -> Callable:
    """
    Decorator to require specific subscription
    
    Usage:
        @router.get("/premium")
        @require_subscription("PREMIUM")
        async def premium_endpoint(request: Request):
            return {"message": "Premium content"}
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        async def decorated_function(request: Request, *args, **kwargs):
            # First check authentication
            auth_header = request.headers.get("Authorization", "")
            token = extract_token_from_header(auth_header)
            
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Verify token
            jwt_payload = verify_jwt_token(token)
            if not jwt_payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check subscription
            if not validate_subscription(jwt_payload, required_subscription=subscription):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Subscription '{subscription}' required"
                )
            
            request.state.jwt_payload = jwt_payload
            return await f(request, *args, **kwargs)
        
        return decorated_function
    return decorator


def require_scopes(*scopes: str) -> Callable:
    """
    Decorator to require specific scopes
    
    Usage:
        @router.post("/admin/action")
        @require_scopes("admin:write", "admin:delete")
        async def admin_action(request: Request):
            return {"message": "Admin action performed"}
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        async def decorated_function(request: Request, *args, **kwargs):
            # First check authentication
            auth_header = request.headers.get("Authorization", "")
            token = extract_token_from_header(auth_header)
            
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Verify token
            jwt_payload = verify_jwt_token(token)
            if not jwt_payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check scopes
            if not validate_subscription(jwt_payload, required_scopes=list(scopes)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required scopes: {', '.join(scopes)}"
                )
            
            request.state.jwt_payload = jwt_payload
            return await f(request, *args, **kwargs)
        
        return decorated_function
    return decorator


# Dependency for use in path operations
async def optional_user(
    jwt_payload: Optional[JWTPayload] = Depends(get_current_user_jwt),
    db: Optional[AsyncSession] = Depends(get_optional_db)
) -> Optional[User]:
    """
    Optional user dependency - doesn't raise exception if not authenticated
    Works with or without database enabled.
    
    Args:
        jwt_payload: JWT payload if authenticated
        db: Database session (None if database is disabled)
        
    Returns:
        User object if authenticated and database enabled, None otherwise
    """
    if not jwt_payload:
        return None
    
    # If database is disabled, we can't look up the user
    if not db or not settings.enable_database:
        return None
    
    # Database lookup only when database is enabled
    result = await db.execute(
        select(User).where(User.external_auth_id == jwt_payload.user_id)
    )
    return result.scalar_one_or_none()


async def conditional_jwt_token(
    token: Optional[str] = Depends(get_current_token)
) -> Optional[JWTPayload]:
    """
    Conditionally require JWT token based on ENABLE_AUTH setting
    
    Args:
        token: JWT token from request
        
    Returns:
        JWTPayload if authenticated or auth disabled, None if auth disabled and no token
        
    Raises:
        HTTPException: If auth is enabled and token is missing/invalid
    """
    # If auth is disabled, return None (no authentication required)
    if not settings.enable_auth:
        return None
    
    # If auth is enabled, require valid token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    jwt_payload = verify_jwt_token(token)
    
    if not jwt_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return jwt_payload