"""Pydantic schemas for the photo-claim flow."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class ClaimRequest(BaseModel):
    """Request body for ``POST /claims``."""

    event_id: int = Field(..., description="ID of the event to claim photos for.")
    bib_number: str = Field(..., description="The participant's bib number.")
    email: EmailStr = Field(..., description="The participant's registered email.")


class ClaimResponse(BaseModel):
    """Neutral response for ``POST /claims`` (never reveals whether it matched)."""

    message: str = Field(..., description="Human-readable status message.")


class ClaimVerifyRequest(BaseModel):
    """Request body for ``POST /claims/verify`` (exchanges a magic-link token)."""

    token: str = Field(..., description="The claim token from the magic link.")
