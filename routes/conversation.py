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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Conversation"])


@router.post("/end-conversation", summary="Finalize lead + send emails (REQ-B03)")
async def end_conversation(
    background_tasks: BackgroundTasks,
    body: dict = Body(
        ...,
        examples={
            "default": {
                "summary": "End of conversation payload",
                "value": {
                    "lead_data": {"name": "John", "email": "john@example.com", "phone": "123", "product_interest": "CRM"},
                    "conversation_summary": "User asked about pricing...",
                    "source_channel": "web",
                },
            }
        },
    ),
    db: Session = Depends(get_db),
):
    """
    Finalize a conversation: save lead to database, send emails.

    Body:
        lead_data: { name, email, phone, product_interest }
        conversation_summary: Full conversation text
        source_channel: "web" or "whatsapp"

    Returns:
        { success, lead }
    """
    lead_data = body.get("lead_data", {})
    summary = body.get("conversation_summary", "")
    source = body.get("source_channel", "web")

    lead = lead_service.save_lead(
        db=db,
        name=lead_data.get("name"),
        email=lead_data.get("email"),
        phone=lead_data.get("phone"),
        product_interest=lead_data.get("product_interest"),
        conversation_summary=summary,
        source_channel=source,
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
    body: dict = Body(
        ...,
        examples={
            "default": {
                "summary": "Standalone email payload",
                "value": {
                    "lead_name": "John Doe",
                    "lead_email": "john@example.com",
                    "lead_data": {"name": "John", "email": "john@example.com"},
                },
            }
        },
    ),
):
    """
    Trigger emails without saving a lead (standalone).

    Body:
        lead_name: str
        lead_email: str
        lead_data: dict (for admin notification)

    Returns:
        { success, thank_you_sent, admin_sent }
    """
    lead_name = body.get("lead_name")
    lead_email = body.get("lead_email")
    lead_data = body.get("lead_data", {})

    if not lead_email:
        raise HTTPException(status_code=400, detail="lead_email is required.")

    ty = email_service.send_thank_you_email(lead_name, lead_email)
    admin = email_service.send_admin_notification(lead_data)

    return {
        "success": True,
        "thank_you_sent": ty,
        "admin_sent": admin,
    }
