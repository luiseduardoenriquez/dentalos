# CO-03 — RIPS List History Spec

## Overview

**Feature:** List the full RIPS generation history for the tenant. Returns paginated batches sorted by creation date, with per-batch summary metrics (period, status, file count, record count, error count). Supports filtering by period (month/year) and status. Designed to give clinic owners a compliance audit trail and quick access to prior submissions.

**Domain:** compliance

**Priority:** Low (Sprint 13-14)

**Dependencies:** CO-01 (rips-generate), CO-02 (rips-get), infra/caching.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only available for `country = "CO"` tenants. Returns empty list rather than 403 if no batches exist.

---

## Endpoint

```
GET /api/v1/compliance/rips
```

**Rate Limiting:**
- 30 requests per minute per tenant (list endpoints are heavier than single-item gets)
- Inherits global tenant rate limit as secondary limit

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| year | No | integer | 2020–current year | Filter by year | 2026 |
| month | No | integer | 1–12 | Filter by month (requires year) | 1 |
| status | No | string | queued, generating, generated, generated_with_errors, validated, submitted, rejected, failed | Filter by batch status | submitted |
| page | No | integer | >= 1, default=1 | Page number | 2 |
| page_size | No | integer | 1–50, default=12 | Results per page | 12 |
| sort | No | string | created_at_desc, created_at_asc, period_desc, period_asc — default=created_at_desc | Sort order | period_desc |

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "items": [
    {
      "batch_id": "string (UUID)",
      "period": "string — YYYY-MM",
      "period_year": "integer",
      "period_month": "integer",
      "period_display": "string — localized display, e.g. Enero 2026",
      "status": "string — enum",
      "status_display": "string — Spanish label for UI badge",
      "status_color": "string — green | yellow | red | gray (for UI badge color)",
      "file_count": "integer",
      "record_count": "integer",
      "error_count": "integer",
      "warning_count": "integer",
      "file_types_included": "array[string]",
      "generated_at": "string (ISO 8601) | null",
      "submitted_at": "string (ISO 8601) | null",
      "created_at": "string (ISO 8601)",
      "created_by_name": "string",
      "notes": "string | null",
      "has_errors": "boolean — true if error_count > 0",
      "detail_url": "string — API URL to fetch full detail via CO-02"
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
  "summary": {
    "total_batches": "integer",
    "total_submitted": "integer",
    "total_pending": "integer — queued + generating + generated + generated_with_errors",
    "latest_submitted_period": "string | null — YYYY-MM of last submitted batch",
    "compliance_gap": "boolean — true if current month's RIPS has not been submitted"
  }
}
```

**Example:**
```json
{
  "items": [
    {
      "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "period": "2026-01",
      "period_year": 2026,
      "period_month": 1,
      "period_display": "Enero 2026",
      "status": "submitted",
      "status_display": "Enviado",
      "status_color": "green",
      "file_count": 7,
      "record_count": 832,
      "error_count": 0,
      "warning_count": 3,
      "file_types_included": ["AF", "AC", "AP", "AT", "AM", "AN", "AU"],
      "generated_at": "2026-02-01T09:17:42Z",
      "submitted_at": "2026-02-05T14:30:00Z",
      "created_at": "2026-02-01T09:15:00Z",
      "created_by_name": "Dra. María Torres",
      "notes": "Generación mensual enero 2026",
      "has_errors": false,
      "detail_url": "/api/v1/compliance/rips/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    },
    {
      "batch_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "period": "2025-12",
      "period_year": 2025,
      "period_month": 12,
      "period_display": "Diciembre 2025",
      "status": "generated_with_errors",
      "status_display": "Con errores",
      "status_color": "yellow",
      "file_count": 7,
      "record_count": 910,
      "error_count": 22,
      "warning_count": 5,
      "file_types_included": ["AF", "AC", "AP", "AT", "AM", "AN", "AU"],
      "generated_at": "2026-01-03T10:05:11Z",
      "submitted_at": null,
      "created_at": "2026-01-03T10:00:00Z",
      "created_by_name": "Dra. María Torres",
      "notes": null,
      "has_errors": true,
      "detail_url": "/api/v1/compliance/rips/b2c3d4e5-f6a7-8901-bcde-f12345678901"
    }
  ],
  "pagination": {
    "total": 14,
    "page": 1,
    "page_size": 12,
    "total_pages": 2,
    "has_next": true,
    "has_previous": false
  },
  "summary": {
    "total_batches": 14,
    "total_submitted": 12,
    "total_pending": 2,
    "latest_submitted_period": "2026-01",
    "compliance_gap": false
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** `month` is provided without `year`; invalid sort value; month without year filter.

**Example:**
```json
{
  "error": "invalid_filter",
  "message": "month filter requires year to also be specified",
  "details": {
    "month": ["month parameter requires year parameter to be set"]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Caller does not have `clinic_owner` role, or tenant country is not Colombia.

#### 422 Unprocessable Entity
**When:** Query parameter types are invalid (e.g., `year=abc`, `page=-1`).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "year": ["value is not a valid integer"],
    "page": ["ensure this value is greater than or equal to 1"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database error or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Validate all query parameters via Pydantic query schema `RIPSListParams`.
2. Resolve tenant_id from JWT; verify `tenant.country == "CO"`.
3. Verify caller has `clinic_owner` role.
4. Validate filter combination: if `month` is present, `year` must also be present.
5. Attempt cache lookup: `tenant:{tenant_id}:rips:list:{cache_key}` where cache_key is hash of filter params.
6. On cache miss, execute paginated query:
   - Base filter: `tenant_id = current_tenant`
   - Optional filter: `period_year = year` if year provided
   - Optional filter: `period_month = month` if month provided
   - Optional filter: `status = status` if status provided
   - Apply sort order from `sort` parameter
   - Apply OFFSET/LIMIT pagination
7. Compute `summary` block: COUNT queries for total, submitted, and pending batches; determine latest_submitted_period; compute compliance_gap (is current month submitted?).
8. Map each batch row to response model: compute `period_display` (Spanish month name), `status_display` (Spanish label), `status_color` (for UI badge), `has_errors`, `detail_url`.
9. Cache assembled response for 120 seconds.
10. Write audit log: action=`rips_list_read`, resource=`rips_batch`, resource_id=null (list operation).
11. Return 200 with items, pagination, and summary.

**Status → Display mapping:**

| Status | status_display | status_color |
|--------|---------------|--------------|
| queued | En cola | gray |
| generating | Generando... | gray |
| generated | Generado | green |
| generated_with_errors | Con errores | yellow |
| validated | Validado | green |
| submitted | Enviado | green |
| rejected | Rechazado | red |
| failed | Falló | red |

**Compliance Gap Logic:**
- `compliance_gap = true` if the previous calendar month's RIPS has not been submitted (status != 'submitted') AND current date is after the 5th of the current month (grace period).
- Example: if today is 2026-02-25, check that 2026-01 batch has `status = 'submitted'`. If not, gap = true.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| year | Integer, 2020–current year | "Año fuera del rango permitido" |
| month | Integer, 1–12; only valid with year | "Mes requiere que se especifique el año" |
| status | Must be a valid RIPSBatchStatus value | "Estado no válido" |
| page | Integer >= 1 | "Página debe ser mayor o igual a 1" |
| page_size | Integer 1–50 | "Tamaño de página debe estar entre 1 y 50" |
| sort | Must be one of the allowed sort values | "Ordenamiento no válido" |

**Business Rules:**

- Multiple batches for the same period can exist (re-generation creates new batch; history is preserved). All appear in the list.
- The most recent batch per period is shown first when sorting by `period_desc`.
- `compliance_gap` is a helper field for the frontend dashboard compliance widget; it does not block any actions.
- `detail_url` is always the CO-02 endpoint URL for the batch.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No batches exist yet | Returns empty items[], pagination.total=0, summary fields all zero, compliance_gap=true if past grace period |
| Multiple batches for same period | All shown; frontend groups by period if desired |
| Filter by status=submitted returns zero results | Returns empty items[], pagination.total=0; no error |
| Year filter for a year with no batches | Returns empty items[] with pagination.total=0 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None — read-only endpoint

**Public schema tables affected:**
- `rips_batches`: SELECT (filtered, paginated, sorted)

**Example query (SQLAlchemy):**
```python
stmt = (
    select(RIPSBatch)
    .where(
        RIPSBatch.tenant_id == tenant_id,
        *optional_filters,
    )
    .order_by(sort_column)
    .offset((page - 1) * page_size)
    .limit(page_size)
)
results = await session.execute(stmt)
batches = results.scalars().all()

count_stmt = select(func.count()).select_from(
    select(RIPSBatch.id).where(
        RIPSBatch.tenant_id == tenant_id,
        *optional_filters
    ).subquery()
)
total = await session.scalar(count_stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:rips:list:{params_hash}`: SET on cache miss, INVALIDATE on new batch creation (CO-01)

**Cache TTL:** 120 seconds

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — read-only endpoint.

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** read
- **Resource:** rips_batch
- **PHI involved:** No (list metadata; no PHI in summary data)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (cache hit)
- **Maximum acceptable:** < 300ms (cache miss with index scan)

### Caching Strategy
- **Strategy:** Redis cache on assembled list response
- **Cache key:** `tenant:{tenant_id}:rips:list:{sha256(params)}`
- **TTL:** 120 seconds
- **Invalidation:** Invalidated by CO-01 (new batch created), CO-04 (batch status updated to validated)

### Database Performance

**Queries executed:** 3–4 (batch list, total count, summary counts, compliance gap check)

**Indexes required:**
- `rips_batches.(tenant_id, created_at DESC)` — COMPOSITE INDEX for default sort
- `rips_batches.(tenant_id, period_year, period_month)` — COMPOSITE INDEX for period filters
- `rips_batches.(tenant_id, status)` — COMPOSITE INDEX for status filter

**N+1 prevention:** No joins required; list response uses aggregated data only (no per-file loading for list view).

### Pagination

**Pagination:** Yes

- **Style:** offset-based
- **Default page size:** 12
- **Max page size:** 50

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| year | Pydantic integer validator, range 2020–current year | Prevents unbounded range |
| month | Pydantic integer validator, ge=1, le=12 | Range enforcement |
| status | Pydantic Literal enum | Only valid status strings |
| page | Pydantic integer, ge=1 | Positive integers only |
| page_size | Pydantic integer, ge=1, le=50 | Bounded to prevent oversized responses |
| sort | Pydantic Literal enum | Only allowed sort expressions |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Sort columns are from a hard-coded allowlist, never interpolated from user input.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API endpoints.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. List contains only batch metadata: periods, statuses, record counts. No patient names, identifiers, or clinical data exposed.

**Audit requirement:** List access logged (not per-record; one log entry per list request).

---

## Testing

### Test Cases

#### Happy Path
1. Default list (no filters)
   - **Given:** clinic_owner JWT, 14 batches in DB for the tenant
   - **When:** GET /api/v1/compliance/rips
   - **Then:** 200 OK, items has 12 (page_size default), pagination.total=14, pagination.has_next=true

2. Filter by year
   - **Given:** 5 batches for 2026, 9 for 2025
   - **When:** GET /api/v1/compliance/rips?year=2026
   - **Then:** 200 OK, items has 5, all with period starting "2026-"

3. Filter by year and month
   - **Given:** 2 batches for 2026-01 (re-generation)
   - **When:** GET /api/v1/compliance/rips?year=2026&month=1
   - **Then:** 200 OK, items has 2, both with period=2026-01

4. Filter by status=submitted
   - **Given:** 12 submitted, 2 with errors
   - **When:** GET /api/v1/compliance/rips?status=submitted
   - **Then:** 200 OK, all items have status=submitted

5. Sort by period_asc
   - **Given:** Multiple batches
   - **When:** GET /api/v1/compliance/rips?sort=period_asc
   - **Then:** 200 OK, items ordered from oldest period first

#### Edge Cases
1. No batches in DB
   - **Given:** New tenant, no RIPS generated yet
   - **When:** GET /api/v1/compliance/rips
   - **Then:** 200 OK, items=[], pagination.total=0, summary.compliance_gap=true

2. Month filter without year
   - **Given:** clinic_owner JWT
   - **When:** GET /api/v1/compliance/rips?month=1
   - **Then:** 400 Bad Request, "month filter requires year"

3. Page beyond total
   - **Given:** 5 batches, page_size=12
   - **When:** GET /api/v1/compliance/rips?page=3
   - **Then:** 200 OK, items=[], pagination reflects no results

#### Error Cases
1. Doctor attempts access
   - **Given:** doctor JWT
   - **When:** GET /api/v1/compliance/rips
   - **Then:** 403 Forbidden

2. Non-Colombian tenant
   - **Given:** clinic_owner JWT, tenant.country=MX
   - **When:** GET /api/v1/compliance/rips
   - **Then:** 403 Forbidden

3. Invalid year type
   - **Given:** clinic_owner JWT
   - **When:** GET /api/v1/compliance/rips?year=abc
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** clinic_owner for Colombian tenant (country=CO), doctor (for 403 test), clinic_owner for non-Colombian tenant

**Patients/Entities:** 14 rips_batch rows across different periods and statuses (some submitted, some with errors, some generating)

### Mocking Strategy

- Redis: Use fakeredis in unit tests
- Database: PostgreSQL test instance with seeded rips_batch fixtures

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns paginated list of batches with correct metadata
- [ ] Filter by year works correctly
- [ ] Filter by year+month works correctly
- [ ] Filter by status works correctly
- [ ] Default sort is created_at_desc (newest first)
- [ ] All sort options functional
- [ ] summary block computed correctly (total, submitted, pending, compliance_gap)
- [ ] status_display and status_color correctly map for all 8 statuses
- [ ] compliance_gap=true when previous month not submitted past grace period
- [ ] Empty list returns 200 (not 404)
- [ ] month without year returns 400
- [ ] Non-Colombian tenant gets 403
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms cached)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Downloading RIPS files (see CO-02)
- Generating new batches (see CO-01)
- Validating batches (see CO-04)
- Marking a batch as submitted (manual action in MinSalud portal; DentalOS tracks this via a separate PATCH endpoint not in this sprint)
- Deleting historic batches

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
