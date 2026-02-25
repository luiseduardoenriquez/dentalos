# Voice Capture Session Spec

> **Spec ID:** V-01
> **Status:** Draft
> **Last Updated:** 2026-02-24

---

## Overview

**Feature:** Creates a voice capture session scoped to a specific patient, establishing the context (odontogram, evolution, or notes) under which subsequent audio uploads will be transcribed and parsed. This is the entry point for the Voice-to-Odontogram pipeline, enabling dentists to dictate clinical findings hands-free instead of relying on manual data entry via a third-party channel.

**Domain:** voice

**Priority:** High

**Dependencies:** V-02 (voice-transcription.md), V-03 (voice-parse.md), V-04 (voice-apply.md), V-05 (voice-settings.md), I-01 (multi-tenancy.md), I-02 (database-architecture.md), auth/authentication-rules.md, patients/patient-get.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** The requesting user must have the target patient's record open (i.e., the patient must belong to the same tenant). Assistant role is allowed because in the clinic workflow the assistant operates the computer while the dentist dictates. Plan add-on check: the tenant must have the Voice feature add-on active (see V-05).

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/voice/sessions
```

**Rate Limiting:**
- 50 requests per hour per doctor (to control upstream Whisper API costs)
- Rate limit key: `voice:sessions:{user_id}` (per individual user, not per tenant)
- Exceeding the limit returns 429 with a `Retry-After` header

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
| patient_id | Yes | UUID v4 | Must exist in tenant, must be active | The patient for whom the session is being created | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "context": "string (required) — enum: odontogram | evolution | notes",
  "notes": "string (optional) — max 500 chars, free text about the session intent"
}
```

**Example Request:**
```json
{
  "context": "odontogram",
  "notes": "Evaluacion inicial dientes 30-40"
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "session_id": "uuid",
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "tenant_id": "string",
  "context": "string",
  "status": "string",
  "notes": "string | null",
  "expires_at": "string (ISO 8601 datetime)",
  "created_at": "string (ISO 8601 datetime)",
  "rate_limit": {
    "remaining": "integer",
    "reset_at": "string (ISO 8601 datetime)"
  }
}
```

**Example:**
```json
{
  "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "tenant_id": "tn_abc123",
  "context": "odontogram",
  "status": "open",
  "notes": "Evaluacion inicial dientes 30-40",
  "expires_at": "2026-02-24T15:30:00Z",
  "created_at": "2026-02-24T15:00:00Z",
  "rate_limit": {
    "remaining": 47,
    "reset_at": "2026-02-24T16:00:00Z"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or missing required fields.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 402 Payment Required
**When:** The tenant does not have the Voice add-on active in their subscription plan.

**Example:**
```json
{
  "error": "addon_required",
  "message": "La funcion de voz requiere el complemento de Voz activo. Contacte a su administrador para activarlo.",
  "details": {
    "addon": "voice",
    "upgrade_url": "/settings/billing/addons"
  }
}
```

#### 403 Forbidden
**When:** User role is not doctor or assistant.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para iniciar sesiones de voz."
}
```

#### 404 Not Found
**When:** The patient_id does not exist within the tenant or the patient is inactive.

**Example:**
```json
{
  "error": "patient_not_found",
  "message": "El paciente no fue encontrado o no esta activo.",
  "details": {
    "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }
}
```

#### 409 Conflict
**When:** The same user already has an open (non-expired) voice session for the same patient.

**Example:**
```json
{
  "error": "session_already_open",
  "message": "Ya existe una sesion de voz activa para este paciente. Finalice la sesion anterior antes de iniciar una nueva.",
  "details": {
    "existing_session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
    "expires_at": "2026-02-24T15:30:00Z"
  }
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails (invalid enum value for context).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "context": ["Contexto no valido. Opciones: odontogram, evolution, notes."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit of 50 sessions per hour per user exceeded. See `infra/rate-limiting.md`.

**Example:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Ha alcanzado el limite de 50 sesiones de voz por hora. Intente nuevamente mas tarde.",
  "details": {
    "limit": 50,
    "window": "1 hour",
    "reset_at": "2026-02-24T16:00:00Z"
  }
}
```

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema (context enum, notes length).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role via RBAC (must be doctor or assistant).
4. Check Voice add-on status: query `public.tenant_addons` where `tenant_id = :tid AND addon = 'voice' AND is_active = true`. If not found, return 402.
5. Verify patient exists and is active within the tenant: `SELECT id FROM patients WHERE id = :patient_id AND is_active = true`. If not found, return 404.
6. Check rate limit for the user: consult Redis key `voice:sessions:{user_id}`. If count >= 50, return 429 with `Retry-After`.
7. Check for existing open session: `SELECT id, expires_at FROM voice_sessions WHERE patient_id = :pid AND created_by = :uid AND status = 'open' AND expires_at > NOW()`. If found, return 409.
8. Compute `expires_at` as `NOW() + INTERVAL '30 minutes'` (inactivity expiry).
9. Insert `voice_sessions` record with `status = 'open'`, `context`, `patient_id`, `doctor_id` (current user), `tenant_id`.
10. Increment Redis rate limit counter: `INCR voice:sessions:{user_id}`, `EXPIRE` to end of current hour.
11. Write audit log entry (action: create, resource: voice_session, PHI: yes).
12. Return 201 with session details and remaining rate limit info.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| context | Must be one of: odontogram, evolution, notes | Contexto no valido. Opciones: odontogram, evolution, notes. |
| notes | Max 500 chars if provided | Las notas no pueden superar los 500 caracteres. |
| patient_id | Valid UUID v4, must exist in tenant, must be is_active = true | El paciente no fue encontrado o no esta activo. |

**Business Rules:**

- Only doctor and assistant roles can create voice sessions. clinic_owner cannot (they are administrative, not clinical).
- The `doctor_id` recorded on the session is always the JWT subject (`current_user.id`), regardless of role. If the assistant creates the session, it is still attributed to the assistant's user ID; the actual treating doctor is identified by the patient's assigned doctor in the patient record.
- A user can only have one open session per patient at a time. Multiple patients are allowed concurrently (e.g., assistant managing sessions for different exam rooms).
- Session expiry is based on inactivity: 30 minutes from creation. Any audio upload (V-02) resets the expiry clock.
- Rate limit (50/hour) is per user, not per tenant, to prevent a single heavy user from monopolizing API costs.
- Voice add-on check is performed at session creation. If the add-on lapses mid-session, audio uploads (V-02) will also perform the check.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient exists but is deactivated (is_active = false) | Return 404 (not 403) to avoid exposing deactivation status |
| User creates a session and then the add-on is revoked immediately | Session remains open; add-on is re-checked at audio upload time (V-02) |
| Expired session exists for the same patient | Ignore expired session; allow creating a new one (expired sessions are not "open") |
| notes field is null or absent | Accept; store as NULL |
| Two concurrent requests from the same user for the same patient (race condition) | Database unique partial index on (patient_id, created_by) WHERE status = 'open' prevents duplicate inserts; second request returns 409 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `voice_sessions`: INSERT — new voice capture session record

**Example query (SQLAlchemy):**
```python
from datetime import datetime, timezone, timedelta
import uuid

session_record = VoiceSession(
    id=uuid.uuid4(),
    patient_id=data.patient_id,
    created_by=current_user.id,
    context=data.context,
    notes=data.notes,
    status="open",
    expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
)
db_session.add(session_record)
await db_session.flush()
```

### Cache Operations

**Cache keys affected:**
- `voice:sessions:{user_id}`: INCREMENT — rate limit counter for the requesting user

**Cache TTL:** Remainder of the current clock hour (auto-set via Redis EXPIREAT to next hour boundary)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None at session creation. Jobs are dispatched on audio upload (V-02).

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** voice_session
- **PHI involved:** Yes (session is linked to a patient record)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No response caching (write operation). Redis used only for rate limit counters.
- **Cache key:** `voice:sessions:{user_id}`
- **TTL:** Remainder of current clock hour
- **Invalidation:** Counter resets automatically at hour boundary via Redis TTL

### Database Performance

**Queries executed:** 4 (add-on check, patient existence check, open session conflict check, insert)

**Indexes required:**
- `voice_sessions.(patient_id, created_by)` WHERE `status = 'open'` — PARTIAL UNIQUE INDEX (prevents duplicates, supports conflict check)
- `voice_sessions.created_by` — INDEX (supports rate limit lookups by user)
- `voice_sessions.expires_at` — INDEX (supports cleanup of expired sessions by maintenance worker)

**N+1 prevention:** Not applicable (single insert flow)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| context | Pydantic enum validator | Only allows odontogram, evolution, notes |
| notes | Pydantic `strip()` + bleach.clean | User-supplied free text, stored in DB |
| patient_id | Pydantic UUID validator | Must be valid UUID v4 |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id (links to patient clinical record), notes (may contain clinical intent language)

**Audit requirement:** All write access logged with tenant_id, user_id, patient_id, and session_id. No PHI is exposed in error messages or logs beyond identifiers.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor creates odontogram session for active patient
   - **Given:** Authenticated doctor, tenant with Voice add-on active, patient is active, no existing open session
   - **When:** POST /api/v1/patients/{patient_id}/voice/sessions with `{"context": "odontogram"}`
   - **Then:** 201 Created, session_id returned, expires_at is 30 minutes from now, status is "open"

2. Assistant creates evolution session with notes
   - **Given:** Authenticated assistant, Voice add-on active
   - **When:** POST with `{"context": "evolution", "notes": "Control post extraccion"}`
   - **Then:** 201 Created, notes stored correctly, doctor_id equals assistant's user_id

3. User creates session after previous one expired
   - **Given:** User had a session that expired 5 minutes ago
   - **When:** POST for same patient
   - **Then:** 201 Created (expired session is ignored)

#### Edge Cases
1. Rate limit boundary (49th request)
   - **Given:** User has made 49 sessions in the current hour
   - **When:** POST to create session 50
   - **Then:** 201 Created, rate_limit.remaining = 0

2. Concurrent duplicate requests (race condition)
   - **Given:** Two simultaneous requests from the same user for the same patient
   - **When:** Both requests arrive at the same millisecond
   - **Then:** One returns 201, the other returns 409 (enforced by DB partial unique index)

#### Error Cases
1. Voice add-on not active
   - **Given:** Tenant does not have Voice add-on enabled
   - **When:** POST /api/v1/patients/{patient_id}/voice/sessions
   - **Then:** 402 Payment Required with upgrade_url

2. Patient not found
   - **Given:** patient_id is a valid UUID but does not exist in the tenant
   - **When:** POST with that patient_id
   - **Then:** 404 Not Found

3. Existing open session conflict
   - **Given:** User already has an open session for the same patient
   - **When:** POST for same patient
   - **Then:** 409 Conflict with existing_session_id and expires_at

4. Rate limit exceeded
   - **Given:** User has made 50 sessions in the current hour
   - **When:** POST to create session 51
   - **Then:** 429 Too Many Requests with reset_at

5. Invalid context value
   - **Given:** `{"context": "radiografia"}`
   - **When:** POST
   - **Then:** 422 Unprocessable Entity with context validation error

6. Unauthorized role (patient trying to create)
   - **Given:** User with patient role
   - **When:** POST
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** doctor (primary), assistant, patient role user (for negative test), clinic_owner (for negative test)

**Patients/Entities:** Active patient, deactivated patient (for 404 test). Tenant with Voice add-on active, tenant without Voice add-on (for 402 test).

### Mocking Strategy

- Redis: Use fakeredis for rate limit counter tests
- Voice add-on check: Fixture with known add-on states (active/inactive)
- Database partial unique index: Tested with real PostgreSQL in integration tests (cannot mock uniqueness constraints reliably)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST creates a voice session returning 201 with session_id and expires_at
- [ ] Session expires_at is exactly 30 minutes from creation
- [ ] Voice add-on check returns 402 when add-on is not active
- [ ] Patient not found or inactive returns 404
- [ ] Existing open session for same user+patient returns 409 with existing session details
- [ ] Rate limit of 50/hour per user enforced; 51st request returns 429
- [ ] Rate limit remaining count returned in response
- [ ] Unauthorized roles return 403
- [ ] Audit log entry written with PHI flag
- [ ] Database partial unique index prevents duplicate open sessions under concurrent load
- [ ] All test cases pass
- [ ] Performance target met (< 150ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Audio upload and Whisper transcription (V-02)
- LLM parsing of transcription (V-03)
- Applying findings to odontogram (V-04)
- Voice settings configuration (V-05)
- Listing or closing voice sessions (future enhancement)
- Real-time WebSocket push for session status (future enhancement)
- Fine-tuning of Whisper or LLM models (out of scope for MVP)
- Mobile app recording; only browser MediaRecorder API is in scope

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
- [x] Follows service boundaries (domain separation — voice domain isolated)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md conventions

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced rate limit key)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A for create)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A for this endpoint)

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
| 1.0 | 2026-02-24 | Initial spec — Voice-to-Odontogram MVP |
