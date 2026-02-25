# Consent Void Spec

---

## Overview

**Feature:** Void a signed or draft informed consent form. Voiding is strictly for error correction (e.g., wrong patient, wrong procedure). The original consent record is NEVER deleted — it is marked as `voided` with a mandatory reason. A full audit trail is created. Only clinic_owner can void consents.

**Domain:** consents

**Priority:** High

**Dependencies:** IC-05 (consent-sign.md), IC-06 (consent-get.md), auth/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner ONLY
- **Tenant context:** Required — resolved from JWT
- **Special rules:** No other role can void a consent. Doctors, assistants, and patients cannot void consents under any circumstances.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/consents/{consent_id}/void
```

**Rate Limiting:**
- 10 requests per hour per user
- Voiding is an exceptional action; very low rate limit intentional

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
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient owning the consent | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| consent_id | Yes | string (UUID) | Valid UUID v4, must belong to patient | Consent to void | c3d4e5f6-0000-4000-8000-000000000030 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "reason": "string (required) — mandatory justification for voiding; min 20 chars, max 1000 chars"
}
```

**Example Request:**
```json
{
  "reason": "Consentimiento creado para paciente incorrecto por error de sistema. El procedimiento fue realizado para la paciente Maria Garcia Lopez (cedula 1020304050) y no para el paciente registrado en este consentimiento."
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "consent_id": "uuid",
  "patient_id": "uuid",
  "status": "voided",
  "void_reason": "string",
  "voided_by": "uuid",
  "voided_at": "string (ISO 8601 datetime)",
  "previous_status": "string (draft | pending_signatures | signed)"
}
```

**Example:**
```json
{
  "consent_id": "c3d4e5f6-0000-4000-8000-000000000030",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "voided",
  "void_reason": "Consentimiento creado para paciente incorrecto por error de sistema. El procedimiento fue realizado para la paciente Maria Garcia Lopez (cedula 1020304050) y no para el paciente registrado en este consentimiento.",
  "voided_by": "e5f6a7b8-0000-4000-8000-000000000099",
  "voided_at": "2026-02-24T16:00:00Z",
  "previous_status": "signed"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or reason field is missing.

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

#### 403 Forbidden
**When:** User role is not `clinic_owner`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede anular consentimientos."
}
```

#### 404 Not Found
**When:** `patient_id` or `consent_id` not found in tenant, or `consent_id` does not belong to `patient_id`.

**Example:**
```json
{
  "error": "not_found",
  "message": "Consentimiento no encontrado."
}
```

#### 409 Conflict
**When:** Consent is already voided.

**Example:**
```json
{
  "error": "already_voided",
  "message": "Este consentimiento ya fue anulado el 2026-02-20T10:00:00Z.",
  "details": {
    "voided_at": "2026-02-20T10:00:00Z",
    "voided_by": "e5f6a7b8-0000-4000-8000-000000000099"
  }
}
```

#### 422 Unprocessable Entity
**When:** `reason` does not meet minimum length requirement.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "reason": ["La razon de anulacion debe tener al menos 20 caracteres."]
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

1. Validate input against Pydantic schema (`reason` length and format).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role — must be `clinic_owner`. Return 403 for any other role.
4. Verify `patient_id` exists in tenant. Return 404 if not.
5. Fetch consent by `consent_id` and verify `consent.patient_id == patient_id`. Return 404 if not found or mismatched.
6. Check consent status — if already `voided`, return 409 with existing void details.
7. Record `previous_status` for audit and response.
8. Update consent record:
   - `status` → `voided`
   - `void_reason` → sanitized reason text
   - `voided_by` → current user ID (JWT sub)
   - `voided_at` → server-side UTC timestamp
9. Write dedicated audit log entry with `action: void`, including the `reason` text.
10. Invalidate patient consent list and detail caches.
11. Dispatch `consent.voided` event to RabbitMQ.
12. Return 200 with void confirmation.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| consent_id | Valid UUID v4 | El identificador del consentimiento no es valido. |
| reason | Required, minimum 20 chars | La razon de anulacion debe tener al menos 20 caracteres. |
| reason | Maximum 1000 chars | La razon de anulacion no puede exceder 1000 caracteres. |
| reason | Cannot be blank after stripping whitespace | La razon de anulacion no puede estar vacia. |

**Business Rules:**

- The original consent record is NEVER deleted. Only the `status` column changes to `voided`. All content, signatures, and metadata are preserved indefinitely.
- A voided consent is a permanent part of the legal record. It cannot be "un-voided".
- A voided signed consent does NOT invalidate any medical procedure that was performed — it only indicates the paperwork had an error.
- If a voided consent's procedure still needs proper documentation, a new consent should be created (separate workflow).
- The `voided_at` timestamp is always set server-side; it cannot be specified by the client.
- `void_reason` is stored in the consent record AND in the audit log (duplicated for legal traceability).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Void a draft consent | Allowed; consent transitions from draft to voided |
| Void a pending_signatures consent | Allowed; consent transitions from pending_signatures to voided |
| Void an already-voided consent | Return 409 with existing void details |
| `reason` is exactly 20 characters | Accept |
| `reason` is 19 characters | Reject 422 |
| clinic_owner voids a consent they created | Allowed (no self-conflict restriction) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `consents`: UPDATE — set `status = voided`, `void_reason`, `voided_by`, `voided_at`

**Example query (SQLAlchemy):**
```python
await session.execute(
    update(Consent)
    .where(Consent.id == consent_id, Consent.patient_id == patient_id)
    .values(
        status=ConsentStatus.VOIDED,
        void_reason=sanitized_reason,
        voided_by=current_user.id,
        voided_at=datetime.utcnow(),
    )
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:{patient_id}:consents:list:*`: INVALIDATE
- `tenant:{tenant_id}:patients:{patient_id}:consents:{consent_id}`: INVALIDATE

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| consents | consent.voided | { tenant_id, consent_id, patient_id, voided_by, void_reason, previous_status } | After successful void |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** void
- **Resource:** consent
- **PHI involved:** Yes (consent content references patient PHI; void_reason may contain PHI references)

**Additional audit fields:**
- `void_reason`: included verbatim in audit record
- `previous_status`: included to show what status was changed from
- `voided_by_role`: `clinic_owner` (recorded for legal accountability)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | consent_voided_alert | Treating doctor (who created the consent) | On consent.voided |
| email | consent_voided_notification | clinic_owner (confirmation) | On consent.voided |

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on void (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Consent list and detail caches invalidated on void

### Database Performance

**Queries executed:** 3 (patient lookup, consent lookup, consent UPDATE)

**Indexes required:**
- `{tenant}.consents.(patient_id, id)` — COMPOSITE INDEX (already required)
- `{tenant}.consents.status` — INDEX (already required)

**N+1 prevention:** Not applicable (single row update)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| reason | Pydantic `strip()` + bleach.clean (strip_tags) | Free text stored in legal audit record |
| patient_id | Pydantic UUID validator | Reject malformed path params |
| consent_id | Pydantic UUID validator | Reject malformed path params |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** `void_reason` sanitized via bleach on input. Pydantic serialization on output.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** void_reason (may contain patient names, procedure references), consent content (preserved, not modified)

**Audit requirement:** All access logged with full `void_reason` text in audit record (legal requirement).

---

## Testing

### Test Cases

#### Happy Path
1. Void a signed consent
   - **Given:** Authenticated clinic_owner, signed consent
   - **When:** POST /api/v1/patients/{patient_id}/consents/{consent_id}/void with valid reason (>= 20 chars)
   - **Then:** 200 OK, status=voided, previous_status=signed, void_reason stored, voided_at set

2. Void a draft consent
   - **Given:** Authenticated clinic_owner, draft consent
   - **When:** POST with valid reason
   - **Then:** 200 OK, status=voided, previous_status=draft

3. Void a pending_signatures consent
   - **Given:** Authenticated clinic_owner, pending_signatures consent
   - **When:** POST with valid reason
   - **Then:** 200 OK, status=voided, previous_status=pending_signatures

4. Audit log written with full void_reason
   - **Given:** clinic_owner voids consent
   - **When:** POST void
   - **Then:** Audit record created with action=void, PHI=true, void_reason included verbatim

#### Edge Cases
1. Reason is exactly 20 characters
   - **Given:** reason = "A" * 20 (20 chars)
   - **When:** POST void
   - **Then:** 200 OK

2. Reason contains HTML tags
   - **Given:** reason = "<b>Error de digitacion</b> en el nombre del paciente."
   - **When:** POST void
   - **Then:** 200 OK, HTML tags stripped by bleach, plain text stored

#### Error Cases
1. Doctor attempts to void
   - **Given:** User with doctor role
   - **When:** POST /api/v1/patients/{patient_id}/consents/{consent_id}/void
   - **Then:** 403 Forbidden

2. Assistant attempts to void
   - **Given:** User with assistant role
   - **When:** POST
   - **Then:** 403 Forbidden

3. Reason too short
   - **Given:** reason = "Error" (5 chars)
   - **When:** POST void
   - **Then:** 422 Unprocessable Entity with reason validation error

4. Void already voided consent
   - **Given:** Consent already has status=voided
   - **When:** POST void
   - **Then:** 409 Conflict with existing void details

5. Consent not found
   - **Given:** consent_id does not exist
   - **When:** POST void
   - **Then:** 404 Not Found

6. Consent belongs to different patient
   - **Given:** consent_id exists but belongs to different patient
   - **When:** POST with mismatched patient_id
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** clinic_owner (happy path); doctor, assistant, patient (negative tests)

**Patients/Entities:** Consent in each status (draft, pending_signatures, signed, already voided) for appropriate tests.

### Mocking Strategy

- Redis cache: Use fakeredis to verify cache invalidation
- RabbitMQ: Mock publish; assert `consent.voided` event dispatched with correct payload
- Audit log: Mock audit service; assert void_reason included in audit entry

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Consent record updated to `status: voided` with reason, voided_by, and voided_at
- [ ] Original consent record preserved (no deletion of any fields)
- [ ] `previous_status` returned in response for traceability
- [ ] Only `clinic_owner` can void consents (403 for all other roles)
- [ ] `reason` minimum 20 characters enforced (422 if shorter)
- [ ] Already-voided consent returns 409 with existing void info
- [ ] Audit log entry created with void_reason verbatim and PHI=true
- [ ] Patient consent list and detail caches invalidated
- [ ] `consent.voided` RabbitMQ event dispatched
- [ ] In-app notification sent to treating doctor
- [ ] All test cases pass
- [ ] Performance target met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Deleting consents (consents are NEVER deleted — preservation is a legal requirement)
- Un-voiding a consent (once voided, permanently voided)
- Creating a replacement consent after voiding (separate workflow using IC-04)
- Bulk voiding multiple consents
- Voiding consent templates

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
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (clinic_owner ONLY)
- [x] Input sanitization defined (bleach + Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation on void)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (void_reason included verbatim)
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
| 1.0 | 2026-02-24 | Initial spec |
