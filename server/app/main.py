from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import time
import uuid

from app.core.config import settings
from app.core.logging import get_logger, set_request_id, clear_context, generate_request_id
from app.core.monitoring import ErrorMonitoring
from app.core.cache import cache_manager
from app.core.responses import (
    create_error_response,
    validation_error,
    internal_error,
    ErrorCode
)
from app.api.v1 import api_router
from app.api.middleware import LoggingMiddleware, RateLimitMiddleware


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    logger.info("Starting application", environment=settings.environment)
    
    # Initialize Sentry
    ErrorMonitoring.init_sentry(settings)
    
    # Connect to cache if enabled
    if settings.enable_caching:
        await cache_manager.connect()
    else:
        logger.info("Cache is disabled")
    
    # Initialize database if enabled
    if settings.enable_database:
        from app.core.database import DatabaseManager
        if await DatabaseManager.check_connection():
            logger.info("Database connection established")
        else:
            logger.warning("Database connection failed")
    else:
        logger.info("Database is disabled")
    
    # Initialize other services here (external APIs, etc.)
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    
    # Disconnect from cache if enabled
    if settings.enable_caching:
        await cache_manager.disconnect()
    
    # Close database connections if enabled
    if settings.enable_database:
        from app.core.database import DatabaseManager
        await DatabaseManager.close()
    
    # Close other connections here
    
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.api.title,
    description=settings.api.description,
    version=settings.api.version,
    openapi_url=f"{settings.api.prefix}/openapi.json" if not settings.is_production else None,
    docs_url=f"{settings.api.prefix}/docs" if not settings.is_production else None,
    redoc_url=f"{settings.api.prefix}/redoc" if not settings.is_production else None,
    lifespan=lifespan
)

# Add trusted host middleware (security)
if settings.is_production:
    allowed_hosts = ["*.railway.app", "*.up.railway.app"]
    
    # Add frontend domain if specified
    if settings.frontend_url:
        from urllib.parse import urlparse
        parsed = urlparse(settings.frontend_url if settings.frontend_url.startswith(("http://", "https://")) else f"https://{settings.frontend_url}")
        if parsed.hostname:
            allowed_hosts.append(parsed.hostname)
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.security.allow_credentials,
    allow_methods=settings.security.allowed_methods,
    allow_headers=settings.security.allowed_headers,
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
if settings.api.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with proper formatting
    """
    errors = []
    for error in exc.errors():
        error_detail = {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        }
        errors.append(error_detail)
        
    return validation_error(
        message="Request validation failed",
        errors=errors
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions
    """
    # Map status codes to error codes
    error_code_map = {
        400: ErrorCode.INVALID_REQUEST,
        401: ErrorCode.AUTHENTICATION_REQUIRED,
        403: ErrorCode.PERMISSION_DENIED,
        404: ErrorCode.NOT_FOUND,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_ERROR,
        502: ErrorCode.EXTERNAL_API_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE
    }
    
    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    
    return create_error_response(
        error_code=error_code,
        message=exc.detail,
        status_code=exc.status_code
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions
    """
    # Log the error
    logger.error("Unhandled exception", error=exc)
    
    # Capture to Sentry
    ErrorMonitoring.capture_exception(
        exc,
        context={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None
        }
    )
    
    # Return generic error response
    return internal_error(
        message="An unexpected error occurred",
        error=exc if settings.debug else None
    )


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Add request ID to context and response headers
    """
    request_id = generate_request_id()
    set_request_id(request_id)
    
    # Store in request state for access in endpoints
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        clear_context()


# Process time middleware
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    """
    Add process time to response headers
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response


# Include API router
app.include_router(api_router, prefix=settings.api.prefix)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint
    """
    return {
        "name": settings.api.title,
        "version": settings.api.version,
        "environment": settings.environment,
        "docs": f"{settings.api.prefix}/docs" if not settings.is_production else None
    }


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint with detailed status
    """
    # Check cache connection
    cache_status = {
        "enabled": settings.enable_caching,
        "connected": cache_manager._connected if settings.enable_caching else None,
        "metrics": cache_manager.get_metrics() if settings.enable_caching else None
    }
    
    # Check database connection
    database_status = {
        "enabled": settings.enable_database,
        "connected": None
    }
    
    if settings.enable_database:
        from app.core.database import DatabaseManager
        database_status["connected"] = await DatabaseManager.check_connection()
    
    # Check external services (example)
    external_services = []
    # Add your external service health checks here
    
    # Overall health - system is healthy if all enabled services are connected
    is_healthy = True
    if settings.enable_caching and not cache_manager._connected:
        is_healthy = False
    if settings.enable_database and not database_status["connected"]:
        is_healthy = False
    
    health_data = {
        "status": "healthy" if is_healthy else "degraded",
        "version": settings.api.version,
        "environment": settings.environment,
        "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0,
        "cache": cache_status,
        "database": database_status,
        "external_services": external_services,
        "features": {
            "database": settings.enable_database,
            "caching": settings.enable_caching,
            **settings.features
        }
    }
    
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_data


# Set start time on startup
@app.on_event("startup")
async def set_start_time():
    app.state.start_time = time.time()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.logging_config.level.lower()
    )
