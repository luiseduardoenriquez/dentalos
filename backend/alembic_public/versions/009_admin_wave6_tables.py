"""Add Wave 6 tables: broadcast_history, alert_rules, scheduled_reports, support_threads, support_messages

Revision ID: 009_admin_wave6_tables
Revises: 008_admin_revenue_snapshots
Create Date: 2026-03-12 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# revision identifiers, used by Alembic.
revision: str = "009_admin_wave6_tables"
down_revision: Union[str, None] = "008_admin_revenue_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Broadcast History ─────────────────────────────────
    op.create_table(
        "admin_broadcast_history",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("template", sa.String(50), nullable=True),
        sa.Column("filter_plan", sa.String(100), nullable=True),
        sa.Column("filter_country", sa.String(2), nullable=True),
        sa.Column("filter_status", sa.String(20), nullable=True),
        sa.Column("recipients_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sent_by", UUID(as_uuid=True), sa.ForeignKey("superadmins.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_admin_broadcast_created_at", "admin_broadcast_history", ["created_at"])

    # ─── Alert Rules ───────────────────────────────────────
    op.create_table(
        "admin_alert_rules",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("condition", sa.String(50), nullable=False),
        sa.Column("threshold", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("superadmins.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ─── Scheduled Reports ─────────────────────────────────
    op.create_table(
        "admin_scheduled_reports",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("schedule", sa.String(20), nullable=False),
        sa.Column("recipients", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("superadmins.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ─── Support Threads ───────────────────────────────────
    op.create_table(
        "admin_support_threads",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("unread_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('open', 'closed')", name="chk_support_thread_status"),
    )
    op.create_index("idx_admin_support_threads_tenant", "admin_support_threads", ["tenant_id"])

    # ─── Support Messages ──────────────────────────────────
    op.create_table(
        "admin_support_messages",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("thread_id", UUID(as_uuid=True), sa.ForeignKey("admin_support_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("sender_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sender_name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("sender_type IN ('admin', 'clinic_owner')", name="chk_support_msg_sender_type"),
    )
    op.create_index("idx_admin_support_messages_thread", "admin_support_messages", ["thread_id"])
    op.create_index("idx_admin_support_messages_created", "admin_support_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("admin_support_messages")
    op.drop_table("admin_support_threads")
    op.drop_table("admin_scheduled_reports")
    op.drop_table("admin_alert_rules")
    op.drop_table("admin_broadcast_history")
