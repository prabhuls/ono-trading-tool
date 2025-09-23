from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, HTTPException
from fastapi.responses import JSONResponse

from app.core.responses import create_success_response, create_error_response, ErrorCode
from app.core.logging import get_logger
from app.core.monitoring import monitor_performance, capture_errors
from app.core.auth import optional_user
from app.core.cache import redis_cache
from app.schemas.market_data import (
    MarketSidebarStatusResponse,
    EnhancedMarketStatusResponse,
    MarketHealthResponse,
    SingleStockPriceResponse,
    MultipleStockPricesResponse,
    IntradayChartResponse
)
from app.services.market_status_enhanced_service import get_market_status_enhanced_service
from app.services.external.thetradelist_service import get_thetradelist_service, TheTradeListService
from app.services.external.base import ExternalAPIError


logger = get_logger(__name__)
router = APIRouter()


async def get_cached_or_fetch(cache_key: str, fetch_func, ttl: int = 30):
    """Helper function to implement caching for stock price endpoints"""
    try:
        # Try to get cached data
        cached_data = redis_cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Cache hit: {cache_key}")
            return cached_data
        
        # Fetch fresh data
        fresh_data = await fetch_func()
        
        # Cache the result
        redis_cache.set(cache_key, fresh_data, ttl)
        logger.info(f"Cache set: {cache_key} (TTL: {ttl}s)")
        
        return fresh_data
    except Exception as e:
        logger.error(f"Cache operation failed for {cache_key}: {str(e)}")
        # Fallback to direct fetch if caching fails
        return await fetch_func()


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


@router.get(
    "/current-price/{ticker}",
    response_model=SingleStockPriceResponse,
    summary="Get current price for a single stock ticker",
    description="Get real-time price data for a single stock ticker (SPY, XSP, SPX)",
    operation_id="get_current_stock_price"
)
@monitor_performance("api.market_data.current_price")
@capture_errors(level="error")
async def get_current_price(
    ticker: str = Path(..., description="Stock ticker symbol (SPY, XSP, SPX)", regex="^(SPY|XSP|SPX)$"),
    current_user = Depends(optional_user)
) -> JSONResponse:
    """
    Get current price for a single stock ticker
    
    Retrieves real-time price data including:
    - Current price
    - Price change from previous close
    - Percentage change
    - Timestamp of data retrieval
    
    Supports the following tickers: SPY, XSP, SPX
    Data is cached for 30 seconds for optimal performance.
    
    Args:
        ticker: Stock ticker symbol (SPY, XSP, or SPX)
        
    Returns:
        JSONResponse with current stock price data
        
    Raises:
        HTTPException: 400 for invalid ticker, 503 for API unavailable, 500 for server errors
    """
    try:
        logger.info(
            "Fetching current stock price",
            ticker=ticker.upper(),
            user_id=getattr(current_user, 'id', None) if current_user else None
        )
        
        # Get TheTradeList service
        tradelist_service = get_thetradelist_service()
        
        # Use caching for stock price data
        cache_key = f"stock_price:{ticker.upper()}"
        price_data = await get_cached_or_fetch(
            cache_key,
            lambda: tradelist_service.get_stock_price(ticker),
            ttl=TheTradeListService.CACHE_TTL_DYNAMIC
        )
        
        logger.info(
            "Stock price retrieved successfully",
            ticker=ticker.upper(),
            price=price_data["price"],
            change=price_data["change"]
        )
        
        return create_success_response(
            data=price_data,
            message=f"Current price for {ticker.upper()} retrieved successfully"
        )
        
    except ExternalAPIError as e:
        logger.error("External API error fetching stock price", ticker=ticker, error=str(e))
        if "not supported" in str(e).lower():
            return create_error_response(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Ticker {ticker} is not supported",
                status_code=400,
                error_details={"supported_tickers": ["SPY", "XSP", "SPX"]}
            )
        else:
            return create_error_response(
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                message="Stock price data temporarily unavailable",
                status_code=503,
                error_details={"service": "TheTradeList API"}
            )
    except Exception as e:
        logger.error("Failed to fetch stock price", ticker=ticker, error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to retrieve price for {ticker}",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )


@router.get(
    "/current-prices",
    response_model=MultipleStockPricesResponse,
    summary="Get current prices for multiple stock tickers",
    description="Get real-time price data for multiple stock tickers (SPY, XSP, SPX)",
    operation_id="get_current_stock_prices"
)
@monitor_performance("api.market_data.current_prices")
@capture_errors(level="error")
async def get_current_prices(
    tickers: List[str] = Query(..., description="Comma-separated list of stock ticker symbols", example=["SPY", "XSP", "SPX"]),
    current_user = Depends(optional_user)
) -> JSONResponse:
    """
    Get current prices for multiple stock tickers
    
    Retrieves real-time price data for multiple tickers including:
    - Current price for each ticker
    - Price change from previous close
    - Percentage change
    - Timestamp of data retrieval
    
    Supports the following tickers: SPY, XSP, SPX
    Data is cached for 30 seconds for optimal performance.
    
    Args:
        tickers: List of stock ticker symbols (SPY, XSP, SPX)
        
    Returns:
        JSONResponse with current stock prices data
        
    Raises:
        HTTPException: 400 for invalid tickers, 503 for API unavailable, 500 for server errors
    """
    try:
        logger.info(
            "Fetching multiple stock prices",
            tickers=tickers,
            user_id=getattr(current_user, 'id', None) if current_user else None
        )
        
        # Validate input
        if not tickers:
            return create_error_response(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="At least one ticker must be provided",
                status_code=400
            )
        
        # Get TheTradeList service
        tradelist_service = get_thetradelist_service()
        
        # Use caching for stock prices data
        cache_key = f"stock_prices:{'_'.join(sorted([t.upper() for t in tickers]))}"
        prices_data = await get_cached_or_fetch(
            cache_key,
            lambda: tradelist_service.get_multiple_stock_prices(tickers),
            ttl=TheTradeListService.CACHE_TTL_DYNAMIC
        )
        
        logger.info(
            "Multiple stock prices retrieved successfully",
            tickers=tickers,
            count=len(prices_data.get("prices", []))
        )
        
        return create_success_response(
            data=prices_data,
            message=f"Current prices for {len(tickers)} tickers retrieved successfully"
        )
        
    except ExternalAPIError as e:
        logger.error("External API error fetching stock prices", tickers=tickers, error=str(e))
        if "unsupported" in str(e).lower():
            return create_error_response(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="One or more tickers are not supported",
                status_code=400,
                error_details={
                    "supported_tickers": ["SPY", "XSP", "SPX"],
                    "error": str(e)
                }
            )
        else:
            return create_error_response(
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                message="Stock price data temporarily unavailable",
                status_code=503,
                error_details={"service": "TheTradeList API"}
            )
    except Exception as e:
        logger.error("Failed to fetch stock prices", tickers=tickers, error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Failed to retrieve stock prices",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )


@router.get(
    "/spy-price",
    response_model=SingleStockPriceResponse,
    summary="Get current SPY price",
    description="Get real-time price data specifically for SPY ticker (optimized for trading algorithm)",
    operation_id="get_spy_price"
)
@monitor_performance("api.market_data.spy_price")
@capture_errors(level="error")
async def get_spy_price(
    current_user = Depends(optional_user)
) -> JSONResponse:
    """
    Get current SPY price (dedicated endpoint for the trading algorithm)
    
    Optimized endpoint specifically for SPY price retrieval, commonly used
    by the trading algorithm for quick decision making.
    
    Retrieves real-time SPY price data including:
    - Current SPY price
    - Price change from previous close
    - Percentage change
    - Timestamp of data retrieval
    
    Data is cached for 30 seconds for optimal performance.
    
    Returns:
        JSONResponse with current SPY price data
        
    Raises:
        HTTPException: 503 for API unavailable, 500 for server errors
    """
    try:
        logger.info(
            "Fetching SPY price",
            user_id=getattr(current_user, 'id', None) if current_user else None
        )
        
        # Get TheTradeList service
        tradelist_service = get_thetradelist_service()
        
        # Use caching for SPY price data
        cache_key = "stock_price:SPY"
        price_data = await get_cached_or_fetch(
            cache_key,
            lambda: tradelist_service.get_stock_price("SPY"),
            ttl=TheTradeListService.CACHE_TTL_DYNAMIC
        )
        
        logger.info(
            "SPY price retrieved successfully",
            price=price_data["price"],
            change=price_data["change"]
        )
        
        return create_success_response(
            data=price_data,
            message="SPY price retrieved successfully"
        )
        
    except ExternalAPIError as e:
        logger.error("External API error fetching SPY price", error=str(e))
        return create_error_response(
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            message="SPY price data temporarily unavailable",
            status_code=503,
            error_details={"service": "TheTradeList API"}
        )
    except Exception as e:
        logger.error("Failed to fetch SPY price", error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Failed to retrieve SPY price",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )


@router.get(
    "/intraday/{ticker}",
    response_model=IntradayChartResponse,
    summary="Get intraday chart data for a ticker",
    description="Get real-time intraday OHLCV data for chart display with optional benchmark strikes",
    operation_id="get_intraday_chart_data"
)
@monitor_performance("api.market_data.intraday_chart")
@capture_errors(level="error")
async def get_intraday_chart_data(
    ticker: str = Path(..., description="Stock ticker symbol (SPY, XSP, SPX)", regex="^(SPY|XSP|SPX)$"),
    interval: str = Query("5m", description="Time interval", regex="^(1m|5m|15m|30m|1h)$"),
    period: str = Query("1d", description="Time period", regex="^(1d|5d|1w)$"),
    buy_strike: Optional[float] = Query(None, description="Buy strike price for benchmark line", ge=0),
    sell_strike: Optional[float] = Query(None, description="Sell strike price for benchmark line", ge=0),
    current_user = Depends(optional_user)
) -> JSONResponse:
    """
    Get intraday chart data for SPY panel with real market data
    
    Retrieves OHLCV intraday data for chart visualization including:
    - Price candles with open, high, low, close, volume
    - Current market price 
    - Optional benchmark strike lines
    - Market hours metadata
    
    Supports different time intervals (1m, 5m, 15m, 30m, 1h) and periods (1d, 5d, 1w).
    
    Note: SPY and SPX now use ISIN endpoint with true 1-minute data. XSP uses range-data endpoint.
    Data is cached for 60-120 seconds for real-time feel while managing API limits.
    
    Args:
        ticker: Stock ticker symbol (SPY, XSP, SPX)
        interval: Time interval between data points (default: "5m")
        period: Time period for historical data (default: "1d")  
        buy_strike: Optional buy strike price for benchmark line
        sell_strike: Optional sell strike price for benchmark line
        
    Returns:
        JSONResponse with intraday chart data including OHLCV candles and benchmark lines
        
    Raises:
        HTTPException: 400 for invalid ticker/params, 503 for API unavailable, 500 for server errors
    """
    try:
        logger.info(
            "Fetching intraday chart data",
            ticker=ticker.upper(),
            interval=interval,
            period=period,
            buy_strike=buy_strike,
            sell_strike=sell_strike,
            user_id=getattr(current_user, 'id', None) if current_user else None
        )
        
        # Get TheTradeList service
        tradelist_service = get_thetradelist_service()
        
        # Create cache key including benchmark strikes
        strikes_key = f"{buy_strike or 'none'}:{sell_strike or 'none'}"
        cache_key = f"intraday_chart:{ticker.upper()}:{interval}:{period}:{strikes_key}"
        
        # Check cache first
        cached_data = redis_cache.get(cache_key)
        if cached_data is not None:
            logger.info("Using cached intraday chart data", ticker=ticker.upper(), interval=interval, period=period)
            
            return create_success_response(
                data=cached_data,
                message=f"Intraday chart data for {ticker.upper()} retrieved successfully (cached)"
            )
        
        # Fetch fresh intraday data
        chart_data = await tradelist_service.get_intraday_data(
            ticker=ticker,
            interval=interval,
            period=period
        )
        
        # Add benchmark strikes if provided
        if buy_strike is not None:
            chart_data["benchmark_lines"]["buy_strike"] = float(buy_strike)
        if sell_strike is not None:
            chart_data["benchmark_lines"]["sell_strike"] = float(sell_strike)
        
        # Cache the result for 90 seconds (real-time feel)
        redis_cache.set(cache_key, chart_data, ttl=90)
        
        logger.info(
            "Intraday chart data retrieved successfully",
            ticker=ticker.upper(),
            interval=interval,
            period=period,
            data_points=len(chart_data.get("price_data", [])),
            current_price=chart_data.get("current_price", 0),
            buy_strike=buy_strike,
            sell_strike=sell_strike
        )
        
        return create_success_response(
            data=chart_data,
            message=f"Intraday chart data for {ticker.upper()} retrieved successfully"
        )
        
    except ExternalAPIError as e:
        logger.error("External API error fetching intraday chart data", ticker=ticker, error=str(e))
        if "not supported" in str(e).lower():
            return create_error_response(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Ticker {ticker} is not supported for intraday data",
                status_code=400,
                error_details={"supported_tickers": ["SPY", "XSP", "SPX"]}
            )
        else:
            return create_error_response(
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                message="Intraday chart data temporarily unavailable",
                status_code=503,
                error_details={"service": "TheTradeList API"}
            )
    except Exception as e:
        logger.error("Failed to fetch intraday chart data", ticker=ticker, error=str(e))
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to retrieve intraday chart data for {ticker}",
            status_code=500,
            error_details={
                "error_type": type(e).__name__,
                "details": str(e)
            }
        )