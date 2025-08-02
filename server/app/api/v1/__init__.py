from fastapi import APIRouter

from .endpoints import health, example


# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(example.router, prefix="/example", tags=["example"])

# Add more routers as needed
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])