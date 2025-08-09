# Authentication Documentation

## Overview

This boilerplate implements a streamlined JWT-based authentication system designed for tools that receive authentication tokens from One Click Trading's main platform. The system uses RS256 (RSA public key) verification for production tokens and supports HS256 for development.

**Important**: Authentication can be completely disabled for development/testing by setting `ENABLE_AUTH=false` in your `.env` file.

## Quick Start for Development

1. **Disable authentication entirely** (Recommended for initial development):
   ```bash
   # In your server/.env file
   ENABLE_AUTH=false
   ```
   Now all API endpoints work without any authentication!

2. **Enable authentication** (For production or testing auth flows):
   ```bash
   # In your server/.env file
   ENABLE_AUTH=true
   ```
   Now endpoints using `conditional_jwt_token` will require valid JWT tokens.

## Key Features

- **External Authentication**: Users authenticate through One Click Trading and arrive with a JWT token
- **No User Management**: No local user database, registration, or password management
- **No Logout**: Tools rely on token expiration; users re-authenticate through One Click Trading
- **Token-Based Subscriptions**: Subscription data embedded directly in JWT payload
- **Simplified UI**: No user menu, profile, or account management features

## Architecture

### Backend (FastAPI)
- **JWT Verification**: RS256 algorithm with RSA public key (supports HS256 for development)
- **Stateless Authentication**: No session management or database users
- **Subscription Tracking**: Subscription data extracted from JWT payload
- **Flexible Protection**: Decorators and dependencies for endpoint protection

### Frontend (Next.js)
- **Auth Context**: Global authentication state management
- **Automatic Token Detection**: Captures token from URL parameters
- **Protected Routes**: Redirects unauthenticated users to login page
- **No User Menu**: Simplified interface without logout or profile features

## Configuration

### Backend Environment Variables

```bash
# Authentication toggle (new)
ENABLE_AUTH=false  # Set to true to require authentication for API endpoints

# Only frontend URL needed
FRONTEND_URL=http://localhost:3000
```

### Frontend Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FRONTEND_URL=http://localhost:3000
```

## Authentication Flow

1. **User visits tool directly**: Redirected to login page
2. **Login page**: Displays message and button to authenticate via One Click Trading
3. **User clicks login**: Redirected to `https://app.oneclicktrading.com/landing/login`
4. **After authentication**: One Click Trading redirects back with `?token=JWT_TOKEN`
5. **Token capture**: Frontend automatically detects and stores token
6. **Authenticated access**: User can access protected features until token expires
7. **Token expiration**: User redirected back to login page to re-authenticate

## Disabling Authentication for Development

When `ENABLE_AUTH=false` is set in your `.env` file:
- All API endpoints work without requiring any authentication token
- The `conditional_jwt_token` dependency returns `None` instead of checking for tokens
- Perfect for local development and testing without dealing with JWT tokens
- Frontend can call backend APIs directly without authentication headers

## Usage Examples

### Backend: Protecting Endpoints

#### 1. Conditional Authentication (Respects ENABLE_AUTH setting)

```python
from app.core.auth import conditional_jwt_token
from typing import Optional
from fastapi import Depends

@router.get("/protected")
async def protected_endpoint(jwt_payload: Optional[JWTPayload] = Depends(conditional_jwt_token)):
    # When ENABLE_AUTH=false, jwt_payload will be None
    # When ENABLE_AUTH=true, jwt_payload will contain user data or raise 401
    if jwt_payload:
        return {"message": f"Hello {jwt_payload.email}"}
    return {"message": "Hello anonymous (auth disabled)"}
```

#### 2. Always Require Authentication (Ignores ENABLE_AUTH)

```python
from app.core.auth import require_jwt_token
from fastapi import Depends

@router.get("/always-protected")
async def always_protected_endpoint(jwt_payload = Depends(require_jwt_token)):
    # This will always require authentication regardless of ENABLE_AUTH setting
    return {"message": f"Hello {jwt_payload.email}"}
```

#### 3. Optional Authentication (Always Optional)

```python
from app.core.auth import get_current_user_jwt
from typing import Optional

@router.get("/public")
async def public_endpoint(jwt_payload: Optional[JWTPayload] = Depends(get_current_user_jwt)):
    # This is always optional - doesn't raise errors if no token
    if jwt_payload:
        return {"message": f"Hello {jwt_payload.email}"}
    return {"message": "Hello anonymous"}
```

#### 4. Subscription Required

```python
from app.core.auth import conditional_jwt_token

@router.get("/premium")
async def premium_endpoint(jwt_payload: Optional[JWTPayload] = Depends(conditional_jwt_token)):
    # When ENABLE_AUTH=false, this check is bypassed
    if jwt_payload and not jwt_payload.get_subscription("FI"):
        raise HTTPException(status_code=403, detail="FI subscription required")
    return {"message": "Premium content"}
```

### Frontend: Authentication Implementation

#### 1. AuthContext Usage

```tsx
import { useAuth } from "@/contexts/AuthContext";

function MyComponent() {
  const { isAuthenticated, user, checkSubscription } = useAuth();
  
  if (!isAuthenticated) {
    // Redirect to login or show public content
    return <div>Please log in</div>;
  }
  
  const hasFI = checkSubscription("FI");
  const hasDITTY = checkSubscription("DITTY");
  
  return (
    <div>
      <p>Welcome {user?.email}</p>
      {hasFI && <div>FI Content</div>}
      {hasDITTY && <div>DITTY Content</div>}
    </div>
  );
}
```

#### 2. Protected Page

```tsx
"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ProtectedPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return <div>Protected content here</div>;
}
```

## JWT Token Structure

```json
{
  "sub": "user-id-123",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "subscriptions": {
    "FI": true,
    "DITTY": true
  },
  "exp": 1234567890,
  "iat": 1234567880,
  "type": "access",
  "is_active": true
}
```

## API Endpoints

### Authentication Endpoints

- `POST /api/v1/auth/auth/verify` - Verify current token
- `GET /api/v1/auth/auth/check-subscription/{subscription_name}` - Check specific subscription
- `GET /api/v1/auth/auth/dev/create-test-token` - Create test token (development only)

## Development Tools

### Create Test Token (Development Only)

```bash
# Create a test token for development
curl "http://localhost:8000/api/v1/auth/auth/dev/create-test-token?user_id=test-123&email=test@example.com&include_subscriptions=true"
```

### Verify Token

```bash
# Verify current token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  -X POST "http://localhost:8000/api/v1/auth/auth/verify"
```

### Check Subscription

```bash
# Check specific subscription
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/auth/auth/check-subscription/FI"
```

## Security Features

- **RS256 Verification**: Asymmetric key cryptography for token verification
- **Hardcoded Public Key**: RSA public key embedded in configuration
- **HS256 Development Mode**: Simplified symmetric key for development tokens
- **Token Expiration**: Automatic handling of expired tokens
- **URL Token Cleanup**: Automatically removes token from URL after capture
- **No Sensitive Operations**: No logout endpoints or session management to exploit

## Troubleshooting

### Common Issues

1. **"Invalid token" errors**
   - Verify token hasn't expired
   - Ensure token is being sent in Authorization header
   - Check if using correct algorithm (RS256 for production, HS256 for dev)

2. **Subscription not detected**
   - Verify subscription data in JWT payload
   - Check subscription name matches exactly (case-sensitive)
   - Ensure token is recent (subscriptions may change)

3. **Redirect loop**
   - Clear localStorage and cookies
   - Ensure FRONTEND_URL is correctly configured
   - Check that One Click Trading is sending token parameter

4. **Token not captured from URL**
   - Verify URL contains `?token=` parameter
   - Check browser console for errors
   - Ensure AuthContext is properly initialized

## Best Practices

1. **Always use HTTPS in production** for secure token transmission
2. **Handle token expiration gracefully** by redirecting to login
3. **Validate subscriptions** at both frontend and backend
4. **Don't store sensitive data** in localStorage beyond the token
5. **Test with development tokens** before production deployment

## Examples for Tool Builders

### Creating a Public API Endpoint

```python
@router.get("/api/public/market-data")
async def get_market_data():
    # No authentication required
    return {"data": "public market data"}
```

### Creating a Protected API Endpoint

```python
@router.get("/api/protected/portfolio")
async def get_portfolio(jwt_payload = Depends(get_current_user_jwt)):
    if not jwt_payload:
        raise HTTPException(status_code=401)
    return {"user_id": jwt_payload.user_id, "portfolio": [...]}
```

### Creating a Subscription-Gated Feature

```python
@router.get("/api/premium/fi-data")
async def get_fi_data(jwt_payload = Depends(get_current_user_jwt)):
    if not jwt_payload or not jwt_payload.get_subscription("FI"):
        raise HTTPException(status_code=403, detail="FI subscription required")
    return {"fi_data": [...]}
```

## What's NOT Included

This simplified authentication system intentionally excludes:

- User registration or signup
- Password management or reset
- User profiles or settings
- Logout functionality (rely on token expiration)
- User menu or account dropdown
- Session management
- OAuth flows or client credentials
- Refresh tokens (users re-authenticate through One Click Trading)

This design ensures tools remain lightweight and focused on their core functionality while delegating authentication complexity to One Click Trading's main platform.