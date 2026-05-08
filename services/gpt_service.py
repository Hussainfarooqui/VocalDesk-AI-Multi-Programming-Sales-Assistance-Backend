"""
VocalDesk – AI Service (GPT-4o-mini)
Structured JSON response: { reply_text, lead_data }.
Per-session conversation history support.
"""

import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SALES_SYSTEM_PROMPT = """You are VocalDesk — a professional AI Sales Assistant.
Your mission: understand customer needs through natural conversation and qualify leads.

Rules:
- Be warm, consultative, and professional
- Ask ONE clarifying question per turn to understand needs
- Keep replies concise: 2-4 sentences maximum
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
    Generate a structured AI sales response.

    Args:
        transcript: The user's current input (text).
        conversation_history: Optional list of prior message dicts {"role": ..., "content": ...}.

    Returns:
        Dict with keys:
            reply_text (str): The human-readable AI reply.
            lead_data (dict): Extracted lead fields {name, email, phone, product_interest}.

    Raises:
        RuntimeError: If GPT API call fails.
    """
    messages = [{"role": "system", "content": SALES_SYSTEM_PROMPT}]

    if conversation_history:
        # Keep last 8 messages (4 turns) for context
        messages.extend(conversation_history[-8:])

    messages.append({"role": "user", "content": transcript})

    logger.info(f"GPT request: {transcript[:100]}")

    api_key = os.getenv("OPENAI_API_KEY", "")
    if "sk-test-dummy" in api_key or "sk-your-openai" in api_key:
        logger.info("Using mock GPT response due to dummy API key.")
        return _parse_response(
            "Hello! I am the VocalDesk mock AI. Your message was received successfully.\n"
            "<lead_data>\n"
            '{"name": null, "email": null, "phone": null, "product_interest": null}\n'
            "</lead_data>"
        )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        )
        raw = response.choices[0].message.content.strip()
        logger.info(f"GPT raw response: {raw[:120]}")

        return _parse_response(raw)

    except Exception as e:
        logger.error(f"GPT generation failed: {e}")
        raise RuntimeError(f"AI processing failed: {str(e)}")


def _parse_response(raw: str) -> dict:
    """
    Parse the model's raw output into reply_text + lead_data.
    Splits on <lead_data> tag; falls back gracefully if tag is missing.
    """
    lead_data = {"name": None, "email": None, "phone": None, "product_interest": None}
    reply_text = raw

    if "<lead_data>" in raw and "</lead_data>" in raw:
        parts = raw.split("<lead_data>")
        reply_text = parts[0].strip()
        json_part = parts[1].split("</lead_data>")[0].strip()
        try:
            extracted = json.loads(json_part)
            lead_data = {
                "name": extracted.get("name"),
                "email": extracted.get("email"),
                "phone": extracted.get("phone"),
                "product_interest": extracted.get("product_interest"),
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Lead data JSON parse failed: {e}")

    return {"reply_text": reply_text, "lead_data": lead_data}
