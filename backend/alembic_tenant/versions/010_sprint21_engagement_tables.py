"""Add Sprint 21-22 engagement tables: memberships, intake forms, recall campaigns.

Revision ID: 010_sprint21_engage
Revises: 009_must_change_pw
Create Date: 2026-03-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "010_sprint21_engage"
down_revision: Union[str, None] = "009_must_change_pw"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- membership_plans ---
    op.create_table(
        "membership_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("monthly_price_cents", sa.Integer(), nullable=False),
        sa.Column("annual_price_cents", sa.Integer(), nullable=True),
        sa.Column("benefits", postgresql.JSONB(), nullable=True),
        sa.Column("discount_percentage", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'archived')", name="chk_membership_plans_status"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_membership_plans_status", "membership_plans", ["status"])

    # --- membership_subscriptions ---
    op.create_table(
        "membership_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("next_billing_date", sa.Date(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("external_subscription_id", sa.String(length=100), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'cancelled', 'expired')",
            name="chk_membership_subscriptions_status",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["membership_plans.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_membership_subscriptions_patient", "membership_subscriptions", ["patient_id"])
    op.create_index("idx_membership_subscriptions_plan", "membership_subscriptions", ["plan_id"])
    op.create_index("idx_membership_subscriptions_status", "membership_subscriptions", ["status"])
    op.create_index("idx_membership_subscriptions_billing", "membership_subscriptions", ["next_billing_date"])

    # --- membership_usage_log ---
    op.create_table(
        "membership_usage_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("discount_applied_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["membership_subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_membership_usage_subscription", "membership_usage_log", ["subscription_id"])
    op.create_index("idx_membership_usage_used_at", "membership_usage_log", ["used_at"])

    # --- intake_form_templates ---
    op.create_table(
        "intake_form_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("fields", postgresql.JSONB(), nullable=False),
        sa.Column("consent_template_ids", postgresql.JSONB(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_intake_templates_active", "intake_form_templates", ["is_active"])
    op.create_index("idx_intake_templates_default", "intake_form_templates", ["is_default"])

    # --- intake_submissions ---
    op.create_table(
        "intake_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'reviewed', 'approved', 'rejected')",
            name="chk_intake_submissions_status",
        ),
        sa.ForeignKeyConstraint(["template_id"], ["intake_form_templates.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_intake_submissions_status", "intake_submissions", ["status"])
    op.create_index("idx_intake_submissions_appointment", "intake_submissions", ["appointment_id"])
    op.create_index("idx_intake_submissions_patient", "intake_submissions", ["patient_id"])

    # --- recall_campaigns ---
    op.create_table(
        "recall_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=True),
        sa.Column("message_templates", postgresql.JSONB(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default=sa.text("'whatsapp'")),
        sa.Column("schedule", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "type IN ('recall', 'reactivation', 'treatment_followup', 'birthday')",
            name="chk_recall_campaigns_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed')",
            name="chk_recall_campaigns_status",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_recall_campaigns_status", "recall_campaigns", ["status"])
    op.create_index("idx_recall_campaigns_type", "recall_campaigns", ["type"])

    # --- recall_campaign_recipients ---
    op.create_table(
        "recall_campaign_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("booked_appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opted_out", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'opened', 'clicked', 'booked', 'failed', 'opted_out')",
            name="chk_recall_recipients_status",
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["recall_campaigns.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_recall_recipients_campaign", "recall_campaign_recipients", ["campaign_id"])
    op.create_index("idx_recall_recipients_patient", "recall_campaign_recipients", ["patient_id"])
    op.create_index("idx_recall_recipients_status", "recall_campaign_recipients", ["status"])


def downgrade() -> None:
    op.drop_index("idx_recall_recipients_status", table_name="recall_campaign_recipients")
    op.drop_index("idx_recall_recipients_patient", table_name="recall_campaign_recipients")
    op.drop_index("idx_recall_recipients_campaign", table_name="recall_campaign_recipients")
    op.drop_table("recall_campaign_recipients")

    op.drop_index("idx_recall_campaigns_type", table_name="recall_campaigns")
    op.drop_index("idx_recall_campaigns_status", table_name="recall_campaigns")
    op.drop_table("recall_campaigns")

    op.drop_index("idx_intake_submissions_patient", table_name="intake_submissions")
    op.drop_index("idx_intake_submissions_appointment", table_name="intake_submissions")
    op.drop_index("idx_intake_submissions_status", table_name="intake_submissions")
    op.drop_table("intake_submissions")

    op.drop_index("idx_intake_templates_default", table_name="intake_form_templates")
    op.drop_index("idx_intake_templates_active", table_name="intake_form_templates")
    op.drop_table("intake_form_templates")

    op.drop_index("idx_membership_usage_used_at", table_name="membership_usage_log")
    op.drop_index("idx_membership_usage_subscription", table_name="membership_usage_log")
    op.drop_table("membership_usage_log")

    op.drop_index("idx_membership_subscriptions_billing", table_name="membership_subscriptions")
    op.drop_index("idx_membership_subscriptions_status", table_name="membership_subscriptions")
    op.drop_index("idx_membership_subscriptions_plan", table_name="membership_subscriptions")
    op.drop_index("idx_membership_subscriptions_patient", table_name="membership_subscriptions")
    op.drop_table("membership_subscriptions")

    op.drop_index("idx_membership_plans_status", table_name="membership_plans")
    op.drop_table("membership_plans")
