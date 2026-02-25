# Tenant List Spec

---

## Overview

**Feature:** Superadmin endpoint to retrieve a paginated list of all tenants with filtering by plan, status, country, and text search (name/slug/email). Supports sorting by created_at, name, or patient_count.

**Domain:** tenants

**Priority:** High

**Spec ID:** T-03

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
GET /api/v1/superadmin/tenants
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

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| page | No | integer | >= 1, default 1 | Page number | 1 |
| page_size | No | integer | 1-100, default 20 | Items per page | 20 |
| plan_id | No | uuid | Valid UUID | Filter by plan | b2c3d4e5-... |
| status | No | string | active, suspended, cancelled, provisioning | Filter by status | active |
| country | No | string | ISO 3166-1 alpha-2 | Filter by country | CO |
| search | No | string | 1-100 chars | Search name, slug, or owner_email | sonrisa |
| sort_by | No | string | created_at, name, patient_count | Sort field | created_at |
| sort_order | No | string | asc, desc; default desc | Sort direction | desc |

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "string",
      "name": "string",
      "country": "string",
      "status": "string",
      "owner_email": "string",
      "plan": {
        "id": "uuid",
        "name": "string"
      },
      "usage": {
        "patient_count": "integer",
        "user_count": "integer"
      },
      "created_at": "datetime"
    }
  ],
  "total": "integer",
  "page": "integer",
  "page_size": "integer",
  "total_pages": "integer"
}
```

**Example:**
```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "slug": "clinica-sonrisa",
      "name": "Clínica Dental Sonrisa",
      "country": "CO",
      "status": "active",
      "owner_email": "admin@clinicasonrisa.com",
      "plan": {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "name": "professional"
      },
      "usage": {
        "patient_count": 327,
        "user_count": 5
      },
      "created_at": "2026-01-15T08:00:00Z"
    },
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "slug": "dental-mexico",
      "name": "Dental México DF",
      "country": "MX",
      "status": "active",
      "owner_email": "doctora@dentalmexico.mx",
      "plan": {
        "id": "d4e5f6a7-b890-1234-5678-901234567890",
        "name": "starter"
      },
      "usage": {
        "patient_count": 89,
        "user_count": 2
      },
      "created_at": "2026-02-01T12:00:00Z"
    }
  ],
  "total": 47,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter value (e.g., non-numeric page, invalid status).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parámetros de consulta inválidos.",
  "details": {
    "status": ["Valor no permitido. Opciones: active, suspended, cancelled, provisioning."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or invalid superadmin JWT.

#### 403 Forbidden
**When:** JWT does not belong to a superadmin user.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

---

## Business Logic

**Step-by-step process:**

1. Validate query parameters against Pydantic schema.
2. Authenticate superadmin from JWT claims.
3. Build base query: `SELECT t.*, p.name as plan_name, p.id as plan_id FROM public.tenants t JOIN public.plans p ON t.plan_id = p.id`.
4. Apply filters:
   a. If `plan_id`: `WHERE t.plan_id = :plan_id`
   b. If `status`: `WHERE t.status = :status`
   c. If `country`: `WHERE t.country = :country`
   d. If `search`: `WHERE (lower(t.name) LIKE :search OR lower(t.slug) LIKE :search OR lower(t.owner_email) LIKE :search)` using `%{search}%`
5. Count total matching rows for pagination metadata.
6. Apply sorting:
   a. `created_at`: `ORDER BY t.created_at :sort_order`
   b. `name`: `ORDER BY lower(t.name) :sort_order`
   c. `patient_count`: requires subquery or materialized count (see below)
7. Apply pagination: `LIMIT :page_size OFFSET (:page - 1) * :page_size`
8. For each tenant in the result, fetch lightweight usage stats (patient_count, user_count) from a materialized view or cached aggregation.
9. Assemble paginated response.

**Patient count sorting strategy:**

Since patient counts live in tenant schemas, real-time sorting by patient_count across all tenants is expensive. Strategy:

- Maintain a `public.tenant_usage_cache` table updated every 15 minutes by a background job.
- Sort by `tenant_usage_cache.patient_count` when `sort_by=patient_count`.
- Usage stats in the list response come from this cache (acceptable staleness for list view).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| page | Integer >= 1 | El número de página debe ser mayor o igual a 1. |
| page_size | Integer 1-100 | El tamaño de página debe estar entre 1 y 100. |
| status | Enum: active, suspended, cancelled, provisioning | Valor de estado no permitido. |
| country | 2-char ISO code | Código de país inválido. |
| search | 1-100 chars | La búsqueda debe tener entre 1 y 100 caracteres. |
| sort_by | Enum: created_at, name, patient_count | Campo de ordenamiento no válido. |
| sort_order | Enum: asc, desc | Dirección de ordenamiento no válida. |

**Business Rules:**

- Deleted tenants (status = 'cancelled' with deleted_at set) are excluded by default unless `status=cancelled` is explicitly filtered.
- Search is case-insensitive and uses ILIKE for partial matching.
- Default sort is `created_at DESC` (newest first).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No tenants match filters | Return empty `items` array with `total: 0`. |
| Page exceeds total_pages | Return empty `items` array (no error). |
| Search with special SQL chars (%, _) | Escaped by SQLAlchemy parameterization. |
| Very long search string | Truncated to 100 chars by validation. |

---

## Side Effects

### Database Changes

**Tables affected:**
- None (read-only endpoint)

### Cache Operations

**Cache keys affected:**
- Reads from `superadmin:tenants:usage_cache` for patient/user counts

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** No

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Tenant usage stats read from materialized cache table
- **Cache key:** `public.tenant_usage_cache` table
- **TTL:** Refreshed every 15 minutes by background job
- **Invalidation:** Background job recomputes

### Database Performance

**Queries executed:** 2 (count query + data query with JOIN)

**Indexes required:**
- `public.tenants.status` — INDEX
- `public.tenants.country` — INDEX
- `public.tenants.plan_id` — INDEX
- `public.tenants.slug` — INDEX
- `public.tenants.created_at` — INDEX (for sort)
- `public.tenants.name` — INDEX (for sort and search, use `lower(name)`)

**N+1 prevention:** Usage stats come from a pre-aggregated cache table, joined in the main query. No per-tenant subqueries.

### Pagination

**Pagination:** Yes

- **Style:** offset-based
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| search | Pydantic strip, max 100 chars | SQL special chars escaped by parameterized query |
| plan_id | Pydantic UUID validator | Only valid UUIDs |
| status | Pydantic Literal/Enum | Only allowed values |
| country | Pydantic regex [A-Z]{2} | Uppercase enforced |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. ILIKE patterns use parameterized `%search%`.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** Not required

---

## Testing

### Test Cases

#### Happy Path
1. List all tenants (no filters)
   - **Given:** 5 tenants exist
   - **When:** GET /api/v1/superadmin/tenants
   - **Then:** 200 OK with all 5 tenants, default sort created_at DESC

2. Filter by status
   - **Given:** 3 active, 2 suspended
   - **When:** GET ?status=active
   - **Then:** 200 OK with 3 tenants

3. Search by name
   - **Given:** Tenant named "Clinica Sonrisa"
   - **When:** GET ?search=sonrisa
   - **Then:** 200 OK with matching tenant

4. Pagination
   - **Given:** 25 tenants
   - **When:** GET ?page=2&page_size=10
   - **Then:** 200 OK with 10 items, total=25, total_pages=3

#### Edge Cases
1. Empty results
   - **Given:** No tenants match filter
   - **When:** GET ?status=cancelled
   - **Then:** 200 OK with empty items, total=0

#### Error Cases
1. Invalid status value
   - **Given:** status=invalid
   - **When:** GET
   - **Then:** 400 Bad Request

2. Non-superadmin access
   - **Given:** Tenant user JWT
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** One superadmin user

**Entities:** 5+ tenants across different plans, statuses, and countries

### Mocking Strategy

- No external services to mock

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Superadmin can list tenants with pagination
- [ ] Filtering by plan_id, status, country, and search works
- [ ] Sorting by created_at, name, and patient_count works
- [ ] Usage stats are included for each tenant
- [ ] Empty results return correctly
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Tenant export to CSV/Excel
- Bulk operations on tenants
- Real-time usage stats (uses cached aggregation)

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
- [x] Caching strategy stated (materialized cache)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied

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
