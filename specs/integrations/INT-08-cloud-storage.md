# Cloud Storage Integration Spec

> **Spec ID:** INT-08
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** S3-compatible object storage integration for storing dental X-rays, intraoral photos, consent PDFs, invoice PDFs, and patient documents. Uses Hetzner Object Storage in production and MinIO in local development. Tenant-isolated path prefixes, signed URL access (no public URLs), ClamAV virus scanning, and async thumbnail generation. Lifecycle policies move cold files to archival storage after 1 year.

**Domain:** integrations / infra

**Priority:** Critical

**Dependencies:** I-10 (security-policy — file upload validation), I-14 (deployment-architecture), I-16 (backup-DR), patients domain (photo uploads), clinical-records domain (X-rays), billing domain (invoice PDFs), consents domain (consent PDFs)

---

## 1. Provider Strategy

### Production: Hetzner Object Storage

- **Compatible with:** AWS S3 API (boto3, s3cmd, rclone)
- **Endpoint:** `https://fsn1.your-objectstorage.com` (Falkenstein DC)
- **Protocol:** S3 REST API over HTTPS
- **Region:** `eu-central` (Hetzner Falkenstein)
- **Pricing:** ~$5/month per 1TB + €0.01/10,000 operations

### Local Development: MinIO

- **Mode:** Docker Compose service `minio`
- **Endpoint:** `http://minio:9000`
- **Console:** `http://localhost:9001`
- **Credentials:** `.env` file (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`)

### Client Library

```python
import boto3
from botocore.client import Config
from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name=settings.S3_REGION,
    )
```

---

## 2. Bucket Structure

### Buckets per Environment

| Environment | Bucket Name | Purpose |
|------------|------------|---------|
| Production | `dentalos-prod` | All production files |
| Staging | `dentalos-staging` | Staging environment |
| Development | `dentalos-dev` | Local dev (MinIO) |
| Backups | `dentalos-backups` | PostgreSQL WAL, config backups |

### Object Key (Path) Structure

```
{tenant_id}/{file_type}/{year}/{month}/{uuid}.{ext}
```

**Examples:**

```
# X-ray uploaded by tenant abc123, April 2026
abc123/xrays/2026/04/f47ac10b-58cc-4372-a567-0e02b2c3d479.dcm

# Intraoral photo
abc123/intraoral_photos/2026/04/550e8400-e29b-41d4-a716-446655440000.jpg

# Generated consent PDF
abc123/consent_pdfs/2026/04/6ba7b810-9dad-11d1-80b4-00c04fd430c8.pdf

# Generated invoice PDF
abc123/invoice_pdfs/2026/04/7c9e6679-7425-40de-944b-e07fc1f90ae7.pdf

# Patient avatar
abc123/avatars/2026/04/f5dc3b9e-1234-4567-89ab-cdef01234567.jpg
```

### File Type Definitions

| File Type | Path Segment | MIME Types | Max Size | Description |
|-----------|-------------|------------|---------|-------------|
| `xrays` | `xrays/` | `image/jpeg`, `image/png`, `application/dicom` | 100 MB | Dental radiographs (DICOM or JPEG) |
| `intraoral_photos` | `intraoral_photos/` | `image/jpeg`, `image/png` | 10 MB | Intraoral and facial photos |
| `documents` | `documents/` | `application/pdf`, `image/jpeg`, `image/png` | 50 MB | Lab results, referrals, external docs |
| `consent_pdfs` | `consent_pdfs/` | `application/pdf` | 5 MB | Generated consent form PDFs |
| `invoice_pdfs` | `invoice_pdfs/` | `application/pdf` | 5 MB | Generated invoice PDFs |
| `avatars` | `avatars/` | `image/jpeg`, `image/png` | 2 MB | Patient and user profile photos |
| `imports` | `imports/` | `text/csv`, `.xlsx` | 5 MB | Patient import files (temporary) |
| `voice_recordings` | `voice_recordings/` | `audio/webm`, `audio/wav`, `audio/mp4` | 50 MB | Voice-to-Odontogram recordings |

---

## 3. Upload Flow

### Presigned URL Upload (Recommended for Large Files)

The upload flow uses presigned URLs for direct browser-to-storage upload, avoiding file transfer through the DentalOS API server:

```
Browser                   DentalOS API              Hetzner S3
   │                          │                          │
   │  POST /files/upload-url  │                          │
   │─────────────────────────►│                          │
   │                          │  Generate presigned URL  │
   │                          │─────────────────────────►│
   │                          │  Presigned PUT URL       │
   │                          │◄─────────────────────────│
   │  {upload_url, file_id}   │                          │
   │◄─────────────────────────│                          │
   │                          │                          │
   │  PUT {upload_url} [file] │                          │
   │─────────────────────────────────────────────────────►
   │  200 OK                  │                          │
   │◄─────────────────────────────────────────────────────
   │                          │                          │
   │  POST /files/{id}/confirm│                          │
   │─────────────────────────►│                          │
   │                          │  ClamAV scan + metadata save
   │  {file_metadata}         │                          │
   │◄─────────────────────────│                          │
```

### Step 1: Request Upload URL

```
POST /api/v1/files/upload-url
```

**Auth:** Authenticated (all roles)

**Request:**

```json
{
  "file_type": "xrays",
  "content_type": "image/jpeg",
  "filename": "panoramica_2026.jpg",
  "file_size": 2456789,
  "patient_id": "uuid",
  "context": "clinical_record"
}
```

**Response:**

```json
{
  "file_id": "uuid",
  "upload_url": "https://fsn1.your-objectstorage.com/dentalos-prod/...",
  "upload_method": "PUT",
  "upload_expires_at": "2026-04-15T11:00:00Z",
  "required_headers": {
    "Content-Type": "image/jpeg",
    "x-amz-meta-tenant-id": "abc123",
    "x-amz-meta-file-id": "uuid"
  }
}
```

**Business Logic:**

```python
from app.integrations.storage.service import StorageService
import uuid
from datetime import datetime, timedelta


async def generate_upload_url(
    tenant_id: str,
    user_id: str,
    file_type: str,
    content_type: str,
    filename: str,
    file_size: int,
) -> dict:
    """Generate a presigned PUT URL for direct browser upload."""
    # 1. Validate file type and size
    validate_upload_request(file_type, content_type, file_size)

    # 2. Generate unique file ID and key
    file_id = str(uuid.uuid4())
    ext = get_extension_for_mime(content_type)
    year_month = datetime.utcnow().strftime("%Y/%m")
    object_key = f"{tenant_id}/{file_type}/{year_month}/{file_id}{ext}"

    # 3. Generate presigned URL (1 hour expiry)
    storage = StorageService()
    upload_url = storage.generate_presigned_put_url(
        key=object_key,
        content_type=content_type,
        expiry=3600,
        metadata={
            "tenant-id": tenant_id,
            "file-id": file_id,
            "uploaded-by": user_id,
            "original-filename": filename[:255],
        },
    )

    # 4. Pre-register file in DB (status=pending_upload)
    async with get_tenant_session(tenant_id) as session:
        await create_file_record(session, {
            "id": file_id,
            "object_key": object_key,
            "file_type": file_type,
            "content_type": content_type,
            "original_filename": filename,
            "file_size": file_size,
            "status": "pending_upload",
            "uploaded_by": user_id,
        })

    return {
        "file_id": file_id,
        "upload_url": upload_url,
        "upload_method": "PUT",
        "upload_expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "required_headers": {
            "Content-Type": content_type,
            "x-amz-meta-tenant-id": tenant_id,
            "x-amz-meta-file-id": file_id,
        },
    }
```

### Step 2: Confirm Upload

```
POST /api/v1/files/{file_id}/confirm
```

Called by the browser after the direct S3 upload completes. Triggers virus scan and thumbnail generation.

**Response:**

```json
{
  "file_id": "uuid",
  "status": "processing",
  "message": "Archivo recibido, procesando..."
}
```

**Worker (ClamAV + Thumbnail):**

```python
from app.integrations.storage.service import StorageService
from app.integrations.storage.virus_scan import scan_object
from app.integrations.storage.thumbnails import generate_thumbnail
import logging

logger = logging.getLogger(__name__)


class FileProcessingWorker:
    async def process(self, file_id: str, tenant_id: str, object_key: str) -> None:
        """
        Post-upload processing:
        1. Download from S3 to memory (streaming)
        2. Virus scan with ClamAV
        3. Generate thumbnail (images only)
        4. Update file status
        """
        storage = StorageService()

        # 1. Stream file for scanning
        file_bytes = await storage.download_object(object_key)

        # 2. Virus scan
        scan_result = await scan_object(file_bytes)
        if not scan_result.is_clean:
            await storage.delete_object(object_key)
            await update_file_status(tenant_id, file_id, "virus_detected")
            logger.error(
                "Virus detected in uploaded file",
                extra={"tenant_id": tenant_id, "file_id": file_id}
            )
            return

        # 3. Thumbnail generation for images
        async with get_tenant_session(tenant_id) as session:
            file_record = await get_file_record(session, file_id)

        if file_record.content_type.startswith("image/"):
            thumbnail_key = object_key.replace(
                f"/{file_record.file_type}/",
                "/thumbnails/"
            )
            await generate_thumbnail(
                source_bytes=file_bytes,
                storage=storage,
                output_key=thumbnail_key,
                max_size=(400, 400),
            )
            await update_file_thumbnail_key(tenant_id, file_id, thumbnail_key)

        # 4. Mark file as ready
        await update_file_status(tenant_id, file_id, "ready")
        logger.info(
            "File processing complete",
            extra={"tenant_id": tenant_id, "file_id": file_id}
        )
```

---

## 4. Storage Service

```python
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class StorageService:
    SIGNED_URL_EXPIRY = 3600  # 1 hour

    def __init__(self):
        self.client = get_s3_client()
        self.bucket = settings.S3_BUCKET_NAME

    def generate_presigned_get_url(
        self,
        key: str,
        expiry: int = SIGNED_URL_EXPIRY,
        filename_override: Optional[str] = None,
    ) -> str:
        """Generate a presigned GET URL for secure file access."""
        params = {
            "Bucket": self.bucket,
            "Key": key,
        }
        if filename_override:
            params["ResponseContentDisposition"] = (
                f'attachment; filename="{filename_override}"'
            )

        return self.client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiry,
        )

    def generate_presigned_put_url(
        self,
        key: str,
        content_type: str,
        expiry: int = 3600,
        metadata: Optional[dict] = None,
    ) -> str:
        """Generate a presigned PUT URL for direct upload."""
        params = {
            "Bucket": self.bucket,
            "Key": key,
            "ContentType": content_type,
        }
        if metadata:
            params["Metadata"] = metadata

        return self.client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=expiry,
        )

    async def download_object(self, key: str) -> bytes:
        """Download object content for processing (virus scan, thumbnail)."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as exc:
            logger.error("S3 download error", extra={"key": key, "error": str(exc)})
            raise

    async def delete_object(self, key: str) -> None:
        """Permanently delete an object."""
        self.client.delete_object(Bucket=self.bucket, Key=key)

    async def copy_object(self, source_key: str, dest_key: str) -> None:
        """Copy object within the same bucket (for archival)."""
        self.client.copy_object(
            CopySource={"Bucket": self.bucket, "Key": source_key},
            Bucket=self.bucket,
            Key=dest_key,
        )

    def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
```

---

## 5. Signed URL Access Control

**All file access through DentalOS API — no public URLs.**

```
GET /api/v1/files/{file_id}/url
```

**Auth:** Authenticated — patient or staff with permission on patient record

**Response:**

```json
{
  "file_id": "uuid",
  "url": "https://fsn1.your-objectstorage.com/dentalos-prod/...?X-Amz-Expires=3600&...",
  "expires_at": "2026-04-15T11:00:00Z",
  "content_type": "image/jpeg",
  "filename": "panoramica_2026.jpg"
}
```

**URL Expiry per File Type:**

| File Type | Expiry | Rationale |
|-----------|--------|-----------|
| X-rays | 1 hour | Clinical viewing session |
| Intraoral photos | 1 hour | Clinical viewing session |
| Consent PDFs | 24 hours | Patient download window |
| Invoice PDFs | 24 hours | Patient download window |
| Avatars | 7 days | Profile display (cached by browser) |
| Voice recordings | 1 hour | Processing session only |

---

## 6. Virus Scanning (ClamAV)

```python
import clamd
import io
import logging

logger = logging.getLogger(__name__)


class VirusScanResult:
    def __init__(self, is_clean: bool, threat_name: Optional[str] = None):
        self.is_clean = is_clean
        self.threat_name = threat_name


async def scan_object(file_bytes: bytes) -> VirusScanResult:
    """
    Scan file bytes with ClamAV.
    ClamAV runs as a daemon on the worker server.
    """
    try:
        cd = clamd.ClamdUnixSocket(path="/var/run/clamav/clamd.ctl")
        result = cd.instream(io.BytesIO(file_bytes))
        stream_result = result.get("stream", ["OK", ""])
        status = stream_result[0]

        if status == "OK":
            return VirusScanResult(is_clean=True)
        elif status == "FOUND":
            threat = stream_result[1] if len(stream_result) > 1 else "Unknown"
            logger.error("Virus found", extra={"threat": threat})
            return VirusScanResult(is_clean=False, threat_name=threat)
        else:
            logger.warning("ClamAV scan returned unexpected status", extra={"status": status})
            return VirusScanResult(is_clean=True)  # Fail open for availability

    except clamd.ConnectionError:
        logger.error("ClamAV daemon not available — scan skipped")
        return VirusScanResult(is_clean=True)  # Fail open; log for monitoring
```

**ClamAV Update Schedule:** Virus definitions updated daily via `freshclam` cron job.

---

## 7. Thumbnail Generation

```python
from PIL import Image
import io


async def generate_thumbnail(
    source_bytes: bytes,
    storage: StorageService,
    output_key: str,
    max_size: tuple = (400, 400),
) -> None:
    """
    Generate a JPEG thumbnail for image files.
    Stores thumbnail in {tenant_id}/thumbnails/{year}/{month}/{uuid}.jpg
    """
    img = Image.open(io.BytesIO(source_bytes))

    # Convert to RGB if needed (DICOM/PNG may be grayscale/RGBA)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Thumbnail (preserves aspect ratio)
    img.thumbnail(max_size, Image.LANCZOS)

    # Encode as JPEG
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85, optimize=True)
    thumbnail_bytes = output.getvalue()

    # Upload thumbnail
    await storage.upload_bytes(
        key=output_key,
        data=thumbnail_bytes,
        content_type="image/jpeg",
    )
```

---

## 8. File Metadata Table (Tenant Schema)

```sql
CREATE TABLE files (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_type           VARCHAR(30) NOT NULL,          -- xrays | intraoral_photos | documents | etc.
    object_key          VARCHAR(500) NOT NULL,          -- S3 object key
    thumbnail_key       VARCHAR(500),                   -- S3 thumbnail key (images only)
    original_filename   VARCHAR(255) NOT NULL,
    content_type        VARCHAR(100) NOT NULL,
    file_size           BIGINT NOT NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'pending_upload',
    -- pending_upload | processing | ready | virus_detected | deleted
    patient_id          UUID,
    uploaded_by         UUID NOT NULL,                 -- user_id
    context             VARCHAR(50),                   -- clinical_record | consent | invoice | etc.
    context_id          UUID,                          -- FK to the related record
    is_archived         BOOLEAN DEFAULT FALSE,
    archived_at         TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ,                   -- Soft delete
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_files_patient_id ON files(patient_id);
CREATE INDEX idx_files_context ON files(context, context_id);
CREATE INDEX idx_files_status ON files(status);
```

---

## 9. Lifecycle Policies

### Automated Archival

Files older than 1 year are moved to a cheaper cold storage tier via a scheduled job:

```python
from datetime import datetime, timedelta


async def archive_old_files(tenant_id: str) -> None:
    """
    Archive files older than 1 year:
    - Move to archival prefix within the same bucket (cold tier)
    - Update database record
    - Old clinical records (xrays) are never deleted (15-year retention per Colombia law)
    """
    cutoff = datetime.utcnow() - timedelta(days=365)

    async with get_tenant_session(tenant_id) as session:
        old_files = await get_files_older_than(session, cutoff)

        storage = StorageService()
        for file_record in old_files:
            if file_record.is_archived:
                continue

            # Move to archival prefix
            archive_key = file_record.object_key.replace(
                f"{tenant_id}/",
                f"{tenant_id}/archive/",
            )
            await storage.copy_object(file_record.object_key, archive_key)
            await storage.delete_object(file_record.object_key)

            # Update record
            await update_file_archive_status(
                session, file_record.id,
                archive_key=archive_key,
                archived_at=datetime.utcnow(),
            )
```

**Retention policy by file type:**

| File Type | Minimum Retention | Colombia | Mexico | Chile |
|-----------|------------------|---------|--------|-------|
| X-rays (clinical) | 15 years | 15 years | 5 years | 10 years |
| Clinical photos | 15 years | 15 years | 5 years | 10 years |
| Consent PDFs | 15 years | 15 years | 5 years | 10 years |
| Invoice PDFs | 5 years | 5 years | 5 years | 6 years |
| Voice recordings | 1 year | 1 year | 1 year | 1 year |
| Import files | 30 days | 30 days | 30 days | 30 days |
| Avatars | While active | While active | While active | While active |

---

## 10. CORS Configuration

For direct browser uploads to Hetzner Object Storage:

```xml
<!-- Bucket CORS configuration (set via S3 API) -->
<CORSConfiguration>
    <CORSRule>
        <AllowedOrigin>https://app.dentalos.app</AllowedOrigin>
        <AllowedOrigin>https://portal.dentalos.app</AllowedOrigin>
        <AllowedOrigin>https://staging.dentalos.app</AllowedOrigin>
        <AllowedMethod>PUT</AllowedMethod>
        <AllowedHeader>Content-Type</AllowedHeader>
        <AllowedHeader>x-amz-meta-*</AllowedHeader>
        <MaxAgeSeconds>3600</MaxAgeSeconds>
    </CORSRule>
</CORSConfiguration>
```

---

## 11. Security

- **No public bucket access:** Bucket policy denies all anonymous access
- **Tenant isolation:** Object keys prefixed with `{tenant_id}/` — enforced at API level, not S3 policy
- **Signed URL validation:** API checks that the `file_id` belongs to the requesting tenant before issuing a signed URL
- **Content-type verification:** MIME type checked via `python-magic` (magic bytes), not just extension
- **Virus scanning:** ClamAV scan before file marked `ready`
- **Access token rotation:** S3 access keys rotated semi-annually (see security spec)
- **Audit log:** All file access (download URL generation) logged with user_id and patient_id

---

## 12. Configuration Reference

### Environment Variables

| Variable | Description |
|----------|-------------|
| `S3_ENDPOINT_URL` | `https://fsn1.your-objectstorage.com` (prod) or `http://minio:9000` (dev) |
| `S3_ACCESS_KEY` | S3 access key ID |
| `S3_SECRET_KEY` | S3 secret access key |
| `S3_BUCKET_NAME` | `dentalos-prod` or `dentalos-dev` |
| `S3_REGION` | `eu-central` |
| `CLAMAV_SOCKET` | `/var/run/clamav/clamd.ctl` |

---

## Out of Scope

- Video file support (patient education videos) — not planned for v1
- DICOM viewer integration — files stored as DICOM, viewing left to external app
- Resumable upload (TUS protocol) — standard PUT is sufficient for < 100MB
- CDN integration (Cloudflare) — not needed for healthcare files (always signed)
- Database backups via this spec — see I-16 (backup-DR)

---

## Acceptance Criteria

**This integration is complete when:**

- [ ] Presigned upload URL generated and direct S3 upload works
- [ ] ClamAV virus scan rejects infected files before marking ready
- [ ] Thumbnails generated for JPEG/PNG uploads
- [ ] Signed GET URL returns working download link (expires in 1h)
- [ ] Tenant isolation: tenant A cannot access tenant B files via DentalOS API
- [ ] Files older than 1 year moved to archival prefix
- [ ] CORS configured for direct browser upload
- [ ] MinIO works identically in local development
- [ ] File size limits enforced per file type

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
