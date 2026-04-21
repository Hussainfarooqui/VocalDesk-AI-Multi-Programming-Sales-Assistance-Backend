"""
VocalDesk – STT Service
OpenAI Whisper API integration for Speech-to-Text transcription.
"""

import os
import logging
import tempfile
from openai import OpenAI
from fastapi import UploadFile

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUPPORTED_FORMATS = {
    "audio/wav", "audio/mpeg", "audio/mp4",
    "audio/webm", "audio/ogg", "audio/x-wav",
    "audio/mp3", "application/octet-stream"
}


async def transcribe_audio(audio_file: UploadFile) -> str:
    """
    Transcribe an uploaded audio file using OpenAI Whisper.

    Args:
        audio_file: FastAPI UploadFile object.

    Returns:
        Transcribed text string.

    Raises:
        ValueError: If audio format is unsupported.
        RuntimeError: If Whisper API call fails.
    """
    content_type = audio_file.content_type or "application/octet-stream"
    logger.info(f"Transcribing audio: {audio_file.filename}, type={content_type}")

    # Determine file extension
    filename = audio_file.filename or "audio.webm"
    ext = os.path.splitext(filename)[-1] or ".webm"

    # Write to a temp file for Whisper API
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
        content = await audio_file.read()
        tmp.write(content)

    try:
        with open(tmp_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en",
            )
        transcript = response.text.strip()
        logger.info(f"Transcription successful: {transcript[:80]}...")
        return transcript
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise RuntimeError(f"Speech-to-text failed: {str(e)}")
    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
