# TP-03: List Treatment Plans Spec

---

## Overview

**Feature:** List all treatment plans for a given patient with filtering by status and date range. Returns a paginated summary view (not full item detail) for quick overview in the clinic dashboard and patient timeline.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** TP-01 (plan-create.md), P-01 (patient-create.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patient role may access this from the portal (see portal domain); only their own plans visible.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/treatment-plans
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | uuid | Valid UUID, must belong to tenant | Patient's unique identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| status | No | string | enum: draft, active, completed, cancelled | Filter by plan status | active |
| date_from | No | string | ISO 8601 date (YYYY-MM-DD) | Filter plans created on or after this date | 2026-01-01 |
| date_to | No | string | ISO 8601 date (YYYY-MM-DD) | Filter plans created on or before this date | 2026-12-31 |
| priority | No | string | enum: high, medium, low | Filter by plan priority | high |
| page | No | integer | min 1, default 1 | Page number | 1 |
| page_size | No | integer | min 1, max 50, default 20 | Items per page | 20 |
| sort_by | No | string | enum: created_at, updated_at, title, status; default: created_at | Sort field | created_at |
| sort_order | No | string | enum: asc, desc; default: desc | Sort direction | desc |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "string",
      "description": "string | null",
      "priority": "string (high | medium | low)",
      "status": "string (draft | active | completed | cancelled)",
      "items_count": "integer",
      "completed_count": "integer",
      "total_cost_estimated": "number (decimal)",
      "progress_pct": "number (0.0 - 100.0)",
      "approval_status": "string (pending_approval | approved | rejected)",
      "quotation_id": "uuid | null",
      "created_by_name": "string",
      "created_at": "string (ISO 8601 datetime)",
      "updated_at": "string (ISO 8601 datetime)"
    }
  ],
  "pagination": {
    "page": "integer",
    "page_size": "integer",
    "total_count": "integer",
    "total_pages": "integer",
    "has_next": "boolean",
    "has_prev": "boolean"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "title": "Plan de tratamiento integral 2026",
      "description": "Plan completo para restaurar sectores posteriores.",
      "priority": "high",
      "status": "active",
      "items_count": 5,
      "completed_count": 2,
      "total_cost_estimated": 1200000.00,
      "progress_pct": 40.0,
      "approval_status": "approved",
      "quotation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "created_by_name": "Dr. Carlos Ruiz",
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-02-10T14:30:00Z"
    },
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-012345678901",
      "title": "Plan endodontico diente 11",
      "description": null,
      "priority": "medium",
      "status": "draft",
      "items_count": 2,
      "completed_count": 0,
      "total_cost_estimated": 600000.00,
      "progress_pct": 0.0,
      "approval_status": "pending_approval",
      "quotation_id": null,
      "created_by_name": "Dr. Carlos Ruiz",
      "created_at": "2026-02-20T09:00:00Z",
      "updated_at": "2026-02-20T09:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 2,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values (invalid enum, invalid date format).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta no validos.",
  "details": {
    "status": ["Estado no valido. Opciones: draft, active, completed, cancelled."],
    "date_from": ["El formato de fecha no es valido. Use YYYY-MM-DD."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not in the allowed list.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para listar planes de tratamiento."
}
```

#### 404 Not Found
**When:** patient_id does not exist in the tenant.

**Example:**
```json
{
  "error": "patient_not_found",
  "message": "Paciente no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** date_from is after date_to, page_size exceeds max, etc.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "date_range": ["La fecha de inicio no puede ser posterior a la fecha de fin."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate all query parameters against Pydantic schema (enums, date formats, pagination bounds).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC.
4. Verify `patient_id` exists and belongs to the tenant.
5. Validate date range if both date_from and date_to provided (date_from must be <= date_to).
6. Build base query: `SELECT ... FROM treatment_plans WHERE patient_id = :patient_id`.
7. Apply optional filters: status, date_from (created_at >= date_from), date_to (created_at <= date_to), priority.
8. Apply sorting via `sort_by` and `sort_order`.
9. Execute count query for pagination metadata.
10. Execute paginated data query with `LIMIT page_size OFFSET (page - 1) * page_size`.
11. For each plan, `items_count` and `completed_count` are aggregated in a subquery or JOIN (not fetched individually).
12. `progress_pct` computed per plan as `(completed_count / NULLIF(items_count, 0)) * 100`, defaulting to 0.0.
13. `created_by_name` resolved via JOIN on users table.
14. Return 200 with data array and pagination object.
15. Write audit log entry (action: read, resource: treatment_plan_list, PHI: yes).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| status | Must be one of: draft, active, completed, cancelled | Estado no valido. |
| date_from | Valid ISO 8601 date (if provided) | Formato de fecha no valido. Use YYYY-MM-DD. |
| date_to | Valid ISO 8601 date (if provided), must be >= date_from | La fecha de fin debe ser posterior a la fecha de inicio. |
| priority | Must be one of: high, medium, low (if provided) | Prioridad no valida. |
| page | Integer >= 1 | El numero de pagina debe ser mayor a 0. |
| page_size | Integer 1-50 | El tamano de pagina debe ser entre 1 y 50. |
| sort_by | Must be one of: created_at, updated_at, title, status | Campo de ordenamiento no valido. |
| sort_order | Must be one of: asc, desc | Orden no valido. Opciones: asc, desc. |

**Business Rules:**

- Returns all plans regardless of status if no status filter provided (draft, active, completed, cancelled all included).
- Plans are scoped to the tenant (search_path) and to the specific patient_id — no cross-patient leakage possible.
- The `items` array (full item detail) is NOT returned in this endpoint — only summary counts. Use TP-02 (plan-get.md) for full detail.
- If date_from provided without date_to, filter applies from date_from to present.
- If date_to provided without date_from, filter applies from the beginning of records to date_to.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no plans | Returns empty data array, total_count = 0, 200 OK |
| page > total_pages | Returns empty data array, pagination reflects actual totals |
| No filters applied | Returns all plans for patient, most recent first |
| date_from = date_to | Filter returns plans created on that exact date |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plans:list:{hash_of_params}`: SET on response

**Cache TTL:** 120 seconds (2 minutes)

**Note:** List cache is invalidated broadly on any write to treatment_plans for this patient (TP-01, TP-04).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** treatment_plan_list
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms (cache hit)
- **Maximum acceptable:** < 400ms (cache miss with filters)

### Caching Strategy
- **Strategy:** Redis cache with parameter-hash key
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:treatment_plans:list:{sha256(query_params)}`
- **TTL:** 120 seconds
- **Invalidation:** On any create, update, or delete of a treatment_plan for this patient

### Database Performance

**Queries executed:** 2 (count query + data query with aggregated item counts)

**Indexes required:**
- `treatment_plans.(patient_id, status)` — INDEX (primary filter)
- `treatment_plans.(patient_id, created_at)` — INDEX (date range + sort)
- `treatment_plans.(patient_id, priority)` — INDEX (priority filter)
- `treatment_plan_items.(plan_id, status)` — INDEX (aggregation for counts)

**N+1 prevention:** Item counts aggregated in a single GROUP BY subquery or LEFT JOIN; no per-plan queries.

### Pagination

**Pagination:** Yes

**If Yes:**
- **Style:** Offset-based
- **Default page size:** 20
- **Max page size:** 50

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Path parameter |
| status | Pydantic Enum validator | Query parameter |
| date_from, date_to | Pydantic date validator | ISO 8601 only |
| sort_by | Pydantic Enum validator | Prevents SQL injection via ORDER BY |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. sort_by is validated against an enum before use in ORDER BY clause. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, plan titles/descriptions (may contain clinical information).

**Audit requirement:** All access logged.

---

## Testing

### Test Cases

#### Happy Path
1. List all plans, no filters
   - **Given:** Authenticated doctor, patient has 3 plans (1 draft, 1 active, 1 completed)
   - **When:** GET /api/v1/patients/{patient_id}/treatment-plans
   - **Then:** 200 OK, data array with 3 plans, pagination total_count = 3

2. Filter by status = active
   - **Given:** Patient has 3 plans (1 draft, 2 active)
   - **When:** GET with status=active
   - **Then:** 200 OK, data array with 2 plans, all status = active

3. Filter by date range
   - **Given:** Patient has 3 plans created on different dates
   - **When:** GET with date_from=2026-01-01&date_to=2026-01-31
   - **Then:** 200 OK, only plans created in January 2026 returned

4. Pagination works correctly
   - **Given:** Patient has 25 plans
   - **When:** GET with page=2&page_size=20
   - **Then:** 200 OK, data array with 5 plans, has_prev = true, has_next = false

#### Edge Cases
1. Patient has no plans
   - **Given:** Patient exists but has no treatment plans
   - **When:** GET request
   - **Then:** 200 OK, data = [], total_count = 0

2. page exceeds total pages
   - **Given:** 5 plans exist, page=99 requested
   - **When:** GET with page=99
   - **Then:** 200 OK, data = [], pagination reflects total_pages = 1

#### Error Cases
1. Invalid status filter
   - **Given:** status=urgente
   - **When:** GET request
   - **Then:** 400 Bad Request with validation error

2. date_from after date_to
   - **Given:** date_from=2026-12-01&date_to=2026-01-01
   - **When:** GET request
   - **Then:** 422 Unprocessable Entity

3. Patient not found
   - **Given:** Non-existent patient_id
   - **When:** GET request
   - **Then:** 404 Not Found

4. Receptionist role blocked
   - **Given:** User with patient role (not portal context)
   - **When:** GET request
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** doctor, clinic_owner, assistant, receptionist

**Patients/Entities:** Patient with 25+ plans across various statuses and dates. Patient with 0 plans.

### Mocking Strategy

- Redis cache: fakeredis for cache hit/miss tests
- Date filtering: Use fixed test dates in fixtures

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] All plans returned when no filters applied
- [ ] Status filter returns only plans with matching status
- [ ] Date range filter correctly scopes results
- [ ] Pagination returns correct page sizes and metadata
- [ ] Empty result returns 200 with empty data array (not 404)
- [ ] page > total_pages returns empty data, not error
- [ ] Patient not found returns 404
- [ ] Invalid enum query parameter returns 400
- [ ] item counts aggregated in single DB query (no N+1)
- [ ] Response cached for 2 minutes with tenant-namespaced key
- [ ] Audit log written for each list access
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms cached, < 400ms cold)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Full item detail per plan (see TP-02 plan-get.md)
- Listing plans across all patients (clinic-wide view — separate admin/analytics endpoint)
- Bulk plan operations

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
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM, enum-validated sort_by)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed, N+1 prevented)
- [x] Pagination applied (offset-based, max 50)

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
| 1.0 | 2026-02-24 | Initial spec |
