"""
VocalDesk – Email Service (SMTP SSL)
Sends thank-you email to lead and notification email to admin.
All credentials from environment variables.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "VocalDesk")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@vocaldesk.ai")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@vocaldesk.ai")


def _send_email(to_address: str, subject: str, html_body: str) -> bool:
    """Internal helper: send a single HTML email via SMTP SSL."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured — skipping email.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_address
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, to_address, msg.as_string())
        logger.info(f"Email sent: to={to_address}, subject='{subject}'")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — check SMTP_USER and SMTP_PASSWORD.")
        return False
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_thank_you_email(lead_name: str, lead_email: str) -> bool:
    """
    Send a thank-you email to the lead after conversation ends.

    Args:
        lead_name: Customer name (may be None).
        lead_email: Customer email address.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not lead_email:
        logger.info("No lead email provided — skipping thank-you email.")
        return False

    name = lead_name or "there"
    subject = "Thank you for connecting with VocalDesk!"
    body = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #00A9A5, #00d4d0); padding: 40px; border-radius: 12px; text-align: center;">
            <h1 style="color: white; margin: 0;">VocalDesk</h1>
            <p style="color: rgba(255,255,255,0.9); margin-top: 8px;">AI Voice Sales Assistant</p>
        </div>
        <div style="padding: 32px;">
            <h2 style="color: #00A9A5;">Hi {name}, thank you for reaching out! 👋</h2>
            <p>We appreciate you taking the time to speak with our AI assistant. A member of our team will review your conversation and get in touch shortly.</p>
            <p>In the meantime, if you have any immediate questions, feel free to reply to this email.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
            <p style="color: #888; font-size: 14px;">VocalDesk — Multi-Platform AI Voice Sales Assistant</p>
        </div>
    </body></html>
    """
    return _send_email(lead_email, subject, body)


def send_admin_notification(lead_data: dict) -> bool:
    """
    Send a lead notification email to the admin.

    Args:
        lead_data: Lead dictionary with name, email, phone, etc.

    Returns:
        True if sent successfully, False otherwise.
    """
    subject = f"🔔 New VocalDesk Lead: {lead_data.get('name') or 'Unknown'}"
    channel = lead_data.get("source_channel", "web").upper()
    body = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; padding: 24px; border-radius: 12px;">
            <h2 style="color: #00A9A5; margin: 0;">New Lead Captured [{channel}]</h2>
        </div>
        <div style="padding: 24px; background: #f9f9f9; border-radius: 12px; margin-top: 12px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; font-weight: bold; color: #555; width: 140px;">Name</td>
                    <td style="padding: 8px;">{lead_data.get('name') or '—'}</td>
                </tr>
                <tr style="background: white;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Email</td>
                    <td style="padding: 8px;">{lead_data.get('email') or '—'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold; color: #555;">Phone</td>
                    <td style="padding: 8px;">{lead_data.get('phone') or '—'}</td>
                </tr>
                <tr style="background: white;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Interest</td>
                    <td style="padding: 8px;">{lead_data.get('product_interest') or '—'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold; color: #555;">Channel</td>
                    <td style="padding: 8px;">{channel}</td>
                </tr>
                <tr style="background: white;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Lead ID</td>
                    <td style="padding: 8px; font-family: monospace; font-size: 12px;">{lead_data.get('id') or '—'}</td>
                </tr>
            </table>
        </div>
        <div style="padding: 16px; color: #888; font-size: 13px; text-align: center;">
            VocalDesk Admin Dashboard — <a href="http://localhost:8000/admin" style="color: #00A9A5;">View All Leads</a>
        </div>
    </body></html>
    """
    return _send_email(ADMIN_EMAIL, subject, body)
