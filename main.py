"""
VocalDesk – FastAPI Application Entry Point (v2)
New architecture: serves static frontend + REST API.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

# ─── Logging Configuration ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vocaldesk")


# ─── Database Startup ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    from backend.database.connection import create_tables
    logger.info("VocalDesk backend starting up…")
    try:
        create_tables()
        logger.info("Database tables ready.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    yield
    logger.info("VocalDesk backend shutting down.")


# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="VocalDesk API",
    description=(
        "Multi-Platform AI Voice Sales Assistant – "
        "Backend API for voice processing, lead capture, and CRM automation."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS Middleware ─────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8001,http://127.0.0.1:8001,http://localhost:8000,http://localhost:3000,http://localhost:8002,http://127.0.0.1:8002,https://vocaldesk-frontend.onrender.com"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routers (added per phase) ───────────────────────────────────────────
# Phase 3: Admin auth + lead CRUD
from backend.routes import admin, leads   # noqa: E402
app.include_router(admin.router)
app.include_router(leads.router)

# Phase 4: AI voice + text input
from backend.routes import voice           # noqa: E402
app.include_router(voice.router)

# Phase 5: Email + end-conversation
from backend.routes import conversation    # noqa: E402
app.include_router(conversation.router)

# Phase 6: WhatsApp webhook
from backend.routes import whatsapp       # noqa: E402
app.include_router(whatsapp.router)

# Phase 7: Analytics (SRS FR-37–40)
from backend.routes import analytics      # noqa: E402
app.include_router(analytics.router)

# ─── Health & Root Endpoints ─────────────────────────────────────────────────
# Root endpoint removed to allow StaticFiles to serve index.html by default


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {"status": "healthy", "service": "vocaldesk-backend"}


# ─── Static Frontend (served last, catches all non-API routes) ───────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
