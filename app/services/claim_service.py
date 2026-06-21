"""Claim flow: request a magic-link email to claim a participant's photos.

Designed to be anti-enumeration: the request always succeeds silently whether
or not the (event, bib, email) tuple matches a real participant, so the API
never reveals which bib numbers or emails are registered.
"""

from __future__ import annotations

import logging

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.exceptions import EmailError
from app.core.security import create_claim_token
from app.db.models import Event, Participant
from app.services import email_service

logger = logging.getLogger(__name__)


def request_claim(
    session: Session, event_id: int, bib_number: str, email: str
) -> None:
    """Send a claim magic-link if the details match a participant.

    Looks up the participant by ``(event_id, bib_number)``; if found and the
    registered email matches ``email`` (case-insensitive, trimmed), a claim
    token is minted and emailed to the *registered* address. Email failures are
    logged but never propagated.

    Always returns ``None`` without distinguishing match from no-match (and
    without raising :class:`EventNotFoundError`) to prevent enumeration.
    """
    participant = session.exec(
        select(Participant).where(
            Participant.event_id == event_id,
            Participant.bib_number == bib_number,
        )
    ).first()

    if participant is None or not participant.email:
        return None

    if participant.email.strip().lower() != email.strip().lower():
        return None

    event = session.get(Event, event_id)
    if event is None:
        return None

    settings = get_settings()
    token = create_claim_token(
        participant_id=participant.id,
        event_id=event_id,
        bib_number=bib_number,
    )
    magic_link = f"{settings.frontend_url}/claim/verify?token={token}"

    try:
        email_service.send_claim_email(
            participant.email, magic_link, event.name
        )
    except EmailError:
        logger.warning(
            "Claim email could not be sent for participant %s.",
            participant.id,
        )

    return None
