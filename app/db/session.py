"""Database engine and session lifecycle.

The engine is created lazily from ``DATABASE_URL`` and reused. ``init_db`` is
called on application startup to create tables (Alembic migrations are planned
for later). ``get_session`` is the FastAPI dependency that yields a session.
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_engine = None


def _normalize_db_url(url: str) -> str:
    """Force the psycopg v3 driver for Postgres URLs.

    Neon/Heroku hand out ``postgresql://`` (or legacy ``postgres://``), which
    SQLAlchemy maps to psycopg2 by default. We installed psycopg v3, so we
    rewrite the scheme to ``postgresql+psycopg://``. SQLite and already-explicit
    URLs are left untouched.
    """
    if url.startswith("postgresql+") or url.startswith("sqlite"):
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_engine():
    """Return the lazily-created, process-wide SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = _normalize_db_url(settings.database_url)
        # ``check_same_thread`` only matters for SQLite; it is ignored by other
        # drivers, so we apply it conditionally.
        connect_args = (
            {"check_same_thread": False}
            if db_url.startswith("sqlite")
            else {}
        )
        logger.info("Creating database engine")
        _engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _engine


def init_db() -> None:
    """Create all tables. Importing models registers them on the metadata."""
    from app.db import models  # noqa: F401 - registers tables on metadata

    logger.info("Creating database tables (if missing)")
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    with Session(get_engine()) as session:
        yield session
