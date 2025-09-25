from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.responses import create_success_response, create_error_response, ErrorCode
from app.core.logging import get_logger
from app.core.monitoring import monitor_performance, capture_errors
from app.schemas.market_status import MarketStatusResponse
from app.services.market_status_service import MarketStatusService


logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/status",
    response_model=MarketStatusResponse,
    summary="Get market session status",
    description="Get current overnight options trading session status with dynamic Eastern Time calculation",
    operation_id="get_market_status"
)
@monitor_performance("api.market_status")
@capture_errors(level="error")
async def get_market_status() -> JSONResponse:
    """
    Get current market session status with calculated ET times
    
    This endpoint provides real-time information about the overnight options trading session:
    - Session activity status (3:00 PM - 4:00 PM ET)
    - Current Eastern Time (calculated from UTC, handles DST automatically)
    - Session start/end times in UTC
    - Next active session time if not currently active
    
    All Eastern Time calculations are performed dynamically from UTC without relying
    on system timezone, ensuring accuracy regardless of server location.
    
    Returns:
        JSONResponse with market status data
        
    Raises:
        HTTPException: 500 if time calculations fail
    """
    try:
        logger.info("Calculating market status")
        
        # Calculate market session status
        session_data = MarketStatusService.calculate_market_session()
        
        logger.info(
            "Market status calculated successfully",
            is_live=session_data["is_live"],
            current_time_et=session_data["current_time_et"]
        )
        
        return create_success_response(
            data=session_data,
            message="Market status retrieved successfully",
            metadata={
                "calculation_source": "dynamic_utc_conversion",
                "dst_aware": True
            }
        )
        
    except ValueError as e:
        # Time calculation errors
        logger.error("Time calculation failed", error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Failed to calculate market session times",
            status_code=500,
            error_details={
                "error_type": "time_calculation_error",
                "details": str(e)
            }
        )
        
    except Exception as e:
        # Unexpected errors
        logger.error("Unexpected error in market status calculation", error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred while retrieving market status",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )