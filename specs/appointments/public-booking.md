# AP-15 Public Patient Self-Booking Spec

---

## Overview

**Feature:** Allow patients to self-book an appointment via a shareable public link associated with a tenant clinic. No authentication required. Patient selects a doctor, picks an available time slot, and provides basic contact information. Creates the appointment and, if the patient record does not exist, creates a new patient record automatically. Rate limited to prevent abuse. CAPTCHA verification required on submission. Sends confirmation notification via email and/or WhatsApp upon successful booking.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-16 (public-booking-config.md), AP-09 (availability-get.md), P-01 (patient-get.md), AP-01 (appointment-create.md), infra/rate-limiting.md, infra/multi-tenancy.md

---

## Authentication

- **Level:** Public
- **Tenant context:** Not required — tenant resolved from `tenant_slug` URL parameter
- **Roles allowed:** None — public endpoint, no JWT required
- **Special rules:** IP-based rate limiting enforced. CAPTCHA token required in request body. Tenant must have `public_booking_enabled = true` in settings or request is rejected with 403.

---

## Endpoint

```
POST /api/v1/public/booking/{tenant_slug}
```

**Rate Limiting:**
- 10 requests per hour per IP address
- Redis sliding window: `dentalos:rl:public_booking:{ip}` (TTL 3600s)
- Additional tenant-level limit: 200 public bookings per hour per tenant to prevent spam

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Content-Type | Yes | string | Request format | application/json |
| X-Forwarded-For | No | string | Real IP behind proxy (set by load balancer) | 190.24.145.33 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| tenant_slug | Yes | string | Lowercase alphanumeric, hyphens allowed, max 63 chars | Tenant identifier from shareable URL | clinica-san-jose |

### Query Parameters

None.

### Request Body Schema

```json
{
  "doctor_id": "uuid (required) — ID of the selected doctor within the tenant",
  "start_time": "string (required) — ISO 8601 datetime with timezone, e.g. 2026-03-15T10:00:00-05:00",
  "service_type": "string (required) — enum: consultation, procedure, emergency, follow_up",
  "first_name": "string (required) — patient first name, max 100 chars",
  "last_name": "string (required) — patient last name, max 100 chars",
  "phone": "string (required) — E.164 format, e.g. +573001234567",
  "email": "string (required) — valid email, max 254 chars",
  "document_number": "string (optional) — national ID or document, max 20 chars",
  "document_type": "string (optional) — enum: cc, ti, ce, passport, nit — default: cc",
  "notes": "string (optional) — patient notes or reason for visit, max 500 chars",
  "captcha_token": "string (required) — CAPTCHA response token from provider (hCaptcha or reCAPTCHA v3)"
}
```

**Example Request:**
```json
{
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-20T10:00:00-05:00",
  "service_type": "consultation",
  "first_name": "Laura",
  "last_name": "Herrera Gomez",
  "phone": "+573158765432",
  "email": "laura.herrera@email.com",
  "document_number": "1032456789",
  "document_type": "cc",
  "notes": "Tengo dolor en una muela del juicio desde hace 3 dias.",
  "captcha_token": "03AGdBq27gXjQ..."
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "appointment_id": "uuid",
  "confirmation_code": "string — short human-readable code, e.g. APPT-A3X9",
  "start_time": "string (ISO 8601 datetime)",
  "end_time": "string (ISO 8601 datetime)",
  "duration_minutes": "integer",
  "doctor": {
    "first_name": "string",
    "last_name": "string",
    "specialty": "string | null"
  },
  "clinic": {
    "name": "string",
    "address": "string | null",
    "phone": "string | null"
  },
  "patient_created": "boolean — true if a new patient record was created",
  "message": "string — confirmation message in es-419"
}
```

**Example:**
```json
{
  "appointment_id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "confirmation_code": "APPT-A3X9",
  "start_time": "2026-03-20T10:00:00-05:00",
  "end_time": "2026-03-20T10:30:00-05:00",
  "duration_minutes": 30,
  "doctor": {
    "first_name": "Carlos",
    "last_name": "Mendez",
    "specialty": "Odontologia General"
  },
  "clinic": {
    "name": "Clinica Dental San Jose",
    "address": "Calle 45 #12-34, Bogota",
    "phone": "+5716001234"
  },
  "patient_created": true,
  "message": "Tu cita ha sido agendada. Recibirás una confirmación a laura.herrera@email.com."
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields, invalid email format, invalid phone format, invalid datetime format, or invalid enum value.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud contiene errores.",
  "details": {
    "phone": ["El formato del telefono no es valido. Use formato E.164, ej: +573001234567."],
    "email": ["El email no tiene un formato valido."]
  }
}
```

#### 403 Forbidden
**When:** Tenant has `public_booking_enabled = false` in settings.

**Example:**
```json
{
  "error": "booking_disabled",
  "message": "La clinica no tiene habilitado el agendamiento en linea."
}
```

#### 404 Not Found
**When:** `tenant_slug` does not match any active tenant, or `doctor_id` does not belong to the resolved tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "La clinica o el doctor seleccionado no fue encontrado."
}
```

#### 409 Conflict
**When:** The selected time slot is no longer available (concurrency collision — slot taken between availability check and booking).

**Example:**
```json
{
  "error": "slot_unavailable",
  "message": "El horario seleccionado ya no está disponible. Por favor selecciona otro horario."
}
```

#### 422 Unprocessable Entity
**When:** CAPTCHA token verification fails, slot is outside doctor's working hours, or start_time is in the past or below minimum advance booking time configured by clinic.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "No se pudo completar el agendamiento.",
  "details": {
    "captcha_token": ["La verificacion CAPTCHA fallo. Por favor intenta de nuevo."],
    "start_time": ["La cita debe agendarse con al menos 2 horas de anticipacion."]
  }
}
```

#### 429 Too Many Requests
**When:** IP has exceeded 10 public bookings per hour. See `infra/rate-limiting.md`.

**Example:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Has realizado demasiados intentos. Por favor espera antes de intentar de nuevo.",
  "retry_after_seconds": 1800
}
```

#### 500 Internal Server Error
**When:** Unexpected database failure, CAPTCHA provider timeout, or notification dispatch failure.

---

## Business Logic

**Step-by-step process:**

1. Validate `Content-Type: application/json` header present. Validate body against Pydantic schema.
2. Check IP-based rate limit via Redis: key `dentalos:rl:public_booking:{ip}`. If exceeded, return 429.
3. Resolve tenant from `tenant_slug`: query `public` schema `tenants` table `WHERE slug = :tenant_slug AND is_active = true`. If not found, return 404.
4. Check `tenant.settings.public_booking_enabled`. If false, return 403.
5. Verify CAPTCHA token by calling CAPTCHA provider verification endpoint (hCaptcha or reCAPTCHA v3). If token is invalid or score below threshold (0.5 for reCAPTCHA v3), return 422.
6. Set `search_path` to resolved tenant schema for all subsequent queries.
7. Validate `doctor_id` exists in `users` table with `role = 'doctor'` and `is_active = true` within the tenant. If not, return 404.
8. Load `tenant.settings.min_advance_booking_hours` (default: 2). Validate that `start_time >= now() + min_advance_hours`. If not, return 422.
9. Validate `start_time` falls within doctor's working hours: load doctor schedule from cache or DB. Check day_of_week and time window. Emergency type bypasses this check. If outside hours, return 422.
10. Check for conflicting appointments: `SELECT id FROM appointments WHERE doctor_id = :doctor_id AND status IN ('scheduled','confirmed','in_progress') AND start_time < :computed_end_time AND end_time > :start_time`. If conflict, return 409.
11. Auto-calculate `end_time` from `service_type` duration defaults: consultation=30min, procedure=60min, emergency=30min, follow_up=20min. Use doctor's custom defaults if configured.
12. Check if patient exists: search `patients` table `WHERE (document_number = :document_number AND document_type = :document_type) OR (email = :email AND phone = :phone)`. Use first match. If no match found, create new patient record with `status = 'active'`, `source = 'online_booking'`.
13. Generate short confirmation code: `APPT-{random 4-char alphanumeric uppercase}`. Verify uniqueness in `appointments` table (retry up to 3 times on collision).
14. Insert appointment record with `status = 'scheduled'`, `source = 'online_booking'`, `created_by = NULL` (no auth user), `confirmation_code = generated_code`.
15. Increment IP rate limit counter in Redis: `INCR dentalos:rl:public_booking:{ip}` with TTL 3600s.
16. Write audit log: action `create`, resource `appointment`, `source = online_booking`, tenant_id, patient_id.
17. Dispatch notification jobs to RabbitMQ: confirmation email and WhatsApp (if configured).
18. Invalidate doctor availability cache for the affected date.
19. Load clinic info (name, address, phone) from tenant settings for response.
20. Return 201 with confirmation details.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| doctor_id | Valid UUID, must belong to resolved tenant with role=doctor | La clinica o el doctor seleccionado no fue encontrado. |
| start_time | ISO 8601 datetime with timezone, >= now() + min_advance_hours | La cita debe agendarse con anticipacion suficiente. |
| service_type | Enum: consultation, procedure, emergency, follow_up | Tipo de cita no valido. |
| first_name | Non-empty string, max 100 chars, no numeric only | El nombre es requerido. |
| last_name | Non-empty string, max 100 chars | El apellido es requerido. |
| phone | E.164 format regex `^\+[1-9]\d{7,14}$` | Formato de telefono invalido. Usa formato E.164. |
| email | RFC 5322 compliant, max 254 chars | El email no tiene formato valido. |
| document_type | Enum: cc, ti, ce, passport, nit (if provided) | Tipo de documento invalido. |
| document_number | Alphanumeric, max 20 chars (if provided) | Numero de documento invalido. |
| notes | Max 500 chars (if provided) | Las notas no pueden superar 500 caracteres. |
| captcha_token | Non-empty string; must pass provider verification | La verificacion CAPTCHA fallo. |

**Business Rules:**

- This is a public endpoint — no JWT is required or accepted. Tenant is resolved solely from `tenant_slug`.
- If a patient with matching document_number+document_type or email+phone combination already exists, the booking is linked to that patient. No new patient record is created.
- If no match is found, a new patient record is created with `source = 'online_booking'` for staff follow-up.
- The `service_type` field maps to appointment `type` in the internal model (consultation, procedure, emergency, follow_up).
- Confirmation codes are short (APPT-XXXX), human-readable, and tenant-unique. They are shown on the booking confirmation page and included in the notification email/WhatsApp.
- The minimum advance booking time (`min_advance_booking_hours`) is configured per clinic in AP-16/AP-18 settings. Default is 2 hours.
- If CAPTCHA provider is unavailable (network timeout), the request is rejected with 422 to prevent bypass. CAPTCHA provider calls timeout after 3 seconds.
- Emergency type self-bookings via public link are technically allowed but the slot conflict check is still enforced (unlike internal staff bookings).
- Patient data collected via this endpoint must be stored with `gdpr_consent = true` implied by form submission.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient already exists with same email and different phone | Match by email; link to existing patient; do not create duplicate |
| Two concurrent requests for the same slot | One succeeds (201), the other gets 409 after overlap check |
| Doctor has no configured schedule | Reject if start_time cannot be validated; use clinic business hours as fallback |
| Tenant slug exists but tenant is inactive | Return 404 (treat same as not found to avoid tenant enumeration) |
| CAPTCHA provider returns score 0.3 (reCAPTCHA v3, low confidence) | Return 422 with CAPTCHA failure message |
| `document_number` provided but patient exists with same doc but different document_type | Not a match; proceed with email/phone lookup |
| `min_advance_booking_hours = 0` configured by clinic | Allow bookings for any future time including within the next hour |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: INSERT — new appointment with `source = 'online_booking'`, `status = 'scheduled'`, `created_by = NULL`
- `patients`: INSERT (conditional) — new patient record if no existing match; `source = 'online_booking'`
- `audit_logs`: INSERT — booking event with tenant_id and patient_id

**Public schema tables affected:**
- None — tenant resolution only reads from `public.tenants`

**Example query (SQLAlchemy):**
```python
# Patient upsert logic
existing_patient = await session.execute(
    select(Patient).where(
        or_(
            and_(
                Patient.document_number == data.document_number,
                Patient.document_type == data.document_type,
                data.document_number.isnot(None),
            ),
            and_(
                Patient.email == data.email,
                Patient.phone == data.phone,
            ),
        )
    ).limit(1)
)
patient = existing_patient.scalar_one_or_none()
patient_created = False
if patient is None:
    patient = Patient(
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        email=data.email,
        document_number=data.document_number,
        document_type=data.document_type,
        status="active",
        source="online_booking",
    )
    session.add(patient)
    await session.flush()
    patient_created = True

appointment = Appointment(
    patient_id=patient.id,
    doctor_id=data.doctor_id,
    start_time=data.start_time.astimezone(timezone.utc),
    end_time=computed_end_time,
    duration_minutes=duration,
    type=data.service_type,
    status=AppointmentStatus.SCHEDULED,
    notes=data.notes,
    source="online_booking",
    confirmation_code=confirmation_code,
    created_by=None,
)
session.add(appointment)
await session.flush()
```

### Cache Operations

**Cache keys affected:**
- `dentalos:rl:public_booking:{ip}`: INCR — rate limit counter per IP
- `tenant:{tenant_id}:availability:{doctor_id}:{date}`: INVALIDATE — availability slots for booked date
- `tenant:{tenant_id}:appointments:calendar:{doctor_id}:{date}`: INVALIDATE — calendar cache

**Cache TTL:** Rate limit key TTL = 3600s (1 hour sliding window)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | appointment.confirmation_email | { tenant_id, appointment_id, patient_id, email, confirmation_code, start_time, doctor_name, clinic_name } | After successful insert |
| notifications | appointment.confirmation_whatsapp | { tenant_id, appointment_id, patient_id, phone, confirmation_code, start_time, doctor_name } | After successful insert, if WhatsApp enabled for tenant |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** create
- **Resource:** appointment
- **PHI involved:** Yes — patient name, phone, email collected

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | public_booking_confirmation | patient (email from request) | On successful booking |
| whatsapp | public_booking_confirmation_wa | patient (phone from request) | On successful booking if tenant has WhatsApp enabled |
| in-app | appointment_new | clinic staff (clinic_owner, receptionist) | On successful booking so staff is notified of new online booking |

---

## Performance

### Expected Response Time
- **Target:** < 500ms
- **Maximum acceptable:** < 1500ms (includes CAPTCHA verification external call)

### Caching Strategy
- **Strategy:** No response caching (write operation). Doctor availability read from cache if warm.
- **Cache key:** `tenant:{tenant_id}:availability:{doctor_id}:{date}` (read-through)
- **TTL:** N/A for write path
- **Invalidation:** Invalidates availability and calendar caches for affected doctor/date on booking

### Database Performance

**Queries executed:** 5-6 (tenant lookup, doctor validation, schedule load, overlap check, patient upsert, appointment insert)

**Indexes required:**
- `tenants.slug` — UNIQUE INDEX (public schema)
- `appointments.(doctor_id, start_time, end_time, status)` — COMPOSITE INDEX for overlap query
- `patients.(document_number, document_type)` — COMPOSITE INDEX for patient lookup
- `patients.(email, phone)` — COMPOSITE INDEX for patient lookup fallback
- `appointments.confirmation_code` — UNIQUE INDEX per tenant

**N+1 prevention:** Patient lookup uses single query with OR condition. Doctor info eagerly loaded with single JOIN for response.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| tenant_slug | Pydantic regex `^[a-z0-9-]{1,63}$` | Prevents path traversal |
| doctor_id | Pydantic UUID validator | Rejects non-UUID strings |
| start_time | Pydantic datetime with timezone | ISO 8601 strict |
| first_name, last_name | Pydantic strip() + bleach.clean(), max_length=100 | No HTML allowed |
| phone | Pydantic regex E.164 | Strict format enforcement |
| email | Pydantic EmailStr validator | RFC 5322 |
| notes | Pydantic strip() + bleach.clean(), max_length=500 | Free text, sanitized |
| captcha_token | Non-empty string, verified server-side | Never logged or stored |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization. `bleach.clean()` applied to all user-supplied free text before storage.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API. CAPTCHA provides bot protection for public endpoint.

### Data Privacy (PHI)

**PHI fields in this endpoint:** first_name, last_name, phone, email, document_number, notes (may contain clinical reasons)

**Audit requirement:** All write operations logged with PHI flag. Patient contact info not included in structured logs — only patient_id and tenant_id after record creation.

### Additional Security Notes

- `tenant_slug` must not reveal tenant internal IDs — return generic 404 for both missing and inactive tenants to prevent enumeration.
- CAPTCHA token is verified server-side only; never passed to database.
- IP address is extracted from `X-Forwarded-For` only when set by trusted load balancer (configurable list of trusted proxies).
- `confirmation_code` is short but sufficiently random (4 chars from base-36 = ~1.7M combinations per tenant) for human use. It is not a security token — full `appointment_id` UUID is the authoritative reference.

---

## Testing

### Test Cases

#### Happy Path
1. New patient self-booking with full data
   - **Given:** Active tenant with public_booking_enabled=true, valid doctor working Monday-Friday, slot free at 10:00, valid CAPTCHA token
   - **When:** POST /api/v1/public/booking/clinica-san-jose with all required fields
   - **Then:** 201 Created, `patient_created = true`, confirmation_code starts with APPT-, availability cache invalidated

2. Returning patient self-booking matched by email+phone
   - **Given:** Patient with email `laura@email.com` and phone `+573158765432` already exists in tenant
   - **When:** POST with same email and phone
   - **Then:** 201 Created, `patient_created = false`, appointment linked to existing patient

3. Returning patient matched by document_number
   - **Given:** Patient with CC `1032456789` exists in tenant
   - **When:** POST with same document_number and document_type=cc
   - **Then:** 201 Created, `patient_created = false`

#### Edge Cases
1. Two concurrent requests for the same slot
   - **Given:** Slot at 10:00 is free, two simultaneous POST requests
   - **When:** Both requests processed
   - **Then:** First to commit gets 201; second gets 409 slot_unavailable

2. Booking exactly at minimum advance time boundary
   - **Given:** `min_advance_booking_hours = 2`, current time is 08:00
   - **When:** POST with start_time = 10:00 (exactly 2h ahead)
   - **Then:** 201 Created (boundary is inclusive)

3. Tenant has public_booking_enabled=false
   - **Given:** Tenant setting `public_booking_enabled = false`
   - **When:** POST to tenant's public booking endpoint
   - **Then:** 403 Forbidden with booking_disabled error

#### Error Cases
1. Invalid CAPTCHA token
   - **Given:** Valid request body but `captcha_token = "invalid_token"`
   - **When:** POST with invalid token
   - **Then:** 422 with captcha_token validation error

2. Rate limit exceeded
   - **Given:** IP has already made 10 bookings in the past hour
   - **When:** 11th POST from same IP
   - **Then:** 429 Too Many Requests with retry_after_seconds

3. Slot taken (409 conflict)
   - **Given:** Doctor has confirmed appointment at 10:00-10:30
   - **When:** POST with start_time=10:15, service_type=consultation
   - **Then:** 409 Conflict with slot_unavailable

4. Unknown tenant slug
   - **Given:** POST to `/api/v1/public/booking/nonexistent-clinic`
   - **When:** Request sent
   - **Then:** 404 Not Found

5. start_time in the past
   - **Given:** start_time = yesterday
   - **When:** POST
   - **Then:** 422 validation error on start_time

### Test Data Requirements

**Tenants:** One active tenant with `public_booking_enabled=true`, slug `clinica-san-jose`; one with `public_booking_enabled=false`

**Doctors:** One active doctor with working hours Monday-Friday 08:00-17:00; one doctor not working on weekends

**Patients:** One existing patient with known email+phone; one with known document_number

**Appointments:** One confirmed appointment to test conflict scenario

### Mocking Strategy

- CAPTCHA provider: Mock HTTP client; simulate success (score 0.9), failure (score 0.2), and timeout
- Redis: Use `fakeredis` for rate limit counter simulation
- RabbitMQ: Mock publish; assert correct job types dispatched with expected payloads
- Doctor schedule: Seed `doctor_schedules` table with known working days

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/public/booking/{tenant_slug} returns 201 with confirmation_code
- [ ] New patient record created when no match found
- [ ] Existing patient matched by document or email+phone without creating duplicate
- [ ] CAPTCHA verification enforced — invalid token returns 422
- [ ] IP rate limit of 10/hour enforced — 11th request returns 429
- [ ] Slot conflict returns 409 (including under concurrent load)
- [ ] Clinic with public_booking_enabled=false returns 403
- [ ] Minimum advance booking time enforced per clinic configuration
- [ ] Confirmation email and WhatsApp jobs dispatched to RabbitMQ
- [ ] Audit log written with PHI flag
- [ ] Availability and calendar caches invalidated for affected doctor/date
- [ ] All test cases pass
- [ ] Performance targets met (< 1500ms including CAPTCHA call)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Authenticated booking by logged-in patients via the patient portal (see portal specs)
- Recurring appointment self-booking
- Group booking (multiple patients at once)
- SMS confirmation (handled by notification worker consuming the RabbitMQ job)
- Booking page UI/frontend (see frontend specs)
- Booking configuration management (see AP-16, AP-17, AP-18)
- Payment collection at time of booking (post-MVP)
- Cancellation by patient via public link (separate spec)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (public, no JWT, CAPTCHA)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (appointments domain)
- [x] Uses tenant schema isolation (resolved from slug)
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (public with CAPTCHA + IP rate limit)
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for PHI collection

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 1500ms)
- [x] Caching strategy stated (availability cache read-through, invalidated on write)
- [x] DB queries optimized (indexes listed)
- [x] Pagination N/A

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included, no PHI in logs)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for CAPTCHA, Redis, RabbitMQ
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
