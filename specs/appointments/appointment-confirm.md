# AP-06 Confirm Appointment Spec

---

## Overview

**Feature:** Confirm a scheduled appointment. Can be triggered by clinic staff on behalf of a patient, or by the patient directly via the patient portal (e.g., by clicking a confirmation link in the reminder notification). Transitions status from scheduled to confirmed.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create.md), AP-02 (appointment-get.md), AP-17 (reminder-config.md), infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients may only confirm their own appointments. Staff roles may confirm any appointment in the tenant. Confirmation via reminder notification link uses a signed short-lived token (see Special Token Flow below).

---

## Endpoint

```
POST /api/v1/appointments/{appointment_id}/confirm
```

**Rate Limiting:**
- 30 requests per minute per user
- 10 requests per hour per IP for unauthenticated confirmation token flows

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token (or omit if using confirmation_token) | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| appointment_id | Yes | uuid | Must be valid UUID; must exist in tenant | Appointment to confirm | c3d4e5f6-a1b2-7890-abcd-1234567890ef |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| token | No | string | Signed confirmation token (alternative to JWT auth) | Short-lived token from reminder notification | eyJhcHBvaW50... |

### Request Body Schema

```json
{}
```

No request body fields required. Body may be omitted entirely.

**Example Request (staff confirms for patient):**
```json
{}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "status": "string (confirmed)",
  "confirmed_at": "string (ISO 8601 datetime)",
  "confirmed_by": "uuid | null",
  "confirmed_by_patient": "boolean",
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "start_time": "string (ISO 8601 datetime)",
  "end_time": "string (ISO 8601 datetime)",
  "type": "string"
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "status": "confirmed",
  "confirmed_at": "2026-03-14T09:00:00-05:00",
  "confirmed_by": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "confirmed_by_patient": true,
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T09:00:00-05:00",
  "end_time": "2026-03-15T09:30:00-05:00",
  "type": "consultation"
}
```

### Error Responses

#### 401 Unauthorized
**When:** No JWT and no valid token query param. Or JWT is invalid/expired.

**Example:**
```json
{
  "error": "unauthorized",
  "message": "Autenticacion requerida para confirmar la cita."
}
```

#### 403 Forbidden
**When:** Patient JWT but appointment.patient_id does not match caller's patient record. Or token is valid but belongs to a different appointment.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para confirmar esta cita."
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

#### 410 Gone
**When:** Confirmation token has expired (tokens are valid for 48 hours from issuance).

**Example:**
```json
{
  "error": "token_expired",
  "message": "El enlace de confirmacion ha expirado. Por favor contacte a la clinica."
}
```

#### 422 Unprocessable Entity
**When:** Appointment is not in scheduled status (already confirmed, cancelled, completed, or no_show).

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "La cita ya fue confirmada.",
  "details": {
    "current_status": "confirmed"
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

1. Determine auth mode: if `token` query param present, validate signed confirmation token (HMAC-SHA256, 48h TTL). Extract `appointment_id` and `patient_id` from token claims. If token is expired, return 410. If JWT is present instead, use standard JWT validation.
2. Resolve tenant from JWT or token claims; set `search_path` to tenant schema.
3. Load appointment from DB. Return 404 if not found.
4. If auth mode = JWT + patient role: assert `appointment.patient_id == caller_linked_patient_id`. Return 403 if mismatch.
5. If auth mode = token: assert `appointment.id == token.appointment_id` and `appointment.patient_id == token.patient_id`. Return 403 if mismatch.
6. Validate `appointment.status == 'scheduled'`. Return 422 if any other status.
7. Execute UPDATE: `status = 'confirmed'`, `confirmed_at = now()`, `confirmed_by = caller_user_id (or null for token flow)`, `confirmed_by_patient = (patient role or token flow ? true : false)`.
8. Write audit log entry.
9. Invalidate cache: appointment detail, calendar list.
10. Dispatch `appointment.confirmed` event to RabbitMQ (can trigger a confirmation acknowledgment back to patient).
11. Return 200 with confirmed appointment summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| appointment_id | Valid UUID, exists in tenant | Cita no encontrada. |
| token (if used) | Valid HMAC signature, not expired (< 48h) | El enlace de confirmacion ha expirado. |
| appointment.status | Must be scheduled | La cita ya fue confirmada / cancelada / completada. |

**Business Rules:**

- Confirmation is idempotent for staff: if already confirmed, return 422 with clear message.
- `confirmed_by_patient` = true when patient confirms (via JWT or token); false when staff confirms on behalf.
- `confirmed_by` is null when confirmation happens via anonymous token (no authenticated user session).
- Confirmation token is generated by the notification worker when sending the 24h reminder; not generated by this endpoint.
- If appointment is already confirmed and staff attempts to confirm again, return 422 (not silently accept).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Staff confirms already confirmed appointment | Return 422 invalid_status_transition |
| Token belongs to correct appointment but different tenant | Reject — tenant context mismatch |
| Patient has no linked patient record in tenant | Return 403 Forbidden |
| Appointment cancelled before patient clicks confirmation link | Return 422 (appointment is cancelled) |
| Confirmation via valid token on completed appointment | Return 422 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: UPDATE — status, confirmed_at, confirmed_by, confirmed_by_patient
- `audit_logs`: INSERT — confirm event

**Example query (SQLAlchemy):**
```python
stmt = (
    update(Appointment)
    .where(Appointment.id == appointment_id)
    .values(
        status=AppointmentStatus.CONFIRMED,
        confirmed_at=utcnow(),
        confirmed_by=current_user_id_or_none,
        confirmed_by_patient=is_patient_confirmation,
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

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | appointment.confirmed | { tenant_id, appointment_id, patient_id, confirmed_by_patient } | After successful confirm |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** update
- **Resource:** appointment
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** Yes (optional — confirmation acknowledgment)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | appointment_confirmed_ack | patient | When patient confirms (portal notification) |

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** No caching on confirm (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates appointment detail and calendar caches

### Database Performance

**Queries executed:** 2 (load appointment, update)

**Indexes required:**
- `appointments.id` — PRIMARY KEY (exists)
- `appointments.patient_id` — INDEX (for patient role check)
- `appointments.status` — INDEX (for status validation and reporting)

**N+1 prevention:** Not applicable — single appointment operation.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_id | Pydantic UUID validator | URL param |
| token | HMAC-SHA256 signature verification + expiry check | Cryptographic validation |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API. Confirmation token is cryptographically signed.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id (in confirmation token claims)

**Audit requirement:** All confirmation events logged. Token-based confirmation logged with token_flow=true flag.

---

## Testing

### Test Cases

#### Happy Path
1. Receptionist confirms appointment for patient
   - **Given:** Authenticated receptionist JWT, appointment status=scheduled
   - **When:** POST /api/v1/appointments/{id}/confirm
   - **Then:** 200 with status=confirmed, confirmed_by_patient=false

2. Patient confirms via JWT (portal)
   - **Given:** Valid patient JWT, appointment.patient_id matches caller's record
   - **When:** POST /api/v1/appointments/{id}/confirm
   - **Then:** 200 with status=confirmed, confirmed_by_patient=true

3. Patient confirms via reminder link token
   - **Given:** Valid HMAC token in ?token=..., appointment status=scheduled
   - **When:** POST /api/v1/appointments/{id}/confirm?token=...
   - **Then:** 200 with confirmed_by=null, confirmed_by_patient=true

#### Edge Cases
1. Double confirmation by staff — idempotency check
   - **Given:** Appointment already confirmed
   - **When:** POST confirm again
   - **Then:** 422 invalid_status_transition (not silently ignored)

2. Confirmation token for correct appointment but already cancelled
   - **Given:** Valid token, appointment status=cancelled
   - **When:** POST confirm with token
   - **Then:** 422 with current_status=cancelled

#### Error Cases
1. Expired confirmation token
   - **Given:** Token issued 50 hours ago (> 48h TTL)
   - **When:** POST confirm?token=...
   - **Then:** 410 Gone token_expired

2. Patient confirms another patient's appointment
   - **Given:** Patient JWT, appointment.patient_id = different patient
   - **When:** POST confirm
   - **Then:** 403 Forbidden

3. No auth at all
   - **Given:** No JWT, no token param
   - **When:** POST confirm
   - **Then:** 401 Unauthorized

4. Appointment in completed status
   - **Given:** Appointment status=completed
   - **When:** POST confirm
   - **Then:** 422 invalid_status_transition

### Test Data Requirements

**Users:** clinic_owner, doctor, receptionist, patient (with linked patient record), second patient

**Patients/Entities:** Appointments in scheduled, confirmed, cancelled, completed status; valid and expired HMAC confirmation tokens

### Mocking Strategy

- HMAC token generation: Use test secret key; generate tokens with known expiry for tests
- RabbitMQ: Mock publish; assert `appointment.confirmed` event dispatched
- Redis: Use `fakeredis`; verify cache invalidation

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/appointments/{id}/confirm returns 200 with confirmed status
- [ ] Staff confirmation sets confirmed_by_patient=false
- [ ] Patient confirmation (JWT or token) sets confirmed_by_patient=true
- [ ] Expired token returns 410 Gone
- [ ] Cannot confirm cancelled, completed, or no_show appointments (422)
- [ ] Patient role restricted to own appointments (403)
- [ ] appointment.confirmed event dispatched to RabbitMQ
- [ ] Cache invalidated for detail and calendar keys
- [ ] Audit log entry written
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Generating confirmation tokens (handled by notification worker / reminder system)
- Patient portal UI for confirmation
- Cancelling from a confirmation link (see AP-05)
- Moving appointment to in_progress (handled by AP-07)

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
