"""Routing / VRP optimization service.

This package is pure (no FastAPI / SQLAlchemy dependency). It is safely
importable even if ``ortools`` or ``httpx`` are not available: the heavy
imports are performed lazily inside the relevant functions.

Public surface:

* :class:`OptimizeInput` / :class:`OptimizeOutput` — request / response DTOs.
* :class:`RoutingError` — raised on solver or configuration failures.
* :func:`optimize` — synchronous VRP solver entry point.
"""

from __future__ import annotations

from app.services.routing.models import (
    Caregiver,
    Coordinate,
    OptimizeInput,
    OptimizeOptions,
    OptimizeOutput,
    PatientStop,
    RouteStop,
    Tour,
)
from app.services.routing.solver import RoutingError, optimize

__all__ = [
    "Caregiver",
    "Coordinate",
    "OptimizeInput",
    "OptimizeOptions",
    "OptimizeOutput",
    "PatientStop",
    "RouteStop",
    "RoutingError",
    "Tour",
    "optimize",
]
