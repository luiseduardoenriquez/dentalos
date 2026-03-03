"""Payment model — lives in each tenant schema.

Payments are immutable for financial audit compliance.
No update or delete operations are supported.
If a payment was recorded in error, create a negative adjustment payment.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A payment recorded against an invoice.

    Payments are IMMUTABLE — once created they cannot be updated or deleted.
    This is a financial audit trail requirement. All amounts in cents (COP).
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "payment_method IN ('cash', 'card', 'transfer', 'other')",
            name="chk_payments_method",
        ),
        Index("idx_payments_invoice", "invoice_id"),
        Index("idx_payments_patient", "patient_id"),
        Index("idx_payments_date", "payment_date"),
    )

    # Invoice link
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=False,
    )

    # Patient link (denormalized for faster queries)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Amount — in cents of the specified currency, must be > 0 (enforced at service level)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    # ISO 4217 currency code for this payment (default COP)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="COP"
    )

    # Payment method
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)

    # External reference (bank transaction ID, card authorization, etc.)
    reference_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # Who received the payment
    received_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Payment date (when the payment was actually made)
    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<Payment invoice={self.invoice_id} "
            f"amount={self.amount} method={self.payment_method}>"
        )
