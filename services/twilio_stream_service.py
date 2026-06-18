"""
VocalDesk – Twilio Stream Service
Handles real-time WebSocket audio streaming, VAD (Voice Activity Detection), and AI conversation loop.
"""

import os
import json
import base64
import logging
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydub import AudioSegment
import io

from backend.database.connection import SessionLocal
from backend.services import stt_service, groq_service, tts_service, lead_service

logger = logging.getLogger(__name__)

# Constants for Twilio Audio
# Twilio sends 8000Hz, 8-bit, 1-channel, mu-law audio
SAMPLE_RATE = 8000
CHANNELS = 1

# VAD Constants
SILENCE_THRESHOLD_RMS = 500  # Adjust based on background noise
SILENCE_DURATION_SECONDS = 1.5  # Seconds of silence to trigger AI response

class TwilioStreamConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.stream_sid = None
        self.audio_buffer = bytearray()
        self.silence_chunks = 0
        self.is_processing = False
        
        # Audio formatting
        self.chunk_duration_ms = 20  # Typical Twilio chunk
        self.chunks_per_second = 1000 / self.chunk_duration_ms
        self.silence_chunks_threshold = int(SILENCE_DURATION_SECONDS * self.chunks_per_second)

    async def connect(self):
        await self.websocket.accept()
        logger.info("Twilio WebSocket connected.")

    async def handle_media(self, payload: str):
        if self.is_processing:
            return  # Ignore incoming audio while AI is speaking/thinking

        # Decode base64 payload to mu-law bytes
        audio_chunk = base64.b64decode(payload)
        self.audio_buffer.extend(audio_chunk)

        # We can analyze the RMS of this chunk to detect silence
        try:
            # Load mu-law bytes into AudioSegment
            segment = AudioSegment(
                data=audio_chunk,
                sample_width=1,  # 8-bit
                frame_rate=SAMPLE_RATE,
                channels=CHANNELS
            )
            # Twilio audio is actually G.711 mu-law, pydub natively needs standard PCM if passing directly, 
            # but wait, pydub cannot load raw mu-law easily without setting codec if we just pass bytes.
            # Actually, let's just dump it into a buffer and wait for a certain size for simplicity, 
            # OR we can just use a simple heuristic for RMS on the raw bytes if they are 8-bit.
            # Since mu-law is logarithmic, checking for exact silence (0xFF) is possible.
            # For a proper VAD without audioop, we can rely on a simpler timeout or write a small decoder.
            
            # Let's write a simple energy function for mu-law:
            # 0xFF is silence in mu-law. 
            non_silence_bytes = sum(1 for b in audio_chunk if b not in (0xff, 0x7f, 0xfe))
            
            # If less than 10% of the chunk is non-silence, consider it silence
            if non_silence_bytes < len(audio_chunk) * 0.1:
                self.silence_chunks += 1
            else:
                self.silence_chunks = 0

            # If user has spoken something (buffer > 1 second) and now is silent
            if len(self.audio_buffer) > SAMPLE_RATE * 1 and self.silence_chunks >= self.silence_chunks_threshold:
                logger.info("Silence detected. Triggering AI processing.")
                await self.process_turn()

        except Exception as e:
            logger.error(f"Error processing media chunk: {e}")

    async def process_turn(self):
        self.is_processing = True
        
        # Take a copy of the buffer and clear it
        audio_data = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        self.silence_chunks = 0

        logger.info(f"Processing turn with {len(audio_data)} bytes of mu-law audio.")

        try:
            # 1. Convert mu-law to WAV using ffmpeg via pydub
            # We must tell pydub it's raw mu-law at 8000Hz 1-channel
            with io.BytesIO(audio_data) as in_f:
                # Use from_file with format and codec
                audio_segment = AudioSegment.from_file(
                    in_f, 
                    format="raw", 
                    codec="pcm_mulaw", 
                    frame_rate=SAMPLE_RATE, 
                    channels=CHANNELS, 
                    sample_width=1
                )
            
            with io.BytesIO() as wav_io:
                audio_segment.export(wav_io, format="wav")
                wav_bytes = wav_io.getvalue()

            # 2. Transcribe (STT)
            user_text = await stt_service.transcribe_audio_bytes(wav_bytes, filename="twilio_audio.wav")
            if not user_text.strip():
                logger.warning("No speech recognized. Resuming listening.")
                self.is_processing = False
                return

            logger.info(f"User (Twilio): {user_text}")

            # 3. AI Generation
            # Ideally, we should maintain conversation history per Call SID.
            # For MVP, we use the standard Groq service logic.
            ai_result = groq_service.generate_response(user_text)
            reply_text = ai_result["reply_text"]
            lead_data = ai_result.get("lead_data", {})

            logger.info(f"AI (Twilio): {reply_text}")

            # Save lead if we have contact info (optional mid-call)
            if lead_data.get("name") or lead_data.get("email"):
                db = SessionLocal()
                try:
                    lead_service.save_lead(
                        db=db,
                        name=lead_data.get("name"),
                        email=lead_data.get("email"),
                        phone="twilio_caller", # We could extract caller ID from the POST request
                        product_interest=lead_data.get("product_interest"),
                        conversation_summary=f"User: {user_text}\nAI: {reply_text}",
                        source_channel="twilio_voice",
                    )
                finally:
                    db.close()

            # 4. Text-to-Speech (TTS)
            tts_audio_bytes = await tts_service.text_to_speech(reply_text)
            
            if tts_audio_bytes:
                # 5. Convert TTS MP3/WAV to 8000Hz mu-law for Twilio
                with io.BytesIO(tts_audio_bytes) as tts_in:
                    tts_segment = AudioSegment.from_file(tts_in)
                    # Resample to 8000Hz, 1 channel
                    tts_segment = tts_segment.set_frame_rate(8000).set_channels(1)
                    
                    with io.BytesIO() as tts_out:
                        # Export as raw mu-law
                        tts_segment.export(tts_out, format="raw", codec="pcm_mulaw")
                        out_bytes = tts_out.getvalue()
                
                # Send audio in small chunks back to Twilio
                chunk_size = 4000  # 0.5 second chunks
                for i in range(0, len(out_bytes), chunk_size):
                    chunk = out_bytes[i:i+chunk_size]
                    encoded_payload = base64.b64encode(chunk).decode("utf-8")
                    
                    media_message = {
                        "event": "media",
                        "streamSid": self.stream_sid,
                        "media": {
                            "payload": encoded_payload
                        }
                    }
                    await self.websocket.send_json(media_message)
                    
                    # Sleep slightly to let audio play (Twilio buffers internally too)
                    await asyncio.sleep(0.1)
                
                # Optionally send a mark event when done speaking
                mark_message = {
                    "event": "mark",
                    "streamSid": self.stream_sid,
                    "mark": {"name": "ai_response_complete"}
                }
                await self.websocket.send_json(mark_message)
            
        except Exception as e:
            logger.error(f"Error in Twilio turn processing: {e}")
        finally:
            self.is_processing = False

    async def receive_loop(self):
        try:
            while True:
                data = await self.websocket.receive_text()
                message = json.loads(data)
                
                event = message.get("event")
                
                if event == "start":
                    self.stream_sid = message["start"]["streamSid"]
                    logger.info(f"Twilio stream started: {self.stream_sid}")
                
                elif event == "media":
                    payload = message["media"]["payload"]
                    await self.handle_media(payload)
                
                elif event == "stop":
                    logger.info("Twilio stream stopped.")
                    break
                
        except WebSocketDisconnect:
            logger.info("Twilio WebSocket disconnected.")
        except Exception as e:
            logger.error(f"Twilio WebSocket error: {e}")
