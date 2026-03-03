"""Add Sprint 25-26 tables: reputation, loyalty, periodontal, convenios, families + multi-currency columns.

Revision ID: 012_sprint25_reputation
Revises: 011_sprint23_growth
Create Date: 2026-03-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "012_sprint25_reputation"
down_revision: Union[str, None] = "011_sprint23_growth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ALTER invoices: add multi-currency columns ─────────────────────────
    op.add_column(
        "invoices",
        sa.Column(
            "currency_code",
            sa.String(length=3),
            nullable=False,
            server_default=sa.text("'COP'"),
        ),
    )
    op.create_check_constraint(
        "chk_invoices_currency_code",
        "invoices",
        "currency_code IN ('COP', 'USD', 'EUR', 'MXN')",
    )
    op.add_column(
        "invoices",
        sa.Column("exchange_rate", sa.Numeric(precision=12, scale=6), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("exchange_rate_date", sa.Date(), nullable=True),
    )

    # ── ALTER service_catalog: add multi-currency pricing ──────────────────
    op.add_column(
        "service_catalog",
        sa.Column("prices_multi_currency", postgresql.JSONB(), nullable=True),
    )

    # ── satisfaction_surveys ───────────────────────────────────────────────
    op.create_table(
        "satisfaction_surveys",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("channel_sent", sa.String(length=20), nullable=True),
        sa.Column("survey_token", sa.String(length=64), nullable=False),
        sa.Column("routed_to", sa.String(length=20), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("score >= 1 AND score <= 5", name="chk_satisfaction_surveys_score"),
        sa.CheckConstraint(
            "channel_sent IN ('whatsapp', 'sms', 'email')",
            name="chk_satisfaction_surveys_channel",
        ),
        sa.CheckConstraint(
            "routed_to IN ('google_review', 'private_feedback')",
            name="chk_satisfaction_surveys_routed_to",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("survey_token", name="uq_satisfaction_surveys_token"),
    )
    op.create_index("idx_satisfaction_surveys_patient", "satisfaction_surveys", ["patient_id"])
    op.create_index("idx_satisfaction_surveys_token", "satisfaction_surveys", ["survey_token"])
    op.create_index("idx_satisfaction_surveys_appointment", "satisfaction_surveys", ["appointment_id"])

    # ── loyalty_points ─────────────────────────────────────────────────────
    op.create_table(
        "loyalty_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("points_balance", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("lifetime_points_earned", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("lifetime_points_redeemed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("points_balance >= 0", name="chk_loyalty_points_balance"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", name="uq_loyalty_points_patient"),
    )
    op.create_index("idx_loyalty_points_patient", "loyalty_points", ["patient_id"])

    # ── loyalty_transactions (append-only, no TimestampMixin) ──────────────
    op.create_table(
        "loyalty_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(length=30), nullable=True),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "type IN ('earned', 'redeemed', 'expired', 'adjusted')",
            name="chk_loyalty_transactions_type",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_loyalty_transactions_patient", "loyalty_transactions", ["patient_id"])
    op.create_index("idx_loyalty_transactions_type", "loyalty_transactions", ["type"])
    op.create_index("idx_loyalty_transactions_created_at", "loyalty_transactions", ["created_at"])

    # ── periodontal_records ────────────────────────────────────────────────
    op.create_table(
        "periodontal_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dentition_type", sa.String(length=20), nullable=False, server_default=sa.text("'adult'")),
        sa.Column("source", sa.String(length=20), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "dentition_type IN ('adult', 'pediatric', 'mixed')",
            name="chk_periodontal_records_dentition",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'voice')",
            name="chk_periodontal_records_source",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_periodontal_records_patient", "periodontal_records", ["patient_id"])
    op.create_index("idx_periodontal_records_recorded_by", "periodontal_records", ["recorded_by"])

    # ── periodontal_measurements (no TimestampMixin — high-volume data) ───
    op.create_table(
        "periodontal_measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tooth_number", sa.Integer(), nullable=False),
        sa.Column("site", sa.String(length=20), nullable=False),
        sa.Column("pocket_depth", sa.SmallInteger(), nullable=True),
        sa.Column("recession", sa.SmallInteger(), nullable=True),
        sa.Column("clinical_attachment_level", sa.SmallInteger(), nullable=True),
        sa.Column("bleeding_on_probing", sa.Boolean(), nullable=True),
        sa.Column("plaque_index", sa.Boolean(), nullable=True),
        sa.Column("mobility", sa.SmallInteger(), nullable=True),
        sa.Column("furcation", sa.SmallInteger(), nullable=True),
        sa.CheckConstraint(
            "site IN ('mesial_buccal', 'buccal', 'distal_buccal', "
            "'mesial_lingual', 'lingual', 'distal_lingual')",
            name="chk_periodontal_measurements_site",
        ),
        sa.CheckConstraint("mobility >= 0 AND mobility <= 3", name="chk_periodontal_measurements_mobility"),
        sa.CheckConstraint("furcation >= 0 AND furcation <= 3", name="chk_periodontal_measurements_furcation"),
        sa.ForeignKeyConstraint(["record_id"], ["periodontal_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", "tooth_number", "site", name="uq_periodontal_measurements_record_tooth_site"),
    )
    op.create_index("idx_periodontal_measurements_record", "periodontal_measurements", ["record_id"])

    # ── convenios ──────────────────────────────────────────────────────────
    op.create_table(
        "convenios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("contact_info", postgresql.JSONB(), nullable=True),
        sa.Column("discount_rules", postgresql.JSONB(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_convenios_active", "convenios", ["is_active"])

    # ── convenio_patients ──────────────────────────────────────────────────
    op.create_table(
        "convenio_patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("convenio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["convenio_id"], ["convenios.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("convenio_id", "patient_id", name="uq_convenio_patients_convenio_patient"),
    )
    op.create_index("idx_convenio_patients_convenio", "convenio_patients", ["convenio_id"])
    op.create_index("idx_convenio_patients_patient", "convenio_patients", ["patient_id"])

    # ── family_groups ──────────────────────────────────────────────────────
    op.create_table(
        "family_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("primary_contact_patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["primary_contact_patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_family_groups_primary_contact", "family_groups", ["primary_contact_patient_id"])

    # ── family_members ─────────────────────────────────────────────────────
    op.create_table(
        "family_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint(
            "relationship IN ('parent', 'child', 'spouse', 'sibling', 'other')",
            name="chk_family_members_relationship",
        ),
        sa.ForeignKeyConstraint(["family_group_id"], ["family_groups.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", name="uq_family_members_patient"),
    )
    op.create_index("idx_family_members_group", "family_members", ["family_group_id"])
    op.create_index("idx_family_members_patient", "family_members", ["patient_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("idx_family_members_patient", table_name="family_members")
    op.drop_index("idx_family_members_group", table_name="family_members")
    op.drop_table("family_members")

    op.drop_index("idx_family_groups_primary_contact", table_name="family_groups")
    op.drop_table("family_groups")

    op.drop_index("idx_convenio_patients_patient", table_name="convenio_patients")
    op.drop_index("idx_convenio_patients_convenio", table_name="convenio_patients")
    op.drop_table("convenio_patients")

    op.drop_index("idx_convenios_active", table_name="convenios")
    op.drop_table("convenios")

    op.drop_index("idx_periodontal_measurements_record", table_name="periodontal_measurements")
    op.drop_table("periodontal_measurements")

    op.drop_index("idx_periodontal_records_recorded_by", table_name="periodontal_records")
    op.drop_index("idx_periodontal_records_patient", table_name="periodontal_records")
    op.drop_table("periodontal_records")

    op.drop_index("idx_loyalty_transactions_created_at", table_name="loyalty_transactions")
    op.drop_index("idx_loyalty_transactions_type", table_name="loyalty_transactions")
    op.drop_index("idx_loyalty_transactions_patient", table_name="loyalty_transactions")
    op.drop_table("loyalty_transactions")

    op.drop_index("idx_loyalty_points_patient", table_name="loyalty_points")
    op.drop_table("loyalty_points")

    op.drop_index("idx_satisfaction_surveys_appointment", table_name="satisfaction_surveys")
    op.drop_index("idx_satisfaction_surveys_token", table_name="satisfaction_surveys")
    op.drop_index("idx_satisfaction_surveys_patient", table_name="satisfaction_surveys")
    op.drop_table("satisfaction_surveys")

    op.drop_column("service_catalog", "prices_multi_currency")

    op.drop_column("invoices", "exchange_rate_date")
    op.drop_column("invoices", "exchange_rate")
    op.drop_constraint("chk_invoices_currency_code", "invoices", type_="check")
    op.drop_column("invoices", "currency_code")
