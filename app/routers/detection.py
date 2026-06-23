"""Detection API routes: ``POST /detect`` and ``GET /health``."""

from __future__ import annotations

import io
import time

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from PIL import Image, UnidentifiedImageError
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import EventNotFoundError
from app.core.rate_limit import limiter
from app.db.models import Event
from app.db.session import get_session
from app.schemas.detection import DetectResponse, HealthResponse
from app.services import photo_service, storage
from app.services.detector import BibDetector, get_detector

router = APIRouter(tags=["detection"])

# MIME types accepted by the upload endpoint.
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


def _image_dimensions(image_bytes: bytes) -> tuple[int | None, int | None]:
    """Best-effort decode of an image's (width, height); ``(None, None)`` on failure."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            return img.width, img.height
    except (UnidentifiedImageError, OSError):
        return None, None


@router.get("/health", response_model=HealthResponse)
def health(detector: BibDetector = Depends(get_detector)) -> HealthResponse:
    """Liveness probe that also reports the active detection backend."""
    return HealthResponse(status="ok", detector=detector.backend)


@router.post("/detect", response_model=DetectResponse)
@limiter.limit("10/minute")
async def detect(
    request: Request,
    file: UploadFile = File(..., description="Race photo (JPEG or PNG)."),
    event_id: int | None = Form(
        default=None, description="Optional event to associate the photo with."
    ),
    detector: BibDetector = Depends(get_detector),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> DetectResponse:
    """Detect bib numbers in an uploaded race photo, store and persist it.

    Flow: validate -> detect -> upload to Cloudinary -> persist Photo +
    Detections -> return the detections plus the new photo id and image URL.
    When ``event_id`` is provided, the photo is linked to that event.

    Rate limited to 10 requests/minute per client IP.

    Raises:
        HTTPException: 400 for an invalid/empty upload, 413 if it exceeds
            ``MAX_UPLOAD_MB``.
        EventNotFoundError: 404 if ``event_id`` is given but does not exist.
    """
    if event_id is not None and session.get(Event, event_id) is None:
        raise EventNotFoundError(f"Event {event_id} not found.")

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image/jpeg and image/png uploads are supported.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds the {settings.max_upload_mb} MB limit.",
        )

    # 2. Run the existing detection pipeline (timed).
    start = time.perf_counter()
    detections = detector.detect(image_bytes)
    processing_time = time.perf_counter() - start

    # 3. Upload the original image to Cloudinary.
    filename = file.filename or "upload"
    cloudinary_url, public_id = storage.upload_image(image_bytes, filename)

    # 4. Persist the photo and its detections.
    width, height = _image_dimensions(image_bytes)
    photo = photo_service.create_photo(
        session,
        filename=filename,
        cloudinary_url=cloudinary_url,
        cloudinary_public_id=public_id,
        width=width,
        height=height,
        processing_time=processing_time,
        detections=detections,
        event_id=event_id,
    )

    # 5. Return the same response shape as before, plus id and image URL.
    return DetectResponse(
        photo_id=photo.id,
        cloudinary_url=cloudinary_url,
        filename=filename,
        processing_time=processing_time,
        detections=detections,
    )
