"""Pydantic DTOs for the persisted photo history endpoints.

These map the ORM models in :mod:`app.db.models` to the API wire format,
reassembling the split bbox columns into the ``[x, y, w, h]`` list used
everywhere else in the API.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import Photo


class DetectionRead(BaseModel):
    """A persisted detection as returned by the history endpoints."""

    id: int
    bib_number: str
    confidence: float
    bbox: list[float] = Field(
        ...,
        description="Bounding box as [x, y, w, h] in pixels (top-left origin).",
    )


class PhotoRead(BaseModel):
    """A persisted photo with its detections."""

    id: int
    filename: str
    cloudinary_url: str | None
    width: int | None
    height: int | None
    processing_time: float
    status: str
    created_at: datetime
    detections: list[DetectionRead]

    @classmethod
    def from_model(cls, photo: Photo) -> "PhotoRead":
        """Build a ``PhotoRead`` from a :class:`~app.db.models.Photo` row."""
        return cls(
            id=photo.id,
            filename=photo.filename,
            cloudinary_url=photo.cloudinary_url,
            width=photo.width,
            height=photo.height,
            processing_time=photo.processing_time,
            status=photo.status,
            created_at=photo.created_at,
            detections=[
                DetectionRead(
                    id=det.id,
                    bib_number=det.bib_number,
                    confidence=det.confidence,
                    bbox=[det.bbox_x, det.bbox_y, det.bbox_w, det.bbox_h],
                )
                for det in photo.detections
            ],
        )
