from datetime import datetime, timedelta
from typing import Dict, Optional
from app.core.logging import get_logger
from app.core.config import get_settings
from app.services.exceptions import TimeCalculationError, DSTCalculationError, SessionCalculationError


logger = get_logger(__name__)


class MarketStatusService:
    """Service for calculating market status and Eastern Time conversions"""
    
    # Trading window constants (in ET)
    TRADING_START_HOUR = 14  # 3 PM ET
    TRADING_START_MINUTE = 0  # 3:00 PM ET
    TRADING_END_HOUR = 16  # 4 PM ET
    TRADING_END_MINUTE = 0  # 4:00 PM ET
    
    @staticmethod
    def calculate_dst_dates(year: int) -> tuple[datetime, datetime]:
        """
        Calculate DST start and end dates for a given year
        
        DST Rules:
        - Starts: 2nd Sunday in March at 2:00 AM ET
        - Ends: 1st Sunday in November at 2:00 AM ET
        
        Args:
            year: Year to calculate DST dates for
            
        Returns:
            Tuple of (dst_start_utc, dst_end_utc) as UTC datetimes
        """
        # March: Find 2nd Sunday
        march_first = datetime(year, 3, 1)
        
        # Calculate days to get to the first Sunday
        days_to_first_sunday = (6 - march_first.weekday()) % 7
        first_sunday = march_first + timedelta(days=days_to_first_sunday)
        
        # Add 7 days to get to the second Sunday
        second_sunday = first_sunday + timedelta(days=7)
        
        # DST starts at 2:00 AM ET on the second Sunday
        # 2:00 AM EST = 7:00 AM UTC (EST is UTC-5)
        dst_start = second_sunday.replace(hour=7, minute=0, second=0, microsecond=0)
        
        # November: Find 1st Sunday
        november_first = datetime(year, 11, 1)
        days_to_first_sunday = (6 - november_first.weekday()) % 7
        first_sunday_nov = november_first + timedelta(days=days_to_first_sunday)
        
        # DST ends at 2:00 AM EST on the first Sunday in November
        # 2:00 AM EST = 6:00 AM UTC (EST is UTC-5, but we "fall back")
        dst_end = first_sunday_nov.replace(hour=6, minute=0, second=0, microsecond=0)
        
        return dst_start, dst_end
    
    @staticmethod
    def get_eastern_time(utc_datetime: datetime) -> datetime:
        """
        Convert UTC datetime to Eastern Time, handling DST automatically
        
        Args:
            utc_datetime: UTC datetime to convert
            
        Returns:
            Eastern Time datetime (EST or EDT based on date)
            
        Raises:
            ValueError: If calculation fails
        """
        try:
            year = utc_datetime.year
            dst_start, dst_end = MarketStatusService.calculate_dst_dates(year)
            
            # Check if we're in DST period
            if dst_start <= utc_datetime < dst_end:
                # EDT (UTC-4)
                et_datetime = utc_datetime - timedelta(hours=4)
            else:
                # EST (UTC-5) 
                et_datetime = utc_datetime - timedelta(hours=5)
            
            logger.debug(
                "Converted UTC to ET",
                utc=utc_datetime.isoformat(),
                et=et_datetime.isoformat(),
                is_dst=dst_start <= utc_datetime < dst_end
            )
            
            return et_datetime
            
        except Exception as e:
            logger.error("Failed to calculate Eastern Time", error=e, utc=utc_datetime.isoformat())
            raise TimeCalculationError(f"Failed to calculate Eastern Time: {str(e)}")
    
    @staticmethod
    def is_session_active(current_et: datetime) -> bool:
        """
        Check if current ET time is in the 3:00-4:00 PM window (Monday-Thursday only)

        Args:
            current_et: Current Eastern Time

        Returns:
            True if in trading session, False otherwise
        """
        # Check day of week (0=Monday, 6=Sunday)
        # Only active Monday (0) through Thursday (3)
        if current_et.weekday() > 3:  # Friday (4), Saturday (5), Sunday (6)
            return False

        current_hour = current_et.hour
        current_minute = current_et.minute

        # Check if in 3:00 PM - 4:00 PM ET window
        start_minutes = MarketStatusService.TRADING_START_HOUR * 60 + MarketStatusService.TRADING_START_MINUTE
        end_minutes = MarketStatusService.TRADING_END_HOUR * 60 + MarketStatusService.TRADING_END_MINUTE
        current_minutes = current_hour * 60 + current_minute

        return start_minutes <= current_minutes < end_minutes
    
    @staticmethod
    def calculate_next_session_utc(current_utc: datetime) -> datetime:
        """
        Calculate the next 3:00 PM ET session start time in UTC
        
        Args:
            current_utc: Current UTC datetime
            
        Returns:
            Next session start time in UTC (skips weekends)
        """
        current_et = MarketStatusService.get_eastern_time(current_utc)
        
        # Start with today
        next_session_et = current_et.replace(
            hour=MarketStatusService.TRADING_START_HOUR, 
            minute=MarketStatusService.TRADING_START_MINUTE, 
            second=0, 
            microsecond=0
        )
        
        # If session already passed today, move to tomorrow
        if current_et >= next_session_et:
            next_session_et += timedelta(days=1)
        
        # Skip weekends (Saturday = 5, Sunday = 6)
        while next_session_et.weekday() >= 5:
            next_session_et += timedelta(days=1)
        
        # Convert back to UTC using proper DST calculation
        year = next_session_et.year
        dst_start, dst_end = MarketStatusService.calculate_dst_dates(year)
        
        # Create a UTC datetime to test for the session date
        # We need to check both EDT and EST possibilities to determine which is correct
        test_edt_utc = next_session_et + timedelta(hours=4)  # EDT assumption
        test_est_utc = next_session_et + timedelta(hours=5)  # EST assumption
        
        # Check if the session date falls within DST period
        # Use the date portion for DST boundary comparison
        session_date = next_session_et.date()
        dst_start_date = (dst_start - timedelta(hours=4)).date()  # Convert DST start to ET date
        dst_end_date = (dst_end - timedelta(hours=5)).date()      # Convert DST end to ET date
        
        if dst_start_date <= session_date < dst_end_date:
            # Session is during DST period - use EDT
            next_session_utc = next_session_et + timedelta(hours=4)
        else:
            # Session is during standard time - use EST
            next_session_utc = next_session_et + timedelta(hours=5)
        
        return next_session_utc
    
    
    @staticmethod
    def format_et_time(et_datetime: datetime) -> str:
        """
        Format ET datetime as '3:25 PM ET'
        
        Args:
            et_datetime: Eastern Time datetime
            
        Returns:
            Formatted time string
        """
        # Format as 12-hour time with AM/PM
        time_str = et_datetime.strftime("%I:%M %p").lstrip('0')  # Remove leading zero from hour
        return f"{time_str} ET"
    
    @staticmethod
    def calculate_market_session() -> Dict:
        """
        Calculate current market session status with all required information
        
        Returns:
            Dictionary containing market session details
            
        Raises:
            Exception: If any calculation fails
        """
        try:
            # Get settings for trading window bypass
            settings = get_settings()
            
            # Get current UTC time
            current_utc = datetime.utcnow()
            
            # Convert to Eastern Time
            current_et = MarketStatusService.get_eastern_time(current_utc)
            
            # Check if session is currently active
            # If bypass is enabled, always show as live
            if settings.bypass_trading_window:
                is_live = True
                logger.info("Trading window bypassed - showing as live", bypass_enabled=True)
            else:
                is_live = MarketStatusService.is_session_active(current_et)
            
            # Calculate session start/end times for today in ET
            session_start_et = current_et.replace(
                hour=MarketStatusService.TRADING_START_HOUR,
                minute=MarketStatusService.TRADING_START_MINUTE,
                second=0,
                microsecond=0
            )
            session_end_et = current_et.replace(
                hour=MarketStatusService.TRADING_END_HOUR,
                minute=MarketStatusService.TRADING_END_MINUTE,
                second=0,
                microsecond=0
            )
            
            # Convert session times to UTC for API response
            year = current_utc.year
            dst_start, dst_end = MarketStatusService.calculate_dst_dates(year)
            
            # Convert session times to UTC
            if dst_start <= current_utc < dst_end:
                # EDT: ET + 4 hours = UTC
                session_start_utc = session_start_et + timedelta(hours=4)
                session_end_utc = session_end_et + timedelta(hours=4)
            else:
                # EST: ET + 5 hours = UTC
                session_start_utc = session_start_et + timedelta(hours=5)
                session_end_utc = session_end_et + timedelta(hours=5)
            
            # Calculate next active session if not currently live
            next_active_session = None
            if not is_live:
                next_active_session = MarketStatusService.calculate_next_session_utc(current_utc)
            
            # Format current time in ET
            current_time_et = MarketStatusService.format_et_time(current_et)
            
            # Build response data
            result = {
                "is_live": is_live,
                "active_time_range": "3:00 PM - 4:00 PM ET",
                "current_time_et": current_time_et,
                "session_start_utc": session_start_utc.isoformat() + "Z",
                "session_end_utc": session_end_utc.isoformat() + "Z",
                "next_active_session": next_active_session.isoformat() + "Z" if next_active_session else None
            }
            
            logger.info(
                "Market session calculated",
                is_live=is_live,
                current_time_et=current_time_et,
                session_start_utc=session_start_utc.isoformat(),
                session_end_utc=session_end_utc.isoformat(),
                next_session=next_active_session.isoformat() if next_active_session else None
            )
            
            return result
            
        except (TimeCalculationError, DSTCalculationError) as e:
            # Re-raise domain-specific exceptions
            raise
        except Exception as e:
            logger.error("Failed to calculate market session", error=e)
            raise SessionCalculationError(f"Failed to calculate market session: {str(e)}")