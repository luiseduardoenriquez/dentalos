# List Patients Spec

---

## Overview

**Feature:** Retrieve a paginated, filterable, and sortable list of patients for a tenant clinic. Returns minimal data suitable for table/list views. Supports full-text search across name, document number, and phone.

**Domain:** patients

**Priority:** Critical

**Dependencies:** P-01 (patient-create.md), I-02 (database-architecture.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** None. List access is not individually audit-logged (bulk PHI read is logged at a reduced rate; see infra/audit-logging.md).

---

## Endpoint

```
GET /api/v1/patients
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

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| page | No | integer | >= 1, default 1 | Page number | 1 |
| page_size | No | integer | 1-100, default 20 | Results per page | 20 |
| search | No | string | min 2 chars, max 100 | Full-text search on name + document + phone | Garcia |
| is_active | No | boolean | true/false | Filter by active status | true |
| created_from | No | string | ISO 8601 date | Filter by created_at >= date | 2026-01-01 |
| created_to | No | string | ISO 8601 date | Filter by created_at <= date | 2026-02-28 |
| doctor_id | No | uuid | Valid UUID v4 | Patients seen by this doctor (via appointments) | a1b2c3d4-... |
| has_balance | No | boolean | true/false | Filter patients with outstanding balance | true |
| insurance_provider | No | string | max 200 chars | Filter by insurance provider (exact match) | Sura EPS |
| sort_by | No | string | enum: last_name, created_at, last_visit_at | Sort field | last_name |
| sort_order | No | string | enum: asc, desc, default asc | Sort direction | asc |

### Request Body Schema

None (GET request).

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
      "first_name": "string",
      "last_name": "string",
      "full_name": "string",
      "document_type": "string",
      "document_number": "string",
      "phone": "string",
      "email": "string | null",
      "age": "integer",
      "last_visit_at": "string | null (ISO 8601 datetime)",
      "is_active": "boolean",
      "avatar_url": "string | null"
    }
  ],
  "pagination": {
    "page": "integer",
    "page_size": "integer",
    "total_count": "integer",
    "total_pages": "integer",
    "has_next": "boolean",
    "has_previous": "boolean"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "first_name": "Maria",
      "last_name": "Garcia Lopez",
      "full_name": "Maria Garcia Lopez",
      "document_type": "cedula",
      "document_number": "1020304050",
      "phone": "+573001234567",
      "email": "maria.garcia@email.com",
      "age": 35,
      "last_visit_at": "2026-02-10T10:00:00Z",
      "is_active": true,
      "avatar_url": null
    },
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "first_name": "Carlos",
      "last_name": "Hernandez",
      "full_name": "Carlos Hernandez",
      "document_type": "cedula",
      "document_number": "5060708090",
      "phone": "+573005551234",
      "email": null,
      "age": 42,
      "last_visit_at": null,
      "is_active": true,
      "avatar_url": null
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 157,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values (e.g., page < 1, invalid sort_by value).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta no validos.",
  "details": {
    "sort_by": ["Valor no valido. Opciones: last_name, created_at, last_visit_at."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure -- see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not in the allowed list.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para listar pacientes."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate query parameters against Pydantic schema.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (any staff role is allowed).
4. Build cache key from all query parameters: `tenant:{tenant_id}:patients:list:{hash(params)}`.
5. Check Redis cache. If hit, return cached response.
6. Build base SQL query: `SELECT id, first_name, last_name, document_type, document_number, phone, email, birthdate, last_visit_at, is_active, avatar_url FROM patients`.
7. Apply filters conditionally:
   - `is_active`: `WHERE is_active = :is_active`
   - `search`: `WHERE to_tsvector('spanish', ...) @@ websearch_to_tsquery('spanish', :search)`
   - `created_from / created_to`: `WHERE created_at >= :from AND created_at <= :to`
   - `doctor_id`: `WHERE id IN (SELECT DISTINCT patient_id FROM appointments WHERE doctor_id = :doctor_id)`
   - `has_balance`: `WHERE id IN (SELECT patient_id FROM invoices WHERE status IN ('sent', 'partial', 'overdue') GROUP BY patient_id HAVING SUM(total_cents - paid_cents) > 0)`
   - `insurance_provider`: `WHERE insurance_provider = :insurance_provider`
8. Apply sorting: ORDER BY the specified field + direction. Default: `last_name ASC`.
9. Execute COUNT query for total_count.
10. Apply OFFSET/LIMIT for pagination.
11. Calculate `age` for each patient from `birthdate`.
12. Build pagination metadata.
13. Store result in Redis cache with TTL 2 minutes.
14. Return 200 with data and pagination.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| page | Integer >= 1 | El numero de pagina debe ser mayor o igual a 1. |
| page_size | Integer 1-100 | El tamano de pagina debe estar entre 1 y 100. |
| search | 2-100 characters (if provided) | La busqueda requiere al menos 2 caracteres. |
| sort_by | One of: last_name, created_at, last_visit_at | Campo de ordenamiento no valido. |
| sort_order | One of: asc, desc | Direccion de ordenamiento no valida. |
| created_from, created_to | Valid ISO 8601 dates; from <= to | Rango de fechas no valido. |
| doctor_id | Valid UUID v4 (if provided) | Identificador de doctor no valido. |

**Business Rules:**

- Default filter: `is_active = true` when no `is_active` parameter is provided. To see all patients including deactivated, pass `is_active` explicitly or omit it to get active-only.
- The `search` parameter uses PostgreSQL `websearch_to_tsquery` for natural language-like search.
- The `doctor_id` filter finds patients who have had at least one appointment with the specified doctor (any status).
- The `has_balance` filter finds patients with at least one invoice where `total_cents - paid_cents > 0`.
- The response returns minimal data; use P-02 (patient-get) for full profile.
- `age` is calculated per row from `birthdate` at response time.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No patients match filters | Return empty data array with total_count = 0 |
| page exceeds total_pages | Return empty data array (not an error) |
| search term matches document_number partially | Full-text search may not match partial numbers; use P-06 (patient-search) for typeahead |
| Tenant has zero patients | Return empty data array with total_count = 0 |
| created_from = created_to (same day) | Filter for patients created on that day |
| doctor_id that does not exist | Return empty data array (no error) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:list:{hash(params)}`: SET -- cache list response

**Cache TTL:** 2 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No -- list endpoints are not individually audit-logged to avoid excessive log volume. Bulk PHI access is monitored via rate-based anomaly detection (see infra/audit-logging.md).

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms (cache hit), < 400ms (cache miss)
- **Maximum acceptable:** < 800ms

### Caching Strategy
- **Strategy:** Redis cache with query-parameter-based key
- **Cache key:** `tenant:{tenant_id}:patients:list:{md5(sorted_params)}`
- **TTL:** 2 minutes
- **Invalidation:** On patient create (P-01), patient update (P-04), patient deactivation (P-05)

### Database Performance

**Queries executed:** 2 on cache miss (1 COUNT, 1 paginated SELECT)

**Indexes required:**
- `patients.(lower(last_name), lower(first_name))` -- INDEX for name sorting (already defined)
- `patients.is_active` -- INDEX for active filter (already defined)
- `patients.created_at` -- INDEX for date range filter (already defined)
- `patients.phone` -- INDEX for search (already defined)
- `patients USING GIN (to_tsvector('spanish', ...))` -- GIN for full-text search (already defined)
- `appointments.doctor_id` -- INDEX for doctor_id filter (implicit via idx_appointments_doctor_time)
- `invoices.(patient_id, status)` -- INDEX for has_balance filter (already defined)

**N+1 prevention:** Single query returns all columns needed for the list view. No lazy-loaded relationships.

### Pagination

**Pagination:** Yes

**If Yes:**
- **Style:** offset-based
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| search | Pydantic strip + limit to 100 chars | Passed to websearch_to_tsquery (parameterized) |
| insurance_provider | Pydantic strip | Exact match filter |
| doctor_id | Pydantic UUID validator | Rejects non-UUID |
| created_from, created_to | Pydantic date validator | Rejects invalid dates |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. The `search` value is passed to `websearch_to_tsquery` as a bound parameter, never interpolated.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** first_name, last_name, document_number, phone, email (minimal subset)

**Audit requirement:** Not individually logged (rate-based monitoring for bulk PHI access)

---

## Testing

### Test Cases

#### Happy Path
1. List patients with default parameters
   - **Given:** Tenant with 50 active patients
   - **When:** GET /api/v1/patients
   - **Then:** 200 OK, 20 results (default page_size), total_count = 50, sorted by last_name ASC

2. Search by name
   - **Given:** Patient "Garcia Lopez" exists
   - **When:** GET /api/v1/patients?search=Garcia
   - **Then:** 200 OK, results include the matching patient

3. Filter by doctor_id
   - **Given:** Doctor has 10 patients via appointments
   - **When:** GET /api/v1/patients?doctor_id={uuid}
   - **Then:** 200 OK, exactly 10 results

4. Filter by has_balance
   - **Given:** 5 patients have outstanding balances
   - **When:** GET /api/v1/patients?has_balance=true
   - **Then:** 200 OK, exactly 5 results

5. Paginate through results
   - **Given:** 50 patients, page_size = 10
   - **When:** GET /api/v1/patients?page=3&page_size=10
   - **Then:** 200 OK, 10 results, page = 3, has_next = true, has_previous = true

#### Edge Cases
1. No matching patients
   - **Given:** search = "ZZZZZ" (no match)
   - **When:** GET /api/v1/patients?search=ZZZZZ
   - **Then:** 200 OK, data = [], total_count = 0

2. Page beyond total
   - **Given:** 50 patients, page_size = 20
   - **When:** GET /api/v1/patients?page=100
   - **Then:** 200 OK, data = [], has_next = false

3. Multiple filters combined
   - **Given:** Various patients
   - **When:** GET /api/v1/patients?is_active=true&has_balance=true&sort_by=last_visit_at&sort_order=desc
   - **Then:** 200 OK, results match all filters, sorted correctly

#### Error Cases
1. Invalid sort_by value
   - **Given:** sort_by = "invalid_field"
   - **When:** GET /api/v1/patients?sort_by=invalid_field
   - **Then:** 400 Bad Request

2. page_size exceeds max
   - **Given:** page_size = 500
   - **When:** GET /api/v1/patients?page_size=500
   - **Then:** 400 Bad Request (or clamp to 100 depending on policy)

3. Search too short
   - **Given:** search = "a"
   - **When:** GET /api/v1/patients?search=a
   - **Then:** 400 Bad Request with min length error

### Test Data Requirements

**Users:** One user per staff role

**Patients/Entities:** 50+ patients with varied names, active/inactive states, appointments with different doctors, invoices with balances. At least one patient per document_type.

### Mocking Strategy

- Redis cache: Use fakeredis; test both cache hit and miss
- Database: Test fixtures with known data distributions

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Paginated list returns correct data with default parameters
- [ ] Full-text search works across name, document, and phone
- [ ] All filters (is_active, date range, doctor_id, has_balance, insurance_provider) work correctly
- [ ] Sorting by last_name, created_at, last_visit_at works in both directions
- [ ] Pagination metadata is accurate (total_count, total_pages, has_next, has_previous)
- [ ] Response cached for 2 minutes with correct key
- [ ] Cache invalidated on patient create/update/deactivate
- [ ] Empty result sets handled gracefully
- [ ] All test cases pass
- [ ] Performance targets met (< 400ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Typeahead/autocomplete search (see P-06, patient-search.md)
- CSV/Excel export of patient list (separate endpoint)
- Patient list grouped by doctor or insurance provider (reporting domain)
- Advanced analytics on patient demographics (analytics domain)

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
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access (rate-based monitoring)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (rate-based)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A for read)

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
