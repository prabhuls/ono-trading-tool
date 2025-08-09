from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib

from .base import ExternalAPIService, ExternalAPIError
from app.core.config import settings


class PolygonService(ExternalAPIService):
    """
    Polygon.io API service implementation
    
    Example of how to implement a specific external API service
    """
    
    def __init__(self):
        # Get config from settings
        config = settings.get_external_api_config("polygon")
        
        super().__init__(
            service_name="polygon",
            base_url=config.get("base_url", "https://api.polygon.io"),
            api_key=config.get("api_key"),
            timeout=config.get("timeout", 30),
            max_retries=config.get("retry_count", 3),
            rate_limit=12.0,  # 12 requests per second for free tier
            cache_ttl=300,  # 5 minutes default cache
            headers={
                "Authorization": f"Bearer {config.get('api_key')}"
            }
        )
        
    def _get_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for Polygon requests"""
        # Create a unique key based on endpoint and params
        key_parts = [self.service_name, endpoint]
        
        if params:
            # Sort params for consistent keys
            sorted_params = sorted(params.items())
            params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
            key_parts.append(hashlib.md5(params_str.encode()).hexdigest()[:8])
            
        return ":".join(key_parts)
        
    def _parse_error_response(self, response) -> str:
        """Parse error message from Polygon response"""
        try:
            data = response.json()
            # Polygon typically returns errors in 'error' or 'message' fields
            return data.get("error", data.get("message", "Unknown error"))
        except Exception:
            return response.text or "Unknown error"
            
    async def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """
        Get detailed information about a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Ticker details including name, market cap, etc.
        """
        endpoint = f"/v3/reference/tickers/{ticker.upper()}"
        response = await self.get(endpoint)
        
        if response.get("status") != "OK":
            raise ExternalAPIError(
                message=f"Failed to get ticker details: {response.get('message')}",
                service=self.service_name
            )
            
        return response.get("results", {})
        
    async def get_last_trade(self, ticker: str) -> Dict[str, Any]:
        """
        Get the last trade for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Last trade information
        """
        endpoint = f"/v2/last/trade/{ticker.upper()}"
        response = await self.get(endpoint)
        
        if response.get("status") != "success":
            raise ExternalAPIError(
                message=f"Failed to get last trade: {response.get('message')}",
                service=self.service_name
            )
            
        return response.get("results", {})
        
    async def get_aggregates(
        self,
        ticker: str,
        multiplier: int = 1,
        timespan: str = "day",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 120
    ) -> List[Dict[str, Any]]:
        """
        Get aggregate bars for a ticker
        
        Args:
            ticker: Stock ticker symbol
            multiplier: Size of the time window
            timespan: Unit of time (minute, hour, day, week, month, quarter, year)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            limit: Number of results
            
        Returns:
            List of aggregate bars
        """
        # Default date range if not provided
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
        endpoint = f"/v2/aggs/ticker/{ticker.upper()}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        
        params = {
            "limit": limit,
            "sort": "desc"
        }
        
        response = await self.get(endpoint, params=params)
        
        if response.get("status") != "OK":
            raise ExternalAPIError(
                message=f"Failed to get aggregates: {response.get('message')}",
                service=self.service_name
            )
            
        return response.get("results", [])
        
    async def search_tickers(
        self,
        search: str,
        active: bool = True,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for tickers
        
        Args:
            search: Search query
            active: Only return active tickers
            limit: Number of results
            
        Returns:
            List of matching tickers
        """
        endpoint = "/v3/reference/tickers"
        
        params = {
            "search": search,
            "active": str(active).lower(),
            "limit": limit,
            "market": "stocks"
        }
        
        response = await self.get(endpoint, params=params)
        
        if response.get("status") != "OK":
            raise ExternalAPIError(
                message=f"Failed to search tickers: {response.get('message')}",
                service=self.service_name
            )
            
        return response.get("results", [])
        
    async def get_snapshot(self, ticker: str) -> Dict[str, Any]:
        """
        Get snapshot of a ticker including latest quote and trade
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Snapshot data
        """
        endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}"
        response = await self.get(endpoint)
        
        if response.get("status") != "OK":
            raise ExternalAPIError(
                message=f"Failed to get snapshot: {response.get('message')}",
                service=self.service_name
            )
            
        return response.get("ticker", {})
        
    async def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status
        
        Returns:
            Market status information
        """
        endpoint = "/v1/marketstatus/now"
        response = await self.get(endpoint, use_cache=False)  # Don't cache market status
        
        return {
            "market": response.get("market"),
            "exchange": response.get("exchanges"),
            "currencies": response.get("currencies")
        }
        
    async def health_check(self) -> Dict[str, Any]:
        """Check Polygon API health"""
        try:
            # Use market status endpoint for health check
            await self.get_market_status()
            return {
                "service": self.service_name,
                "status": "healthy"
            }
        except Exception as e:
            return {
                "service": self.service_name,
                "status": "unhealthy",
                "error": str(e)
            }


# Create singleton instance
polygon_service = PolygonService()