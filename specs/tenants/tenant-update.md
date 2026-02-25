# Tenant Update Spec

---

## Overview

**Feature:** Superadmin endpoint to update tenant properties: plan_id, status, name, and settings overrides. Plan changes affect feature flags and resource limits immediately. Cache is invalidated to propagate changes.

**Domain:** tenants

**Priority:** High

**Spec ID:** T-04

**Dependencies:** T-01 (tenant-provision.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required (superadmin operates on `public` schema)
- **Special rules:** None

---

## Endpoint

```
PUT /api/v1/superadmin/tenants/{tenant_id}
```

**Rate Limiting:**
- 30 requests per minute per superadmin user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT (superadmin) | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| tenant_id | Yes | uuid | Valid UUID v4 | Tenant identifier | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

None.

### Request Body Schema

All fields are optional. Only provided fields are updated (partial update semantics).

```json
{
  "name": "string (optional) — new clinic display name",
  "plan_id": "uuid (optional) — new plan assignment",
  "status": "string (optional) — active, suspended, cancelled",
  "settings": "object (optional) — settings overrides merged into existing settings"
}
```

**Example Request:**
```json
{
  "plan_id": "d4e5f6a7-b890-1234-5678-901234567890",
  "settings": {
    "odontogram_mode": "anatomic",
    "branding": {
      "primary_color": "#10B981"
    }
  }
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "slug": "string",
  "name": "string",
  "country": "string",
  "status": "string",
  "plan": {
    "id": "uuid",
    "name": "string",
    "max_patients": "integer",
    "max_users": "integer",
    "features": "object"
  },
  "settings": "object",
  "updated_at": "datetime"
}
```

**Example:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "slug": "clinica-sonrisa",
  "name": "Clínica Dental Sonrisa",
  "country": "CO",
  "status": "active",
  "plan": {
    "id": "d4e5f6a7-b890-1234-5678-901234567890",
    "name": "enterprise",
    "max_patients": 5000,
    "max_users": 50,
    "features": {
      "appointments": true,
      "billing": true,
      "patient_portal": true,
      "treatment_plans": true,
      "whatsapp_reminders": true,
      "analytics_advanced": true,
      "api_access": true
    }
  },
  "settings": {
    "odontogram_mode": "anatomic",
    "default_appointment_duration_min": 30,
    "branding": {
      "primary_color": "#10B981",
      "clinic_name_display": "Clínica Dental Sonrisa"
    }
  },
  "updated_at": "2026-02-24T15:45:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid field values or types.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Datos de entrada inválidos.",
  "details": {
    "status": ["Valor no permitido. Opciones: active, suspended, cancelled."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or invalid superadmin JWT.

#### 403 Forbidden
**When:** JWT does not belong to a superadmin user.

#### 404 Not Found
**When:** Tenant with the given `tenant_id` does not exist.

**Example:**
```json
{
  "error": "tenant_not_found",
  "message": "No se encontró el tenant con el ID proporcionado."
}
```

#### 409 Conflict
**When:** Status transition is invalid (e.g., cancelled -> active).

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "No se puede cambiar el estado de 'cancelled' a 'active'. Los tenants cancelados no pueden reactivarse."
}
```

#### 422 Unprocessable Entity
**When:** plan_id does not exist or is inactive. Name too short/long.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validación.",
  "details": {
    "plan_id": ["El plan seleccionado no existe o no está activo."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

---

## Business Logic

**Step-by-step process:**

1. Validate `tenant_id` as a valid UUID.
2. Validate request body against Pydantic schema (`TenantUpdateRequest`).
3. Authenticate superadmin from JWT claims.
4. Load existing tenant from `public.tenants` WHERE `id = tenant_id`.
5. If not found, return 404.
6. If `plan_id` provided: verify plan exists in `public.plans` and `is_active = true`.
7. If `status` provided: validate status transition (see state machine below).
8. If `name` provided: validate length (2-200 chars).
9. If `settings` provided: deep merge with existing `settings` JSONB.
10. Update `public.tenants` row with changed fields, set `updated_at = now()`.
11. If `status` changed to `suspended`: set `suspended_at = now()`.
12. If `status` changed to `cancelled`: set `cancelled_at = now()`.
13. Invalidate Redis cache for the tenant.
14. Log audit entry.
15. Return updated tenant with plan info.

**Status state machine:**

```
provisioning -> active (automatic, via async job)
active -> suspended (superadmin action)
active -> cancelled (superadmin action)
suspended -> active (superadmin reactivation)
suspended -> cancelled (superadmin action)
cancelled -> (terminal state, no transitions allowed)
```

**Settings deep merge:**

The `settings` field uses deep merge, not replacement. Example:
- Existing: `{"odontogram_mode": "classic", "branding": {"primary_color": "#2563EB"}}`
- Update payload: `{"branding": {"primary_color": "#10B981"}}`
- Result: `{"odontogram_mode": "classic", "branding": {"primary_color": "#10B981"}}`

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| name | 2-200 characters | El nombre debe tener entre 2 y 200 caracteres. |
| plan_id | Valid UUID, references active plan | El plan seleccionado no existe o no está activo. |
| status | Enum: active, suspended, cancelled | Valor de estado no permitido. |
| settings | Valid JSON object | Los ajustes deben ser un objeto JSON válido. |

**Business Rules:**

- Plan changes take effect immediately. The next request from the tenant will use new limits/features.
- Downgrading a plan does NOT retroactively delete data that exceeds new limits. It prevents new data creation.
- Status change to `suspended` makes the tenant read-only (enforced by TenantMiddleware).
- Status change to `cancelled` is a terminal state. The tenant can no longer access the system.
- Slug and country cannot be changed via this endpoint (immutable after creation).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Plan downgrade while over limits | Allowed. Existing data preserved. New writes blocked at limit. |
| Update with empty body | 200 OK, no changes, updated_at unchanged. |
| Settings deep merge with null value | Null removes the key from settings. |
| Updating a provisioning tenant | Allowed for plan_id, name, settings. Status cannot be changed from provisioning. |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `public.tenants`: UPDATE — name, plan_id, status, settings, suspended_at, cancelled_at, updated_at

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:info`: INVALIDATE — forces reload on next request
- `tenant:{tenant_id}:plan`: INVALIDATE — plan features/limits refreshed
- `tenant:{tenant_id}:settings`: INVALIDATE

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | tenant.plan_changed | { tenant_id, old_plan, new_plan, owner_email } | When plan_id changes |
| notifications | tenant.status_changed | { tenant_id, old_status, new_status, owner_email } | When status changes |

### Audit Log

**Audit entry:** Yes — platform-level audit.

- **Action:** update
- **Resource:** tenant
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes (conditional)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | plan_change_notification | owner_email | Plan changed |
| email | tenant_suspended_notice | owner_email | Status changed to suspended |
| email | tenant_cancelled_notice | owner_email | Status changed to cancelled |

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Cache invalidation on update
- **Cache key:** `tenant:{tenant_id}:info`, `tenant:{tenant_id}:plan`
- **TTL:** Invalidated on update
- **Invalidation:** Immediate on this endpoint

### Database Performance

**Queries executed:** 2-3 (load tenant, optionally load plan, update tenant)

**Indexes required:**
- `public.tenants.id` — PRIMARY KEY
- `public.plans.id` — PRIMARY KEY

**N+1 prevention:** Single UPDATE query with all changed fields.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| tenant_id | Pydantic UUID validator | Only valid UUIDs |
| name | Pydantic strip, max 200 chars | HTML stripped |
| plan_id | Pydantic UUID validator | Only valid UUIDs |
| status | Pydantic Literal/Enum | Only allowed values |
| settings | Pydantic dict validator | Keys validated against allowed schema |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** Write-only logged (superadmin action)

---

## Testing

### Test Cases

#### Happy Path
1. Update plan
   - **Given:** Tenant exists with starter plan
   - **When:** PUT with plan_id for professional plan
   - **Then:** 200 OK, plan updated, cache invalidated

2. Update name
   - **Given:** Tenant exists
   - **When:** PUT with new name
   - **Then:** 200 OK, name updated

3. Deep merge settings
   - **Given:** Tenant has existing settings
   - **When:** PUT with partial settings
   - **Then:** 200 OK, settings merged correctly

#### Edge Cases
1. Empty body
   - **Given:** Valid tenant
   - **When:** PUT with {}
   - **Then:** 200 OK, no changes

2. Plan downgrade over limits
   - **Given:** Tenant has 200 patients, new plan max_patients = 50
   - **When:** PUT with downgrade plan
   - **Then:** 200 OK, plan changed (existing data preserved)

#### Error Cases
1. Invalid status transition
   - **Given:** Tenant is cancelled
   - **When:** PUT with status=active
   - **Then:** 409 Conflict

2. Non-existent tenant
   - **Given:** Random UUID
   - **When:** PUT
   - **Then:** 404 Not Found

3. Invalid plan
   - **Given:** Non-existent plan_id
   - **When:** PUT
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** One superadmin user

**Entities:** Tenants in various statuses, multiple active plans

### Mocking Strategy

- RabbitMQ: Mock queue publisher
- Redis: Mock or use test Redis instance

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Superadmin can update tenant plan, name, status, and settings
- [ ] Plan changes take effect immediately via cache invalidation
- [ ] Status transitions follow the state machine
- [ ] Settings deep merge works correctly
- [ ] Notifications dispatched on plan/status changes
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Slug changes (immutable after creation)
- Country changes (immutable)
- Tenant deletion (data export + schema drop — separate spec)
- Billing integration for plan changes

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
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for superadmin action

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized (indexes listed)
- [x] Pagination not needed (single resource)

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
| 1.0 | 2026-02-24 | Initial spec |
