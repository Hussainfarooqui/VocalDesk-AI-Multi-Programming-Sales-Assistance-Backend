"""VocalDesk – Services package."""
from backend.services import (
    stt_service,
    gpt_service,
    lead_service,
    email_service,
    auth_service,
)

__all__ = [
    "stt_service",
    "gpt_service",
    "lead_service",
    "email_service",
    "auth_service",
]
