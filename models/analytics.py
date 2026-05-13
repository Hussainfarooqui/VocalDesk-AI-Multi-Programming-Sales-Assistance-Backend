"""
VocalDesk – Analytics ORM Model (SRS 7.4)
Stores system usage and AI performance metrics.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, Integer
from backend.database.connection import Base


class Analytics(Base):
    """System-wide performance and usage metrics."""

    __tablename__ = "analytics"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        nullable=False,
    )
    metric_name = Column(String(100), nullable=False, index=True) # e.g. "api_latency", "conversion_rate"
    metric_value = Column(Float, nullable=False)
    details = Column(Text, nullable=True) # JSON details
    category = Column(String(50), index=True) # e.g. "AI", "Sales", "System"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "details": self.details,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
