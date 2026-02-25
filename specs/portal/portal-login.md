# PP-01 Portal Login Spec

---

## Overview

**Feature:** Authenticate a patient into the patient portal using email/phone + password or a magic link (one-time token sent via email or WhatsApp). Issues a portal-scoped JWT with role=patient. Separate from clinic-staff authentication context.

**Domain:** portal

**Priority:** Medium

**Dependencies:** A-01 (auth/login.md), I-01 (multi-tenancy.md), I-02 (auth-rules.md), P-11 (patient-portal-access.md), infra/rate-limiting.md

---

## Authentication

- **Level:** Public
- **Roles allowed:** N/A (unauthenticated endpoint; issues patient-role JWT on success)
- **Tenant context:** Required — tenant resolved from subdomain or `X-Tenant-ID` header (not from JWT, since patient is not yet authenticated)
- **Special rules:** Portal access must be explicitly granted to the patient by the clinic (portal_access = true on patient record). Patients without portal access receive 403 even with correct credentials.

---

## Endpoint

```
POST /api/v1/portal/auth/login
```

**Rate Limiting:**
- 5 requests per 15 minutes per IP address
- 10 requests per 15 minutes per email/phone (cross-IP brute force protection)
- Magic link requests: 3 per 15 minutes per email/phone

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (from subdomain or explicit header) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "login_method": "string (required) — enum: password, magic_link",
  "identifier": "string (required) — email or phone in E.164 format, max 320 chars",
  "password": "string (conditional) — required if login_method=password, min 8 chars, max 128 chars",
  "magic_link_channel": "string (conditional) — required if login_method=magic_link, enum: email, whatsapp"
}
```

**Example Request — Password Login:**
```json
{
  "login_method": "password",
  "identifier": "maria.garcia@email.com",
  "password": "MiContrasena123!"
}
```

**Example Request — Magic Link:**
```json
{
  "login_method": "magic_link",
  "identifier": "+573001234567",
  "magic_link_channel": "whatsapp"
}
```

---

## Response

### Success Response — Password Login

**Status:** 200 OK

**Schema:**
```json
{
  "access_token": "string — JWT, expires in 30 minutes",
  "refresh_token": "string — JWT, expires in 7 days",
  "token_type": "string — always 'bearer'",
  "expires_in": "integer — seconds until access_token expiry",
  "patient": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "email": "string | null",
    "phone": "string | null",
    "portal_access": "boolean — always true here"
  }
}
```

**Example:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "patient": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "first_name": "Maria",
    "last_name": "Garcia Lopez",
    "email": "maria.garcia@email.com",
    "phone": "+573001234567",
    "portal_access": true
  }
}
```

### Success Response — Magic Link Requested

**Status:** 200 OK

**Schema:**
```json
{
  "status": "string — always 'magic_link_sent'",
  "message": "string — localized confirmation message",
  "expires_in_minutes": "integer — always 15",
  "channel": "string — email or whatsapp"
}
```

**Example:**
```json
{
  "status": "magic_link_sent",
  "message": "Se ha enviado un enlace de acceso a su WhatsApp. El enlace expira en 15 minutos.",
  "expires_in_minutes": 15,
  "channel": "whatsapp"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON, missing required fields, or invalid login_method enum.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "login_method": ["Metodo de inicio de sesion no valido. Opciones: password, magic_link."]
  }
}
```

#### 401 Unauthorized
**When:** Password login with incorrect password, or magic link token is invalid/expired.

**Example:**
```json
{
  "error": "invalid_credentials",
  "message": "Correo electronico o contrasena incorrectos."
}
```

#### 403 Forbidden
**When:** Patient record exists but portal_access = false for this tenant.

**Example:**
```json
{
  "error": "portal_access_denied",
  "message": "Su clinica no ha habilitado el acceso al portal para su cuenta. Contacte a su clinica para mas informacion."
}
```

#### 404 Not Found
**When:** No patient with the given identifier exists in the tenant. Returns 401-style message to avoid user enumeration.

**Example:**
```json
{
  "error": "invalid_credentials",
  "message": "Correo electronico o contrasena incorrectos."
}
```

#### 422 Unprocessable Entity
**When:** Field-level validation fails (e.g., password too short, invalid email format).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "identifier": ["Formato de correo electronico no valido."],
    "password": ["La contrasena debe tener al menos 8 caracteres."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded (5 attempts per 15 minutes per IP). See `infra/rate-limiting.md`.

**Example:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiados intentos de inicio de sesion. Intente nuevamente en 15 minutos.",
  "retry_after_seconds": 847
}
```

#### 500 Internal Server Error
**When:** Unexpected database or token generation failure.

---

## Business Logic

**Step-by-step process — Password Login:**

1. Validate input against Pydantic schema (required fields, enums, lengths).
2. Resolve tenant from `X-Tenant-ID` header; verify tenant exists and is active in `public.tenants`.
3. Check IP-based rate limit (5/15min). If exceeded, return 429 before any DB query.
4. Look up patient by identifier: search `patients.email` or `patients.phone` (whichever matches E.164 or email pattern) within tenant schema.
5. If patient not found, increment failed-attempt counter in Redis and return 401 (do not reveal whether account exists).
6. Verify `patient.portal_access = true`. If false, return 403.
7. Verify `patient.is_active = true`. If false, return 403 with generic message.
8. Compare provided password against `portal_credentials.password_hash` (bcrypt, cost factor 12). If mismatch, increment failed-attempt counter and return 401.
9. If failed_attempts >= 5 for this identifier in the last 15 minutes, lock for 15 minutes and return 429.
10. Generate portal-scoped JWT:
    - `sub`: patient.id
    - `tenant_id`: tenant.id
    - `role`: "patient"
    - `scope`: "portal"
    - `exp`: now + 30 minutes (access), now + 7 days (refresh)
11. Store refresh token hash in Redis: `portal:refresh:{tenant_id}:{patient_id}:{token_jti}` with TTL 7 days.
12. Reset failed-attempt counter for this identifier in Redis.
13. Update `portal_credentials.last_login_at` timestamp.
14. Write audit log entry (action: login, resource: portal_session, PHI: no).
15. Return 200 with tokens and patient summary.

**Step-by-step process — Magic Link:**

1. Validate input against Pydantic schema.
2. Resolve tenant, check rate limits.
3. Look up patient by identifier. If not found, return 200 anyway (do not reveal user enumeration).
4. Verify `portal_access = true` for patient. If false, return 200 anyway (silent fail to prevent enumeration).
5. Generate one-time token: UUID v4 + HMAC-SHA256 signed with tenant secret, store in Redis: `portal:magic:{tenant_id}:{token}` → patient_id, TTL 15 minutes.
6. Dispatch RabbitMQ job to `notifications` queue: send magic link via chosen channel.
7. Return 200 with `magic_link_sent` status.

**Magic Link Redemption** (separate `GET /api/v1/portal/auth/magic?token={token}&tenant={tenant_id}` flow):
- Validates token from Redis, deletes it (one-time use), issues JWT same as password login flow.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| login_method | Must be: password or magic_link | Metodo de inicio de sesion no valido. |
| identifier | Valid email (RFC 5322) or E.164 phone, max 320 chars | Identificador no valido. |
| password | Required if login_method=password; 8-128 chars | La contrasena es obligatoria y debe tener entre 8 y 128 caracteres. |
| magic_link_channel | Required if login_method=magic_link; must be: email, whatsapp | Canal de magic link no valido. |

**Business Rules:**

- Portal JWT claims always include `scope: "portal"` — staff endpoints reject portal tokens.
- Staff JWT tokens are rejected by portal endpoints (scope mismatch check in middleware).
- A patient can have portal credentials in multiple tenants independently (multi-clinic patients).
- Magic link tokens are single-use and deleted from Redis upon redemption.
- Tenant must have an active plan with portal feature enabled; otherwise return 403.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient provides phone but registered only with email | Look up by both fields; match if either found |
| Magic link request for unknown identifier | Return 200 silently (prevent user enumeration) |
| Magic link token used twice | Second use returns 401 (token deleted after first use) |
| Patient has no password set (magic-link-only account) | password login returns 401 with generic message |
| Concurrent magic link requests (3rd within 15 min) | Return 429 for magic link rate limit |
| Portal access granted mid-session | Next login attempt will succeed; existing sessions unaffected |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `portal_credentials`: UPDATE — last_login_at, failed_attempts reset on success
- `portal_credentials`: UPDATE — failed_attempts increment on failed password attempt

**Example query (SQLAlchemy):**
```python
stmt = (
    update(PortalCredentials)
    .where(PortalCredentials.patient_id == patient.id)
    .values(last_login_at=func.now(), failed_attempts=0)
)
await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `portal:refresh:{tenant_id}:{patient_id}:{jti}`: SET — refresh token hash, TTL 7 days
- `portal:magic:{tenant_id}:{token}`: SET — magic link token → patient_id, TTL 15 minutes
- `portal:failed_attempts:{tenant_id}:{identifier_hash}`: INCR — failed login counter, TTL 15 minutes
- `portal:ip_rate:{ip_hash}`: INCR — IP-based rate limit counter, TTL 15 minutes

**Cache TTL:** Varies per key (see above)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | portal.magic_link_send | { tenant_id, patient_id, token, channel, expires_at } | Magic link requested |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** login
- **Resource:** portal_session
- **PHI involved:** No (only patient_id + tenant_id logged, no clinical data)

### Notifications

**Notifications triggered:** Yes (magic link flow only)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | portal_magic_link | patient | Magic link via email requested |
| whatsapp | portal_magic_link_wa | patient | Magic link via WhatsApp requested |

---

## Performance

### Expected Response Time
- **Target:** < 200ms (password login including bcrypt verify)
- **Maximum acceptable:** < 800ms (bcrypt cost=12 adds ~200-300ms; acceptable for auth)

### Caching Strategy
- **Strategy:** Rate limit counters in Redis; refresh tokens in Redis; no patient data cached
- **Cache key:** `portal:failed_attempts:{tenant_id}:{sha256(identifier)}`
- **TTL:** 15 minutes for rate limit windows
- **Invalidation:** Rate counters expire automatically; refresh tokens deleted on logout

### Database Performance

**Queries executed:** 2 (tenant lookup, patient + portal_credentials lookup with JOIN)

**Indexes required:**
- `patients.email` — INDEX (for identifier lookup)
- `patients.phone` — INDEX (for identifier lookup)
- `patients.portal_access` — INDEX (for filtering)
- `portal_credentials.patient_id` — UNIQUE INDEX

**N+1 prevention:** Single JOIN query for patient + portal_credentials.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| identifier | Pydantic EmailStr or E.164 regex; strip whitespace | Used only for lookup; never echoed raw in errors |
| password | No trimming (whitespace is valid in passwords); max length enforced | Never logged, never returned |
| login_method | Enum validation (Pydantic Literal) | Strict allowlist |
| magic_link_channel | Enum validation (Pydantic Literal) | Strict allowlist |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped by default via Pydantic serialization. Tokens are opaque strings.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** identifier (email/phone is PII, not clinical PHI)

**Audit requirement:** Login events logged (success + failure) without PHI field values. Identifier is hashed in rate-limit Redis keys.

### Timing Attack Prevention

- Constant-time comparison used for password hash verification (bcrypt handles this).
- When patient not found, still execute a dummy bcrypt verify to prevent timing-based user enumeration.

---

## Testing

### Test Cases

#### Happy Path
1. Password login with valid email and password
   - **Given:** Patient with portal_access=true, active account, valid credentials
   - **When:** POST /api/v1/portal/auth/login with login_method=password
   - **Then:** 200 OK with access_token, refresh_token, patient summary

2. Password login with phone identifier
   - **Given:** Patient registered with phone, portal_access=true
   - **When:** POST with identifier="+573001234567", correct password
   - **Then:** 200 OK with tokens

3. Magic link request via email
   - **Given:** Patient with email and portal_access=true
   - **When:** POST with login_method=magic_link, magic_link_channel=email
   - **Then:** 200 OK with magic_link_sent status; RabbitMQ job dispatched

4. Magic link request via WhatsApp
   - **Given:** Patient with phone and portal_access=true
   - **When:** POST with login_method=magic_link, magic_link_channel=whatsapp
   - **Then:** 200 OK; WhatsApp notification job dispatched

#### Edge Cases
1. Patient identified by phone using email lookup field
   - **Given:** Patient has both email and phone stored
   - **When:** Login with email identifier
   - **Then:** 200 OK — correct patient resolved

2. 5th failed attempt triggers lockout
   - **Given:** 4 previous failed password attempts in 15 minutes
   - **When:** 5th failed attempt
   - **Then:** 429 with retry_after_seconds

3. Magic link for unknown identifier
   - **Given:** No patient with provided email in tenant
   - **When:** POST with login_method=magic_link
   - **Then:** 200 OK (silent — prevent enumeration), no job dispatched

#### Error Cases
1. Wrong password
   - **Given:** Patient exists, portal_access=true
   - **When:** POST with incorrect password
   - **Then:** 401 Unauthorized, generic error message

2. Portal access not granted
   - **Given:** Patient exists, portal_access=false
   - **When:** POST with correct credentials
   - **Then:** 403 Forbidden with portal_access_denied error

3. Rate limit exceeded
   - **Given:** 5 login attempts from same IP in 15 minutes
   - **When:** 6th attempt
   - **Then:** 429 with retry_after_seconds populated

4. Staff JWT used on portal endpoint
   - **Given:** Valid doctor JWT (scope=staff)
   - **When:** POST to portal login (N/A — but portal protected endpoints with staff token)
   - **Then:** 403 scope mismatch

### Test Data Requirements

**Users:** Patient with portal_access=true and password set; patient with portal_access=false; patient with magic-link-only (no password).

**Patients/Entities:** Tenant with portal feature enabled; Redis instance for rate limit and token storage.

### Mocking Strategy

- Redis: fakeredis for all cache/rate-limit operations
- RabbitMQ: Mock publish, assert job payload structure
- bcrypt: Use low cost factor (4) in tests for speed

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Password login returns 200 with valid portal-scoped JWT
- [ ] Magic link flow returns 200 and dispatches correct RabbitMQ job
- [ ] portal_access=false returns 403 (not 401)
- [ ] IP rate limit blocks after 5 attempts in 15 minutes
- [ ] Per-identifier rate limit prevents cross-IP brute force
- [ ] Portal JWT claims include scope="portal" and role="patient"
- [ ] Staff JWT tokens rejected on portal-protected routes (scope check)
- [ ] User enumeration prevented (404 returns identical response to 401)
- [ ] Timing attack mitigation active (dummy bcrypt on user-not-found)
- [ ] Audit log entry written for each login attempt
- [ ] All test cases pass
- [ ] Performance targets met (< 800ms including bcrypt)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Patient portal registration (patients are created by clinic staff, not self-registered)
- Password reset flow (separate endpoint)
- Token refresh endpoint (separate endpoint: POST /api/v1/portal/auth/refresh)
- Magic link redemption endpoint (GET /api/v1/portal/auth/magic)
- Portal logout endpoint (separate endpoint)
- Two-factor authentication (future enhancement)
- OAuth2 / social login (future enhancement)

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
- [x] Auth level stated (public endpoint issuing patient role token)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for login events

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (Redis rate limits and refresh tokens)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

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
