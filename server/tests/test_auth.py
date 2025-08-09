"""
Test cases for JWT authentication endpoints
"""
import pytest
import httpx
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_create_test_token():
    """Test creating a development test token"""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/auth/auth/dev/create-test-token",
            params={
                "user_id": "test-123",
                "email": "test@example.com",
                "include_subscriptions": "true"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_verify_token():
    """Test token verification"""
    # First create a token
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        token_response = await client.get(
            "/api/v1/auth/auth/dev/create-test-token",
            params={"user_id": "test-123", "email": "test@example.com"}
        )
        token = token_response.json()["data"]["access_token"]
        
        # Then verify it
        verify_response = await client.post(
            "/api/v1/auth/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["success"] is True
    assert data["data"]["valid"] is True
    assert data["data"]["user_id"] == "test-123"


@pytest.mark.asyncio
async def test_check_subscription():
    """Test subscription checking"""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create token with subscriptions
        token_response = await client.get(
            "/api/v1/auth/auth/dev/create-test-token",
            params={"include_subscriptions": "true"}
        )
        token = token_response.json()["data"]["access_token"]
        
        # Check FI subscription (should be true)
        fi_response = await client.get(
            "/api/v1/auth/auth/check-subscription/FI",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Check PREMIUM subscription (should be false)
        premium_response = await client.get(
            "/api/v1/auth/auth/check-subscription/PREMIUM",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    # FI should be true
    assert fi_response.status_code == 200
    fi_data = fi_response.json()
    assert fi_data["success"] is True
    assert fi_data["data"]["has_subscription"] is True
    assert fi_data["data"]["authenticated"] is True
    
    # PREMIUM should be false
    assert premium_response.status_code == 200
    premium_data = premium_response.json()
    assert premium_data["success"] is True
    assert premium_data["data"]["has_subscription"] is False
    assert premium_data["data"]["authenticated"] is True


@pytest.mark.asyncio
async def test_unauthenticated_subscription_check():
    """Test subscription check without authentication"""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/auth/check-subscription/FI")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["has_subscription"] is False
    assert data["data"]["authenticated"] is False