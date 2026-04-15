"""Auth tests: login happy/sad paths, rate limit, enumeration resistance."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.models.user import User


def test_login_success(client: TestClient, admin_user: User) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPass-123456"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, admin_user: User) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Invalid credentials"}


def test_login_unknown_email_same_shape(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@test.local", "password": "whatever-123456"},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Invalid credentials"}


def test_login_timing_is_floor(client: TestClient, admin_user: User) -> None:
    """Unknown and known-with-wrong-password should both meet a minimum
    latency (no fast 'user not found' shortcut)."""
    t0 = time.perf_counter()
    client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.local", "password": "pw-12345678"},
    )
    unknown = time.perf_counter() - t0

    t0 = time.perf_counter()
    client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "bad-pw-12345678"},
    )
    known = time.perf_counter() - t0

    # Both paths must take at least ~0.2s (the configured floor is 0.25s).
    assert unknown > 0.2
    assert known > 0.2


def test_rate_limit_login(client: TestClient) -> None:
    payload = {"email": "ghost@test.local", "password": "pw-12345678"}
    statuses = []
    for _ in range(7):
        r = client.post("/api/v1/auth/login", json=payload)
        statuses.append(r.status_code)
    assert 429 in statuses


def test_refresh_and_me(client: TestClient, admin_user: User) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPass-123456"},
    ).json()

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["access_token"] != login["access_token"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == admin_user.email


def test_refresh_rejects_access_token(client: TestClient, admin_user: User) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPass-123456"},
    ).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": login["access_token"]})
    assert r.status_code == 401


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
