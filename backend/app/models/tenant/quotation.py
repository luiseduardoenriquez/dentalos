"""Quotation models — live in each tenant schema.

Two tables:
  - Quotation: a price quote for a patient, optionally linked to a treatment plan.
  - QuotationItem: individual line item within a quotation.
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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class Quotation(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A price quotation for a patient.

    Sequential quotation_number per tenant (COT-{YYYY}-{NNNNN}).
    Status transitions: draft → sent → approved | rejected | expired.
    All monetary values in cents (COP).

    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "quotations"
    __table_args__ = (
        UniqueConstraint("quotation_number", name="uq_quotations_number"),
        CheckConstraint(
            "status IN ('draft', 'sent', 'approved', 'rejected', 'expired')",
            name="chk_quotations_status",
        ),
        Index("idx_quotations_patient", "patient_id"),
        Index("idx_quotations_status", "status"),
        Index("idx_quotations_created_at", "created_at"),
    )

    # Sequential number
    quotation_number: Mapped[str] = mapped_column(String(20), nullable=False)

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

    # Optional treatment plan link
    treatment_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treatment_plans.id"),
        nullable=True,
    )

    # Totals — always cents (COP)
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Validity
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Approval signature
    signature_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Stub for future invoice link (Sprint 11-12)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    items: Mapped[list["QuotationItem"]] = relationship(
        back_populates="quotation",
        lazy="selectin",
        order_by="QuotationItem.sort_order",
    )

    def __repr__(self) -> str:
        return (
            f"<Quotation number={self.quotation_number} "
            f"patient={self.patient_id} status={self.status}>"
        )


class QuotationItem(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single line item within a quotation.

    Links to a service catalog entry. Prices in cents (COP).
    """

    __tablename__ = "quotation_items"
    __table_args__ = (
        Index("idx_quotation_items_quotation", "quotation_id"),
    )

    # Parent quotation
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id"),
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

    # Treatment plan item link — preserves lineage from plan → quotation → invoice
    treatment_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treatment_plan_items.id"),
        nullable=True,
    )

    # Relationships
    quotation: Mapped["Quotation"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return (
            f"<QuotationItem quotation={self.quotation_id} "
            f"desc={self.description!r} total={self.line_total}>"
        )
