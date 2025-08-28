"""
Stock and market data models
"""
from datetime import datetime
from datetime import date as date_type
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, Date, Text, Numeric, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Stock(Base):
    """Stock information model"""
    __tablename__ = "stocks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    trend_status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="neutral",
        index=True
    )
    variability_52w: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    variability_monthly: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    variability_3day: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    passed_variability_check: Mapped[bool] = mapped_column(Boolean, default=False)
    special_character: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    last_verified: Mapped[Optional[date_type]] = mapped_column(Date, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<Stock(symbol={self.symbol}, trend={self.trend_status})>"


class HistoricalData(Base):
    """Historical price data model"""
    __tablename__ = "historical_data"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<HistoricalData(symbol={self.symbol}, date={self.date})>"


class EMACache(Base):
    """Cached EMA calculations model"""
    __tablename__ = "ema_cache"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    ema22: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    ema53: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    ema208: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<EMACache(symbol={self.symbol}, date={self.date})>"


class MainList(Base):
    """Main list of stocks to track - matches income-machine-v2 structure"""
    __tablename__ = "main_list"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    last_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    trend: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    rsi: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    ema20: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    ema50: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    iv_rank: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    spread_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    best_roi: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<MainList(ticker={self.ticker}, trend={self.trend})>"