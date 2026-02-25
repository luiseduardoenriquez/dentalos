# Prescription List Spec

---

## Overview

**Feature:** List all prescriptions for a specific patient with optional date range and doctor filters. Returns summary-level data suitable for the prescription history view. Paginated for patients with long prescription histories.

**Domain:** prescriptions

**Priority:** Medium

**Dependencies:** RX-01 (prescription-create.md), RX-02 (prescription-get.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, patient (own prescriptions only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients can only list their own prescriptions via the patient portal.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/prescriptions
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
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient whose prescriptions to list | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| date_from | No | string | ISO 8601 date (YYYY-MM-DD) | Filter prescriptions from this date | 2026-01-01 |
| date_to | No | string | ISO 8601 date (YYYY-MM-DD) | Filter prescriptions up to this date | 2026-02-24 |
| doctor_id | No | string (UUID) | Valid UUID v4 | Filter by prescribing doctor | d4e5f6a7-... |
| page | No | integer | min: 1, default: 1 | Page number | 1 |
| page_size | No | integer | min: 1, max: 50, default: 20 | Items per page | 20 |

### Request Body Schema

None (GET request).

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
      "doctor_id": "uuid",
      "doctor_name": "string",
      "medications_count": "integer",
      "medications_summary": "string[] — first medication name from each item (max 3 shown)",
      "prescribed_at": "string (ISO 8601 datetime)",
      "created_at": "string (ISO 8601 datetime)"
    }
  ],
  "total": "integer",
  "page": "integer",
  "page_size": "integer",
  "total_pages": "integer"
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "rx1a2b3c-0000-4000-8000-000000000010",
      "doctor_id": "d4e5f6a7-0000-4000-8000-000000000004",
      "doctor_name": "Juan Carlos Perez Rodriguez",
      "medications_count": 2,
      "medications_summary": ["Amoxicilina", "Clorhexidina 0.12% Enjuague Bucal"],
      "prescribed_at": "2026-02-24T14:30:00Z",
      "created_at": "2026-02-24T14:30:00Z"
    },
    {
      "id": "rx2b3c4d-0000-4000-8000-000000000011",
      "doctor_id": "d4e5f6a7-0000-4000-8000-000000000004",
      "doctor_name": "Juan Carlos Perez Rodriguez",
      "medications_count": 1,
      "medications_summary": ["Ibuprofeno"],
      "prescribed_at": "2026-01-15T10:00:00Z",
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values (invalid date format, negative page).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "date_from": ["Formato de fecha invalido. Use YYYY-MM-DD."],
    "doctor_id": ["El identificador del medico no es valido."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Patient attempting to list another patient's prescriptions.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver las prescripciones de este paciente."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate path and query parameters against Pydantic schema.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role:
   - If `patient`: verify JWT sub matches `portal_user_id` linked to `patient_id`. Return 403 if mismatch.
   - If clinic staff: allow any patient in tenant.
4. Verify `patient_id` exists in tenant. Return 404 if not found.
5. Build cache key: `tenant:{tenant_id}:patients:{patient_id}:prescriptions:list:{date_from}:{date_to}:{doctor_id}:{page}:{page_size}`.
6. Check Redis cache — return if hit.
7. Query `prescriptions` table with applied filters, LEFT JOIN `prescription_medications` aggregated (COUNT and first 3 names by order_number).
8. Apply pagination (offset-based).
9. Cache result with 5-minute TTL.
10. Write audit log entry for PHI list access.
11. Return 200 with paginated summary list.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| date_from | Valid ISO 8601 date (if provided) | Formato de fecha invalido. Use YYYY-MM-DD. |
| date_to | Valid ISO 8601 date (if provided); must be >= date_from | La fecha final debe ser mayor o igual a la fecha inicial. |
| doctor_id | Valid UUID v4 (if provided) | El identificador del medico no es valido. |
| page | Integer >= 1 | El numero de pagina debe ser mayor a 0. |
| page_size | Integer 1–50 | El tamano de pagina debe estar entre 1 y 50. |

**Business Rules:**

- The list returns summary data only — no full medication detail. Use RX-02 to retrieve full prescription.
- `medications_summary` returns the `medication_name` of the first 3 medications ordered by `order_number`. If a prescription has more than 3 medications, the summary is truncated (the full list is available via RX-02).
- `medications_count` is the total number of medications in the prescription (not limited to 3).
- Results ordered by `prescribed_at DESC` (most recent first) by default.
- `doctor_id` filter allows clinic staff to see prescriptions by a specific doctor.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no prescriptions | Return `data: []`, `total: 0`, 200 OK |
| Prescription has exactly 3 medications | All 3 names in `medications_summary` |
| Prescription has 10 medications | `medications_count: 10`, `medications_summary` shows first 3 names |
| `date_from` without `date_to` | Apply lower-bound filter only |
| `page` beyond total pages | Return `data: []` with correct total metadata |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:{patient_id}:prescriptions:list:*`: SET — populated on cache miss

**Cache TTL:** 5 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** prescription_list
- **PHI involved:** Yes (medication names are health data)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 80ms (cache hit)
- **Maximum acceptable:** < 300ms (cache miss)

### Caching Strategy
- **Strategy:** Redis cache per patient + filter combination
- **Cache key:** `tenant:{tenant_id}:patients:{patient_id}:prescriptions:list:{filters_hash}`
- **TTL:** 5 minutes
- **Invalidation:** Invalidated when a new prescription is created for this patient (via RX-01)

### Database Performance

**Queries executed:** 2 (count query + data query with aggregate JOIN)

**Indexes required:**
- `{tenant}.prescriptions.patient_id` — INDEX
- `{tenant}.prescriptions.doctor_id` — INDEX
- `{tenant}.prescriptions.prescribed_at` — INDEX (for ORDER BY and date filters)
- `{tenant}.prescription_medications.(prescription_id, order_number)` — COMPOSITE INDEX

**N+1 prevention:** Medication names fetched via aggregate JOIN on prescriptions query using `ARRAY_AGG` ordered by `order_number` limited to 3; no per-prescription sub-queries.

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
| patient_id | Pydantic UUID validator | Reject malformed path params |
| doctor_id | Pydantic UUID validator | Reject malformed filter params |
| date_from, date_to | Pydantic date validator | Strict ISO 8601 parsing |
| page, page_size | Pydantic int with min/max | Prevent negative or unreasonable pagination |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Pydantic serialization escapes all string fields on output.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** medication names (health data), doctor name

**Audit requirement:** All access logged (PHI list access audited per request).

---

## Testing

### Test Cases

#### Happy Path
1. List all prescriptions (no filters)
   - **Given:** Authenticated doctor, patient with 2 prescriptions
   - **When:** GET /api/v1/patients/{patient_id}/prescriptions
   - **Then:** 200 OK, both prescriptions returned ordered by prescribed_at DESC

2. Filter by date range
   - **Given:** Patient with prescriptions from Jan 2026 and Feb 2026
   - **When:** GET ?date_from=2026-02-01&date_to=2026-02-28
   - **Then:** 200 OK, only Feb 2026 prescriptions returned

3. Filter by doctor
   - **Given:** Patient has prescriptions from two different doctors
   - **When:** GET ?doctor_id={doctor_a_id}
   - **Then:** 200 OK, only prescriptions from doctor A returned

4. Patient lists own prescriptions
   - **Given:** Patient with portal access
   - **When:** GET (patient JWT)
   - **Then:** 200 OK, own prescriptions returned

5. Pagination
   - **Given:** Patient has 25 prescriptions
   - **When:** GET ?page=2&page_size=20
   - **Then:** 200 OK, 5 items returned, total=25, total_pages=2

6. medications_summary truncation at 3
   - **Given:** Prescription with 7 medications
   - **When:** GET
   - **Then:** `medications_count: 7`, `medications_summary` has 3 items (first 3 by order_number)

#### Edge Cases
1. Patient with no prescriptions
   - **Given:** Patient exists but has no prescriptions
   - **When:** GET /api/v1/patients/{patient_id}/prescriptions
   - **Then:** 200 OK, `data: []`, `total: 0`

2. Page beyond available results
   - **Given:** Patient has 5 prescriptions, page=2, page_size=20
   - **When:** GET
   - **Then:** 200 OK, `data: []`, correct total metadata

#### Error Cases
1. Patient not found
   - **Given:** `patient_id` does not exist
   - **When:** GET
   - **Then:** 404 Not Found

2. Patient accessing another patient's prescriptions
   - **Given:** Patient A's JWT, URL uses Patient B's patient_id
   - **When:** GET
   - **Then:** 403 Forbidden

3. Invalid date format
   - **Given:** `date_from=24-02-2026`
   - **When:** GET
   - **Then:** 400 Bad Request

4. `date_to` before `date_from`
   - **Given:** `date_from=2026-02-24&date_to=2026-01-01`
   - **When:** GET
   - **Then:** 400 Bad Request with date range error

### Test Data Requirements

**Users:** doctor, assistant, clinic_owner (happy path); patient with portal access; patient without portal access

**Patients/Entities:** Patient with prescriptions from multiple doctors; patient with >20 prescriptions for pagination; patient with a prescription containing 7 medications; patient with no prescriptions.

### Mocking Strategy

- Redis cache: Use fakeredis to test cache hit/miss and invalidation
- Audit log: Mock audit service; assert PHI=true

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Prescription list returned with correct pagination
- [ ] `date_from` and `date_to` filters work independently and together
- [ ] `doctor_id` filter correctly reduces results
- [ ] `medications_count` correctly reflects total medications per prescription
- [ ] `medications_summary` shows first 3 medication names by order_number
- [ ] Results ordered by `prescribed_at DESC`
- [ ] Patient can only list their own prescriptions (403 otherwise)
- [ ] Empty results return 200 (not 404)
- [ ] Cache populated on first request; 5-minute TTL
- [ ] Cache invalidated when new prescription created for patient
- [ ] Audit log written per PHI list access
- [ ] All test cases pass
- [ ] Performance target met (< 80ms cache hit, < 300ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Full medication detail in list view (see RX-02 prescription-get.md)
- Downloading PDFs (see RX-04 prescription-pdf.md)
- Listing prescriptions across all patients (admin/reporting view)
- Sorting by fields other than prescribed_at

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
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (5-minute TTL)
- [x] DB queries optimized (aggregate JOIN, indexes listed)
- [x] Pagination applied (offset-based, max 50)

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
| 1.0 | 2026-02-24 | Initial spec |
