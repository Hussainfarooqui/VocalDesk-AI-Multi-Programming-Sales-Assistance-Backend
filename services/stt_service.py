"""
VocalDesk – STT Service
Groq Whisper (primary) + OpenAI Whisper (fallback) for Speech-to-Text.
"""

import os
import logging
import tempfile
from fastapi import UploadFile

logger = logging.getLogger(__name__)

# ── Groq Whisper (primary) ──────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq Whisper STT client initialized.")
    except ImportError:
        logger.warning("groq package not installed — Groq STT unavailable.")

# ── OpenAI Whisper (fallback) ───────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
openai_client = None
if OPENAI_API_KEY and "sk-your-" not in OPENAI_API_KEY and "sk-test-dummy" not in OPENAI_API_KEY:
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI Whisper STT client initialized (fallback).")
    except ImportError:
        logger.warning("openai package not installed — OpenAI STT unavailable.")


SUPPORTED_FORMATS = {
    "audio/wav", "audio/mpeg", "audio/mp4",
    "audio/webm", "audio/ogg", "audio/x-wav",
    "audio/mp3", "application/octet-stream"
}


async def transcribe_audio(audio_file: UploadFile) -> str:
    """
    Transcribe an uploaded audio file.
    """
    content_type = audio_file.content_type or "application/octet-stream"
    logger.info(f"Transcribing audio: {audio_file.filename}, type={content_type}")

    # Determine file extension
    filename = audio_file.filename or "audio.webm"
    content = await audio_file.read()
    
    return await transcribe_audio_bytes(content, filename)


async def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """
    Transcribe raw audio bytes.
    """
    ext = os.path.splitext(filename)[-1] or ".ogg"

    # Write to a temp file
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(audio_bytes)

    try:
        # ── Try Groq Whisper first ──────────────────────────────────
        if groq_client:
            try:
                with open(tmp_path, "rb") as f:
                    response = groq_client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=(filename, f),
                        language="en",
                    )
                transcript = response.text.strip()
                if transcript:
                    logger.info(f"Groq Whisper transcription: {transcript[:80]}...")
                    return transcript
                else:
                    logger.warning("Groq Whisper returned empty transcript.")
            except Exception as e:
                logger.warning(f"Groq Whisper failed: {e}")

        # ── Try OpenAI Whisper fallback ─────────────────────────────
        if openai_client:
            try:
                with open(tmp_path, "rb") as f:
                    response = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        language="en",
                    )
                transcript = response.text.strip()
                if transcript:
                    logger.info(f"OpenAI Whisper transcription: {transcript[:80]}...")
                    return transcript
                else:
                    logger.warning("OpenAI Whisper returned empty transcript.")
            except Exception as e:
                logger.warning(f"OpenAI Whisper failed: {e}")

        # ── Fallback to mock ────────────────────────────────────────
        logger.warning("No working STT service. Using mock transcription.")
        return "This is a mock transcription. Please configure a valid GROQ_API_KEY or OPENAI_API_KEY for real speech recognition."

    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
