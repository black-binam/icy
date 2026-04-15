"""Pathology reference CRUD (admin)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.models.pathology import Pathology
from app.models.user import User, UserRole
from app.schemas.pathology import PathologyCreate, PathologyOut, PathologyUpdate

router = APIRouter(prefix="/pathologies", tags=["pathologies"])


@router.get("", response_model=list[PathologyOut])
def list_pathologies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Pathology]:
    """Any authenticated user may read the reference table."""
    return list(db.scalars(select(Pathology)).all())


@router.post("", response_model=PathologyOut, status_code=status.HTTP_201_CREATED)
def create_pathology(
    payload: PathologyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
) -> Pathology:
    if db.scalar(select(Pathology).where(Pathology.code == payload.code)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Pathology code already exists"
        )
    obj = Pathology(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{pk}", response_model=PathologyOut)
def update_pathology(
    pk: int,
    payload: PathologyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
) -> Pathology:
    obj = db.get(Pathology, pk)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pathology not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{pk}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pathology(
    pk: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
) -> None:
    obj = db.get(Pathology, pk)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pathology not found")
    db.delete(obj)
    db.commit()
