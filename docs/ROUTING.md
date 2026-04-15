# Routing & VRP — Technical Notes

This document describes the optimisation module that lives under
`backend/app/services/routing/`. It is self-contained (no FastAPI /
SQLAlchemy dependency) and can be exercised in isolation with
`pytest app/tests/test_routing.py`.

## 1. Problem

A **Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)**:

* A fleet of **caregivers** (vehicles), each with their own home base
  (`home`), daily minute budget (`capacity_minutes`), and shift
  window `[shift_start_minutes, shift_end_minutes]`.
* A set of **patients** (stops) geolocated, each with:
  * a service duration `service_minutes` (precomputed by
    [`compute_patient_minutes`](../backend/app/services/routing/compute.py)
    from pathologies and overrides),
  * an optional preferred **time window** `time_window_start..end`.
* A **distance / duration matrix** produced by a pluggable
  provider (Haversine, OSRM, OpenRouteService).

Output: for each caregiver, an ordered list of patient visits with
arrival/departure times, plus a list of patients the solver could not
schedule given the constraints.

## 2. Mathematical formulation (compact)

Let:

* `V` — set of caregivers (vehicles), `P` — set of patient nodes.
* `x_{ijv} ∈ {0,1}` — caregiver `v` uses arc `(i,j)`.
* `y_p ∈ {0,1}` — patient `p` is dropped (disjunction slack).
* `d_{ij}` — travel distance (m), `t_{ij}` — travel time (s),
  `s_p` — service time (s), `w_p ∈ [a_p, b_p]` — preferred window.
* `T_v` — workload of `v` (Σ `s_p` over its stops).

Minimise

```
α · Σ_{i,j,v} d_{ij} · x_{ijv}            (distance)
+ β · (max_v T_v − min_v T_v)             (equity, via SpanCostCoefficient)
+ γ · Σ_p [ soft_lower(a_p) + soft_upper(b_p) ]
+ Γ · Σ_p y_p                             (drop penalty, Γ ≫ α,β,γ · n)
```

Subject to:

* Flow conservation per vehicle on its start / end depots.
* `T_v ≤ capacity_minutes_v` (Workload dimension).
* `start_cumul_time_v ∈ [shift_start_v, shift_end_v]`.
* Time cumul at depot end ≤ shift end (hard).
* Per-patient soft windows `[a_p, b_p]` (see §4).

## 3. Weights (`OptimizeOptions`)

| Parameter            | Default | Role                                                     |
|----------------------|---------|----------------------------------------------------------|
| `alpha_distance`     | 1.0     | Arc cost multiplier (distance in meters).                |
| `beta_balance`       | 1.0     | `GlobalSpanCostCoefficient` on the `Workload` dimension. |
| `gamma_time`         | 1.0     | Penalty scaler on soft window violations & drops.        |
| `time_limit_seconds` | 20      | OR-Tools wall-clock budget.                              |
| `speed_kmh`          | 30.0    | Fallback urban speed for Haversine travel time.          |

## 4. OR-Tools modelling choices

* **Multi-depot** — each vehicle has its own start *and* end node
  pointing to its caregiver's home coordinate. This is straightforward
  with `RoutingIndexManager(len(coords), n_vehicles, starts, ends)`.
* **Dimensions**
  * `Distance` (meters, int) — arc cost evaluator used via
    `SetArcCostEvaluatorOfVehicle`.
  * `Time` (seconds, int) — travel + service at the origin. Shift
    windows applied to start/end cumul variables; patient soft windows
    via `SetCumulVarSoftLowerBound` / `SetCumulVarSoftUpperBound`.
  * `Workload` (minutes, int) — per-vehicle capacities; equity via
    `SetGlobalSpanCostCoefficient(beta_balance * 100)`.
* **Disjunctions** — every patient node is made droppable with a large
  integer penalty proportional to `gamma_time`. Dropped patients are
  surfaced as `OptimizeOutput.unassigned`.
* **Search**
  * First solution: `PATH_CHEAPEST_ARC` (fast, good for warm-start).
  * Local search: `GUIDED_LOCAL_SEARCH`.
  * Time limit: `options.time_limit_seconds`.

## 5. Distance providers

Defined in `distance.py`:

* `HaversineProvider` — always available, uses great-circle + constant
  speed. Acceptable for MVP and offline tests.
* `OSRMProvider` — hits `/table/v1/driving/...` on an OSRM host
  (`OSRM_BASE_URL`). Requires `httpx`.
* `OpenRouteServiceProvider` — hits `/v2/matrix/driving-car` on ORS
  with `OPENROUTESERVICE_API_KEY`. Requires `httpx`.
* `get_provider(settings)` — factory that reads `ROUTING_PROVIDER` and
  gracefully falls back to Haversine when config or `httpx` is missing
  (with a runtime warning).

## 6. Known limitations

* **Single-day horizon** — no multi-day planning.
* **No skills matching** — `Caregiver.skills` is stored but not yet
  used as a constraint. A `NodeDisallowedInAssignment` callback is the
  planned extension.
* **Deterministic-only inputs** — traffic / stochastic durations are
  not modelled; use OSRM in an environment-aware mode if needed.
* **Mono-objective aggregation** — Pareto fronts are not returned; we
  collapse α/β/γ into a single weighted cost.
* **Determinism** — OR-Tools does not expose a true RNG seed for GLS;
  the test suite assertions are written with tolerances.

## 7. Possible extensions

* Skills / certifications as hard `AllowedVehiclesForNode`.
* Multi-day planning (stack N copies of the graph with symmetry breakers).
* Patient priorities (VIP, fragility) as per-patient disjunction
  penalties overriding the global drop penalty.
* Break / lunch windows on the `Time` dimension.
* Traffic-aware OSRM (`annotations=duration,distance` already on).
* Warm-start from yesterday's plan via
  `ReadAssignmentFromRoutes`.

## 8. Endpoint wiring (reference)

The HTTP layer (future `POST /routes/optimize`) is expected to:

1. Load caregivers + patients + pathologies from SQLAlchemy.
2. Convert each patient's pathology list into `service_minutes` with
   `compute_patient_minutes`.
3. Build an `OptimizeInput`.
4. Resolve a `DistanceProvider` via `get_provider(settings)`.
5. Call `optimize(input, provider)` (blocking ~= seconds — wrap in a
   Celery task in production).
6. Persist the returned `Tour`s into `Route` / `RouteStop` tables.
7. Return `OptimizeOutput` to the caller.
