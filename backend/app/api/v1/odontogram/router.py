"""Odontogram API routes — OD-01 through OD-12.

Endpoint map (all scoped to /patients/{patient_id}/odontogram):
  GET  /patients/{patient_id}/odontogram                           — OD-01: Full odontogram state
  POST /patients/{patient_id}/odontogram/conditions                — OD-02: Add/update condition
  DEL  /patients/{patient_id}/odontogram/conditions/{condition_id} — OD-03: Remove condition
  GET  /patients/{patient_id}/odontogram/history                   — OD-04: Cursor-paginated history
  POST /patients/{patient_id}/odontogram/snapshots                 — OD-05: Create snapshot
  GET  /patients/{patient_id}/odontogram/snapshots                 — OD-07: List snapshots
  GET  /patients/{patient_id}/odontogram/snapshots/{snapshot_id}   — OD-06: Get snapshot detail
  GET  /patients/{patient_id}/odontogram/compare                   — OD-08: Compare two snapshots
  GET  /patients/{patient_id}/odontogram/teeth/{tooth_number}      — OD-10: Single tooth detail
  POST /patients/{patient_id}/odontogram/bulk                      — OD-11: Bulk condition update
  POST /patients/{patient_id}/odontogram/dentition                 — OD-12: Toggle dentition type

IMPORTANT: The /snapshots list route (OD-07) is registered BEFORE the
/snapshots/{snapshot_id} detail route (OD-06) to prevent FastAPI from
treating the literal string "snapshots" as a UUID path parameter.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.odontogram import (
    BulkConditionUpdate,
    BulkUpdateResult,
    CompareResponse,
    ConditionCreate,
    ConditionUpdateResult,
    DentitionToggle,
    HistoryListResponse,
    OdontogramResponse,
    SnapshotCreate,
    SnapshotDetailResponse,
    SnapshotListResponse,
    SnapshotResponse,
)
from app.services.odontogram_service import odontogram_service

router = APIRouter(prefix="/patients/{patient_id}/odontogram", tags=["odontogram"])


# ─── OD-01: Get full odontogram state ────────────────────────────────────────


@router.get("", response_model=OdontogramResponse)
async def get_odontogram(
    patient_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> OdontogramResponse:
    """Return the full odontogram state for a patient.

    Returns all tooth-zone conditions organised by FDI tooth number.
    Results are cached in Redis for 5 minutes per patient per tenant.
    No audit event is emitted (read-only, high-frequency endpoint).
    """
    result = await odontogram_service.get_odontogram(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="ODONTOGRAM_not_found",
            resource_name="Odontogram",
        )
    return OdontogramResponse(**result)


# ─── OD-02: Add / update condition ───────────────────────────────────────────


@router.post("/conditions", response_model=ConditionUpdateResult, status_code=201)
async def update_condition(
    patient_id: str,
    body: ConditionCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("odontogram:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConditionUpdateResult:
    """Record or replace a condition on a single tooth zone.

    If the zone already has a condition, the previous entry is overwritten
    and an immutable history record is created capturing the change.
    Emits an update_condition audit event on success.
    """
    result = await odontogram_service.update_condition(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
        user_id=current_user.user_id,
        tooth_number=body.tooth_number,
        zone=body.zone,
        condition_code=body.condition_code,
        severity=body.severity,
        notes=body.notes,
        source=body.source,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update_condition",
        resource_type="odontogram",
        resource_id=patient_id,
    )

    return ConditionUpdateResult(**result)


# ─── OD-03: Remove condition ──────────────────────────────────────────────────


@router.delete("/conditions/{condition_id}", response_model=dict)
async def remove_condition(
    patient_id: str,
    condition_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("odontogram:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Soft-delete a tooth-zone condition from the odontogram.

    The condition is marked inactive and an immutable history entry is
    created. Clinical data is never hard-deleted (Resolución 1888).
    Emits a remove_condition audit event on success.
    """
    result = await odontogram_service.remove_condition(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
        user_id=current_user.user_id,
        condition_id=condition_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="remove_condition",
        resource_type="odontogram",
        resource_id=patient_id,
    )

    return result


# ─── OD-04: History ───────────────────────────────────────────────────────────


@router.get("/history", response_model=HistoryListResponse)
async def get_odontogram_history(
    patient_id: str,
    tooth_number: int | None = Query(default=None),
    zone: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> HistoryListResponse:
    """Return cursor-paginated condition history for an odontogram.

    Optionally filtered by tooth number and/or zone. Each page returns
    up to `limit` entries (default 50, max 100) ordered newest-first.
    No audit event is emitted (read-only).
    """
    result = await odontogram_service.get_history(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
        tooth_number=tooth_number,
        zone=zone,
        cursor=cursor,
        limit=limit,
    )
    return HistoryListResponse(**result)


# ─── OD-05: Create snapshot ───────────────────────────────────────────────────


@router.post("/snapshots", response_model=SnapshotResponse, status_code=201)
async def create_snapshot(
    patient_id: str,
    body: SnapshotCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("odontogram:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> SnapshotResponse:
    """Create a point-in-time snapshot of the current odontogram state.

    Snapshots are immutable after creation and can be compared against
    each other or against the live odontogram. Emits a create_snapshot
    audit event on success.
    """
    result = await odontogram_service.create_snapshot(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
        user_id=current_user.user_id,
        label=body.label,
        linked_record_id=body.linked_record_id,
        linked_treatment_plan_id=body.linked_treatment_plan_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create_snapshot",
        resource_type="odontogram",
        resource_id=patient_id,
    )

    return SnapshotResponse(**result)


# ─── OD-07: List snapshots ────────────────────────────────────────────────────
# Registered BEFORE OD-06 (/snapshots/{snapshot_id}) to prevent FastAPI from
# treating the literal string "snapshots" as a path parameter value.


@router.get("/snapshots", response_model=SnapshotListResponse)
async def list_snapshots(
    patient_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> SnapshotListResponse:
    """Return all snapshots for an odontogram, ordered newest-first.

    No audit event is emitted (read-only).
    """
    result = await odontogram_service.list_snapshots(
        db=db,
        patient_id=patient_id,
    )
    return SnapshotListResponse(**result)


# ─── OD-06: Get snapshot detail ───────────────────────────────────────────────


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotDetailResponse)
async def get_snapshot(
    patient_id: str,
    snapshot_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> SnapshotDetailResponse:
    """Return full snapshot detail including the serialised odontogram state.

    Returns 404 if the snapshot does not exist or belongs to a different patient.
    No audit event is emitted (read-only).
    """
    result = await odontogram_service.get_snapshot(
        db=db,
        patient_id=patient_id,
        snapshot_id=snapshot_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="ODONTOGRAM_snapshot_not_found",
            resource_name="OdontogramSnapshot",
        )
    return SnapshotDetailResponse(**result)


# ─── OD-08: Compare snapshots ────────────────────────────────────────────────


@router.get("/compare", response_model=CompareResponse)
async def compare_snapshots(
    patient_id: str,
    snapshot_a_id: str = Query(description="ID of the first snapshot (baseline)."),
    snapshot_b_id: str = Query(description="ID of the second snapshot (comparison)."),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> CompareResponse:
    """Return a structural diff between two odontogram snapshots.

    The diff is expressed as lists of added, removed, and changed
    tooth-zone conditions relative to snapshot_a. No audit event is emitted.
    """
    result = await odontogram_service.compare_snapshots(
        db=db,
        patient_id=patient_id,
        snapshot_a_id=snapshot_a_id,
        snapshot_b_id=snapshot_b_id,
    )
    return CompareResponse(**result)


# ─── OD-10: Single tooth detail ───────────────────────────────────────────────


@router.get("/teeth/{tooth_number}", response_model=dict)
async def get_tooth_detail(
    patient_id: str,
    tooth_number: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Return all zone conditions and recent history for a single FDI tooth.

    No audit event is emitted (read-only).
    """
    result = await odontogram_service.get_tooth_detail(
        db=db,
        patient_id=patient_id,
        tooth_number=tooth_number,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="ODONTOGRAM_tooth_not_found",
            resource_name="Tooth",
        )
    return result


# ─── OD-11: Bulk condition update ─────────────────────────────────────────────


@router.post("/bulk", response_model=BulkUpdateResult)
async def bulk_update_conditions(
    patient_id: str,
    body: BulkConditionUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("odontogram:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> BulkUpdateResult:
    """Apply a batch of condition updates in a single atomic operation.

    All updates in the batch succeed or all fail together. Useful for
    recording an entire examination session at once. Emits a bulk_update
    audit event on success.
    """
    result = await odontogram_service.bulk_update(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
        user_id=current_user.user_id,
        updates=[u.model_dump() for u in body.updates],
        session_notes=body.session_notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="bulk_update",
        resource_type="odontogram",
        resource_id=patient_id,
    )

    return BulkUpdateResult(**result)


# ─── OD-12: Toggle dentition ──────────────────────────────────────────────────


@router.post("/dentition", response_model=dict)
async def toggle_dentition(
    patient_id: str,
    body: DentitionToggle,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("odontogram:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Switch the dentition mode (permanent / mixed / primary) for an odontogram.

    Changing dentition clears teeth that do not exist in the new mode and
    triggers a cache invalidation. Emits a toggle_dentition audit event.
    """
    result = await odontogram_service.toggle_dentition(
        db=db,
        patient_id=patient_id,
        tenant_id=current_user.tenant.tenant_id,
        dentition_type=body.dentition_type,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="toggle_dentition",
        resource_type="odontogram",
        resource_id=patient_id,
    )

    return result
