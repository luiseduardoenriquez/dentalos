"""Inventory API routes — Sprint 15-16.

Endpoint map:
  POST   /inventory                    — Create inventory item
  GET    /inventory                    — List inventory items (paginated, filterable)
  PUT    /inventory/{item_id}          — Update inventory item (may create history row)
  GET    /inventory/alerts             — Get expiry and low-stock alerts
  POST   /inventory/sterilization      — Create sterilization record (immutable)
  GET    /inventory/sterilization      — List sterilization records (paginated)
  POST   /inventory/implants/link      — Link implant from inventory to patient (atomic)
  GET    /inventory/implants/search    — Search implant placements by lot or patient

IMPORTANT: /alerts, /sterilization, /implants/search are defined BEFORE /{item_id}
to prevent path parameter collisions.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.inventory import (
    ImplantPlacementCreate,
    ImplantPlacementResponse,
    ImplantSearchResponse,
    InventoryAlertsResponse,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    PaginatedResponse,
    SterilizationRecordCreate,
    SterilizationRecordResponse,
)
from app.services.inventory_service import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ─── Alerts — MUST be before /{item_id} ─────────────────────────────────────


@router.get("/alerts", response_model=InventoryAlertsResponse)
async def get_alerts(
    current_user: AuthenticatedUser = Depends(require_permission("inventory:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> InventoryAlertsResponse:
    """Return grouped inventory alerts: expired items, critical expiry (≤30 days), and low stock."""
    result = await inventory_service.get_alerts(db=db)
    return InventoryAlertsResponse(**result)


# ─── Sterilization — MUST be before /{item_id} ───────────────────────────────


@router.post(
    "/sterilization",
    response_model=SterilizationRecordResponse,
    status_code=201,
)
async def create_sterilization(
    body: SterilizationRecordCreate,
    current_user: AuthenticatedUser = Depends(require_permission("inventory:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SterilizationRecordResponse:
    """Create an immutable sterilization record for an autoclave load.

    All instrument_ids must exist in inventory and be category='instrument'.
    (autoclave_id, load_number, date) must be unique.
    """
    result = await inventory_service.create_sterilization(
        db=db,
        created_by_id=current_user.user_id,
        autoclave_id=body.autoclave_id,
        load_number=body.load_number,
        date=body.date,
        responsible_user_id=str(body.responsible_user_id),
        instrument_ids=[str(iid) for iid in body.instrument_ids],
        temperature_celsius=body.temperature_celsius,
        duration_minutes=body.duration_minutes,
        biological_indicator=body.biological_indicator,
        chemical_indicator=body.chemical_indicator,
        signature_data=body.signature_data,
        signature_sha256_hash=body.signature_sha256_hash,
        notes=body.notes,
    )
    return SterilizationRecordResponse(**result)


@router.get(
    "/sterilization",
    response_model=PaginatedResponse[SterilizationRecordResponse],
)
async def list_sterilization(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    autoclave_id: str | None = Query(default=None),
    compliant_only: bool | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("inventory:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaginatedResponse[SterilizationRecordResponse]:
    """List sterilization records with optional date range, autoclave, and compliance filters."""
    result = await inventory_service.list_sterilization(
        db=db,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        autoclave_id=autoclave_id,
        compliant_only=compliant_only,
    )
    return PaginatedResponse[SterilizationRecordResponse](
        items=[SterilizationRecordResponse(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ─── Implants — MUST be before /{item_id} ────────────────────────────────────


@router.post(
    "/implants/link",
    response_model=ImplantPlacementResponse,
    status_code=201,
)
async def link_implant(
    body: ImplantPlacementCreate,
    current_user: AuthenticatedUser = Depends(require_permission("inventory:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ImplantPlacementResponse:
    """Atomically place an implant: decrement inventory quantity and create placement record.

    Item must be category='implant' with quantity > 0.
    """
    result = await inventory_service.link_implant(
        db=db,
        created_by_id=current_user.user_id,
        item_id=str(body.item_id),
        patient_id=str(body.patient_id),
        placement_date=body.placement_date,
        procedure_id=str(body.procedure_id) if body.procedure_id else None,
        tooth_number=body.tooth_number,
        serial_number=body.serial_number,
        lot_number=body.lot_number,
        manufacturer=body.manufacturer,
        notes=body.notes,
    )
    return ImplantPlacementResponse(**result)


@router.get(
    "/implants/search",
    response_model=ImplantSearchResponse,
)
async def search_implants(
    lot_number: str | None = Query(
        default=None,
        description="Search by lot number (ILIKE — for implant recall)",
    ),
    patient_id: UUID | None = Query(
        default=None,
        description="Filter by patient UUID",
    ),
    current_user: AuthenticatedUser = Depends(require_permission("inventory:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ImplantSearchResponse:
    """Search implant placements by lot number (ILIKE) or patient ID.

    At least one of lot_number or patient_id is required.
    """
    result = await inventory_service.search_implants(
        db=db,
        lot_number=lot_number,
        patient_id=str(patient_id) if patient_id else None,
    )
    return ImplantSearchResponse(**result)


# ─── Inventory Items ─────────────────────────────────────────────────────────


@router.post("", response_model=InventoryItemResponse, status_code=201)
async def create_item(
    body: InventoryItemCreate,
    current_user: AuthenticatedUser = Depends(require_permission("inventory:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> InventoryItemResponse:
    """Create a new inventory item (material, instrument, implant, or medication)."""
    result = await inventory_service.create_item(
        db=db,
        created_by_id=current_user.user_id,
        name=body.name,
        category=body.category.value,
        quantity=body.quantity,
        unit=body.unit.value,
        lot_number=body.lot_number,
        expiry_date=body.expiry_date,
        manufacturer=body.manufacturer,
        supplier=body.supplier,
        cost_per_unit=body.cost_per_unit,
        minimum_stock=body.minimum_stock,
        location=body.location,
    )
    return InventoryItemResponse(**result)


@router.get("", response_model=PaginatedResponse[InventoryItemResponse])
async def list_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    expiry_status: str | None = Query(default=None),
    low_stock: bool | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("inventory:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaginatedResponse[InventoryItemResponse]:
    """List active inventory items with optional filters for category, expiry status, and stock level."""
    result = await inventory_service.list_items(
        db=db,
        page=page,
        page_size=page_size,
        category=category,
        expiry_status=expiry_status,
        low_stock=low_stock,
    )
    return PaginatedResponse[InventoryItemResponse](
        items=[InventoryItemResponse(**i) for i in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.put("/{item_id}", response_model=InventoryItemResponse)
async def update_item(
    item_id: str,
    body: InventoryItemUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("inventory:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> InventoryItemResponse:
    """Update an inventory item.

    If quantity_change is provided, change_reason is required and an immutable
    QuantityHistory row is created automatically.
    """
    result = await inventory_service.update_item(
        db=db,
        item_id=item_id,
        created_by_id=current_user.user_id,
        name=body.name,
        quantity_change=body.quantity_change,
        change_reason=body.change_reason.value if body.change_reason else None,
        change_notes=body.change_notes,
        lot_number=body.lot_number,
        expiry_date=body.expiry_date,
        manufacturer=body.manufacturer,
        supplier=body.supplier,
        cost_per_unit=body.cost_per_unit,
        minimum_stock=body.minimum_stock,
        location=body.location,
    )
    return InventoryItemResponse(**result)
