# PP-08 Portal Book Appointment Spec

---

## Overview

**Feature:** Patient books an appointment from the portal. Patient is already authenticated and identified — no anonymous booking. Patient selects doctor, appointment type, available time slot, and optionally adds notes. Subject to tenant-configured booking rules (advance notice, allowed types, available slots). Creates appointment with status 'pending' pending clinic confirmation.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-03 (portal-appointments.md), appointments domain (AP-01 through AP-10), infra/multi-tenancy.md, infra/rate-limiting.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Portal-scoped JWT required (scope=portal). Appointment is always created for the authenticated patient — patient_id cannot be overridden in request body.

---

## Endpoint

```
POST /api/v1/portal/appointments
```

**Rate Limiting:**
- 5 requests per hour per patient (prevent appointment spam)
- 20 requests per day per patient

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "doctor_id": "string (optional) — UUID; if omitted, any available doctor",
  "appointment_type_id": "string (required) — UUID; references tenant's appointment type catalog",
  "scheduled_at": "string (required) — ISO 8601 datetime with timezone, e.g. '2026-03-15T10:00:00-05:00'",
  "notes": "string (optional) — patient notes or reason for visit, max 500 chars",
  "preferred_location_id": "string (optional) — UUID; clinic branch preference"
}
```

**Example Request:**
```json
{
  "doctor_id": "d1e2f3a4-b5c6-7890-abcd-123456789012",
  "appointment_type_id": "b2c3d4e5-f6a7-8901-bcde-234567890123",
  "scheduled_at": "2026-03-15T10:00:00-05:00",
  "notes": "Tengo dolor en el diente 21 desde hace 3 dias.",
  "preferred_location_id": "c3d4e5f6-a7b8-9012-cdef-345678901234"
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
  "status": "string — always 'pending' on creation from portal",
  "scheduled_at": "string (ISO 8601 datetime)",
  "duration_minutes": "integer — from appointment type definition",
  "appointment_type": {
    "id": "uuid",
    "name": "string"
  },
  "doctor": {
    "id": "uuid | null",
    "name": "string | null — null if no specific doctor assigned"
  },
  "location": {
    "id": "uuid | null",
    "name": "string | null",
    "address": "string | null"
  },
  "notes": "string | null",
  "confirmation_message": "string — tenant-configured message shown to patient post-booking",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "g9h0i1j2-k3l4-5678-mnop-qr1234567890",
  "status": "pending",
  "scheduled_at": "2026-03-15T10:00:00-05:00",
  "duration_minutes": 30,
  "appointment_type": {
    "id": "b2c3d4e5-f6a7-8901-bcde-234567890123",
    "name": "Consulta general"
  },
  "doctor": {
    "id": "d1e2f3a4-b5c6-7890-abcd-123456789012",
    "name": "Dr. Juan Martinez"
  },
  "location": {
    "id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "name": "Sede Norte",
    "address": "Calle 100 # 15-20, Bogota"
  },
  "notes": "Tengo dolor en el diente 21 desde hace 3 dias.",
  "confirmation_message": "Su cita ha sido registrada. La clinica la confirmara en las proximas 2 horas. Si necesita ayuda, contactenos al +5716001234.",
  "created_at": "2026-02-25T16:00:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON, missing required fields, scheduled_at in invalid format.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "scheduled_at": ["Formato de fecha no valido. Use ISO 8601 con zona horaria."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal", role is not "patient", or tenant has portal booking disabled.

**Example:**
```json
{
  "error": "portal_booking_disabled",
  "message": "La reserva de citas en linea no esta habilitada para esta clinica. Por favor contacte a la clinica directamente."
}
```

#### 409 Conflict
**When:** Time slot already taken (race condition) or patient already has an appointment at the same time.

**Example:**
```json
{
  "error": "slot_unavailable",
  "message": "El horario seleccionado ya no esta disponible. Por favor seleccione otro horario."
}
```

#### 422 Unprocessable Entity
**When:** Validation failures — past date, insufficient advance notice, appointment type not allowed for portal booking.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "scheduled_at": ["No se pueden reservar citas con menos de 2 horas de anticipacion."],
    "appointment_type_id": ["Este tipo de cita no esta disponible para reserva en linea."]
  }
}
```

#### 429 Too Many Requests
**When:** Patient exceeded hourly (5) or daily (20) booking limit.

**Example:**
```json
{
  "error": "booking_rate_limit",
  "message": "Ha alcanzado el limite de reservas. Intente nuevamente mas tarde.",
  "retry_after_seconds": 1800
}
```

#### 500 Internal Server Error
**When:** Unexpected database failure or notification dispatch error.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Validate request body: required fields, ISO 8601 datetime with timezone, UUID formats.
3. Check rate limits: 5/hour and 20/day per patient_id in Redis.
4. Resolve tenant schema; check `tenant_settings.portal_booking_enabled = true`. If false, return 403.
5. Resolve appointment type: fetch from `appointment_types WHERE id = :appointment_type_id AND portal_bookable = true`. If not found or not portal_bookable, return 422.
6. Get appointment duration from `appointment_types.default_duration_minutes`.
7. Validate `scheduled_at`:
   - Must be in the future.
   - Must respect `tenant_settings.portal_booking_min_advance_hours` (e.g., 2 hours minimum notice).
   - Must respect `tenant_settings.portal_booking_max_advance_days` (e.g., max 30 days ahead).
   - Must fall within clinic operating hours (fetch from `clinic_schedules`).
8. If `doctor_id` provided, verify doctor belongs to tenant and is active. Check doctor's availability for the slot (no existing appointment that overlaps). If slot taken, return 409.
9. If `doctor_id` not provided, find any available doctor for the slot and appointment type — assign first available.
10. Check patient has no other appointment at same time (prevent double-booking).
11. INSERT appointment:
    - `patient_id` = jwt.sub
    - `doctor_id` = resolved doctor (or null if assignment deferred to clinic)
    - `status` = 'pending' (portal-created appointments require clinic confirmation)
    - `source` = 'portal'
    - `scheduled_at`, `duration_minutes`, `appointment_type_id`, `notes`, `location_id`
12. Write audit log.
13. Invalidate appointment caches for this patient.
14. Dispatch RabbitMQ jobs:
    - Notification to clinic staff: new pending appointment to confirm.
    - Confirmation notification to patient (email/WhatsApp based on preferences).
15. Fetch `tenant_settings.portal_booking_confirmation_message` for response.
16. Return 201 with appointment details.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| appointment_type_id | Valid UUID; must exist and have portal_bookable=true | Tipo de cita no disponible para reserva en linea. |
| scheduled_at | ISO 8601 with TZ; must be future; min advance hours respected; within operating hours | El horario seleccionado no es valido. |
| doctor_id | If provided: valid UUID; doctor must be active in tenant; available at scheduled_at | Doctor no disponible en el horario seleccionado. |
| notes | Optional; max 500 chars; strip_tags | Notas demasiado largas (max 500 caracteres). |
| preferred_location_id | If provided: valid UUID; location must belong to tenant | Sede no encontrada. |

**Business Rules:**

- Portal-created appointments always start with status='pending'; clinic must confirm.
- Patient cannot override their own patient_id — always set from JWT sub.
- `source='portal'` field marks the appointment as patient-initiated (useful for analytics).
- If no doctor_id provided, appointment is created with doctor_id=null and status='pending' until clinic assigns a doctor on confirmation.
- Tenant can disable portal booking globally (`portal_booking_enabled=false`) or per appointment type (`portal_bookable=false`).
- Operating hours validated against `clinic_schedules` table for the given day/location.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Slot becomes unavailable between slot selection and POST | Return 409 (slot_unavailable) |
| No doctors available for the slot | Return 422: no_availability with message to try different time |
| Patient already has appointment overlapping requested slot | Return 409 with existing appointment reference |
| scheduled_at exactly at minimum advance notice boundary | Accept (>= not strictly >) |
| Location closed on requested day (holiday) | Return 422: location_closed |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: INSERT — new appointment with status='pending', source='portal'

**Example query (SQLAlchemy):**
```python
appointment = Appointment(
    patient_id=patient_id,
    doctor_id=resolved_doctor_id,
    appointment_type_id=data.appointment_type_id,
    scheduled_at=data.scheduled_at,
    duration_minutes=appointment_type.default_duration_minutes,
    status=AppointmentStatus.PENDING,
    source="portal",
    notes=data.notes,
    location_id=data.preferred_location_id,
    created_source="patient_portal",
)
session.add(appointment)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:appointments:*`: INVALIDATE — all appointment list caches
- `tenant:{tenant_id}:appointments:schedule:{date}`: INVALIDATE — daily schedule cache

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | portal.appointment_booked_patient | { tenant_id, patient_id, appointment_id } | After successful insert |
| notifications | portal.appointment_pending_staff | { tenant_id, appointment_id, patient_id } | After successful insert |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** appointment
- **PHI involved:** Yes (appointment reason/notes may contain clinical information)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | appointment_booking_confirmation | patient | On successful booking |
| whatsapp | appointment_booking_wa | patient | If WhatsApp preference set |
| in-app | new_pending_appointment | clinic staff (receptionist) | On successful booking |
| email | new_pending_appointment_staff | receptionist | On successful booking |

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 600ms (slot conflict check and availability query add latency)

### Caching Strategy
- **Strategy:** No caching on write; invalidation of appointment caches
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Patient appointment list and daily schedule cache invalidated

### Database Performance

**Queries executed:** 5 (tenant settings, appointment type, doctor availability, patient overlap check, insert)

**Indexes required:**
- `appointments.(doctor_id, scheduled_at, status)` — COMPOSITE INDEX (availability check)
- `appointments.(patient_id, scheduled_at)` — COMPOSITE INDEX (patient overlap check)
- `appointment_types.(id, portal_bookable)` — COMPOSITE INDEX
- `clinic_schedules.(location_id, day_of_week)` — COMPOSITE INDEX

**N+1 prevention:** Single availability check query per doctor. Doctor selection query returns only first available.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_type_id | UUID v4 validation | Path to appointment type catalog |
| scheduled_at | ISO 8601 datetime parse; timezone required | Prevent ambiguous times |
| doctor_id | UUID v4 validation if provided | Verified against tenant's doctor list |
| notes | Pydantic strip + bleach.clean; max 500 chars | Patient free text |
| preferred_location_id | UUID v4 validation if provided | Verified against tenant's locations |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs escaped by Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** notes (patient's reason for visit), scheduled_at + doctor assignment (reveals care context)

**Audit requirement:** All bookings logged (PHI: notes may contain clinical information).

---

## Testing

### Test Cases

#### Happy Path
1. Book appointment with specific doctor and type
   - **Given:** Patient authenticated, doctor available at requested time, appointment_type is portal_bookable
   - **When:** POST /api/v1/portal/appointments with all fields
   - **Then:** 201 Created, status='pending', source='portal', notifications dispatched

2. Book appointment without specifying doctor
   - **Given:** Patient authenticated, at least one available doctor
   - **When:** POST with no doctor_id
   - **Then:** 201 Created with available doctor assigned (or doctor_id=null if deferred)

3. Book appointment without notes
   - **Given:** Patient authenticated, valid slot
   - **When:** POST without notes field
   - **Then:** 201 Created, notes=null

#### Edge Cases
1. Slot available at exactly min_advance_hours boundary
   - **Given:** min_advance_hours=2; scheduled_at = NOW() + 2 hours exactly
   - **When:** POST appointment
   - **Then:** 201 Created (boundary included)

2. Race condition — slot taken between check and insert
   - **Given:** Two patients simultaneously booking same slot with same doctor
   - **When:** Both POST simultaneously
   - **Then:** One succeeds (201), second returns 409 slot_unavailable

#### Error Cases
1. Appointment type not portal_bookable
   - **Given:** Appointment type exists but portal_bookable=false
   - **When:** POST with that appointment_type_id
   - **Then:** 422 with appointment_type_id validation error

2. Less than minimum advance notice
   - **Given:** min_advance_hours=2; scheduled_at = NOW() + 30 minutes
   - **When:** POST appointment
   - **Then:** 422 with scheduled_at validation error

3. Hourly rate limit exceeded
   - **Given:** Patient already made 5 bookings this hour
   - **When:** 6th POST attempt
   - **Then:** 429 with retry_after_seconds

4. Portal booking disabled
   - **Given:** tenant_settings.portal_booking_enabled=false
   - **When:** POST appointment
   - **Then:** 403 portal_booking_disabled

### Test Data Requirements

**Users:** Patient with portal_access=true; at least 2 doctors with schedules; appointment types with portal_bookable=true and false.

**Patients/Entities:** Tenant with portal_booking_enabled=true; clinic schedules configured; slot availability fixtures.

### Mocking Strategy

- Redis: fakeredis for rate limit testing
- RabbitMQ: Mock publish, verify both notification jobs dispatched
- Time: pytest-freezegun for advance notice boundary tests
- DB row locking: test concurrent inserts in integration tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient can book appointment with valid doctor, type, and time
- [ ] Appointment created with status='pending' and source='portal'
- [ ] Patient_id always set from JWT (cannot be overridden)
- [ ] Slot conflict returns 409 slot_unavailable
- [ ] Portal_booking_disabled returns 403
- [ ] Min advance notice enforced; boundary case accepted
- [ ] Appointment type portal_bookable=false returns 422
- [ ] Rate limit 5/hour and 20/day enforced per patient
- [ ] Both staff and patient notifications dispatched via RabbitMQ
- [ ] Appointment list and schedule caches invalidated
- [ ] Audit log entry written
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms target, < 600ms max)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Rescheduling appointments from portal (future enhancement)
- Real-time slot availability endpoint (separate GET endpoint for slot picker)
- Public/anonymous booking (portal booking requires authentication)
- Clinic-initiated appointment creation (AP-01 appointment-create.md)
- Automatic appointment confirmation (clinic staff confirms via AP-03)

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
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for appointment creation

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation on write)
- [x] DB queries optimized (composite indexes for availability check)
- [x] Pagination N/A

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
