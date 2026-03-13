"""Add ortho_case_id and ortho_visit_id to invoice_items.

Links invoice line items to orthodontic cases and visits for:
  - Initial payment billing (ortho_case_id without ortho_visit_id)
  - Monthly control billing (ortho_visit_id tied to a specific visit)

Revision ID: 025_invoice_item_ortho_link
Revises: 024_quot_item_tp_link
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "025_invoice_item_ortho_link"
down_revision = "024_quot_item_tp_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoice_items",
        sa.Column(
            "ortho_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ortho_cases.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "invoice_items",
        sa.Column(
            "ortho_visit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ortho_visits.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_invoice_items_ortho_case",
        "invoice_items",
        ["ortho_case_id"],
    )
    op.create_index(
        "idx_invoice_items_ortho_visit",
        "invoice_items",
        ["ortho_visit_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_invoice_items_ortho_visit", table_name="invoice_items")
    op.drop_index("idx_invoice_items_ortho_case", table_name="invoice_items")
    op.drop_column("invoice_items", "ortho_visit_id")
    op.drop_column("invoice_items", "ortho_case_id")
