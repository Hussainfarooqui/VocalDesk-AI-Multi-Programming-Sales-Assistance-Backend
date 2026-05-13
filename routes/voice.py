import base64
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Form
from backend.services import stt_service, groq_service, tts_service

from typing import List, Optional
from pydantic import BaseModel

class TextInputRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Voice & Text Input"])


@router.post("/voice-input", summary="Audio upload → AI reply (Groq + ElevenLabs)")
async def voice_input(
    audio: UploadFile = File(..., description="Audio file (wav/mp3/webm/ogg)"),
    conversation_history: str | None = Form(None),
    session_id: str = None,
):
    """
    Accept an audio file, transcribe with Whisper, run through Groq, and generate ElevenLabs TTS.
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
            logger.warning("Invalid conversation_history payload received.")

    try:
        # Using Groq instead of GPT
        result = groq_service.generate_response(transcript, conversation_history=history)
        reply_text = result["reply_text"]
        
        # Generate TTS audio
        audio_content = await tts_service.text_to_speech(reply_text)
        audio_base64 = base64.b64encode(audio_content).decode("utf-8") if audio_content else None

    except Exception as e:
        logger.error(f"AI processing failed: {e}")
        raise HTTPException(status_code=503, detail="AI processing failed.")

    return {
        "success": True,
        "transcript": transcript,
        "reply_text": reply_text,
        "lead_data": result["lead_data"],
        "audio_base64": audio_base64,
    }


@router.post("/text-input", summary="Text message → AI reply (Groq + ElevenLabs)")
async def text_input(
    body: TextInputRequest,
):
    """
    Accept a text message, run through Groq, and generate ElevenLabs TTS.
    """
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    history = body.conversation_history

    try:
        result = groq_service.generate_response(message, conversation_history=history)
        reply_text = result["reply_text"]
        
        # Generate TTS audio
        audio_content = await tts_service.text_to_speech(reply_text)
        audio_base64 = base64.b64encode(audio_content).decode("utf-8") if audio_content else None

    except Exception as e:
        logger.error(f"AI processing failed: {e}")
        raise HTTPException(status_code=503, detail="AI processing failed.")

    return {
        "success": True,
        "transcript": message,
        "reply_text": reply_text,
        "lead_data": result["lead_data"],
        "audio_base64": audio_base64,
    }
