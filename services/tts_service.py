"""
VocalDesk – ElevenLabs TTS Service
Converts AI text responses to realistic voice audio.
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Default voice ID (e.g. "Rachel")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
API_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"


async def text_to_speech(text: str) -> bytes:
    """
    Convert text to speech using ElevenLabs API.

    Returns:
        Audio binary data (mp3).
    """
    if not ELEVENLABS_API_KEY:
        logger.warning("ElevenLabs API key not configured. Skipping TTS.")
        return b""

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(API_URL, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"ElevenLabs TTS failed: {e}")
        return b""
