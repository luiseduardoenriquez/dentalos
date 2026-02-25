# AP-11 Quick Reschedule (Drag-and-Drop) Spec

---

## Overview

**Feature:** Quickly reschedule an appointment via a minimal-payload endpoint optimized for drag-and-drop interactions in the calendar UI. Accepts only the new start_time and optionally a new doctor_id (for cross-doctor drag). Validates availability and dispatches patient notification if time changes. Designed for sub-200ms response to support smooth calendar UX.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create.md), AP-04 (appointment-update.md), AP-09 (availability-get.md), infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Doctors may only drag-reschedule their own appointments. Receptionists, assistants, and clinic_owners may drag-reschedule any appointment in the tenant. Patients cannot use this endpoint.

---

## Endpoint

```
PUT /api/v1/appointments/{appointment_id}/reschedule
```

**Rate Limiting:**
- 60 requests per minute per user — accommodates rapid sequential drag operations

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
| appointment_id | Yes | uuid | Must be valid UUID; must exist in tenant | Appointment to reschedule | c3d4e5f6-a1b2-7890-abcd-1234567890ef |

### Query Parameters

None.

### Request Body Schema

```json
{
  "new_start_time": "string (required) — ISO 8601 datetime with timezone",
  "new_doctor_id": "uuid (optional) — if provided, reassigns appointment to different doctor"
}
```

**Example Request (same doctor, new time):**
```json
{
  "new_start_time": "2026-03-15T11:00:00-05:00"
}
```

**Example Request (new doctor and new time):**
```json
{
  "new_start_time": "2026-03-15T14:00:00-05:00",
  "new_doctor_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
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
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "start_time": "string (ISO 8601 datetime)",
  "end_time": "string (ISO 8601 datetime)",
  "duration_minutes": "integer",
  "type": "string",
  "status": "string",
  "doctor": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string"
  },
  "updated_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T11:00:00-05:00",
  "end_time": "2026-03-15T11:30:00-05:00",
  "duration_minutes": 30,
  "type": "consultation",
  "status": "scheduled",
  "doctor": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "first_name": "Carlos",
    "last_name": "Mendez"
  },
  "updated_at": "2026-03-14T10:30:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** new_start_time is missing or is in the past.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "La nueva hora de inicio no puede ser en el pasado.",
  "details": {
    "new_start_time": ["La nueva hora de inicio no puede ser en el pasado."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor attempts to drag-reschedule another doctor's appointment.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para reagendar esta cita."
}
```

#### 404 Not Found
**When:** appointment_id or new_doctor_id does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Cita no encontrada."
}
```

#### 409 Conflict
**When:** New time slot conflicts with an existing appointment for the target doctor.

**Example:**
```json
{
  "error": "slot_conflict",
  "message": "El doctor ya tiene una cita en el nuevo horario.",
  "details": {
    "conflicting_appointment_id": "d4e5f6a1-b2c3-4567-890a-bcdef1234567",
    "conflict_start": "2026-03-15T11:00:00-05:00",
    "conflict_end": "2026-03-15T11:30:00-05:00"
  }
}
```

#### 422 Unprocessable Entity
**When:** Appointment cannot be rescheduled in current status (cancelled, completed, no_show). Or new time falls outside doctor's working hours.

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "No se puede reagendar una cita cancelada.",
  "details": {
    "current_status": "cancelled"
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

1. Validate `appointment_id` as UUID and `new_start_time` as ISO 8601 datetime. Reject if `new_start_time` is in the past.
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Load appointment from DB. Return 404 if not found.
4. Check RBAC: if caller is doctor, assert `appointment.doctor_id == caller_user_id`. Return 403 if mismatch.
5. Validate appointment status is scheduled or confirmed. Return 422 if cancelled, completed, or no_show.
6. Determine target doctor: if `new_doctor_id` provided, validate it exists and has role=doctor. Use `appointment.doctor_id` if not provided.
7. If doctor is changing (`new_doctor_id != appointment.doctor_id`): verify caller has permission to reassign (clinic_owner, receptionist, or assistant — not a doctor reassigning to someone else).
8. Compute `new_end_time = new_start_time + appointment.duration_minutes`.
9. Validate `new_start_time` falls within target doctor's working window for that day (skip for type=emergency).
10. Run overlap check for target doctor: exclude current appointment. Return 409 if conflict.
11. Execute UPDATE: `start_time = new_start_time`, `end_time = new_end_time`, `doctor_id = target_doctor_id`, `updated_by = caller_user_id`, `updated_at = now()`.
12. Write audit log entry.
13. Invalidate cache: appointment detail, old calendar date, new calendar date, availability for both dates/doctors if reassigned.
14. Dispatch `appointment.rescheduled` event to RabbitMQ — triggers patient notification and reminder rescheduling.
15. Return 200 with minimal response (optimized for calendar refresh).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| new_start_time | ISO 8601 datetime, not in the past | La nueva hora de inicio no puede ser en el pasado. |
| new_doctor_id | Valid UUID, role=doctor in tenant (if provided) | Doctor no encontrado. |
| appointment.status | Must be scheduled or confirmed | No se puede reagendar una cita en estado {status}. |
| new_start_time | Must fall within target doctor's working window | El doctor no trabaja en ese horario. |

**Business Rules:**

- Duration is preserved on reschedule. Only start_time shifts; end_time = new_start_time + original duration_minutes.
- Doctor reassignment (cross-doctor drag) is only allowed for staff roles, not a doctor dragging to another doctor's column.
- On doctor reassignment, the confirmation status (confirmed/scheduled) is preserved.
- Notification is always sent to patient when start_time changes, regardless of whether it was a drag-drop or explicit update.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Drag to same start_time (no actual change) | 200 OK, no notification dispatched (no-op) |
| Cross-doctor drag by receptionist | Allowed — doctor_id updated, both doctors' availability caches invalidated |
| Cross-doctor drag by a doctor | Rejected 403 — doctor cannot reassign to another doctor |
| new_start_time exactly equals existing start_time but new_doctor_id provided | Doctor reassigned, notification dispatched if doctor changed |
| Emergency appointment drag | Bypasses working-hours check; overlap check still applied |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: UPDATE — start_time, end_time, doctor_id (if reassigned), updated_by, updated_at
- `audit_logs`: INSERT — reschedule event

**Example query (SQLAlchemy):**
```python
stmt = (
    update(Appointment)
    .where(Appointment.id == appointment_id)
    .values(
        start_time=new_start_utc,
        end_time=new_end_utc,
        doctor_id=target_doctor_id,
        updated_by=current_user.id,
        updated_at=utcnow(),
    )
    .returning(Appointment)
)
result = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:appointment:{appointment_id}`: INVALIDATE
- `tenant:{tenant_id}:appointments:calendar:{old_doctor_id}:{old_date}`: INVALIDATE
- `tenant:{tenant_id}:appointments:calendar:{new_doctor_id}:{new_date}`: INVALIDATE
- `tenant:{tenant_id}:availability:{old_doctor_id}:{old_date}`: INVALIDATE
- `tenant:{tenant_id}:availability:{new_doctor_id}:{new_date}`: INVALIDATE
- `tenant:{tenant_id}:appointments:list:*`: INVALIDATE

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | appointment.rescheduled | { tenant_id, appointment_id, old_start_time, new_start_time, old_doctor_id, new_doctor_id, patient_id } | When start_time or doctor_id changes |
| notifications | reminder.reschedule | { tenant_id, appointment_id, new_start_time, cancel_old_reminders: true } | When start_time changes |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** update
- **Resource:** appointment
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** Yes (when start_time or doctor_id changes)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | appointment_reschedule | patient | When start_time or doctor changes |
| whatsapp | appointment_reschedule_wa | patient | When start_time or doctor changes (if enabled) |
| sms | appointment_reschedule_sms | patient | When start_time or doctor changes (if enabled) |

---

## Performance

### Expected Response Time
- **Target:** < 150ms (optimized for real-time calendar UX)
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** No caching on reschedule (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates all relevant calendar and availability cache keys

### Database Performance

**Queries executed:** 3 (load appointment, overlap check, update)

**Indexes required:**
- `appointments.id` — PRIMARY KEY (exists)
- `appointments.(doctor_id, start_time, end_time, status)` — COMPOSITE INDEX for overlap check
- `appointments.doctor_id` — INDEX (for RBAC check)

**N+1 prevention:** Overlap check is a single aggregation query. Response is minimal (no deep JOIN needed).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_id | Pydantic UUID validator | URL param |
| new_start_time | Pydantic datetime validator with timezone | ISO 8601 strict |
| new_doctor_id | Pydantic UUID validator (optional) | Validated if provided |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Implicit PHI via patient appointment context

**Audit requirement:** All reschedule events logged with old/new time and doctor in audit payload.

---

## Testing

### Test Cases

#### Happy Path
1. Drag appointment to new time same doctor
   - **Given:** Receptionist JWT, appointment status=scheduled, new slot free
   - **When:** PUT /api/v1/appointments/{id}/reschedule with new_start_time
   - **Then:** 200 with updated start/end times, appointment.rescheduled event dispatched

2. Cross-doctor drag by receptionist
   - **Given:** Receptionist JWT, valid new_doctor_id, new slot free for target doctor
   - **When:** PUT with new_start_time and new_doctor_id
   - **Then:** 200 with updated doctor_id, both doctors' caches invalidated

3. No-op drag (same start_time)
   - **Given:** new_start_time = current start_time, no new_doctor_id
   - **When:** PUT reschedule
   - **Then:** 200 with unchanged appointment, no event dispatched

#### Edge Cases
1. Emergency appointment drag to occupied slot
   - **Given:** type=emergency, target slot occupied by another appointment
   - **When:** PUT reschedule
   - **Then:** 409 Conflict — emergency type does not bypass overlap in reschedule context (only on create)

2. Duration preserved after drag
   - **Given:** Appointment duration=60 min, dragged to new start_time
   - **When:** PUT reschedule
   - **Then:** 200 with end_time = new_start_time + 60 min

#### Error Cases
1. Doctor dragging another doctor's appointment
   - **Given:** Doctor A JWT, appointment.doctor_id = Doctor B
   - **When:** PUT reschedule
   - **Then:** 403 Forbidden

2. Drag to conflicting slot
   - **Given:** Another appointment at new time for same doctor
   - **When:** PUT reschedule
   - **Then:** 409 slot_conflict with conflicting_appointment_id

3. Drag cancelled appointment
   - **Given:** Appointment status=cancelled
   - **When:** PUT reschedule
   - **Then:** 422 invalid_status_transition

4. new_start_time in the past
   - **Given:** new_start_time = yesterday
   - **When:** PUT reschedule
   - **Then:** 400 invalid_input

### Test Data Requirements

**Users:** clinic_owner, two doctors, receptionist

**Patients/Entities:** Appointments in scheduled and confirmed status; a second appointment for same doctor on the same day to test conflict

### Mocking Strategy

- RabbitMQ: Mock publish; assert `appointment.rescheduled` and `reminder.reschedule` dispatched only when time actually changes
- Redis: Use `fakeredis`; verify all relevant cache keys invalidated

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] PUT /api/v1/appointments/{id}/reschedule returns 200 with updated times
- [ ] Duration preserved after reschedule (end_time = new_start_time + original duration)
- [ ] Cross-doctor drag works for staff roles; 403 for doctor-to-doctor reassignment
- [ ] Overlap check validates against target doctor
- [ ] No-op drag (same time, same doctor) returns 200 without dispatching events
- [ ] appointment.rescheduled and reminder.reschedule events dispatched when time changes
- [ ] Cache invalidated for both old and new date/doctor combinations
- [ ] Audit log written
- [ ] Response time < 150ms target
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Full appointment update with all fields (see AP-04)
- Recurring appointment drag-rescheduling
- Multi-appointment batch reschedule (e.g., "move all today's appointments to tomorrow")
- Undo/redo of drag operations

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
