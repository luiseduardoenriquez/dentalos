# AP-08 No-Show Appointment Spec

---

## Overview

**Feature:** Mark a patient as a no-show when they fail to attend their appointment. Increments the `no_show_count` counter on the patient record, transitions appointment status to no_show, and frees the time slot for potential waitlist filling. Triggers internal staff notification (not patient notification).

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create.md), AP-05 (appointment-cancel.md), P-01 (patient-get.md), infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients cannot mark themselves as no-show. Doctors may mark no-show only for appointments assigned to themselves. clinic_owner, assistant, and receptionist may mark any appointment.

---

## Endpoint

```
POST /api/v1/appointments/{appointment_id}/no-show
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

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| appointment_id | Yes | uuid | Must be valid UUID; must exist in tenant | Appointment to mark as no-show | c3d4e5f6-a1b2-7890-abcd-1234567890ef |

### Query Parameters

None.

### Request Body Schema

```json
{
  "notes": "string (optional) — max 500 chars; reason or context for the no-show record"
}
```

**Example Request:**
```json
{
  "notes": "Paciente no contesto llamadas de recordatorio."
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "status": "string (no_show)",
  "no_show_at": "string (ISO 8601 datetime)",
  "no_show_by": "uuid",
  "notes": "string | null",
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "start_time": "string (ISO 8601 datetime)",
  "end_time": "string (ISO 8601 datetime)",
  "type": "string",
  "patient_no_show_count": "integer"
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "status": "no_show",
  "no_show_at": "2026-03-15T09:45:00-05:00",
  "no_show_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "notes": "Paciente no contesto llamadas de recordatorio.",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T09:00:00-05:00",
  "end_time": "2026-03-15T09:30:00-05:00",
  "type": "consultation",
  "patient_no_show_count": 3
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient role tries to access this endpoint. Doctor tries to mark no-show for another doctor's appointment.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para marcar esta cita como no presentado."
}
```

#### 404 Not Found
**When:** appointment_id does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Cita no encontrada."
}
```

#### 422 Unprocessable Entity
**When:** Appointment is already completed, cancelled, or no_show. Or appointment start_time is in the future (cannot mark no-show before appointment was supposed to happen).

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "No se puede marcar como no presentado una cita que aun no ha ocurrido.",
  "details": {
    "current_status": "scheduled",
    "appointment_start": "2026-03-20T09:00:00-05:00"
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

1. Validate `appointment_id` as valid UUID. Validate request body.
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Load appointment from DB. Return 404 if not found.
4. Check RBAC: patient role always rejected (403). If caller is doctor, assert `appointment.doctor_id == caller_user_id`. Return 403 if mismatch. clinic_owner, assistant, receptionist pass.
5. Validate `appointment.status` is scheduled or confirmed. Return 422 if completed, cancelled, or already no_show.
6. Validate `appointment.start_time <= now()` (appointment's scheduled time must have passed or be current). Return 422 if appointment is in the future (at least within tolerance of 15 minutes).
7. Execute UPDATE in transaction:
   a. `appointments`: set `status = 'no_show'`, `no_show_at = now()`, `no_show_by = caller_user_id`, `notes` (append to existing or set if null).
   b. `patients`: `UPDATE patients SET no_show_count = no_show_count + 1 WHERE id = :patient_id`. Atomic increment.
8. Write audit log entry.
9. Invalidate cache: appointment detail, calendar, patient detail (no_show_count changed), availability for freed slot.
10. Dispatch `appointment.no_show` event to RabbitMQ.
11. Dispatch `waitlist.slot_opened` event — the freed slot may match a waitlist entry.
12. Return 200 with no-show appointment summary including updated `patient_no_show_count`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| appointment_id | Valid UUID, exists in tenant | Cita no encontrada. |
| appointment.status | Must be scheduled or confirmed | La cita ya fue {status}. |
| appointment.start_time | Must be <= now() + 15 min grace period | No se puede marcar no presentado antes de la hora de la cita. |
| notes | Max 500 chars if provided | Las notas no pueden superar 500 caracteres. |

**Business Rules:**

- No-show counter is incremented atomically on the patient record to avoid race conditions.
- The slot is effectively freed for waitlist matching (same as cancellation).
- No notification is sent to the patient (no-show is an internal clinical record).
- Staff can optionally be notified via in-app notification if tenant has `no_show_staff_alert` setting enabled.
- 15-minute grace period: no-show can be marked up to 15 minutes before the scheduled start (for early detection of no-shows in busy clinics).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Appointment scheduled exactly at current time | Allow (within grace period) |
| Patient has no_show_count = 0 | Increment to 1; no special handling |
| High no_show_count (e.g., 5+) | Increment regardless; no automatic blacklist logic in this spec |
| notes field contains HTML | Sanitize, store clean text |
| Appointment is in_progress (doctor started it) | Reject — cannot mark in_progress as no_show; doctor must complete it |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: UPDATE — status, no_show_at, no_show_by, notes (optional)
- `patients`: UPDATE — no_show_count incremented by 1
- `audit_logs`: INSERT — no_show event with PHI flag

**Example query (SQLAlchemy):**
```python
async with session.begin():
    # Update appointment
    appt_stmt = (
        update(Appointment)
        .where(Appointment.id == appointment_id)
        .values(
            status=AppointmentStatus.NO_SHOW,
            no_show_at=utcnow(),
            no_show_by=current_user.id,
            notes=data.notes,
        )
        .returning(Appointment)
    )
    appt_result = await session.execute(appt_stmt)

    # Atomic increment on patient no_show_count
    patient_stmt = (
        update(Patient)
        .where(Patient.id == appointment.patient_id)
        .values(no_show_count=Patient.no_show_count + 1)
        .returning(Patient.no_show_count)
    )
    patient_result = await session.execute(patient_stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:appointment:{appointment_id}`: INVALIDATE
- `tenant:{tenant_id}:appointments:calendar:{doctor_id}:{date}`: INVALIDATE
- `tenant:{tenant_id}:appointments:list:*`: INVALIDATE
- `tenant:{tenant_id}:patient:{patient_id}`: INVALIDATE — no_show_count changed
- `tenant:{tenant_id}:availability:{doctor_id}:{date}`: INVALIDATE — slot freed

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | appointment.no_show | { tenant_id, appointment_id, patient_id, doctor_id, no_show_count } | After successful no-show mark |
| waitlist | waitlist.slot_opened | { tenant_id, doctor_id, start_time, end_time, duration_minutes, type } | After successful no-show mark |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** update
- **Resource:** appointment
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** Yes (internal only)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | no_show_alert | clinic staff (if tenant setting enabled) | After no-show marked |

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on no-show (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates appointment detail, calendar, patient detail, and availability caches

### Database Performance

**Queries executed:** 3 (load appointment, update appointment, update patient — in transaction)

**Indexes required:**
- `appointments.id` — PRIMARY KEY (exists)
- `appointments.doctor_id` — INDEX (for RBAC check)
- `patients.id` — PRIMARY KEY (exists)
- `appointments.status` — INDEX

**N+1 prevention:** Not applicable — single appointment, single patient update in one transaction.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_id | Pydantic UUID validator | URL param |
| notes | Pydantic strip() + bleach.clean, max 500 chars | Optional free-text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, patient_no_show_count (behavioral health data), notes

**Audit requirement:** All no-show events logged with PHI flag. no_show_count increment is audit-worthy behavior pattern data.

---

## Testing

### Test Cases

#### Happy Path
1. Receptionist marks scheduled appointment as no-show
   - **Given:** Receptionist JWT, appointment status=scheduled, start_time in past
   - **When:** POST /api/v1/appointments/{id}/no-show
   - **Then:** 200 with status=no_show, patient_no_show_count incremented by 1

2. Doctor marks own confirmed appointment as no-show
   - **Given:** Doctor JWT (own appointment), appointment status=confirmed, past start_time
   - **When:** POST with notes
   - **Then:** 200 with status=no_show, notes stored, event dispatched

3. Patient with prior no-shows reaches count=5
   - **Given:** Patient previously had no_show_count=4, appointment status=scheduled
   - **When:** POST no-show
   - **Then:** 200 with patient_no_show_count=5

#### Edge Cases
1. Mark no-show within 15-minute grace period before start
   - **Given:** Appointment start_time = 10 minutes from now, clinic_owner JWT
   - **When:** POST no-show
   - **Then:** 200 — grace period allows early marking

2. Concurrent no-show calls (race condition test)
   - **Given:** Two simultaneous POST calls for same appointment
   - **When:** Both execute
   - **Then:** One succeeds, one returns 422 (already no_show); no_show_count incremented once

#### Error Cases
1. Patient role attempts no-show
   - **Given:** Patient JWT
   - **When:** POST /api/v1/appointments/{id}/no-show
   - **Then:** 403 Forbidden

2. Mark no-show for future appointment (> 15 min grace)
   - **Given:** Appointment start_time = 2 hours from now
   - **When:** POST no-show
   - **Then:** 422 with appointment_start in details

3. Appointment already completed
   - **Given:** Appointment status=completed
   - **When:** POST no-show
   - **Then:** 422 invalid_status_transition

4. Doctor marking another doctor's appointment
   - **Given:** Doctor A JWT, appointment.doctor_id = Doctor B
   - **When:** POST no-show
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, two doctors, receptionist, patient (for negative test)

**Patients/Entities:** Patient with no_show_count=4; appointments in scheduled, confirmed, completed, cancelled status with various start times (past and future)

### Mocking Strategy

- RabbitMQ: Mock publish; assert `appointment.no_show` and `waitlist.slot_opened` dispatched
- Redis: Use `fakeredis`; verify patient cache key invalidated
- Database transaction: Test atomic increment under concurrent load using `asyncio.gather` with two simultaneous calls

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/appointments/{id}/no-show returns 200 with status=no_show
- [ ] Patient no_show_count incremented atomically
- [ ] patient_no_show_count reflected in response
- [ ] Only allowed from scheduled or confirmed status (422 otherwise)
- [ ] Cannot mark no-show for future appointments outside grace period (422)
- [ ] Patient role receives 403 always
- [ ] Doctor restricted to own appointments (403)
- [ ] appointment.no_show event dispatched to RabbitMQ
- [ ] waitlist.slot_opened event dispatched
- [ ] Cache invalidated for appointment detail, calendar, patient detail, availability
- [ ] Audit log written with PHI flag
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Automatic no-show marking (background job for appointments past end_time with no status change)
- Patient blacklisting or restriction based on no_show_count
- No-show analytics and reporting (see analytics specs)
- Reversing a no-show mark (appointment would need to be rescheduled via AP-01)

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
