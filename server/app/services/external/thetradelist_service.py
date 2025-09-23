import asyncio
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.services.external.base import ExternalAPIService, ExternalAPIError
from app.core.config import settings
from app.core.logging import get_logger
from app.core.cache import redis_cache
from app.services.tradelist.calculations import BlackScholesCalculator


logger = get_logger(__name__)


class TheTradeListService(ExternalAPIService):
    """
    TheTradeList API integration service

    Provides access to real-time market data including:
    - Snapshot Locale endpoint for real-time market data
    - Grouped Locale endpoint for market statistics
    - Reference Ticker endpoint for ticker validation
    - Range Data endpoint for intraday chart data
    - Options Contracts endpoint for option chain data
    - ISIN endpoint for specific ticker current prices

    SPX Data Source Strategy:
    - CURRENT PRICE: Uses ISIN endpoint (US78378X1072) for single price point
    - CHART DATA: Uses regular range-data endpoint with "SPX" ticker directly
    - OPTIONS: Uses regular options-contracts endpoint with "SPX" ticker directly

    Features:
    - Automatic rate limiting and retry logic
    - Response caching with configurable TTL
    - Comprehensive error handling
    - Data normalization for consistent output
    - SPX-specific routing based on data type needed

    Cache Strategy:
    - Static data (5 seconds): Contract details, strikes, expirations
    - Dynamic data (5 seconds): Prices, quotes, volume, bid/ask
    """

    # Cache TTL constants
    CACHE_TTL_STATIC = 5      # 5 seconds for static data (contract details, strikes, expirations)
    CACHE_TTL_DYNAMIC = 5      # 5 seconds for dynamic data (prices, quotes, volume)
    
    def __init__(self):
        config = settings.get_external_api_config("thetradelist")

        super().__init__(
            service_name="thetradelist",
            base_url=config.get("base_url", "https://api.thetradelist.com"),
            api_key=config.get("api_key"),
            timeout=config.get("timeout", 10),
            max_retries=config.get("retry_count", 3),
            rate_limit=5.0,  # 5 calls per second
            cache_ttl=config.get("cache_ttl", self.CACHE_TTL_DYNAMIC)  # Default to dynamic cache
        )
        
        if not self.api_key:
            logger.warning("TheTradeList API key not configured")
    
    def _get_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for the request"""
        # Create a deterministic cache key
        key_parts = [f"thetradelist:{endpoint}"]
        
        if params:
            # Sort params for consistent cache keys
            sorted_params = sorted(params.items())
            param_str = urlencode(sorted_params)
            # Hash long parameter strings to keep cache keys manageable
            if len(param_str) > 100:
                param_hash = hashlib.md5(param_str.encode()).hexdigest()
                key_parts.append(param_hash)
            else:
                key_parts.append(param_str)
                
        return ":".join(key_parts)
    
    def _parse_error_response(self, response) -> str:
        """Parse error message from TheTradeList API response"""
        try:
            error_data = response.json()
            
            # Common TheTradeList error formats
            if isinstance(error_data, dict):
                # Try different error message fields
                for field in ["error", "message", "detail", "error_message"]:
                    if field in error_data:
                        return str(error_data[field])
                        
                # If no specific error field, return the whole dict as string
                return str(error_data)
                
            return str(error_data)
        except Exception:
            # Fallback to response text
            return response.text or f"HTTP {response.status_code}"
    
    def _setup_headers(self):
        """Setup TheTradeList-specific headers"""
        super()._setup_headers()
        # TheTradeList uses apiKey as query parameter, not header
        
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request with apiKey as query parameter"""
        if params is None:
            params = {}
        
        # Add API key as query parameter for TheTradeList
        if self.api_key:
            params["apiKey"] = self.api_key
            
        return await super().get(endpoint, params=params, **kwargs)
    
    async def get_market_snapshot(
        self,
        tickers: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get real-time market snapshot data using TheTradeList snapshot-locale endpoint
        
        Args:
            tickers: Comma-separated list of ticker symbols (e.g., "MSFT,GOOG,AAPL,")
            
        Returns:
            Market snapshot data normalized for frontend consumption
            
        Raises:
            ExternalAPIError: On API errors
        """
        endpoint = "/v1/data/snapshot-locale"
        params = {}
        
        if tickers:
            params["tickers"] = tickers
        
        try:
            logger.info(
                "Fetching market snapshot",
                tickers=tickers
            )
            
            raw_data = await self.get(endpoint, params=params)
            normalized_data = self._normalize_snapshot_data(raw_data)
            
            logger.info(
                "Market snapshot retrieved successfully",
                data_points=len(normalized_data.get("tickers", [])),
                tickers=tickers
            )
            
            return normalized_data
            
        except ExternalAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error("Failed to normalize market snapshot data", error=str(e))
            raise ExternalAPIError(
                message=f"Failed to process market snapshot: {str(e)}",
                service=self.service_name
            )
    
    async def get_grouped_daily(
        self,
        date: Optional[str] = None,
        locale: str = "US",
        market: str = "stocks",
        include_otc: bool = False
    ) -> Dict[str, Any]:
        """
        Get grouped daily market data
        
        Args:
            date: Date in YYYY-MM-DD format (default: previous trading day)
            locale: Market locale (default: "US")  
            market: Market type (default: "stocks")
            include_otc: Include OTC markets (default: False)
            
        Returns:
            Grouped daily market data
            
        Raises:
            ExternalAPIError: On API errors
        """
        endpoint = "/v1/data/grouped-locale"
        
        # Use previous trading day if no date specified
        if not date:
            date = self._get_previous_trading_day()
            
        params = {
            "startdate": date
        }
        
        try:
            logger.info(
                "Fetching grouped daily data",
                date=date
            )
            
            raw_data = await self.get(endpoint, params=params)
            normalized_data = self._normalize_grouped_data(raw_data)
            
            logger.info(
                "Grouped daily data retrieved successfully",
                date=date,
                total_volume=normalized_data.get("total_volume", "N/A")
            )
            
            return normalized_data
            
        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error("Failed to normalize grouped daily data", error=str(e))
            raise ExternalAPIError(
                message=f"Failed to process grouped daily data: {str(e)}",
                service=self.service_name
            )
    
    async def validate_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Validate ticker symbol and get reference data
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Ticker reference data
            
        Raises:
            ExternalAPIError: On API errors
        """
        endpoint = "/v1/data/reference-ticker"
        params = {"ticker": ticker.upper()}
        
        try:
            logger.info("Validating ticker", ticker=ticker)
            
            raw_data = await self.get(endpoint, params=params, use_cache=True, cache_ttl=3600)  # Cache for 1 hour
            normalized_data = self._normalize_ticker_data(raw_data)
            
            logger.info("Ticker validated successfully", ticker=ticker)
            
            return normalized_data
            
        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error("Failed to validate ticker", ticker=ticker, error=str(e))
            raise ExternalAPIError(
                message=f"Failed to validate ticker {ticker}: {str(e)}",
                service=self.service_name
            )
    
    async def get_market_indicators(self) -> Dict[str, Any]:
        """
        Get comprehensive market indicators for the sidebar
        
        Combines data from multiple endpoints to provide:
        - Market volume statistics
        - Active/declining ratios
        - Real IV Rank calculated from VIX data via TheTradeList endpoints
        - Market breadth indicators
        
        Returns:
            Comprehensive market indicators including real VIX-based IV Rank
        """
        try:
            # Check cache first
            cache_key = "market_indicators:comprehensive"
            cached_data = redis_cache.get(f"external_api:{self.service_name}:{cache_key}")
            if cached_data is not None:
                logger.info("Using cached market indicators")
                return cached_data
            
            logger.info("Fetching comprehensive market indicators")
            
            # Fetch market data concurrently would be ideal, but for now sequential
            snapshot_data = await self.get_market_snapshot()
            grouped_data = await self.get_grouped_daily()
            
            # Combine and analyze data
            indicators = await self._calculate_market_indicators(snapshot_data, grouped_data)
            
            # Cache the results
            redis_cache.set(
                f"external_api:{self.service_name}:{cache_key}",
                indicators,
                ttl=self.cache_ttl
            )
            
            logger.info(
                "Market indicators calculated successfully",
                total_volume=indicators.get("volume", "N/A"),
                market_sentiment_score=indicators.get("market_sentiment_score", "N/A"),
                iv_rank=indicators.get("iv_rank", "N/A")
            )
            
            return indicators
            
        except Exception as e:
            logger.error("Failed to get market indicators", error=str(e))
            
            # Return fallback data if available in cache with longer TTL
            fallback_key = f"{cache_key}:fallback"
            fallback_data = redis_cache.get(f"external_api:{self.service_name}:{fallback_key}")
            if fallback_data:
                logger.warning("Using fallback market indicators data")
                return fallback_data
            
            # Return minimal indicators as last resort
            return self._get_fallback_indicators()
    
    def _normalize_snapshot_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize TheTradeList snapshot data for consistent frontend consumption"""
        try:
            # TheTradeList snapshot-locale returns: {"tickers": [...], "status": "OK", "count": N}
            tickers = raw_data.get("tickers", [])
            if not isinstance(tickers, list):
                tickers = []
            
            normalized = {
                "status": raw_data.get("status", "unknown"),
                "count": raw_data.get("count", len(tickers)),
                "tickers": [],
                "market_summary": {
                    "total_volume": 0,
                    "advancing": 0,
                    "declining": 0,
                    "unchanged": 0
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # Process individual tickers
            total_volume = 0
            advancing = 0
            declining = 0
            unchanged = 0
            
            for ticker_data in tickers:
                if not isinstance(ticker_data, dict):
                    continue
                
                # Extract from TheTradeList format
                day = ticker_data.get("day", {})
                prev_day = ticker_data.get("prevDay", {})
                
                # Calculate current price: use day.c if available (market hours), otherwise prev_day.c + change
                day_close = day.get("c", 0)
                prev_close = prev_day.get("c", 0)
                change = ticker_data.get("todaysChange", 0)
                current_price = day_close if day_close > 0 else (prev_close + change if prev_close > 0 else 0)
                    
                ticker_info = {
                    "ticker": ticker_data.get("ticker", ""),
                    "price": current_price,  # calculated current price
                    "change": change,
                    "change_percent": ticker_data.get("todaysChangePerc", 0),
                    "volume": day.get("v", 0),  # volume
                    "high": day.get("h", 0),    # high
                    "low": day.get("l", 0),     # low  
                    "open": day.get("o", 0),    # open
                    "previous_close": prev_close  # previous close
                }
                
                normalized["tickers"].append(ticker_info)
                
                # Accumulate market statistics
                volume = ticker_info["volume"]
                if isinstance(volume, (int, float)) and volume > 0:
                    total_volume += volume
                
                change = ticker_info["change"]
                if isinstance(change, (int, float)):
                    if change > 0:
                        advancing += 1
                    elif change < 0:
                        declining += 1
                    else:
                        unchanged += 1
            
            # Update market summary
            normalized["market_summary"].update({
                "total_volume": total_volume,
                "advancing": advancing,
                "declining": declining,
                "unchanged": unchanged
            })
            
            return normalized
            
        except Exception as e:
            logger.error("Failed to normalize snapshot data", error=str(e))
            return {
                "status": "error",
                "count": 0,
                "tickers": [],
                "market_summary": {
                    "total_volume": 0,
                    "advancing": 0,
                    "declining": 0,
                    "unchanged": 0
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }
    
    def _normalize_grouped_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize grouped daily data"""
        try:
            results = raw_data.get("results", [])
            if not isinstance(results, list):
                results = []
            
            total_volume = sum(
                item.get("v", 0) for item in results 
                if isinstance(item.get("v"), (int, float))
            )
            
            normalized = {
                "status": raw_data.get("status", "unknown"),
                "count": len(results),
                "total_volume": total_volume,
                "date": raw_data.get("date"),
                "market_data": results,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            return normalized
            
        except Exception as e:
            logger.error("Failed to normalize grouped data", error=str(e))
            return {
                "status": "error", 
                "count": 0,
                "total_volume": 0,
                "date": None,
                "market_data": [],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }
    
    def _normalize_ticker_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize ticker reference data"""
        try:
            results = raw_data.get("results", {})
            if not isinstance(results, dict):
                results = {}
            
            normalized = {
                "ticker": results.get("ticker", ""),
                "name": results.get("name", ""),
                "market": results.get("market", ""),
                "locale": results.get("locale", ""),
                "primary_exchange": results.get("primary_exchange", ""),
                "type": results.get("type", ""),
                "active": results.get("active", True),
                "currency_name": results.get("currency_name", ""),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            return normalized
            
        except Exception as e:
            logger.error("Failed to normalize ticker data", error=str(e))
            return {
                "ticker": "",
                "name": "",
                "market": "",
                "locale": "",
                "primary_exchange": "",
                "type": "",
                "active": False,
                "currency_name": "",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }
    
    async def _calculate_market_indicators(
        self, 
        snapshot_data: Dict[str, Any], 
        grouped_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate comprehensive market indicators"""
        try:
            market_summary = snapshot_data.get("market_summary", {})
            
            # Calculate advance/decline ratio
            advancing = market_summary.get("advancing", 0)
            declining = market_summary.get("declining", 0)
            ad_ratio = advancing / declining if declining > 0 else 0
            
            # Calculate volume metrics
            current_volume = market_summary.get("total_volume", 0)
            historical_volume = grouped_data.get("total_volume", 0)
            
            # Volume comparison (current vs historical)
            volume_ratio = current_volume / historical_volume if historical_volume > 0 else 1
            
            # Market sentiment approximation based on market conditions
            # NOTE: This is NOT actual IV rank - real IV rank requires VIX data and 52-week history
            market_sentiment_score = self._calculate_market_sentiment_score(
                ad_ratio, volume_ratio, market_summary
            )
            
            # Try to get real IV rank from VIX data
            real_iv_rank = await self._get_real_iv_rank()
            
            # Format volume for display
            formatted_volume = self._format_volume(current_volume)
            
            indicators = {
                "volume": formatted_volume,
                "volume_raw": current_volume,
                "market_sentiment_score": round(market_sentiment_score, 1),
                "iv_rank": real_iv_rank,
                "advance_decline_ratio": round(ad_ratio, 2),
                "advancing_stocks": advancing,
                "declining_stocks": declining,
                "unchanged_stocks": market_summary.get("unchanged", 0),
                "volume_vs_average": round(volume_ratio, 2),
                "market_breadth": "bullish" if ad_ratio > 1.5 else "bearish" if ad_ratio < 0.67 else "neutral",
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            
            return indicators
            
        except Exception as e:
            logger.error("Failed to calculate market indicators", error=str(e))
            return self._get_fallback_indicators()
    
    def _calculate_market_sentiment_score(
        self,
        ad_ratio: float,
        volume_ratio: float,
        market_summary: Dict[str, Any]
    ) -> float:
        """
        Calculate market sentiment score based on market conditions
        
        IMPORTANT: This is NOT implied volatility rank. It's a market sentiment
        approximation based on advance/decline ratios and volume patterns.
        
        Real IV rank is now calculated using VIX data from TheTradeList API:
        - Current VIX price from snapshot endpoint
        - 52-week high/low VIX history from ticker-range endpoint
        - Formula: (Current VIX - 52w Low VIX) / (52w High VIX - 52w Low VIX) × 100
        
        This method provides a rough market sentiment indicator for when
        real VIX data from TheTradeList is unavailable.
        """
        try:
            # Base sentiment score around 50 (middle of 0-100 range)
            base_sentiment = 50.0
            
            # Adjust based on advance/decline ratio
            if ad_ratio > 2.0:
                # Very bullish - lower sentiment volatility
                sentiment_adjustment = -20.0
            elif ad_ratio > 1.5:
                # Bullish - slightly lower sentiment volatility
                sentiment_adjustment = -10.0
            elif ad_ratio < 0.5:
                # Very bearish - higher sentiment volatility
                sentiment_adjustment = 20.0
            elif ad_ratio < 0.67:
                # Bearish - slightly higher sentiment volatility
                sentiment_adjustment = 10.0
            else:
                # Neutral
                sentiment_adjustment = 0.0
            
            # Adjust based on volume (higher volume often correlates with market uncertainty)
            if volume_ratio > 2.0:
                sentiment_adjustment += 15.0
            elif volume_ratio > 1.5:
                sentiment_adjustment += 10.0
            elif volume_ratio < 0.5:
                sentiment_adjustment -= 10.0
            
            # Calculate final sentiment score
            sentiment_score = base_sentiment + sentiment_adjustment
            
            # Constrain to 0-100 range
            sentiment_score = max(0.0, min(100.0, sentiment_score))
            
            return sentiment_score
            
        except Exception as e:
            logger.error("Failed to calculate market sentiment score", error=str(e))
            return 50.0  # Default middle value
    
    async def get_vix_current_price(self) -> Optional[float]:
        """
        Get current VIX price from TheTradeList snapshot endpoint
        
        Returns:
            Current VIX price or None if unavailable
        """
        try:
            logger.info("Fetching current VIX price from TheTradeList")
            
            # Use the get_market_snapshot method directly
            snapshot_data = await self.get_market_snapshot(tickers="VIX,")
            
            # Extract VIX data from response
            tickers = snapshot_data.get("tickers", [])
            if not tickers:
                logger.warning("No VIX data in TheTradeList snapshot response")
                return None
                
            for ticker_data in tickers:
                if isinstance(ticker_data, dict) and ticker_data.get("ticker") == "VIX":
                    # Try different field names for price
                    price = ticker_data.get("price") or ticker_data.get("day", {}).get("c") 
                    if price is not None:
                        logger.info(f"Current VIX price: {price}")
                        return float(price)
                        
            logger.warning("VIX ticker not found in TheTradeList snapshot")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current VIX price: {str(e)}")
            return None
    
    async def get_vix_52_week_history(self) -> Optional[Dict[str, float]]:
        """
        Get 52-week VIX history from TheTradeList ticker-range endpoint
        
        Returns:
            Dictionary with 52-week high, low, and historical data or None if unavailable
        """
        try:
            # Calculate date range for 52 weeks
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 52 weeks
            
            endpoint = "/v1/data/ticker-range"
            params = {
                "ticker": "VIX",
                "startdate": start_date.strftime("%Y-%m-%d"),
                "enddate": end_date.strftime("%Y-%m-%d")
            }
            
            logger.info(
                "Fetching VIX 52-week history from TheTradeList",
                start_date=params["startdate"],
                end_date=params["enddate"]
            )
            
            raw_data = await self.get(endpoint, params=params)
            
            # Extract VIX historical data
            results = raw_data.get("results", [])
            if not results:
                logger.warning("No VIX historical data from TheTradeList")
                return None
                
            # Extract closing prices
            closing_prices = []
            for bar in results:
                if isinstance(bar, dict):
                    # Try different field names for closing price
                    close_price = bar.get("c") or bar.get("close") or bar.get("price")
                    if close_price is not None:
                        closing_prices.append(float(close_price))
            
            if len(closing_prices) < 50:  # Need reasonable amount of data
                logger.warning(f"Insufficient VIX historical data: {len(closing_prices)} days")
                return None
                
            # Calculate 52-week high and low
            vix_52w_high = max(closing_prices)
            vix_52w_low = min(closing_prices)
            
            result = {
                "vix_52w_high": vix_52w_high,
                "vix_52w_low": vix_52w_low,
                "data_points": len(closing_prices)
            }
            
            logger.info(
                "VIX 52-week data retrieved",
                high=vix_52w_high,
                low=vix_52w_low,
                data_points=len(closing_prices)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get VIX 52-week history: {str(e)}")
            return None
    
    async def calculate_real_iv_rank(self) -> Optional[float]:
        """
        Calculate real IV Rank using VIX data from TheTradeList
        
        Formula: (Current VIX - 52w Low) / (52w High - 52w Low) × 100
        
        Returns:
            Real IV rank as float or None if unavailable
        """
        try:
            # Check cache first
            cache_key = "vix_iv_rank_thetradelist"
            cached_data = redis_cache.get(f"external_api:{self.service_name}:{cache_key}")
            if cached_data is not None:
                logger.info("Using cached VIX IV rank from TheTradeList")
                return cached_data
            
            logger.info("Calculating fresh IV rank using TheTradeList VIX data")
            
            # Get current VIX price and historical data concurrently would be ideal,
            # but for now we'll do sequential calls
            current_vix = await self.get_vix_current_price()
            if current_vix is None:
                logger.warning("Cannot calculate IV rank: current VIX price unavailable")
                return None
                
            vix_history = await self.get_vix_52_week_history()
            if vix_history is None:
                logger.warning("Cannot calculate IV rank: VIX historical data unavailable")
                return None
            
            vix_52w_high = vix_history["vix_52w_high"]
            vix_52w_low = vix_history["vix_52w_low"]
            
            # Calculate IV rank using the proper formula
            if vix_52w_high > vix_52w_low:
                iv_rank = ((current_vix - vix_52w_low) / (vix_52w_high - vix_52w_low)) * 100
                iv_rank = max(0.0, min(100.0, iv_rank))  # Clamp to 0-100 range
                iv_rank = round(iv_rank, 1)
            else:
                logger.warning("Invalid VIX range for IV rank calculation")
                return None
            
            # Cache the result for 5 minutes
            redis_cache.set(
                f"external_api:{self.service_name}:{cache_key}",
                iv_rank,
                ttl=300  # 5 minutes
            )
            
            logger.info(
                "Real IV rank calculated using TheTradeList",
                current_vix=current_vix,
                vix_52w_high=vix_52w_high,
                vix_52w_low=vix_52w_low,
                iv_rank=iv_rank,
                data_points=vix_history["data_points"]
            )
            
            return iv_rank
            
        except Exception as e:
            logger.error(f"Failed to calculate real IV rank: {str(e)}")
            return None
    
    async def _get_real_iv_rank(self) -> Optional[float]:
        """
        Get real IV rank using VIX data from TheTradeList API
        
        Returns:
            Actual IV rank based on VIX percentile over 52-week period, or None if unavailable
        """
        try:
            # Use TheTradeList for VIX data instead of Polygon
            iv_rank = await self.calculate_real_iv_rank()
            
            if iv_rank is not None:
                logger.info(f"Retrieved real IV rank from TheTradeList VIX data: {iv_rank}")
                return iv_rank
            else:
                logger.debug("TheTradeList VIX data unavailable, IV rank will be None")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get real IV rank from TheTradeList: {str(e)}")
            return None
    
    def _format_volume(self, volume: int) -> str:
        """Format volume with K/M/B suffixes"""
        try:
            if not isinstance(volume, (int, float)) or volume < 0:
                return "0"
            
            if volume >= 1_000_000_000:
                return f"{volume / 1_000_000_000:.1f}B"
            elif volume >= 1_000_000:
                return f"{volume / 1_000_000:.1f}M"
            elif volume >= 1_000:
                return f"{volume / 1_000:.1f}K"
            else:
                return str(int(volume))
                
        except Exception as e:
            logger.error("Failed to format volume", volume=volume, error=str(e))
            return "N/A"
    
    def _get_previous_trading_day(self) -> str:
        """Get previous trading day in YYYY-MM-DD format"""
        try:
            today = datetime.now()
            
            # Go back one day
            previous_day = today - timedelta(days=1)
            
            # If it's Monday, go back to Friday (skip weekend)
            if previous_day.weekday() == 6:  # Sunday
                previous_day = previous_day - timedelta(days=2)
            elif previous_day.weekday() == 5:  # Saturday
                previous_day = previous_day - timedelta(days=1)
            
            return previous_day.strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.error("Failed to calculate previous trading day", error=str(e))
            # Fallback to yesterday
            yesterday = datetime.now() - timedelta(days=1)
            return yesterday.strftime("%Y-%m-%d")
    
    def _get_fallback_indicators(self) -> Dict[str, Any]:
        """Return fallback market indicators when API fails"""
        return {
            "volume": "N/A",
            "volume_raw": 0,
            "market_sentiment_score": 50.0,
            "iv_rank": None,
            "advance_decline_ratio": 1.0,
            "advancing_stocks": 0,
            "declining_stocks": 0,
            "unchanged_stocks": 0,
            "volume_vs_average": 1.0,
            "market_breadth": "neutral",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "status": "fallback"
        }
    
    async def get_spx_price_via_isin(self) -> Dict[str, Any]:
        """
        Get SPX current price via ISIN endpoint
        
        IMPORTANT: This endpoint returns ONLY a single current price point,
        NOT time series data. Use this for current price display only.
        For SPX chart data, use the regular range-data endpoint with "SPX" ticker.
        
        Uses ISIN: US78378X1072 for SPX on the v3/data/isin endpoint
        
        Returns:
            SPX current price data (single data point)
            
        Raises:
            ExternalAPIError: On API errors
        """
        endpoint = "/v3/data/isin"
        params = {"isin": "US78378X1072"}  # SPX ISIN
        
        try:
            logger.info("Fetching SPX current price via ISIN endpoint (single data point only)", isin="US78378X1072")
            
            # Check cache first with ticker-specific key
            cache_key = "stock_price:SPX:isin"
            cached_data = redis_cache.get(f"external_api:{self.service_name}:{cache_key}")
            if cached_data is not None:
                logger.info("Using cached SPX ISIN price data")
                return cached_data
            
            # Fetch fresh data from ISIN endpoint
            raw_data = await self.get(endpoint, params=params)
            
            # Parse and normalize ISIN endpoint response
            normalized_data = self._normalize_isin_price_data(raw_data, "SPX")
            
            # Cache the result for 30 seconds (same TTL as other price data)
            redis_cache.set(
                f"external_api:{self.service_name}:{cache_key}",
                normalized_data,
                ttl=self.cache_ttl
            )
            
            logger.info(
                "SPX current price retrieved successfully via ISIN",
                price=normalized_data["price"],
                change=normalized_data["change"],
                data_type="single_price_point",
                endpoint_used="isin"
            )
            
            return normalized_data
            
        except ExternalAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error("Failed to get SPX price via ISIN", error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get SPX price via ISIN: {str(e)}",
                service=self.service_name
            )
    
    def _normalize_isin_price_data(self, raw_data: Dict[str, Any], ticker: str) -> Dict[str, Any]:
        """
        Normalize ISIN endpoint response to match standard price data format
        
        ISIN endpoint provides ONLY current price (single data point), not time series.
        This is used exclusively for SPX current price display.
        
        Expected ISIN response format:
        {
            "price": "6409.903",
            "unix_timestamp": 1756857605,
            "currency": null,
            "change_absolute": -50.35699999999997,
            "change_percent": -0.7794887512267303,
            "meta": {
                "name": "S&P 500",
                "id": 1000002
            }
        }
        
        Args:
            raw_data: Raw API response from ISIN endpoint (single price data)
            ticker: Ticker symbol (e.g., "SPX")
            
        Returns:
            Normalized current price data matching get_stock_price format
        """
        try:
            # ISIN endpoint returns data directly at root level, not nested under "results"
            # Extract price data from the actual ISIN response format
            price = 0.0
            change = 0.0
            change_percent = 0.0
            
            # Handle ISIN endpoint direct response format
            if "price" in raw_data:
                try:
                    # Price comes as string in ISIN endpoint, need to convert to float
                    price = float(raw_data["price"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse price from ISIN response: {raw_data.get('price')}, error: {e}")
            
            if "change_absolute" in raw_data:
                try:
                    # change_absolute maps to our "change" field
                    change = float(raw_data["change_absolute"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse change_absolute from ISIN response: {raw_data.get('change_absolute')}, error: {e}")
            
            if "change_percent" in raw_data:
                try:
                    # change_percent is already the correct field name
                    change_percent = float(raw_data["change_percent"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse change_percent from ISIN response: {raw_data.get('change_percent')}, error: {e}")
            
            # Fallback: try legacy format in case the response format differs
            if price == 0.0:
                logger.warning("ISIN price not found in expected format, trying legacy parsing")
                
                # Check if there's a nested results structure (legacy format)
                results = raw_data.get("results", raw_data)  # Use raw_data itself if no results key
                if isinstance(results, list) and results:
                    results = results[0]  # Take first result if it's a list
                
                # Try legacy field names
                legacy_price_fields = ["c", "close", "price", "last_price", "current_price"]
                legacy_change_fields = ["change", "todaysChange", "daily_change", "change_absolute"]
                legacy_change_percent_fields = ["changePercent", "todaysChangePerc", "change_percent", "daily_change_percent"]
                
                for field in legacy_price_fields:
                    if field in results and results[field] is not None:
                        try:
                            price = float(results[field])
                            logger.info(f"Found legacy price in field '{field}': {price}")
                            break
                        except (ValueError, TypeError):
                            continue
                
                for field in legacy_change_fields:
                    if field in results and results[field] is not None:
                        try:
                            change = float(results[field])
                            logger.info(f"Found legacy change in field '{field}': {change}")
                            break
                        except (ValueError, TypeError):
                            continue
                
                for field in legacy_change_percent_fields:
                    if field in results and results[field] is not None:
                        try:
                            change_percent = float(results[field])
                            logger.info(f"Found legacy change_percent in field '{field}': {change_percent}")
                            break
                        except (ValueError, TypeError):
                            continue
            
            normalized_data = {
                "ticker": ticker,
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(
                "ISIN current price data normalized",
                ticker=ticker,
                price=price,
                change=change,
                change_percent=change_percent,
                raw_response_keys=list(raw_data.keys()) if isinstance(raw_data, dict) else "non-dict",
                source_format="isin_direct" if "price" in raw_data else "legacy_fallback"
            )
            
            return normalized_data
            
        except Exception as e:
            logger.error("Failed to normalize ISIN price data", ticker=ticker, error=str(e), raw_data_keys=list(raw_data.keys()) if isinstance(raw_data, dict) else "non-dict")
            # Return fallback data
            return {
                "ticker": ticker,
                "price": 0.0,
                "change": 0.0,
                "change_percent": 0.0,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }

    async def get_sp_prices(self) -> Dict[str, Any]:
        """
        Get real-time prices for SPY and SPX in a single API call

        Uses the new sp-prices endpoint for efficient fetching

        Returns:
            Dictionary with SPY and SPX price data including net change info

        Raises:
            ExternalAPIError: On API errors
        """
        try:
            logger.info("Fetching SP prices from sp-prices endpoint")

            # Use the client from parent class
            endpoint = "/v1/data/sp-prices"
            params = {"apiKey": self.api_key}

            # Make the request using the parent class client
            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            # Parse response
            result = {
                "SPY": None,
                "SPX": None,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            for item in data.get("data", []):
                ticker = item.get("ticker")
                if ticker in ["SPY", "SPX"]:
                    result[ticker] = {
                        "ticker": ticker,
                        "price": float(item.get("price", 0)),
                        "net_change": float(item.get("net_change", 0)),
                        "net_change_pct": float(item.get("net_change_pct", 0)),
                        "timestamp": item.get("time", result["timestamp"])
                    }

            logger.info(
                "SP prices retrieved successfully",
                spy_price=result["SPY"]["price"] if result["SPY"] else None,
                spx_price=result["SPX"]["price"] if result["SPX"] else None
            )

            return result

        except Exception as e:
            logger.error("Failed to get SP prices", error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get SP prices: {str(e)}",
                service=self.service_name
            )

    async def get_stock_price(self, ticker: str) -> Dict[str, Any]:
        """
        Get current price for a single stock ticker

        Uses sp-prices endpoint for SPY/SPX (more efficient and real-time)
        Regular snapshot endpoint is used for other tickers

        Args:
            ticker: Stock ticker symbol (e.g., "SPY", "XSP", "SPX")

        Returns:
            Stock price data with normalized format (current price only)

        Raises:
            ExternalAPIError: On API errors or invalid ticker
        """
        # Validate ticker is one of the supported symbols
        supported_tickers = {"SPY", "XSP", "SPX"}
        ticker_upper = ticker.upper()

        if ticker_upper not in supported_tickers:
            raise ExternalAPIError(
                message=f"Ticker {ticker} not supported. Supported tickers: {', '.join(supported_tickers)}",
                service=self.service_name
            )

        try:
            logger.info("Fetching stock price", ticker=ticker_upper)

            # Use new sp-prices endpoint for SPY and SPX
            if ticker_upper in ["SPY", "SPX"]:
                sp_prices = await self.get_sp_prices()
                ticker_data = sp_prices.get(ticker_upper)

                if not ticker_data:
                    raise ExternalAPIError(
                        message=f"No price data found for ticker {ticker_upper}",
                        service=self.service_name
                    )

                # Normalize to match existing format (using net_change as change)
                return {
                    "ticker": ticker_data["ticker"],
                    "price": ticker_data["price"],
                    "change": ticker_data["net_change"],
                    "change_percent": ticker_data["net_change_pct"],
                    "timestamp": ticker_data["timestamp"]
                }

            # Use existing market snapshot method for XSP
            snapshot_data = await self.get_market_snapshot(tickers=f"{ticker_upper},")

            # Extract ticker data from response
            tickers = snapshot_data.get("tickers", [])
            if not tickers:
                raise ExternalAPIError(
                    message=f"No price data found for ticker {ticker_upper}",
                    service=self.service_name
                )

            # Find the specific ticker in the response
            ticker_data = None
            for ticker_info in tickers:
                if isinstance(ticker_info, dict) and ticker_info.get("ticker") == ticker_upper:
                    ticker_data = ticker_info
                    break

            if not ticker_data:
                raise ExternalAPIError(
                    message=f"Ticker {ticker_upper} not found in API response",
                    service=self.service_name
                )

            # Normalize the response format
            normalized_data = {
                "ticker": ticker_data.get("ticker", ticker_upper),
                "price": float(ticker_data.get("price", 0)),
                "change": float(ticker_data.get("change", 0)),
                "change_percent": float(ticker_data.get("change_percent", 0)),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(
                "Stock price retrieved successfully",
                ticker=ticker_upper,
                price=normalized_data["price"],
                change=normalized_data["change"]
            )

            return normalized_data

        except ExternalAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error("Failed to get stock price", ticker=ticker, error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get price for {ticker}: {str(e)}",
                service=self.service_name
            )

    async def get_multiple_stock_prices(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Get current prices for multiple stock tickers
        
        Routes SPX to ISIN endpoint for current price (single data point),
        uses regular snapshot endpoint for other tickers.
        
        Args:
            tickers: List of stock ticker symbols (e.g., ["SPY", "XSP", "SPX"])
            
        Returns:
            Multiple stock prices data with normalized format (current prices only)
            
        Raises:
            ExternalAPIError: On API errors or invalid tickers
        """
        # Validate all tickers are supported
        supported_tickers = {"SPY", "XSP", "SPX"}
        tickers_upper = [ticker.upper() for ticker in tickers]
        invalid_tickers = [t for t in tickers_upper if t not in supported_tickers]
        
        if invalid_tickers:
            raise ExternalAPIError(
                message=f"Unsupported tickers: {', '.join(invalid_tickers)}. Supported: {', '.join(supported_tickers)}",
                service=self.service_name
            )
        
        try:
            logger.info("Fetching multiple stock prices", tickers=tickers_upper)
            
            prices = []
            
            # Handle SPX separately via ISIN endpoint
            non_spx_tickers = [t for t in tickers_upper if t != "SPX"]
            spx_requested = "SPX" in tickers_upper
            
            # Get SPX current price via ISIN if requested (single data point)
            if spx_requested:
                try:
                    spx_data = await self.get_spx_price_via_isin()
                    prices.append(spx_data)
                    logger.info("SPX current price retrieved via ISIN", price=spx_data.get("price"))
                except Exception as e:
                    logger.warning("Failed to get SPX current price via ISIN", error=str(e))
            
            # Get other tickers via snapshot endpoint
            if non_spx_tickers:
                tickers_string = ",".join(non_spx_tickers) + ","
                
                # Use existing market snapshot method
                snapshot_data = await self.get_market_snapshot(tickers=tickers_string)
                
                # Extract and normalize ticker data
                api_tickers = snapshot_data.get("tickers", [])
                
                for ticker_info in api_tickers:
                    if not isinstance(ticker_info, dict):
                        continue
                        
                    ticker_symbol = ticker_info.get("ticker", "")
                    if ticker_symbol in non_spx_tickers:
                        normalized_data = {
                            "ticker": ticker_symbol,
                            "price": float(ticker_info.get("price", 0)),
                            "change": float(ticker_info.get("change", 0)),
                            "change_percent": float(ticker_info.get("change_percent", 0)),
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                        prices.append(normalized_data)
            
            # Check if we got all requested tickers
            found_tickers = {p["ticker"] for p in prices}
            missing_tickers = set(tickers_upper) - found_tickers
            if missing_tickers:
                logger.warning("Some tickers not found in API responses", missing=list(missing_tickers))
            
            result = {"prices": prices}
            
            logger.info(
                "Multiple stock prices retrieved successfully",
                requested_count=len(tickers_upper),
                found_count=len(prices),
                tickers=tickers_upper,
                spx_via_isin=spx_requested
            )
            
            return result
            
        except ExternalAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error("Failed to get multiple stock prices", tickers=tickers, error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get prices for tickers {tickers}: {str(e)}",
                service=self.service_name
            )

    async def get_options_contracts(
        self,
        underlying_ticker: str,
        expiration_date: Optional[str] = None,
        limit: int = 1000,
        fetch_all: bool = False,  # Default to optimized fetching for SPX
        current_price: Optional[float] = None,
        target_strikes_around_price: int = 30  # Target number of strikes around current price for analysis
    ) -> Dict[str, Any]:
        """
        Get options contracts for a specific underlying ticker with pagination support

        SPX options work directly with the options-contracts endpoint using "SPX" ticker.
        Handles pagination when there are more than 1000 contracts with smart early exit.

        Args:
            underlying_ticker: The stock symbol (e.g., "SPY", "SPX")
            expiration_date: Optional specific expiration date filter (YYYY-MM-DD)
            limit: Maximum number of results per page (default: 1000)
            fetch_all: If True, fetch all contracts (old behavior). If False, use smart pagination
            current_price: Current price for smart pagination (will fetch if not provided)
            target_strikes_around_price: Number of strikes to fetch around current price

        Returns:
            Dictionary containing all options contracts data

        Raises:
            ExternalAPIError: On API errors
        """
        endpoint = "/v1/data/options-contracts"

        # Increase timeout for SPX as it may have multiple pages
        original_timeout = self.timeout
        if underlying_ticker.upper() == "SPX":
            self.timeout = 120  # 2 minutes for SPX

        # For SPX, default to smart pagination unless explicitly requested otherwise
        if underlying_ticker.upper() == "SPX" and not fetch_all and current_price is None:
            # Try to get current price for smart pagination
            try:
                price_data = await self.get_stock_price(underlying_ticker)
                current_price = price_data.get("price")
                if current_price:
                    logger.info(f"Using current {underlying_ticker} price {current_price} for smart pagination")
                else:
                    # If we can't get the current price, we must fetch all
                    logger.warning(f"Could not get current price for {underlying_ticker}, will fetch all contracts")
                    fetch_all = True
            except Exception as e:
                logger.warning(f"Error fetching current price for {underlying_ticker}: {e}, will fetch all contracts")
                fetch_all = True

        all_results = []
        page_count = 0
        next_url = None
        passed_current_price = False
        unique_strikes_above = set()
        unique_strikes_below = set()

        try:
            logger.info(
                "Fetching options contracts (with smart pagination)",
                underlying_ticker=underlying_ticker.upper(),
                expiration_date=expiration_date,
                limit=limit,
                fetch_all=fetch_all,
                current_price=current_price,
                endpoint=endpoint
            )

            while True:
                page_count += 1

                # Build params for this request
                params = {
                    "underlying_ticker": underlying_ticker.upper(),
                    "limit": limit,
                    "sort": "expiration_date",  # Sort by expiration date to get nearest expirations first
                    "order": "asc"  # Ascending order (nearest expirations first)
                }

                # Note: expiration_date parameter is not supported by the API
                # We'll filter results after fetching instead

                # Add next_url parameter if we have it from previous response
                if next_url:
                    params["next_url"] = next_url

                if page_count > 1:
                    logger.info(f"Fetching page {page_count} for {underlying_ticker.upper()} options...")

                # Make the request
                raw_data = await self.get(
                    endpoint,
                    params=params,
                    use_cache=(page_count == 1),  # Only cache first page
                    cache_ttl=self.CACHE_TTL_STATIC  # 5 second cache for contract data
                )

                # Extract results from this page
                page_results = raw_data.get("results", [])

                # Smart pagination logic - collect ALL contracts for target expiration
                if expiration_date and not fetch_all:
                    found_target_date = False
                    passed_target_date = False
                    target_date_contracts_in_page = []

                    for contract in page_results:
                        contract_exp = contract.get('expiration_date')

                        if contract_exp == expiration_date:
                            found_target_date = True
                            target_date_contracts_in_page.append(contract)
                            all_results.append(contract)  # Only add target date contracts

                            # Track strikes for the target date
                            if current_price:
                                strike = float(contract.get('strike_price', 0))
                                if strike > current_price:
                                    unique_strikes_above.add(strike)
                                elif strike < current_price:
                                    unique_strikes_below.add(strike)

                        elif contract_exp and contract_exp > expiration_date:
                            # We've moved past our target date
                            passed_target_date = True
                            # Don't add these contracts to results
                        elif contract_exp and contract_exp < expiration_date:
                            # Haven't reached target date yet, skip these
                            continue

                    logger.info(
                        f"Page {page_count}: Processed {len(page_results)} contracts, "
                        f"found {len(target_date_contracts_in_page)} for {expiration_date}, "
                        f"strikes above: {len(unique_strikes_above)}, below: {len(unique_strikes_below)} "
                        f"(total for date: {len(all_results)})"
                    )

                    # Continue fetching if:
                    # - We haven't found the target date yet, OR
                    # - We found it but haven't passed it yet (more contracts might be on next page)
                    # Stop when we've passed the target date
                    if passed_target_date and found_target_date:
                        logger.info(
                            f"Collected all contracts for {expiration_date}: "
                            f"{len(all_results)} contracts with {len(unique_strikes_above) + len(unique_strikes_below)} unique strikes"
                        )
                        break
                    elif not found_target_date and page_count > 10:
                        logger.warning(f"Target date {expiration_date} not found after {page_count} pages")
                        break
                else:
                    # No expiration filter - add all contracts
                    all_results.extend(page_results)
                    logger.info(
                        f"Page {page_count}: Retrieved {len(page_results)} contracts (total: {len(all_results)})"
                    )

                # Check for next_url to continue pagination
                next_url = raw_data.get("next_url")
                if not next_url:
                    break

                # Safety check to prevent infinite loops
                # More aggressive limit for SPX to prevent timeouts
                max_pages = 10 if underlying_ticker == "SPX" else 20
                if page_count > max_pages:
                    logger.warning(f"Stopping after {page_count} pages (max {max_pages} for {underlying_ticker}) to prevent timeout")
                    break

            # Build final response with all results
            final_data = {
                "results": all_results,
                "resultsCount": len(all_results),
                "status": "OK"
            }

            # Filter by expiration date if provided
            if expiration_date and all_results:
                filtered_results = [
                    contract for contract in all_results
                    if contract.get("expiration_date") == expiration_date
                ]
                final_data["results"] = filtered_results
                final_data["resultsCount"] = len(filtered_results)

            logger.info(
                "All options contracts retrieved successfully",
                underlying_ticker=underlying_ticker.upper(),
                total_contracts=len(final_data.get("results", [])),
                total_pages=page_count,
                expiration_filter=expiration_date
            )

            return final_data

        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get options contracts",
                underlying_ticker=underlying_ticker,
                error=str(e)
            )
            raise ExternalAPIError(
                message=f"Failed to get options contracts for {underlying_ticker}: {str(e)}",
                service=self.service_name
            )
        finally:
            # Restore original timeout
            self.timeout = original_timeout

    async def get_options_snapshot(
        self,
        ticker: str,
        option_contract: str
    ) -> Dict[str, Any]:
        """
        Get real-time option pricing snapshot
        
        Args:
            ticker: Underlying stock ticker (e.g., "SPY")
            option_contract: Full option contract symbol (e.g., "O:SPY250829C00580000")
            
        Returns:
            Option pricing data with bid/ask, volume, etc.
            
        Raises:
            ExternalAPIError: On API errors
        """
        endpoint = "/v1/data/snapshot-options"
        params = {
            "ticker": ticker.upper(),
            "option": option_contract
        }
        
        try:
            logger.info(
                "Fetching option snapshot",
                ticker=ticker.upper(),
                option_contract=option_contract
            )
            
            raw_data = await self.get(endpoint, params=params, use_cache=True, cache_ttl=self.CACHE_TTL_DYNAMIC)  # Cache for 5 seconds
            
            logger.info(
                "Option snapshot retrieved successfully",
                ticker=ticker.upper(),
                option_contract=option_contract
            )
            
            return raw_data
            
        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get option snapshot",
                ticker=ticker,
                option_contract=option_contract,
                error=str(e)
            )
            raise ExternalAPIError(
                message=f"Failed to get option snapshot for {option_contract}: {str(e)}",
                service=self.service_name
            )

    async def get_batch_options_snapshot(
        self,
        option_contracts: List[str],
        underlying_ticker: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get real-time pricing snapshots for multiple options

        Since TheTradeList API doesn't have a batch endpoint for options,
        we'll fetch them individually but with concurrent requests for better performance.

        Args:
            option_contracts: List of option contract symbols (e.g., ["O:SPY250117C00585000"])
            underlying_ticker: The underlying stock ticker (e.g., "SPY")

        Returns:
            Dictionary mapping option ticker to pricing data

        Raises:
            ExternalAPIError: On API errors
        """
        if not option_contracts:
            return {}

        pricing_map = {}

        # Process in batches to avoid overwhelming the API
        batch_size = 5  # Process 5 options at a time

        for i in range(0, len(option_contracts), batch_size):
            batch = option_contracts[i:i+batch_size]

            # Create concurrent tasks for this batch
            tasks = []
            for option_ticker in batch:
                tasks.append(self._fetch_single_option_snapshot(option_ticker, underlying_ticker))

            # Execute batch concurrently
            import asyncio
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for option_ticker, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.warning(
                        "Failed to fetch option snapshot",
                        option=option_ticker,
                        error=str(result)
                    )
                    continue

                if result:
                    pricing_map[option_ticker] = result

        logger.info(
            "Batch options pricing completed",
            contracts_requested=len(option_contracts),
            contracts_received=len(pricing_map)
        )

        return pricing_map

    async def _fetch_single_option_snapshot(
        self,
        option_ticker: str,
        underlying_ticker: str
    ) -> Dict[str, Any]:
        """
        Fetch snapshot for a single option contract

        Args:
            option_ticker: Option contract symbol (e.g., "O:SPY250117C00585000")
            underlying_ticker: Underlying stock ticker (e.g., "SPY")

        Returns:
            Option pricing data
        """
        endpoint = "/v1/data/snapshot-options"
        params = {
            "ticker": underlying_ticker,
            "option": option_ticker
        }

        try:
            raw_data = await self.get(endpoint, params=params, use_cache=True, cache_ttl=self.CACHE_TTL_DYNAMIC)

            if raw_data and raw_data.get("results"):
                results = raw_data["results"]

                # Extract pricing data from the response
                day_data = results.get("day", {})
                last_quote = results.get("last_quote", {})
                last_trade = results.get("last_trade", {})

                # Get bid/ask from last_quote
                bid = last_quote.get("bid", 0) if last_quote else 0
                ask = last_quote.get("ask", 0) if last_quote else 0

                # Only use actual quote data, don't estimate from last trade
                # If no quote data is available, the contract will be skipped

                return {
                    "bid": bid,
                    "ask": ask,
                    "volume": day_data.get("volume", 0),
                    "open_interest": results.get("open_interest", 0),
                    "implied_volatility": results.get("implied_volatility"),  # May not be available
                    "last_price": last_trade.get("price", 0) if last_trade else 0,
                    "day": day_data
                }

            return None

        except Exception as e:
            logger.debug(f"Failed to fetch option snapshot for {option_ticker}: {str(e)}")
            return None

    async def get_last_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get last quote for a stock or option ticker

        Args:
            ticker: Ticker symbol (stock or option contract)

        Returns:
            Last quote data with bid/ask prices and sizes

        Raises:
            ExternalAPIError: On API errors
        """
        endpoint = "/v1/data/last-quote"
        params = {"ticker": ticker}

        try:
            logger.info("Fetching last quote", ticker=ticker)

            raw_data = await self.get(endpoint, params=params, use_cache=True, cache_ttl=self.CACHE_TTL_DYNAMIC)  # Cache for 5 seconds

            logger.info("Last quote retrieved successfully", ticker=ticker)

            return raw_data

        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error("Failed to get last quote", ticker=ticker, error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get last quote for {ticker}: {str(e)}",
                service=self.service_name
            )

    async def get_next_trading_day_expiration(self, ticker: str = "SPY") -> str:
        """
        Get the next available expiration date from API data for the specified ticker

        For SPY: Looks for next trading day expiration (daily options)
        For SPX: Looks for next trading day expiration (daily SPX options + weekly SPXW options)

        Args:
            ticker: The ticker symbol to get expiration for (e.g., "SPY", "SPX")

        Returns:
            Next available expiration date in YYYY-MM-DD format
        """
        ticker = ticker.upper()
        
        try:
            logger.info("Getting next available expiration from API", ticker=ticker)
            
            # MAJOR OPTIMIZATION: For common tickers, calculate expiration instead of fetching
            if ticker in ["SPY", "SPX"]:
                # Both SPY and SPX have daily options, return next trading day
                # SPX has both daily (SPX) and weekly (SPXW) options available
                return self._calculate_next_trading_day()

            # For other tickers, fetch just first page
            contracts_data = await self.get_options_contracts(
                underlying_ticker=ticker,
                limit=10,  # Very small limit - we only need expiration dates
                fetch_all=False  # Don't fetch all pages
            )
            
            results = contracts_data.get("results", [])
            if not results:
                logger.warning("No option contracts found for expiration date lookup", ticker=ticker)
                # Fallback to calculated date
                return self._calculate_next_trading_day()
            
            # Extract unique expiration dates
            expiration_dates = set()
            for contract in results:
                exp_date = contract.get("expiration_date")
                if exp_date:
                    expiration_dates.add(exp_date)
            
            if not expiration_dates:
                logger.warning("No expiration dates found in contracts", ticker=ticker)
                return self._calculate_next_trading_day()
            
            # Sort expiration dates and find next available
            sorted_expirations = sorted(list(expiration_dates))
            
            # Use ET timezone for comparison since market data is in ET
            try:
                from zoneinfo import ZoneInfo
                et_tz = ZoneInfo('America/New_York')
                today_et = datetime.now(et_tz).strftime('%Y-%m-%d')
                today = today_et
                logger.info(f"Using ET timezone for date comparison: {today_et}")
            except ImportError:
                # Fallback if zoneinfo not available (Python < 3.9)
                try:
                    import pytz
                    et_tz = pytz.timezone('America/New_York')
                    today_et = datetime.now(et_tz).strftime('%Y-%m-%d')
                    today = today_et
                    logger.info(f"Using ET timezone via pytz for date comparison: {today_et}")
                except ImportError:
                    # Ultimate fallback if no timezone library available
                    today = datetime.now().strftime('%Y-%m-%d')
                    logger.warning("No timezone library available, using local time for comparison")
            
            # Different logic for SPY vs SPX
            if ticker == "SPY":
                # SPY: Look for next trading day expiration (daily options)
                next_trading_day = self._calculate_next_trading_day()
                
                # Check if the calculated next trading day has options available
                if next_trading_day in sorted_expirations:
                    logger.info(
                        "SPY next trading day expiration found",
                        expiration_date=next_trading_day,
                        ticker=ticker
                    )
                    return next_trading_day
                else:
                    # Fall back to nearest available expiration for SPY
                    logger.warning(
                        "SPY next trading day expiration not available, using nearest",
                        calculated_date=next_trading_day,
                        available_dates=sorted_expirations[:5],  # Log first 5 for debugging
                        ticker=ticker
                    )
            
            # SPX or SPY fallback: Find nearest available expiration (any future date)
            next_available = None
            for exp_date in sorted_expirations:
                if exp_date > today:
                    next_available = exp_date
                    break
            
            if next_available:
                expiration_type = "daily" if ticker == "SPY" else "weekly/monthly"
                logger.info(
                    "Next available expiration found via API",
                    ticker=ticker,
                    expiration_date=next_available,
                    expiration_type=expiration_type,
                    total_available=len(sorted_expirations)
                )
                return next_available
            else:
                logger.warning("No future expiration dates found in API data", ticker=ticker)
                return self._calculate_next_trading_day()
                
        except Exception as e:
            logger.error("Failed to get next expiration from API", ticker=ticker, error=str(e))
            # Fallback to calculated date
            return self._calculate_next_trading_day()
    
    def _calculate_next_trading_day(self) -> str:
        """
        Fallback method to calculate next trading day when API lookup fails
        Uses Eastern Time for market hours consideration
        
        Returns:
            Next trading day date in YYYY-MM-DD format
        """
        try:
            from zoneinfo import ZoneInfo
            
            # Use Eastern Time for market hours
            et_tz = ZoneInfo('America/New_York')
            et_now = datetime.now(et_tz)
            
            # For options, we always want the NEXT trading day, not today
            # This ensures we get the proper expiration for overnight trading
            next_trading_day = et_now.date() + timedelta(days=1)
            
            # Skip weekends
            while next_trading_day.weekday() > 4:  # 5=Saturday, 6=Sunday
                next_trading_day = next_trading_day + timedelta(days=1)
            
            return next_trading_day.strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.error("Failed to calculate fallback trading day", error=str(e))
            # Ultimate fallback using ET
            try:
                from zoneinfo import ZoneInfo
                et_now = datetime.now(ZoneInfo('America/New_York'))
                tomorrow = et_now.date() + timedelta(days=1)
                # Skip to Monday if tomorrow is weekend
                while tomorrow.weekday() > 4:
                    tomorrow = tomorrow + timedelta(days=1)
                return tomorrow.strftime("%Y-%m-%d")
            except:
                # Final fallback if timezone fails
                tomorrow = datetime.now() + timedelta(days=1)
                return tomorrow.strftime("%Y-%m-%d")

    async def build_option_chain_with_pricing(
        self,
        ticker: str = "SPY",
        expiration_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build a complete option chain with live pricing data
        
        SPX options work directly with the regular options-contracts endpoint
        using "SPX" ticker - no special handling required.
        
        Args:
            ticker: Stock ticker symbol (supports "SPY", "SPX")
            expiration_date: Option expiration date (default: next trading day)
            
        Returns:
            Complete option chain with contracts and pricing
            
        Raises:
            ExternalAPIError: On API errors
        """
        if not expiration_date:
            expiration_date = await self.get_next_trading_day_expiration(ticker)
        
        try:
            logger.info(
                "Building option chain with pricing",
                ticker=ticker,
                expiration_date=expiration_date
            )

            # Get current underlying price FIRST - this is required
            try:
                underlying_price_data = await self.get_stock_price(ticker)
                current_underlying_price = underlying_price_data.get("price")

                if not current_underlying_price:
                    raise ExternalAPIError(
                        message=f"Unable to retrieve current {ticker} price. Option chain cannot be displayed without current price.",
                        service=self.service_name
                    )

                logger.info(f"Current {ticker} price: ${current_underlying_price:.2f}")

            except ExternalAPIError:
                # Re-raise if it's already our error
                raise
            except Exception as e:
                logger.error(f"Failed to get {ticker} price for option chain", error=str(e))
                raise ExternalAPIError(
                    message=f"Failed to retrieve current {ticker} price: {str(e)}. Option chain requires current price.",
                    service=self.service_name
                )

            # Get options contracts - SPX works directly with options-contracts endpoint
            # Use optimized fetching to get contracts around current price
            contracts_data = await self.get_options_contracts(
                underlying_ticker=ticker,  # Use SPX ticker directly
                expiration_date=expiration_date,
                fetch_all=False,  # Use optimization for faster fetching
                current_price=current_underlying_price,  # Pass the price we validated above
                target_strikes_around_price=30  # Target strikes around current price for analysis
            )
            
            logger.info(
                "Retrieved options contracts",
                ticker=ticker,
                expiration_date=expiration_date,
                total_results=len(contracts_data.get("results", []))
            )
            
            contracts = contracts_data.get("results", [])
            if not contracts:
                logger.warning(
                    "No options contracts found",
                    ticker=ticker,
                    expiration_date=expiration_date
                )
                return {
                    "ticker": ticker,
                    "expiration_date": expiration_date,
                    "contracts": [],
                    "total_contracts": 0,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            
            # Filter for call options only (as per overnight algorithm requirements)
            call_contracts = [
                contract for contract in contracts
                if contract.get("contract_type") == "call"
            ]
            
            logger.info(
                "Found call contracts",
                ticker=ticker,
                total_contracts=len(contracts),
                call_contracts=len(call_contracts)
            )
            
            # OPTIMIZATION: Limit API calls by only fetching pricing for near-the-money contracts
            # Current price already fetched above and validated - using current_underlying_price variable
            
            # Filter to only near-the-money contracts
            # For SPY: within $15 of current price
            # For SPX: Use adaptive range - all available strikes if deep ITM situation
            if ticker == "SPY":
                price_range = 15
                nearby_contracts = [
                    contract for contract in call_contracts
                    if abs(float(contract.get("strike_price", 0)) - current_underlying_price) <= price_range
                ]
            else:  # SPX
                # Check if we're in a deep ITM situation (all strikes significantly below current price)
                strike_prices = [float(contract.get("strike_price", 0)) for contract in call_contracts]
                max_available_strike = max(strike_prices) if strike_prices else 0
                
                # If the highest available strike is more than 1000 points below current price,
                # use all available strikes (deep ITM scenario)
                if max_available_strike > 0 and (current_underlying_price - max_available_strike) > 1000:
                    nearby_contracts = call_contracts  # Use all available strikes
                    price_range = current_underlying_price - min(strike_prices) if strike_prices else 0
                    logger.info(
                        "SPX deep ITM scenario detected - using all available strikes",
                        current_price=current_underlying_price,
                        max_available_strike=max_available_strike,
                        gap=current_underlying_price - max_available_strike,
                        total_strikes=len(call_contracts)
                    )
                else:
                    # Normal SPX filtering: within $1500 of current price
                    price_range = 1500
                    nearby_contracts = [
                        contract for contract in call_contracts
                        if abs(float(contract.get("strike_price", 0)) - current_underlying_price) <= price_range
                    ]
            
            logger.info(
                "Optimized contract selection",
                ticker=ticker,
                total_contracts=len(call_contracts),
                nearby_contracts=len(nearby_contracts),
                current_price=current_underlying_price,
                price_range=price_range,
                is_deep_itm_scenario=(ticker == "SPX" and len(nearby_contracts) == len(call_contracts))
            )
            
            # Enhance contracts with pricing data using batch API call
            enhanced_contracts = []

            # Prepare contracts for batch pricing
            # Use ticker-specific limits to balance performance and completeness
            # Since we're already filtering to single expiration date, we need to be selective
            if ticker == "SPY":
                max_contracts_to_price = 60  # SPY - reduced for faster processing
            else:  # SPX
                max_contracts_to_price = 40  # SPX - aggressive limit to avoid timeouts

            # For deepest ITM spread selection, prioritize ITM contracts (below current price)
            contracts_itm = [c for c in nearby_contracts if float(c.get("strike_price", 0)) < current_underlying_price]
            contracts_atm_otm = [c for c in nearby_contracts if float(c.get("strike_price", 0)) >= current_underlying_price]

            # For spread calculation, we need contracts that are close enough to form valid spreads
            # SPY: $1 spreads, SPX: $5 spreads
            spread_width = 1.0 if ticker == "SPY" else 5.0

            # Focus on ITM contracts that can form valid spreads
            # Sort ITM by strike (highest first - closest to current price)
            contracts_itm = sorted(contracts_itm, key=lambda x: float(x.get("strike_price", 0)), reverse=True)

            # Take enough ITM contracts to form spreads but not too many to timeout
            if ticker == "SPY":
                contracts_itm = contracts_itm[:40]  # Top 40 ITM strikes for SPY
            else:  # SPX
                contracts_itm = contracts_itm[:30]  # Top 30 ITM strikes for SPX

            # Include a few ATM/OTM for completeness
            contracts_to_price = contracts_itm + contracts_atm_otm[:min(10, len(contracts_atm_otm))]

            # Limit to max contracts to prevent timeout
            contracts_to_price = contracts_to_price[:max_contracts_to_price]

            # Log contract selection details
            logger.info(
                "Contract selection for pricing",
                ticker=ticker,
                itm_contracts=len(contracts_itm),
                atm_otm_contracts=len(contracts_atm_otm),
                contracts_to_price=len(contracts_to_price),
                max_allowed=max_contracts_to_price
            )

            # Extract option tickers for batch call
            option_tickers = [contract.get("ticker") for contract in contracts_to_price if contract.get("ticker")]

            if option_tickers:
                try:
                    # Fetch pricing data for all contracts
                    logger.info(
                        "Fetching batch pricing data",
                        ticker=ticker,
                        num_contracts=len(option_tickers)
                    )

                    # Get batch pricing data with concurrent requests
                    pricing_map = await self.get_batch_options_snapshot(option_tickers, ticker)

                    logger.info(
                        "Batch pricing data received",
                        contracts_requested=len(option_tickers),
                        contracts_received=len(pricing_map)
                    )

                    # Process each contract with its pricing data
                    # DON'T deduplicate here - the algorithm needs all contracts to select from
                    for contract in contracts_to_price:
                        option_ticker = contract.get("ticker")
                        if not option_ticker or option_ticker not in pricing_map:
                            continue

                        option_data = pricing_map[option_ticker]

                        # Extract pricing data
                        bid = float(option_data.get("bid", 0))
                        ask = float(option_data.get("ask", 0))

                        if bid == 0 and ask == 0:
                            continue

                        # Extract other data
                        volume = option_data.get("volume", 0)
                        open_interest = option_data.get("open_interest", 0)
                        implied_vol = option_data.get("implied_volatility")
                        iv_source = "api" if implied_vol else "unavailable"

                        # For SPX, consider Black-Scholes approximation if needed
                        if implied_vol is None and ticker.upper() == "SPX" and bid > 0 and ask > 0:
                            try:
                                market_price = (bid + ask) / 2.0
                                strike_price = float(contract.get("strike_price", 0))
                                exp_date = contract.get("expiration_date", expiration_date)

                                if strike_price > 0 and exp_date and current_underlying_price > 0:
                                    time_to_exp = BlackScholesCalculator.calculate_time_to_expiration(exp_date)

                                    if time_to_exp and time_to_exp > 0:
                                        approx_iv = BlackScholesCalculator.approximate_implied_volatility(
                                            market_price=market_price,
                                            S=current_underlying_price,
                                            K=strike_price,
                                            T=time_to_exp,
                                            r=0.05
                                        )

                                        if approx_iv is not None:
                                            implied_vol = approx_iv
                                            iv_source = "black_scholes_approximation"
                            except Exception as bs_error:
                                logger.debug(f"Black-Scholes IV calculation failed: {str(bs_error)}")

                        # Create enhanced contract
                        strike = float(contract.get("strike_price", 0))

                        enhanced_contract = {
                            "strike": strike,
                            "bid": bid,
                            "ask": ask,
                            "volume": volume,
                            "open_interest": open_interest,
                            "implied_volatility": implied_vol,
                            "iv_source": iv_source,
                            "contract_ticker": option_ticker,
                            "expiration_date": contract.get("expiration_date"),
                            "last_updated": datetime.utcnow().isoformat() + "Z",
                            "is_highlighted": None
                        }

                        enhanced_contracts.append(enhanced_contract)

                except Exception as batch_error:
                    logger.error(
                        "Failed to process batch pricing data, falling back to sequential calls",
                        error=str(batch_error),
                        ticker=ticker
                    )

                    # Fallback to sequential API calls if batch fails
                    for contract in contracts_to_price[:20]:  # Limit to 20 for fallback
                        try:
                            option_ticker = contract.get("ticker")
                            if not option_ticker:
                                continue

                            pricing_data = await self.get_options_snapshot(ticker, option_ticker)

                            if pricing_data and pricing_data.get("results"):
                                results = pricing_data.get("results", {})
                                last_quote = results.get("last_quote", {})

                                bid = float(last_quote.get("bid", 0)) if last_quote.get("bid") else 0
                                ask = float(last_quote.get("ask", 0)) if last_quote.get("ask") else 0

                                if bid > 0 or ask > 0:
                                    enhanced_contract = {
                                        "strike": float(contract.get("strike_price", 0)),
                                        "bid": bid,
                                        "ask": ask,
                                        "volume": 0,
                                        "open_interest": 0,
                                        "implied_volatility": None,
                                        "iv_source": "unavailable",
                                        "contract_ticker": option_ticker,
                                        "expiration_date": contract.get("expiration_date"),
                                        "last_updated": datetime.utcnow().isoformat() + "Z",
                                        "is_highlighted": None
                                    }
                                    enhanced_contracts.append(enhanced_contract)

                            await asyncio.sleep(0.1)  # Small delay between calls

                        except Exception as fallback_error:
                            logger.debug(f"Fallback pricing failed for {contract.get('ticker')}: {str(fallback_error)}")
                            continue
            else:
                logger.info("No option tickers to price")

            logger.info(
                "Option pricing enhancement completed",
                contracts_enhanced=len(enhanced_contracts),
                total_attempted=len(contracts_to_price)
            )
            
            # Sort by strike price
            enhanced_contracts.sort(key=lambda x: x["strike"])
            
            result = {
                "ticker": ticker,
                "expiration_date": expiration_date,
                "contracts": enhanced_contracts,
                "total_contracts": len(enhanced_contracts),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(
                "Option chain built successfully",
                ticker=ticker,
                expiration_date=expiration_date,
                enhanced_contracts=len(enhanced_contracts)
            )
            
            return result
            
        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error(
                "Failed to build option chain",
                ticker=ticker,
                expiration_date=expiration_date,
                error=str(e)
            )
            raise ExternalAPIError(
                message=f"Failed to build option chain for {ticker}: {str(e)}",
                service=self.service_name
            )

    def _aggregate_candles(
        self,
        candles: List[Dict[str, Any]],
        interval: str
    ) -> List[Dict[str, Any]]:
        """
        Aggregate 1-minute candles into specified intervals
        
        Args:
            candles: List of 1-minute OHLCV candles (sorted chronologically)
            interval: Target interval ("1m", "5m", "15m")
            
        Returns:
            List of aggregated candles with proper OHLCV values
        """
        if not candles or interval == "1m":
            return candles
        
        # Determine aggregation factor
        if interval == "5m":
            group_size = 5
        elif interval == "15m":
            group_size = 15
        else:
            logger.warning(f"Unsupported interval {interval}, returning 1m data")
            return candles
        
        logger.info(
            "Aggregating candles",
            original_count=len(candles),
            interval=interval,
            group_size=group_size
        )
        
        aggregated_candles = []
        
        # Group candles by the specified interval
        for i in range(0, len(candles), group_size):
            group = candles[i:i + group_size]
            
            if not group:
                continue
            
            # Skip incomplete groups at the end if they have less than half the expected size
            # This helps avoid partial intervals that might be misleading
            if len(group) < max(1, group_size // 2):
                logger.debug(f"Skipping incomplete group of {len(group)} candles")
                continue
            
            try:
                # Extract OHLCV values with null safety
                opens = []
                highs = []
                lows = []
                closes = []
                volumes = []
                
                for candle in group:
                    if not isinstance(candle, dict):
                        continue
                    
                    # Safely extract numeric values
                    try:
                        open_val = float(candle.get("open", 0))
                        high_val = float(candle.get("high", 0))
                        low_val = float(candle.get("low", 0))
                        close_val = float(candle.get("close", 0))
                        volume_val = int(candle.get("volume", 0))
                        
                        # Only include valid candles (non-zero OHLC)
                        if all([open_val, high_val, low_val, close_val]):
                            opens.append(open_val)
                            highs.append(high_val)
                            lows.append(low_val)
                            closes.append(close_val)
                            volumes.append(volume_val)
                            
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Skipping invalid candle data: {e}")
                        continue
                
                # Skip group if no valid candles found
                if not opens:
                    logger.debug(f"No valid candles in group starting at index {i}")
                    continue
                
                # Aggregate according to OHLCV rules:
                # - Open: First candle's open
                # - High: Maximum high in the group  
                # - Low: Minimum low in the group
                # - Close: Last candle's close
                # - Volume: Sum of all volumes
                # - Timestamp: Use first candle's timestamp
                aggregated_candle = {
                    "timestamp": group[0]["timestamp"],  # First candle's timestamp
                    "open": opens[0],                    # First open
                    "high": max(highs),                  # Maximum high
                    "low": min(lows),                    # Minimum low
                    "close": closes[-1],                 # Last close
                    "volume": sum(volumes)               # Sum of volumes
                }
                
                aggregated_candles.append(aggregated_candle)
                
            except Exception as e:
                logger.warning(
                    f"Failed to aggregate candle group at index {i}: {str(e)}"
                )
                continue
        
        logger.info(
            "Candle aggregation completed",
            original_count=len(candles),
            aggregated_count=len(aggregated_candles),
            interval=interval,
            group_size=group_size
        )
        
        return aggregated_candles

    async def get_isin_chart_data(
        self,
        ticker: str,
        isin: str,
        interval: str = "1m"
    ) -> Dict[str, Any]:
        """
        Get intraday chart data from ISIN-data endpoint with candle aggregation support
        
        This method fetches intraday data from the ISIN-data endpoint which provides
        1-minute interval OHLCV data for the current trading day only (real-time data).
        For 5m and 15m intervals, it aggregates the 1-minute data accordingly.
        
        Supported intervals:
        - "1m": Returns 1-minute candles as-is (~394 candles)
        - "5m": Aggregates every 5 consecutive 1-minute candles (~79 candles) 
        - "15m": Aggregates every 15 consecutive 1-minute candles (~26 candles)
        
        Args:
            ticker: Stock ticker symbol (e.g., "SPY", "SPX")
            isin: ISIN code for the instrument
            interval: Time interval ("1m", "5m", "15m")
        
        Returns:
            Dictionary containing aggregated OHLCV data formatted for chart display
            
        Raises:
            ExternalAPIError: On API errors or data processing failures
        """
        endpoint = "/v3/data/isin-data"
        
        # For real-time data, use ISIN endpoint without date parameters
        # This returns only today's current trading day data (no future data)
        params = {
            "isin": isin,  # Use the provided ISIN
            "type": "intraday"  # Request intraday data for 1-minute intervals
        }
        
        # Validate interval - only support 1m, 5m, 15m
        valid_intervals = {"1m", "5m", "15m"}
        if interval not in valid_intervals:
            logger.warning(
                f"Invalid interval {interval} for {ticker} chart data, defaulting to 1m",
                valid_intervals=list(valid_intervals)
            )
            interval = "1m"

        try:
            logger.info(
                "Fetching intraday chart data via ISIN-data endpoint",
                ticker=ticker,
                isin=isin,
                type="intraday",
                interval=interval,
                requires_aggregation=(interval != "1m"),
                real_time_only=True
            )
            
            # Check cache first with interval-specific key for intraday data
            cache_key = f"{ticker.lower()}_intraday_data:{interval}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                logger.info("Using cached intraday chart data", ticker=ticker, interval=interval)
                return cached_data
            
            # Fetch fresh data from ISIN-data endpoint
            raw_data = await self.get(endpoint, params=params)
            
            # Expected response format for intraday data:
            # {n: "Instrument Name", id: xxxxxx, isin: "ISINxxxxxx", currency: null, 
            #  quotes: [{t: 1756764000, o: 6405.614, h: 6420.653, l: 6364.661, c: 6419.653, v: 4784000000}, ...]}
            # Note: With type:"intraday", we expect many more data points (1-minute intervals)
            
            price_data = []
            current_price = 0.0
            
            # Extract quotes array
            quotes = raw_data.get("quotes", [])
            if not isinstance(quotes, list):
                quotes = []
            
            for quote in quotes:
                if not isinstance(quote, dict):
                    continue
                
                # Extract OHLCV data
                timestamp_raw = quote.get("t")
                if timestamp_raw:
                    # Handle both Unix timestamp and ISO string formats
                    try:
                        if isinstance(timestamp_raw, str):
                            # It's already an ISO string, use it directly
                            if "T" in timestamp_raw:  # ISO format check
                                timestamp = timestamp_raw
                            else:
                                # Try to parse as Unix timestamp string
                                timestamp_seconds = int(timestamp_raw)
                                timestamp = datetime.fromtimestamp(timestamp_seconds).isoformat() + "Z"
                        else:
                            # Numeric timestamp (int or float)
                            timestamp = datetime.fromtimestamp(timestamp_raw).isoformat() + "Z"
                    except (ValueError, TypeError):
                        continue
                else:
                    continue
                
                open_price = float(quote.get("o", 0))
                high_price = float(quote.get("h", 0))
                low_price = float(quote.get("l", 0))
                close_price = float(quote.get("c", 0))
                # Volume may not be available for intraday data
                volume = int(quote.get("v", 0)) if "v" in quote else 0
                
                # Skip invalid bars (volume is optional)
                if not all([open_price, high_price, low_price, close_price]):
                    continue
                
                price_point = {
                    "timestamp": timestamp,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume
                }
                
                price_data.append(price_point)
                current_price = close_price  # Use most recent close as current price
            
            # Sort by timestamp to ensure chronological order
            price_data.sort(key=lambda x: x["timestamp"])
            
            logger.info(
                "Raw 1-minute data processed",
                raw_candles=len(price_data),
                interval=interval,
                will_aggregate=(interval != "1m")
            )
            
            # Apply candle aggregation if needed
            if interval != "1m" and price_data:
                original_count = len(price_data)
                price_data = self._aggregate_candles(price_data, interval)
                
                # Update current_price from aggregated data
                if price_data:
                    current_price = price_data[-1]["close"]
                
                logger.info(
                    "Candle aggregation applied",
                    original_candles=original_count,
                    aggregated_candles=len(price_data),
                    interval=interval,
                    current_price=current_price
                )
            
            # If no current price from data, use fallback based on ticker
            if current_price == 0.0:
                fallback_prices = {
                    "SPY": 585.0,   # SPY fallback price
                    "SPX": 6400.0   # SPX fallback price
                }
                current_price = fallback_prices.get(ticker, 500.0)  # Default fallback
            
            # Create benchmark lines (current price and placeholder strikes)
            benchmark_lines = {
                "current_price": current_price,
                "buy_strike": None,
                "sell_strike": None
            }
            
            # Create metadata
            metadata = {
                "total_candles": len(price_data),  # Reflects actual count after aggregation
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "interval": interval,  # Reflects requested interval
                "period": "1d",  # Always 1d for intraday data
                "data_type": "intraday",
                "aggregation_applied": (interval != "1m"),
                "source_resolution": "1m",  # Source data is always 1-minute from API
                "real_time_only": True,  # No future data, only current trading day
                "ticker": ticker,
                "isin": isin
            }
            
            normalized_data = {
                "price_data": price_data,
                "current_price": current_price,
                "benchmark_lines": benchmark_lines,
                "metadata": metadata,
                "interval": interval,  # Use the actual interval passed in
                "period": "1d"  # Always 1d for intraday data
            }
            
            # Cache the result for 30 seconds (shorter TTL for intraday data)
            self._set_cache(cache_key, normalized_data, ttl=30)
            
            logger.info(
                "Intraday chart data retrieved successfully via ISIN-data",
                ticker=ticker,
                data_points=len(price_data),
                current_price=current_price,
                interval=interval,
                data_type="intraday",
                aggregation_applied=(interval != "1m"),
                source_resolution="1m",
                real_time_only=True
            )
            
            return normalized_data
            
        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error("Failed to get intraday chart data", ticker=ticker, error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get {ticker} chart data: {str(e)}",
                service=self.service_name
            )
    
    async def get_intraday_data(
        self,
        ticker: str,
        interval: str = "5m",
        period: str = "1d"
    ) -> Dict[str, Any]:
        """
        Get intraday OHLCV data for chart display
        
        Routes SPY and SPX to ISIN-data endpoint for real-time data only.
        Uses regular TheTradeList range-data endpoint for XSP only.
        
        Args:
            ticker: Stock ticker symbol (e.g., "SPY", "SPX", "XSP")
            interval: Time interval ("1m", "5m", "15m", "30m", "1h")
            period: Time period ("1d", "5d", "1w")
            
        Returns:
            Dictionary containing OHLCV data formatted for chart display
            
        Raises:
            ExternalAPIError: On API errors or data processing failures
        """
        # Validate ticker
        supported_tickers = {"SPY", "XSP", "SPX"}
        ticker_upper = ticker.upper()
        
        if ticker_upper not in supported_tickers:
            raise ExternalAPIError(
                message=f"Ticker {ticker} not supported for intraday data. Supported: {', '.join(supported_tickers)}",
                service=self.service_name
            )
        
        # Define ISIN codes for supported tickers
        isin_codes = {
            "SPY": "US78462F1030",  # SPY ISIN
            "SPX": "US78378X1072"   # SPX ISIN
        }
        
        # Route SPY and SPX to the ISIN-data endpoint for real-time intraday data
        if ticker_upper in isin_codes:
            logger.info(
                "Routing to ISIN-data endpoint for real-time intraday chart data",
                ticker=ticker_upper,
                isin=isin_codes[ticker_upper],
                requested_interval=interval,
                requested_period=period,
                endpoint="isin-data",
                data_type="intraday",
                real_time_only=True
            )
            
            # Use the new generic ISIN endpoint
            chart_data = await self.get_isin_chart_data(
                ticker=ticker_upper,
                isin=isin_codes[ticker_upper],
                interval=interval
            )
            
            # Add ticker to the response for consistency
            chart_data["ticker"] = ticker_upper
            return chart_data
        
        # Handle XSP using range-data endpoint (only remaining ticker)
        if ticker_upper == "XSP":
            # Validate interval for XSP
            valid_intervals = {"1m", "5m", "15m", "30m", "1h"}
            if interval not in valid_intervals:
                logger.warning(f"Invalid interval {interval} for XSP, defaulting to 5m")
                interval = "5m"
            
            # Validate period for XSP
            valid_periods = {"1d", "5d", "1w"}
            if period not in valid_periods:
                logger.warning(f"Invalid period {period} for XSP, defaulting to 1d")
                period = "1d"
            
            # Map intervals to TheTradeList API format
            interval_mapping = {
                "1m": "1/minute",
                "5m": "5/minute",
                "15m": "15/minute", 
                "30m": "30/minute",
                "1h": "1/hour"
            }
            
            try:
                logger.info(
                    "Fetching XSP intraday data using range-data endpoint",
                    ticker=ticker_upper,
                    interval=interval,
                    period=period
                )
                
                # Calculate date range based on period using ET timezone
                try:
                    import pytz
                    et_tz = pytz.timezone('America/New_York')
                    end_date = datetime.now(et_tz).replace(tzinfo=None)
                    logger.info(f"Using ET timezone for XSP intraday date range: {end_date}")
                except ImportError:
                    end_date = datetime.now()
                    logger.warning("pytz not available, using local time for XSP intraday date range")
                    
                if period == "1d":
                    start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                elif period == "5d":
                    start_date = end_date - timedelta(days=5)
                elif period == "1w":
                    start_date = end_date - timedelta(weeks=1)
                else:
                    start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Use TheTradeList range-data endpoint for XSP
                endpoint = "/v1/data/range-data"
                params = {
                    "ticker": ticker_upper,
                    "range": interval_mapping[interval],
                    "startdate": start_date.strftime("%Y-%m-%d"),
                    "enddate": end_date.strftime("%Y-%m-%d"),
                    "limit": 200
                }
                
                # Use caching for intraday data
                cache_key = f"intraday_data:{ticker_upper}:{interval}:{period}"
                cached_data = self._get_from_cache(cache_key)
                if cached_data is not None:
                    logger.info("Using cached XSP intraday data", ticker=ticker_upper, interval=interval, period=period)
                    return cached_data
                
                # Fetch fresh data from range-data endpoint
                logger.info(
                    "Fetching XSP intraday data from TheTradeList range-data endpoint",
                    ticker=ticker_upper,
                    endpoint=endpoint,
                    data_type="time_series"
                )
                
                raw_data = await self.get(endpoint, params=params)
                
                # Normalize the response
                normalized_data = self._normalize_intraday_data(raw_data, ticker_upper, interval, period)
                
                # Cache the result for 90 seconds
                self._set_cache(cache_key, normalized_data, ttl=90)
                
                logger.info(
                    "XSP intraday data retrieved successfully",
                    ticker=ticker_upper,
                    interval=interval,
                    period=period,
                    data_points=len(normalized_data.get("price_data", [])),
                    endpoint_used=endpoint,
                    data_source="range_data_endpoint"
                )
                
                return normalized_data
                
            except ExternalAPIError:
                raise
            except Exception as e:
                logger.error(
                    "Failed to get XSP intraday data",
                    ticker=ticker,
                    interval=interval,
                    period=period,
                    error=str(e)
                )
                raise ExternalAPIError(
                    message=f"Failed to get XSP intraday data: {str(e)}",
                    service=self.service_name
                )
        
        # This should not happen as we validate supported tickers above
        raise ExternalAPIError(
            message=f"Unsupported ticker {ticker_upper} reached end of method",
            service=self.service_name
        )
    
    def _normalize_intraday_data(
        self,
        raw_data: Dict[str, Any],
        ticker: str,
        interval: str,
        period: str
    ) -> Dict[str, Any]:
        """
        Normalize TheTradeList range-data response for intraday chart display
        
        This method is now only used for XSP ticker. SPY and SPX use the ISIN-data 
        endpoint with different normalization logic in get_isin_chart_data().
        
        Args:
            raw_data: Raw API response from TheTradeList range-data endpoint
            ticker: Stock ticker symbol (should be "XSP")
            interval: Time interval
            period: Time period
            
        Returns:
            Normalized intraday data for frontend consumption
        """
        try:
            results = raw_data.get("results", [])
            if not isinstance(results, list):
                results = []
            
            price_data = []
            current_price = 0.0
            
            for bar in results:
                if not isinstance(bar, dict):
                    continue
                    
                # Extract OHLCV data from TheTradeList format
                # Fields: t (timestamp), o (open), h (high), l (low), c (close), v (volume)
                timestamp_ms = bar.get("t", 0)
                if timestamp_ms:
                    # Convert milliseconds to ISO format
                    timestamp = datetime.fromtimestamp(timestamp_ms / 1000).isoformat() + "Z"
                else:
                    continue
                
                open_price = float(bar.get("o", 0))
                high_price = float(bar.get("h", 0))
                low_price = float(bar.get("l", 0))
                close_price = float(bar.get("c", 0))
                volume = int(bar.get("v", 0))
                
                # Skip invalid bars
                if not all([open_price, high_price, low_price, close_price]):
                    continue
                
                price_point = {
                    "timestamp": timestamp,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume
                }
                
                price_data.append(price_point)
                current_price = close_price  # Use most recent close as current price
            
            # Sort by timestamp to ensure chronological order
            price_data.sort(key=lambda x: x["timestamp"])
            
            # Note: We use the last close price from historical data instead of making 
            # an async call to get_stock_price here since this is a sync method.
            # Current price will be fetched separately by the calling code if needed.
            
            # If no current price from data, use fallback based on ticker
            if current_price == 0.0:
                current_price = 585.0 if ticker == "SPY" else 5850.0  # Fallback prices
            
            # Create benchmark lines (current price and placeholder strikes)
            benchmark_lines = {
                "current_price": current_price,
                "buy_strike": None,  # Will be set by calling code if provided
                "sell_strike": None   # Will be set by calling code if provided
            }
            
            # Create metadata
            # Ensure interval reflects actual data granularity
            metadata = {
                "total_candles": len(price_data),
                "market_hours": "09:30-16:00 ET",
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "interval": interval
            }
            
            normalized = {
                "ticker": ticker,
                "interval": interval,
                "period": period,
                "current_price": current_price,
                "price_data": price_data,
                "benchmark_lines": benchmark_lines,
                "metadata": metadata
            }
            
            return normalized
            
        except Exception as e:
            logger.error("Failed to normalize intraday data", error=str(e))
            # Return empty but valid structure
            return {
                "ticker": ticker,
                "interval": interval,
                "period": period,
                "current_price": 0.0,
                "price_data": [],
                "benchmark_lines": {
                    "current_price": 0.0,
                    "buy_strike": None,
                    "sell_strike": None
                },
                "metadata": {
                    "total_candles": 0,
                    "market_hours": "09:30-16:00 ET",
                    "last_updated": datetime.utcnow().isoformat() + "Z"
                },
                "error": str(e)
            }
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache with proper key formatting"""
        try:
            full_key = f"external_api:{self.service_name}:{cache_key}"
            return redis_cache.get(full_key)
        except Exception as e:
            logger.warning("Cache get failed", key=cache_key, error=str(e))
            return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any], ttl: int = 60) -> None:
        """Set data in cache with proper key formatting"""
        try:
            full_key = f"external_api:{self.service_name}:{cache_key}"
            redis_cache.set(full_key, data, ttl)
        except Exception as e:
            logger.warning("Cache set failed", key=cache_key, error=str(e))
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for TheTradeList API"""
        try:
            # Try a simple API call to check connectivity
            await self.validate_ticker("AAPL")
            
            return {
                "service": self.service_name,
                "status": "healthy",
                "api_key_configured": bool(self.api_key),
                "base_url": self.base_url
            }
        except Exception as e:
            return {
                "service": self.service_name,
                "status": "unhealthy", 
                "error": str(e),
                "api_key_configured": bool(self.api_key),
                "base_url": self.base_url
            }


# Singleton instance
_thetradelist_service: Optional[TheTradeListService] = None


def get_thetradelist_service() -> TheTradeListService:
    """Get singleton TheTradeList service instance"""
    global _thetradelist_service
    if _thetradelist_service is None:
        _thetradelist_service = TheTradeListService()
    return _thetradelist_service