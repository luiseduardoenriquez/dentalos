"""EPS insurance verification model — VP-06."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class EPSVerification(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """EPS insurance affiliation verification record for a patient.

    Each row captures one point-in-time ADRES BDUA lookup result.
    Multiple verifications per patient are supported; the most recent
    active record is the canonical insurance status.

    Regulatory note: records are NEVER hard-deleted (audit trail).
    """

    __tablename__ = "eps_verifications"
    __table_args__ = (
        CheckConstraint(
            "affiliation_status IN ('activo','inactivo','suspendido','retirado','no_afiliado')",
            name="chk_eps_verifications_status",
        ),
        CheckConstraint(
            "regime IN ('contributivo','subsidiado','vinculado','excepcion')",
            name="chk_eps_verifications_regime",
        ),
        Index("idx_eps_verifications_patient", "patient_id"),
    )

    # FK to the patient whose insurance was verified.
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Timestamp of when the ADRES lookup was performed (≠ created_at which is
    # when this DB row was inserted).
    verification_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # EPS details returned by ADRES.
    eps_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    eps_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    affiliation_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    regime: Mapped[str | None] = mapped_column(String(20), nullable=True)
    copay_category: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Full ADRES API response — kept for audit, never exposed in public APIs.
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<EPSVerification patient_id={self.patient_id} "
            f"status={self.affiliation_status}>"
        )
