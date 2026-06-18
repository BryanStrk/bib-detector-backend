"""Pydantic schemas for authentication."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """OAuth2 bearer-token response returned by ``POST /auth/login``."""

    access_token: str = Field(..., description="Signed JWT access token.")
    token_type: str = Field(default="bearer", description="Token type.")
