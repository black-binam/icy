"""Pathology schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PathologyBase(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    base_care_minutes: int = Field(default=15, ge=1, le=600)
    weight_coefficient: float = Field(default=1.0, ge=0.1, le=10.0)


class PathologyCreate(PathologyBase):
    pass


class PathologyUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    label: str | None = Field(default=None, min_length=1, max_length=255)
    base_care_minutes: int | None = Field(default=None, ge=1, le=600)
    weight_coefficient: float | None = Field(default=None, ge=0.1, le=10.0)


class PathologyOut(PathologyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
