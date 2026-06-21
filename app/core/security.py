"""Authentication primitives: password hashing and JWT (Spring Security-style).

Mirrors a Spring Security + JWT setup: a stateless bearer-token scheme backed
by a single admin identity whose credentials live in the environment (no user
table). Passwords are verified against a bcrypt hash; access is granted via a
short-lived signed JWT.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import get_settings

# Single, shared password hasher (bcrypt). The hash_password script imports
# this so generated hashes always match what the app verifies against.
_password_hash = PasswordHash((BcryptHasher(),))

# Bearer scheme; ``tokenUrl`` makes Swagger's Authorize button hit the login
# endpoint. Relative path (no leading slash) so it works behind a prefix.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for ``plain_password`` (used by the CLI script)."""
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True if ``plain_password`` matches the given bcrypt hash."""
    return _password_hash.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
    """Build a signed JWT for ``subject`` with an ``exp`` claim.

    Raises:
        RuntimeError: If ``JWT_SECRET_KEY`` is not configured.
    """
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT, returning its claims.

    Raises:
        jwt.PyJWTError: If the token is invalid, malformed, or expired.
    """
    settings = get_settings()
    return jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )


def create_claim_token(
    participant_id: int, event_id: int, bib_number: str
) -> str:
    """Build a short-lived, single-use JWT for claiming a participant's photos.

    The token carries a ``type: "claim"`` marker so it cannot be used as an
    admin access token (and vice versa), plus the identifying claims needed to
    resolve the participant on verification.

    Raises:
        RuntimeError: If ``JWT_SECRET_KEY`` is not configured.
    """
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.claim_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(participant_id),
        "event_id": event_id,
        "bib_number": bib_number,
        "type": "claim",
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_claim_token(token: str) -> dict[str, Any]:
    """Decode and verify a claim token, returning its claims.

    Enforces the ``type == "claim"`` marker so an admin access token cannot be
    replayed against the claim-verification flow.

    Raises:
        jwt.PyJWTError: If the token is invalid, malformed, expired, or is not a
            claim token.
    """
    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != "claim":
        raise jwt.InvalidTokenError("Not a claim token.")
    return payload


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> str:
    """Resolve the admin identity from a bearer token.

    Returns:
        The admin username carried in the token's ``sub`` claim.

    Raises:
        HTTPException: 401 if the token is missing, invalid, expired, or does
            not identify the configured admin.
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    subject = payload.get("sub")
    if not subject or subject != settings.admin_username:
        raise credentials_exception

    return subject
