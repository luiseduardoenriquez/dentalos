# Authentication & Authorization Rules (I-02)

---

## Overview

**Feature:** Global authentication and authorization rules for DentalOS. Defines the JWT-based stateless auth system, role-based access control (RBAC), multi-tenant auth context, token lifecycle, password security, invite flow, patient portal authentication, and all related FastAPI implementation patterns.

**Domain:** infra (cross-cutting)

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy.md)

**Referenced by:** Every authenticated endpoint in the system. This is the foundation spec for all access control.

---

## 1. Authentication Strategy

### 1.1 Overview

DentalOS uses **JWT-based stateless authentication** with a dual-token scheme: a short-lived access token for API authorization and a long-lived single-use refresh token for session continuity.

All tokens are signed with **RS256** (asymmetric) using a private key known only to the backend. Public keys are available for token verification by internal services.

**Why RS256 over HS256:** Asymmetric signing allows future service-to-service token verification without sharing the signing secret. This is important for a SaaS that may evolve toward a distributed backend.

### 1.2 Token Types

| Token | Purpose | Storage | TTL | Signing |
|-------|---------|---------|-----|---------|
| Access Token | Authorize API requests | Client memory (JS variable) | 15 minutes | RS256 JWT |
| Refresh Token | Obtain new token pair | HttpOnly cookie + DB record | 30 days | Opaque UUID v4 |

### 1.3 Access Token -- JWT Structure

**Header:**
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "dentalos-2026-02"
}
```

**Payload (Claims):**
```json
{
  "sub": "usr_550e8400-e29b-41d4-a716-446655440000",
  "tid": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "role": "doctor",
  "perms": ["patients:read", "patients:write", "odontogram:write", "clinical_records:write"],
  "email": "doctor@clinica.co",
  "name": "Dr. Maria Rodriguez",
  "iat": 1708790400,
  "exp": 1708791300,
  "iss": "dentalos",
  "aud": "dentalos-api",
  "jti": "tok_a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Claim Definitions:**

| Claim | Type | Required | Description |
|-------|------|----------|-------------|
| `sub` | string | Yes | User ID, prefixed `usr_` |
| `tid` | string | Yes | Tenant ID, prefixed `tn_`. Null for superadmin. |
| `role` | string | Yes | User role within the tenant |
| `perms` | string[] | Yes | Computed permissions array for this role |
| `email` | string | Yes | User email address |
| `name` | string | Yes | User display name |
| `iat` | int | Yes | Issued-at timestamp (Unix epoch) |
| `exp` | int | Yes | Expiration timestamp (Unix epoch) |
| `iss` | string | Yes | Issuer, always `"dentalos"` |
| `aud` | string | Yes | Audience, `"dentalos-api"` for staff, `"dentalos-portal"` for patients |
| `jti` | string | Yes | Unique token ID for revocation tracking |

**Token size consideration:** The `perms` array is embedded to avoid a DB lookup on every request. For the defined roles, the permissions array never exceeds 25 entries, keeping the JWT under 1 KB.

### 1.4 Refresh Token Structure

Refresh tokens are **not JWTs**. They are opaque UUIDs stored in the database with metadata.

**Database schema (shared `public` schema):**

```sql
CREATE TABLE public.refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash      VARCHAR(128) NOT NULL UNIQUE,  -- SHA-256 hash of the token
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    tenant_id       UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    device_info     JSONB,                          -- user-agent, IP, device name
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    revoked_reason  VARCHAR(50),                    -- 'rotation' | 'logout' | 'password_change' | 'security'
    replaced_by     UUID REFERENCES public.refresh_tokens(id),
    created_ip      INET NOT NULL,

    CONSTRAINT refresh_token_not_expired CHECK (expires_at > issued_at)
);

CREATE INDEX idx_refresh_tokens_user ON public.refresh_tokens(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_refresh_tokens_hash ON public.refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires ON public.refresh_tokens(expires_at) WHERE revoked_at IS NULL;
```

**Key design decisions:**
- The raw token is **never stored** in the database. Only the SHA-256 hash is stored.
- `replaced_by` creates a chain for replay detection.
- `device_info` enables multi-device session listing (post-MVP).
- Expired and revoked tokens are cleaned up by a daily background job.

---

## 2. Token Lifecycle

### 2.1 Login Flow

```
Client                          Backend                         Database
  |                                |                               |
  |  POST /api/v1/auth/login       |                               |
  |  {email, password}             |                               |
  |------------------------------->|                               |
  |                                |  1. Validate input             |
  |                                |  2. Look up user by email      |
  |                                |------------------------------→|
  |                                |  3. Verify password (bcrypt)   |
  |                                |  4. Check account status       |
  |                                |     (active, not locked)       |
  |                                |  5. Check login rate limit     |
  |                                |  6. Generate access token JWT  |
  |                                |  7. Generate refresh token     |
  |                                |  8. Hash & store refresh token |
  |                                |------------------------------→|
  |                                |  9. Reset failed login counter |
  |                                |------------------------------→|
  |  200 OK                        |                               |
  |  {access_token, user, tenant}  |                               |
  |  Set-Cookie: refresh_token     |                               |
  |<-------------------------------|                               |
```

**Response payload:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "usr_550e8400-e29b-41d4-a716-446655440000",
    "email": "doctor@clinica.co",
    "name": "Dr. Maria Rodriguez",
    "role": "doctor",
    "avatar_url": "https://..."
  },
  "tenant": {
    "id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "name": "Clinica Dental Sonrisa",
    "plan": "professional",
    "country": "CO"
  }
}
```

**Refresh token delivery:** Set via `Set-Cookie` header with the following attributes:
```
Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=2592000
```

- `HttpOnly`: Not accessible via JavaScript (XSS protection).
- `Secure`: Only sent over HTTPS.
- `SameSite=Strict`: Not sent on cross-origin requests (CSRF protection).
- `Path=/api/v1/auth`: Only sent to auth endpoints (minimizes exposure).

### 2.2 Token Refresh Flow

```
Client                          Backend                         Database
  |                                |                               |
  |  POST /api/v1/auth/refresh     |                               |
  |  Cookie: refresh_token=<old>   |                               |
  |------------------------------->|                               |
  |                                |  1. Extract token from cookie  |
  |                                |  2. Hash token (SHA-256)       |
  |                                |  3. Look up by hash            |
  |                                |------------------------------→|
  |                                |  4. Check: not revoked?        |
  |                                |  5. Check: not expired?        |
  |                                |  6. Revoke old token           |
  |                                |     (reason: 'rotation')       |
  |                                |  7. Generate new token pair    |
  |                                |  8. Store new refresh token    |
  |                                |     (old.replaced_by = new.id) |
  |                                |------------------------------→|
  |  200 OK                        |                               |
  |  {access_token}                |                               |
  |  Set-Cookie: refresh_token     |                               |
  |<-------------------------------|                               |
```

**Critical rule:** Every refresh token is **single-use**. Upon successful rotation, the old token is immediately revoked and linked to its replacement via `replaced_by`.

### 2.3 Replay Detection (Token Theft Mitigation)

If a revoked refresh token is presented, this indicates a potential session compromise -- either the legitimate user or an attacker is using a stale token.

**Detection flow:**
```
Client presents revoked refresh token
  |
  v
Backend detects: token exists but revoked_at IS NOT NULL
  |
  v
Follow the replaced_by chain to find the entire token family
  |
  v
Revoke ALL active refresh tokens for this user (reason: 'security')
  |
  v
Return 401 with error code 'session_compromised'
  |
  v
Log security event: attempted refresh token replay
  |
  v
(Post-MVP) Send security alert email to user
```

**Implementation rule:** When a revoked refresh token is detected:
1. All active refresh tokens for that `user_id` are revoked with `revoked_reason = 'security'`.
2. The response is `401 Unauthorized` with error code `session_compromised`.
3. The user must re-authenticate on all devices.
4. An entry is written to the audit log with severity `SECURITY`.

### 2.4 Logout Flow

```
Client                          Backend                         Database
  |                                |                               |
  |  POST /api/v1/auth/logout      |                               |
  |  Cookie: refresh_token=<token> |                               |
  |  Authorization: Bearer <jwt>   |                               |
  |------------------------------->|                               |
  |                                |  1. Revoke refresh token       |
  |                                |     (reason: 'logout')         |
  |                                |------------------------------→|
  |                                |  2. Add access token JTI to    |
  |                                |     Redis blacklist            |
  |                                |     (TTL = token remaining TTL)|
  |                                |------------------------------→|  (Redis)
  |  204 No Content                |                               |
  |  Set-Cookie: refresh_token=;   |                               |
  |    expires=epoch               |                               |
  |<-------------------------------|                               |
```

**Access token blacklist:** Since JWTs are stateless, a logout cannot truly invalidate them. For immediate logout, the `jti` of the access token is added to a Redis set with a TTL equal to the token's remaining lifetime (at most 15 minutes). The `get_current_user` dependency checks this blacklist.

**Redis key pattern:**
```
dentalos:token_blacklist:{jti}  ->  "1"  (TTL: remaining seconds)
```

### 2.5 Force Logout All Devices

Triggered by:
- Password change (`auth/change-password.md`)
- Password reset (`auth/reset-password.md`)
- Account security event (replay detection)
- Explicit "log out everywhere" action

**Process:**
1. Revoke all active refresh tokens for the user (`revoked_reason = 'password_change'` or `'security'`).
2. Increment a per-user token version counter in Redis:
   ```
   dentalos:user_token_version:{user_id}  ->  integer (no TTL)
   ```
3. When validating access tokens, compare the token's `iat` against the timestamp of the last version increment. If the token was issued before the version change, reject it.

This avoids needing to blacklist every individual access token JTI.

---

## 3. Role-Based Access Control (RBAC)

### 3.1 Role Hierarchy

DentalOS defines six roles across two auth contexts:

**Clinic context (tenant-scoped):**

| Role | Numeric Level | Description |
|------|--------------|-------------|
| `clinic_owner` | 100 | Clinic administrator. Full tenant access. |
| `doctor` | 80 | Licensed dentist. Full clinical access. |
| `assistant` | 60 | Dental assistant. Limited clinical access. |
| `receptionist` | 40 | Front desk. Administrative access. |
| `patient` | 10 | Patient portal. Own data only. |

**Platform context (not tenant-scoped):**

| Role | Numeric Level | Description |
|------|--------------|-------------|
| `superadmin` | 200 | DentalOS platform administrator. |

The numeric levels exist to support "at least this level" checks when useful, but **permission-based checks are always preferred** over level comparisons.

### 3.2 Permission Definitions

Permissions follow the format `resource:action` with optional sub-resource specificity.

**Resource actions:**
- `read` -- View/list resources
- `write` -- Create resources
- `update` -- Modify existing resources
- `delete` -- Remove/deactivate resources
- `manage` -- Full CRUD + configuration (implies read, write, update, delete)
- `export` -- Export/download data
- `approve` -- Approve/authorize actions (e.g., treatment plans)

**Full permission catalog:**

```python
class Permission(str, Enum):
    # Patients
    PATIENTS_READ = "patients:read"
    PATIENTS_WRITE = "patients:write"
    PATIENTS_UPDATE = "patients:update"
    PATIENTS_DELETE = "patients:delete"
    PATIENTS_EXPORT = "patients:export"
    PATIENTS_IMPORT = "patients:import"
    PATIENTS_MERGE = "patients:merge"

    # Odontogram
    ODONTOGRAM_READ = "odontogram:read"
    ODONTOGRAM_WRITE = "odontogram:write"

    # Clinical Records
    CLINICAL_RECORDS_READ = "clinical_records:read"
    CLINICAL_RECORDS_WRITE = "clinical_records:write"
    CLINICAL_RECORDS_UPDATE = "clinical_records:update"

    # Diagnoses
    DIAGNOSES_READ = "diagnoses:read"
    DIAGNOSES_WRITE = "diagnoses:write"
    DIAGNOSES_UPDATE = "diagnoses:update"

    # Treatment Plans
    TREATMENT_PLANS_READ = "treatment_plans:read"
    TREATMENT_PLANS_WRITE = "treatment_plans:write"
    TREATMENT_PLANS_UPDATE = "treatment_plans:update"
    TREATMENT_PLANS_APPROVE = "treatment_plans:approve"

    # Prescriptions
    PRESCRIPTIONS_READ = "prescriptions:read"
    PRESCRIPTIONS_WRITE = "prescriptions:write"

    # Consents
    CONSENTS_READ = "consents:read"
    CONSENTS_WRITE = "consents:write"
    CONSENTS_VOID = "consents:void"

    # Appointments
    APPOINTMENTS_READ = "appointments:read"
    APPOINTMENTS_WRITE = "appointments:write"
    APPOINTMENTS_UPDATE = "appointments:update"
    APPOINTMENTS_DELETE = "appointments:delete"

    # Billing
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    BILLING_UPDATE = "billing:update"
    BILLING_MANAGE = "billing:manage"

    # Users / Team
    TEAM_READ = "team:read"
    TEAM_WRITE = "team:write"
    TEAM_UPDATE = "team:update"
    TEAM_DELETE = "team:delete"

    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_MANAGE = "settings:manage"

    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # Notifications
    NOTIFICATIONS_READ = "notifications:read"
    NOTIFICATIONS_MANAGE = "notifications:manage"

    # Messages
    MESSAGES_READ = "messages:read"
    MESSAGES_WRITE = "messages:write"

    # Compliance
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_MANAGE = "compliance:manage"

    # Audit Trail
    AUDIT_TRAIL_READ = "audit_trail:read"

    # Portal Access Management
    PORTAL_MANAGE = "portal:manage"
```

### 3.3 Permission Matrix

| Permission | clinic_owner | doctor | assistant | receptionist | patient |
|------------|:---:|:---:|:---:|:---:|:---:|
| `patients:read` | Y | Y | Y | Y | Own |
| `patients:write` | Y | Y | -- | Y | -- |
| `patients:update` | Y | Y | -- | Y | -- |
| `patients:delete` | Y | -- | -- | -- | -- |
| `patients:export` | Y | -- | -- | -- | -- |
| `patients:import` | Y | -- | -- | -- | -- |
| `patients:merge` | Y | -- | -- | -- | -- |
| `odontogram:read` | Y | Y | Y | -- | Own |
| `odontogram:write` | Y | Y | Y | -- | -- |
| `clinical_records:read` | Y | Y | Y | -- | Own |
| `clinical_records:write` | Y | Y | Y | -- | -- |
| `clinical_records:update` | Y | Y | -- | -- | -- |
| `diagnoses:read` | Y | Y | Y | -- | Own |
| `diagnoses:write` | Y | Y | -- | -- | -- |
| `diagnoses:update` | Y | Y | -- | -- | -- |
| `treatment_plans:read` | Y | Y | Y | Y | Own |
| `treatment_plans:write` | Y | Y | -- | -- | -- |
| `treatment_plans:update` | Y | Y | -- | -- | -- |
| `treatment_plans:approve` | Y | Y | -- | -- | Own |
| `prescriptions:read` | Y | Y | Y | -- | Own |
| `prescriptions:write` | Y | Y | -- | -- | -- |
| `consents:read` | Y | Y | Y | Y | Own |
| `consents:write` | Y | Y | -- | -- | -- |
| `consents:void` | Y | -- | -- | -- | -- |
| `appointments:read` | Y | Y | Y | Y | Own |
| `appointments:write` | Y | Y | Y | Y | Own |
| `appointments:update` | Y | Y | Y | Y | -- |
| `appointments:delete` | Y | Y | -- | Y | -- |
| `billing:read` | Y | Y | -- | Y | Own |
| `billing:write` | Y | -- | -- | Y | -- |
| `billing:update` | Y | -- | -- | Y | -- |
| `billing:manage` | Y | -- | -- | -- | -- |
| `team:read` | Y | Y | Y | Y | -- |
| `team:write` | Y | -- | -- | -- | -- |
| `team:update` | Y | -- | -- | -- | -- |
| `team:delete` | Y | -- | -- | -- | -- |
| `settings:read` | Y | Y | Y | Y | -- |
| `settings:manage` | Y | -- | -- | -- | -- |
| `analytics:read` | Y | Y | -- | -- | -- |
| `analytics:export` | Y | -- | -- | -- | -- |
| `notifications:read` | Y | Y | Y | Y | Y |
| `notifications:manage` | Y | -- | -- | -- | -- |
| `messages:read` | Y | Y | Y | Y | Own |
| `messages:write` | Y | Y | Y | Y | Own |
| `compliance:read` | Y | -- | -- | -- | -- |
| `compliance:manage` | Y | -- | -- | -- | -- |
| `audit_trail:read` | Y | -- | -- | -- | -- |
| `portal:manage` | Y | -- | -- | -- | -- |

**Legend:** `Y` = full access, `Own` = only own data (patient portal context), `--` = no access.

**Notes on "Own" access:**
- The patient role never uses the standard API endpoints. Patient access is exclusively through `/api/v1/portal/*` endpoints.
- "Own" means the patient can only access records where `patient_id` matches their linked patient record.
- Patient permissions are not included in the JWT `perms` array. Instead, the portal auth context enforces own-data-only access at the dependency level.

### 3.4 Role-to-Permission Mapping (Code)

```python
# app/auth/permissions.py

from enum import Enum
from typing import Dict, FrozenSet

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "clinic_owner": frozenset([
        "patients:read", "patients:write", "patients:update", "patients:delete",
        "patients:export", "patients:import", "patients:merge",
        "odontogram:read", "odontogram:write",
        "clinical_records:read", "clinical_records:write", "clinical_records:update",
        "diagnoses:read", "diagnoses:write", "diagnoses:update",
        "treatment_plans:read", "treatment_plans:write", "treatment_plans:update",
        "treatment_plans:approve",
        "prescriptions:read", "prescriptions:write",
        "consents:read", "consents:write", "consents:void",
        "appointments:read", "appointments:write", "appointments:update",
        "appointments:delete",
        "billing:read", "billing:write", "billing:update", "billing:manage",
        "team:read", "team:write", "team:update", "team:delete",
        "settings:read", "settings:manage",
        "analytics:read", "analytics:export",
        "notifications:read", "notifications:manage",
        "messages:read", "messages:write",
        "compliance:read", "compliance:manage",
        "audit_trail:read",
        "portal:manage",
    ]),

    "doctor": frozenset([
        "patients:read", "patients:write", "patients:update",
        "odontogram:read", "odontogram:write",
        "clinical_records:read", "clinical_records:write", "clinical_records:update",
        "diagnoses:read", "diagnoses:write", "diagnoses:update",
        "treatment_plans:read", "treatment_plans:write", "treatment_plans:update",
        "treatment_plans:approve",
        "prescriptions:read", "prescriptions:write",
        "consents:read", "consents:write",
        "appointments:read", "appointments:write", "appointments:update",
        "appointments:delete",
        "billing:read",
        "team:read",
        "settings:read",
        "analytics:read",
        "notifications:read",
        "messages:read", "messages:write",
    ]),

    "assistant": frozenset([
        "patients:read",
        "odontogram:read", "odontogram:write",
        "clinical_records:read", "clinical_records:write",
        "diagnoses:read",
        "treatment_plans:read",
        "prescriptions:read",
        "consents:read",
        "appointments:read", "appointments:write", "appointments:update",
        "team:read",
        "settings:read",
        "notifications:read",
        "messages:read", "messages:write",
    ]),

    "receptionist": frozenset([
        "patients:read", "patients:write", "patients:update",
        "treatment_plans:read",
        "consents:read",
        "appointments:read", "appointments:write", "appointments:update",
        "appointments:delete",
        "billing:read", "billing:write", "billing:update",
        "team:read",
        "settings:read",
        "notifications:read",
        "messages:read", "messages:write",
    ]),

    "patient": frozenset([
        # Patient permissions are enforced at the portal endpoint level,
        # not via the standard permission system. This set exists for
        # completeness and token generation, but the portal dependency
        # enforces own-data-only access independently.
        "notifications:read",
    ]),
}
```

### 3.5 Superadmin Permissions

Superadmins operate in a **separate auth context** with their own permission set:

```python
SUPERADMIN_PERMISSIONS: FrozenSet[str] = frozenset([
    "platform:tenants:manage",
    "platform:plans:manage",
    "platform:analytics:read",
    "platform:feature_flags:manage",
    "platform:system_health:read",
    "platform:impersonate",
])
```

Superadmin tokens use `aud: "dentalos-admin"` and do not carry a `tid` claim. Superadmin endpoints live under `/api/v1/admin/*` and `/api/v1/superadmin/*` and use a separate `get_current_superadmin()` dependency.

---

## 4. Multi-Tenant Auth Context

### 4.1 Tenant Resolution

Every authenticated API request (except superadmin and public endpoints) is scoped to a single tenant.

**Resolution order:**
1. Extract `tid` claim from the validated JWT access token.
2. Validate that the tenant exists and is active (checked against a Redis cache, falling back to DB).
3. Inject the tenant context into the request state.

There is **no secondary resolution** via subdomain or header. The JWT is the single source of truth for tenant identity.

### 4.2 Tenant Context Object

```python
# app/auth/context.py

from dataclasses import dataclass
from uuid import UUID
from typing import Optional

@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context injected into every authenticated request."""
    tenant_id: UUID
    schema_name: str          # e.g., "tenant_7c9e6679"
    plan: str                 # e.g., "professional"
    country: str              # ISO 3166-1 alpha-2: "CO", "MX", "CL", etc.
    is_active: bool
    max_doctors: int
    max_patients: int

@dataclass(frozen=True)
class AuthenticatedUser:
    """Current user with full auth context."""
    user_id: UUID
    email: str
    name: str
    role: str
    permissions: frozenset[str]
    tenant: TenantContext
    token_jti: str            # For blacklist checking on logout
```

### 4.3 Tenant Isolation Guarantee

**Rule:** Each authenticated session is scoped to exactly ONE tenant at a time. A user may hold memberships in multiple tenants, but a single JWT can only carry one `tid` claim.

This is enforced at:
1. **Registration:** A user record is created in `public.users`. Their first tenant membership is recorded in `public.user_tenant_memberships`.
2. **Invite acceptance:** The invited user gains a new membership record for the inviting tenant.
3. **JWT issuance:** The `tid` claim is always set to the tenant selected at login (or via `POST /api/v1/auth/select-tenant`). A single JWT is never scoped to multiple tenants.
4. **Database queries:** All queries execute against the tenant-specific schema, resolved from `TenantContext.schema_name`. A session scoped to Tenant A can never access Tenant B's schema.

**Multi-clinic support:** Users may belong to multiple clinics via `public.user_tenant_memberships`. The login flow handles tenant selection when multiple active memberships exist. See Section 4.5 for full details.

### 4.4 Tenant Status Enforcement

| Tenant Status | API Access | Auth Behavior |
|---------------|-----------|---------------|
| `active` | Full access | Normal |
| `suspended` | Read-only | Login allowed, write operations return 403 with `tenant_suspended` error |
| `cancelled` | No access | Login returns 403 with `tenant_cancelled` error |
| `provisioning` | No access | Login returns 503 with `tenant_provisioning` error |

### 4.5 Multi-Clinic Doctor Flow

#### Architecture

A real dental professional commonly works across 2-6 clinics simultaneously. DentalOS supports this via the `public.user_tenant_memberships` junction table, which links a global user account to one or more tenant (clinic) accounts.

Key design points:

- A user's global identity lives in `public.users` (one record, one email, one password).
- Each clinic is a separate tenant with its own schema (e.g., `tenant_7c9e6679`).
- `public.user_tenant_memberships` links a `user_id` to a `tenant_id` with a `role` and `status`.
- The JWT `tid` claim determines which tenant schema is active for the current session.
- A doctor's personal preferences (note templates, voice settings, specialties) are stored in their global `public.users` profile and are available regardless of which clinic they are currently working in.
- Each tenant membership grants a role that may differ per clinic (e.g., a doctor may be `doctor` at one clinic and `clinic_owner` at their own practice).

```sql
-- Conceptual structure (full DDL in database-architecture.md)
CREATE TABLE public.user_tenant_memberships (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    role        VARCHAR(50) NOT NULL,       -- 'clinic_owner' | 'doctor' | 'assistant' | 'receptionist'
    status      VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active' | 'suspended' | 'removed'
    is_primary  BOOLEAN NOT NULL DEFAULT false,
    invited_by  UUID REFERENCES public.users(id),
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, tenant_id)
);
CREATE INDEX idx_utm_user_id ON public.user_tenant_memberships(user_id) WHERE status = 'active';
```

#### Login Flow

```
Client                          Backend                         Database
  |                                |                               |
  |  POST /api/v1/auth/login       |                               |
  |  {email, password}             |                               |
  |------------------------------->|                               |
  |                                |  1. Authenticate user          |
  |                                |     (verify password, check    |
  |                                |     locks, rate limits)        |
  |                                |                               |
  |                                |  2. Query active memberships   |
  |                                |  SELECT * FROM                 |
  |                                |  user_tenant_memberships       |
  |                                |  WHERE user_id = ? AND         |
  |                                |  status = 'active'             |
  |                                |------------------------------→|
  |                                |                               |
  |                                |  3a. If 1 membership:          |
  |                                |      Auto-select tenant        |
  |                                |      Issue JWT with tenant_id  |
  |  200 OK                        |                               |
  |  {access_token, tenant, ...}   |                               |
  |<-------------------------------|                               |
  |                                |                               |
  |                                |  3b. If 2+ memberships:        |
  |                                |      Return tenant list,       |
  |                                |      NO JWT yet                |
  |  200 OK                        |                               |
  |  {requires_tenant_selection,   |                               |
  |   tenants: [...]}              |                               |
  |<-------------------------------|                               |
  |                                |                               |
  |  POST /api/v1/auth/select-tenant                               |
  |  {tenant_id}                   |                               |
  |------------------------------->|                               |
  |                                |  4. Verify membership active   |
  |                                |  5. Issue JWT with tenant_id   |
  |  200 OK                        |                               |
  |  {access_token, tenant, ...}   |                               |
  |<-------------------------------|                               |
```

**Step-by-step:**

1. User authenticates with email + password (standard credential verification).
2. System queries `public.user_tenant_memberships` for all memberships with `status = 'active'`.
3. If 0 active memberships → return 403 `no_active_clinics`.
4. If 1 active membership → auto-select that tenant, issue JWT with `tenant_id`, return full token response.
5. If 2+ active memberships → return `requires_tenant_selection: true` plus the tenants list. Do NOT issue a JWT at this stage.
6. Client presents the clinic list to the user (clinic name, logo, role at each clinic).
7. User selects a clinic → client calls `POST /api/v1/auth/select-tenant` with the chosen `tenant_id`.
8. Backend verifies the user still has an active membership in that tenant, then issues the tenant-scoped JWT pair.

#### Tenant Switching

Once authenticated, a user can switch to any of their other active clinics without re-entering their password.

**Endpoint:** `POST /api/v1/auth/switch-tenant`

**Request:**
```json
{
  "tenant_id": "tn_3f8a1234-ab12-4321-bcde-123456789abc"
}
```

**Behavior:**
- Requires a valid access token (standard `Authorization: Bearer` header).
- Backend verifies the user has an active membership in the requested tenant.
- Issues a new JWT pair (`access_token` + `refresh_token`) scoped to the selected tenant.
- The old access token remains valid until its natural expiry (max 15 min), but the old refresh token is revoked and replaced.
- No password re-entry required.
- Rate limited: 10 switches per hour per user (Redis sliding window: `dentalos:tenant_switch_rate:{user_id}`).

**Response:** Same structure as a normal login success response (single-tenant schema), with the new tenant's context.

#### select-tenant Endpoint

**Endpoint:** `POST /api/v1/auth/select-tenant`

This endpoint is called immediately after a multi-tenant login response (`requires_tenant_selection: true`). It is public (no JWT required) because the JWT has not been issued yet at this stage.

**Request:**
```json
{
  "tenant_id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

**Validations:**
- The `tenant_id` must correspond to one of the active memberships returned at login. The backend re-queries `public.user_tenant_memberships` to confirm.
- The user identity is resolved from a short-lived pre-auth token issued during the login response (stored in Redis: `dentalos:preauth:{token}` with 5-minute TTL), **not** from a JWT.
- If the pre-auth token has expired, the user must log in again.

#### Security Rules

| Rule | Detail |
|------|--------|
| Membership verification on every JWT issuance | User can only receive a JWT for a tenant where they have `status = 'active'` membership |
| Suspended membership | A user with a suspended membership in Clinic A cannot obtain a JWT for Clinic A, but can still log into Clinic B if that membership is active |
| Membership removal | When a membership is removed (`status = 'removed'`), the user's active refresh tokens for that tenant are immediately revoked. Active access tokens for that tenant expire naturally (within 15 min) |
| Data isolation maintained | Switching tenants issues a completely new JWT with a different `tid`. The previous tenant's schema is never accessible from the new session |
| Cross-tenant data access | Forbidden by design. The JWT `tid` determines the schema; there is no mechanism for a single request to span multiple tenant schemas |
| Rate limiting on switches | 10 tenant switches per hour per user to prevent abuse |

---

## 5. FastAPI Implementation

### 5.1 Security Scheme

```python
# app/auth/scheme.py

from fastapi.security import OAuth2PasswordBearer

# Standard staff authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True,
)

# Patient portal authentication (separate token URL)
portal_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/portal/auth/login",
    auto_error=True,
)
```

### 5.2 JWT Creation

```python
# app/auth/jwt.py

import jwt
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
from typing import Optional

from app.config import settings
from app.auth.permissions import ROLE_PERMISSIONS

# Load RSA keys at startup
_private_key = open(settings.JWT_PRIVATE_KEY_PATH).read()
_public_key = open(settings.JWT_PUBLIC_KEY_PATH).read()

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)


def create_access_token(
    user_id: UUID,
    tenant_id: Optional[UUID],
    role: str,
    email: str,
    name: str,
    audience: str = "dentalos-api",
) -> tuple[str, str]:
    """
    Create a signed JWT access token.

    Returns:
        Tuple of (encoded_jwt, jti)
    """
    jti = f"tok_{uuid4()}"
    permissions = list(ROLE_PERMISSIONS.get(role, frozenset()))

    now = datetime.now(timezone.utc)
    payload = {
        "sub": f"usr_{user_id}",
        "tid": f"tn_{tenant_id}" if tenant_id else None,
        "role": role,
        "perms": permissions,
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "iss": "dentalos",
        "aud": audience,
        "jti": jti,
    }

    encoded = jwt.encode(
        payload,
        _private_key,
        algorithm="RS256",
        headers={"kid": settings.JWT_KEY_ID},
    )
    return encoded, jti


def create_refresh_token() -> tuple[str, str]:
    """
    Create an opaque refresh token.

    Returns:
        Tuple of (raw_token, token_hash) -- store the hash, send the raw token.
    """
    raw_token = str(uuid4())
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is invalid.
    """
    return jwt.decode(
        token,
        _public_key,
        algorithms=["RS256"],
        issuer="dentalos",
        audience=["dentalos-api", "dentalos-portal", "dentalos-admin"],
        options={
            "require": ["sub", "tid", "role", "exp", "iat", "jti"],
        },
    )
```

### 5.3 Core Authentication Dependency -- `get_current_user()`

```python
# app/auth/dependencies.py

from fastapi import Depends, HTTPException, status, Request
from uuid import UUID
import jwt

from app.auth.scheme import oauth2_scheme
from app.auth.jwt import decode_access_token
from app.auth.context import AuthenticatedUser, TenantContext
from app.cache.redis import redis_client
from app.db.tenant_registry import get_tenant_info


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> AuthenticatedUser:
    """
    Core authentication dependency.

    Validates the JWT access token, checks the blacklist, resolves
    tenant context, and returns an AuthenticatedUser.

    Usage:
        @router.get("/patients")
        async def list_patients(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    # 1. Decode and validate JWT
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "token_expired",
                "message": "Access token has expired. Use refresh token to obtain a new one.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "token_invalid",
                "message": "Access token is invalid.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload["jti"]

    # 2. Check token blacklist (for post-logout invalidation)
    is_blacklisted = await redis_client.exists(f"dentalos:token_blacklist:{jti}")
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "token_revoked",
                "message": "This token has been revoked.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Check user token version (for force-logout-all)
    user_id_raw = payload["sub"].replace("usr_", "")
    version_key = f"dentalos:user_token_version:{user_id_raw}"
    version_ts = await redis_client.get(version_key)
    if version_ts and payload["iat"] < float(version_ts):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "session_invalidated",
                "message": "All sessions have been invalidated. Please log in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Resolve tenant context
    tenant_id_raw = payload.get("tid")
    tenant_context = None
    if tenant_id_raw:
        tenant_id = UUID(tenant_id_raw.replace("tn_", ""))
        tenant_info = await get_tenant_info(tenant_id)  # Redis-cached, DB fallback

        if not tenant_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "tenant_not_found",
                    "message": "Tenant does not exist.",
                },
            )

        if tenant_info.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "tenant_cancelled",
                    "message": "This clinic account has been cancelled.",
                },
            )

        if tenant_info.status == "suspended":
            # Allow read operations, block writes -- enforced per-endpoint
            pass

        if tenant_info.status == "provisioning":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "tenant_provisioning",
                    "message": "Your clinic is being set up. Please try again shortly.",
                },
            )

        tenant_context = TenantContext(
            tenant_id=tenant_id,
            schema_name=tenant_info.schema_name,
            plan=tenant_info.plan,
            country=tenant_info.country,
            is_active=tenant_info.status == "active",
            max_doctors=tenant_info.max_doctors,
            max_patients=tenant_info.max_patients,
        )

    # 5. Build and return authenticated user
    return AuthenticatedUser(
        user_id=UUID(user_id_raw),
        email=payload["email"],
        name=payload["name"],
        role=payload["role"],
        permissions=frozenset(payload.get("perms", [])),
        tenant=tenant_context,
        token_jti=jti,
    )
```

### 5.4 Role Check Dependency -- `require_role()`

```python
# app/auth/dependencies.py (continued)

from typing import List
from functools import wraps


def require_role(allowed_roles: List[str]):
    """
    Dependency factory that checks if the current user has one of the allowed roles.

    Usage:
        @router.post("/users/{user_id}/deactivate")
        async def deactivate_user(
            user_id: UUID,
            current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
        ):
            ...
    """
    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_role",
                    "message": f"This action requires one of the following roles: {', '.join(allowed_roles)}.",
                    "details": {
                        "required_roles": allowed_roles,
                        "current_role": current_user.role,
                    },
                },
            )
        return current_user

    return role_checker
```

### 5.5 Permission Check Dependency -- `require_permission()`

```python
# app/auth/dependencies.py (continued)

def require_permission(permission: str):
    """
    Dependency factory that checks if the current user has a specific permission.

    Usage:
        @router.post("/patients")
        async def create_patient(
            body: PatientCreate,
            current_user: AuthenticatedUser = Depends(require_permission("patients:write")),
        ):
            ...
    """
    async def permission_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_permission",
                    "message": f"You do not have permission to perform this action.",
                    "details": {
                        "required_permission": permission,
                        "current_role": current_user.role,
                    },
                },
            )
        return current_user

    return permission_checker
```

### 5.6 Tenant Write Guard

For suspended tenants, read operations are allowed but writes must be blocked:

```python
# app/auth/dependencies.py (continued)

def require_active_tenant():
    """
    Dependency that ensures the tenant is fully active (not suspended).
    Use on all write/mutating endpoints.

    Usage:
        @router.post("/patients")
        async def create_patient(
            body: PatientCreate,
            current_user: AuthenticatedUser = Depends(require_permission("patients:write")),
            _active: None = Depends(require_active_tenant()),
        ):
            ...
    """
    async def active_tenant_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> None:
        if current_user.tenant and not current_user.tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "tenant_suspended",
                    "message": "Your clinic account is suspended. Only read operations are allowed.",
                },
            )
        return None

    return active_tenant_checker
```

### 5.7 Superadmin Authentication

```python
# app/auth/dependencies.py (continued)

from app.auth.scheme import oauth2_scheme  # Reuses same scheme, different validation

async def get_current_superadmin(
    token: str = Depends(oauth2_scheme),
) -> AuthenticatedUser:
    """
    Authentication dependency for superadmin endpoints.

    Validates that the token has audience 'dentalos-admin' and role 'superadmin'.
    Superadmin tokens do not carry tenant context.

    Usage:
        @router.get("/admin/tenants")
        async def list_tenants(
            admin: AuthenticatedUser = Depends(get_current_superadmin),
        ):
            ...
    """
    try:
        payload = jwt.decode(
            token,
            _public_key,
            algorithms=["RS256"],
            issuer="dentalos",
            audience="dentalos-admin",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_admin_token",
                "message": "Invalid or missing superadmin credentials.",
            },
        )

    if payload.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "not_superadmin",
                "message": "This endpoint requires superadmin access.",
            },
        )

    return AuthenticatedUser(
        user_id=UUID(payload["sub"].replace("usr_", "")),
        email=payload["email"],
        name=payload["name"],
        role="superadmin",
        permissions=frozenset(payload.get("perms", [])),
        tenant=None,  # Superadmins are not tenant-scoped
        token_jti=payload["jti"],
    )
```

### 5.8 Composing Dependencies -- Real Endpoint Example

```python
# app/api/v1/patients/router.py

from fastapi import APIRouter, Depends
from uuid import UUID

from app.auth.dependencies import (
    get_current_user,
    require_role,
    require_permission,
    require_active_tenant,
)
from app.auth.context import AuthenticatedUser
from app.schemas.patient import PatientCreate, PatientResponse, PatientList

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.get("", response_model=PatientList)
async def list_patients(
    current_user: AuthenticatedUser = Depends(require_permission("patients:read")),
):
    """List patients in the current tenant."""
    # current_user.tenant.schema_name is used to query the correct schema
    ...


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    body: PatientCreate,
    current_user: AuthenticatedUser = Depends(require_permission("patients:write")),
    _active: None = Depends(require_active_tenant()),
):
    """Create a new patient. Blocked if tenant is suspended."""
    ...


@router.delete("/{patient_id}", status_code=204)
async def deactivate_patient(
    patient_id: UUID,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    _active: None = Depends(require_active_tenant()),
):
    """Deactivate a patient. Clinic owner only."""
    ...
```

### 5.9 Database Session with Tenant Schema

```python
# app/db/session.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.context import AuthenticatedUser
from app.db.engine import async_engine


async def get_tenant_db(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AsyncSession:
    """
    Provides an async database session scoped to the tenant's schema.

    This dependency chains off get_current_user to resolve the schema name,
    then sets the search_path for all queries in the session.

    Usage:
        @router.get("/patients")
        async def list_patients(
            db: AsyncSession = Depends(get_tenant_db),
            current_user: AuthenticatedUser = Depends(require_permission("patients:read")),
        ):
            result = await db.execute(select(Patient))
            ...
    """
    schema = current_user.tenant.schema_name
    async with AsyncSession(async_engine) as session:
        await session.execute(f"SET search_path TO {schema}, public")
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## 6. Password Security

### 6.1 Hashing

| Setting | Value |
|---------|-------|
| Algorithm | bcrypt |
| Library | `passlib[bcrypt]` |
| Rounds | 12 (default) |
| Pepper | Optional application-level pepper via `settings.PASSWORD_PEPPER` |

```python
# app/auth/password.py

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)
```

### 6.2 Password Requirements

| Requirement | Rule |
|-------------|------|
| Minimum length | 8 characters |
| Maximum length | 128 characters |
| Uppercase | At least 1 uppercase letter |
| Number | At least 1 digit |
| Special character | Not required (for MVP -- LATAM users often struggle with special chars on mobile keyboards) |
| Common passwords | Checked against a list of 10,000 common passwords |
| Email match | Password must not contain the user's email address |

```python
# app/auth/validators.py

import re
from fastapi import HTTPException, status

COMMON_PASSWORDS_SET: set = set()  # Loaded from file at startup


def validate_password(password: str, email: str) -> None:
    """
    Validate password against security requirements.

    Raises HTTPException with 422 status if validation fails.
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if len(password) > 128:
        errors.append("Password must not exceed 128 characters.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number.")
    if email and email.lower() in password.lower():
        errors.append("Password must not contain your email address.")
    if password.lower() in COMMON_PASSWORDS_SET:
        errors.append("This password is too common. Please choose a stronger one.")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "weak_password",
                "message": "Password does not meet security requirements.",
                "details": {"password": errors},
            },
        )
```

### 6.3 Login Rate Limiting

| Dimension | Limit | Window | Backend |
|-----------|-------|--------|---------|
| Per IP | 5 attempts | 15 minutes | Redis sliding window |
| Per account | 10 attempts total | Rolling | PostgreSQL counter |
| Account lockout | After 10 failed attempts | 30 minutes lockout | PostgreSQL `locked_until` |

**Redis key for IP rate limiting:**
```
dentalos:login_rate:{ip_address}  ->  counter  (TTL: 900 seconds)
```

**Account lockout fields (on `users` table):**
```sql
failed_login_attempts   INTEGER NOT NULL DEFAULT 0,
locked_until            TIMESTAMPTZ,
last_failed_login_at    TIMESTAMPTZ
```

**Lockout logic:**
```python
# app/auth/rate_limit.py

from datetime import datetime, timedelta, timezone

LOCKOUT_THRESHOLD = 10
LOCKOUT_DURATION = timedelta(minutes=30)
IP_RATE_LIMIT = 5
IP_RATE_WINDOW = 900  # 15 minutes in seconds


async def check_login_rate_limit(ip: str, redis) -> None:
    """Check IP-based login rate limit."""
    key = f"dentalos:login_rate:{ip}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, IP_RATE_WINDOW)
    if current > IP_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many login attempts. Please try again later.",
                "details": {"retry_after_seconds": await redis.ttl(key)},
            },
        )


def check_account_lockout(user) -> None:
    """Check if the account is locked due to failed attempts."""
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = (user.locked_until - datetime.now(timezone.utc)).seconds
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "error": "account_locked",
                "message": "Account is temporarily locked due to too many failed login attempts.",
                "details": {"retry_after_seconds": remaining},
            },
        )


async def record_failed_login(user, db) -> None:
    """Increment failed counter, lock if threshold reached."""
    user.failed_login_attempts += 1
    user.last_failed_login_at = datetime.now(timezone.utc)
    if user.failed_login_attempts >= LOCKOUT_THRESHOLD:
        user.locked_until = datetime.now(timezone.utc) + LOCKOUT_DURATION
    await db.commit()


async def reset_failed_login(user, db) -> None:
    """Reset failed counter on successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_failed_login_at = None
    await db.commit()
```

**Security note:** Login error messages must be generic. Never reveal whether the email exists or the password was wrong. Always return:
```json
{
  "error": "invalid_credentials",
  "message": "Invalid email or password."
}
```

---

## 7. Invite Flow

### 7.1 Overview

The invite flow allows a `clinic_owner` to invite team members (doctors, assistants, receptionists) to their clinic's tenant.

### 7.2 Invite Lifecycle

```
clinic_owner                    Backend                         Email Service
  |                                |                               |
  |  POST /api/v1/auth/invite      |                               |
  |  {email, role, name}           |                               |
  |------------------------------->|                               |
  |                                |  1. Validate: role is allowed  |
  |                                |     (not clinic_owner/patient) |
  |                                |  2. Check: email not already   |
  |                                |     registered in this tenant  |
  |                                |  3. Check: plan allows more    |
  |                                |     users of this role         |
  |                                |  4. Create pending user record |
  |                                |     status='pending'           |
  |                                |  5. Generate invite token      |
  |                                |     (UUID, stored hashed)      |
  |                                |  6. Queue invite email         |
  |                                |------------------------------→|
  |  201 Created                   |                               |
  |  {invite_id, expires_at}       |                               |
  |<-------------------------------|                               |
```

### 7.3 Invite Token

| Property | Value |
|----------|-------|
| Format | UUID v4 |
| Storage | SHA-256 hash in `invitations` table |
| TTL | 7 days |
| Single use | Yes -- consumed on acceptance |

**Database schema (shared `public` schema):**

```sql
CREATE TABLE public.invitations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash      VARCHAR(128) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL,
    role            VARCHAR(50) NOT NULL,
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),
    invited_by      UUID NOT NULL REFERENCES public.users(id),
    invited_name    VARCHAR(255),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'accepted', 'expired', 'revoked'
    expires_at      TIMESTAMPTZ NOT NULL,
    accepted_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_invite_role CHECK (role IN ('doctor', 'assistant', 'receptionist'))
);

CREATE INDEX idx_invitations_email ON public.invitations(email, tenant_id);
CREATE INDEX idx_invitations_token ON public.invitations(token_hash);
```

### 7.4 Invite Acceptance Flow

```
Invited User                    Backend                         Database
  |                                |                               |
  |  Clicks invite link:           |                               |
  |  /join?token=<uuid>            |                               |
  |------------------------------->|                               |
  |                                |                               |
  |  GET /api/v1/auth/invite-info  |                               |
  |  ?token=<uuid>                 |                               |
  |------------------------------->|                               |
  |                                |  1. Hash token, look up       |
  |                                |  2. Check not expired/used     |
  |  200 OK                        |                               |
  |  {email, role, clinic_name}    |                               |
  |<-------------------------------|                               |
  |                                |                               |
  |  POST /api/v1/auth/accept-invite                               |
  |  {token, password, name, ...}  |                               |
  |------------------------------->|                               |
  |                                |  1. Validate token (again)     |
  |                                |  2. Validate password strength |
  |                                |  3. Create user record         |
  |                                |     (status='active')          |
  |                                |  4. Mark invitation 'accepted' |
  |                                |  5. Issue token pair           |
  |  200 OK                        |                               |
  |  {access_token, user, tenant}  |                               |
  |  Set-Cookie: refresh_token     |                               |
  |<-------------------------------|                               |
```

### 7.5 Invite Rules

| Rule | Detail |
|------|--------|
| Who can invite | `clinic_owner` only |
| Invitable roles | `doctor`, `assistant`, `receptionist` |
| Cannot invite | `clinic_owner` (only one per tenant), `patient` (separate flow), `superadmin` (separate system) |
| Duplicate email | If email already exists in tenant, return 409 Conflict |
| Re-invite | If invitation is expired, clinic_owner can re-invite the same email (creates new token) |
| Plan enforcement | Check tenant plan limits before creating the invitation (e.g., free plan = max 2 users) |
| Invite expiry | 7 days after creation |
| Expired invite cleanup | Background job marks invitations as `expired` when past `expires_at` |
| Revocation | clinic_owner can revoke a pending invitation |

---

## 8. Session Management

### 8.1 Multiple Device Support

Users can be logged in from multiple devices simultaneously. Each device holds its own refresh token.

**Maximum concurrent sessions:** 5 per user. When a 6th refresh token is created, the oldest active refresh token is automatically revoked.

### 8.2 Session Listing (Post-MVP)

```
GET /api/v1/auth/sessions
```

Returns a list of active sessions:
```json
{
  "sessions": [
    {
      "id": "session_uuid",
      "device_info": {
        "user_agent": "Mozilla/5.0 ...",
        "ip": "190.25.x.x",
        "device_name": "Chrome on macOS"
      },
      "created_at": "2026-02-20T10:00:00Z",
      "last_used_at": "2026-02-24T14:30:00Z",
      "is_current": true
    }
  ]
}
```

### 8.3 Force Logout All Devices

Triggered automatically on:
- Password change (see `auth/change-password.md`)
- Password reset (see `auth/reset-password.md`)
- Replay detection (see Section 2.3)

Available manually:
```
POST /api/v1/auth/logout-all
```

Process:
1. Revoke all refresh tokens for the user.
2. Set the user token version timestamp in Redis (see Section 2.5).
3. Return 204 No Content.

---

## 9. Patient Portal Authentication

### 9.1 Overview

The patient portal uses a **separate auth context** with restricted access. Patients authenticate through dedicated portal endpoints and receive tokens with `aud: "dentalos-portal"`.

### 9.2 Auth Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/portal/auth/login` | POST | Email + password login |
| `/api/v1/portal/auth/magic-link` | POST | Request magic link via email |
| `/api/v1/portal/auth/magic-link/verify` | POST | Verify magic link token |
| `/api/v1/portal/auth/refresh` | POST | Refresh token rotation |
| `/api/v1/portal/auth/logout` | POST | Logout |

### 9.3 Magic Link Authentication

For patients who do not have a password (or prefer passwordless login):

```
Patient                         Backend                         Email Service
  |                                |                               |
  |  POST /portal/auth/magic-link  |                               |
  |  {email}                       |                               |
  |------------------------------->|                               |
  |                                |  1. Look up patient user       |
  |                                |  2. Generate magic link token  |
  |                                |     (UUID, hashed in DB)       |
  |                                |  3. Token TTL: 15 minutes      |
  |                                |  4. Queue email                |
  |                                |------------------------------→|
  |  200 OK                        |                               |
  |  (always, even if email        |                               |
  |   doesn't exist)               |                               |
  |<-------------------------------|                               |
  |                                |                               |
  |  -- Patient clicks link --     |                               |
  |                                |                               |
  |  POST /portal/auth/magic-link/verify                           |
  |  {token}                       |                               |
  |------------------------------->|                               |
  |                                |  1. Validate token             |
  |                                |  2. Mark as used               |
  |                                |  3. Issue token pair           |
  |  200 OK                        |                               |
  |  {access_token}                |                               |
  |  Set-Cookie: refresh_token     |                               |
  |<-------------------------------|                               |
```

**Magic link token properties:**
- TTL: 15 minutes
- Single use
- Rate limited: 3 requests per hour per email
- Token format: UUID v4 (sent in URL: `https://app.dentalos.com/portal/auth/verify?token=<uuid>`)

### 9.4 Portal Auth Dependency

```python
# app/auth/dependencies.py (continued)

async def get_current_patient(
    request: Request,
    token: str = Depends(portal_oauth2_scheme),
) -> AuthenticatedUser:
    """
    Authentication dependency for patient portal endpoints.

    Validates the JWT, ensures audience is 'dentalos-portal',
    ensures role is 'patient', and resolves tenant context.

    Usage:
        @router.get("/portal/appointments")
        async def my_appointments(
            patient: AuthenticatedUser = Depends(get_current_patient),
        ):
            # patient.user_id links to the patient record
            ...
    """
    try:
        payload = jwt.decode(
            token,
            _public_key,
            algorithms=["RS256"],
            issuer="dentalos",
            audience="dentalos-portal",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_portal_token",
                "message": "Invalid or expired portal session.",
            },
        )

    if payload.get("role") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "not_patient",
                "message": "This endpoint is only accessible to patients.",
            },
        )

    # Resolve tenant context (same as staff auth)
    tenant_id = UUID(payload["tid"].replace("tn_", ""))
    tenant_info = await get_tenant_info(tenant_id)

    if not tenant_info or tenant_info.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "clinic_unavailable",
                "message": "This clinic is currently unavailable.",
            },
        )

    return AuthenticatedUser(
        user_id=UUID(payload["sub"].replace("usr_", "")),
        email=payload["email"],
        name=payload["name"],
        role="patient",
        permissions=frozenset(),  # Portal enforces own-data at query level
        tenant=TenantContext(
            tenant_id=tenant_id,
            schema_name=tenant_info.schema_name,
            plan=tenant_info.plan,
            country=tenant_info.country,
            is_active=True,
            max_doctors=tenant_info.max_doctors,
            max_patients=tenant_info.max_patients,
        ),
        token_jti=payload["jti"],
    )
```

### 9.5 Own-Data Enforcement

All portal queries must filter by the patient's own record:

```python
# app/api/v1/portal/appointments.py

@router.get("/portal/appointments")
async def my_appointments(
    patient: AuthenticatedUser = Depends(get_current_patient),
    db: AsyncSession = Depends(get_tenant_db),
):
    # The patient's user_id links to a patient record
    patient_record = await db.execute(
        select(Patient).where(Patient.portal_user_id == patient.user_id)
    )
    patient_obj = patient_record.scalar_one_or_none()
    if not patient_obj:
        raise HTTPException(status_code=404, detail={"error": "patient_not_found"})

    # ALL queries filter by this patient's ID
    appointments = await db.execute(
        select(Appointment)
        .where(Appointment.patient_id == patient_obj.id)
        .order_by(Appointment.start_time.desc())
    )
    return appointments.scalars().all()
```

---

## 10. Error Responses

All auth-related errors follow the standard error schema defined in `infra/error-handling.md`.

### 10.1 Error Code Registry

| HTTP Status | Error Code | When | Message |
|-------------|-----------|------|---------|
| 401 | `token_missing` | No Authorization header or cookie | "Authentication required." |
| 401 | `token_expired` | Access token JWT has expired | "Access token has expired. Use refresh token to obtain a new one." |
| 401 | `token_invalid` | JWT signature invalid, malformed, or wrong audience | "Access token is invalid." |
| 401 | `token_revoked` | Access token JTI is in the Redis blacklist | "This token has been revoked." |
| 401 | `session_invalidated` | All sessions were force-invalidated (password change) | "All sessions have been invalidated. Please log in again." |
| 401 | `session_compromised` | Replay detection triggered | "Session compromised. All sessions have been revoked for your security. Please log in again." |
| 401 | `refresh_token_expired` | Refresh token past its `expires_at` | "Session has expired. Please log in again." |
| 401 | `refresh_token_invalid` | Refresh token not found in DB | "Invalid refresh token." |
| 401 | `invalid_credentials` | Wrong email or password | "Invalid email or password." |
| 401 | `invalid_portal_token` | Portal JWT invalid or expired | "Invalid or expired portal session." |
| 401 | `invalid_admin_token` | Superadmin JWT invalid | "Invalid or missing superadmin credentials." |
| 401 | `magic_link_expired` | Magic link token expired or used | "This link has expired. Please request a new one." |
| 401 | `invite_token_invalid` | Invite token not found, expired, or used | "This invitation is invalid or has expired." |
| 403 | `insufficient_role` | Valid auth but wrong role | "This action requires one of the following roles: {roles}." |
| 403 | `insufficient_permission` | Valid auth but missing permission | "You do not have permission to perform this action." |
| 403 | `tenant_suspended` | Tenant is suspended, write attempted | "Your clinic account is suspended. Only read operations are allowed." |
| 403 | `tenant_cancelled` | Tenant is cancelled | "This clinic account has been cancelled." |
| 403 | `not_superadmin` | Non-superadmin accessing admin endpoints | "This endpoint requires superadmin access." |
| 403 | `not_patient` | Non-patient accessing portal endpoints | "This endpoint is only accessible to patients." |
| 403 | `clinic_unavailable` | Portal access to inactive clinic | "This clinic is currently unavailable." |
| 422 | `weak_password` | Password does not meet requirements | "Password does not meet security requirements." |
| 423 | `account_locked` | Too many failed login attempts | "Account is temporarily locked due to too many failed login attempts." |
| 429 | `rate_limit_exceeded` | Too many login attempts from IP | "Too many login attempts. Please try again later." |
| 503 | `tenant_provisioning` | Tenant schema not ready | "Your clinic is being set up. Please try again shortly." |

### 10.2 Standard Error Response Format

```json
{
  "error": "error_code_string",
  "message": "Human-readable message in English (frontend localizes via error code).",
  "details": {}
}
```

**Localization note:** Error codes are stable identifiers. The frontend maps error codes to localized messages in Spanish (and other LATAM languages). The `message` field is an English fallback.

### 10.3 WWW-Authenticate Header

All 401 responses include the `WWW-Authenticate: Bearer` header per RFC 6750.

---

## 11. Configuration

All auth-related settings are loaded from environment variables.

```python
# app/config.py (auth-related subset)

class AuthSettings:
    # JWT
    JWT_PRIVATE_KEY_PATH: str       # Path to RS256 private key PEM file
    JWT_PUBLIC_KEY_PATH: str        # Path to RS256 public key PEM file
    JWT_KEY_ID: str = "dentalos-2026-02"
    JWT_ACCESS_TOKEN_TTL_MINUTES: int = 15
    JWT_REFRESH_TOKEN_TTL_DAYS: int = 30
    JWT_ISSUER: str = "dentalos"

    # Password
    PASSWORD_BCRYPT_ROUNDS: int = 12
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 128
    PASSWORD_PEPPER: str = ""       # Optional pepper, empty = disabled

    # Rate Limiting
    LOGIN_RATE_LIMIT_PER_IP: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 900
    ACCOUNT_LOCKOUT_THRESHOLD: int = 10
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30

    # Sessions
    MAX_SESSIONS_PER_USER: int = 5

    # Invitations
    INVITE_TOKEN_TTL_DAYS: int = 7

    # Magic Link
    MAGIC_LINK_TTL_MINUTES: int = 15
    MAGIC_LINK_RATE_LIMIT_PER_EMAIL: int = 3
    MAGIC_LINK_RATE_LIMIT_WINDOW_HOURS: int = 1

    # Cookie
    REFRESH_TOKEN_COOKIE_SECURE: bool = True
    REFRESH_TOKEN_COOKIE_SAMESITE: str = "strict"
    REFRESH_TOKEN_COOKIE_PATH: str = "/api/v1/auth"
```

---

## 12. Key Rotation

### 12.1 JWT Key Rotation

RSA key pairs must be rotated periodically (recommended: every 6 months).

**Process:**
1. Generate a new key pair with a new `kid` (e.g., `dentalos-2026-08`).
2. Deploy the new private key alongside the old public key.
3. New tokens are signed with the new key.
4. Old tokens continue to validate against the old public key (still accepted for their remaining TTL).
5. After 30 days (max refresh token TTL), remove the old public key.

The `kid` header in the JWT identifies which public key to use for verification.

### 12.2 Key Storage

| Environment | Storage |
|-------------|---------|
| Local development | File system (`./keys/jwt_private.pem`, `./keys/jwt_public.pem`) |
| Production | Environment variables or mounted secrets (Hetzner Cloud Secret) |

**Never commit private keys to version control.**

---

## 13. Background Jobs

### 13.1 Token Cleanup

**Queue:** `maintenance`
**Schedule:** Daily at 03:00 UTC

```python
async def cleanup_expired_tokens():
    """
    Remove expired and revoked refresh tokens older than 60 days.
    Prevents unbounded table growth.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    await db.execute(
        delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < cutoff,
                and_(
                    RefreshToken.revoked_at.isnot(None),
                    RefreshToken.revoked_at < cutoff,
                ),
            )
        )
    )
```

### 13.2 Invite Expiry

**Queue:** `maintenance`
**Schedule:** Hourly

```python
async def expire_stale_invitations():
    """Mark pending invitations as expired when past their TTL."""
    await db.execute(
        update(Invitation)
        .where(
            Invitation.status == "pending",
            Invitation.expires_at < datetime.now(timezone.utc),
        )
        .values(status="expired")
    )
```

---

## 14. Testing Requirements

### 14.1 Unit Tests

| Area | Test Cases |
|------|-----------|
| JWT creation | Valid claims, correct TTL, correct audience per context |
| JWT validation | Valid token, expired token, wrong issuer, wrong audience, tampered signature |
| Password hashing | Hash + verify roundtrip, wrong password fails |
| Password validation | Too short, no uppercase, no number, common password, contains email |
| Permission mapping | Each role has correct permissions, no permission leaks |
| Rate limiting | Under limit passes, over limit blocks, window expiry resets |
| Refresh token rotation | New pair issued, old token revoked, chain linked |
| Replay detection | Revoked token triggers full revocation |

### 14.2 Integration Tests

| Area | Test Cases |
|------|-----------|
| Login flow | Valid credentials return tokens, invalid credentials return 401 |
| Token refresh | Valid refresh returns new pair, expired refresh returns 401 |
| Logout | Refresh token revoked, access token blacklisted |
| Force logout all | All sessions revoked, old access tokens rejected |
| Role enforcement | Each role accessing allowed/forbidden endpoints |
| Permission enforcement | Fine-grained permission checks per endpoint |
| Tenant isolation | User A cannot access Tenant B data |
| Account lockout | Lock after threshold, unlock after duration |
| Invite flow | Create invite, accept invite, expired invite rejected |
| Patient portal | Portal login, magic link, own-data enforcement |

### 14.3 Security Tests

| Test | Expected Result |
|------|----------------|
| JWT with modified claims | 401 (signature invalid) |
| JWT signed with wrong key | 401 |
| Access token used as refresh | Rejected |
| Refresh token used as access | Rejected |
| Cross-tenant access attempt | 403 or no data returned |
| SQL injection in email field | Parameterized query prevents |
| Timing attack on password | bcrypt constant-time comparison |
| Enumeration via login | Same error for wrong email vs wrong password |
| Enumeration via forgot-password | Same 200 response regardless |

---

## 15. Observability

### 15.1 Structured Logging

All auth events are logged as structured JSON with the following fields:

```json
{
  "timestamp": "2026-02-24T14:30:00Z",
  "level": "INFO",
  "event": "auth.login.success",
  "user_id": "usr_550e8400...",
  "tenant_id": "tn_7c9e6679...",
  "ip": "190.25.x.x",
  "user_agent": "Mozilla/5.0...",
  "duration_ms": 45
}
```

### 15.2 Auth Events

| Event | Level | When |
|-------|-------|------|
| `auth.login.success` | INFO | Successful login |
| `auth.login.failed` | WARN | Invalid credentials |
| `auth.login.locked` | WARN | Account locked out |
| `auth.login.rate_limited` | WARN | IP rate limited |
| `auth.token.refresh` | INFO | Token rotation |
| `auth.token.replay_detected` | ERROR | Revoked refresh token reused |
| `auth.logout` | INFO | Explicit logout |
| `auth.logout_all` | WARN | Force logout all devices |
| `auth.password.changed` | INFO | Password changed |
| `auth.password.reset` | INFO | Password reset via email |
| `auth.invite.created` | INFO | Invitation sent |
| `auth.invite.accepted` | INFO | Invitation accepted |
| `auth.invite.expired` | INFO | Invitation expired |
| `auth.portal.login` | INFO | Patient portal login |
| `auth.portal.magic_link` | INFO | Magic link requested |
| `auth.tenant.selected` | INFO | User selected tenant after multi-tenant login |
| `auth.tenant.switched` | INFO | User switched active tenant without re-authenticating |
| `auth.tenant.switch_denied` | WARN | Tenant switch attempted for a tenant where user lacks active membership |

### 15.3 Metrics (Prometheus-compatible)

| Metric | Type | Labels |
|--------|------|--------|
| `dentalos_auth_login_total` | Counter | `status` (success/failed/locked/rate_limited), `tenant_id` |
| `dentalos_auth_token_refresh_total` | Counter | `status` (success/expired/replayed), `tenant_id` |
| `dentalos_auth_active_sessions` | Gauge | `tenant_id` |
| `dentalos_auth_invite_total` | Counter | `status` (created/accepted/expired), `tenant_id` |
| `dentalos_auth_portal_login_total` | Counter | `method` (password/magic_link), `tenant_id` |

---

## 16. Redis Key Reference

Complete list of Redis keys used by the auth system:

| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `dentalos:token_blacklist:{jti}` | String | Remaining token TTL (max 900s) | Immediate access token revocation |
| `dentalos:user_token_version:{user_id}` | String | None | Force-invalidate all tokens issued before this timestamp |
| `dentalos:login_rate:{ip}` | String (counter) | 900s | IP-based login rate limiting |
| `dentalos:magic_link_rate:{email}` | String (counter) | 3600s | Magic link request rate limiting |
| `dentalos:tenant_info:{tenant_id}` | Hash | 300s | Cached tenant info for auth context resolution |
| `dentalos:preauth:{token}` | String (JSON) | 300s | Pre-auth token payload for multi-tenant select-tenant flow (user identity before JWT issuance) |
| `dentalos:tenant_switch_rate:{user_id}` | String (counter) | 3600s | Tenant switch rate limiting (10/hour per user) |

---

## Out of Scope

This spec explicitly does NOT cover:

- **Multi-tenant user membership** (full implementation details) -- architecture and flow covered in Section 4.5. Detailed endpoint specs live in `auth/select-tenant.md` and `auth/switch-tenant.md`.
- **OAuth2/SSO integration** (Google, Microsoft, Apple login) -- deferred post-MVP.
- **Multi-factor authentication (MFA)** for staff -- deferred post-MVP. MFA for superadmin is referenced in `admin/superadmin-login.md`.
- **API key authentication** for third-party integrations -- will be its own spec if needed.
- **WebSocket authentication** -- to be defined in a separate spec when real-time features are added.
- **CORS configuration** -- covered in `infra/security-policy.md`.
- **Detailed rate limiting beyond login** -- covered in `infra/rate-limiting.md`.
- **Audit logging implementation** -- covered in `infra/audit-logging.md`.
- **Email delivery** (invite emails, magic link emails) -- covered in `integrations/email-engine.md`.
- **User profile management** -- covered in `users/` specs.
- **Registration flow** (new clinic signup) -- covered in `auth/register.md`.
- **Specific endpoint implementations** -- each auth endpoint (login, refresh, logout, etc.) has its own spec in the `auth/` directory.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec. JWT auth, RBAC, multi-tenant context, password security, invite flow, patient portal auth, FastAPI implementation patterns. |
| 1.1 | 2026-02-24 | Added Section 4.5 (Multi-Clinic Doctor Flow): `user_tenant_memberships` architecture, login flow with conditional JWT issuance, `select-tenant` endpoint, `switch-tenant` endpoint, security rules. Updated Section 4.3 to remove single-tenant MVP constraint. Added Redis keys and auth events for tenant selection and switching. |
