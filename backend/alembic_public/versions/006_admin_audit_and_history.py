"""Add admin audit logs, impersonation sessions, and plan change history

Revision ID: 006_admin_audit_and_history
Revises: 005_add_consent_templates
Create Date: 2026-03-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "006_admin_audit_and_history"
down_revision: Union[str, None] = "005_add_consent_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── admin_audit_logs ──────────────────────────────────────────────
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("public.superadmins.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("details", JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index("idx_admin_audit_logs_admin_id", "admin_audit_logs", ["admin_id"], schema="public")
    op.create_index("idx_admin_audit_logs_action", "admin_audit_logs", ["action"], schema="public")
    op.create_index(
        "idx_admin_audit_logs_created_at", "admin_audit_logs",
        [sa.text("created_at DESC")], schema="public",
    )

    # ── admin_impersonation_sessions ──────────────────────────────────
    op.create_table(
        "admin_impersonation_sessions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("public.superadmins.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("public.tenants.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        schema="public",
    )
    op.create_index(
        "idx_impersonation_sessions_admin", "admin_impersonation_sessions",
        ["admin_id"], schema="public",
    )
    op.create_index(
        "idx_impersonation_sessions_active", "admin_impersonation_sessions",
        ["is_active"], schema="public",
    )

    # ── plan_change_history ───────────────────────────────────────────
    op.create_table(
        "plan_change_history",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("public.plans.id"), nullable=False),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("public.superadmins.id"), nullable=False),
        sa.Column("field_changed", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index("idx_plan_change_history_plan", "plan_change_history", ["plan_id"], schema="public")
    op.create_index("idx_plan_change_history_admin", "plan_change_history", ["admin_id"], schema="public")

    # ── Add expires_at and reason to feature_flags ────────────────────
    op.add_column("feature_flags", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True), schema="public")
    op.add_column("feature_flags", sa.Column("reason", sa.Text(), nullable=True), schema="public")

    # ── feature_flag_change_history ───────────────────────────────────
    op.create_table(
        "feature_flag_change_history",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("flag_id", UUID(as_uuid=True), sa.ForeignKey("public.feature_flags.id"), nullable=False),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("public.superadmins.id"), nullable=False),
        sa.Column("field_changed", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index("idx_ff_change_history_flag", "feature_flag_change_history", ["flag_id"], schema="public")

    # ── admin_notifications ───────────────────────────────────────────
    op.create_table(
        "admin_notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("public.superadmins.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(30), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="public",
    )
    op.create_index("idx_admin_notifications_admin_id", "admin_notifications", ["admin_id"], schema="public")
    op.create_index("idx_admin_notifications_created_at", "admin_notifications", ["created_at"], schema="public")


def downgrade() -> None:
    op.drop_index("idx_admin_notifications_created_at", table_name="admin_notifications", schema="public")
    op.drop_index("idx_admin_notifications_admin_id", table_name="admin_notifications", schema="public")
    op.drop_table("admin_notifications", schema="public")
    op.drop_table("feature_flag_change_history", schema="public")
    op.drop_column("feature_flags", "reason", schema="public")
    op.drop_column("feature_flags", "expires_at", schema="public")
    op.drop_table("plan_change_history", schema="public")
    op.drop_table("admin_impersonation_sessions", schema="public")
    op.drop_table("admin_audit_logs", schema="public")
