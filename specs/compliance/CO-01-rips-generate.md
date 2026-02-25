# CO-01 — RIPS Generate Spec

## Overview

**Feature:** Generate RIPS (Registro Individual de Prestación de Servicios) files for Colombian MinSalud monthly reporting. Processes clinical data from the tenant schema to produce the 7 mandatory file types (AF, AC, AP, AT, AM, AN, AU), validates structure, and returns a batch_id for async tracking.

**Domain:** compliance

**Priority:** Low (Sprint 13-14)

**Dependencies:** patients/P-01, clinical-records/CR-01, billing/B-01, infra/bg-processing.md, infra/audit-logging.md, CO-08 (country-config)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only available for tenants with `country = "CO"` (Colombia). Returns 403 if tenant country is not Colombia. Tenant must have active plan (not suspended/cancelled).

---

## Endpoint

```
POST /api/v1/compliance/rips/generate
```

**Rate Limiting:**
- 5 requests per hour per tenant
- Generates are expensive; additional requests return 429 with retry-after header pointing to next available window

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "period_year": "integer (required) — 4-digit year, e.g. 2026",
  "period_month": "integer (required) — month 1–12",
  "file_types": "array[string] (optional) — subset of [AF, AC, AP, AT, AM, AN, AU]; omit to generate all",
  "include_nullified": "boolean (optional, default false) — include voided/annulled records",
  "notes": "string (optional, max 500) — internal notes for this generation run"
}
```

**Example Request:**
```json
{
  "period_year": 2026,
  "period_month": 1,
  "file_types": ["AF", "AC", "AP", "AT", "AM", "AN", "AU"],
  "include_nullified": false,
  "notes": "Generación mensual enero 2026 — primera entrega"
}
```

---

## Response

### Success Response

**Status:** 202 Accepted

**Schema:**
```json
{
  "batch_id": "string — UUID of this generation job",
  "period": "string — formatted period (YYYY-MM)",
  "status": "string — enum: queued",
  "file_types_requested": "array[string]",
  "estimated_record_count": "integer — approximate records to process",
  "created_at": "string — ISO 8601 timestamp",
  "poll_url": "string — URL to check status (CO-02)",
  "message": "string — human-readable status message"
}
```

**Example:**
```json
{
  "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "period": "2026-01",
  "status": "queued",
  "file_types_requested": ["AF", "AC", "AP", "AT", "AM", "AN", "AU"],
  "estimated_record_count": 847,
  "created_at": "2026-02-01T09:15:00Z",
  "poll_url": "/api/v1/compliance/rips/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "RIPS generation queued. Use poll_url to track progress."
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid period (future month, month before clinic creation, invalid year/month values), or unrecognized file_type values in the array.

**Example:**
```json
{
  "error": "invalid_period",
  "message": "Cannot generate RIPS for a future period",
  "details": {
    "period_year": ["Year 2027 is in the future; reports can only be generated for past or current periods"],
    "period_month": ["Month must be between 1 and 12"]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Authenticated user does not have `clinic_owner` role, or tenant country is not Colombia.

**Example:**
```json
{
  "error": "forbidden",
  "message": "RIPS generation is only available for Colombian clinics (country=CO)",
  "details": {}
}
```

#### 409 Conflict
**When:** A generation job for the same period and tenant is already running (status = generating or queued).

**Example:**
```json
{
  "error": "generation_in_progress",
  "message": "A RIPS generation job for 2026-01 is already running",
  "details": {
    "existing_batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "generating",
    "poll_url": "/api/v1/compliance/rips/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

#### 422 Unprocessable Entity
**When:** Request body fields fail Pydantic validation (wrong types, missing required fields).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "period_month": ["value is not a valid integer"],
    "file_types": ["value is not a valid list"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded (5 generations/hour per tenant). See `infra/rate-limiting.md`.

**Example:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "RIPS generation limit reached (5 per hour)",
  "details": {
    "retry_after_seconds": 1847,
    "limit": 5,
    "window": "1h"
  }
}
```

#### 500 Internal Server Error
**When:** Failed to enqueue the RabbitMQ job, or unexpected database error during pre-flight checks.

---

## Business Logic

**Step-by-step process:**

1. Validate request body against Pydantic schema `RIPSGenerateRequest`.
2. Resolve tenant from JWT claims; verify `tenant.country == "CO"`.
3. Verify caller has `clinic_owner` role via RBAC middleware.
4. Validate period: `period_year` must be >= clinic `created_at` year; `period_month` + `period_year` must not be in the future relative to current UTC date.
5. Normalize `file_types`: if omitted, default to all seven (`AF`, `AC`, `AP`, `AT`, `AM`, `AN`, `AU`). Validate each string is in the allowed enum.
6. Check for conflicting in-progress job: query `rips_batches` table WHERE `tenant_id = X AND period = Y AND status IN ('queued','generating')`. If found, return 409.
7. Compute `estimated_record_count`: quick COUNT queries across appointments, clinical records, prescriptions for the period (no PHI loaded at this stage).
8. Create `rips_batches` row with `status = 'queued'`, `file_types`, `period`, `notes`, `created_by`.
9. Publish message to RabbitMQ `rips.generation` queue with payload: `{ batch_id, tenant_id, tenant_schema, period_year, period_month, file_types, include_nullified }`.
10. Write audit log entry: action=`rips_generate_requested`, resource=`rips_batch`, resource_id=`batch_id`, actor=`user_id`.
11. Return 202 Accepted with `batch_id` and `poll_url`.

**Background Worker (separate process — not part of HTTP handler):**

12. Worker picks up message from `rips.generation` queue.
13. Set `status = 'generating'` on the batch row.
14. For each requested file type, execute the corresponding extractor:
    - **AF** (Consultas): query `appointments` + `clinical_records` joined on encounter fields required by MinSalud AF specification.
    - **AC** (Procedimientos): query `procedures` from `clinical_records`, map to CUPS codes.
    - **AP** (Urgencias): query `appointments` with `modality = 'urgency'`.
    - **AT** (Otros servicios): query miscellaneous service lines.
    - **AM** (Medicamentos): query `prescriptions` for the period.
    - **AN** (Neonatal): query `patients` with age < 28 days at time of service.
    - **AU** (Usuarios): deduplicate patient demographic data across all other files.
15. For each file type, validate records against MinSalud RIPS structure rules (field lengths, required codes, valid CUPS/CIE-10/CUMS codes). Accumulate errors into `rips_batch_errors` table.
16. Generate fixed-width or delimited text files per MinSalud specification; store in tenant object storage path `rips/{tenant_id}/{batch_id}/{type}.txt`.
17. Update `rips_batches`: set `status = 'generated'`, `file_count`, `record_count`, `error_count`, `generated_at`.
18. If `error_count > 0`: set `status = 'generated_with_errors'` to signal validation needed.
19. Publish notification event to `notifications.internal` queue: `{ user_id, type: 'rips_ready', batch_id }`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| period_year | Integer, >= 2020, <= current year + 1 | "Año fuera del rango permitido (2020–actual)" |
| period_month | Integer, 1–12 | "Mes debe estar entre 1 y 12" |
| period (combined) | Not in the future (year+month > now) | "No se puede generar RIPS para un período futuro" |
| file_types[*] | Must be one of AF, AC, AP, AT, AM, AN, AU | "Tipo de archivo RIPS no válido: {value}" |
| notes | Max 500 characters | "Notas no pueden superar 500 caracteres" |

**Business Rules:**

- Only `clinic_owner` may trigger RIPS generation (not doctor, not assistant).
- Only one active generation job per period per tenant at a time (idempotency guard).
- RIPS is exclusively a Colombian compliance feature; tenants with `country != "CO"` get 403.
- Generated files are immutable; re-generating same period creates a new batch with a new batch_id (prior batch is not deleted — full history preserved).
- `include_nullified = false` by default: voided records (cancelled appointments, reversed invoices) are excluded unless explicitly requested.
- Worker must handle large datasets (10,000+ records) in streaming batches to avoid memory exhaustion.
- All CUPS codes must exist in the `cups_codes` reference table (loaded from MinSalud catalog).
- All CIE-10 diagnosis codes must validate against `cie10_codes` reference table.
- Patient `tipo_documento` must map to MinSalud-accepted document type codes.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No records exist for the requested period | Job completes successfully; files generated with header-only content and zero record rows; status = 'generated'; error_count = 0 |
| Appointment has no associated clinical record | Record excluded from AC file; error logged in `rips_batch_errors` with severity = 'warning' |
| Patient demographic data incomplete (missing NUIP) | Record excluded from AU file; error logged as severity = 'error'; error_count incremented |
| Worker crashes mid-generation | Batch status remains 'generating'; dead-letter queue handler resets to 'failed' after 30 min timeout |
| Tenant storage quota exceeded during file write | Worker marks batch as 'failed'; error message stored on batch row; tenant notified |
| Same period requested concurrently (race condition) | Database unique constraint on (tenant_id, period, status IN queued/generating) prevents duplicate; second request gets 409 |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `rips_batches`: INSERT — creates new batch record with status='queued'
- `rips_batch_files`: INSERT (by worker) — one row per generated file
- `rips_batch_errors`: INSERT (by worker) — one row per validation error

**Tenant schema tables affected:**
- None written during HTTP handler (read-only for record counting)
- Worker reads: `appointments`, `clinical_records`, `procedures`, `prescriptions`, `patients`

**Example query (SQLAlchemy):**
```python
# Create batch record
batch = RIPSBatch(
    id=uuid4(),
    tenant_id=tenant_id,
    period_year=body.period_year,
    period_month=body.period_month,
    period=f"{body.period_year}-{body.period_month:02d}",
    file_types=body.file_types,
    include_nullified=body.include_nullified,
    notes=body.notes,
    status=RIPSBatchStatus.QUEUED,
    created_by=current_user.id,
)
session.add(batch)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:rips:list`: INVALIDATE — force refresh of RIPS history list (CO-03)

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| rips.generation | rips_generate | `{ batch_id, tenant_id, tenant_schema, period_year, period_month, file_types, include_nullified }` | After batch row created and committed |
| notifications.internal | rips_ready | `{ user_id, batch_id, period, status }` | After worker completes generation |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** create
- **Resource:** rips_batch
- **PHI involved:** Yes — generation involves reading patient clinical data

### Notifications

**Notifications triggered:** Yes (async, via worker)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | rips_generation_complete | clinic_owner | Worker completes generation successfully |
| in-app | rips_generation_failed | clinic_owner | Worker fails with unrecoverable error |

---

## Performance

### Expected Response Time
- **Target:** < 300ms (HTTP handler only — enqueues and returns)
- **Maximum acceptable:** < 800ms

### Caching Strategy
- **Strategy:** No caching on POST handler
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates `tenant:{tenant_id}:rips:list` on successful enqueue

### Database Performance

**Queries executed (HTTP handler):** 3–4
1. Check tenant country
2. Check in-progress batch (conflict check)
3. Count estimates (3 quick COUNTs)
4. INSERT batch row

**Indexes required:**
- `rips_batches.(tenant_id, period, status)` — COMPOSITE INDEX for conflict check
- `rips_batches.(tenant_id, created_at)` — INDEX for history listing
- `rips_batch_errors.(batch_id)` — INDEX for error retrieval

**N+1 prevention:** Worker uses streaming queries with server-side cursors for large datasets; does not load all records into memory.

### Pagination

**Pagination:** No (POST endpoint returns single batch reference)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| period_year | Pydantic integer validator, range 2020–current+1 | Prevents unreasonable date ranges |
| period_month | Pydantic integer validator, ge=1, le=12 | Range enforcement |
| file_types | Pydantic Literal enum validation | Only allows AF, AC, AP, AT, AM, AN, AU |
| notes | Pydantic max_length=500, strip whitespace | No HTML; plain text only |
| include_nullified | Pydantic bool | Boolean coercion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. `notes` field stored as plain text, returned as plain text.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API endpoints.

### Data Privacy (PHI)

**PHI fields in this endpoint:** No PHI in request body. Worker accesses patient PHI (name, NUIP, diagnoses, procedures) but only within tenant-isolated schema.

**Audit requirement:** All generation requests logged. Worker accesses logged per batch_id (not per-record to avoid audit log flooding).

---

## Testing

### Test Cases

#### Happy Path
1. Generate all 7 file types for a completed month
   - **Given:** Clinic with country=CO, clinic_owner JWT, records exist for 2026-01
   - **When:** POST /api/v1/compliance/rips/generate with period_year=2026, period_month=1
   - **Then:** 202 Accepted, batch_id returned, status=queued, job enqueued to RabbitMQ

2. Generate subset of file types
   - **Given:** Same clinic, same period
   - **When:** POST with file_types=["AF", "AC"]
   - **Then:** 202 Accepted, file_types_requested contains only AF and AC

#### Edge Cases
1. Generate for period with no records
   - **Given:** Clinic with country=CO, no appointments in March 2025
   - **When:** POST with period_year=2025, period_month=3
   - **Then:** 202 Accepted; worker completes and sets status='generated'; record_count=0; file_count=7

2. Generate same period twice
   - **Given:** First generation is in status=generating
   - **When:** Second POST for same period
   - **Then:** 409 Conflict with existing_batch_id in response

#### Error Cases
1. Non-Colombian tenant attempts generation
   - **Given:** Tenant with country=MX, clinic_owner JWT
   - **When:** POST /api/v1/compliance/rips/generate
   - **Then:** 403 Forbidden, "RIPS generation is only available for Colombian clinics"

2. Non-owner role attempts generation
   - **Given:** Authenticated doctor JWT
   - **When:** POST /api/v1/compliance/rips/generate
   - **Then:** 403 Forbidden

3. Future period requested
   - **Given:** Current date is 2026-02-25
   - **When:** POST with period_year=2026, period_month=3
   - **Then:** 400 Bad Request, error=invalid_period

### Test Data Requirements

**Users:** clinic_owner for Colombian tenant, doctor (for 403 test), clinic_owner for non-Colombian tenant

**Patients/Entities:** 20+ patients with complete demographic data; 50+ appointments with clinical records for target period; 10+ prescriptions; mix of procedure types (urgency, elective)

### Mocking Strategy

- RabbitMQ: Use in-memory broker (aio-pika mock) in unit tests; real RabbitMQ in integration tests
- Object storage: Mock `StorageService.write()` to avoid real file I/O in unit tests
- MinSalud CUPS/CIE-10 catalogs: Preload test database fixtures

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/compliance/rips/generate returns 202 with batch_id and poll_url
- [ ] Job published to rips.generation queue with correct payload
- [ ] Conflict detection prevents duplicate jobs for same period
- [ ] 403 returned for non-Colombian tenants
- [ ] 403 returned for non-clinic_owner roles
- [ ] Worker generates all 7 file types conforming to MinSalud spec
- [ ] Worker validates CUPS and CIE-10 codes; populates rips_batch_errors
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms HTTP handler)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI accessed by worker)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Automatic RIPS submission to MinSalud (submission is manual via the government portal; DentalOS only generates the files)
- RIPS file download (see CO-02)
- Validation-only run without file generation (see CO-04)
- Non-Colombian compliance reporting (Mexico SAT, etc.)
- Historical RIPS migration from paper/legacy systems
- RIPS file format versioning (spec targets MinSalud 2023 format)

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
