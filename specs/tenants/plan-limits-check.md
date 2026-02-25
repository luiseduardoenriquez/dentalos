# Plan Limits Check Spec

---

## Overview

**Feature:** Authenticated endpoint for any tenant user to check current plan limits and whether specific actions are allowed. Returns boolean flags like can_add_patient, can_add_user, can_use_anatomic_odontogram, can_use_treatment_plans, etc. Used by the frontend to show/hide features, enable/disable buttons, and display upgrade prompts before attempting an action.

**Domain:** tenants

**Priority:** Critical

**Spec ID:** T-09

**Dependencies:** T-06 (tenant-settings-get.md), T-08 (tenant-usage-stats.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Works for `active` and `suspended` tenants. For suspended tenants, all write-action flags return false.

---

## Endpoint

```
GET /api/v1/settings/plan-limits
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |

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
  "plan_name": "string",
  "plan_display_name": "string",
  "limits": {
    "max_patients": "integer",
    "max_users": "integer",
    "max_storage_mb": "integer",
    "max_appointments_per_month": "integer | null"
  },
  "actions": {
    "can_add_patient": "boolean",
    "can_add_user": "boolean",
    "can_upload_file": "boolean",
    "can_create_appointment": "boolean",
    "can_use_anatomic_odontogram": "boolean",
    "can_use_treatment_plans": "boolean",
    "can_use_prescriptions": "boolean",
    "can_use_patient_portal": "boolean",
    "can_use_whatsapp_reminders": "boolean",
    "can_use_analytics_advanced": "boolean",
    "can_use_electronic_invoice": "boolean",
    "can_use_custom_consent_templates": "boolean",
    "can_use_api_access": "boolean"
  },
  "upgrade_prompts": {
    "add_patient": "string | null",
    "add_user": "string | null",
    "upload_file": "string | null",
    "anatomic_odontogram": "string | null",
    "treatment_plans": "string | null",
    "patient_portal": "string | null",
    "whatsapp_reminders": "string | null",
    "analytics_advanced": "string | null"
  }
}
```

**Example:**
```json
{
  "plan_name": "starter",
  "plan_display_name": "Plan Inicial",
  "limits": {
    "max_patients": 50,
    "max_users": 5,
    "max_storage_mb": 1000,
    "max_appointments_per_month": 200
  },
  "actions": {
    "can_add_patient": true,
    "can_add_user": true,
    "can_upload_file": true,
    "can_create_appointment": true,
    "can_use_anatomic_odontogram": false,
    "can_use_treatment_plans": true,
    "can_use_prescriptions": true,
    "can_use_patient_portal": false,
    "can_use_whatsapp_reminders": false,
    "can_use_analytics_advanced": false,
    "can_use_electronic_invoice": false,
    "can_use_custom_consent_templates": false,
    "can_use_api_access": false
  },
  "upgrade_prompts": {
    "add_patient": null,
    "add_user": null,
    "upload_file": null,
    "anatomic_odontogram": "El odontograma anatómico está disponible desde el Plan Profesional.",
    "treatment_plans": null,
    "patient_portal": "El portal de pacientes está disponible desde el Plan Profesional.",
    "whatsapp_reminders": "Los recordatorios por WhatsApp están disponibles desde el Plan Profesional.",
    "analytics_advanced": "Analítica avanzada está disponible desde el Plan Empresarial."
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT.

#### 403 Forbidden
**When:** Tenant is cancelled.

**Example:**
```json
{
  "error": "tenant_inactive",
  "message": "La cuenta de esta clínica ha sido cancelada."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

---

## Business Logic

**Step-by-step process:**

1. Extract tenant_id and user_id from JWT claims.
2. Resolve tenant context via TenantMiddleware (includes plan features and limits).
3. Load cached usage counts from Redis (or compute if cache miss):
   a. patient_count from `tenant:{tenant_id}:usage:patients`
   b. user_count from `tenant:{tenant_id}:usage:users`
   c. storage_used_mb from `tenant:{tenant_id}:usage:storage`
   d. appointments_this_month from `tenant:{tenant_id}:usage:appointments_month`
4. Resolve plan features from TenantContext.
5. Compute action flags:

| Action | Condition |
|--------|-----------|
| can_add_patient | patient_count < max_patients AND tenant.status == 'active' |
| can_add_user | user_count < max_users AND tenant.status == 'active' |
| can_upload_file | storage_used_mb < max_storage_mb AND tenant.status == 'active' |
| can_create_appointment | appointments_this_month < max_appointments_per_month (or unlimited) AND tenant.status == 'active' |
| can_use_anatomic_odontogram | plan.features.odontogram_anatomic == true |
| can_use_treatment_plans | plan.features.treatment_plans == true |
| can_use_prescriptions | plan.features.prescriptions == true |
| can_use_patient_portal | plan.features.patient_portal == true |
| can_use_whatsapp_reminders | plan.features.whatsapp_reminders == true |
| can_use_analytics_advanced | plan.features.analytics_advanced == true |
| can_use_electronic_invoice | plan.features.electronic_invoice == true |
| can_use_custom_consent_templates | plan.features.custom_consent_templates == true |
| can_use_api_access | plan.features.api_access == true |

6. Generate upgrade prompts for features that are not available:
   - Map each disabled feature to the minimum plan that includes it.
   - Format: "La funcionalidad X está disponible desde el Plan Y."
7. For limit-based actions at capacity, generate prompts:
   - "Ha alcanzado el límite de {resource}. Actualice su plan para continuar."
8. Return response.

**Usage count caching strategy:**

Usage counts for plan-limits are cached in Redis with short TTL (2 minutes) to avoid hitting the database on every frontend navigation. The cache is updated:
- On patient/user creation (increment counter)
- On patient/user deletion (decrement counter)
- On file upload (update storage counter)
- On appointment creation (increment monthly counter)
- Fallback: if cache miss, query the tenant schema live and set cache.

**Validation Rules:**

None (no input beyond JWT).

**Business Rules:**

- All authenticated users can access this endpoint (not just clinic_owner).
- For suspended tenants, all write-action flags (`can_add_*`, `can_create_*`) return false regardless of limits.
- Feature flags (`can_use_*`) are based on plan only, not on tenant status.
- This endpoint is designed to be called frequently (every page load), so it must be fast.
- `max_appointments_per_month = null` means unlimited.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Plan has unlimited patients (max_patients = -1) | can_add_patient = true always (if active). |
| Usage exceeds limit (post-downgrade) | can_add_patient = false, upgrade_prompt generated. |
| Cache miss for usage counts | Fallback to live query, set cache, return response. |
| Suspended tenant | All can_add/can_create = false. can_use features reflect plan. |
| Free plan (all features disabled) | All can_use_* = false, prompts for all features. |

---

## Side Effects

### Database Changes

**Tables affected:**
- None (read-only endpoint)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:usage:patients`: READ
- `tenant:{tenant_id}:usage:users`: READ
- `tenant:{tenant_id}:usage:storage`: READ
- `tenant:{tenant_id}:usage:appointments_month`: READ
- `tenant:{tenant_id}:info`: READ (plan features)

**Cache TTL:** 2 minutes for usage counters

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** No — high-frequency read, no PHI.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms (all cache hits)
- **Maximum acceptable:** < 300ms (cache miss, live queries)

### Caching Strategy
- **Strategy:** Redis cached usage counters + cached plan features
- **Cache key:** `tenant:{tenant_id}:usage:*` and `tenant:{tenant_id}:info`
- **TTL:** 2 minutes for usage counters, 5 minutes for plan info
- **Invalidation:** Usage counters updated on write operations (patient/user/file/appointment CRUD)

### Database Performance

**Queries executed:** 0 on full cache hit; up to 4 COUNT queries on cache miss

**Indexes required:**
- `{schema}.patients.is_active` — INDEX
- `{schema}.users.is_active` — INDEX
- `{schema}.appointments.start_time` — INDEX

**N+1 prevention:** Independent COUNT queries, parallelized with asyncio.gather.

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

**PHI fields in this endpoint:** None (aggregate counts and plan data only)

**Audit requirement:** Not required

---

## Testing

### Test Cases

#### Happy Path
1. Check limits with available capacity
   - **Given:** Tenant has 30/50 patients, plan=starter
   - **When:** GET /api/v1/settings/plan-limits
   - **Then:** can_add_patient=true, can_use_anatomic_odontogram=false

2. Check limits at capacity
   - **Given:** Tenant has 50/50 patients
   - **When:** GET
   - **Then:** can_add_patient=false, upgrade_prompts.add_patient contains message

3. Professional plan features
   - **Given:** Tenant on professional plan with patient_portal=true
   - **When:** GET
   - **Then:** can_use_patient_portal=true, no upgrade prompt

#### Edge Cases
1. Suspended tenant
   - **Given:** Tenant is suspended with capacity available
   - **When:** GET
   - **Then:** All can_add/can_create = false. can_use features reflect plan.

2. Unlimited plan
   - **Given:** Plan max_patients = -1
   - **When:** GET
   - **Then:** can_add_patient=true, limits.max_patients=-1

3. Cache miss
   - **Given:** No usage data in Redis
   - **When:** GET
   - **Then:** Live query executed, cache populated, correct response

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

**Users:** Users with various roles (all should have access)

**Entities:** Tenants on different plans (free, starter, professional) with varying usage levels

### Mocking Strategy

- Redis: Mock or use test Redis instance for cache behavior testing

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Any authenticated user can check plan limits
- [ ] Action flags accurately reflect current usage vs limits
- [ ] Feature flags match plan configuration
- [ ] Upgrade prompts generated for unavailable features
- [ ] Suspended tenants have write actions disabled
- [ ] Response time < 50ms on cache hit
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Plan upgrade flow (billing domain)
- Enforcement of limits at write time (handled by individual create endpoints)
- Detailed usage analytics or trends
- Admin override of limits

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (JWT only)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (N/A)
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
- [x] Response time target defined (< 50ms cache hit)
- [x] Caching strategy stated (Redis counters)
- [x] DB queries optimized (indexes listed)
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
