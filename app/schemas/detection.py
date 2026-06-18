"""Pydantic schemas for the detection API.

These define the stable wire contract shared with the React frontend. Both the
EasyOCR MVP path and the optional YOLO path produce ``Detection`` objects, so
the model behind the API can be swapped without changing this contract.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """A single detected bib number."""

    bib_number: str = Field(
        ...,
        description="The recognized bib number text (1-5 digits).",
        examples=["1234"],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Detection/OCR confidence in the range [0, 1].",
        examples=[0.92],
    )
    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Bounding box as [x, y, w, h] in pixels (top-left origin).",
        examples=[[120.0, 80.0, 60.0, 30.0]],
    )


class DetectResponse(BaseModel):
    """Response body for ``POST /detect``."""

    photo_id: int = Field(..., description="ID of the persisted photo record.")
    cloudinary_url: str | None = Field(
        default=None,
        description="URL of the uploaded image in Cloudinary.",
    )
    filename: str = Field(..., description="Original uploaded filename.")
    processing_time: float = Field(
        ...,
        ge=0.0,
        description="Server-side processing time in seconds.",
    )
    detections: list[Detection] = Field(
        default_factory=list,
        description="All bib detections above the configured confidence threshold.",
    )


class HealthResponse(BaseModel):
    """Response body for ``GET /health``."""

    status: str = Field(default="ok", description="Service health status.")
    detector: str = Field(
        ...,
        description="Active detection backend: 'yolo+easyocr' or 'easyocr'.",
    )
