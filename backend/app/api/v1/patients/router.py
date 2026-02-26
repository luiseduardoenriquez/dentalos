"""Patient API routes — P-01 through P-06.

Endpoint map:
  GET  /patients/search          — P-01: Type-ahead search (any staff)
  GET  /patients/                — P-02: Paginated list   (any staff)
  GET  /patients/{patient_id}    — P-03: Get detail       (any staff)
  POST /patients/                — P-04: Create patient   (patients:write)
  PUT  /patients/{patient_id}    — P-05: Update patient   (patients:write)
  POST /patients/{patient_id}/deactivate — P-06: Soft-delete (clinic_owner)

IMPORTANT: /search is registered BEFORE /{patient_id} so FastAPI does not
           treat the literal string "search" as a UUID path parameter.
"""

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission, require_role
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.medical_history import MedicalHistoryResponse
from app.schemas.patient import (
    PatientCreate,
    PatientListItem,
    PatientListResponse,
    PatientResponse,
    PatientSearchResponse,
    PatientSearchResult,
    PatientUpdate,
)
from app.schemas.patient_document import PatientDocumentListResponse, PatientDocumentResponse
from app.services.medical_history_service import medical_history_service
from app.services.patient_document_service import patient_document_service
from app.services.patient_service import patient_service

router = APIRouter(prefix="/patients", tags=["patients"])


# ─── P-01: Search ────────────────────────────────────────────────────────────
# Registered FIRST to avoid collision with /{patient_id}


@router.get("/search", response_model=PatientSearchResponse)
async def search_patients(
    q: str = Query(min_length=2, description="Search query — min 2 characters."),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientSearchResponse:
    """Type-ahead patient search using PostgreSQL FTS.

    Returns up to 10 matching patients ranked by relevance. Falls back
    to ILIKE on document_number and phone when FTS yields no results.

    Results are cached in Redis for 120 seconds per query per tenant.
    No audit event is emitted for searches (read-only, high frequency).
    """
    result = await patient_service.search_patients(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        q=q,
    )
    return PatientSearchResponse(
        data=[PatientSearchResult(**item) for item in result["data"]],
        count=result["count"],
    )


# ─── P-02: List ──────────────────────────────────────────────────────────────


@router.get("/", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=2),
    is_active: bool | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    sort_by: str = Query(default="last_name", pattern=r"^(last_name|created_at)$"),
    sort_order: str = Query(default="asc", pattern=r"^(asc|desc)$"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientListResponse:
    """Return a paginated list of patients.

    Supports full-text search over name and document number, date range
    filtering, and stable sorting. When `is_active` is omitted, only
    active patients are returned by default.
    """
    result = await patient_service.list_patients(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PatientListResponse(
        items=[PatientListItem(**p) for p in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


# ─── P-03: Get detail ────────────────────────────────────────────────────────


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    include_deleted: bool = Query(default=False),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientResponse:
    """Return full patient detail including clinical summary stub.

    Returns 404 if the patient does not exist or is inactive.
    `include_deleted=true` is available but restricted to clinic_owner
    and superadmin roles in a future permission check — for MVP it is
    accepted at the route level and the service filters accordingly.
    """
    # For include_deleted, only clinic owners should have access
    allow_deleted = include_deleted and current_user.role in ("clinic_owner", "superadmin")

    result = await patient_service.get_patient(
        db=db,
        patient_id=patient_id,
        include_deleted=allow_deleted,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="PATIENT_not_found",
            resource_name="Patient",
        )
    return PatientResponse(**result)


# ─── P-04: Create ────────────────────────────────────────────────────────────


@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(
    body: PatientCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("patients:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientResponse:
    """Register a new patient in the current tenant.

    Enforces plan-level patient limits (402) and document uniqueness (409).
    Emits a create audit event on success.
    """
    result = await patient_service.create_patient(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        created_by_id=current_user.user_id,
        document_type=body.document_type,
        document_number=body.document_number,
        first_name=body.first_name,
        last_name=body.last_name,
        birthdate=body.birthdate,
        gender=body.gender,
        phone=body.phone,
        phone_secondary=body.phone_secondary,
        email=str(body.email) if body.email else None,
        address=body.address,
        city=body.city,
        state_province=body.state_province,
        emergency_contact_name=body.emergency_contact_name,
        emergency_contact_phone=body.emergency_contact_phone,
        insurance_provider=body.insurance_provider,
        insurance_policy_number=body.insurance_policy_number,
        blood_type=body.blood_type,
        allergies=body.allergies,
        chronic_conditions=body.chronic_conditions,
        referral_source=body.referral_source,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="patient",
        resource_id=result["id"],
    )

    return PatientResponse(**result)


# ─── P-05: Update ────────────────────────────────────────────────────────────


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    body: PatientUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("patients:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientResponse:
    """Apply partial updates to an existing patient.

    All fields are optional. Only non-None fields are applied.
    Emits an update audit event on success.
    """
    # Build changes dict for audit log — exclude None fields to keep
    # the audit record clean and avoid logging PHI-adjacent field names
    # without values.
    changes = body.model_dump(exclude_none=True)

    result = await patient_service.update_patient(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        patient_id=patient_id,
        document_type=body.document_type,
        document_number=body.document_number,
        first_name=body.first_name,
        last_name=body.last_name,
        birthdate=body.birthdate,
        gender=body.gender,
        phone=body.phone,
        phone_secondary=body.phone_secondary,
        email=str(body.email) if body.email else None,
        address=body.address,
        city=body.city,
        state_province=body.state_province,
        emergency_contact_name=body.emergency_contact_name,
        emergency_contact_phone=body.emergency_contact_phone,
        insurance_provider=body.insurance_provider,
        insurance_policy_number=body.insurance_policy_number,
        blood_type=body.blood_type,
        allergies=body.allergies,
        chronic_conditions=body.chronic_conditions,
        referral_source=body.referral_source,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="patient",
        resource_id=patient_id,
        changes={k: v for k, v in changes.items() if k not in (
            # Exclude PHI-containing fields from audit changes dict.
            # The fact that they changed is logged; the values are not.
            "first_name", "last_name", "document_number", "phone",
            "phone_secondary", "email", "address", "emergency_contact_name",
            "emergency_contact_phone", "notes",
        )},
    )

    return PatientResponse(**result)


# ─── P-06: Deactivate ────────────────────────────────────────────────────────


@router.post("/{patient_id}/deactivate", response_model=PatientResponse)
async def deactivate_patient(
    patient_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientResponse:
    """Soft-deactivate a patient (clinic_owner only).

    Sets is_active=False and records deleted_at timestamp. The patient
    record is preserved permanently for regulatory compliance
    (Resolución 1888 — clinical data is never hard-deleted).

    Returns 404 if the patient is not found or already inactive.
    Emits a deactivate audit event on success.
    """
    result = await patient_service.deactivate_patient(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        patient_id=patient_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="deactivate",
        resource_type="patient",
        resource_id=patient_id,
    )

    return PatientResponse(**result)


# ─── Medical History: Unified timeline ───────────────────────────────────────


@router.get("/{patient_id}/medical-history", response_model=MedicalHistoryResponse)
async def get_medical_history(
    patient_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> MedicalHistoryResponse:
    """Return unified medical history timeline for a patient."""
    result = await medical_history_service.get_timeline(
        db=db,
        patient_id=patient_id,
        cursor=cursor,
        limit=limit,
    )
    return MedicalHistoryResponse(**result)


# ─── P-12: List Documents ──────────────────────────────────────────────────────


@router.get("/{patient_id}/documents", response_model=PatientDocumentListResponse)
async def list_patient_documents(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    document_type: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientDocumentListResponse:
    """List documents for a patient with optional type filter."""
    result = await patient_document_service.list_documents(
        db=db,
        patient_id=patient_id,
        document_type=document_type,
        page=page,
        page_size=page_size,
    )
    return PatientDocumentListResponse(**result)


# ─── P-13: Upload Document ─────────────────────────────────────────────────────


@router.post("/{patient_id}/documents", response_model=PatientDocumentResponse, status_code=201)
async def upload_patient_document(
    patient_id: str,
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    description: str | None = Form(default=None),
    tooth_number: int | None = Form(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("patients:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientDocumentResponse:
    """Upload a document for a patient.

    Accepts multipart form data with the file and metadata fields.
    Validates MIME type and file size. Stores in S3 with tenant-scoped path.
    """
    file_data = await file.read()
    result = await patient_document_service.upload_document(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        patient_id=patient_id,
        uploaded_by=current_user.user_id,
        file_data=file_data,
        file_name=file.filename or "unnamed",
        file_size=len(file_data),
        mime_type=file.content_type or "application/octet-stream",
        document_type=document_type,
        description=description,
        tooth_number=tooth_number,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="upload",
        resource_type="patient_document",
        resource_id=result["id"],
    )

    return PatientDocumentResponse(**result)


# ─── P-14: Delete Document ─────────────────────────────────────────────────────


@router.delete("/{patient_id}/documents/{document_id}", response_model=PatientDocumentResponse)
async def delete_patient_document(
    patient_id: str,
    document_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("patients:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientDocumentResponse:
    """Soft-delete a patient document.

    Clinical data is never hard-deleted (Resolución 1888).
    The file remains in S3 for regulatory compliance.
    """
    result = await patient_document_service.delete_document(
        db=db,
        patient_id=patient_id,
        document_id=document_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="delete",
        resource_type="patient_document",
        resource_id=document_id,
    )

    return PatientDocumentResponse(**result)
