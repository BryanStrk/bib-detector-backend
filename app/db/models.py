"""SQLModel ORM models for persisted photos and their detections.

These are the *table* models. They are intentionally separate from the
Pydantic API schemas in ``app.schemas`` so the storage layout (e.g. bbox split
into columns) can evolve independently of the wire contract.

Note: this module deliberately does NOT use ``from __future__ import
annotations`` — SQLModel needs the real relationship type objects (not strings)
to configure the ORM mappers.
"""

from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    """Return the current UTC time (factory for ``created_at`` defaults)."""
    return datetime.now(timezone.utc)


class Event(SQLModel, table=True):
    """A race event that owns a roster of participants."""

    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    event_date: Optional[date] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)

    participants: List["Participant"] = Relationship(
        back_populates="event",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Participant(SQLModel, table=True):
    """A registered athlete (bib number + identity) belonging to an Event."""

    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("event_id", "bib_number", name="uq_participant_event_bib"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    # DB-level CASCADE so deleting an event clears its roster even outside the
    # ORM; the relationship below adds the ORM-level delete-orphan cascade.
    event_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("events.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
    )
    bib_number: str = Field(index=True)
    full_name: str
    email: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)

    event: Optional[Event] = Relationship(back_populates="participants")


class Photo(SQLModel, table=True):
    """A processed race photo and its detection run metadata."""

    __tablename__ = "photos"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    cloudinary_url: Optional[str] = Field(default=None)
    cloudinary_public_id: Optional[str] = Field(default=None)
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    processing_time: float
    status: str = Field(default="completed")
    # Cloudinary delivery type: "upload" (legacy public assets) or
    # "authenticated" (newer private assets served via signed URLs). The column
    # is added to existing databases via a manual migration.
    storage_type: str = Field(default="upload", index=False)
    created_at: datetime = Field(default_factory=_utcnow, index=True)
    # Optional link to the event this photo belongs to. No inverse relationship;
    # ON DELETE SET NULL so removing an event detaches (not deletes) its photos.
    # The column itself is added to existing databases via a manual migration.
    event_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("events.id", ondelete="SET NULL"),
            index=True,
            nullable=True,
        ),
    )

    detections: List["Detection"] = Relationship(
        back_populates="photo",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )


class Detection(SQLModel, table=True):
    """A single bib detection belonging to a :class:`Photo`."""

    __tablename__ = "detections"

    id: Optional[int] = Field(default=None, primary_key=True)
    photo_id: int = Field(foreign_key="photos.id", index=True)
    bib_number: str = Field(index=True)
    confidence: float
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float

    photo: Optional[Photo] = Relationship(back_populates="detections")
