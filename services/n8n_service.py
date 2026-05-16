"""
VocalDesk – n8n Service
Triggers n8n workflow webhook for lead processing.
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)

def trigger_webhook(lead_data: dict) -> bool:
    """
    Sends lead data to the n8n webhook.
    """
    # Read URL inside function to ensure we get the latest env value
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    
    if not webhook_url:
        logger.warning("N8N_WEBHOOK_URL not configured. Skipping n8n automation.")
        return False

    logger.info(f"Triggering n8n webhook: {webhook_url}")

    try:
        # Send data to n8n webhook
        response = httpx.post(
            webhook_url,
            json=lead_data,
            timeout=10.0
        )
        response.raise_for_status()
        logger.info(f"Successfully triggered n8n webhook for lead ID: {lead_data.get('id')}")
        return True
    except httpx.HTTPStatusError as e:
        logger.error(f"N8N Webhook returned error status {e.response.status_code}: {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to n8n webhook at {webhook_url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when calling n8n webhook: {e}")
        return False
