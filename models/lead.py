"""
VocalDesk – Lead ORM Model (v2)
Includes source_channel for multi-channel tracking (web / whatsapp).
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from backend.database.connection import Base


class Lead(Base):
    """Represents a sales lead captured from any channel."""

    __tablename__ = "leads"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    product_interest = Column(Text, nullable=True)       # Structured product/service interest
    conversation_summary = Column(Text, nullable=True)   # Full conversation transcript
    source_channel = Column(String(50), nullable=False, default="web")  # "web" or "whatsapp"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self) -> dict:
        """Serialize the lead to a JSON-safe dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "product_interest": self.product_interest,
            "conversation_summary": self.conversation_summary,
            "source_channel": self.source_channel,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
