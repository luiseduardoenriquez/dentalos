# INV-04 Inventory Alerts Spec

---

## Overview

**Feature:** Retrieve active inventory alerts grouped by type: expired items, critical items (expiry within 30 days), and low stock items. Returns item summaries per group. A daily background cron checks inventory and dispatches alert notifications via RabbitMQ to clinic_owner email. Also provides the alert badge count for use in the dashboard header.

**Domain:** inventory

**Priority:** Low

**Dependencies:** INV-01 (item-create.md), INV-02 (item-list.md), INV-03 (item-update.md), infra/caching.md, infra/bg-processing.md, RabbitMQ

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner and assistant see alert details. The badge count (total_alerts) is available to all staff roles via the summary endpoint.

---

## Endpoint

```
GET /api/v1/inventory/alerts
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

None.

### Request Body Schema

None — GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "expired_items": [
    {
      "id": "uuid",
      "name": "string",
      "category": "string",
      "quantity": "number",
      "unit": "string",
      "expiry_date": "string ISO 8601 date",
      "days_since_expiry": "integer — positive number = days past expiry",
      "lot_number": "string | null",
      "location": "string | null"
    }
  ],
  "critical_items": [
    {
      "id": "uuid",
      "name": "string",
      "category": "string",
      "quantity": "number",
      "unit": "string",
      "expiry_date": "string ISO 8601 date",
      "days_until_expiry": "integer — 0 to 30",
      "lot_number": "string | null",
      "location": "string | null"
    }
  ],
  "low_stock_items": [
    {
      "id": "uuid",
      "name": "string",
      "category": "string",
      "quantity": "number",
      "unit": "string",
      "minimum_stock": "number",
      "stock_deficit": "number — minimum_stock - quantity",
      "location": "string | null",
      "supplier": "string | null"
    }
  ],
  "summary": {
    "expired_count": "integer",
    "critical_count": "integer",
    "low_stock_count": "integer",
    "total_alerts": "integer — expired_count + critical_count + low_stock_count"
  },
  "last_checked_at": "string ISO 8601 — when the cron last ran for this tenant",
  "cached_at": "string ISO 8601"
}
```

**Example:**
```json
{
  "expired_items": [
    {
      "id": "inv-ccdd-3344-eeff-5566-001177889900",
      "name": "Sutura Vicryl 3-0",
      "category": "material",
      "quantity": 4,
      "unit": "units",
      "expiry_date": "2026-01-15",
      "days_since_expiry": 41,
      "lot_number": "SUT-2023-0412",
      "location": "Gabinete Cirugias"
    }
  ],
  "critical_items": [
    {
      "id": "inv-aabb-1122-ccdd-3344-eeff55667788",
      "name": "Anestesia Lidocaina 2%",
      "category": "medication",
      "quantity": 3,
      "unit": "boxes",
      "expiry_date": "2026-03-10",
      "days_until_expiry": 13,
      "lot_number": "LIDO-2025-0512",
      "location": "Refrigerador Consultorio 1"
    }
  ],
  "low_stock_items": [
    {
      "id": "inv-ddee-4455-ffaa-6677-bbcc00112233",
      "name": "Guantes Nitrilo Talla S",
      "category": "material",
      "quantity": 2,
      "unit": "boxes",
      "minimum_stock": 5,
      "stock_deficit": 3,
      "location": "Bodega Principal",
      "supplier": "MedSupply Colombia"
    }
  ],
  "summary": {
    "expired_count": 1,
    "critical_count": 1,
    "low_stock_count": 1,
    "total_alerts": 3
  },
  "last_checked_at": "2026-02-25T06:00:00-05:00",
  "cached_at": "2026-02-25T11:30:00-05:00"
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Role is doctor, receptionist, or patient.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver las alertas de inventario."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`. If not `clinic_owner` or `assistant`, return 403.
2. Check Redis cache: `tenant:{tenant_id}:inventory:alerts`. If cache hit, return cached response.
3. If cache miss, set `search_path` to tenant schema.
4. Run three parallel queries via `asyncio.gather`:
   a. Expired: `SELECT ... FROM inventory_items WHERE tenant_id = :tenant_id AND expiry_status = 'expired' ORDER BY expiry_date ASC`
   b. Critical: `SELECT ... FROM inventory_items WHERE tenant_id = :tenant_id AND expiry_status = 'critical' ORDER BY expiry_date ASC`
   c. Low stock: `SELECT ... FROM inventory_items WHERE tenant_id = :tenant_id AND quantity < minimum_stock ORDER BY (minimum_stock - quantity) DESC`
5. Compute derived fields:
   - `days_since_expiry = (today - expiry_date).days` for expired items.
   - `days_until_expiry = (expiry_date - today).days` for critical items.
   - `stock_deficit = minimum_stock - quantity` for low stock items.
6. Load `last_checked_at` from `tenant_settings.inventory_last_checked_at`.
7. Build response with summary counts and `cached_at = now()`.
8. Cache response: `tenant:{tenant_id}:inventory:alerts`, TTL = 3600s (1 hour). Alert data is not real-time critical — daily cron keeps it accurate.
9. Return 200.

**Background Cron Job (described here, not a separate endpoint):**

The background cron runs once per day per tenant (dispatched via RabbitMQ scheduler at 06:00 tenant timezone):
1. Query expired and critical items for all active tenants.
2. For each tenant with alerts: dispatch `inventory.daily_alert` to RabbitMQ.
3. Notification worker sends email summary to clinic_owner with list of items needing attention.
4. Update `tenant_settings.inventory_last_checked_at = now()`.
5. Invalidate `tenant:{tenant_id}:inventory:alerts` cache.

**Validation Rules:**

None — read-only GET with no user parameters.

**Business Rules:**

- An item can appear in multiple groups. For example, a medication that has expired AND is below minimum_stock would appear in both `expired_items` and `low_stock_items`. The `total_alerts` in summary counts each group separately.
- Items with `expiry_date = null` never appear in expired or critical groups.
- The `low_stock_items` group includes items where `quantity < minimum_stock`, regardless of whether `minimum_stock = 0`. Items with `minimum_stock = 0` and `quantity >= 0` are never in low_stock (quantity is always >= minimum_stock=0).
- The 1-hour cache TTL balances freshness with performance. The cache is invalidated when any inventory item is created or updated (INV-01, INV-03), so in practice the data may be more current than 1 hour.
- `last_checked_at` reflects when the daily cron last ran and sent notifications — not the timestamp of this GET request. This helps staff know if the daily notification has gone out today.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No alerts at all | All arrays empty, summary all zeros, total_alerts=0 |
| Item is both expired and low stock | Appears in expired_items AND low_stock_items; counted twice in total_alerts |
| No daily cron has run yet (new tenant) | last_checked_at=null |
| minimum_stock=0 items | Never in low_stock_items regardless of quantity |
| Critical item has quantity=0 | Appears in BOTH critical_items AND low_stock_items (if minimum_stock > 0) |

---

## Side Effects

### Database Changes

**No write operations** — read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:inventory:alerts`: SET on cache miss

**Cache TTL:** 3600 seconds (1 hour)

**Cache invalidation:** Deleted by INV-01 and INV-03 on any inventory write (pattern `tenant:{tenant_id}:inventory:*`).

### Queue Jobs (RabbitMQ)

**Jobs dispatched by background cron (not this endpoint):**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | inventory.daily_alert | { tenant_id, clinic_owner_email, expired_count, critical_count, low_stock_count, items_summary: [{name, type, severity}] } | Daily at 06:00 tenant timezone, if any alerts exist |

### Audit Log

**Audit entry:** No — routine alert check, no PHI.

### Notifications

**Notifications triggered:** No (from this GET endpoint). The daily cron dispatches email notifications.

---

## Performance

### Expected Response Time
- **Target:** < 20ms (cache hit)
- **Target:** < 100ms (cache miss)
- **Maximum acceptable:** < 200ms (cache miss)

### Caching Strategy
- **Strategy:** Full response cache with 1-hour TTL
- **Cache key:** `tenant:{tenant_id}:inventory:alerts`
- **TTL:** 3600 seconds
- **Invalidation:** Pattern DELETE `tenant:{tenant_id}:inventory:*` on any inventory write

### Database Performance

**Queries executed (cache miss):** 3 parallel queries (expired, critical, low_stock)

**Indexes required:**
- `inventory_items.(tenant_id, expiry_status)` — COMPOSITE INDEX for expired/critical queries
- `inventory_items.(tenant_id, quantity, minimum_stock)` — for low_stock: note that `quantity < minimum_stock` requires the expression to be evaluated; a partial index may help for tenants with many items

**N+1 prevention:** 3 queries run in parallel via asyncio.gather. No per-item sub-queries.

### Pagination

**Pagination:** No — alerts list is bounded. Clinics typically have < 100 alert items at any time. If edge cases require pagination, it will be added in a future version.

---

## Security

### Input Sanitization

No user-provided parameters.

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — operational inventory data only.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. Clinic with all three alert types
   - **Given:** clinic_owner authenticated, 1 expired item, 2 critical items, 3 low stock items
   - **When:** GET /api/v1/inventory/alerts
   - **Then:** 200 OK, correct counts in each group, summary.total_alerts=6 (2+2+3, one item is both expired and low stock)

2. Cache hit on second request
   - **Given:** First request cached
   - **When:** Second GET within 1 hour
   - **Then:** 200 OK, served from cache

3. No alerts
   - **Given:** All items have ok status and sufficient stock
   - **When:** GET
   - **Then:** 200 OK, all arrays empty, total_alerts=0

#### Edge Cases
1. Item appears in both expired_items and low_stock_items
   - **Given:** Item with expiry_status=expired AND quantity < minimum_stock
   - **When:** GET
   - **Then:** Item in both arrays; counted once in expired_count and once in low_stock_count

2. New tenant (last_checked_at=null)
   - **Given:** Tenant just created
   - **When:** GET
   - **Then:** 200 OK, last_checked_at=null

#### Error Cases
1. Doctor role
   - **Given:** Authenticated doctor
   - **When:** GET
   - **Then:** 403 Forbidden

2. Receptionist role
   - **Given:** Authenticated receptionist
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, assistant, doctor, receptionist

**Inventory Items:** 1 expired, 2 critical (within 30 days), 3 low stock, 1 both expired and low stock, 5 ok items

### Mocking Strategy

- Redis: `fakeredis` for cache hit/miss testing
- Database: SQLite in-memory; compute expiry_status in application layer for SQLite compatibility
- Fixed `today` date in tests for deterministic days_since_expiry and days_until_expiry

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/inventory/alerts returns 200 with three grouped alert arrays
- [ ] expired_items includes items with expiry_status=expired (days_since_expiry computed)
- [ ] critical_items includes items with expiry_status=critical (days_until_expiry computed)
- [ ] low_stock_items includes items where quantity < minimum_stock (stock_deficit computed)
- [ ] Items can appear in multiple groups
- [ ] summary.total_alerts = sum of all group counts
- [ ] Response cached for 1 hour
- [ ] Cache invalidated on inventory writes
- [ ] Background cron described (even if not fully implemented in this sprint)
- [ ] Only clinic_owner and assistant can access (403 for others)
- [ ] All test cases pass
- [ ] Performance targets met (< 20ms cache, < 100ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Per-item alert management (acknowledge/dismiss individual alerts)
- Alert history (which alerts were sent on which dates)
- In-app notification for alerts (the badge count is derived from this endpoint's summary)
- Cron scheduling infrastructure (see infra/bg-processing.md)
- Alert threshold configuration (minimum_stock per item is the threshold)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (none — no params)
- [x] All outputs defined (3 grouped arrays + summary + metadata)
- [x] Background cron behavior documented
- [x] Error cases enumerated
- [x] Auth requirements explicit (clinic_owner, assistant)
- [x] Side effects listed (cache, cron job)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Uses PostgreSQL GENERATED ALWAYS expiry_status column
- [x] Parallel queries via asyncio.gather
- [x] Tenant isolation enforced

### Hook 3: Security & Privacy
- [x] Auth restricted to clinic_owner and assistant
- [x] No PHI
- [x] SQL injection prevented

### Hook 4: Performance & Scalability
- [x] 1-hour cache (appropriate for alert frequency)
- [x] 3 parallel queries
- [x] Pagination deferred (bounded alert count)

### Hook 5: Observability
- [x] cache hit/miss logged
- [x] Cron last_checked_at visible in response
- [x] Error tracking compatible

### Hook 6: Testability
- [x] Test cases enumerated (including item in multiple groups)
- [x] Fixed today date for deterministic calculations
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
