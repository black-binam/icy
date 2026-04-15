"""Authentication endpoints: login, refresh, logout, me."""
from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.core.rate_limit import LOGIN_LIMIT, limiter
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    needs_rehash,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginIn, RefreshIn, TokenOut
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

# Pre-computed dummy hash used to equalize timing when the email is unknown.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))

# Minimum total time spent in the login handler to reduce timing-based
# account enumeration. Tuned to a value > Argon2id cost on typical hardware.
_MIN_LOGIN_SECONDS = 0.25


def _equalize_timing(start: float) -> None:
    elapsed = time.perf_counter() - start
    remaining = _MIN_LOGIN_SECONDS - elapsed
    if remaining > 0:
        time.sleep(remaining)


@router.post("/login", response_model=TokenOut)
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,
    payload: LoginIn,
    db: Session = Depends(get_db),
) -> TokenOut:
    """Exchange credentials for an access/refresh token pair.

    The response is identical whether the email exists or the password is
    wrong: same status, same body shape, same timing floor.
    """
    start = time.perf_counter()

    user: User | None = db.scalar(select(User).where(User.email == payload.email))

    # Always run a hash verification to keep timing constant.
    if user is None or not user.is_active or user.deleted_at is not None:
        verify_password(payload.password, _DUMMY_HASH)
        _equalize_timing(start)
        write_audit(
            db,
            actor_id=None,
            action="auth.login_failed",
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    ok = verify_password(payload.password, user.hashed_password)
    if not ok:
        _equalize_timing(start)
        write_audit(
            db,
            actor_id=user.id,
            action="auth.login_failed",
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Opportunistic rehash upgrade.
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(payload.password)
        db.add(user)

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    write_audit(
        db,
        actor_id=user.id,
        action="auth.login",
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    _equalize_timing(start)
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    """Issue a new access token from a valid refresh token."""
    try:
        data = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    user_id = int(data["sub"])
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return TokenOut(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Stateless logout stub — client discards the token.

    A token-revocation list (Redis-backed) is planned; for MVP we only
    record the event in the audit log.
    """
    write_audit(
        db,
        actor_id=user.id,
        action="auth.logout",
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user."""
    return user


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
