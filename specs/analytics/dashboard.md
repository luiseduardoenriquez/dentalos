# AN-01 — Analytics Dashboard Spec

---

## Overview

**Feature:** Clinic analytics dashboard. Returns pre-aggregated metric widgets for the main clinic dashboard: new/total patients, appointments (today/week/month), revenue for the period, no-show rate, top 5 procedures by count, and doctor occupancy rate. Supports date range presets and custom ranges. clinic_owner sees clinic-wide; doctor sees only their own data.

**Domain:** analytics

**Priority:** Medium

**Dependencies:** A-01 (login), A-02 (me), patients/patient-list, appointments (sprint 5-6), billing/quotation-create, infra/caching-strategy.md, infra/audit-logging.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** doctor role automatically scoped to their own appointments, revenue, and procedures. clinic_owner sees all doctors. assistant and receptionist do not have access to analytics. Superadmin uses a separate platform-level analytics endpoint.

---

## Endpoint

```
GET /api/v1/analytics/dashboard
```

**Rate Limiting:**
- 30 requests per minute per user
- Analytics endpoints have lower rate limits due to query cost

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
| period | No | string | Enum: `today`, `this_week`, `this_month`, `this_quarter`, `this_year`, `custom`. Default: `this_month` | Date range preset | `this_month` |
| date_from | Conditional | string | ISO 8601 date (YYYY-MM-DD). Required when `period=custom` | Custom range start | `2026-01-01` |
| date_to | Conditional | string | ISO 8601 date (YYYY-MM-DD). Required when `period=custom`. Must be >= date_from. Max range: 366 days | Custom range end | `2026-02-25` |
| doctor_id | No | string (UUID) | Only valid for clinic_owner role. Doctor role ignores this param and always uses their own ID | Filter dashboard to a single doctor | `b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7` |

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
    "timezone": "string (IANA timezone)"
  },
  "widgets": {
    "patients": {
      "total": "integer — total active patients in clinic",
      "new_in_period": "integer — new patients created in the selected period",
      "growth_vs_previous": "number | null — percentage change vs same-length previous period"
    },
    "appointments": {
      "today": "integer — appointments scheduled for today",
      "in_period": "integer — total appointments in period",
      "completed": "integer — appointments with status 'completed' in period",
      "no_shows": "integer — appointments with status 'no_show' in period",
      "no_show_rate": "number — percentage (0-100)",
      "cancelled": "integer"
    },
    "revenue": {
      "total_in_period": "number — sum of paid invoices in period (COP)",
      "currency": "string (ISO 4217)",
      "growth_vs_previous": "number | null — percentage change vs previous period",
      "pending_collection": "number — sum of unpaid/overdue invoices"
    },
    "top_procedures": [
      {
        "procedure_code": "string (CUPS code)",
        "procedure_name": "string",
        "count": "integer",
        "rank": "integer (1-5)"
      }
    ],
    "occupancy": [
      {
        "doctor_id": "uuid",
        "doctor_name": "string",
        "scheduled_slots": "integer",
        "used_slots": "integer",
        "occupancy_rate": "number (percentage 0-100)"
      }
    ]
  },
  "generated_at": "string (ISO 8601 datetime — when this data was computed)",
  "cache_hit": "boolean — true if served from cache"
}
```

**Example:**
```json
{
  "period": {
    "preset": "this_month",
    "date_from": "2026-02-01",
    "date_to": "2026-02-25",
    "timezone": "America/Bogota"
  },
  "widgets": {
    "patients": {
      "total": 342,
      "new_in_period": 18,
      "growth_vs_previous": 12.5
    },
    "appointments": {
      "today": 8,
      "in_period": 187,
      "completed": 162,
      "no_shows": 12,
      "no_show_rate": 6.4,
      "cancelled": 13
    },
    "revenue": {
      "total_in_period": 15400000,
      "currency": "COP",
      "growth_vs_previous": 8.3,
      "pending_collection": 2100000
    },
    "top_procedures": [
      {"procedure_code": "89.07.01.01", "procedure_name": "Consulta odontológica", "count": 45, "rank": 1},
      {"procedure_code": "23.01.02.01", "procedure_name": "Extracción dental simple", "count": 31, "rank": 2},
      {"procedure_code": "23.11.01.01", "procedure_name": "Restauración resina", "count": 28, "rank": 3},
      {"procedure_code": "23.13.02.01", "procedure_name": "Blanqueamiento dental", "count": 19, "rank": 4},
      {"procedure_code": "23.09.02.01", "procedure_name": "Endodoncia unirradicular", "count": 14, "rank": 5}
    ],
    "occupancy": [
      {"doctor_id": "...", "doctor_name": "Dr. García", "scheduled_slots": 160, "used_slots": 142, "occupancy_rate": 88.75},
      {"doctor_id": "...", "doctor_name": "Dra. López", "scheduled_slots": 120, "used_slots": 98, "occupancy_rate": 81.67}
    ]
  },
  "generated_at": "2026-02-25T10:30:00Z",
  "cache_hit": true
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid `period` value, `date_from` > `date_to`, date range exceeds 366 days, `custom` period missing `date_from` or `date_to`, `doctor_id` used by doctor role.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "El rango de fechas personalizado requiere 'date_from' y 'date_to'.",
  "details": {
    "date_from": ["Este campo es requerido cuando period='custom'."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. See `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Role not allowed (assistant, receptionist, patient attempting to access analytics).

**Example:**
```json
{
  "error": "acceso_denegado",
  "message": "No tiene permisos para acceder al panel de análisis.",
  "details": {}
}
```

#### 422 Unprocessable Entity
**When:** Date strings cannot be parsed as valid ISO 8601 dates.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Aggregation query failure, materialized view refresh error, or Redis failure with DB fallback failure.

---

## Business Logic

**Step-by-step process:**

1. Validate and parse JWT — extract `user_id`, `tenant_id`, `role` from claims.
2. Authorize: if role not in `[clinic_owner, doctor]`, return 403.
3. Validate query parameters: parse `period`, compute `date_from`/`date_to` from the preset in tenant timezone (fetched from `tenants.settings.timezone`). Validate custom range constraints.
4. Determine scope: if `role == doctor`, set `doctor_filter = current_user.id`. If `role == clinic_owner` and `doctor_id` param provided, set `doctor_filter = doctor_id`. Otherwise, `doctor_filter = None` (clinic-wide).
5. Build cache key: `tenant:{tenant_id}:analytics:dashboard:{role}:{doctor_filter}:{date_from}:{date_to}`.
6. Check Redis for cache hit. If hit and `generated_at` within 5 minutes, return cached response with `cache_hit: true`.
7. On cache miss, execute analytics queries (all async, concurrent via `asyncio.gather`):
   - **Patients widget:** `COUNT(*)` on `patients` where `deleted_at IS NULL` for total; `COUNT(*)` where `created_at BETWEEN date_from AND date_to` for new. Compute previous period growth.
   - **Appointments widget:** Multiple aggregate queries on `appointments` table filtered by date range (and doctor if scoped).
   - **Revenue widget:** SUM of `invoices.total_paid` where `paid_at BETWEEN date_from AND date_to`. SUM of unpaid `invoices.balance_due` where `due_date < NOW()`.
   - **Top procedures widget:** GROUP BY procedure CUPS code on `clinical_record_procedures` for the period, ORDER BY count DESC LIMIT 5.
   - **Occupancy widget:** Per-doctor: `(used_slots / available_slots * 100)` computed from appointment schedule grid. One query per doctor if scoped, or multi-row aggregate if clinic-wide.
8. Assemble widget response object.
9. Store in Redis with 300-second TTL.
10. Return 200 with full widget object and `cache_hit: false`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| period | Must be one of: today, this_week, this_month, this_quarter, this_year, custom | Período no válido. |
| date_from | Required when period=custom; valid ISO 8601 date | La fecha de inicio es requerida. |
| date_to | Required when period=custom; must be >= date_from; max 366-day range | La fecha de fin es requerida y debe ser mayor a la fecha de inicio. |
| doctor_id | Only valid UUID; only accepted when role=clinic_owner | No puede filtrar por médico con su rol actual. |

**Business Rules:**

- All date range calculations use the tenant's configured timezone (`tenants.settings.timezone`). Default: `America/Bogota`.
- Doctor role always sees only their own data. The `doctor_id` query parameter is silently ignored for doctor role.
- `growth_vs_previous` compares the selected period to the same-length period immediately before it. If previous period has 0, growth is `null` (not infinity).
- Materialized views should be used for the top procedures and occupancy widgets (refreshed every 15 minutes via background job) to avoid full-table scans on large datasets.
- Revenue amounts are always in the tenant's configured currency (default: COP). No multi-currency conversion in v1.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| period=today, no appointments today | appointments.today = 0, no error |
| period=custom, date_from == date_to | Valid — returns metrics for a single day |
| No invoices in period | revenue.total_in_period = 0, growth_vs_previous = null |
| Only 1 doctor in clinic | occupancy array has 1 element |
| clinic_owner filters by doctor_id that doesn't exist | 404 doctor not found |
| Top procedures — fewer than 5 procedure types in period | Returns only available procedures (1-4 items) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- All queries are READ-ONLY. No writes.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:analytics:dashboard:{role}:{doctor_filter_hash}:{date_from}:{date_to}`: SET — full response cached.

**Cache TTL:** 300 seconds (5 minutes).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None. Read-only.

### Audit Log

**Audit entry:** Yes (read access to aggregated clinical and revenue data).
- **Action:** read
- **Resource:** analytics_dashboard
- **PHI involved:** No (aggregated/anonymous data only — no individual patient records returned)

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 300ms (cached), < 2000ms (cache miss / DB aggregation)
- **Maximum acceptable:** < 5000ms (heavy custom range queries)

### Caching Strategy
- **Strategy:** Redis cache with 5-minute TTL; materialized views for heavy widgets
- **Cache key:** `tenant:{tenant_id}:analytics:dashboard:{role}:{doctor_filter_hash}:{date_from}:{date_to}`
- **TTL:** 300 seconds
- **Invalidation:** Time-based expiry only — dashboards are near-real-time, not real-time.

### Database Performance

**Queries executed:** 5-7 concurrent async queries (one per widget)

**Indexes required:**
- `patients.(tenant_id, created_at, deleted_at)` — new patients in period
- `appointments.(doctor_id, scheduled_at, status)` — appointment widgets
- `appointments.(scheduled_at, status)` — clinic-wide appointment queries
- `invoices.(paid_at, status)` — revenue widget
- `invoices.(due_date, status)` — pending collection widget
- Materialized view: `mv_top_procedures_{tenant_id}` — refreshed every 15 minutes via background job

**N+1 prevention:** All widgets computed with aggregate queries. No per-row iteration.

### Pagination

**Pagination:** No — returns fixed-size widget payload.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| period | Pydantic enum validator | Rejects unknown presets |
| date_from / date_to | Pydantic date validator | Rejects non-date strings |
| doctor_id | Pydantic UUID validator | Rejects non-UUID; existence checked in DB |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries and aggregate functions.

### XSS Prevention

**Output encoding:** All string outputs (procedure names, doctor names) escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. All data is aggregated. Individual patient identifiers are not present in the response. `doctor_name` is an employee record, not patient PHI.

**Audit requirement:** Read access logged for accountability. Aggregate data only.

---

## Testing

### Test Cases

#### Happy Path
1. clinic_owner requests this_month dashboard
   - **Given:** Tenant with 342 patients, 187 appointments, revenue data for Feb 2026
   - **When:** GET /api/v1/analytics/dashboard?period=this_month
   - **Then:** 200 with all 5 widgets populated correctly; `cache_hit: false`; second request returns `cache_hit: true`

2. doctor role requests dashboard
   - **Given:** Doctor user with 45 of the 187 clinic appointments
   - **When:** GET /api/v1/analytics/dashboard
   - **Then:** 200 with appointments.in_period = 45 (not 187); revenue reflects only this doctor's invoices

3. Custom date range
   - **Given:** clinic_owner
   - **When:** GET /api/v1/analytics/dashboard?period=custom&date_from=2026-01-01&date_to=2026-01-31
   - **Then:** 200 with metrics for January 2026 only

#### Edge Cases
1. Empty clinic (new tenant)
   - **Given:** New tenant with no patients or appointments
   - **When:** GET /api/v1/analytics/dashboard
   - **Then:** 200 with all counts = 0, growth = null, top_procedures = [], occupancy = []

2. Cache hit
   - **Given:** Dashboard fetched within past 5 minutes
   - **When:** Subsequent GET with same params
   - **Then:** `cache_hit: true`; response served in < 300ms

#### Error Cases
1. assistant role
   - **Given:** Authenticated assistant user
   - **When:** GET /api/v1/analytics/dashboard
   - **Then:** 403 Forbidden

2. Custom period missing date_from
   - **Given:** clinic_owner
   - **When:** GET /api/v1/analytics/dashboard?period=custom&date_to=2026-02-25
   - **Then:** 400 with Spanish error about missing date_from

3. Date range > 366 days
   - **Given:** clinic_owner
   - **When:** period=custom, date_from=2024-01-01, date_to=2026-02-25
   - **Then:** 400 — range exceeds maximum allowed

### Test Data Requirements

**Users:** clinic_owner; doctor user; assistant user (for 403 test).

**Patients/Entities:** 10+ patients, 20+ appointments across varied statuses, 5+ invoices, 3+ procedure types in test DB.

### Mocking Strategy

- Redis: fakeredis for unit tests; real Redis for integration tests.
- Database: Full tenant schema with seeded analytics data.
- External dependencies: None (pure DB aggregation).

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] All 5 widgets return correct aggregated data for each period preset
- [ ] Doctor role scoped to their own data only; clinic_owner sees clinic-wide
- [ ] `growth_vs_previous` computed correctly; null when previous period has 0
- [ ] Cache hit within 300ms; cache miss within 2000ms
- [ ] 5-minute Redis cache with correct tenant-namespaced key
- [ ] 403 for assistant/receptionist/patient roles
- [ ] Custom date range validation (missing dates, too wide range)
- [ ] Tenant timezone applied to all date range calculations
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Real-time WebSocket dashboard updates
- Patient-level drill-down from widgets (separate endpoints in AN-02 through AN-05)
- Multi-location (multi-tenant) aggregate views
- Custom widget configuration per user
- Forecasting or predictive analytics
- Export from dashboard (see AN-06)

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
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

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
| 1.0 | 2026-02-25 | Initial spec |
