# PP-09 Portal Cancel Appointment Spec

---

## Overview

**Feature:** Patient cancels one of their own appointments from the portal. Subject to cancellation policy configured per tenant (e.g., 24h minimum notice). Requires a reason field. Once cancelled, the appointment cannot be un-cancelled from the portal. Notifies clinic staff.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-03 (portal-appointments.md), PP-08 (portal-book-appointment.md), appointments domain (AP-05 appointment-cancel.md), infra/multi-tenancy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient can only cancel their own appointments — ownership enforced at query level with `patient_id = jwt.sub`.

---

## Endpoint

```
POST /api/v1/portal/appointments/{appointment_id}/cancel
```

**Rate Limiting:**
- 10 requests per hour per patient (prevent cancel-rebook spam)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| appointment_id | Yes | string (UUID) | Valid UUID v4 | Appointment to cancel | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "reason": "string (required) — patient's reason for cancellation, max 500 chars",
  "reason_category": "string (optional) — enum: scheduling_conflict, illness, cost, no_longer_needed, other; default: other"
}
```

**Example Request:**
```json
{
  "reason": "Tuve un imprevisto en el trabajo y no puedo asistir.",
  "reason_category": "scheduling_conflict"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "status": "string — always 'cancelled'",
  "appointment_id": "uuid",
  "cancelled_at": "string (ISO 8601 datetime)",
  "reason": "string",
  "reason_category": "string",
  "refund_eligible": "boolean — whether a refund/credit may apply per tenant policy",
  "message": "string — tenant-configured cancellation acknowledgement message"
}
```

**Example:**
```json
{
  "status": "cancelled",
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "cancelled_at": "2026-02-25T16:30:00-05:00",
  "reason": "Tuve un imprevisto en el trabajo y no puedo asistir.",
  "reason_category": "scheduling_conflict",
  "refund_eligible": false,
  "message": "Su cita ha sido cancelada. Si desea reagendar, puede hacerlo desde este portal o contactando a la clinica."
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing reason field, malformed JSON, invalid reason_category.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "reason": ["El motivo de cancelacion es obligatorio."],
    "reason_category": ["Categoria no valida. Opciones: scheduling_conflict, illness, cost, no_longer_needed, other."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal", role is not "patient", or appointment does not belong to this patient.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para cancelar esta cita."
}
```

#### 404 Not Found
**When:** Appointment with given ID not found in tenant, or does not belong to authenticated patient.

**Example:**
```json
{
  "error": "appointment_not_found",
  "message": "Cita no encontrada."
}
```

#### 409 Conflict
**When:** Appointment already cancelled.

**Example:**
```json
{
  "error": "already_cancelled",
  "message": "Esta cita ya fue cancelada el 2026-02-20T10:00:00-05:00.",
  "details": {
    "cancelled_at": "2026-02-20T10:00:00-05:00"
  }
}
```

#### 422 Unprocessable Entity
**When:** Cancellation not allowed — appointment is past, completed, or within the cancellation notice window.

**Example:**
```json
{
  "error": "cancellation_not_allowed",
  "message": "No es posible cancelar esta cita. La politica de cancelacion requiere un minimo de 24 horas de anticipacion. El plazo limite fue el 2026-03-09T10:00:00-05:00.",
  "details": {
    "reason": "cancellation_window_expired",
    "policy_hours": 24,
    "cancel_deadline": "2026-03-09T10:00:00-05:00",
    "appointment_scheduled_at": "2026-03-10T10:00:00-05:00"
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Validate path parameter: appointment_id must be valid UUID v4.
3. Validate request body: reason required; reason_category optional with enum check.
4. Check rate limit: 10 cancellations/hour per patient_id.
5. Resolve tenant schema; set `search_path`.
6. Fetch appointment: `SELECT ... FROM appointments WHERE id = :appointment_id AND patient_id = :patient_id`. If not found, return 404 (do not reveal whether appointment exists for another patient).
7. Check appointment status:
   - If status = 'cancelled', return 409 with cancelled_at.
   - If status IN ('completed', 'no_show'), return 422: cannot cancel past appointment.
8. Check cancellation policy:
   - Fetch `tenant_settings.cancellation_policy_hours` (0 = no restriction, 24, 48, etc.).
   - If policy_hours > 0: `cancel_deadline = scheduled_at - policy_hours`. If `NOW() > cancel_deadline`, return 422 with policy details.
   - If policy_hours = 0: always allowed.
9. Determine `refund_eligible`:
   - Fetch `tenant_settings.cancellation_refund_policy` (boolean or days threshold).
   - Simple rule: if cancelled within refund window AND payment was made → refund_eligible=true. (Actual refund processing is handled by billing domain, not this endpoint.)
10. UPDATE appointment: status='cancelled', cancelled_at=NOW(), cancellation_reason=reason, cancellation_reason_category=reason_category, cancelled_by='patient', cancelled_by_id=patient_id.
11. Write audit log.
12. Invalidate appointment caches.
13. Dispatch RabbitMQ jobs: staff notification + patient confirmation.
14. Return 200 with cancellation confirmation.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| appointment_id | Valid UUID v4 | Cita no encontrada. |
| reason | Required; 1-500 chars; strip_tags | El motivo de cancelacion es obligatorio. |
| reason_category | Optional enum: scheduling_conflict, illness, cost, no_longer_needed, other | Categoria de cancelacion no valida. |

**Business Rules:**

- Patient can only cancel appointments with status IN ('pending', 'confirmed') and that are in the future beyond the cancellation window.
- Cancellation policy is enforced even for portal-created appointments.
- `cancelled_by='patient'` distinguishes from clinic-initiated cancellation in audit trail and analytics.
- Refund eligibility is informational only — no payment processing happens in this endpoint.
- A cancelled appointment cannot be un-cancelled from portal; patient must book a new appointment.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Cancellation policy = 0 hours | Any future appointment cancellable at any time |
| Appointment in 25 hours, policy = 24h | Cancellable (25 > 24) |
| Appointment in 23 hours, policy = 24h | Not cancellable — window expired |
| No_show appointment | Return 422 cannot cancel past/completed appointment |
| Patient cancels pending appointment (not yet confirmed) | 200 — allowed |
| Clinic simultaneously cancels the same appointment | 409 already_cancelled (second request loses race) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: UPDATE — status='cancelled', cancelled_at, cancellation_reason, cancellation_reason_category, cancelled_by, cancelled_by_id

**Example query (SQLAlchemy):**
```python
stmt = (
    update(Appointment)
    .where(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient_id,
        Appointment.status.in_(["pending", "confirmed"]),
    )
    .values(
        status="cancelled",
        cancelled_at=func.now(),
        cancellation_reason=data.reason,
        cancellation_reason_category=data.reason_category or "other",
        cancelled_by="patient",
        cancelled_by_id=patient_id,
    )
    .returning(Appointment.scheduled_at)
)
result = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:appointments:*`: INVALIDATE
- `tenant:{tenant_id}:appointments:schedule:{date}`: INVALIDATE — free up the cancelled slot

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | appointment.cancelled_by_patient | { tenant_id, appointment_id, patient_id, reason_category } | After successful cancellation |
| notifications | appointment.cancellation_confirmation_patient | { tenant_id, appointment_id, patient_id } | After successful cancellation |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** cancel
- **Resource:** appointment
- **PHI involved:** Yes (cancellation reason may contain health-related information)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | appointment_cancelled_patient | clinic staff (receptionist) | On cancellation |
| email | appointment_cancellation_staff | receptionist + assigned doctor | On cancellation |
| email | appointment_cancellation_patient | patient | On cancellation (confirmation) |
| whatsapp | appointment_cancelled_wa | patient | If WhatsApp preference set |

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on write; invalidation of appointment caches
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Patient appointment list and daily schedule cache

### Database Performance

**Queries executed:** 3 (appointment fetch, tenant settings for policy, update with RETURNING)

**Indexes required:**
- `appointments.(id, patient_id)` — COMPOSITE INDEX (ownership check + fetch)
- `appointments.(patient_id, status)` — COMPOSITE INDEX (status filter)
- `appointments.scheduled_at` — INDEX (policy window check)

**N+1 prevention:** Single update with WHERE clause; tenant settings cached in Redis.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_id | UUID v4 regex validation (path param) | Ownership verified by DB query |
| reason | Pydantic strip + bleach.clean; max 500 chars | Patient free text with PHI potential |
| reason_category | Pydantic Literal enum | Strict allowlist |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs escaped by Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** reason (may contain health information), appointment reference (reveals care context)

**Audit requirement:** All cancellations logged with reason (PHI — may contain illness description).

---

## Testing

### Test Cases

#### Happy Path
1. Cancel confirmed appointment within policy window
   - **Given:** Appointment 48 hours from now, policy=24h; status=confirmed
   - **When:** POST /api/v1/portal/appointments/{id}/cancel with reason
   - **Then:** 200 OK, status='cancelled', notifications dispatched

2. Cancel pending appointment (not yet confirmed)
   - **Given:** Appointment created via portal (status=pending)
   - **When:** POST cancel
   - **Then:** 200 OK, status='cancelled'

3. Cancel with no restriction policy (policy=0h)
   - **Given:** Tenant policy=0h; appointment in 30 minutes
   - **When:** POST cancel
   - **Then:** 200 OK — no window restriction

#### Edge Cases
1. Exactly at cancellation boundary (25h for 24h policy)
   - **Given:** Appointment 25 hours away; policy=24h
   - **When:** POST cancel
   - **Then:** 200 OK — within cancellable window

2. Just expired cancellation window (23h for 24h policy)
   - **Given:** Appointment 23 hours away; policy=24h
   - **When:** POST cancel
   - **Then:** 422 with cancel_deadline in response

3. Concurrent clinic and patient cancellation
   - **Given:** Two simultaneous cancel requests from different actors
   - **When:** Both arrive at same moment
   - **Then:** One succeeds, second returns 409 already_cancelled

#### Error Cases
1. Appointment already cancelled
   - **Given:** Appointment with status=cancelled
   - **When:** POST cancel
   - **Then:** 409 already_cancelled with cancelled_at

2. Appointment belongs to different patient
   - **Given:** Valid appointment_id but different patient owns it
   - **When:** POST from current patient's JWT
   - **Then:** 404 appointment_not_found

3. Past/completed appointment
   - **Given:** Appointment with status=completed
   - **When:** POST cancel
   - **Then:** 422 cancellation_not_allowed

4. Missing reason
   - **Given:** Patient authenticated, valid appointment
   - **When:** POST with empty request body
   - **Then:** 400 with reason validation error

5. Rate limit: 11th cancellation in 1 hour
   - **Given:** Patient already cancelled 10 appointments this hour
   - **When:** 11th POST
   - **Then:** 429 with retry_after_seconds

### Test Data Requirements

**Users:** Patient with portal_access=true; appointments in various statuses.

**Patients/Entities:** Tenant with cancellation_policy_hours=24 and another with 0; appointments at various time distances.

### Mocking Strategy

- Redis: fakeredis for rate limit testing
- RabbitMQ: Mock publish, verify both staff and patient notification jobs
- Time: pytest-freezegun for policy window boundary tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient can cancel own confirmed/pending future appointments within policy window
- [ ] Status updated to 'cancelled' with cancelled_by='patient' in DB
- [ ] Reason and reason_category stored
- [ ] Cancellation policy enforced: 422 when within notice window
- [ ] Appointment belonging to another patient returns 404
- [ ] Already cancelled appointment returns 409
- [ ] Staff and patient notifications dispatched via RabbitMQ
- [ ] Appointment list and schedule caches invalidated
- [ ] Audit log entry written with PHI flag for reason
- [ ] Rate limit 10/hour per patient enforced
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Rescheduling (cancel + rebook in one step — future enhancement)
- Clinic-initiated cancellation (AP-05 appointment-cancel.md)
- Refund processing (billing domain)
- Cancellation policy configuration (tenant settings)
- Re-activating a cancelled appointment

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
- [x] Audit trail for cancellation with PHI flag

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized (indexes listed)
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
