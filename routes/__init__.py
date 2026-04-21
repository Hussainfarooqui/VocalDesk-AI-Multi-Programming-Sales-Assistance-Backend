"""VocalDesk – Routes package."""
from backend.routes.admin import router as admin_router
from backend.routes.voice import router as voice_router
from backend.routes.leads import router as leads_router
from backend.routes.conversation import router as conversation_router
from backend.routes.whatsapp import router as whatsapp_router

__all__ = [
    "admin_router",
    "voice_router",
    "leads_router",
    "conversation_router",
    "whatsapp_router",
]
