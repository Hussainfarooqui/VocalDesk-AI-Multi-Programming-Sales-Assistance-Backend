"""
VocalDesk – Leads Route (v2)
JWT-protected endpoints for lead management.
GET /api/leads      — paginated list
GET /api/leads/stats — aggregate dashboard stats
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.connection import get_db
from backend.models.lead import Lead
from backend.models.admin_user import AdminUser
from backend.routes.admin import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/leads", tags=["Leads"])


@router.get("/stats", summary="Dashboard statistics (admin only)")
def get_lead_stats(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """
    Return aggregate stats for the admin dashboard.

    Returns:
        { total_leads, web_leads, whatsapp_leads, recent_leads[] }
    """
    total = db.query(func.count(Lead.id)).scalar() or 0
    web = db.query(func.count(Lead.id)).filter(Lead.source_channel == "web").scalar() or 0
    whatsapp = db.query(func.count(Lead.id)).filter(Lead.source_channel == "whatsapp").scalar() or 0

    recent = (
        db.query(Lead)
        .order_by(Lead.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "success": True,
        "total_leads": total,
        "web_leads": web,
        "whatsapp_leads": whatsapp,
        "recent_leads": [lead.to_dict() for lead in recent],
    }


@router.get("/", summary="Paginated lead list (admin only)")
def list_leads(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """
    Return a paginated, most-recent-first list of all leads.

    Returns:
        { success, total, leads[] }
    """
    total = db.query(func.count(Lead.id)).scalar() or 0
    leads = (
        db.query(Lead)
        .order_by(Lead.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "success": True,
        "total": total,
        "leads": [lead.to_dict() for lead in leads],
    }
