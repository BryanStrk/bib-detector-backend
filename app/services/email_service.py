"""Transactional email via Resend.

Thin wrapper around the ``resend`` SDK so the rest of the app depends on a
small, typed surface (``send_claim_email``) instead of the provider directly.
"""

from __future__ import annotations

import logging

import resend

from app.core.config import get_settings
from app.core.exceptions import EmailError

logger = logging.getLogger(__name__)


def send_claim_email(to_email: str, magic_link: str, event_name: str) -> None:
    """Send the claim magic-link email to a participant.

    Args:
        to_email: Recipient address (the participant's registered email).
        magic_link: Single-use URL that verifies the claim.
        event_name: Name of the event, shown in the email body.

    Raises:
        EmailError: If the Resend API call fails.
    """
    settings = get_settings()
    resend.api_key = settings.resend_api_key

    html = (
        f"<p>Hi,</p>"
        f"<p>We received a request to claim your photos for "
        f"<strong>{event_name}</strong>.</p>"
        f'<p><a href="{magic_link}">Click here to view your photos</a>. '
        f"This link expires in {settings.claim_token_expire_minutes} minutes.</p>"
        f"<p>If you didn't request this, you can safely ignore this email.</p>"
    )

    try:
        resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": f"Claim your photos from {event_name}",
                "html": html,
            }
        )
    except Exception as exc:  # noqa: BLE001 - provider may raise any error type
        logger.exception("Failed to send claim email to %s", to_email)
        raise EmailError("Failed to send claim email.") from exc
