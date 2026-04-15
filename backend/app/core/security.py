"""Password hashing, JWT tokens, field-level encryption."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exceptions
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from sqlalchemy import String, TypeDecorator
from sqlalchemy.engine.interfaces import Dialect

from app.core.config import get_settings

settings = get_settings()

TokenType = Literal["access", "refresh"]

_password_hasher = PasswordHasher()
_fernet = Fernet(settings.FIELD_ENCRYPTION_KEY.encode("ascii"))


# --- Passwords -----------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a password with Argon2id. Never log the result."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time verification; returns False on any failure."""
    try:
        return _password_hasher.verify(hashed, password)
    except (argon2_exceptions.VerifyMismatchError, argon2_exceptions.InvalidHash):
        return False
    except argon2_exceptions.VerificationError:
        return False


def needs_rehash(hashed: str) -> bool:
    """Whether the stored hash should be upgraded."""
    return _password_hasher.check_needs_rehash(hashed)


# --- JWT -----------------------------------------------------------------


class TokenError(Exception):
    """Raised when a token is invalid/expired/wrong type."""


def _create_token(subject: str | int, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str | int) -> str:
    return _create_token(
        subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode + validate a JWT, ensuring the claim `type` matches."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise TokenError("invalid token") from exc
    if payload.get("type") != expected_type:
        raise TokenError("wrong token type")
    if "sub" not in payload:
        raise TokenError("missing sub")
    return payload


# --- Field encryption ----------------------------------------------------


def encrypt_str(value: str) -> str:
    """Encrypt a UTF-8 string using Fernet, return urlsafe-base64 ciphertext."""
    return _fernet.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_str(token: str) -> str:
    """Decrypt a Fernet urlsafe-base64 ciphertext back to a UTF-8 string."""
    try:
        return _fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("invalid ciphertext") from exc


class EncryptedString(TypeDecorator[str]):
    """SQLAlchemy TypeDecorator that transparently encrypts/decrypts strings.

    Note: disables textual searches on the column (ciphertext is non-deterministic).
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int | None = None, **kwargs: Any) -> None:
        super().__init__(length=length or 1024, **kwargs)

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("EncryptedString expects str")
        return encrypt_str(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return decrypt_str(value)
