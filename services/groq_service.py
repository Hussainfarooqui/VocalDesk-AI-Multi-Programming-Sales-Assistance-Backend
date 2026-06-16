"""
VocalDesk – Groq AI Service
Integrates Groq Cloud (Llama 3 / Mixtral) for NLP processing.
"""

import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# Initialize Groq client
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

SALES_SYSTEM_PROMPT = """You are VocalDesk — a professional AI Sales Assistant.
Your mission: understand customer needs through natural conversation and qualify leads.

Rules:
- Be warm, consultative, and professional
- You represent a company that builds custom websites and software.
- If asked about costs or pricing, provide approximate estimates: basic websites start around $1,000-$5,000, and custom software/web apps start around $10,000+. Always offer to discuss their specific needs for a tailored quote.
- For VOICE CALLS: Keep responses extremely concise (1-2 short sentences) and punchy.
- Ask ONE clarifying question per turn to understand needs
- Naturally try to collect: name, email, phone, product interest
- Never be pushy; be helpful and value-driven
- Always reply in English

IMPORTANT: At the end of every reply, output a JSON block on a new line in this exact format:
<lead_data>
{"name": null, "email": null, "phone": null, "product_interest": null}
</lead_data>

Fill in any fields you can extract from the conversation so far. Use null for unknown fields."""


def generate_response(transcript: str, conversation_history: list = None) -> dict:
    """
    Generate a structured AI sales response using Groq.

    Args:
        transcript: The user's current input (text).
        conversation_history: Optional list of prior message dicts {"role": ..., "content": ...}.

    Returns:
        Dict with keys:
            reply_text (str): The human-readable AI reply.
            lead_data (dict): Extracted lead fields {name, email, phone, product_interest}.
    """
    if not client:
        logger.error("Groq API key not configured.")
        return _mock_response(transcript)

    messages = [{"role": "system", "content": SALES_SYSTEM_PROMPT}]

    if conversation_history:
        # Keep last 10 messages for context
        messages.extend(conversation_history[-10:])

    messages.append({"role": "user", "content": transcript})

    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant", # Updated from decommissioned llama3-8b-8192
            temperature=0.7,
            max_tokens=512,
        )
        raw_response = chat_completion.choices[0].message.content.strip()
        return _parse_response(raw_response)
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return _mock_response(transcript)


def _parse_response(raw: str) -> dict:
    """
    Parse the model's raw output into reply_text + lead_data.
    """
    lead_data = {"name": None, "email": None, "phone": None, "product_interest": None}
    reply_text = raw

    if "<lead_data>" in raw and "</lead_data>" in raw:
        parts = raw.split("<lead_data>")
        reply_text = parts[0].strip()
        json_part = parts[1].split("</lead_data>")[0].strip()
        try:
            extracted = json.loads(json_part)
            lead_data.update(extracted)
        except json.JSONDecodeError:
            logger.warning("Failed to parse lead_data JSON from Groq response.")

    return {"reply_text": reply_text, "lead_data": lead_data}


def _mock_response(transcript: str) -> dict:
    """Fallback response if API fails."""
    return {
        "reply_text": "I'm sorry, I'm having trouble processing that right now. How else can I help you?",
        "lead_data": {"name": None, "email": None, "phone": None, "product_interest": None}
    }
