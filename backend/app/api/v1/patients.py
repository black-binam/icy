"""Patient CRUD (admin / coordinator)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user, get_db, require_role
from app.models.patient import Patient
from app.models.patient_pathology import PatientPathology
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.models.user import User, UserRole
from app.schemas.patient import PatientCreate, PatientOut, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])

_STAFF = (UserRole.ADMIN.value, UserRole.COORDINATOR.value)


@router.get("", response_model=list[PatientOut])
def list_patients(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> list[Patient]:
    """List patients.

    - admin / coordinator: all active patients.
    - caregiver: only patients scheduled on their upcoming/in-progress routes.
    """
    stmt = select(Patient).options(selectinload(Patient.pathologies))
    if user.role == UserRole.CAREGIVER:
        cg = user.caregiver
        if cg is None:
            return []
        stmt = (
            stmt.join(RouteStop, RouteStop.patient_id == Patient.id)
            .join(Route, Route.id == RouteStop.route_id)
            .where(Route.caregiver_id == cg.id)
            .where(Route.status.in_([RouteStatus.PUBLISHED, RouteStatus.IN_PROGRESS]))
            .distinct()
        )
    return list(db.scalars(stmt.offset(skip).limit(limit)).all())


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> Patient:
    data = payload.model_dump(exclude={"pathologies"})
    patient = Patient(**data)
    db.add(patient)
    db.flush()
    for link in payload.pathologies:
        db.add(
            PatientPathology(
                patient_id=patient.id,
                pathology_id=link.pathology_id,
                override_minutes=link.override_minutes,
                override_coefficient=link.override_coefficient,
            )
        )
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if user.role == UserRole.CAREGIVER:
        cg = user.caregiver
        if cg is None or not _caregiver_sees_patient(db, cg_id=cg.id, patient_id=patient_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(patient, k, v)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> None:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    patient.is_active = False
    db.add(patient)
    db.commit()


def _caregiver_sees_patient(db: Session, *, cg_id: int, patient_id: int) -> bool:
    stmt = (
        select(RouteStop.id)
        .join(Route, Route.id == RouteStop.route_id)
        .where(RouteStop.patient_id == patient_id)
        .where(Route.caregiver_id == cg_id)
        .where(Route.status.in_([RouteStatus.PUBLISHED, RouteStatus.IN_PROGRESS]))
        .limit(1)
    )
    return db.scalar(stmt) is not None
