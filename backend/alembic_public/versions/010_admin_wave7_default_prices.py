"""Add Wave 7 table: admin_default_prices for default procedure pricing

Revision ID: 010_admin_wave7_default_prices
Revises: 009_admin_wave6_tables
Create Date: 2026-03-12 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "010_admin_wave7_default_prices"
down_revision: Union[str, None] = "009_admin_wave6_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Default Prices ─────────────────────────────────
    op.create_table(
        "admin_default_prices",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("cups_code", sa.String(10), nullable=False),
        sa.Column("cups_description", sa.String(300), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False, server_default="CO"),
        sa.Column("price_cents", sa.Integer, nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="COP"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("superadmins.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("cups_code", "country_code", name="uq_default_prices_cups_country"),
    )
    op.create_index("idx_admin_default_prices_cups", "admin_default_prices", ["cups_code"])
    op.create_index("idx_admin_default_prices_country", "admin_default_prices", ["country_code"])


def downgrade() -> None:
    op.drop_table("admin_default_prices")
