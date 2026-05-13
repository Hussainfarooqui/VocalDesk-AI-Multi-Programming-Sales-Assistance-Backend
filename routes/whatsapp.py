"""
VocalDesk – WhatsApp Cloud API Webhook (REQ-W01 – W04)
GET  /webhook/whatsapp → Meta verification challenge
POST /webhook/whatsapp → receive message → AI → reply → store lead
"""

import os
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.params import Depends

from backend.database.connection import get_db
from backend.services import groq_service, lead_service, email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["WhatsApp"])

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "vocaldesk_verify")
WHATSAPP_API_URL = "https://graph.facebook.com/v19.0"


# ─── GET: Meta Webhook Verification ─────────────────────────────────────────
@router.get("/whatsapp", summary="Meta webhook verification (REQ-W01)")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Handle Meta's webhook verification challenge.
    Returns the challenge string if token matches.
    """
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully.")
        return int(hub_challenge)

    logger.warning(f"Webhook verification failed: mode={hub_mode}, token={hub_verify_token}")
    raise HTTPException(status_code=403, detail="Verification failed.")


# ─── POST: Receive & Process Messages ────────────────────────────────────────
@router.post("/whatsapp", summary="Receive WhatsApp messages (REQ-W02, W03, W04)")
async def receive_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Process incoming WhatsApp messages:
    1. Parse message from Meta webhook payload
    2. Generate AI reply via Groq (Llama)
    3. Send reply via Cloud API
    4. Store lead with source_channel="whatsapp"
    5. Trigger admin notification email (background)
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    logger.info(f"WhatsApp webhook received: {str(body)[:200]}")

    # Extract message from Meta webhook structure
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            # Not a message event (e.g., status update) — acknowledge silently
            return {"status": "ok"}

        message = messages[0]
        from_number = message.get("from")
        msg_type = message.get("type")

        if msg_type != "text":
            # Only handle text messages for now
            logger.info(f"Ignoring non-text message type: {msg_type}")
            return {"status": "ok"}

        user_text = message["text"]["body"].strip()
        logger.info(f"WhatsApp message from {from_number}: {user_text[:100]}")

    except (KeyError, IndexError) as e:
        logger.warning(f"Failed to parse WhatsApp payload: {e}")
        return {"status": "ok"}

    # Generate AI response
    try:
        result = groq_service.generate_response(user_text)
        reply_text = result["reply_text"]
        lead_data = result["lead_data"]
    except Exception as e:
        logger.error(f"AI generation failed for WhatsApp: {e}")
        reply_text = "Thank you for reaching out! Our team will contact you shortly."
        lead_data = {}

    # Send reply via WhatsApp Cloud API
    sent = await _send_whatsapp_reply(from_number, reply_text)
    if not sent:
        logger.warning(f"Failed to send WhatsApp reply to {from_number}")

    # Save lead to database (source_channel = "whatsapp")
    lead = lead_service.save_lead(
        db=db,
        name=lead_data.get("name"),
        email=lead_data.get("email"),
        phone=from_number,  # Use WhatsApp number as phone
        product_interest=lead_data.get("product_interest"),
        conversation_summary=f"User: {user_text}\nAI: {reply_text}",
        source_channel="whatsapp",
    )

    # Admin notification in background
    background_tasks.add_task(email_service.send_admin_notification, lead.to_dict())

    return {"status": "ok", "lead_id": str(lead.id)}


async def _send_whatsapp_reply(to_number: str, message: str) -> bool:
    """
    Send a reply via WhatsApp Cloud API.

    Args:
        to_number: Recipient's phone number (international format, no +).
        message: Text message to send.

    Returns:
        True if sent successfully.
    """
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured — reply not sent.")
        return False

    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"WhatsApp reply sent to {to_number}")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"WhatsApp API error: {e.response.status_code} — {e.response.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"WhatsApp reply failed: {e}")
        return False
