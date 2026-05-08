"""
VocalDesk – Voice Route (v2)
POST /api/voice-input  → Whisper STT → GPT → structured JSON response
POST /api/text-input   → GPT → structured JSON response
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Form
from backend.services import stt_service, gpt_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Voice & Text Input"])


@router.post("/voice-input", summary="Audio upload → AI reply (REQ-B01)")
async def voice_input(
    audio: UploadFile = File(..., description="Audio file (wav/mp3/webm/ogg)"),
    conversation_history: str | None = Form(None),
    session_id: str = None,
):
    """
    Accept an audio file, transcribe with Whisper, run through GPT.

    Returns:
        { success, transcript, reply_text, lead_data }
    """
    if not audio or not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    logger.info(f"Voice input: {audio.filename} ({audio.content_type})")

    try:
        transcript = await stt_service.transcribe_audio(audio)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not transcript:
        raise HTTPException(status_code=422, detail="Could not transcribe audio. Please speak clearly.")

    history = []
    if conversation_history:
        try:
            import json
            history = json.loads(conversation_history)
        except Exception:
            logger.warning("Invalid conversation_history payload received for voice input.")
            history = []

    try:
        result = gpt_service.generate_response(transcript, conversation_history=history)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "success": True,
        "transcript": transcript,
        "reply_text": result["reply_text"],
        "lead_data": result["lead_data"],
    }


@router.post("/text-input", summary="Text message → AI reply (REQ-B02)")
async def text_input(
    body: dict = Body(
        ..., 
        examples={
            "default": {
                "summary": "Basic text message",
                "value": {"message": "Hi, I'm interested in your product"},
            }
        },
    ),
):
    """
    Accept a text message, run through GPT.

    Body: { message: str, conversation_history?: list }

    Returns:
        { success, transcript, reply_text, lead_data }
    """
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    history = body.get("conversation_history", [])

    try:
        result = gpt_service.generate_response(message, conversation_history=history)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "success": True,
        "transcript": message,
        "reply_text": result["reply_text"],
        "lead_data": result["lead_data"],
    }
