"""Route model (one tour for a caregiver for a given date)."""
from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class RouteStatus(str, enum.Enum):
    """Lifecycle of a route."""

    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Route(Base, TimestampMixin):
    """Planned tour for a caregiver on a specific date."""

    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    caregiver_id: Mapped[int] = mapped_column(
        ForeignKey("caregivers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    status: Mapped[RouteStatus] = mapped_column(
        Enum(RouteStatus, name="route_status", native_enum=False, length=32),
        nullable=False,
        default=RouteStatus.DRAFT,
    )
    total_distance_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_duration_s: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_workload_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    caregiver: Mapped["Caregiver"] = relationship("Caregiver", back_populates="routes")  # noqa: F821
    stops: Mapped[list["RouteStop"]] = relationship(  # noqa: F821
        "RouteStop",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteStop.sequence",
    )
