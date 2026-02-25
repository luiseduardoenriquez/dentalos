# AP-01 Create Appointment Spec

---

## Overview

**Feature:** Create a new appointment within a tenant clinic. Validates the selected doctor's availability against their configured schedule and existing appointments, auto-calculates duration from procedure type when end_time is not provided, and enforces the MAX 3 taps UX goal by providing intelligent defaults.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** U-07 (doctor-schedule-get.md), P-01 (patient-get.md), AP-09 (availability-get.md), infra/multi-tenancy.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** A doctor may only create appointments assigned to themselves unless they are also a clinic_owner. Assistants and receptionists may create appointments for any doctor in the tenant.

---

## Endpoint

```
POST /api/v1/appointments
```

**Rate Limiting:**
- 60 requests per minute per user
- Prevents accidental double-submit loops in fast booking flows

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
  "doctor_id": "uuid (required)",
  "start_time": "string (required) — ISO 8601 datetime with timezone, e.g. 2026-03-15T09:00:00-05:00",
  "end_time": "string (optional) — ISO 8601 datetime with timezone; if omitted, auto-calculated from type",
  "type": "string (required) — enum: consultation, procedure, emergency, follow_up",
  "notes": "string (optional) — max 2000 chars",
  "treatment_plan_item_id": "uuid (optional) — links appointment to a treatment plan item"
}
```

**Example Request:**
```json
{
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T09:00:00-05:00",
  "type": "consultation",
  "notes": "Primera consulta, revisar radiografias previas.",
  "treatment_plan_item_id": null
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
    "phone": "string",
    "document_number": "string"
  },
  "doctor": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string"
  },
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T09:00:00-05:00",
  "end_time": "2026-03-15T09:30:00-05:00",
  "duration_minutes": 30,
  "type": "consultation",
  "status": "scheduled",
  "notes": "Primera consulta, revisar radiografias previas.",
  "treatment_plan_item_id": null,
  "patient": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "first_name": "Maria",
    "last_name": "Garcia Lopez",
    "phone": "+573001234567",
    "document_number": "1020304050"
  },
  "doctor": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "first_name": "Carlos",
    "last_name": "Mendez"
  },
  "created_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "created_at": "2026-03-10T14:30:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON, missing required fields, or start_time is in the past.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "start_time": ["La hora de inicio no puede ser en el pasado."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor tries to create appointment for a different doctor without clinic_owner permissions.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para agendar citas para este doctor."
}
```

#### 404 Not Found
**When:** patient_id or doctor_id does not exist in the tenant, or treatment_plan_item_id not found.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 409 Conflict
**When:** The selected time slot overlaps with an existing confirmed or scheduled appointment for the same doctor (non-emergency types only).

**Example:**
```json
{
  "error": "slot_conflict",
  "message": "El doctor ya tiene una cita en ese horario.",
  "details": {
    "conflicting_appointment_id": "d4e5f6a1-b2c3-4567-890a-bcdef1234567",
    "conflict_start": "2026-03-15T09:00:00-05:00",
    "conflict_end": "2026-03-15T09:30:00-05:00"
  }
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails (invalid enum, start_time >= end_time, doctor not working that day).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "type": ["Tipo de cita no valido. Opciones: consultation, procedure, emergency, follow_up."],
    "start_time": ["La hora de inicio debe ser anterior a la hora de fin."]
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

1. Validate input against Pydantic schema (field types, enums, ISO 8601 datetime format).
2. Reject if `start_time` is in the past (unless type = emergency and caller is clinic_owner or doctor).
3. Resolve tenant from JWT claims; set `search_path` to tenant schema.
4. Check RBAC: if caller has role = doctor, assert `doctor_id == caller_user_id`; else allow any doctor in tenant.
5. Confirm `patient_id` exists and is active in tenant `patients` table. Return 404 if not found.
6. Confirm `doctor_id` exists and has role = doctor in tenant `users` table. Return 404 if not found.
7. If `treatment_plan_item_id` provided, confirm it exists and belongs to the same patient. Return 404 if not.
8. Auto-calculate `end_time` if not provided: look up doctor's `appointment_duration_defaults` from `doctor_schedules` by `type`. Fall back to system defaults: consultation=30min, procedure=60min, emergency=30min, follow_up=20min.
9. Validate `start_time < end_time` after auto-calculation.
10. Load doctor's schedule from cache (`tenant:{tenant_id}:user:{doctor_id}:schedule`) or DB. Verify appointment falls within a working window (correct day_of_week, within start_time..end_time, not during a break). Emergency type bypasses schedule check.
11. Check for overlapping appointments: `SELECT id, start_time, end_time FROM appointments WHERE doctor_id = :doctor_id AND status IN ('scheduled','confirmed','in_progress') AND start_time < :end_time AND end_time > :start_time`. If overlap found and type != emergency, return 409.
12. Insert appointment record with `status = 'scheduled'`.
13. Write audit log entry.
14. Invalidate calendar cache keys for affected doctor and date.
15. Dispatch `appointment.created` event to RabbitMQ (triggers 24h/2h reminder scheduling).
16. Eager-load patient and doctor summary fields.
17. Return 201 with full appointment object.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID, must exist in tenant | Paciente no encontrado. |
| doctor_id | Valid UUID, must exist and have role = doctor | Doctor no encontrado. |
| start_time | ISO 8601 datetime, not in the past | La hora de inicio no puede ser en el pasado. |
| end_time | ISO 8601 datetime, must be after start_time | La hora de fin debe ser posterior a la hora de inicio. |
| type | Enum: consultation, procedure, emergency, follow_up | Tipo de cita no valido. |
| notes | Max 2000 chars (if provided) | Las notas no pueden superar 2000 caracteres. |
| treatment_plan_item_id | Valid UUID, must exist and belong to patient_id (if provided) | Item de plan de tratamiento no encontrado. |

**Business Rules:**

- Initial status is always `scheduled` on creation regardless of caller role.
- Emergency type bypasses both schedule window check and overlap conflict check; allows same-slot booking.
- Auto-calculated duration is sourced from doctor's custom defaults first, then system defaults.
- Doctor can only create appointments for themselves unless they are clinic_owner.
- `created_by` is always set server-side from JWT; clients cannot supply it.
- Appointment timezone is stored in UTC internally; response includes original timezone offset.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| end_time not provided | Auto-calculate from type using doctor's duration defaults |
| Emergency type overlapping existing appointment | Allow; insert without conflict check |
| Doctor not working on selected day | Return 422 with message "El doctor no trabaja ese dia." |
| Appointment falls during doctor's break | Return 422 with message "El horario cae en el descanso del doctor." |
| treatment_plan_item_id belongs to different patient | Return 404 for the item |
| start_time == end_time | Return 422 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: INSERT — new appointment record
- `audit_logs`: INSERT — PHI access event

**Example query (SQLAlchemy):**
```python
appointment = Appointment(
    patient_id=data.patient_id,
    doctor_id=data.doctor_id,
    start_time=data.start_time.astimezone(timezone.utc),
    end_time=computed_end_time,
    duration_minutes=duration,
    type=data.type,
    status=AppointmentStatus.SCHEDULED,
    notes=data.notes,
    treatment_plan_item_id=data.treatment_plan_item_id,
    created_by=current_user.id,
)
session.add(appointment)
await session.flush()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:appointments:calendar:{doctor_id}:{date}`: INVALIDATE — daily calendar for affected doctor
- `tenant:{tenant_id}:appointments:list:*`: INVALIDATE — all paginated list caches
- `tenant:{tenant_id}:availability:{doctor_id}:{date}`: INVALIDATE — availability slots for that day

**Cache TTL:** N/A (invalidation only on write)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | appointment.created | { tenant_id, appointment_id, patient_id, doctor_id, start_time, type } | After successful insert |
| notifications | reminder.schedule | { tenant_id, appointment_id, start_time, patient_id, channels: ["email","whatsapp","sms"] } | After successful insert |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** create
- **Resource:** appointment
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | appointment_confirmation | patient | On appointment creation |
| whatsapp | appointment_confirmation_wa | patient | On appointment creation (if WhatsApp enabled) |

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on create (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates calendar, list, and availability caches for the affected doctor/date

### Database Performance

**Queries executed:** 5 (patient lookup, doctor lookup, schedule load, overlap check, insert)

**Indexes required:**
- `appointments.doctor_id` — INDEX
- `appointments.patient_id` — INDEX
- `appointments.(doctor_id, start_time, end_time, status)` — COMPOSITE INDEX for overlap queries
- `appointments.start_time` — INDEX (for date-range filtering)
- `doctor_schedules.user_id` — INDEX (exists from U-07)

**N+1 prevention:** Patient and doctor info eagerly loaded in single JOIN on insert response.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, doctor_id | Pydantic UUID validator | Rejects non-UUID strings before DB query |
| start_time, end_time | Pydantic datetime validator with timezone | ISO 8601 strict parsing |
| notes | Pydantic strip() + bleach.clean | Free-text field, sanitize HTML |
| type | Pydantic enum validator | Whitelist approach |
| treatment_plan_item_id | Pydantic UUID validator (optional) | Validated if provided |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, notes (may contain clinical information), treatment_plan_item_id

**Audit requirement:** All write operations logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Create consultation with auto-calculated duration
   - **Given:** Authenticated receptionist, valid patient and doctor, doctor works on Monday 08:00-17:00, slot is free
   - **When:** POST /api/v1/appointments with type=consultation, no end_time
   - **Then:** 201 Created, end_time = start_time + 30 min, status = scheduled

2. Create procedure with explicit end_time
   - **Given:** Authenticated doctor (own appointment), valid patient, slot free
   - **When:** POST /api/v1/appointments with type=procedure, start + end_time provided
   - **Then:** 201 Created with supplied end_time, duration_minutes calculated from diff

3. Create appointment with treatment_plan_item_id
   - **Given:** Authenticated clinic_owner, valid treatment_plan_item belonging to patient
   - **When:** POST /api/v1/appointments with treatment_plan_item_id
   - **Then:** 201 Created, treatment_plan_item_id linked

#### Edge Cases
1. Emergency overlapping existing appointment
   - **Given:** Doctor has a scheduled consultation at 09:00-09:30
   - **When:** POST with type=emergency, start_time=09:00
   - **Then:** 201 Created without conflict error

2. Doctor uses custom duration for consultation (45 min)
   - **Given:** Doctor has appointment_duration_defaults.consultation = 45 in doctor_schedules
   - **When:** POST with type=consultation, no end_time
   - **Then:** 201 Created, end_time = start_time + 45 min

#### Error Cases
1. Slot overlap for non-emergency
   - **Given:** Doctor has scheduled appointment 09:00-09:30
   - **When:** POST with type=consultation, start_time=09:15
   - **Then:** 409 Conflict with conflicting_appointment_id

2. Doctor not working that day
   - **Given:** Selected doctor has Saturday marked as is_working=false
   - **When:** POST with start_time on a Saturday
   - **Then:** 422 with schedule validation error

3. Doctor creating appointment for another doctor
   - **Given:** Caller is doctor A, doctor_id is doctor B
   - **When:** POST /api/v1/appointments
   - **Then:** 403 Forbidden

4. patient_id not in tenant
   - **Given:** Valid JWT, patient_id belongs to different tenant
   - **When:** POST /api/v1/appointments
   - **Then:** 404 Paciente no encontrado

### Test Data Requirements

**Users:** clinic_owner, two doctors (one with custom durations), assistant, receptionist

**Patients/Entities:** Active patient, inactive patient, treatment plan with item linked to patient

### Mocking Strategy

- Redis: Use `fakeredis` for schedule cache; simulate cache miss for availability check
- RabbitMQ: Mock publish, assert `appointment.created` and `reminder.schedule` events dispatched
- Doctor schedule: Seed `doctor_schedules` table with known working days

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/appointments returns 201 with full appointment object
- [ ] end_time auto-calculated from appointment type when not provided
- [ ] Doctor's custom duration defaults used when available
- [ ] Slot overlap returns 409 for non-emergency appointments
- [ ] Emergency type bypasses overlap and schedule checks
- [ ] Doctor cannot create appointment for another doctor (403)
- [ ] Appointment falls within doctor's working window or returns 422
- [ ] audit_log entry written with PHI flag
- [ ] appointment.created and reminder.schedule events dispatched to RabbitMQ
- [ ] Calendar and availability caches invalidated
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Patient self-booking via public portal (see AP-15)
- Recurring appointments
- Group appointments (multiple patients)
- Sending SMS/WhatsApp confirmation messages (handled by notification worker consuming appointment.created event)
- Appointment status transitions after creation (see AP-06, AP-07, AP-08)

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
