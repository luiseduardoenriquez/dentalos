# B-12 Doctor Commissions Report Spec

---

## Overview

**Feature:** Generate a commission report for one or all doctors within a tenant for a specified date range. Returns per-doctor aggregates: procedure count, total revenue billed, configured commission percentage, and calculated commission amount. Commission percentage is configured per doctor in their user profile. Clinic_owner only.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), U-01 (user-list.md), infra/authentication-rules.md, infra/caching.md, `invoices` and `invoice_items` tables, `users.commission_percentage` field

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner may access commission data. Doctors cannot see their own or other doctors' commissions via this endpoint. Superadmin may access as part of tenant administration.

---

## Endpoint

```
GET /api/v1/billing/commissions
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
| doctor_id | No | UUID | Valid UUID v4 | Filter report to a single doctor | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |
| date_from | Yes | string | ISO 8601 date, <= date_to | Start date of reporting period (inclusive) | 2026-01-01 |
| date_to | Yes | string | ISO 8601 date, >= date_from, <= today | End date of reporting period (inclusive) | 2026-01-31 |
| status | No | string | Enum: paid, all — default: paid | Whether to include all invoices or only paid ones | paid |

### Request Body Schema

None — GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "period": {
    "date_from": "string ISO 8601 date",
    "date_to": "string ISO 8601 date"
  },
  "currency": "string — ISO 4217 currency code for the tenant",
  "commissions": [
    {
      "doctor": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string",
        "specialty": "string | null"
      },
      "procedure_count": "integer — count of invoice line items linked to this doctor in the period",
      "total_revenue": "integer — sum of invoice item subtotals in cents for this doctor",
      "commission_percentage": "number — percentage configured on the doctor's profile (0-100)",
      "commission_amount": "integer — floor(total_revenue * commission_percentage / 100) in cents"
    }
  ],
  "totals": {
    "total_revenue": "integer — sum across all doctors in cents",
    "total_commission": "integer — sum of all commission_amounts in cents"
  },
  "generated_at": "string ISO 8601 datetime"
}
```

**Example:**
```json
{
  "period": {
    "date_from": "2026-01-01",
    "date_to": "2026-01-31"
  },
  "currency": "COP",
  "commissions": [
    {
      "doctor": {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "first_name": "Carlos",
        "last_name": "Mendez",
        "specialty": "Odontologia General"
      },
      "procedure_count": 42,
      "total_revenue": 168000000,
      "commission_percentage": 35.0,
      "commission_amount": 58800000
    },
    {
      "doctor": {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "first_name": "Ana",
        "last_name": "Reyes",
        "specialty": "Ortodoncia"
      },
      "procedure_count": 18,
      "total_revenue": 95000000,
      "commission_percentage": 40.0,
      "commission_amount": 38000000
    }
  ],
  "totals": {
    "total_revenue": 263000000,
    "total_commission": 96800000
  },
  "generated_at": "2026-02-25T11:00:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** `date_from` or `date_to` missing, invalid date format, or `date_from > date_to`.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de fecha invalidos.",
  "details": {
    "date_from": ["La fecha de inicio es requerida. Formato: YYYY-MM-DD."],
    "date_to": ["La fecha de fin debe ser posterior o igual a la fecha de inicio."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Authenticated user does not have role `clinic_owner` or `superadmin`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede ver los reportes de comisiones."
}
```

#### 404 Not Found
**When:** `doctor_id` provided but not found in the tenant or does not have role=doctor.

**Example:**
```json
{
  "error": "not_found",
  "message": "El doctor especificado no fue encontrado en esta clinica."
}
```

#### 422 Unprocessable Entity
**When:** `date_to` is in the future (beyond today), or date range exceeds 366 days.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Rango de fechas invalido.",
  "details": {
    "date_to": ["La fecha de fin no puede ser futura."],
    "date_range": ["El rango de fechas no puede superar 366 dias."]
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

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. Check role: if not `clinic_owner` or `superadmin`, return 403.
3. Validate query parameters:
   - `date_from` and `date_to` required; parse as ISO 8601 date.
   - `date_from <= date_to`. If not, return 400.
   - `date_to <= today` (cannot request future commissions). If not, return 422.
   - `date_to - date_from <= 366 days`. If exceeds, return 422.
4. If `doctor_id` provided, validate it exists and has role=doctor in the tenant. If not, return 404.
5. Set `search_path` to tenant schema.
6. Build commission query (single aggregation query):
   ```sql
   SELECT
     u.id, u.first_name, u.last_name, u.specialty, u.commission_percentage,
     COUNT(ii.id) AS procedure_count,
     SUM(ii.subtotal) AS total_revenue
   FROM users u
   LEFT JOIN invoices inv ON inv.doctor_id = u.id
     AND inv.status = :status_filter
     AND inv.issued_date BETWEEN :date_from AND :date_to
   LEFT JOIN invoice_items ii ON ii.invoice_id = inv.id
   WHERE u.role = 'doctor' AND u.is_active = true
     AND (:doctor_id IS NULL OR u.id = :doctor_id)
   GROUP BY u.id, u.first_name, u.last_name, u.specialty, u.commission_percentage
   ORDER BY total_revenue DESC NULLS LAST
   ```
7. For each doctor row, calculate `commission_amount = floor(total_revenue * commission_percentage / 100)`. Use integer math to avoid floating-point errors.
8. For doctors with no invoices in the period, `procedure_count = 0`, `total_revenue = 0`, `commission_amount = 0`.
9. Calculate totals: `total_revenue = sum of all doctor total_revenues`, `total_commission = sum of all commission_amounts`.
10. Return 200 with commission report.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| date_from | Required, ISO 8601 date format | La fecha de inicio es requerida. Formato: YYYY-MM-DD. |
| date_to | Required, ISO 8601 date format, >= date_from, <= today | La fecha de fin es invalida. |
| date range | date_to - date_from <= 366 days | El rango de fechas no puede superar 366 dias. |
| doctor_id | Valid UUID v4, exists in tenant with role=doctor (if provided) | El doctor especificado no fue encontrado. |
| status | Enum: paid, all (if provided) | Estado de factura invalido. Opciones: paid, all. |

**Business Rules:**

- Commission percentage (`commission_percentage`) is stored on each `users` record (per doctor) as a decimal number 0-100. It is configured separately via the user profile update endpoint.
- If a doctor has no `commission_percentage` configured (null), the report returns `commission_percentage = 0` and `commission_amount = 0` for that doctor.
- By default (`status=paid`), only invoices with `status = 'paid'` are included. This reflects actual collected revenue. When `status=all`, all non-cancelled invoice statuses are included (draft, sent, paid, overdue).
- Commission is calculated on `invoice_items.subtotal` (line item revenue), not on `invoices.total` (which includes tax). This is the standard industry practice — commission is on revenue before tax.
- Commission amount uses integer floor division to avoid fractional cents.
- If `doctor_id` is filtered, the `totals` section reflects only that doctor's data.
- The report does not cache results as the data should be real-time accurate for payroll purposes. If caching is needed in future, TTL should be <= 5min.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor has commission_percentage = null | Report shows commission_percentage=0, commission_amount=0 |
| No invoices in period for any doctor | Returns all active doctors with procedure_count=0, total_revenue=0 |
| Doctor has status=inactive | Excluded from report (only active doctors) |
| Single doctor filtered with doctor_id | commissions array has exactly 1 entry; totals reflect that doctor only |
| date_from == date_to (single day) | Valid; returns commissions for that specific date |

---

## Side Effects

### Database Changes

**No write operations** — this is a read-only reporting endpoint.

### Cache Operations

**Cache keys affected:** None — this report is not cached (real-time accuracy required for payroll).

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** commission_report
- **PHI involved:** No — financial data only

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching — real-time financial data
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 2 (optional doctor validation, main aggregation query)

**Indexes required:**
- `invoices.(tenant_id, doctor_id, status, issued_date)` — COMPOSITE INDEX for commission aggregation
- `invoice_items.invoice_id` — INDEX
- `users.(tenant_id, role, is_active)` — COMPOSITE INDEX

**N+1 prevention:** Single aggregation JOIN query returns all doctor commission data in one pass. No per-doctor queries.

### Pagination

**Pagination:** No — bounded by number of doctors in clinic (typically 1-20). Full report returned in single response.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| doctor_id | Pydantic UUID validator | Rejects non-UUID |
| date_from, date_to | Pydantic date validator | ISO 8601 strict |
| status | Pydantic enum validator | Whitelist: paid, all |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — financial and professional data only.

**Audit requirement:** Access logged (read event, financial data).

---

## Testing

### Test Cases

#### Happy Path
1. Full commission report for all doctors in January 2026
   - **Given:** 2 doctors, each with paid invoices in January, commission_percentage set
   - **When:** GET /api/v1/billing/commissions?date_from=2026-01-01&date_to=2026-01-31
   - **Then:** 200 OK, 2 entries in commissions array, correct totals, commission_amount calculated correctly

2. Filtered to single doctor
   - **Given:** 2 doctors, valid date range
   - **When:** GET with doctor_id= one doctor's UUID
   - **Then:** 200 OK, commissions array has exactly 1 entry, totals reflect that doctor only

3. Status=all includes draft and sent invoices
   - **Given:** One doctor has paid and draft invoices
   - **When:** GET with status=all
   - **Then:** Both invoice types included in total_revenue

#### Edge Cases
1. Doctor with no invoices in period
   - **Given:** One doctor has no invoices in requested range
   - **When:** GET for that range
   - **Then:** Doctor appears with procedure_count=0, total_revenue=0, commission_amount=0

2. Doctor with null commission_percentage
   - **Given:** Doctor profile has commission_percentage=null
   - **When:** GET commission report
   - **Then:** commission_percentage=0, commission_amount=0 in response

3. Single-day report (date_from == date_to)
   - **Given:** Valid date where invoices exist
   - **When:** GET with same date for both params
   - **Then:** 200 OK with commissions for that day

#### Error Cases
1. date_to in the future
   - **Given:** date_to = tomorrow
   - **When:** GET request
   - **Then:** 422 with date_to future error

2. Date range exceeds 366 days
   - **Given:** date_from 2 years ago, date_to today
   - **When:** GET request
   - **Then:** 422 with range exceeded error

3. Non-existent doctor_id
   - **Given:** doctor_id of a user who does not exist in tenant
   - **When:** GET with that doctor_id
   - **Then:** 404 Not Found

4. Role is doctor accessing commissions
   - **Given:** Authenticated doctor
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Two doctors with different commission_percentage values (35%, 40%); one doctor with null commission_percentage; one clinic_owner

**Invoices:** Multiple paid invoices assigned to each doctor in January 2026; some draft invoices; invoices outside the date range

### Mocking Strategy

- Database: SQLite in-memory; seed invoices, invoice_items, and users tables with known data for predictable math verification

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/billing/commissions returns 200 with commission report
- [ ] Commission calculated as floor(total_revenue * commission_percentage / 100)
- [ ] Only paid invoices included by default (status=paid); status=all includes all non-cancelled
- [ ] doctor_id filter returns single-doctor report
- [ ] Doctors with no invoices appear with zero values
- [ ] date_to cannot be in the future (422)
- [ ] Date range limited to 366 days (422)
- [ ] Only clinic_owner can access (other roles return 403)
- [ ] All monetary values in cents (integer)
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Setting commission percentages per doctor (see user profile update spec)
- Commission payment recording or accounting integration
- Per-procedure commission overrides (post-MVP)
- Commission report PDF export
- Historical commission snapshots or versioning

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (query params)
- [x] All outputs defined (per-doctor aggregates + totals)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (clinic_owner only)
- [x] Side effects listed (audit log only)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Single aggregation query (efficient)
- [x] Matches FastAPI conventions

### Hook 3: Security & Privacy
- [x] Auth level stated (clinic_owner only)
- [x] Input sanitization defined
- [x] SQL injection prevented
- [x] No PHI in response

### Hook 4: Performance & Scalability
- [x] Response time target (< 200ms)
- [x] No caching (real-time required)
- [x] Single aggregation query with indexes listed
- [x] Bounded by clinic size

### Hook 5: Observability
- [x] Structured logging (tenant_id, user_id, date range)
- [x] Audit log entry defined
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
