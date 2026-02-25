# Tenant Get (Detail) Spec

---

## Overview

**Feature:** Superadmin endpoint to retrieve the full details of a single tenant, including name, slug, schema_name, country, plan info, status, usage statistics (patient_count, user_count, storage_used_mb), and timestamps.

**Domain:** tenants

**Priority:** High

**Spec ID:** T-02

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
GET /api/v1/superadmin/tenants/{tenant_id}
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT (superadmin) | Bearer eyJhbGc... |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| tenant_id | Yes | uuid | Valid UUID v4 | Tenant identifier | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| include_usage | No | boolean | true/false, default true | Include live usage stats | true |

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "slug": "string",
  "schema_name": "string",
  "name": "string",
  "country": "string",
  "timezone": "string",
  "locale": "string",
  "owner_email": "string",
  "phone": "string | null",
  "address": "string | null",
  "logo_url": "string | null",
  "onboarding_step": "integer",
  "status": "string",
  "plan": {
    "id": "uuid",
    "name": "string",
    "max_patients": "integer",
    "max_users": "integer",
    "max_storage_mb": "integer",
    "features": "object"
  },
  "settings": "object",
  "usage": {
    "patient_count": "integer",
    "user_count": "integer",
    "storage_used_mb": "number",
    "appointments_this_month": "integer",
    "invoices_this_month": "integer"
  },
  "created_at": "datetime",
  "updated_at": "datetime"
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
  "timezone": "America/Bogota",
  "locale": "es",
  "owner_email": "admin@clinicasonrisa.com",
  "phone": "+573001234567",
  "address": "Calle 100 #15-20, Bogotá",
  "logo_url": "https://cdn.dentalos.app/tenants/a1b2c3d4/logo.png",
  "onboarding_step": 4,
  "status": "active",
  "plan": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "name": "professional",
    "max_patients": 500,
    "max_users": 10,
    "max_storage_mb": 5000,
    "features": {
      "appointments": true,
      "billing": true,
      "patient_portal": true,
      "treatment_plans": true,
      "whatsapp_reminders": true,
      "analytics_advanced": false
    }
  },
  "settings": {
    "odontogram_mode": "classic",
    "default_appointment_duration_min": 30,
    "branding": {
      "primary_color": "#2563EB",
      "clinic_name_display": "Clínica Dental Sonrisa"
    }
  },
  "usage": {
    "patient_count": 327,
    "user_count": 5,
    "storage_used_mb": 1240.5,
    "appointments_this_month": 89,
    "invoices_this_month": 45
  },
  "created_at": "2026-01-15T08:00:00Z",
  "updated_at": "2026-02-20T14:30:00Z"
}
```

### Error Responses

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

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

---

## Business Logic

**Step-by-step process:**

1. Validate `tenant_id` as a valid UUID.
2. Authenticate superadmin from JWT claims.
3. Query `public.tenants` JOIN `public.plans` WHERE `tenants.id = tenant_id`.
4. If not found, return 404.
5. If `include_usage = true` (default), query tenant schema for live usage:
   a. `SELECT COUNT(*) FROM {schema}.patients WHERE is_active = true` -> patient_count
   b. `SELECT COUNT(*) FROM {schema}.users WHERE is_active = true` -> user_count
   c. `SELECT COALESCE(SUM(file_size_bytes), 0) FROM {schema}.patient_documents` -> storage_used_mb (convert bytes to MB)
   d. `SELECT COUNT(*) FROM {schema}.appointments WHERE date_trunc('month', start_time) = date_trunc('month', now())` -> appointments_this_month
   e. `SELECT COUNT(*) FROM {schema}.invoices WHERE date_trunc('month', created_at) = date_trunc('month', now())` -> invoices_this_month
6. Assemble and return response.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| tenant_id | Valid UUID v4 | ID de tenant inválido. |

**Business Rules:**

- Usage stats are fetched live from the tenant schema (not cached) to ensure accuracy for superadmin.
- If `include_usage = false`, the `usage` key is omitted from the response.
- Tenants in any status (including `provisioning`, `suspended`, `cancelled`) are returned.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant in `provisioning` status | Return tenant with null/zero usage (schema may not exist yet). |
| Tenant schema doesn't exist yet | Return tenant data from `public.tenants` with usage as null. |
| Very large tenant (100k+ patients) | COUNT queries may be slow; acceptable for superadmin. |

---

## Side Effects

### Database Changes

**Tables affected:**
- None (read-only endpoint)

### Cache Operations

**Cache keys affected:**
- None (direct query for superadmin accuracy)

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** No — superadmin read-only access to non-PHI data.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms (without usage), < 500ms (with usage)
- **Maximum acceptable:** < 1000ms (with usage for large tenants)

### Caching Strategy
- **Strategy:** No caching (superadmin needs fresh data)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 1 (tenant + plan join) + up to 5 (usage stats if enabled)

**Indexes required:**
- `public.tenants.id` — PRIMARY KEY
- `{schema}.patients.is_active` — INDEX
- `{schema}.users.is_active` — INDEX
- `{schema}.appointments.start_time` — INDEX

**N+1 prevention:** Usage queries are independent COUNT(*) queries, not nested loops.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| tenant_id | Pydantic UUID validator | Only valid UUIDs accepted |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Schema name is looked up from `public.tenants`, never from user input.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None (aggregate counts only, no patient data)

**Audit requirement:** Not required

---

## Testing

### Test Cases

#### Happy Path
1. Retrieve existing tenant with usage
   - **Given:** Tenant exists with patients and users
   - **When:** GET /api/v1/superadmin/tenants/{id}
   - **Then:** 200 OK with full tenant details and usage stats

2. Retrieve tenant without usage
   - **Given:** Tenant exists
   - **When:** GET /api/v1/superadmin/tenants/{id}?include_usage=false
   - **Then:** 200 OK without `usage` key

#### Edge Cases
1. Tenant in provisioning status
   - **Given:** Tenant just created, schema not provisioned yet
   - **When:** GET
   - **Then:** 200 OK with usage as null

#### Error Cases
1. Non-existent tenant
   - **Given:** Random UUID
   - **When:** GET
   - **Then:** 404 Not Found

2. Non-superadmin access
   - **Given:** Regular tenant user JWT
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** One superadmin user

**Entities:** At least one active tenant with patients, users, appointments, and invoices

### Mocking Strategy

- No external services to mock for this endpoint

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Superadmin can retrieve tenant details by ID
- [ ] Usage stats are accurate and match actual tenant data
- [ ] include_usage=false omits the usage block
- [ ] 404 for non-existent tenants
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Tenant editing (see T-04)
- Tenant list/search (see T-03)
- Tenant-side settings view (see T-06)

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
- [x] Audit trail not needed (no PHI)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized (indexes listed)
- [x] Pagination not needed (single resource)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
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
