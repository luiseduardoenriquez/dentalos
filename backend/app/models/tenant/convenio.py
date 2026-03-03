"""Convenio (corporate agreement) models — GAP-04."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class Convenio(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A corporate agreement granting discounts to affiliated patients."""

    __tablename__ = "convenios"
    __table_args__ = (
        Index("idx_convenios_is_active", "is_active"),
        Index("idx_convenios_valid_from", "valid_from"),
    )

    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    discount_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )


class ConvenioPatient(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Association between a convenio and a patient (employee link)."""

    __tablename__ = "convenio_patients"
    __table_args__ = (
        UniqueConstraint("convenio_id", "patient_id", name="uq_convenio_patients_convenio_patient"),
        Index("idx_convenio_patients_convenio", "convenio_id"),
        Index("idx_convenio_patients_patient", "patient_id"),
    )

    convenio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("convenios.id"), nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    employee_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
