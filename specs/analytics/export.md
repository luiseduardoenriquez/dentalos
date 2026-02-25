# AN-06 — Analytics Export Spec

---

## Overview

**Feature:** Export analytics data to CSV or Excel. Accepts report type, date range, and format. For small datasets (<= 1000 rows), returns the file synchronously as a download. For large datasets (> 1000 rows), triggers async generation via RabbitMQ and returns a job ID; the caller polls or receives a notification with a signed download URL when ready. Supports 4 report types: patients, appointments, revenue, clinical.

**Domain:** analytics

**Priority:** Medium

**Dependencies:** AN-02, AN-03, AN-04, AN-05, A-01 (login), infra/background-processing.md, infra/caching-strategy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** doctor role is automatically scoped to their own data across all report types. clinic_owner receives clinic-wide exports. The `revenue` report type is restricted to clinic_owner only for full exports (doctor can export their own revenue). Export files are stored temporarily in Hetzner Object Storage and served via pre-signed URLs (15-minute expiry).

---

## Endpoint

```
GET /api/v1/analytics/export
```

**Rate Limiting:**
- 10 requests per minute per user (export generation is expensive)
- Maximum 5 concurrent active export jobs per tenant

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Tenant identifier (auto-resolved from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| report_type | Yes | string | Enum: `patients`, `appointments`, `revenue`, `clinical` | Type of data to export | `revenue` |
| period | No | string | Enum: `today`, `this_week`, `this_month`, `this_quarter`, `this_year`, `custom`. Default: `this_month` | Date range preset | `this_quarter` |
| date_from | Conditional | string | ISO 8601 date. Required when period=custom | Custom range start | `2026-01-01` |
| date_to | Conditional | string | ISO 8601 date. Required when period=custom; >= date_from; max 366 days | Custom range end | `2026-03-31` |
| format | No | string | Enum: `csv`, `xlsx`. Default: `csv` | Output file format | `xlsx` |

### Request Body Schema

None. GET request.

---

## Response

### Success Response — Synchronous (dataset <= 1000 rows)

**Status:** 200 OK

**Headers:**
```
Content-Type: text/csv; charset=utf-8             (for CSV)
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet  (for XLSX)
Content-Disposition: attachment; filename="dentalos_patients_2026-02-25.csv"
X-Row-Count: 342
X-Export-Mode: synchronous
```

**Body:** File binary content (streamed). No JSON wrapper.

### Success Response — Asynchronous (dataset > 1000 rows)

**Status:** 202 Accepted

**Schema:**
```json
{
  "export_job_id": "uuid",
  "status": "queued",
  "report_type": "string",
  "format": "string",
  "estimated_rows": "integer",
  "date_from": "string (YYYY-MM-DD)",
  "date_to": "string (YYYY-MM-DD)",
  "created_at": "string (ISO 8601 datetime)",
  "estimated_ready_at": "string | null (ISO 8601 datetime)",
  "poll_url": "string (relative URL to check job status)"
}
```

**Example (async):**
```json
{
  "export_job_id": "a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6",
  "status": "queued",
  "report_type": "appointments",
  "format": "xlsx",
  "estimated_rows": 5840,
  "date_from": "2026-01-01",
  "date_to": "2026-12-31",
  "created_at": "2026-02-25T10:30:00Z",
  "estimated_ready_at": "2026-02-25T10:31:30Z",
  "poll_url": "/api/v1/analytics/export/jobs/a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6"
}
```

### Export Job Status Response

```
GET /api/v1/analytics/export/jobs/{export_job_id}
```

**Status:** 200 OK

**Schema:**
```json
{
  "export_job_id": "uuid",
  "status": "string (queued | processing | completed | failed)",
  "report_type": "string",
  "format": "string",
  "estimated_rows": "integer",
  "actual_rows": "integer | null",
  "created_at": "string (ISO 8601 datetime)",
  "completed_at": "string | null",
  "download_url": "string | null (pre-signed URL, 15-min expiry — only when status=completed)",
  "download_expires_at": "string | null",
  "error_message": "string | null (only when status=failed)"
}
```

**Completed example:**
```json
{
  "export_job_id": "a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6",
  "status": "completed",
  "report_type": "appointments",
  "format": "xlsx",
  "estimated_rows": 5840,
  "actual_rows": 5823,
  "created_at": "2026-02-25T10:30:00Z",
  "completed_at": "2026-02-25T10:31:15Z",
  "download_url": "https://storage.hetzner.com/dentalos-exports/tenant_abc/exports/a1b2c3d4.xlsx?signature=...&expires=1740481275",
  "download_expires_at": "2026-02-25T10:46:15Z",
  "error_message": null
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing `report_type`, invalid `report_type`/`format`/`period` value, custom period missing dates, date range > 366 days.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "El tipo de reporte especificado no es válido.",
  "details": {
    "report_type": ["Valores permitidos: patients, appointments, revenue, clinical."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token.

#### 403 Forbidden
**When:** Role not in `[clinic_owner, doctor]`. Also when doctor attempts to export full clinic revenue report (clinic_owner only for clinic-wide revenue).

**Example:**
```json
{
  "error": "acceso_denegado",
  "message": "Solo el propietario de la clínica puede exportar el reporte de ingresos completo.",
  "details": {}
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded (10 req/min per user) or concurrent job limit exceeded (5 active export jobs per tenant).

**Example:**
```json
{
  "error": "limite_excedido",
  "message": "Ha alcanzado el límite de exportaciones activas simultáneas. Por favor espere a que finalicen las exportaciones anteriores.",
  "details": {
    "active_jobs": 5,
    "max_allowed": 5
  }
}
```

#### 500 Internal Server Error
**When:** Export generation failure, storage upload failure, or queue dispatch failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT — extract `user_id`, `tenant_id`, `role`. Authorize: reject non-analyst roles with 403. If `report_type=revenue` and role=doctor and doctor attempting clinic-wide, return 403 (doctor can still export their own revenue scoped data — the restriction is on clinic_owner-only clinic-wide revenue).
2. Parse and validate all query parameters.
3. Determine scope filter from role.
4. **Estimate row count:** Execute a lightweight `COUNT(*)` query for the report type + date range. Use this to decide sync vs async path. Threshold: 1000 rows.
5. **Concurrent job limit check:** Query `export_jobs` table: `SELECT COUNT(*) FROM export_jobs WHERE tenant_id = :tenant_id AND status IN ('queued', 'processing')`. If count >= 5, return 429.

6. **Synchronous path (estimated rows <= 1000):**
   - Execute the full data query (see report_type schemas below).
   - Generate file in memory using `io.BytesIO`:
     - CSV: `csv` module with UTF-8 encoding with BOM for Excel compatibility
     - XLSX: `openpyxl` library with styled headers
   - Set appropriate Content-Type and Content-Disposition headers.
   - Stream response via `StreamingResponse`.

7. **Asynchronous path (estimated rows > 1000):**
   - INSERT into `export_jobs` table with status `queued`.
   - Publish message to RabbitMQ queue `analytics.export`:
     ```json
     {
       "export_job_id": "uuid",
       "tenant_id": "uuid",
       "user_id": "uuid",
       "report_type": "appointments",
       "format": "xlsx",
       "date_from": "2026-01-01",
       "date_to": "2026-12-31",
       "doctor_filter": "uuid | null"
     }
     ```
   - Return 202 with job details and poll URL.

**Report Type Data Schemas:**

| Report Type | Columns Exported |
|-------------|-----------------|
| patients | patient_id (anonymized), full_name, date_of_birth, biological_sex, phone, email, document_type, document_number, city, referral_source, created_at, total_visits, last_visit_date |
| appointments | appointment_id, patient_name, doctor_name, appointment_type, scheduled_at, actual_start, actual_end, status, duration_scheduled_min, duration_actual_min, notes_flag |
| revenue | invoice_id, patient_name, doctor_name, issue_date, due_date, paid_date, total_amount, discount_amount, net_amount, status, payment_method, procedure_types |
| clinical | record_id (anonymized), doctor_name, record_date, diagnoses_cie10, procedures_cups, treatment_plan_id, notes_flag |

Note: `notes_flag` is a boolean (1/0) indicating whether clinical notes exist — actual note content is NOT exported (PHI protection).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| report_type | Required. Enum: patients, appointments, revenue, clinical | El tipo de reporte es requerido. |
| format | Enum: csv, xlsx | Formato no válido. |
| period | Enum: today, this_week, this_month, this_quarter, this_year, custom | Período no válido. |
| date_from | Valid ISO date, required for custom | La fecha de inicio es requerida. |
| date_to | Valid ISO date, >= date_from, max 366 days | La fecha de fin no es válida. |

**Business Rules:**

- Clinical note free-text content is NEVER exported — only a boolean flag. This is a PHI safeguard.
- Patient `patient_id` in exports is an anonymized sequential number, not the internal UUID, to reduce re-identification risk.
- Export files are stored with tenant-namespaced paths: `{tenant_id}/exports/{export_job_id}.{ext}`.
- Pre-signed download URLs expire after 15 minutes. Regeneration requires re-requesting the job status endpoint (which extends the URL if still within 1 hour of completion).
- Export files are automatically deleted from storage after 24 hours via a scheduled cleanup job.
- The asynchronous worker sends an in-app notification (via N-05 dispatch engine) with `event_type=system_update` when the export is ready, containing the download URL.
- CSV files use UTF-8 with BOM and comma delimiter for maximum Excel compatibility (Colombian market).
- XLSX files use `openpyxl` with header row bold and column widths auto-fitted.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Row count exactly 1000 | Synchronous path used (threshold is > 1000 for async) |
| Async job fails in worker | status set to `failed`; error_message populated; user notified via in-app notification |
| download_url expires before user downloads | User must re-request the job status; if within 1 hour, new pre-signed URL generated |
| 5 concurrent jobs at limit | 429 with explanation message |
| Empty dataset (0 rows) | Synchronous path; returns empty file with headers only; Content-Length: 0 with headers |
| Concurrent job limit checks in race condition | DB-level constraint prevents exceeding limit |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `export_jobs`: INSERT (async path), UPDATE (worker updates status and download_url)

```sql
CREATE TABLE export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    report_type VARCHAR(32) NOT NULL,
    format VARCHAR(8) NOT NULL,
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'queued',
    estimated_rows INTEGER,
    actual_rows INTEGER,
    download_url TEXT,
    download_expires_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

### Cache Operations

**Cache keys affected:** None — exports are not cached.

**Cache TTL:** N/A.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| analytics.export | generate_export | {export_job_id, tenant_id, user_id, report_type, format, date_from, date_to, doctor_filter} | Async path: estimated rows > 1000 |
| notification.dispatch | system_update | {user_id, tenant_id, data: {download_url, report_type}} | When async export completes |

### Audit Log

**Audit entry:** Yes — export of clinical and financial data.
- **Action:** read (data export)
- **Resource:** analytics_export
- **PHI involved:** Yes — patient and clinical data exported. Audit entry includes: user_id, tenant_id, report_type, date_from, date_to, format, estimated_rows, timestamp.

### Notifications

**Notifications triggered:** Yes — for async exports only.

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in_app | `system_update` | Requesting user | When async export job completes successfully or fails |

---

## Performance

### Expected Response Time
- **Target (sync):** < 2000ms for datasets up to 1000 rows
- **Target (async enqueue):** < 500ms to return 202 response
- **Worker processing time:** < 60s for datasets up to 50,000 rows
- **Maximum acceptable (sync):** < 5000ms

### Caching Strategy
- **Strategy:** No caching — exports are always fresh data.
- **Cache key:** N/A
- **TTL:** N/A

### Database Performance

**Queries executed (sync path):** 2 (COUNT for threshold + full data SELECT)
**Queries executed (async enqueue path):** 3 (COUNT, concurrent jobs check, INSERT export_job)

**Indexes required:**
- `export_jobs.(tenant_id, status)` — concurrent job count check
- `export_jobs.(id, user_id)` — job status polling (user can only see own jobs)
- All indexes from AN-02 through AN-05 (export uses same data sources)

**N+1 prevention:** Single comprehensive SELECT per report type with JOINs. No looping over rows in Python — data fetched and written to stream in chunks of 100 rows.

### Pagination

**Pagination:** No — exports return complete datasets. Large dataset handling via async path.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| report_type | Pydantic enum | |
| format | Pydantic enum | |
| period | Pydantic enum | |
| date_from / date_to | Pydantic date | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** CSV and XLSX files do not contain executable content. CSV values with special characters (commas, quotes, newlines) are properly escaped per RFC 4180.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Patient names, dates of birth, document numbers, and appointment data are PHI. Clinical note content is explicitly excluded. Patient IDs are anonymized in exports.

**Audit requirement:** All export requests logged with full context. Required for Colombian regulatory compliance (Resolución 1888).

---

## Testing

### Test Cases

#### Happy Path
1. Small CSV export (sync path)
   - **Given:** 250 appointments in period
   - **When:** GET /api/v1/analytics/export?report_type=appointments&format=csv
   - **Then:** 200 with CSV file content; Content-Disposition header set; X-Row-Count: 250; X-Export-Mode: synchronous

2. Large XLSX export (async path)
   - **Given:** 8000 appointments in period
   - **When:** GET /api/v1/analytics/export?report_type=appointments&format=xlsx
   - **Then:** 202 with export_job_id; poll_url set; worker processes and sets status=completed; download_url generated with 15min expiry

3. Poll for async job completion
   - **Given:** Async export job created
   - **When:** GET /api/v1/analytics/export/jobs/{export_job_id}
   - **Then:** Returns current status; when completed, returns download_url

4. doctor role — scoped revenue export
   - **Given:** Doctor with 45 patients
   - **When:** GET ?report_type=revenue
   - **Then:** CSV contains only invoices for doctor's patients

#### Edge Cases
1. Exactly 1000 rows
   - **Given:** Exactly 1000 appointments in period
   - **When:** GET export request
   - **Then:** Synchronous path; 200 with file; X-Export-Mode: synchronous

2. Empty dataset (0 rows)
   - **Given:** No data in period
   - **When:** GET export request
   - **Then:** 200 with empty file containing headers only

3. Concurrent job limit reached
   - **Given:** 5 export jobs already queued/processing for the tenant
   - **When:** 6th export request
   - **Then:** 429 with explanation

#### Error Cases
1. Missing report_type
   - **When:** GET /api/v1/analytics/export (no report_type)
   - **Then:** 400 with Spanish error

2. doctor requests full clinic revenue export
   - **When:** doctor role, report_type=revenue (full clinic)
   - **Then:** 403 with Spanish error

3. Invalid format
   - **When:** GET ?format=pdf
   - **Then:** 400 with Spanish error

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (for 403 verification).

**Patients/Entities:** 100+ appointments, patients, invoices for sync path tests; mock for async large dataset simulation.

### Mocking Strategy

- Redis: fakeredis.
- RabbitMQ: Mock publisher for unit tests; real broker for integration tests.
- Hetzner Object Storage: Mock using `moto` S3-compatible mock or direct temp file in integration.
- Export worker: Unit tested separately from the API endpoint.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Sync path returns valid CSV/XLSX file for datasets <= 1000 rows with correct headers
- [ ] Async path returns 202 with job ID for datasets > 1000 rows
- [ ] Job status polling endpoint returns correct status transitions: queued → processing → completed/failed
- [ ] Download URL is pre-signed and expires in 15 minutes
- [ ] Worker notifies user via in-app notification when async export completes
- [ ] Clinical note content is NEVER included in exports (only boolean flag)
- [ ] Patient IDs are anonymized sequential numbers in exports
- [ ] Concurrent job limit (5 per tenant) enforced with 429
- [ ] Audit log entry with full context created for every export request
- [ ] doctor role scoped to own data; cannot export full clinic revenue
- [ ] CSV has UTF-8 BOM for Excel compatibility
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- PDF export format
- RIPS report export (compliance spec — see compliance/)
- Real-time streaming exports via WebSocket
- Email delivery of export files
- FTP/SFTP export integration
- Scheduled recurring exports
- Export templates customization

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined (sync file + async job response)
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (StreamingResponse, async)
- [x] RabbitMQ queue topology matches infra/background-processing.md

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization defined
- [x] SQL injection prevented
- [x] Clinical notes NEVER exported (PHI safeguard)
- [x] Audit trail mandatory (PHI export)

### Hook 4: Performance & Scalability
- [x] Response time targets defined (sync + async)
- [x] Async path for large datasets
- [x] Chunked streaming for sync
- [x] Concurrent job limit enforced

### Hook 5: Observability
- [x] Structured logging
- [x] Audit log with full export context
- [x] Error tracking
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data requirements specified
- [x] Mocking strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
