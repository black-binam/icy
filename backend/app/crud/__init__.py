"""Generic CRUD helpers built on SQLAlchemy 2.x."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class CRUDBase(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    """Minimal CRUD operations for a SQLAlchemy model."""

    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    def get(self, db: Session, obj_id: int) -> ModelT | None:
        return db.get(self.model, obj_id)

    def list(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelT]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    def create(self, db: Session, *, data: CreateSchemaT | dict[str, Any]) -> ModelT:
        payload = data if isinstance(data, dict) else data.model_dump(exclude_unset=False)
        obj = self.model(**payload)
        db.add(obj)
        db.flush()
        db.refresh(obj)
        return obj

    def update(
        self,
        db: Session,
        *,
        obj: ModelT,
        data: UpdateSchemaT | dict[str, Any],
    ) -> ModelT:
        payload = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(obj, field, value)
        db.add(obj)
        db.flush()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, *, obj: ModelT) -> None:
        db.delete(obj)
        db.flush()


__all__ = ["CRUDBase"]
