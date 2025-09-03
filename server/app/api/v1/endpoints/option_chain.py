"""
Option Chain API Endpoints

Provides real-time option chain data with the overnight options algorithm applied.
Supports SPY options with next-day expiration focused on call debit spreads.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Path, Query, HTTPException
from fastapi.responses import JSONResponse

from app.core.responses import create_success_response, create_error_response, ErrorCode
from app.core.logging import get_logger
from app.core.monitoring import monitor_performance, capture_errors
from app.core.auth import optional_user
from app.core.cache import redis_cache
from app.schemas.option_chain import (
    OptionChainResponse,
    OptionChainWithAlgorithm
)
from app.services.overnight_options_algorithm import get_overnight_options_algorithm
from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.external.base import ExternalAPIError


logger = get_logger(__name__)
router = APIRouter()


async def get_cached_option_chain(cache_key: str, fetch_func, ttl: int = 30):
    """Helper function to implement caching for option chain endpoints"""
    try:
        # Try to get cached data
        cached_data = redis_cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Option chain cache hit: {cache_key}")
            return cached_data
        
        # Fetch fresh data
        fresh_data = await fetch_func()
        
        # Cache the result
        redis_cache.set(cache_key, fresh_data, ttl)
        logger.info(f"Option chain cached: {cache_key} (TTL: {ttl}s)")
        
        return fresh_data
    except Exception as e:
        logger.error(f"Option chain cache operation failed for {cache_key}: {str(e)}")
        # Fallback to direct fetch if caching fails
        return await fetch_func()


@router.get(
    "/option-chain/{ticker}",
    response_model=OptionChainWithAlgorithm,
    summary="Get option chain with overnight algorithm",
    description="Get real-time option chain data with the overnight options algorithm applied for optimal spread identification",
    operation_id="get_option_chain_with_algorithm"
)
@monitor_performance("api.option_chain.get_with_algorithm")
@capture_errors(level="error")
async def get_option_chain(
    ticker: str = Path(
        ..., 
        description="Stock ticker symbol (supports SPY and SPX)", 
        regex="^(SPY|SPX)$"
    ),
    expiration_date: Optional[str] = Query(
        None,
        description="Option expiration date in YYYY-MM-DD format (defaults to next trading day)",
        regex="^\\d{4}-\\d{2}-\\d{2}$"
    ),
    max_cost: Optional[float] = Query(
        0.74,
        description="Maximum spread cost threshold (default: $0.74). SPY: $0.50-$2.00 for $1-wide spreads, SPX: $5.00-$50.00 for $10-wide spreads",
        ge=0.01,
        le=50.00
    ),
    current_user = Depends(optional_user)
) -> JSONResponse:
    """
    Get option chain with overnight algorithm applied
    
    Retrieves real-time option chain data and applies the sophisticated overnight options
    algorithm to identify optimal call debit spreads. The algorithm:
    
    1. Filters strikes below current underlying price (ITM bias)
    2. Calculates spread costs (SPY: $1-wide spreads, SPX: $10-wide spreads)
    3. Applies maximum cost filtering
    4. Selects deepest ITM spread (lowest sell strike)
    5. Highlights BUY and SELL options
    
    **Time Window**: Optimized for 3:00-4:00 PM ET trading window
    
    **Spread Cost Ranges**:
    - SPY: Typically $0.50-$2.00 for $1-wide spreads
    - SPX: Typically $5.00-$50.00 for $10-wide spreads (proportional to ~10x price scale)
    
    Args:
        ticker: Stock ticker (supports SPY and SPX)
        expiration_date: Option expiration date (optional, defaults to next trading day)
        max_cost: Maximum spread cost threshold in dollars (default: $0.74)
        
    Returns:
        JSONResponse with option chain data and algorithm results
        
    Raises:
        HTTPException: 400 for validation errors, 503 for API unavailable, 500 for server errors
    """
    try:
        logger.info(
            "Fetching option chain with algorithm",
            ticker=ticker.upper(),
            expiration_date=expiration_date,
            max_cost=max_cost,
            user_id=getattr(current_user, 'id', None) if current_user else None
        )
        
        # Get algorithm service with custom max cost threshold
        algorithm_service = get_overnight_options_algorithm(max_cost_threshold=max_cost)
        
        # Create cache key based on parameters
        cache_key = f"option_chain_algorithm:{ticker.upper()}:{expiration_date or 'next_day'}:{max_cost}"
        
        # Use caching with 30-second TTL for real-time data
        option_chain_result = await get_cached_option_chain(
            cache_key,
            lambda: algorithm_service.run_algorithm(
                ticker=ticker.upper(),
                expiration_date=expiration_date
            ),
            ttl=30
        )
        
        logger.info(
            "Option chain with algorithm retrieved successfully",
            ticker=ticker.upper(),
            expiration_date=option_chain_result.get("metadata", {}).get("expiration_date"),
            total_contracts=option_chain_result.get("metadata", {}).get("total_contracts", 0),
            algorithm_applied=option_chain_result.get("metadata", {}).get("algorithm_applied", False),
            optimal_spread_found=option_chain_result.get("algorithm_result", {}).get("selected_spread") is not None
        )
        
        return create_success_response(
            data=option_chain_result,
            message=option_chain_result.get("message", "Option chain retrieved successfully")
        )
        
    except ExternalAPIError as e:
        logger.error("External API error fetching option chain", ticker=ticker, error=str(e))
        return create_error_response(
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            message="Option chain data temporarily unavailable",
            status_code=503,
            error_details={
                "service": "TheTradeList API",
                "ticker": ticker.upper()
            }
        )
    except ValueError as e:
        logger.error("Validation error in option chain request", ticker=ticker, error=str(e))
        return create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"Invalid request parameters: {str(e)}",
            status_code=400,
            error_details={
                "ticker": ticker,
                "expiration_date": expiration_date,
                "max_cost": max_cost
            }
        )
    except Exception as e:
        logger.error("Failed to fetch option chain", ticker=ticker, error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to retrieve option chain for {ticker}",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )


@router.get(
    "/option-chain/{ticker}/raw",
    response_model=OptionChainResponse,
    summary="Get raw option chain without algorithm",
    description="Get raw option chain data without the overnight algorithm applied (for debugging/analysis)",
    operation_id="get_raw_option_chain"
)
@monitor_performance("api.option_chain.get_raw")
@capture_errors(level="error")
async def get_raw_option_chain(
    ticker: str = Path(
        ..., 
        description="Stock ticker symbol (supports SPY and SPX)", 
        regex="^(SPY|SPX)$"
    ),
    expiration_date: Optional[str] = Query(
        None,
        description="Option expiration date in YYYY-MM-DD format (defaults to next trading day)",
        regex="^\\d{4}-\\d{2}-\\d{2}$"
    ),
    current_user = Depends(optional_user)
) -> JSONResponse:
    """
    Get raw option chain data without algorithm
    
    Retrieves real-time option chain data without applying the overnight options algorithm.
    Useful for debugging, analysis, or when you need unprocessed option data.
    
    Args:
        ticker: Stock ticker (supports SPY and SPX)
        expiration_date: Option expiration date (optional, defaults to next trading day)
        
    Returns:
        JSONResponse with raw option chain data
        
    Raises:
        HTTPException: 400 for validation errors, 503 for API unavailable, 500 for server errors
    """
    try:
        logger.info(
            "Fetching raw option chain",
            ticker=ticker.upper(),
            expiration_date=expiration_date,
            user_id=getattr(current_user, 'id', None) if current_user else None
        )
        
        # Get TheTradeList service
        tradelist_service = get_thetradelist_service()
        
        # Create cache key for raw data
        cache_key = f"raw_option_chain:{ticker.upper()}:{expiration_date or 'next_day'}"
        
        # Use caching with 30-second TTL
        option_chain_data = await get_cached_option_chain(
            cache_key,
            lambda: tradelist_service.build_option_chain_with_pricing(
                ticker=ticker.upper(),
                expiration_date=expiration_date
            ),
            ttl=30
        )
        
        # Get current underlying price for metadata
        underlying_price_data = await tradelist_service.get_stock_price(ticker.upper())
        current_price = float(underlying_price_data.get("price", 0))
        
        # Format response to match expected schema
        contracts = option_chain_data.get("contracts", [])
        formatted_contracts = []
        
        for contract in contracts:
            formatted_contract = {
                "strike": float(contract.get("strike", 0)),
                "bid": float(contract.get("bid", 0)),
                "ask": float(contract.get("ask", 0)),
                "volume": int(contract.get("volume", 0)),
                "openInterest": int(contract.get("open_interest", 0)),
                "impliedVolatility": contract.get("implied_volatility") if contract.get("implied_volatility") is not None else None,
                "isHighlighted": None  # No highlighting for raw data
            }
            formatted_contracts.append(formatted_contract)
        
        result = {
            "success": True,
            "data": formatted_contracts,
            "metadata": {
                "ticker": ticker.upper(),
                "expiration_date": option_chain_data.get("expiration_date"),
                "current_price": current_price,
                "total_contracts": len(formatted_contracts),
                "algorithm_applied": False,
                "max_cost_threshold": 0.0,  # N/A for raw data
                "timestamp": option_chain_data.get("timestamp")
            },
            "message": f"Raw option chain for {ticker.upper()} retrieved successfully"
        }
        
        logger.info(
            "Raw option chain retrieved successfully",
            ticker=ticker.upper(),
            expiration_date=result["metadata"]["expiration_date"],
            total_contracts=len(formatted_contracts)
        )
        
        return create_success_response(
            data=result,
            message=result["message"]
        )
        
    except ExternalAPIError as e:
        logger.error("External API error fetching raw option chain", ticker=ticker, error=str(e))
        return create_error_response(
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            message="Option chain data temporarily unavailable",
            status_code=503,
            error_details={
                "service": "TheTradeList API",
                "ticker": ticker.upper()
            }
        )
    except Exception as e:
        logger.error("Failed to fetch raw option chain", ticker=ticker, error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to retrieve raw option chain for {ticker}",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )


@router.get(
    "/algorithm/health",
    summary="Check overnight algorithm health",
    description="Health check for the overnight options algorithm and its dependencies",
    operation_id="get_algorithm_health"
)
@monitor_performance("api.option_chain.algorithm_health")
async def get_algorithm_health() -> JSONResponse:
    """
    Health check for the overnight options algorithm
    
    Checks the health of:
    - TheTradeList API connectivity
    - Algorithm service initialization
    - Cache connectivity
    
    Returns:
        JSONResponse with health status
    """
    try:
        logger.info("Checking algorithm health")
        
        # Get services
        tradelist_service = get_thetradelist_service()
        algorithm_service = get_overnight_options_algorithm()
        
        # Test API connectivity
        api_health = await tradelist_service.health_check()
        
        # Test basic algorithm components
        try:
            next_expiration = await tradelist_service.get_next_trading_day_expiration("SPY")
            algorithm_ready = True
        except Exception as e:
            logger.warning("Algorithm initialization test failed", error=str(e))
            algorithm_ready = False
        
        # Test cache
        cache_healthy = True
        try:
            test_key = "health_check_test"
            redis_cache.set(test_key, "test", ttl=5)
            cached_value = redis_cache.get(test_key)
            if cached_value != "test":
                cache_healthy = False
        except Exception as e:
            logger.warning("Cache health check failed", error=str(e))
            cache_healthy = False
        
        overall_status = "healthy" if (
            api_health.get("status") == "healthy" and 
            algorithm_ready and 
            cache_healthy
        ) else "unhealthy"
        
        health_data = {
            "status": overall_status,
            "algorithm": {
                "status": "healthy" if algorithm_ready else "unhealthy",
                "max_cost_threshold": algorithm_service.max_cost_threshold,
                "next_expiration": next_expiration if algorithm_ready else None
            },
            "api": api_health,
            "cache": {
                "status": "healthy" if cache_healthy else "unhealthy"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info(
            "Algorithm health check completed",
            status=overall_status,
            api_healthy=api_health.get("status") == "healthy",
            algorithm_ready=algorithm_ready,
            cache_healthy=cache_healthy
        )
        
        status_code = 200 if overall_status == "healthy" else 503
        
        return create_success_response(
            data=health_data,
            message="Algorithm health check completed",
            status_code=status_code
        )
        
    except Exception as e:
        logger.error("Failed to perform algorithm health check", error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Failed to perform algorithm health check",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )