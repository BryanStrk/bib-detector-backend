"""Runner self-service routes: ``GET /me/photos`` (private gallery)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.security import RunnerContext, get_current_runner
from app.db.session import get_session
from app.schemas.photo import PhotoRead
from app.services import photo_service

router = APIRouter(tags=["me"])


@router.get("/me/photos", response_model=list[PhotoRead])
def list_my_photos(
    runner: RunnerContext = Depends(get_current_runner),
    session: Session = Depends(get_session),
) -> list[PhotoRead]:
    """Return the authenticated runner's photos for their event (newest first).

    Scoped to the runner's own ``event_id`` and ``bib_number`` from their token,
    so it never exposes photos from other events or bib numbers. Requires a
    valid runner bearer token (401 otherwise).
    """
    photos = photo_service.get_runner_photos(
        session, runner.event_id, runner.bib_number
    )
    return [
        PhotoRead.from_model_runner(photo, runner.bib_number) for photo in photos
    ]
