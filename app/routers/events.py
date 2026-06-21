"""Event routes: create/list events and import participant rosters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session

from app.core.rate_limit import limiter
from app.core.security import get_current_admin
from app.db.session import get_session
from app.schemas.event import (
    EventCreate,
    EventResponse,
    ImportResult,
    ParticipantBulkCreate,
)
from app.services import event_service

router = APIRouter(tags=["events"])


@router.post(
    "/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    data: EventCreate,
    session: Session = Depends(get_session),
    admin: str = Depends(get_current_admin),
) -> EventResponse:
    """Create a new event with a unique slug. Admin-only.

    Returns 201 with the created event (participant count starts at 0) and 401
    if the request is not authenticated as the admin.
    """
    event = event_service.create_event(session, data)
    return EventResponse.from_model(event, participant_count=0)


@router.get("/events", response_model=list[EventResponse])
def list_events(
    session: Session = Depends(get_session),
) -> list[EventResponse]:
    """Return all events with their participant counts (newest first). Public."""
    return [
        EventResponse.from_model(event, participant_count=count)
        for event, count in event_service.list_events(session)
    ]


@router.post(
    "/events/{event_id}/participants",
    response_model=ImportResult,
)
@limiter.limit("5/minute")
async def add_participants(
    request: Request,
    event_id: int,
    data: ParticipantBulkCreate,
    session: Session = Depends(get_session),
    admin: str = Depends(get_current_admin),
) -> ImportResult:
    """Bulk-add participants to an event. Admin-only.

    Each item needs a non-empty ``bib_number`` and ``full_name`` (``email``
    optional). Rate limited to 5 requests/minute per client IP.

    Returns the import summary, 404 if the event does not exist, and 401 if the
    request is not authenticated.
    """
    return event_service.add_participants(session, event_id, data.participants)
