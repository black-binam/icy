"""Route CRUD + VRP optimization entry point."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from datetime import timezone as dt_tz

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user, get_db, require_role
from app.models.caregiver import Caregiver
from app.models.patient import Patient
from app.models.patient_pathology import PatientPathology
from app.models.pathology import Pathology
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.models.user import User, UserRole
from app.schemas.route import (
    RouteCreate,
    RouteOptimizeRequest,
    RouteOptimizeResponse,
    RouteOut,
    RouteStopOut,
    RouteUpdate,
)

router = APIRouter(prefix="/routes", tags=["routes"])

_STAFF = (UserRole.ADMIN.value, UserRole.COORDINATOR.value)


@router.get("", response_model=list[RouteOut])
def list_routes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> list[Route]:
    stmt = select(Route).options(selectinload(Route.stops))
    if user.role == UserRole.CAREGIVER:
        cg = user.caregiver
        if cg is None:
            return []
        stmt = stmt.where(Route.caregiver_id == cg.id)
    return list(db.scalars(stmt.offset(skip).limit(limit)).all())


@router.post("", response_model=RouteOut, status_code=status.HTTP_201_CREATED)
def create_route(
    payload: RouteCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> Route:
    data = payload.model_dump(exclude={"stops"})
    route = Route(**data)
    db.add(route)
    db.flush()
    for idx, stop in enumerate(payload.stops):
        db.add(
            RouteStop(
                route_id=route.id,
                patient_id=stop.patient_id,
                sequence=stop.sequence if stop.sequence is not None else idx,
                planned_arrival=stop.planned_arrival,
                planned_departure=stop.planned_departure,
                estimated_care_minutes=stop.estimated_care_minutes,
            )
        )
    db.commit()
    db.refresh(route)
    return route


@router.get("/{route_id}", response_model=RouteOut)
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Route:
    route = db.get(Route, route_id)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    if user.role == UserRole.CAREGIVER:
        cg = user.caregiver
        if cg is None or route.caregiver_id != cg.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return route


@router.patch("/{route_id}", response_model=RouteOut)
def update_route(
    route_id: int,
    payload: RouteUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> Route:
    route = db.get(Route, route_id)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        route.status = RouteStatus(data["status"])
    if "stops" in data and data["stops"] is not None:
        for stop in list(route.stops):
            db.delete(stop)
        db.flush()
        for idx, stop in enumerate(payload.stops or []):
            db.add(
                RouteStop(
                    route_id=route.id,
                    patient_id=stop.patient_id,
                    sequence=stop.sequence if stop.sequence is not None else idx,
                    planned_arrival=stop.planned_arrival,
                    planned_departure=stop.planned_departure,
                    estimated_care_minutes=stop.estimated_care_minutes,
                )
            )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> None:
    route = db.get(Route, route_id)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    db.delete(route)
    db.commit()


# --- Optimization ---------------------------------------------------------


def _service_minutes_for_patient(
    db: Session, patient_id: int, default: int = 15
) -> int:
    """Sum care minutes over a patient's pathologies, applying overrides."""
    rows = db.execute(
        select(PatientPathology, Pathology).join(
            Pathology, Pathology.id == PatientPathology.pathology_id
        ).where(PatientPathology.patient_id == patient_id)
    ).all()
    if not rows:
        return default
    total = 0.0
    for link, patho in rows:
        base = link.override_minutes if link.override_minutes is not None else patho.base_care_minutes
        coef = (
            link.override_coefficient
            if link.override_coefficient is not None
            else patho.weight_coefficient
        )
        total += float(base) * float(coef)
    return max(1, int(round(total)))


def _minutes_to_datetime(base_date, minutes: int) -> datetime:
    return datetime.combine(base_date, time(0, 0), tzinfo=dt_tz.utc) + timedelta(
        minutes=int(minutes)
    )


@router.post("/optimize", response_model=RouteOptimizeResponse)
def optimize_routes(
    payload: RouteOptimizeRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> RouteOptimizeResponse:
    """Solve the VRP for the given date.

    Loads caregivers/patients from the DB, builds the pure solver input,
    delegates to ``app.services.routing.optimize`` and persists the
    resulting tours as draft ``Route`` rows.

    Returns 503 while the solver module is absent or raises
    ``NotImplementedError``.
    """
    try:
        from app.services.routing import (  # lazy, isolates heavy deps
            Caregiver as SolverCaregiver,
            Coordinate,
            OptimizeInput,
            OptimizeOptions,
            PatientStop,
            optimize as solver_optimize,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Routing solver is not available yet",
        ) from exc

    # Load caregivers.
    cg_stmt = select(Caregiver)
    if payload.caregiver_ids:
        cg_stmt = cg_stmt.where(Caregiver.id.in_(payload.caregiver_ids))
    caregivers = list(db.scalars(cg_stmt).all())
    if not caregivers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No caregivers selected",
        )

    # Load patients.
    pat_stmt = select(Patient).where(Patient.is_active.is_(True))
    if payload.patient_ids:
        pat_stmt = pat_stmt.where(Patient.id.in_(payload.patient_ids))
    patients = list(db.scalars(pat_stmt).all())

    solver_caregivers = [
        SolverCaregiver(
            id=cg.id,
            home=Coordinate(lat=cg.home_base_lat, lon=cg.home_base_lon),
            capacity_minutes=cg.daily_capacity_minutes,
        )
        for cg in caregivers
    ]

    solver_patients: list[PatientStop] = []
    for p in patients:
        tw = None
        if p.preferred_time_window_start and p.preferred_time_window_end:
            tw = (
                p.preferred_time_window_start.hour * 60
                + p.preferred_time_window_start.minute,
                p.preferred_time_window_end.hour * 60
                + p.preferred_time_window_end.minute,
            )
        solver_patients.append(
            PatientStop(
                id=p.id,
                coord=Coordinate(lat=p.lat, lon=p.lon),
                service_minutes=_service_minutes_for_patient(db, p.id),
                time_window=tw,
            )
        )

    solver_input = OptimizeInput(
        caregivers=solver_caregivers,
        patients=solver_patients,
        options=OptimizeOptions(time_limit_seconds=payload.max_seconds),
    )

    try:
        result = solver_optimize(solver_input)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Routing solver is not wired yet",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        # The solver module defines RoutingError; fall back to generic 500.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Solver failed: {exc}",
        ) from exc

    # Persist as draft Routes.
    created_routes: list[Route] = []
    for tour in result.tours:
        route = Route(
            caregiver_id=int(tour.caregiver_id),
            date=payload.date,
            status=RouteStatus.DRAFT,
            total_distance_m=float(tour.total_distance_m),
            total_duration_s=int(tour.total_duration_minutes) * 60,
            total_workload_minutes=int(tour.total_workload_minutes),
        )
        db.add(route)
        db.flush()
        for idx, st in enumerate(tour.stops):
            db.add(
                RouteStop(
                    route_id=route.id,
                    patient_id=int(st.patient_id),
                    sequence=idx,
                    planned_arrival=_minutes_to_datetime(payload.date, st.arrival_minutes),
                    planned_departure=_minutes_to_datetime(payload.date, st.departure_minutes),
                    estimated_care_minutes=int(
                        max(0, st.departure_minutes - st.arrival_minutes)
                    ),
                )
            )
        db.flush()
        db.refresh(route)
        created_routes.append(route)

    db.commit()

    return RouteOptimizeResponse(
        solved=True,
        routes=[
            RouteOut(
                id=r.id,
                caregiver_id=r.caregiver_id,
                date=r.date,
                status=r.status,
                total_distance_m=r.total_distance_m,
                total_duration_s=r.total_duration_s,
                total_workload_minutes=r.total_workload_minutes,
                stops=[
                    RouteStopOut(
                        id=s.id,
                        patient_id=s.patient_id,
                        sequence=s.sequence,
                        planned_arrival=s.planned_arrival,
                        planned_departure=s.planned_departure,
                        estimated_care_minutes=s.estimated_care_minutes,
                    )
                    for s in r.stops
                ],
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in created_routes
        ],
        unassigned_patient_ids=[int(x) for x in result.unassigned],
        objective_value=float(result.total_distance_m),
        solver_seconds=float(result.solve_time_ms) / 1000.0,
    )
