"""Add Sprint 33 tables: ortho_cases, ortho_bonding_records, ortho_bonding_teeth,
ortho_visits, ortho_case_materials.

Revision ID: 016_sprint33_ortho
Revises: 015_sprint31_voip_claims
Create Date: 2026-03-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "016_sprint33_ortho"
down_revision: Union[str, None] = "015_sprint31_voip_claims"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. ortho_cases (GAP-07 Orthodontics — main case entity) ──────────
    op.create_table(
        "ortho_cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id"),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "treatment_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("treatment_plans.id"),
            nullable=True,
        ),
        sa.Column("case_number", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'planning'"),
        ),
        sa.Column("angle_class", sa.String(20), nullable=True),
        sa.Column("malocclusion_type", sa.String(100), nullable=True),
        sa.Column("appliance_type", sa.String(30), nullable=False),
        sa.Column("estimated_duration_months", sa.Integer, nullable=True),
        sa.Column("actual_start_date", sa.Date, nullable=True),
        sa.Column("actual_end_date", sa.Date, nullable=True),
        sa.Column(
            "total_cost_estimated",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "initial_payment",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "monthly_payment",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("notes", sa.Text, nullable=True),
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
            "status IN ('planning','bonding','active_treatment','retention','completed','cancelled')",
            name="chk_ortho_cases_status",
        ),
        sa.CheckConstraint(
            "angle_class IS NULL OR angle_class IN ('class_i','class_ii_div1','class_ii_div2','class_iii')",
            name="chk_ortho_cases_angle_class",
        ),
        sa.CheckConstraint(
            "appliance_type IN ('brackets','aligners','mixed')",
            name="chk_ortho_cases_appliance_type",
        ),
    )
    op.create_index("idx_ortho_cases_patient", "ortho_cases", ["patient_id"])
    op.create_index("idx_ortho_cases_doctor", "ortho_cases", ["doctor_id"])
    op.create_index("idx_ortho_cases_status", "ortho_cases", ["status"])

    # ── 2. ortho_bonding_records (bonding session header) ─────────────────
    op.create_table(
        "ortho_bonding_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "ortho_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ortho_cases.id"),
            nullable=False,
        ),
        sa.Column(
            "recorded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text, nullable=True),
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
    )
    op.create_index(
        "idx_ortho_bonding_records_case",
        "ortho_bonding_records",
        ["ortho_case_id"],
    )

    # ── 3. ortho_bonding_teeth (per-tooth bracket state) ─────────────────
    op.create_table(
        "ortho_bonding_teeth",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ortho_bonding_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tooth_number", sa.Integer, nullable=False),
        sa.Column("bracket_status", sa.String(20), nullable=False),
        sa.Column("bracket_type", sa.String(30), nullable=True),
        sa.Column("slot_size", sa.String(10), nullable=True),
        sa.Column("wire_type", sa.String(50), nullable=True),
        sa.Column(
            "band",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.CheckConstraint(
            "bracket_status IN ('pending','bonded','removed','not_applicable')",
            name="chk_ortho_bonding_teeth_bracket_status",
        ),
        sa.CheckConstraint(
            "bracket_type IS NULL OR bracket_type IN ('metalico','ceramico','autoligado','lingual')",
            name="chk_ortho_bonding_teeth_bracket_type",
        ),
        sa.UniqueConstraint(
            "record_id",
            "tooth_number",
            name="uq_ortho_bonding_teeth_record_tooth",
        ),
    )
    op.create_index(
        "idx_ortho_bonding_teeth_record",
        "ortho_bonding_teeth",
        ["record_id"],
    )

    # ── 4. ortho_visits (adjustment visits within a case) ─────────────────
    op.create_table(
        "ortho_visits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "ortho_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ortho_cases.id"),
            nullable=False,
        ),
        sa.Column("visit_number", sa.Integer, nullable=False),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("visit_date", sa.Date, nullable=False),
        sa.Column("wire_upper", sa.String(50), nullable=True),
        sa.Column("wire_lower", sa.String(50), nullable=True),
        sa.Column("elastics", sa.String(200), nullable=True),
        sa.Column("adjustments", sa.Text, nullable=True),
        sa.Column("next_visit_date", sa.Date, nullable=True),
        sa.Column(
            "payment_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "payment_amount",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "payment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payments.id"),
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
            "payment_status IN ('pending','paid','waived')",
            name="chk_ortho_visits_payment_status",
        ),
        sa.UniqueConstraint(
            "ortho_case_id",
            "visit_number",
            name="uq_ortho_visits_case_visit_number",
        ),
    )
    op.create_index("idx_ortho_visits_case", "ortho_visits", ["ortho_case_id"])

    # ── 5. ortho_case_materials (inventory consumption per case/visit) ────
    op.create_table(
        "ortho_case_materials",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "ortho_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ortho_cases.id"),
            nullable=False,
        ),
        sa.Column(
            "visit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ortho_visits.id"),
            nullable=True,
        ),
        sa.Column(
            "inventory_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory_items.id"),
            nullable=False,
        ),
        sa.Column("quantity_used", sa.Numeric, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity_used > 0",
            name="chk_ortho_case_materials_quantity_used",
        ),
    )
    op.create_index(
        "idx_ortho_case_materials_case",
        "ortho_case_materials",
        ["ortho_case_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_ortho_case_materials_case", table_name="ortho_case_materials")
    op.drop_table("ortho_case_materials")

    op.drop_index("idx_ortho_visits_case", table_name="ortho_visits")
    op.drop_table("ortho_visits")

    op.drop_index("idx_ortho_bonding_teeth_record", table_name="ortho_bonding_teeth")
    op.drop_table("ortho_bonding_teeth")

    op.drop_index(
        "idx_ortho_bonding_records_case", table_name="ortho_bonding_records"
    )
    op.drop_table("ortho_bonding_records")

    op.drop_index("idx_ortho_cases_status", table_name="ortho_cases")
    op.drop_index("idx_ortho_cases_doctor", table_name="ortho_cases")
    op.drop_index("idx_ortho_cases_patient", table_name="ortho_cases")
    op.drop_table("ortho_cases")
