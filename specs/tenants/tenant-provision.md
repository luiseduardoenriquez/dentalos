# Tenant Provisioning Spec

---

## Overview

**Feature:** Superadmin endpoint to create a new tenant (dental clinic). Creates the `public.tenants` row, dispatches an async job to provision the PostgreSQL schema (`tn_{short_id}`), run Alembic migrations, create the admin user, and seed default data (consent templates, service catalog).

**Domain:** tenants

**Priority:** Critical

**Spec ID:** T-01

**Dependencies:** I-01 (multi-tenancy.md), I-04 (database-architecture.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required (superadmin operates on `public` schema)
- **Special rules:** Superadmin JWT is issued from `public.superadmin_users`, not from a tenant schema.

---

## Endpoint

```
POST /api/v1/superadmin/tenants
```

**Rate Limiting:**
- 10 requests per minute per superadmin user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT (superadmin) | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "name": "string (required) — clinic display name",
  "slug": "string (required) — URL-safe identifier, lowercase, a-z 0-9 hyphens only",
  "country": "string (required) — ISO 3166-1 alpha-2 code",
  "plan_id": "uuid (required) — references public.plans",
  "owner_email": "string (required) — email of the first clinic_owner user",
  "owner_name": "string (required) — full name of the clinic owner",
  "timezone": "string (optional) — IANA timezone, defaults based on country",
  "locale": "string (optional) — defaults to 'es'"
}
```

**Example Request:**
```json
{
  "name": "Clínica Dental Sonrisa",
  "slug": "clinica-sonrisa",
  "country": "CO",
  "plan_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "owner_email": "admin@clinicasonrisa.com",
  "owner_name": "Dr. María García",
  "timezone": "America/Bogota"
}
```

---

## Response

### Success Response

**Status:** 202 Accepted

**Schema:**
```json
{
  "id": "uuid",
  "slug": "string",
  "schema_name": "string",
  "name": "string",
  "country": "string",
  "plan_id": "uuid",
  "status": "provisioning",
  "owner_email": "string",
  "created_at": "datetime"
}
```

**Example:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "slug": "clinica-sonrisa",
  "schema_name": "tn_a1b2c3d4",
  "name": "Clínica Dental Sonrisa",
  "country": "CO",
  "plan_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "status": "provisioning",
  "owner_email": "admin@clinicasonrisa.com",
  "created_at": "2026-02-24T10:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields or invalid field format.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Datos de entrada inválidos.",
  "details": {
    "slug": ["El slug solo puede contener letras minúsculas, números y guiones."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or invalid superadmin JWT.

#### 403 Forbidden
**When:** JWT does not belong to a superadmin user.

#### 409 Conflict
**When:** Slug already exists or owner_email already owns another tenant.

**Example:**
```json
{
  "error": "slug_taken",
  "message": "El slug 'clinica-sonrisa' ya está en uso. Elija otro."
}
```

#### 422 Unprocessable Entity
**When:** plan_id does not exist or is inactive. Country code not supported.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validación.",
  "details": {
    "plan_id": ["El plan seleccionado no existe o no está activo."],
    "country": ["Código de país no soportado."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Database error during tenant row insertion. Schema provisioning errors are handled asynchronously and do not affect this response.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema (`TenantCreateRequest`).
2. Authenticate superadmin from JWT claims.
3. Verify `plan_id` exists in `public.plans` and `is_active = true`.
4. Verify `slug` is unique in `public.tenants`.
5. Verify `owner_email` is not already an owner of another active tenant.
6. Generate `schema_name` as `tn_` + first 8 hex chars of the new tenant UUID.
7. Handle collision: if `schema_name` exists, extend to first 12 chars.
8. Derive default `timezone` from `country` if not provided (CO -> America/Bogota, MX -> America/Mexico_City, CL -> America/Santiago).
9. Insert row into `public.tenants` with `status = 'provisioning'`.
10. Dispatch `tenant.provision` job to RabbitMQ with tenant_id and owner details.
11. Return 202 Accepted with the tenant record.

**Async provisioning job (`tenant.provision`):**

1. Create PostgreSQL schema `tn_{short_id}`.
2. Run Alembic migrations on the new schema (`alembic upgrade head` with `--schema` flag).
3. Create the `clinic_owner` user in `{schema}.users` with a temporary random password.
4. Seed default `consent_templates` (informed consent, data processing consent).
5. Seed default `service_catalog` entries (common dental procedures with country-specific pricing).
6. Insert default `tenant_settings` keys (odontogram_mode=classic, appointment_duration=30, etc.).
7. Update `public.tenants` row: set `status = 'active'`, set `owner_user_id`.
8. Dispatch `tenant.welcome_email` job with temporary password and login URL.
9. On failure: set `status = 'provisioning'`, log error, alert superadmin via notification.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| name | 2-200 characters | El nombre debe tener entre 2 y 200 caracteres. |
| slug | 3-63 chars, lowercase, `^[a-z0-9][a-z0-9-]*[a-z0-9]$` | El slug solo puede contener letras minúsculas, números y guiones. |
| country | Must be in supported list: CO, MX, CL, PE, EC, AR | Código de país no soportado. |
| plan_id | Valid UUID, references active plan | El plan seleccionado no existe o no está activo. |
| owner_email | Valid email, max 320 chars | Formato de correo electrónico inválido. |
| owner_name | 2-200 characters | El nombre del propietario debe tener entre 2 y 200 caracteres. |
| timezone | Valid IANA timezone | Zona horaria inválida. |

**Business Rules:**

- A slug cannot be reused even from cancelled/deleted tenants.
- One owner_email can own at most one active tenant (but can be a user in others).
- Schema provisioning is asynchronous; the API returns immediately with `status = 'provisioning'`.
- The async job must be idempotent (re-runnable on failure).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Schema name collision (first 8 chars) | Extend to 12 chars of UUID. |
| Async provisioning fails mid-way | Tenant stays in `provisioning` status. Superadmin can retry or investigate. Partial schema is cleaned up by the retry logic. |
| Plan has zero limits (free trial) | Tenant is created normally; limits are enforced at usage time. |
| Owner email already has an account in another tenant | Allowed. The new tenant creates a separate user record. |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `public.tenants`: INSERT — new tenant row with `status = 'provisioning'`

**Tenant schema tables affected (async):**
- Schema `tn_{short_id}`: CREATE SCHEMA
- `{schema}.users`: INSERT — clinic_owner user
- `{schema}.consent_templates`: INSERT — default consent templates
- `{schema}.service_catalog`: INSERT — default service catalog
- `{schema}.tenant_settings`: INSERT — default settings

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:info`: SET after provisioning completes — tenant data with plan info
- `superadmin:tenants:list`: INVALIDATE — cached tenant list

**Cache TTL:** 5 minutes for tenant info

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| tenant_provisioning | tenant.provision | { tenant_id, schema_name, owner_email, owner_name, plan_id, country } | After tenant row insert |
| notifications | tenant.welcome_email | { owner_email, owner_name, tenant_name, temp_password, login_url } | After provisioning completes |

### Audit Log

**Audit entry:** Yes — logged in a platform-level audit table (not tenant-scoped).

- **Action:** create
- **Resource:** tenant
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | welcome_clinic_owner | owner_email | After async provisioning completes |

---

## Performance

### Expected Response Time
- **Target:** < 300ms (synchronous part only)
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching for the POST itself. Tenant info cached after provisioning.
- **Cache key:** `tenant:{tenant_id}:info`
- **TTL:** 5 minutes
- **Invalidation:** On tenant update or status change

### Database Performance

**Queries executed:** 3 (check plan, check slug uniqueness, insert tenant)

**Indexes required:**
- `public.tenants.slug` — UNIQUE
- `public.tenants.schema_name` — UNIQUE
- `public.plans.id` — PRIMARY KEY

**N+1 prevention:** Not applicable (single insert)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| name | Pydantic strip, max 200 chars | HTML stripped |
| slug | Pydantic regex validator, lowercase forced | Only safe chars allowed |
| owner_email | Pydantic EmailStr, lowercase | Normalized |
| owner_name | Pydantic strip, max 200 chars | HTML stripped |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Schema name is generated from UUID (hex-only), never from user input.

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
1. Create tenant with valid data
   - **Given:** Superadmin is authenticated, plan exists, slug is unique
   - **When:** POST with valid payload
   - **Then:** 202 Accepted, tenant in `provisioning` status, async job dispatched

2. Create tenant with default timezone derivation
   - **Given:** No timezone provided, country = "MX"
   - **When:** POST
   - **Then:** Timezone defaults to "America/Mexico_City"

#### Edge Cases
1. Schema name collision
   - **Given:** Two tenants whose UUIDs share first 8 hex chars
   - **When:** Second tenant is created
   - **Then:** Schema name extended to 12 chars, no collision

#### Error Cases
1. Duplicate slug
   - **Given:** Tenant with slug "clinica-sonrisa" exists
   - **When:** POST with same slug
   - **Then:** 409 Conflict

2. Invalid plan_id
   - **Given:** plan_id does not exist
   - **When:** POST
   - **Then:** 422 Unprocessable Entity

3. Non-superadmin JWT
   - **Given:** JWT belongs to a regular tenant user
   - **When:** POST
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** One superadmin user in `public.superadmin_users`

**Entities:** At least two active plans in `public.plans`

### Mocking Strategy

- RabbitMQ: Mock queue publisher to capture dispatched jobs
- Alembic migrations: Mock in unit tests, run in integration tests
- Email service: Mock SMTP/email provider

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Superadmin can create a tenant with valid data and receives 202 Accepted
- [ ] Async provisioning creates schema, runs migrations, seeds data
- [ ] Admin user is created with temporary password
- [ ] Welcome email is sent to owner after provisioning
- [ ] Duplicate slugs return 409
- [ ] Invalid plans return 422
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Self-service tenant registration (covered by auth/register.md)
- Plan billing integration (covered by billing domain)
- Tenant deletion or data export
- Custom domain setup

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
- [x] Caching strategy stated
- [x] DB queries optimized (indexes listed)
- [x] Pagination not needed (single resource creation)

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
