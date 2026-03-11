"""Orthodontics models -- live in each tenant schema.

Five tables:
  - OrthoCase:          main orthodontic treatment case (soft-deletable)
  - OrthoBondingRecord: a bonding session header tied to a case (soft-deletable)
  - OrthoBondingTooth:  per-tooth bracket state within a bonding record (immutable)
  - OrthoVisit:         individual adjustment visit within a case (soft-deletable)
  - OrthoCaseMaterial:  inventory items consumed during a case or visit (immutable)

Money columns (total_cost_estimated, initial_payment, monthly_payment,
payment_amount) are stored in INTEGER cents (COP).  Never use floats for money.

Clinical data is NEVER hard-deleted (regulatory requirement).
Use is_active=False + deleted_at for soft delete on the three main tables.
"""

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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin

# ─── Valid-value sets (referenced in multiple places) ────────────────────────

_VALID_STATUSES = (
    "'planning','bonding','active_treatment','retention','completed','cancelled'"
)
_VALID_ANGLE_CLASSES = "'class_i','class_ii_div1','class_ii_div2','class_iii'"
_VALID_APPLIANCE_TYPES = "'brackets','aligners','mixed'"
_VALID_BRACKET_STATUSES = "'pending','bonded','removed','not_applicable'"
_VALID_BRACKET_TYPES = "'metalico','ceramico','autoligado','lingual'"
_VALID_PAYMENT_STATUSES = "'pending','paid','waived'"


class OrthoCase(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Main orthodontic treatment case entity for a patient.

    One case per orthodontic treatment episode.  Tracks the appliance type,
    estimated duration, cost structure (estimated / initial / monthly), and
    clinical classification (Angle class, malocclusion type).

    Status flow:
        planning → bonding → active_treatment → retention → completed
        (any status) → cancelled

    Clinical data is NEVER hard-deleted (regulatory requirement).
    Use is_active=False + deleted_at for soft delete.
    """

    __tablename__ = "ortho_cases"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_VALID_STATUSES})",
            name="chk_ortho_cases_status",
        ),
        CheckConstraint(
            f"angle_class IS NULL OR angle_class IN ({_VALID_ANGLE_CLASSES})",
            name="chk_ortho_cases_angle_class",
        ),
        CheckConstraint(
            f"appliance_type IN ({_VALID_APPLIANCE_TYPES})",
            name="chk_ortho_cases_appliance_type",
        ),
        Index("idx_ortho_cases_patient", "patient_id"),
        Index("idx_ortho_cases_doctor", "doctor_id"),
        Index("idx_ortho_cases_status", "status"),
    )

    # Ownership
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    treatment_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treatment_plans.id"),
        nullable=True,
    )

    # Case identification
    case_number: Mapped[str] = mapped_column(String(20), nullable=False)

    # Clinical status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="planning",
        server_default="planning",
    )

    # Orthodontic classification
    angle_class: Mapped[str | None] = mapped_column(String(20), nullable=True)
    malocclusion_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Treatment setup
    appliance_type: Mapped[str] = mapped_column(String(30), nullable=False)
    estimated_duration_months: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # Timeline
    actual_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Financials (all in cents COP)
    total_cost_estimated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    initial_payment: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    monthly_payment: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    bonding_records: Mapped[list["OrthoBondingRecord"]] = relationship(
        back_populates="case",
        lazy="selectin",
    )
    visits: Mapped[list["OrthoVisit"]] = relationship(
        back_populates="case",
        lazy="selectin",
    )
    materials: Mapped[list["OrthoCaseMaterial"]] = relationship(
        back_populates="case",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<OrthoCase patient={self.patient_id} "
            f"case_number={self.case_number!r} status={self.status!r}>"
        )


class OrthoBondingRecord(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A bonding session header for an orthodontic case.

    One record per bonding session.  The record owns a collection of
    OrthoBondingTooth rows -- one per tooth bracket that was placed or
    updated during the session.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    Use is_active=False + deleted_at for soft delete.
    """

    __tablename__ = "ortho_bonding_records"
    __table_args__ = (Index("idx_ortho_bonding_records_case", "ortho_case_id"),)

    # Parent case
    ortho_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ortho_cases.id"),
        nullable=False,
    )

    # Recorder
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    case: Mapped["OrthoCase"] = relationship(back_populates="bonding_records")
    teeth: Mapped[list["OrthoBondingTooth"]] = relationship(
        back_populates="record",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<OrthoBondingRecord case={self.ortho_case_id} "
            f"recorded_by={self.recorded_by}>"
        )


class OrthoBondingTooth(UUIDPrimaryKeyMixin, TenantBase):
    """Per-tooth bracket state within a bonding record.

    High-volume table: up to 32 rows per bonding record (full adult dentition).
    TimestampMixin is NOT used -- these rows are immutable once written.
    To record a re-bonding, create a new OrthoBondingRecord.

    FDI tooth numbering: valid range 11-48 for adults.
    """

    __tablename__ = "ortho_bonding_teeth"
    __table_args__ = (
        UniqueConstraint(
            "record_id",
            "tooth_number",
            name="uq_ortho_bonding_teeth_record_tooth",
        ),
        CheckConstraint(
            f"bracket_status IN ({_VALID_BRACKET_STATUSES})",
            name="chk_ortho_bonding_teeth_bracket_status",
        ),
        CheckConstraint(
            f"bracket_type IS NULL OR bracket_type IN ({_VALID_BRACKET_TYPES})",
            name="chk_ortho_bonding_teeth_bracket_type",
        ),
        Index("idx_ortho_bonding_teeth_record", "record_id"),
    )

    # Parent record (cascade delete: if the record is removed, so are teeth)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ortho_bonding_records.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Tooth identification (FDI notation)
    tooth_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Bracket state
    bracket_status: Mapped[str] = mapped_column(String(20), nullable=False)
    bracket_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    slot_size: Mapped[str | None] = mapped_column(String(10), nullable=True)
    wire_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    band: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    record: Mapped["OrthoBondingRecord"] = relationship(back_populates="teeth")

    def __repr__(self) -> str:
        return (
            f"<OrthoBondingTooth record={self.record_id} "
            f"tooth={self.tooth_number} status={self.bracket_status!r}>"
        )


class OrthoVisit(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """An individual adjustment visit within an orthodontic case.

    Captures wire changes, elastic prescription, adjustments performed,
    and the optional payment collected at the visit.

    visit_number is unique within a case and auto-assigned by the service layer.

    Clinical data is NEVER hard-deleted (regulatory requirement).
    Use is_active=False + deleted_at for soft delete.
    """

    __tablename__ = "ortho_visits"
    __table_args__ = (
        UniqueConstraint(
            "ortho_case_id",
            "visit_number",
            name="uq_ortho_visits_case_visit_number",
        ),
        CheckConstraint(
            f"payment_status IN ({_VALID_PAYMENT_STATUSES})",
            name="chk_ortho_visits_payment_status",
        ),
        Index("idx_ortho_visits_case", "ortho_case_id"),
    )

    # Parent case
    ortho_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ortho_cases.id"),
        nullable=False,
    )

    # Sequence
    visit_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Staff
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Visit details
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    wire_upper: Mapped[str | None] = mapped_column(String(50), nullable=True)
    wire_lower: Mapped[str | None] = mapped_column(String(50), nullable=True)
    elastics: Mapped[str | None] = mapped_column(String(200), nullable=True)
    adjustments: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Payment (amount in cents COP)
    payment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    payment_amount: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id"),
        nullable=True,
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    case: Mapped["OrthoCase"] = relationship(back_populates="visits")

    def __repr__(self) -> str:
        return (
            f"<OrthoVisit case={self.ortho_case_id} "
            f"visit_number={self.visit_number} date={self.visit_date}>"
        )


class OrthoCaseMaterial(UUIDPrimaryKeyMixin, TenantBase):
    """Inventory item consumed during an orthodontic case or visit.

    Immutable once written -- tracks material consumption for inventory
    deduction and cost tracking.  No updated_at column (not needed).

    quantity_used stores fractional units (e.g., 0.5 ml) via Numeric,
    consistent with InventoryQuantityHistory in the inventory module.
    """

    __tablename__ = "ortho_case_materials"
    __table_args__ = (
        CheckConstraint(
            "quantity_used > 0",
            name="chk_ortho_case_materials_quantity_used",
        ),
        Index("idx_ortho_case_materials_case", "ortho_case_id"),
    )

    # Parent case
    ortho_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ortho_cases.id"),
        nullable=False,
    )

    # Optional link to the specific visit the material was used in
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ortho_visits.id"),
        nullable=True,
    )

    # Inventory reference
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id"),
        nullable=False,
    )

    # Consumption
    quantity_used: Mapped[float] = mapped_column(Numeric, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Timestamp -- manual, not mixin (immutable row, no updated_at)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    case: Mapped["OrthoCase"] = relationship(back_populates="materials")

    def __repr__(self) -> str:
        return (
            f"<OrthoCaseMaterial case={self.ortho_case_id} "
            f"item={self.inventory_item_id} qty={self.quantity_used}>"
        )
