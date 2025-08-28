import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.services.external.base import ExternalAPIService, ExternalAPIError
from app.core.config import settings
from app.core.logging import get_logger
from app.core.cache import redis_cache


logger = get_logger(__name__)


class TheTradeListService(ExternalAPIService):
    """
    TheTradeList API integration service
    
    Provides access to real-time market data including:
    - Snapshot Locale endpoint for real-time market data
    - Grouped Locale endpoint for market statistics
    - Reference Ticker endpoint for ticker validation
    
    Features:
    - Automatic rate limiting and retry logic
    - Response caching with configurable TTL
    - Comprehensive error handling
    - Data normalization for consistent output
    """
    
    def __init__(self):
        config = settings.get_external_api_config("thetradelist")
        
        super().__init__(
            service_name="thetradelist",
            base_url=config.get("base_url", "https://api.thetradelist.com"),
            api_key=config.get("api_key"),
            timeout=config.get("timeout", 10),
            max_retries=config.get("retry_count", 3),
            rate_limit=5.0,  # 5 calls per second
            cache_ttl=config.get("cache_ttl", 30)  # 30 seconds
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
                    
                ticker_info = {
                    "ticker": ticker_data.get("ticker", ""),
                    "price": day.get("c", 0),  # close price
                    "change": ticker_data.get("todaysChange", 0),
                    "change_percent": ticker_data.get("todaysChangePerc", 0),
                    "volume": day.get("v", 0),  # volume
                    "high": day.get("h", 0),    # high
                    "low": day.get("l", 0),     # low  
                    "open": day.get("o", 0),    # open
                    "previous_close": prev_day.get("c", 0)  # previous close
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
    
    async def get_stock_price(self, ticker: str) -> Dict[str, Any]:
        """
        Get current price for a single stock ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., "SPY", "XSP", "SPX")
            
        Returns:
            Stock price data with normalized format
            
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
            
            # Use existing market snapshot method with specific ticker
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
        
        Args:
            tickers: List of stock ticker symbols (e.g., ["SPY", "XSP", "SPX"])
            
        Returns:
            Multiple stock prices data with normalized format
            
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
            
            # Create ticker string for API call
            tickers_string = ",".join(tickers_upper) + ","
            
            # Use existing market snapshot method
            snapshot_data = await self.get_market_snapshot(tickers=tickers_string)
            
            # Extract and normalize ticker data
            api_tickers = snapshot_data.get("tickers", [])
            if not api_tickers:
                raise ExternalAPIError(
                    message="No price data found for requested tickers",
                    service=self.service_name
                )
            
            # Process each ticker and create normalized response
            prices = []
            found_tickers = set()
            
            for ticker_info in api_tickers:
                if not isinstance(ticker_info, dict):
                    continue
                    
                ticker_symbol = ticker_info.get("ticker", "")
                if ticker_symbol in tickers_upper:
                    normalized_data = {
                        "ticker": ticker_symbol,
                        "price": float(ticker_info.get("price", 0)),
                        "change": float(ticker_info.get("change", 0)),
                        "change_percent": float(ticker_info.get("change_percent", 0)),
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    prices.append(normalized_data)
                    found_tickers.add(ticker_symbol)
            
            # Check if any requested tickers were missing
            missing_tickers = set(tickers_upper) - found_tickers
            if missing_tickers:
                logger.warning("Some tickers not found in API response", missing=list(missing_tickers))
            
            result = {"prices": prices}
            
            logger.info(
                "Multiple stock prices retrieved successfully",
                requested_count=len(tickers_upper),
                found_count=len(prices),
                tickers=tickers_upper
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