# AP-12 Add to Waitlist Spec

---

## Overview

**Feature:** Add a patient to the appointment waitlist when their preferred slot is unavailable. Captures preferred doctor, preferred time ranges (day of week, time window), and procedure type. The patient is automatically notified when a matching slot opens due to cancellation or no-show.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-05 (appointment-cancel.md), AP-08 (appointment-no-show.md), AP-14 (waitlist-notify.md), P-01 (patient-get.md), infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients cannot directly add themselves to the waitlist via this endpoint; staff add them. Patient self-service waitlist (if implemented) would use a portal-specific endpoint.

---

## Endpoint

```
POST /api/v1/appointments/waitlist
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
  "patient_id": "uuid (required)",
  "preferred_doctor_id": "uuid (optional) — if null, any doctor in the tenant",
  "procedure_type": "string (required) — enum: consultation, procedure, emergency, follow_up",
  "preferred_days": "integer[] (optional) — day_of_week values 0-6 (Monday=0); empty means any day",
  "preferred_time_from": "string (optional) — HH:MM 24h format; start of preferred time window",
  "preferred_time_to": "string (optional) — HH:MM 24h format; end of preferred time window",
  "valid_until": "string (required) — ISO 8601 date; waitlist entry expires on this date; max 6 months",
  "notes": "string (optional) — max 500 chars; additional context for staff"
}
```

**Example Request:**
```json
{
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "preferred_doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "procedure_type": "consultation",
  "preferred_days": [0, 1, 2, 3, 4],
  "preferred_time_from": "08:00",
  "preferred_time_to": "13:00",
  "valid_until": "2026-04-15",
  "notes": "Paciente flexible, prefiere mananas entre semana."
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
  "patient_id": "uuid",
  "preferred_doctor_id": "uuid | null",
  "procedure_type": "string",
  "preferred_days": "integer[]",
  "preferred_time_from": "string | null (HH:MM)",
  "preferred_time_to": "string | null (HH:MM)",
  "valid_until": "string (ISO 8601 date)",
  "status": "string (active)",
  "notes": "string | null",
  "patient": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "phone": "string"
  },
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
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
  "notes": "Paciente flexible, prefiere mananas entre semana.",
  "patient": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "first_name": "Maria",
    "last_name": "Garcia Lopez",
    "phone": "+573001234567"
  },
  "created_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "created_at": "2026-03-10T14:30:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields, preferred_time_from >= preferred_time_to, valid_until in the past.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "La fecha de vencimiento debe ser futura.",
  "details": {
    "valid_until": ["La fecha de vencimiento debe ser futura."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Caller role is patient (patients cannot add to waitlist via this endpoint).

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para agregar pacientes a la lista de espera."
}
```

#### 404 Not Found
**When:** patient_id or preferred_doctor_id does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 409 Conflict
**When:** Patient already has an active waitlist entry for the same procedure_type and preferred_doctor_id combination.

**Example:**
```json
{
  "error": "duplicate_waitlist",
  "message": "El paciente ya tiene una entrada activa en la lista de espera para este procedimiento y doctor.",
  "details": {
    "existing_entry_id": "f6a1b2c3-d4e5-7890-abcd-4567890abcde"
  }
}
```

#### 422 Unprocessable Entity
**When:** valid_until exceeds 6 months, preferred_days contains invalid values, invalid time format.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "valid_until": ["La fecha de vencimiento no puede superar 6 meses desde hoy."],
    "preferred_days": ["Los dias preferidos deben estar entre 0 (lunes) y 6 (domingo)."]
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
3. Reject if caller role = patient (403).
4. Validate `patient_id` exists and is active in tenant. Return 404 if not.
5. If `preferred_doctor_id` provided: validate it exists and has role=doctor. Return 404 if not.
6. Validate `valid_until` is in the future and not more than 6 months from today. Return 422 if violated.
7. If `preferred_time_from` and `preferred_time_to` both provided: validate `preferred_time_from < preferred_time_to`. Return 400 if not.
8. Validate all `preferred_days` values are in range 0-6. Return 422 if any invalid.
9. Check for duplicate: `SELECT id FROM waitlist WHERE patient_id = :pid AND preferred_doctor_id = :did AND procedure_type = :type AND status = 'active'`. Return 409 if found.
10. Insert waitlist entry with `status = 'active'`, `created_by = caller_user_id`.
11. Write audit log entry.
12. Eager-load patient summary.
13. Return 201 with waitlist entry.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID, active patient in tenant | Paciente no encontrado. |
| preferred_doctor_id | Valid UUID, role=doctor (if provided) | Doctor no encontrado. |
| procedure_type | Enum: consultation, procedure, emergency, follow_up | Tipo de procedimiento no valido. |
| preferred_days | Array of integers 0-6 (if provided) | Los dias preferidos deben estar entre 0 y 6. |
| preferred_time_from | HH:MM 24h format (if provided) | Formato de hora invalido (HH:MM). |
| preferred_time_to | HH:MM 24h format, after preferred_time_from (if provided) | La hora de fin debe ser posterior a la hora de inicio. |
| valid_until | ISO 8601 date, future, max 6 months | La fecha de vencimiento no puede superar 6 meses. |
| notes | Max 500 chars (if provided) | Las notas no pueden superar 500 caracteres. |

**Business Rules:**

- A patient may have multiple active waitlist entries for different doctors or procedure types.
- Duplicate check is scoped to the same patient + doctor + procedure_type combination.
- If `preferred_doctor_id` is null, the entry matches any available doctor in the tenant when a slot opens.
- Expired waitlist entries (valid_until < today) are not matched even if a slot opens; a background job deactivates them nightly.
- `created_by` is always set server-side from JWT.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| preferred_days empty array | Treated as "any day" — same as not providing the field |
| preferred_doctor_id null — match any doctor | Entry created; slot_opened matcher will check all doctors |
| valid_until = today | Allow (expires at end of day) |
| Patient already has an appointment scheduled (not a waitlist) | Allow — waitlist is for additional/earlier slots |
| Inactive patient | Return 404 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `waitlist_entries`: INSERT — new waitlist entry
- `audit_logs`: INSERT — waitlist entry create event

**Example query (SQLAlchemy):**
```python
entry = WaitlistEntry(
    patient_id=data.patient_id,
    preferred_doctor_id=data.preferred_doctor_id,
    procedure_type=data.procedure_type,
    preferred_days=data.preferred_days or [],
    preferred_time_from=data.preferred_time_from,
    preferred_time_to=data.preferred_time_to,
    valid_until=data.valid_until,
    status=WaitlistStatus.ACTIVE,
    notes=data.notes,
    created_by=current_user.id,
)
session.add(entry)
await session.flush()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:waitlist:list:*`: INVALIDATE — all waitlist list caches

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None on creation. Events are consumed when a slot opens (AP-05/AP-08 dispatch `waitlist.slot_opened`).

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** create
- **Resource:** waitlist_entry
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No immediate notification on waitlist add. Patient is notified when a matching slot opens (see AP-14).

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on create (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates waitlist list caches

### Database Performance

**Queries executed:** 3 (patient lookup, duplicate check, insert)

**Indexes required:**
- `waitlist_entries.patient_id` — INDEX
- `waitlist_entries.(patient_id, preferred_doctor_id, procedure_type, status)` — COMPOSITE INDEX for duplicate check
- `waitlist_entries.status` — INDEX (for active entry queries)
- `waitlist_entries.valid_until` — INDEX (for expiry cleanup job)

**N+1 prevention:** Patient summary loaded in single JOIN during insert response.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, preferred_doctor_id | Pydantic UUID validator | Rejects non-UUID strings |
| procedure_type | Pydantic enum validator | Whitelist |
| preferred_days | Pydantic list[int] with ge=0, le=6 per item | Bounds enforced |
| preferred_time_from, preferred_time_to | Regex: `^([01]?[0-9]|2[0-3]):[0-5][0-9]$` | 24h time format validation |
| valid_until | Pydantic date validator | ISO 8601 strict |
| notes | Pydantic strip() + bleach.clean, max 500 | Free-text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, procedure_type (clinical intent), notes

**Audit requirement:** All waitlist adds logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Receptionist adds patient to waitlist with full preferences
   - **Given:** Receptionist JWT, valid patient and doctor, no existing waitlist entry
   - **When:** POST /api/v1/appointments/waitlist with all fields
   - **Then:** 201 with waitlist entry, status=active

2. Add to waitlist with no preferred doctor (any doctor)
   - **Given:** Valid request with preferred_doctor_id=null
   - **When:** POST waitlist
   - **Then:** 201 with preferred_doctor_id=null

3. Add multiple waitlist entries for same patient, different procedure
   - **Given:** Patient already on waitlist for consultation; now adding for procedure
   - **When:** POST waitlist with procedure_type=procedure
   - **Then:** 201 — different procedure type, no conflict

#### Edge Cases
1. preferred_days = [] (any day)
   - **Given:** preferred_days not provided or empty
   - **When:** POST waitlist
   - **Then:** 201 with preferred_days=[]

2. valid_until = today
   - **Given:** valid_until = today's date
   - **When:** POST waitlist
   - **Then:** 201 — valid single-day entry

#### Error Cases
1. Duplicate entry for same patient/doctor/type
   - **Given:** Active entry exists for patient + doctor_A + consultation
   - **When:** POST with same patient, doctor_A, consultation
   - **Then:** 409 duplicate_waitlist

2. valid_until more than 6 months
   - **Given:** valid_until = 8 months from now
   - **When:** POST waitlist
   - **Then:** 422 validation_failed

3. Patient role attempts to add
   - **Given:** Patient JWT
   - **When:** POST waitlist
   - **Then:** 403 Forbidden

4. preferred_time_from > preferred_time_to
   - **Given:** preferred_time_from=14:00, preferred_time_to=09:00
   - **When:** POST waitlist
   - **Then:** 400 invalid_input

### Test Data Requirements

**Users:** clinic_owner, doctor, receptionist, patient (for negative test)

**Patients/Entities:** Active patient; existing waitlist entry for duplicate test

### Mocking Strategy

- Redis: Use `fakeredis`; verify list cache invalidation
- Database: Test tenant schema seeded with existing waitlist entry for duplicate conflict test

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/appointments/waitlist returns 201 with entry detail
- [ ] Patient role receives 403 always
- [ ] Duplicate patient/doctor/procedure combination returns 409
- [ ] valid_until max 6 months enforced (422)
- [ ] preferred_days validated as 0-6 integers
- [ ] preferred_time_from < preferred_time_to enforced
- [ ] Entry created with status=active
- [ ] Audit log written with PHI flag
- [ ] Waitlist list cache invalidated
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing waitlist entries (see AP-13)
- Notifying waitlist patients of available slots (see AP-14)
- Patient self-service waitlist (portal feature)
- Automatic appointment booking from waitlist match (manual notification only)
- Waitlist entry removal/deactivation

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
