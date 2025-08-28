"""
Domain-specific exceptions for services
"""


class MarketStatusError(Exception):
    """Base exception for market status calculations"""
    pass


class TimeCalculationError(MarketStatusError):
    """Raised when time calculations fail"""
    pass


class DSTCalculationError(MarketStatusError):
    """Raised when DST calculation fails"""
    pass


class SessionCalculationError(MarketStatusError):
    """Raised when session time calculations fail"""
    pass