"""
VocalDesk – User ORM Model (SRS §7.1)
Stores system user accounts with bcrypt-hashed passwords and RBAC.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from backend.database.connection import Base


class User(Base):
    """System user account (Admin/Staff) per SRS 7.1."""

    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    full_name = Column(String(200), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="admin", nullable=False)  # SRS FR-5: RBAC
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
