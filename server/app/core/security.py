"""
Security utilities for JWT authentication and authorization
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from jose import jwt, JWTError  # type: ignore[import-untyped]
from jose.exceptions import ExpiredSignatureError, JWTClaimsError  # type: ignore[import-untyped]
from passlib.context import CryptContext  # type: ignore[import-untyped]

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Password hashing context (for local user management if needed)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTPayload:
    """JWT Payload structure from one-click trading service"""
    def __init__(self, payload: Dict[str, Any]):
        self.sub: str = payload.get("sub", "")  # User ID
        self.email: Optional[str] = payload.get("email")
        self.username: Optional[str] = payload.get("username")
        self.full_name: Optional[str] = payload.get("full_name")
        self.subscriptions: Dict[str, Any] = payload.get("subscriptions", {})
        self.exp: Optional[int] = payload.get("exp")
        self.iat: Optional[int] = payload.get("iat")
        self.scopes: List[str] = payload.get("scopes", [])
        self.is_active: bool = payload.get("is_active", True)
        self.raw_payload: Dict[str, Any] = payload
        
    @property
    def user_id(self) -> str:
        """Get user ID from subject claim"""
        return self.sub
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if self.exp:
            return datetime.utcnow().timestamp() > self.exp
        return False
    
    @property
    def has_subscription(self) -> bool:
        """Check if user has any active subscription"""
        return bool(self.subscriptions)
    
    def has_scope(self, scope: str) -> bool:
        """Check if user has specific scope"""
        return scope in self.scopes
    
    def get_subscription(self, service: str) -> Optional[Any]:
        """Get subscription data for specific service"""
        return self.subscriptions.get(service)


def verify_jwt_token(token: str) -> Optional[JWTPayload]:
    """
    Verify JWT token using RSA public key
    
    Args:
        token: JWT token string
        
    Returns:
        JWTPayload object if valid, None otherwise
    """
    try:
        # Decode and verify the token
        payload = jwt.decode(
            token,
            settings.security.jwt_public_key,
            algorithms=[settings.security.algorithm],
            options={"verify_exp": True}
        )
        
        # Create and return JWTPayload object
        jwt_payload = JWTPayload(payload)
        
        logger.info(
            "JWT token verified successfully",
            user_id=jwt_payload.user_id,
            has_subscriptions=jwt_payload.has_subscription
        )
        
        return jwt_payload
        
    except ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
        
    except JWTClaimsError as e:
        logger.warning(f"JWT claims error: {str(e)}")
        return None
        
    except JWTError as e:
        logger.warning(f"JWT error: {str(e)}")
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error verifying JWT: {str(e)}")
        return None


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token (for local testing/development)
    Note: In production, tokens should come from the one-click trading service
    
    Args:
        subject: User ID or identifier
        expires_delta: Token expiration time
        additional_claims: Additional JWT claims
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    # Note: This uses HS256 for local tokens
    # Production tokens from trading service use RS256
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm="HS256"
    )
    
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password
    (For local user management if needed)
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password for storing
    (For local user management if needed)
    """
    return pwd_context.hash(password)


def extract_token_from_header(authorization: str) -> Optional[str]:
    """
    Extract token from Authorization header
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token string if valid Bearer format, None otherwise
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


def validate_subscription(
    jwt_payload: JWTPayload,
    required_subscription: Optional[str] = None,
    required_scopes: Optional[List[str]] = None
) -> bool:
    """
    Validate user subscriptions and scopes
    
    Args:
        jwt_payload: JWT payload object
        required_subscription: Required subscription name
        required_scopes: List of required scopes
        
    Returns:
        True if validation passes, False otherwise
    """
    # Check if user is active
    if not jwt_payload.is_active:
        return False
    
    # Check required subscription
    if required_subscription:
        if not jwt_payload.get_subscription(required_subscription):
            logger.warning(
                f"User {jwt_payload.user_id} lacks required subscription: {required_subscription}"
            )
            return False
    
    # Check required scopes
    if required_scopes:
        for scope in required_scopes:
            if not jwt_payload.has_scope(scope):
                logger.warning(
                    f"User {jwt_payload.user_id} lacks required scope: {scope}"
                )
                return False
    
    return True


# Security utility functions for rate limiting and request validation
def generate_api_key() -> str:
    """Generate a secure API key"""
    import secrets
    return secrets.token_urlsafe(32)


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid format, False otherwise
    """
    # Basic validation - ensure it's the right length and format
    if not api_key or len(api_key) < 32:
        return False
    
    # Check if it only contains valid URL-safe characters
    import string
    valid_chars = string.ascii_letters + string.digits + "-_"
    return all(c in valid_chars for c in api_key)