# AN-04 — Revenue Analytics Spec

---

## Overview

**Feature:** Revenue analytics endpoint. Returns financial metrics: revenue by period, revenue breakdown by doctor, by procedure type, and by payment method. Includes accounts receivable aging buckets (0-30d, 30-60d, 60-90d, 90d+) and comparison with the previous equivalent period. clinic_owner only — doctor role sees only their own revenue. Sensitive financial data — strict role enforcement.

**Domain:** analytics

**Priority:** Medium

**Dependencies:** AN-01 (dashboard), billing/quotation-create, invoices (sprint 7-8), infra/caching-strategy.md, infra/audit-logging.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** clinic_owner sees all revenue across all doctors. doctor sees only revenue from their own patients' invoices. assistant and receptionist do not have access to revenue analytics. Revenue data is considered financially sensitive — access is audit-logged.

---

## Endpoint

```
GET /api/v1/analytics/revenue
```

**Rate Limiting:**
- 15 requests per minute per user (lower than other analytics — financial data is more sensitive)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Tenant identifier (auto-resolved from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| period | No | string | Enum: `today`, `this_week`, `this_month`, `this_quarter`, `this_year`, `custom`. Default: `this_month` | Date range preset | `this_quarter` |
| date_from | Conditional | string | ISO 8601 date. Required when period=custom | Custom range start | `2026-01-01` |
| date_to | Conditional | string | ISO 8601 date. Required when period=custom; >= date_from; max 366 days | Custom range end | `2026-03-31` |
| granularity | No | string | Enum: `day`, `week`, `month`. Default: `month` | Granularity for revenue time-series | `month` |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "period": {
    "preset": "string | null",
    "date_from": "string (YYYY-MM-DD)",
    "date_to": "string (YYYY-MM-DD)",
    "timezone": "string (IANA)",
    "granularity": "string",
    "currency": "string (ISO 4217)"
  },
  "summary": {
    "total_revenue": "number — sum of all paid invoices in period",
    "total_invoiced": "number — sum of all issued invoices (paid + unpaid)",
    "collection_rate": "number (percentage — total_revenue / total_invoiced * 100)",
    "average_invoice_value": "number",
    "total_discounts_applied": "number",
    "growth_vs_previous": "number | null (percentage)"
  },
  "revenue_over_time": [
    {
      "period_label": "string",
      "date_from": "string (YYYY-MM-DD)",
      "date_to": "string (YYYY-MM-DD)",
      "revenue": "number (paid in this bucket)",
      "invoiced": "number (issued in this bucket)",
      "collection_rate": "number (percentage)"
    }
  ],
  "revenue_by_doctor": [
    {
      "doctor_id": "uuid",
      "doctor_name": "string",
      "revenue": "number",
      "invoiced": "number",
      "collection_rate": "number",
      "percentage_of_total": "number"
    }
  ],
  "revenue_by_procedure_type": [
    {
      "procedure_type": "string (CUPS category or custom category)",
      "revenue": "number",
      "count": "integer (number of procedures billed)",
      "average_per_procedure": "number",
      "percentage_of_total": "number"
    }
  ],
  "revenue_by_payment_method": [
    {
      "payment_method": "string (efectivo | tarjeta_credito | tarjeta_debito | transferencia | convenio | otro)",
      "revenue": "number",
      "count": "integer (number of payments)",
      "percentage_of_total": "number"
    }
  ],
  "accounts_receivable_aging": {
    "total_outstanding": "number",
    "buckets": [
      {
        "label": "string (e.g., '0-30 días')",
        "days_from": "integer",
        "days_to": "integer | null (null for 90+)",
        "amount": "number",
        "invoice_count": "integer",
        "percentage": "number"
      }
    ]
  },
  "generated_at": "string (ISO 8601 datetime)",
  "cache_hit": "boolean"
}
```

**Example:**
```json
{
  "period": {
    "preset": "this_quarter",
    "date_from": "2026-01-01",
    "date_to": "2026-03-31",
    "timezone": "America/Bogota",
    "granularity": "month",
    "currency": "COP"
  },
  "summary": {
    "total_revenue": 47200000,
    "total_invoiced": 52800000,
    "collection_rate": 89.4,
    "average_invoice_value": 312000,
    "total_discounts_applied": 3200000,
    "growth_vs_previous": 12.8
  },
  "revenue_over_time": [
    {"period_label": "2026-01", "date_from": "2026-01-01", "date_to": "2026-01-31", "revenue": 15400000, "invoiced": 17200000, "collection_rate": 89.5},
    {"period_label": "2026-02", "date_from": "2026-02-01", "date_to": "2026-02-28", "revenue": 16800000, "invoiced": 18600000, "collection_rate": 90.3},
    {"period_label": "2026-03", "date_from": "2026-03-01", "date_to": "2026-03-31", "revenue": 15000000, "invoiced": 17000000, "collection_rate": 88.2}
  ],
  "revenue_by_doctor": [
    {"doctor_id": "...", "doctor_name": "Dr. García", "revenue": 28500000, "invoiced": 31800000, "collection_rate": 89.6, "percentage_of_total": 60.4},
    {"doctor_id": "...", "doctor_name": "Dra. López", "revenue": 18700000, "invoiced": 21000000, "collection_rate": 89.0, "percentage_of_total": 39.6}
  ],
  "revenue_by_procedure_type": [
    {"procedure_type": "Ortodoncia", "revenue": 18400000, "count": 42, "average_per_procedure": 438095, "percentage_of_total": 39.0},
    {"procedure_type": "Restauraciones", "revenue": 9800000, "count": 98, "average_per_procedure": 100000, "percentage_of_total": 20.8},
    {"procedure_type": "Endodoncia", "revenue": 8200000, "count": 38, "average_per_procedure": 215789, "percentage_of_total": 17.4},
    {"procedure_type": "Consulta general", "revenue": 5400000, "count": 180, "average_per_procedure": 30000, "percentage_of_total": 11.4},
    {"procedure_type": "Otros", "revenue": 5400000, "count": 59, "average_per_procedure": 91525, "percentage_of_total": 11.4}
  ],
  "revenue_by_payment_method": [
    {"payment_method": "transferencia", "revenue": 21200000, "count": 89, "percentage_of_total": 44.9},
    {"payment_method": "tarjeta_credito", "revenue": 14600000, "count": 62, "percentage_of_total": 30.9},
    {"payment_method": "efectivo", "revenue": 8400000, "count": 112, "percentage_of_total": 17.8},
    {"payment_method": "tarjeta_debito", "revenue": 3000000, "count": 24, "percentage_of_total": 6.4}
  ],
  "accounts_receivable_aging": {
    "total_outstanding": 5600000,
    "buckets": [
      {"label": "0-30 días", "days_from": 0, "days_to": 30, "amount": 3200000, "invoice_count": 18, "percentage": 57.1},
      {"label": "30-60 días", "days_from": 30, "days_to": 60, "amount": 1400000, "invoice_count": 8, "percentage": 25.0},
      {"label": "60-90 días", "days_from": 60, "days_to": 90, "amount": 600000, "invoice_count": 4, "percentage": 10.7},
      {"label": "90+ días", "days_from": 90, "days_to": null, "amount": 400000, "invoice_count": 3, "percentage": 7.1}
    ]
  },
  "generated_at": "2026-02-25T10:30:00Z",
  "cache_hit": false
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid `period` or `granularity` value, custom period missing dates, `date_from` > `date_to`, date range > 366 days.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "Rango de fechas inválido.",
  "details": {
    "date_from": ["La fecha de inicio debe ser anterior o igual a la fecha de fin."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token.

#### 403 Forbidden
**When:** Role not in `[clinic_owner, doctor]`.

**Example:**
```json
{
  "error": "acceso_denegado",
  "message": "No tiene permisos para acceder a los análisis de ingresos.",
  "details": {}
}
```

#### 422 Unprocessable Entity
**When:** Date strings cannot be parsed.

#### 429 Too Many Requests
**When:** Rate limit exceeded.

#### 500 Internal Server Error
**When:** Financial aggregation query failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT — extract `user_id`, `tenant_id`, `role`. Authorize.
2. Parse and validate query parameters. Compute date range in tenant timezone.
3. Determine scope: doctor role scoped to `invoices WHERE doctor_id = current_user.id`.
4. Check Redis cache. Return cached response if hit.
5. On cache miss, execute concurrent queries:

   **Summary:** SUM paid invoices in period, SUM all invoices issued in period, COUNT invoices, SUM discounts, compute rates.

   **Revenue over time:** `DATE_TRUNC(granularity, paid_at) GROUP BY` for paid amounts; same for issued_at for invoiced amounts.

   **Revenue by doctor:** `GROUP BY doctor_id JOIN users` for name. Only for clinic_owner scope (single-doctor queries omit this section when doctor role is scoped to self).

   **Revenue by procedure type:** JOIN `invoices` → `invoice_line_items` → `procedures` → `procedure_type`. `GROUP BY procedure_type` with SUM of line item amounts.

   **Revenue by payment method:** JOIN `invoices` → `payments`. `GROUP BY payment_method`.

   **Accounts receivable aging:** SELECT unpaid/overdue invoices. CASE WHEN `NOW() - due_date` buckets: 0-30, 30-60, 60-90, 90+. Only includes invoices where `due_date < NOW() OR status IN ('pending', 'overdue')`.

   **Previous period comparison:** Same SUM query for the previous equivalent period (same duration, ending at `date_from`). Compute growth percentage.

6. Assemble response, compute all percentages. Return 200 with cache set.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| period | Enum: today, this_week, this_month, this_quarter, this_year, custom | Período no válido. |
| granularity | Enum: day, week, month | La granularidad especificada no es válida. |
| date_from | Required for custom, valid ISO date | La fecha de inicio es requerida. |
| date_to | Required for custom, >= date_from, max 366 days | La fecha de fin no es válida. |

**Business Rules:**

- `total_revenue` counts only invoices with `status='paid'` and `paid_at BETWEEN date_from AND date_to`.
- `total_invoiced` counts all invoices with `issued_at BETWEEN date_from AND date_to` regardless of payment status.
- `collection_rate = total_revenue / total_invoiced * 100` — null if total_invoiced = 0.
- Accounts receivable aging shows the current snapshot (as of query time, not as of period end) of all outstanding invoices. This is intentionally not period-filtered.
- `total_discounts_applied` sums `discount_amount` on invoices issued in the period.
- Doctor role: `revenue_by_doctor` section is omitted (only contains themselves — redundant). All other sections reflect their own scoped data.
- Revenue amounts in COP (or tenant currency). No multi-currency conversion in v1.
- Accounts receivable aging bucket for `days_to: null` means "90 days or more past due".

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No invoices in period | All sums = 0, empty time-series buckets, aging total = 0 |
| total_invoiced = 0 | collection_rate = null (not 0% — mathematically undefined) |
| No overdue invoices | accounts_receivable_aging.total_outstanding = 0, all bucket amounts = 0 |
| Previous period has 0 revenue | growth_vs_previous = null |
| All payments in cash | revenue_by_payment_method has one entry: efectivo |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- All queries READ-ONLY.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:analytics:revenue:{doctor_filter}:{date_from}:{date_to}:{granularity}`: SET, 300s TTL.

**Cache TTL:** 300 seconds.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — revenue data is financially sensitive.
- **Action:** read
- **Resource:** analytics_revenue
- **PHI involved:** No (aggregated financial data, no patient records)

The audit log entry includes `user_id`, `tenant_id`, `date_from`, `date_to`, `role`, and timestamp.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 300ms (cached), < 2000ms (cache miss)
- **Maximum acceptable:** < 5000ms

### Caching Strategy
- **Strategy:** Redis cache, 5-minute TTL. Financial data changes infrequently within 5-minute windows.
- **Cache key:** `tenant:{tenant_id}:analytics:revenue:{doctor_filter_hash}:{date_from}:{date_to}:{granularity}`
- **TTL:** 300 seconds
- **Invalidation:** Time-based. Immediate invalidation triggered when a new payment is recorded (via billing service cache bust hook) — optional optimization.

### Database Performance

**Queries executed:** 6-8 concurrent async queries

**Indexes required:**
- `invoices.(paid_at, status, doctor_id)` — revenue queries
- `invoices.(issued_at, status)` — invoiced amounts
- `invoices.(due_date, status)` — aging buckets
- `payments.(invoice_id, payment_method, paid_at)` — payment method breakdown
- `invoice_line_items.(invoice_id, procedure_type)` — procedure type breakdown

**N+1 prevention:** All GROUP BY aggregate queries. No per-invoice iteration.

### Pagination

**Pagination:** No.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| period | Pydantic enum | |
| granularity | Pydantic enum | |
| date_from / date_to | Pydantic date | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized aggregate queries.

### XSS Prevention

**Output encoding:** Pydantic serialization. No free-text user content in response.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Revenue figures are financial data, not health data. Doctor names are employee records. Individual patient identifiers are not present.

**Audit requirement:** All access logged — revenue data is financially sensitive.

---

## Testing

### Test Cases

#### Happy Path
1. clinic_owner quarterly revenue breakdown
   - **Given:** 169 invoices across Q1, 3 payment methods, 4 procedure types, 12 overdue invoices
   - **When:** GET /api/v1/analytics/revenue?period=this_quarter&granularity=month
   - **Then:** 200 with all sections populated; sums verified; aging buckets sum to total_outstanding

2. doctor role — self-scoped
   - **Given:** Doctor has generated $28.5M of the $47.2M clinic revenue
   - **When:** GET /api/v1/analytics/revenue
   - **Then:** total_revenue = 28500000; revenue_by_doctor section omitted

3. Accounts receivable aging
   - **Given:** 33 outstanding invoices: 18 0-30d, 8 30-60d, 4 60-90d, 3 90d+
   - **When:** GET /api/v1/analytics/revenue
   - **Then:** Aging buckets match known distribution; percentages sum to 100

#### Edge Cases
1. No invoices
   - **When:** GET /api/v1/analytics/revenue for empty period
   - **Then:** All amounts = 0, collection_rate = null, empty arrays

2. Growth vs previous when previous = 0
   - **Given:** First month of operation (no previous period)
   - **When:** GET /api/v1/analytics/revenue?period=this_month
   - **Then:** growth_vs_previous = null

#### Error Cases
1. Unauthorized role (assistant)
   - **When:** assistant requests endpoint
   - **Then:** 403

2. Invalid period
   - **When:** GET ?period=last_year (not in enum)
   - **Then:** 400

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (for 403).

**Patients/Entities:** 30+ invoices with varied statuses (paid, pending, overdue), payment records with varied methods, procedure types on line items, past-due invoices for aging test.

### Mocking Strategy

- Redis: fakeredis.
- Database: Full billing data seeded in tenant schema.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Revenue summary computes correctly: only paid invoices in period
- [ ] collection_rate = null when total_invoiced = 0 (not division-by-zero error)
- [ ] Revenue time-series has correct granularity buckets
- [ ] Accounts receivable aging correctly buckets by days past due_date
- [ ] Revenue by doctor, procedure type, payment method all accurate
- [ ] growth_vs_previous computes correctly; null when previous period = 0
- [ ] doctor role: revenue_by_doctor section omitted; data scoped to own patients
- [ ] All revenue data audit-logged (user, tenant, date range, timestamp)
- [ ] 5-minute Redis cache applied
- [ ] 403 for unauthorized roles
- [ ] Rate limit 15 req/min enforced
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- DIAN e-invoicing integration and tax analytics
- Multi-currency revenue reporting
- Cash flow forecasting
- Payroll and doctor commission calculations
- Cost accounting or profitability analysis
- Insurance/EPS claim reimbursement tracking
- Export (see AN-06)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization defined
- [x] SQL injection prevented
- [x] No PHI exposure
- [x] Audit trail defined (mandatory for revenue)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized
- [x] Pagination defined

### Hook 5: Observability
- [x] Structured logging
- [x] Audit log entries defined
- [x] Error tracking
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data requirements specified
- [x] Mocking strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
