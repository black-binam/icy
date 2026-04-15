"""Patient CRUD + RBAC tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _patient_payload() -> dict:
    return {
        "first_name": "Alice",
        "last_name": "Martin",
        "address": "1 rue du Test, 75001 Paris",
        "lat": 48.8566,
        "lon": 2.3522,
        "phone": "+33600000000",
        "notes": "Diabétique",
        "is_active": True,
    }


def test_coordinator_can_create_patient(
    client: TestClient, coordinator_user: User
) -> None:
    token = _login(client, coordinator_user.email, "CoordPass-123456")
    r = client.post(
        "/api/v1/patients",
        json=_patient_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["first_name"] == "Alice"
    assert body["last_name"] == "Martin"
    assert isinstance(body["id"], int)


def test_caregiver_cannot_create_patient(
    client: TestClient, caregiver_user: User
) -> None:
    token = _login(client, caregiver_user.email, "CaregvPass-12345")
    r = client.post(
        "/api/v1/patients",
        json=_patient_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_caregiver_sees_only_own_route_patients(
    client: TestClient, caregiver_user: User, coordinator_user: User
) -> None:
    # Coordinator creates a patient first.
    coord_token = _login(client, coordinator_user.email, "CoordPass-123456")
    client.post(
        "/api/v1/patients",
        json=_patient_payload(),
        headers={"Authorization": f"Bearer {coord_token}"},
    )

    # Caregiver without any route sees an empty list.
    cg_token = _login(client, caregiver_user.email, "CaregvPass-12345")
    r = client.get(
        "/api/v1/patients", headers={"Authorization": f"Bearer {cg_token}"}
    )
    assert r.status_code == 200
    assert r.json() == []


def test_update_and_delete_patient(
    client: TestClient, coordinator_user: User
) -> None:
    token = _login(client, coordinator_user.email, "CoordPass-123456")
    created = client.post(
        "/api/v1/patients",
        json=_patient_payload(),
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    pid = created["id"]

    upd = client.patch(
        f"/api/v1/patients/{pid}",
        json={"first_name": "Alicia"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upd.status_code == 200
    assert upd.json()["first_name"] == "Alicia"

    dele = client.delete(
        f"/api/v1/patients/{pid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert dele.status_code == 204


def test_patient_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/patients").status_code == 401
