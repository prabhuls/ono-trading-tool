# Authentication Documentation

## Overview

This boilerplate includes a complete JWT-based authentication system that integrates with a one-click trading service using OAuth 2.0. The implementation uses RS256 (RSA public key) verification for maximum security.

## Architecture

### Backend (FastAPI)
- **JWT Verification**: RS256 algorithm with RSA public key
- **User Management**: Automatic user creation on first login
- **Subscription Tracking**: Real-time subscription status from trading service
- **Flexible Protection**: Decorators and dependencies for endpoint protection

### Frontend (Next.js)
- **Auth Context**: Global authentication state management
- **Auth Guards**: Components for protecting pages
- **Token Management**: Automatic token storage and injection
- **OAuth Flow**: Seamless integration with trading service

## Configuration

### Backend Environment Variables

```bash
# Required for OAuth integration
TRADING_SERVICE_AUTH_URL=https://auth.tradingservice.com
TRADING_SERVICE_CLIENT_ID=your-client-id
TRADING_SERVICE_CLIENT_SECRET=your-client-secret
FRONTEND_URL=http://localhost:3000
```

### Frontend Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FRONTEND_URL=http://localhost:3000
```

## Usage Examples

### Backend: Protecting Endpoints

#### 1. Basic Authentication Required

```python
from app.core.auth import get_current_active_user
from fastapi import Depends

@router.get("/protected")
async def protected_endpoint(user = Depends(get_current_active_user)):
    return {"message": f"Hello {user.email}"}
```

#### 2. Optional Authentication

```python
from app.core.auth import optional_user

@router.get("/public")
async def public_endpoint(user = Depends(optional_user)):
    if user:
        return {"message": f"Hello {user.email}"}
    return {"message": "Hello anonymous"}
```

#### 3. Subscription Required

```python
from app.core.auth import require_subscription

@router.get("/premium")
@require_subscription("PREMIUM")
async def premium_endpoint(request: Request):
    return {"message": "Premium content"}
```

#### 4. Multiple Scopes Required

```python
from app.core.auth import require_scopes

@router.post("/admin/action")
@require_scopes("admin:write", "admin:delete")
async def admin_action(request: Request):
    return {"message": "Admin action performed"}
```

#### 5. Using JWT Payload Directly

```python
from app.core.auth import get_current_user_jwt

@router.get("/user/subscriptions")
async def get_subscriptions(jwt_payload = Depends(get_current_user_jwt)):
    return {"subscriptions": jwt_payload.subscriptions}
```

### Frontend: Protecting Pages

#### 1. Using AuthGuard Component

```tsx
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function ProtectedPage() {
  return (
    <AuthGuard>
      <div>Protected content here</div>
    </AuthGuard>
  );
}
```

#### 2. With Subscription Requirement

```tsx
<AuthGuard requiredSubscription="PREMIUM">
  <div>Premium content here</div>
</AuthGuard>
```

#### 3. Using HOC Pattern

```tsx
import { withAuth } from "@/contexts/AuthContext";

function PremiumPage() {
  return <div>Premium content</div>;
}

export default withAuth(PremiumPage, {
  requiredSubscription: "PREMIUM",
  redirectTo: "/subscription-required"
});
```

#### 4. Using Auth Hook

```tsx
import { useAuth } from "@/contexts/AuthContext";

function Component() {
  const { user, isAuthenticated, checkSubscription, login, logout } = useAuth();
  
  if (!isAuthenticated) {
    return <button onClick={login}>Sign In</button>;
  }
  
  const hasPremium = checkSubscription("PREMIUM");
  
  return (
    <div>
      <p>Welcome {user.email}</p>
      {hasPremium && <p>You have premium access!</p>}
      <button onClick={logout}>Sign Out</button>
    </div>
  );
}
```

## Authentication Flow

1. **Login Initiation**
   - User clicks login button
   - Frontend redirects to `/api/v1/auth/login`
   - Backend redirects to trading service OAuth

2. **OAuth Authorization**
   - User authenticates with trading service
   - Trading service redirects back with authorization code

3. **Token Exchange**
   - Backend exchanges code for JWT token
   - Verifies token with RSA public key
   - Creates/updates user in database

4. **Session Establishment**
   - Frontend stores JWT token
   - Token automatically included in API requests
   - User data cached in context

5. **Token Verification**
   - Each protected request verifies JWT
   - Subscription data checked in real-time
   - User access granted/denied based on requirements

## JWT Token Structure

```json
{
  "sub": "user-id-123",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "subscriptions": {
    "BASIC": true,
    "PREMIUM": true,
    "FI": true,
    "DITTY": false
  },
  "scopes": ["read", "write"],
  "exp": 1234567890,
  "iat": 1234567880
}
```

## Security Features

- **RS256 Verification**: Asymmetric key cryptography for token verification
- **Automatic Token Injection**: Tokens automatically added to API requests
- **Secure Storage**: Tokens stored in localStorage with HttpOnly cookie option
- **CSRF Protection**: State parameter in OAuth flow
- **Rate Limiting**: Built-in rate limiting for auth endpoints
- **Token Expiration**: Automatic handling of expired tokens

## Development Tools

### Create Test Token (Development Only)

```bash
# Create a test token for development
curl "http://localhost:8000/api/v1/auth/dev/create-test-token?user_id=test-123&email=test@example.com&include_subscriptions=true"
```

### Verify Token

```bash
# Verify current token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  -X POST "http://localhost:8000/api/v1/auth/verify"
```

### Check Subscription

```bash
# Check specific subscription
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/auth/check-subscription/PREMIUM"
```

## Database Schema

The User model includes:
- `external_auth_id`: Unique ID from trading service
- `subscription_data`: JSON field with current subscriptions
- `last_login_at`: Timestamp of last authentication

## Troubleshooting

### Common Issues

1. **"Invalid token" errors**
   - Verify RSA public key is correctly configured
   - Check token hasn't expired
   - Ensure token is being sent in Authorization header

2. **"User not found" after login**
   - Check database connection
   - Verify user creation on first login
   - Check for unique constraint violations

3. **OAuth redirect issues**
   - Verify FRONTEND_URL is correctly set
   - Check OAuth client configuration with trading service
   - Ensure callback URL is whitelisted

4. **Subscription not detected**
   - Verify subscription data in JWT payload
   - Check subscription name matches exactly
   - Ensure token is recent (subscriptions may change)

## Best Practices

1. **Always use HTTPS in production** for OAuth redirects
2. **Store sensitive config in environment variables**, never in code
3. **Implement token refresh** before expiration for better UX
4. **Cache user data** to reduce API calls
5. **Use subscription checks** at both frontend and backend
6. **Log authentication events** for security auditing
7. **Implement rate limiting** on auth endpoints
8. **Handle token expiration gracefully** with auto-redirect to login

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
async def get_portfolio(user = Depends(get_current_active_user)):
    # Requires valid JWT token
    return {"user_id": user.id, "portfolio": [...]}
```

### Creating a Subscription-Gated Feature

```python
@router.get("/api/premium/advanced-analytics")
@require_subscription("PREMIUM")
async def get_advanced_analytics(request: Request):
    # Only accessible with PREMIUM subscription
    return {"analytics": [...]}
```

### Frontend Page with Mixed Access

```tsx
export default function TradingDashboard() {
  const { isAuthenticated, checkSubscription } = useAuth();
  
  return (
    <div>
      {/* Public content */}
      <MarketOverview />
      
      {/* Authenticated content */}
      {isAuthenticated && <Portfolio />}
      
      {/* Premium content */}
      {checkSubscription("PREMIUM") && <AdvancedCharts />}
    </div>
  );
}
```

This authentication system provides maximum flexibility for tool builders to choose what features require authentication and what subscription levels are needed for different functionality.