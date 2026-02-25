# B-13 Billing Summary Dashboard Spec

---

## Overview

**Feature:** Return aggregated billing dashboard data for the authenticated clinic including current period revenue figures, outstanding balances, overdue invoice counts, top procedures by revenue, payment method breakdown, and period-over-period comparisons. This data powers the clinic's financial dashboard widget. Clinic_owner only. Results cached 5 minutes TTL.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), B-07 (payment-record.md), B-14 (service-catalog.md), infra/caching.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner may view billing summary. Superadmin may access for tenant administration. All other roles return 403.

---

## Endpoint

```
GET /api/v1/billing/summary
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
| as_of_date | No | string | ISO 8601 date, <= today | Compute summary as of this date (default: today) | 2026-01-31 |

### Request Body Schema

None — GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "currency": "string — ISO 4217 for this tenant",
  "as_of_date": "string ISO 8601 date",
  "revenue": {
    "this_month": "integer — cents, paid invoices in current calendar month",
    "this_quarter": "integer — cents, paid invoices in current calendar quarter",
    "this_year": "integer — cents, paid invoices in current calendar year",
    "comparison_previous_month": {
      "amount": "integer — cents, previous calendar month revenue",
      "change_percentage": "number — positive = growth, negative = decline"
    },
    "comparison_previous_quarter": {
      "amount": "integer — cents",
      "change_percentage": "number"
    },
    "comparison_previous_year": {
      "amount": "integer — cents",
      "change_percentage": "number"
    }
  },
  "outstanding": {
    "total_outstanding_balance": "integer — cents, sum of balance_due on unpaid invoices (sent + overdue)",
    "overdue_count": "integer — count of invoices where due_date < today and status != paid",
    "overdue_amount": "integer — cents, sum of balance_due on overdue invoices"
  },
  "top_procedures": [
    {
      "service_id": "uuid | null",
      "cups_code": "string | null",
      "description": "string — procedure name or invoice item description",
      "count": "integer — number of times billed in current month",
      "total_revenue": "integer — cents, total revenue from this procedure in current month"
    }
  ],
  "payment_method_breakdown": [
    {
      "method": "string — enum: cash, card, transfer, insurance, other",
      "count": "integer — number of payments using this method this month",
      "total_amount": "integer — cents"
    }
  ],
  "invoice_status_counts": {
    "draft": "integer",
    "sent": "integer",
    "paid": "integer",
    "overdue": "integer",
    "cancelled": "integer"
  },
  "cached_at": "string ISO 8601 datetime — when this summary was last computed"
}
```

**Example:**
```json
{
  "currency": "COP",
  "as_of_date": "2026-02-25",
  "revenue": {
    "this_month": 48500000,
    "this_quarter": 121000000,
    "this_year": 121000000,
    "comparison_previous_month": {
      "amount": 39000000,
      "change_percentage": 24.36
    },
    "comparison_previous_quarter": {
      "amount": 0,
      "change_percentage": 0
    },
    "comparison_previous_year": {
      "amount": 0,
      "change_percentage": 0
    }
  },
  "outstanding": {
    "total_outstanding_balance": 18500000,
    "overdue_count": 3,
    "overdue_amount": 6200000
  },
  "top_procedures": [
    {
      "service_id": "svc-aabb-1122-ccdd-3344-eeff55667788",
      "cups_code": "895101",
      "description": "Resina Compuesta",
      "count": 28,
      "total_revenue": 19600000
    },
    {
      "service_id": "svc-bbcc-2233-ddee-4455-ff006677889",
      "cups_code": "895301",
      "description": "Limpieza y Profilaxis",
      "count": 22,
      "total_revenue": 9240000
    },
    {
      "service_id": "svc-ccdd-3344-eeff-5566-001177889900",
      "cups_code": "895501",
      "description": "Endodoncia Unirradicular",
      "count": 6,
      "total_revenue": 6600000
    }
  ],
  "payment_method_breakdown": [
    { "method": "cash", "count": 35, "total_amount": 21000000 },
    { "method": "card", "count": 18, "total_amount": 15400000 },
    { "method": "transfer", "count": 10, "total_amount": 12100000 }
  ],
  "invoice_status_counts": {
    "draft": 5,
    "sent": 8,
    "paid": 63,
    "overdue": 3,
    "cancelled": 2
  },
  "cached_at": "2026-02-25T10:55:00-05:00"
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Authenticated user does not have role `clinic_owner` or `superadmin`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede ver el resumen de facturacion."
}
```

#### 422 Unprocessable Entity
**When:** `as_of_date` is in the future.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "La fecha de referencia no puede ser futura.",
  "details": {
    "as_of_date": ["La fecha no puede ser posterior a hoy."]
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
2. Check role: if not `clinic_owner` or `superadmin`, return 403.
3. Parse and validate `as_of_date` (default: today in tenant timezone). If future date, return 422.
4. Build cache key: `tenant:{tenant_id}:billing:summary:{as_of_date}`. Check Redis. If cache hit, return cached response.
5. If cache miss, set `search_path` to tenant schema.
6. Compute calendar boundaries from `as_of_date`:
   - `month_start` = first day of as_of_date month
   - `quarter_start` = first day of current quarter (Q1: Jan 1, Q2: Apr 1, Q3: Jul 1, Q4: Oct 1)
   - `year_start` = Jan 1 of as_of_date year
   - `prev_month_start` / `prev_month_end` — previous calendar month
   - `prev_quarter_start` / `prev_quarter_end` — previous calendar quarter
   - `prev_year_start` / `prev_year_end` — previous calendar year
7. Run 5 parallel aggregation queries (using SQLAlchemy coroutines with `asyncio.gather`):
   a. Revenue: `SELECT SUM(total) grouped by period` for current month, quarter, year and previous periods (WHERE status='paid')
   b. Outstanding: `SELECT SUM(balance_due), COUNT(*)` for status IN ('sent') and for status='overdue' (or due_date < as_of_date and status != 'paid')
   c. Top procedures: `SELECT ii.description, ii.service_id, COUNT(*), SUM(ii.subtotal)` joined to invoice_items WHERE invoice.status='paid' AND invoice.issued_date >= month_start ORDER BY SUM(ii.subtotal) DESC LIMIT 10
   d. Payment methods: `SELECT method, COUNT(*), SUM(amount)` FROM payments WHERE payment_date >= month_start GROUP BY method
   e. Invoice status counts: `SELECT status, COUNT(*)` FROM invoices GROUP BY status (all time, no date filter)
8. Calculate comparison percentages: `change_pct = ((current - previous) / previous) * 100`. If previous = 0, return 0 for change_percentage (avoid division by zero).
9. Join top procedures descriptions to service_catalog to include cups_code where available.
10. Build response object.
11. Serialize and store in Redis: `tenant:{tenant_id}:billing:summary:{as_of_date}`, TTL = 300s.
12. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| as_of_date | ISO 8601 date, <= today (if provided) | La fecha de referencia no puede ser futura. |

**Business Rules:**

- Revenue figures include only `status = 'paid'` invoices. Outstanding figures cover `status IN ('sent', 'overdue')`.
- An invoice is considered overdue if `due_date < as_of_date AND status NOT IN ('paid', 'cancelled')`.
- The `top_procedures` list is limited to 10 entries, ordered by total_revenue DESC. It reflects only the current calendar month.
- Payment method breakdown reflects payments recorded in the current calendar month only.
- Invoice status counts are all-time (not date-filtered) — they show the current state of all invoices in the system.
- If a tenant has no invoices or payments for a period, all revenue/count fields return 0. No 404 is returned.
- `comparison_previous_quarter` and `comparison_previous_year` may show 0/0 = 0% change for new tenants.
- The `cached_at` field in the response always reflects the actual computation time, even for cached responses (it is stored in the cache alongside the data).
- For `as_of_date` = today (default), the cache key includes the date so yesterday's cache does not pollute today's results. Cache is automatically invalidated at midnight by including the date in the key.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| New tenant with no invoices | All revenue/count fields = 0; top_procedures = []; payment_method_breakdown = [] |
| Previous period has no revenue (e.g. first month) | comparison_previous_month.change_percentage = 0 (no division by zero) |
| as_of_date is today (default) | Current month/quarter/year computed from today |
| as_of_date is last day of a quarter | Current quarter is Q that includes that date |
| Invoice due_date = as_of_date | Not yet overdue — due_date < as_of_date is the overdue condition |

---

## Side Effects

### Database Changes

**No write operations** — read-only reporting endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:billing:summary:{as_of_date}`: SET on cache miss

**Cache TTL:** 300 seconds (5 minutes)

**Cache invalidation:** When a payment is recorded (B-07), when an invoice status changes, or when an invoice is created (write endpoints invalidate this key as a side effect). Pattern: DELETE `tenant:{tenant_id}:billing:summary:*`.

**Example cache set (Python):**
```python
cache_key = f"tenant:{tenant_id}:billing:summary:{as_of_date.isoformat()}"
cached = await redis.get(cache_key)
if cached:
    return BillingSummaryResponse.model_validate_json(cached)

# ... run queries ...
response = build_response(...)
await redis.set(cache_key, response.model_dump_json(), ex=300)
return response
```

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — read-only.

### Audit Log

**Audit entry:** No — read-only financial dashboard; no PHI; high-frequency access makes per-access audit impractical.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 30ms (cache hit)
- **Target:** < 200ms (cache miss)
- **Maximum acceptable:** < 400ms (cache miss under load)

### Caching Strategy
- **Strategy:** Full response Redis cache with 5-minute TTL per date
- **Cache key:** `tenant:{tenant_id}:billing:summary:{as_of_date}`
- **TTL:** 300 seconds
- **Invalidation:** Explicit key deletion pattern `tenant:{tenant_id}:billing:summary:*` on any invoice/payment write

### Database Performance

**Queries executed (cache miss):** 5 parallel aggregation queries

**Indexes required:**
- `invoices.(tenant_id, status, issued_date)` — COMPOSITE INDEX for revenue aggregation
- `invoices.(tenant_id, due_date, status)` — COMPOSITE INDEX for overdue calculation
- `invoice_items.(invoice_id, service_id)` — COMPOSITE INDEX for top procedures
- `payments.(tenant_id, payment_date, method)` — COMPOSITE INDEX for payment breakdown
- `invoices.(tenant_id, status)` — COMPOSITE INDEX for status counts

**N+1 prevention:** All 5 aggregation queries run in parallel via `asyncio.gather`. No per-record sub-queries.

### Pagination

**Pagination:** No — dashboard data is a single aggregated response.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| as_of_date | Pydantic date validator, <= today | Strict ISO 8601 |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — financial aggregates only. No patient names, procedures linked to specific patients.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. Full summary for active tenant in February 2026
   - **Given:** Authenticated clinic_owner, tenant has paid invoices in Jan and Feb 2026, payments recorded
   - **When:** GET /api/v1/billing/summary (as_of_date=today)
   - **Then:** 200 OK, this_month > 0, comparison_previous_month.amount > 0, top_procedures has entries, payment_method_breakdown has entries

2. Cache hit on second request
   - **Given:** First request computed and cached summary
   - **When:** Second GET within 5 minutes
   - **Then:** 200 OK, served from cache, no DB queries

3. as_of_date = end of previous month
   - **Given:** Tenant with Jan 2026 invoices
   - **When:** GET with as_of_date=2026-01-31
   - **Then:** this_month reflects January 2026 revenue

#### Edge Cases
1. New tenant with no invoices
   - **Given:** Tenant created today, no invoices
   - **When:** GET summary
   - **Then:** 200 OK, all revenue fields = 0, top_procedures = [], payment_method_breakdown = []

2. Previous period has zero revenue
   - **Given:** Tenant has no invoices in December 2025, has invoices in Jan 2026
   - **When:** GET in Jan 2026
   - **Then:** comparison_previous_month.change_percentage = 0 (no division by zero)

#### Error Cases
1. as_of_date is tomorrow
   - **Given:** as_of_date = tomorrow's date
   - **When:** GET with that date
   - **Then:** 422 with future date error

2. Role is receptionist
   - **Given:** Authenticated receptionist
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** One clinic_owner, one receptionist

**Invoices:** Paid invoices with different issued_dates spanning 2 months; draft and overdue invoices; invoices with multiple items

**Payments:** Payment records with different methods (cash, card, transfer) in current month

### Mocking Strategy

- Redis: `fakeredis` to test cache hit/miss paths
- Database: SQLite in-memory; seed invoices, invoice_items, payments with known amounts for deterministic math verification

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/billing/summary returns 200 with all sections populated
- [ ] Revenue figures reflect only paid invoices
- [ ] Overdue count/amount calculated correctly (due_date < today, not paid)
- [ ] top_procedures limited to 10, ordered by total_revenue DESC
- [ ] Comparison percentages computed correctly (no division-by-zero)
- [ ] Response cached for 5 minutes
- [ ] Cache key includes date (no cross-day contamination)
- [ ] Only clinic_owner can access (403 for other roles)
- [ ] All monetary values in cents
- [ ] All test cases pass
- [ ] Performance targets met (< 30ms cache, < 200ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Detailed invoice lists (see B-03 invoice-list.md)
- Payment history (see B-08 payment-list.md)
- Doctor commission summary (see B-12 doctor-commissions.md)
- Export to PDF or CSV
- Custom date range revenue queries (see separate analytics spec)
- Patient balance dashboard (see B-11 patient-balance.md)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (optional as_of_date only)
- [x] All outputs defined (7 sections in response)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (clinic_owner only)
- [x] Side effects listed (cache write only)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Parallel aggregation queries (asyncio.gather)
- [x] Matches FastAPI conventions

### Hook 3: Security & Privacy
- [x] Auth level stated (clinic_owner only)
- [x] No PHI in aggregated response
- [x] SQL injection prevented

### Hook 4: Performance & Scalability
- [x] Response time targets (30ms cache, 200ms miss)
- [x] 5-minute cache with date-keyed invalidation
- [x] 5 parallel queries
- [x] Indexes listed for all aggregations

### Hook 5: Observability
- [x] cache hit/miss logged
- [x] No PHI in logs
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
