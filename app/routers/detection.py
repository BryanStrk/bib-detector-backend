"""Detection API routes: ``POST /detect`` and ``GET /health``."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.schemas.detection import DetectResponse, HealthResponse
from app.services.detector import BibDetector, get_detector

router = APIRouter(tags=["detection"])

# MIME types accepted by the upload endpoint.
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


@router.get("/health", response_model=HealthResponse)
def health(detector: BibDetector = Depends(get_detector)) -> HealthResponse:
    """Liveness probe that also reports the active detection backend."""
    return HealthResponse(status="ok", detector=detector.backend)


@router.post("/detect", response_model=DetectResponse)
async def detect(
    file: UploadFile = File(..., description="Race photo (JPEG or PNG)."),
    detector: BibDetector = Depends(get_detector),
) -> DetectResponse:
    """Detect athlete bib numbers in an uploaded race photo.

    Accepts a JPEG or PNG image and returns each detected bib number with its
    bounding box and confidence, plus the server-side processing time.

    Raises:
        HTTPException: 400 if the upload is missing or not a JPEG/PNG image.
    """
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

    start = time.perf_counter()
    detections = detector.detect(image_bytes)
    processing_time = time.perf_counter() - start

    return DetectResponse(
        filename=file.filename or "upload",
        processing_time=processing_time,
        detections=detections,
    )
