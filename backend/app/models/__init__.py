"""SQLAlchemy ORM models.

Imports all models so that ``Base.metadata`` is populated when this
package is imported (notably by Alembic's ``env.py``).
"""
from __future__ import annotations

from app.models.audit_log import AuditLog
from app.models.caregiver import Caregiver
from app.models.pathology import Pathology
from app.models.patient import Patient
from app.models.patient_pathology import PatientPathology
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.models.user import User, UserRole

__all__ = [
    "AuditLog",
    "Caregiver",
    "Pathology",
    "Patient",
    "PatientPathology",
    "Route",
    "RouteStatus",
    "RouteStop",
    "User",
    "UserRole",
]
