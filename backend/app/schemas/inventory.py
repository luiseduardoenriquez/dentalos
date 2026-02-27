"""Inventory request/response schemas — Pydantic v2.

Covers:
  - InventoryItem create/update/response
  - QuantityHistory response (immutable)
  - Alerts (expired, critical, low_stock)
  - SterilizationRecord create/response (immutable)
  - ImplantPlacement create/response (immutable)
  - Pagination wrapper
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ─── Enums ────────────────────────────────────────────────────────────────────


class ItemCategory(str, Enum):
    material = "material"
    instrument = "instrument"
    implant = "implant"
    medication = "medication"


class ItemUnit(str, Enum):
    units = "units"
    ml = "ml"
    g = "g"
    boxes = "boxes"


class ExpiryStatus(str, Enum):
    ok = "ok"
    warning = "warning"
    critical = "critical"
    expired = "expired"


class QuantityChangeReason(str, Enum):
    received = "received"
    consumed = "consumed"
    discarded = "discarded"
    adjustment = "adjustment"


# ─── Inventory Item ───────────────────────────────────────────────────────────


class InventoryItemCreate(BaseModel):
    """Fields required to create a new inventory item."""

    name: str = Field(..., min_length=1, max_length=200)
    category: ItemCategory
    quantity: Decimal = Field(..., ge=0)
    unit: ItemUnit
    lot_number: str | None = Field(default=None, max_length=100)
    expiry_date: date | None = None
    manufacturer: str | None = Field(default=None, max_length=200)
    supplier: str | None = Field(default=None, max_length=200)
    cost_per_unit: int | None = Field(default=None, ge=0, description="Cost in cents")
    minimum_stock: Decimal | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=100)


class InventoryItemUpdate(BaseModel):
    """Fields for updating an existing inventory item.

    If quantity_change is provided, change_reason is required.
    A QuantityHistory row is created automatically when quantity_change is set.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity_change: Decimal | None = Field(
        default=None,
        description="Delta to apply to current quantity (positive=add, negative=remove)",
    )
    change_reason: QuantityChangeReason | None = Field(
        default=None,
        description="Required when quantity_change is provided",
    )
    change_notes: str | None = None
    lot_number: str | None = Field(default=None, max_length=100)
    expiry_date: date | None = None
    manufacturer: str | None = Field(default=None, max_length=200)
    supplier: str | None = Field(default=None, max_length=200)
    cost_per_unit: int | None = Field(default=None, ge=0, description="Cost in cents")
    minimum_stock: Decimal | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=100)


class InventoryItemResponse(BaseModel):
    """Full inventory item detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    quantity: Decimal
    unit: str
    lot_number: str | None
    expiry_date: date | None
    expiry_status: str | None
    manufacturer: str | None
    supplier: str | None
    cost_per_unit: int | None
    minimum_stock: Decimal
    location: str | None
    created_by: str
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ─── Quantity History ─────────────────────────────────────────────────────────


class QuantityHistoryResponse(BaseModel):
    """Immutable record of a single quantity change."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    quantity_change: Decimal
    reason: str
    previous_quantity: Decimal
    new_quantity: Decimal
    notes: str | None
    created_by: str
    created_at: datetime


# ─── Alerts ──────────────────────────────────────────────────────────────────


class InventoryAlertItem(BaseModel):
    """Compact item representation used in alert lists."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    quantity: Decimal
    expiry_status: str | None
    expiry_date: date | None
    minimum_stock: Decimal


class InventoryAlertsResponse(BaseModel):
    """Grouped alert lists: expired, critical expiry, low stock."""

    expired: list[InventoryAlertItem]
    critical: list[InventoryAlertItem]
    low_stock: list[InventoryAlertItem]


# ─── Sterilization ────────────────────────────────────────────────────────────


class SterilizationRecordCreate(BaseModel):
    """Fields required to create a sterilization record."""

    autoclave_id: str = Field(..., min_length=1, max_length=100)
    load_number: str = Field(..., min_length=1, max_length=50)
    date: date
    temperature_celsius: Decimal | None = None
    duration_minutes: int | None = Field(default=None, ge=1)
    biological_indicator: str | None = Field(default=None, max_length=10)
    chemical_indicator: str | None = Field(default=None, max_length=10)
    responsible_user_id: UUID
    instrument_ids: list[UUID] = Field(
        ..., min_length=1, description="Inventory item IDs of instruments in this load"
    )
    signature_data: str | None = None
    signature_sha256_hash: str | None = Field(
        default=None,
        max_length=64,
        description="SHA-256 hex digest of signature_data",
    )
    notes: str | None = None


class SterilizationRecordResponse(BaseModel):
    """Full sterilization record detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    autoclave_id: str
    load_number: str
    date: date
    temperature_celsius: Decimal | None
    duration_minutes: int | None
    biological_indicator: str | None
    chemical_indicator: str | None
    responsible_user_id: str
    is_compliant: bool
    instrument_ids: list[str]
    signature_data: str | None
    signature_sha256_hash: str | None
    notes: str | None
    created_by: str
    created_at: datetime


# ─── Implant Placement ────────────────────────────────────────────────────────


class ImplantPlacementCreate(BaseModel):
    """Fields required to link an implant from inventory to a patient."""

    item_id: UUID
    patient_id: UUID
    procedure_id: UUID | None = None
    tooth_number: int | None = Field(default=None, ge=11, le=88)
    placement_date: date
    serial_number: str | None = Field(default=None, max_length=100)
    lot_number: str | None = Field(default=None, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class ImplantPlacementResponse(BaseModel):
    """Full implant placement record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    patient_id: str
    procedure_id: str | None
    tooth_number: int | None
    placement_date: date
    serial_number: str | None
    lot_number: str | None
    manufacturer: str | None
    notes: str | None
    created_by: str
    created_at: datetime


class ImplantSearchResponse(BaseModel):
    """Result of an implant placement search (by lot_number or patient_id)."""

    placements: list[ImplantPlacementResponse]
    total: int


# ─── Pagination ───────────────────────────────────────────────────────────────

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic pagination wrapper matching the DentalOS API convention."""

    items: list[T]
    total: int
    page: int
    page_size: int
