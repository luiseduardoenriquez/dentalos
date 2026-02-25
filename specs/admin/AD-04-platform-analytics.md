# AD-04 — Admin Platform Analytics Spec

## Overview

**Feature:** Platform-level business analytics for superadmins. Returns aggregate metrics across all tenants: total tenant counts by status/plan/country, MRR, ARR, Monthly/Daily Active Users, churn rate, new signup trends, revenue per tenant averages, top tenants by revenue, plan distribution, country distribution, and feature usage statistics. Data is pre-aggregated via background jobs; most metrics are served from cache.

**Domain:** admin

**Priority:** Medium (Sprint 13+)

**Dependencies:** AD-01 (superadmin-login), AD-02 (tenant-management — shares materialized views), infra/caching.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required — platform-level
- **Special rules:** Requires admin JWT (RS256). All analytics access is audit-logged.

---

## Endpoint

```
GET /api/v1/admin/analytics
```

**Rate Limiting:**
- 30 requests per minute per admin session (analytics queries can be heavy; cache reduces actual DB load)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer admin JWT | Bearer eyJhbGc... |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| period | No | string | 7d, 30d, 90d, 12m — default=30d | Time window for trend data | 30d |
| granularity | No | string | day, week, month — default=day (for <=30d), week (for 90d), month (for 12m) | Trend data granularity | day |
| country | No | string | 2-letter ISO code | Filter analytics to a specific country | CO |
| include_feature_usage | No | boolean | default=true | Include feature_usage_stats section | true |
| include_top_tenants | No | boolean | default=true | Include top_tenants_by_revenue section | true |

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "generated_at": "string (ISO 8601) — when this snapshot was computed",
  "period": "string — period filter applied: 7d | 30d | 90d | 12m",
  "country_filter": "string | null",
  "data_freshness_minutes": "integer — how old the underlying data is",

  "overview": {
    "total_tenants": "integer",
    "active_tenants": "integer",
    "trial_tenants": "integer",
    "suspended_tenants": "integer",
    "cancelled_tenants": "integer",
    "past_due_tenants": "integer",
    "new_tenants_in_period": "integer",
    "churned_tenants_in_period": "integer"
  },

  "revenue": {
    "mrr_usd": "number — current MRR",
    "arr_usd": "number — MRR * 12",
    "mrr_growth_pct": "number — MoM MRR growth percentage",
    "arr_growth_pct": "number",
    "mrr_new_usd": "number — MRR from new subscribers in period",
    "mrr_expansion_usd": "number — MRR gained from upgrades in period",
    "mrr_contraction_usd": "number — MRR lost from downgrades in period",
    "mrr_churn_usd": "number — MRR lost from cancellations in period",
    "net_new_mrr_usd": "number — mrr_new + mrr_expansion - mrr_contraction - mrr_churn",
    "avg_revenue_per_tenant_usd": "number — MRR / active tenants",
    "median_revenue_per_tenant_usd": "number",
    "ltv_estimate_usd": "number — avg_mrr / monthly_churn_rate"
  },

  "users": {
    "total_registered_users": "integer — across all tenants",
    "mau": "integer — Monthly Active Users (unique in last 30 days)",
    "dau": "integer — Daily Active Users (unique in last 1 day)",
    "dau_mau_ratio": "number — engagement ratio",
    "mau_growth_pct": "number — vs previous period",
    "avg_users_per_tenant": "number",
    "median_users_per_tenant": "number"
  },

  "churn": {
    "monthly_churn_rate_pct": "number — tenants churned / total at start of period",
    "mrr_churn_rate_pct": "number — MRR churned / total MRR at start",
    "net_revenue_retention_pct": "number — (MRR end - new MRR) / MRR start * 100",
    "avg_tenure_months": "number — average months a tenant has been active",
    "churn_by_plan": {
      "free": "number",
      "starter": "number",
      "pro": "number",
      "clinica": "number",
      "enterprise": "number"
    }
  },

  "new_signups": {
    "total_in_period": "integer",
    "trend": [
      {
        "date": "string (ISO 8601 date or week/month label)",
        "new_tenants": "integer",
        "new_mrr_usd": "number"
      }
    ],
    "conversion_rate_trial_to_paid_pct": "number — trials that converted to paid in period",
    "avg_trial_length_days": "number"
  },

  "plan_distribution": [
    {
      "plan": "string",
      "plan_display": "string",
      "tenant_count": "integer",
      "tenant_pct": "number",
      "mrr_usd": "number",
      "mrr_pct": "number"
    }
  ],

  "country_distribution": [
    {
      "country": "string",
      "country_name": "string",
      "tenant_count": "integer",
      "tenant_pct": "number",
      "mrr_usd": "number"
    }
  ],

  "top_tenants_by_revenue": "array[TopTenantItem] | null — only if include_top_tenants=true",

  "feature_usage_stats": "object | null — only if include_feature_usage=true",

  "clinical_volume": {
    "total_patients_platform": "integer",
    "total_appointments_in_period": "integer",
    "total_clinical_records_in_period": "integer",
    "appointments_trend": [
      { "date": "string", "count": "integer" }
    ]
  }
}
```

**TopTenantItem schema:**
```json
{
  "tenant_id": "string",
  "clinic_name": "string",
  "plan": "string",
  "country": "string",
  "mrr_usd": "number",
  "active_users_30d": "integer",
  "patient_count": "integer",
  "tenure_months": "integer",
  "add_ons": "array[string]"
}
```

**feature_usage_stats schema:**
```json
{
  "voice_enabled_tenants": "integer",
  "ai_radiograph_enabled_tenants": "integer",
  "odontogram_anatomic_tenants": "integer",
  "electronic_invoicing_active_tenants": "integer",
  "rips_generated_in_period": "integer",
  "consents_signed_in_period": "integer",
  "treatment_plans_created_in_period": "integer",
  "patient_portal_active_tenants": "integer",
  "api_access_tenants": "integer"
}
```

**Example (abbreviated):**
```json
{
  "generated_at": "2026-02-25T10:00:00Z",
  "period": "30d",
  "country_filter": null,
  "data_freshness_minutes": 15,
  "overview": {
    "total_tenants": 247,
    "active_tenants": 198,
    "trial_tenants": 32,
    "suspended_tenants": 8,
    "cancelled_tenants": 7,
    "past_due_tenants": 2,
    "new_tenants_in_period": 28,
    "churned_tenants_in_period": 3
  },
  "revenue": {
    "mrr_usd": 12450.00,
    "arr_usd": 149400.00,
    "mrr_growth_pct": 12.3,
    "arr_growth_pct": 12.3,
    "mrr_new_usd": 1560.00,
    "mrr_expansion_usd": 390.00,
    "mrr_contraction_usd": 78.00,
    "mrr_churn_usd": 117.00,
    "net_new_mrr_usd": 1755.00,
    "avg_revenue_per_tenant_usd": 62.88,
    "median_revenue_per_tenant_usd": 39.00,
    "ltv_estimate_usd": 4164.00
  },
  "users": {
    "total_registered_users": 891,
    "mau": 647,
    "dau": 312,
    "dau_mau_ratio": 0.48,
    "mau_growth_pct": 8.4,
    "avg_users_per_tenant": 4.5,
    "median_users_per_tenant": 3.0
  },
  "churn": {
    "monthly_churn_rate_pct": 1.5,
    "mrr_churn_rate_pct": 0.94,
    "net_revenue_retention_pct": 115.1,
    "avg_tenure_months": 2.3,
    "churn_by_plan": { "free": 0.0, "starter": 2.1, "pro": 0.8, "clinica": 0.0, "enterprise": 0.0 }
  },
  "new_signups": {
    "total_in_period": 28,
    "trend": [
      { "date": "2026-02-01", "new_tenants": 2, "new_mrr_usd": 78.00 },
      { "date": "2026-02-02", "new_tenants": 1, "new_mrr_usd": 39.00 }
    ],
    "conversion_rate_trial_to_paid_pct": 42.3,
    "avg_trial_length_days": 12.4
  },
  "plan_distribution": [
    { "plan": "pro", "plan_display": "Pro", "tenant_count": 93, "tenant_pct": 37.7, "mrr_usd": 10491.00, "mrr_pct": 84.3 }
  ],
  "country_distribution": [
    { "country": "CO", "country_name": "Colombia", "tenant_count": 241, "tenant_pct": 97.6, "mrr_usd": 12200.00 }
  ],
  "top_tenants_by_revenue": [
    {
      "tenant_id": "tn_xyz",
      "clinic_name": "Centro Dental Elite",
      "plan": "enterprise",
      "country": "CO",
      "mrr_usd": 980.00,
      "active_users_30d": 12,
      "patient_count": 2100,
      "tenure_months": 3,
      "add_ons": ["voice", "ai_radiograph"]
    }
  ],
  "feature_usage_stats": {
    "voice_enabled_tenants": 18,
    "ai_radiograph_enabled_tenants": 7,
    "odontogram_anatomic_tenants": 142,
    "electronic_invoicing_active_tenants": 67,
    "rips_generated_in_period": 98,
    "consents_signed_in_period": 2841,
    "treatment_plans_created_in_period": 1205,
    "patient_portal_active_tenants": 43,
    "api_access_tenants": 4
  },
  "clinical_volume": {
    "total_patients_platform": 48321,
    "total_appointments_in_period": 14820,
    "total_clinical_records_in_period": 12940,
    "appointments_trend": [
      { "date": "2026-02-01", "count": 487 },
      { "date": "2026-02-02", "count": 512 }
    ]
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid period value; granularity incompatible with period (e.g., granularity=day with period=12m is allowed but returns many data points).

#### 401 Unauthorized
**When:** Admin JWT missing or invalid.

#### 403 Forbidden
**When:** Role is not superadmin.

#### 422 Unprocessable Entity
**When:** Query parameter validation fails.

---

## Business Logic

**Step-by-step process:**

1. Validate admin JWT and superadmin role.
2. Validate query params via Pydantic schema `AdminAnalyticsParams`.
3. Determine cache key: `admin:analytics:{period}:{country_filter}:{include_feature_usage}:{include_top_tenants}`.
4. Check Redis cache — TTL 15 minutes (data freshness is acceptable for analytics).
5. On cache miss:
   a. Load `overview` from `platform_daily_snapshots` table (last snapshot).
   b. Load `revenue` metrics: query `subscriptions` + `plan_change_history` for MRR waterfall components.
   c. Load `users`: query aggregated `user_activity_daily` table for MAU/DAU.
   d. Load `churn`: compute from `subscription_events` table (created/cancelled/upgraded/downgraded).
   e. Load `new_signups` trend: query `tenants.created_at` bucketed by granularity.
   f. Load `plan_distribution`: aggregate from `subscriptions`.
   g. Load `country_distribution`: aggregate from `tenants`.
   h. If `include_top_tenants`: query `tenant_metrics` view, ORDER BY mrr_usd DESC LIMIT 10.
   i. If `include_feature_usage`: query `feature_usage_aggregates` table (updated every 15 min by background job).
   j. Load `clinical_volume`: query `platform_clinical_daily` aggregated table.
6. Apply `country_filter` WHERE clause to all queries if provided.
7. Compute derived metrics:
   - `dau_mau_ratio = dau / mau`
   - `net_new_mrr_usd = mrr_new + mrr_expansion - mrr_contraction - mrr_churn`
   - `ltv_estimate_usd = avg_mrr / (monthly_churn_rate / 100)`
   - `net_revenue_retention_pct = (mrr_end - mrr_new) / mrr_start * 100`
8. Set `data_freshness_minutes`: compute from last `platform_daily_snapshots.created_at`.
9. Cache assembled response (TTL 15 min).
10. Write audit log: action=`admin_analytics_read`, actor=`admin_user_id`, params logged.
11. Return 200.

**Data Freshness Strategy:**
- Platform-wide aggregates computed by background job every 15 minutes
- Real-time data not provided (too expensive to compute cross-tenant in real-time)
- `data_freshness_minutes` tells admin panel how stale the data is
- Manual refresh available via separate `POST /api/v1/admin/analytics/refresh` (superadmin triggers background recomputation)

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| period | 7d, 30d, 90d, or 12m | "period must be one of: 7d, 30d, 90d, 12m" |
| granularity | day, week, or month | "granularity must be one of: day, week, month" |
| country | 2-letter ISO if provided | "country must be a 2-letter ISO code" |

**Business Rules:**

- All MRR figures in USD (canonical currency). Local currency figures available in individual tenant records.
- `mrr_churn_rate_pct = churned_mrr / starting_mrr * 100` (not tenant count churn).
- NRR > 100% indicates expansion revenue exceeds churn (healthy SaaS signal).
- Top 10 tenants by MRR; ties broken by creation date (oldest first).
- Feature usage stats are estimates (based on API call patterns) — not exact counts.
- `conversion_rate_trial_to_paid_pct` measures trials that started IN the period and converted (not all-time).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No tenants yet (fresh platform) | All metrics are 0; trend arrays are empty; no error |
| monthly_churn_rate_pct = 0 | ltv_estimate_usd = null (cannot divide by zero) |
| period=12m with granularity=day | Response includes ~365 data points in trend arrays; allowed but large |
| Country filter with no tenants | Returns zero metrics for that country; no error |

---

## Side Effects

### Database Changes

All read-only. No writes during HTTP handler.

### Cache Operations

**Cache keys affected:**
- `admin:analytics:{period}:{country}:{flags_hash}`: SET TTL 900s (15 min)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None (reads from pre-computed aggregates)

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** platform_analytics
- **PHI involved:** No (aggregate statistics; no individual patient data)

---

## Performance

### Expected Response Time
- **Target:** < 200ms (cache hit)
- **Maximum acceptable:** < 3,000ms (full recomputation on cache miss)

### Caching Strategy
- **Strategy:** Redis cache; 15-minute TTL (acceptable staleness for business analytics)
- **Cache key:** `admin:analytics:{period}:{country}:{include_feature_usage}:{include_top_tenants}`
- **TTL:** 900 seconds

### Database Performance

**Queries executed (cache miss):** ~10 aggregate queries against pre-computed tables

**Pre-computed tables (updated by background jobs):**
- `platform_daily_snapshots` — refreshed every 15 min
- `tenant_metrics` — materialized view, refreshed every 15 min
- `user_activity_daily` — aggregated by background job
- `feature_usage_aggregates` — aggregated by background job
- `platform_clinical_daily` — aggregated by background job

**Indexes required:**
- `platform_daily_snapshots.(created_at DESC)` — INDEX for latest snapshot
- `subscription_events.(created_at, event_type)` — COMPOSITE INDEX for revenue metrics
- `tenants.(created_at, country)` — COMPOSITE INDEX for signup trends

**N+1 prevention:** All metrics from pre-computed tables; no cross-tenant schema queries at request time.

### Pagination

**Pagination:** No (single analytics object; trend arrays are bounded by period)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| period | Pydantic Literal enum | Only valid period strings |
| granularity | Pydantic Literal enum | Only valid granularity strings |
| country | Pydantic uppercase 2-char | ISO code only |

---

## Testing

### Test Cases

#### Happy Path
1. Default 30-day analytics
   - **Given:** superadmin JWT, 247 tenants, pre-computed aggregates loaded
   - **When:** GET /api/v1/admin/analytics
   - **Then:** 200 OK, all sections populated, mrr_usd > 0, trend has 30 data points

2. 12-month analytics (monthly granularity)
   - **Given:** superadmin JWT
   - **When:** GET ?period=12m&granularity=month
   - **Then:** 200 OK, trend has 12 data points, revenue metrics reflect 12m window

3. Country filter (Colombia only)
   - **Given:** 241 CO tenants, 6 MX tenants
   - **When:** GET ?country=CO
   - **Then:** 200 OK, overview reflects only CO tenants

4. Cache hit
   - **Given:** Previous request cached
   - **When:** Second identical GET
   - **Then:** 200 OK in < 200ms

#### Edge Cases
1. Monthly churn = 0 (no cancellations)
   - **Given:** No cancellations in period
   - **When:** GET /api/v1/admin/analytics
   - **Then:** 200 OK, churn.monthly_churn_rate_pct=0.0, ltv_estimate_usd=null

2. Fresh platform (no tenants)
   - **Given:** Empty platform
   - **When:** GET analytics
   - **Then:** 200 OK, all counts=0, trend arrays empty

#### Error Cases
1. Non-superadmin access
   - **Given:** Regular clinic_owner JWT
   - **When:** GET /api/v1/admin/analytics
   - **Then:** 401 (wrong JWT type)

2. Invalid period
   - **Given:** superadmin JWT
   - **When:** GET ?period=45d
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** 1 superadmin

**Patients/Entities:** Pre-populated `platform_daily_snapshots`, `tenant_metrics`, `user_activity_daily`, `feature_usage_aggregates` tables with 30+ days of history

### Mocking Strategy

- Redis: fakeredis
- Background aggregation tables: seeded with known test data fixtures
- Time: freeze at known point for deterministic trend calculations

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns all 7 sections (overview, revenue, users, churn, new_signups, distributions, clinical_volume)
- [ ] feature_usage_stats populated when include_feature_usage=true
- [ ] top_tenants_by_revenue returns top 10 sorted by MRR
- [ ] MRR waterfall components (new, expansion, contraction, churn, net) sum correctly
- [ ] Trend arrays correctly bucketed by granularity
- [ ] Country filter scopes all metrics to selected country
- [ ] Redis cache used (15 min TTL)
- [ ] data_freshness_minutes reflects time since last background job run
- [ ] All test cases pass
- [ ] Performance target: < 200ms cached
- [ ] Quality Hooks passed
- [ ] Audit logging verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Cohort analysis (tenant cohorts by signup month)
- Individual tenant analytics (see tenant detail endpoint)
- Custom date ranges (only predefined periods: 7d, 30d, 90d, 12m)
- CSV/Excel export of analytics data
- Real-time streaming analytics
- A/B test analytics
- Marketing attribution analytics

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Matches FastAPI conventions
- [x] Pre-computed aggregates pattern documented

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization defined
- [x] No PHI in analytics response
- [x] Audit trail

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] 15-min cache strategy documented
- [x] Pre-computed tables listed
- [x] No real-time cross-tenant queries

### Hook 5: Observability
- [x] Structured logging
- [x] Audit log entries
- [x] data_freshness_minutes in response

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Mocking strategy
- [x] Acceptance criteria

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
