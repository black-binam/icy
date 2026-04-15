"""Route schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.route import RouteStatus


class RouteStopBase(BaseModel):
    patient_id: int
    sequence: int = Field(ge=0)
    planned_arrival: datetime | None = None
    planned_departure: datetime | None = None
    estimated_care_minutes: int = Field(default=0, ge=0, le=600)


class RouteStopOut(RouteStopBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RouteBase(BaseModel):
    caregiver_id: int
    date: date
    status: RouteStatus = RouteStatus.DRAFT


class RouteCreate(RouteBase):
    stops: list[RouteStopBase] = Field(default_factory=list)


class RouteUpdate(BaseModel):
    status: RouteStatus | None = None
    stops: list[RouteStopBase] | None = None


class RouteOut(RouteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_distance_m: float
    total_duration_s: int
    total_workload_minutes: int
    stops: list[RouteStopOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# --- Optimization contract --------------------------------------------------


class RouteOptimizeRequest(BaseModel):
    """Input for POST /routes/optimize."""

    date: date
    caregiver_ids: list[int] = Field(default_factory=list)
    patient_ids: list[int] = Field(default_factory=list)
    balance_workload: bool = True
    max_seconds: int = Field(default=30, ge=1, le=600)


class RouteOptimizeResponse(BaseModel):
    """Solver output."""

    solved: bool
    routes: list[RouteOut] = Field(default_factory=list)
    unassigned_patient_ids: list[int] = Field(default_factory=list)
    objective_value: float | None = None
    solver_seconds: float | None = None
