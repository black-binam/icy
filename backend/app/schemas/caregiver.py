"""Caregiver schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CaregiverBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    home_base_lat: float = Field(ge=-90, le=90)
    home_base_lon: float = Field(ge=-180, le=180)
    daily_capacity_minutes: int = Field(default=420, ge=30, le=1440)
    skills: list[Any] = Field(default_factory=list)


class CaregiverCreate(CaregiverBase):
    user_id: int


class CaregiverUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    home_base_lat: float | None = Field(default=None, ge=-90, le=90)
    home_base_lon: float | None = Field(default=None, ge=-180, le=180)
    daily_capacity_minutes: int | None = Field(default=None, ge=30, le=1440)
    skills: list[Any] | None = None


class CaregiverOut(CaregiverBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
