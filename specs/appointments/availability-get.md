# AP-09 Get Availability Spec

---

## Overview

**Feature:** Calculate and return available time slots for a doctor within a date range, given a desired duration. Used by the appointment booking UI (staff calendar), patient self-booking portal, and intelligent duration suggestions. Accounts for doctor schedule, existing appointments, and blocked time slots.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** U-07 (doctor-schedule-get.md), AP-01 (appointment-create.md), AP-10 (availability-block.md), infra/authentication-rules.md, infra/caching.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** All authenticated tenant users may query availability. Patient role queries are restricted to public booking flow via AP-16; this endpoint requires staff or patient portal authentication. Unauthenticated public availability is via AP-16.

---

## Endpoint

```
GET /api/v1/appointments/availability
```

**Rate Limiting:**
- 120 requests per minute per user (high limit — called frequently during booking flow)

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
| doctor_id | Yes | uuid | Must be valid UUID; user must have role=doctor | Doctor to check availability for | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |
| date_from | Yes | string | ISO 8601 date (YYYY-MM-DD); must not be in the past | Start of date range | 2026-03-15 |
| date_to | No | string | ISO 8601 date (YYYY-MM-DD); max 14 days from date_from; defaults to date_from | End of date range | 2026-03-22 |
| duration | No | integer | Minutes; 10-240; default 30 | Desired appointment duration in minutes | 30 |
| type | No | string | Enum: consultation, procedure, emergency, follow_up | Auto-select duration from doctor defaults | consultation |

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "doctor_id": "uuid",
  "date_from": "string (ISO 8601 date)",
  "date_to": "string (ISO 8601 date)",
  "duration_minutes": "integer",
  "slots": {
    "2026-03-15": [
      {
        "start": "string (ISO 8601 datetime)",
        "end": "string (ISO 8601 datetime)",
        "available": "boolean"
      }
    ],
    "2026-03-16": []
  }
}
```

**Example:**
```json
{
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "date_from": "2026-03-15",
  "date_to": "2026-03-15",
  "duration_minutes": 30,
  "slots": {
    "2026-03-15": [
      {
        "start": "2026-03-15T08:00:00-05:00",
        "end": "2026-03-15T08:30:00-05:00",
        "available": true
      },
      {
        "start": "2026-03-15T08:30:00-05:00",
        "end": "2026-03-15T09:00:00-05:00",
        "available": true
      },
      {
        "start": "2026-03-15T09:00:00-05:00",
        "end": "2026-03-15T09:30:00-05:00",
        "available": false
      },
      {
        "start": "2026-03-15T09:30:00-05:00",
        "end": "2026-03-15T10:00:00-05:00",
        "available": true
      }
    ]
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** date_to before date_from, date range exceeds 14 days, duration out of bounds, or date_from in the past.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El rango de fechas no puede superar 14 dias.",
  "details": {
    "date_range": ["El rango de fechas no puede superar 14 dias."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 404 Not Found
**When:** doctor_id does not exist or is not a doctor role in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Doctor no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Invalid UUID format for doctor_id, invalid date format, duration out of range.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "duration": ["La duracion debe estar entre 10 y 240 minutos."],
    "doctor_id": ["Formato de UUID invalido."]
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

1. Validate all query parameters via Pydantic query schema.
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Validate `doctor_id` exists and has role = doctor. Return 404 if not.
4. Apply defaults: if `date_to` not provided, default to `date_from` (single day). Validate range <= 14 days.
5. If `type` provided and `duration` not provided: look up doctor's `appointment_duration_defaults[type]`. Fall back to system defaults. Override `duration` with this value.
6. Check Redis cache: `tenant:{tenant_id}:availability:{doctor_id}:{date_from}:{date_to}:{duration}`. Return if hit.
7. Load doctor's schedule from cache or DB (U-07 structure).
8. For each date in `date_from..date_to`:
   a. Determine `is_working` day from schedule. If not working, return empty slots array for that date.
   b. Generate candidate slots: start from `day_start_time`, advance by `duration` minutes each step until `day_end_time`. Break for any break windows.
   c. Load all existing appointments for this doctor on this date with status in (scheduled, confirmed, in_progress).
   d. Load all availability blocks (AP-10) for this doctor on this date.
   e. For each candidate slot: mark `available = false` if any appointment or block overlaps it.
9. Cache result with TTL 60 seconds.
10. Return 200 with slots object keyed by date.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| doctor_id | Valid UUID, role=doctor in tenant | Doctor no encontrado. |
| date_from | ISO 8601 date, not in the past | La fecha de inicio no puede ser en el pasado. |
| date_to | ISO 8601 date, >= date_from, max 14 days ahead of date_from | El rango de fechas no puede superar 14 dias. |
| duration | Integer, 10-240 inclusive | La duracion debe estar entre 10 y 240 minutos. |
| type | Enum: consultation, procedure, emergency, follow_up (if provided) | Tipo de cita no valido. |

**Business Rules:**

- Slots are generated with `duration`-minute granularity aligned to the doctor's schedule start_time (e.g., 08:00, 08:30, 09:00...).
- Slots that overlap with breaks are skipped (not returned as unavailable — simply not generated).
- Emergency appointments do not block slots (they were allowed through even in occupied slots), so they are excluded from the busy-slot calculation.
- `available = false` slots are included in the response to allow UI to show "already taken" slots for context (vs completely empty time blocks).
- Response keys only dates within doctor working days. Non-working days return empty array.
- If `type` is provided alongside explicit `duration`, `duration` takes precedence.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor has no configured schedule | Return empty slots for all dates (no working windows defined) |
| Duration longer than working window | Return empty slots for that date |
| Break exactly at slot boundary | Slot ending exactly at break start is valid; slot starting at break start is skipped |
| date_from = today, doctor already past working hours | Return empty array for today (past slots not shown) |
| All slots taken for a day | All slots returned with available=false |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None. This is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:availability:{doctor_id}:{date_from}:{date_to}:{duration}`: SET on cache miss

**Cache TTL:** 60 seconds — short TTL because appointments can be booked at any moment, changing availability.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — availability queries are not PHI and not audit-logged.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 80ms (cache hit), < 200ms (cache miss, single day)
- **Maximum acceptable:** < 400ms (14-day range, cache miss)

### Caching Strategy
- **Strategy:** Redis cache
- **Cache key:** `tenant:{tenant_id}:availability:{doctor_id}:{date_from}:{date_to}:{duration}`
- **TTL:** 60 seconds
- **Invalidation:** On appointment create, update, cancel, complete, no-show; on availability block create/delete; on doctor schedule update

### Database Performance

**Queries executed:** 0 (cache hit) or 2 (cache miss: schedule load + appointments/blocks fetch for date range)

**Indexes required:**
- `doctor_schedules.user_id` — INDEX (exists from U-07)
- `appointments.(doctor_id, start_time, status)` — COMPOSITE INDEX
- `availability_blocks.(doctor_id, start_time, end_time)` — COMPOSITE INDEX

**N+1 prevention:** Appointments and blocks for entire date range loaded in single queries; slot generation done in-memory.

### Pagination

**Pagination:** No (all slots for date range returned; 14-day max enforces bounded response size)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| doctor_id | Pydantic UUID validator | Rejects non-UUID strings |
| date_from, date_to | Pydantic date validator | ISO 8601 strict parsing |
| duration | Pydantic int with ge=10, le=240 | Bounds enforced |
| type | Pydantic enum validator | Whitelist |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Availability slots are operational scheduling data, not PHI.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. Single-day availability for doctor with mixed slots
   - **Given:** Doctor works Mon-Fri 08:00-17:00, lunch break 13:00-14:00, 2 existing appointments (09:00 and 10:00)
   - **When:** GET /api/v1/appointments/availability?doctor_id=...&date_from=2026-03-16&duration=30
   - **Then:** 200 with slots every 30 min from 08:00-17:00 (excluding break), 09:00 and 10:00 slots marked available=false

2. Weekly view for booking widget
   - **Given:** Doctor has schedule for Mon-Fri, date range is a full week
   - **When:** GET with date_from=Monday, date_to=Friday
   - **Then:** 200 with 5 date keys; Saturday/Sunday would be excluded (not requested)

3. Duration auto-calculated from type
   - **Given:** Doctor has custom consultation=45 in duration_defaults
   - **When:** GET with type=consultation (no explicit duration)
   - **Then:** 200 with 45-minute slots

4. Cache hit
   - **Given:** Same request made twice within 60 seconds
   - **When:** Second GET
   - **Then:** 200 from cache within 80ms

#### Edge Cases
1. Doctor non-working day requested
   - **Given:** Doctor has Saturday is_working=false
   - **When:** GET with date_from=Saturday
   - **Then:** 200 with slots["2026-03-21"]: [] (empty array)

2. No schedule configured for doctor
   - **Given:** Doctor has never set up schedule (no doctor_schedules row)
   - **When:** GET availability
   - **Then:** 200 with empty slots for all dates

3. Duration longer than half-day working window
   - **Given:** Doctor works 08:00-12:00 (4 hours), requested duration=300 min
   - **When:** GET with duration=300
   - **Then:** 400 Bad Request — duration exceeds 240 max

#### Error Cases
1. doctor_id not a doctor (receptionist UUID)
   - **Given:** Valid UUID but role=receptionist
   - **When:** GET availability
   - **Then:** 404 Doctor no encontrado

2. date_range exceeds 14 days
   - **Given:** date_from=2026-03-01, date_to=2026-03-20
   - **When:** GET
   - **Then:** 400 invalid_input

3. No JWT
   - **Given:** No Authorization header
   - **When:** GET /api/v1/appointments/availability
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** clinic_owner, doctor with full schedule configured, doctor without schedule, receptionist (for negative test)

**Patients/Entities:** Existing appointments for the test doctor across several dates; availability blocks configured

### Mocking Strategy

- Redis: Use `fakeredis`; test cache hit/miss scenarios; simulate Redis unavailable for fallback
- Database: Seed `doctor_schedules`, `appointments`, and `availability_blocks` tables

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/appointments/availability returns 200 with correct slot arrays per date
- [ ] Slots respect doctor's working hours and breaks
- [ ] Existing appointments mark slots as available=false
- [ ] Blocked time (AP-10) marks slots as available=false
- [ ] Emergency appointments excluded from busy-slot calculation
- [ ] duration auto-resolved from type when not explicitly provided
- [ ] 14-day max enforced; 400 if exceeded
- [ ] Non-working days return empty slot array
- [ ] Results cached 60 seconds with invalidation on booking events
- [ ] All test cases pass
- [ ] Performance targets met (< 80ms cache hit, < 200ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Public availability for patient self-booking (see AP-16 — uses public config endpoint)
- Blocking time slots (see AP-10)
- Multi-doctor availability comparison
- Appointment booking (see AP-01)

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
