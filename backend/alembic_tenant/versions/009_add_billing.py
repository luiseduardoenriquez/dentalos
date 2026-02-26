"""Add billing tables: invoices, invoice_items, payments, payment_plans, payment_plan_installments

Revision ID: 009_add_billing
Revises: 008_add_patient_documents
Create Date: 2026-02-26

Five tables for the billing module (B-01 through B-13):
  - invoices: financial documents linked to patients/quotations
  - invoice_items: line items within an invoice
  - payments: immutable payment records (financial audit trail)
  - payment_plans: installment plan headers
  - payment_plan_installments: individual installments with due dates
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "009_add_billing"
down_revision: Union[str, None] = "008_add_patient_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── invoices ─────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("invoice_number", sa.String(20), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("quotation_id", UUID(as_uuid=True), sa.ForeignKey("quotations.id"), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subtotal", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("tax", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("amount_paid", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("balance", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("invoice_number", name="uq_invoices_number"),
        sa.CheckConstraint(
            "status IN ('draft', 'sent', 'partial', 'paid', 'overdue', 'cancelled')",
            name="chk_invoices_status",
        ),
    )
    op.create_index("idx_invoices_patient", "invoices", ["patient_id"])
    op.create_index("idx_invoices_status", "invoices", ["status"])
    op.create_index("idx_invoices_created_at", "invoices", ["created_at"])

    # ── invoice_items ────────────────────────────────────────────────────────
    op.create_table(
        "invoice_items",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("service_catalog.id"), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("cups_code", sa.String(10), nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("unit_price", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("discount", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("line_total", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("tooth_number", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_invoice_items_invoice", "invoice_items", ["invoice_id"])

    # ── payments ─────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("received_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'card', 'transfer', 'other')",
            name="chk_payments_method",
        ),
    )
    op.create_index("idx_payments_invoice", "payments", ["invoice_id"])
    op.create_index("idx_payments_patient", "payments", ["patient_id"])
    op.create_index("idx_payments_date", "payments", ["payment_date"])

    # ── payment_plans ────────────────────────────────────────────────────────
    op.create_table(
        "payment_plans",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("total_amount", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("num_installments", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="chk_payment_plans_status",
        ),
    )
    op.create_index("idx_payment_plans_invoice", "payment_plans", ["invoice_id"])

    # ── payment_plan_installments ────────────────────────────────────────────
    op.create_table(
        "payment_plan_installments",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("payment_plans.id"), nullable=False),
        sa.Column("installment_number", sa.Integer, nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_id", UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('pending', 'paid', 'overdue')",
            name="chk_installments_status",
        ),
    )
    op.create_index("idx_installments_plan", "payment_plan_installments", ["plan_id"])
    op.create_index("idx_installments_due_date", "payment_plan_installments", ["due_date"])


def downgrade() -> None:
    op.drop_index("idx_installments_due_date", table_name="payment_plan_installments")
    op.drop_index("idx_installments_plan", table_name="payment_plan_installments")
    op.drop_table("payment_plan_installments")

    op.drop_index("idx_payment_plans_invoice", table_name="payment_plans")
    op.drop_table("payment_plans")

    op.drop_index("idx_payments_date", table_name="payments")
    op.drop_index("idx_payments_patient", table_name="payments")
    op.drop_index("idx_payments_invoice", table_name="payments")
    op.drop_table("payments")

    op.drop_index("idx_invoice_items_invoice", table_name="invoice_items")
    op.drop_table("invoice_items")

    op.drop_index("idx_invoices_created_at", table_name="invoices")
    op.drop_index("idx_invoices_status", table_name="invoices")
    op.drop_index("idx_invoices_patient", table_name="invoices")
    op.drop_table("invoices")
