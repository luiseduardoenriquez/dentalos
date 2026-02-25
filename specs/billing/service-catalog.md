# B-14 Service Catalog Spec

---

## Overview

**Feature:** Retrieve the service/procedure price catalog for the authenticated tenant. The catalog contains all billable procedures with their CUPS codes, names, descriptions, default prices, categories, and active status. Searchable by procedure name or CUPS code. Pre-populated from the standard Colombian dental CUPS subset on tenant creation. Paginated with 30-minute cache.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-15 (service-catalog-update.md), B-01 (invoice-create.md), B-16 (quotation-create.md), infra/caching.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** All authenticated clinic staff may browse the service catalog. Patient role cannot access this endpoint.

---

## Endpoint

```
GET /api/v1/billing/services
```

**Rate Limiting:**
- Inherits global rate limit (100 requests per minute per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| search | No | string | Max 100 chars | Full-text search on name and cups_code | resina |
| category | No | string | Enum: diagnostico, cirugia, periodoncia, operatoria, endodoncia, protesis, ortodoncia, prevencion, otros | Filter by service category | operatoria |
| is_active | No | boolean | true or false — default: true | Filter by active status | true |
| cursor | No | string | Opaque cursor from previous response | Pagination cursor | eyJpZCI6IjEyMyJ9 |
| limit | No | integer | Min 1, max 100, default 20 | Page size | 20 |

### Request Body Schema

None — GET request.

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
      "cups_code": "string | null — CUPS code, e.g. 895101",
      "name": "string — procedure name in es-419",
      "description": "string | null — detailed description",
      "default_price": "integer — price in cents (tenant currency)",
      "category": "string — enum category",
      "is_active": "boolean",
      "created_at": "string ISO 8601",
      "updated_at": "string ISO 8601"
    }
  ],
  "pagination": {
    "next_cursor": "string | null — cursor for next page, null if last page",
    "has_more": "boolean",
    "total_count": "integer — total matching items (used for UI display)"
  }
}
```

**Example:**
```json
{
  "items": [
    {
      "id": "svc-aabb-1122-ccdd-3344-eeff55667788",
      "cups_code": "895101",
      "name": "Resina Compuesta",
      "description": "Restauracion con resina compuesta de una superficie en diente posterior o anterior.",
      "default_price": 70000,
      "category": "operatoria",
      "is_active": true,
      "created_at": "2026-01-15T09:00:00Z",
      "updated_at": "2026-02-01T14:30:00Z"
    },
    {
      "id": "svc-bbcc-2233-ddee-4455-ff0066778899",
      "cups_code": "895301",
      "name": "Limpieza y Profilaxis",
      "description": "Detartraje supragingival y pulido coronario.",
      "default_price": 42000,
      "category": "prevencion",
      "is_active": true,
      "created_at": "2026-01-15T09:00:00Z",
      "updated_at": "2026-01-15T09:00:00Z"
    },
    {
      "id": "svc-ccdd-3344-eeff-5566-001177889900",
      "cups_code": "895501",
      "name": "Endodoncia Unirradicular",
      "description": "Tratamiento de conductos radiculares en diente con un solo conducto.",
      "default_price": 85000,
      "category": "endodoncia",
      "is_active": true,
      "created_at": "2026-01-15T09:00:00Z",
      "updated_at": "2026-01-15T09:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6InN2Yy1jY2RkLTMzNDQtZWVmZi01NTY2LTAwMTE3Nzg4OTkwMCJ9",
    "has_more": true,
    "total_count": 87
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient role attempting to access the catalog.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver el catalogo de servicios."
}
```

#### 422 Unprocessable Entity
**When:** Invalid query parameter values (invalid category enum, non-boolean is_active, limit out of range).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "category": ["Categoria invalida. Opciones: diagnostico, cirugia, periodoncia, operatoria, endodoncia, protesis, ortodoncia, prevencion, otros."],
    "limit": ["El limite debe estar entre 1 y 100."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. Check role: if role = `patient`, return 403. All other authenticated roles allowed.
3. Validate query parameters via Pydantic:
   - `category` must be a valid enum if provided.
   - `limit` must be 1-100.
   - `search` max 100 chars.
   - `cursor` is an opaque base64-encoded JSON string; validate decodable if provided.
4. Build cache key: `tenant:{tenant_id}:billing:services:{hash(query_params)}`. Check Redis. If cache hit, return cached response.
5. If cache miss, set `search_path` to tenant schema.
6. Decode cursor if provided: `{ "id": "last_seen_id" }` for cursor-based pagination using keyset pagination on `id`.
7. Build SQLAlchemy query:
   - Base: `SELECT * FROM service_catalog WHERE tenant_id = :tenant_id`
   - If `is_active` specified: `AND is_active = :is_active` (default: `AND is_active = true`)
   - If `category` specified: `AND category = :category`
   - If `search` specified: `AND (name ILIKE :pattern OR cups_code ILIKE :pattern)` where pattern = `%{search}%`
   - If `cursor` specified: `AND id > :last_id` (keyset pagination — requires stable UUID sort order)
   - ORDER BY `name ASC, id ASC` (stable sort for consistent pagination)
   - LIMIT `:limit + 1` (fetch one extra to determine `has_more`)
8. Execute count query for `total_count` (with same filters but without cursor/limit): `SELECT COUNT(*) FROM service_catalog WHERE ...filters...`. This count is cached separately if expensive.
9. If results length > limit, set `has_more = true` and trim last item. Generate `next_cursor` by encoding last item's `id`.
10. Build response.
11. Store in Redis cache: TTL = 1800s (30 minutes). Cache key includes a hash of all query parameters to avoid cross-query cache collisions.
12. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| search | Max 100 chars (if provided) | La busqueda no puede superar 100 caracteres. |
| category | Enum: diagnostico, cirugia, periodoncia, operatoria, endodoncia, protesis, ortodoncia, prevencion, otros | Categoria invalida. |
| limit | Integer 1-100 | El limite debe estar entre 1 y 100. |
| cursor | Valid base64-decodable JSON with id field (if provided) | Cursor de paginacion invalido. |

**Business Rules:**

- On tenant creation, the `service_catalog` table is pre-populated with the standard Colombian dental CUPS subset (~80-100 procedures) at system-defined default prices. Clinics customize prices via B-15.
- `is_active = false` items are hidden by default (not shown in standard catalog browse). They can be shown by explicitly passing `is_active=false` in the query (useful for staff to re-activate deactivated services).
- `default_price` is stored in integer cents of the tenant's currency (COP for Colombian tenants). All prices are stored as integers to avoid floating-point errors.
- CUPS codes are strings (not integers) to preserve leading zeros and allow alphanumeric codes in future LATAM markets.
- The catalog is tenant-specific — each tenant has their own copy of the service catalog, initialized from the system CUPS seed data. Changes by one tenant do not affect other tenants.
- When `search` is provided, it performs a case-insensitive partial match on both `name` and `cups_code`. For advanced full-text search, a PostgreSQL GIN index on `name` is used.
- The `total_count` in the pagination response is a best-effort count. It may lag slightly for newly added items when served from cache.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| search matches cups_code exactly (e.g. "895101") | Returns that service and any whose name contains "895101" |
| search returns no results | items: [], pagination.total_count: 0, has_more: false |
| is_active=false requested | Returns deactivated services; useful for re-activation workflow |
| All services deactivated | items: [] for default query (is_active=true) |
| limit=1 to test pagination | Returns 1 item, has_more=true if more exist, next_cursor provided |
| cursor from different tenant | Returns empty results (tenant isolation in WHERE clause) |

---

## Side Effects

### Database Changes

**No write operations** — read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:billing:services:{params_hash}`: SET on cache miss

**Cache TTL:** 1800 seconds (30 minutes)

**Cache invalidation:** B-15 (service-catalog-update) deletes the pattern `tenant:{tenant_id}:billing:services:*` on any service update/creation.

**Example cache pattern (Python):**
```python
import hashlib, json

params_hash = hashlib.md5(
    json.dumps({
        "search": search, "category": category,
        "is_active": is_active, "cursor": cursor, "limit": limit
    }, sort_keys=True).encode()
).hexdigest()[:16]

cache_key = f"tenant:{tenant_id}:billing:services:{params_hash}"
```

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — browsing the service catalog is a routine read operation with no PHI.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 30ms (cache hit)
- **Target:** < 100ms (cache miss)
- **Maximum acceptable:** < 200ms (cache miss with search)

### Caching Strategy
- **Strategy:** Per-query response cache with 30-minute TTL
- **Cache key:** `tenant:{tenant_id}:billing:services:{params_hash}`
- **TTL:** 1800 seconds
- **Invalidation:** Pattern DELETE `tenant:{tenant_id}:billing:services:*` on service update

### Database Performance

**Queries executed (cache miss):** 2 (count query, paginated items query)

**Indexes required:**
- `service_catalog.(tenant_id, is_active, name)` — COMPOSITE INDEX for filtered queries
- `service_catalog.(tenant_id, category, is_active)` — COMPOSITE INDEX for category filter
- `service_catalog.cups_code` — INDEX for CUPS search
- `service_catalog.name` — GIN index for full-text search: `CREATE INDEX ON service_catalog USING gin(to_tsvector('spanish', name))`
- `service_catalog.(tenant_id, id)` — COMPOSITE INDEX for keyset pagination

**N+1 prevention:** Single query with all filters and limit. Count query runs separately but is cached.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on `id`)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| search | Pydantic strip(), max_length=100, bleach | Used in ILIKE — parameterized, not interpolated |
| category | Pydantic enum | Whitelist |
| limit | Pydantic int, ge=1, le=100 | Numeric range |
| cursor | Base64 decode + JSON parse; validate structure | Decoded value used in parameterized query |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. `search` parameter is passed as a bound parameter to ILIKE (`%:search%`), never interpolated into SQL string.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — service catalog contains procedure and price data only.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. List first page of active services (default)
   - **Given:** Tenant with 87 active services, no inactive services
   - **When:** GET /api/v1/billing/services (no params)
   - **Then:** 200 OK, 20 items, has_more=true, next_cursor present, total_count=87

2. Search by name
   - **Given:** 5 services with "resina" in the name
   - **When:** GET with search=resina
   - **Then:** 200 OK, exactly those 5 items returned, total_count=5

3. Filter by category
   - **Given:** 12 services in category=endodoncia
   - **When:** GET with category=endodoncia
   - **Then:** 200 OK, items all have category=endodoncia, total_count=12

4. Pagination — second page
   - **Given:** First page returned 20 items with next_cursor
   - **When:** GET with cursor=next_cursor from previous response
   - **Then:** 200 OK, next 20 items, no overlap with first page

5. Cache hit on second request
   - **Given:** Same query params within 30 minutes
   - **When:** Second GET
   - **Then:** Served from cache

#### Edge Cases
1. Search returns no results
   - **Given:** search=xyznonexistent
   - **When:** GET with search
   - **Then:** 200 OK, items=[], total_count=0, has_more=false

2. Request deactivated services
   - **Given:** 3 services with is_active=false
   - **When:** GET with is_active=false
   - **Then:** Only inactive services returned

3. Search matches cups_code
   - **Given:** Service with cups_code=895101
   - **When:** GET with search=895101
   - **Then:** That service appears in results

#### Error Cases
1. Invalid category enum
   - **Given:** category=invalid_cat
   - **When:** GET
   - **Then:** 422 with category validation error

2. Patient role
   - **Given:** Authenticated patient
   - **When:** GET
   - **Then:** 403 Forbidden

3. limit=0
   - **Given:** limit=0
   - **When:** GET
   - **Then:** 422 validation error

### Test Data Requirements

**Service Catalog:** 87 seeded active services across all categories; 3 deactivated services; CUPS codes present on ~70% of entries

**Users:** clinic_owner, doctor, receptionist, patient (for 403 test)

### Mocking Strategy

- Redis: `fakeredis` for cache hit/miss testing
- Database: SQLite in-memory with CUPS dental seed data

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/billing/services returns paginated catalog list
- [ ] Default filter: is_active=true (inactive services hidden)
- [ ] Search works on both name and cups_code (case-insensitive)
- [ ] Category filter returns only matching items
- [ ] Cursor-based pagination works correctly with no duplicates or gaps
- [ ] total_count accurate for filtered queries
- [ ] Response cached 30 minutes per unique query combination
- [ ] Cache invalidated on service update (B-15)
- [ ] Patient role returns 403
- [ ] All monetary values in cents (integer)
- [ ] All test cases pass
- [ ] Performance targets met (< 30ms cache, < 100ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating new custom services (can be done via B-15 with new service creation)
- Updating service prices or details (see B-15 service-catalog-update.md)
- CUPS seed data population at tenant creation (infrastructure concern)
- Bulk import of custom services
- Multi-currency price variants (single currency per tenant for MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (search, category, is_active, cursor, limit)
- [x] All outputs defined (items array + pagination)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (all staff, no patient)
- [x] Side effects listed (cache only)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Cursor-based pagination
- [x] Matches FastAPI conventions

### Hook 3: Security & Privacy
- [x] Input sanitization (search parameterized)
- [x] No PHI
- [x] SQL injection prevented (ILIKE via bound params)

### Hook 4: Performance & Scalability
- [x] 30-minute cache with per-query key
- [x] GIN index for full-text search
- [x] Keyset pagination (no OFFSET performance degradation)

### Hook 5: Observability
- [x] Structured logging (tenant_id, cache hit/miss)
- [x] Error tracking compatible

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data specified
- [x] Mocking strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
