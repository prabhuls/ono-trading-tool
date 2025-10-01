"""
Simplified JWT authentication endpoints (no OAuth flow)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import create_access_token, JWTPayload
from app.core.auth import conditional_jwt_token, public_jwt_token
from app.core.responses import create_success_response

logger = get_logger(__name__)
router = APIRouter()


@router.get("/verify")
async def verify_token(
    jwt_payload: Optional[JWTPayload] = Depends(public_jwt_token)
):
    """
    Verify current JWT token (public endpoint - no subscription required)

    Returns user information if token is valid, or auth status if no token
    """
    if not jwt_payload:
        return {
            "success": False,
            "valid": False,
            "authenticated": False,
            "message": "No token provided or authentication disabled"
        }
    
    # Return user object in the format the frontend expects
    # OCT tokens only have sub and subscriptions, no email/username
    return create_success_response(
        data={
            "user": {
                "sub": jwt_payload.user_id,
                "user_id": jwt_payload.user_id,
                "subscriptions": jwt_payload.subscriptions,
                "exp": jwt_payload.exp,
                "iat": jwt_payload.iat,
                "is_active": jwt_payload.is_active
            },
            "valid": True
        },
        message="Token is valid"
    )


@router.get("/check-subscription/{subscription_name}")
async def check_subscription(
    subscription_name: str,
    jwt_payload: Optional[JWTPayload] = Depends(public_jwt_token)
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
    user_id: str = Query("test-user-123", description="User ID for the test token"),
    email: str = Query("test@example.com", description="Email for the test token"),
    include_subscriptions: bool = Query(True, description="Include subscriptions (deprecated, use subscription_type)"),
    subscription_type: str = Query("both", regex="^(none|ono|onov|both)$", description="Subscription type: none, ono (standard), onov (VIP), or both")
):
    """
    Create a test JWT token for development with flexible subscription options

    Args:
        user_id: User identifier
        email: User email
        include_subscriptions: (Deprecated) If False, no subscriptions are added
        subscription_type: Type of subscription to include
            - "none": No subscriptions
            - "ono": Only ONO (standard subscription)
            - "onov": ONO1 (VIP subscription, includes ONO access)
            - "both": Both ONO and ONO1 (default)

    Examples:
        - Standard user (ONO only): ?subscription_type=ono
        - VIP user (ONO1): ?subscription_type=onov
        - No subscription: ?subscription_type=none or ?include_subscriptions=false
        - Both (default): ?subscription_type=both or just omit parameters

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

    # Determine subscriptions based on parameters
    # include_subscriptions=false takes precedence for backward compatibility
    if not include_subscriptions:
        additional_claims["subscriptions"] = {}
        subscription_message = "no subscriptions"
    else:
        # Use subscription_type to determine which subscriptions to include
        if subscription_type == "none":
            additional_claims["subscriptions"] = {}
            subscription_message = "no subscriptions"
        elif subscription_type == "ono":
            additional_claims["subscriptions"] = {"ONO": True}
            subscription_message = "ONO (standard) subscription"
        elif subscription_type == "onov":
            # ONO1 users also have ONO access (VIP includes standard)
            additional_claims["subscriptions"] = {"ONO": True, "ONO1": True}
            subscription_message = "ONO1 (VIP) subscription with ONO access"
        elif subscription_type == "both":
            additional_claims["subscriptions"] = {"ONO": True, "ONO1": True}
            subscription_message = "both ONO and ONO1 subscriptions"

    token = create_access_token(
        subject=user_id,
        additional_claims=additional_claims
    )

    return create_success_response(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user_id": user_id,
            "subscriptions": additional_claims.get("subscriptions", {}),
            "subscription_type": subscription_type if include_subscriptions else "none",
            "warning": "This is a test token for development only"
        },
        message=f"Test token created with {subscription_message}"
    )