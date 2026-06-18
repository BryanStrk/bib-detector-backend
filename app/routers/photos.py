"""Photo history routes: ``GET /photos`` and ``GET /photos/{id}``."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.photo import PhotoRead
from app.services import photo_service

router = APIRouter(tags=["photos"])


@router.get("/photos", response_model=list[PhotoRead])
def list_photos(session: Session = Depends(get_session)) -> list[PhotoRead]:
    """Return recent processed photos with their detections (newest first)."""
    photos = photo_service.list_photos(session)
    return [PhotoRead.from_model(photo) for photo in photos]


@router.get("/photos/{photo_id}", response_model=PhotoRead)
def get_photo(
    photo_id: int, session: Session = Depends(get_session)
) -> PhotoRead:
    """Return a single photo with its detections, or 404 if not found."""
    photo = photo_service.get_photo(session, photo_id)
    if photo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found.",
        )
    return PhotoRead.from_model(photo)
