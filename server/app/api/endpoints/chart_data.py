"""
Chart Data API Endpoint
Provides historical price data for candlestick charts
Matches the exact data format expected by BreakevenChart.tsx
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.core.auth import conditional_jwt_token
from app.core.security import JWTPayload
from app.services.tradelist.client import TradeListClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/chart-data/{symbol}")
async def get_chart_data(
    symbol: str,
    current_user: Optional[JWTPayload] = Depends(conditional_jwt_token)
):
    """
    Get historical price data for charting
    
    Returns candlestick data in the format expected by BreakevenChart.tsx:
    - Last 30 days of OHLC data
    - Basic stock information
    - Formatted for ApexCharts candlestick chart
    
    Response format matches frontend StockData interface:
    {
        "symbol": "TSLA",
        "name": "Tesla Inc",
        "price": 331.21,
        "priceData": [
            {
                "x": "2025-01-15T00:00:00Z",
                "y": [open, high, low, close]
            },
            ...
        ],
        ...
    }
    """
    try:
        symbol = symbol.upper()
        logger.info(f"Fetching chart data for {symbol}")
        
        # Initialize TradeList client
        client = TradeListClient()
        
        # Fetch historical price data using range-data endpoint
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Get 30 days of data
        
        # Use the range-data endpoint (same as stock price fetcher)
        import aiohttp
        import os
        
        api_key = os.environ.get('TRADELIST_API_KEY', '5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5')
        
        url = "https://api.thetradelist.com/v1/data/range-data"
        params = {
            'ticker': symbol,
            'range': '1/day',
            'startdate': start_date.strftime('%Y-%m-%d'),
            'enddate': end_date.strftime('%Y-%m-%d'),
            'limit': 50,  # Get more days to ensure we have enough trading days
            'apiKey': api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"TheTradeList API error: {response.status} - {error_text}")
                    raise HTTPException(
                        status_code=503,
                        detail=f"Failed to fetch price data for {symbol}"
                    )
                
                data = await response.json()
                results = data.get('results', [])
                
                if not results:
                    logger.warning(f"No price data found for {symbol}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"No price data available for {symbol}"
                    )
                
                # Convert to candlestick format expected by frontend
                price_data = []
                latest_price = 0
                latest_open = 0
                latest_high = 0
                latest_low = 0
                latest_volume = 0
                
                for day_data in results:
                    # Each result has: t (timestamp), o (open), h (high), l (low), c (close), v (volume)
                    timestamp = day_data.get('t')
                    if timestamp:
                        # Convert milliseconds timestamp to datetime
                        date = datetime.fromtimestamp(timestamp / 1000)
                        
                        open_price = float(day_data.get('o', 0))
                        high_price = float(day_data.get('h', 0))
                        low_price = float(day_data.get('l', 0))
                        close_price = float(day_data.get('c', 0))
                        volume = int(day_data.get('v', 0))
                        
                        # Update latest values from most recent data
                        if not latest_price and close_price > 0:
                            latest_price = close_price
                            latest_open = open_price
                            latest_high = high_price
                            latest_low = low_price
                            latest_volume = volume
                        
                        # Format for ApexCharts candlestick
                        price_data.append({
                            "x": date.isoformat() + "Z",  # ISO format with Z suffix
                            "y": [open_price, high_price, low_price, close_price]
                        })
                
                # Sort by date (oldest first)
                price_data.sort(key=lambda x: x['x'])
                
                # If we have data, use the most recent values
                if price_data:
                    last_candle = price_data[-1]
                    latest_price = last_candle['y'][3]  # Close price
                    latest_high = max(candle['y'][1] for candle in price_data[-5:])  # 5-day high
                    latest_low = min(candle['y'][2] for candle in price_data[-5:])  # 5-day low
                
                # Calculate change from previous close
                change = 0
                change_percent = 0
                if len(price_data) >= 2:
                    prev_close = price_data[-2]['y'][3]
                    if prev_close > 0:
                        change = latest_price - prev_close
                        change_percent = (change / prev_close) * 100
                
                # Determine trend based on recent price action
                trend_type = 'neutral'
                trend_strength = 50
                if len(price_data) >= 5:
                    # Simple trend detection: compare current price to 5-day average
                    five_day_avg = sum(candle['y'][3] for candle in price_data[-5:]) / 5
                    if latest_price > five_day_avg * 1.02:
                        trend_type = 'uptrend'
                        trend_strength = min(80, 50 + (latest_price - five_day_avg) / five_day_avg * 100)
                    elif latest_price < five_day_avg * 0.98:
                        trend_type = 'downtrend'
                        trend_strength = min(80, 50 + (five_day_avg - latest_price) / five_day_avg * 100)
                
                # Build response matching frontend StockData interface
                response_data = {
                    "symbol": symbol,
                    "name": f"{symbol} Inc",  # Simplified name
                    "description": f"Stock chart data for {symbol}",
                    "price": round(latest_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "open": round(latest_open, 2),
                    "high": round(latest_high, 2),
                    "low": round(latest_low, 2),
                    "volume": latest_volume,
                    "yearRange": f"${round(latest_low, 2)} - ${round(latest_high, 2)}",
                    "updated": datetime.now().isoformat(),
                    "trendType": trend_type,
                    "trendStrength": round(trend_strength, 0),
                    "priceData": price_data
                }
                
                logger.info(f"Successfully fetched {len(price_data)} days of chart data for {symbol}")
                return response_data
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error fetching chart data: {str(e)}"
        )


@router.get("/stocks/{symbol}")
async def get_stock_chart_data(
    symbol: str,
    current_user: Optional[JWTPayload] = Depends(conditional_jwt_token)
):
    """
    Alternative endpoint path to match frontend expectations
    Redirects to the main chart-data endpoint
    """
    return await get_chart_data(symbol, current_user)