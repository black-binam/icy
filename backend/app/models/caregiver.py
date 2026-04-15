"""Caregiver profile model."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base, TimestampMixin

# Use JSONB on Postgres, JSON elsewhere (sqlite tests).
SkillsJSON = JSON().with_variant(JSONB(), "postgresql")


class Caregiver(Base, TimestampMixin):
    """Professional profile attached to a User account."""

    __tablename__ = "caregivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    home_base_lat: Mapped[float] = mapped_column(Float, nullable=False)
    home_base_lon: Mapped[float] = mapped_column(Float, nullable=False)
    daily_capacity_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=420)
    skills: Mapped[list[Any]] = mapped_column(SkillsJSON, nullable=False, default=list)

    user: Mapped["User"] = relationship("User", back_populates="caregiver")  # noqa: F821
    routes: Mapped[list["Route"]] = relationship(  # noqa: F821
        "Route", back_populates="caregiver", cascade="all, delete-orphan"
    )
