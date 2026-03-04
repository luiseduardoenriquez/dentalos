"""Dental lab order management API routes -- VP-22 / Sprint 31-32.

Endpoint map (all JWT-protected):

  Lab directory:
    POST   /lab-orders/labs              — LAB-01: Create dental lab
    GET    /lab-orders/labs              — LAB-02: List dental labs
    GET    /lab-orders/labs/{lab_id}     — LAB-03: Get dental lab detail
    PUT    /lab-orders/labs/{lab_id}     — LAB-04: Update dental lab

  Work orders:
    POST   /lab-orders                         — ORD-01: Create lab order
    GET    /lab-orders                         — ORD-02: List lab orders (paginated)
    GET    /lab-orders/overdue                 — ORD-03: List overdue orders
    GET    /lab-orders/{order_id}              — ORD-04: Get lab order detail
    PUT    /lab-orders/{order_id}              — ORD-05: Update lab order
    POST   /lab-orders/{order_id}/advance      — ORD-06: Advance order status

Auth:
  - lab_orders:read  — view labs and orders
  - lab_orders:write — create / update labs and orders, advance status

IMPORTANT: The /overdue route is declared BEFORE /{order_id} to prevent
FastAPI from interpreting the literal string "overdue" as an order UUID.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.core.exceptions import DentalOSError
from app.schemas.lab_order import (
    DentalLabCreate,
    DentalLabResponse,
    DentalLabUpdate,
    LabOrderCreate,
    LabOrderListResponse,
    LabOrderResponse,
    LabOrderStatusUpdate,
    LabOrderUpdate,
)
from app.services.lab_order_service import lab_order_service

router = APIRouter(prefix="/lab-orders", tags=["lab-orders"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    """Parse a string UUID or raise a 400 DentalOSError."""
    try:
        return uuid.UUID(value)
    except ValueError:
        raise DentalOSError(
            error="VALIDATION_invalid_field",
            message=f"{field_name} inválido.",
            status_code=400,
        )


# ── LAB-01: Create dental lab ─────────────────────────────────────────────────


@router.post(
    "/labs",
    response_model=DentalLabResponse,
    status_code=201,
    summary="Crear laboratorio dental",
)
async def create_lab(
    body: DentalLabCreate,
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> DentalLabResponse:
    """Register a new external dental laboratory in the clinic's directory.

    The lab can then be assigned to lab work orders. All fields except name
    are optional and can be filled in or updated later.
    """
    result = await lab_order_service.create_lab(db=db, data=body)
    return DentalLabResponse(**result)


# ── LAB-02: List dental labs ──────────────────────────────────────────────────


@router.get(
    "/labs",
    response_model=list[DentalLabResponse],
    summary="Listar laboratorios dentales",
)
async def list_labs(
    include_inactive: bool = Query(
        default=False,
        description="Incluir laboratorios inactivos",
    ),
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[DentalLabResponse]:
    """Return all dental labs registered for this clinic.

    By default only active labs are returned. Pass include_inactive=true to
    also see deactivated labs (useful for historical order context).
    """
    labs = await lab_order_service.list_labs(db=db, include_inactive=include_inactive)
    return [DentalLabResponse(**lab) for lab in labs]


# ── LAB-03: Get dental lab detail ─────────────────────────────────────────────


@router.get(
    "/labs/{lab_id}",
    response_model=DentalLabResponse,
    summary="Detalle de laboratorio dental",
)
async def get_lab(
    lab_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> DentalLabResponse:
    """Return full detail for a single dental laboratory."""
    lab_uuid = _parse_uuid(lab_id, "lab_id")
    result = await lab_order_service.get_lab(db=db, lab_id=lab_uuid)
    return DentalLabResponse(**result)


# ── LAB-04: Update dental lab ─────────────────────────────────────────────────


@router.put(
    "/labs/{lab_id}",
    response_model=DentalLabResponse,
    summary="Actualizar laboratorio dental",
)
async def update_lab(
    lab_id: str,
    body: DentalLabUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> DentalLabResponse:
    """Update contact details or active status for a dental laboratory.

    Only fields included in the request body are modified. Omitted fields
    retain their current values.
    """
    lab_uuid = _parse_uuid(lab_id, "lab_id")
    result = await lab_order_service.update_lab(db=db, lab_id=lab_uuid, data=body)
    return DentalLabResponse(**result)


# ── ORD-01: Create lab order ──────────────────────────────────────────────────


@router.post(
    "",
    response_model=LabOrderResponse,
    status_code=201,
    summary="Crear orden de laboratorio",
)
async def create_order(
    body: LabOrderCreate,
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> LabOrderResponse:
    """Create a new lab work order for a patient.

    The order is created in status=pending. The lab assignment (lab_id) and
    cost_cents can be left blank and filled in later via the PUT endpoint.
    Once ready, use the /advance endpoint to progress through the status
    lifecycle: pending → sent_to_lab → in_progress → ready → delivered.
    """
    result = await lab_order_service.create_order(
        db=db,
        data=body,
        created_by=current_user.user_id,
    )
    return LabOrderResponse(**result)


# ── ORD-02: List lab orders ───────────────────────────────────────────────────


@router.get(
    "",
    response_model=LabOrderListResponse,
    summary="Listar órdenes de laboratorio",
)
async def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, description="Filtrar por estado"),
    lab_id: str | None = Query(default=None, description="Filtrar por UUID de laboratorio"),
    patient_id: str | None = Query(default=None, description="Filtrar por UUID de paciente"),
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> LabOrderListResponse:
    """Return a paginated list of lab work orders for this clinic.

    Supports optional filtering by status, laboratory, and patient.
    Results are ordered by creation date descending (newest first).
    """
    lab_uuid: uuid.UUID | None = None
    if lab_id is not None:
        lab_uuid = _parse_uuid(lab_id, "lab_id")

    patient_uuid: uuid.UUID | None = None
    if patient_id is not None:
        patient_uuid = _parse_uuid(patient_id, "patient_id")

    result = await lab_order_service.list_orders(
        db=db,
        page=page,
        page_size=page_size,
        status_filter=status,
        lab_id=lab_uuid,
        patient_id=patient_uuid,
    )
    return LabOrderListResponse(
        items=[LabOrderResponse(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ── ORD-03: List overdue orders ───────────────────────────────────────────────
# IMPORTANT: This route is declared BEFORE /{order_id} so that the literal
# path segment "overdue" is not mistaken for an order UUID by FastAPI's router.


@router.get(
    "/overdue",
    response_model=list[LabOrderResponse],
    summary="Órdenes de laboratorio vencidas",
)
async def get_overdue_orders(
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[LabOrderResponse]:
    """Return all active lab orders that have passed their due date.

    An order is considered overdue when its due_date is in the past and
    its status is not delivered or cancelled. Results are ordered by
    due_date ascending so the most overdue orders appear first.
    """
    orders = await lab_order_service.get_overdue_orders(db=db)
    return [LabOrderResponse(**order) for order in orders]


# ── ORD-04: Get lab order detail ──────────────────────────────────────────────


@router.get(
    "/{order_id}",
    response_model=LabOrderResponse,
    summary="Detalle de orden de laboratorio",
)
async def get_order(
    order_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> LabOrderResponse:
    """Return full detail for a single lab work order."""
    order_uuid = _parse_uuid(order_id, "order_id")
    result = await lab_order_service.get_order(db=db, order_id=order_uuid)
    return LabOrderResponse(**result)


# ── ORD-05: Update lab order ──────────────────────────────────────────────────


@router.put(
    "/{order_id}",
    response_model=LabOrderResponse,
    summary="Actualizar orden de laboratorio",
)
async def update_order(
    order_id: str,
    body: LabOrderUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> LabOrderResponse:
    """Update editable fields on a lab work order.

    Only orders that are not in a terminal state (delivered, cancelled) can
    be updated. To change the order's status use the /advance endpoint.
    """
    order_uuid = _parse_uuid(order_id, "order_id")
    result = await lab_order_service.update_order(db=db, order_id=order_uuid, data=body)
    return LabOrderResponse(**result)


# ── ORD-06: Advance status ────────────────────────────────────────────────────


@router.post(
    "/{order_id}/advance",
    response_model=LabOrderResponse,
    summary="Avanzar estado de orden de laboratorio",
)
async def advance_order_status(
    order_id: str,
    body: LabOrderStatusUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("lab_orders:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> LabOrderResponse:
    """Advance a lab order to the next status in its lifecycle.

    Valid forward transitions:
      pending → sent_to_lab → in_progress → ready → delivered

    Any non-delivered order may also be transitioned to 'cancelled'.

    Side effects:
      - sent_to_lab: records sent_at timestamp.
      - ready: records ready_at timestamp + enqueues lab_order.ready notification.
      - delivered: records delivered_at timestamp.

    Delivered orders are immutable — no further status changes are allowed.
    """
    order_uuid = _parse_uuid(order_id, "order_id")
    result = await lab_order_service.advance_status(
        db=db,
        order_id=order_uuid,
        new_status=body.status,
        tenant_id=current_user.tenant.schema_name,
    )
    return LabOrderResponse(**result)
