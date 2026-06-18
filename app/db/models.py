"""SQLModel ORM models for persisted photos and their detections.

These are the *table* models. They are intentionally separate from the
Pydantic API schemas in ``app.schemas`` so the storage layout (e.g. bbox split
into columns) can evolve independently of the wire contract.

Note: this module deliberately does NOT use ``from __future__ import
annotations`` — SQLModel needs the real relationship type objects (not strings)
to configure the ORM mappers.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    """Return the current UTC time (factory for ``created_at`` defaults)."""
    return datetime.now(timezone.utc)


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
    created_at: datetime = Field(default_factory=_utcnow, index=True)

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
