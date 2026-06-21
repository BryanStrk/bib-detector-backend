"""Service layer for events and participant rosters (router -> service -> db).

Owns all database access for creating events, listing them with their
participant counts, and importing participants from an uploaded CSV.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.exceptions import EventNotFoundError
from app.db.models import Event, Participant
from app.schemas.event import EventCreate, ImportResult, ParticipantImportItem

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Build a URL-safe slug from ``name``.

    Lowercases, strips accents via Unicode NFKD normalization, collapses
    whitespace/hyphens into single hyphens, and drops any remaining
    non-alphanumeric characters. Uses only the standard library.
    """
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_only = re.sub(r"[^a-z0-9\s-]", "", ascii_only)
    return re.sub(r"[\s-]+", "-", ascii_only).strip("-")


def create_event(session: Session, data: EventCreate) -> Event:
    """Create an event, assigning a unique slug derived from its name.

    If the base slug is already taken, a numeric suffix (``-2``, ``-3``, ...)
    is appended until a free slug is found.

    Returns:
        The persisted :class:`Event`, refreshed with its ID.
    """
    base_slug = _slugify(data.name) or "event"
    slug = base_slug
    suffix = 2
    while session.exec(select(Event).where(Event.slug == slug)).first() is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    event = Event(name=data.name, slug=slug, event_date=data.event_date)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def list_events(session: Session) -> list[tuple[Event, int]]:
    """Return all events paired with their participant counts (newest first)."""
    statement = (
        select(Event, func.count(Participant.id))
        .outerjoin(Participant, Participant.event_id == Event.id)
        .group_by(Event.id)
        .order_by(Event.created_at.desc())
    )
    return [(event, count) for event, count in session.exec(statement).all()]


def add_participants(
    session: Session, event_id: int, items: list[ParticipantImportItem]
) -> ImportResult:
    """Bulk-add participants to an event from a list of items.

    Items with an empty ``bib_number`` or ``full_name`` (after trimming) are
    reported in ``errors``. Bib numbers that already exist for the event or
    repeat within the list are counted as ``skipped``. Valid, unique items are
    bulk-inserted.

    Args:
        items: Participants to register; ``row`` in any error is the item's
            1-based index in this list.

    Raises:
        EventNotFoundError: If ``event_id`` does not exist.
    """
    if session.get(Event, event_id) is None:
        raise EventNotFoundError(f"Event {event_id} not found.")

    existing_bibs = set(
        session.exec(
            select(Participant.bib_number).where(
                Participant.event_id == event_id
            )
        ).all()
    )

    seen: set[str] = set()
    errors: list[dict] = []
    skipped = 0
    to_create: list[Participant] = []

    for index, item in enumerate(items, start=1):
        bib_number = (item.bib_number or "").strip()
        full_name = (item.full_name or "").strip()
        email = (item.email or "").strip() or None

        if not bib_number or not full_name:
            errors.append(
                {
                    "row": index,
                    "reason": "Missing required bib_number or full_name.",
                }
            )
            continue

        if bib_number in existing_bibs or bib_number in seen:
            skipped += 1
            continue

        seen.add(bib_number)
        to_create.append(
            Participant(
                event_id=event_id,
                bib_number=bib_number,
                full_name=full_name,
                email=email,
            )
        )

    if to_create:
        session.add_all(to_create)
        session.commit()

    return ImportResult(created=len(to_create), skipped=skipped, errors=errors)
