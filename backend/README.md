# ICY Backend

FastAPI + SQLAlchemy 2 backend for the ICY healthcare route optimizer.

## Prerequisites

- Python 3.11
- PostgreSQL 16 (PostGIS optional; lat/lon floats suffice for MVP)
- Redis (for Celery — not required for the API alone)

## Installation

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Copy `/.env.example` to `/.env` at the repo root and generate real secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"   # SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # FIELD_ENCRYPTION_KEY
```

`FIELD_ENCRYPTION_KEY` must be a urlsafe-base64 value decoding to exactly 32 bytes.

## Database

```bash
# Apply migrations
alembic upgrade head

# Seed an admin user + default pathologies (idempotent)
SEED_ADMIN_EMAIL=admin@icy.local SEED_ADMIN_PASSWORD=ChangeMe-strong python -m app.seeds
```

## Run

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- OpenAPI (dev only): http://localhost:8000/docs
- Health: http://localhost:8000/health

## Tests

```bash
pytest
# PostGIS-specific tests are skipped by default:
pytest -m "not postgis"
```

## Security highlights

- Argon2id password hashing (`argon2-cffi`)
- JWT HS256, access 15 min + refresh 7 d with explicit `type` claim validation
- Fernet field-level encryption on patient PII (`first_name`, `last_name`, `phone`, `notes`)
- IP anonymization (/24 IPv4, /48 IPv6) + SHA-256(user-agent) in audit log
- Login rate-limited to 5/min/IP (slowapi), constant-time floor against enumeration
- Baseline security headers + HSTS in production
- Log filter redacting password/token/authorization/email

## Layout

```
app/
  core/        # config, db, security, deps, audit, logging, rate_limit
  models/      # SQLAlchemy 2 ORM models
  schemas/     # Pydantic v2 DTOs
  crud/        # generic CRUDBase helper
  api/v1/      # FastAPI routers
  services/
    routing/   # VRP solver (handled by another agent)
  tests/       # pytest + httpx tests
alembic/
  versions/    # SQL migrations
```
