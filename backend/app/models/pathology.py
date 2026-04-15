"""Pathology reference table."""
from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class Pathology(Base, TimestampMixin):
    """Reference entry describing a care act / pathology."""

    __tablename__ = "pathologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    base_care_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    weight_coefficient: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    patient_links: Mapped[list["PatientPathology"]] = relationship(  # noqa: F821
        "PatientPathology", back_populates="pathology", cascade="all, delete-orphan"
    )
