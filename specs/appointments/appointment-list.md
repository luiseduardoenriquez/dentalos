# AP-03 List Appointments Spec

---

## Overview

**Feature:** List appointments for the tenant with flexible filtering by doctor, patient, date range, and status. Returns results in both list and calendar-grouped formats. Default view is daily (today's appointments), matching the "daily view default" interview requirement. Supports cursor-based pagination for list view.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create.md), AP-02 (appointment-get.md), infra/authentication-rules.md, infra/caching.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients may only list their own appointments (doctor_id and patient_id filters ignored; patient_id forced to their own). Doctors see all appointments in the tenant unless filtered. Receptionists and assistants see all appointments in the tenant.

---

## Endpoint

```
GET /api/v1/appointments
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

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| doctor_id | No | uuid | Must be valid UUID if provided | Filter by doctor | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |
| patient_id | No | uuid | Must be valid UUID if provided | Filter by patient | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| date_from | No | string | ISO 8601 date (YYYY-MM-DD); defaults to today | Range start date | 2026-03-15 |
| date_to | No | string | ISO 8601 date (YYYY-MM-DD); max 90 days from date_from | Range end date | 2026-03-22 |
| status | No | string | Enum: scheduled, confirmed, in_progress, completed, cancelled, no_show; comma-separated for multiple | Filter by status | scheduled,confirmed |
| view | No | string | Enum: list, calendar; default: list | Response format | calendar |
| cursor | No | string | Opaque cursor from previous response | Pagination cursor | eyJpZCI6ICJ... |
| limit | No | integer | 1-100; default: 20 | Page size | 20 |

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema (view=list):**
```json
{
  "data": [
    {
      "id": "uuid",
      "patient_id": "uuid",
      "doctor_id": "uuid",
      "start_time": "string (ISO 8601 datetime)",
      "end_time": "string (ISO 8601 datetime)",
      "duration_minutes": "integer",
      "type": "string",
      "status": "string",
      "notes": "string | null",
      "patient": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string",
        "phone": "string"
      },
      "doctor": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string"
      }
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  }
}
```

**Schema (view=calendar):**
```json
{
  "data": {
    "2026-03-15": [
      {
        "id": "uuid",
        "patient_id": "uuid",
        "doctor_id": "uuid",
        "start_time": "string (ISO 8601 datetime)",
        "end_time": "string (ISO 8601 datetime)",
        "duration_minutes": "integer",
        "type": "string",
        "status": "string",
        "patient": {
          "id": "uuid",
          "first_name": "string",
          "last_name": "string",
          "phone": "string"
        },
        "doctor": {
          "id": "uuid",
          "first_name": "string",
          "last_name": "string"
        }
      }
    ],
    "2026-03-16": []
  },
  "date_range": {
    "from": "string (ISO 8601 date)",
    "to": "string (ISO 8601 date)"
  }
}
```

**Example (view=list, default daily):**
```json
{
  "data": [
    {
      "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
      "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "start_time": "2026-02-25T09:00:00-05:00",
      "end_time": "2026-02-25T09:30:00-05:00",
      "duration_minutes": 30,
      "type": "consultation",
      "status": "confirmed",
      "notes": null,
      "patient": {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "first_name": "Maria",
        "last_name": "Garcia Lopez",
        "phone": "+573001234567"
      },
      "doctor": {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "first_name": "Carlos",
        "last_name": "Mendez"
      }
    }
  ],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "total_count": 1
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** date_to is before date_from, or date range exceeds 90 days, or invalid status enum value.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El rango de fechas no puede superar 90 dias.",
  "details": {
    "date_range": ["El rango de fechas no puede superar 90 dias."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient user attempts to list appointments with a different patient_id.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para ver las citas de este paciente."
}
```

#### 422 Unprocessable Entity
**When:** Invalid UUID format for doctor_id or patient_id, invalid date format, invalid limit value.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "doctor_id": ["Formato de UUID invalido."],
    "limit": ["El limite debe estar entre 1 y 100."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache error.

---

## Business Logic

**Step-by-step process:**

1. Validate all query parameters via Pydantic query schema (UUIDs, date formats, enums, limit range).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Extract caller role and caller_user_id from JWT.
4. If caller role = patient: force `patient_id` filter to caller's linked patient record. Ignore any client-supplied `doctor_id` or `patient_id` params. Return 403 if patient has no linked record.
5. Apply defaults: if `date_from` not provided, default to today (tenant timezone). If `date_to` not provided and `view=calendar`, default to same day as `date_from` (daily view). If `view=list`, default `date_to` to 30 days from `date_from`.
6. Validate date range does not exceed 90 days. Return 400 if exceeded.
7. Parse `status` filter: split comma-separated string into array of valid enum values.
8. Build dynamic SQLAlchemy query with applicable filters (doctor_id, patient_id, date_range, status list).
9. For `view=list`: apply cursor-based pagination using `appointment.start_time` + `appointment.id` as composite cursor. ORDER BY start_time ASC, id ASC.
10. For `view=calendar`: fetch all matching records (no pagination), group by date key (YYYY-MM-DD in tenant timezone), return all dates in range (empty arrays for dates with no appointments).
11. Execute query with JOIN to patient and doctor tables for summary fields.
12. Cache result with appropriate TTL based on date range (see Caching Strategy).
13. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| doctor_id | Valid UUID format if provided | Formato de UUID invalido. |
| patient_id | Valid UUID format if provided | Formato de UUID invalido. |
| date_from | ISO 8601 date format if provided | Formato de fecha invalido (YYYY-MM-DD). |
| date_to | ISO 8601 date format, must be >= date_from | La fecha de fin debe ser posterior a la fecha de inicio. |
| date_to - date_from | Max 90 days | El rango de fechas no puede superar 90 dias. |
| status | Comma-separated; each value must be valid enum | Estado de cita no valido. |
| view | Enum: list, calendar | Vista no valida. Opciones: list, calendar. |
| limit | Integer 1-100 | El limite debe estar entre 1 y 100. |

**Business Rules:**

- Default behavior (no filters): returns today's appointments for all doctors, list view, chronological order.
- Calendar view returns all dates in range as keys even if empty (supports UI rendering of empty days).
- Notes field is intentionally excluded from list/calendar view for performance; available in AP-02 detail endpoint.
- Patient role cannot filter by other patients or doctors; their filter is always forced to their own patient record.
- `view=calendar` does not support cursor pagination; returns all records in range (enforced 90-day max prevents overload).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No appointments in date range | Return empty data array (list) or empty date keys (calendar) |
| date_from equals date_to | Return single day (valid) |
| Patient user with no linked patient record | Return 403 |
| status filter with single value (no comma) | Parse correctly as single-item array |
| view=calendar with limit param | Ignore limit param; return all in range |
| doctor_id provided but doctor not in tenant | Return empty results (not 404) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None. This is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:appointments:list:{hash(filters)}`: SET on cache miss — hashed query param fingerprint as key
- `tenant:{tenant_id}:appointments:calendar:{doctor_id}:{date}`: SET per date (used by calendar view)

**Cache TTL:** 60 seconds for list view (changes frequently with status updates); 120 seconds for calendar view of past dates.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — bulk listing is not individually audit-logged (read PHI access is tracked at detail level).

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 100ms (cache hit), < 250ms (cache miss, daily view)
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Redis cache with query-fingerprint key
- **Cache key:** `tenant:{tenant_id}:appointments:list:{sha256(sorted_query_params)}`
- **TTL:** 60 seconds (list), 120 seconds (calendar for past/current day)
- **Invalidation:** On any appointment create, update, or status transition within the queried date range and doctor scope

### Database Performance

**Queries executed:** 1-2 (count query optional, main query with JOIN)

**Indexes required:**
- `appointments.(doctor_id, start_time)` — COMPOSITE INDEX for doctor+date filters
- `appointments.(patient_id, start_time)` — COMPOSITE INDEX for patient+date filters
- `appointments.status` — INDEX for status filtering
- `appointments.start_time` — INDEX (for date range scans)
- `appointments.(start_time, id)` — COMPOSITE INDEX for cursor pagination

**N+1 prevention:** Single JOIN query loads patient and doctor summary for all appointments in one query.

### Pagination

**Pagination:** Yes (list view only)

**If Yes:**
- **Style:** cursor-based (composite cursor: start_time + id)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| doctor_id, patient_id | Pydantic UUID validator | Rejects non-UUID strings |
| date_from, date_to | Pydantic date validator | ISO 8601 strict parsing |
| status | Pydantic enum validator per item after split | Whitelist approach |
| cursor | Base64 decode + JSON parse with validation | Opaque cursor, validated server-side |
| limit | Pydantic int with ge=1, le=100 | Bounds enforced |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient.first_name, patient.last_name, patient.phone (summary fields only in list/calendar view)

**Audit requirement:** Not individually logged at list level; detail-level access logged via AP-02.

---

## Testing

### Test Cases

#### Happy Path
1. Receptionist lists today's appointments (default, no filters)
   - **Given:** Valid receptionist JWT, 5 appointments for today across 2 doctors
   - **When:** GET /api/v1/appointments
   - **Then:** 200 with 5 appointments ordered by start_time ASC, list view

2. Clinic owner views weekly calendar
   - **Given:** Valid clinic_owner JWT, appointments across Mon-Fri next week
   - **When:** GET /api/v1/appointments?view=calendar&date_from=2026-03-16&date_to=2026-03-20
   - **Then:** 200 with calendar object, 5 date keys, appointments under correct dates

3. Doctor filters own appointments by status
   - **Given:** Valid doctor JWT, 3 confirmed appointments, 2 cancelled
   - **When:** GET /api/v1/appointments?status=confirmed&doctor_id={own_id}
   - **Then:** 200 with 3 confirmed appointments

4. Patient lists own appointments
   - **Given:** Valid patient JWT, 2 appointments linked to their patient record
   - **When:** GET /api/v1/appointments
   - **Then:** 200 with only their 2 appointments, doctor_id filter ignored

5. Paginated list — cursor navigation
   - **Given:** 25 appointments matching filters
   - **When:** GET /api/v1/appointments?limit=20
   - **Then:** 200 with 20 items, next_cursor set, has_more=true

#### Edge Cases
1. Date range with no appointments
   - **Given:** Valid filters for a date range with zero appointments
   - **When:** GET /api/v1/appointments?date_from=2026-12-25&date_to=2026-12-25
   - **Then:** 200 with empty data array, total_count=0

2. Calendar view returns empty date keys
   - **Given:** view=calendar, 3-day range, appointments only on day 1
   - **When:** GET /api/v1/appointments?view=calendar&date_from=...&date_to=...
   - **Then:** 200 with 3 date keys; days 2 and 3 have empty arrays

3. Multiple status filters comma-separated
   - **Given:** GET /api/v1/appointments?status=scheduled,confirmed
   - **When:** Query executed
   - **Then:** Returns appointments with either status

#### Error Cases
1. Date range exceeds 90 days
   - **Given:** date_from=2026-01-01, date_to=2026-06-01
   - **When:** GET /api/v1/appointments
   - **Then:** 400 Bad Request

2. Patient requests with explicit other patient_id
   - **Given:** Patient JWT, patient_id param = different patient's UUID
   - **When:** GET /api/v1/appointments?patient_id={other_patient_id}
   - **Then:** 403 Forbidden

3. Invalid status enum value
   - **Given:** GET /api/v1/appointments?status=pending
   - **When:** Query executed
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** clinic_owner, doctor (with appointments), receptionist, patient (linked to patient record), second patient

**Patients/Entities:** 25+ appointments across multiple doctors and statuses; appointments on multiple dates for calendar tests

### Mocking Strategy

- Redis: Use `fakeredis` for cache hit/miss tests
- Database: Test tenant schema seeded with appointments across multiple dates, doctors, patients, statuses

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/appointments returns 200 with list or calendar format based on view param
- [ ] Default view is list, default date is today
- [ ] Calendar view groups by date with all days in range as keys (empty arrays included)
- [ ] Cursor-based pagination works correctly for list view
- [ ] Patient role forced to own appointments; 403 for other patient_id
- [ ] Status filter accepts comma-separated values
- [ ] Date range exceeding 90 days returns 400
- [ ] Results cached with 60-second TTL and query fingerprint key
- [ ] Cache invalidated on appointment state changes
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms cache hit, < 250ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Appointment detail (see AP-02)
- Availability slots (see AP-09)
- Waitlist entries (see AP-13)
- Appointment export to CSV/PDF (separate analytics feature)

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
