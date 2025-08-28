from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class MarketSidebarStatusResponse(BaseModel):
    """Market status response model for the sidebar component"""
    
    isOpen: bool = Field(
        ...,
        description="Whether the market is currently open for regular trading"
    )
    market_session: str = Field(
        ...,
        description="Current market session state",
        pattern="^(pre_market|regular_hours|after_hours|closed)$"
    )
    next_expiration: str = Field(
        ...,
        description="Next options expiration date in YYYY-MM-DD format",
        pattern="^\\d{4}-\\d{2}-\\d{2}$"
    )
    last_updated: str = Field(
        ...,
        description="Timestamp when data was last updated (ISO format with Z)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "isOpen": True,
                "market_session": "regular_hours",
                "next_expiration": "2024-12-20",
                "last_updated": "2025-08-28T14:30:00Z"
            }
        }


class SessionTimes(BaseModel):
    """Market session times in UTC"""
    
    pre_market_start: str = Field(..., description="Pre-market start time in UTC")
    regular_start: str = Field(..., description="Regular hours start time in UTC")
    regular_end: str = Field(..., description="Regular hours end time in UTC") 
    after_hours_end: str = Field(..., description="After-hours end time in UTC")


class EnhancedMarketStatusResponse(BaseModel):
    """Enhanced market status with comprehensive session information"""
    
    isOpen: bool = Field(..., description="Whether market is open for regular trading")
    market_session: str = Field(..., description="Current market session")
    next_expiration: str = Field(..., description="Next options expiration date")
    current_time_et: str = Field(..., description="Current Eastern Time")
    session_times: SessionTimes = Field(..., description="Today's session times in UTC")
    is_holiday: bool = Field(..., description="Whether today is a market holiday")
    is_weekend: bool = Field(..., description="Whether today is a weekend")
    trading_day: bool = Field(..., description="Whether today is a trading day")
    
    class Config:
        json_schema_extra = {
            "example": {
                "isOpen": True,
                "market_session": "regular_hours",
                "next_expiration": "2024-12-20",
                "current_time_et": "2:30 PM ET",
                "session_times": {
                    "pre_market_start": "2025-08-28T08:00:00Z",
                    "regular_start": "2025-08-28T13:30:00Z",
                    "regular_end": "2025-08-28T20:00:00Z",
                    "after_hours_end": "2025-08-29T00:00:00Z"
                },
                "is_holiday": False,
                "is_weekend": False,
                "trading_day": True
            }
        }


class MarketHealthResponse(BaseModel):
    """Market data services health check response"""
    
    status: str = Field(..., description="Overall health status")
    services: Dict[str, Any] = Field(..., description="Individual service health")
    timestamp: str = Field(..., description="Health check timestamp")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "services": {
                    "cache": {
                        "status": "healthy"
                    }
                },
                "timestamp": "2025-08-28T14:30:00Z"
            }
        }


class StockPriceData(BaseModel):
    """Individual stock price data"""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    price: float = Field(..., description="Current stock price")
    change: float = Field(..., description="Price change from previous close")
    change_percent: float = Field(..., description="Percentage change from previous close")
    timestamp: str = Field(..., description="Timestamp when price was retrieved (ISO format with Z)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "SPY",
                "price": 585.18,
                "change": 2.34,
                "change_percent": 0.40,
                "timestamp": "2025-08-28T15:30:00Z"
            }
        }


class SingleStockPriceResponse(BaseModel):
    """Response model for single stock price endpoint"""
    
    success: bool = Field(..., description="Whether the request was successful")
    data: StockPriceData = Field(..., description="Stock price data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "ticker": "SPY",
                    "price": 585.18,
                    "change": 2.34,
                    "change_percent": 0.40,
                    "timestamp": "2025-08-28T15:30:00Z"
                }
            }
        }


class MultipleStockPricesResponse(BaseModel):
    """Response model for multiple stock prices endpoint"""
    
    success: bool = Field(..., description="Whether the request was successful")
    data: Dict[str, List[StockPriceData]] = Field(..., description="Multiple stock prices data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "prices": [
                        {
                            "ticker": "SPY",
                            "price": 585.18,
                            "change": 2.34,
                            "change_percent": 0.40,
                            "timestamp": "2025-08-28T15:30:00Z"
                        },
                        {
                            "ticker": "XSP",
                            "price": 58.52,
                            "change": 0.23,
                            "change_percent": 0.39,
                            "timestamp": "2025-08-28T15:30:00Z"
                        },
                        {
                            "ticker": "SPX",
                            "price": 5851.8,
                            "change": 23.4,
                            "change_percent": 0.40,
                            "timestamp": "2025-08-28T15:30:00Z"
                        }
                    ]
                }
            }
        }


class IntradayDataPoint(BaseModel):
    """Individual intraday OHLCV data point"""
    
    timestamp: str = Field(
        ...,
        description="Timestamp in ISO format with Z"
    )
    open: float = Field(
        ...,
        description="Opening price for this time period",
        ge=0
    )
    high: float = Field(
        ...,
        description="Highest price for this time period",
        ge=0
    )
    low: float = Field(
        ...,
        description="Lowest price for this time period",
        ge=0
    )
    close: float = Field(
        ...,
        description="Closing price for this time period",
        ge=0
    )
    volume: int = Field(
        ...,
        description="Volume for this time period",
        ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-08-28T09:30:00Z",
                "open": 584.50,
                "high": 585.20,
                "low": 584.30,
                "close": 584.80,
                "volume": 12450
            }
        }


class BenchmarkLines(BaseModel):
    """Benchmark lines for chart display"""
    
    current_price: float = Field(
        ...,
        description="Current market price of the underlying asset",
        ge=0
    )
    buy_strike: Optional[float] = Field(
        None,
        description="Recommended buy strike price",
        ge=0
    )
    sell_strike: Optional[float] = Field(
        None,
        description="Recommended sell strike price", 
        ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "current_price": 585.18,
                "buy_strike": 580.0,
                "sell_strike": 581.0
            }
        }


class IntradayMetadata(BaseModel):
    """Metadata for intraday chart data"""
    
    total_candles: int = Field(
        ...,
        description="Total number of data points returned",
        ge=0
    )
    market_hours: str = Field(
        ...,
        description="Market trading hours"
    )
    last_updated: str = Field(
        ...,
        description="When data was last updated (ISO format with Z)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_candles": 78,
                "market_hours": "09:30-16:00 ET",
                "last_updated": "2025-08-28T15:25:00Z"
            }
        }


class IntradayChartData(BaseModel):
    """Complete intraday chart data response"""
    
    ticker: str = Field(
        ...,
        description="Stock ticker symbol"
    )
    interval: str = Field(
        ...,
        description="Time interval between data points",
        pattern="^(1m|5m|15m|30m|1h)$"
    )
    period: str = Field(
        ...,
        description="Time period for data",
        pattern="^(1d|5d|1w)$"
    )
    current_price: float = Field(
        ...,
        description="Most recent price",
        ge=0
    )
    price_data: List[IntradayDataPoint] = Field(
        ...,
        description="Array of OHLCV data points"
    )
    benchmark_lines: BenchmarkLines = Field(
        ...,
        description="Benchmark strike levels for chart display"
    )
    metadata: IntradayMetadata = Field(
        ...,
        description="Additional metadata about the data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "SPY",
                "interval": "5m",
                "period": "1d",
                "current_price": 585.18,
                "price_data": [
                    {
                        "timestamp": "2025-08-28T09:30:00Z",
                        "open": 584.50,
                        "high": 585.20,
                        "low": 584.30,
                        "close": 584.80,
                        "volume": 12450
                    }
                ],
                "benchmark_lines": {
                    "current_price": 585.18,
                    "buy_strike": 580.0,
                    "sell_strike": 581.0
                },
                "metadata": {
                    "total_candles": 78,
                    "market_hours": "09:30-16:00 ET",
                    "last_updated": "2025-08-28T15:25:00Z"
                }
            }
        }


class IntradayChartResponse(BaseModel):
    """Response model for intraday chart endpoint"""
    
    success: bool = Field(..., description="Whether the request was successful")
    data: IntradayChartData = Field(..., description="Intraday chart data")
    message: str = Field(..., description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "ticker": "SPY",
                    "interval": "5m",
                    "period": "1d",
                    "current_price": 585.18,
                    "price_data": [
                        {
                            "timestamp": "2025-08-28T09:30:00Z",
                            "open": 584.50,
                            "high": 585.20,
                            "low": 584.30,
                            "close": 584.80,
                            "volume": 12450
                        }
                    ],
                    "benchmark_lines": {
                        "current_price": 585.18,
                        "buy_strike": 580.0,
                        "sell_strike": 581.0
                    },
                    "metadata": {
                        "total_candles": 78,
                        "market_hours": "09:30-16:00 ET",
                        "last_updated": "2025-08-28T15:25:00Z"
                    }
                },
                "message": "Intraday chart data retrieved successfully"
            }
        }


