# P-08 Patient Bulk Import (CSV) Spec

---

## Overview

**Feature:** Bulk import patients from a CSV file. The file is validated, duplicates detected by document_type+document_number, and processing is executed asynchronously via RabbitMQ. Returns a job_id for tracking progress. Supports up to 5,000 rows per import.

**Domain:** patients

**Priority:** High

**Dependencies:** P-01 (patient-create.md), infra/queue-architecture.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner can perform bulk imports to prevent unauthorized mass data insertion. Plan limit on max_patients is enforced during processing.

---

## Endpoint

```
POST /api/v1/patients/import
```

**Progress tracking:**
```
GET /api/v1/patients/import/{job_id}
```

**Error report download:**
```
GET /api/v1/patients/import/{job_id}/errors
```

**Rate Limiting:**
- 5 requests per hour per tenant (import initiation)
- GET status/errors: inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Multipart form data | multipart/form-data |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

**POST /api/v1/patients/import:** None.

**GET /api/v1/patients/import/{job_id}:**

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| job_id | Yes | UUID | Valid UUIDv4 | Import job identifier | 550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

None.

### Request Body Schema (multipart/form-data)

| Field | Required | Type | Constraints | Description |
|-------|----------|------|-------------|-------------|
| file | Yes | file | .csv, max 5MB, UTF-8 encoded | CSV file with patient data |
| duplicate_action | No | string | skip (default), update | Action when duplicate detected |
| date_format | No | string | YYYY-MM-DD (default), DD/MM/YYYY, MM/DD/YYYY | Date format used in the CSV |

**CSV Column Mapping:**

| CSV Column | Maps To | Required | Validation |
|------------|---------|----------|------------|
| tipo_documento | document_type | Yes | cedula, curp, rut, passport, other |
| numero_documento | document_number | Yes | Max 30 chars, alphanumeric |
| nombres | first_name | Yes | Max 100 chars |
| apellidos | last_name | Yes | Max 100 chars |
| fecha_nacimiento | birthdate | Yes | Must match date_format param |
| genero | gender | Yes | masculino/femenino/otro -> male/female/other |
| email | email | No | Valid email format |
| telefono | phone | No | Max 20 chars |
| telefono_secundario | phone_secondary | No | Max 20 chars |
| direccion | address | No | Max 500 chars |
| ciudad | city | No | Max 100 chars |
| departamento | state_province | No | Max 100 chars |
| contacto_emergencia_nombre | emergency_contact_name | No | Max 200 chars |
| contacto_emergencia_telefono | emergency_contact_phone | No | Max 20 chars |
| aseguradora | insurance_provider | No | Max 200 chars |
| poliza | insurance_policy_number | No | Max 50 chars |
| tipo_sangre | blood_type | No | A+, A-, B+, B-, AB+, AB-, O+, O- |
| fuente_referido | referral_source | No | Max 50 chars |
| notas | notes | No | Max 1000 chars |

---

## Response

### Success Response (POST — Job Created)

**Status:** 202 Accepted

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "total_rows": 2500,
  "message": "Importacion en cola. Use GET /api/v1/patients/import/{job_id} para consultar el progreso."
}
```

### Success Response (GET — Job Status)

**Status:** 200 OK

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "total_rows": 2500,
  "processed_rows": 1200,
  "successful_rows": 1180,
  "failed_rows": 20,
  "skipped_duplicates": 15,
  "updated_duplicates": 0,
  "progress_percent": 48.0,
  "started_at": "2025-11-15T14:30:00-05:00",
  "completed_at": null,
  "error_report_url": null
}
```

**Terminal status example (completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "total_rows": 2500,
  "processed_rows": 2500,
  "successful_rows": 2450,
  "failed_rows": 35,
  "skipped_duplicates": 15,
  "updated_duplicates": 0,
  "progress_percent": 100.0,
  "started_at": "2025-11-15T14:30:00-05:00",
  "completed_at": "2025-11-15T14:32:15-05:00",
  "error_report_url": "/api/v1/patients/import/550e8400.../errors"
}
```

### Success Response (GET — Error Report)

**Status:** 200 OK (text/csv)

Returns a CSV file with failed rows and their error reasons:

```csv
fila,tipo_documento,numero_documento,nombres,apellidos,error
15,cedula,123456789,Juan,,"El campo 'apellidos' es requerido."
42,cedula,ABC-INVALID,Maria,Lopez,"El numero de documento contiene caracteres no permitidos."
```

### Error Responses

#### 400 Bad Request
**When:** Invalid CSV format, missing required headers, file too large, or exceeds 5,000 rows.

```json
{
  "error": "invalid_input",
  "message": "El archivo CSV excede el limite de 5,000 filas. Se encontraron 7,200 filas.",
  "details": { "row_count": 7200, "max_rows": 5000 }
}
```

#### 401 Unauthorized
**When:** Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not clinic_owner.

```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede realizar importaciones masivas."
}
```

#### 404 Not Found
**When:** job_id does not exist or belongs to a different tenant.

```json
{
  "error": "not_found",
  "message": "Trabajo de importacion no encontrado."
}
```

#### 409 Conflict
**When:** Another import job is already in progress for this tenant.

```json
{
  "error": "conflict",
  "message": "Ya existe una importacion en progreso. Espere a que finalice antes de iniciar otra."
}
```

#### 422 Unprocessable Entity
**When:** CSV headers do not match expected columns.

```json
{
  "error": "validation_failed",
  "message": "Columnas requeridas faltantes en el CSV.",
  "details": {
    "missing_columns": ["tipo_documento", "fecha_nacimiento"],
    "unknown_columns": ["telefono_3"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded (5 imports/hour).

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract tenant context; verify role = clinic_owner.
2. Check no other import job is in status `queued` or `processing` for this tenant.
3. Validate uploaded file: extension (.csv), size (max 5MB), encoding (UTF-8).
4. Parse CSV headers — validate all required columns present.
5. Count rows — reject if > 5,000.
6. Quick-validate first 10 rows for format sanity (fail fast on clearly broken files).
7. Check tenant plan limit: current patient count + total_rows <= plan.max_patients.
8. Store CSV temporarily in S3: `{tenant_id}/imports/{job_id}/source.csv`.
9. Create import job record in `import_jobs` tracking table (tenant schema extension).
10. Publish message to RabbitMQ `patient_import` queue with job_id and tenant context.
11. Return 202 with job_id.

**Async Worker Process (consumer):**

1. Consume message from `patient_import` queue.
2. Download CSV from S3 temporary location.
3. Set search_path to tenant schema.
4. Process rows in batches of 100:
   a. Validate each row against field rules.
   b. Check duplicate by `document_type` + `document_number` in patients table.
   c. If duplicate found: skip (default) or update (if duplicate_action=update).
   d. If valid and not duplicate: INSERT into patients table.
   e. Track failed rows with error details.
5. Update job progress after each batch (for GET polling).
6. On completion: generate error report CSV (if failures > 0), upload to S3.
7. Update job status to `completed` or `completed_with_errors`.
8. Invalidate patient list cache for tenant.
9. Create audit log entry: action=create, resource_type=patient_import.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| tipo_documento | Must be in: cedula, curp, rut, passport, other | "Tipo de documento no valido: {value}." |
| numero_documento | Non-empty, alphanumeric, max 30 | "Numero de documento requerido y debe ser alfanumerico." |
| nombres | Non-empty, max 100 | "El campo 'nombres' es requerido." |
| apellidos | Non-empty, max 100 | "El campo 'apellidos' es requerido." |
| fecha_nacimiento | Valid date, not in the future, not before 1900-01-01 | "Fecha de nacimiento invalida." |
| genero | masculino/femenino/otro | "Genero no valido. Valores: masculino, femenino, otro." |
| email | Valid email format or empty | "Formato de email invalido." |

**Business Rules:**

- Only one import job per tenant can run at a time (queue serialization).
- Plan max_patients limit is enforced; if importing would exceed the limit, the job processes until the limit and marks remaining as failed.
- Gender mapping: masculino->male, femenino->female, otro->other.
- CSV must be UTF-8 encoded. BOM is stripped if present.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Empty CSV (headers only, no rows) | Return 400: "El archivo CSV no contiene filas de datos." |
| All rows are duplicates (skip mode) | Job completes with 0 successful, N skipped. |
| CSV with extra unknown columns | Ignored silently (only mapped columns processed). |
| Worker crashes mid-import | Job stays in `processing`; health check marks as `failed` after 30min timeout. |
| Import would exceed plan limit | Process up to limit, then mark remaining rows as failed with error: "Se alcanzo el limite de pacientes del plan." |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `patients`: INSERT (bulk) — new patient records.
- `patients`: UPDATE (if duplicate_action=update) — update existing patient data.
- `audit_log`: INSERT — import job audit entry.

**Import job tracking (tenant schema extension):**
```sql
CREATE TABLE import_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type        VARCHAR(20) NOT NULL DEFAULT 'patient_import',
    status          VARCHAR(20) NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued', 'processing', 'completed', 'completed_with_errors', 'failed')),
    total_rows      INTEGER NOT NULL DEFAULT 0,
    processed_rows  INTEGER NOT NULL DEFAULT 0,
    successful_rows INTEGER NOT NULL DEFAULT 0,
    failed_rows     INTEGER NOT NULL DEFAULT 0,
    skipped_rows    INTEGER NOT NULL DEFAULT 0,
    updated_rows    INTEGER NOT NULL DEFAULT 0,
    source_file_path TEXT NOT NULL,
    error_report_path TEXT,
    config          JSONB DEFAULT '{}',
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_import_jobs_status ON import_jobs (status);
CREATE INDEX idx_import_jobs_created ON import_jobs (created_by, created_at);
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:list:*`: INVALIDATE — on job completion.
- `tenant:{tenant_id}:patients:count`: DELETE — patient count changed.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| patient_import | import_patients | { job_id, tenant_id, schema_name, file_path, config: { duplicate_action, date_format } } | On POST acceptance |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** patient_import
- **PHI involved:** Yes (patient PII in bulk)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | import_completed | clinic_owner | When job finishes (success or with errors) |

---

## Performance

### Expected Response Time
- **Target (POST):** < 500ms (validation + queue dispatch)
- **Maximum acceptable (POST):** < 2000ms
- **Target (GET status):** < 100ms
- **Worker throughput:** ~500 rows/second

### Caching Strategy
- **Strategy:** No caching for import endpoints. Patient list cache invalidated post-import.
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Patient list cache cleared on completion.

### Database Performance

**Queries executed (POST):** 3 (check active job, count patients, insert job record)
**Queries executed (Worker):** Batch inserts of 100 rows + duplicate checks.

**Indexes required:**
- `patients.document_type` + `document_number` — UNIQUE INDEX (existing: `idx_patients_document`)
- `import_jobs.status` — INDEX
- `import_jobs.created_by` — INDEX

**N+1 prevention:** Batch inserts using `executemany()`. Duplicate check via single SELECT with IN clause per batch.

### Pagination

**Pagination:** No (single job status per GET).

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| CSV file content | strip_tags on all text fields | Prevent HTML/script injection |
| All text fields | Pydantic str validators, max length | Enforce constraints |
| file | File extension + MIME type check | Only .csv / text/csv allowed |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. CSV field values are never interpolated into SQL strings.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** All patient PII fields (names, document numbers, phone, email, address, blood type).

**Audit requirement:** Write-only logged (import creation and completion).

---

## Testing

### Test Cases

#### Happy Path
1. Successful import of 100 patients
   - **Given:** Valid CSV with 100 unique rows, clinic_owner user.
   - **When:** POST with CSV file.
   - **Then:** Returns 202, job processes, GET shows progress, completes with 100 successful.

2. Import with duplicates (skip)
   - **Given:** CSV with 50 rows, 10 already exist.
   - **When:** POST with duplicate_action=skip.
   - **Then:** 40 created, 10 skipped.

3. Import with duplicates (update)
   - **Given:** CSV with 50 rows, 10 already exist with different phone numbers.
   - **When:** POST with duplicate_action=update.
   - **Then:** 40 created, 10 updated.

#### Edge Cases
1. CSV with exactly 5,000 rows
   - **Given:** Maximum allowed file.
   - **When:** POST.
   - **Then:** Accepted and processed successfully.

2. CSV with BOM character
   - **Given:** UTF-8 CSV with BOM prefix.
   - **When:** POST.
   - **Then:** BOM stripped, processes normally.

#### Error Cases
1. Non-clinic_owner role
   - **Given:** Doctor user.
   - **When:** POST import.
   - **Then:** Returns 403.

2. CSV exceeds 5,000 rows
   - **Given:** CSV with 6,000 rows.
   - **When:** POST.
   - **Then:** Returns 400 with row count error.

3. Concurrent import attempt
   - **Given:** Active import job in progress.
   - **When:** POST another import.
   - **Then:** Returns 409.

### Test Data Requirements

**Users:** 1 clinic_owner, 1 doctor (for 403 test).

**Patients/Entities:** Pre-existing patients for duplicate detection tests. Valid CSV fixture files.

### Mocking Strategy

- RabbitMQ: Mock publisher; verify message payload.
- S3: Mock upload/download; use local temp files in tests.
- Worker: Test independently with in-memory CSV parsing.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] CSV upload validates format, headers, and row count
- [ ] Async processing via RabbitMQ works end-to-end
- [ ] Progress tracking via GET returns accurate counts
- [ ] Duplicate detection by document_type+document_number works (skip + update modes)
- [ ] Error report CSV is downloadable with row-level error details
- [ ] Plan max_patients limit enforced during import
- [ ] Only one import per tenant at a time
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed
- [ ] Audit logging verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Importing clinical data (diagnoses, procedures, odontogram) — separate clinical import spec.
- Real-time WebSocket progress updates (polling via GET is sufficient for v1).
- Import from Excel (.xlsx) format (future enhancement).
- Importing from other dental software systems (requires custom adapters).

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
- [x] Input sanitization defined (Pydantic + strip_tags)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation post-import)
- [x] DB queries optimized (batch inserts, indexes listed)
- [x] Pagination applied where needed (N/A — async job)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (job status tracking table)

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
