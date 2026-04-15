"""Unit tests for password hashing, JWT, and field-level encryption."""
from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun import freeze_time

from app.core.security import (
    EncryptedString,
    TokenError,
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_str,
    encrypt_str,
    hash_password,
    verify_password,
)


def test_argon2id_hash_roundtrip() -> None:
    h = hash_password("correcthorsebatterystaple")
    assert h.startswith("$argon2id$")
    assert verify_password("correcthorsebatterystaple", h) is True
    assert verify_password("wrong", h) is False


def test_jwt_access_and_refresh_types() -> None:
    access = create_access_token(42)
    refresh = create_refresh_token(42)

    data = decode_token(access, expected_type="access")
    assert data["sub"] == "42"
    assert data["type"] == "access"
    assert "jti" in data

    with pytest.raises(TokenError):
        decode_token(refresh, expected_type="access")
    with pytest.raises(TokenError):
        decode_token(access, expected_type="refresh")


def test_jwt_expiry() -> None:
    with freeze_time("2026-04-15 12:00:00"):
        token = _create_token(1, "access", timedelta(seconds=1))
    # 10s later — past expiry.
    with freeze_time("2026-04-15 12:00:30"):
        with pytest.raises(TokenError):
            decode_token(token, expected_type="access")


def test_fernet_field_encryption_roundtrip() -> None:
    ct = encrypt_str("Jean Dupont")
    assert ct != "Jean Dupont"
    assert decrypt_str(ct) == "Jean Dupont"


def test_encrypted_string_typedecorator_roundtrip() -> None:
    col = EncryptedString()
    bound = col.process_bind_param("Confidentiel", None)  # type: ignore[arg-type]
    assert bound is not None and bound != "Confidentiel"
    restored = col.process_result_value(bound, None)  # type: ignore[arg-type]
    assert restored == "Confidentiel"


def test_encrypted_string_handles_none() -> None:
    col = EncryptedString()
    assert col.process_bind_param(None, None) is None  # type: ignore[arg-type]
    assert col.process_result_value(None, None) is None  # type: ignore[arg-type]
