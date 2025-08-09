"""
Simplified JWT authentication endpoints (no OAuth flow)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import create_access_token, JWTPayload
from app.core.auth import conditional_jwt_token
from app.core.responses import create_success_response

logger = get_logger(__name__)
router = APIRouter()


@router.post("/verify")
async def verify_token(
    jwt_payload: Optional[JWTPayload] = Depends(conditional_jwt_token)
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


@router.get("/check-subscription/{subscription_name}")
async def check_subscription(
    subscription_name: str,
    jwt_payload: Optional[JWTPayload] = Depends(conditional_jwt_token)
):
    """
    Check if user has a specific subscription
    
    Args:
        subscription_name: Name of the subscription to check (e.g., FI, DITTY)
    """
    if not jwt_payload:
        return create_success_response(
            data={"has_subscription": False, "authenticated": False},
            message="Not authenticated"
        )
    
    # Check if subscription exists and is true
    subscription_value = jwt_payload.get_subscription(subscription_name)
    has_subscription = subscription_value is True if subscription_value is not None else False
    
    return create_success_response(
        data={
            "has_subscription": has_subscription,
            "authenticated": True,
            "is_active": jwt_payload.is_active,
            "subscription_data": subscription_value
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