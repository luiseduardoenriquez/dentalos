"""Add treatment_plan_item_id and doctor_id to invoice_items.

Links invoice line items directly to treatment plan items for:
  - Per-concept billing (ortodoncia vs limpieza)
  - Doctor-level commission tracking
  - Auto-populating invoices from active treatment plans

Revision ID: 023_invoice_item_treatment_link
Revises: 022_ai_usage_logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023_invoice_item_treatment_link"
down_revision = "022_ai_usage_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoice_items",
        sa.Column(
            "treatment_plan_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("treatment_plan_items.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "invoice_items",
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_invoice_items_treatment",
        "invoice_items",
        ["treatment_plan_item_id"],
    )
    op.create_index(
        "idx_invoice_items_doctor",
        "invoice_items",
        ["doctor_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_invoice_items_doctor", table_name="invoice_items")
    op.drop_index("idx_invoice_items_treatment", table_name="invoice_items")
    op.drop_column("invoice_items", "doctor_id")
    op.drop_column("invoice_items", "treatment_plan_item_id")
