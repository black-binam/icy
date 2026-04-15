"""FastAPI application factory + middlewares."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.api.v1 import api_router
from app.core import db as core_db
from app.core.audit import anonymize_ip, hash_user_agent, write_audit
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.logging import configure_logging
from app.core.rate_limit import limiter

configure_logging()
log = logging.getLogger("app")

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to every response."""

    def __init__(self, app, is_production: bool) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        if self.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """Log mutating HTTP requests into the AuditLog table.

    Never records request/response bodies — only method, path, pseudonymized
    IP and hashed user-agent.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        response = await call_next(request)

        if request.method not in _MUTATING_METHODS:
            return response
        # Skip audit for the audit-log endpoints themselves (none exposed yet).
        if not request.url.path.startswith("/api/"):
            return response

        actor_id: int | None = None
        try:
            # Reuse the same decoding logic without raising on anonymous.
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                from app.core.security import TokenError, decode_token

                try:
                    payload = decode_token(auth.split(" ", 1)[1], expected_type="access")
                    actor_id = int(payload["sub"])
                except (TokenError, ValueError, KeyError):
                    actor_id = None
        except Exception:  # noqa: BLE001 — audit must never break the response
            actor_id = None

        try:
            db = core_db.SessionLocal()
            try:
                write_audit(
                    db,
                    actor_id=actor_id,
                    action=f"{request.method} {request.url.path}",
                    ip=_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                )
                db.commit()
            finally:
                db.close()
        except Exception:  # noqa: BLE001
            log.exception("audit write failed")

        return response


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )
    app.add_middleware(SecurityHeadersMiddleware, is_production=settings.is_production)
    app.add_middleware(AuditMiddleware)

    app.include_router(api_router)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "env": settings.ENVIRONMENT}

    # Silence unused-import complaints for dependency-injection wiring.
    _ = get_current_user
    _ = anonymize_ip
    _ = hash_user_agent

    return app


app = create_app()
