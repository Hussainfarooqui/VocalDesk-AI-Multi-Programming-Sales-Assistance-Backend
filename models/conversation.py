"""
VocalDesk – Conversation ORM Model (SRS 7.2)
Stores user-lead conversation history and context.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from backend.database.connection import Base


class Conversation(Base):
    """Represents a chat/voice session between a user and the AI assistant."""

    __tablename__ = "conversations"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        nullable=False,
    )
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=True)
    session_id = Column(String(100), index=True, nullable=True)
    messages = Column(Text, nullable=True)  # JSON serialized list of messages
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "lead_id": str(self.lead_id) if self.lead_id else None,
            "session_id": self.session_id,
            "messages": self.messages,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
