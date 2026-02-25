# Get Doctor Schedule Spec

---

## Overview

**Feature:** Retrieve a doctor's weekly working schedule, including working days, time ranges, break periods, and default appointment durations per procedure type. Used by the appointment booking system to calculate available time slots.

**Domain:** users

**Priority:** Medium

**Dependencies:** U-01 (get-profile.md), AP-09 (appointment availability slots)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** doctor (own schedule), clinic_owner, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** A doctor may only read their own schedule unless they are a clinic_owner. Receptionists may read any doctor's schedule (needed for booking). Assistants cannot read doctor schedules directly.

---

## Endpoint

```
GET /api/v1/users/{user_id}/schedule
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_a1b2c3d4e5f6 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| user_id | Yes | uuid | Must be valid UUID; user must exist and have role = doctor | The doctor's user ID | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "user_id": "uuid",
  "days": [
    {
      "day_of_week": "integer (0-6, Monday=0)",
      "is_working": "boolean",
      "start_time": "string | null (HH:MM, 24h)",
      "end_time": "string | null (HH:MM, 24h)",
      "breaks": [
        {
          "break_start": "string (HH:MM, 24h)",
          "break_end": "string (HH:MM, 24h)"
        }
      ]
    }
  ],
  "appointment_duration_defaults": {
    "evaluacion": "integer (minutes)",
    "endodoncia": "integer (minutes)",
    "limpieza": "integer (minutes)",
    "urgencia": "integer (minutes)"
  },
  "updated_at": "datetime | null"
}
```

**Example:**
```json
{
  "user_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "days": [
    {
      "day_of_week": 0,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": [
        { "break_start": "13:00", "break_end": "14:00" }
      ]
    },
    {
      "day_of_week": 1,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": []
    },
    {
      "day_of_week": 2,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": [
        { "break_start": "13:00", "break_end": "14:00" }
      ]
    },
    {
      "day_of_week": 3,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": []
    },
    {
      "day_of_week": 4,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "13:00",
      "breaks": []
    },
    {
      "day_of_week": 5,
      "is_working": false,
      "start_time": null,
      "end_time": null,
      "breaks": []
    },
    {
      "day_of_week": 6,
      "is_working": false,
      "start_time": null,
      "end_time": null,
      "breaks": []
    }
  ],
  "appointment_duration_defaults": {
    "evaluacion": 20,
    "endodoncia": 80,
    "limpieza": 30,
    "urgencia": 15
  },
  "updated_at": "2026-02-20T09:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Authenticated user is not the target doctor, clinic_owner, or receptionist. Assistants receive 403.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para ver el horario de este doctor."
}
```

#### 404 Not Found
**When:** `user_id` does not exist in the tenant, or the user exists but has a role other than `doctor`.

**Example:**
```json
{
  "error": "not_found",
  "message": "Doctor no encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache error.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract `caller_user_id`, `caller_role`, and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id`.
3. Check RBAC: caller must be doctor (with `caller_user_id == user_id`), clinic_owner, or receptionist. Reject all others with 403.
4. Query `users` table to confirm `user_id` exists and has `role = 'doctor'`. If not found, return 404.
5. Check Redis cache for key `tenant:{tenant_id}:user:{user_id}:schedule`.
6. If cache hit, return cached schedule directly.
7. If cache miss, query `doctor_schedules` table: `SELECT * FROM doctor_schedules WHERE user_id = :user_id`.
8. If no schedule row exists yet, return a default schedule: all 7 days `is_working = false`, default durations applied.
9. Serialize via Pydantic `DoctorScheduleResponse`.
10. Cache result with TTL 300 seconds.
11. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| user_id | Must be a valid UUID format | "ID de usuario invalido." |
| user_id | Must correspond to a user with role = doctor in the tenant | "Doctor no encontrado." |

**Business Rules:**

- If the doctor has never configured a schedule, the endpoint returns the system defaults rather than 404: all days `is_working = false`, durations `{ evaluacion: 20, endodoncia: 80, limpieza: 30, urgencia: 15 }`.
- `is_working = false` days always return `start_time: null`, `end_time: null`, and `breaks: []`.
- The `appointment_duration_defaults` map may contain additional custom procedure types beyond the four standard ones, as set by U-08.
- Times are stored and returned in 24-hour `HH:MM` format, tenant-timezone-aware display is left to the frontend.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor has never set a schedule | Return default schedule (all non-working, standard durations) |
| Redis cache unavailable | Fall back to direct DB query. Log warning. Do not fail request. |
| user_id belongs to a non-doctor role (e.g., receptionist) | Return 404 "Doctor no encontrado." |
| Caller is a doctor requesting another doctor's schedule | Return 403 Forbidden |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None. This is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:schedule`: SET on cache miss — stores serialized schedule JSON.

**Cache TTL:** 300 seconds (5 minutes).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — reading a schedule is not a clinical PHI operation; not audit-logged.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 50ms (cache hit), < 150ms (cache miss)
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** Redis cache
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:schedule`
- **TTL:** 300 seconds (5 minutes)
- **Invalidation:** On schedule update (U-08). Also invalidate appointment availability cache keys for this doctor.

### Database Performance

**Queries executed:** 0 (cache hit) or 1-2 (cache miss: user lookup + schedule fetch)

**Indexes required:**
- `users.id` — PRIMARY KEY (exists)
- `doctor_schedules.user_id` — INDEX (for single-row fetch by doctor)

**N+1 prevention:** Not applicable — single doctor, single schedule row.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| user_id (URL param) | Pydantic UUID validator | Rejects non-UUID strings before DB query |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Doctor working schedules are operational data, not PHI.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. Clinic owner retrieves a doctor's schedule (cache miss)
   - **Given:** Valid clinic_owner JWT, target doctor has a saved schedule
   - **When:** GET /api/v1/users/{user_id}/schedule
   - **Then:** 200 with full 7-day schedule and appointment_duration_defaults

2. Receptionist retrieves a doctor's schedule (cache hit)
   - **Given:** Valid receptionist JWT, schedule cached in Redis
   - **When:** GET /api/v1/users/{user_id}/schedule
   - **Then:** 200 from cache within 50ms

3. Doctor retrieves own schedule
   - **Given:** Valid doctor JWT, `user_id` matches caller's ID
   - **When:** GET /api/v1/users/{user_id}/schedule
   - **Then:** 200 with own schedule

4. Doctor with no schedule configured returns defaults
   - **Given:** Valid clinic_owner JWT, target doctor has no schedule row in DB
   - **When:** GET /api/v1/users/{user_id}/schedule
   - **Then:** 200 with all `is_working: false` and standard durations

#### Edge Cases
1. Redis unavailable — graceful fallback
   - **Given:** Redis is down, valid clinic_owner JWT
   - **When:** GET /api/v1/users/{user_id}/schedule
   - **Then:** 200 from DB; warning logged in structured JSON

2. Doctor with custom procedure types in duration defaults
   - **Given:** Doctor has a saved schedule with custom type `corona: 60`
   - **When:** GET /api/v1/users/{user_id}/schedule
   - **Then:** 200 includes `corona: 60` in `appointment_duration_defaults`

#### Error Cases
1. Doctor requests another doctor's schedule
   - **Given:** Valid doctor JWT, `user_id` belongs to a different doctor
   - **When:** GET /api/v1/users/{other_doctor_id}/schedule
   - **Then:** 403 Forbidden

2. user_id belongs to a receptionist
   - **Given:** Valid clinic_owner JWT, `user_id` belongs to a receptionist
   - **When:** GET /api/v1/users/{receptionist_id}/schedule
   - **Then:** 404 "Doctor no encontrado."

3. user_id does not exist
   - **Given:** Valid clinic_owner JWT, non-existent UUID
   - **When:** GET /api/v1/users/{fake_id}/schedule
   - **Then:** 404 "Doctor no encontrado."

4. No Authorization header
   - **Given:** No JWT provided
   - **When:** GET /api/v1/users/{user_id}/schedule
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** One clinic_owner, two doctors (one with schedule configured, one without), one receptionist, one assistant.

**Patients/Entities:** None.

### Mocking Strategy

- Redis: Use `fakeredis` for cache tests; disconnect mock for fallback test.
- Database: Use test tenant schema with seeded `doctor_schedules` rows.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/users/{user_id}/schedule returns 200 with full schedule for valid doctor
- [ ] Default schedule returned when doctor has no saved schedule (no 404)
- [ ] Response includes all 7 days (0-6) always
- [ ] `appointment_duration_defaults` present with at minimum the 4 standard types
- [ ] Response is cached in Redis for 5 minutes
- [ ] Cache fallback to DB works when Redis is unavailable
- [ ] clinic_owner and receptionist can read any doctor's schedule
- [ ] Doctor can only read own schedule; 403 for others
- [ ] Non-doctor user_id returns 404
- [ ] All test cases pass
- [ ] Performance targets met (< 50ms cache hit, < 150ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Updating or setting the doctor's schedule (see U-08: doctor-schedule-update.md)
- Computing available appointment slots from the schedule (see AP-09)
- Holiday or exception dates (e.g., doctor is off on a specific date despite normally working)
- Timezone conversion — times are returned in 24h format; frontend handles display conversion

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
| 1.0 | 2026-02-24 | Initial spec |
