"""Patient model with field-level encryption on PII."""
from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, Float, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin
from app.core.security import EncryptedString


class Patient(Base, TimestampMixin):
    """Patient record; PII fields are stored encrypted at rest.

    Note: encrypted columns cannot be searched by equality or LIKE.
    """

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(EncryptedString(), nullable=False)
    last_name: Mapped[str] = mapped_column(EncryptedString(), nullable=False)
    # Address is highly identifying for at-home patients: encrypted at rest.
    address: Mapped[str] = mapped_column(EncryptedString(length=1024), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    phone: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    notes: Mapped[str | None] = mapped_column(EncryptedString(length=4096), nullable=True)
    preferred_time_window_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    preferred_time_window_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pathologies: Mapped[list["PatientPathology"]] = relationship(  # noqa: F821
        "PatientPathology", back_populates="patient", cascade="all, delete-orphan"
    )
    route_stops: Mapped[list["RouteStop"]] = relationship(  # noqa: F821
        "RouteStop", back_populates="patient"
    )
