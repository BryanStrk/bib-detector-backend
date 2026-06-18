"""Service layer for persisting and querying photos and detections.

The router calls into these functions; they own all database access so the
route handlers stay thin (router -> service -> db).
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import Session, select

from app.db.models import Detection as DetectionRow
from app.db.models import Photo
from app.schemas.detection import Detection as DetectionSchema

# Default number of photos returned by the history listing.
_DEFAULT_HISTORY_LIMIT = 50


def create_photo(
    session: Session,
    *,
    filename: str,
    cloudinary_url: str | None,
    cloudinary_public_id: str | None,
    width: int | None,
    height: int | None,
    processing_time: float,
    detections: Sequence[DetectionSchema],
    status: str = "completed",
) -> Photo:
    """Persist a photo and its detections in a single transaction.

    Args:
        session: Active database session.
        detections: Detection DTOs produced by the detection pipeline; their
            ``bbox`` list is unpacked into the stored column layout.

    Returns:
        The persisted :class:`~app.db.models.Photo`, refreshed with its ID.
    """
    photo = Photo(
        filename=filename,
        cloudinary_url=cloudinary_url,
        cloudinary_public_id=cloudinary_public_id,
        width=width,
        height=height,
        processing_time=processing_time,
        status=status,
        detections=[
            DetectionRow(
                bib_number=d.bib_number,
                confidence=d.confidence,
                bbox_x=d.bbox[0],
                bbox_y=d.bbox[1],
                bbox_w=d.bbox[2],
                bbox_h=d.bbox[3],
            )
            for d in detections
        ],
    )
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def list_photos(
    session: Session, limit: int = _DEFAULT_HISTORY_LIMIT
) -> Sequence[Photo]:
    """Return the most recent photos (newest first) with their detections."""
    statement = select(Photo).order_by(Photo.created_at.desc()).limit(limit)
    return session.exec(statement).all()


def get_photo(session: Session, photo_id: int) -> Photo | None:
    """Return a single photo by ID, or ``None`` if not found."""
    return session.get(Photo, photo_id)
