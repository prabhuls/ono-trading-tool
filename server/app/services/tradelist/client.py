"""
TheTradeList API client
"""
import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import aiohttp
import json

logger = logging.getLogger(__name__)


class TradeListClient:
    """Client for TheTradeList API - Matches PHP implementation exactly"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Use the PHP API key for highs/lows and general data
        self.api_key = api_key or os.getenv("TRADELIST_API_KEY", "a599851f-e85e-4477-b6f5-ceb68850983c")
        self.base_url = "https://api.thetradelist.com/v1/data"
        # Different API key for options data (matches PHP)
        self.options_api_key = "5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _request(self, url: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Make async HTTP request to API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API request failed: {response.status} - {await response.text()}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return None
    
    async def get_highs_lows(self, extreme: str = "high", price: float = 15.0, volume: int = 500000) -> List[str]:
        """
        Fetch high or low stocks from API - Matches PHP exactly
        
        Args:
            extreme: "high" or "low"
            price: Minimum price threshold
            volume: Minimum volume threshold
            
        Returns:
            List of ticker symbols
        """
        # Match PHP URL structure exactly with trailing slash
        url = f"{self.base_url}/get_highs_lows.php/"
        params = {
            "price": f"{price:.2f}",  # Format as 15.00 like PHP
            "volume": str(volume),
            "extreme": extreme,
            "returntype": "csv",  # PHP uses CSV format
            "apiKey": self.api_key
        }
        
        logger.info(f"Fetching {extreme} stocks from TheTradeList")
        
        # Build full URL with params for CSV request
        full_url = f"{url}?price={params['price']}&volume={params['volume']}&extreme={params['extreme']}&returntype=csv&apiKey={params['apiKey']}"
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(full_url, timeout=30) as response:
                if response.status == 200:
                    csv_data = await response.text()
                    # Parse CSV data like PHP does
                    tickers = []
                    lines = csv_data.strip().split('\n')
                    if len(lines) > 1:  # Skip header
                        for line in lines[1:]:
                            line = line.strip()
                            if line:
                                # CSV format: symbol is first column
                                parts = line.split(',')
                                if parts and parts[0]:
                                    tickers.append(parts[0].strip())
                    
                    logger.info(f"Found {len(tickers)} {extreme} stocks")
                    return tickers
                else:
                    logger.error(f"API request failed: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return []
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get current quote for a symbol - ENDPOINT RETURNS 404"""
        # This endpoint returns 404 - keeping method for compatibility
        # Use get_historical_data instead for price data
        return None
    
    async def get_ohlcv(self, symbol: str) -> Optional[Dict]:
        """Get OHLCV data for a symbol - using Polygon endpoint only"""
        # Skip quote endpoint as it returns 404, use Polygon directly
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.base_url}/get_polygon.php/ticker/{symbol}/range/1/day/{today}/{today}"
        params = {
            "adjusted": "true",
            "sort": "desc",
            "limit": 1,
            "apiKey": self.api_key
        }
        
        response = await self._request(url, params)
        if response and "results" in response and response["results"]:
            result = response["results"][0]
            return {
                "open": float(result.get("o", 0)),
                "high": float(result.get("h", 0)),
                "low": float(result.get("l", 0)),
                "close": float(result.get("c", 0)),
                "volume": int(result.get("v", 0)),
                "adj_close": float(result.get("c", 0))
            }
        
        return None
    
    async def get_52week_stats(self, symbol: str) -> Optional[Dict]:
        """Get 52-week statistics for a symbol - skip failing endpoints"""
        # Skip quote and stock_info endpoints as they return 404
        # The market_scanner will calculate from historical data instead
        return None
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """Get stock info from API - ENDPOINT RETURNS 404"""
        # This endpoint returns 404 - keeping method for compatibility
        # Use get_historical_data instead for stock data
        return None
    
    async def get_options_data(self, symbol: str) -> Dict:
        """
        Get options analysis for a symbol
        
        Returns:
            Dict with options_expiring_10days and has_weeklies
        """
        url = f"{self.base_url}/options-contracts"
        params = {
            "underlying_ticker": symbol,
            "limit": 1000,
            "apiKey": self.options_api_key
        }
        
        response = await self._request(url, params)
        
        if not response:
            return {"options_expiring_10days": 0, "has_weeklies": False}
        
        # Extract contracts
        contracts = []
        if isinstance(response, dict):
            if "results" in response:
                contracts = response["results"]
            elif "contracts" in response:
                contracts = response["contracts"]
        elif isinstance(response, list):
            contracts = response
        
        if not contracts:
            return {"options_expiring_10days": 0, "has_weeklies": False}
        
        # Analyze expiration dates
        today = datetime.now().date()
        ten_days_from_now = today + timedelta(days=10)
        expiring_count = 0
        expiration_dates = set()
        
        for contract in contracts:
            if not isinstance(contract, dict):
                continue
            
            # Get expiration date
            exp_date_str = contract.get("expiration_date") or contract.get("expiration")
            if not exp_date_str:
                continue
            
            try:
                exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
                
                # Count if expiring within 10 days
                if today <= exp_date <= ten_days_from_now:
                    expiring_count += 1
                
                # Collect unique dates for weekly detection
                expiration_dates.add(exp_date)
                
            except (ValueError, TypeError):
                continue
        
        # Detect weekly options (4+ unique expiration dates in next 60 days)
        sixty_days_from_now = today + timedelta(days=60)
        near_term_dates = [d for d in expiration_dates if today <= d <= sixty_days_from_now]
        has_weeklies = len(near_term_dates) >= 4
        
        logger.info(f"Options analysis for {symbol}: {expiring_count} expiring in 10 days, has_weeklies={has_weeklies}")
        
        return {
            "options_expiring_10days": expiring_count,
            "has_weeklies": has_weeklies
        }
    
    async def get_historical_data(self, symbol: str, days: int = 365) -> Optional[List[Dict]]:
        """Get historical price data for a symbol - Matches PHP exactly"""
        # Match PHP date calculation
        today = datetime.now().strftime("%Y-%m-%d")
        year_ago = (datetime.now() - timedelta(days=days + 3)).strftime("%Y-%m-%d")  # PHP adds 3 extra days
        
        # Match PHP URL structure exactly
        url = f"{self.base_url}/get_polygon.php/ticker/{symbol}/range/1/day/{year_ago}/{today}"
        params = {
            "adjusted": "true",
            "sort": "desc",  # PHP uses desc
            "limit": "300",  # PHP uses 300
            "apiKey": self.api_key
        }
        
        # Build full URL like PHP
        full_url = f"{url}?adjusted={params['adjusted']}&sort={params['sort']}&limit={params['limit']}&apiKey={params['apiKey']}"
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(full_url, timeout=30) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    text = await response.text()
                    
                    # Check if we got JSON or HTML (ETFs often return HTML)
                    if 'json' in content_type or (text.strip().startswith('{') or text.strip().startswith('[')):
                        try:
                            data = json.loads(text)
                            # PHP checks for valid results
                            if data and "results" in data and data["results"]:
                                # PHP also checks resultsTicker matches
                                if "resultsTicker" in data and data["resultsTicker"].upper() != symbol.upper():
                                    logger.warning(f"Ticker mismatch: expected {symbol}, got {data['resultsTicker']}")
                                    return None
                                # Return raw results like PHP - don't transform
                                return data["results"]
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON response for {symbol}")
                            return None
                    else:
                        # Got HTML instead of JSON (common for ETFs)
                        logger.debug(f"Got HTML response for {symbol} (likely an ETF)")
                        return None
                else:
                    logger.debug(f"Historical data request failed for {symbol}: {response.status}")
        except Exception as e:
            logger.debug(f"Historical data error for {symbol}: {str(e)}")
        
        return None
    
    async def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price for a symbol"""
        quote = await self.get_quote(symbol)
        if quote:
            return quote.get("price")
        return None
    
    async def get_options_contracts(self, symbol: str, limit: int = 1000) -> List[Dict]:
        """Get options contracts for a symbol - Matches PHP exactly"""
        # PHP uses this exact URL structure
        url = f"{self.base_url}/options-contracts"
        params = {
            "underlying_ticker": symbol,
            "limit": str(limit),
            "apiKey": self.options_api_key  # PHP uses different key for options
        }
        
        # Build full URL like PHP
        full_url = f"{url}?underlying_ticker={params['underlying_ticker']}&limit={params['limit']}&apiKey={params['apiKey']}"
        
        logger.info(f"Fetching options contracts for {symbol}")
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(full_url, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Options request failed: {response.status}")
                    return []
                    
                response = await response.json()
        except Exception as e:
            logger.error(f"Options error: {str(e)}")
            return []
        
        if not response:
            return []
        
        # Extract contracts from various response formats - matches PHP logic
        contracts = []
        if isinstance(response, dict):
            if "results" in response and isinstance(response["results"], list):
                contracts = response["results"]
            elif "contracts" in response and isinstance(response["contracts"], list):
                contracts = response["contracts"]
            elif "data" in response:
                contracts = response["data"]
        elif isinstance(response, list):
            contracts = response
        
        # Normalize contract format
        normalized_contracts = []
        for contract in contracts:
            if not isinstance(contract, dict):
                continue
            
            normalized_contract = {
                "ticker": contract.get("ticker") or contract.get("contract_ticker") or "",
                "underlying_ticker": symbol,
                "strike_price": contract.get("strike_price") or contract.get("strike") or 0,
                "contract_type": contract.get("contract_type") or contract.get("option_type", "").lower(),
                "expiration_date": contract.get("expiration_date") or contract.get("expiration") or ""
            }
            
            if normalized_contract["ticker"] and normalized_contract["strike_price"]:
                normalized_contracts.append(normalized_contract)
        
        logger.info(f"Retrieved {len(normalized_contracts)} normalized contracts for {symbol}")
        return normalized_contracts
    
    async def get_option_quote(self, option_ticker: str) -> Optional[Dict]:
        """Get option quote using last-quote endpoint (matches CashFlowAgent-Scanner-1)"""
        # Use the correct last-quote endpoint like the reference implementation
        url = f"{self.base_url}/last-quote"
        params = {
            "ticker": option_ticker,  # Changed from option_ticker to ticker
            "apiKey": self.options_api_key or self.api_key
        }
        
        logger.debug(f"Fetching option quote for {option_ticker} using last-quote endpoint")
        response = await self._request(url, params)
        
        # Parse response matching the reference implementation structure
        if response and isinstance(response, dict) and 'results' in response:
            results = response['results']
            if isinstance(results, list) and len(results) > 0:
                quote_data = results[0]
                return {
                    "ticker": option_ticker,
                    "bid_price": float(quote_data.get("bid_price", 0) or quote_data.get("bid", 0)),
                    "ask_price": float(quote_data.get("ask_price", 0) or quote_data.get("ask", 0)),
                    "last_price": float(quote_data.get("last_price", 0) or quote_data.get("last", 0)),
                    "volume": int(quote_data.get("volume", 0)),
                    "open_interest": int(quote_data.get("open_interest", 0)),
                    "implied_volatility": float(quote_data.get("implied_volatility", 0) or quote_data.get("iv", 0))
                }
        elif response and isinstance(response, dict):
            # Fallback for direct response format
            return {
                "ticker": option_ticker,
                "bid_price": float(response.get("bid_price", 0) or response.get("bid", 0)),
                "ask_price": float(response.get("ask_price", 0) or response.get("ask", 0)),
                "last_price": float(response.get("last_price", 0) or response.get("last", 0)),
                "volume": int(response.get("volume", 0)),
                "open_interest": int(response.get("open_interest", 0)),
                "implied_volatility": float(response.get("implied_volatility", 0) or response.get("iv", 0))
            }
        
        logger.warning(f"No quote data found for {option_ticker}")
        return None