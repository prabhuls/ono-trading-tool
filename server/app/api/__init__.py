"""
API Router Configuration
Registers all API endpoints
"""

from fastapi import APIRouter

# Import endpoint routers
from app.api.endpoints import credit_spread

# Create main API router
api_router = APIRouter()

# Register endpoint routers
api_router.include_router(
    credit_spread.router,
    prefix="/credit-spread",
    tags=["credit-spread"]
)