"""Financing application models -- VP-11 / Sprint 29-30.

Two tables:
  - FinancingApplication: tracks a patient's BNPL financing request with a provider
    (Addi, Sistecrédito, or Mercado Pago).
  - FinancingPayment: individual installment payment tracking for a financing application.

Clinical data is NEVER hard-deleted (regulatory requirement).
All monetary values in COP cents.
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
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class FinancingApplication(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A patient financing application with an external BNPL provider.

    Status lifecycle: requested → pending → approved → disbursed → completed
                                          └─ rejected (terminal)
                                          └─ cancelled (terminal)

    provider: addi | sistecredito | mercadopago
    All monetary values in COP cents.
    """

    __tablename__ = "financing_applications"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('addi', 'sistecredito', 'mercadopago')",
            name="chk_financing_applications_provider",
        ),
        CheckConstraint(
            "status IN ('requested', 'pending', 'approved', 'disbursed', 'rejected', 'cancelled', 'completed')",
            name="chk_financing_applications_status",
        ),
        CheckConstraint(
            "amount_cents > 0",
            name="chk_financing_applications_amount_positive",
        ),
        CheckConstraint(
            "installments > 0",
            name="chk_financing_applications_installments_positive",
        ),
        Index("idx_financing_applications_patient", "patient_id"),
        Index("idx_financing_applications_invoice", "invoice_id"),
        Index("idx_financing_applications_status", "status"),
        Index("idx_financing_applications_provider_ref", "provider", "provider_reference"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Optional link to the invoice being financed
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Provider and external tracking
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'requested'"),
    )
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Financing terms
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    installments: Mapped[int] = mapped_column(Integer, nullable=False)
    interest_rate_bps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Annual interest rate in basis points (100 bps = 1%)",
    )

    # Timeline
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    disbursed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<FinancingApplication provider={self.provider} "
            f"status={self.status} patient={self.patient_id}>"
        )


class FinancingPayment(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single installment payment within a financing application.

    Tracks each monthly installment, its due date, paid status, and amount.
    Used for displaying the repayment schedule to clinic staff and patients.
    """

    __tablename__ = "financing_payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'overdue', 'waived')",
            name="chk_financing_payments_status",
        ),
        CheckConstraint(
            "amount_cents > 0",
            name="chk_financing_payments_amount_positive",
        ),
        CheckConstraint(
            "installment_number > 0",
            name="chk_financing_payments_installment_positive",
        ),
        Index("idx_financing_payments_application", "application_id"),
        Index("idx_financing_payments_due_date", "due_date"),
    )

    # Parent application
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financing_applications.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Installment details
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Payment tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<FinancingPayment application={self.application_id} "
            f"installment={self.installment_number} status={self.status}>"
        )
