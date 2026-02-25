# AD-02 — Admin Tenant Management Spec

## Overview

**Feature:** Platform-wide tenant management endpoint for superadmins. Returns a comprehensive paginated list of all tenants across the DentalOS platform, with business metrics (MRR, active users, patient count, last activity, storage used). Supports filtering by plan, status, country, creation date range, and full-text search. Sortable by revenue, user count, and creation date. Extended view beyond T-01 through T-05 (tenant CRUD).

**Domain:** admin

**Priority:** High (Sprint 1-2 — needed for platform operations from day one)

**Dependencies:** AD-01 (superadmin-login), tenants/T-01 through T-05, billing/B-01, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required — superadmin is platform-level; operates across all tenants
- **Special rules:** Requires valid admin JWT (RS256, from AD-01). Standard tenant JWTs are rejected. All responses are audit-logged.

---

## Endpoint

```
GET /api/v1/admin/tenants
```

**Rate Limiting:**
- 60 requests per minute per admin session
- Export operations (large page sizes > 100) limited to 5 per minute

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer admin JWT from AD-01 | Bearer eyJhbGc... |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| page | No | integer | >= 1, default=1 | Page number | 1 |
| page_size | No | integer | 1–200, default=25 | Results per page | 25 |
| sort | No | string | mrr_desc, mrr_asc, active_users_desc, active_users_asc, patient_count_desc, created_at_desc, created_at_asc, last_activity_desc — default=created_at_desc | Sort order | mrr_desc |
| plan | No | string | free, starter, pro, clinica, enterprise | Filter by subscription plan | pro |
| status | No | string | active, trial, suspended, cancelled, past_due | Filter by account status | active |
| country | No | string | 2-letter ISO code | Filter by country | CO |
| created_after | No | string | ISO 8601 date | Created on or after this date | 2026-01-01 |
| created_before | No | string | ISO 8601 date | Created before this date | 2026-02-01 |
| search | No | string | max 100 chars | Full-text search: matches clinic name, owner email, slug | clínica odonto |
| has_overdue | No | boolean | default=false | Filter to tenants with overdue invoices | true |
| min_mrr | No | number | >= 0 | Minimum MRR filter (USD) | 50 |

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "items": [
    {
      "tenant_id": "string — internal UUID",
      "slug": "string — URL slug e.g. clinica-torres",
      "clinic_name": "string",
      "country": "string — ISO code",
      "country_name": "string",
      "plan": "string — free | starter | pro | clinica | enterprise",
      "plan_display": "string — formatted plan label",
      "status": "string — active | trial | suspended | cancelled | past_due",
      "status_display": "string — Spanish label",
      "status_color": "string — green | yellow | red | gray",
      "owner_email": "string — clinic owner email",
      "owner_name": "string",
      "created_at": "string (ISO 8601)",
      "trial_ends_at": "string (ISO 8601) | null",
      "subscription_start_at": "string (ISO 8601) | null",
      "last_activity_at": "string (ISO 8601) | null — last API request from any user",
      "metrics": {
        "mrr_usd": "number — monthly recurring revenue in USD",
        "mrr_local": "number — MRR in local currency",
        "arr_usd": "number",
        "active_users_30d": "integer — unique users with activity in last 30 days",
        "total_users": "integer",
        "patient_count": "integer",
        "clinical_records_count": "integer",
        "appointments_30d": "integer",
        "storage_used_gb": "number",
        "storage_limit_gb": "number",
        "add_ons": "array[string] — active add-ons: voice, ai_radiograph"
      },
      "billing": {
        "current_period_end": "string (ISO 8601) | null",
        "overdue_amount_usd": "number — 0 if none",
        "last_payment_at": "string (ISO 8601) | null",
        "payment_method": "string — card | bank_transfer | none"
      },
      "flags": {
        "is_compliant": "boolean | null — null if country has no compliance checks",
        "has_open_support_ticket": "boolean",
        "is_on_trial": "boolean",
        "is_high_value": "boolean — MRR >= $100"
      }
    }
  ],
  "pagination": {
    "total": "integer",
    "page": "integer",
    "page_size": "integer",
    "total_pages": "integer",
    "has_next": "boolean",
    "has_previous": "boolean"
  },
  "platform_summary": {
    "total_tenants": "integer",
    "active_tenants": "integer",
    "trial_tenants": "integer",
    "suspended_tenants": "integer",
    "total_mrr_usd": "number",
    "total_arr_usd": "number",
    "total_patients": "integer",
    "tenants_by_plan": {
      "free": "integer",
      "starter": "integer",
      "pro": "integer",
      "clinica": "integer",
      "enterprise": "integer"
    },
    "tenants_by_country": {
      "CO": "integer",
      "MX": "integer"
    }
  },
  "applied_filters": {
    "plan": "string | null",
    "status": "string | null",
    "country": "string | null",
    "search": "string | null",
    "has_overdue": "boolean | null",
    "created_range": "string | null"
  }
}
```

**Example (truncated):**
```json
{
  "items": [
    {
      "tenant_id": "tn_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "slug": "clinica-torres-bogota",
      "clinic_name": "Clínica Dental Torres",
      "country": "CO",
      "country_name": "Colombia",
      "plan": "pro",
      "plan_display": "Pro ($39/doctor/mo)",
      "status": "active",
      "status_display": "Activo",
      "status_color": "green",
      "owner_email": "torres@clinicadental.co",
      "owner_name": "Dra. María Torres",
      "created_at": "2026-01-15T10:00:00Z",
      "trial_ends_at": null,
      "subscription_start_at": "2026-01-15T10:00:00Z",
      "last_activity_at": "2026-02-25T08:47:00Z",
      "metrics": {
        "mrr_usd": 117.00,
        "mrr_local": 455550.00,
        "arr_usd": 1404.00,
        "active_users_30d": 3,
        "total_users": 4,
        "patient_count": 312,
        "clinical_records_count": 1847,
        "appointments_30d": 94,
        "storage_used_gb": 2.3,
        "storage_limit_gb": 10.0,
        "add_ons": ["voice"]
      },
      "billing": {
        "current_period_end": "2026-03-15T00:00:00Z",
        "overdue_amount_usd": 0.0,
        "last_payment_at": "2026-02-15T00:00:00Z",
        "payment_method": "card"
      },
      "flags": {
        "is_compliant": false,
        "has_open_support_ticket": false,
        "is_on_trial": false,
        "is_high_value": true
      }
    }
  ],
  "pagination": {
    "total": 247,
    "page": 1,
    "page_size": 25,
    "total_pages": 10,
    "has_next": true,
    "has_previous": false
  },
  "platform_summary": {
    "total_tenants": 247,
    "active_tenants": 198,
    "trial_tenants": 32,
    "suspended_tenants": 8,
    "total_mrr_usd": 12450.00,
    "total_arr_usd": 149400.00,
    "total_patients": 48321,
    "tenants_by_plan": { "free": 41, "starter": 87, "pro": 93, "clinica": 22, "enterprise": 4 },
    "tenants_by_country": { "CO": 241, "MX": 6 }
  },
  "applied_filters": {
    "plan": null, "status": null, "country": null, "search": null, "has_overdue": null, "created_range": null
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid date range (created_before < created_after); invalid sort value.

**Example:**
```json
{
  "error": "invalid_filter",
  "message": "created_before must be after created_after",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Admin JWT missing, expired, or is a tenant JWT (wrong type).

**Example:**
```json
{
  "error": "admin_authentication_required",
  "message": "Valid superadmin token required",
  "details": {}
}
```

#### 403 Forbidden
**When:** JWT is valid but role is not superadmin.

#### 422 Unprocessable Entity
**When:** Query parameter types are invalid.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

---

## Business Logic

**Step-by-step process:**

1. Validate admin JWT: verify RS256 signature with admin public key; verify `type == "admin_access"` and `role == "superadmin"` in claims.
2. Validate query parameters via Pydantic schema `AdminTenantListParams`.
3. If `created_after` and `created_before` both provided, verify `created_before > created_after`.
4. Attempt cache lookup for `platform_summary` only (short TTL); per-page results are not cached.
5. Build base query from `tenants` table (public schema) with applied filters.
6. JOIN with pre-computed `tenant_metrics` materialized view (updated every 15 minutes via background job) for MRR, user counts, patient counts.
7. For `search` filter: use PostgreSQL `to_tsvector` full-text search on `clinic_name + owner_email + slug`.
8. For `sort=mrr_desc|asc`: ORDER BY `tenant_metrics.mrr_usd`.
9. Apply OFFSET/LIMIT for pagination.
10. Execute COUNT query for total.
11. Compute `platform_summary`: run aggregate queries or use cached summary (TTL 5 minutes).
12. Map results to response model, computing `plan_display`, `status_display`, `status_color`, `flags`.
13. Write audit log: action=`admin_tenant_list`, actor=`admin_user_id`, filter_params=logged.
14. Return 200.

**Metrics Computation (Background Job — not HTTP handler):**
- `tenant_metrics` materialized view refreshed every 15 minutes
- `mrr_usd`: `subscriptions.amount_monthly_usd` + active add-ons sum
- `active_users_30d`: COUNT DISTINCT user_id from `audit_logs` WHERE `timestamp > now()-30d` per tenant
- `patient_count`: COUNT from each tenant schema `patients` table
- `appointments_30d`: COUNT from tenant schema `appointments` WHERE `scheduled_at > now()-30d`
- `storage_used_gb`: sum of file sizes from object storage manifest per tenant

**is_high_value flag:** `mrr_usd >= 100`

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| page | Integer >= 1 | "Page must be >= 1" |
| page_size | Integer 1–200 | "Page size must be between 1 and 200" |
| sort | Allowed sort values only | "Invalid sort option" |
| plan | Must be free, starter, pro, clinica, or enterprise | "Invalid plan value" |
| status | Must be active, trial, suspended, cancelled, past_due | "Invalid status value" |
| country | 2-letter ISO code | "Country must be a 2-letter ISO code" |
| created_after | ISO 8601 date if provided | "Invalid date format" |
| created_before | ISO 8601 date if provided; must be after created_after | "created_before must be after created_after" |
| search | Max 100 characters | "Search query too long" |
| min_mrr | Number >= 0 | "min_mrr must be non-negative" |

**Business Rules:**

- `platform_summary` always reflects ALL tenants (not filtered to current page).
- `applied_filters` echoes back active filters to help frontend display active filter chips.
- Metrics are from the materialized view (up to 15 min stale) — not real-time to avoid slow queries on every admin page load.
- `is_compliant` is null for tenants in countries without compliance modules (not Colombia).
- Billing data comes from `subscriptions` + `invoices` public schema tables (not tenant schema).
- Owner email and name are always shown to superadmin (no PHI restrictions for admin level).
- All admin actions are audit-logged with the full filter set applied.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Search matches no tenants | Returns empty items[], pagination.total=0; platform_summary still computed over all tenants |
| Materialized view is being refreshed | Last snapshot data returned; staleness acceptable |
| Tenant has no subscription (free tier) | mrr_usd=0.00, overdue_amount_usd=0.00, payment_method=none |
| Very large export (page_size=200) | Allowed; rate-limited to 5/min to prevent abuse; query optimized via index scan |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- All reads: `tenants`, `subscriptions`, `invoices`, `tenant_metrics` (materialized view)

### Cache Operations

**Cache keys affected:**
- `admin:platform_summary`: SET on compute — TTL: 300s (5 min)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — read-only endpoint.

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** read
- **Resource:** tenant_list (admin)
- **PHI involved:** No (tenant metadata, no patient data)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms (indexed queries + materialized view)
- **Maximum acceptable:** < 800ms

### Caching Strategy
- **Strategy:** Materialized view for metrics (refreshed every 15 min); Redis for platform_summary (5 min TTL)
- **Cache key:** `admin:platform_summary`
- **TTL:** 300s
- **Invalidation:** Auto-expires; also invalidated by tenant creation/plan change events

### Database Performance

**Queries executed:** 3 (tenant list with filters, COUNT for pagination, platform_summary aggregates)

**Indexes required:**
- `tenants.(created_at DESC)` — INDEX for default sort
- `tenants.(plan, status)` — COMPOSITE INDEX for plan/status filters
- `tenants.(country)` — INDEX for country filter
- `tenants.search_vector` — GIN INDEX for full-text search (`to_tsvector(clinic_name || ' ' || owner_email || ' ' || slug)`)
- `tenant_metrics.(mrr_usd DESC)` — INDEX for MRR sort

**N+1 prevention:** Metrics loaded from materialized view JOIN — no per-tenant queries.

### Pagination

**Pagination:** Yes

- **Style:** offset-based
- **Default page size:** 25
- **Max page size:** 200

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| search | Pydantic max_length=100; stripped | Passed to full-text search (parameterized) |
| plan/status/country | Pydantic Literal enums | Only valid values accepted |
| sort | Pydantic Literal enum | Column names from allowlist; never interpolated |
| page/page_size | Pydantic integers with bounds | Prevents extreme values |
| created_after/before | Pydantic date | ISO 8601 only |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Sort column is resolved from a hard-coded Python dict (`SORT_MAP = {"mrr_desc": desc(TenantMetrics.mrr_usd), ...}`) — never interpolated from user input.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Tenant management data (clinic names, owner emails) is business data, not patient PHI.

---

## Testing

### Test Cases

#### Happy Path
1. Default list (no filters)
   - **Given:** superadmin JWT, 247 tenants
   - **When:** GET /api/v1/admin/tenants
   - **Then:** 200 OK, items has 25, pagination.total=247, platform_summary populated

2. Filter by plan=pro, sort by mrr_desc
   - **Given:** 93 pro tenants
   - **When:** GET ?plan=pro&sort=mrr_desc
   - **Then:** 200 OK, all items have plan=pro, sorted by mrr_usd descending

3. Search by clinic name
   - **Given:** 3 tenants with "Torres" in clinic name
   - **When:** GET ?search=Torres
   - **Then:** 200 OK, items has 3, all match Torres

#### Edge Cases
1. Search with no matches
   - **Given:** Search term with no matching tenants
   - **When:** GET ?search=xyznotexist
   - **Then:** 200 OK, items=[], pagination.total=0

2. Export-size request (page_size=200)
   - **Given:** superadmin
   - **When:** GET ?page_size=200
   - **Then:** 200 OK, up to 200 items returned

#### Error Cases
1. Tenant JWT used instead of admin JWT
   - **Given:** Regular clinic_owner JWT
   - **When:** GET /api/v1/admin/tenants
   - **Then:** 401 Unauthorized, "admin_authentication_required"

2. created_before before created_after
   - **Given:** superadmin JWT
   - **When:** GET ?created_after=2026-02-01&created_before=2026-01-01
   - **Then:** 400 Bad Request

### Test Data Requirements

**Users:** 1 superadmin user, regular clinic_owner (for 401 test)

**Patients/Entities:** 50+ tenant fixtures across plans and statuses; tenant_metrics materialized view populated

### Mocking Strategy

- Materialized view: Use regular table in test environment with fixtures
- Redis: fakeredis for platform_summary cache tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns paginated tenant list with metrics for each tenant
- [ ] All filters functional (plan, status, country, search, date range, min_mrr, has_overdue)
- [ ] All sort options functional (mrr, active_users, patient_count, created_at, last_activity)
- [ ] platform_summary reflects all tenants (not just current page)
- [ ] applied_filters echoed in response
- [ ] Metrics from materialized view (not real-time per-tenant queries)
- [ ] 401 returned for non-admin JWT
- [ ] 403 returned for non-superadmin role
- [ ] All test cases pass
- [ ] Performance target: < 300ms
- [ ] Quality Hooks passed
- [ ] Audit logging verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating tenants (T-01)
- Updating tenant plan/status (separate admin action specs)
- Viewing individual tenant detail (separate endpoint)
- Tenant impersonation (see AD-07)
- Deleting tenants (separate destructive action spec with additional safeguards)
- Exporting to CSV (future feature)

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
- [x] Caching strategy stated (materialized view + Redis)
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
