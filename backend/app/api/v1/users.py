"""User endpoints: admin CRUD + RGPD self-service (export / delete)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.core.security import hash_password, verify_password
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.pagination import Paginated
from app.schemas.user import UserCreate, UserOut, UserSelfUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


# --- Self-service (any authenticated user) ----------------------------------


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Change the authenticated user's password after verifying the current one."""
    current = payload.get("current_password", "")
    new = payload.get("new_password", "")
    if not verify_password(current, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect")
    if len(new) < 12:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le nouveau mot de passe doit faire au moins 12 caractères")
    user.hashed_password = hash_password(new)
    db.add(user)
    db.commit()


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserSelfUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    """Update self — role/is_active are NOT user-controlled."""
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.hashed_password = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/export")
def export_me(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """RGPD data portability — export all data belonging to the user.

    Note: patient data is intentionally NOT exported here; patients own
    their own data and exercise their rights via a separate channel.
    """
    audit_rows = db.scalars(
        select(AuditLog).where(AuditLog.actor_id == user.id).order_by(AuditLog.created_at)
    ).all()
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        },
        "audit_entries": [
            {
                "action": a.action,
                "target_type": a.target_type,
                "target_id": a.target_id,
                "created_at": a.created_at.isoformat(),
            }
            for a in audit_rows
        ],
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """RGPD right to erasure — soft-delete (purge at J+30 via job)."""
    user.is_active = False
    user.deleted_at = datetime.now(tz=timezone.utc)
    db.add(user)
    db.commit()


# --- Admin CRUD -------------------------------------------------------------


@router.get("", response_model=Paginated[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
    page: int = 1,
    page_size: int = 100,
) -> Paginated[UserOut]:
    from sqlalchemy import func

    stmt = select(User)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return Paginated(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
) -> User:
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.hashed_password = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    user.deleted_at = datetime.now(tz=timezone.utc)
    db.add(user)
    db.commit()
