from datetime import datetime, timedelta, time
from typing import Dict, Optional, List
import calendar
from enum import Enum

from app.core.logging import get_logger
from app.core.cache import redis_cache
from app.services.exceptions import TimeCalculationError, SessionCalculationError
from app.services.market_status_service import MarketStatusService


logger = get_logger(__name__)


class MarketSession(str, Enum):
    """Market session types"""
    PRE_MARKET = "pre_market"
    REGULAR_HOURS = "regular_hours" 
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


class MarketStatusEnhancedService:
    """
    Enhanced market status service that integrates with TheTradeList API
    and provides comprehensive market information for the sidebar component.
    
    Features:
    - Real-time market session detection
    - Options expiration date calculation
    - Volume data with formatting (K/M/B)
    - IV Rank calculation using market data
    - Integration with external market data APIs
    - Fallback mechanisms for API failures
    """
    
    # US Market hours in ET (Eastern Time)
    MARKET_HOURS = {
        "pre_market_start": time(4, 0),      # 4:00 AM ET
        "regular_start": time(9, 30),        # 9:30 AM ET
        "regular_end": time(16, 0),          # 4:00 PM ET
        "after_hours_end": time(20, 0)       # 8:00 PM ET
    }
    
    # US market holidays (will be checked dynamically)
    MARKET_HOLIDAYS_2025 = [
        "2025-01-01",  # New Year's Day
        "2025-01-20",  # Martin Luther King Jr. Day
        "2025-02-17",  # Presidents' Day
        "2025-04-18",  # Good Friday
        "2025-05-26",  # Memorial Day
        "2025-07-03",  # Independence Day (observed)
        "2025-09-01",  # Labor Day
        "2025-11-27",  # Thanksgiving
        "2025-12-25",  # Christmas Day
    ]
    
    def __init__(self):
        pass
    
    @staticmethod
    def calculate_market_session(current_utc: Optional[datetime] = None) -> Dict:
        """
        Calculate current market session with enhanced information
        
        Args:
            current_utc: Current UTC datetime (defaults to now)
            
        Returns:
            Dictionary containing enhanced market session details
        """
        try:
            if current_utc is None:
                current_utc = datetime.utcnow()
            
            # Get Eastern Time
            current_et = MarketStatusService.get_eastern_time(current_utc)
            current_date = current_et.date()
            current_time = current_et.time()
            
            # Check if it's a market holiday or weekend
            is_holiday = MarketStatusEnhancedService._is_market_holiday(current_date)
            is_weekend = current_et.weekday() >= 5  # Saturday=5, Sunday=6
            
            # Determine market session
            if is_holiday or is_weekend:
                market_session = MarketSession.CLOSED
                is_open = False
            else:
                market_session, is_open = MarketStatusEnhancedService._get_current_session(current_time)
            
            # Calculate next expiration
            next_expiration = MarketStatusEnhancedService.calculate_next_expiration_date(current_et)
            
            # Get session times in UTC
            session_times = MarketStatusEnhancedService._get_session_times_utc(current_et, current_utc)
            
            result = {
                "isOpen": is_open,
                "market_session": market_session.value,
                "next_expiration": next_expiration,
                "current_time_et": MarketStatusService.format_et_time(current_et),
                "session_times": session_times,
                "is_holiday": is_holiday,
                "is_weekend": is_weekend,
                "trading_day": not (is_holiday or is_weekend)
            }
            
            logger.info(
                "Enhanced market session calculated",
                is_open=is_open,
                session=market_session.value,
                next_expiration=next_expiration,
                is_holiday=is_holiday
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to calculate enhanced market session", error=str(e))
            raise SessionCalculationError(f"Failed to calculate enhanced market session: {str(e)}")
    
    @staticmethod
    def _get_current_session(current_time: time) -> tuple[MarketSession, bool]:
        """Determine current market session based on time"""
        hours = MarketStatusEnhancedService.MARKET_HOURS
        
        if current_time < hours["pre_market_start"]:
            return MarketSession.CLOSED, False
        elif current_time < hours["regular_start"]:
            return MarketSession.PRE_MARKET, False  # Pre-market is not "open" for regular trading
        elif current_time < hours["regular_end"]:
            return MarketSession.REGULAR_HOURS, True
        elif current_time < hours["after_hours_end"]:
            return MarketSession.AFTER_HOURS, False  # After-hours is not "open" for regular trading
        else:
            return MarketSession.CLOSED, False
    
    @staticmethod
    def _get_session_times_utc(current_et: datetime, current_utc: datetime) -> Dict[str, str]:
        """Get session start/end times in UTC for today"""
        try:
            # Determine if we're in DST
            year = current_utc.year
            dst_start, dst_end = MarketStatusService.calculate_dst_dates(year)
            is_dst = dst_start <= current_utc < dst_end
            utc_offset = 4 if is_dst else 5  # EDT = UTC-4, EST = UTC-5
            
            # Create session times for today in ET
            date = current_et.date()
            session_times_et = {
                "pre_market_start": datetime.combine(date, MarketStatusEnhancedService.MARKET_HOURS["pre_market_start"]),
                "regular_start": datetime.combine(date, MarketStatusEnhancedService.MARKET_HOURS["regular_start"]),
                "regular_end": datetime.combine(date, MarketStatusEnhancedService.MARKET_HOURS["regular_end"]),
                "after_hours_end": datetime.combine(date, MarketStatusEnhancedService.MARKET_HOURS["after_hours_end"])
            }
            
            # Convert to UTC
            session_times_utc = {}
            for key, et_time in session_times_et.items():
                utc_time = et_time + timedelta(hours=utc_offset)
                session_times_utc[key] = utc_time.isoformat() + "Z"
            
            return session_times_utc
            
        except Exception as e:
            logger.error("Failed to calculate session times UTC", error=str(e))
            return {}
    
    @staticmethod
    def _is_market_holiday(date) -> bool:
        """Check if given date is a US market holiday"""
        date_str = date.strftime("%Y-%m-%d")
        return date_str in MarketStatusEnhancedService.MARKET_HOLIDAYS_2025
    
    @staticmethod
    def calculate_next_expiration_date(current_et: datetime) -> str:
        """
        Calculate next options expiration date
        
        Options typically expire on the third Friday of each month.
        
        Args:
            current_et: Current Eastern Time datetime
            
        Returns:
            Next expiration date as string in YYYY-MM-DD format
        """
        try:
            # Start with current month
            year = current_et.year
            month = current_et.month
            
            # Find third Friday of current month
            third_friday = MarketStatusEnhancedService._get_third_friday(year, month)
            
            # If we've passed this month's expiration, move to next month
            if current_et.date() > third_friday:
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                third_friday = MarketStatusEnhancedService._get_third_friday(year, month)
            
            result = third_friday.strftime("%Y-%m-%d")
            
            logger.debug(
                "Next expiration calculated",
                current_date=current_et.date(),
                next_expiration=result
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to calculate next expiration date", error=str(e))
            # Fallback: return first Friday of next month
            next_month = current_et.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            
            # Find first Friday of next month as fallback
            for day in range(1, 8):
                test_date = next_month.replace(day=day)
                if test_date.weekday() == 4:  # Friday
                    return test_date.strftime("%Y-%m-%d")
            
            # Ultimate fallback
            return (current_et + timedelta(days=30)).strftime("%Y-%m-%d")
    
    @staticmethod
    def _get_third_friday(year: int, month: int) -> datetime.date:
        """Get the third Friday of given month/year"""
        # Find the first day of the month
        first_day = datetime(year, month, 1).date()
        
        # Find the first Friday (weekday 4)
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)
        
        # Third Friday is two weeks later
        third_friday = first_friday + timedelta(days=14)
        
        # Make sure it's still in the same month
        if third_friday.month != month:
            # This shouldn't happen, but fallback to second Friday
            third_friday = first_friday + timedelta(days=7)
        
        return third_friday
    
    async def get_sidebar_status_data(self) -> Dict:
        """
        Get basic market status data for the sidebar component
        
        Returns:
            Basic market status data including:
            - Market session status
            - Next options expiration date
        """
        try:
            # Check cache first
            cache_key = "market_sidebar_status"
            cached_data = redis_cache.get(f"market_data:{cache_key}")
            if cached_data is not None:
                logger.info("Using cached sidebar status data")
                return cached_data
            
            logger.info("Fetching fresh sidebar status data")
            
            # Get basic market session info
            session_data = self.calculate_market_session()
            
            # Prepare response with only basic session data
            response_data = {
                "isOpen": session_data["isOpen"],
                "market_session": session_data["market_session"],
                "next_expiration": session_data["next_expiration"],
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            
            # Cache the result
            cache_ttl = 300  # 5 minutes (can be longer since no external API calls)
            redis_cache.set(f"market_data:{cache_key}", response_data, ttl=cache_ttl)
            
            logger.info(
                "Sidebar status data prepared",
                is_open=response_data["isOpen"],
                session=response_data["market_session"],
                next_expiration=response_data["next_expiration"]
            )
            
            return response_data
            
        except Exception as e:
            logger.error("Failed to get sidebar status data", error=str(e))
            
            # Return fallback data
            return {
                "isOpen": False,
                "market_session": MarketSession.CLOSED.value,
                "next_expiration": self._get_fallback_expiration(),
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "status": "fallback"
            }
    
    def _get_fallback_expiration(self) -> str:
        """Get fallback expiration date"""
        try:
            # Simple fallback: next Friday
            today = datetime.now()
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0:  # Today is Friday
                days_until_friday = 7  # Next Friday
            
            next_friday = today + timedelta(days=days_until_friday)
            return next_friday.strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.error("Failed to calculate fallback expiration", error=str(e))
            # Ultimate fallback
            return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    async def get_market_health(self) -> Dict:
        """Get health status of market data services"""
        try:
            # Check cache connectivity only (no external API dependencies)
            cache_healthy = True
            try:
                redis_cache.set("health:health_check", "test", ttl=10)
                cached_value = redis_cache.get("health:health_check")
                cache_healthy = cached_value == "test"
            except Exception:
                cache_healthy = False
            
            return {
                "status": "healthy" if cache_healthy else "unhealthy",
                "services": {
                    "cache": {
                        "status": "healthy" if cache_healthy else "unhealthy"
                    }
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error("Failed to check market service health", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }


# Singleton instance
_market_status_enhanced: Optional[MarketStatusEnhancedService] = None


def get_market_status_enhanced_service() -> MarketStatusEnhancedService:
    """Get singleton enhanced market status service instance"""
    global _market_status_enhanced
    if _market_status_enhanced is None:
        _market_status_enhanced = MarketStatusEnhancedService()
    return _market_status_enhanced