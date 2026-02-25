"""Digital signature models — live in each tenant schema.

Two tables:
  - DigitalSignature: polymorphic signature record for any document type
  - SignatureVerification: audit trail for signature verification attempts
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin

_DOCUMENT_TYPES = "'consent','treatment_plan','quotation','prescription'"
_SIGNER_TYPES = "'patient','doctor','clinic_owner','witness'"


class DigitalSignature(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A digital signature record for any document type.

    Polymorphic design: document_type + document_id point to the signed entity.
    UNIQUE constraint on (document_type, document_id, signer_type) ensures
    each signer role can only sign a document once.

    The canonical_payload is the deterministic hash input string.
    The signature_hash is the SHA-256 of the canonical payload.
    The signature image is stored in S3, referenced by s3_key.

    Signatures are NEVER deleted (regulatory requirement).
    """

    __tablename__ = "digital_signatures"
    __table_args__ = (
        UniqueConstraint(
            "document_type", "document_id", "signer_type",
            name="uq_digital_signatures_doc_signer",
        ),
        CheckConstraint(
            f"document_type IN ({_DOCUMENT_TYPES})",
            name="chk_digital_signatures_doc_type",
        ),
        CheckConstraint(
            f"signer_type IN ({_SIGNER_TYPES})",
            name="chk_digital_signatures_signer_type",
        ),
        Index("idx_digital_signatures_document", "document_type", "document_id"),
        Index("idx_digital_signatures_signer", "signer_id"),
    )

    # Polymorphic document reference
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Signer info
    signer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    signer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Signature image (S3)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)

    # Cryptographic integrity
    canonical_payload: Mapped[str] = mapped_column(Text, nullable=False)
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Signing context
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<DigitalSignature doc_type={self.document_type} "
            f"doc_id={self.document_id} signer={self.signer_type}>"
        )


class SignatureVerification(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Audit trail for signature verification attempts.

    Each verification recomputes the canonical hash and compares it
    to the stored signature_hash. The result is logged immutably.
    """

    __tablename__ = "signature_verifications"
    __table_args__ = (
        Index("idx_signature_verifications_signature", "signature_id"),
    )

    # Verified signature
    signature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("digital_signatures.id"),
        nullable=False,
    )

    # Verification result
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    computed_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    stored_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Who verified
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<SignatureVerification sig={self.signature_id} "
            f"valid={self.is_valid}>"
        )
