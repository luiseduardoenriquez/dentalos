"""RIPS (Registro Individual de Prestación de Servicios) models.

Three tables:
  - RIPSBatch: a batch export for a reporting period
  - RIPSBatchFile: individual file within a batch (AF, AC, AP, etc.)
  - RIPSBatchError: validation errors/warnings found during generation
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class RIPSBatch(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A RIPS batch export for a reporting period.

    Status transitions: queued -> generating -> generated -> validated / failed.
    """

    __tablename__ = "rips_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'generating', 'generated', 'validated', 'failed')",
            name="chk_rips_batches_status",
        ),
        Index("idx_rips_batches_status", "status"),
        Index("idx_rips_batches_period", "period_start", "period_end"),
    )

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    file_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    files: Mapped[list["RIPSBatchFile"]] = relationship(
        back_populates="batch",
        lazy="selectin",
    )
    errors: Mapped[list["RIPSBatchError"]] = relationship(
        back_populates="batch",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<RIPSBatch period={self.period_start}-{self.period_end} "
            f"status={self.status}>"
        )


class RIPSBatchFile(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An individual RIPS file within a batch (AF, AC, AP, AT, AM, AN, AU)."""

    __tablename__ = "rips_batch_files"
    __table_args__ = (
        Index("idx_rips_batch_files_batch", "batch_id"),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rips_batches.id"),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(String(5), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationship
    batch: Mapped["RIPSBatch"] = relationship(back_populates="files")

    def __repr__(self) -> str:
        return (
            f"<RIPSBatchFile batch={self.batch_id} "
            f"type={self.file_type} records={self.record_count}>"
        )


class RIPSBatchError(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A validation error or warning found during RIPS generation."""

    __tablename__ = "rips_batch_errors"
    __table_args__ = (
        Index("idx_rips_batch_errors_batch", "batch_id"),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rips_batches.id"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(10), nullable=False)  # error, warning
    rule_code: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    record_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationship
    batch: Mapped["RIPSBatch"] = relationship(back_populates="errors")

    def __repr__(self) -> str:
        return (
            f"<RIPSBatchError batch={self.batch_id} "
            f"severity={self.severity} rule={self.rule_code}>"
        )
