"""
VocalDesk – Conversation Route
POST /api/end-conversation  → save lead + send emails (REQ-B03, REQ-B04)
POST /api/send-email        → standalone email trigger (REQ-B04)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.services import lead_service, email_service

from typing import List, Optional
from pydantic import BaseModel

class LeadData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    product_interest: Optional[str] = None

class EndConversationRequest(BaseModel):
    lead_data: LeadData
    conversation_summary: str
    source_channel: str = "web"

class SendEmailRequest(BaseModel):
    lead_name: Optional[str] = None
    lead_email: str
    lead_data: Optional[dict] = {}

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Conversation"])


@router.post("/end-conversation", summary="Finalize lead + send emails (REQ-B03)")
async def end_conversation(
    background_tasks: BackgroundTasks,
    body: EndConversationRequest,
    db: Session = Depends(get_db),
):
    """
    Finalize a conversation: save lead to database, send emails.
    """
    lead = lead_service.save_lead(
        db=db,
        name=body.lead_data.name,
        email=body.lead_data.email,
        phone=body.lead_data.phone,
        product_interest=body.lead_data.product_interest,
        conversation_summary=body.conversation_summary,
        source_channel=body.source_channel,
    )

    # Send emails asynchronously in the background
    lead_dict = lead.to_dict()
    background_tasks.add_task(
        email_service.send_thank_you_email,
        lead.name,
        lead.email,
    )
    background_tasks.add_task(
        email_service.send_admin_notification,
        lead_dict,
    )

    logger.info(f"Conversation ended: lead_id={lead.id}")

    return {
        "success": True,
        "message": "Lead saved and emails queued.",
        "lead": lead_dict,
    }


@router.post("/send-email", summary="Standalone email trigger (REQ-B04)")
async def send_email(
    body: SendEmailRequest,
):
    """
    Trigger emails without saving a lead (standalone).
    """
    if not body.lead_email:
        raise HTTPException(status_code=400, detail="lead_email is required.")

    ty = email_service.send_thank_you_email(body.lead_name, body.lead_email)
    admin = email_service.send_admin_notification(body.lead_data)

    return {
        "success": True,
        "thank_you_sent": ty,
        "admin_sent": admin,
    }
