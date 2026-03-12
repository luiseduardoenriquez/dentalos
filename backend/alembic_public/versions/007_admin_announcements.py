"""Add admin announcements table

Revision ID: 007_admin_announcements
Revises: 006_admin_audit_and_history
Create Date: 2026-03-12 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "007_admin_announcements"
down_revision: Union[str, None] = "006_admin_audit_and_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_announcements",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("announcement_type", sa.String(20), nullable=False, server_default="info"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="all"),
        sa.Column("visibility_filter", JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_dismissable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("public.superadmins.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index("idx_admin_announcements_active", "admin_announcements", ["is_active"], schema="public")
    op.create_index("idx_admin_announcements_starts_at", "admin_announcements", ["starts_at"], schema="public")


def downgrade() -> None:
    op.drop_index("idx_admin_announcements_starts_at", table_name="admin_announcements", schema="public")
    op.drop_index("idx_admin_announcements_active", table_name="admin_announcements", schema="public")
    op.drop_table("admin_announcements", schema="public")
