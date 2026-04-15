"""Database seed script.

Run as::

    python -m app.seeds

Idempotent: re-running will not create duplicates.
"""
from __future__ import annotations

import logging
import os
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.pathology import Pathology
from app.models.user import User, UserRole

log = logging.getLogger("app.seeds")

DEFAULT_PATHOLOGIES = [
    # code, label, base_care_minutes, weight_coefficient
    ("DIAB", "Diabète — suivi / injection insuline", 15, 1.2),
    ("PANS_SIMPLE", "Pansement simple", 10, 1.0),
    ("PANS_COMPLEX", "Pansement complexe", 25, 1.6),
    ("INJ", "Injection intramusculaire / sous-cutanée", 10, 0.9),
    ("TOILETTE", "Toilette / aide à l'hygiène", 35, 1.4),
    ("PALLIATIF", "Soins palliatifs", 45, 2.0),
    ("PERF", "Pose / surveillance perfusion", 20, 1.5),
    ("PRELEV", "Prélèvement sanguin", 10, 0.8),
    ("SURV_TA", "Surveillance tension / constantes", 10, 0.7),
]


def seed() -> None:
    db = SessionLocal()
    try:
        # Admin user — credentials taken from env for safety.
        admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@icy.local")
        admin_password = os.environ.get("SEED_ADMIN_PASSWORD", "ChangeMeNow!2026")
        existing = db.scalar(select(User).where(User.email == admin_email))
        if existing is None:
            db.add(
                User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            log.info("seeded admin user %s", admin_email)

        # Pathologies
        for code, label, minutes, coef in DEFAULT_PATHOLOGIES:
            if not db.scalar(select(Pathology).where(Pathology.code == code)):
                db.add(
                    Pathology(
                        code=code,
                        label=label,
                        base_care_minutes=minutes,
                        weight_coefficient=coef,
                    )
                )
        db.commit()
        log.info("seed complete")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        seed()
    except Exception as exc:  # noqa: BLE001
        log.error("seed failed: %s", exc)
        sys.exit(1)
