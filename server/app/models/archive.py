"""
Archive and transfer tracking models
"""
from datetime import datetime, date
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, Date, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Last7DaysMovers(Base):
    """7-day rolling archive of market movers"""
    __tablename__ = "last_7_days_movers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Last time this symbol appeared in movers"
    )
    mover_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="uptrend or downtrend"
    )
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    special_character: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    has_weeklies: Mapped[bool] = mapped_column(Boolean, default=False)
    passed_variability_check: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self) -> str:
        return f"<Last7DaysMovers(symbol={self.symbol}, last_seen={self.last_seen_at})>"


class TransferStatus(Base):
    """Track daily transfer operations"""
    __tablename__ = "transfer_status"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transfer_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        unique=True,
        index=True,
        comment="Date of transfer (prevents duplicates)"
    )
    daily_transfer_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether daily transfer was completed"
    )
    transferred_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when transfer completed"
    )
    records_transferred: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of records transferred"
    )
    records_archived: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of records added to 7-day archive"
    )
    records_cleaned: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of expired records removed from archive"
    )
    
    def __repr__(self) -> str:
        return f"<TransferStatus(date={self.transfer_date}, completed={self.daily_transfer_completed})>"