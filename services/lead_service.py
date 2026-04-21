"""
VocalDesk – Lead Service (v2)
Handles lead persistence and retrieval with new model fields.
"""

import logging
from sqlalchemy.orm import Session
from backend.models.lead import Lead

logger = logging.getLogger(__name__)


def save_lead(
    db: Session,
    name: str = None,
    email: str = None,
    phone: str = None,
    product_interest: str = None,
    conversation_summary: str = None,
    source_channel: str = "web",
) -> Lead:
    """
    Create and persist a new lead record.

    Args:
        db: SQLAlchemy session.
        name: Customer name.
        email: Customer email.
        phone: Customer phone.
        product_interest: Extracted product/service interest.
        conversation_summary: Full conversation transcript.
        source_channel: "web" or "whatsapp".

    Returns:
        Saved Lead ORM object.
    """
    lead = Lead(
        name=name,
        email=email,
        phone=phone,
        product_interest=product_interest,
        conversation_summary=conversation_summary,
        source_channel=source_channel,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info(f"Lead saved: id={lead.id}, channel={source_channel}, email={email}")
    return lead


def get_leads(db: Session, skip: int = 0, limit: int = 50) -> list[Lead]:
    """Retrieve paginated list of leads, most recent first."""
    return (
        db.query(Lead)
        .order_by(Lead.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
