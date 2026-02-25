# Consent List Spec

---

## Overview

**Feature:** List all informed consent forms for a specific patient, with filtering by status and date range. Returns summary-level data (not full rendered content). Used by the patient history view and the pre-procedure checklist.

**Domain:** consents

**Priority:** High

**Dependencies:** IC-04 (consent-create.md), IC-06 (consent-get.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, patient (own consents only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients can only list their own consents via the patient portal.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/consents
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
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient whose consents to list | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| status | No | string | enum: draft, pending_signatures, signed, voided | Filter by consent status | signed |
| template_id | No | string (UUID) | Valid UUID v4 | Filter by template used | a1b2c3d4-... |
| date_from | No | string | ISO 8601 date (YYYY-MM-DD) | Filter consents created on or after this date | 2026-01-01 |
| date_to | No | string | ISO 8601 date (YYYY-MM-DD) | Filter consents created on or before this date | 2026-02-24 |
| page | No | integer | min: 1, default: 1 | Page number | 1 |
| page_size | No | integer | min: 1, max: 50, default: 20 | Items per page | 20 |

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
      "template_id": "uuid",
      "template_name": "string",
      "procedure_description": "string",
      "tooth_numbers": "integer[]",
      "scheduled_date": "string (ISO 8601 date) | null",
      "status": "string (draft | pending_signatures | signed | voided)",
      "signatures_count": "integer",
      "pending_signatures": "string[]",
      "pdf_url": "string | null",
      "created_by": "uuid",
      "created_at": "string (ISO 8601 datetime)"
    }
  ],
  "total": "integer",
  "page": "integer",
  "page_size": "integer",
  "total_pages": "integer"
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "c3d4e5f6-0000-4000-8000-000000000030",
      "template_id": "a1b2c3d4-0000-4000-8000-000000000001",
      "template_name": "Consentimiento General Odontologico",
      "procedure_description": "Extraccion quirurgica de tercer molar inferior derecho impactado",
      "tooth_numbers": [48],
      "scheduled_date": "2026-03-15",
      "status": "signed",
      "signatures_count": 2,
      "pending_signatures": [],
      "pdf_url": "/api/v1/patients/f47ac10b-58cc-4372-a567-0e02b2c3d479/consents/c3d4e5f6-0000-4000-8000-000000000030/pdf",
      "created_by": "d4e5f6a7-0000-4000-8000-000000000004",
      "created_at": "2026-02-24T14:15:00Z"
    },
    {
      "id": "d4e5f6a7-0000-4000-8000-000000000031",
      "template_id": "b2c3d4e5-0000-4000-8000-000000000002",
      "template_name": "Consentimiento Implante Osseointegrado",
      "procedure_description": "Implante en sector posterior superior izquierdo",
      "tooth_numbers": [26],
      "scheduled_date": "2026-04-10",
      "status": "draft",
      "signatures_count": 0,
      "pending_signatures": ["patient", "doctor"],
      "pdf_url": null,
      "created_by": "d4e5f6a7-0000-4000-8000-000000000004",
      "created_at": "2026-02-20T09:00:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values (e.g., unrecognized status enum, invalid date format).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "status": ["Estado no valido. Opciones: draft, pending_signatures, signed, voided."],
    "date_from": ["Formato de fecha invalido. Use YYYY-MM-DD."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Patient attempting to list another patient's consents.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver los consentimientos de este paciente."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate path and query parameters against Pydantic schema.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role:
   - If `patient`: verify JWT sub matches portal_user_id of `patient_id`. Return 403 if mismatch.
   - If clinic staff: allow any patient in tenant.
4. Verify `patient_id` exists in tenant. Return 404 if not found.
5. Build cache key: `tenant:{tenant_id}:patients:{patient_id}:consents:list:{status}:{template_id}:{date_from}:{date_to}:{page}:{page_size}`.
6. Check Redis cache — return if hit.
7. Query `consents` table with applied filters, JOIN `digital_signatures` aggregated (COUNT, collected types).
8. Compute `pending_signatures` for each record from template required signatures minus collected types.
9. Set `pdf_url` for signed consents.
10. Apply pagination (offset-based).
11. Cache result with 3-minute TTL.
12. Write audit log entry for PHI access.
13. Return 200 with paginated list.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| status | One of: draft, pending_signatures, signed, voided (if provided) | Estado no valido. |
| template_id | Valid UUID v4 (if provided) | El identificador de plantilla no es valido. |
| date_from | Valid ISO 8601 date (if provided) | Formato de fecha invalido. Use YYYY-MM-DD. |
| date_to | Valid ISO 8601 date (if provided); must be >= date_from | La fecha final debe ser mayor o igual a la fecha inicial. |
| page | Integer >= 1 | El numero de pagina debe ser mayor a 0. |
| page_size | Integer 1–50 | El tamano de pagina debe estar entre 1 y 50. |

**Business Rules:**

- The list does NOT include `content_rendered` — only summary metadata. Full content is available via IC-06 (consent-get.md).
- Voided consents are included in results (they are a legal part of the patient record), but clearly marked with `status: voided`.
- `pdf_url` is only set for consents with `status: signed`.
- `pending_signatures` is derived from the consent's template configuration at query time (not stored separately).
- Consents are returned ordered by `created_at DESC` (most recent first) by default.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no consents | Return `data: []`, `total: 0`, no error |
| `date_from` without `date_to` | Apply only lower bound filter |
| `date_to` without `date_from` | Apply only upper bound filter |
| `page` beyond total results | Return `data: []` with correct `total` and `total_pages` |
| Filter by both `status` and `template_id` | Apply AND logic |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:{patient_id}:consents:list:*`: SET — populated on cache miss

**Cache TTL:** 3 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** consent_list
- **PHI involved:** Yes (procedure descriptions, patient context)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 80ms (cache hit)
- **Maximum acceptable:** < 300ms (cache miss with DB query)

### Caching Strategy
- **Strategy:** Redis cache per patient + filter combination
- **Cache key:** `tenant:{tenant_id}:patients:{patient_id}:consents:list:{filters_hash}`
- **TTL:** 3 minutes
- **Invalidation:** Invalidated when any consent for this patient is created, signed, or voided

### Database Performance

**Queries executed:** 2 (count query + data query with JOIN)

**Indexes required:**
- `{tenant}.consents.patient_id` — INDEX
- `{tenant}.consents.status` — INDEX
- `{tenant}.consents.template_id` — INDEX
- `{tenant}.consents.created_at` — INDEX (for ORDER BY and date filters)
- `{tenant}.digital_signatures.consent_id` — INDEX

**N+1 prevention:** Signature counts fetched via aggregate JOIN on consents query; no per-consent sub-queries.

### Pagination

**Pagination:** Yes
- **Style:** offset-based
- **Default page size:** 20
- **Max page size:** 50

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Reject malformed path params |
| status | Pydantic enum validator | Constrained to defined values |
| template_id | Pydantic UUID validator | Reject malformed params |
| date_from, date_to | Pydantic date validator | Strict ISO 8601 parsing |
| page, page_size | Pydantic int with min/max | Prevent negative or unreasonable pagination |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Pydantic serialization escapes all string fields on output.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** procedure_description (per consent)

**Audit requirement:** All access logged (PHI list access audited per request).

---

## Testing

### Test Cases

#### Happy Path
1. List all consents for a patient
   - **Given:** Authenticated doctor, patient with 3 consents (1 signed, 1 pending, 1 draft)
   - **When:** GET /api/v1/patients/{patient_id}/consents
   - **Then:** 200 OK, 3 items returned, correctly ordered by created_at DESC

2. Filter by status=signed
   - **Given:** Patient with mix of signed and draft consents
   - **When:** GET /api/v1/patients/{patient_id}/consents?status=signed
   - **Then:** 200 OK, only signed consents returned

3. Filter by date range
   - **Given:** Patient with consents from Jan 2026 and Feb 2026
   - **When:** GET /api/v1/patients/{patient_id}/consents?date_from=2026-02-01&date_to=2026-02-28
   - **Then:** 200 OK, only Feb 2026 consents returned

4. Patient lists own consents
   - **Given:** Patient with portal access
   - **When:** GET /api/v1/patients/{patient_id}/consents (patient JWT)
   - **Then:** 200 OK, own consents returned

5. Pagination
   - **Given:** Patient has 25 consents
   - **When:** GET /api/v1/patients/{patient_id}/consents?page=2&page_size=20
   - **Then:** 200 OK, 5 items in data, total=25, total_pages=2

#### Edge Cases
1. Patient with no consents
   - **Given:** Patient exists but has never had a consent created
   - **When:** GET /api/v1/patients/{patient_id}/consents
   - **Then:** 200 OK, `data: []`, `total: 0`

2. Filter beyond available pages
   - **Given:** Patient has 5 consents, page_size=20
   - **When:** GET ?page=3
   - **Then:** 200 OK, `data: []`, `total: 5`, `total_pages: 1`

#### Error Cases
1. Patient not found
   - **Given:** `patient_id` does not exist in tenant
   - **When:** GET /api/v1/patients/{nonexistent_id}/consents
   - **Then:** 404 Not Found

2. Patient accessing another patient's list
   - **Given:** Patient A's JWT, URL uses Patient B's patient_id
   - **When:** GET
   - **Then:** 403 Forbidden

3. Invalid status filter
   - **Given:** `status=unknown_status`
   - **When:** GET /api/v1/patients/{patient_id}/consents?status=unknown_status
   - **Then:** 400 Bad Request

4. Invalid date format
   - **Given:** `date_from=24/02/2026` (wrong format)
   - **When:** GET /api/v1/patients/{patient_id}/consents?date_from=24/02/2026
   - **Then:** 400 Bad Request

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (happy path); patient with portal access; patient without portal access (negative test)

**Patients/Entities:** Patient with consents in all four statuses; patient with no consents; patient with >20 consents for pagination test.

### Mocking Strategy

- Redis cache: Use fakeredis to test cache hit/miss and invalidation
- Audit log: Mock audit service; assert PHI=true

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Full consent list returned with correct pagination
- [ ] `status` filter correctly reduces result set
- [ ] `date_from` and `date_to` filters work independently and together
- [ ] `template_id` filter works
- [ ] `pending_signatures` correctly computed per consent
- [ ] `pdf_url` only set for signed consents
- [ ] Patient can only list their own consents (403 otherwise)
- [ ] Empty results return 200 (not 404)
- [ ] Voided consents included in results
- [ ] Audit log entry written per PHI list access
- [ ] Cache populated on first request; 3-minute TTL
- [ ] All test cases pass
- [ ] Performance target met (< 80ms cache hit, < 300ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Full consent content in list view (see IC-06 consent-get.md)
- Downloading PDF (see IC-08 consent-pdf.md)
- Listing consents across all patients (admin view — separate endpoint)
- Sorting options (default sort only: created_at DESC)

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
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (3-minute TTL)
- [x] DB queries optimized (indexes listed)
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
