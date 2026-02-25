# Tenant Settings Get Spec

---

## Overview

**Feature:** Authenticated endpoint for any tenant user to retrieve the current tenant's settings: clinic name, address, phone, logo_url, country, timezone, locale, odontogram_mode, notification preferences, branding, plan info, and feature flags. This is the primary endpoint for the frontend to render the correct UI and feature toggles.

**Domain:** tenants

**Priority:** Critical

**Spec ID:** T-06

**Dependencies:** T-01 (tenant-provision.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Works in both `active` and `suspended` status (read-only endpoint).

---

## Endpoint

```
GET /api/v1/settings
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_a1b2c3d4 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "tenant": {
    "id": "uuid",
    "slug": "string",
    "name": "string",
    "country": "string",
    "timezone": "string",
    "locale": "string",
    "status": "string",
    "onboarding_step": "integer",
    "onboarding_complete": "boolean"
  },
  "clinic": {
    "name": "string",
    "address": "string | null",
    "phone": "string | null",
    "logo_url": "string | null",
    "owner_email": "string"
  },
  "preferences": {
    "odontogram_mode": "string",
    "default_appointment_duration_min": "integer",
    "cancellation_policy_hours": "integer",
    "reminder_channels": ["string"],
    "reminder_timing_hours": ["integer"]
  },
  "branding": {
    "primary_color": "string",
    "clinic_name_display": "string"
  },
  "plan": {
    "id": "uuid",
    "name": "string",
    "display_name": "string",
    "max_patients": "integer",
    "max_users": "integer",
    "max_storage_mb": "integer"
  },
  "features": {
    "appointments": "boolean",
    "billing": "boolean",
    "patient_portal": "boolean",
    "treatment_plans": "boolean",
    "prescriptions": "boolean",
    "whatsapp_reminders": "boolean",
    "analytics_advanced": "boolean",
    "electronic_invoice": "boolean",
    "custom_consent_templates": "boolean",
    "api_access": "boolean",
    "odontogram_anatomic": "boolean"
  }
}
```

**Example:**
```json
{
  "tenant": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "slug": "clinica-sonrisa",
    "name": "Clínica Dental Sonrisa",
    "country": "CO",
    "timezone": "America/Bogota",
    "locale": "es",
    "status": "active",
    "onboarding_step": 4,
    "onboarding_complete": true
  },
  "clinic": {
    "name": "Clínica Dental Sonrisa",
    "address": "Calle 100 #15-20, Bogotá",
    "phone": "+573001234567",
    "logo_url": "https://cdn.dentalos.app/tenants/a1b2c3d4/logo.png",
    "owner_email": "admin@clinicasonrisa.com"
  },
  "preferences": {
    "odontogram_mode": "classic",
    "default_appointment_duration_min": 30,
    "cancellation_policy_hours": 24,
    "reminder_channels": ["whatsapp", "email"],
    "reminder_timing_hours": [24, 2]
  },
  "branding": {
    "primary_color": "#2563EB",
    "clinic_name_display": "Clínica Dental Sonrisa"
  },
  "plan": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "name": "professional",
    "display_name": "Plan Profesional",
    "max_patients": 500,
    "max_users": 10,
    "max_storage_mb": 5000
  },
  "features": {
    "appointments": true,
    "billing": true,
    "patient_portal": true,
    "treatment_plans": true,
    "prescriptions": true,
    "whatsapp_reminders": true,
    "analytics_advanced": false,
    "electronic_invoice": false,
    "custom_consent_templates": false,
    "api_access": false,
    "odontogram_anatomic": false
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Tenant is cancelled (not active or suspended).

**Example:**
```json
{
  "error": "tenant_inactive",
  "message": "La cuenta de esta clínica ha sido cancelada. Contacte soporte."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

---

## Business Logic

**Step-by-step process:**

1. Extract tenant_id and user_id from JWT claims.
2. Resolve tenant context via TenantMiddleware (cached in Redis).
3. Load tenant data from cache or `public.tenants` JOIN `public.plans`.
4. Extract settings from `public.tenants.settings` JSONB.
5. Merge plan features with any tenant-level feature flag overrides.
6. Compute `onboarding_complete = (onboarding_step >= 4)`.
7. Build structured response with tenant, clinic, preferences, branding, plan, features sections.
8. Return 200 OK.

**Feature flag resolution order:**

1. Start with plan's `features` JSONB from `public.plans`.
2. Override with tenant-level `settings.features_enabled` array.
3. Override with `public.feature_flags.tenant_overrides` for this tenant_id.
4. Final resolved features are returned in the `features` object.

**Validation Rules:**

None (no input beyond JWT).

**Business Rules:**

- This endpoint is read-only and works for both `active` and `suspended` tenants.
- The response is the canonical source of truth for the frontend to determine what features to show.
- `odontogram_anatomic` is derived from the plan feature, not from `odontogram_mode` setting.
- All users (any role) can access this endpoint. No role restriction.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant has no custom settings (freshly created) | Defaults from plan are used. |
| Settings JSONB has unknown keys | Unknown keys are ignored; only known fields are returned. |
| Plan was changed but cache not yet invalidated | TTL of 5 min; eventual consistency acceptable. |
| Suspended tenant | Endpoint works normally (read-only). |

---

## Side Effects

### Database Changes

**Tables affected:**
- None (read-only endpoint)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:info`: READ — tenant data with plan
- `tenant:{tenant_id}:settings`: READ — resolved settings

**Cache TTL:** 5 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** No — high-frequency read, no PHI.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms (cache hit)
- **Maximum acceptable:** < 200ms (cache miss)

### Caching Strategy
- **Strategy:** Redis cache for tenant info + plan + resolved settings
- **Cache key:** `tenant:{tenant_id}:settings:resolved`
- **TTL:** 5 minutes
- **Invalidation:** On tenant update (T-04), settings update (T-07), plan change

### Database Performance

**Queries executed:** 0 on cache hit; 1-2 on cache miss (tenant + plan join)

**Indexes required:**
- `public.tenants.id` — PRIMARY KEY

**N+1 prevention:** Single join query on cache miss.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| JWT claims | Validated by auth middleware | Cryptographically signed |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None (clinic settings only, no patient data)

**Audit requirement:** Not required

---

## Testing

### Test Cases

#### Happy Path
1. Get settings for active tenant
   - **Given:** Authenticated user in active tenant with professional plan
   - **When:** GET /api/v1/settings
   - **Then:** 200 OK with full settings including plan features

2. Get settings for suspended tenant
   - **Given:** Authenticated user in suspended tenant
   - **When:** GET /api/v1/settings
   - **Then:** 200 OK with status=suspended, all settings returned

3. Get settings with cache hit
   - **Given:** Settings cached in Redis
   - **When:** GET /api/v1/settings
   - **Then:** 200 OK, < 50ms response

#### Edge Cases
1. Freshly created tenant (no custom settings)
   - **Given:** Tenant just provisioned, default settings
   - **When:** GET
   - **Then:** 200 OK with plan defaults

2. Feature flag override via public.feature_flags
   - **Given:** analytics_advanced disabled in plan but enabled via feature flag override
   - **When:** GET
   - **Then:** features.analytics_advanced = true

#### Error Cases
1. Expired JWT
   - **Given:** Token expired
   - **When:** GET
   - **Then:** 401 Unauthorized

2. Cancelled tenant
   - **Given:** Tenant is cancelled
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Users with different roles (clinic_owner, doctor, assistant, receptionist)

**Entities:** Active and suspended tenants with different plans and custom settings

### Mocking Strategy

- Redis: Mock or use test Redis instance for cache behavior

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Any authenticated user can retrieve tenant settings
- [ ] Response includes tenant info, clinic details, preferences, branding, plan, and features
- [ ] Feature flags resolved correctly (plan -> tenant override -> global override)
- [ ] Cache hit returns in < 50ms
- [ ] Works for active and suspended tenants
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Updating settings (see T-07)
- Usage stats (see T-08)
- Plan limits enforcement (see T-09)
- Superadmin view of tenant settings (see T-02)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (JWT only)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (N/A for GET)
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
- [x] Input sanitization defined (JWT)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail not needed (no PHI)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (Redis)
- [x] DB queries optimized (cache-first)
- [x] Pagination not needed

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (N/A)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

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
