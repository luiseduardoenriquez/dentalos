# TP-10: Share Treatment Plan Spec

---

## Overview

**Feature:** Share a treatment plan with the patient via one or more channels: email (PDF attachment + portal link), WhatsApp (message with portal link), or portal notification. Generates a temporary access link (valid 7 days) for patients without a portal account. PDF generation is invoked automatically (TP-09) if not already cached.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** TP-09 (plan-pdf.md), TP-02 (plan-get.md), P-01 (patient-create.md), notifications domain, portal domain, I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist role is permitted to share plans as a front-desk workflow step (printing/sharing the plan after the consultation).

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/share
```

**Rate Limiting:**
- 10 requests per minute per user
- 3 share attempts per plan per hour (prevents spam to patient)

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
| patient_id | Yes | uuid | Valid UUID, must belong to tenant | Patient's unique identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| plan_id | Yes | uuid | Valid UUID, must belong to patient | Treatment plan's unique identifier | b2c3d4e5-f6a7-8901-bcde-f12345678901 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "channels": "string[] (required) — at least 1 item; allowed values: email, whatsapp, portal",
  "message": "string (optional) — custom message to include in the share notification, max 500 chars"
}
```

**Example Request (all channels):**
```json
{
  "channels": ["email", "whatsapp", "portal"],
  "message": "Estimada Maria, adjuntamos su plan de tratamiento. Si tiene preguntas no dude en contactarnos."
}
```

**Example Request (email only):**
```json
{
  "channels": ["email"]
}
```

**Example Request (WhatsApp only):**
```json
{
  "channels": ["whatsapp"]
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "plan_id": "uuid",
  "patient_id": "uuid",
  "channels_requested": "string[]",
  "channels_dispatched": "string[]",
  "channels_skipped": [
    {
      "channel": "string",
      "reason": "string"
    }
  ],
  "access_link": {
    "url": "string",
    "expires_at": "string (ISO 8601 datetime)"
  },
  "pdf_url": "string (S3 pre-signed URL, 1 hour TTL)",
  "shared_at": "string (ISO 8601 datetime)",
  "shared_by": "uuid"
}
```

**Example:**
```json
{
  "plan_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "channels_requested": ["email", "whatsapp", "portal"],
  "channels_dispatched": ["email", "portal"],
  "channels_skipped": [
    {
      "channel": "whatsapp",
      "reason": "WhatsApp no configurado para esta clinica."
    }
  ],
  "access_link": {
    "url": "https://app.dentalos.com/p/plan/tk_a1b2c3d4e5f6...",
    "expires_at": "2026-03-03T14:00:00Z"
  },
  "pdf_url": "https://s3.amazonaws.com/dental-os-docs/pdfs/.../plan.pdf?X-Amz-Expires=3600",
  "shared_at": "2026-02-24T14:00:00Z",
  "shared_by": "d4e5f6a1-b2c3-4567-efab-234567890123"
}
```

### Error Responses

#### 400 Bad Request
**When:** No valid channels provided, or all channels are invalid.

**Example:**
```json
{
  "error": "invalid_channels",
  "message": "Debe especificar al menos un canal de envio valido.",
  "details": {
    "channels": ["Canal 'sms' no es valido. Opciones: email, whatsapp, portal."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not allowed (e.g., patient role cannot use this endpoint).

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para compartir planes de tratamiento."
}
```

#### 404 Not Found
**When:** patient_id or plan_id not found in tenant.

**Example:**
```json
{
  "error": "plan_not_found",
  "message": "Plan de tratamiento no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** channels array is empty, message too long, etc.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "channels": ["El campo channels no puede estar vacio."],
    "message": ["El mensaje no puede superar 500 caracteres."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded or 3 share attempts per plan per hour exceeded.

**Example:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiados intentos de compartir este plan. Espere antes de volver a intentarlo."
}
```

#### 500 Internal Server Error
**When:** PDF generation failure, queue dispatch failure, or unexpected system error.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema (channels array non-empty, valid enum values, message length).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (must be doctor, clinic_owner, or receptionist).
4. Fetch plan and verify it exists and belongs to the patient.
5. Fetch patient record (name, email, phone) for channel dispatch.
6. Check share rate limit: query `plan_share_logs` for this plan_id in the last hour. If >= 3 shares, return 429.
7. Ensure PDF is available (call TP-09 logic internally or check cached PDF):
   - If PDF already exists in S3 and is not stale (generated after plan's `updated_at`), use existing PDF.
   - If PDF is stale or missing, generate it synchronously (or enqueue generation and include pending status).
8. Generate temporary access link:
   - Create a `plan_access_tokens` record: token (UUID v4, hashed), plan_id, patient_id, expires_at = now() + 7 days.
   - Access URL: `{portal_base_url}/p/plan/{token}`
   - Token is valid for 7 days for patients without portal accounts; patients WITH portal accounts are redirected to their authenticated portal view.
9. For each requested channel, check dispatch conditions and enqueue:
   a. **email**: Requires patient.email to be non-null. If null, channel is skipped with reason "El paciente no tiene correo electronico registrado." Enqueue job to `notifications.treatment_plan_shared` queue with payload including PDF S3 URL, patient name, access_link, custom message.
   b. **whatsapp**: Requires tenant WhatsApp integration to be configured (check `tenant_integrations` table). If not configured, skip with reason "WhatsApp no configurado para esta clinica." Requires patient.phone to be non-null. Enqueue job to `notifications.treatment_plan_shared` queue with channel=whatsapp, access_link URL, and templated message.
   c. **portal**: Always dispatches if patient has a portal account (check `patient_portal_accounts` table). Creates an in-app notification: "Su clinica ha compartido un plan de tratamiento con usted." with link to the plan in portal. If patient has no portal account, dispatch is replaced by the temporary access link (always generated).
10. Insert `plan_share_log` record: plan_id, channels_dispatched, shared_by, shared_at.
11. Write audit log entry (action: share, resource: treatment_plan, PHI: yes).
12. Return 200 with dispatch results and access_link.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| channels | Non-empty array; each item must be one of: email, whatsapp, portal | Debe especificar al menos un canal valido. |
| message | max 500 chars (if provided) | El mensaje no puede superar 500 caracteres. |

**Business Rules:**

- A share always generates the temporary access link regardless of channels — this ensures patients can always be sent the link manually if needed.
- Channels that cannot be dispatched (missing patient contact, unconfigured integration) are added to `channels_skipped` in the response — this is not an error, it is informational. The response is still 200 OK.
- At least one channel must be successfully dispatched. If ALL channels are skipped, return 400 with explanation.
- WhatsApp message text is pre-built from a template (not a free-form message from the doctor) per WhatsApp Business API template regulations. The custom `message` field in the body is included in the email body only.
- The temporary access link is single-use per URL session: the token is valid for 7 days but is not restricted to a single access. A patient can open the link multiple times within the validity window.
- `plan_access_tokens` are stored hashed in the database (SHA-256 of the token UUID). The plain token is sent to the patient and never stored.
- The share is non-blocking: all channel dispatches are enqueued to RabbitMQ, not sent synchronously. The response confirms dispatch (not delivery).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no email and only channel is email | All channels skipped; return 400 |
| Patient has no phone, whatsapp requested | whatsapp skipped (reason: no phone); other channels dispatched |
| Patient has portal account | portal notification created; access_link still generated |
| Patient has no portal account | No portal notification; access_link is the primary access method |
| WhatsApp not configured for tenant, only whatsapp requested | All channels skipped; return 400 |
| Re-sharing same plan (within 1 hour, under 3 attempts) | 200 OK, new share log entry, new token generated |
| 3rd share within 1 hour | 429 rate limited |
| PDF is stale (plan updated after last PDF generation) | New PDF generated before dispatch |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `plan_access_tokens`: INSERT — temporary access token (hashed) with 7-day expiry
- `plan_share_logs`: INSERT — share attempt record (plan_id, channels_dispatched, shared_by, shared_at)
- `patient_notifications`: INSERT — in-app portal notification (if portal channel dispatched and patient has portal account)

**Example query (SQLAlchemy):**
```python
# Generate and store access token
token_plain = str(uuid4())
token_hash = hashlib.sha256(token_plain.encode()).hexdigest()
access_token = PlanAccessToken(
    token_hash=token_hash,
    plan_id=plan_id,
    patient_id=patient_id,
    expires_at=datetime.utcnow() + timedelta(days=7),
    created_by=current_user.id,
)
session.add(access_token)

# Log the share
share_log = PlanShareLog(
    plan_id=plan_id,
    channels_dispatched=channels_dispatched,
    shared_by=current_user.id,
    shared_at=datetime.utcnow(),
)
session.add(share_log)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:plan:{plan_id}:share_count`: INCR — increment share count for rate limiting

**Cache TTL:** 3600 seconds (rolling 1-hour window for rate limiting)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications.treatment_plan_shared | email.send | { tenant_id, patient_id, plan_id, patient_email, patient_name, pdf_url, access_link, message, doctor_name } | When email channel dispatched |
| notifications.treatment_plan_shared | whatsapp.send | { tenant_id, patient_id, plan_id, patient_phone, access_link, template_name } | When whatsapp channel dispatched |
| notifications.treatment_plan_shared | portal.notify | { tenant_id, patient_id, plan_id, notification_type, access_link } | When portal channel dispatched |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** share
- **Resource:** treatment_plan
- **PHI involved:** Yes (patient contact info used for dispatch, plan shared externally)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | treatment_plan_shared_email | patient | When email channel dispatched |
| whatsapp | treatment_plan_whatsapp_msg | patient | When whatsapp channel dispatched and integration configured |
| in-app (portal) | treatment_plan_shared_portal | patient | When portal channel dispatched and patient has portal account |

---

## Performance

### Expected Response Time
- **Target:** < 500ms (PDF cached, queue dispatch only)
- **Maximum acceptable:** < 3000ms (PDF regeneration required)

### Caching Strategy
- **Strategy:** Redis for share rate-limit counter; PDF cached in S3 (from TP-09)
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:plan:{plan_id}:share_count`
- **TTL:** 3600 seconds (rate limit window)
- **Invalidation:** N/A (counter is time-bounded)

### Database Performance

**Queries executed:** 5 (plan fetch, patient fetch, share rate limit check, access_token insert, share_log insert)

**Indexes required:**
- `plan_share_logs.(plan_id, shared_at)` — INDEX (rate limit check query)
- `plan_access_tokens.(token_hash)` — UNIQUE INDEX (token lookup for portal access)
- `plan_access_tokens.(plan_id, patient_id, expires_at)` — INDEX (cleanup queries)

**N+1 prevention:** Not applicable (sequential single-record operations).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| channels | Pydantic Enum validator for each item | Prevents arbitrary channel names |
| message | Pydantic `strip()` + bleach.clean | Custom message in email body; HTML stripped |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped via Pydantic serialization. Message content HTML-stripped before inclusion in email templates.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, patient email and phone (used for dispatch), plan contents (sent externally via email/WhatsApp).

**Audit requirement:** All share actions logged as PHI external disclosure events. Access tokens expire in 7 days and are stored hashed. PDF accessed only via time-limited S3 pre-signed URLs.

---

## Testing

### Test Cases

#### Happy Path
1. Share via all channels (email + whatsapp + portal)
   - **Given:** Doctor, plan exists, patient has email + phone, WhatsApp configured, patient has portal account
   - **When:** POST /share with channels = [email, whatsapp, portal]
   - **Then:** 200 OK, all 3 channels dispatched, access_link generated (7 days expiry), 3 RabbitMQ jobs enqueued

2. Share via email only
   - **Given:** Valid plan, patient has email
   - **When:** POST /share with channels = [email]
   - **Then:** 200 OK, email job dispatched, access_link generated

3. Share skips WhatsApp (not configured)
   - **Given:** Tenant has no WhatsApp integration configured
   - **When:** POST /share with channels = [email, whatsapp]
   - **Then:** 200 OK, email dispatched, whatsapp in channels_skipped with reason

4. Patient has no portal account — access link as fallback
   - **Given:** portal channel requested, patient has no portal account
   - **When:** POST /share with channels = [portal]
   - **Then:** 200 OK, no portal notification created (no account), access_link generated as primary access

5. Share with custom message
   - **Given:** channels = [email], message = "Su plan de tratamiento..."
   - **When:** POST /share
   - **Then:** 200 OK, email job payload includes custom message

#### Edge Cases
1. PDF stale — regenerated before share
   - **Given:** Plan updated after last PDF generation
   - **When:** POST /share
   - **Then:** 200 OK, new PDF generated, dispatched with updated PDF URL

2. Second share within 1 hour (2nd of 3 allowed)
   - **Given:** 1 prior share in last hour
   - **When:** POST /share
   - **Then:** 200 OK, new token generated, new jobs dispatched

3. Share with no custom message
   - **Given:** channels = [email], no message field
   - **When:** POST /share
   - **Then:** 200 OK, email uses default template text

#### Error Cases
1. Rate limit exceeded (4th share in 1 hour)
   - **Given:** 3 prior shares in last hour
   - **When:** 4th POST /share
   - **Then:** 429 Too Many Requests

2. All channels skipped (patient has no email, whatsapp not configured, only those two requested)
   - **Given:** Patient no email, no WhatsApp integration, channels = [email, whatsapp]
   - **When:** POST /share
   - **Then:** 400 invalid_channels — all channels skipped

3. Empty channels array
   - **Given:** channels = []
   - **When:** POST /share
   - **Then:** 422 validation error

4. Plan not found
   - **Given:** Non-existent plan_id
   - **When:** POST /share
   - **Then:** 404 Not Found

5. Receptionist role blocked for patient role
   - **Given:** User with patient role calls share endpoint
   - **When:** POST /share
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** doctor, clinic_owner, receptionist

**Patients/Entities:** Patient with email and phone; patient with email only; patient with no email or phone; patient with portal account; patient without portal account. Tenant with WhatsApp configured; tenant without WhatsApp. Treatment plan in any status.

### Mocking Strategy

- RabbitMQ: Mock publish, assert all three job payloads (email, whatsapp, portal)
- S3 / PDF generation: Return known PDF URL from TP-09 mock
- portal_access_tokens: Verify token hash stored, not plain token
- Redis cache: fakeredis for rate limit counter tests
- patient_portal_accounts: Fixture with/without portal account

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] All requested channels dispatched to RabbitMQ queue
- [ ] Channels without required conditions (no email, no WhatsApp config) skipped and reported in response
- [ ] If all channels skipped, 400 returned (not 200)
- [ ] Temporary access link generated for every share (7 days TTL)
- [ ] Access token stored hashed in DB (plain token never stored)
- [ ] PDF is current (regenerated if stale) before dispatch
- [ ] Rate limit enforced: max 3 shares per plan per hour
- [ ] Email job payload includes PDF URL, access link, and optional custom message
- [ ] WhatsApp job blocked when integration not configured
- [ ] Portal notification only created when patient has portal account
- [ ] Audit log written as PHI external disclosure event
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms cached, < 3000ms with PDF generation)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Email/WhatsApp/portal notification delivery (handled by notification domain consumers of the RabbitMQ queue)
- WhatsApp Business API integration configuration (tenant settings domain)
- Portal access token validation (portal domain — the token is consumed by the portal login/view endpoint)
- Revoking access links (no revocation mechanism in v1; links expire naturally)
- Bulk sharing across multiple patients

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
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access (external disclosure logged)
- [x] Access tokens stored hashed

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (Redis rate limit + S3 PDF cache)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (PHI external disclosure)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (3 queue jobs per share)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services (RabbitMQ, S3, portal accounts)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
