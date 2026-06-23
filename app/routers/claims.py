"""Claim routes: request a magic-link email and verify it for a runner token."""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.rate_limit import limiter
from app.core.security import create_runner_token, decode_claim_token
from app.db.session import get_session
from app.schemas.auth import TokenResponse
from app.schemas.claim import ClaimRequest, ClaimResponse, ClaimVerifyRequest
from app.services import claim_service

router = APIRouter(tags=["claims"])


@router.post(
    "/claims",
    response_model=ClaimResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("5/minute")
async def request_claim(
    request: Request,
    data: ClaimRequest,
    session: Session = Depends(get_session),
) -> ClaimResponse:
    """Request a claim magic-link email. Public, rate limited to 5/minute per IP.

    Always returns 202 with a neutral message regardless of whether the details
    match a participant, so the endpoint cannot be used to enumerate registered
    bib numbers or emails.
    """
    claim_service.request_claim(
        session, data.event_id, data.bib_number, data.email
    )
    return ClaimResponse(
        message="If the details match, you'll receive an email shortly."
    )


@router.post("/claims/verify", response_model=TokenResponse)
@limiter.limit("10/minute")
async def verify_claim(
    request: Request,
    data: ClaimVerifyRequest,
) -> TokenResponse:
    """Verify a claim magic-link token and exchange it for a runner token.

    Public, rate limited to 10/minute per IP.

    Raises:
        HTTPException: 401 if the token is missing the ``claim`` type, invalid,
            or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired claim token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_claim_token(data.token)
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    try:
        token = create_runner_token(
            participant_id=int(payload["sub"]),
            event_id=payload["event_id"],
            bib_number=payload["bib_number"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise credentials_exception from exc

    return TokenResponse(access_token=token)
