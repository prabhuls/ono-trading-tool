"""Claims model for tracking trading positions and outcomes."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Index
from sqlalchemy.sql import func
from app.core.database import Base


class Claims(Base):
    """
    Model for tracking trade claims/positions
    """
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    
    # Entry details
    entry_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    entry_price = Column(Numeric(10, 2), nullable=False)
    
    # Exit details  
    exit_date = Column(DateTime(timezone=True))
    exit_price = Column(Numeric(10, 2))
    
    # Option details
    expiry_date = Column(DateTime(timezone=True))
    strike_price = Column(Numeric(10, 2))
    
    # Trade outcome
    status = Column(String(20), default="active")  # active, closed, expired
    profit_loss = Column(Numeric(10, 2))
    
    # Strategy and notes
    strategy = Column(String(50))  # credit_spread, iron_condor, etc
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_claims_ticker_status', 'ticker', 'status'),
        Index('idx_claims_entry_date', 'entry_date'),
        Index('idx_claims_exit_date', 'exit_date'),
    )