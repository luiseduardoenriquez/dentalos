# OD-04: Odontogram History Spec

---

## Overview

**Feature:** Retrieve the chronological timeline of all changes made to a patient's odontogram. Every condition addition, update, and removal is recorded as an immutable history entry (written by OD-02 and OD-03). This endpoint provides filterable, cursor-paginated access to that audit trail, showing who changed what, when, what the old value was, and what the new value is. Used for clinical review, treatment planning context, and compliance auditing.

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-02 (odontogram-update-condition.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist does NOT have access to clinical history. Patient role is excluded.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/odontogram/history
```

**Rate Limiting:**
- 60 requests per minute per user
- Inherits global rate limit baseline; history is rarely fetched in rapid succession.

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
| patient_id | Yes | UUID | Valid UUID v4 | Patient identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| tooth_number | No | integer | Valid FDI notation | Filter by specific tooth | 36 |
| condition_code | No | string | Valid catalog code | Filter by condition type | caries |
| date_from | No | string | ISO 8601 date (YYYY-MM-DD) | Filter entries from this date inclusive | 2026-01-01 |
| date_to | No | string | ISO 8601 date (YYYY-MM-DD) | Filter entries to this date inclusive | 2026-02-24 |
| doctor_id | No | UUID | Valid UUID v4 | Filter by doctor who made the change | d4e5f6a7-b1c2-7890-abcd-ef1234567890 |
| action | No | string | enum: add, update, remove | Filter by action type | add |
| cursor | No | string | Opaque cursor string from previous response | Pagination cursor | eyJpZCI6IjEyMzQifQ== |
| limit | No | integer | 1–100, default 50 | Page size | 50 |

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
      "patient_id": "uuid",
      "tooth_number": "integer",
      "zone": "string",
      "action": "string (add | update | remove)",
      "condition_code": "string",
      "previous_data": {
        "condition_code": "string | null",
        "severity": "string | null",
        "notes": "string | null"
      },
      "new_data": {
        "condition_code": "string | null",
        "severity": "string | null",
        "notes": "string | null",
        "source": "string (manual | voice) | null"
      },
      "performed_by": {
        "id": "uuid",
        "full_name": "string",
        "role": "string"
      },
      "created_at": "string (ISO 8601)"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_returned": "integer"
  },
  "filters_applied": {
    "tooth_number": "integer | null",
    "condition_code": "string | null",
    "date_from": "string | null",
    "date_to": "string | null",
    "doctor_id": "uuid | null",
    "action": "string | null"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "h1i2j3k4-l5m6-7890-abcd-123456789def",
      "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tooth_number": 36,
      "zone": "oclusal",
      "action": "update",
      "condition_code": "restoration",
      "previous_data": {
        "condition_code": "caries",
        "severity": "moderate",
        "notes": "Caries detectada en control"
      },
      "new_data": {
        "condition_code": "restoration",
        "severity": null,
        "notes": "Restauracion compuesta clase I",
        "source": "manual"
      },
      "performed_by": {
        "id": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
        "full_name": "Dr. Carlos Mendez",
        "role": "doctor"
      },
      "created_at": "2026-02-20T10:30:00Z"
    },
    {
      "id": "a9b8c7d6-e5f4-7890-abcd-321098765fed",
      "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tooth_number": 36,
      "zone": "oclusal",
      "action": "add",
      "condition_code": "caries",
      "previous_data": null,
      "new_data": {
        "condition_code": "caries",
        "severity": "moderate",
        "notes": "Caries detectada en control de rutina",
        "source": "manual"
      },
      "performed_by": {
        "id": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
        "full_name": "Dr. Carlos Mendez",
        "role": "doctor"
      },
      "created_at": "2026-01-15T09:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "total_returned": 2
  },
  "filters_applied": {
    "tooth_number": 36,
    "condition_code": null,
    "date_from": null,
    "date_to": null,
    "doctor_id": null,
    "action": null
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Receptionist or patient role attempts access.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver el historial del odontograma."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist in the tenant.

```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Invalid query parameter values (e.g., invalid date format, invalid tooth_number).

```json
{
  "error": "validation_failed",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "date_from": ["Formato de fecha invalido. Use YYYY-MM-DD."],
    "tooth_number": ["El numero de diente debe ser un entero valido en notacion FDI."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure during history query.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` UUID format and all query parameters.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role is in `[clinic_owner, doctor, assistant]`. Reject with 403 otherwise.
4. Verify patient exists in tenant schema. Return 404 if not found.
5. Build dynamic query against `odontogram_history` with optional WHERE clauses:
   - `tooth_number = :tooth_number` (if provided)
   - `condition_code = :condition_code` (if provided)
   - `created_at >= :date_from` (if provided — date cast to start of day in tenant timezone)
   - `created_at <= :date_to` (if provided — date cast to end of day in tenant timezone)
   - `performed_by = :doctor_id` (if provided)
   - `action = :action` (if provided)
6. Apply cursor-based pagination: if `cursor` provided, decode it and apply `created_at < cursor_timestamp AND id < cursor_id` (keyset pagination for consistent ordering).
7. ORDER BY `created_at DESC, id DESC`. Fetch `limit + 1` rows to detect `has_more`.
8. JOIN with `users` table to resolve `performed_by` into `{id, full_name, role}`.
9. If `total_returned = limit + 1`, pop the last row, set `has_more = true`, encode next cursor from the last retained row's `(created_at, id)`.
10. Write audit log entry (action: read, resource: odontogram_history, PHI: yes).
11. Return 200 with paginated data.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| tooth_number | Integer in valid FDI range (if provided) | El numero de diente debe ser un entero valido en notacion FDI. |
| condition_code | Must match catalog code (if provided) | El codigo de condicion '{code}' no existe en el catalogo. |
| date_from | Valid ISO 8601 date (if provided) | Formato de fecha invalido. Use YYYY-MM-DD. |
| date_to | Valid ISO 8601 date (if provided); must be >= date_from | La fecha final no puede ser anterior a la fecha inicial. |
| doctor_id | Valid UUID v4 (if provided) | El identificador del doctor no es valido. |
| action | One of: add, update, remove (if provided) | La accion debe ser: add, update o remove. |
| limit | Integer 1-100 (default 50) | El limite debe ser entre 1 y 100. |
| cursor | Valid opaque cursor string (if provided) | El cursor de paginacion no es valido. |

**Business Rules:**

- History is returned in reverse chronological order (most recent first) by default.
- Cursor encodes `(created_at, id)` as base64 JSON to support keyset pagination without offset performance degradation.
- `doctor_id` filter allows supervisors to review a specific clinician's work on a patient.
- If `date_from` and `date_to` are the same day, all entries for that calendar day are returned.
- The `filters_applied` response object always echoes back which filters were active, even if null, to help frontend display active filter chips.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has zero history entries | Return empty data array, has_more=false |
| All filters applied simultaneously | All filters are ANDed; may return zero results |
| date_to before date_from | Return 422 with specific validation error |
| cursor from a different patient's history | Cursor decodes to a timestamp/id; WHERE patient_id scopes the query — cross-patient data impossible |
| doctor_id filter for a doctor not in the tenant | Returns empty result (no error; just no matching records) |
| limit=1 with many history entries | Returns 1 entry, has_more=true, next_cursor set |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint).

### Cache Operations

**Cache keys affected:**
- None (history is not cached; it is always fetched fresh to ensure compliance accuracy).

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** read
- **Resource:** odontogram_history
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 250ms
- **Maximum acceptable:** < 600ms

### Caching Strategy
- **Strategy:** No caching (compliance data must be fresh; history is immutable so cache would be valid, but the risk of serving stale history for legal purposes outweighs the performance gain).
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 2 (patient existence check + history query with user JOIN).

**Indexes required:**
- `odontogram_history.(patient_id, created_at)` — INDEX (already defined: `idx_odontogram_history_date`)
- `odontogram_history.(patient_id, tooth_number)` — INDEX (already defined: `idx_odontogram_history_tooth`)
- `odontogram_history.performed_by` — INDEX for doctor_id filter (add if not present)

**N+1 prevention:** Single JOIN to `users` table within the history query avoids per-row lookups.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on `created_at DESC, id DESC`)
- **Default page size:** 50
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | |
| tooth_number | Pydantic int validator | |
| condition_code | Pydantic string, whitelist enum | |
| date_from, date_to | Pydantic date validator | Prevent injection via date strings |
| doctor_id | Pydantic UUID validator | |
| cursor | Base64 decode + JSON parse + timestamp/UUID extract | Reject malformed cursors |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Dynamic WHERE clauses built via ORM `.filter()` calls, not string concatenation.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization. `notes` and `previous_data` JSONB values are returned as-is (already sanitized on write in OD-02).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** All history entries contain clinical PHI (tooth conditions, treatment notes).

**Audit requirement:** All access logged (read access to clinical history).

---

## Testing

### Test Cases

#### Happy Path
1. Get all history for patient (no filters)
   - **Given:** Authenticated doctor, patient has 10 history entries across multiple teeth
   - **When:** GET /api/v1/patients/{patient_id}/odontogram/history
   - **Then:** 200 OK, entries returned in descending chronological order, default limit=50

2. Filter by tooth_number
   - **Given:** Patient has 10 entries total, 3 for tooth 36
   - **When:** GET with tooth_number=36
   - **Then:** 200 OK, exactly 3 entries returned

3. Filter by date range
   - **Given:** Patient has entries in January and February 2026
   - **When:** GET with date_from=2026-02-01&date_to=2026-02-28
   - **Then:** 200 OK, only February entries returned

4. Paginated response
   - **Given:** Patient has 75 history entries
   - **When:** GET with limit=50
   - **Then:** 200 OK, 50 entries returned, has_more=true, next_cursor set

5. Second page via cursor
   - **Given:** Previous response returned next_cursor
   - **When:** GET with cursor={next_cursor}
   - **Then:** 200 OK, remaining 25 entries returned, has_more=false

#### Edge Cases
1. Patient with zero history
   - **Given:** Patient with no odontogram changes
   - **When:** GET history
   - **Then:** 200 OK, data=[], has_more=false

2. Filter returns zero results
   - **Given:** Filter by doctor_id of a doctor who never touched this patient
   - **When:** GET with doctor_id={other_doctor_id}
   - **Then:** 200 OK, data=[], has_more=false

3. Combined filters
   - **Given:** Filter by tooth_number=36, condition_code=caries, action=add
   - **When:** GET with all three filters
   - **Then:** 200 OK, only entries matching all three filters returned

#### Error Cases
1. Invalid date format
   - **Given:** date_from=24-02-2026 (wrong format)
   - **When:** GET history
   - **Then:** 422 with date_from validation error

2. date_to before date_from
   - **Given:** date_from=2026-02-24, date_to=2026-01-01
   - **When:** GET history
   - **Then:** 422 with date range validation error

3. Receptionist access
   - **Given:** Authenticated user with receptionist role
   - **When:** GET history
   - **Then:** 403 Forbidden

4. Patient not found
   - **Given:** Non-existent patient_id
   - **When:** GET history
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** doctor, assistant (pass); receptionist, patient (fail with 403).

**Patients/Entities:** Patient with at least 75 history entries (various teeth, conditions, dates, and doctors) for pagination testing. Patient with zero history for empty response testing.

### Mocking Strategy

- No external service mocking required (pure database read).
- Use fixed-time test fixtures for date range tests.
- Generate cursor tokens in test setup to validate pagination logic.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Returns history in descending chronological order by default
- [ ] All filter combinations work correctly (AND logic)
- [ ] Cursor-based pagination returns consistent results across pages
- [ ] `performed_by` resolved to full_name + role (not raw UUID)
- [ ] `filters_applied` echoed in every response
- [ ] Receptionist and patient roles return 403
- [ ] Audit log entry written on every access
- [ ] All test cases pass
- [ ] Performance targets met (< 250ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Modifying or deleting history entries (immutable by design)
- Exporting history as PDF or CSV (separate export feature)
- Snapshot comparison (OD-08 handles that)
- Cross-patient history queries (admin analytics domain)

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
- [x] Input sanitization defined (Pydantic validators)
- [x] SQL injection prevented (SQLAlchemy ORM dynamic filters)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical history access

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 250ms)
- [x] Caching strategy stated (no cache — compliance requirement)
- [x] DB queries optimized (indexes listed, keyset pagination)
- [x] Pagination applied (cursor-based, default 50)

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
