"""
VocalDesk – Analytics Routes (SRS FR-37–40)
GET /api/analytics         → list analytics metrics
GET /api/analytics/summary → dashboard summary with AI performance
"""

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.connection import get_db
from backend.models.analytics import Analytics
from backend.models.lead import Lead
from backend.models.conversation import Conversation
from backend.models.voice_log import VoiceLog
from backend.models.user import User
from backend.routes.admin import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary", summary="Analytics dashboard summary (FR-37, FR-39)")
def analytics_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Return aggregate analytics for the admin dashboard.

    Returns:
        { total_leads, total_conversations, total_voice_logs,
          web_leads, whatsapp_leads, ai_metrics }
    """
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    web_leads = db.query(func.count(Lead.id)).filter(Lead.source_channel == "web").scalar() or 0
    whatsapp_leads = db.query(func.count(Lead.id)).filter(Lead.source_channel == "whatsapp").scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    total_voice_logs = db.query(func.count(VoiceLog.id)).scalar() or 0

    # AI performance metrics (FR-39)
    ai_metrics = (
        db.query(Analytics)
        .filter(Analytics.category == "AI")
        .order_by(Analytics.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "success": True,
        "total_leads": total_leads,
        "web_leads": web_leads,
        "whatsapp_leads": whatsapp_leads,
        "total_conversations": total_conversations,
        "total_voice_logs": total_voice_logs,
        "ai_metrics": [m.to_dict() for m in ai_metrics],
    }


@router.get("/", summary="List analytics metrics (FR-37, FR-40)")
def list_analytics(
    category: str = Query(None, description="Filter by category: AI, Sales, System"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Return paginated analytics metrics, optionally filtered by category.

    Returns:
        { success, total, metrics[] }
    """
    query = db.query(Analytics)
    if category:
        query = query.filter(Analytics.category == category)

    total = query.count()
    metrics = query.order_by(Analytics.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "success": True,
        "total": total,
        "metrics": [m.to_dict() for m in metrics],
    }
