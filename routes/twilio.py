"""
VocalDesk – Twilio Webhook Routes
Handles POST requests for incoming calls (TwiML) and WebSocket connections for media streams.
"""

import logging
from fastapi import APIRouter, Request, WebSocket, Response
from backend.services.twilio_stream_service import TwilioStreamConnection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio", tags=["Twilio"])

@router.post("/incoming")
async def twilio_incoming(request: Request):
    """
    Twilio hits this webhook when someone calls the Twilio phone number.
    We return TwiML XML instructing Twilio to connect to our WebSocket.
    """
    # Build the WebSocket URL (use wss:// in production)
    # E.g., request.base_url usually returns http://...
    # We replace http with ws (and https with wss)
    base_url = str(request.base_url)
    ws_scheme = "wss://" if "https" in base_url else "ws://"
    host_path = base_url.split("://")[1].rstrip("/")
    
    # In production on Render, request.base_url might be HTTP behind the proxy.
    # It's safer to check headers or force wss if on render.com
    if "onrender.com" in host_path:
        ws_scheme = "wss://"
        
    ws_url = f"{ws_scheme}{host_path}/api/twilio/stream"

    logger.info(f"Incoming Twilio Call. Redirecting stream to {ws_url}")

    # Generate TwiML
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Welcome to Vocal Desk! How can I help you today?</Say>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""

    return Response(content=twiml, media_type="text/xml")


@router.websocket("/stream")
async def twilio_stream(websocket: WebSocket):
    """
    WebSocket endpoint that receives live audio from Twilio.
    """
    connection = TwilioStreamConnection(websocket)
    await connection.connect()
    
    # Start receiving loop
    await connection.receive_loop()
