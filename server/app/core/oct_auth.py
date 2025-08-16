"""
One Click Trading (OCT) JWT authentication
"""
from jose import jwt
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from fastapi import Query, Header, Cookie, HTTPException, status, Depends

logger = logging.getLogger(__name__)

# OCT Public Key for JWT verification
OCT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtSt0xH5N6SOVXY4E2h1X
WE6edernQCmw2kfg6023C64hYR4PZH8XM2P9qoyAzq19UDJZbVj4hi/75GKHEFBC
zL+SrJLgc/6jZoMpOYtEhDgzEKKdfFtgpGD18Idc5IyvBLeW2d8gvfIJMuxRUnT6
K3spmisjdZtd+7bwMKPl6BGAsxZbhlkGjLI1gP/fHrdfU2uoL5okxbbzg1NH95xc
LSXX2JJ+q//t8vLGy+zMh8HPqFM9ojsxzT97AiR7uZZPBvR6c/rX5GDIFPvo5QVr
crCucCyTMeYqwyGl14zN0rArFi6eFXDn+JWTs3Qf04F8LQn7TiwxKV9KRgPHYFtG
qwIDAQAB
-----END PUBLIC KEY-----"""


class OCTTokenPayload:
    """OCT JWT token payload structure"""
    def __init__(self, data: Dict[str, Any]):
        self.sub: str = data.get("sub", "")  # User ID
        self.subscriptions: Any = data.get("subscriptions")
        self.exp: Optional[int] = data.get("exp")
        self.iat: Optional[int] = data.get("iat")
        self._raw = data
    
    @property
    def user_id(self) -> str:
        """Get user ID from token"""
        return self.sub
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if self.exp:
            return datetime.utcnow().timestamp() > self.exp
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self._raw


def verify_token_string(token: str) -> Optional[OCTTokenPayload]:
    """
    Verify JWT token string from One Click Trading
    
    Args:
        token: JWT token string
        
    Returns:
        OCTTokenPayload if valid, None if invalid
    """
    try:
        logger.debug("Attempting to verify OCT JWT token")
        
        # Decode and verify the token
        decoded = jwt.decode(
            token, 
            OCT_PUBLIC_KEY, 
            algorithms=["RS256"],
            options={"verify_signature": True}
        )
        
        # Create payload object
        payload = OCTTokenPayload(decoded)
        
        # Check if expired
        if payload.is_expired:
            logger.warning(f"OCT token expired for user {payload.user_id}")
            return None
        
        logger.info(f"OCT token verified successfully for user {payload.user_id}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("OCT token has expired signature")
        return None
    except jwt.JWTError as e:
        logger.warning(f"Invalid OCT token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying OCT token: {str(e)}")
        return None


def extract_token_from_request(
    query_params: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Extract JWT token from various request sources
    
    Args:
        query_params: Query parameters dictionary
        headers: Request headers dictionary
        cookies: Request cookies dictionary
        
    Returns:
        Token string if found, None otherwise
    """
    # Check query parameter first (most common for OCT)
    if query_params and "token" in query_params:
        logger.debug("Token found in query parameters")
        return query_params["token"]
    
    # Check Authorization header
    if headers:
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            logger.debug("Token found in Authorization header")
            return auth_header[7:]
    
    # Check cookies
    if cookies and "auth_token" in cookies:
        logger.debug("Token found in cookies")
        return cookies["auth_token"]
    
    logger.debug("No token found in request")
    return None


def verify_oct_token(
    token_from_query: Optional[str] = Query(None, alias="token"),
    authorization: Optional[str] = Header(None),
    auth_token: Optional[str] = Cookie(None)
) -> Optional[OCTTokenPayload]:
    """
    FastAPI dependency to verify OCT JWT token from various sources
    
    Args:
        token_from_query: Token from query parameter (?token=...)
        authorization: Authorization header
        auth_token: Token from cookie
        
    Returns:
        OCTTokenPayload if valid
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    # Extract token from various sources
    token = None
    
    # Priority 1: Query parameter
    if token_from_query:
        token = token_from_query
        logger.debug("Using token from query parameter")
    # Priority 2: Authorization header
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        logger.debug("Using token from Authorization header")
    # Priority 3: Cookie
    elif auth_token:
        token = auth_token
        logger.debug("Using token from cookie")
    
    if not token:
        logger.warning("No token provided in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify the token
    payload = verify_token_string(token)
    
    if not payload:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return payload