# AP-10 Block Availability Spec

---

## Overview

**Feature:** Create an availability block that prevents appointment booking during a specified time period for a doctor. Used for vacations, lunch breaks not defined in the schedule, meetings, training sessions, or any other non-clinical time. Blocked slots appear as unavailable in AP-09.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-09 (availability-get.md), U-07 (doctor-schedule-get.md), infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** A doctor may only create blocks for their own schedule. clinic_owner may create blocks for any doctor in the tenant. Receptionists and assistants cannot create availability blocks.

---

## Endpoint

```
POST /api/v1/appointments/availability/block
```

**Rate Limiting:**
- 30 requests per minute per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "doctor_id": "uuid (required)",
  "start_time": "string (required) — ISO 8601 datetime with timezone",
  "end_time": "string (required) — ISO 8601 datetime with timezone",
  "reason": "string (required) — enum: vacation, lunch, meeting, training, personal, other",
  "notes": "string (optional) — max 500 chars; additional context",
  "is_recurring": "boolean (optional) — default false; if true, recurs weekly on same day/time",
  "recurring_until": "string (optional) — ISO 8601 date; required if is_recurring=true; max 12 months"
}
```

**Example Request (single block):**
```json
{
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-20T00:00:00-05:00",
  "end_time": "2026-03-27T23:59:59-05:00",
  "reason": "vacation",
  "notes": "Vacaciones de semana santa.",
  "is_recurring": false
}
```

**Example Request (recurring weekly lunch):**
```json
{
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-16T13:00:00-05:00",
  "end_time": "2026-03-16T14:00:00-05:00",
  "reason": "lunch",
  "is_recurring": true,
  "recurring_until": "2026-12-31"
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "id": "uuid",
  "doctor_id": "uuid",
  "start_time": "string (ISO 8601 datetime)",
  "end_time": "string (ISO 8601 datetime)",
  "reason": "string",
  "notes": "string | null",
  "is_recurring": "boolean",
  "recurring_until": "string | null (ISO 8601 date)",
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "d4e5f6a1-b2c3-7890-abcd-1234567890ab",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-20T00:00:00-05:00",
  "end_time": "2026-03-27T23:59:59-05:00",
  "reason": "vacation",
  "notes": "Vacaciones de semana santa.",
  "is_recurring": false,
  "recurring_until": null,
  "created_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "created_at": "2026-03-10T11:00:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** start_time >= end_time, missing required fields, is_recurring=true without recurring_until.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "La hora de fin debe ser posterior a la hora de inicio.",
  "details": {
    "end_time": ["La hora de fin debe ser posterior a la hora de inicio."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor tries to block time for another doctor. Receptionist or assistant attempts to create a block.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para bloquear el horario de este doctor."
}
```

#### 404 Not Found
**When:** doctor_id does not exist or is not a doctor role in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Doctor no encontrado."
}
```

#### 409 Conflict
**When:** A block with overlapping time range already exists for the same doctor (exact same reason and time).

**Example:**
```json
{
  "error": "block_conflict",
  "message": "Ya existe un bloqueo en ese horario para este doctor.",
  "details": {
    "conflicting_block_id": "e5f6a1b2-c3d4-7890-abcd-234567890abc"
  }
}
```

#### 422 Unprocessable Entity
**When:** is_recurring=true but recurring_until not provided. Or recurring_until exceeds 12 months from start_time.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "recurring_until": ["La fecha de fin de recurrencia es obligatoria cuando is_recurring es verdadero."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate request body via Pydantic schema.
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Check RBAC: if caller is doctor, assert `doctor_id == caller_user_id`. Return 403 otherwise. Reject receptionist/assistant with 403.
4. Validate `doctor_id` exists and has role = doctor. Return 404 if not.
5. Validate `start_time < end_time`. Return 400 if not.
6. If `is_recurring = true`: validate `recurring_until` is provided and is not more than 12 months from `start_time`. Return 422 if violated.
7. Check for overlapping blocks: `SELECT id FROM availability_blocks WHERE doctor_id = :id AND start_time < :end AND end_time > :start AND is_active = true`. If overlap found, return 409.
8. Insert block record. For recurring blocks, store a single row with `is_recurring=true` and `recurring_until`; the availability calculation in AP-09 expands recurring blocks at query time.
9. Write audit log entry.
10. Invalidate all availability cache keys for the doctor within the block's date range.
11. Return 201 with created block.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| doctor_id | Valid UUID, role=doctor in tenant | Doctor no encontrado. |
| start_time | ISO 8601 datetime with timezone | Formato de fecha invalido. |
| end_time | ISO 8601 datetime, must be after start_time | La hora de fin debe ser posterior a la hora de inicio. |
| reason | Enum: vacation, lunch, meeting, training, personal, other | Motivo de bloqueo no valido. |
| notes | Max 500 chars (if provided) | Las notas no pueden superar 500 caracteres. |
| recurring_until | Required when is_recurring=true; max 12 months from start_time | La fecha de fin de recurrencia es obligatoria. |

**Business Rules:**

- Overlapping blocks for the same doctor are rejected. Existing appointments during a newly created block are NOT auto-cancelled — staff must manually handle existing bookings.
- Recurring blocks are stored as a single record; AP-09 expands weekly occurrences at query time to avoid storing N rows.
- Blocking time does not automatically notify patients with existing appointments in the blocked range — that is a manual staff task.
- `created_by` is always set server-side from JWT.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Block spans midnight (e.g., 22:00-02:00) | Valid; treated as single continuous block |
| Multi-day vacation block | Valid; availability API returns empty for all days in range |
| Recurring block until date is today | Immediate single instance only |
| Block overlaps partially with existing block | Return 409 with conflicting block ID |
| Doctor creates block for past date | Allow (may need to record retroactively) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `availability_blocks`: INSERT — new block record
- `audit_logs`: INSERT — block create event

**Example query (SQLAlchemy):**
```python
block = AvailabilityBlock(
    doctor_id=data.doctor_id,
    start_time=data.start_time.astimezone(timezone.utc),
    end_time=data.end_time.astimezone(timezone.utc),
    reason=data.reason,
    notes=data.notes,
    is_recurring=data.is_recurring,
    recurring_until=data.recurring_until,
    is_active=True,
    created_by=current_user.id,
)
session.add(block)
await session.flush()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:availability:{doctor_id}:*`: INVALIDATE — all availability cache keys for this doctor (pattern delete)

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | availability.blocked | { tenant_id, doctor_id, start_time, end_time, reason } | After successful block create |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** create
- **Resource:** availability_block
- **PHI involved:** No

### Notifications

**Notifications triggered:** No. Notifying patients with existing appointments is a manual staff responsibility.

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on create (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Pattern-invalidates all availability cache keys for affected doctor

### Database Performance

**Queries executed:** 3 (doctor lookup, overlap check, insert)

**Indexes required:**
- `availability_blocks.doctor_id` — INDEX
- `availability_blocks.(doctor_id, start_time, end_time)` — COMPOSITE INDEX for overlap check
- `availability_blocks.is_active` — INDEX (for filtering active blocks)

**N+1 prevention:** Not applicable — single insert operation.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| doctor_id | Pydantic UUID validator | Rejects non-UUID strings |
| start_time, end_time | Pydantic datetime validator | ISO 8601 strict |
| reason | Pydantic enum validator | Whitelist |
| notes | Pydantic strip() + bleach.clean, max 500 | Free-text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Availability blocks are scheduling/operational data.

**Audit requirement:** Written for operational audit; no PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Clinic owner creates vacation block for a doctor
   - **Given:** clinic_owner JWT, valid doctor, non-overlapping date range
   - **When:** POST /api/v1/appointments/availability/block with reason=vacation
   - **Then:** 201 Created, availability cache invalidated for doctor's date range

2. Doctor creates own recurring lunch block
   - **Given:** Doctor JWT (own doctor_id), is_recurring=true, valid recurring_until
   - **When:** POST availability/block
   - **Then:** 201 Created with is_recurring=true, single row in DB

3. Block covers weekend (non-working days)
   - **Given:** Block from Friday 17:00 to Monday 08:00
   - **When:** POST block
   - **Then:** 201 Created; AP-09 returns empty arrays for Sat/Sun (already non-working) and Friday PM / Monday AM as blocked

#### Edge Cases
1. Block created for past date (retroactive)
   - **Given:** start_time = yesterday
   - **When:** POST block
   - **Then:** 201 Created — no restriction on past dates

2. Recurring block with recurring_until = today
   - **Given:** is_recurring=true, recurring_until=today, start_time=today
   - **When:** POST block
   - **Then:** 201 Created — single occurrence

#### Error Cases
1. Doctor creates block for another doctor
   - **Given:** Doctor A JWT, doctor_id = Doctor B
   - **When:** POST block
   - **Then:** 403 Forbidden

2. Overlapping block
   - **Given:** Existing block 09:00-12:00, new block 10:00-13:00
   - **When:** POST block
   - **Then:** 409 block_conflict

3. is_recurring=true without recurring_until
   - **Given:** is_recurring=true, no recurring_until provided
   - **When:** POST block
   - **Then:** 422 validation_failed

4. Receptionist attempts to create block
   - **Given:** Receptionist JWT
   - **When:** POST block
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, two doctors, receptionist (for negative test)

**Patients/Entities:** Existing availability_blocks for overlap conflict tests

### Mocking Strategy

- Redis: Use `fakeredis`; verify pattern invalidation of availability keys
- RabbitMQ: Mock publish; assert `availability.blocked` event dispatched

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/appointments/availability/block returns 201 with block detail
- [ ] Doctor restricted to own doctor_id (403 for others)
- [ ] Receptionist and assistant receive 403
- [ ] Overlapping blocks rejected with 409
- [ ] is_recurring=true requires recurring_until (422 if absent)
- [ ] Recurring blocks stored as single row (not expanded)
- [ ] Availability cache invalidated for affected doctor after block created
- [ ] availability.blocked event dispatched to RabbitMQ
- [ ] Audit log written
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing existing availability blocks (requires separate GET endpoint)
- Deleting/deactivating a block (requires separate DELETE endpoint)
- Auto-cancelling existing appointments within the blocked range
- Patient notification when a block affects their appointment

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
