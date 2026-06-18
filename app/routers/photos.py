"""Photo history routes: ``GET /photos`` and ``GET /photos/{id}``."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.core.security import get_current_admin
from app.db.session import get_session
from app.schemas.photo import PhotoRead
from app.services import photo_service

router = APIRouter(tags=["photos"])


@router.get("/photos", response_model=list[PhotoRead])
def list_photos(
    bib_number: str | None = Query(
        default=None,
        description="Return only photos with a detection matching this bib number exactly.",
    ),
    limit: int = Query(
        default=50, ge=0, le=100, description="Page size (max 100)."
    ),
    offset: int = Query(default=0, ge=0, description="Number of photos to skip."),
    session: Session = Depends(get_session),
) -> list[PhotoRead]:
    """Return recent processed photos with their detections (newest first).

    Supports optional exact-match search by ``bib_number`` and standard
    ``limit``/``offset`` pagination. Out-of-range pagination values are
    rejected with ``422``.
    """
    photos = photo_service.list_photos(
        session, bib_number=bib_number, limit=limit, offset=offset
    )
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


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: int,
    session: Session = Depends(get_session),
    admin: str = Depends(get_current_admin),
) -> Response:
    """Delete a photo and its Cloudinary asset. Admin-only.

    Returns 204 on success, 404 if the photo does not exist, and 401 if the
    request is not authenticated as the admin.
    """
    deleted = photo_service.delete_photo(session, photo_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
