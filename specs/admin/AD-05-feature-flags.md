# AD-05 — Admin Feature Flags Spec

## Overview

**Feature:** Manage feature flags for the DentalOS platform. GET lists all flags with their current state across global, plan-based, and tenant-specific scopes. PUT updates a specific flag's state for a given scope. Supports global flags (all tenants), plan-based flags (all tenants on plan X), and tenant-specific overrides (for a single tenant). Changes propagate to tenant session caches within 60 seconds.

**Domain:** admin

**Priority:** High (Sprint 1-2 — needed to safely roll out features progressively)

**Dependencies:** AD-01 (superadmin-login), AD-03 (plan-management — plan-based flags), infra/caching.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required — platform-level
- **Special rules:** Requires admin JWT (RS256). Feature flag changes have immediate effect on tenant behavior; changes are audit-logged with the specific flag name and scope.

---

## Endpoints

```
GET /api/v1/admin/feature-flags
PUT /api/v1/admin/feature-flags/{flag_name}
```

**Rate Limiting:**
- GET: 60 requests per minute per admin session
- PUT: 20 requests per minute per admin session (writes are logged and propagated)

---

## Request — GET /api/v1/admin/feature-flags

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer admin JWT | Bearer eyJhbGc... |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| scope | No | string | global, plan, tenant — default: all | Filter by scope type | global |
| plan | No | string | free, starter, pro, clinica, enterprise | Filter plan-scoped flags by plan | pro |
| tenant_id | No | string | UUID | Filter tenant-specific overrides by tenant | tn_abc123 |
| include_inherited | No | boolean | default=true | For tenant overrides, show effective value after applying inheritance | true |

---

## Request — PUT /api/v1/admin/feature-flags/{flag_name}

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| flag_name | Yes | string | Valid flag name from the known flags list | Flag to update | voice_enabled |

### Request Body Schema

```json
{
  "scope": "string (required) — global | plan | tenant",
  "plan": "string (required if scope=plan) — free | starter | pro | clinica | enterprise",
  "tenant_id": "string (required if scope=tenant) — UUID of the target tenant",
  "enabled": "boolean (required) — new flag value",
  "reason": "string (required, max 500) — reason for this change (required for audit)",
  "expires_at": "string (optional) — ISO 8601 datetime; flag reverts to parent scope value after this time",
  "notify_tenants": "boolean (optional, default=false) — send in-app notification to affected tenants"
}
```

**Example PUT Request (tenant override):**
```json
{
  "scope": "tenant",
  "tenant_id": "tn_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "enabled": true,
  "reason": "Beta tester for anatomic odontogram — approved by sales team (ticket #1234)",
  "expires_at": "2026-04-01T00:00:00Z",
  "notify_tenants": false
}
```

**Example PUT Request (global disable):**
```json
{
  "scope": "global",
  "enabled": false,
  "reason": "Disabling telehealth globally while we fix HIPAA compliance issue — ETA 72h"
}
```

---

## Response — GET /api/v1/admin/feature-flags

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "flags": [
    {
      "flag_name": "string — machine identifier",
      "display_name": "string — human-readable name",
      "description": "string — what this flag controls",
      "category": "string — clinical | compliance | billing | infrastructure | ai",
      "global_value": "boolean — the global default",
      "plan_overrides": [
        {
          "plan": "string",
          "enabled": "boolean",
          "set_at": "string (ISO 8601)",
          "set_by": "string — admin user name"
        }
      ],
      "tenant_overrides": [
        {
          "tenant_id": "string",
          "clinic_name": "string",
          "enabled": "boolean",
          "set_at": "string (ISO 8601)",
          "set_by": "string",
          "reason": "string",
          "expires_at": "string (ISO 8601) | null",
          "is_expired": "boolean"
        }
      ],
      "affected_tenants_count": "integer — count of tenants for which effective value differs from global",
      "last_changed_at": "string (ISO 8601)",
      "last_changed_by": "string",
      "last_change_reason": "string"
    }
  ],
  "summary": {
    "total_flags": "integer",
    "flags_with_plan_overrides": "integer",
    "flags_with_tenant_overrides": "integer",
    "expired_overrides_count": "integer"
  }
}
```

**Known flags (as of v1.0):**

| flag_name | category | description |
|-----------|----------|-------------|
| voice_enabled | ai | Voice-to-Odontogram ($10/doctor/mo add-on) |
| anatomic_odontogram | clinical | Anatomic 3D-style odontogram (vs Classic) |
| offline_mode | infrastructure | PWA offline mode (iOS/Android service worker) |
| ai_radiograph | ai | AI radiograph analysis ($20/doctor/mo add-on) |
| telehealth | clinical | Teleconsultation module |
| inventory_module | clinical | Inventory and sterilization tracking |
| patient_portal | clinical | Patient self-service portal |
| whatsapp_notifications | infrastructure | WhatsApp Business API notifications |
| rips_reporting | compliance | RIPS generation and submission (Colombia only) |
| rda_compliance | compliance | RDA status dashboard (Colombia only) |
| electronic_invoicing | billing | DIAN/MATIAS e-invoicing |
| analytics_advanced | clinical | Advanced analytics and reports |
| api_access | infrastructure | REST API access (for integrations) |
| multi_location | clinical | Multi-location / multi-branch support |

**Example Response:**
```json
{
  "flags": [
    {
      "flag_name": "voice_enabled",
      "display_name": "Voice-to-Odontogram",
      "description": "Enables the Voice-to-Odontogram AI feature (Whisper + Claude pipeline). Add-on at $10/doctor/mo.",
      "category": "ai",
      "global_value": false,
      "plan_overrides": [
        { "plan": "pro", "enabled": false, "set_at": "2026-01-01T00:00:00Z", "set_by": "Platform Admin" },
        { "plan": "enterprise", "enabled": false, "set_at": "2026-01-01T00:00:00Z", "set_by": "Platform Admin" }
      ],
      "tenant_overrides": [
        {
          "tenant_id": "tn_xyz789",
          "clinic_name": "Clínica Beta Dental",
          "enabled": true,
          "set_at": "2026-02-10T14:00:00Z",
          "set_by": "Platform Admin",
          "reason": "Beta tester group A",
          "expires_at": "2026-04-01T00:00:00Z",
          "is_expired": false
        }
      ],
      "affected_tenants_count": 1,
      "last_changed_at": "2026-02-10T14:00:00Z",
      "last_changed_by": "Platform Admin",
      "last_change_reason": "Beta tester group A"
    }
  ],
  "summary": {
    "total_flags": 14,
    "flags_with_plan_overrides": 3,
    "flags_with_tenant_overrides": 5,
    "expired_overrides_count": 0
  }
}
```

## Response — PUT /api/v1/admin/feature-flags/{flag_name}

**Status:** 200 OK

**Schema:**
```json
{
  "flag_name": "string",
  "scope": "string",
  "plan": "string | null",
  "tenant_id": "string | null",
  "previous_value": "boolean",
  "new_value": "boolean",
  "effective_immediately": "boolean — true (changes propagate via Redis pub/sub)",
  "affected_tenants_estimate": "integer — estimated tenants affected by this change",
  "cache_invalidation_queued": "boolean",
  "expires_at": "string (ISO 8601) | null",
  "updated_at": "string (ISO 8601)",
  "updated_by": "string"
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid flag_name; scope=plan without plan provided; scope=tenant without tenant_id provided; expires_at in the past.

**Example:**
```json
{
  "error": "invalid_flag_update",
  "message": "Validation errors in flag update",
  "details": {
    "plan": ["plan is required when scope is 'plan'"],
    "expires_at": ["expires_at must be a future datetime"]
  }
}
```

#### 401 Unauthorized
**When:** Admin JWT missing or invalid.

#### 403 Forbidden
**When:** Role is not superadmin.

#### 404 Not Found
**When:** `flag_name` is not a recognized flag; or `tenant_id` does not exist (for tenant-scope).

**Example:**
```json
{
  "error": "flag_not_found",
  "message": "Unknown feature flag: 'experimental_module'",
  "details": {
    "valid_flags": ["voice_enabled", "anatomic_odontogram", "offline_mode", "..."]
  }
}
```

#### 422 Unprocessable Entity
**When:** Request body Pydantic validation fails.

---

## Business Logic

**Step-by-step process (PUT):**

1. Validate admin JWT and superadmin role.
2. Validate `flag_name` is in the known flags registry (`KNOWN_FLAGS` constant). Return 404 if not.
3. Validate request body:
   - If `scope=plan`: `plan` field required.
   - If `scope=tenant`: `tenant_id` field required; verify tenant exists.
   - If `scope=global`: no extra fields needed.
   - `reason` is always required (non-empty, max 500 chars).
   - `expires_at` if provided must be > now().
4. Compute `previous_value` by reading current effective value for this scope.
5. If `previous_value == enabled` (no change): return 200 with no-op indicator (no DB write, no cache invalidation).
6. Write to `feature_flags` table:
   - For `scope=global`: UPSERT `feature_flags.(flag_name, scope=global)`.
   - For `scope=plan`: UPSERT `feature_flags.(flag_name, scope=plan, plan=plan)`.
   - For `scope=tenant`: UPSERT `feature_flags.(flag_name, scope=tenant, tenant_id=tenant_id)`.
7. Publish cache invalidation to Redis pub/sub channel `feature_flags.changed`:
   - Payload: `{ flag_name, scope, plan, tenant_id, new_value, changed_at }`.
   - All application nodes subscribed to this channel will invalidate their local feature flag caches.
8. Publish event to RabbitMQ `admin.feature_flag_changed` queue for background processing (notify tenants if requested).
9. Compute `affected_tenants_estimate`:
   - Global change: ALL active tenants.
   - Plan change: count of active tenants on that plan.
   - Tenant change: always 1.
10. Write audit log: action=`feature_flag_updated`, actor=`admin_user_id`, flag_name=flag_name, scope=scope, previous_value=prev, new_value=enabled, reason=reason.
11. Return 200.

**Flag Inheritance/Resolution (how tenants evaluate a flag):**
Priority order (highest to lowest):
1. Tenant-specific override (if exists and not expired)
2. Plan-based override (for tenant's plan)
3. Global value

```python
def evaluate_flag(flag_name: str, tenant_id: str, plan: str) -> bool:
    # Check tenant override (non-expired)
    tenant_override = get_tenant_override(flag_name, tenant_id)
    if tenant_override and not tenant_override.is_expired:
        return tenant_override.enabled
    # Check plan override
    plan_override = get_plan_override(flag_name, plan)
    if plan_override:
        return plan_override.enabled
    # Fall back to global
    return get_global_value(flag_name)
```

**Expiry Handling:**
- Expired tenant overrides are NOT automatically deleted (kept for audit trail).
- The `is_expired` flag is computed at read time: `expires_at is not None and expires_at < now()`.
- Background job runs every 5 minutes to clean up expired overrides from cache.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| flag_name | Must be in KNOWN_FLAGS list | "Unknown feature flag" |
| scope | global, plan, or tenant | "scope must be global, plan, or tenant" |
| plan | Required when scope=plan; valid plan slug | "plan is required for plan-scope flags" |
| tenant_id | Required when scope=tenant; must exist | "tenant_id is required for tenant-scope flags" |
| reason | Non-empty, max 500 chars | "Reason is required for audit trail" |
| expires_at | Future datetime if provided | "expires_at must be a future datetime" |

**Business Rules:**

- All 14 flags are defined in code (`KNOWN_FLAGS` constant) — not in DB. New flags require a code deploy.
- `scope=global` overrides are the baseline default for all tenants.
- Plan overrides take precedence over global; tenant overrides take precedence over plan.
- `notify_tenants=true` sends an in-app notification to clinic_owners of affected tenants (use sparingly — e.g., when enabling a major new feature).
- Disabling a flag that is a paid add-on (voice_enabled, ai_radiograph) does NOT cancel the subscription — billing is separate.
- `expires_at` is useful for temporary overrides (beta programs, incident response).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| PUT with same value as current | 200 OK, no-op; previous_value==new_value; no DB write; no cache invalidation |
| Tenant override expires | Expired override ignored; plan or global value applies; is_expired=true in list |
| Disable voice_enabled globally | All tenants with voice add-on subscription lose the feature; billing not cancelled |
| scope=global enable, but tenant override is false | Tenant still sees false (tenant override wins) |
| flag_name not recognized | 404 with list of valid flags |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `feature_flags`: UPSERT (flag_name, scope, plan/tenant_id, enabled, set_by, set_at, reason, expires_at)
- `feature_flag_change_history`: INSERT (full audit trail of every change)

**Example query (SQLAlchemy):**
```python
stmt = (
    insert(FeatureFlag)
    .values(
        flag_name=flag_name,
        scope=scope,
        plan=plan,
        tenant_id=tenant_id,
        enabled=body.enabled,
        set_by=admin_user_id,
        set_at=utcnow(),
        reason=body.reason,
        expires_at=body.expires_at,
    )
    .on_conflict_do_update(
        index_elements=["flag_name", "scope", "plan", "tenant_id"],
        set_=dict(enabled=body.enabled, set_by=admin_user_id, set_at=utcnow(), reason=body.reason, expires_at=body.expires_at),
    )
)
await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:feature_flags`: INVALIDATE for affected tenants (via pub/sub)
- `global:feature_flags`: INVALIDATE on global change
- `plan:{plan}:feature_flags`: INVALIDATE on plan change
- `admin:feature_flags:list`: INVALIDATE on any PUT

**Cache TTL:** Feature flag evaluations cached 60s per tenant

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| admin.feature_flag_changed | flag_changed | `{ flag_name, scope, plan, tenant_id, new_value, notify_tenants }` | After PUT succeeds |

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** feature_flag
- **PHI involved:** No

### Notifications

**Notifications triggered:** Conditional (only if `notify_tenants=true` in PUT request)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | feature_enabled | clinic_owner | notify_tenants=true and enabled=true |
| in-app | feature_disabled | clinic_owner | notify_tenants=true and enabled=false |

---

## Performance

### Expected Response Time
- **GET Target:** < 100ms (cache hit)
- **PUT Target:** < 300ms

### Caching Strategy
- **Cache key (GET):** `admin:feature_flags:list`
- **TTL:** 60 seconds
- **Propagation:** Redis pub/sub for instant tenant cache invalidation

### Database Performance

**GET Queries:** 1 (all flags + all overrides)
**PUT Queries:** 2 (verify tenant exists if scope=tenant; UPSERT flag row)

**Indexes required:**
- `feature_flags.(flag_name, scope, plan, tenant_id)` — COMPOSITE UNIQUE (upsert target)
- `feature_flags.(tenant_id)` — INDEX for tenant-specific flag lookups
- `feature_flag_change_history.(flag_name, changed_at DESC)` — COMPOSITE INDEX

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| flag_name | Literal validation against KNOWN_FLAGS | No unknown strings |
| scope | Pydantic Literal enum | Only global/plan/tenant |
| plan | Pydantic Literal plan slug | Only valid plan names |
| tenant_id | UUID validation | Non-UUID rejected |
| reason | max_length=500, strip whitespace | Plain text |
| expires_at | Future datetime | Prevents backdating |

---

## Testing

### Test Cases

#### Happy Path
1. GET all feature flags
   - **Given:** superadmin JWT, 14 flags configured
   - **When:** GET /api/v1/admin/feature-flags
   - **Then:** 200 OK, 14 flags returned with global_value, plan_overrides, tenant_overrides

2. PUT global flag enable
   - **Given:** voice_enabled global_value=false
   - **When:** PUT voice_enabled with scope=global, enabled=true, reason="Global launch"
   - **Then:** 200 OK, previous_value=false, new_value=true, cache invalidation queued

3. PUT tenant-specific override with expiry
   - **Given:** tenant exists, voice_enabled=false globally
   - **When:** PUT voice_enabled with scope=tenant, tenant_id=X, enabled=true, expires_at=2026-04-01
   - **Then:** 200 OK, tenant override created, expires_at stored

4. Plan-scope override
   - **Given:** pro plan
   - **When:** PUT anatomic_odontogram with scope=plan, plan=pro, enabled=true
   - **Then:** 200 OK, plan_overrides for pro updated

#### Edge Cases
1. PUT with same value (no-op)
   - **Given:** voice_enabled already false globally
   - **When:** PUT global, enabled=false
   - **Then:** 200 OK, affected_tenants_estimate not computed; no DB write

2. Expired override
   - **Given:** Tenant override with expires_at in the past
   - **When:** GET feature flags
   - **Then:** Override shown with is_expired=true

#### Error Cases
1. Unknown flag name
   - **Given:** superadmin JWT
   - **When:** PUT /api/v1/admin/feature-flags/experimental_xyz
   - **Then:** 404 Not Found with valid_flags list

2. scope=tenant without tenant_id
   - **Given:** superadmin JWT
   - **When:** PUT with scope=tenant but no tenant_id
   - **Then:** 400 Bad Request

3. No reason provided
   - **Given:** superadmin JWT
   - **When:** PUT with empty reason=""
   - **Then:** 400 Bad Request, reason required

### Test Data Requirements

**Users:** 1 superadmin

**Patients/Entities:** 2–3 tenant fixtures for tenant-scope override tests

### Mocking Strategy

- Redis pub/sub: Mock channel publish; verify subscribers receive invalidation
- RabbitMQ: In-memory broker; verify flag_changed message published

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns all 14 flags with global, plan, and tenant override values
- [ ] PUT supports global, plan, and tenant scopes
- [ ] Flag inheritance/resolution documented and tested (tenant > plan > global)
- [ ] Reason field required on PUT
- [ ] expires_at support for temporary overrides
- [ ] Cache invalidation via Redis pub/sub (propagates within 60s)
- [ ] No-op detected when value unchanged
- [ ] 404 for unknown flag names
- [ ] feature_flag_change_history row created on every PUT
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed
- [ ] Audit logging verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating new feature flags (requires code deployment; not a runtime operation)
- Per-user feature flags (granularity is tenant, not user)
- A/B testing framework
- Percentage rollouts (flags are boolean only in v1)
- Flag dependencies (ensuring flag A requires flag B — enforced in flag evaluation code, not this spec)
- Frontend flag SDK (frontend reads flags via CO-08 or a separate flags endpoint)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions
- [x] Inheritance resolution logic documented

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] Audit trail for all changes

### Hook 4: Performance & Scalability
- [x] Response time targets defined
- [x] Redis pub/sub for instant propagation
- [x] Indexes listed

### Hook 5: Observability
- [x] Structured logging
- [x] Audit log entries
- [x] Change history table

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Mocking strategy
- [x] Acceptance criteria

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
