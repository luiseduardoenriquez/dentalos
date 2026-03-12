"""GAP-12: Facial aesthetics tables.

Revision ID: gap12_facial_aesthetics
Revises: 016_sprint33_ortho
Create Date: 2026-03-11

Creates:
  - facial_aesthetics_sessions
  - facial_aesthetics_injections
  - facial_aesthetics_history
  - facial_aesthetics_snapshots
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "gap12_facial_aesthetics"
down_revision = "016_sprint33_ortho"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── facial_aesthetics_sessions ──────────────────────────────────────
    op.create_table(
        "facial_aesthetics_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("diagram_type", sa.String(20), server_default="face_front", nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "diagram_type IN ('face_front','face_lateral_left','face_lateral_right')",
            name="chk_facial_aesthetics_sessions_diagram_type",
        ),
    )
    op.create_index("idx_facial_aesthetics_sessions_patient", "facial_aesthetics_sessions", ["patient_id"])
    op.create_index("idx_facial_aesthetics_sessions_created", "facial_aesthetics_sessions", ["created_at"])

    # ─── facial_aesthetics_injections ────────────────────────────────────
    op.create_table(
        "facial_aesthetics_injections",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facial_aesthetics_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("zone_id", sa.String(50), nullable=False),
        sa.Column("injection_type", sa.String(30), nullable=False),
        sa.Column("product_name", sa.String(100), nullable=True),
        sa.Column("dose_units", sa.Numeric(6, 2), nullable=True),
        sa.Column("dose_volume_ml", sa.Numeric(5, 2), nullable=True),
        sa.Column("depth", sa.String(20), nullable=True),
        sa.Column("coordinates_x", sa.Numeric(6, 3), nullable=True),
        sa.Column("coordinates_y", sa.Numeric(6, 3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "zone_id", name="uq_facial_aesthetics_injections_session_zone"),
        sa.CheckConstraint(
            "injection_type IN ('botulinum_toxin','hyaluronic_acid','calcium_hydroxylapatite','poly_lactic_acid','prf','other')",
            name="chk_facial_aesthetics_injections_type",
        ),
        sa.CheckConstraint(
            "depth IS NULL OR depth IN ('intradermal','subcutaneous','supraperiosteal','intramuscular')",
            name="chk_facial_aesthetics_injections_depth",
        ),
    )
    op.create_index("idx_facial_aesthetics_injections_session", "facial_aesthetics_injections", ["session_id"])
    op.create_index("idx_facial_aesthetics_injections_patient", "facial_aesthetics_injections", ["patient_id"])

    # ─── facial_aesthetics_history ───────────────────────────────────────
    op.create_table(
        "facial_aesthetics_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facial_aesthetics_sessions.id"), nullable=False),
        sa.Column("zone_id", sa.String(50), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("injection_type", sa.String(30), nullable=False),
        sa.Column("previous_data", postgresql.JSONB(), nullable=True),
        sa.Column("new_data", postgresql.JSONB(), nullable=True),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_facial_aesthetics_history_patient", "facial_aesthetics_history", ["patient_id"])
    op.create_index("idx_facial_aesthetics_history_session", "facial_aesthetics_history", ["session_id"])
    op.create_index("idx_facial_aesthetics_history_created", "facial_aesthetics_history", ["created_at"])

    # ─── facial_aesthetics_snapshots ─────────────────────────────────────
    op.create_table(
        "facial_aesthetics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facial_aesthetics_sessions.id"), nullable=True),
        sa.Column("snapshot_data", postgresql.JSONB(), nullable=False),
        sa.Column("diagram_type", sa.String(20), nullable=False),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("linked_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_facial_aesthetics_snapshots_patient", "facial_aesthetics_snapshots", ["patient_id"])
    op.create_index("idx_facial_aesthetics_snapshots_created", "facial_aesthetics_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_table("facial_aesthetics_snapshots")
    op.drop_table("facial_aesthetics_history")
    op.drop_table("facial_aesthetics_injections")
    op.drop_table("facial_aesthetics_sessions")
