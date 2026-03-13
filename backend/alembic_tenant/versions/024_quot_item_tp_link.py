"""Add treatment_plan_item_id to quotation_items.

Preserves the link from quotation items back to the source treatment plan
item, so when an invoice is created from a quotation, the treatment plan
item reference is propagated to the invoice item.

Revision ID: 024_quot_item_tp_link
Revises: 023_inv_item_tp_link
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "024_quot_item_tp_link"
down_revision = "023_inv_item_tp_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quotation_items",
        sa.Column(
            "treatment_plan_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("treatment_plan_items.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_quotation_items_treatment",
        "quotation_items",
        ["treatment_plan_item_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_quotation_items_treatment", table_name="quotation_items")
    op.drop_column("quotation_items", "treatment_plan_item_id")
