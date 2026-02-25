# PP-04 Portal Treatment Plans Spec

---

## Overview

**Feature:** List a patient's own treatment plans from the portal — both active and completed. Read-only. Shows plan progress, individual treatment items with procedures and costs, and approval status. Designed to give patients full transparency into their proposed and ongoing care.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-05 (portal-treatment-plan-approve.md), treatment-plans domain (TP-01 through TP-10), infra/multi-tenancy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT (portal JWT contains tenant_id claim)
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient sees only their own treatment plans — query always filtered by patient_id from JWT sub claim.

---

## Endpoint

```
GET /api/v1/portal/treatment-plans
```

**Rate Limiting:**
- 30 requests per minute per patient

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| status | No | string | enum: active, completed, draft, cancelled, all; default: active | Filter plans by status | active |
| cursor | No | string | Opaque cursor from previous response | Pagination cursor | eyJpZCI6... |
| limit | No | integer | 1-100; default: 20 | Results per page | 20 |

### Request Body Schema

None. GET request.

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
      "title": "string — plan name/title",
      "status": "string — enum: draft, active, completed, cancelled",
      "created_at": "string (ISO 8601 datetime)",
      "approved_at": "string (ISO 8601 datetime) | null",
      "completed_at": "string (ISO 8601 datetime) | null",
      "doctor": {
        "id": "uuid",
        "name": "string"
      },
      "progress": {
        "total_items": "integer",
        "completed_items": "integer",
        "percentage": "integer — 0-100"
      },
      "financial_summary": {
        "total_cost": "number (decimal) — total plan cost in COP",
        "discount_amount": "number (decimal)",
        "insurance_coverage": "number (decimal)",
        "patient_responsibility": "number (decimal) — after discounts and insurance",
        "amount_paid": "number (decimal)",
        "amount_pending": "number (decimal)"
      },
      "requires_patient_approval": "boolean",
      "patient_approved": "boolean",
      "items": [
        {
          "id": "uuid",
          "procedure_name": "string",
          "tooth_numbers": "string[] — e.g. ['11', '12']",
          "quantity": "integer",
          "unit_price": "number (decimal)",
          "total_price": "number (decimal)",
          "status": "string — enum: pending, in_progress, completed, cancelled",
          "scheduled_at": "string (ISO 8601 date) | null",
          "notes_for_patient": "string | null"
        }
      ]
    }
  ],
  "pagination": {
    "cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  }
}
```

**Example:**
```json
{
  "items": [
    {
      "id": "c3d4e5f6-a1b2-7890-abcd-ef1234567890",
      "title": "Plan de Tratamiento Integral",
      "status": "active",
      "created_at": "2026-01-15T09:00:00Z",
      "approved_at": "2026-01-17T14:30:00Z",
      "completed_at": null,
      "doctor": {
        "id": "d1e2f3a4-b5c6-7890-abcd-123456789012",
        "name": "Dr. Juan Martinez"
      },
      "progress": {
        "total_items": 5,
        "completed_items": 2,
        "percentage": 40
      },
      "financial_summary": {
        "total_cost": 1200000.00,
        "discount_amount": 120000.00,
        "insurance_coverage": 0.00,
        "patient_responsibility": 1080000.00,
        "amount_paid": 400000.00,
        "amount_pending": 680000.00
      },
      "requires_patient_approval": true,
      "patient_approved": true,
      "items": [
        {
          "id": "e5f6a7b8-c9d0-1234-abcd-567890123456",
          "procedure_name": "Extraccion simple",
          "tooth_numbers": ["38"],
          "quantity": 1,
          "unit_price": 150000.00,
          "total_price": 150000.00,
          "status": "completed",
          "scheduled_at": "2026-01-22",
          "notes_for_patient": "Extraccion realizada sin complicaciones."
        },
        {
          "id": "f6a7b8c9-d0e1-2345-bcde-678901234567",
          "procedure_name": "Endodoncia unirradicular",
          "tooth_numbers": ["21"],
          "quantity": 1,
          "unit_price": 350000.00,
          "total_price": 350000.00,
          "status": "in_progress",
          "scheduled_at": "2026-03-10",
          "notes_for_patient": null
        }
      ]
    }
  ],
  "pagination": {
    "cursor": null,
    "has_more": false,
    "total_count": 1
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta no validos.",
  "details": {
    "status": ["Estado no valido. Opciones: active, completed, draft, cancelled, all."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal" or role is not "patient".

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id from sub claim.
2. Validate query parameters against Pydantic schema.
3. Resolve tenant schema; set `search_path`.
4. Build base query: `SELECT ... FROM treatment_plans WHERE patient_id = :patient_id`.
5. Apply status filter (default: active). If status=active, include plans with status IN ('active').
6. Exclude `draft` plans from patient view unless explicitly requested with status=draft — draft plans are not yet presented to the patient.
7. Apply cursor-based pagination on `(created_at DESC, id DESC)`.
8. For each plan, JOIN treatment_plan_items to fetch items; JOIN users for doctor name.
9. Compute progress: `total_items` = COUNT(items), `completed_items` = COUNT(items WHERE status='completed'). `percentage` = round(completed/total * 100).
10. Compute financial_summary from treatment_plan_items and associated invoices/payments.
11. Filter item-level `notes_for_patient` field — do NOT include internal staff notes on items.
12. Build pagination cursor.
13. Cache result.
14. Return 200.

**Excluded Fields (never returned to patient):**
- Internal staff notes on treatment plan or items
- `created_by` user references (staff IDs)
- Diagnostic codes (ICD/CIE-10) — clinical data not shown in portal
- Internal discount justifications
- Cost breakdown beyond patient responsibility

**Business Rules:**

- Draft treatment plans are hidden by default (not yet presented to patient); patient must explicitly request status=draft (unusual case, typically draft=not visible).
- Plans requiring patient approval show `requires_patient_approval=true` and `patient_approved=false` until PP-05 is used.
- Completed percentage rounded to nearest integer (not floating point).
- `patient_responsibility` = total_cost - discount_amount - insurance_coverage.
- `amount_pending` = patient_responsibility - amount_paid.
- Financial amounts in COP (Colombian Pesos) by default; currency ISO code not shown (implied by tenant locale).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Plan with zero items | progress.total_items=0, percentage=0 |
| All items completed but plan not marked completed | progress.percentage=100, status still shows actual plan status |
| Treatment plan with no discount | discount_amount=0.00, insurance_coverage=0.00 |
| Plan not yet approved by patient | patient_approved=false, requires_patient_approval=true |
| Doctor deactivated | Show doctor name as stored; no error |

---

## Side Effects

### Database Changes

None. Read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:treatment_plans:{status}:{cursor}:{limit}`: SET — cached results, TTL 3 minutes

**Cache TTL:** 3 minutes

**Cache invalidation triggers:**
- Treatment plan created, updated, approved, or completed for this patient
- Treatment plan item status changed
- Payment recorded against this patient's plan

### Queue Jobs (RabbitMQ)

None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** treatment_plan
- **PHI involved:** Yes (treatment plans contain clinical and financial PHI)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms (with cache hit)
- **Maximum acceptable:** < 350ms (cache miss, with items JOIN)

### Caching Strategy
- **Strategy:** Redis cache, patient-namespaced, per-filter combination
- **Cache key:** `tenant:{tenant_id}:portal:patient:{patient_id}:treatment_plans:{status}:{cursor_hash}:{limit}`
- **TTL:** 3 minutes
- **Invalidation:** On any change to patient's treatment plans or items

### Database Performance

**Queries executed:** 2-3 (plans list with doctor JOIN; items per plan via IN query; financial aggregate)

**Indexes required:**
- `treatment_plans.(patient_id, status, created_at)` — COMPOSITE INDEX
- `treatment_plan_items.treatment_plan_id` — INDEX (for items JOIN)
- `treatment_plan_items.status` — INDEX (for progress computation)
- `invoices.(patient_id, treatment_plan_id)` — COMPOSITE INDEX (for financial aggregate)

**N+1 prevention:** Items fetched with WHERE treatment_plan_id IN (:plan_ids) batch query; financial data aggregated in single GROUP BY query.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on created_at + id)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| status | Pydantic Literal enum | Strict allowlist |
| cursor | Base64 decode + datetime/UUID validation | Malformed cursor returns 400 |
| limit | Pydantic int ge=1, le=100 | Bounded integer |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. patient_id from validated JWT sub claim.

### XSS Prevention

**Output encoding:** All string outputs escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** procedure_name, tooth_numbers, financial amounts, doctor name

**Audit requirement:** Access logged (PHI read by patient, logged per Resolución 1888)

---

## Testing

### Test Cases

#### Happy Path
1. Patient fetches active treatment plans
   - **Given:** Patient with 1 active plan containing 5 items, 2 completed
   - **When:** GET /api/v1/portal/treatment-plans
   - **Then:** 200 OK, plan returned with progress.percentage=40, all items listed

2. Patient fetches completed plans
   - **Given:** Patient with 2 completed historical plans
   - **When:** GET /api/v1/portal/treatment-plans?status=completed
   - **Then:** 200 OK, 2 completed plans, all items with status=completed

3. Financial summary correct
   - **Given:** Plan: total=1,200,000, discount=120,000, paid=400,000
   - **When:** GET /api/v1/portal/treatment-plans
   - **Then:** patient_responsibility=1,080,000; amount_pending=680,000

4. Pagination of plans
   - **Given:** Patient with 25 plans (status=all)
   - **When:** GET with limit=20
   - **Then:** 20 items, has_more=true, cursor set; next call returns 5 items

#### Edge Cases
1. Draft plan not visible by default
   - **Given:** Plan in draft status
   - **When:** GET /api/v1/portal/treatment-plans (default status=active)
   - **Then:** Draft plan not in response

2. Plan with zero items
   - **Given:** Plan created with no items yet
   - **When:** GET /api/v1/portal/treatment-plans
   - **Then:** progress.total_items=0, percentage=0, items=[]

3. All items completed but plan status=active
   - **Given:** 3/3 items completed, plan still in active state
   - **When:** GET /api/v1/portal/treatment-plans
   - **Then:** percentage=100, status="active" (not auto-changed to completed)

#### Error Cases
1. Invalid status parameter
   - **Given:** Patient authenticated
   - **When:** GET /api/v1/portal/treatment-plans?status=pending
   - **Then:** 400 Bad Request with validation error

2. Staff token used
   - **Given:** Doctor JWT (scope=staff)
   - **When:** GET /api/v1/portal/treatment-plans
   - **Then:** 403 Forbidden

3. Internal notes not exposed
   - **Given:** Treatment plan item has internal notes="Paciente dificil"
   - **When:** GET /api/v1/portal/treatment-plans
   - **Then:** notes_for_patient field absent or null; internal notes never returned

### Test Data Requirements

**Users:** Patient with portal_access=true, 2+ treatment plans with various statuses and item states.

**Patients/Entities:** Plans with items in various statuses; invoices/payments for financial summary tests; doctor records.

### Mocking Strategy

- Redis: fakeredis
- asyncio.gather: verify parallel queries (items batch + financial aggregate)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient sees only their own treatment plans (query-level enforcement)
- [ ] Draft plans hidden by default; visible only with explicit status=draft filter
- [ ] Progress percentage computed correctly
- [ ] Financial summary (total, discount, insurance, responsibility, paid, pending) accurate
- [ ] Items listed per plan with tooth numbers and status
- [ ] Internal staff notes never exposed; only notes_for_patient shown
- [ ] Cursor-based pagination works correctly
- [ ] PHI access audit logged
- [ ] Cache with 3-minute TTL works; invalidated on plan changes
- [ ] Staff JWT returns 403
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms cache hit, < 350ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Approving a treatment plan (see PP-05 portal-treatment-plan-approve.md)
- Creating or editing treatment plans (clinic staff only — TP-01 through TP-10)
- Treatment plan PDF download (see PP-07 portal-documents.md)
- Diagnostic codes or clinical justification details
- Price negotiation from portal (future enhancement)

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
- [x] Auth level stated (patient portal scope)
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for PHI read

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant+patient namespaced)
- [x] DB queries optimized (composite indexes, batch items query)
- [x] Pagination applied (cursor-based)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

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
