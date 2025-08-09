from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.core.responses import create_success_response
from app.core.cache import cache_manager
from app.core.config import settings


router = APIRouter()


@router.get("")
async def health_check() -> JSONResponse:
    """
    Detailed health check endpoint
    """
    # Check cache status
    cache_metrics = cache_manager.get_metrics()
    
    # Build health response
    health_data = {
        "status": "healthy",
        "service": settings.api.title,
        "version": settings.api.version,
        "environment": settings.environment,
        "cache": {
            "connected": cache_manager._connected,
            "metrics": cache_metrics
        },
        "features": settings.features
    }
    
    return create_success_response(
        data=health_data,
        message="Service is healthy"
    )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Kubernetes readiness probe endpoint
    """
    # Check if all required services are ready
    is_ready = cache_manager._connected
    
    if not is_ready:
        return create_success_response(
            data={"ready": False},
            message="Service is not ready",
            status_code=503
        )
        
    return create_success_response(
        data={"ready": True},
        message="Service is ready"
    )


@router.get("/live")
async def liveness_check() -> JSONResponse:
    """
    Kubernetes liveness probe endpoint
    """
    return create_success_response(
        data={"alive": True},
        message="Service is alive"
    )