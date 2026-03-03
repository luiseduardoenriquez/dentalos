"""Periodontal charting models -- live in each tenant schema.

Two tables:
  - PeriodontalRecord:      one per charting session (soft-deletable)
  - PeriodontalMeasurement: individual site measurements per tooth (high-volume)
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
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin

# ─── Valid values ────────────────────────────────────────────────────────────

_VALID_SITES = (
    "'mesial_buccal','buccal','distal_buccal',"
    "'mesial_lingual','lingual','distal_lingual'"
)
_VALID_DENTITION_TYPES = "'adult','pediatric','mixed'"
_VALID_SOURCES = "'manual','voice'"


class PeriodontalRecord(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single periodontal charting session for a patient.

    Each record captures one full or partial charting session.  The record
    owns a collection of PeriodontalMeasurement rows -- one per (tooth, site)
    pair that was probed during the session.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    Use is_active=False + deleted_at for soft delete.
    """

    __tablename__ = "periodontal_records"
    __table_args__ = (
        CheckConstraint(
            f"dentition_type IN ({_VALID_DENTITION_TYPES})",
            name="chk_periodontal_records_dentition_type",
        ),
        CheckConstraint(
            f"source IN ({_VALID_SOURCES})",
            name="chk_periodontal_records_source",
        ),
        Index("idx_periodontal_records_patient", "patient_id"),
        Index("idx_periodontal_records_created", "created_at"),
    )

    # Owner
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Recorder
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Settings
    dentition_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="adult",
        server_default="adult",
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    measurements: Mapped[list["PeriodontalMeasurement"]] = relationship(
        back_populates="record",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<PeriodontalRecord patient={self.patient_id} "
            f"dentition={self.dentition_type} source={self.source}>"
        )


class PeriodontalMeasurement(UUIDPrimaryKeyMixin, TenantBase):
    """A single periodontal measurement at one site of one tooth.

    High-volume table: up to 192 rows per record (32 teeth x 6 sites).
    TimestampMixin is NOT used -- only created_at is stored, no updated_at,
    to minimize write overhead on bulk inserts.

    Measurements are immutable once written.  To re-chart, create a new
    PeriodontalRecord with fresh measurements.
    """

    __tablename__ = "periodontal_measurements"
    __table_args__ = (
        UniqueConstraint(
            "record_id",
            "tooth_number",
            "site",
            name="uq_periodontal_measurements_record_tooth_site",
        ),
        CheckConstraint(
            f"site IN ({_VALID_SITES})",
            name="chk_periodontal_measurements_site",
        ),
        CheckConstraint(
            "mobility IS NULL OR (mobility >= 0 AND mobility <= 3)",
            name="chk_periodontal_measurements_mobility",
        ),
        CheckConstraint(
            "furcation IS NULL OR (furcation >= 0 AND furcation <= 3)",
            name="chk_periodontal_measurements_furcation",
        ),
        Index("idx_periodontal_measurements_record", "record_id"),
    )

    # Parent record
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("periodontal_records.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Tooth location
    tooth_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Measurement site (one of 6 periodontal sites per tooth)
    site: Mapped[str] = mapped_column(String(20), nullable=False)

    # Probing measurements
    pocket_depth: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    recession: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    clinical_attachment_level: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )

    # Clinical indicators
    bleeding_on_probing: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    plaque_index: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Mobility and furcation
    mobility: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    furcation: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Timestamp -- manual, not mixin (no updated_at needed for immutable rows)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    record: Mapped["PeriodontalRecord"] = relationship(back_populates="measurements")

    def __repr__(self) -> str:
        return (
            f"<PeriodontalMeasurement record={self.record_id} "
            f"tooth={self.tooth_number} site={self.site}>"
        )
