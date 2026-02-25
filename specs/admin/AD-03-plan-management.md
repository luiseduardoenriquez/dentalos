# AD-03 — Admin Plan Management Spec

## Overview

**Feature:** Manage subscription plans for the DentalOS platform. GET returns all plans with current pricing, limits, and feature flags. PUT updates a specific plan's pricing, limits, and feature toggles. Plan changes apply to new subscriptions only; existing subscribers are grandfathered at their current rates. Superadmin only.

**Domain:** admin

**Priority:** High (Sprint 1-2 — plans must be defined before first tenant can subscribe)

**Dependencies:** AD-01 (superadmin-login), tenants/T-01 (uses plan limits), infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required — platform-level operation
- **Special rules:** Requires admin JWT (RS256 from AD-01). Plan updates trigger a cache invalidation event that propagates to all tenant sessions within 1 minute.

---

## Endpoints

```
GET  /api/v1/admin/plans
PUT  /api/v1/admin/plans/{plan_id}
```

**Rate Limiting:**
- GET: 60 requests per minute per admin session
- PUT: 10 requests per minute per admin session (write operations are audited heavily)

---

## Request — GET /api/v1/admin/plans

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer admin JWT | Bearer eyJhbGc... |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| include_inactive | No | boolean | default=false | Include deprecated/inactive plans | false |
| include_tenant_counts | No | boolean | default=true | Include count of tenants per plan | true |

---

## Request — PUT /api/v1/admin/plans/{plan_id}

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| plan_id | Yes | string | Valid plan slug | Plan to update | pro |

### Request Body Schema

```json
{
  "display_name": "string (optional) — plan display name",
  "description": "string (optional, max 500) — plan description",
  "pricing": {
    "monthly_usd": "number (optional) — monthly price per unit in USD",
    "annual_usd": "number (optional) — annual price per unit in USD (usually ~17% discount)",
    "currency": "string (optional) — COP | MXN | USD",
    "price_cop": "number (optional) — price in COP for Colombia",
    "price_mxn": "number (optional) — price in MXN for Mexico"
  },
  "limits": {
    "max_doctors": "integer (optional) — -1 for unlimited",
    "max_patients": "integer (optional) — -1 for unlimited",
    "max_locations": "integer (optional)",
    "max_storage_gb": "number (optional)",
    "max_monthly_appointments": "integer (optional) — -1 for unlimited",
    "max_users": "integer (optional)"
  },
  "features": {
    "odontogram_classic": "boolean (optional)",
    "odontogram_anatomic": "boolean (optional)",
    "treatment_plans": "boolean (optional)",
    "consents_digital": "boolean (optional)",
    "rips_reporting": "boolean (optional)",
    "rda_compliance": "boolean (optional)",
    "electronic_invoicing": "boolean (optional)",
    "patient_portal": "boolean (optional)",
    "whatsapp_notifications": "boolean (optional)",
    "analytics_basic": "boolean (optional)",
    "analytics_advanced": "boolean (optional)",
    "api_access": "boolean (optional)",
    "multi_location": "boolean (optional)",
    "inventory_module": "boolean (optional)",
    "telehealth": "boolean (optional)"
  },
  "add_ons_available": "array[string] (optional) — which add-ons can be purchased on this plan: voice, ai_radiograph",
  "is_publicly_visible": "boolean (optional) — show on pricing page",
  "is_active": "boolean (optional) — allow new signups",
  "grandfathering_notes": "string (optional, max 500) — internal notes about existing subscriber handling"
}
```

**Example PUT Request:**
```json
{
  "pricing": {
    "monthly_usd": 39.00,
    "annual_usd": 32.00,
    "price_cop": 151710
  },
  "limits": {
    "max_patients": -1,
    "max_storage_gb": 10.0
  },
  "features": {
    "analytics_advanced": true,
    "patient_portal": true
  },
  "grandfathering_notes": "Existing pro subscribers keep unlimited storage until 2027-01-01"
}
```

---

## Response — GET /api/v1/admin/plans

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "plans": [
    {
      "plan_id": "string — slug: free | starter | pro | clinica | enterprise",
      "display_name": "string",
      "description": "string",
      "is_active": "boolean",
      "is_publicly_visible": "boolean",
      "billing_unit": "string — per_doctor | per_location | flat",
      "created_at": "string (ISO 8601)",
      "last_updated_at": "string (ISO 8601)",
      "last_updated_by": "string — admin user name",
      "pricing": {
        "monthly_usd": "number",
        "annual_usd": "number",
        "annual_savings_pct": "number — computed: (1 - annual/monthly) * 100",
        "price_cop": "number",
        "price_mxn": "number | null"
      },
      "limits": {
        "max_doctors": "integer — -1 = unlimited",
        "max_patients": "integer",
        "max_locations": "integer",
        "max_storage_gb": "number",
        "max_monthly_appointments": "integer",
        "max_users": "integer"
      },
      "features": {
        "odontogram_classic": "boolean",
        "odontogram_anatomic": "boolean",
        "treatment_plans": "boolean",
        "consents_digital": "boolean",
        "rips_reporting": "boolean",
        "rda_compliance": "boolean",
        "electronic_invoicing": "boolean",
        "patient_portal": "boolean",
        "whatsapp_notifications": "boolean",
        "analytics_basic": "boolean",
        "analytics_advanced": "boolean",
        "api_access": "boolean",
        "multi_location": "boolean",
        "inventory_module": "boolean",
        "telehealth": "boolean"
      },
      "add_ons_available": "array[string]",
      "tenant_stats": {
        "total_subscribers": "integer",
        "active_subscribers": "integer",
        "trial_subscribers": "integer",
        "mrr_usd": "number — total MRR from this plan",
        "avg_mrr_per_tenant_usd": "number"
      }
    }
  ],
  "summary": {
    "total_plans": "integer",
    "active_plans": "integer",
    "total_platform_mrr_usd": "number"
  }
}
```

**Example:**
```json
{
  "plans": [
    {
      "plan_id": "free",
      "display_name": "Free",
      "description": "Para clínicas unipersonales comenzando su digitalización",
      "is_active": true,
      "is_publicly_visible": true,
      "billing_unit": "flat",
      "created_at": "2026-01-01T00:00:00Z",
      "last_updated_at": "2026-02-01T00:00:00Z",
      "last_updated_by": "Platform Admin",
      "pricing": {
        "monthly_usd": 0.0,
        "annual_usd": 0.0,
        "annual_savings_pct": 0.0,
        "price_cop": 0,
        "price_mxn": null
      },
      "limits": {
        "max_doctors": 1,
        "max_patients": 50,
        "max_locations": 1,
        "max_storage_gb": 1.0,
        "max_monthly_appointments": 30,
        "max_users": 2
      },
      "features": {
        "odontogram_classic": true,
        "odontogram_anatomic": false,
        "treatment_plans": false,
        "consents_digital": false,
        "rips_reporting": false,
        "rda_compliance": false,
        "electronic_invoicing": false,
        "patient_portal": false,
        "whatsapp_notifications": false,
        "analytics_basic": false,
        "analytics_advanced": false,
        "api_access": false,
        "multi_location": false,
        "inventory_module": false,
        "telehealth": false
      },
      "add_ons_available": [],
      "tenant_stats": {
        "total_subscribers": 41,
        "active_subscribers": 35,
        "trial_subscribers": 6,
        "mrr_usd": 0.0,
        "avg_mrr_per_tenant_usd": 0.0
      }
    },
    {
      "plan_id": "pro",
      "display_name": "Pro",
      "description": "Para clínicas con 2-4 doctores y flujo de trabajo completo",
      "is_active": true,
      "is_publicly_visible": true,
      "billing_unit": "per_doctor",
      "created_at": "2026-01-01T00:00:00Z",
      "last_updated_at": "2026-02-15T10:00:00Z",
      "last_updated_by": "Platform Admin",
      "pricing": {
        "monthly_usd": 39.0,
        "annual_usd": 32.0,
        "annual_savings_pct": 17.9,
        "price_cop": 151710,
        "price_mxn": null
      },
      "limits": {
        "max_doctors": -1,
        "max_patients": -1,
        "max_locations": 3,
        "max_storage_gb": 10.0,
        "max_monthly_appointments": -1,
        "max_users": -1
      },
      "features": {
        "odontogram_classic": true, "odontogram_anatomic": true,
        "treatment_plans": true, "consents_digital": true,
        "rips_reporting": true, "rda_compliance": true,
        "electronic_invoicing": true, "patient_portal": true,
        "whatsapp_notifications": true, "analytics_basic": true,
        "analytics_advanced": false, "api_access": false,
        "multi_location": true, "inventory_module": true,
        "telehealth": false
      },
      "add_ons_available": ["voice", "ai_radiograph"],
      "tenant_stats": {
        "total_subscribers": 93,
        "active_subscribers": 89,
        "trial_subscribers": 4,
        "mrr_usd": 10491.00,
        "avg_mrr_per_tenant_usd": 117.0
      }
    }
  ],
  "summary": {
    "total_plans": 5,
    "active_plans": 5,
    "total_platform_mrr_usd": 12450.00
  }
}
```

## Response — PUT /api/v1/admin/plans/{plan_id}

**Status:** 200 OK

**Schema:**
```json
{
  "plan_id": "string",
  "display_name": "string",
  "updated_fields": "array[string] — list of fields that were changed",
  "previous_values": {
    "field_name": "previous_value"
  },
  "new_values": {
    "field_name": "new_value"
  },
  "grandfathering_applied": "boolean — true if existing subscribers are NOT affected",
  "affected_new_signups": "boolean — true (always affects new signups)",
  "cache_invalidation_queued": "boolean",
  "updated_at": "string (ISO 8601)",
  "updated_by": "string"
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid pricing values (negative prices), invalid limit values (max_doctors=0 is not valid, use -1 for unlimited), inconsistent feature flags (analytics_advanced=true requires analytics_basic=true).

**Example:**
```json
{
  "error": "invalid_plan_update",
  "message": "Validation errors in plan update",
  "details": {
    "pricing.monthly_usd": ["Price cannot be negative"],
    "features": ["analytics_advanced requires analytics_basic to be enabled first"]
  }
}
```

#### 401 Unauthorized
**When:** Admin JWT missing or invalid.

#### 403 Forbidden
**When:** JWT role is not superadmin.

#### 404 Not Found
**When:** `plan_id` does not match any existing plan.

#### 422 Unprocessable Entity
**When:** Request body Pydantic validation fails.

---

## Business Logic — GET

1. Validate admin JWT.
2. Check cache: `admin:plans:all:{include_inactive}`.
3. On cache miss, query `plans` table with all fields; JOIN `plan_tenant_stats` materialized view.
4. If `include_inactive=false`, filter `is_active=true` plans only.
5. Compute `annual_savings_pct` = `(1 - annual_usd / monthly_usd) * 100` for each plan.
6. Cache response: TTL 300s.
7. Return 200.

## Business Logic — PUT

1. Validate admin JWT.
2. Validate path parameter `plan_id` is a valid plan slug.
3. Validate request body: no negative prices; limits use -1 (not 0) for unlimited; feature dependency checks.
4. Fetch current plan from `plans` table. Return 404 if not found.
5. Compute `updated_fields`: diff old vs new values for each provided field.
6. Apply updates to `plans` table (only fields explicitly provided in request body).
7. Mark plan as grandfathered: add entry to `plan_change_history` table with `applies_to_new_only=true`.
8. Invalidate caches:
   - `admin:plans:all:*` (admin panel plan list)
   - `global:compliance_config:*` (plans affect feature availability in country config)
   - `tenant:*:plan_features` (plan feature cache on all tenants — via background propagation)
9. Publish `plan_updated` event to `admin.events` exchange so tenant-level feature flag caches can be invalidated.
10. Write audit log: action=`plan_updated`, actor=`admin_user_id`, plan_id=`plan_id`, changes=`updated_fields`, previous=`previous_values`.
11. Return 200 with diff.

**Business Rules:**

- `max_doctors=-1`, `max_patients=-1`, `max_monthly_appointments=-1`, `max_users=-1` all mean unlimited.
- Plan pricing changes apply to NEW subscriptions and renewals. Existing subscribers are grandfathered at their subscription's `locked_monthly_price_usd` until they change plans.
- `analytics_advanced` feature requires `analytics_basic=true` (dependency check).
- `multi_location` feature requires `max_locations > 1`.
- `rips_reporting` and `rda_compliance` can only be enabled if country=CO (enforced at feature flag evaluation time, not plan config time).
- `is_active=false` prevents new signups on that plan but does not affect existing subscribers.
- Free plan: `monthly_usd=0`, `add_ons_available=[]` — add-ons cannot be purchased on free plan.
- Enterprise plan: pricing shown as 0 (handled via custom contracts outside the system).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| pricing.monthly_usd | >= 0 | "Price cannot be negative" |
| pricing.annual_usd | >= 0 and <= monthly_usd | "Annual price must be <= monthly price" |
| limits.max_doctors | Integer >= 1 or -1 | "max_doctors must be >= 1 or -1 (unlimited)" |
| limits.max_patients | Integer >= 1 or -1 | "max_patients must be >= 1 or -1 (unlimited)" |
| limits.max_storage_gb | Number > 0 | "Storage must be positive" |
| features.analytics_advanced | Requires analytics_basic=true | "analytics_advanced requires analytics_basic" |
| features.multi_location | Requires max_locations > 1 | "multi_location requires max_locations > 1" |

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| PUT with no changed fields | 200 OK with empty updated_fields; no DB write; no cache invalidation |
| PUT on enterprise plan | Allowed; enterprise plan is treated as any other plan |
| PUT changes free plan monthly_usd to non-zero | Allowed but logs warning; existing free users are grandfathered |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `plans`: UPDATE (on PUT)
- `plan_change_history`: INSERT (on PUT) — audit trail of plan changes

**Example query (SQLAlchemy):**
```python
await session.execute(
    update(Plan)
    .where(Plan.id == plan_id)
    .values(**updated_values)
)
plan_change = PlanChangeHistory(
    plan_id=plan_id,
    changed_by=admin_user_id,
    changed_at=utcnow(),
    previous_values=previous_values_json,
    new_values=new_values_json,
    applies_to_new_only=True,
)
session.add(plan_change)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `admin:plans:all:*`: INVALIDATE on PUT
- `global:compliance_config:*`: INVALIDATE on PUT (features may change)
- `tenant:*:plan_features`: INVALIDATE via background propagation (fan-out via `admin.events` queue)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| admin.events | plan_updated | `{ plan_id, updated_fields, changed_at }` | After PUT succeeds |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** read (GET) / update (PUT)
- **Resource:** plan
- **PHI involved:** No

### Notifications

**Notifications triggered:** No (plan changes affect new signups; no tenant notification needed)

---

## Performance

### Expected Response Time
- **GET Target:** < 100ms (cache hit)
- **PUT Target:** < 300ms

### Caching Strategy
- **Cache key (GET):** `admin:plans:all:{include_inactive}`
- **TTL:** 300s
- **Invalidation:** On PUT; on tenant stats materialized view refresh

### Database Performance (GET)

**Queries executed:** 1 (JOIN plans + plan_tenant_stats view)

**Indexes required:**
- `plans.(plan_id)` — UNIQUE INDEX
- `plans.(is_active)` — INDEX for active filter

**N+1 prevention:** Tenant stats from materialized view JOIN — single query.

### Pagination

**Pagination:** No (only 5–10 plans total)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| plan_id | Literal slug enum | Only known plan slugs |
| pricing fields | Pydantic float, ge=0 | Non-negative numbers only |
| limit fields | Pydantic integer, ge=-1 | -1 or positive |
| feature flags | Pydantic bool | Boolean only |
| display_name | Pydantic max_length=100 | Plain text |
| description | Pydantic max_length=500 | Plain text |

---

## Testing

### Test Cases

#### Happy Path
1. GET all plans
   - **Given:** superadmin JWT, 5 plans in DB
   - **When:** GET /api/v1/admin/plans
   - **Then:** 200 OK, 5 plans returned with all fields, tenant_stats populated

2. PUT update pro plan pricing
   - **Given:** superadmin JWT, pro plan exists
   - **When:** PUT /api/v1/admin/plans/pro with pricing.monthly_usd=42.00
   - **Then:** 200 OK, updated_fields=["pricing.monthly_usd"], previous_values shows 39.0, plan_change_history row created

3. GET includes inactive plans when requested
   - **Given:** 1 deprecated plan with is_active=false
   - **When:** GET ?include_inactive=true
   - **Then:** 200 OK, includes the inactive plan

#### Edge Cases
1. PUT with only one field changes
   - **Given:** Pro plan
   - **When:** PUT with only max_storage_gb=15
   - **Then:** 200 OK, only max_storage_gb in updated_fields; other fields unchanged

2. PUT with no actual changes
   - **Given:** Pro plan monthly_usd=39.00
   - **When:** PUT with monthly_usd=39.00 (same value)
   - **Then:** 200 OK, updated_fields=[]

#### Error Cases
1. PUT with negative price
   - **Given:** superadmin JWT
   - **When:** PUT with monthly_usd=-5
   - **Then:** 400 Bad Request

2. PUT analytics_advanced without analytics_basic
   - **Given:** Free plan with analytics_basic=false
   - **When:** PUT with features.analytics_advanced=true
   - **Then:** 400 Bad Request, dependency error

3. PUT non-existent plan
   - **Given:** superadmin JWT
   - **When:** PUT /api/v1/admin/plans/enterprise_plus
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** 1 superadmin

**Patients/Entities:** 5 plan rows (free, starter, pro, clinica, enterprise); plan_tenant_stats materialized view with counts

### Mocking Strategy

- Redis: fakeredis for cache tests
- RabbitMQ: In-memory for plan_updated event tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns all 5 plans with pricing, limits, features, and tenant_stats
- [ ] GET include_inactive=true shows deprecated plans
- [ ] PUT updates specified fields only (partial update)
- [ ] PUT creates plan_change_history record
- [ ] PUT with negative price returns 400
- [ ] Feature dependency validation enforced (analytics_advanced needs analytics_basic)
- [ ] Cache invalidated after PUT (admin plans, compliance config, tenant feature flags)
- [ ] plan_updated event published to admin.events queue
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed
- [ ] Audit logging verified for PUT operations

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating new plans (done via migration/seed script; plans rarely change)
- Deleting plans (use is_active=false instead)
- Per-tenant pricing overrides (custom enterprise pricing via custom contracts)
- Subscription management (upgrading/downgrading a tenant's plan — separate spec)
- Add-on pricing (add-ons have separate price table)
- Promotional codes and discounts

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
- [x] Auth level stated
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure
- [x] Audit trail for plan changes

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized
- [x] Pagination applied where needed

### Hook 5: Observability
- [x] Structured logging
- [x] Audit log entries defined
- [x] Error tracking
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data requirements specified
- [x] Mocking strategy for external services
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
