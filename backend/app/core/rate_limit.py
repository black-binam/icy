"""Rate-limit plumbing via slowapi."""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()


def _key_func(request: Request) -> str:
    """Prefer a forwarded IP (behind proxy) then the peer."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_key_func, default_limits=[], headers_enabled=False)

LOGIN_LIMIT = settings.LOGIN_RATE_LIMIT
