"""Custom exceptions and JSON error handlers.

Handlers are registered in ``app.main`` so that the API returns clean JSON
error payloads (``{"detail": ...}``) instead of leaking stack traces.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DetectorError(Exception):
    """Raised when the detection pipeline fails to process an image."""

    def __init__(self, message: str = "Failed to process image.") -> None:
        self.message = message
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON exception handlers to the FastAPI application."""

    @app.exception_handler(DetectorError)
    async def _handle_detector_error(
        request: Request, exc: DetectorError
    ) -> JSONResponse:
        """Return a 500 with a clean message when detection fails."""
        logger.exception("Detection failed for %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all handler so unexpected errors never leak a stack trace."""
        logger.exception("Unhandled error for %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )
