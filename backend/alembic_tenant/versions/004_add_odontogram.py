"""Add odontogram tables to tenant schema

Revision ID: 004_add_odontogram
Revises: 003_add_patients
Create Date: 2026-02-25

Four tables:
  - odontogram_states:     per-patient dentition settings (one per patient)
  - odontogram_conditions: individual tooth/zone conditions
  - odontogram_history:    immutable audit trail of condition changes
  - odontogram_snapshots:  point-in-time full-state captures
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "004_add_odontogram"
down_revision: Union[str, None] = "003_add_patients"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── odontogram_states ────────────────────────────────────────────────
    op.create_table(
        "odontogram_states",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, unique=True),
        sa.Column("dentition_type", sa.String(20), nullable=False, server_default="adult"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "dentition_type IN ('adult', 'pediatric', 'mixed')",
            name="chk_odontogram_states_dentition_type",
        ),
    )
    op.create_index("idx_odontogram_states_patient", "odontogram_states", ["patient_id"])

    # ── odontogram_conditions ────────────────────────────────────────────
    op.create_table(
        "odontogram_conditions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("tooth_number", sa.Integer, nullable=False),
        sa.Column("zone", sa.String(20), nullable=False),
        sa.Column("condition_code", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("patient_id", "tooth_number", "zone", name="uq_odontogram_conditions_tooth_zone"),
        sa.CheckConstraint(
            "zone IN ('mesial','distal','vestibular','lingual','palatino','oclusal','incisal','root','full')",
            name="chk_odontogram_conditions_zone",
        ),
        sa.CheckConstraint(
            "condition_code IN ('caries','restoration','extraction','absent','crown',"
            "'endodontic','implant','fracture','sealant','fluorosis',"
            "'temporary','prosthesis')",
            name="chk_odontogram_conditions_code",
        ),
        sa.CheckConstraint(
            "severity IS NULL OR severity IN ('mild', 'moderate', 'severe')",
            name="chk_odontogram_conditions_severity",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'voice')",
            name="chk_odontogram_conditions_source",
        ),
    )
    op.create_index("idx_odontogram_conditions_patient", "odontogram_conditions", ["patient_id"])
    op.create_index("idx_odontogram_conditions_tooth", "odontogram_conditions", ["patient_id", "tooth_number"])

    # ── odontogram_history (immutable — no updated_at) ───────────────────
    op.create_table(
        "odontogram_history",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("tooth_number", sa.Integer, nullable=False),
        sa.Column("zone", sa.String(20), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("condition_code", sa.String(30), nullable=False),
        sa.Column("previous_data", JSONB, nullable=True),
        sa.Column("new_data", JSONB, nullable=True),
        sa.Column("performed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("idx_odontogram_history_patient_tooth", "odontogram_history", ["patient_id", "tooth_number"])
    op.create_index("idx_odontogram_history_created", "odontogram_history", ["created_at"])

    # ── odontogram_snapshots ─────────────────────────────────────────────
    op.create_table(
        "odontogram_snapshots",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("snapshot_data", JSONB, nullable=False),
        sa.Column("dentition_type", sa.String(20), nullable=False),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("linked_record_id", UUID(as_uuid=True), nullable=True),
        sa.Column("linked_treatment_plan_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_odontogram_snapshots_patient", "odontogram_snapshots", ["patient_id"])
    op.create_index("idx_odontogram_snapshots_created", "odontogram_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_odontogram_snapshots_created", table_name="odontogram_snapshots")
    op.drop_index("idx_odontogram_snapshots_patient", table_name="odontogram_snapshots")
    op.drop_table("odontogram_snapshots")

    op.drop_index("idx_odontogram_history_created", table_name="odontogram_history")
    op.drop_index("idx_odontogram_history_patient_tooth", table_name="odontogram_history")
    op.drop_table("odontogram_history")

    op.drop_index("idx_odontogram_conditions_tooth", table_name="odontogram_conditions")
    op.drop_index("idx_odontogram_conditions_patient", table_name="odontogram_conditions")
    op.drop_table("odontogram_conditions")

    op.drop_index("idx_odontogram_states_patient", table_name="odontogram_states")
    op.drop_table("odontogram_states")
