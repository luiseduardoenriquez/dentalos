"""Inventory models — items, quantity history, sterilization records, implant placements.

Five tables:
  - InventoryItem: consumables, instruments, implants, medications with expiry tracking
  - InventoryQuantityHistory: immutable audit log of every quantity change
  - SterilizationRecord: autoclave load records with compliance tracking
  - SterilizationRecordInstrument: junction between sterilization records and instruments
  - ImplantPlacement: immutable record linking implant items to patients/procedures
"""

import uuid
from datetime import date, datetime

import sqlalchemy as sa
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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class InventoryItem(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A tracked inventory item: consumable material, instrument, implant, or medication.

    expiry_status is a server-side persisted computed column driven by expiry_date
    and today's date. Values: ok | warning | critical | expired.

    Quantity is stored as Numeric to support fractional units (e.g., 2.5 ml).
    Cost is in cents (Integer) to avoid floating-point money issues.
    Soft-deleted: is_active + deleted_at — clinical data is never hard-deleted.
    """

    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint(
            "category IN ('material', 'instrument', 'implant', 'medication')",
            name="chk_inventory_items_category",
        ),
        CheckConstraint(
            "unit IN ('units', 'ml', 'g', 'boxes')",
            name="chk_inventory_items_unit",
        ),
        Index("idx_inventory_items_category", "category"),
        Index("idx_inventory_items_expiry_status", "expiry_status"),
        Index("idx_inventory_items_is_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Persisted computed column — server evaluates based on expiry_date vs CURRENT_DATE.
    # ok: no expiry or > 90 days remaining
    # warning: 31-90 days remaining
    # critical: 1-30 days remaining
    # expired: past expiry date
    expiry_status: Mapped[str | None] = mapped_column(
        String(10),
        sa.Computed(
            """
            CASE
                WHEN expiry_date IS NULL THEN 'ok'
                WHEN expiry_date < CURRENT_DATE THEN 'expired'
                WHEN expiry_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'critical'
                WHEN expiry_date <= CURRENT_DATE + INTERVAL '90 days' THEN 'warning'
                ELSE 'ok'
            END
            """,
            persisted=True,
        ),
        nullable=True,
    )

    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cost_per_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # cents
    minimum_stock: Mapped[float] = mapped_column(Numeric, nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    quantity_history: Mapped[list["InventoryQuantityHistory"]] = relationship(
        back_populates="item",
        lazy="selectin",
        order_by="InventoryQuantityHistory.created_at.desc()",
    )
    implant_placements: Mapped[list["ImplantPlacement"]] = relationship(
        back_populates="item",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryItem name={self.name!r} "
            f"category={self.category} quantity={self.quantity} unit={self.unit}>"
        )


class InventoryQuantityHistory(UUIDPrimaryKeyMixin, TenantBase):
    """Immutable audit log of every quantity change on an inventory item.

    No updated_at — records are never modified after creation.
    reason: received | consumed | discarded | adjustment
    """

    __tablename__ = "inventory_quantity_history"
    __table_args__ = (
        CheckConstraint(
            "reason IN ('received', 'consumed', 'discarded', 'adjustment')",
            name="chk_inventory_quantity_history_reason",
        ),
        Index("idx_inventory_quantity_history_item", "item_id"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id"),
        nullable=False,
    )
    quantity_change: Mapped[float] = mapped_column(Numeric, nullable=False)
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    new_quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    # Relationship
    item: Mapped["InventoryItem"] = relationship(back_populates="quantity_history")

    def __repr__(self) -> str:
        return (
            f"<InventoryQuantityHistory item={self.item_id} "
            f"change={self.quantity_change} reason={self.reason}>"
        )


class SterilizationRecord(UUIDPrimaryKeyMixin, TenantBase):
    """An autoclave sterilization load record for regulatory compliance.

    is_compliant is a persisted computed column: True when both biological
    and chemical indicators are 'pass'.

    Records are IMMUTABLE — no update or delete endpoints exist.
    (autoclave_id, load_number, date) must be unique to prevent duplicate loads.
    """

    __tablename__ = "sterilization_records"
    __table_args__ = (
        UniqueConstraint(
            "autoclave_id",
            "load_number",
            "date",
            name="uq_sterilization_records_load",
        ),
        Index("idx_sterilization_records_date", "date"),
        Index("idx_sterilization_records_autoclave", "autoclave_id"),
        Index("idx_sterilization_records_compliant", "is_compliant"),
    )

    autoclave_id: Mapped[str] = mapped_column(String(100), nullable=False)
    load_number: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    temperature_celsius: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    biological_indicator: Mapped[str | None] = mapped_column(String(10), nullable=True)
    chemical_indicator: Mapped[str | None] = mapped_column(String(10), nullable=True)

    responsible_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    signature_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Persisted computed: compliant when both indicators passed
    is_compliant: Mapped[bool] = mapped_column(
        Boolean,
        sa.Computed(
            """
            (biological_indicator = 'pass' AND chemical_indicator = 'pass')
            """,
            persisted=True,
        ),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    # Relationship
    instruments: Mapped[list["SterilizationRecordInstrument"]] = relationship(
        back_populates="sterilization_record",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<SterilizationRecord autoclave={self.autoclave_id} "
            f"load={self.load_number} date={self.date} compliant={self.is_compliant}>"
        )


class SterilizationRecordInstrument(UUIDPrimaryKeyMixin, TenantBase):
    """Junction table linking sterilization records to the instruments sterilized."""

    __tablename__ = "sterilization_record_instruments"
    __table_args__ = (
        Index(
            "idx_sterilization_record_instruments_record",
            "sterilization_record_id",
        ),
        Index(
            "idx_sterilization_record_instruments_item",
            "inventory_item_id",
        ),
    )

    sterilization_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sterilization_records.id"),
        nullable=False,
    )
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id"),
        nullable=False,
    )

    # Relationship back to the record
    sterilization_record: Mapped["SterilizationRecord"] = relationship(
        back_populates="instruments",
    )

    def __repr__(self) -> str:
        return (
            f"<SterilizationRecordInstrument "
            f"record={self.sterilization_record_id} item={self.inventory_item_id}>"
        )


class ImplantPlacement(UUIDPrimaryKeyMixin, TenantBase):
    """Immutable record of an implant placed in a patient.

    When an implant is placed, the inventory item's quantity is decremented
    atomically and a QuantityHistory row (reason='consumed') is created in
    the same flush. No update or delete endpoints exist.
    """

    __tablename__ = "implant_placements"
    __table_args__ = (
        Index("idx_implant_placements_item", "item_id"),
        Index("idx_implant_placements_patient", "patient_id"),
        Index("idx_implant_placements_lot", "lot_number"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    procedure_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    tooth_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    placement_date: Mapped[date] = mapped_column(Date, nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    # Relationship
    item: Mapped["InventoryItem"] = relationship(back_populates="implant_placements")

    def __repr__(self) -> str:
        return (
            f"<ImplantPlacement item={self.item_id} "
            f"patient={self.patient_id} date={self.placement_date}>"
        )
