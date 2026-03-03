"""Invoice models — live in each tenant schema.

Two tables:
  - Invoice: a financial document for a patient, optionally linked to a quotation.
  - InvoiceItem: individual line item within an invoice.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A financial invoice for a patient.

    Sequential invoice_number per tenant (FAC-{YYYY}-{NNNNN}).
    Status transitions: draft -> sent -> partial/paid/overdue/cancelled.
    All monetary values in cents (COP).

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_invoices_number"),
        CheckConstraint(
            "status IN ('draft', 'sent', 'partial', 'paid', 'overdue', 'cancelled')",
            name="chk_invoices_status",
        ),
        Index("idx_invoices_patient", "patient_id"),
        Index("idx_invoices_status", "status"),
        Index("idx_invoices_created_at", "created_at"),
    )

    # Sequential number
    invoice_number: Mapped[str] = mapped_column(String(20), nullable=False)

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Optional quotation link
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id"),
        nullable=True,
    )

    # Totals — always cents (COP)
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amount_paid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Due date and payment tracking
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Multi-currency (Sprint 25-26)
    currency_code: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="COP"
    )
    exchange_rate: Mapped[float | None] = mapped_column(
        Numeric(precision=12, scale=6), nullable=True
    )
    exchange_rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice",
        lazy="selectin",
        order_by="InvoiceItem.sort_order",
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice number={self.invoice_number} "
            f"patient={self.patient_id} status={self.status}>"
        )


class InvoiceItem(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single line item within an invoice.

    Links to a service catalog entry. Prices in cents (COP).
    """

    __tablename__ = "invoice_items"
    __table_args__ = (
        Index("idx_invoice_items_invoice", "invoice_id"),
    )

    # Parent invoice
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=False,
    )

    # Service reference
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_catalog.id"),
        nullable=True,
    )

    # Description (denormalized for historical reference)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    cups_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Pricing — always cents (COP)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    line_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Ordering
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Tooth reference (optional)
    tooth_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    invoice: Mapped["Invoice"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return (
            f"<InvoiceItem invoice={self.invoice_id} "
            f"desc={self.description!r} total={self.line_total}>"
        )
