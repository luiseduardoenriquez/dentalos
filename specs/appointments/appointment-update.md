# AP-04 Update Appointment Spec

---

## Overview

**Feature:** Update an existing appointment's fields including reschedule (new start/end time), type change, and notes update. Validates availability when rescheduling. Sends automatic notification to patient if start_time changes. Supports partial updates — only provided fields are modified.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create.md), AP-02 (appointment-get.md), AP-09 (availability-get.md), infra/authentication-rules.md, notifications/reminder-config.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients cannot update appointments via this endpoint (they use AP-05 cancel or AP-06 confirm only). A doctor may only update appointments assigned to themselves unless they are clinic_owner.

---

## Endpoint

```
PUT /api/v1/appointments/{appointment_id}
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
| appointment_id | Yes | uuid | Must be valid UUID; must exist in tenant | Appointment to update | c3d4e5f6-a1b2-7890-abcd-1234567890ef |

### Query Parameters

None.

### Request Body Schema

```json
{
  "start_time": "string (optional) — ISO 8601 datetime with timezone; triggers availability validation and patient notification",
  "end_time": "string (optional) — ISO 8601 datetime with timezone; required when start_time changes unless auto-calculated",
  "type": "string (optional) — enum: consultation, procedure, emergency, follow_up",
  "notes": "string (optional) — max 2000 chars; pass null to clear",
  "treatment_plan_item_id": "uuid | null (optional) — pass null to unlink"
}
```

**Example Request (reschedule):**
```json
{
  "start_time": "2026-03-15T10:00:00-05:00",
  "end_time": "2026-03-15T10:30:00-05:00",
  "notes": "Paciente solicito cambio de horario."
}
```

**Example Request (notes only):**
```json
{
  "notes": "Confirmar seguro antes de la cita."
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
  "notes": "string | null",
  "treatment_plan_item_id": "uuid | null",
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
  },
  "updated_by": "uuid",
  "updated_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T10:00:00-05:00",
  "end_time": "2026-03-15T10:30:00-05:00",
  "duration_minutes": 30,
  "type": "consultation",
  "status": "scheduled",
  "notes": "Paciente solicito cambio de horario.",
  "treatment_plan_item_id": null,
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
  },
  "updated_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "updated_at": "2026-03-14T09:00:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** Empty request body (all fields null/absent), or start_time in the past.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Se debe proporcionar al menos un campo para actualizar.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor attempts to update an appointment assigned to a different doctor.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para modificar esta cita."
}
```

#### 404 Not Found
**When:** appointment_id does not exist in the tenant, or treatment_plan_item_id not found.

**Example:**
```json
{
  "error": "not_found",
  "message": "Cita no encontrada."
}
```

#### 409 Conflict
**When:** Rescheduled time slot overlaps with another existing appointment for the same doctor.

**Example:**
```json
{
  "error": "slot_conflict",
  "message": "El doctor ya tiene una cita en el nuevo horario.",
  "details": {
    "conflicting_appointment_id": "d4e5f6a1-b2c3-4567-890a-bcdef1234567",
    "conflict_start": "2026-03-15T10:00:00-05:00",
    "conflict_end": "2026-03-15T10:30:00-05:00"
  }
}
```

#### 422 Unprocessable Entity
**When:** Cannot update a cancelled, completed, or no_show appointment. Or field validation fails.

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "No se puede modificar una cita cancelada.",
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

1. Validate `appointment_id` as valid UUID via Pydantic path param.
2. Validate request body — at least one field must be non-null; fail with 400 if all absent.
3. Resolve tenant from JWT; set `search_path` to tenant schema.
4. Load appointment from DB. Return 404 if not found.
5. Check RBAC: if caller is doctor, assert `appointment.doctor_id == caller_user_id`. Return 403 if mismatch.
6. Reject update if `appointment.status` is cancelled, completed, or no_show. Return 422.
7. Record `previous_start_time` before any changes.
8. If `start_time` provided: validate it is not in the past. If `end_time` not provided alongside new `start_time`, auto-calculate end_time by adding existing `duration_minutes` to new `start_time`.
9. If `start_time` or `end_time` changed: run overlap check against all other appointments for same doctor, excluding the current appointment itself. Return 409 if conflict. Also validate new times fall within doctor working window (unless type = emergency).
10. If `type` changed: recalculate `duration_minutes` from doctor defaults and update `end_time` if not explicitly provided.
11. If `treatment_plan_item_id` provided (not null): validate item exists and belongs to same patient.
12. Apply all provided fields as partial update (`UPDATE appointments SET ... WHERE id = :id`).
13. Set `updated_by = caller_user_id`, `updated_at = now()`.
14. Write audit log entry.
15. Invalidate cache keys for the appointment detail and affected calendar dates (both old and new dates if rescheduled).
16. If `start_time` changed: dispatch `appointment.rescheduled` event to RabbitMQ. Notification worker will cancel old reminders and schedule new ones, and send immediate reschedule notification to patient.
17. Return 200 with updated appointment.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| start_time | ISO 8601 datetime, not in the past if provided | La nueva hora de inicio no puede ser en el pasado. |
| end_time | Must be after start_time if provided | La hora de fin debe ser posterior a la hora de inicio. |
| type | Valid enum value if provided | Tipo de cita no valido. |
| notes | Max 2000 chars if provided | Las notas no pueden superar 2000 caracteres. |
| treatment_plan_item_id | Valid UUID, belongs to same patient (if provided) | Item de plan de tratamiento no encontrado. |
| appointment status | Must be scheduled or confirmed to allow update | No se puede modificar una cita en estado {status}. |

**Business Rules:**

- Cannot update cancelled, completed, or no_show appointments.
- Rescheduling (start_time change) always triggers patient notification regardless of notification settings.
- `updated_by` and `updated_at` are always set server-side.
- If only notes or treatment_plan_item_id changes, no notification is sent.
- Changing `type` without explicit `end_time` auto-recalculates duration from doctor defaults.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Only notes updated (no time change) | Update notes, no notification dispatched |
| New start_time same as existing start_time | No reschedule notification; treat as no-op for that field |
| type changed but end_time explicitly provided | Use provided end_time, recalculate duration_minutes from diff |
| treatment_plan_item_id set to null | Unlink item, appointment.treatment_plan_item_id = null |
| start_time provided but end_time omitted | Derive end_time by adding current duration_minutes to new start_time |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: UPDATE — modified fields + updated_by + updated_at
- `audit_logs`: INSERT — update event with before/after snapshot

**Example query (SQLAlchemy):**
```python
stmt = (
    update(Appointment)
    .where(Appointment.id == appointment_id)
    .values(**update_fields, updated_by=current_user.id, updated_at=utcnow())
    .returning(Appointment)
)
result = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:appointment:{appointment_id}`: INVALIDATE — clear detail cache
- `tenant:{tenant_id}:appointments:calendar:{doctor_id}:{old_date}`: INVALIDATE — if rescheduled
- `tenant:{tenant_id}:appointments:calendar:{doctor_id}:{new_date}`: INVALIDATE — if rescheduled
- `tenant:{tenant_id}:appointments:list:*`: INVALIDATE — all list caches
- `tenant:{tenant_id}:availability:{doctor_id}:{old_date}`: INVALIDATE — if rescheduled
- `tenant:{tenant_id}:availability:{doctor_id}:{new_date}`: INVALIDATE — if rescheduled

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | appointment.rescheduled | { tenant_id, appointment_id, old_start_time, new_start_time, patient_id } | When start_time changes |
| notifications | reminder.reschedule | { tenant_id, appointment_id, new_start_time, cancel_old_reminders: true } | When start_time changes |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** update
- **Resource:** appointment
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** Yes (when start_time changes)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | appointment_reschedule | patient | When start_time changes |
| whatsapp | appointment_reschedule_wa | patient | When start_time changes (if WhatsApp enabled) |
| sms | appointment_reschedule_sms | patient | When start_time changes (if SMS enabled) |

---

## Performance

### Expected Response Time
- **Target:** < 250ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on update (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates appointment detail, calendar, list, and availability caches

### Database Performance

**Queries executed:** 3 (load appointment, overlap check if rescheduling, update)

**Indexes required:**
- `appointments.id` — PRIMARY KEY (exists)
- `appointments.(doctor_id, start_time, end_time, status)` — COMPOSITE INDEX for overlap check
- `appointments.doctor_id` — INDEX (for RBAC check)

**N+1 prevention:** Patient and doctor joined in a single query after update using `RETURNING` clause + join.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_id | Pydantic UUID validator | URL param validation |
| start_time, end_time | Pydantic datetime validator | ISO 8601 strict |
| notes | Pydantic strip() + bleach.clean | Free-text sanitization |
| type | Pydantic enum validator | Whitelist |
| treatment_plan_item_id | Pydantic UUID validator (optional) | Validated if provided |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** notes (may contain clinical context), patient identifiers in audit log

**Audit requirement:** All updates logged with before/after snapshot, PHI flag set.

---

## Testing

### Test Cases

#### Happy Path
1. Reschedule appointment to new time
   - **Given:** Authenticated receptionist, appointment status=scheduled, new slot is free
   - **When:** PUT /api/v1/appointments/{id} with new start_time and end_time
   - **Then:** 200 with updated times, appointment.rescheduled event dispatched

2. Update notes only
   - **Given:** Authenticated doctor (own appointment), valid appointment
   - **When:** PUT /api/v1/appointments/{id} with notes only
   - **Then:** 200 with updated notes, no notification dispatched

3. Change appointment type
   - **Given:** Authenticated clinic_owner, appointment status=confirmed
   - **When:** PUT /api/v1/appointments/{id} with type=procedure
   - **Then:** 200 with updated type and recalculated duration_minutes

4. Unlink treatment plan item
   - **Given:** Appointment has treatment_plan_item_id set
   - **When:** PUT /api/v1/appointments/{id} with treatment_plan_item_id=null
   - **Then:** 200 with treatment_plan_item_id=null

#### Edge Cases
1. Reschedule to same start_time
   - **Given:** New start_time equals existing start_time
   - **When:** PUT /api/v1/appointments/{id} with unchanged start_time
   - **Then:** 200 with no notification dispatched (no real change)

2. Type change without explicit end_time
   - **Given:** Appointment is consultation (30 min), change to procedure
   - **When:** PUT with type=procedure, no end_time
   - **Then:** 200, end_time auto-adjusted by 60 min from start_time

#### Error Cases
1. Update cancelled appointment
   - **Given:** Appointment status=cancelled
   - **When:** PUT /api/v1/appointments/{id} with new notes
   - **Then:** 422 invalid_status_transition

2. Reschedule to conflicting slot
   - **Given:** Another appointment exists at new proposed time
   - **When:** PUT with new start_time overlapping existing
   - **Then:** 409 slot_conflict with conflicting_appointment_id

3. Doctor updating another doctor's appointment
   - **Given:** Caller is doctor A, appointment.doctor_id = doctor B
   - **When:** PUT /api/v1/appointments/{id}
   - **Then:** 403 Forbidden

4. Empty request body
   - **Given:** Valid JWT, existing appointment
   - **When:** PUT /api/v1/appointments/{id} with {}
   - **Then:** 400 invalid_input

### Test Data Requirements

**Users:** clinic_owner, two doctors, receptionist

**Patients/Entities:** Appointments in scheduled, confirmed, cancelled, completed status; a second appointment on same day to test conflict

### Mocking Strategy

- RabbitMQ: Mock publish; assert `appointment.rescheduled` dispatched only when start_time changes
- Redis: Use `fakeredis`; assert correct cache keys invalidated

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] PUT /api/v1/appointments/{id} returns 200 with updated appointment
- [ ] Partial update works (only provided fields changed)
- [ ] Reschedule triggers slot overlap validation
- [ ] Reschedule dispatches appointment.rescheduled event and patient notification
- [ ] Notes-only update does not trigger notification
- [ ] Cannot update cancelled, completed, or no_show appointments (422)
- [ ] Doctor restricted to own appointments (403)
- [ ] Cache invalidated for detail, calendar, list, and availability keys
- [ ] Audit log entry written with before/after snapshot
- [ ] All test cases pass
- [ ] Performance targets met (< 250ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Cancelling appointments (see AP-05)
- Status transitions to confirmed/completed/no_show (see AP-06, AP-07, AP-08)
- Drag-and-drop quick reschedule (see AP-11)
- Changing the patient or doctor assigned to the appointment

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
