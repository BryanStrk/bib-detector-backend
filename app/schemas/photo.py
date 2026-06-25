"""Pydantic DTOs for the persisted photo history endpoints.

These map the ORM models in :mod:`app.db.models` to the API wire format,
reassembling the split bbox columns into the ``[x, y, w, h]`` list used
everywhere else in the API.

Two views exist for a photo:

* the **public** gallery (``GET /photos``) only exposes the watermarked
  ``preview_url`` — the clean original is never returned;
* the **runner** gallery (``GET /me/photos``) additionally exposes the original
  ``cloudinary_url`` and limits ``detections`` to the runner's own bib number.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import Photo
from app.services.storage import (
    build_authenticated_preview_url,
    build_preview_url,
    build_signed_original_url,
)


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
    cloudinary_url: str | None = Field(
        default=None,
        description="Original image URL. Only exposed to the photo's runner.",
    )
    preview_url: str = Field(
        ...,
        description="Watermarked, resized preview URL (safe for public display).",
    )
    width: int | None
    height: int | None
    processing_time: float
    status: str
    created_at: datetime
    detections: list[DetectionRead]

    @staticmethod
    def _read_detections(
        photo: Photo, bib_number: str | None = None
    ) -> list[DetectionRead]:
        """Map a photo's detections, optionally filtered to one bib number."""
        return [
            DetectionRead(
                id=det.id,
                bib_number=det.bib_number,
                confidence=det.confidence,
                bbox=[det.bbox_x, det.bbox_y, det.bbox_w, det.bbox_h],
            )
            for det in photo.detections
            if bib_number is None or det.bib_number == bib_number
        ]

    @staticmethod
    def _preview_url(photo: Photo) -> str:
        """Watermarked preview URL, signed for ``authenticated`` assets."""
        if photo.storage_type == "authenticated":
            if not photo.cloudinary_public_id:
                return ""
            return build_authenticated_preview_url(photo.cloudinary_public_id)
        # Legacy "upload" (public) assets: manual unsigned transformation URL.
        return build_preview_url(photo.cloudinary_url) if photo.cloudinary_url else ""

    @staticmethod
    def _original_url(photo: Photo) -> str | None:
        """Original image URL for the runner, signed for ``authenticated`` assets."""
        if photo.storage_type == "authenticated":
            if not photo.cloudinary_public_id:
                return None
            return build_signed_original_url(photo.cloudinary_public_id)
        # Legacy public assets are served directly.
        return photo.cloudinary_url

    @classmethod
    def from_model_public(cls, photo: Photo) -> "PhotoRead":
        """Public view: watermarked preview only, original URL withheld."""
        return cls(
            id=photo.id,
            filename=photo.filename,
            cloudinary_url=None,
            preview_url=cls._preview_url(photo),
            width=photo.width,
            height=photo.height,
            processing_time=photo.processing_time,
            status=photo.status,
            created_at=photo.created_at,
            detections=cls._read_detections(photo),
        )

    @classmethod
    def from_model_runner(cls, photo: Photo, bib_number: str) -> "PhotoRead":
        """Runner view: preview + original, detections limited to ``bib_number``."""
        return cls(
            id=photo.id,
            filename=photo.filename,
            cloudinary_url=cls._original_url(photo),
            preview_url=cls._preview_url(photo),
            width=photo.width,
            height=photo.height,
            processing_time=photo.processing_time,
            status=photo.status,
            created_at=photo.created_at,
            detections=cls._read_detections(photo, bib_number),
        )
