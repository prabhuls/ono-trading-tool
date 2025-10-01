# ONO/ONO1 Subscription System

This document explains how to use the ONO and ONO1 subscription system implemented in the Trading Tools API.

## Subscription Levels

- **ONO**: Basic subscription for standard API endpoints
- **ONO1**: VIP subscription with access to all endpoints (includes ONO access)

## How It Works

### Authentication Control

The system is controlled by the `ENABLE_AUTH` environment variable:

- `ENABLE_AUTH=false`: No authentication required, all endpoints accessible
- `ENABLE_AUTH=true`: Authentication and subscription validation required

### Subscription Validation

When `ENABLE_AUTH=true`, all API endpoints require:
1. Valid JWT token
2. ONO or ONO1 subscription in the token payload

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
    "ONO1": true
  },
  "exp": 1758820583,
  "iat": 1758818783,
  "is_active": true
}
```

## Testing

### Create Test Token (Development Only)

The test token endpoint now supports flexible subscription types for testing different user scenarios:

```bash
# Create token with ONO only (Standard Subscription)
curl -X GET "http://localhost:8000/api/v1/auth/dev/create-test-token?subscription_type=ono"

# Create token with ONO1 (VIP Subscription - includes ONO access)
curl -X GET "http://localhost:8000/api/v1/auth/dev/create-test-token?subscription_type=onov"

# Create token with both ONO and ONO1 (Default)
curl -X GET "http://localhost:8000/api/v1/auth/dev/create-test-token?subscription_type=both"
# OR simply
curl -X GET "http://localhost:8000/api/v1/auth/dev/create-test-token"

# Create token without any subscriptions
curl -X GET "http://localhost:8000/api/v1/auth/dev/create-test-token?subscription_type=none"
```

**Available Subscription Types:**
- `ono` - Only ONO (standard subscription) - Can access SPY, SPX
- `onov` - ONO1 (VIP subscription) - Can access SPY, SPX, QQQ, IWM, GLD
- `both` - Both ONO and ONO1 (default)
- `none` - No subscriptions

**Response includes subscription details:**
```json
{
  "success": true,
  "message": "Test token created with ONO (standard) subscription",
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "user_id": "test-user-123",
    "subscriptions": {
      "ONO": true
    },
    "subscription_type": "ono",
    "warning": "This is a test token for development only"
  }
}
```

### Test API Endpoints

```bash
# Without token (should fail if ENABLE_AUTH=true)
curl -X GET "http://localhost:8000/api/v1/market-data/spy-price"

# With valid token
curl -X GET "http://localhost:8000/api/v1/market-data/spy-price" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Testing Scenarios

#### 1. Test Standard User (ONO only)
```bash
# Create ONO-only token
TOKEN=$(curl -s "http://localhost:8000/api/v1/auth/dev/create-test-token?subscription_type=ono" | jq -r '.data.access_token')

# Should succeed - ONO can access SPY
curl -X GET "http://localhost:8000/api/v1/market-data/current-price/SPY" \
  -H "Authorization: Bearer $TOKEN"

# Should fail with 403 - QQQ requires ONO1 (VIP)
curl -X GET "http://localhost:8000/api/v1/market-data/current-price/QQQ" \
  -H "Authorization: Bearer $TOKEN"
```

#### 2. Test VIP User (ONO1)
```bash
# Create ONO1 token
TOKEN=$(curl -s "http://localhost:8000/api/v1/auth/dev/create-test-token?subscription_type=onov" | jq -r '.data.access_token')

# Should succeed - ONO1 can access all symbols
curl -X GET "http://localhost:8000/api/v1/market-data/current-price/QQQ" \
  -H "Authorization: Bearer $TOKEN"

curl -X GET "http://localhost:8000/api/v1/market-data/current-price/IWM" \
  -H "Authorization: Bearer $TOKEN"

curl -X GET "http://localhost:8000/api/v1/market-data/current-price/GLD" \
  -H "Authorization: Bearer $TOKEN"
```

#### 3. Test No Subscription
```bash
# Create token without subscriptions
TOKEN=$(curl -s "http://localhost:8000/api/v1/auth/dev/create-test-token?subscription_type=none" | jq -r '.data.access_token')

# Should fail with 403 - No subscription
curl -X GET "http://localhost:8000/api/v1/market-data/current-price/SPY" \
  -H "Authorization: Bearer $TOKEN"
```

## Error Responses

| Scenario | Status | Error Message |
|----------|--------|---------------|
| No token provided | 401 | "Missing authentication token" |
| Invalid/expired token | 401 | "Invalid or expired token" |
| No ONO/ONO1 subscription | 403 | "ONO or ONO1 subscription required" |
| No ONO1 for VIP endpoint | 403 | "ONO1 (VIP) subscription required" |

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

| User Type | ONO Endpoints | ONO1 (VIP) Endpoints |
|-----------|---------------|---------------------|
| No subscription | ❌ | ❌ |
| ONO only | ✅ | ❌ |
| ONO1 (VIP) | ✅ | ✅ |

## Implementation Notes

- ONO1 users automatically get access to all ONO endpoints
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