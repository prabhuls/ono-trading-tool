"""
API Key model for storing encrypted external API credentials
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class APIKey(Base):
    """Model for storing encrypted API keys for external services"""
    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_api_keys_user_id_name"),
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
    
    # API key information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User-friendly name for the API key"
    )
    service_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Service identifier (polygon, alpaca, binance, etc.)"
    )
    encrypted_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted API key value"
    )
    encrypted_secret: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted API secret (if applicable)"
    )
    
    # Metadata
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description or notes"
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
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this API key was used"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_keys",
        lazy="joined"
    )
    
    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, service={self.service_name})>"