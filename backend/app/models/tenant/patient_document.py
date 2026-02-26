"""Patient document model — lives in each tenant schema.

One table:
  - PatientDocument: a document belonging to a patient, stored in S3.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class PatientDocument(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A document belonging to a patient, stored in S3.

    Documents are stored in S3 with tenant-scoped paths:
    /{tenant_id}/{patient_id}/documents/{document_type}/{uuid}.{ext}

    Supported document types: xray, consent, lab_result, referral, photo, other.
    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "patient_documents"
    __table_args__ = (
        Index("idx_patient_documents_patient", "patient_id"),
        Index("idx_patient_documents_type", "patient_id", "document_type"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Document classification
    document_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # File metadata
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional fields
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tooth_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Who uploaded
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<PatientDocument patient={self.patient_id} "
            f"type={self.document_type} file={self.file_name!r}>"
        )
