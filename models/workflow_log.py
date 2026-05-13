"""
VocalDesk – WorkflowLog ORM Model (SRS 7.5)
Stores automation workflow execution history (n8n, webhooks).
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer
from backend.database.connection import Base


class WorkflowLog(Base):
    """Execution logs for automated workflows."""

    __tablename__ = "workflow_logs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        nullable=False,
    )
    workflow_name = Column(String(200), nullable=False, index=True)
    status = Column(String(50), nullable=False) # e.g. "success", "failed"
    trigger_source = Column(String(100)) # e.g. "whatsapp_webhook", "lead_capture"
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True) # Duration in milliseconds
    payload = Column(Text, nullable=True) # JSON request/response
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "workflow_name": self.workflow_name,
            "status": self.status,
            "trigger_source": self.trigger_source,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
