from fastapi import APIRouter

from .endpoints import health, example, users, auth, market_status, market_data
from app.api.endpoints import credit_spread, market, claims, chart_data, credit_spreads, user_spreads


# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(example.router, prefix="/example", tags=["example"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(market_status.router, prefix="/market-status", tags=["market-status"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(credit_spread.router, prefix="/credit-spread", tags=["credit-spread"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(claims.router, prefix="/claims", tags=["claims"])
api_router.include_router(chart_data.router, tags=["chart-data"])  # No prefix to match frontend expectations
api_router.include_router(credit_spreads.router, prefix="/credit-spreads", tags=["credit-spreads"])
api_router.include_router(user_spreads.router, prefix="/user-spreads", tags=["user-spreads"])  # Simple JWT-based spreads