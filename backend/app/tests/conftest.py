"""Pytest fixtures: SQLite DB, test client, preloaded users."""
from __future__ import annotations

import base64
import os
import secrets
from collections.abc import Generator, Iterator

# --- Test-time environment ------------------------------------------------
# Must be set BEFORE importing the app modules.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(64))
os.environ.setdefault(
    "FIELD_ENCRYPTION_KEY",
    base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii"),
)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://testserver")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import db as core_db
from app.core.config import get_settings
from app.core.db import Base
from app.core.deps import get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(scope="session", autouse=True)
def _configure_test_engine() -> Iterator[None]:
    """Swap the app engine for a shared in-memory SQLite instance."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    core_db.engine = engine
    core_db.SessionLocal = TestingSessionLocal

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_tables() -> Iterator[None]:
    """Wipe all rows between tests for full isolation."""
    yield
    with core_db.engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture()
def db_session() -> Iterator[Session]:
    session = core_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient wired to the shared in-memory engine."""

    def _override_get_db() -> Iterator[Session]:
        s = core_db.SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db
    # Reset the in-memory rate-limit storage between tests when possible.
    try:
        storage = getattr(app.state.limiter, "_storage", None)
        if storage is not None and hasattr(storage, "reset"):
            storage.reset()
        elif hasattr(app.state.limiter, "reset"):
            app.state.limiter.reset()
    except Exception:  # noqa: BLE001
        pass
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(
    db: Session, *, email: str, password: str, role: UserRole
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def admin_user(db_session: Session) -> User:
    return _make_user(
        db_session,
        email="admin@example.com",
        password="AdminPass-123456",
        role=UserRole.ADMIN,
    )


@pytest.fixture()
def coordinator_user(db_session: Session) -> User:
    return _make_user(
        db_session,
        email="coord@example.com",
        password="CoordPass-123456",
        role=UserRole.COORDINATOR,
    )


@pytest.fixture()
def caregiver_user(db_session: Session) -> User:
    return _make_user(
        db_session,
        email="cg@example.com",
        password="CaregvPass-12345",
        role=UserRole.CAREGIVER,
    )


@pytest.fixture()
def settings_fixture():
    return get_settings()
