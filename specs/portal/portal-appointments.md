# PP-03 Portal Appointments Spec

---

## Overview

**Feature:** List a patient's own appointments from the portal — both upcoming and past. Returns paginated results with doctor name, appointment type, status, and scheduled time. Read-only. Separated by default into upcoming vs. past via query parameter.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-02 (portal-profile.md), appointments domain (AP-01 appointment-create.md), infra/multi-tenancy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT (portal JWT contains tenant_id claim)
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient can only see their own appointments — query is always filtered by patient_id from JWT sub claim.

---

## Endpoint

```
GET /api/v1/portal/appointments
```

**Rate Limiting:**
- 30 requests per minute per patient

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| view | No | string | enum: upcoming, past, all; default: upcoming | Filter by time relative to now | upcoming |
| status | No | string | enum: confirmed, pending, cancelled, completed, no_show | Filter by appointment status | confirmed |
| cursor | No | string | Opaque cursor token from previous response | Cursor for pagination | eyJpZCI6... |
| limit | No | integer | 1-100; default: 20 | Number of results per page | 20 |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "items": [
    {
      "id": "uuid",
      "scheduled_at": "string (ISO 8601 datetime with timezone)",
      "duration_minutes": "integer",
      "status": "string — enum: confirmed, pending, cancelled, completed, no_show",
      "appointment_type": "string",
      "doctor": {
        "id": "uuid",
        "name": "string — Dr./Dra. + full name",
        "specialty": "string | null"
      },
      "location": {
        "name": "string — clinic branch name",
        "address": "string | null"
      },
      "notes_for_patient": "string | null — optional pre-appointment instructions",
      "can_cancel": "boolean — whether patient can still cancel per policy",
      "cancel_deadline": "string (ISO 8601 datetime) | null — latest time to cancel"
    }
  ],
  "pagination": {
    "cursor": "string | null — next page cursor, null if last page",
    "has_more": "boolean",
    "total_count": "integer — total appointments matching filter"
  },
  "summary": {
    "upcoming_count": "integer",
    "past_count": "integer"
  }
}
```

**Example:**
```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "scheduled_at": "2026-03-10T10:00:00-05:00",
      "duration_minutes": 45,
      "status": "confirmed",
      "appointment_type": "Limpieza dental",
      "doctor": {
        "id": "d1e2f3a4-b5c6-7890-abcd-123456789012",
        "name": "Dr. Juan Martinez",
        "specialty": "Odontologia General"
      },
      "location": {
        "name": "Sede Norte",
        "address": "Calle 100 # 15-20, Bogota"
      },
      "notes_for_patient": "Por favor llegar 10 minutos antes.",
      "can_cancel": true,
      "cancel_deadline": "2026-03-09T10:00:00-05:00"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-234567890123",
      "scheduled_at": "2026-03-25T14:30:00-05:00",
      "duration_minutes": 60,
      "status": "pending",
      "appointment_type": "Endodoncia",
      "doctor": {
        "id": "e2f3a4b5-c6d7-8901-bcde-345678901234",
        "name": "Dra. Lucia Fernandez",
        "specialty": "Endodoncia"
      },
      "location": {
        "name": "Sede Principal",
        "address": "Av. El Dorado # 68B-31, Bogota"
      },
      "notes_for_patient": null,
      "can_cancel": true,
      "cancel_deadline": "2026-03-23T14:30:00-05:00"
    }
  ],
  "pagination": {
    "cursor": null,
    "has_more": false,
    "total_count": 2
  },
  "summary": {
    "upcoming_count": 2,
    "past_count": 8
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values (invalid enum, limit out of range).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta no validos.",
  "details": {
    "view": ["Valor no valido. Opciones: upcoming, past, all."],
    "limit": ["El limite debe estar entre 1 y 100."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal" or role is not "patient".

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id from sub claim, tenant_id from JWT.
2. Validate query parameters against Pydantic schema (enums, integer ranges).
3. Resolve tenant schema; set `search_path`.
4. Build base query: `SELECT ... FROM appointments WHERE patient_id = :patient_id`.
5. Apply view filter:
   - `upcoming`: `scheduled_at >= NOW()` AND `status NOT IN ('cancelled')`
   - `past`: `scheduled_at < NOW()` OR `status IN ('completed', 'no_show', 'cancelled')`
   - `all`: no time filter
6. Apply optional status filter if provided.
7. Apply cursor-based pagination: decode cursor to get last seen `(scheduled_at, id)`, apply `WHERE (scheduled_at, id) > (cursor_scheduled_at, cursor_id)` for upcoming (ASC order) or `< ` for past (DESC order).
8. JOIN users table for doctor name and specialty.
9. JOIN clinic_locations (or similar) for location name and address.
10. Compute `can_cancel` and `cancel_deadline` for each appointment:
    - Fetch tenant cancellation policy from `tenant_settings.cancellation_policy_hours` (e.g., 24).
    - `cancel_deadline = scheduled_at - policy_hours`.
    - `can_cancel = cancel_deadline > NOW()` AND `status IN ('confirmed', 'pending')`.
11. Compute summary counts: two separate COUNT queries for upcoming and past totals.
12. Build pagination cursor from last item's `(scheduled_at, id)`.
13. Cache result in Redis.
14. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| view | Must be: upcoming, past, all | Valor no valido. Opciones: upcoming, past, all. |
| status | Must be valid enum if provided | Estado de cita no valido. |
| limit | Integer 1-100 | El limite debe estar entre 1 y 100. |
| cursor | Must be valid base64-encoded cursor if provided | Cursor de paginacion no valido. |

**Business Rules:**

- Patient ownership enforced at query level (`patient_id = {jwt.sub}`) — not just middleware.
- `can_cancel` is computed server-side based on tenant's cancellation policy (configurable in hours: 0=anytime, 24, 48).
- Cancelled appointments appear in both past and upcoming (if future) but `can_cancel=false`.
- Doctor name shown as "Dr." or "Dra." based on doctor's gender field: `dr_prefix + first_name + last_name`.
- `notes_for_patient` is a specific field distinct from internal staff notes — only patient-facing instructions shown.
- Default sort: upcoming = ASC by scheduled_at; past = DESC by scheduled_at.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no appointments | items = [], total_count = 0, summary counts = 0 |
| Appointment is today, in 2 hours | Appears in upcoming view |
| Appointment cancelled but in the future | Appears in past view (cancelled = past regardless of date) |
| Cancellation policy = 0 hours | can_cancel = true for all future confirmed/pending appointments |
| Doctor record deleted (soft-delete) | Show "Doctor no disponible" as doctor name |

---

## Side Effects

### Database Changes

None. Read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:appointments:{view}:{status}:{cursor}:{limit}`: SET — paginated results, TTL 2 minutes

**Cache TTL:** 2 minutes (short to reflect appointment status changes promptly)

### Queue Jobs (RabbitMQ)

None.

### Audit Log

**Audit entry:** No — appointment list views are not individually audited (high volume, low sensitivity for self-access).

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms (with cache hit)
- **Maximum acceptable:** < 300ms (cache miss)

### Caching Strategy
- **Strategy:** Redis cache, tenant+patient-namespaced, short TTL
- **Cache key:** `tenant:{tenant_id}:portal:patient:{patient_id}:appointments:{view}:{status_filter}:{cursor_hash}:{limit}`
- **TTL:** 2 minutes
- **Invalidation:** On appointment created, updated, or cancelled for this patient

### Database Performance

**Queries executed:** 3 (main paginated list, upcoming count, past count — counts executed in parallel)

**Indexes required:**
- `appointments.(patient_id, scheduled_at)` — COMPOSITE INDEX (primary query filter + sort)
- `appointments.(patient_id, status)` — COMPOSITE INDEX (status filter)
- `appointments.scheduled_at` — INDEX (for time-based filtering)

**N+1 prevention:** Doctor and location data fetched via JOIN in main query, not per-item lookups.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset pagination on scheduled_at + id)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| view | Pydantic Literal enum validation | Strict allowlist |
| status | Pydantic Literal enum validation | Strict allowlist |
| cursor | Base64 decode + JSON parse + UUID/datetime validation | Malformed cursor returns 400 |
| limit | Pydantic int with ge=1, le=100 | Bounded integer |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Patient_id from validated JWT sub claim.

### XSS Prevention

**Output encoding:** All string outputs escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** appointment type (may reveal condition), doctor name, scheduled time

**Audit requirement:** Not individually audited (read-only, patient self-access, high volume). Session-level audit via login audit covers access.

---

## Testing

### Test Cases

#### Happy Path
1. Fetch upcoming appointments (default)
   - **Given:** Patient with 3 upcoming confirmed appointments
   - **When:** GET /api/v1/portal/appointments
   - **Then:** 200 OK, 3 items, all scheduled in the future, sorted ASC

2. Fetch past appointments
   - **Given:** Patient with 5 past completed appointments
   - **When:** GET /api/v1/portal/appointments?view=past
   - **Then:** 200 OK, 5 items, sorted DESC by date

3. Filter by status
   - **Given:** Mix of confirmed and pending upcoming appointments
   - **When:** GET /api/v1/portal/appointments?view=upcoming&status=confirmed
   - **Then:** Only confirmed appointments returned

4. Paginate results
   - **Given:** Patient with 25 appointments (view=all)
   - **When:** GET /api/v1/portal/appointments?limit=20
   - **Then:** 20 items, has_more=true, cursor populated; second call returns 5 items, has_more=false

#### Edge Cases
1. No appointments at all
   - **Given:** Newly registered patient
   - **When:** GET /api/v1/portal/appointments
   - **Then:** 200 OK, items=[], total_count=0, summary zeros

2. Cancellation policy = 48h, appointment in 30h
   - **Given:** Tenant cancellation_policy_hours=48, appointment in 30 hours
   - **When:** GET /api/v1/portal/appointments
   - **Then:** can_cancel=false, cancel_deadline shows 48h before appointment (past)

3. Soft-deleted doctor
   - **Given:** Appointment doctor record was deactivated
   - **When:** GET /api/v1/portal/appointments
   - **Then:** doctor.name = "Doctor no disponible", no error

#### Error Cases
1. Invalid view parameter
   - **Given:** Patient authenticated
   - **When:** GET /api/v1/portal/appointments?view=future
   - **Then:** 400 Bad Request with validation details

2. Limit out of range
   - **Given:** Patient authenticated
   - **When:** GET /api/v1/portal/appointments?limit=500
   - **Then:** 400 Bad Request

3. No portal JWT
   - **Given:** Request with no Authorization header
   - **When:** GET /api/v1/portal/appointments
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Patient with portal_access=true; mix of appointment statuses and dates.

**Patients/Entities:** 5+ appointments with various statuses, 2 doctors, 2 locations; tenant with cancellation_policy_hours=24.

### Mocking Strategy

- Redis: fakeredis for cache testing
- asyncio.gather: verify parallel count queries execute correctly
- NOW() function: freeze time in tests using pytest-freezegun

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Returns patient's own appointments only (query-level enforcement)
- [ ] view=upcoming returns future non-cancelled appointments sorted ASC
- [ ] view=past returns past + cancelled appointments sorted DESC
- [ ] Status filter works correctly
- [ ] can_cancel and cancel_deadline computed correctly per tenant policy
- [ ] Doctor name formatted with Dr./Dra. prefix
- [ ] Cursor-based pagination works (20 default, 100 max)
- [ ] Summary counts accurate
- [ ] Response cached for 2 minutes; cache invalidated on appointment change
- [ ] Staff JWT returns 403
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms cache hit, < 300ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Booking new appointments (see PP-08 portal-book-appointment.md)
- Cancelling appointments (see PP-09 portal-cancel-appointment.md)
- Appointment details view (all relevant fields returned in list)
- Real-time appointment reminders (see notifications domain)
- Appointment rescheduling from portal (future enhancement)

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
- [x] Auth level stated (patient portal scope)
- [x] Input sanitization defined (Pydantic enum + integer bounds)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Patient data ownership enforced at query level

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (2-minute TTL, tenant+patient namespaced)
- [x] DB queries optimized (composite indexes listed)
- [x] Pagination applied (cursor-based)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (N/A for read list)
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
| 1.0 | 2026-02-25 | Initial spec |
