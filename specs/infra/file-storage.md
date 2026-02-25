# File Storage Architecture Spec

> **Spec ID:** I-17
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** File storage architecture for DentalOS using S3-compatible Hetzner Object Storage. Covers bucket structure, upload flow (presigned URLs for direct browser upload), access control (tenant-isolated signed URLs), virus scanning (ClamAV), thumbnail generation, and file lifecycle management. This spec describes the storage architecture; INT-08 (cloud-storage.md) covers the integration client details.

**Domain:** infra

**Priority:** Critical

**Dependencies:** INT-08 (cloud-storage integration), I-10 (security-policy), I-12 (data-retention), I-16 (backup-DR), I-14 (deployment-architecture)

---

## 1. File Type Definitions and Constraints

### File Types

| File Type | Path | Allowed MIME Types | Max Size | Notes |
|-----------|------|--------------------|---------|-------|
| `xrays` | `{tenant_id}/xrays/{year}/{month}/` | `image/jpeg`, `image/png`, `application/dicom` | 100 MB | Dental radiographs. DICOM requires specialized viewer. |
| `intraoral_photos` | `{tenant_id}/intraoral_photos/{year}/{month}/` | `image/jpeg`, `image/png` | 10 MB | Intraoral and facial photos. Thumbnails generated. |
| `documents` | `{tenant_id}/documents/{year}/{month}/` | `application/pdf`, `image/jpeg`, `image/png` | 50 MB | Lab results, referrals, imported scans. |
| `consent_pdfs` | `{tenant_id}/consent_pdfs/{year}/{month}/` | `application/pdf` | 5 MB | System-generated. Never user-uploaded. |
| `invoice_pdfs` | `{tenant_id}/invoice_pdfs/{year}/{month}/` | `application/pdf` | 5 MB | System-generated. Never user-uploaded. |
| `avatars` | `{tenant_id}/avatars/` | `image/jpeg`, `image/png` | 2 MB | Patient and user profile photos. Thumbnails generated. |
| `imports` | `{tenant_id}/imports/{year}/{month}/` | `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | 5 MB | Patient import files. Deleted after 30 days. |
| `voice_recordings` | `{tenant_id}/voice_recordings/{year}/{month}/` | `audio/webm`, `audio/wav`, `audio/mp4`, `audio/ogg` | 50 MB | Voice-to-Odontogram (add-on). Deleted after 1 year. |
| `thumbnails` | `{tenant_id}/thumbnails/{year}/{month}/` | `image/jpeg` | — | System-generated thumbnails. Not user-accessible directly. |

### File Size Enforcement

```python
FILE_SIZE_LIMITS = {
    "xrays": 100 * 1024 * 1024,           # 100 MB
    "intraoral_photos": 10 * 1024 * 1024,  # 10 MB
    "documents": 50 * 1024 * 1024,         # 50 MB
    "consent_pdfs": 5 * 1024 * 1024,       # 5 MB
    "invoice_pdfs": 5 * 1024 * 1024,       # 5 MB
    "avatars": 2 * 1024 * 1024,            # 2 MB
    "imports": 5 * 1024 * 1024,            # 5 MB
    "voice_recordings": 50 * 1024 * 1024,  # 50 MB
}

ALLOWED_MIMES = {
    "xrays": {"image/jpeg", "image/png", "application/dicom"},
    "intraoral_photos": {"image/jpeg", "image/png"},
    "documents": {"application/pdf", "image/jpeg", "image/png"},
    "consent_pdfs": {"application/pdf"},
    "invoice_pdfs": {"application/pdf"},
    "avatars": {"image/jpeg", "image/png"},
    "imports": {
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    "voice_recordings": {"audio/webm", "audio/wav", "audio/mp4", "audio/ogg"},
}
```

---

## 2. Bucket Structure

### Buckets

| Bucket | Environment | Purpose |
|--------|------------|---------|
| `dentalos-prod` | Production | All tenant files |
| `dentalos-staging` | Staging | Staging environment |
| `dentalos-dev` | Development (MinIO) | Local dev |
| `dentalos-backups` | Production | DB backups, WAL |

### Object Key Naming Convention

```
{tenant_id}/{file_type}/{year}/{month}/{uuid}{ext}
```

**Examples:**

```
# X-ray
abc12345-def6-7890-abcd-ef1234567890/xrays/2026/04/f47ac10b-58cc-4372-a567-0e02b2c3d479.dcm

# Intraoral photo
abc12345-def6-7890-abcd-ef1234567890/intraoral_photos/2026/04/550e8400-e29b-41d4-a716-446655440000.jpg

# Generated thumbnail (same UUID, different prefix)
abc12345-def6-7890-abcd-ef1234567890/thumbnails/2026/04/550e8400-e29b-41d4-a716-446655440000.jpg

# Archived file (moved after 1 year)
abc12345-def6-7890-abcd-ef1234567890/archive/xrays/2025/04/f47ac10b-58cc-4372-a567-0e02b2c3d479.dcm
```

### Key Design Principles

1. **No patient identifiers in keys** — keys use UUID file IDs only, not patient names or document numbers
2. **Tenant prefix as first segment** — enables tenant-level operations (delete all, archive all) via S3 prefix operations
3. **Year/month partitioning** — enables efficient lifecycle policy targeting by date prefix
4. **Archive prefix** — files moved to `archive/` prefix after 1 year for storage tiering

---

## 3. Upload Flow (Presigned URL)

### Flow Overview

```
Browser → DentalOS API → S3
                │
Step 1: Request presigned PUT URL
        Browser: POST /api/v1/files/upload-url
        API: validate request, generate presigned URL, create pending file record
        Returns: {file_id, upload_url, expires_at, required_headers}

Step 2: Direct upload to S3
        Browser: PUT {upload_url} with file binary
        S3: stores file
        Returns: 200 OK

Step 3: Confirm upload
        Browser: POST /api/v1/files/{file_id}/confirm
        API: trigger post-upload processing
        Returns: {status: "processing"}

Step 4: Async processing (RabbitMQ worker)
        Worker: download file, virus scan, thumbnail (if image)
        Worker: update file status to "ready"
        Worker: (optional) send webhook/event to frontend
```

### Step 1: Request Presigned URL

**Endpoint:** `POST /api/v1/files/upload-url`

**Request:**

```json
{
  "file_type": "intraoral_photos",
  "content_type": "image/jpeg",
  "filename": "foto_superior_2026.jpg",
  "file_size": 3456789,
  "patient_id": "uuid",
  "context": "clinical_record",
  "context_id": "uuid"
}
```

**Validation:**

```python
from pydantic import BaseModel, field_validator
from typing import Optional


class UploadUrlRequest(BaseModel):
    file_type: str
    content_type: str
    filename: str
    file_size: int
    patient_id: Optional[str] = None
    context: Optional[str] = None
    context_id: Optional[str] = None

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v):
        allowed = set(FILE_SIZE_LIMITS.keys())
        if v not in allowed:
            raise ValueError(f"Tipo de archivo inválido. Permitidos: {', '.join(sorted(allowed))}")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v, info):
        file_type = info.data.get("file_type")
        if file_type and v not in ALLOWED_MIMES.get(file_type, set()):
            raise ValueError(f"Tipo de contenido '{v}' no permitido para '{file_type}'")
        return v

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v, info):
        file_type = info.data.get("file_type")
        max_size = FILE_SIZE_LIMITS.get(file_type, 0)
        if max_size and v > max_size:
            max_mb = max_size // (1024 * 1024)
            raise ValueError(f"Archivo demasiado grande. Máximo: {max_mb} MB")
        if v <= 0:
            raise ValueError("Tamaño de archivo inválido")
        return v
```

**Response:**

```json
{
  "file_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "upload_url": "https://fsn1.your-objectstorage.com/dentalos-prod/...?X-Amz-...",
  "upload_method": "PUT",
  "upload_expires_at": "2026-04-15T11:00:00Z",
  "required_headers": {
    "Content-Type": "image/jpeg",
    "x-amz-meta-tenant-id": "abc123",
    "x-amz-meta-file-id": "f47ac10b-..."
  }
}
```

### Step 2: Browser PUT (Direct to S3)

The browser performs a `PUT` request directly to the presigned URL. DentalOS API is not involved in the data transfer.

```javascript
// Frontend: upload to presigned URL
const uploadFile = async (file, uploadUrl, requiredHeaders) => {
  await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": file.type,
      ...requiredHeaders,
    },
    body: file,
  });
};
```

### Step 3: Confirm Upload

**Endpoint:** `POST /api/v1/files/{file_id}/confirm`

```python
@router.post("/api/v1/files/{file_id}/confirm")
async def confirm_upload(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Called after direct S3 upload completes.
    Verifies file exists in S3 and triggers processing queue.
    """
    file_record = await get_file_record(session, file_id)

    if not file_record or file_record.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "Archivo no encontrado")

    if file_record.status != "pending_upload":
        raise HTTPException(409, "El archivo ya fue confirmado")

    # Verify file exists in S3
    storage = StorageService()
    if not storage.object_exists(file_record.object_key):
        raise HTTPException(400, "El archivo no fue subido correctamente. Intenta de nuevo.")

    # Update status and trigger processing
    file_record.status = "processing"
    await session.commit()

    # Enqueue processing job
    await enqueue_file_processing({
        "file_id": file_id,
        "tenant_id": current_user.tenant_id,
        "object_key": file_record.object_key,
        "file_type": file_record.file_type,
        "content_type": file_record.content_type,
    })

    return {"status": "processing", "file_id": file_id}
```

---

## 4. Post-Upload Processing (Async Worker)

### Processing Pipeline

```python
from PIL import Image
import io
import clamd
import logging

logger = logging.getLogger(__name__)


class FileProcessingWorker:
    """
    Processes uploaded files:
    1. Download from S3
    2. Virus scan (ClamAV)
    3. Image validation (if image)
    4. Thumbnail generation (if image)
    5. Update file status
    """

    async def process(self, job: dict) -> None:
        file_id = job["file_id"]
        tenant_id = job["tenant_id"]
        object_key = job["object_key"]
        file_type = job["file_type"]
        content_type = job["content_type"]

        storage = StorageService()

        try:
            # Step 1: Download
            file_bytes = await storage.download_object(object_key)

            # Step 2: Virus scan
            scan_result = await self._virus_scan(file_bytes)
            if not scan_result["is_clean"]:
                await storage.delete_object(object_key)
                await self._mark_failed(tenant_id, file_id, "virus_detected")
                logger.error(
                    "Virus detected in uploaded file",
                    extra={"tenant_id": tenant_id, "file_id": file_id,
                           "threat": scan_result.get("threat_name")}
                )
                await self._notify_virus_detection(tenant_id, file_id)
                return

            # Step 3: Image validation
            if content_type.startswith("image/") and content_type != "application/dicom":
                is_valid, error = self._validate_image(file_bytes)
                if not is_valid:
                    await storage.delete_object(object_key)
                    await self._mark_failed(tenant_id, file_id, f"invalid_image: {error}")
                    return

                # Step 4: Thumbnail generation
                thumbnail_key = self._build_thumbnail_key(object_key, file_type)
                await self._generate_thumbnail(file_bytes, storage, thumbnail_key)
                await self._update_thumbnail_key(tenant_id, file_id, thumbnail_key)

            # Step 5: Mark ready
            await self._mark_ready(tenant_id, file_id)
            logger.info(
                "File processing complete",
                extra={"tenant_id": tenant_id, "file_id": file_id}
            )

        except Exception as exc:
            logger.error(
                "File processing failed",
                extra={"tenant_id": tenant_id, "file_id": file_id, "error": str(exc)}
            )
            await self._mark_failed(tenant_id, file_id, str(exc))
            raise

    async def _virus_scan(self, file_bytes: bytes) -> dict:
        """Scan with ClamAV via Unix socket."""
        try:
            cd = clamd.ClamdUnixSocket()
            result = cd.instream(io.BytesIO(file_bytes))
            status, threat = result.get("stream", ["OK", ""])
            return {"is_clean": status == "OK", "threat_name": threat or None}
        except clamd.ConnectionError:
            logger.warning("ClamAV unavailable — scan skipped")
            return {"is_clean": True}  # Fail open

    def _validate_image(self, file_bytes: bytes) -> tuple[bool, str]:
        """Validate image file — format, dimensions, no decompression bombs."""
        try:
            img = Image.open(io.BytesIO(file_bytes))
            if img.format not in ("JPEG", "PNG"):
                return False, f"Format {img.format} not allowed"
            if img.width * img.height > 50_000_000:
                return False, "Image exceeds 50 megapixel limit"
            return True, ""
        except Exception as exc:
            return False, str(exc)

    async def _generate_thumbnail(
        self,
        source_bytes: bytes,
        storage: StorageService,
        thumbnail_key: str,
        max_size: tuple = (400, 400),
    ) -> None:
        """Generate JPEG thumbnail and upload to S3."""
        img = Image.open(io.BytesIO(source_bytes))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)

        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        thumbnail_bytes = output.getvalue()

        await storage.upload_bytes(
            key=thumbnail_key,
            data=thumbnail_bytes,
            content_type="image/jpeg",
        )

    def _build_thumbnail_key(self, original_key: str, file_type: str) -> str:
        """Build thumbnail key from original object key."""
        parts = original_key.split("/")
        tenant_id = parts[0]
        rest = "/".join(parts[2:])  # Skip file_type segment
        return f"{tenant_id}/thumbnails/{rest.rsplit('.', 1)[0]}.jpg"
```

---

## 5. Access Control and Signed URLs

### Signed URL Generation

```python
@router.get("/api/v1/files/{file_id}/url")
async def get_file_url(
    file_id: str,
    download: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Generate a signed URL for secure file access.
    Validates that requesting user has permission to access the file.
    """
    file_record = await get_file_record(session, file_id)

    if not file_record:
        raise HTTPException(404, "Archivo no encontrado")

    # Tenant isolation check
    if file_record.tenant_id != current_user.tenant_id:
        raise HTTPException(403, "Acceso denegado")

    # File status check
    if file_record.status != "ready":
        raise HTTPException(409, f"Archivo no disponible (estado: {file_record.status})")

    # Role-based access check for clinical files
    if file_record.file_type in ("xrays", "intraoral_photos", "documents"):
        if current_user.role == "receptionist" and not await has_patient_access(
            session, current_user.id, file_record.patient_id
        ):
            raise HTTPException(403, "No tienes permiso para ver este archivo clínico")

    # Patient self-access (portal)
    if current_user.role == "patient":
        if file_record.patient_id != current_user.patient_id:
            raise HTTPException(403, "Acceso denegado")
        if file_record.file_type not in ("consent_pdfs", "invoice_pdfs", "intraoral_photos"):
            raise HTTPException(403, "Los pacientes solo pueden acceder a consentimientos y facturas")

    # Generate signed URL
    expiry_map = {
        "xrays": 3600,           # 1 hour
        "intraoral_photos": 3600,
        "documents": 3600,
        "consent_pdfs": 86400,   # 24 hours
        "invoice_pdfs": 86400,
        "avatars": 604800,       # 7 days
        "voice_recordings": 3600,
    }

    expiry = expiry_map.get(file_record.file_type, 3600)
    storage = StorageService()
    filename_override = file_record.original_filename if download else None

    signed_url = storage.generate_presigned_get_url(
        key=file_record.object_key,
        expiry=expiry,
        filename_override=filename_override,
    )

    # Audit log for clinical file access
    if file_record.file_type in ("xrays", "intraoral_photos", "documents"):
        await audit_log(
            session, "read", "file", file_id, phi=True,
            metadata={"file_type": file_record.file_type}
        )

    return {
        "file_id": file_id,
        "url": signed_url,
        "expires_at": (datetime.utcnow() + timedelta(seconds=expiry)).isoformat(),
        "content_type": file_record.content_type,
        "filename": file_record.original_filename,
    }
```

---

## 6. File Soft Deletion

Files are never hard-deleted except by the lifecycle policy (retention). The `deleted_at` field marks a soft delete:

```python
@router.delete("/api/v1/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(require_roles(["doctor", "clinic_owner"])),
    session: AsyncSession = Depends(get_session),
):
    """
    Soft-delete a file. Clinical files (xrays, photos) cannot be deleted
    while the associated clinical record is within the retention period.
    """
    file_record = await get_file_record(session, file_id)

    if file_record.file_type in ("xrays", "intraoral_photos", "documents"):
        # Check retention period before allowing deletion
        country = await get_tenant_country(current_user.tenant_id)
        policy = get_retention_policy(country)
        if not await can_delete_clinical_file(session, file_record, policy):
            raise HTTPException(
                403,
                "Este archivo clínico no puede eliminarse durante el período de retención legal"
            )

    # Soft delete — S3 object kept, DB record marked
    file_record.deleted_at = datetime.utcnow()
    file_record.status = "deleted"
    await session.commit()

    await audit_log(session, "delete", "file", file_id, phi=True)
    return {"status": "deleted"}
```

---

## 7. File Metadata Table (Tenant Schema)

```sql
CREATE TABLE files (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_type           VARCHAR(30) NOT NULL
                        CHECK (file_type IN (
                            'xrays', 'intraoral_photos', 'documents',
                            'consent_pdfs', 'invoice_pdfs', 'avatars',
                            'imports', 'voice_recordings'
                        )),
    object_key          VARCHAR(500) NOT NULL,
    thumbnail_key       VARCHAR(500),
    original_filename   VARCHAR(255) NOT NULL,
    content_type        VARCHAR(100) NOT NULL,
    file_size           BIGINT NOT NULL CHECK (file_size > 0),
    status              VARCHAR(30) NOT NULL DEFAULT 'pending_upload'
                        CHECK (status IN (
                            'pending_upload', 'processing', 'ready',
                            'virus_detected', 'failed', 'deleted', 'archived'
                        )),
    patient_id          UUID,
    uploaded_by         UUID NOT NULL,
    context             VARCHAR(50),        -- clinical_record | consent | invoice | voice | import
    context_id          UUID,              -- FK to the related record
    is_archived         BOOLEAN DEFAULT FALSE,
    archived_at         TIMESTAMPTZ,
    archive_key         VARCHAR(500),       -- S3 key after archival
    deleted_at          TIMESTAMPTZ,        -- Soft delete
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_files_patient_id
    ON files(patient_id)
    WHERE patient_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX idx_files_context
    ON files(context, context_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_files_type_status
    ON files(file_type, status)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_files_created_at
    ON files(created_at)
    WHERE deleted_at IS NULL;
```

---

## 8. System-Generated Files (Consent PDFs, Invoice PDFs)

These files are generated by DentalOS workers and uploaded directly to S3 (no presigned URL flow):

```python
async def store_generated_pdf(
    tenant_id: str,
    file_type: str,          # "consent_pdfs" or "invoice_pdfs"
    pdf_bytes: bytes,
    filename: str,
    context: str,
    context_id: str,
) -> str:
    """
    Store a system-generated PDF directly to S3.
    Returns the file_id for later access.
    """
    file_id = str(uuid.uuid4())
    now = datetime.utcnow()
    year_month = now.strftime("%Y/%m")
    object_key = f"{tenant_id}/{file_type}/{year_month}/{file_id}.pdf"

    storage = StorageService()
    await storage.upload_bytes(
        key=object_key,
        data=pdf_bytes,
        content_type="application/pdf",
        metadata={
            "tenant-id": tenant_id,
            "file-id": file_id,
            "generated-by": "system",
        }
    )

    async with get_tenant_session(tenant_id) as session:
        await create_file_record(session, {
            "id": file_id,
            "file_type": file_type,
            "object_key": object_key,
            "original_filename": filename,
            "content_type": "application/pdf",
            "file_size": len(pdf_bytes),
            "status": "ready",
            "uploaded_by": "system",
            "context": context,
            "context_id": context_id,
        })

    return file_id
```

---

## 9. Storage Quotas per Plan

```python
STORAGE_QUOTAS_GB = {
    "free": 1,        # 1 GB — very limited, clinical use only
    "starter": 10,    # 10 GB per doctor
    "pro": 25,        # 25 GB per doctor
    "clinica": 100,   # 100 GB per location
    "enterprise": 0,  # Unlimited (negotiated)
}


async def check_storage_quota(
    tenant_id: str,
    file_size_bytes: int,
) -> None:
    """
    Check if uploading this file would exceed the tenant's storage quota.
    Raises StorageQuotaExceeded if limit would be exceeded.
    """
    plan = await get_tenant_plan(tenant_id)
    quota_gb = STORAGE_QUOTAS_GB.get(plan, 10)

    if quota_gb == 0:
        return  # Unlimited

    used_bytes = await get_tenant_storage_used(tenant_id)
    quota_bytes = quota_gb * 1024 * 1024 * 1024

    if used_bytes + file_size_bytes > quota_bytes:
        raise StorageQuotaExceeded(
            f"Límite de almacenamiento alcanzado. "
            f"Usado: {used_bytes // (1024**3):.1f} GB / "
            f"{quota_gb} GB. "
            f"Actualiza tu plan para más almacenamiento."
        )
```

---

## 10. Local Development (MinIO)

```yaml
# docker-compose.yml (excerpt)
services:
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"    # S3 API
      - "9001:9001"    # Web console
    environment:
      MINIO_ROOT_USER: dentalos_dev
      MINIO_ROOT_PASSWORD: dentalos_dev_secret
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Create default bucket on startup
  minio-setup:
    image: minio/mc:latest
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set minio http://minio:9000 dentalos_dev dentalos_dev_secret;
      mc mb minio/dentalos-dev --ignore-existing;
      mc anonymous set none minio/dentalos-dev;
      "
```

**Development environment variables:**

```
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=dentalos_dev
S3_SECRET_KEY=dentalos_dev_secret
S3_BUCKET_NAME=dentalos-dev
S3_REGION=us-east-1
```

---

## 11. CORS Configuration

For direct browser uploads to Hetzner Object Storage, CORS must be configured on the bucket:

```python
def configure_bucket_cors(bucket_name: str, allowed_origins: list) -> None:
    """Configure CORS policy for direct browser uploads."""
    s3_client = get_s3_client()
    s3_client.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedOrigins": allowed_origins,
                    "AllowedMethods": ["PUT"],
                    "AllowedHeaders": [
                        "Content-Type",
                        "x-amz-meta-*",
                    ],
                    "MaxAgeSeconds": 3600,
                }
            ]
        }
    )
```

---

## Out of Scope

- DICOM viewer integration — files stored as DICOM, viewing via external app
- Video file support — not planned for v1
- CDN for file delivery — signed URLs served directly from Hetzner S3
- Client-side encryption before upload — server-side encryption at rest is sufficient
- Full-text search over document contents

---

## Acceptance Criteria

**This spec is complete when:**

- [ ] All upload flows work end-to-end (presigned URL → confirm → processing → ready)
- [ ] Virus scan rejects infected files (tested with EICAR test file)
- [ ] Thumbnails generated for all JPEG/PNG uploads
- [ ] Signed GET URL returns working link expiring after configured duration
- [ ] Tenant A cannot access tenant B files via DentalOS API
- [ ] Patient can only access their own consent PDFs and invoice PDFs
- [ ] System-generated PDFs stored and accessible via file API
- [ ] Storage quota enforced per plan
- [ ] MinIO works identically to Hetzner S3 in local dev
- [ ] CORS configured for direct browser upload

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
