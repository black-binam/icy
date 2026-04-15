"""FastAPI dependencies: DB session, current user, RBAC."""
from __future__ import annotations

from collections.abc import Callable, Iterator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db as _get_db
from app.core.security import TokenError, decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


def get_db() -> Iterator[Session]:
    yield from _get_db()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the active user from a JWT access token."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise credentials_exc from exc

    try:
        user_id = int(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise credentials_exc from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise credentials_exc
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    """Factory dependency that allows only users with one of the given roles."""
    allowed = {UserRole(r) for r in roles}

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges",
            )
        return user

    return _checker
