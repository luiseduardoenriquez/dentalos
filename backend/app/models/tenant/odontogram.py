"""Odontogram models — live in each tenant schema.

Four tables:
  - OdontogramState:     one-per-patient current dentition settings
  - OdontogramCondition: individual tooth/zone conditions (soft-deletable)
  - OdontogramHistory:   immutable audit trail of condition changes
  - OdontogramSnapshot:  point-in-time full-state captures
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin

# ─── Valid values (mirrors odontogram_constants, but kept local for DB layer) ──

_VALID_ZONES = (
    "'mesial','distal','vestibular','lingual','palatino','oclusal','incisal','root','full'"
)
_VALID_CONDITION_CODES = (
    "'caries','restoration','extraction','absent','crown',"
    "'endodontic','implant','fracture','sealant','fluorosis',"
    "'temporary','prosthesis'"
)


class OdontogramState(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Per-patient odontogram settings (dentition type, etc.).

    There is exactly ONE OdontogramState per patient (enforced by UNIQUE on patient_id).
    Created lazily on first odontogram access.
    """

    __tablename__ = "odontogram_states"
    __table_args__ = (
        CheckConstraint(
            "dentition_type IN ('adult', 'pediatric', 'mixed')",
            name="chk_odontogram_states_dentition_type",
        ),
        Index("idx_odontogram_states_patient", "patient_id"),
    )

    # Owner
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
        unique=True,
    )

    # Settings
    dentition_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="adult",
        server_default="adult",
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<OdontogramState patient={self.patient_id} dentition={self.dentition_type}>"


class OdontogramCondition(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single condition recorded on a specific tooth zone.

    Each row = one condition on one zone of one tooth for one patient.
    Conditions are soft-deleted on removal so history remains intact.
    """

    __tablename__ = "odontogram_conditions"
    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            "tooth_number",
            "zone",
            name="uq_odontogram_conditions_tooth_zone",
        ),
        CheckConstraint(
            f"zone IN ({_VALID_ZONES})",
            name="chk_odontogram_conditions_zone",
        ),
        CheckConstraint(
            f"condition_code IN ({_VALID_CONDITION_CODES})",
            name="chk_odontogram_conditions_code",
        ),
        CheckConstraint(
            "severity IS NULL OR severity IN ('mild', 'moderate', 'severe')",
            name="chk_odontogram_conditions_severity",
        ),
        CheckConstraint(
            "source IN ('manual', 'voice')",
            name="chk_odontogram_conditions_source",
        ),
        Index("idx_odontogram_conditions_patient", "patient_id"),
        Index("idx_odontogram_conditions_tooth", "patient_id", "tooth_number"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Tooth location
    tooth_number: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Condition data
    condition_code: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance
    source: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<OdontogramCondition patient={self.patient_id} "
            f"tooth={self.tooth_number} zone={self.zone} code={self.condition_code}>"
        )


class OdontogramHistory(TenantBase):
    """Immutable audit trail of every odontogram condition change.

    This table is append-only. No updated_at, no soft delete.
    TimestampMixin is NOT used because it adds updated_at.
    """

    __tablename__ = "odontogram_history"
    __table_args__ = (
        Index("idx_odontogram_history_patient_tooth", "patient_id", "tooth_number"),
        Index("idx_odontogram_history_created", "created_at"),
    )

    # Primary key — UUID with server-side default
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )

    # Created at only — this row is immutable
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Subject
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    tooth_number: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Action
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # add/update/remove
    condition_code: Mapped[str] = mapped_column(String(30), nullable=False)

    # Diffs (nullable — add has no previous_data, remove has no new_data)
    previous_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Actor
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<OdontogramHistory patient={self.patient_id} "
            f"tooth={self.tooth_number} action={self.action}>"
        )


class OdontogramSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Full point-in-time copy of a patient's odontogram.

    Created automatically when a clinical record is signed,
    or manually by the doctor for reference.
    """

    __tablename__ = "odontogram_snapshots"
    __table_args__ = (
        Index("idx_odontogram_snapshots_patient", "patient_id"),
        Index("idx_odontogram_snapshots_created", "created_at"),
    )

    # Owner
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Snapshot payload
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dentition_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Optional links to records / treatment plans
    linked_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinical_records.id"),
        nullable=True,
    )
    linked_treatment_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Actor
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<OdontogramSnapshot patient={self.patient_id} label={self.label!r}>"
