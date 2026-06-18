"""FastAPI application entrypoint.

Run with::

    uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import limiter
from app.db.session import init_db
from app.routers import detection, photos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (Alembic migrations come later)."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Bib Detector API",
        description="Detect athlete bib numbers in race photos.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Rate limiting (slowapi): expose the limiter and inject 429 headers.
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(detection.router)
    app.include_router(photos.router)

    return app


app = create_app()
