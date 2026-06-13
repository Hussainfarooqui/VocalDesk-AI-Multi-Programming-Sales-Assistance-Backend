"""VocalDesk – Services package."""
from backend.services.auth_service import *
from backend.services.email_service import *
from backend.services.groq_service import generate_response as generate_groq_response
from backend.services.lead_service import *
from backend.services.stt_service import *
from backend.services.tts_service import text_to_speech

__all__ = [
    "stt_service",
    "lead_service",
    "email_service",
    "auth_service",
    "groq_service",
    "tts_service",
]
