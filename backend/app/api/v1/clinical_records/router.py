"""Clinical records API routes — CR-01 through CR-06.

Endpoint map (all scoped to /patients/{patient_id}/...):
  POST /patients/{patient_id}/clinical-records                        — CR-01: Create record
  GET  /patients/{patient_id}/clinical-records                        — CR-03: List records
  GET  /patients/{patient_id}/clinical-records/{record_id}            — CR-02: Get record detail
  PUT  /patients/{patient_id}/clinical-records/{record_id}            — CR-04: Update record
  POST /patients/{patient_id}/anamnesis                               — CR-05: Create / upsert anamnesis
  GET  /patients/{patient_id}/anamnesis                               — CR-06: Get anamnesis

IMPORTANT: The /anamnesis routes (CR-05, CR-06) are registered BEFORE the
/{record_id} routes (CR-02, CR-04) to prevent FastAPI from treating the
literal string "anamnesis" as a record_id path parameter.

The list endpoint (CR-03) is registered before the detail endpoint (CR-02)
for the same reason.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.clinical_record import (
    AnamnesisCreate,
    AnamnesisResponse,
    ClinicalRecordCreate,
    ClinicalRecordListItem,
    ClinicalRecordListResponse,
    ClinicalRecordResponse,
    ClinicalRecordUpdate,
)
from app.services.clinical_record_service import clinical_record_service

router = APIRouter(prefix="/patients/{patient_id}", tags=["clinical-records"])


# ─── CR-05: Create / upsert anamnesis ────────────────────────────────────────
# Registered FIRST to prevent collision with /{record_id}.


@router.post("/anamnesis", response_model=AnamnesisResponse, status_code=201)
async def create_anamnesis(
    patient_id: str,
    body: AnamnesisCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("clinical_records:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> AnamnesisResponse:
    """Create or replace the medical anamnesis for a patient.

    This is an upsert operation — if an anamnesis record already exists
    for the patient, it is updated in place. Only provided sections are
    applied; omitted sections are left unchanged.

    Emits an upsert audit event on success. No PHI is included in the
    audit change log.
    """
    result = await clinical_record_service.create_anamnesis(
        db=db,
        patient_id=patient_id,
        user_id=current_user.user_id,
        **body.model_dump(),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="upsert",
        resource_type="anamnesis",
        resource_id=patient_id,
    )

    return AnamnesisResponse(**result)


# ─── CR-06: Get anamnesis ─────────────────────────────────────────────────────


@router.get("/anamnesis", response_model=AnamnesisResponse)
async def get_anamnesis(
    patient_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> AnamnesisResponse:
    """Return the medical anamnesis for a patient.

    Returns 404 if no anamnesis has been recorded yet. No audit event is
    emitted (read-only).
    """
    result = await clinical_record_service.get_anamnesis(
        db=db,
        patient_id=patient_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="CLINICAL_anamnesis_not_found",
            resource_name="Anamnesis",
        )
    return AnamnesisResponse(**result)


# ─── CR-01: Create clinical record ────────────────────────────────────────────


@router.post("/clinical-records", response_model=ClinicalRecordResponse, status_code=201)
async def create_clinical_record(
    patient_id: str,
    body: ClinicalRecordCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("clinical_records:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClinicalRecordResponse:
    """Create a new clinical record entry for a patient.

    Accepted types: examination, evolution_note, procedure. Use the
    dedicated /anamnesis endpoint for anamnesis records.

    Emits a create audit event on success.
    """
    result = await clinical_record_service.create_record(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        type=body.type,
        content=body.content,
        tooth_numbers=body.tooth_numbers,
        template_id=body.template_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="clinical_record",
        resource_id=result["id"],
    )

    return ClinicalRecordResponse(**result)


# ─── CR-03: List clinical records ─────────────────────────────────────────────
# Registered BEFORE CR-02 (/{record_id}) to avoid path collision.


@router.get("/clinical-records", response_model=ClinicalRecordListResponse)
async def list_clinical_records(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    type: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClinicalRecordListResponse:
    """Return a paginated list of clinical records for a patient.

    Optionally filtered by record type. Records are ordered newest-first.
    No audit event is emitted (read-only).
    """
    result = await clinical_record_service.list_records(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
        type=type,
    )
    return ClinicalRecordListResponse(
        items=[ClinicalRecordListItem(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ─── CR-02: Get clinical record detail ────────────────────────────────────────


@router.get("/clinical-records/{record_id}", response_model=ClinicalRecordResponse)
async def get_clinical_record(
    patient_id: str,
    record_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClinicalRecordResponse:
    """Return full detail for a single clinical record.

    Returns 404 if the record does not exist or belongs to a different patient.
    No audit event is emitted (read-only).
    """
    result = await clinical_record_service.get_record(
        db=db,
        patient_id=patient_id,
        record_id=record_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="CLINICAL_record_not_found",
            resource_name="ClinicalRecord",
        )
    return ClinicalRecordResponse(**result)


# ─── CR-04: Update clinical record ────────────────────────────────────────────


@router.put("/clinical-records/{record_id}", response_model=ClinicalRecordResponse)
async def update_clinical_record(
    patient_id: str,
    record_id: str,
    body: ClinicalRecordUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("clinical_records:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClinicalRecordResponse:
    """Update an existing clinical record.

    Records can only be edited within their edit window (24 hours after
    creation by default). Attempting to update a locked record returns 422.

    Only content and tooth_numbers are updatable — type and doctor_id are
    immutable after creation. Emits an update audit event on success.
    """
    result = await clinical_record_service.update_record(
        db=db,
        patient_id=patient_id,
        record_id=record_id,
        user_id=current_user.user_id,
        content=body.content,
        tooth_numbers=body.tooth_numbers,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="clinical_record",
        resource_id=record_id,
    )

    return ClinicalRecordResponse(**result)
