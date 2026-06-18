"""Cloudinary image storage service.

Credentials are read from ``CLOUDINARY_URL`` (format:
``cloudinary://<api_key>:<api_secret>@<cloud_name>``). Configuration happens
lazily on first upload so the app can import without credentials present.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.exceptions import StorageError

logger = logging.getLogger(__name__)

# Cloudinary folder under which uploads are organized.
_UPLOAD_FOLDER = "bib-detector"

_configured = False


def _ensure_configured() -> None:
    """Configure the Cloudinary SDK from ``CLOUDINARY_URL`` (once)."""
    global _configured
    if _configured:
        return

    settings = get_settings()
    if not settings.cloudinary_url:
        raise StorageError("Cloudinary is not configured (CLOUDINARY_URL unset).")

    parsed = urlparse(settings.cloudinary_url)
    if not (parsed.hostname and parsed.username and parsed.password):
        raise StorageError("CLOUDINARY_URL is malformed.")

    import cloudinary  # Imported here so the app imports without the dep loaded.

    cloudinary.config(
        cloud_name=parsed.hostname,
        api_key=parsed.username,
        api_secret=parsed.password,
        secure=True,
    )
    _configured = True


def upload_image(data: bytes, filename: str | None = None) -> tuple[str, str]:
    """Upload image bytes to Cloudinary.

    Args:
        data: Raw image bytes.
        filename: Original filename, used only for log context.

    Returns:
        A ``(secure_url, public_id)`` tuple.

    Raises:
        StorageError: If Cloudinary is unconfigured or the upload fails.
    """
    _ensure_configured()

    import cloudinary.uploader

    try:
        result = cloudinary.uploader.upload(
            data,
            folder=_UPLOAD_FOLDER,
            resource_type="image",
        )
    except Exception as exc:  # noqa: BLE001 - normalize to StorageError
        logger.exception("Cloudinary upload failed for %s", filename or "<bytes>")
        raise StorageError("Failed to upload image to storage.") from exc

    return result["secure_url"], result["public_id"]


def delete_image(public_id: str) -> bool:
    """Delete an image from Cloudinary by its public ID.

    Args:
        public_id: The Cloudinary public ID returned at upload time.

    Returns:
        True if the asset was deleted, False if Cloudinary reports it was not
        found (already gone) — callers can treat the latter as a no-op.

    Raises:
        StorageError: If Cloudinary is unconfigured or the call itself fails.
    """
    _ensure_configured()

    import cloudinary.uploader

    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
    except Exception as exc:  # noqa: BLE001 - normalize to StorageError
        logger.exception("Cloudinary delete failed for %s", public_id)
        raise StorageError("Failed to delete image from storage.") from exc

    return result.get("result") == "ok"
