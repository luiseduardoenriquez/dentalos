"""Add superadmin, admin sessions, and feature flags tables

Revision ID: 003_admin_tables
Revises: 002_add_catalogs
Create Date: 2026-02-26 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "003_admin_tables"
down_revision: Union[str, None] = "002_add_catalogs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── superadmins ──────────────────────────────────────────────────────
    op.create_table(
        "superadmins",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("totp_secret", sa.String(100), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ip_allowlist", JSONB(), nullable=False, server_default="[]"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index("idx_superadmins_email", "superadmins", ["email"], schema="public")

    # ── admin_sessions ───────────────────────────────────────────────────
    op.create_table(
        "admin_sessions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("public.superadmins.id"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )
    op.create_index("idx_admin_sessions_admin", "admin_sessions", ["admin_id"], schema="public")
    op.create_index("idx_admin_sessions_expires", "admin_sessions", ["expires_at"], schema="public")

    # ── feature_flags ────────────────────────────────────────────────────
    op.create_table(
        "feature_flags",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("flag_name", sa.String(100), nullable=False, unique=True),
        sa.Column("scope", sa.String(20), nullable=True),
        sa.Column("plan_filter", sa.String(50), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index("idx_feature_flags_name", "feature_flags", ["flag_name"], schema="public")
    op.create_index("idx_feature_flags_tenant", "feature_flags", ["tenant_id"], schema="public")


def downgrade() -> None:
    op.drop_table("feature_flags", schema="public")
    op.drop_table("admin_sessions", schema="public")
    op.drop_table("superadmins", schema="public")
