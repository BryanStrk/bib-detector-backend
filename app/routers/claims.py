"""Claim routes: ``POST /claims`` (request a magic-link email)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session

from app.core.rate_limit import limiter
from app.db.session import get_session
from app.schemas.claim import ClaimRequest, ClaimResponse
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
