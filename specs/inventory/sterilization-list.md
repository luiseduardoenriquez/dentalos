# INV-06 List Sterilization Records Spec

---

## Overview

**Feature:** Retrieve sterilization cycle records for the clinic. Supports filtering by date range, autoclave ID, load number, and responsible user. Paginated. Includes a PDF export mode: when `Accept: application/pdf` header is provided, returns a formatted audit PDF suitable for regulatory inspections. This endpoint supports Colombia's healthcare regulatory compliance requirements.

**Domain:** inventory

**Priority:** Low

**Dependencies:** INV-05 (sterilization-create.md), infra/authentication-rules.md, infra/caching.md, PDF generation library (WeasyPrint or ReportLab)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner and assistant can view sterilization records. Doctors and receptionists cannot access sterilization data.

---

## Endpoint

```
GET /api/v1/inventory/sterilization
```

**PDF Export Mode:**
```
GET /api/v1/inventory/sterilization
Accept: application/pdf
```

**Rate Limiting:**
- Inherits global rate limit (100 requests per minute per user)
- PDF generation is rate-limited additionally: 5 PDF exports per minute per user (WeasyPrint is CPU-intensive)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |
| Accept | No | string | application/json (default) or application/pdf for PDF export | application/pdf |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| date_from | No | string | ISO 8601 date | Start of date range (inclusive) | 2026-01-01 |
| date_to | No | string | ISO 8601 date, >= date_from | End of date range (inclusive) | 2026-02-28 |
| autoclave_id | No | string | Max 100 chars | Filter by autoclave identifier | AUTOCLAVE-01 |
| load_number | No | string | Max 50 chars | Filter by specific load number | 2026-02-25-003 |
| responsible_user_id | No | UUID | Valid UUID v4 | Filter by user who performed sterilization | usr-assistant-0001 |
| is_compliant | No | boolean | true or false | Filter by compliance status | false |
| cursor | No | string | Opaque base64 cursor | Pagination cursor | eyJpZCI6Ii4uLiJ9 |
| limit | No | integer | Min 1, max 100, default 20 | Page size (JSON only; PDF exports all matching records) | 20 |

### Request Body Schema

None — GET request.

---

## Response

### Success Response (JSON)

**Status:** 200 OK

**Schema:**
```json
{
  "records": [
    {
      "id": "uuid",
      "autoclave_id": "string",
      "load_number": "string",
      "date": "string ISO 8601 date",
      "temperature_celsius": "number",
      "duration_minutes": "integer",
      "biological_indicator": "string — positive | negative",
      "chemical_indicator": "string — pass | fail",
      "is_compliant": "boolean",
      "instrument_count": "integer — number of instruments in this cycle",
      "responsible_user": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string",
        "role": "string"
      },
      "notes": "string | null",
      "created_at": "string ISO 8601",
      "created_by": "uuid"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  },
  "summary": {
    "total_cycles": "integer — in filtered period",
    "compliant_cycles": "integer",
    "non_compliant_cycles": "integer"
  }
}
```

**Example:**
```json
{
  "records": [
    {
      "id": "ster-aaaa-1111-bbbb-2222-cccc33334444",
      "autoclave_id": "AUTOCLAVE-01",
      "load_number": "2026-02-25-003",
      "date": "2026-02-25",
      "temperature_celsius": 134,
      "duration_minutes": 18,
      "biological_indicator": "negative",
      "chemical_indicator": "pass",
      "is_compliant": true,
      "instrument_count": 3,
      "responsible_user": {
        "id": "usr-assistant-0001-000000000000",
        "first_name": "Ana",
        "last_name": "Jimenez",
        "role": "assistant"
      },
      "notes": "Ciclo de rutina.",
      "created_at": "2026-02-25T17:00:00-05:00",
      "created_by": "usr-clinic-owner-0001-000000000000"
    }
  ],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "total_count": 1
  },
  "summary": {
    "total_cycles": 45,
    "compliant_cycles": 44,
    "non_compliant_cycles": 1
  }
}
```

### Success Response (PDF)

**Status:** 200 OK

**Headers:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="esterilizacion_{tenant_slug}_{date_from}_{date_to}.pdf"
```

**Body:** Binary PDF content. The PDF contains:
- Clinic header (name, NIT, address)
- Report title: "Registro de Ciclos de Esterilizacion"
- Period: date_from to date_to
- Summary table: total cycles, compliant, non-compliant
- Detailed table per cycle: all fields from the JSON response plus instrument names
- Footer: generation timestamp and "Generado por DentalOS"
- Signature column (reference to signature hash, not the image itself)

### Error Responses

#### 400 Bad Request
**When:** `date_from > date_to`.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "La fecha de inicio no puede ser posterior a la fecha de fin.",
  "details": { "date_from": ["date_from debe ser anterior o igual a date_to."] }
}
```

#### 401 Unauthorized
**When:** JWT missing or invalid. Standard auth failure.

#### 403 Forbidden
**When:** Doctor, receptionist, or patient role.

#### 422 Unprocessable Entity
**When:** Invalid date format, invalid UUID for responsible_user_id.

#### 429 Too Many Requests
**When:** Rate limit exceeded (or PDF export limit exceeded).

#### 500 Internal Server Error
**When:** Unexpected database failure or PDF generation failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`. If not `clinic_owner` or `assistant`, return 403.
2. Check `Accept` header:
   - If `Accept: application/pdf`: enter PDF export mode (no pagination, all matching records).
   - Otherwise: JSON mode with cursor pagination.
3. Validate query parameters: date format, date range order, UUID formats.
4. Set `search_path` to tenant schema.
5. Build query:
   ```sql
   SELECT sr.*, u.first_name, u.last_name, u.role AS u_role,
     (SELECT COUNT(*) FROM sterilization_record_instruments sri WHERE sri.sterilization_record_id = sr.id) AS instrument_count
   FROM sterilization_records sr
   JOIN users u ON u.id = sr.responsible_user_id
   WHERE sr.tenant_id = :tenant_id
   ```
   Apply filters:
   - `date_from`: `AND sr.date >= :date_from`
   - `date_to`: `AND sr.date <= :date_to`
   - `autoclave_id`: `AND sr.autoclave_id = :autoclave_id`
   - `load_number`: `AND sr.load_number = :load_number`
   - `responsible_user_id`: `AND sr.responsible_user_id = :responsible_user_id`
   - `is_compliant`: `AND sr.is_compliant = :is_compliant`
   - ORDER BY `sr.date DESC, sr.created_at DESC, sr.id DESC`
6. For JSON mode: apply cursor keyset pagination. LIMIT `:limit + 1`.
7. For PDF mode: no limit; load all matching records. Also load instrument names per record (`sterilization_record_instruments JOIN inventory_items`).
8. Run summary count query: `SELECT COUNT(*), SUM(CASE WHEN is_compliant THEN 1 ELSE 0 END) FROM sterilization_records WHERE tenant_id = :tenant_id [+ date filters]`.
9. For JSON: build paginated response.
10. For PDF:
    a. Render PDF using WeasyPrint or ReportLab with clinic header from tenant settings.
    b. Return binary PDF with appropriate headers.
    c. Rate check: PDF export limit (5/min per user).
11. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| date_from | ISO 8601 date format (if provided) | Formato de fecha invalido. |
| date_to | ISO 8601 date format, >= date_from (if provided) | La fecha de fin debe ser posterior a la fecha de inicio. |
| autoclave_id | Max 100 chars (if provided) | ID de autoclave invalido. |
| load_number | Max 50 chars (if provided) | Numero de carga invalido. |
| responsible_user_id | Valid UUID v4 (if provided) | ID de usuario invalido. |
| limit | Integer 1-100 (if provided) | El limite debe estar entre 1 y 100. |

**Business Rules:**

- Sterilization records are immutable — this endpoint is read-only.
- The PDF export bypasses cursor pagination and returns all matching records. This is intentional for regulatory audit use where a complete printable record is needed.
- For PDF exports, the `limit` parameter is ignored.
- The `summary` block in the JSON response reflects the total counts for the applied filters (not the full history). This helps staff see at a glance how many non-compliant cycles occurred in the selected period.
- Non-compliant cycles (`is_compliant=false`) are highlighted in red in the PDF output.
- The PDF export does not include the signature images — only the SHA-256 hash reference is included. This is by design: the PDF is for operational review; forensic signature verification is a separate process.
- If no filters are applied, the date range defaults to the last 30 days for JSON mode and the last 90 days for PDF mode (to prevent accidental large exports).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No records in period | records: [], total_count: 0, summary all zeros |
| PDF with 0 records | Valid empty PDF with header and "No se encontraron registros en este periodo" |
| date_from and date_to not provided | JSON: last 30 days; PDF: last 90 days |
| is_compliant=false filter | Returns only non-compliant cycles |
| Filtering by load_number that does not exist | records: [], total_count: 0 |

---

## Side Effects

### Database Changes

**No write operations** — read-only endpoint.

### Cache Operations

**Cache keys affected:** None — sterilization records are immutable; caching adds complexity without benefit. JSON responses are not cached.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes (for PDF export)

- **Action:** export
- **Resource:** sterilization_records
- **PHI involved:** No
- **Regulatory flag:** Yes — export of regulatory records is tracked

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (JSON, cache miss, small result set)
- **Target:** < 2000ms (PDF generation for up to 500 records)
- **Maximum acceptable:** < 5000ms (PDF generation for large result sets)

### Caching Strategy
- **Strategy:** No caching (regulatory data must be current; immutability means no cache invalidation complexity needed)
- **Cache key:** N/A

### Database Performance

**Queries executed:** 2-3 (main records query with responsible_user JOIN, instrument_count subquery, summary count)

**Indexes required:**
- `sterilization_records.(tenant_id, date DESC, created_at DESC, id DESC)` — COMPOSITE INDEX for default sort + pagination
- `sterilization_records.(tenant_id, autoclave_id)` — INDEX for autoclave filter
- `sterilization_records.(tenant_id, responsible_user_id)` — INDEX for user filter
- `sterilization_records.(tenant_id, is_compliant)` — INDEX for compliance filter
- `sterilization_record_instruments.sterilization_record_id` — INDEX

**N+1 prevention:** `instrument_count` is a correlated subquery on the main query (acceptable for list; count is the only sub-query). For PDF export, instrument names are loaded in a single batch JOIN query after the main query.

### Pagination

**Pagination:** Yes (JSON mode)
- **Style:** Cursor-based (keyset on `(date DESC, created_at DESC, id DESC)`)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| date_from, date_to | Pydantic date | Strict ISO 8601 |
| autoclave_id | Pydantic strip(), max_length=100 | Used in exact match, parameterized |
| load_number | Pydantic strip(), max_length=50 | |
| responsible_user_id | Pydantic UUID | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. PDF content sanitized at generation time.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — sterilization data is operational/regulatory.

**Audit requirement:** PDF exports logged with regulatory flag.

---

## Testing

### Test Cases

#### Happy Path
1. List records in date range (JSON)
   - **Given:** Authenticated clinic_owner, 45 records in 2026, 1 non-compliant
   - **When:** GET with date_from=2026-01-01&date_to=2026-02-28
   - **Then:** 200 OK, paginated records, summary shows 44 compliant, 1 non-compliant

2. Filter by autoclave_id
   - **Given:** Records for AUTOCLAVE-01 and AUTOCLAVE-02
   - **When:** GET with autoclave_id=AUTOCLAVE-01
   - **Then:** Only AUTOCLAVE-01 records returned

3. Filter is_compliant=false
   - **Given:** 1 non-compliant record
   - **When:** GET with is_compliant=false
   - **Then:** That 1 record returned

4. PDF export
   - **Given:** Accept: application/pdf, date range with 15 records
   - **When:** GET with PDF Accept header
   - **Then:** 200 OK, Content-Type: application/pdf, Content-Disposition with filename, binary PDF content

5. PDF with no matching records
   - **Given:** Accept: application/pdf, date range with no records
   - **When:** GET
   - **Then:** 200 OK, valid empty PDF with "no records" message

#### Error Cases
1. date_from after date_to
   - **Given:** date_from=2026-03-01, date_to=2026-01-01
   - **When:** GET
   - **Then:** 400 Bad Request

2. Doctor role
   - **Given:** Authenticated doctor
   - **When:** GET
   - **Then:** 403 Forbidden

3. PDF rate limit exceeded (6th PDF in a minute)
   - **Given:** User already made 5 PDF exports this minute
   - **When:** 6th GET with Accept: application/pdf
   - **Then:** 429 Too Many Requests

### Test Data Requirements

**Users:** clinic_owner, assistant, doctor (403)

**Sterilization Records:** 45 records spread across 2 months; 1 non-compliant; records for 2 different autoclave IDs; records for 2 different responsible users

### Mocking Strategy

- Database: SQLite in-memory; seed sterilization_records and sterilization_record_instruments
- PDF generation: Mock PDF library in unit tests; use integration test for actual PDF output validation (check Content-Type header and non-empty response body)
- Redis: `fakeredis` for PDF rate limit

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns paginated JSON list of sterilization records
- [ ] date_from, date_to, autoclave_id, load_number, responsible_user_id, is_compliant filters work
- [ ] summary counts accurate for applied filters
- [ ] GET with Accept: application/pdf returns binary PDF with correct headers
- [ ] PDF includes all matching records (no pagination limit)
- [ ] PDF includes clinic header and report title
- [ ] PDF export audit logged with regulatory flag
- [ ] Default date range applied when no dates specified (30 days JSON, 90 days PDF)
- [ ] Only clinic_owner and assistant can access (403 for others)
- [ ] PDF rate limit: 5 exports per minute per user
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms JSON, < 2000ms PDF)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating sterilization records (see INV-05)
- Modifying or deleting records (immutable)
- Sterilization schedule/planning
- Electronic submission to health authorities
- Autoclave certification management

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (6 filter params + Accept header)
- [x] All outputs defined (JSON + PDF)
- [x] PDF format documented
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed (audit for PDF)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Immutable records (read-only endpoint)
- [x] PDF generation library choice noted
- [x] Tenant isolation

### Hook 3: Security & Privacy
- [x] PDF export audit logged (regulatory flag)
- [x] No PHI in sterilization data
- [x] PDF rate limited (CPU-intensive operation)

### Hook 4: Performance & Scalability
- [x] Response time targets (JSON vs PDF)
- [x] No caching for regulatory data
- [x] Composite indexes for all filter combinations

### Hook 5: Observability
- [x] PDF export audit log
- [x] Structured logging (filters applied, result_count)
- [x] Error tracking compatible

### Hook 6: Testability
- [x] Test cases enumerated
- [x] PDF mock strategy documented
- [x] PDF rate limit test case
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
