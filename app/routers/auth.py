"""Authentication routes: ``POST /auth/login``."""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, verify_password
from app.schemas.auth import TokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Authenticate the admin and return a JWT access token.

    Uses the standard OAuth2 password form so Swagger's Authorize button works.
    Verifies the username and the password (against ``ADMIN_PASSWORD_HASH``);
    rate limited to 5 requests/minute per IP.

    Raises:
        HTTPException: 401 on invalid credentials (or if auth is unconfigured).
    """
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not (settings.admin_username and settings.admin_password_hash):
        logger.warning("Login attempted but admin credentials are not configured.")
        raise invalid_credentials

    # ``compare_digest`` for the username avoids leaking it via timing; the
    # password check is constant-time inside bcrypt.
    username_ok = secrets.compare_digest(form_data.username, settings.admin_username)
    password_ok = verify_password(form_data.password, settings.admin_password_hash)
    if not (username_ok and password_ok):
        raise invalid_credentials

    token = create_access_token(subject=settings.admin_username)
    return TokenResponse(access_token=token)
