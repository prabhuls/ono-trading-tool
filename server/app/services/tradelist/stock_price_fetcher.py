"""
Stock price fetcher using TheTradeList range-data API
Matches the exact implementation from CashFlowAgent-Scanner-1
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)


async def get_current_price_from_api(ticker: str) -> Optional[float]:
    """
    Get current stock price from TheTradeList range-data API
    Returns the most recent closing price
    
    This matches the exact implementation from CashFlowAgent-Scanner-1
    """
    try:
        api_key = os.environ.get('TRADELIST_API_KEY')
        if not api_key:
            logger.error("TRADELIST_API_KEY not found in environment variables")
            return None
        
        # Calculate date range - last 5 trading days to ensure we get recent data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Go back 7 days to ensure we catch recent trading days
        
        # Format dates for API
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Make API request to TheTradeList range-data endpoint
        url = "https://api.thetradelist.com/v1/data/range-data"
        params = {
            'ticker': ticker,
            'range': '1/day',
            'startdate': start_date_str,
            'enddate': end_date_str,
            'limit': 10,  # Only need the most recent few data points
            'apiKey': api_key
        }
        
        logger.info(f"Fetching current price for {ticker} from TheTradeList API")
        logger.debug(f"URL: {url}")
        logger.debug(f"Params: {params}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    
                    if results:
                        # Get the most recent data point (last item in results)
                        latest_data = results[-1]
                        current_price = latest_data.get('c')  # 'c' is the closing price
                        
                        if current_price:
                            logger.info(f"TheTradeList API SUCCESS: {ticker} current price = ${current_price}")
                            return float(current_price)
                        else:
                            logger.error(f"No closing price found in API response for {ticker}")
                            return None
                    else:
                        logger.error(f"No results in API response for {ticker}")
                        return None
                else:
                    text = await response.text()
                    logger.error(f"TheTradeList API error for {ticker}: {response.status} - {text}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error fetching price for {ticker} from TheTradeList API: {str(e)}")
        logger.exception(e)  # This will log the full traceback
        return None
    
    return None