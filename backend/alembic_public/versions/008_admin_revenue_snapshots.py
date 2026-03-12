"""Add admin revenue snapshots table for MRR trend tracking

Revision ID: 008_admin_revenue_snapshots
Revises: 007_admin_announcements
Create Date: 2026-03-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "008_admin_revenue_snapshots"
down_revision: Union[str, None] = "007_admin_announcements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_revenue_snapshots",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("month", sa.String(7), nullable=False),  # YYYY-MM format
        sa.Column("mrr_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_tenants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("churned_tenants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_tenants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_patients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("addon_revenue_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("plan_breakdown", JSONB(), nullable=False, server_default="{}"),
        sa.Column("country_breakdown", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index(
        "idx_revenue_snapshots_month",
        "admin_revenue_snapshots",
        ["month"],
        unique=True,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("idx_revenue_snapshots_month", table_name="admin_revenue_snapshots", schema="public")
    op.drop_table("admin_revenue_snapshots", schema="public")
