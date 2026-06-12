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
        Audio binary data (mp3), or empty bytes if TTS fails/unavailable.
        Never raises — the caller always gets a usable result.
    """
    if not ELEVENLABS_API_KEY:
        logger.info("ElevenLabs API key not configured — TTS skipped. "
                     "Frontend will use browser speechSynthesis fallback.")
        return b""

    if not text or not text.strip():
        logger.warning("Empty text provided to TTS — skipping.")
        return b""

    # Truncate very long text to avoid API limits
    if len(text) > 5000:
        text = text[:5000]
        logger.info("TTS text truncated to 5000 chars.")

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
            if response.status_code == 401:
                logger.error("ElevenLabs TTS: Invalid API key (401). Check ELEVENLABS_API_KEY.")
                return b""
            if response.status_code == 429:
                logger.warning("ElevenLabs TTS: Rate limited (429). Skipping TTS for this request.")
                return b""
            response.raise_for_status()
            audio_data = response.content
            if len(audio_data) < 100:
                logger.warning(f"ElevenLabs TTS returned suspiciously small audio ({len(audio_data)} bytes).")
                return b""
            logger.info(f"ElevenLabs TTS success: {len(audio_data)} bytes.")
            return audio_data
    except httpx.TimeoutException:
        logger.error("ElevenLabs TTS timed out (30s). Skipping TTS.")
        return b""
    except Exception as e:
        logger.error(f"ElevenLabs TTS failed: {type(e).__name__}: {e}")
        return b""
