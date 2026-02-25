# P-13 Patient Document Upload Spec

---

## Overview

**Feature:** Upload a document (X-ray, photo, consent, lab result, referral) to a patient record via multipart form upload. Files are scanned for viruses via ClamAV, stored in a tenant-isolated S3 path, and recorded in the database. File size limits vary by document type.

**Domain:** patients

**Priority:** High

**Dependencies:** P-01 (patient-create.md), P-12 (patient-documents.md), infra/storage-architecture.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant, clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist cannot upload clinical documents. Storage usage counts toward the tenant's plan `max_storage_mb` limit.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/documents
```

**Rate Limiting:**
- 60 requests per hour per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Multipart form data | multipart/form-data |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | Valid UUIDv4 | Target patient identifier | 550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

None.

### Request Body Schema (multipart/form-data)

| Field | Required | Type | Constraints | Description |
|-------|----------|------|-------------|-------------|
| file | Yes | file | See max sizes below; allowed MIME types | The document file to upload |
| document_type | Yes | string | xray, consent, lab_result, referral, photo, other | Type classification |
| description | No | string | Max 500 chars | Human-readable description |
| tooth_number | No | integer | 11-48 (adult) or 51-85 (pediatric) | Associated tooth in FDI notation |

**File Size Limits by document_type:**

| Document Type | Max File Size |
|--------------|---------------|
| xray | 25 MB |
| photo | 10 MB |
| consent | 15 MB |
| lab_result | 15 MB |
| referral | 15 MB |
| other | 15 MB |

**Allowed MIME Types:**

| MIME Type | Extension | Notes |
|-----------|-----------|-------|
| image/jpeg | .jpg, .jpeg | Photos and X-rays |
| image/png | .png | Photos and X-rays |
| application/pdf | .pdf | All document types |
| image/dicom | .dcm | DICOM X-ray images |

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "file_name": "string",
  "document_type": "string",
  "file_size_bytes": "integer",
  "mime_type": "string",
  "description": "string (nullable)",
  "tooth_number": "integer (nullable)",
  "uploaded_by": {
    "id": "uuid",
    "name": "string"
  },
  "created_at": "ISO 8601 datetime",
  "download_url": "string (signed S3 URL, 15min expiry)"
}
```

**Example:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "radiografia_periapical_36.jpg",
  "document_type": "xray",
  "file_size_bytes": 2456789,
  "mime_type": "image/jpeg",
  "description": "Radiografia periapical diente 36 pre-tratamiento",
  "tooth_number": 36,
  "uploaded_by": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "name": "Dr. Carlos Martinez"
  },
  "created_at": "2025-11-15T14:30:00-05:00",
  "download_url": "https://s3.amazonaws.com/dentalos-docs/tn_abc123/patients/550e.../xray/a1b2c3d4.jpg?X-Amz-Signature=..."
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields, invalid document_type, or invalid tooth_number.

```json
{
  "error": "invalid_input",
  "message": "El campo 'document_type' es requerido.",
  "details": { "field": "document_type" }
}
```

#### 401 Unauthorized
**When:** Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not doctor, assistant, or clinic_owner.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para subir documentos de pacientes."
}
```

#### 404 Not Found
**When:** patient_id does not exist or is inactive in the current tenant.

```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 413 Payload Too Large
**When:** File exceeds the size limit for its document_type.

```json
{
  "error": "file_too_large",
  "message": "El archivo excede el tamano maximo permitido. Limite para radiografias: 25 MB. Tamano recibido: 32 MB.",
  "details": {
    "document_type": "xray",
    "max_size_mb": 25,
    "received_size_mb": 32
  }
}
```

#### 415 Unsupported Media Type
**When:** File MIME type is not in the allowed list.

```json
{
  "error": "unsupported_media_type",
  "message": "Tipo de archivo no permitido: application/zip. Tipos permitidos: image/jpeg, image/png, application/pdf, image/dicom.",
  "details": { "received_mime": "application/zip" }
}
```

#### 422 Unprocessable Entity
**When:** Virus detected in uploaded file, or tooth_number out of FDI range.

```json
{
  "error": "validation_failed",
  "message": "El archivo fue rechazado por el escaneo de seguridad. No se permite subir archivos potencialmente daninos.",
  "details": { "scan_result": "threat_detected" }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

#### 507 Insufficient Storage
**When:** Tenant storage quota (plan.max_storage_mb) would be exceeded.

```json
{
  "error": "storage_limit_exceeded",
  "message": "Se ha alcanzado el limite de almacenamiento del plan. Almacenamiento usado: 480 MB / 500 MB.",
  "details": {
    "used_mb": 480,
    "limit_mb": 500,
    "file_size_mb": 25
  }
}
```

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract tenant context; verify role in [doctor, assistant, clinic_owner].
2. Validate patient_id UUID format via Pydantic.
3. Parse multipart form data: extract file, document_type, description, tooth_number.
4. Validate document_type is in allowed values.
5. Validate file MIME type (check both Content-Type header AND magic bytes).
6. Validate file size against document_type-specific limit.
7. Validate tooth_number if provided: must be valid FDI notation (11-18, 21-28, 31-38, 41-48 for adult; 51-55, 61-65, 71-75, 81-85 for pediatric).
8. Load patient from DB; return 404 if not found or inactive.
9. Check tenant storage quota: sum(file_size_bytes) from patient_documents + new file size <= plan.max_storage_mb * 1024 * 1024.
10. Scan file with ClamAV daemon via TCP socket. If threat detected, return 422 and log security event.
11. Generate unique file path: `{tenant_id}/patients/{patient_id}/{document_type}/{uuid}.{ext}`
12. Sanitize original file_name: strip path separators, null bytes, and control characters.
13. Upload file to S3 with:
    - Content-Type set to actual MIME type.
    - Server-side encryption (AES-256).
    - Cache-Control: private, no-cache.
14. INSERT record into `patient_documents` table.
15. Generate signed S3 download URL (15-minute expiry).
16. Write audit log: action=create, resource_type=patient_document, PHI=true.
17. Return 201 with document metadata and download_url.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| file | Non-empty, within size limit | "El archivo es requerido." / "El archivo excede el tamano maximo." |
| document_type | In: xray, consent, lab_result, referral, photo, other | "Tipo de documento no valido." |
| file MIME | In: image/jpeg, image/png, application/pdf, image/dicom | "Tipo de archivo no permitido." |
| description | Max 500 chars if provided | "La descripcion no puede exceder 500 caracteres." |
| tooth_number | Valid FDI notation if provided | "Numero de diente no valido en notacion FDI." |
| MIME vs magic bytes | Header MIME must match detected MIME from file magic bytes | "El tipo de archivo declarado no coincide con el contenido." |

**Business Rules:**

- MIME type is validated via both the Content-Type header and python-magic (libmagic) for magic byte detection to prevent disguised files.
- ClamAV scan is mandatory; if the ClamAV daemon is unavailable, the upload fails with 503 and an alert is raised.
- Files are stored with server-side encryption (SSE-S3 or SSE-KMS).
- The original file name is stored in DB but the S3 key uses a UUID to prevent path traversal.
- Storage quota is checked before upload to avoid uploading then rejecting.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| File with .jpg extension but PNG magic bytes | Reject with MIME mismatch error (415). |
| ClamAV daemon unavailable | Return 503: "El servicio de escaneo de archivos no esta disponible." |
| Zero-byte file | Return 400: "El archivo esta vacio." |
| Duplicate file name (same patient) | Allowed; S3 key uses UUID, so no collision. DB records are independent. |
| Upload exactly at storage limit | Reject with 507 if file would exceed limit by even 1 byte. |
| DICOM file for document_type=photo | Allowed (MIME validation is independent of document_type). |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `patient_documents`: INSERT — new document record.
- `audit_log`: INSERT — document upload audit entry.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:documents:count`: DELETE — document count changed.
- `tenant:{tenant_id}:storage_used`: DELETE — storage usage changed.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None (upload is synchronous).

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** patient_document
- **PHI involved:** Yes
- **Metadata:** `{ "file_name": "...", "document_type": "xray", "file_size_bytes": 2456789, "mime_type": "image/jpeg" }`

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 2000ms (includes virus scan + S3 upload)
- **Maximum acceptable:** < 5000ms (for 25MB files)

### Caching Strategy
- **Strategy:** Cache invalidation for document counts and storage usage.
- **Cache key:** Document count + storage usage keys.
- **TTL:** N/A
- **Invalidation:** Immediate on successful upload.

### Database Performance

**Queries executed:** 3 (load patient, check storage quota, insert document)

**Indexes required:**
- `patient_documents.patient_id` — INDEX (existing: `idx_patient_documents_patient`)

**N+1 prevention:** Not applicable (single INSERT).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID |
| file_name | Strip path separators, null bytes, control chars | Prevent path traversal |
| document_type | Pydantic enum validator | Whitelist only |
| description | strip_tags, max 500 chars | Prevent HTML injection |
| tooth_number | Pydantic integer validator, FDI range check | Must be valid FDI |
| file content | ClamAV virus scan + magic byte MIME check | Prevent malicious uploads |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs are escaped via Pydantic. file_name is sanitized before storage.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** The uploaded file content itself is PHI (X-rays, lab results, clinical photos).

**Audit requirement:** All uploads logged with file metadata (but NOT file content).

---

## Testing

### Test Cases

#### Happy Path
1. Upload JPEG X-ray
   - **Given:** Active patient, doctor user, valid 5MB JPEG file.
   - **When:** POST with file, document_type=xray, tooth_number=36.
   - **Then:** Returns 201 with document metadata, file stored in S3, DB record created.

2. Upload PDF consent
   - **Given:** Active patient, clinic_owner user, valid 2MB PDF.
   - **When:** POST with file, document_type=consent.
   - **Then:** Returns 201, stored at correct S3 path.

3. Upload with description
   - **Given:** Valid file and description text.
   - **When:** POST with description="Radiografia panoramica anual".
   - **Then:** Description stored in DB and returned in response.

#### Edge Cases
1. File at exact size limit (25MB xray)
   - **Given:** JPEG file exactly 25MB.
   - **When:** POST with document_type=xray.
   - **Then:** Returns 201 (accepted at boundary).

2. DICOM file upload
   - **Given:** Valid DICOM file (.dcm).
   - **When:** POST with document_type=xray.
   - **Then:** Returns 201, MIME type recorded as image/dicom.

3. Storage quota boundary
   - **Given:** Tenant at 495MB of 500MB limit, uploading 4MB file.
   - **When:** POST upload.
   - **Then:** Returns 201 (499MB < 500MB limit).

#### Error Cases
1. Virus detected
   - **Given:** File containing EICAR test signature.
   - **When:** POST upload.
   - **Then:** Returns 422, file not stored, security event logged.

2. MIME mismatch
   - **Given:** File with .jpg extension but EXE magic bytes.
   - **When:** POST upload.
   - **Then:** Returns 415.

3. Storage quota exceeded
   - **Given:** Tenant at 498MB of 500MB, uploading 5MB.
   - **When:** POST upload.
   - **Then:** Returns 507.

4. Receptionist role
   - **Given:** Receptionist user.
   - **When:** POST upload.
   - **Then:** Returns 403.

5. File too large
   - **Given:** 30MB JPEG for document_type=xray.
   - **When:** POST upload.
   - **Then:** Returns 413.

### Test Data Requirements

**Users:** 1 clinic_owner, 1 doctor, 1 assistant, 1 receptionist (for 403 test).

**Patients/Entities:** 1 active patient. Test files: valid JPEG (5MB), valid PDF (2MB), valid DICOM, oversized JPEG (30MB), EICAR test file, MIME-mismatched file.

### Mocking Strategy

- S3: Mock upload; verify key path, encryption, content-type.
- ClamAV: Mock TCP socket; return clean/threat responses.
- python-magic: Mock for deterministic MIME detection in tests.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Multipart file upload works for all allowed MIME types
- [ ] File size limits enforced per document_type
- [ ] MIME type validated via both header and magic bytes
- [ ] ClamAV virus scanning operational and mandatory
- [ ] Files stored at correct tenant-isolated S3 path with encryption
- [ ] Storage quota enforced (plan.max_storage_mb)
- [ ] DB record created with correct metadata
- [ ] Signed download URL returned in response
- [ ] Audit log entry created for every upload
- [ ] Receptionist role receives 403
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing documents (covered in P-12 patient-documents.md).
- Deleting documents (covered in P-14 patient-document-delete.md).
- Image compression or thumbnail generation (future enhancement).
- DICOM metadata parsing or viewing (future enhancement).
- Batch/multi-file upload in a single request (future enhancement).
- Direct S3 presigned upload (would bypass virus scanning).

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic + ClamAV + magic bytes)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for document uploads

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
