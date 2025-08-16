from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.responses import create_success_response
from app.core.cache import redis_cache
from app.core.config import settings


router = APIRouter()


@router.get("")
async def health_check() -> JSONResponse:
    """
    Detailed health check endpoint
    """
    # Build health response
    health_data = {
        "status": "healthy",
        "service": settings.api.title,
        "version": settings.api.version,
        "environment": settings.environment,
        "cache": {
            "connected": redis_cache.redis_client is not None,
            "enabled": settings.enable_caching
        },
        "database": {
            "enabled": settings.enable_database
        }
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
    # Service is ready if basic requirements are met
    is_ready = True
        
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