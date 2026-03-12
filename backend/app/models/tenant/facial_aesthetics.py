"""Facial aesthetics models — live in each tenant schema.

Four tables:
  - FacialAestheticsSession:   one per injection session (soft-deletable)
  - FacialAestheticsInjection: individual injection points per session (soft-deletable)
  - FacialAestheticsHistory:   immutable audit trail of injection changes
  - FacialAestheticsSnapshot:  point-in-time full-state captures
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin

# ─── Valid values ────────────────────────────────────────────────────────────

_VALID_DIAGRAM_TYPES = "'face_front','face_lateral_left','face_lateral_right'"

_VALID_INJECTION_TYPES = (
    "'botulinum_toxin','hyaluronic_acid','calcium_hydroxylapatite',"
    "'poly_lactic_acid','prf','other'"
)

_VALID_DEPTHS = "'intradermal','subcutaneous','supraperiosteal','intramuscular'"


class FacialAestheticsSession(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single facial aesthetics injection session for a patient.

    Each session captures one visit where injections are plotted on a face diagram.
    Clinical data is NEVER hard-deleted (regulatory requirement).
    """

    __tablename__ = "facial_aesthetics_sessions"
    __table_args__ = (
        CheckConstraint(
            f"diagram_type IN ({_VALID_DIAGRAM_TYPES})",
            name="chk_facial_aesthetics_sessions_diagram_type",
        ),
        Index("idx_facial_aesthetics_sessions_patient", "patient_id"),
        Index("idx_facial_aesthetics_sessions_created", "created_at"),
    )

    # Owner
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Performing doctor
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Diagram settings
    diagram_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="face_front",
        server_default="face_front",
    )

    session_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    injections: Mapped[list["FacialAestheticsInjection"]] = relationship(
        back_populates="session",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<FacialAestheticsSession patient={self.patient_id} "
            f"date={self.session_date} diagram={self.diagram_type}>"
        )


class FacialAestheticsInjection(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single injection point recorded on a facial aesthetics session.

    Each row = one injection at one zone for one session.
    Injections are soft-deleted on removal so history remains intact.
    """

    __tablename__ = "facial_aesthetics_injections"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "zone_id",
            name="uq_facial_aesthetics_injections_session_zone",
        ),
        CheckConstraint(
            f"injection_type IN ({_VALID_INJECTION_TYPES})",
            name="chk_facial_aesthetics_injections_type",
        ),
        CheckConstraint(
            f"depth IS NULL OR depth IN ({_VALID_DEPTHS})",
            name="chk_facial_aesthetics_injections_depth",
        ),
        Index("idx_facial_aesthetics_injections_session", "session_id"),
        Index("idx_facial_aesthetics_injections_patient", "patient_id"),
    )

    # Parent session
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facial_aesthetics_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Patient (denormalized for faster queries)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Zone on the face diagram
    zone_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Injection data
    injection_type: Mapped[str] = mapped_column(String(30), nullable=False)
    product_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dose_units: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    dose_volume_ml: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    depth: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Coordinates on the SVG diagram (normalized 0–1)
    coordinates_x: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    coordinates_y: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Actor
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

    # Relationships
    session: Mapped["FacialAestheticsSession"] = relationship(
        back_populates="injections"
    )

    def __repr__(self) -> str:
        return (
            f"<FacialAestheticsInjection session={self.session_id} "
            f"zone={self.zone_id} type={self.injection_type}>"
        )


class FacialAestheticsHistory(TenantBase):
    """Immutable audit trail of every facial aesthetics injection change.

    This table is append-only. No updated_at, no soft delete.
    TimestampMixin is NOT used because it adds updated_at.
    """

    __tablename__ = "facial_aesthetics_history"
    __table_args__ = (
        Index("idx_facial_aesthetics_history_patient", "patient_id"),
        Index("idx_facial_aesthetics_history_session", "session_id"),
        Index("idx_facial_aesthetics_history_created", "created_at"),
    )

    # Primary key
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
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facial_aesthetics_sessions.id"),
        nullable=False,
    )
    zone_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Action
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # add/update/remove
    injection_type: Mapped[str] = mapped_column(String(30), nullable=False)

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
            f"<FacialAestheticsHistory patient={self.patient_id} "
            f"zone={self.zone_id} action={self.action}>"
        )


class FacialAestheticsSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Full point-in-time copy of a patient's facial aesthetics session.

    Created manually by the doctor for reference or before/after comparison.
    """

    __tablename__ = "facial_aesthetics_snapshots"
    __table_args__ = (
        Index("idx_facial_aesthetics_snapshots_patient", "patient_id"),
        Index("idx_facial_aesthetics_snapshots_created", "created_at"),
    )

    # Owner
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )

    # Optional link to a session
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facial_aesthetics_sessions.id"),
        nullable=True,
    )

    # Snapshot payload
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    diagram_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Optional link to clinical record
    linked_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinical_records.id"),
        nullable=True,
    )

    # Actor
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<FacialAestheticsSnapshot patient={self.patient_id} label={self.label!r}>"
