# AP-05 Cancel Appointment Spec

---

## Overview

**Feature:** Cancel an existing appointment with a mandatory reason. Triggers a notification to the patient via configured channels. Frees the time slot so waitlist matching can run. Valid from scheduled or confirmed status only.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create.md), AP-12 (waitlist-add.md), AP-14 (waitlist-notify.md), infra/authentication-rules.md, notifications/reminder-config.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients may only cancel their own appointments via the portal. Patients cannot cancel within 2 hours of the appointment start_time (policy configurable per clinic). Doctors may cancel appointments assigned to themselves. clinic_owner can cancel any appointment.

---

## Endpoint

```
POST /api/v1/appointments/{appointment_id}/cancel
```

**Rate Limiting:**
- 20 requests per minute per user

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
| appointment_id | Yes | uuid | Must be valid UUID; must exist in tenant | Appointment to cancel | c3d4e5f6-a1b2-7890-abcd-1234567890ef |

### Query Parameters

None.

### Request Body Schema

```json
{
  "reason": "string (required) — max 500 chars; free text cancellation reason",
  "cancelled_by_patient": "boolean (optional) — true if patient self-cancelled; default false; set server-side for patient role"
}
```

**Example Request:**
```json
{
  "reason": "El paciente llamo para cancelar por enfermedad."
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
  "status": "string (cancelled)",
  "cancellation_reason": "string",
  "cancelled_at": "string (ISO 8601 datetime)",
  "cancelled_by": "uuid",
  "cancelled_by_patient": "boolean",
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "start_time": "string (ISO 8601 datetime)",
  "end_time": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "status": "cancelled",
  "cancellation_reason": "El paciente llamo para cancelar por enfermedad.",
  "cancelled_at": "2026-03-14T10:00:00-05:00",
  "cancelled_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "cancelled_by_patient": false,
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T09:00:00-05:00",
  "end_time": "2026-03-15T09:30:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** reason field is missing or empty.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El motivo de cancelacion es obligatorio.",
  "details": {
    "reason": ["El motivo de cancelacion es obligatorio."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient attempts to cancel within the clinic's minimum notice window, or a doctor tries to cancel another doctor's appointment without clinic_owner role.

**Example:**
```json
{
  "error": "cancellation_window_expired",
  "message": "No puede cancelar la cita con menos de 2 horas de anticipacion.",
  "details": {
    "minimum_notice_hours": 2,
    "appointment_start": "2026-03-15T09:00:00-05:00"
  }
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
**When:** Appointment is already cancelled, completed, or no_show.

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "La cita ya se encuentra en estado cancelada.",
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

1. Validate `appointment_id` as valid UUID. Validate request body (reason required, non-empty).
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Load appointment from DB. Return 404 if not found.
4. Check RBAC:
   - If caller role = patient: confirm `appointment.patient_id` matches caller's linked patient record. Return 403 if mismatch.
   - If caller role = doctor: confirm `appointment.doctor_id == caller_user_id`. Return 403 if mismatch.
   - clinic_owner, receptionist, assistant: allow any appointment in tenant.
5. If caller role = patient: load tenant setting `min_cancellation_notice_hours` (default 2). If `appointment.start_time - now() < min_notice`, return 403 with cancellation_window_expired error.
6. Validate `appointment.status` is scheduled or confirmed. Return 422 if already cancelled, completed, or no_show.
7. Set `cancelled_by_patient = true` if caller role = patient, else false.
8. Execute UPDATE: set `status = 'cancelled'`, `cancellation_reason = reason`, `cancelled_at = now()`, `cancelled_by = caller_user_id`, `cancelled_by_patient = flag`.
9. Write audit log entry.
10. Invalidate cache: appointment detail, calendar, list, availability caches for the freed date/doctor.
11. Dispatch `appointment.cancelled` event to RabbitMQ.
12. Notification worker subscribing to event: cancel pending reminder jobs for this appointment, send cancellation notification to patient.
13. Dispatch `waitlist.slot_opened` event: includes doctor_id, date, duration, type — triggers waitlist matching for any waiting patients.
14. Return 200 with cancelled appointment summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| reason | Required, non-empty, max 500 chars | El motivo de cancelacion es obligatorio. |
| appointment.status | Must be scheduled or confirmed | La cita ya se encuentra en estado {status}. |
| Cancellation window (patient) | Must be >= min_notice_hours before start_time | No puede cancelar con menos de {n} horas de anticipacion. |

**Business Rules:**

- Minimum cancellation notice for patients is configurable per tenant (default 2 hours). Staff roles have no minimum notice restriction.
- `cancelled_by_patient` flag is always set server-side from JWT role; client-supplied value ignored.
- Cancelling a confirmed appointment still triggers patient notification (important for double-confirmation flows).
- Freed slot triggers waitlist matching asynchronously via `waitlist.slot_opened` event.
- Pending reminder jobs (24h/2h reminders) must be cancelled upon appointment cancellation.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Appointment already in_progress | Return 422 — cannot cancel in_progress appointment |
| Patient cancels exactly at 2h boundary | Allow cancellation (boundary is exclusive: < 2h is rejected) |
| Waitlist has no matching entries for freed slot | Slot opened event processed; no notification sent; no error |
| Clinic has min_cancellation_notice_hours = 0 | Patients can cancel at any time |
| reason contains HTML/script tags | Sanitize on input; store clean text |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: UPDATE — status, cancellation_reason, cancelled_at, cancelled_by, cancelled_by_patient
- `audit_logs`: INSERT — cancel event with PHI flag

**Example query (SQLAlchemy):**
```python
stmt = (
    update(Appointment)
    .where(Appointment.id == appointment_id)
    .values(
        status=AppointmentStatus.CANCELLED,
        cancellation_reason=data.reason,
        cancelled_at=utcnow(),
        cancelled_by=current_user.id,
        cancelled_by_patient=is_patient_caller,
    )
    .returning(Appointment)
)
result = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:appointment:{appointment_id}`: INVALIDATE
- `tenant:{tenant_id}:appointments:calendar:{doctor_id}:{date}`: INVALIDATE
- `tenant:{tenant_id}:appointments:list:*`: INVALIDATE
- `tenant:{tenant_id}:availability:{doctor_id}:{date}`: INVALIDATE — slot is now freed

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | appointment.cancelled | { tenant_id, appointment_id, patient_id, doctor_id, start_time, cancelled_by_patient } | After successful cancel |
| notifications | reminder.cancel | { tenant_id, appointment_id } | Cancels pending reminder jobs |
| waitlist | waitlist.slot_opened | { tenant_id, doctor_id, start_time, end_time, duration_minutes, type } | After successful cancel |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** update
- **Resource:** appointment
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | appointment_cancellation | patient | On successful cancel |
| whatsapp | appointment_cancellation_wa | patient | On successful cancel (if WhatsApp enabled) |
| sms | appointment_cancellation_sms | patient | On successful cancel (if SMS enabled) |

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on cancel (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates appointment detail, calendar, list, and availability caches

### Database Performance

**Queries executed:** 2 (load appointment + update)

**Indexes required:**
- `appointments.id` — PRIMARY KEY (exists)
- `appointments.patient_id` — INDEX (for patient role check)
- `appointments.doctor_id` — INDEX (for doctor role check)
- `appointments.status` — INDEX (for list queries post-cancel)

**N+1 prevention:** Not applicable — single appointment operation.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_id | Pydantic UUID validator | URL param |
| reason | Pydantic strip() + bleach.clean, max 500 chars | Free-text; sanitize HTML |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** cancellation_reason (may contain clinical context), patient_id

**Audit requirement:** All cancel operations logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Staff cancels scheduled appointment
   - **Given:** Authenticated receptionist, appointment status=scheduled
   - **When:** POST /api/v1/appointments/{id}/cancel with valid reason
   - **Then:** 200 with status=cancelled, appointment.cancelled event dispatched

2. Staff cancels confirmed appointment
   - **Given:** Authenticated clinic_owner, appointment status=confirmed
   - **When:** POST /api/v1/appointments/{id}/cancel
   - **Then:** 200 with status=cancelled, patient notification dispatched

3. Patient self-cancels with sufficient notice
   - **Given:** Patient JWT, appointment 4 hours from now, clinic min_notice=2h
   - **When:** POST /api/v1/appointments/{id}/cancel
   - **Then:** 200 with cancelled_by_patient=true

4. Waitlist slot_opened event dispatched
   - **Given:** Appointment cancelled, waitlist entry exists for same doctor/date
   - **When:** Cancel completes
   - **Then:** waitlist.slot_opened event published; waitlist notification worker processes it

#### Edge Cases
1. Clinic with min_cancellation_notice_hours = 0
   - **Given:** Patient JWT, appointment 30 minutes from now, clinic setting = 0
   - **When:** POST cancel
   - **Then:** 200 — no time restriction

2. Reason contains HTML
   - **Given:** reason = "<script>alert('xss')</script>Cancelacion"
   - **When:** POST cancel
   - **Then:** 200 with sanitized reason stored as "Cancelacion"

#### Error Cases
1. Appointment already cancelled
   - **Given:** Appointment status=cancelled
   - **When:** POST cancel again
   - **Then:** 422 invalid_status_transition

2. Patient cancels within minimum notice window
   - **Given:** Patient JWT, appointment 1 hour from now, clinic min_notice=2h
   - **When:** POST cancel
   - **Then:** 403 cancellation_window_expired

3. Doctor cancels another doctor's appointment
   - **Given:** Doctor A JWT, appointment.doctor_id = Doctor B
   - **When:** POST cancel
   - **Then:** 403 Forbidden

4. Missing reason
   - **Given:** Valid JWT, POST body without reason field
   - **When:** POST cancel
   - **Then:** 400 invalid_input with reason validation error

### Test Data Requirements

**Users:** clinic_owner, two doctors, receptionist, patient (with linked patient record)

**Patients/Entities:** Appointments in scheduled, confirmed, cancelled, completed status; tenant settings with min_cancellation_notice_hours configured

### Mocking Strategy

- RabbitMQ: Mock publish; assert `appointment.cancelled`, `reminder.cancel`, and `waitlist.slot_opened` dispatched
- Redis: Use `fakeredis`; verify cache keys invalidated

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/appointments/{id}/cancel returns 200 with cancelled status
- [ ] reason field is required; 400 if missing
- [ ] Cannot cancel completed, cancelled, or no_show appointments (422)
- [ ] Patient role restricted to own appointments and minimum notice window
- [ ] cancelled_by_patient set correctly from JWT role
- [ ] appointment.cancelled event dispatched to RabbitMQ
- [ ] reminder.cancel event dispatched to cancel pending reminders
- [ ] waitlist.slot_opened event dispatched to trigger waitlist matching
- [ ] Patient notification sent via configured channels
- [ ] Cache invalidated for detail, calendar, list, availability keys
- [ ] Audit log entry written
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Bulk cancellation of multiple appointments
- Recurring appointment cancellation logic
- Waitlist notification to specific patient (see AP-14)
- No-show marking (see AP-08)
- Refund processing for paid appointments

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
