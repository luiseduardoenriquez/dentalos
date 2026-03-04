"""Add Sprint 31-32 tables: call_logs, eps_claims, dental_labs, lab_orders.

Revision ID: 015_sprint31_voip_claims
Revises: 014_sprint29_financing
Create Date: 2026-03-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "015_sprint31_voip_claims"
down_revision: Union[str, None] = "014_sprint29_financing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. call_logs (VP-18 VoIP Screen Pop) ─────────────────────────────
    op.create_table(
        "call_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'ringing'"),
        ),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column(
            "staff_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("twilio_call_sid", sa.String(64), nullable=True, unique=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="chk_call_logs_direction",
        ),
        sa.CheckConstraint(
            "status IN ('ringing', 'in_progress', 'completed', 'missed', 'voicemail')",
            name="chk_call_logs_status",
        ),
    )
    op.create_index("idx_call_logs_patient", "call_logs", ["patient_id"])
    op.create_index("idx_call_logs_phone", "call_logs", ["phone_number"])
    op.create_index("idx_call_logs_started_at", "call_logs", ["started_at"])

    # ── 2. eps_claims (VP-19 EPS Claims Management) ─────────────────────
    op.create_table(
        "eps_claims",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("eps_code", sa.String(20), nullable=False),
        sa.Column("eps_name", sa.String(200), nullable=False),
        sa.Column("claim_type", sa.String(30), nullable=False),
        sa.Column(
            "procedures",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("total_amount_cents", sa.Integer, nullable=False),
        sa.Column("copay_amount_cents", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("external_claim_id", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "claim_type IN ('outpatient', 'emergency', 'hospitalization', 'dental')",
            name="chk_eps_claims_claim_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'acknowledged', 'paid', 'rejected', 'appealed')",
            name="chk_eps_claims_status",
        ),
    )
    op.create_index("idx_eps_claims_patient", "eps_claims", ["patient_id"])
    op.create_index("idx_eps_claims_status", "eps_claims", ["status"])
    op.create_index("idx_eps_claims_submitted_at", "eps_claims", ["submitted_at"])
    op.create_index("idx_eps_claims_is_active", "eps_claims", ["is_active"])

    # ── 3. dental_labs (VP-22 Lab Order Management) ─────────────────────
    op.create_table(
        "dental_labs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── 4. lab_orders (VP-22 Lab Order Management) ──────────────────────
    op.create_table(
        "lab_orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "treatment_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("treatment_plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "lab_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dental_labs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("order_type", sa.String(30), nullable=False),
        sa.Column(
            "specifications",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_cents", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "order_type IN ('crown', 'bridge', 'denture', 'implant_abutment', 'retainer', 'other')",
            name="chk_lab_orders_order_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent_to_lab', 'in_progress', 'ready', 'delivered', 'cancelled')",
            name="chk_lab_orders_status",
        ),
    )
    op.create_index("idx_lab_orders_patient", "lab_orders", ["patient_id"])
    op.create_index("idx_lab_orders_lab", "lab_orders", ["lab_id"])
    op.create_index("idx_lab_orders_status", "lab_orders", ["status"])
    op.create_index("idx_lab_orders_due_date", "lab_orders", ["due_date"])

    # ── 5. ALTER: add phone index on patients for screen-pop lookup ─────
    op.create_index(
        "idx_patients_phone",
        "patients",
        ["phone"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_patients_phone", table_name="patients")
    op.drop_table("lab_orders")
    op.drop_table("dental_labs")
    op.drop_table("eps_claims")
    op.drop_table("call_logs")
