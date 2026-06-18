"""Shared slowapi rate limiter, keyed by client IP.

The limiter is created here so routers can import and apply ``@limiter.limit``
decorators, while ``app.main`` wires it into the application state and
registers the 429 handler.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP limiter. Individual limits are applied with @limiter.limit(...).
limiter = Limiter(key_func=get_remote_address)
