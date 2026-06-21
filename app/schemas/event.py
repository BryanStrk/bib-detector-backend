"""Pydantic schemas for the events API (events, participants, CSV import).

These define the wire contract for managing race events and their participant
rosters, mirroring the ORM models in :mod:`app.db.models`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.db.models import Event, Participant


class EventCreate(BaseModel):
    """Request body for ``POST /events``."""

    name: str = Field(..., description="Human-readable event name.")
    event_date: date | None = Field(
        default=None, description="Date the event takes place (optional)."
    )


class EventResponse(BaseModel):
    """An event with its participant count, as returned by the events API."""

    id: int
    name: str
    slug: str
    event_date: date | None
    created_at: datetime
    participant_count: int = Field(
        ..., description="Number of participants registered for the event."
    )

    @classmethod
    def from_model(cls, event: Event, participant_count: int) -> "EventResponse":
        """Build an ``EventResponse`` from an :class:`Event` and its count."""
        return cls(
            id=event.id,
            name=event.name,
            slug=event.slug,
            event_date=event.event_date,
            created_at=event.created_at,
            participant_count=participant_count,
        )


class ParticipantImportItem(BaseModel):
    """A single participant to register via the bulk-add endpoint."""

    bib_number: str = Field(..., description="The athlete's bib number.")
    full_name: str = Field(..., description="The athlete's full name.")
    email: str | None = Field(default=None, description="Contact email (optional).")


class ParticipantBulkCreate(BaseModel):
    """Request body for bulk-adding participants to an event."""

    participants: list[ParticipantImportItem] = Field(
        default_factory=list,
        description="Participants to register for the event.",
    )


class ParticipantResponse(BaseModel):
    """A single registered participant."""

    id: int
    bib_number: str
    full_name: str
    email: str | None
    created_at: datetime

    @classmethod
    def from_model(cls, participant: Participant) -> "ParticipantResponse":
        """Build a ``ParticipantResponse`` from a :class:`Participant` row."""
        return cls(
            id=participant.id,
            bib_number=participant.bib_number,
            full_name=participant.full_name,
            email=participant.email,
            created_at=participant.created_at,
        )


class ImportResult(BaseModel):
    """Outcome of a participant CSV import."""

    created: int = Field(..., description="Number of participants inserted.")
    skipped: int = Field(
        ..., description="Rows skipped as duplicates (existing or repeated)."
    )
    errors: list[dict] = Field(
        default_factory=list,
        description="Per-row validation failures as {'row': int, 'reason': str}.",
    )
