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

    async def get_stock_price(self, ticker: str) -> Dict[str, Any]:
        """
        Get current price for a single stock ticker
        
        ISIN endpoint is used ONLY for SPX current price (single data point).
        Regular snapshot endpoint is used for all other tickers and purposes.
        
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
            
            # Route SPX to ISIN endpoint for CURRENT PRICE ONLY
            # (ISIN only provides single price point, not time series)
            if ticker_upper == "SPX":
                return await self.get_spx_price_via_isin()
            
            # Use existing market snapshot method for SPY and XSP
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
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Get options contracts for a specific underlying ticker
        
        SPX options work directly with the options-contracts endpoint using "SPX" ticker.
        No special handling or routing required.
        
        Args:
            underlying_ticker: The stock symbol (e.g., "SPY", "SPX")
            expiration_date: Optional specific expiration date filter (YYYY-MM-DD)
            limit: Maximum number of results (default: 1000)
            
        Returns:
            Dictionary containing options contracts data
            
        Raises:
            ExternalAPIError: On API errors
        """
        endpoint = "/v1/data/options-contracts"
        params = {
            "underlying_ticker": underlying_ticker.upper(),  # SPX works directly
            "limit": limit
        }
        
        try:
            logger.info(
                "Fetching options contracts",
                underlying_ticker=underlying_ticker.upper(),
                expiration_date=expiration_date,
                limit=limit,
                endpoint=endpoint
            )
            
            raw_data = await self.get(endpoint, params=params, use_cache=True, cache_ttl=300)  # Cache for 5 minutes
            
            # Filter by expiration date if provided
            if expiration_date and "results" in raw_data:
                filtered_results = [
                    contract for contract in raw_data.get("results", [])
                    if contract.get("expiration_date") == expiration_date
                ]
                raw_data["results"] = filtered_results
                raw_data["resultsCount"] = len(filtered_results)
            
            logger.info(
                "Options contracts retrieved successfully",
                underlying_ticker=underlying_ticker.upper(),
                total_contracts=len(raw_data.get("results", [])),
                expiration_filter=expiration_date
            )
            
            return raw_data
            
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
            
            raw_data = await self.get(endpoint, params=params, use_cache=True, cache_ttl=30)  # Cache for 30 seconds
            
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
            
            raw_data = await self.get(endpoint, params=params, use_cache=True, cache_ttl=30)  # Cache for 30 seconds
            
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
        For SPX: Looks for nearest available expiration (weekly/monthly options)
        
        Args:
            ticker: The ticker symbol to get expiration for (e.g., "SPY", "SPX")
        
        Returns:
            Next available expiration date in YYYY-MM-DD format
        """
        ticker = ticker.upper()
        
        try:
            logger.info("Getting next available expiration from API", ticker=ticker)
            
            # Get all available option contracts for the specified ticker
            contracts_data = await self.get_options_contracts(
                underlying_ticker=ticker,
                limit=1000
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
                import pytz
                et_tz = pytz.timezone('America/New_York')
                today_et = datetime.now(et_tz).strftime('%Y-%m-%d')
                today = today_et
                logger.info(f"Using ET timezone for date comparison: {today_et}")
            except ImportError:
                # Fallback if pytz not available
                today = datetime.now().strftime('%Y-%m-%d')
                logger.warning("pytz not available, using local time for comparison")
            
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
        
        Returns:
            Next trading day date in YYYY-MM-DD format
        """
        try:
            today = datetime.now()
            next_day = today + timedelta(days=1)
            
            # Skip weekends
            while next_day.weekday() > 4:  # 5=Saturday, 6=Sunday
                next_day = next_day + timedelta(days=1)
            
            return next_day.strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.error("Failed to calculate fallback trading day", error=str(e))
            # Ultimate fallback to tomorrow
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
            
            # Get options contracts - SPX works directly with options-contracts endpoint
            contracts_data = await self.get_options_contracts(
                underlying_ticker=ticker,  # Use SPX ticker directly
                expiration_date=expiration_date
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
            # Get current underlying price first (single API call)
            try:
                underlying_price_data = await self.get_stock_price(ticker)
                current_underlying_price = underlying_price_data.get("price", 585.0 if ticker == "SPY" else 5850.0)
            except:
                # Fallback prices based on ticker
                current_underlying_price = 585.0 if ticker == "SPY" else 5850.0
            
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
            
            # Enhance contracts with pricing data (limited set with error handling)
            enhanced_contracts = []
            
            # Only fetch pricing for nearby contracts (max 20 to prevent excessive API calls)
            contracts_to_price = nearby_contracts[:20]
            
            # Track API call success/failure for circuit breaker
            pricing_failures = 0
            max_failures = 5  # Stop fetching if too many failures
            
            for i, contract in enumerate(contracts_to_price):
                try:
                    # Circuit breaker: stop if too many failures
                    if pricing_failures >= max_failures:
                        logger.warning(
                            "Too many pricing API failures, stopping option chain enhancement",
                            failures=pricing_failures,
                            contracts_processed=i
                        )
                        break
                    
                    option_ticker = contract.get("ticker")
                    if not option_ticker:
                        logger.debug("Skipping contract with missing ticker")
                        continue
                    
                    # Get pricing snapshot for this contract with timeout protection
                    pricing_data = await self.get_options_snapshot(ticker, option_ticker)
                    
                    if not pricing_data or not pricing_data.get("results"):
                        pricing_failures += 1
                        logger.debug(
                            "Empty pricing data for contract",
                            option_ticker=option_ticker
                        )
                        continue
                    
                    # Extract relevant pricing information
                    results = pricing_data.get("results", {})
                    last_quote = results.get("last_quote", {})
                    day_data = results.get("day", {})
                    details = results.get("details", {})
                    
                    # Debug: Log the structure to see if IV is available
                    logger.debug(
                        "Option pricing data structure",
                        option_ticker=option_ticker,
                        results_keys=list(results.keys()) if results else [],
                        last_quote_keys=list(last_quote.keys()) if last_quote else [],
                        details_keys=list(details.keys()) if details else []
                    )
                    
                    # Validate that we have usable pricing data with proper null handling
                    bid_raw = last_quote.get("bid")
                    ask_raw = last_quote.get("ask")
                    
                    # Handle None values and convert to float safely
                    try:
                        bid = float(bid_raw) if bid_raw is not None else 0.0
                    except (ValueError, TypeError):
                        bid = 0.0
                    
                    try:
                        ask = float(ask_raw) if ask_raw is not None else 0.0
                    except (ValueError, TypeError):
                        ask = 0.0
                    
                    if bid == 0 and ask == 0:
                        logger.debug(
                            "No pricing data available for contract",
                            option_ticker=option_ticker,
                            bid_raw=bid_raw,
                            ask_raw=ask_raw
                        )
                        pricing_failures += 1
                        continue
                    
                    # Enhanced implied volatility extraction with SPX fallback logic
                    implied_vol = None  # Start with None to indicate unavailable data
                    iv_source = "unavailable"
                    
                    # Check multiple possible field names for IV
                    iv_fields_to_try = [
                        ('last_quote', 'implied_volatility'),
                        ('last_quote', 'iv'), 
                        ('details', 'implied_volatility'),
                        ('details', 'iv'),
                        ('greeks', 'implied_volatility'),
                        ('greeks', 'iv'),
                        ('results', 'implied_volatility'),
                        ('results', 'iv')
                    ]
                    
                    # Try to extract IV from API data first
                    for source, field in iv_fields_to_try:
                        source_data = {'last_quote': last_quote, 'details': details, 'greeks': results.get('greeks', {}), 'results': results}.get(source, {})
                        if isinstance(source_data, dict) and field in source_data:
                            try:
                                iv_value = float(source_data.get(field, 0))
                                if iv_value > 0:  # Only use if it's a positive value
                                    implied_vol = iv_value
                                    iv_source = f"{source}.{field}"
                                    logger.info(f"Found IV {iv_value} in {iv_source} for {option_ticker}")
                                    break
                            except (ValueError, TypeError):
                                continue
                    
                    # If no IV found from API and this is SPX, try Black-Scholes approximation
                    if implied_vol is None and ticker.upper() == "SPX":
                        try:
                            # Calculate IV using Black-Scholes approximation with null safety
                            # Ensure bid and ask are valid numbers before calculating midpoint
                            if (bid is not None and ask is not None and 
                                isinstance(bid, (int, float)) and isinstance(ask, (int, float)) and
                                bid > 0 and ask > 0):
                                market_price = (bid + ask) / 2.0
                            else:
                                market_price = 0.0
                            
                            if market_price > 0:
                                # Extract strike price with null safety
                                strike_raw = details.get("strike_price", contract.get("strike_price"))
                                try:
                                    strike_price = float(strike_raw) if strike_raw is not None else 0.0
                                except (ValueError, TypeError):
                                    strike_price = 0.0
                                
                                exp_date = contract.get("expiration_date", expiration_date)
                                
                                # Add comprehensive null checks before Black-Scholes calculation
                                if (strike_price is not None and strike_price > 0 and 
                                    exp_date is not None and 
                                    current_underlying_price is not None and current_underlying_price > 0):
                                    
                                    # Calculate time to expiration
                                    time_to_exp = BlackScholesCalculator.calculate_time_to_expiration(exp_date)
                                    
                                    # Validate all parameters are not None and have valid values
                                    if (time_to_exp is not None and time_to_exp > 0 and 
                                        market_price is not None and market_price > 0):
                                        
                                        logger.debug(
                                            f"Black-Scholes parameters validated for {option_ticker}",
                                            market_price=market_price,
                                            current_underlying_price=current_underlying_price,
                                            strike_price=strike_price,
                                            time_to_exp=time_to_exp,
                                            risk_free_rate=0.05
                                        )
                                        
                                        # Approximate IV using Black-Scholes
                                        approx_iv = BlackScholesCalculator.approximate_implied_volatility(
                                            market_price=market_price,
                                            S=current_underlying_price,
                                            K=strike_price,
                                            T=time_to_exp,
                                            r=0.05  # 5% risk-free rate assumption
                                        )
                                        
                                        if approx_iv is not None:
                                            implied_vol = approx_iv
                                            iv_source = "black_scholes_approximation"
                                            logger.info(
                                                f"Calculated approximate IV {approx_iv:.4f} for SPX {option_ticker} using Black-Scholes",
                                                market_price=market_price,
                                                strike=strike_price,
                                                underlying=current_underlying_price,
                                                time_to_exp=time_to_exp
                                            )
                                    else:
                                        logger.debug(
                                            f"Invalid Black-Scholes parameters for {option_ticker}",
                                            time_to_exp=time_to_exp,
                                            market_price=market_price
                                        )
                                else:
                                    logger.debug(
                                        f"Missing required parameters for Black-Scholes calculation for {option_ticker}",
                                        strike_price=strike_price,
                                        exp_date=exp_date,
                                        current_underlying_price=current_underlying_price
                                    )
                        except Exception as bs_error:
                            logger.debug(
                                f"Black-Scholes IV calculation failed for {option_ticker}: {str(bs_error)}"
                            )
                    
                    # Log the final IV result
                    if implied_vol is not None:
                        logger.debug(
                            f"Final IV for {option_ticker}: {implied_vol:.4f} (source: {iv_source})"
                        )
                    else:
                        logger.debug(
                            f"No IV available for {option_ticker} - will use null value"
                        )
                    
                    # Create enhanced contract with null safety for all numeric fields
                    strike_raw = details.get("strike_price", contract.get("strike_price"))
                    volume_raw = day_data.get("volume")
                    open_interest_raw = results.get("open_interest")
                    
                    # Safely convert strike price
                    try:
                        strike = float(strike_raw) if strike_raw is not None else 0.0
                    except (ValueError, TypeError):
                        strike = 0.0
                    
                    # Safely convert volume
                    try:
                        volume = int(volume_raw) if volume_raw is not None else 0
                    except (ValueError, TypeError):
                        volume = 0
                    
                    # Safely convert open interest
                    try:
                        open_interest = int(open_interest_raw) if open_interest_raw is not None else 0
                    except (ValueError, TypeError):
                        open_interest = 0

                    enhanced_contract = {
                        "strike": strike,
                        "bid": bid,
                        "ask": ask,
                        "volume": volume,
                        "open_interest": open_interest,
                        "implied_volatility": implied_vol,  # Now can be None for unavailable data
                        "iv_source": iv_source,  # Track source of IV calculation
                        "contract_ticker": option_ticker,
                        "expiration_date": contract.get("expiration_date"),
                        "last_updated": datetime.utcnow().isoformat() + "Z",
                        "is_highlighted": None
                    }
                    
                    enhanced_contracts.append(enhanced_contract)
                    
                    # Small delay between API calls to avoid overwhelming the API
                    if i < len(contracts_to_price) - 1:  # Don't delay after last contract
                        await asyncio.sleep(0.1)  # 100ms delay
                    
                except Exception as contract_error:
                    pricing_failures += 1
                    logger.warning(
                        "Failed to enhance contract with pricing",
                        contract_ticker=contract.get("ticker"),
                        error=str(contract_error),
                        failures=pricing_failures
                    )
                    
                    # If we're getting too many errors, stop processing
                    if pricing_failures >= max_failures:
                        logger.error(
                            "Stopping option pricing due to excessive failures",
                            failures=pricing_failures,
                            contracts_processed=i
                        )
                        break
                    
                    continue
            
            logger.info(
                "Option pricing enhancement completed",
                contracts_enhanced=len(enhanced_contracts),
                pricing_failures=pricing_failures,
                total_attempted=min(len(contracts_to_price), i + 1) if 'i' in locals() else 0
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

    async def get_spx_chart_data(
        self,
        interval: str = "1m",
        period: str = "1d"
    ) -> Dict[str, Any]:
        """
        Get SPX intraday chart data from ISIN-data endpoint with candle aggregation support
        
        This method fetches SPX intraday data from the ISIN-data endpoint which provides
        1-minute interval OHLCV data for the S&P 500 index for the current trading day.
        For 5m and 15m intervals, it aggregates the 1-minute data accordingly.
        
        Supported intervals:
        - "1m": Returns 1-minute candles as-is (~394 candles)
        - "5m": Aggregates every 5 consecutive 1-minute candles (~79 candles) 
        - "15m": Aggregates every 15 consecutive 1-minute candles (~26 candles)
        
        Args:
            interval: Time interval ("1m", "5m", "15m")
            period: Time period (only "1d" supported for intraday data)
        
        Returns:
            Dictionary containing aggregated OHLCV data formatted for chart display
            
        Raises:
            ExternalAPIError: On API errors or data processing failures
        """
        endpoint = "/v3/data/isin-data"
        
        # For intraday data, always use current day
        # The API may require startDate < endDate, so we'll use yesterday as start if needed
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = self._get_previous_trading_day()
        
        # Try with same day first, if API requires range, use yesterday to today
        params = {
            "isin": "US78378X1072",  # SPX ISIN
            "startDate": yesterday,  # Use yesterday to ensure startDate < endDate
            "endDate": today,
            "type": "intraday"  # Request intraday data for 1-minute intervals
        }
        
        # Validate interval - only support 1m, 5m, 15m
        valid_intervals = {"1m", "5m", "15m"}
        if interval not in valid_intervals:
            logger.warning(
                f"Invalid interval {interval} for SPX chart data, defaulting to 1m",
                valid_intervals=list(valid_intervals)
            )
            interval = "1m"

        try:
            logger.info(
                "Fetching SPX intraday chart data via ISIN-data endpoint",
                isin="US78378X1072",
                start_date=yesterday,
                end_date=today,
                type="intraday",
                interval=interval,
                requires_aggregation=(interval != "1m")
            )
            
            # Check cache first with interval-specific key for intraday data
            cache_key = f"spx_intraday_data:{interval}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                logger.info("Using cached SPX intraday chart data", interval=interval)
                return cached_data
            
            # Fetch fresh data from ISIN-data endpoint
            raw_data = await self.get(endpoint, params=params)
            
            # Expected response format for intraday data:
            # {n: "S&P 500", id: 1000002, isin: "US78378X1072", currency: null, 
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
            
            # If no current price from data, use fallback
            if current_price == 0.0:
                current_price = 6400.0  # SPX fallback price
            
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
                "start_date": yesterday,
                "end_date": today,
                "data_type": "intraday",
                "aggregation_applied": (interval != "1m"),
                "source_resolution": "1m"  # Source data is always 1-minute from API
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
                "SPX intraday chart data retrieved successfully via ISIN-data",
                data_points=len(price_data),
                current_price=current_price,
                interval=interval,
                start_date=yesterday,
                end_date=today,
                data_type="intraday",
                aggregation_applied=(interval != "1m"),
                source_resolution="1m"
            )
            
            return normalized_data
            
        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error("Failed to get SPX chart data", error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get SPX chart data: {str(e)}",
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
        
        Routes SPX to ISIN quote endpoint which provides daily data only.
        Uses regular TheTradeList range-data endpoint for SPY and XSP.
        
        Args:
            ticker: Stock ticker symbol (e.g., "SPY", "SPX")
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
        
        # Route SPX to the ISIN-data endpoint for intraday data
        if ticker_upper == "SPX":
            logger.info(
                "Routing SPX to ISIN-data endpoint for intraday chart data",
                ticker=ticker_upper,
                requested_interval=interval,
                requested_period=period,
                endpoint="isin-data",
                data_type="intraday"
            )
            # SPX ISIN-data endpoint provides 1-minute interval data
            # Pass through the requested interval for metadata
            spx_data = await self.get_spx_chart_data(interval=interval, period="1d")
            # Add ticker to the response for consistency
            spx_data["ticker"] = ticker_upper
            # The data is actually 1-minute intervals from the intraday endpoint
            return spx_data
        
        # Validate interval
        valid_intervals = {"1m", "5m", "15m", "30m", "1h"}
        if interval not in valid_intervals:
            logger.warning(f"Invalid interval {interval}, defaulting to 5m")
            interval = "5m"
        
        # Validate period 
        valid_periods = {"1d", "5d", "1w"}
        if period not in valid_periods:
            logger.warning(f"Invalid period {period}, defaulting to 1d")
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
                "Fetching intraday data",
                ticker=ticker_upper,
                interval=interval,
                period=period
            )
            
            # Calculate date range based on period using ET timezone
            try:
                import pytz
                et_tz = pytz.timezone('America/New_York')
                end_date = datetime.now(et_tz).replace(tzinfo=None)  # Remove timezone for API compatibility
                logger.info(f"Using ET timezone for intraday date range: {end_date}")
            except ImportError:
                end_date = datetime.now()
                logger.warning("pytz not available, using local time for intraday date range")
                
            if period == "1d":
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "5d":
                start_date = end_date - timedelta(days=5)
            elif period == "1w":
                start_date = end_date - timedelta(weeks=1)
            else:
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Use TheTradeList range-data endpoint for ALL tickers (including SPX)
            # SPX works directly with this endpoint, no special ISIN handling needed
            endpoint = "/v1/data/range-data"
            params = {
                "ticker": ticker_upper,  # Use SPX ticker directly
                "range": interval_mapping[interval],
                "startdate": start_date.strftime("%Y-%m-%d"),
                "enddate": end_date.strftime("%Y-%m-%d"),
                "limit": 200  # Reasonable limit for intraday data
            }
            
            logger.info(
                "Using range-data endpoint for intraday data",
                ticker=ticker_upper,
                endpoint=endpoint,
                params=params
            )
            
            # Use caching for intraday data (1-2 minutes)
            cache_key = f"intraday_data:{ticker_upper}:{interval}:{period}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                logger.info("Using cached intraday data", ticker=ticker_upper, interval=interval, period=period)
                return cached_data
            
            # Fetch fresh data from range-data endpoint
            # NOTE: SPX works directly with this endpoint, no ISIN routing needed
            logger.info(
                "Fetching intraday data from TheTradeList",
                ticker=ticker_upper,
                endpoint=endpoint,
                using_isin=False,  # SPX uses regular endpoint for chart data
                data_type="time_series"
            )
            
            raw_data = await self.get(endpoint, params=params)
            
            # Normalize the response
            normalized_data = self._normalize_intraday_data(raw_data, ticker_upper, interval, period)
            
            # Cache the result for 90 seconds
            self._set_cache(cache_key, normalized_data, ttl=90)
            
            logger.info(
                "Intraday data retrieved successfully",
                ticker=ticker_upper,
                interval=interval,
                period=period,
                data_points=len(normalized_data.get("price_data", [])),
                endpoint_used=endpoint,
                data_source="range_data_endpoint"
            )
            
            return normalized_data
            
        except ExternalAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error(
                "Failed to get intraday data",
                ticker=ticker,
                interval=interval,
                period=period,
                error=str(e)
            )
            raise ExternalAPIError(
                message=f"Failed to get intraday data for {ticker}: {str(e)}",
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
        
        Args:
            raw_data: Raw API response from TheTradeList
            ticker: Stock ticker symbol
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
            metadata = {
                "total_candles": len(price_data),
                "market_hours": "09:30-16:00 ET",
                "last_updated": datetime.utcnow().isoformat() + "Z"
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