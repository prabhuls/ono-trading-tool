"""
Credit spread trades model
"""
from datetime import datetime, date
from typing import Optional, Dict, Any, TYPE_CHECKING
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, Date, Numeric, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class CreditSpread(Base):
    """Credit spread trades model"""
    __tablename__ = "credit_spreads"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    
    # User relationship
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Trade details
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    short_strike: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    long_strike: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    net_credit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_risk: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    roi: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expiration: Mapped[date] = mapped_column(Date, nullable=False)
    contract_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="call or put"
    )
    days_to_expiration: Mapped[int] = mapped_column(Integer, nullable=False)
    breakeven: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    buffer_room: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Price scenarios (JSON)
    scenarios: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Price scenarios JSON"
    )
    
    # Trade status
    trade_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="saved",
        index=True,
        comment="saved, claimed, closed"
    )
    
    # Trade lifecycle timestamps
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Trade closing details
    closed_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    profit_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="credit_spreads")
    
    def __repr__(self) -> str:
        return f"<CreditSpread(ticker={self.ticker}, strikes={self.short_strike}/{self.long_strike}, status={self.trade_status})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "ticker": self.ticker,
            "currentPrice": float(self.current_price),
            "shortStrike": float(self.short_strike),
            "longStrike": float(self.long_strike),
            "netCredit": float(self.net_credit),
            "maxRisk": float(self.max_risk),
            "roi": float(self.roi),
            "expiration": self.expiration.isoformat(),
            "contractType": self.contract_type,
            "daysToExpiration": self.days_to_expiration,
            "breakeven": float(self.breakeven),
            "bufferRoom": float(self.buffer_room),
            "scenarios": self.scenarios,
            "tradeStatus": self.trade_status,
            "claimedAt": self.claimed_at.isoformat() if self.claimed_at else None,
            "closedAt": self.closed_at.isoformat() if self.closed_at else None,
            "closedPrice": float(self.closed_price) if self.closed_price else None,
            "profitLoss": float(self.profit_loss) if self.profit_loss else None,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat()
        }