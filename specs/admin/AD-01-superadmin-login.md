# AD-01 — Superadmin Login Spec

## Overview

**Feature:** Authenticate a platform superadmin into the DentalOS admin panel. Uses a separate auth context from tenant-level authentication: email + password + TOTP (Time-based One-Time Password) MFA. Returns a superadmin JWT with `role=superadmin` and no tenant scope. Rate-limited, IP-logged, and supports optional IP allowlist enforcement.

**Domain:** admin

**Priority:** Critical (Sprint 1-2 — needed before any admin operations)

**Dependencies:** infra/authentication-rules.md, infra/rate-limiting.md, infra/audit-logging.md

---

## Authentication

- **Level:** Public (this IS the authentication endpoint; no prior auth required)
- **Roles allowed:** N/A (creates a new session)
- **Tenant context:** Not required — superadmin is platform-level, not tenant-scoped
- **Special rules:** TOTP MFA is mandatory (not optional). All failed attempts are logged with IP address. Optional IP allowlist: if configured, rejects requests from non-allowed IPs before password check.

---

## Endpoint

```
POST /api/v1/admin/auth/login
```

**Rate Limiting:**
- 3 requests per 15 minutes per IP address (hard lock, not soft)
- After 3 failed attempts: IP is blocked for 30 minutes; subsequent requests get 429 with retry_after
- Separate from tenant-level rate limiting; uses `admin_rate_limit:{ip}` Redis key

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Content-Type | Yes | string | Request format | application/json |
| X-Forwarded-For | No | string | Client IP (handled by proxy) | 203.0.113.42 |
| User-Agent | No | string | Client user agent (logged for audit) | Mozilla/5.0... |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "email": "string (required) — superadmin email address",
  "password": "string (required) — account password",
  "totp_code": "string (required) — 6-digit TOTP code from authenticator app"
}
```

**Example Request:**
```json
{
  "email": "admin@dentalos.io",
  "password": "Sup3rS3cur3P@ssw0rd!",
  "totp_code": "847291"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "access_token": "string — JWT access token (superadmin-scoped)",
  "token_type": "string — Bearer",
  "expires_in": "integer — seconds until access token expires",
  "expires_at": "string (ISO 8601) — absolute expiry timestamp",
  "admin_user": {
    "id": "string (UUID)",
    "email": "string",
    "name": "string",
    "role": "string — superadmin",
    "mfa_method": "string — totp",
    "last_login_at": "string (ISO 8601) | null",
    "last_login_ip": "string | null"
  },
  "session_id": "string (UUID) — for audit trail correlation"
}
```

**Example:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbl91c2VyX2lkIiwicm9sZSI6InN1cGVyYWRtaW4iLCJzZXNzaW9uX2lkIjoic2Vzc19hYmMxMjMiLCJpYXQiOjE3MDg4NjU2MDAsImV4cCI6MTcwODg2OTIwMH0.signature",
  "token_type": "Bearer",
  "expires_in": 3600,
  "expires_at": "2026-02-25T11:00:00Z",
  "admin_user": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "admin@dentalos.io",
    "name": "Platform Admin",
    "role": "superadmin",
    "mfa_method": "totp",
    "last_login_at": "2026-02-24T09:30:00Z",
    "last_login_ip": "203.0.113.10"
  },
  "session_id": "sess_xyz789abc123"
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields, `totp_code` is not 6 digits, email is not valid format.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "totp_code": ["totp_code must be exactly 6 digits"],
    "email": ["value is not a valid email address"]
  }
}
```

#### 401 Unauthorized
**When:** Email not found, password incorrect, or TOTP code invalid/expired. Response is intentionally generic to prevent email enumeration.

**Example:**
```json
{
  "error": "authentication_failed",
  "message": "Invalid credentials or MFA code",
  "details": {
    "remaining_attempts": 2,
    "lockout_warning": "Account will be temporarily locked after 1 more failed attempt"
  }
}
```

#### 403 Forbidden
**When:** IP address is not in the superadmin IP allowlist (if allowlist is configured and non-empty).

**Example:**
```json
{
  "error": "ip_not_allowed",
  "message": "Access from this IP address is not permitted",
  "details": {
    "client_ip": "192.0.2.50",
    "hint": "Contact the platform administrator to whitelist your IP"
  }
}
```

#### 422 Unprocessable Entity
**When:** Request body is malformed JSON or Pydantic validation fails.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "password": ["field required"],
    "email": ["field required"]
  }
}
```

#### 429 Too Many Requests
**When:** IP has exceeded 3 failed attempts within 15 minutes.

**Example:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many failed login attempts. Try again later.",
  "details": {
    "lockout_duration_seconds": 1800,
    "retry_after": "2026-02-25T10:45:00Z",
    "client_ip": "203.0.113.42"
  }
}
```

#### 500 Internal Server Error
**When:** Redis unavailable (cannot check rate limit), JWT signing failure, unexpected DB error.

---

## Business Logic

**Step-by-step process:**

1. Validate request body via Pydantic schema `SuperadminLoginRequest`:
   - `email`: valid email format, lowercase-normalized
   - `password`: present and non-empty
   - `totp_code`: exactly 6 digits (`^\d{6}$`)
2. Extract client IP from `X-Forwarded-For` header (first IP in chain) or direct connection IP. Sanitize to prevent spoofing (trust only configured proxy headers).
3. Check IP allowlist: if `ADMIN_IP_ALLOWLIST` environment variable is set and non-empty, verify client IP is in the list. Return 403 if not.
4. Check rate limit: `INCR admin_rate_limit:{client_ip}` in Redis with 15-minute sliding window. If count > 3, return 429 with retry_after.
5. Lookup admin user: query `admin_users` table (in public schema, NOT tenant schemas) WHERE `email = lowercase(body.email) AND is_active = true`. If not found, increment rate limit counter and return 401 (generic message to prevent email enumeration).
6. Verify password: `bcrypt.verify(body.password, admin_user.password_hash)`. If invalid, increment rate limit counter, update `admin_users.failed_login_count`, return 401.
7. Verify TOTP:
   - Load TOTP secret from `admin_users.totp_secret` (stored encrypted with application secret).
   - Use `pyotp.TOTP(totp_secret).verify(body.totp_code, valid_window=1)` (allows ±30s clock drift).
   - If invalid, increment rate limit counter, return 401 with generic message.
   - Mark TOTP code as used in Redis (prevent replay within same 30s window): `SET admin_totp_used:{admin_user_id}:{totp_code}:{window} 1 EX 60`.
8. All checks passed: clear rate limit counter for IP: `DEL admin_rate_limit:{client_ip}`.
9. Generate admin JWT:
   - Algorithm: RS256 (asymmetric — admin panel uses separate keypair from tenant JWTs)
   - Claims: `{ sub: admin_user_id, role: "superadmin", session_id: new_uuid, iat: now, exp: now+3600, type: "admin_access" }`
   - Sign with admin private key (`ADMIN_JWT_PRIVATE_KEY` env var)
10. Generate `session_id` UUID; store in Redis: `SET admin_session:{session_id} {admin_user_id}` TTL 3600s (for session invalidation/logout).
11. Update `admin_users`: set `last_login_at = now()`, `last_login_ip = client_ip`, `failed_login_count = 0`.
12. Write audit log: action=`admin_login_success`, actor=`admin_user_id`, ip=`client_ip`, user_agent=`user_agent`, session_id=`session_id`.
13. Return 200 with token and user info.

**TOTP Setup (out of scope for this spec, but relevant context):**
- TOTP is set up at admin account creation time via a separate `POST /api/v1/admin/auth/setup-mfa` endpoint.
- Secrets generated with `pyotp.random_base32()`, stored encrypted.
- QR code generated for Google Authenticator / Authy enrollment.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| email | Valid email format; lowercased | "Ingrese un correo electrónico válido" |
| password | Non-empty string | "Contraseña requerida" |
| totp_code | Exactly 6 digits (regex `^\d{6}$`) | "El código MFA debe ser exactamente 6 dígitos" |

**Business Rules:**

- Admin JWT is separate from tenant JWTs: different keypair, different `type` claim, shorter TTL (1 hour vs 24h for tenant).
- Admin JWT has NO `tenant_id` claim — it is explicitly platform-level.
- Failed authentication always returns generic 401 (no distinction between wrong email, wrong password, wrong TOTP) to prevent enumeration.
- TOTP codes are single-use within their 30-second window (replay prevention via Redis).
- Rate limit counter increments on ANY auth failure (wrong email, wrong password, wrong TOTP).
- Rate limit is per-IP, not per-email — prevents distributed brute force from a single IP.
- IP allowlist is optional. When empty, all IPs are allowed (suitable for development; production should set allowlist).
- Admin accounts cannot be locked permanently; only temporary 30-minute lockouts (avoid self-lockout issues).

**JWT Claims:**
```json
{
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "role": "superadmin",
  "session_id": "sess_xyz789abc123",
  "type": "admin_access",
  "iat": 1708866000,
  "exp": 1708869600,
  "iss": "dentalos-admin",
  "jti": "unique-jwt-id"
}
```

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Correct password, expired TOTP | 401 generic — TOTP validation fails after 90s window |
| TOTP replay (same code, same window) | 401 — code already used in Redis; prevents replay attack |
| IP allowlist empty | All IPs allowed (allowlist only enforced when non-empty) |
| Admin account is_active=false (suspended) | 401 generic — treated same as not found |
| Clock drift > 30s on admin device | Authentication fails; admin must sync device clock |
| Concurrent logins from different IPs | Both succeed (no single-session enforcement for admin; each gets separate session_id) |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `admin_users`: UPDATE `last_login_at`, `last_login_ip`, `failed_login_count`

**Tenant schema tables affected:**
- None

**Example query (SQLAlchemy):**
```python
await session.execute(
    update(AdminUser)
    .where(AdminUser.id == admin_user.id)
    .values(
        last_login_at=utcnow(),
        last_login_ip=client_ip,
        failed_login_count=0,
    )
)
```

### Cache Operations

**Cache keys affected:**
- `admin_rate_limit:{client_ip}`: INCR on failure, DEL on success — TTL: 900s (15 min window)
- `admin_session:{session_id}`: SET on success — TTL: 3600s
- `admin_totp_used:{admin_user_id}:{totp_code}:{window}`: SET (replay prevention) — TTL: 60s

**Cache TTL:** As listed above

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** login (success) or login_failed (failure)
- **Resource:** admin_session
- **PHI involved:** No

**Additional audit fields for admin login:**
- `client_ip`: logged
- `user_agent`: logged
- `failure_reason`: logged on failure (rate_limited, wrong_password, wrong_totp, ip_not_allowed — logged internally but NOT returned to client)

### Notifications

**Notifications triggered:** Yes (security alerting)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | admin_login_new_ip | admin_user | Successful login from an IP not seen in the last 30 days |
| email | admin_login_failed_lockout | admin_user | 3rd failed attempt triggers lockout |

---

## Performance

### Expected Response Time
- **Target:** < 500ms (bcrypt is intentionally slow; ~200-400ms for bcrypt.verify)
- **Maximum acceptable:** < 1,200ms

### Caching Strategy
- **Strategy:** Rate limiting via Redis; session storage via Redis; TOTP replay prevention via Redis
- **No caching of auth responses** — every login is fresh

### Database Performance

**Queries executed:** 2 (SELECT admin_user by email; UPDATE last_login_at)

**Indexes required:**
- `admin_users.(email)` — UNIQUE INDEX (primary lookup)
- `admin_users.(is_active)` — INDEX (filter active accounts)

**N+1 prevention:** Not applicable (single record fetch).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| email | Pydantic EmailStr + .lower() | Normalized to lowercase; rejects non-email format |
| password | Pydantic non-empty string | Not logged anywhere; only compared via bcrypt |
| totp_code | Pydantic regex `^\d{6}$` | Only digits, exactly 6; prevents injection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. Password and TOTP never returned in response.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable. Admin panel should additionally enforce `SameSite=Strict` on any cookies if used.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — admin authentication involves no patient data.

**Audit requirement:** All attempts logged (success and failure).

### Timing Attack Prevention

- Email lookup uses constant-time comparison for email existence check (dummy bcrypt verify even if user not found to prevent timing oracle).
- TOTP verification uses pyotp's constant-time comparison.

---

## Testing

### Test Cases

#### Happy Path
1. Successful login with valid credentials + TOTP
   - **Given:** Active admin user with TOTP setup; valid email, password, and TOTP code
   - **When:** POST /api/v1/admin/auth/login
   - **Then:** 200 OK, access_token returned (RS256 JWT), role=superadmin in claims, session stored in Redis

2. Login from a new IP triggers security email
   - **Given:** Valid credentials; IP not seen in 30 days
   - **When:** POST login
   - **Then:** 200 OK + email notification sent

#### Edge Cases
1. Clock drift ±30s (TOTP valid_window=1)
   - **Given:** TOTP code generated 25 seconds ago
   - **When:** POST login with that code
   - **Then:** 200 OK (within window)

2. Empty IP allowlist (all allowed)
   - **Given:** ADMIN_IP_ALLOWLIST env var is empty
   - **When:** POST from any IP
   - **Then:** IP check skipped; login proceeds normally

3. Replay attack (same TOTP code, same window)
   - **Given:** First login succeeded with code 847291 at T+0
   - **When:** Second login attempted with same code at T+10
   - **Then:** 401 Unauthorized (code marked used in Redis)

#### Error Cases
1. Wrong password
   - **Given:** Correct email, wrong password, valid TOTP
   - **When:** POST login
   - **Then:** 401, generic "Invalid credentials or MFA code", remaining_attempts=2

2. Third failed attempt — lockout
   - **Given:** 2 prior failed attempts in 15 min window
   - **When:** Third failed POST login
   - **Then:** 429 Too Many Requests, retry_after in 30 minutes

3. IP not in allowlist
   - **Given:** ADMIN_IP_ALLOWLIST=["10.0.0.1"], client IP=192.168.1.1
   - **When:** POST login
   - **Then:** 403 Forbidden (before password check)

4. Admin account suspended (is_active=false)
   - **Given:** Valid credentials but is_active=false
   - **When:** POST login
   - **Then:** 401 generic (same as wrong credentials — no info about account status)

### Test Data Requirements

**Users:** 1 active admin user with TOTP configured; 1 suspended admin user

**Patients/Entities:** None

### Mocking Strategy

- pyotp TOTP: Use known TOTP secret to generate valid codes deterministically in tests
- bcrypt: Use test-specific low-cost factor (cost=4) to speed up tests without compromising algorithm
- Redis: Use fakeredis for rate limit and session tests
- Email notifications: Mock email service; verify email sent on new-IP login

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST returns 200 with RS256 JWT (superadmin-scoped, no tenant_id)
- [ ] JWT claims include role=superadmin, session_id, exp=1h
- [ ] TOTP required and validated with pyotp (valid_window=1)
- [ ] Rate limit: 3 attempts per 15 min per IP; 30-min lockout on 3rd failure
- [ ] IP allowlist enforced when ADMIN_IP_ALLOWLIST is set
- [ ] Replay attack prevented (Redis deduplication of TOTP codes)
- [ ] Generic 401 returned for all auth failures (email, password, TOTP)
- [ ] Admin session stored in Redis (TTL 1h)
- [ ] All audit log entries created (success + failure)
- [ ] Security email sent on new-IP login
- [ ] All test cases pass
- [ ] Performance target: < 500ms
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Admin logout (session invalidation endpoint — separate spec)
- Admin password reset (separate spec)
- TOTP MFA setup/enrollment (admin account creation flow)
- Tenant-level authentication (see auth/A-01)
- Admin token refresh (admin sessions are short-lived; re-login required)
- Hardware security key (FIDO2/WebAuthn) — future MFA option

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
- [x] Caching strategy stated
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
