"""
Market movers and lists models
"""
from datetime import datetime, date
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, Date, Numeric, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TodaysMover(Base):
    """Today's market movers model"""
    __tablename__ = "todays_movers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mover_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        index=True,
        comment="uptrend or downtrend"
    )
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_change: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    price_change_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    avg_volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    volume_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # EMA values
    ema22: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    ema53: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    ema208: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    ema_strength: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), 
        nullable=True,
        comment="Position relative to EMAs"
    )
    trend_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Calculated trend strength"
    )
    
    # Additional metadata
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    special_character: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    passed_variability_check: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Options and earnings data
    options_expiring_10days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    has_weeklies: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    has_spreads: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    upcoming_earnings: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    
    # Timestamps
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    def __repr__(self) -> str:
        return f"<TodaysMover(symbol={self.symbol}, type={self.mover_type}, price={self.current_price})>"


class MainList(Base):
    """Main curated lists model"""
    __tablename__ = "main_lists"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    list_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="uptrend or downtrend"
    )
    last_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    variability_52w: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    variability_monthly: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    variability_3day: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    passed_variability_check: Mapped[bool] = mapped_column(Boolean, default=False)
    special_character: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    added_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    def __repr__(self) -> str:
        return f"<MainList(symbol={self.symbol}, type={self.list_type})>"