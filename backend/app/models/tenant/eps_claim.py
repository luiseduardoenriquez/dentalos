"""EPS claims management model -- VP-19 / Sprint 31-32.

Tracks dental procedure claims submitted to EPS (Entidades Promotoras de Salud)
insurers in the Colombian healthcare system.

Lifecycle: draft → submitted → acknowledged → paid
                          └─ rejected (terminal)
                          └─ appealed (from rejected)

All monetary values in COP cents.
Clinical data is NEVER hard-deleted (regulatory requirement).
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class EPSClaim(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An EPS insurance claim for dental procedures rendered to a patient.

    Status lifecycle: draft → submitted → acknowledged → paid
                                    └─ rejected (terminal)
                                    └─ appealed (from rejected)

    claim_type: outpatient | emergency | hospitalization | dental
    All monetary values in COP cents.
    """

    __tablename__ = "eps_claims"
    __table_args__ = (
        CheckConstraint(
            "claim_type IN ('outpatient', 'emergency', 'hospitalization', 'dental')",
            name="chk_eps_claims_claim_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'acknowledged', 'paid', 'rejected', 'appealed')",
            name="chk_eps_claims_status",
        ),
        Index("idx_eps_claims_patient", "patient_id"),
        Index("idx_eps_claims_status", "status"),
        Index("idx_eps_claims_submitted_at", "submitted_at"),
    )

    # Ownership — cascade so claim is removed if patient is hard-deleted
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # EPS insurer identification
    eps_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Official EPS code as registered with ADRES (e.g. EPS010)",
    )
    eps_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable EPS name (e.g. EPS Sura)",
    )

    # Claim type classification
    claim_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Type of claim: outpatient | emergency | hospitalization | dental",
    )

    # Procedure line items — stored as JSONB array
    # Each element: {"cups_code": "...", "description": "...", "quantity": 1,
    #                "unit_price_cents": 50000, "tooth_fdi": "11" (optional)}
    procedures: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        comment="Array of procedure line items with CUPS codes and amounts",
    )

    # Monetary values — always in COP cents
    total_amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total claim value in COP cents",
    )
    copay_amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="Patient copay (cuota moderadora) in COP cents",
    )

    # Claim status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'draft'"),
        comment="Current claim status in the lifecycle",
    )

    # External tracking — set after successful submission to EPS portal
    external_claim_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Claim identifier assigned by the EPS system after submission",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error detail from EPS when status=rejected",
    )

    # Timeline
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp when the claim was submitted to the EPS",
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp when the EPS acknowledged receipt of the claim",
    )
    response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp of the last status update received from the EPS",
    )

    # Audit — who created the claim (SET NULL on user deletion to preserve claim)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this claim draft",
    )

    # Soft delete — regulatory requirement, clinical data never hard-deleted
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<EPSClaim eps={self.eps_code} "
            f"type={self.claim_type} status={self.status} "
            f"patient={self.patient_id}>"
        )
