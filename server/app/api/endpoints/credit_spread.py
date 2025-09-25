"""
Credit Spread Analysis API Endpoint
Provides trend-based credit spread analysis with exact response format from CashFlowAgent-Scanner-1
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.core.auth import conditional_jwt_token
from app.core.security import JWTPayload
from app.core.cache import credit_spread_cache
from app.services.credit_spread_scanner import CreditSpreadScanner
from app.services.tradelist.client import TradeListClient
from app.services.tradelist.stock_price_fetcher import get_current_price_from_api

logger = logging.getLogger(__name__)

router = APIRouter()


class CreditSpreadRequest(BaseModel):
    """Request model for credit spread analysis"""
    ticker: str
    trend: str  # "uptrend" or "downtrend"


class CreditSpreadResponse(BaseModel):
    """Response model for credit spread analysis"""
    success: bool
    ticker: str
    current_stock_price: float
    trend: str
    spread_analysis: Optional[Dict[str, Any]]
    market_context: Dict[str, Any]
    timestamp: str
    message: Optional[str] = None


@router.post("/analyze-credit-spread", response_model=CreditSpreadResponse)
async def analyze_credit_spread(
    request: CreditSpreadRequest,
    current_user: Optional[JWTPayload] = Depends(conditional_jwt_token)
):
    """
    Analyze credit spreads for a given ticker symbol with trend-based logic
    
    Request Body:
    {
        "ticker": "AAPL",
        "trend": "uptrend"  // or "downtrend"
    }
    
    Returns comprehensive credit spread analysis with:
    - Trend-based strategy selection (uptrend=puts, downtrend=calls)
    - 7-15% ROI target range
    - Safety-first strike selection
    - Price scenario analysis
    - 60-second result caching
    """
    try:
        # Validate input
        ticker = request.ticker.upper()
        trend = request.trend.lower()
        
        if trend not in ['uptrend', 'downtrend']:
            raise HTTPException(
                status_code=400,
                detail='Invalid trend. Must be "uptrend" or "downtrend"'
            )
        
        logger.info(f"Analyzing credit spreads for {ticker} in {trend}")
        
        # Check cache first (60-second TTL)
        cached_result = credit_spread_cache.get_spread_result(ticker, trend)
        if cached_result:
            logger.info(f"Returning cached result for {ticker} {trend}")
            return CreditSpreadResponse(**cached_result)
        
        # Get current stock price using the same method as CashFlowAgent-Scanner-1
        logger.info(f"Attempting to fetch price for {ticker} using range-data API")
        current_price = await get_current_price_from_api(ticker)
        
        if not current_price:
            logger.warning(f"range-data API failed for {ticker}, trying fallback method")
            # Fallback to original method if new one fails
            tradelist_client = TradeListClient()
            current_price = await tradelist_client.get_stock_price(ticker)
            
            if not current_price:
                logger.error(f"Both methods failed to fetch price for {ticker}")
                raise HTTPException(
                    status_code=404,
                    detail=f'Unable to fetch current price for {ticker} from TheTradeList API'
                )
        
        # Initialize scanner and analyze
        scanner = CreditSpreadScanner()
        spread_result = await scanner.find_best_credit_spread(
            ticker, 
            current_price, 
            trend
        )
        
        # Build response based on result
        if spread_result and spread_result.get('found'):
            # Successful spread found
            response_data = {
                'success': True,
                'ticker': ticker,
                'current_stock_price': current_price,
                'trend': trend,
                'spread_analysis': spread_result,
                'market_context': {
                    'analysis_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'data_source': 'TheTradeList API',
                    'api_calls_used': spread_result.get('quote_calls_used', 0),
                    'safety_first_approach': True,
                    'cache_hit': False
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(
                f"Successfully found {trend} credit spread for {ticker}: "
                f"{spread_result.get('roi_percent', 0):.1f}% ROI"
            )
            
            # Cache the successful result
            credit_spread_cache.set_spread_result(ticker, trend, response_data)
            
        else:
            # No spread found
            response_data = {
                'success': True,
                'ticker': ticker,
                'current_stock_price': current_price,
                'trend': trend,
                'spread_analysis': None,
                'message': spread_result.get('reason', 'No viable credit spreads found'),
                'market_context': {
                    'analysis_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'data_source': 'TheTradeList API',
                    'safety_criteria': '7-15% ROI, minimum 3 DTE',
                    'api_calls_used': spread_result.get('quote_calls_used', 0),
                    'cache_hit': False
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(
                f"No {trend} credit spread found for {ticker}: "
                f"{spread_result.get('reason', 'Unknown')}"
            )
            
            # Cache the "no spread" result too
            credit_spread_cache.set_spread_result(ticker, trend, response_data)
        
        return CreditSpreadResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing credit spreads: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f'Internal server error: {str(e)}'
        )


@router.get("/credit-spread-status")
async def credit_spread_status():
    """
    Get credit spread scanner status and configuration
    """
    return {
        'status': 'operational',
        'version': '1.0.0',
        'configuration': {
            'cache_ttl_seconds': 60,
            'roi_target_range': '7-15%',
            'minimum_dte': 3,
            'maximum_spread_width': 10,
            'strategies': {
                'uptrend': 'Put credit spreads (sell puts below current price)',
                'downtrend': 'Call credit spreads (sell calls above current price)'
            },
            'safety_thresholds': {
                'uptrend': '95% of current price (5% below)',
                'downtrend': '105% of current price (5% above)'
            }
        },
        'data_source': 'TheTradeList API',
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/clear-spread-cache")
async def clear_spread_cache(
    ticker: Optional[str] = None,
    current_user: Optional[JWTPayload] = Depends(conditional_jwt_token)
):
    """
    Clear credit spread cache
    - If ticker provided, clear only that ticker's cache
    - Otherwise clear all credit spread cache
    """
    try:
        if ticker:
            deleted = credit_spread_cache.invalidate_ticker(ticker.upper())
            message = f"Cleared {deleted} cache entries for {ticker.upper()}"
        else:
            deleted = credit_spread_cache.clear_all()
            message = f"Cleared all {deleted} credit spread cache entries"
        
        logger.info(message)
        
        return {
            'success': True,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f'Failed to clear cache: {str(e)}'
        )