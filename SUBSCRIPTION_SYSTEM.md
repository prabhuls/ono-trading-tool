# ONO/ONOV Subscription System

This document explains how to use the ONO and ONOV subscription system implemented in the Trading Tools API.

## Subscription Levels

- **ONO**: Basic subscription for standard API endpoints
- **ONOV**: VIP subscription with access to all endpoints (includes ONO access)

## How It Works

### Authentication Control

The system is controlled by the `ENABLE_AUTH` environment variable:

- `ENABLE_AUTH=false`: No authentication required, all endpoints accessible
- `ENABLE_AUTH=true`: Authentication and subscription validation required

### Subscription Validation

When `ENABLE_AUTH=true`, all API endpoints require:
1. Valid JWT token
2. ONO or ONOV subscription in the token payload

## API Dependencies

### For Standard Endpoints
Use `conditional_jwt_token` dependency:
```python
from app.core.auth import conditional_jwt_token
from app.core.security import JWTPayload

@router.get("/endpoint")
async def my_endpoint(
    current_user: Optional[JWTPayload] = Depends(conditional_jwt_token)
):
    # Endpoint logic here
    pass
```

### For VIP-Only Endpoints
Use `conditional_jwt_token_vip` dependency:
```python
from app.core.auth import conditional_jwt_token_vip
from app.core.security import JWTPayload

@router.get("/vip-endpoint")
async def my_vip_endpoint(
    current_user: Optional[JWTPayload] = Depends(conditional_jwt_token_vip)
):
    # VIP endpoint logic here
    pass
```

## JWT Token Structure

Tokens must include a `subscriptions` object:

```json
{
  "sub": "user-id",
  "subscriptions": {
    "ONO": true,
    "ONOV": true
  },
  "exp": 1758820583,
  "iat": 1758818783,
  "is_active": true
}
```

## Testing

### Create Test Token (Development Only)

```bash
# Create token with both ONO and ONOV subscriptions
curl -X GET "http://localhost:8000/api/v1/auth/dev/create-test-token?user_id=test-user&include_subscriptions=true"

# Create token without subscriptions
curl -X GET "http://localhost:8000/api/v1/auth/dev/create-test-token?user_id=test-user&include_subscriptions=false"
```

### Test API Endpoints

```bash
# Without token (should fail if ENABLE_AUTH=true)
curl -X GET "http://localhost:8000/api/v1/market-data/spy-price"

# With valid token
curl -X GET "http://localhost:8000/api/v1/market-data/spy-price" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Error Responses

| Scenario | Status | Error Message |
|----------|--------|---------------|
| No token provided | 401 | "Missing authentication token" |
| Invalid/expired token | 401 | "Invalid or expired token" |
| No ONO/ONOV subscription | 403 | "ONO or ONOV subscription required" |
| No ONOV for VIP endpoint | 403 | "ONOV (VIP) subscription required" |

## Environment Configuration

Set these in your `.env` file:

```bash
# Enable/disable authentication
ENABLE_AUTH=true  # or false

# Environment (affects test token generation)
ENVIRONMENT=development  # or production

# Required for JWT verification
SECRET_KEY=your-secret-key-here
```

## Access Matrix

| User Type | ONO Endpoints | ONOV (VIP) Endpoints |
|-----------|---------------|---------------------|
| No subscription | ❌ | ❌ |
| ONO only | ✅ | ❌ |
| ONOV (VIP) | ✅ | ✅ |

## Implementation Notes

- ONOV users automatically get access to all ONO endpoints
- When `ENABLE_AUTH=false`, all endpoints are accessible regardless of subscription
- Test token generation is only available in development environment
- The system uses JWT tokens with RSA public key verification for production tokens
- Development tokens use HMAC signing for testing purposes

## Quick Setup

1. Set `ENABLE_AUTH=true` in `.env`
2. Restart your server
3. Create test tokens using the dev endpoint
4. Test your API endpoints with proper Authorization headers

For production use, ensure proper JWT tokens are issued by your authentication service with the correct subscription data.