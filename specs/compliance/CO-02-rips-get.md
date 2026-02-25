# CO-02 — RIPS Get Batch Spec

## Overview

**Feature:** Retrieve the status and file details of a RIPS generation batch by its batch_id. Acts as the polling endpoint after CO-01 triggers async generation. Returns batch metadata, per-file details with download URLs, error summary, and supports downloading individual files or a full ZIP archive.

**Domain:** compliance

**Priority:** Low (Sprint 13-14)

**Dependencies:** CO-01 (rips-generate), infra/audit-logging.md, infra/caching.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Batch must belong to the requesting tenant. Cross-tenant access is forbidden even for superadmin via this endpoint (superadmin uses admin panel). Only available for `country = "CO"` tenants.

---

## Endpoint

```
GET /api/v1/compliance/rips/{batch_id}
```

**Rate Limiting:**
- 60 requests per minute per tenant (polling-friendly)
- Download sub-endpoints share the tenant rate limit

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| batch_id | Yes | string (UUID) | Valid UUID v4 | Unique identifier of the RIPS batch | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| include_errors | No | boolean | default=false | Include full error list (can be large) | true |
| download | No | string | "zip" or specific file type: AF, AC, AP, AT, AM, AN, AU | Trigger file download instead of JSON response | zip |

---

## Response

### Success Response (JSON — default)

**Status:** 200 OK

**Schema:**
```json
{
  "batch_id": "string (UUID)",
  "period": "string — YYYY-MM format",
  "period_year": "integer",
  "period_month": "integer",
  "status": "string — enum: queued | generating | generated | generated_with_errors | validated | submitted | rejected | failed",
  "file_types_requested": "array[string]",
  "file_count": "integer",
  "record_count": "integer — total records across all files",
  "error_count": "integer",
  "warning_count": "integer",
  "created_at": "string (ISO 8601)",
  "started_at": "string (ISO 8601) | null",
  "generated_at": "string (ISO 8601) | null",
  "validated_at": "string (ISO 8601) | null",
  "submitted_at": "string (ISO 8601) | null",
  "created_by_name": "string — full name of user who triggered generation",
  "notes": "string | null",
  "files": [
    {
      "file_type": "string — AF | AC | AP | AT | AM | AN | AU",
      "file_name": "string — e.g. AF_2026_01.txt",
      "size_bytes": "integer",
      "record_count": "integer",
      "error_count": "integer",
      "download_url": "string — pre-signed URL valid 1 hour",
      "generated_at": "string (ISO 8601) | null"
    }
  ],
  "errors": "array[RIPSError] | null — only if include_errors=true",
  "download_zip_url": "string — pre-signed URL for full ZIP, valid 1 hour | null if not generated",
  "failure_reason": "string | null — set if status=failed"
}
```

**RIPSError schema (when include_errors=true):**
```json
{
  "error_id": "string (UUID)",
  "file_type": "string — which RIPS file the error belongs to",
  "severity": "string — error | warning",
  "rule_code": "string — MinSalud rule identifier, e.g. RIPS-AF-001",
  "message": "string — human-readable description in Spanish",
  "record_ref": "string — identifies the source record (e.g. appointment_id or patient_id)",
  "field_name": "string | null — specific field that failed validation",
  "field_value": "string | null — the invalid value (PHI-safe; IDs only, not names)",
  "corrective_action": "string — guidance on how to fix",
  "correction_url": "string | null — deep-link to fix the record in the app"
}
```

**Example:**
```json
{
  "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "period": "2026-01",
  "period_year": 2026,
  "period_month": 1,
  "status": "generated_with_errors",
  "file_types_requested": ["AF", "AC", "AP", "AT", "AM", "AN", "AU"],
  "file_count": 7,
  "record_count": 832,
  "error_count": 15,
  "warning_count": 3,
  "created_at": "2026-02-01T09:15:00Z",
  "started_at": "2026-02-01T09:15:05Z",
  "generated_at": "2026-02-01T09:17:42Z",
  "validated_at": null,
  "submitted_at": null,
  "created_by_name": "Dra. María Torres",
  "notes": "Generación mensual enero 2026",
  "files": [
    {
      "file_type": "AF",
      "file_name": "AF_202601.txt",
      "size_bytes": 48320,
      "record_count": 214,
      "error_count": 8,
      "download_url": "https://storage.dentalos.io/rips/tn_abc123/a1b2c3d4/AF_202601.txt?token=xyz&expires=1738400862",
      "generated_at": "2026-02-01T09:17:38Z"
    }
  ],
  "errors": null,
  "download_zip_url": "https://storage.dentalos.io/rips/tn_abc123/a1b2c3d4/RIPS_202601.zip?token=abc&expires=1738400862",
  "failure_reason": null
}
```

### Success Response (File Download — when `download` query param is set)

**Status:** 200 OK with file stream

**Content-Type:** `text/plain; charset=utf-8` for individual file, `application/zip` for ZIP

**Headers:**
```
Content-Disposition: attachment; filename="AF_202601.txt"
Content-Length: 48320
X-RIPS-Batch-ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
X-RIPS-Record-Count: 214
```

### Error Responses

#### 400 Bad Request
**When:** `download` query parameter contains an unrecognized value (not "zip" or a valid file type).

**Example:**
```json
{
  "error": "invalid_download_type",
  "message": "download must be one of: zip, AF, AC, AP, AT, AM, AN, AU",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Batch belongs to a different tenant, or caller lacks `clinic_owner` role, or tenant country is not Colombia.

#### 404 Not Found
**When:** No batch with the given `batch_id` exists in the tenant's context.

**Example:**
```json
{
  "error": "batch_not_found",
  "message": "RIPS batch not found",
  "details": {
    "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

#### 409 Conflict
**When:** Download requested for a file that is not yet generated (status is queued or generating).

**Example:**
```json
{
  "error": "files_not_ready",
  "message": "RIPS files are not yet generated. Current status: generating",
  "details": {
    "status": "generating",
    "started_at": "2026-02-01T09:15:05Z"
  }
}
```

#### 422 Unprocessable Entity
**When:** `batch_id` path parameter is not a valid UUID format.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "batch_id": ["value is not a valid UUID"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Pre-signed URL generation fails, or unexpected database error.

---

## Business Logic

**Step-by-step process:**

1. Validate `batch_id` as a valid UUID v4 via Pydantic path parameter validator.
2. Resolve tenant_id from JWT; verify `tenant.country == "CO"`.
3. Verify caller has `clinic_owner` role.
4. Query `rips_batches` WHERE `id = batch_id AND tenant_id = tenant_id`. If not found, return 404.
5. Query `rips_batch_files` WHERE `batch_id = batch_id` to get per-file metadata.
6. If `include_errors=true`, query `rips_batch_errors` WHERE `batch_id = batch_id` (paginated internally, max 500 errors returned).
7. Generate pre-signed URLs for each file's download path via `StorageService.presign(path, ttl=3600)`.
8. If all files exist, generate pre-signed URL for ZIP archive (or trigger on-demand ZIP creation if not cached).
9. If `download` query param is set:
   - Validate that batch status is in `{generated, generated_with_errors, validated, submitted, rejected}`.
   - Resolve requested file path; return as streaming file response with appropriate headers.
   - If `download=zip`, return the ZIP archive.
10. Otherwise, return JSON response with assembled batch detail.
11. Write audit log: action=`rips_batch_read`, resource=`rips_batch`, resource_id=`batch_id`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| batch_id | Valid UUID v4 format | "batch_id must be a valid UUID" |
| download | Must be zip, AF, AC, AP, AT, AM, AN, AU, or absent | "download must be one of: zip, AF, AC, AP, AT, AM, AN, AU" |
| include_errors | Boolean | "include_errors must be a boolean" |

**Business Rules:**

- Pre-signed download URLs are valid for 1 hour. Clients should not cache these URLs; they should re-request to refresh.
- Download is only possible when status is NOT `queued` or `generating`.
- Error list is truncated at 500 records when `include_errors=true` to prevent oversized responses. A field `errors_truncated: true` signals truncation.
- `correction_url` in error objects is a deep-link to the affected record in the DentalOS frontend (e.g., `/patients/{patient_id}/records/{record_id}`).
- `field_value` in error objects is sanitized: for PHI fields (patient name, NUIP), only the record ID is shown, not the actual value.
- ZIP archive is generated lazily on first download request and cached in object storage for 24h; subsequent requests use the cached ZIP.

**Status Transitions:**

| Status | Meaning |
|--------|---------|
| queued | Job in RabbitMQ queue, not yet started |
| generating | Worker is actively processing records |
| generated | All files created, no errors |
| generated_with_errors | Files created but validation errors found |
| validated | Manual validation passed (CO-04 ran and passed) |
| submitted | Clinic manually submitted to MinSalud portal |
| rejected | MinSalud returned rejection (manual update by clinic) |
| failed | Worker encountered unrecoverable error |

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Batch status is queued or generating | Returns JSON with status and timestamps; files array is empty; download_zip_url is null |
| Batch failed during generation | Returns status=failed, failure_reason populated; files array contains only successfully generated files |
| Error list exceeds 500 | First 500 errors returned; errors_truncated=true added to response; full list available via CO-04 |
| Pre-signed URL generation fails for one file | Other files returned normally; affected file's download_url is null with a "url_unavailable" flag |
| File deleted from storage (manual cleanup) | download_url returns presigned URL that will 404 when accessed; a "file_status": "missing" flag is added |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None — this is a read-only endpoint

**Public schema tables affected:**
- `rips_batches`: SELECT (read only)
- `rips_batch_files`: SELECT (read only)
- `rips_batch_errors`: SELECT (read only, conditional on include_errors)

**Example query (SQLAlchemy):**
```python
# Load batch with files eagerly
stmt = (
    select(RIPSBatch)
    .options(selectinload(RIPSBatch.files))
    .where(
        RIPSBatch.id == batch_id,
        RIPSBatch.tenant_id == tenant_id,
    )
)
result = await session.execute(stmt)
batch = result.scalar_one_or_none()
if not batch:
    raise HTTPException(status_code=404, detail="batch_not_found")
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:rips:batch:{batch_id}`: SET (cache batch detail for 60s to handle burst polling)
- Invalidated by CO-01 on new generation, CO-04 on validation

**Cache TTL:** 60 seconds (short TTL since status changes frequently during generation)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — this is a read-only endpoint.

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** read
- **Resource:** rips_batch
- **PHI involved:** No (batch metadata; PHI is inside the files themselves, not the metadata)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms (with cache hit for polling)
- **Maximum acceptable:** < 400ms (cache miss requiring DB + presigned URL generation)

### Caching Strategy
- **Strategy:** Redis cache on batch metadata (not file contents)
- **Cache key:** `tenant:{tenant_id}:rips:batch:{batch_id}`
- **TTL:** 60 seconds (polling-friendly; short enough to reflect status changes)
- **Invalidation:** Invalidated when worker updates batch status

### Database Performance

**Queries executed:** 2–3
1. Fetch batch + files (eager load with selectinload)
2. Fetch errors (conditional, if include_errors=true)
3. Optional: presign URL resolution (storage service call, not DB)

**Indexes required:**
- `rips_batches.(id, tenant_id)` — COMPOSITE UNIQUE for the primary lookup
- `rips_batch_files.(batch_id)` — INDEX for file listing
- `rips_batch_errors.(batch_id, severity)` — COMPOSITE INDEX for filtered error queries

**N+1 prevention:** Files loaded via `selectinload` in a single query.

### Pagination

**Pagination:** No (batch has at most 7 files; error list capped at 500 in response)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| batch_id | UUID validation via Pydantic Path | Invalid UUIDs rejected immediately |
| include_errors | Boolean coercion | Invalid values default to false |
| download | Literal enum validation | Only allowed file type strings accepted |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. File names are validated against safe filename pattern `[A-Z0-9_]+\.(txt|zip)`.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API endpoints.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None in JSON response. Downloaded file contents contain patient PHI (NUIP, diagnoses, procedures), protected by:
- Pre-signed URLs with 1-hour expiry
- HTTPS-only delivery
- Tenant isolation (batch ownership verified before URL generation)

**Audit requirement:** All batch reads logged. Downloads additionally logged as action=`rips_file_download` with file_type.

---

## Testing

### Test Cases

#### Happy Path
1. Poll batch in generating state
   - **Given:** clinic_owner JWT, batch with status=generating
   - **When:** GET /api/v1/compliance/rips/{batch_id}
   - **Then:** 200 OK, status=generating, files=[], download_zip_url=null

2. Get completed batch
   - **Given:** batch with status=generated, 7 files
   - **When:** GET /api/v1/compliance/rips/{batch_id}
   - **Then:** 200 OK, file_count=7, each file has download_url, record_count populated

3. Download individual file
   - **Given:** batch with status=generated, AF file exists
   - **When:** GET /api/v1/compliance/rips/{batch_id}?download=AF
   - **Then:** 200 OK with file stream, Content-Disposition: attachment; filename="AF_202601.txt"

4. Download ZIP
   - **Given:** batch with status=generated, all 7 files exist
   - **When:** GET /api/v1/compliance/rips/{batch_id}?download=zip
   - **Then:** 200 OK with ZIP stream, Content-Type: application/zip

#### Edge Cases
1. Include errors on batch with 600 errors
   - **Given:** batch with error_count=600
   - **When:** GET with include_errors=true
   - **Then:** 200 OK, errors array has 500 entries, errors_truncated=true

2. Batch has status=failed
   - **Given:** batch with status=failed, failure_reason set
   - **When:** GET /api/v1/compliance/rips/{batch_id}
   - **Then:** 200 OK, status=failed, failure_reason populated, files array partial

#### Error Cases
1. Wrong tenant
   - **Given:** batch belonging to tenant_B, JWT from tenant_A
   - **When:** GET /api/v1/compliance/rips/{batch_id}
   - **Then:** 404 Not Found (no cross-tenant leakage)

2. Download before generation complete
   - **Given:** batch with status=generating
   - **When:** GET with download=AF
   - **Then:** 409 Conflict, "files_not_ready"

3. Non-owner attempts access
   - **Given:** doctor JWT
   - **When:** GET /api/v1/compliance/rips/{batch_id}
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner for Colombian tenant, doctor (for 403 test)

**Patients/Entities:** RIPS batch in each status (queued, generating, generated, generated_with_errors, failed); batch with 600+ errors for truncation test

### Mocking Strategy

- Storage service presigning: Mock `StorageService.presign()` to return deterministic test URLs
- Redis cache: Use fakeredis in unit tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns batch metadata with correct status reflecting worker progress
- [ ] files[] populated with per-file metadata and pre-signed download URLs once generated
- [ ] download=zip returns streaming ZIP with all 7 files
- [ ] download={file_type} returns streaming individual file
- [ ] 404 for missing or cross-tenant batch
- [ ] 409 for download before generation completes
- [ ] include_errors=true returns error list (capped at 500)
- [ ] correction_url in errors deep-links to correct record
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms cached, < 400ms cold)
- [ ] Quality Hooks passed
- [ ] Audit logging verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- RIPS file format validation (see CO-04)
- RIPS submission to MinSalud
- Deletion or re-generation of files
- Viewing individual records that contributed to a RIPS file
- Admin-level batch inspection across tenants

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
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

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
| 1.0 | 2026-02-25 | Initial spec |
