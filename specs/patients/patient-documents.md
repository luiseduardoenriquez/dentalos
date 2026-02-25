# P-12 Patient Documents List Spec

---

## Overview

**Feature:** List all documents attached to a patient record. Supports filtering by document_type, date_range, and uploaded_by. Returns metadata including a signed S3 download URL with 15-minute expiry for each document.

**Domain:** patients

**Priority:** High

**Dependencies:** P-01 (patient-create.md), P-13 (patient-document-upload.md), infra/storage-architecture.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** All staff roles can view patient documents. Audit logged as PHI read when document_type is xray, lab_result, or consent.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/documents
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | Valid UUIDv4 | Target patient identifier | 550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| document_type | No | string | Comma-separated. Values: xray, consent, lab_result, referral, photo, other | Filter by document type | xray,photo |
| date_from | No | date | ISO 8601 (YYYY-MM-DD) | Uploaded from date (inclusive) | 2025-01-01 |
| date_to | No | date | ISO 8601 (YYYY-MM-DD) | Uploaded to date (inclusive) | 2025-12-31 |
| uploaded_by | No | UUID | Valid UUIDv4 | Filter by uploader user ID | 880e8400-e29b-41d4-a716-446655440999 |
| page | No | integer | >= 1, default 1 | Page number | 1 |
| page_size | No | integer | 1-50, default 20 | Items per page | 20 |
| sort_by | No | string | created_at (default), file_name, document_type | Sort field | created_at |
| sort_order | No | string | desc (default), asc | Sort direction | desc |

### Request Body Schema

N/A — GET request with no body.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "uuid",
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
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 45,
    "total_pages": 3
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
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
    },
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "file_name": "consentimiento_endodoncia_firmado.pdf",
      "document_type": "consent",
      "file_size_bytes": 154320,
      "mime_type": "application/pdf",
      "description": "Consentimiento informado para endodoncia",
      "tooth_number": null,
      "uploaded_by": {
        "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
        "name": "Ana Rodriguez"
      },
      "created_at": "2025-11-14T10:15:00-05:00",
      "download_url": "https://s3.amazonaws.com/dentalos-docs/tn_abc123/patients/550e.../consent/c3d4e5f6.pdf?X-Amz-Signature=..."
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 2,
    "total_pages": 1
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values.

```json
{
  "error": "invalid_input",
  "message": "Tipo de documento no valido: 'scan'. Valores permitidos: xray, consent, lab_result, referral, photo, other.",
  "details": { "field": "document_type" }
}
```

#### 401 Unauthorized
**When:** Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role not in allowed list.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para acceder a los documentos de este paciente."
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

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` UUID format via Pydantic.
2. Resolve tenant from JWT claims, set `search_path`.
3. Check user role is in [clinic_owner, doctor, assistant, receptionist].
4. Load patient from DB; return 404 if not found or is_active=false.
5. Build query on `patient_documents` table with filters:
   - WHERE patient_id = {patient_id}
   - Optional: document_type IN (...)
   - Optional: created_at >= date_from AND created_at <= date_to (end of day)
   - Optional: uploaded_by = {user_id}
6. JOIN `users` table on uploaded_by for uploader name.
7. Apply sorting (sort_by + sort_order).
8. Execute count query for pagination metadata.
9. Apply LIMIT/OFFSET for pagination.
10. For each document, generate a signed S3 URL using the file_path with 15-minute expiry.
11. Write audit log if any document_type in response is xray, lab_result, or consent (PHI read).
12. Return paginated response.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUIDv4 | "El ID del paciente no es un UUID valido." |
| document_type | Each value in: xray, consent, lab_result, referral, photo, other | "Tipo de documento no valido: {value}." |
| date_from / date_to | ISO 8601 date; from <= to | "El rango de fechas es invalido." |
| uploaded_by | Valid UUIDv4 if provided | "El ID del usuario no es un UUID valido." |
| page | Integer >= 1 | "El numero de pagina debe ser mayor o igual a 1." |
| page_size | Integer 1-50 | "El tamano de pagina debe estar entre 1 y 50." |
| sort_by | Must be in: created_at, file_name, document_type | "Campo de ordenamiento no valido." |
| sort_order | Must be in: asc, desc | "Direccion de ordenamiento no valida." |

**Business Rules:**

- Signed S3 URLs expire in exactly 15 minutes (900 seconds).
- The S3 URL is generated using AWS SigV4 presigned URL mechanism.
- Documents are returned from the tenant-isolated S3 path; no cross-tenant access is possible.
- The download_url should never be cached on the client beyond its expiry.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient with no documents | Return 200 with empty data array and total_items=0. |
| uploaded_by filter with non-existent user | Return 200 with empty results (no error — user may have been deactivated). |
| Document exists in DB but S3 file is missing | Include in results but log a warning; download_url will return 404 from S3 when accessed. |
| Multiple document types in filter | Return documents matching any of the specified types. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_log`: INSERT — when clinical documents (xray, lab_result, consent) are listed.

### Cache Operations

**Cache keys affected:**
- None. Document listings are not cached (signed URLs would expire before cache).

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Conditional — see infra/audit-logging.md

- **Action:** read
- **Resource:** patient_documents
- **PHI involved:** Yes (when clinical document types are returned)
- **Condition:** Audit entry created only when response includes xray, lab_result, or consent documents.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 250ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching (signed URLs are time-sensitive)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 2 (count + paginated data with JOIN to users)

**Indexes required:**
- `patient_documents.patient_id` — INDEX (existing: `idx_patient_documents_patient`)
- `patient_documents.patient_id` + `document_type` — INDEX (existing: `idx_patient_documents_type`)
- `patient_documents.uploaded_by` — INDEX (add if not exists)

**N+1 prevention:** Single query with LEFT JOIN to `users` for uploader name. Signed URL generation is in-memory (no additional queries).

### Pagination

**Pagination:** Yes

- **Style:** offset-based
- **Default page size:** 20
- **Max page size:** 50

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID |
| document_type | Enum whitelist via Pydantic | Only allowed values |
| date_from / date_to | Pydantic date validator | Strict ISO 8601 |
| uploaded_by | Pydantic UUID validator | Rejects non-UUID |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization. file_name values are sanitized on upload (see P-13).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Document content (accessed via download_url) may contain PHI (X-rays, lab results, consent forms).

**Audit requirement:** Conditional — logged when clinical document types are present in the response.

---

## Testing

### Test Cases

#### Happy Path
1. List all documents for a patient
   - **Given:** Patient with 5 documents of various types.
   - **When:** GET /api/v1/patients/{id}/documents
   - **Then:** Returns 200 with 5 documents, each with valid download_url.

2. Filter by document_type
   - **Given:** Patient with 3 xrays, 2 photos.
   - **When:** GET with ?document_type=xray
   - **Then:** Returns 3 documents, all type=xray.

3. Filter by date range and uploaded_by
   - **Given:** Documents across multiple dates and uploaders.
   - **When:** GET with date_from, date_to, uploaded_by.
   - **Then:** Only matching documents returned.

#### Edge Cases
1. Patient with no documents
   - **Given:** Patient exists but has no documents.
   - **When:** GET documents.
   - **Then:** Returns 200, empty data, total_items=0.

2. Signed URL expiry validation
   - **Given:** Document returned with download_url.
   - **When:** URL accessed within 15 minutes.
   - **Then:** S3 returns the file. After 15 minutes, S3 returns 403.

#### Error Cases
1. Non-existent patient
   - **Given:** Random UUID.
   - **When:** GET documents.
   - **Then:** Returns 404.

2. Invalid document_type filter
   - **Given:** ?document_type=mri
   - **When:** GET request.
   - **Then:** Returns 400.

### Test Data Requirements

**Users:** 1 clinic_owner, 1 doctor, 1 assistant, 1 receptionist (all can access).

**Patients/Entities:** 1 patient with 10+ documents of mixed types, uploaded by different users. 1 patient with no documents.

### Mocking Strategy

- S3: Mock presigned URL generation; return deterministic URLs in tests.
- Database: Use test tenant schema with seeded document records.
- Audit log: Verify conditional INSERT.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Document list returns correct metadata for all patient documents
- [ ] Signed S3 download URLs generated with 15-minute expiry
- [ ] All filters work correctly (document_type, date_range, uploaded_by)
- [ ] Pagination works with total counts
- [ ] Sorting by created_at, file_name, document_type works
- [ ] All staff roles can access the endpoint
- [ ] Audit log created for clinical document types (xray, lab_result, consent)
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Uploading documents (covered in P-13 patient-document-upload.md).
- Deleting documents (covered in P-14 patient-document-delete.md).
- Image thumbnails or preview generation (future enhancement).
- Document versioning (files are immutable once uploaded).
- DICOM viewer integration (future enhancement).

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
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (none — signed URLs)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

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
