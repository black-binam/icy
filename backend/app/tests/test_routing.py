"""Tests for the routing / CVRPTW service.

The tests are organised to give meaningful coverage of:

* geometry (Haversine distance),
* workload computation from pathologies,
* end-to-end solver behaviour under varied constraints.

Tests requiring OR-Tools are guarded via ``pytest.importorskip`` so the
suite keeps working in environments where the solver is not installed.
All solver calls use ``time_limit_seconds=2`` to keep the suite fast.
"""

from __future__ import annotations

import math

import pytest

from app.services.routing.compute import (
    DEFAULT_MIN_MINUTES,
    compute_patient_minutes,
)
from app.services.routing.distance import (
    HaversineProvider,
    haversine,
)
from app.services.routing.models import (
    Coordinate,
    OptimizeInput,
    OptimizeOptions,
)
from app.tests.fixtures_routing import (
    ARC_DE_TRIOMPHE,
    BASTILLE,
    CAREGIVER_HOME_CENTER,
    CAREGIVER_HOME_WEST,
    EIFFEL_TOWER,
    LOUVRE,
    MONTPARNASSE,
    PERE_LACHAISE,
    make_caregiver,
    make_patient,
)

# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #


def test_haversine_paris_marseille_approx() -> None:
    """Paris ↔ Marseille great-circle is ~661 km; tolerate ±10 %."""
    paris = Coordinate(lat=48.8566, lon=2.3522)
    marseille = Coordinate(lat=43.2965, lon=5.3698)
    meters = haversine(paris, marseille)
    km = meters / 1000.0
    assert 595.0 <= km <= 727.0, f"Expected ~661 km ±10 %, got {km:.1f} km"


def test_haversine_zero_distance() -> None:
    """Self-distance is exactly 0."""
    c = Coordinate(lat=48.0, lon=2.0)
    assert haversine(c, c) == 0.0


# --------------------------------------------------------------------------- #
# compute_patient_minutes
# --------------------------------------------------------------------------- #


def test_compute_patient_minutes_with_overrides() -> None:
    items = [
        # base 20 min × default coef 1.5 = 30
        {"base_minutes": 20.0, "coefficient": 1.5},
        # override minutes 15, override coef 2.0 → 30
        {
            "base_minutes": 10.0,
            "coefficient": 1.0,
            "override_minutes": 15.0,
            "override_coefficient": 2.0,
        },
        # only minutes overridden, default coef used
        {
            "base_minutes": 5.0,
            "coefficient": 2.0,
            "override_minutes": 10.0,
        },
    ]
    total = compute_patient_minutes(items)
    # 30 + 30 + 20 = 80
    assert math.isclose(total, 80.0, abs_tol=1e-9)


def test_compute_patient_minutes_empty_returns_floor() -> None:
    assert compute_patient_minutes([]) == DEFAULT_MIN_MINUTES


def test_compute_patient_minutes_floor_is_respected() -> None:
    items = [{"base_minutes": 1.0, "coefficient": 0.5}]  # → 0.5 minutes
    assert compute_patient_minutes(items) == DEFAULT_MIN_MINUTES


# --------------------------------------------------------------------------- #
# Distance provider
# --------------------------------------------------------------------------- #


def test_provider_haversine_matrix_symmetry() -> None:
    coords = [EIFFEL_TOWER, LOUVRE, BASTILLE, MONTPARNASSE]
    provider = HaversineProvider(speed_kmh=30.0)
    dist, dur = provider.matrix(coords)

    n = len(coords)
    assert len(dist) == n and all(len(row) == n for row in dist)
    assert len(dur) == n and all(len(row) == n for row in dur)

    for i in range(n):
        assert dist[i][i] == 0.0
        assert dur[i][i] == 0.0
        for j in range(n):
            assert math.isclose(dist[i][j], dist[j][i], rel_tol=1e-9)
            assert math.isclose(dur[i][j], dur[j][i], rel_tol=1e-9)


# --------------------------------------------------------------------------- #
# Solver
# --------------------------------------------------------------------------- #

# Skip the entire solver section if OR-Tools is not present.
pytest.importorskip("ortools")

from app.services.routing.solver import RoutingError, optimize  # noqa: E402


def _short_opts(**kwargs: float | int) -> OptimizeOptions:
    base = {
        "alpha_distance": 1.0,
        "beta_balance": 1.0,
        "gamma_time": 1.0,
        "time_limit_seconds": 2,
        "speed_kmh": 30.0,
    }
    base.update(kwargs)
    return OptimizeOptions(**base)  # type: ignore[arg-type]


def test_optimize_trivial_empty() -> None:
    """Zero patients → each caregiver gets an empty Tour instantly."""
    inp = OptimizeInput(
        caregivers=[make_caregiver(1), make_caregiver(2, home=CAREGIVER_HOME_WEST)],
        patients=[],
        options=_short_opts(),
    )
    out = optimize(inp)
    assert len(out.tours) == 2
    for tour in out.tours:
        assert tour.stops == []
        assert tour.total_distance_m == 0.0
        assert tour.total_duration_minutes == 0
        assert tour.total_workload_minutes == 0
    assert out.unassigned == []
    assert out.total_distance_m == 0.0
    assert out.workload_stddev == 0.0


def test_optimize_rejects_no_caregivers() -> None:
    with pytest.raises(RoutingError):
        optimize(
            OptimizeInput(
                caregivers=[],
                patients=[make_patient(1, EIFFEL_TOWER)],
                options=_short_opts(),
            )
        )


def test_optimize_single_caregiver_small_cluster() -> None:
    """One caregiver, 3 nearby patients: all must be served."""
    patients = [
        make_patient(101, EIFFEL_TOWER, service_minutes=20.0),
        make_patient(102, ARC_DE_TRIOMPHE, service_minutes=25.0),
        make_patient(103, LOUVRE, service_minutes=15.0),
    ]
    inp = OptimizeInput(
        caregivers=[make_caregiver(1, capacity_minutes=480)],
        patients=patients,
        options=_short_opts(),
    )
    out = optimize(inp)

    assert out.unassigned == []
    assert len(out.tours) == 1
    tour = out.tours[0]
    assert tour.caregiver_id == 1

    served_ids = {stop.patient_id for stop in tour.stops}
    assert served_ids == {101, 102, 103}

    # Workload must equal sum of service minutes.
    assert tour.total_workload_minutes == 20 + 25 + 15

    # Duration must be at least the workload (add some travel).
    assert tour.total_duration_minutes >= tour.total_workload_minutes


def test_optimize_balance_two_caregivers() -> None:
    """6 patients, 2 caregivers — charges must stay reasonably balanced."""
    patients = [
        make_patient(201, EIFFEL_TOWER, service_minutes=30.0),
        make_patient(202, ARC_DE_TRIOMPHE, service_minutes=30.0),
        make_patient(203, LOUVRE, service_minutes=30.0),
        make_patient(204, BASTILLE, service_minutes=30.0),
        make_patient(205, MONTPARNASSE, service_minutes=30.0),
        make_patient(206, PERE_LACHAISE, service_minutes=30.0),
    ]
    inp = OptimizeInput(
        caregivers=[
            make_caregiver(1, home=CAREGIVER_HOME_CENTER, capacity_minutes=480),
            make_caregiver(2, home=CAREGIVER_HOME_WEST, capacity_minutes=480),
        ],
        patients=patients,
        # Favor equity strongly to make the test deterministic.
        options=_short_opts(beta_balance=10.0),
    )
    out = optimize(inp)

    assert out.unassigned == []
    assert len(out.tours) == 2

    served_ids: set[int | str] = set()
    for tour in out.tours:
        served_ids.update(s.patient_id for s in tour.stops)
    assert served_ids == {201, 202, 203, 204, 205, 206}

    # Total workload = 6 × 30 = 180 min, perfectly balanced = 90 each.
    # Accept up to 60 min span (two stops off balance).
    workloads = sorted(t.total_workload_minutes for t in out.tours)
    assert workloads[1] - workloads[0] <= 60

    # Stddev must be small relative to the mean (half of mean max).
    assert out.workload_stddev <= 45.0


def test_optimize_respects_capacity() -> None:
    """Low capacity → excess patients become ``unassigned``."""
    # 4 patients × 60 min = 240 min demand, but caregiver capacity = 90 min
    # → at most one patient fits.
    patients = [
        make_patient(301, EIFFEL_TOWER, service_minutes=60.0),
        make_patient(302, ARC_DE_TRIOMPHE, service_minutes=60.0),
        make_patient(303, LOUVRE, service_minutes=60.0),
        make_patient(304, BASTILLE, service_minutes=60.0),
    ]
    inp = OptimizeInput(
        caregivers=[make_caregiver(1, capacity_minutes=90)],
        patients=patients,
        options=_short_opts(),
    )
    out = optimize(inp)

    assert len(out.tours) == 1
    assert len(out.tours[0].stops) <= 1
    # At least three patients must be unassigned.
    assert len(out.unassigned) >= 3
    # Total consistency: served + unassigned == all.
    served = {s.patient_id for s in out.tours[0].stops}
    assert served.union(set(out.unassigned)) == {301, 302, 303, 304}


@pytest.mark.slow
def test_optimize_time_windows_soft() -> None:
    """A patient with a tight time window should be scheduled near it."""
    patients = [
        make_patient(401, EIFFEL_TOWER, service_minutes=20.0),
        # Window: 10h00 – 10h30
        make_patient(
            402,
            ARC_DE_TRIOMPHE,
            service_minutes=20.0,
            time_window=(10 * 60, 10 * 60 + 30),
        ),
        make_patient(403, LOUVRE, service_minutes=20.0),
    ]
    inp = OptimizeInput(
        caregivers=[make_caregiver(1, capacity_minutes=240)],
        patients=patients,
        options=_short_opts(gamma_time=5.0),
    )
    out = optimize(inp)

    assert out.unassigned == []
    target = next(s for t in out.tours for s in t.stops if s.patient_id == 402)
    # Arrival should be in [09:30, 10:45] (60 min either side, soft).
    assert 9 * 60 + 30 <= target.arrival_minutes <= 10 * 60 + 45
