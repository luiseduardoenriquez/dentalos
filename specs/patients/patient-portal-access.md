# P-11 Patient Portal Access (Grant/Revoke) Spec

---

## Overview

**Feature:** Grant or revoke patient portal access. On grant: creates a portal_user_id, sends an invitation via email and/or WhatsApp with a registration link. On revoke: deactivates portal access and revokes all active portal tokens.

**Domain:** patients

**Priority:** High

**Dependencies:** P-01 (patient-create.md), portal/portal-auth.md, notifications/email-service.md, notifications/whatsapp-service.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist can grant/revoke portal access as part of front-desk operations. The patient must have at least an email or phone to receive the invitation.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/portal-access
```

**Rate Limiting:**
- 30 requests per hour per user (to prevent invitation spam)

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
| patient_id | Yes | UUID | Valid UUIDv4 | Target patient identifier | 550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "action": "string (required) — 'grant' or 'revoke'",
  "invitation_channel": "string (optional, for grant) — 'email', 'whatsapp', 'both'. Default: auto-detect"
}
```

**Example Request (grant):**
```json
{
  "action": "grant",
  "invitation_channel": "both"
}
```

**Example Request (revoke):**
```json
{
  "action": "revoke"
}
```

---

## Response

### Success Response (Grant)

**Status:** 200 OK

```json
{
  "message": "Acceso al portal otorgado exitosamente. Se ha enviado la invitacion al paciente.",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "portal_user_id": "770a0622-a4b1-63f6-c938-668877662222",
  "portal_access": true,
  "invitation_sent_via": ["email", "whatsapp"],
  "invitation_expires_at": "2025-11-22T14:30:00-05:00"
}
```

### Success Response (Revoke)

**Status:** 200 OK

```json
{
  "message": "Acceso al portal revocado exitosamente.",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "portal_user_id": null,
  "portal_access": false,
  "tokens_revoked": 2
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid action value, or patient lacks email/phone for invitation delivery.

```json
{
  "error": "invalid_input",
  "message": "El paciente no tiene email ni telefono registrado. Se requiere al menos uno para enviar la invitacion.",
  "details": { "missing": ["email", "phone"] }
}
```

#### 401 Unauthorized
**When:** Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not clinic_owner or receptionist.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para gestionar el acceso al portal de pacientes."
}
```

#### 404 Not Found
**When:** patient_id does not exist or is inactive in the current tenant.

```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 409 Conflict
**When:** Trying to grant access to a patient who already has portal access, or revoke from one who does not.

```json
{
  "error": "conflict",
  "message": "El paciente ya tiene acceso al portal activo."
}
```

#### 422 Unprocessable Entity
**When:** Invitation channel requested but patient lacks the corresponding contact info.

```json
{
  "error": "validation_failed",
  "message": "No se puede enviar invitacion por WhatsApp. El paciente no tiene telefono registrado.",
  "details": { "invitation_channel": ["whatsapp requiere telefono registrado."] }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

---

## Business Logic

**Step-by-step process (Grant):**

1. Validate JWT and extract tenant context; verify role in [clinic_owner, receptionist].
2. Validate request body via Pydantic.
3. Load patient from DB; return 404 if not found or inactive.
4. Check patient.portal_access is false; return 409 if already active.
5. Determine invitation channel:
   - If `invitation_channel` is "auto" or omitted: use email if available, add whatsapp if phone available.
   - If "email": require patient.email; return 422 if null.
   - If "whatsapp": require patient.phone; return 422 if null.
   - If "both": require both; return 422 if either is null.
6. If no email and no phone at all, return 400.
7. Generate portal_user_id (UUIDv4).
8. Generate a secure invitation token (32-byte random, hashed for storage).
9. Build registration URL: `https://{tenant_slug}.dentalos.app/portal/register?token={token}`.
10. UPDATE patient: set portal_user_id, portal_access=true, updated_at=now().
11. Store invitation token with 7-day expiry in portal_invitations table.
12. Dispatch invitation notifications via RabbitMQ (email and/or WhatsApp).
13. Write audit log entry: action=update, resource_type=patient_portal_access, new_value={portal_access: true}.
14. Return success response.

**Step-by-step process (Revoke):**

1. Validate JWT and extract tenant context; verify role in [clinic_owner, receptionist].
2. Validate request body via Pydantic.
3. Load patient from DB; return 404 if not found or inactive.
4. Check patient.portal_access is true; return 409 if already revoked.
5. Revoke all active portal sessions/tokens for this portal_user_id.
6. UPDATE patient: set portal_user_id=null, portal_access=false, updated_at=now().
7. Delete any pending invitation tokens for this patient.
8. Invalidate portal user cache.
9. Write audit log entry: action=update, resource_type=patient_portal_access, new_value={portal_access: false}.
10. Return success response with count of tokens revoked.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUIDv4 | "El ID del paciente no es un UUID valido." |
| action | Must be 'grant' or 'revoke' | "Accion no valida. Use 'grant' o 'revoke'." |
| invitation_channel | Must be 'email', 'whatsapp', or 'both' if provided | "Canal de invitacion no valido." |

**Business Rules:**

- Portal access requires the `patient_portal` feature enabled in the tenant's plan.
- Invitation links expire after 7 days.
- A patient can only have one active portal account at a time.
- On revoke, ALL portal sessions are immediately terminated.
- If the patient has never completed portal registration (only invited), grant can be re-issued after a previous revoke.
- WhatsApp invitations use a pre-approved message template.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has email but no phone, channel=both | Return 422 asking to use channel=email. |
| Portal feature not in tenant plan | Return 403 with: "El plan actual no incluye el portal de pacientes." |
| Re-granting after a previous revoke | Allowed; generates new portal_user_id and fresh invitation. |
| Patient registered but grant re-issued | Return 409: already has active portal access. |
| Invitation already sent but expired | Grant can be re-issued; old token is overwritten. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `patients`: UPDATE portal_user_id, portal_access, updated_at.
- `audit_log`: INSERT — portal access change audit entry.

**Portal invitation tracking (tenant schema extension):**
```sql
CREATE TABLE portal_invitations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL,
    channel         VARCHAR(15) NOT NULL CHECK (channel IN ('email', 'whatsapp')),
    status          VARCHAR(15) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'sent', 'accepted', 'expired')),
    expires_at      TIMESTAMPTZ NOT NULL,
    sent_at         TIMESTAMPTZ,
    accepted_at     TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_portal_invitations_patient ON portal_invitations (patient_id);
CREATE INDEX idx_portal_invitations_token ON portal_invitations (token_hash);
CREATE INDEX idx_portal_invitations_expires ON portal_invitations (expires_at) WHERE status = 'pending';
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}`: INVALIDATE — patient record changed.
- `tenant:{tenant_id}:portal_user:{portal_user_id}`: DELETE (on revoke).

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | portal_invitation_email | { tenant_id, patient_id, email, registration_url, clinic_name, expires_at } | On grant, if email channel selected |
| notifications | portal_invitation_whatsapp | { tenant_id, patient_id, phone, registration_url, clinic_name, expires_at } | On grant, if whatsapp channel selected |

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** patient_portal_access
- **PHI involved:** No (portal access status is not PHI)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | portal_invitation | patient | On grant (if email available) |
| whatsapp | portal_invitation | patient | On grant (if phone available) |

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Cache invalidation on portal access change.
- **Cache key:** Patient record cache + portal user cache.
- **TTL:** N/A
- **Invalidation:** Immediate on grant/revoke.

### Database Performance

**Queries executed:** 3-4 (load patient, update patient, insert invitation, audit log).

**Indexes required:**
- `patients.id` — PRIMARY KEY (existing)
- `portal_invitations.patient_id` — INDEX
- `portal_invitations.token_hash` — INDEX

**N+1 prevention:** Not applicable (single patient operation).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID |
| action | Pydantic enum validator | Only grant/revoke |
| invitation_channel | Pydantic enum validator | Only allowed values |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Patient email and phone are used for invitation delivery but not exposed in logs.

**Audit requirement:** Write-only logged (portal access changes).

---

## Testing

### Test Cases

#### Happy Path
1. Grant portal access via email
   - **Given:** Active patient with email, no current portal access.
   - **When:** POST with action=grant, invitation_channel=email.
   - **Then:** Returns 200, portal_access=true, portal_user_id generated, email job queued.

2. Revoke portal access
   - **Given:** Patient with active portal access and 2 sessions.
   - **When:** POST with action=revoke.
   - **Then:** Returns 200, portal_access=false, tokens_revoked=2.

3. Grant via both channels
   - **Given:** Patient with both email and phone.
   - **When:** POST with action=grant, invitation_channel=both.
   - **Then:** Both email and WhatsApp jobs dispatched.

#### Edge Cases
1. Auto-detect channel (email only)
   - **Given:** Patient with email but no phone.
   - **When:** POST with action=grant (no channel specified).
   - **Then:** Invitation sent via email only.

2. Re-grant after revoke
   - **Given:** Patient previously had access, was revoked.
   - **When:** POST with action=grant.
   - **Then:** New portal_user_id generated, fresh invitation sent.

#### Error Cases
1. Grant to patient without contact info
   - **Given:** Patient with null email and null phone.
   - **When:** POST with action=grant.
   - **Then:** Returns 400.

2. Grant to patient already with access
   - **Given:** Patient with portal_access=true.
   - **When:** POST with action=grant.
   - **Then:** Returns 409.

3. Portal feature not in plan
   - **Given:** Tenant plan without patient_portal feature.
   - **When:** POST with action=grant.
   - **Then:** Returns 403.

### Test Data Requirements

**Users:** 1 clinic_owner, 1 receptionist, 1 doctor (for 403 test).

**Patients/Entities:** 1 patient with email+phone (no portal), 1 with portal active, 1 with email only, 1 with neither.

### Mocking Strategy

- RabbitMQ: Mock publisher; verify message payloads for email/whatsapp.
- Token generation: Mock random bytes for deterministic testing.
- Plan features: Mock tenant plan to test feature flag.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Grant creates portal_user_id and sets portal_access=true
- [ ] Invitation sent via configured channel(s) (email and/or WhatsApp)
- [ ] Registration URL contains valid, expiring token
- [ ] Revoke deactivates portal access and revokes all tokens/sessions
- [ ] Plan feature check enforced (patient_portal must be enabled)
- [ ] Proper conflict detection (409 for duplicate grant/revoke)
- [ ] Audit log entries created for both actions
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Portal user registration flow (covered in portal/portal-registration.md).
- Portal authentication (login, password reset) — covered in portal/portal-auth.md.
- Portal features and patient-facing UI — covered in portal domain specs.
- Bulk grant/revoke for multiple patients (future enhancement).

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
- [x] Audit trail for access changes

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (notification jobs)

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
