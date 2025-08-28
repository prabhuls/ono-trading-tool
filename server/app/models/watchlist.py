"""
Watchlist model for storing user's stock/crypto watchlists
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, JSON, ForeignKey, UniqueConstraint, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Watchlist(Base):
    """Model for user watchlists"""
    __tablename__ = "watchlists"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_watchlists_user_id_name"),
    )
    
    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Watchlist information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Watchlist name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional description"
    )
    
    # Symbols stored as JSON array
    symbols: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Array of symbol objects with metadata"
    )
    
    # Watchlist metadata
    symbol_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of symbols in watchlist"
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this watchlist is publicly visible"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="watchlists",
        lazy="joined"
    )
    
    def __repr__(self) -> str:
        return f"<Watchlist(id={self.id}, name={self.name}, symbols={self.symbol_count})>"
    
    def add_symbol(self, symbol: str, **metadata):
        """Add a symbol to the watchlist"""
        symbol_obj = {"symbol": symbol.upper(), "added_at": datetime.utcnow().isoformat()}
        symbol_obj.update(metadata)
        
        if not any(s["symbol"] == symbol.upper() for s in self.symbols):
            self.symbols.append(symbol_obj)
            self.symbol_count = len(self.symbols)
    
    def remove_symbol(self, symbol: str):
        """Remove a symbol from the watchlist"""
        self.symbols = [s for s in self.symbols if s["symbol"] != symbol.upper()]
        self.symbol_count = len(self.symbols)
    
    def has_symbol(self, symbol: str) -> bool:
        """Check if watchlist contains a symbol"""
        return any(s["symbol"] == symbol.upper() for s in self.symbols)