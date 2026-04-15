"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-15

"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Best-effort PostGIS — not blocking if the role lacks CREATE EXTENSION.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))
        except Exception:  # noqa: BLE001
            # Continue without PostGIS — lat/lon floats cover MVP needs.
            pass

    # --- users ---------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="caregiver"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- caregivers ----------------------------------------------------
    json_variant = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "caregivers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("home_base_lat", sa.Float(), nullable=False),
        sa.Column("home_base_lon", sa.Float(), nullable=False),
        sa.Column(
            "daily_capacity_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("420"),
        ),
        sa.Column("skills", json_variant, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_caregivers_user_id", "caregivers", ["user_id"], unique=True)

    # --- patients ------------------------------------------------------
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(length=1024), nullable=False),  # ciphertext
        sa.Column("last_name", sa.String(length=1024), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(length=1024), nullable=True),
        sa.Column("notes", sa.String(length=4096), nullable=True),
        sa.Column("preferred_time_window_start", sa.Time(), nullable=True),
        sa.Column("preferred_time_window_end", sa.Time(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- pathologies ---------------------------------------------------
    op.create_table(
        "pathologies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "base_care_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("15"),
        ),
        sa.Column(
            "weight_coefficient",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_pathologies_code", "pathologies", ["code"], unique=True)

    # --- patient_pathologies ------------------------------------------
    op.create_table(
        "patient_pathologies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Integer(),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pathology_id",
            sa.Integer(),
            sa.ForeignKey("pathologies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("override_minutes", sa.Integer(), nullable=True),
        sa.Column("override_coefficient", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("patient_id", "pathology_id", name="uq_patient_pathology"),
    )
    op.create_index(
        "ix_patient_pathologies_patient_id", "patient_pathologies", ["patient_id"]
    )
    op.create_index(
        "ix_patient_pathologies_pathology_id", "patient_pathologies", ["pathology_id"]
    )

    # --- routes --------------------------------------------------------
    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "caregiver_id",
            sa.Integer(),
            sa.ForeignKey("caregivers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column(
            "total_distance_m", sa.Float(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "total_duration_s", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "total_workload_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_routes_caregiver_id", "routes", ["caregiver_id"])
    op.create_index("ix_routes_date", "routes", ["date"])

    # --- route_stops ---------------------------------------------------
    op.create_table(
        "route_stops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "route_id",
            sa.Integer(),
            sa.ForeignKey("routes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            sa.Integer(),
            sa.ForeignKey("patients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("planned_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "estimated_care_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("route_id", "sequence", name="uq_route_stop_sequence"),
    )
    op.create_index("ix_route_stops_route_id", "route_stops", ["route_id"])
    op.create_index("ix_route_stops_patient_id", "route_stops", ["patient_id"])

    # --- audit_logs ----------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("ip_anonymized", sa.String(length=64), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("extra", json_variant, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_route_stops_patient_id", table_name="route_stops")
    op.drop_index("ix_route_stops_route_id", table_name="route_stops")
    op.drop_table("route_stops")

    op.drop_index("ix_routes_date", table_name="routes")
    op.drop_index("ix_routes_caregiver_id", table_name="routes")
    op.drop_table("routes")

    op.drop_index("ix_patient_pathologies_pathology_id", table_name="patient_pathologies")
    op.drop_index("ix_patient_pathologies_patient_id", table_name="patient_pathologies")
    op.drop_table("patient_pathologies")

    op.drop_index("ix_pathologies_code", table_name="pathologies")
    op.drop_table("pathologies")

    op.drop_table("patients")

    op.drop_index("ix_caregivers_user_id", table_name="caregivers")
    op.drop_table("caregivers")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
