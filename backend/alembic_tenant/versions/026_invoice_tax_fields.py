"""Add include_tax and tax_rate columns to invoices.

Revision ID: 026
Revises: 025_invoice_item_ortho_link
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "026"
down_revision = "025_invoice_item_ortho_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("include_tax", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "invoices",
        sa.Column("tax_rate", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("invoices", "tax_rate")
    op.drop_column("invoices", "include_tax")
