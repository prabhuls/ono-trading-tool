from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.responses import create_success_response, create_error_response, ErrorCode
from app.core.logging import get_logger
from app.core.monitoring import monitor_performance, capture_errors
from app.core.auth import optional_user
from app.schemas.market_data import (
    MarketSidebarStatusResponse,
    EnhancedMarketStatusResponse,
    MarketHealthResponse
)
from app.services.market_status_enhanced_service import get_market_status_enhanced_service


logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/sidebar-status",
    response_model=MarketSidebarStatusResponse,
    summary="Get market status for sidebar component",
    description="Get basic market status data optimized for the frontend sidebar component",
    operation_id="get_market_sidebar_status"
)
@monitor_performance("api.market_data.sidebar_status")
@capture_errors(level="error")
async def get_market_sidebar_status(
    current_user = Depends(optional_user)
) -> JSONResponse:
    """
    Get market status data optimized for the sidebar component
    
    Returns basic market information including:
    - Current market session status (open/closed, session type)
    - Next options expiration date
    
    This endpoint is optimized for frequent polling by frontend components
    and includes caching for fast response times.
    
    Returns:
        JSONResponse with market sidebar status data
        
    Raises:
        HTTPException: 500 if data retrieval fails
    """
    try:
        logger.info(
            "Fetching market sidebar status",
            user_id=getattr(current_user, 'id', None) if current_user else None
        )
        
        # Get enhanced market status service
        market_service = get_market_status_enhanced_service()
        
        # Fetch sidebar status data
        sidebar_data = await market_service.get_sidebar_status_data()
        
        logger.info(
            "Market sidebar status retrieved successfully",
            is_open=sidebar_data["isOpen"],
            session=sidebar_data["market_session"],
            next_expiration=sidebar_data["next_expiration"]
        )
        
        return create_success_response(
            data=sidebar_data,
            message="Market sidebar status retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve market sidebar status", error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Failed to retrieve market sidebar status",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )


@router.get(
    "/enhanced-status",
    response_model=EnhancedMarketStatusResponse,
    summary="Get enhanced market session status",
    description="Get detailed market session information with comprehensive timing data",
    operation_id="get_enhanced_market_status"
)
@monitor_performance("api.market_data.enhanced_status")
@capture_errors(level="error")
async def get_enhanced_market_status() -> JSONResponse:
    """
    Get enhanced market session status with detailed timing information
    
    Returns detailed market session data including:
    - Current session status and type
    - All session times in UTC
    - Holiday and weekend detection
    - Next options expiration
    - Eastern Time display
    
    Returns:
        JSONResponse with enhanced market status data
    """
    try:
        logger.info("Calculating enhanced market status")
        
        # Get enhanced market status service
        market_service = get_market_status_enhanced_service()
        
        # Calculate enhanced session data
        session_data = market_service.calculate_market_session()
        
        logger.info(
            "Enhanced market status calculated successfully",
            is_open=session_data["isOpen"],
            session=session_data["market_session"],
            is_holiday=session_data["is_holiday"]
        )
        
        return create_success_response(
            data=session_data,
            message="Enhanced market status retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to calculate enhanced market status", error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Failed to calculate enhanced market status",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )


@router.get(
    "/health",
    response_model=MarketHealthResponse,
    summary="Check market data services health",
    description="Check health status of market data services and dependencies",
    operation_id="get_market_health"
)
@monitor_performance("api.market_data.health")
async def get_market_health() -> JSONResponse:
    """
    Check health status of market data services
    
    Returns health status of:
    - Redis cache connectivity
    - Overall system health
    
    Returns:
        JSONResponse with health check results
    """
    try:
        logger.info("Checking market data services health")
        
        # Get enhanced market status service
        market_service = get_market_status_enhanced_service()
        
        # Perform health check
        health_data = await market_service.get_market_health()
        
        logger.info(
            "Market health check completed",
            status=health_data.get("status")
        )
        
        # Use appropriate status code based on health
        status_code = 200 if health_data.get("status") == "healthy" else 503
        
        return create_success_response(
            data=health_data,
            message="Market health check completed",
            status_code=status_code
        )
        
    except Exception as e:
        logger.error("Failed to perform market health check", error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Failed to perform health check",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )