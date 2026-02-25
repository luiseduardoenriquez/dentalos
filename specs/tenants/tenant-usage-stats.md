# Tenant Usage Stats Spec

---

## Overview

**Feature:** Clinic owner endpoint to retrieve current tenant usage statistics compared against plan limits. Returns patient_count vs max_patients, user_count vs max_users, storage_used_mb vs max_storage_mb, appointments_this_month, and invoices_this_month. Used by the frontend for plan limit enforcement dashboards and upgrade prompts.

**Domain:** tenants

**Priority:** High

**Spec ID:** T-08

**Dependencies:** T-06 (tenant-settings-get.md), T-01 (tenant-provision.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Works for `active` and `suspended` tenants (read-only endpoint).

---

## Endpoint

```
GET /api/v1/settings/usage
```

**Rate Limiting:**
- 30 requests per minute per user

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
  "plan": {
    "id": "uuid",
    "name": "string",
    "display_name": "string"
  },
  "usage": {
    "patients": {
      "current": "integer",
      "limit": "integer",
      "percentage": "number",
      "at_limit": "boolean"
    },
    "users": {
      "current": "integer",
      "limit": "integer",
      "percentage": "number",
      "at_limit": "boolean"
    },
    "storage_mb": {
      "current": "number",
      "limit": "integer",
      "percentage": "number",
      "at_limit": "boolean"
    },
    "appointments_this_month": {
      "current": "integer",
      "limit": "integer | null",
      "percentage": "number | null",
      "at_limit": "boolean"
    },
    "invoices_this_month": {
      "current": "integer"
    }
  },
  "upgrade_recommended": "boolean",
  "upgrade_reasons": ["string"],
  "fetched_at": "datetime"
}
```

**Example:**
```json
{
  "plan": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "name": "starter",
    "display_name": "Plan Inicial"
  },
  "usage": {
    "patients": {
      "current": 47,
      "limit": 50,
      "percentage": 94.0,
      "at_limit": false
    },
    "users": {
      "current": 3,
      "limit": 5,
      "percentage": 60.0,
      "at_limit": false
    },
    "storage_mb": {
      "current": 420.5,
      "limit": 1000,
      "percentage": 42.05,
      "at_limit": false
    },
    "appointments_this_month": {
      "current": 85,
      "limit": 200,
      "percentage": 42.5,
      "at_limit": false
    },
    "invoices_this_month": {
      "current": 32
    }
  },
  "upgrade_recommended": true,
  "upgrade_reasons": [
    "Está cerca del límite de pacientes (94%). Actualice su plan para agregar más."
  ],
  "fetched_at": "2026-02-24T16:45:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT.

#### 403 Forbidden
**When:** User is not clinic_owner, or tenant is cancelled.

**Example (not owner):**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clínica puede ver las estadísticas de uso."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

---

## Business Logic

**Step-by-step process:**

1. Extract tenant_id and user_id from JWT claims.
2. Resolve tenant context via TenantMiddleware.
3. Verify user role is `clinic_owner`.
4. Load plan limits from tenant context (cached in TenantContext).
5. Query tenant schema for live usage stats:
   a. `SELECT COUNT(*) FROM {schema}.patients WHERE is_active = true` -> patient_count
   b. `SELECT COUNT(*) FROM {schema}.users WHERE is_active = true` -> user_count
   c. `SELECT COALESCE(SUM(file_size_bytes), 0) / (1024.0 * 1024.0) FROM {schema}.patient_documents` -> storage_used_mb
   d. `SELECT COUNT(*) FROM {schema}.appointments WHERE start_time >= date_trunc('month', CURRENT_TIMESTAMP) AND start_time < date_trunc('month', CURRENT_TIMESTAMP) + INTERVAL '1 month'` -> appointments_this_month
   e. `SELECT COUNT(*) FROM {schema}.invoices WHERE created_at >= date_trunc('month', CURRENT_TIMESTAMP) AND created_at < date_trunc('month', CURRENT_TIMESTAMP) + INTERVAL '1 month'` -> invoices_this_month
6. Calculate percentages: `(current / limit) * 100`, rounded to 2 decimal places.
7. Set `at_limit = (current >= limit)`.
8. Determine `upgrade_recommended` if any resource is at >= 80% usage.
9. Build `upgrade_reasons` array with Spanish messages for each resource near limit.
10. Return response with `fetched_at = now()`.

**Upgrade recommendation logic:**

| Condition | Upgrade Reason Message |
|-----------|----------------------|
| patients >= 80% | Está cerca del límite de pacientes ({pct}%). Actualice su plan para agregar más. |
| patients >= 100% | Ha alcanzado el límite de pacientes. No podrá registrar nuevos pacientes. |
| users >= 80% | Está cerca del límite de usuarios ({pct}%). |
| users >= 100% | Ha alcanzado el límite de usuarios. No podrá invitar más miembros. |
| storage >= 80% | El almacenamiento está al {pct}% de capacidad. |
| storage >= 100% | El almacenamiento está lleno. No podrá subir más archivos. |
| appointments >= 90% | Está cerca del límite mensual de citas ({pct}%). |

**Validation Rules:**

None (no input beyond JWT).

**Business Rules:**

- Usage stats are fetched live (not cached) to provide accurate data for limit decisions.
- `at_limit = true` means the resource is at or over the limit.
- `percentage` can exceed 100% if data was added before a plan downgrade.
- `appointments_this_month.limit` is null if the plan has no appointment limit.
- `upgrade_recommended` is true if any resource is >= 80%.
- Invoices have no plan limit; they are informational only.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Plan has unlimited patients (max_patients = -1) | percentage = null, at_limit = false. |
| Usage exceeds limit (post-downgrade) | percentage > 100, at_limit = true. |
| No invoices table data | invoices_this_month.current = 0. |
| Suspended tenant | Stats returned normally (read-only access). |
| Freshly provisioned tenant (0 data) | All counts = 0, percentage = 0.0. |

---

## Side Effects

### Database Changes

**Tables affected:**
- None (read-only endpoint)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:info`: READ for plan limits

**Cache TTL:** N/A (live queries)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** No — read-only, no PHI.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 800ms

### Caching Strategy
- **Strategy:** No caching for usage stats (must be live for limit enforcement)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 5 (one COUNT per resource type)

**Indexes required:**
- `{schema}.patients.is_active` — INDEX
- `{schema}.users.is_active` — INDEX
- `{schema}.appointments.start_time` — INDEX
- `{schema}.invoices.created_at` — INDEX
- `{schema}.patient_documents` — full table scan for SUM (acceptable for file count)

**N+1 prevention:** All queries are independent COUNT/SUM aggregations. Can be run in parallel using `asyncio.gather`.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| JWT claims | Validated by auth middleware | Cryptographically signed |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Schema name from TenantContext (cached, not from user input).

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None (aggregate counts only)

**Audit requirement:** Not required

---

## Testing

### Test Cases

#### Happy Path
1. Get usage stats with data
   - **Given:** Tenant has 47 patients (limit 50), 3 users (limit 5)
   - **When:** GET /api/v1/settings/usage
   - **Then:** 200 OK with accurate counts, percentages, upgrade_recommended=true

2. Get usage stats with zero data
   - **Given:** Freshly provisioned tenant
   - **When:** GET
   - **Then:** 200 OK with all counts = 0

3. Upgrade recommendations generated
   - **Given:** Patients at 94%
   - **When:** GET
   - **Then:** upgrade_recommended=true, upgrade_reasons contains patient message

#### Edge Cases
1. Post-downgrade over-limit
   - **Given:** 200 patients, plan downgraded to max_patients=50
   - **When:** GET
   - **Then:** percentage=400%, at_limit=true

2. Unlimited plan
   - **Given:** Plan max_patients = -1
   - **When:** GET
   - **Then:** percentage=null, at_limit=false

#### Error Cases
1. Non-owner role
   - **Given:** User with doctor role
   - **When:** GET
   - **Then:** 403 Forbidden

2. Cancelled tenant
   - **Given:** Tenant is cancelled
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, doctor

**Entities:** Tenants with varying amounts of patients, users, documents, appointments, invoices

### Mocking Strategy

- No external services to mock (database queries only)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Clinic owner can retrieve live usage stats
- [ ] Counts are accurate for patients, users, storage, appointments, invoices
- [ ] Percentages calculated correctly
- [ ] at_limit flag works for at-limit and over-limit scenarios
- [ ] Upgrade recommendations generated at 80%+ thresholds
- [ ] Non-owner roles get 403
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms with parallel queries)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Historical usage trends / analytics
- Usage alerts or automatic notifications
- Billing metering
- Storage cleanup recommendations

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
- [x] Audit trail not needed (aggregates only)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (live queries)
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
