"""Patient <-> Pathology association with per-patient overrides."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class PatientPathology(Base, TimestampMixin):
    """Link between a Patient and a Pathology with optional overrides."""

    __tablename__ = "patient_pathologies"
    __table_args__ = (
        UniqueConstraint("patient_id", "pathology_id", name="uq_patient_pathology"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pathology_id: Mapped[int] = mapped_column(
        ForeignKey("pathologies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    override_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_coefficient: Mapped[float | None] = mapped_column(Float, nullable=True)

    patient: Mapped["Patient"] = relationship(  # noqa: F821
        "Patient", back_populates="pathologies"
    )
    pathology: Mapped["Pathology"] = relationship(  # noqa: F821
        "Pathology", back_populates="patient_links"
    )
