"""Tooth photo model — lives in each tenant schema.

One table:
  - ToothPhoto: a photo of a specific tooth, stored in S3.
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


class ToothPhoto(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A photo of a specific tooth for a patient.

    Photos are stored in S3 with tenant-scoped paths:
    /{tenant_id}/{patient_id}/teeth/{tooth_number}/{uuid}.jpg

    Thumbnails are stored alongside the original:
    /{tenant_id}/{patient_id}/teeth/{tooth_number}/{uuid}_thumb.jpg

    Max 20 photos per tooth. HEIC files are converted to JPEG on upload.
    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "tooth_photos"
    __table_args__ = (
        Index("idx_tooth_photos_patient", "patient_id"),
        Index("idx_tooth_photos_tooth", "patient_id", "tooth_number"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Tooth reference (FDI notation)
    tooth_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # S3 storage
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # File metadata
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)

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
            f"<ToothPhoto patient={self.patient_id} "
            f"tooth={self.tooth_number}>"
        )
