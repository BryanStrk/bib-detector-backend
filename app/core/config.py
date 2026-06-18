"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from environment variables, falling back to a local
    ``.env`` file (never commit a real ``.env`` — see ``.env.example``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Optional path to a YOLO ``.pt`` model. When set, the detector uses the
    # YOLO -> crop -> OCR pipeline. When unset (default), it runs the
    # whole-image EasyOCR MVP pipeline.
    model_path: str | None = None

    # Comma-separated list of allowed CORS origins. ``NoDecode`` prevents
    # pydantic-settings from trying to JSON-decode the value, so the validator
    # below can split a plain comma-separated string.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "https://bib-detector.example.com",
    ]

    # Detections scoring below this confidence threshold are discarded.
    min_confidence: float = 0.3

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Allow ``CORS_ORIGINS`` to be supplied as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (used as a FastAPI dependency)."""
    return Settings()