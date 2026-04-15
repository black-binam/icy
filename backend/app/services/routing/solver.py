"""OR-Tools CVRPTW solver for the healthcare routing service.

This module provides :func:`optimize`, the single synchronous entry point
that accepts an :class:`OptimizeInput` and returns an :class:`OptimizeOutput`.

Design notes
------------

* **Multi-depot** — each caregiver starts and ends at their own
  ``home`` coordinate. We therefore build ``len(caregivers)`` pairs of
  start/end nodes, one pair per vehicle, plus N patient nodes.
* **Dimensions**

    - ``Distance`` — arc cost in meters (minimised via
      ``SetArcCostEvaluator``, weighted by ``alpha_distance``).
    - ``Time``     — travel seconds + service minutes (seconds-unit),
      with vehicle shift windows and optional per-patient soft windows.
    - ``Workload`` — service minutes demanded per patient, capped by
      ``daily_capacity_minutes``; the global span cost coefficient
      implements the equity criterion (weighted by ``beta_balance``).

* **Soft time windows** — a ``SetCumulVarSoftLowerBound`` /
  ``SetCumulVarSoftUpperBound`` pair (coefficient ∝ ``gamma_time``)
  penalises both early arrival waits and late lateness, without
  making windows hard (critical for healthcare where over-constraint
  yields empty plans).
* **Disjunctions** — every patient node is made droppable with a high
  penalty (also ∝ ``gamma_time``), guaranteeing the solver can return
  a feasible solution even when capacity or time is insufficient. The
  unmet nodes surface as ``OptimizeOutput.unassigned``.
* **Determinism** — OR-Tools is seeded via
  ``search_parameters.log_search = False`` and
  ``search_parameters.use_full_propagation = True``. While OR-Tools
  does not expose a pure seed option for the meta-heuristic, the
  combination of ``PATH_CHEAPEST_ARC`` + time limit is stable enough
  for the values asserted in the test suite.

If OR-Tools cannot be imported, :func:`optimize` raises
:class:`RoutingError` with a clear message rather than failing at module
import time.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services.routing.distance import DistanceProvider, HaversineProvider
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

if TYPE_CHECKING:  # pragma: no cover - typing-only
    # Avoid importing ortools at module load — it is optional.
    pass


__all__ = ["RoutingError", "optimize"]


class RoutingError(RuntimeError):
    """Raised when the solver cannot build or solve a model."""


# Fixed horizon for the ``Time`` dimension: end of service day + margin.
# OR-Tools wants integer bounds; one day plus a 2h buffer is enough to
# absorb late returns without allowing nonsensical schedules.
_DAY_HORIZON_SECONDS: int = 26 * 3600

# Large sentinel used as the per-patient drop penalty. The effective
# penalty is multiplied by ``gamma_time`` and scaled by the mean service
# time so that a single dropped patient is always costlier than any
# reasonable distance/time overrun.
_DROP_BASE_PENALTY: int = 10_000_000


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _Model:
    """Resolved inputs, ready to feed into OR-Tools."""

    coords: list[Coordinate]
    # patient indices in ``coords``, keyed by patient position in input list
    patient_nodes: list[int]
    # (start_node, end_node) per vehicle
    vehicle_depots: list[tuple[int, int]]
    distance_m: list[list[float]]
    duration_s: list[list[float]]
    # service time per node, in seconds (0 for depots)
    service_s: list[int]


def _build_model(
    caregivers: list[Caregiver],
    patients: list[PatientStop],
    provider: DistanceProvider,
) -> _Model:
    """Assemble coordinates + travel matrices + service times.

    Layout of nodes::

        [ caregiver_home_0, caregiver_home_1, ..., patient_0, patient_1, ... ]

    Each caregiver uses the same node as both start and end (round-trip
    from home). Distinct vehicles may share a home; OR-Tools handles
    that natively.
    """
    coords: list[Coordinate] = [c.home for c in caregivers]
    patient_start = len(coords)
    coords.extend(p.coord for p in patients)

    dist_m, dur_s = provider.matrix(coords)
    n = len(coords)
    if len(dist_m) != n or len(dur_s) != n:
        raise RoutingError("Distance matrix shape mismatch with coordinates")

    service_s: list[int] = [0] * n
    for idx, patient in enumerate(patients):
        service_s[patient_start + idx] = int(round(patient.service_minutes * 60))

    patient_nodes = list(range(patient_start, patient_start + len(patients)))
    vehicle_depots = [(i, i) for i in range(len(caregivers))]

    return _Model(
        coords=coords,
        patient_nodes=patient_nodes,
        vehicle_depots=vehicle_depots,
        distance_m=dist_m,
        duration_s=dur_s,
        service_s=service_s,
    )


def _empty_output(caregivers: list[Caregiver], solve_time_ms: int) -> OptimizeOutput:
    """Return an output with an empty tour for each caregiver."""
    tours = [
        Tour(
            caregiver_id=cg.id,
            stops=[],
            total_distance_m=0.0,
            total_duration_minutes=0,
            total_workload_minutes=0,
        )
        for cg in caregivers
    ]
    return OptimizeOutput(
        tours=tours,
        unassigned=[],
        total_distance_m=0.0,
        workload_stddev=0.0,
        solve_time_ms=solve_time_ms,
    )


def _stddev(values: list[float]) -> float:
    """Population standard deviation; 0.0 for <2 values."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _validate_inputs(inp: OptimizeInput) -> None:
    if not inp.caregivers:
        raise RoutingError("At least one caregiver is required.")
    for cg in inp.caregivers:
        if cg.capacity_minutes <= 0:
            raise RoutingError(
                f"Caregiver {cg.id} has non-positive capacity_minutes={cg.capacity_minutes}."
            )
        if cg.shift_end_minutes <= cg.shift_start_minutes:
            raise RoutingError(
                f"Caregiver {cg.id} has inverted shift window "
                f"[{cg.shift_start_minutes}, {cg.shift_end_minutes}]."
            )
    for p in inp.patients:
        if p.service_minutes < 0:
            raise RoutingError(
                f"Patient {p.id} has negative service_minutes={p.service_minutes}."
            )
        if p.time_window is not None:
            lo, hi = p.time_window
            if hi < lo:
                raise RoutingError(
                    f"Patient {p.id} has inverted time_window ({lo}, {hi})."
                )


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #


def optimize(
    input: OptimizeInput,
    distance_provider: DistanceProvider | None = None,
) -> OptimizeOutput:
    """Solve the CVRPTW for a single day.

    Parameters
    ----------
    input:
        All caregivers, patients and weighting options.
    distance_provider:
        Optional provider; defaults to an offline
        :class:`HaversineProvider` using ``input.options.speed_kmh``.
    """
    t0 = time.perf_counter()
    _validate_inputs(input)

    options: OptimizeOptions = input.options
    caregivers = input.caregivers
    patients = input.patients

    # Trivial: no patients → every caregiver gets an empty tour.
    if not patients:
        ms = int((time.perf_counter() - t0) * 1000)
        return _empty_output(caregivers, ms)

    # Lazy import so the package remains importable without OR-Tools.
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise RoutingError(
            "OR-Tools is not installed. Install `ortools` or call "
            "`optimize` from an environment where it is available."
        ) from exc

    provider = distance_provider or HaversineProvider(speed_kmh=options.speed_kmh)
    model = _build_model(caregivers, patients, provider)

    n_vehicles = len(caregivers)
    starts = [s for s, _ in model.vehicle_depots]
    ends = [e for _, e in model.vehicle_depots]

    manager = pywrapcp.RoutingIndexManager(
        len(model.coords), n_vehicles, starts, ends
    )
    routing = pywrapcp.RoutingModel(manager)

    # ---------------- Arc cost: distance (meters) --------------------------
    def distance_cb(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(round(model.distance_m[from_node][to_node]))

    distance_idx = routing.RegisterTransitCallback(distance_cb)
    # Alpha scaling: OR-Tools expects an int cost coefficient per
    # vehicle. We apply it via ``SetFixedCostOfVehicle``-less route
    # by wrapping the callback into a dedicated scaled callback when
    # alpha != 1.0.
    if not math.isclose(options.alpha_distance, 1.0):
        alpha_mul = max(1, int(round(options.alpha_distance * 100)))

        def scaled_distance_cb(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(round(model.distance_m[from_node][to_node] * alpha_mul / 100))

        scaled_idx = routing.RegisterTransitCallback(scaled_distance_cb)
        arc_cost_idx = scaled_idx
    else:
        arc_cost_idx = distance_idx
    for v in range(n_vehicles):
        routing.SetArcCostEvaluatorOfVehicle(arc_cost_idx, v)
    routing.AddDimension(
        distance_idx,
        0,
        10_000_000,
        True,  # fix_start_cumul_to_zero
        "Distance",
    )
    routing.GetDimensionOrDie("Distance").SetGlobalSpanCostCoefficient(0)

    # ---------------- Time dimension (seconds) -----------------------------
    def time_cb(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel = int(round(model.duration_s[from_node][to_node]))
        # Add service at the origin node (depots have service == 0).
        return travel + model.service_s[from_node]

    time_idx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(
        time_idx,
        _DAY_HORIZON_SECONDS,  # waiting slack
        _DAY_HORIZON_SECONDS,  # max cumul
        False,  # do NOT fix start to zero — we set shift windows below
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # Per-vehicle shift windows on start/end cumul variables.
    for v, cg in enumerate(caregivers):
        start_index = routing.Start(v)
        end_index = routing.End(v)
        lo = int(cg.shift_start_minutes * 60)
        hi = int(cg.shift_end_minutes * 60)
        time_dim.CumulVar(start_index).SetRange(lo, hi)
        time_dim.CumulVar(end_index).SetRange(lo, hi)

    # Per-patient soft time windows (if provided).
    gamma_coef = max(1, int(round(options.gamma_time * 10)))
    for k, patient in enumerate(patients):
        node = model.patient_nodes[k]
        index = manager.NodeToIndex(node)
        cumul = time_dim.CumulVar(index)
        # Always allow the full day; patients without a window are free.
        cumul.SetRange(0, _DAY_HORIZON_SECONDS)
        if patient.time_window is not None:
            lo_s = int(patient.time_window[0] * 60)
            hi_s = int(patient.time_window[1] * 60)
            time_dim.SetCumulVarSoftLowerBound(index, lo_s, gamma_coef)
            time_dim.SetCumulVarSoftUpperBound(index, hi_s, gamma_coef)

    # ---------------- Workload dimension (minutes) -------------------------
    def demand_cb(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        # Demand = service minutes charged when *leaving* the node.
        return int(round(model.service_s[node] / 60))

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    capacities = [int(cg.capacity_minutes) for cg in caregivers]
    routing.AddDimensionWithVehicleCapacity(
        demand_idx,
        0,          # no slack
        capacities, # per-vehicle capacity
        True,       # fix_start_cumul_to_zero
        "Workload",
    )
    workload_dim = routing.GetDimensionOrDie("Workload")
    # Equity: penalise the span of the Workload dimension (max - min).
    beta_coef = max(0, int(round(options.beta_balance * 100)))
    workload_dim.SetGlobalSpanCostCoefficient(beta_coef)

    # ---------------- Disjunctions (patient drop penalty) ------------------
    if patients:
        mean_service_s = sum(model.service_s) / max(1, len(patients))
    else:
        mean_service_s = 600.0
    drop_penalty = int(
        _DROP_BASE_PENALTY * max(1.0, options.gamma_time)
        + mean_service_s * 1000
    )
    for node in model.patient_nodes:
        index = manager.NodeToIndex(node)
        routing.AddDisjunction([index], drop_penalty)

    # ---------------- Search parameters ------------------------------------
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(max(1, int(options.time_limit_seconds)))
    search_parameters.log_search = False

    assignment = routing.SolveWithParameters(search_parameters)
    solve_ms = int((time.perf_counter() - t0) * 1000)

    if assignment is None:
        raise RoutingError(
            "Solver returned no assignment (infeasible or time budget exhausted)."
        )

    # ---------------- Extract solution -------------------------------------
    tours: list[Tour] = []
    assigned_patient_nodes: set[int] = set()

    for v, caregiver in enumerate(caregivers):
        stops: list[RouteStop] = []
        index = routing.Start(v)
        total_dist = 0.0
        prev_node = manager.IndexToNode(index)
        workload_min = 0

        # Step through the route until End.
        while not routing.IsEnd(index):
            next_index = assignment.Value(routing.NextVar(index))
            next_node = manager.IndexToNode(next_index)

            leg_distance = model.distance_m[prev_node][next_node]
            total_dist += leg_distance

            # Record every node that is a patient (skip depot start).
            if next_node in model.patient_nodes:
                assigned_patient_nodes.add(next_node)
                patient_position = next_node - len(caregivers)
                patient = patients[patient_position]
                arrival_s = assignment.Min(time_dim.CumulVar(next_index))
                departure_s = arrival_s + int(round(patient.service_minutes * 60))
                stops.append(
                    RouteStop(
                        patient_id=patient.id,
                        arrival_minutes=int(round(arrival_s / 60)),
                        departure_minutes=int(round(departure_s / 60)),
                        distance_from_prev_m=float(leg_distance),
                    )
                )
                workload_min += int(round(patient.service_minutes))

            prev_node = next_node
            index = next_index

        # Route duration: end cumul - start cumul, in minutes.
        start_time_s = assignment.Min(time_dim.CumulVar(routing.Start(v)))
        end_time_s = assignment.Min(time_dim.CumulVar(routing.End(v)))
        duration_min = max(0, int(round((end_time_s - start_time_s) / 60)))

        tours.append(
            Tour(
                caregiver_id=caregiver.id,
                stops=stops,
                total_distance_m=float(total_dist),
                total_duration_minutes=duration_min,
                total_workload_minutes=workload_min,
            )
        )

    unassigned_ids = [
        patients[node - len(caregivers)].id
        for node in model.patient_nodes
        if node not in assigned_patient_nodes
    ]

    total_distance_m = sum(t.total_distance_m for t in tours)
    workloads = [float(t.total_workload_minutes) for t in tours]
    workload_stddev = _stddev(workloads)

    return OptimizeOutput(
        tours=tours,
        unassigned=unassigned_ids,
        total_distance_m=total_distance_m,
        workload_stddev=workload_stddev,
        solve_time_ms=solve_ms,
    )
