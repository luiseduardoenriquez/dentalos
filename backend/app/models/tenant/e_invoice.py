"""DIAN electronic invoice models — live in each tenant schema.

Two tables:
  - EInvoice: tracks the lifecycle of an electronic invoice submission
  - TenantEInvoiceConfig: per-tenant DIAN configuration (NIT, resolution, cert)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class EInvoice(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An electronic invoice submitted to DIAN via MATIAS.

    Status transitions: pending -> submitted -> accepted / rejected / error.
    """

    __tablename__ = "e_invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'submitted', 'accepted', 'rejected', 'error')",
            name="chk_e_invoices_status",
        ),
        Index("idx_e_invoices_invoice", "invoice_id"),
        Index("idx_e_invoices_status", "status"),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    cufe: Mapped[str | None] = mapped_column(String(128), nullable=True)
    matias_submission_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dian_environment: Mapped[str] = mapped_column(String(20), nullable=False, default="test")
    xml_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<EInvoice invoice={self.invoice_id} "
            f"status={self.status} cufe={self.cufe}>"
        )


class TenantEInvoiceConfig(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Per-tenant DIAN e-invoicing configuration.

    Stores the clinic's NIT, DIAN resolution details, and certificate
    path for X.509 signing. One active config per tenant.
    """

    __tablename__ = "tenant_einvoice_configs"

    nit: Mapped[str] = mapped_column(String(20), nullable=False)
    nit_dv: Mapped[str | None] = mapped_column(String(1), nullable=True)
    resolution_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    resolution_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    range_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    range_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    certificate_s3_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dian_environment: Mapped[str] = mapped_column(String(20), nullable=False, default="test")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"<TenantEInvoiceConfig nit={self.nit} "
            f"env={self.dian_environment} active={self.is_active}>"
        )
