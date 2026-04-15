"""Dashboard KPI endpoint."""
from __future__ import annotations

import math
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.caregiver import Caregiver
from app.models.patient import Patient
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class CaregiverWorkload(BaseModel):
    caregiver_id: int
    caregiver_name: str
    workload_minutes: int
    capacity_minutes: int


class DashboardKpis(BaseModel):
    active_caregivers: int
    active_patients: int
    today_routes: int
    today_stops: int
    workload_stddev_minutes: float
    per_caregiver_workload: list[CaregiverWorkload]


@router.get("/kpis", response_model=DashboardKpis)
def get_kpis(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardKpis:
    today = date.today()

    active_caregivers = db.scalar(select(func.count(Caregiver.id))) or 0
    active_patients = db.scalar(
        select(func.count(Patient.id)).where(Patient.is_active.is_(True))
    ) or 0

    today_routes = db.scalar(
        select(func.count(Route.id)).where(Route.date == today)
    ) or 0

    today_stops = db.scalar(
        select(func.count(RouteStop.id))
        .join(Route, Route.id == RouteStop.route_id)
        .where(Route.date == today)
    ) or 0

    # Per-caregiver workload for today's published/in-progress routes
    rows = db.execute(
        select(Caregiver, Route)
        .join(Route, Route.caregiver_id == Caregiver.id)
        .where(Route.date == today)
        .where(Route.status.in_([RouteStatus.PUBLISHED, RouteStatus.IN_PROGRESS, RouteStatus.DONE]))
    ).all()

    per_caregiver: list[CaregiverWorkload] = [
        CaregiverWorkload(
            caregiver_id=cg.id,
            caregiver_name=f"{cg.first_name} {cg.last_name}",
            workload_minutes=route.total_workload_minutes,
            capacity_minutes=cg.daily_capacity_minutes,
        )
        for cg, route in rows
    ]

    if per_caregiver:
        values = [w.workload_minutes for w in per_caregiver]
        mean = sum(values) / len(values)
        stddev = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
    else:
        stddev = 0.0

    return DashboardKpis(
        active_caregivers=active_caregivers,
        active_patients=active_patients,
        today_routes=today_routes,
        today_stops=today_stops,
        workload_stddev_minutes=stddev,
        per_caregiver_workload=per_caregiver,
    )
