"""
VocalDesk – Conversation Route
POST /api/end-conversation  → save lead + send emails (REQ-B03, REQ-B04)
POST /api/send-email        → standalone email trigger (REQ-B04)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.services import lead_service, email_service, n8n_service

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
    
    # Trigger n8n workflow asynchronously
    background_tasks.add_task(
        n8n_service.trigger_webhook,
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


@router.post("/test-n8n", summary="Test n8n webhook connection")
async def test_n8n():
    """
    Send dummy data to verify the n8n connection.
    """
    test_data = {
        "id": "test-id-123",
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+1234567890",
        "product_interest": "n8n Integration Test",
        "source_channel": "test-bot"
    }
    success = n8n_service.trigger_webhook(test_data)
    if success:
        return {"success": True, "message": "Test data sent to n8n successfully!"}
    else:
        return {"success": False, "message": "Failed to send test data to n8n. Check backend logs."}
