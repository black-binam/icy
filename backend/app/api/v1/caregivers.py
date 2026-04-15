"""Caregiver CRUD (admin / coordinator)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.caregiver import Caregiver
from app.models.user import User, UserRole
from app.schemas.caregiver import CaregiverCreate, CaregiverOut, CaregiverUpdate

router = APIRouter(prefix="/caregivers", tags=["caregivers"])

_STAFF = (UserRole.ADMIN.value, UserRole.COORDINATOR.value)


@router.get("", response_model=list[CaregiverOut])
def list_caregivers(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
    skip: int = 0,
    limit: int = 100,
) -> list[Caregiver]:
    stmt = select(Caregiver).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


@router.post("", response_model=CaregiverOut, status_code=status.HTTP_201_CREATED)
def create_caregiver(
    payload: CaregiverCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> Caregiver:
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if db.scalar(select(Caregiver).where(Caregiver.user_id == payload.user_id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Caregiver already exists for this user"
        )
    cg = Caregiver(**payload.model_dump())
    db.add(cg)
    db.commit()
    db.refresh(cg)
    return cg


@router.get("/{cg_id}", response_model=CaregiverOut)
def get_caregiver(
    cg_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> Caregiver:
    cg = db.get(Caregiver, cg_id)
    if cg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caregiver not found")
    return cg


@router.patch("/{cg_id}", response_model=CaregiverOut)
def update_caregiver(
    cg_id: int,
    payload: CaregiverUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> Caregiver:
    cg = db.get(Caregiver, cg_id)
    if cg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caregiver not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cg, k, v)
    db.add(cg)
    db.commit()
    db.refresh(cg)
    return cg


@router.delete("/{cg_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_caregiver(
    cg_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*_STAFF)),
) -> None:
    cg = db.get(Caregiver, cg_id)
    if cg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caregiver not found")
    db.delete(cg)
    db.commit()
