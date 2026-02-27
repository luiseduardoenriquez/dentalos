"""Patient model — lives in each tenant schema."""

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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class Patient(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Patient demographic and administrative record.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    Use is_active=False + deleted_at for soft delete.
    """

    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("document_type", "document_number", name="uq_patients_document"),
        CheckConstraint(
            "document_type IN ('CC', 'CE', 'PA', 'PEP', 'TI')",
            name="chk_patients_document_type",
        ),
        CheckConstraint(
            "gender IS NULL OR gender IN ('male', 'female', 'other')",
            name="chk_patients_gender",
        ),
        Index("idx_patients_document", func.lower("document_type"), func.lower("document_number")),
        Index("idx_patients_email", "email"),
        Index("idx_patients_is_active", "is_active"),
        Index("idx_patients_created_at", "created_at"),
        Index(
            "idx_patients_fts",
            text(
                "to_tsvector('spanish',"
                " coalesce(first_name,'') || ' ' ||"
                " coalesce(last_name,'') || ' ' ||"
                " coalesce(document_number,''))"
            ),
            postgresql_using="gin",
        ),
    )

    # Identity
    document_type: Mapped[str] = mapped_column(String(10), nullable=False)
    document_number: Mapped[str] = mapped_column(String(30), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_province: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Emergency contact
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Insurance
    insurance_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    insurance_policy_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Clinical
    blood_type: Mapped[str | None] = mapped_column(String(5), nullable=True)
    allergies: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    chronic_conditions: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # Metadata
    referral_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status — soft delete only (clinical data is never hard-deleted)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Counters
    no_show_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Portal
    portal_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # FK — who created this patient record
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Patient {self.first_name} {self.last_name} ({self.document_type}:{self.document_number})>"
