# AD-07 — Admin Tenant Impersonation Spec

## Overview

**Feature:** Allow superadmins to impersonate a tenant for customer support purposes. Creates a time-limited (max 1 hour) session scoped to the target tenant with a special impersonation flag in the JWT. Every action taken during the impersonation session is logged as "superadmin impersonating tenant_id". The session auto-expires and cannot be extended. Requires a mandatory reason field for audit compliance.

**Domain:** admin

**Priority:** High (Sprint 1-2 — needed for customer support from day one)

**Dependencies:** AD-01 (superadmin-login), tenants/T-01, infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required for this endpoint — but the ISSUED token is tenant-scoped
- **Special rules:** Requires admin JWT (RS256, from AD-01). The resulting impersonation token is a tenant-scoped JWT with a special `impersonating=true` claim, NOT an admin JWT. It is used in tenant API endpoints as if the superadmin were a clinic_owner within that tenant.

---

## Endpoint

```
POST /api/v1/admin/tenants/{tenant_id}/impersonate
```

**Rate Limiting:**
- 10 impersonation requests per hour per admin user
- Maximum 3 concurrent active impersonation sessions per admin user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer admin JWT from AD-01 | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| tenant_id | Yes | string (UUID) | Valid tenant UUID | Target tenant to impersonate | tn_a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "reason": "string (required, 10–500 chars) — reason for impersonation; mandatory for audit",
  "duration_minutes": "integer (optional, 1–60, default=60) — session duration; max 60 minutes",
  "role_override": "string (optional) — role to assume within tenant: clinic_owner | doctor | receptionist | assistant; default=clinic_owner",
  "support_ticket_id": "string (optional, max 100) — support ticket reference for traceability"
}
```

**Example Request:**
```json
{
  "reason": "Customer reported odontogram not loading after plan upgrade — investigating rendering bug",
  "duration_minutes": 30,
  "role_override": "clinic_owner",
  "support_ticket_id": "SUPPORT-2847"
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "impersonation_token": "string — tenant-scoped JWT with impersonation claims",
  "token_type": "string — Bearer",
  "expires_in": "integer — seconds until token expires",
  "expires_at": "string (ISO 8601) — absolute expiry time",
  "impersonation_session": {
    "session_id": "string (UUID) — unique ID for this impersonation session",
    "tenant_id": "string — target tenant UUID",
    "clinic_name": "string — target tenant's clinic name",
    "admin_user_id": "string — superadmin who initiated",
    "admin_user_name": "string",
    "assumed_role": "string — role within tenant",
    "reason": "string",
    "support_ticket_id": "string | null",
    "started_at": "string (ISO 8601)",
    "expires_at": "string (ISO 8601)",
    "is_active": "boolean — true"
  },
  "warnings": "array[string] — any relevant warnings (e.g., tenant suspended, trial expiring)",
  "audit_notice": "string — notice that all actions will be logged"
}
```

**Example:**
```json
{
  "impersonation_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbl91c2VyX2lkIiwidGVuYW50X2lkIjoidG5fYTFiMmMzZDQiLCJyb2xlIjoiY2xpbmljX293bmVyIiwiaW1wZXJzb25hdGluZyI6dHJ1ZSwiaW1wZXJzb25hdGlvbl9zZXNzaW9uX2lkIjoic2Vzc19pbXBfYWJjMTIzIiwiaWF0IjoxNzA4ODY2MDAwLCJleHAiOjE3MDg4NjYwMDB9.signature",
  "token_type": "Bearer",
  "expires_in": 1800,
  "expires_at": "2026-02-25T10:30:00Z",
  "impersonation_session": {
    "session_id": "sess_imp_abc123-def456-7890-abcd-ef1234567890",
    "tenant_id": "tn_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "clinic_name": "Clínica Dental Torres",
    "admin_user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "admin_user_name": "Platform Admin",
    "assumed_role": "clinic_owner",
    "reason": "Customer reported odontogram not loading after plan upgrade — investigating rendering bug",
    "support_ticket_id": "SUPPORT-2847",
    "started_at": "2026-02-25T10:00:00Z",
    "expires_at": "2026-02-25T10:30:00Z",
    "is_active": true
  },
  "warnings": [],
  "audit_notice": "NOTICE: All actions taken with this token will be logged as 'superadmin Platform Admin impersonating tenant Clínica Dental Torres (tn_a1b2c3d4)'. This session will expire at 2026-02-25T10:30:00Z."
}
```

### Error Responses

#### 400 Bad Request
**When:** `reason` is too short (< 10 chars) or too long (> 500); `duration_minutes` out of range; `role_override` is not a valid impersonatable role.

**Example:**
```json
{
  "error": "invalid_impersonation_request",
  "message": "Validation errors",
  "details": {
    "reason": ["reason must be at least 10 characters to ensure audit compliance"],
    "duration_minutes": ["duration_minutes must be between 1 and 60"]
  }
}
```

#### 401 Unauthorized
**When:** Admin JWT missing or invalid.

#### 403 Forbidden
**When:** Role is not superadmin; or admin user has exceeded the concurrent session limit (3 active).

**Example (concurrent limit):**
```json
{
  "error": "impersonation_limit_exceeded",
  "message": "Maximum concurrent impersonation sessions (3) reached",
  "details": {
    "active_sessions": [
      { "session_id": "sess_imp_1", "tenant_id": "tn_abc", "expires_at": "2026-02-25T10:15:00Z" },
      { "session_id": "sess_imp_2", "tenant_id": "tn_def", "expires_at": "2026-02-25T10:20:00Z" },
      { "session_id": "sess_imp_3", "tenant_id": "tn_ghi", "expires_at": "2026-02-25T10:25:00Z" }
    ],
    "hint": "Wait for existing sessions to expire or terminate them first"
  }
}
```

#### 404 Not Found
**When:** Tenant with given `tenant_id` does not exist.

**Example:**
```json
{
  "error": "tenant_not_found",
  "message": "Tenant not found",
  "details": { "tenant_id": "tn_a1b2c3d4" }
}
```

#### 409 Conflict
**When:** Admin already has an active impersonation session for this specific tenant.

**Example:**
```json
{
  "error": "already_impersonating",
  "message": "You already have an active impersonation session for this tenant",
  "details": {
    "existing_session_id": "sess_imp_prev123",
    "expires_at": "2026-02-25T10:20:00Z",
    "hint": "Use the existing token or wait for it to expire"
  }
}
```

#### 422 Unprocessable Entity
**When:** `tenant_id` is not a valid UUID; request body Pydantic validation fails.

#### 429 Too Many Requests
**When:** Rate limit exceeded (10 impersonations/hour per admin user).

#### 500 Internal Server Error
**When:** JWT signing failure; unexpected DB error.

---

## Business Logic

**Step-by-step process:**

1. Validate admin JWT and superadmin role.
2. Validate `tenant_id` as valid UUID.
3. Validate request body: `reason` >= 10 chars; `duration_minutes` 1–60; `role_override` valid.
4. Fetch tenant from `tenants` table WHERE `id = tenant_id`. Return 404 if not found.
5. Check concurrent session limit: query `admin_impersonation_sessions` WHERE `admin_user_id = X AND status = 'active' AND expires_at > now()`. If count >= 3, return 403 with list.
6. Check duplicate: same query + `tenant_id = tenant_id`. If found, return 409 with existing session.
7. Compute `expires_at = now() + duration_minutes minutes`.
8. Generate impersonation JWT:
   - Algorithm: RS256 (tenant-side keypair — same as normal tenant JWTs so tenant APIs accept it)
   - Claims:
     ```json
     {
       "sub": "<admin_user_id>",
       "tenant_id": "<tenant_id>",
       "role": "<role_override>",
       "impersonating": true,
       "impersonation_session_id": "<session_id>",
       "impersonating_admin_id": "<admin_user_id>",
       "impersonating_admin_name": "<admin_user_name>",
       "iat": <now>,
       "exp": <expires_at>,
       "iss": "dentalos-impersonation",
       "jti": "<unique_jwt_id>"
     }
     ```
9. Create `admin_impersonation_sessions` record:
   - `session_id`, `admin_user_id`, `tenant_id`, `assumed_role`, `reason`, `support_ticket_id`, `started_at`, `expires_at`, `status='active'`, `jwt_jti`
10. Store session in Redis: `SET admin_impersonation:{session_id} {admin_user_id} EX {duration_seconds}` (for fast revocation checks).
11. Write audit log: action=`impersonation_started`, actor=`admin_user_id`, tenant_id=`tenant_id`, reason=`reason`, support_ticket_id=support_ticket_id, session_id=session_id.
12. Send security alert:
    - Email to all other admins: "Platform Admin started impersonation session for Clínica Dental Torres (SUPPORT-2847)"
    - In-app admin notification
13. Return 201 with token and session details.

**How Impersonation Token is Used:**
- The returned `impersonation_token` is used as a standard Bearer token in ALL tenant-facing API calls.
- Tenant API middleware detects `impersonating=true` in JWT claims and activates impersonation mode.
- In impersonation mode, all audit log entries include:
  - `actor_type: "impersonation"`
  - `actor_admin_id: "<admin_user_id>"`
  - `actor_admin_name: "<admin_user_name>"`
  - `impersonation_session_id: "<session_id>"`
  - `actor_display: "superadmin <admin_name> impersonating <tenant_slug>"`
- This ensures every record created, updated, or read during impersonation is traceable.

**Auto-Expiry:**
- JWT has `exp` claim set to expiry time — no special handling needed at the token validation layer.
- Background job runs every 5 minutes to mark expired sessions as `status='expired'` in `admin_impersonation_sessions` (cleanup; JWT expiry is the actual enforcement).
- Redis key expires automatically (EX duration_seconds).

**Impersonation Restrictions:**
- Impersonating admin CANNOT change the clinic's plan or billing settings (blocked at endpoint level).
- Impersonating admin CANNOT create new admin users or modify role permissions.
- Impersonating admin CANNOT delete the tenant.
- Impersonating admin CANNOT view other impersonation sessions.
- Impersonating admin CAN read and update clinical records, patients, odontograms, etc. (support purposes).
- These restrictions are enforced in the respective endpoint middleware by checking `impersonating=true` + blocked action type.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| tenant_id | Valid UUID | "tenant_id must be a valid UUID" |
| reason | 10–500 chars, non-empty | "reason must be 10–500 characters" |
| duration_minutes | Integer 1–60 | "duration_minutes must be between 1 and 60" |
| role_override | clinic_owner, doctor, receptionist, assistant | "Invalid role; patient role cannot be impersonated" |
| support_ticket_id | Max 100 chars if provided | "support_ticket_id must be <= 100 characters" |

**Business Rules:**

- The `patient` role cannot be impersonated (privacy constraint — superadmin impersonation is for clinical staff workflows only).
- `reason` is mandatory — no impersonation without an audit trail reason.
- Impersonation sessions are immutable after creation (no extension, no role change).
- If the admin initiating impersonation is the same as the clinic owner's email, this is flagged in warnings (unusual — admin testing their own account?).
- Impersonation sessions targeting suspended or cancelled tenants are allowed (support may need to investigate issues on suspended accounts) but generate an additional warning.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant is suspended | 201 Created with warning: "Target tenant is currently suspended" |
| Tenant is cancelled | 201 Created with warning: "Target tenant account is cancelled. Access is limited." |
| Admin tries to impersonate with patient role | 400 Bad Request, "patient role cannot be impersonated" |
| Token used after expiry | JWT validation fails (exp claim); tenant API returns 401 |
| Admin tries to impersonate same tenant twice | 409 Conflict with existing session details |
| duration_minutes=60, admin closes browser | Session expires at 60 min regardless; no early termination (logout endpoint TBD) |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `admin_impersonation_sessions`: INSERT (new session record)

**Tenant schema tables affected:**
- None at creation time; impersonation token is used in subsequent tenant-level requests which may write to tenant schemas (those are the actual support actions).

**Example query (SQLAlchemy):**
```python
session = AdminImpersonationSession(
    id=session_id,
    admin_user_id=admin_user_id,
    tenant_id=tenant_id,
    assumed_role=body.role_override or "clinic_owner",
    reason=body.reason,
    support_ticket_id=body.support_ticket_id,
    jwt_jti=jwt_jti,
    started_at=utcnow(),
    expires_at=expires_at,
    status=ImpersonationStatus.ACTIVE,
)
db_session.add(session)
await db_session.commit()
```

### Cache Operations

**Cache keys affected:**
- `admin_impersonation:{session_id}`: SET (TTL = duration_seconds) — used for fast session lookup and revocation
- `admin_impersonation_active:{admin_user_id}`: INCR (count of active sessions) — for concurrent limit checks

**Cache TTL:** duration_minutes * 60 seconds

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| admin.events | impersonation_started | `{ session_id, admin_user_id, tenant_id, reason, support_ticket_id, expires_at }` | After session created |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** impersonation_started
- **Resource:** admin_impersonation_session
- **PHI involved:** No (session initiation; PHI only if admin subsequently accesses clinical data with the token)

**Note:** All subsequent API calls using the impersonation token will include impersonation context in their own audit entries.

### Notifications

**Notifications triggered:** Yes (security alerting)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | impersonation_alert | All other superadmins | Session created |
| in-app | impersonation_started | Admin panel dashboard | Session created |

---

## Performance

### Expected Response Time
- **Target:** < 400ms (JWT generation + DB write + Redis SET)
- **Maximum acceptable:** < 800ms

### Caching Strategy
- **Strategy:** Redis for session storage and concurrent limit counting
- **Cache key:** `admin_impersonation:{session_id}`
- **TTL:** duration_minutes * 60s

### Database Performance

**Queries executed:** 4–5
1. Fetch tenant by ID
2. Count active sessions for admin (concurrent limit check)
3. Check duplicate session for same tenant
4. INSERT impersonation session
5. Audit log INSERT

**Indexes required:**
- `admin_impersonation_sessions.(admin_user_id, status, expires_at)` — COMPOSITE INDEX for concurrent limit check
- `admin_impersonation_sessions.(admin_user_id, tenant_id, status)` — COMPOSITE INDEX for duplicate check
- `admin_impersonation_sessions.(tenant_id, started_at DESC)` — COMPOSITE INDEX for tenant audit trail
- `admin_impersonation_sessions.(session_id)` — UNIQUE INDEX (primary key)

**N+1 prevention:** All checks done in single queries.

### Pagination

**Pagination:** No (POST endpoint returns single session)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| tenant_id | UUID validation via Pydantic Path | Rejects non-UUID |
| reason | Pydantic min_length=10, max_length=500, strip | Plain text; no HTML |
| duration_minutes | Pydantic integer, ge=1, le=60 | Hard cap at 60 |
| role_override | Pydantic Literal enum (4 valid roles) | Only allowed roles |
| support_ticket_id | Pydantic max_length=100, strip if provided | Alphanumeric + hyphens |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. `reason` stored and returned as plain text.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### JWT Security

- Impersonation JWT uses the same RS256 keypair as regular tenant JWTs so tenant middleware accepts it.
- The `impersonating=true` claim is cryptographically bound to the JWT signature — cannot be forged.
- `jti` (JWT ID) is stored in `admin_impersonation_sessions.jwt_jti` — allows immediate revocation by invalidating the jti in a Redis blocklist if needed.
- `iss: "dentalos-impersonation"` distinguishes from normal tenant JWTs for logging purposes.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None at session creation. Clinical PHI accessed during the session is logged under the impersonation audit trail.

**GDPR/LOPDGDD:** Impersonation sessions are logged for compliance. Tenants can request impersonation history for their account via data subject request process.

---

## Testing

### Test Cases

#### Happy Path
1. Create impersonation session for active tenant
   - **Given:** superadmin JWT, active tenant tn_abc, no existing sessions for that tenant
   - **When:** POST /api/v1/admin/tenants/tn_abc/impersonate with valid reason and duration=30
   - **Then:** 201 Created, impersonation_token returned (valid JWT), session_id created, audit log entry written, security email sent

2. Use impersonation token on tenant API
   - **Given:** impersonation_token from previous step
   - **When:** GET /api/v1/patients (tenant endpoint) with impersonation_token as Bearer
   - **Then:** 200 OK, request processed as clinic_owner; audit log shows "superadmin X impersonating tenant Y"

3. Token auto-expiry
   - **Given:** impersonation token with 1-minute duration
   - **When:** Wait 61 seconds; use token on tenant API
   - **Then:** 401 Unauthorized (JWT exp exceeded)

#### Edge Cases
1. Impersonate suspended tenant
   - **Given:** Tenant with status=suspended
   - **When:** POST impersonate
   - **Then:** 201 Created, warnings includes "Target tenant is currently suspended"

2. role_override=doctor
   - **Given:** superadmin JWT, valid tenant
   - **When:** POST with role_override=doctor
   - **Then:** 201 Created, JWT contains role=doctor, impersonating=true

3. Third concurrent session allowed; fourth rejected
   - **Given:** Admin has 2 active sessions
   - **When:** POST for third tenant
   - **Then:** 201 Created (3rd session OK)
   - **When:** POST for fourth tenant
   - **Then:** 403 Forbidden, impersonation_limit_exceeded with list of active sessions

#### Error Cases
1. Reason too short
   - **Given:** superadmin JWT
   - **When:** POST with reason="fix bug"
   - **Then:** 400 Bad Request, reason must be at least 10 characters

2. Tenant not found
   - **Given:** Non-existent tenant UUID
   - **When:** POST impersonate
   - **Then:** 404 Not Found

3. Duplicate session (same tenant)
   - **Given:** Active impersonation session for tn_abc
   - **When:** POST impersonate tn_abc again
   - **Then:** 409 Conflict with existing session details

4. role_override=patient
   - **Given:** superadmin JWT
   - **When:** POST with role_override=patient
   - **Then:** 400 Bad Request, "patient role cannot be impersonated"

5. Rate limit exceeded
   - **Given:** Admin has made 10 impersonation requests in 1 hour
   - **When:** 11th request
   - **Then:** 429 Too Many Requests

### Test Data Requirements

**Users:** 1 superadmin, other superadmin (for email notification test)

**Patients/Entities:** 4 tenant fixtures (active, suspended, cancelled, deleted); mock JWT signing keys

### Mocking Strategy

- JWT signing: Use test RS256 keypair (deterministic for assertions)
- Redis: fakeredis for session storage and concurrent limit
- Email service: Mock; verify impersonation_alert email sent
- RabbitMQ: In-memory broker; verify impersonation_started event published

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST returns 201 with valid tenant-scoped impersonation JWT
- [ ] JWT contains impersonating=true, impersonation_session_id, assumed_role, correct exp
- [ ] Session persisted to admin_impersonation_sessions table
- [ ] Session stored in Redis (auto-expires)
- [ ] All subsequent API calls with impersonation token show impersonation context in audit logs
- [ ] reason is mandatory (400 if < 10 chars)
- [ ] duration_minutes max 60 (hard cap)
- [ ] Concurrent session limit enforced (max 3 per admin)
- [ ] Duplicate session for same tenant returns 409
- [ ] patient role cannot be impersonated (400)
- [ ] Suspended/cancelled tenant triggers warning (not error)
- [ ] Security email sent to all other admins
- [ ] Token auto-expires at stated time (JWT exp claim)
- [ ] All test cases pass
- [ ] Performance target: < 400ms
- [ ] Quality Hooks passed
- [ ] Audit logging verified (session creation + all subsequent tenant actions)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Early termination of impersonation session (logout endpoint — separate spec)
- Listing active impersonation sessions (separate admin endpoint)
- Impersonation history report (separate reporting endpoint)
- Impersonation of patient role (explicitly excluded for privacy)
- Automatic detection of suspicious impersonation patterns
- Tenant notification that they are being impersonated (intentionally not notified in v1 — support access)

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
- [x] JWT claims fully specified
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Impersonation middleware pattern documented

### Hook 3: Security & Privacy
- [x] Auth level stated (superadmin only)
- [x] JWT security (RS256, jti revocation)
- [x] Impersonation restrictions documented
- [x] Audit trail for all actions
- [x] GDPR compliance noted

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Redis session management
- [x] Indexes listed

### Hook 5: Observability
- [x] Structured logging
- [x] Impersonation audit context in all downstream logs
- [x] Security email alerting

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements
- [x] Mocking strategy
- [x] Acceptance criteria

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
