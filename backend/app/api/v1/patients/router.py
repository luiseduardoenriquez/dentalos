"""Patient API routes — P-01 through P-10, P-15.

Endpoint map:
  GET  /patients/search          — P-01: Type-ahead search (any staff)
  GET  /patients/                — P-02: Paginated list   (any staff)
  GET  /patients/export          — P-09: CSV export        (clinic_owner)
  POST /patients/import          — P-08: CSV import        (clinic_owner)
  GET  /patients/import/{job_id} — P-08: Import job status (staff)
  POST /patients/merge           — P-10: Merge patients    (clinic_owner)
  GET  /patients/{patient_id}    — P-03: Get detail       (any staff)
  POST /patients/                — P-04: Create patient   (patients:write)
  PUT  /patients/{patient_id}    — P-05: Update patient   (patients:write)
  POST /patients/{patient_id}/deactivate — P-06: Soft-delete (clinic_owner)
  POST /patients/{patient_id}/referrals  — P-15: Create referral (doctor)
  GET  /patients/{patient_id}/referrals  — P-15: List referrals  (staff)

IMPORTANT: /search, /export, /import, /merge are registered BEFORE
           /{patient_id} so FastAPI does not treat them as UUID path parameters.
"""

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission, require_role
from app.core.audit import audit_action
from app.core.cache import get_cached, set_cached
from app.core.database import get_tenant_db
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.queue import publish_message
from app.core.storage import storage_client
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
from app.schemas.patient_import import (
    PatientExportParams,
    PatientImportJobResponse,
    PatientMergeRequest,
    PatientMergeResponse,
)
from app.schemas.portal import (
    PortalAccessGrantResponse,
    PortalAccessRequest,
    PortalAccessRevokeResponse,
)
from app.schemas.queue import QueueMessage
from app.services.medical_history_service import medical_history_service
from app.services.patient_document_service import patient_document_service
from app.services.patient_service import patient_service
from app.services.portal_access_service import portal_access_service

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


# ─── P-09: Export CSV ────────────────────────────────────────────────────────
# Registered BEFORE /{patient_id} to avoid path collision.


@router.get("/export")
async def export_patients(
    is_active: bool | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    request: Request = None,  # type: ignore[assignment]
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner"])
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> StreamingResponse:
    """Export patients to CSV (clinic_owner only).

    Streams the CSV response row by row so that large patient lists
    never need to be buffered entirely in memory. The exported file
    contains demographic data only -- no clinical PHI beyond what is
    stored on the patient record itself.
    """
    # Also enforce patients:read permission
    if "patients:read" not in current_user.permissions:
        raise DentalOSError(
            error="AUTH_insufficient_permission",
            message="Missing required permission: patients:read",
            status_code=403,
        )

    today = date.today().isoformat()
    filename = f"pacientes_{today}.csv"

    csv_generator = patient_service.export_patients_csv(
        db=db,
        is_active=is_active,
        created_from=created_from,
        created_to=created_to,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="export",
        resource_type="patient",
    )

    return StreamingResponse(
        csv_generator,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ─── P-08: Import CSV ────────────────────────────────────────────────────────
# Registered BEFORE /{patient_id} to avoid path collision.


_REQUIRED_CSV_HEADERS = {
    "tipo_documento",
    "numero_documento",
    "nombres",
    "apellidos",
}

_IMPORT_JOB_TTL = 86400  # 24 hours


@router.post("/import", response_model=PatientImportJobResponse, status_code=202)
async def import_patients(
    request: Request,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner"])
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientImportJobResponse:
    """Import patients from a CSV file (clinic_owner only).

    Validates the CSV header, uploads the file to S3, and enqueues
    a background job for processing. Returns 202 with a job ID that
    can be polled via GET /patients/import/{job_id}.

    The file must be a CSV with at least the required columns:
    tipo_documento, numero_documento, nombres, apellidos.
    """
    # Also enforce patients:write permission
    if "patients:write" not in current_user.permissions:
        raise DentalOSError(
            error="AUTH_insufficient_permission",
            message="Missing required permission: patients:write",
            status_code=403,
        )

    # Validate file type
    content_type = file.content_type or ""
    filename = file.filename or ""
    if (
        "csv" not in content_type.lower()
        and not filename.lower().endswith(".csv")
    ):
        raise DentalOSError(
            error="VALIDATION_invalid_file_type",
            message="El archivo debe ser un CSV.",
            status_code=400,
        )

    # Read and validate CSV header
    raw_bytes = await file.read()
    try:
        text_content = raw_bytes.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        raise DentalOSError(
            error="VALIDATION_invalid_encoding",
            message="El archivo CSV debe usar codificación UTF-8.",
            status_code=400,
        )

    # Parse first line for header validation
    import csv as csv_mod
    import io

    reader = csv_mod.reader(io.StringIO(text_content))
    try:
        header_row = next(reader)
    except StopIteration:
        raise DentalOSError(
            error="VALIDATION_empty_file",
            message="El archivo CSV está vacío.",
            status_code=400,
        )

    header_normalized = {col.strip().lower() for col in header_row}
    missing_cols = _REQUIRED_CSV_HEADERS - header_normalized
    if missing_cols:
        raise DentalOSError(
            error="VALIDATION_missing_columns",
            message=f"Columnas requeridas faltantes: {', '.join(sorted(missing_cols))}.",
            status_code=400,
            details={"missing_columns": sorted(missing_cols)},
        )

    # Count total rows (excluding header)
    total_rows = sum(1 for _ in reader)

    # Generate job ID and S3 path
    job_id = str(uuid.uuid4())
    tenant_id = current_user.tenant.tenant_id
    s3_path = f"{tenant_id}/imports/{job_id}.csv"

    # Upload CSV to S3
    await storage_client.upload_file(
        key=s3_path,
        data=raw_bytes,
        content_type="text/plain",
    )

    # Store initial job status in Redis
    now = datetime.now(UTC).isoformat()
    job_data = {
        "job_id": job_id,
        "status": "queued",
        "total_rows": total_rows,
        "processed_rows": 0,
        "error_rows": 0,
        "error_csv_url": None,
        "created_at": now,
    }
    redis_key = f"dentalos:{tenant_id[:8]}:import:jobs:{job_id}"
    await set_cached(redis_key, job_data, ttl_seconds=_IMPORT_JOB_TTL)

    # Enqueue import job
    message = QueueMessage(
        tenant_id=tenant_id,
        job_type="patient.import",
        payload={
            "job_id": job_id,
            "s3_path": s3_path,
            "tenant_id": tenant_id,
            "total_rows": total_rows,
        },
        priority=5,
    )
    await publish_message("import", message)

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="import",
        resource_type="patient",
        resource_id=job_id,
    )

    return PatientImportJobResponse(**job_data)


@router.get("/import/{job_id}", response_model=PatientImportJobResponse)
async def get_import_job_status(
    job_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("patients:read")
    ),
) -> PatientImportJobResponse:
    """Poll the status of a patient import job.

    Reads job progress from Redis. Returns 404 if the job ID is not
    found (it may have expired after 24 hours).
    """
    tenant_id = current_user.tenant.tenant_id
    redis_key = f"dentalos:{tenant_id[:8]}:import:jobs:{job_id}"
    job_data = await get_cached(redis_key)

    if job_data is None:
        raise ResourceNotFoundError(
            error="PATIENT_import_job_not_found",
            resource_name="Import Job",
        )

    return PatientImportJobResponse(**job_data)


# ─── P-10: Merge ─────────────────────────────────────────────────────────────
# Registered BEFORE /{patient_id} to avoid path collision.


@router.post("/merge", response_model=PatientMergeResponse)
async def merge_patients(
    body: PatientMergeRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner"])
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientMergeResponse:
    """Merge two patient records (clinic_owner only).

    Transfers all clinical records from the secondary patient to the
    primary patient and deactivates the secondary. This operation is
    irreversible and runs in a single database transaction.
    """
    # Also enforce patients:delete permission
    if "patients:delete" not in current_user.permissions:
        raise DentalOSError(
            error="AUTH_insufficient_permission",
            message="Missing required permission: patients:delete",
            status_code=403,
        )

    result = await patient_service.merge_patients(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        primary_patient_id=str(body.primary_patient_id),
        secondary_patient_id=str(body.secondary_patient_id),
        merged_by_id=current_user.user_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="merge",
        resource_type="patient",
        resource_id=result["primary_patient_id"],
        changes={
            "secondary_patient_id": str(body.secondary_patient_id),
            "merged_records": result["merged_records"],
        },
    )

    return PatientMergeResponse(**result)


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


# ─── P-11: Portal Access ─────────────────────────────────────────────────────


@router.post(
    "/{patient_id}/portal-access",
    response_model=PortalAccessGrantResponse | PortalAccessRevokeResponse,
)
async def manage_portal_access(
    patient_id: str,
    body: PortalAccessRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner", "doctor", "receptionist"])
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalAccessGrantResponse | PortalAccessRevokeResponse:
    """Grant or revoke portal access for a patient (P-11).

    Clinic owners, doctors, and receptionists can manage portal access.
    """
    if body.action == "grant":
        result = await portal_access_service.grant_access(
            db=db,
            patient_id=patient_id,
            invitation_channel=body.invitation_channel,
            created_by=current_user.user_id,
            tenant_id=current_user.tenant.tenant_id,
        )

        await audit_action(
            request=request,
            db=db,
            current_user=current_user,
            action="grant_portal_access",
            resource_type="patient",
            resource_id=patient_id,
        )

        return PortalAccessGrantResponse(**result)
    else:
        result = await portal_access_service.revoke_access(
            db=db,
            patient_id=patient_id,
            tenant_id=current_user.tenant.tenant_id,
        )

        await audit_action(
            request=request,
            db=db,
            current_user=current_user,
            action="revoke_portal_access",
            resource_type="patient",
            resource_id=patient_id,
        )

        return PortalAccessRevokeResponse(**result)


# ─── P-15: Referrals ─────────────────────────────────────────────────────────


from app.schemas.referral import ReferralCreate, ReferralListResponse, ReferralResponse
from app.services.referral_service import referral_service


@router.post(
    "/{patient_id}/referrals",
    response_model=ReferralResponse,
    status_code=201,
    tags=["referrals"],
)
async def create_referral(
    patient_id: str,
    body: ReferralCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner", "doctor"])
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ReferralResponse:
    """Create a patient referral to another doctor (P-15)."""
    result = await referral_service.create_referral(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        patient_id=patient_id,
        from_doctor_id=current_user.user_id,
        to_doctor_id=body.to_doctor_id,
        reason=body.reason,
        priority=body.priority,
        specialty=body.specialty,
        notes=body.notes,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="patient_referral",
        resource_id=result["id"],
    )

    return ReferralResponse(**result)


@router.get(
    "/{patient_id}/referrals",
    response_model=ReferralListResponse,
    tags=["referrals"],
)
async def list_referrals(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("patients:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ReferralListResponse:
    """List referrals for a patient (P-15)."""
    result = await referral_service.list_referrals(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return ReferralListResponse(
        items=[ReferralResponse(**r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
