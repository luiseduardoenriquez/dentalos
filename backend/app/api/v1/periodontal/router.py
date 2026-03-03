"""Periodontal charting API routes.

Endpoint map (all scoped to /patients/{patient_id}/...):
  POST /patients/{patient_id}/periodontal-records             -- Create record
  GET  /patients/{patient_id}/periodontal-records              -- List records
  GET  /patients/{patient_id}/periodontal-records/compare      -- Compare two records
  GET  /patients/{patient_id}/periodontal-records/{record_id}  -- Get record detail

IMPORTANT: The /compare route is registered BEFORE /{record_id} to prevent
FastAPI from treating the literal string "compare" as a record_id parameter.

The list endpoint is registered before the detail endpoint for the same reason.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.periodontal import (
    ComparisonResponse,
    RecordCreate,
    RecordListResponse,
    RecordListItem,
    RecordResponse,
    MeasurementResponse,
)
from app.services.periodontal_service import periodontal_service

router = APIRouter(prefix="/patients/{patient_id}", tags=["periodontal"])


# ─── Create periodontal record ───────────────────────────────────────────────


@router.post(
    "/periodontal-records",
    response_model=RecordResponse,
    status_code=201,
)
async def create_periodontal_record(
    patient_id: str,
    body: RecordCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("periodontogram:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> RecordResponse:
    """Create a new periodontal charting record for a patient.

    Accepts up to 192 measurements (32 teeth x 6 sites) in a single
    request. Measurements are bulk-inserted for performance.

    Emits a create audit event on success.
    """
    result = await periodontal_service.create_record(
        db=db,
        patient_id=patient_id,
        recorded_by=current_user.user_id,
        data=body.model_dump(),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="periodontal_record",
        resource_id=result["id"],
    )

    return RecordResponse(
        id=result["id"],
        patient_id=result["patient_id"],
        recorded_by=result["recorded_by"],
        dentition_type=result["dentition_type"],
        source=result["source"],
        notes=result["notes"],
        measurements=[MeasurementResponse(**m) for m in result["measurements"]],
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


# ─── List periodontal records ────────────────────────────────────────────────
# Registered BEFORE /{record_id} to avoid path collision.


@router.get(
    "/periodontal-records",
    response_model=RecordListResponse,
)
async def list_periodontal_records(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("periodontogram:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> RecordListResponse:
    """Return a paginated list of periodontal records for a patient.

    List view includes metadata only (no measurements) for performance.
    Records are ordered newest-first. No audit event is emitted (read-only).
    """
    result = await periodontal_service.list_records(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return RecordListResponse(
        items=[RecordListItem(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ─── Compare periodontal records ─────────────────────────────────────────────
# Registered BEFORE /{record_id} to avoid path collision.


@router.get(
    "/periodontal-records/compare",
    response_model=ComparisonResponse,
)
async def compare_periodontal_records(
    patient_id: str,
    record_a_id: str = Query(..., description="UUID of the first record (older)"),
    record_b_id: str = Query(..., description="UUID of the second record (newer)"),
    current_user: AuthenticatedUser = Depends(
        require_permission("periodontogram:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ComparisonResponse:
    """Compare two periodontal records and return measurement deltas.

    For each common (tooth, site) pair, computes the difference in
    pocket_depth, recession, and clinical_attachment_level between the
    two records.

    Status is determined by pocket_depth change:
      - decreased -> improved
      - increased -> worsened
      - unchanged or both null -> unchanged

    No audit event is emitted (read-only).
    """
    result = await periodontal_service.compare_records(
        db=db,
        patient_id=patient_id,
        record_a_id=record_a_id,
        record_b_id=record_b_id,
    )
    return ComparisonResponse(**result)


# ─── Get periodontal record detail ──────────────────────────────────────────


@router.get(
    "/periodontal-records/{record_id}",
    response_model=RecordResponse,
)
async def get_periodontal_record(
    patient_id: str,
    record_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("periodontogram:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> RecordResponse:
    """Return full detail for a single periodontal record with measurements.

    Returns 404 if the record does not exist, is inactive, or belongs
    to a different patient. No audit event is emitted (read-only).
    """
    result = await periodontal_service.get_record(
        db=db,
        patient_id=patient_id,
        record_id=record_id,
    )

    return RecordResponse(
        id=result["id"],
        patient_id=result["patient_id"],
        recorded_by=result["recorded_by"],
        dentition_type=result["dentition_type"],
        source=result["source"],
        notes=result["notes"],
        measurements=[MeasurementResponse(**m) for m in result["measurements"]],
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )
