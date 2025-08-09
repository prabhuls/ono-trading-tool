"""
Authentication endpoints for OAuth flow with one-click trading service
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import verify_jwt_token, create_access_token, JWTPayload
from app.core.auth import get_current_user_jwt, get_current_active_user
from app.core.responses import create_success_response, create_error_response
from app.models.user import User
from app.schemas.user import UserResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login")
async def login(
    redirect_uri: Optional[str] = Query(None, description="Custom redirect URI after login")
):
    """
    Initiate OAuth login with one-click trading service
    
    Redirects user to the trading service login page
    """
    # Use custom redirect URI or default from settings
    callback_url = redirect_uri or f"{settings.frontend_url}/auth/callback"
    
    # Build OAuth authorization URL
    auth_params = {
        "client_id": settings.trading_service_client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid profile email subscriptions",
        "state": "random_state_string"  # Should be generated and stored for CSRF protection
    }
    
    # Construct authorization URL
    auth_url = f"{settings.trading_service_auth_url}/authorize"
    query_string = "&".join([f"{k}={v}" for k, v in auth_params.items()])
    full_auth_url = f"{auth_url}?{query_string}"
    
    logger.info(f"Redirecting to OAuth login: {full_auth_url}")
    
    return RedirectResponse(url=full_auth_url)


@router.get("/callback")
async def auth_callback(
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth callback endpoint
    
    Exchanges authorization code for JWT token from trading service
    """
    try:
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{settings.trading_service_auth_url}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.trading_service_client_id,
                    "client_secret": settings.trading_service_client_secret,
                    "redirect_uri": f"{settings.frontend_url}/auth/callback"
                }
            )
            
            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code"
                )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received"
                )
        
        # Verify the JWT token
        jwt_payload = verify_jwt_token(access_token)
        
        if not jwt_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token received from auth service"
            )
        
        # Check if user exists or create new one
        result = await db.execute(
            select(User).where(User.external_auth_id == jwt_payload.user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                external_auth_id=jwt_payload.user_id,
                email=jwt_payload.email or f"{jwt_payload.user_id}@trading.service",
                username=jwt_payload.username,
                full_name=jwt_payload.full_name,
                is_active=True,
                is_verified=True,
                subscription_data=jwt_payload.subscriptions,
                hashed_password="external_auth"  # Placeholder for external auth
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"Created new user from OAuth: {user.id}")
        else:
            # Update existing user
            user.last_login_at = datetime.utcnow()
            user.subscription_data = jwt_payload.subscriptions
            await db.commit()
            
            logger.info(f"User logged in via OAuth: {user.id}")
        
        # Return token to frontend
        # Frontend will store this and redirect to app
        return create_success_response(
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "subscriptions": jwt_payload.subscriptions
                }
            },
            message="Authentication successful"
        )
        
    except httpx.RequestError as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/verify")
async def verify_token(
    jwt_payload: Optional[JWTPayload] = Depends(get_current_user_jwt)
):
    """
    Verify current JWT token
    
    Returns user information if token is valid
    """
    if not jwt_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token"
        )
    
    return create_success_response(
        data={
            "valid": True,
            "user_id": jwt_payload.user_id,
            "email": jwt_payload.email,
            "username": jwt_payload.username,
            "subscriptions": jwt_payload.subscriptions,
            "expires_at": jwt_payload.exp
        },
        message="Token is valid"
    )


@router.get("/user")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information
    
    Requires valid JWT token
    """
    return create_success_response(
        data=UserResponse.model_validate(current_user),
        message="User information retrieved"
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Logout endpoint
    
    Note: Since we use JWT tokens, we can't invalidate them server-side.
    The client should remove the token from storage.
    """
    # Clear any server-side session if implemented
    # For now, just return success and let client clear the token
    
    return create_success_response(
        data={"logged_out": True},
        message="Logged out successfully"
    )


@router.post("/refresh")
async def refresh_token(
    jwt_payload: JWTPayload = Depends(get_current_user_jwt)
):
    """
    Refresh JWT token
    
    Note: In production, this would call the trading service to refresh the token.
    For development, we can create a new token with extended expiration.
    """
    if not jwt_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token"
        )
    
    # In production, call trading service to refresh token
    # For now, return error indicating refresh should be done through trading service
    
    return create_error_response(
        error_code="TOKEN_REFRESH_NOT_IMPLEMENTED",
        message="Token refresh should be done through the trading service OAuth flow",
        status_code=status.HTTP_501_NOT_IMPLEMENTED
    )


@router.get("/check-subscription/{subscription_name}")
async def check_subscription(
    subscription_name: str,
    jwt_payload: Optional[JWTPayload] = Depends(get_current_user_jwt)
):
    """
    Check if user has a specific subscription
    
    Args:
        subscription_name: Name of the subscription to check
    """
    if not jwt_payload:
        return create_success_response(
            data={"has_subscription": False, "authenticated": False},
            message="Not authenticated"
        )
    
    has_subscription = jwt_payload.get_subscription(subscription_name) is not None
    
    return create_success_response(
        data={
            "has_subscription": has_subscription,
            "authenticated": True,
            "subscription_data": jwt_payload.get_subscription(subscription_name)
        },
        message=f"Subscription check for '{subscription_name}'"
    )


@router.get("/dev/create-test-token")
async def create_test_token(
    user_id: str = Query("test-user-123"),
    email: str = Query("test@example.com"),
    include_subscriptions: bool = Query(True)
):
    """
    Create a test JWT token for development
    
    WARNING: This endpoint should be disabled in production!
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test token generation is disabled in production"
        )
    
    # Create test token with optional subscriptions
    additional_claims = {
        "email": email,
        "username": f"test_{user_id}",
        "full_name": "Test User",
        "is_active": True
    }
    
    if include_subscriptions:
        additional_claims["subscriptions"] = {
            "BASIC": True,
            "PREMIUM": True,
            "FI": True,
            "DITTY": True
        }
    
    token = create_access_token(
        subject=user_id,
        additional_claims=additional_claims
    )
    
    return create_success_response(
        data={
            "access_token": token,
            "token_type": "bearer",
            "warning": "This is a test token for development only"
        },
        message="Test token created"
    )