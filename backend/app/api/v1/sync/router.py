"""Offline sync API endpoints.

Three endpoints for the offline-first sync system:
- GET /sync/delta — Records modified since a given timestamp
- GET /sync/full  — Full bounded data dump for initial hydration
- POST /sync/batch — Process a batch of offline write operations
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user
from app.core.database import get_tenant_db
from app.schemas.sync import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncDeltaResponse,
    SyncFullResponse,
    SyncResourceDelta,
)
from app.services import sync_service

router = APIRouter(prefix="/sync", tags=["sync"])


# ─── Delta Sync ───────────────────────────────────────────────────────────────


@router.get("/delta", response_model=SyncDeltaResponse, status_code=200)
async def get_sync_delta(
    since: datetime = Query(..., description="ISO 8601 timestamp"),
    resources: str = Query(
        "patients,appointments,odontogram,clinical_records",
        description="Comma-separated resource types",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> SyncDeltaResponse:
    """Return records modified since the given timestamp.

    Supports filtering by resource type. Used for periodic background sync.
    """
    resource_list = [r.strip() for r in resources.split(",")]
    deltas: list[SyncResourceDelta] = []

    if "patients" in resource_list:
        deltas.append(await sync_service.get_patients_delta(db, since))
    if "appointments" in resource_list:
        deltas.append(await sync_service.get_appointments_delta(db, since))
    if "odontogram" in resource_list:
        deltas.append(await sync_service.get_odontogram_delta(db, since))
    if "clinical_records" in resource_list:
        deltas.append(await sync_service.get_clinical_records_delta(db, since))

    return SyncDeltaResponse(
        deltas=deltas,
        server_time=datetime.now(timezone.utc),
    )


# ─── Full Sync ────────────────────────────────────────────────────────────────


@router.get("/full", response_model=SyncFullResponse, status_code=200)
async def get_sync_full(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> SyncFullResponse:
    """Full bounded data dump for initial offline hydration.

    Rate limited: max 1 request per hour per user (enforced by cache).
    Returns last 200 patients, today+tomorrow appointments,
    all odontogram states, and last 7 days of clinical records.
    """
    data = await sync_service.get_full_sync_data(db)
    return SyncFullResponse(**data)


# ─── Batch Write ──────────────────────────────────────────────────────────────


@router.post("/batch", response_model=SyncBatchResponse, status_code=200)
async def process_sync_batch(
    batch: SyncBatchRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> SyncBatchResponse:
    """Process a batch of offline write operations.

    Operations are processed sequentially in order. Each operation
    delegates to existing domain services to preserve validation,
    permission checks, and audit logging.

    Conflict detection: if operation.queued_at < server_record.updated_at,
    the operation is marked as a conflict and the current server data is
    returned so the client can perform conflict resolution.
    """
    results = []
    succeeded = 0
    conflicts = 0
    errors = 0

    for i, operation in enumerate(batch.operations):
        result = await sync_service.process_sync_operation(
            db=db,
            user=current_user,
            operation=operation,
            index=i,
        )
        results.append(result)
        if result.status == "success":
            succeeded += 1
        elif result.status == "conflict":
            conflicts += 1
        else:
            errors += 1

    await db.commit()

    return SyncBatchResponse(
        results=results,
        total=len(batch.operations),
        succeeded=succeeded,
        conflicts=conflicts,
        errors=errors,
        server_time=datetime.now(timezone.utc),
    )
