"""Patient schemas."""
from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field


class PatientPathologyLink(BaseModel):
    pathology_id: int
    override_minutes: int | None = Field(default=None, ge=0, le=600)
    override_coefficient: float | None = Field(default=None, ge=0.1, le=10.0)


class PatientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=500)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)
    preferred_time_window_start: time | None = None
    preferred_time_window_end: time | None = None
    is_active: bool = True


class PatientCreate(PatientBase):
    consent_given_at: datetime | None = None
    pathologies: list[PatientPathologyLink] = Field(default_factory=list)


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)
    preferred_time_window_start: time | None = None
    preferred_time_window_end: time | None = None
    is_active: bool | None = None
    consent_given_at: datetime | None = None


class PatientPathologyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pathology_id: int
    override_minutes: int | None = None
    override_coefficient: float | None = None


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consent_given_at: datetime | None
    created_at: datetime
    updated_at: datetime
    pathologies: list[PatientPathologyOut] = Field(default_factory=list)
