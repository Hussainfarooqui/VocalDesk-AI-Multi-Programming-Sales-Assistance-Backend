"""
VocalDesk – VoiceLog ORM Model (SRS 7.3)
Stores metadata for voice interactions and transcriptions.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey
from backend.database.connection import Base


class VoiceLog(Base):
    """Logs of voice inputs and their processing details."""

    __tablename__ = "voice_logs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        nullable=False,
    )
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True)
    file_path = Column(String(500), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    transcription = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "file_path": self.file_path,
            "transcription": self.transcription,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
