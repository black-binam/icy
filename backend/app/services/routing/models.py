"""Data models for the routing / VRP service.

These dataclasses are intentionally framework-agnostic (stdlib
``dataclasses``, no Pydantic) so the routing package remains trivially
unit-testable without pulling FastAPI / SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

StopId = Union[int, str]
CaregiverId = Union[int, str]
TimeWindow = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Coordinate:
    """WGS-84 geographic coordinate (degrees)."""

    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class PatientStop:
    """A patient visit to be scheduled."""

    id: StopId
    coord: Coordinate
    service_minutes: float
    time_window: TimeWindow | None = None


@dataclass(frozen=True, slots=True)
class Caregiver:
    """A healthcare professional executing a daily tour."""

    id: CaregiverId
    home: Coordinate
    capacity_minutes: int
    shift_start_minutes: int = 8 * 60
    shift_end_minutes: int = 18 * 60
    skills: list[str] | None = None


@dataclass(frozen=True, slots=True)
class OptimizeOptions:
    """Multi-criteria weights and solver budget.

    ``alpha_distance`` — scaling factor on total distance minimization.
    ``beta_balance``   — scaling factor on workload equity (span of the
        Workload dimension).
    ``gamma_time``     — penalty scaling on time-window soft violations
        and on dropping a patient.
    ``time_limit_seconds`` — wall-clock OR-Tools budget.
    ``speed_kmh``      — fallback constant speed for Haversine-based travel
        time (ignored when a real matrix is provided).
    """

    alpha_distance: float = 1.0
    beta_balance: float = 1.0
    gamma_time: float = 1.0
    time_limit_seconds: int = 20
    speed_kmh: float = 30.0


@dataclass(frozen=True, slots=True)
class OptimizeInput:
    """Bundle of caregivers, patients, and solver options."""

    caregivers: list[Caregiver]
    patients: list[PatientStop]
    options: OptimizeOptions = field(default_factory=OptimizeOptions)


@dataclass(frozen=True, slots=True)
class RouteStop:
    """A single step inside a caregiver's tour (patient visit)."""

    patient_id: StopId
    arrival_minutes: int
    departure_minutes: int
    distance_from_prev_m: float


@dataclass(frozen=True, slots=True)
class Tour:
    """A caregiver's full planned day."""

    caregiver_id: CaregiverId
    stops: list[RouteStop]
    total_distance_m: float
    total_duration_minutes: int
    total_workload_minutes: int


@dataclass(frozen=True, slots=True)
class OptimizeOutput:
    """Solver response."""

    tours: list[Tour]
    unassigned: list[StopId]
    total_distance_m: float
    workload_stddev: float
    solve_time_ms: int
