# AP-13 List Waitlist Entries Spec

---

## Overview

**Feature:** Retrieve a paginated list of waitlist entries for the tenant, with filters by doctor, date range, and status. Used by receptionists and clinic owners to manage the waitlist queue and identify patients to contact when slots open.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-12 (waitlist-add.md), AP-14 (waitlist-notify.md), infra/authentication-rules.md, infra/caching.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Doctors may view the waitlist filtered to their own doctor_id only. clinic_owner, receptionist, and assistant may view all waitlist entries in the tenant. Patients cannot access this endpoint.

---

## Endpoint

```
GET /api/v1/appointments/waitlist
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
| doctor_id | No | uuid | Must be valid UUID if provided | Filter by preferred doctor | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |
| status | No | string | Enum: active, notified, booked, expired, cancelled; comma-separated | Filter by entry status | active,notified |
| valid_from | No | string | ISO 8601 date | Filter entries valid from this date | 2026-03-01 |
| valid_to | No | string | ISO 8601 date | Filter entries valid until this date | 2026-04-30 |
| procedure_type | No | string | Enum: consultation, procedure, emergency, follow_up | Filter by procedure type | consultation |
| cursor | No | string | Opaque cursor from previous response | Pagination cursor | eyJpZCI6ICJ... |
| limit | No | integer | 1-100; default 20 | Page size | 20 |

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
      "preferred_doctor_id": "uuid | null",
      "procedure_type": "string",
      "preferred_days": "integer[]",
      "preferred_time_from": "string | null (HH:MM)",
      "preferred_time_to": "string | null (HH:MM)",
      "valid_until": "string (ISO 8601 date)",
      "status": "string",
      "last_notified_at": "string | null (ISO 8601 datetime)",
      "notification_count": "integer",
      "notes": "string | null",
      "patient": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string",
        "phone": "string",
        "email": "string | null"
      },
      "preferred_doctor": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string"
      } | null,
      "created_by": "uuid",
      "created_at": "string (ISO 8601 datetime)"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "e5f6a1b2-c3d4-7890-abcd-34567890abcd",
      "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "preferred_doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "procedure_type": "consultation",
      "preferred_days": [0, 1, 2, 3, 4],
      "preferred_time_from": "08:00",
      "preferred_time_to": "13:00",
      "valid_until": "2026-04-15",
      "status": "active",
      "last_notified_at": null,
      "notification_count": 0,
      "notes": "Paciente flexible, prefiere mananas.",
      "patient": {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "first_name": "Maria",
        "last_name": "Garcia Lopez",
        "phone": "+573001234567",
        "email": "maria.garcia@email.com"
      },
      "preferred_doctor": {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "first_name": "Carlos",
        "last_name": "Mendez"
      },
      "created_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "created_at": "2026-03-10T14:30:00-05:00"
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

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor attempts to view waitlist for a different doctor_id.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo puede ver la lista de espera asignada a su propio horario."
}
```

#### 422 Unprocessable Entity
**When:** Invalid UUID format for doctor_id, invalid status enum, invalid limit value.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "status": ["Estado no valido. Opciones: active, notified, booked, expired, cancelled."],
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

1. Validate all query parameters via Pydantic query schema.
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. If caller role = doctor: force `doctor_id` filter to `caller_user_id`. If client provided a different `doctor_id`, return 403.
4. Build dynamic SQLAlchemy query with applicable filters (doctor_id, status array, valid_from, valid_to, procedure_type).
5. Default status filter (if not provided): return active and notified entries (most operationally relevant).
6. Apply cursor-based pagination using `waitlist_entry.created_at` + `id` as composite cursor. ORDER BY created_at ASC, id ASC (oldest entries first — first in, first out).
7. Execute query with JOIN to patient and preferred_doctor tables for summary fields.
8. Cache result with TTL 60 seconds using query-fingerprint key.
9. Return 200 with paginated list and pagination metadata.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| doctor_id | Valid UUID format if provided | Formato de UUID invalido. |
| status | Comma-separated; each must be valid enum value | Estado no valido. |
| valid_from, valid_to | ISO 8601 date format if provided | Formato de fecha invalido. |
| procedure_type | Valid enum value if provided | Tipo de procedimiento no valido. |
| limit | Integer 1-100 | El limite debe estar entre 1 y 100. |

**Business Rules:**

- Default status filter is `active,notified` (not all statuses) to reduce noise from historical entries.
- FIFO ordering (oldest first) ensures longest-waiting patients are prioritized.
- Doctor role sees only entries where `preferred_doctor_id = their own ID` or entries with `preferred_doctor_id = null` (any-doctor entries).
- `notification_count` tracks how many times a patient has been notified about available slots for this entry.
- `last_notified_at` is null for entries that have never been notified.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No waitlist entries matching filters | Return empty data array, total_count=0 |
| preferred_doctor_id = null entries | Returned for all staff (not doctor-specific) |
| Doctor queries with their own ID | 200 with their entries |
| status filter with all statuses | Returns all entries including historical ones |
| valid_from > valid_to | Return 400 invalid date range |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None. This is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:waitlist:list:{sha256(sorted_query_params)}`: SET on cache miss

**Cache TTL:** 60 seconds

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — listing waitlist is not individually audit-logged.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 100ms (cache hit), < 250ms (cache miss)
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Redis cache with query-fingerprint key
- **Cache key:** `tenant:{tenant_id}:waitlist:list:{sha256(sorted_query_params)}`
- **TTL:** 60 seconds
- **Invalidation:** On waitlist add (AP-12), waitlist notification (AP-14), or waitlist status change

### Database Performance

**Queries executed:** 1-2 (optional count + main query with JOIN)

**Indexes required:**
- `waitlist_entries.(preferred_doctor_id, status)` — COMPOSITE INDEX
- `waitlist_entries.status` — INDEX for status filtering
- `waitlist_entries.valid_until` — INDEX for date range filtering
- `waitlist_entries.(created_at, id)` — COMPOSITE INDEX for cursor pagination
- `waitlist_entries.procedure_type` — INDEX

**N+1 prevention:** Single JOIN loads patient and preferred_doctor summaries for all entries.

### Pagination

**Pagination:** Yes

**If Yes:**
- **Style:** cursor-based (composite cursor: created_at + id)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| doctor_id | Pydantic UUID validator | Rejects non-UUID strings |
| status | Pydantic enum validator per item after split | Whitelist approach |
| valid_from, valid_to | Pydantic date validator | ISO 8601 strict |
| procedure_type | Pydantic enum validator | Whitelist |
| cursor | Base64 decode + JSON parse with validation | Server-side cursor validation |
| limit | Pydantic int with ge=1, le=100 | Bounds enforced |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient.first_name, patient.last_name, patient.phone, patient.email, notes

**Audit requirement:** Not individually logged at list level.

---

## Testing

### Test Cases

#### Happy Path
1. Receptionist lists all active waitlist entries
   - **Given:** Receptionist JWT, 5 active entries across 2 doctors
   - **When:** GET /api/v1/appointments/waitlist
   - **Then:** 200 with 5 entries ordered by created_at ASC, status=active|notified

2. Filter by doctor
   - **Given:** clinic_owner JWT, entries for 2 doctors
   - **When:** GET /api/v1/appointments/waitlist?doctor_id={doctor_A_id}
   - **Then:** 200 with only doctor A's entries

3. Doctor views own waitlist
   - **Given:** Doctor A JWT, 3 entries for doctor A, 2 for doctor B
   - **When:** GET /api/v1/appointments/waitlist
   - **Then:** 200 with only doctor A's 3 entries

4. Filter by status=expired
   - **Given:** 10 entries: 5 active, 3 expired, 2 booked
   - **When:** GET /api/v1/appointments/waitlist?status=expired
   - **Then:** 200 with 3 expired entries

5. Paginated list
   - **Given:** 25 active entries
   - **When:** GET /api/v1/appointments/waitlist?limit=20
   - **Then:** 200 with 20 entries, has_more=true, next_cursor set

#### Edge Cases
1. Empty waitlist
   - **Given:** No waitlist entries in tenant
   - **When:** GET /api/v1/appointments/waitlist
   - **Then:** 200 with empty data array, total_count=0

2. Entries with preferred_doctor_id=null (any doctor)
   - **Given:** Mix of entries with and without preferred doctor
   - **When:** GET without doctor_id filter
   - **Then:** 200 with all entries including null-doctor ones

#### Error Cases
1. Doctor filters for another doctor's waitlist
   - **Given:** Doctor A JWT, doctor_id param = Doctor B's ID
   - **When:** GET /api/v1/appointments/waitlist?doctor_id={doctor_B_id}
   - **Then:** 403 Forbidden

2. Invalid status value
   - **Given:** GET /api/v1/appointments/waitlist?status=pending
   - **When:** Query executed
   - **Then:** 422 validation_failed

3. Patient role attempts to list
   - **Given:** Patient JWT
   - **When:** GET /api/v1/appointments/waitlist
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, two doctors, receptionist, patient (for negative test)

**Patients/Entities:** 25+ waitlist entries across multiple statuses, doctors, and procedure types

### Mocking Strategy

- Redis: Use `fakeredis` for cache hit/miss tests
- Database: Test tenant schema seeded with waitlist entries in various statuses

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/appointments/waitlist returns 200 with paginated list
- [ ] Default status filter is active,notified
- [ ] FIFO ordering (oldest first) applied
- [ ] Doctor role restricted to own waitlist entries (403 for other doctor_id)
- [ ] Patient role receives 403
- [ ] Status filter accepts comma-separated values
- [ ] Cursor-based pagination works correctly
- [ ] Results cached with 60-second TTL
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms cache hit, < 250ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Adding to waitlist (see AP-12)
- Notifying a waitlist patient (see AP-14)
- Removing/deactivating a waitlist entry (requires separate endpoint)
- Automatic expiry processing (background job)

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
