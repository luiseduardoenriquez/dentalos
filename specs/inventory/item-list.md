# INV-02 List Inventory Items Spec

---

## Overview

**Feature:** List all inventory items for the authenticated clinic. Supports filtering by category, expiry status (semaphore colors: ok/warning/critical/expired), low stock flag, and name search. Items can be sorted by expiry_date ascending (most urgent first) or by name. Returns semaphore color indicators per item. Paginated.

**Domain:** inventory

**Priority:** Low

**Dependencies:** INV-01 (item-create.md), INV-03 (item-update.md), INV-04 (alerts.md), infra/authentication-rules.md, infra/caching.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, assistant, doctor, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** All clinic staff may view inventory. Patient role cannot access inventory.

---

## Endpoint

```
GET /api/v1/inventory/items
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
| category | No | string | Enum: material, instrument, implant, medication | Filter by category | material |
| expiry_status | No | string | Enum: ok, warning, critical, expired | Filter by semaphore status | critical |
| low_stock | No | boolean | true or false | Filter to items where quantity < minimum_stock | true |
| search | No | string | Max 100 chars | Case-insensitive search on item name | resina |
| sort | No | string | Enum: expiry_asc, name_asc — default: expiry_asc | Sort order | expiry_asc |
| cursor | No | string | Opaque base64 cursor | Pagination cursor | eyJpZCI6Ii4uLiJ9 |
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
      "name": "string",
      "category": "string",
      "quantity": "number",
      "unit": "string",
      "lot_number": "string | null",
      "expiry_date": "string ISO 8601 date | null",
      "expiry_status": "string — ok | warning | critical | expired",
      "semaphore_color": "string — green | yellow | orange | red (UI mapping of expiry_status)",
      "manufacturer": "string | null",
      "supplier": "string | null",
      "cost_per_unit": "integer | null — cents",
      "minimum_stock": "number",
      "is_low_stock": "boolean",
      "location": "string | null",
      "created_at": "string ISO 8601",
      "updated_at": "string ISO 8601"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  },
  "summary": {
    "total_items": "integer — total items (unfiltered)",
    "expired_count": "integer",
    "critical_count": "integer — expiry within 30 days",
    "warning_count": "integer — expiry within 31-60 days",
    "low_stock_count": "integer"
  }
}
```

**Example:**
```json
{
  "items": [
    {
      "id": "inv-aabb-1122-ccdd-3344-eeff55667788",
      "name": "Anestesia Lidocaina 2%",
      "category": "medication",
      "quantity": 3,
      "unit": "boxes",
      "lot_number": "LIDO-2025-0512",
      "expiry_date": "2026-03-10",
      "expiry_status": "critical",
      "semaphore_color": "orange",
      "manufacturer": "Scandinibsa",
      "supplier": "Dentales SAS",
      "cost_per_unit": 120000,
      "minimum_stock": 5,
      "is_low_stock": true,
      "location": "Refrigerador Consultorio 1",
      "created_at": "2026-01-10T09:00:00Z",
      "updated_at": "2026-02-20T14:30:00Z"
    },
    {
      "id": "inv-bbcc-2233-ddee-4455-ff0066778899",
      "name": "Guantes Latex Talla M",
      "category": "material",
      "quantity": 180,
      "unit": "units",
      "lot_number": null,
      "expiry_date": "2026-04-01",
      "expiry_status": "warning",
      "semaphore_color": "yellow",
      "manufacturer": "Medline",
      "supplier": "MedSupply Colombia",
      "cost_per_unit": 800,
      "minimum_stock": 50,
      "is_low_stock": false,
      "location": "Bodega Principal",
      "created_at": "2026-01-15T09:00:00Z",
      "updated_at": "2026-01-15T09:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJleHBpcnlfZGF0ZSI6IjIwMjYtMDQtMDEiLCJpZCI6Imljdi1iYmNjLTIyMzMifQ==",
    "has_more": true,
    "total_count": 47
  },
  "summary": {
    "total_items": 52,
    "expired_count": 1,
    "critical_count": 3,
    "warning_count": 8,
    "low_stock_count": 5
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient role attempts to access inventory.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver el inventario."
}
```

#### 422 Unprocessable Entity
**When:** Invalid query parameter values.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "expiry_status": ["Estado de vencimiento invalido. Opciones: ok, warning, critical, expired."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`. If role=patient, return 403.
2. Validate query parameters.
3. Build cache key: `tenant:{tenant_id}:inventory:items:{hash(query_params)}`. Check Redis. If cache hit, return cached response.
4. If cache miss, set `search_path` to tenant schema.
5. Build main query with filters:
   - Base: `SELECT * FROM inventory_items WHERE tenant_id = :tenant_id`
   - `category` filter: `AND category = :category`
   - `expiry_status` filter: `AND expiry_status = :expiry_status`
   - `low_stock = true`: `AND quantity < minimum_stock`
   - `search`: `AND name ILIKE :pattern`
   - Cursor: keyset based on sort order:
     - `sort=expiry_asc`: `ORDER BY expiry_date ASC NULLS LAST, id ASC`. Cursor: `{ "expiry_date": "...", "id": "..." }`. Condition: `(expiry_date, id) > (:expiry_date, :id)`.
     - `sort=name_asc`: `ORDER BY name ASC, id ASC`. Cursor: `{ "name": "...", "id": "..." }`.
   - LIMIT `:limit + 1`
6. Run summary query (same tenant_id, no other filters): count per expiry_status and low_stock.
7. Cache summary separately: `tenant:{tenant_id}:inventory:summary` (TTL 300s).
8. Map `expiry_status` to `semaphore_color`: ok→green, warning→yellow, critical→orange, expired→red.
9. Compute `is_low_stock` per item: `quantity < minimum_stock`.
10. Build pagination cursor from last item.
11. Cache main query result: `tenant:{tenant_id}:inventory:items:{params_hash}`, TTL = 300s (5 minutes).
12. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| category | Enum (if provided) | Categoria invalida. |
| expiry_status | Enum: ok, warning, critical, expired (if provided) | Estado invalido. |
| sort | Enum: expiry_asc, name_asc (if provided) | Ordenamiento invalido. |
| search | Max 100 chars (if provided) | La busqueda no puede superar 100 caracteres. |
| limit | Integer 1-100 | El limite debe estar entre 1 y 100. |

**Business Rules:**

- Semaphore color mapping is deterministic and defined in code: ok=green, warning=yellow, critical=orange, expired=red. This reflects the "semaphore" UI pattern described in the project requirements.
- The `summary` block in the response always returns counts for the entire inventory (unfiltered), regardless of what filters are applied to the items list. This allows the dashboard to show global alert counts even when browsing a filtered view.
- Default sort is `expiry_asc` — most urgent items (closest to expiry) appear first. This surfaces critical items immediately without requiring staff to filter.
- `is_low_stock` is computed in the application layer from stored `quantity` and `minimum_stock` values. It is not a stored column.
- Items with no expiry_date (`expiry_date = null`) are sorted last when `sort=expiry_asc` (NULLS LAST). They have `expiry_status=ok` and `semaphore_color=green`.
- The cache TTL of 5 minutes is acceptable for inventory data — exact real-time accuracy is not required for browsing, but alerts (INV-04) have their own refresh mechanism.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No items in inventory | items: [], total_count: 0, summary all zeros |
| All items have no expiry date | expiry_status=ok for all, sorted by id ASC |
| low_stock=true with no low-stock items | items: [], total_count: 0, summary.low_stock_count from full inventory |
| expiry_status=expired combined with low_stock=true | Returns items that are BOTH expired AND low stock |
| category=implant with no implants | items: [] |

---

## Side Effects

### Database Changes

**No write operations** — read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:inventory:items:{params_hash}`: SET on cache miss
- `tenant:{tenant_id}:inventory:summary`: SET on cache miss (shared with INV-04)

**Cache TTL:** 300 seconds (5 minutes)

**Cache invalidation:** Pattern DELETE `tenant:{tenant_id}:inventory:*` on any inventory write (INV-01, INV-03).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — routine inventory browsing.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 30ms (cache hit)
- **Target:** < 150ms (cache miss)
- **Maximum acceptable:** < 300ms (cache miss with search)

### Caching Strategy
- **Strategy:** Per-query response cache with 5-minute TTL
- **Cache key:** `tenant:{tenant_id}:inventory:items:{params_hash}`
- **TTL:** 300 seconds
- **Invalidation:** Pattern DELETE on any inventory write

### Database Performance

**Queries executed (cache miss):** 2 (main paginated query + summary count query)

**Indexes required:**
- `inventory_items.(tenant_id, expiry_date ASC, id ASC)` — COMPOSITE INDEX for expiry sort
- `inventory_items.(tenant_id, name ASC, id ASC)` — COMPOSITE INDEX for name sort
- `inventory_items.(tenant_id, category)` — COMPOSITE INDEX for category filter
- `inventory_items.(tenant_id, expiry_status)` — COMPOSITE INDEX for status filter
- `inventory_items.name` — GIN index for ILIKE search: `CREATE INDEX ON inventory_items USING gin(to_tsvector('spanish', name))`

**N+1 prevention:** All fields returned in single query. No per-item sub-queries.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset based on sort order)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| category, expiry_status, sort | Pydantic enum | Whitelist |
| search | Pydantic strip(), max_length=100 | ILIKE — parameterized |
| limit | Pydantic int, ge=1, le=100 | |
| cursor | Base64 decode + JSON parse | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — operational inventory data.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. List all items (default sort expiry_asc)
   - **Given:** 47 items, clinic_owner authenticated
   - **When:** GET /api/v1/inventory/items
   - **Then:** 20 items, has_more=true, most critical expiry_date first, semaphore colors correct, summary counts accurate

2. Filter by expiry_status=critical
   - **Given:** 3 items with expiry_status=critical
   - **When:** GET with expiry_status=critical
   - **Then:** 3 items, all with semaphore_color=orange

3. Filter low_stock=true
   - **Given:** 5 items with quantity < minimum_stock
   - **When:** GET with low_stock=true
   - **Then:** Exactly those 5 items

4. Sort by name
   - **Given:** Multiple items
   - **When:** GET with sort=name_asc
   - **Then:** Items in alphabetical order by name

#### Error Cases
1. Patient role
   - **Given:** Authenticated patient
   - **When:** GET
   - **Then:** 403 Forbidden

2. Invalid expiry_status
   - **Given:** expiry_status=blue
   - **When:** GET
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** clinic_owner, assistant, doctor, receptionist, patient

**Inventory Items:** 52 items across categories; items in each expiry_status; items in low stock; items with no expiry date

### Mocking Strategy

- Redis: `fakeredis` for cache hit/miss
- Database: SQLite in-memory; compute expiry_status in application layer (PostgreSQL generated column not in SQLite)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns paginated list with correct semaphore_color mapping
- [ ] Default sort is expiry_asc (most urgent first)
- [ ] category, expiry_status, low_stock, search filters work correctly
- [ ] summary block counts accurate for full inventory (not filtered)
- [ ] is_low_stock computed correctly per item
- [ ] Response cached 5 minutes per query combination
- [ ] Cache invalidated on inventory writes
- [ ] Patient role returns 403
- [ ] All test cases pass
- [ ] Performance targets met (< 30ms cache, < 150ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating inventory items (see INV-01)
- Updating quantity or item details (see INV-03)
- Viewing alerts in grouped format (see INV-04)
- Sterilization records (see INV-05, INV-06)
- Implant tracking (see INV-07)
- Inventory export to CSV/Excel

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (5 filter/sort params)
- [x] All outputs defined (items + pagination + summary)
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (staff only)
- [x] Side effects listed (cache only)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Semaphore color mapping documented
- [x] Keyset pagination with sort-aware cursor
- [x] Tenant schema isolation

### Hook 3: Security & Privacy
- [x] Patient access blocked (403)
- [x] No PHI
- [x] ILIKE parameterized

### Hook 4: Performance & Scalability
- [x] 5-minute cache
- [x] GIN index for name search
- [x] Keyset pagination (no OFFSET degradation)

### Hook 5: Observability
- [x] Structured logging (tenant_id, filters applied)
- [x] Cache hit/miss logged

### Hook 6: Testability
- [x] Test cases enumerated
- [x] SQLite expiry_status application-layer fallback documented
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
