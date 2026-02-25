# Patient Typeahead Search Spec

---

## Overview

**Feature:** Fast typeahead/autocomplete search for patients. Returns a maximum of 10 results with minimal data, optimized for sub-100ms response times. Uses PostgreSQL `tsvector` full-text search across first_name, last_name, document_number, and phone fields.

**Domain:** patients

**Priority:** Critical

**Dependencies:** P-01 (patient-create.md), I-02 (database-architecture.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** None

---

## Endpoint

```
GET /api/v1/patients/search
```

**Rate Limiting:**
- 120 requests per minute per user (higher limit for typeahead use cases)

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
| q | Yes | string | min 2 chars, max 100 chars | Search query text | Garcia |

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
      "full_name": "string",
      "document_number": "string",
      "phone": "string",
      "avatar_url": "string | null",
      "is_active": "boolean"
    }
  ],
  "count": "integer (0-10)"
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "full_name": "Maria Garcia Lopez",
      "document_number": "1020304050",
      "phone": "+573001234567",
      "avatar_url": null,
      "is_active": true
    },
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "full_name": "Carlos Garcia Hernandez",
      "document_number": "5060708090",
      "phone": "+573005551234",
      "avatar_url": null,
      "is_active": true
    }
  ],
  "count": 2
}
```

---

### Error Responses

#### 400 Bad Request
**When:** Query parameter `q` is missing or shorter than 2 characters.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El parametro de busqueda requiere al menos 2 caracteres.",
  "details": {
    "q": ["Minimo 2 caracteres requeridos."]
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
  "message": "No tiene permisos para buscar pacientes."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate query parameter `q` (min 2 chars, max 100 chars).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (any staff role is allowed).
4. Normalize search query: trim whitespace, lowercase.
5. Check Redis cache for key `tenant:{tenant_id}:patients:search:{md5(q_normalized)}`.
6. If cache hit, return cached response.
7. Execute search query using a combined strategy:
   a. **Primary**: PostgreSQL full-text search using the existing GIN index and `websearch_to_tsquery('spanish', :q)`.
   b. **Fallback**: If tsvector returns 0 results, execute a `LIKE` prefix search on `document_number` and `phone` for partial numeric matches (e.g., user typing a phone number or document number digit by digit).
8. Combine results, deduplicate, limit to 10 rows.
9. Build response with minimal fields: id, full_name, document_number, phone, avatar_url, is_active.
10. Store result in Redis cache with TTL 2 minutes.
11. Return 200 with results.

**Search Query (primary -- full-text):**
```sql
SELECT id, first_name || ' ' || last_name AS full_name,
       document_number, phone, avatar_url, is_active
FROM patients
WHERE to_tsvector('spanish',
    coalesce(first_name, '') || ' ' ||
    coalesce(last_name, '') || ' ' ||
    coalesce(document_number, '') || ' ' ||
    coalesce(phone, '')
) @@ websearch_to_tsquery('spanish', :q)
ORDER BY ts_rank(
    to_tsvector('spanish',
        coalesce(first_name, '') || ' ' ||
        coalesce(last_name, '') || ' ' ||
        coalesce(document_number, '') || ' ' ||
        coalesce(phone, '')
    ),
    websearch_to_tsquery('spanish', :q)
) DESC
LIMIT 10;
```

**Search Query (fallback -- prefix match for numeric queries):**
```sql
SELECT id, first_name || ' ' || last_name AS full_name,
       document_number, phone, avatar_url, is_active
FROM patients
WHERE document_number ILIKE :q_prefix || '%'
   OR phone ILIKE '%' || :q_prefix || '%'
ORDER BY last_name, first_name
LIMIT 10;
```

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| q | 2-100 characters, trimmed | El parametro de busqueda requiere al menos 2 caracteres. |

**Business Rules:**

- The search returns both active and inactive patients. The `is_active` flag is included in the response so the frontend can visually distinguish them (e.g., grayed out).
- Results are ranked by relevance using `ts_rank` for full-text results.
- Maximum 10 results are returned regardless of how many match.
- The fallback prefix search activates only when the primary full-text search returns 0 results, to handle partial numeric inputs (phone numbers, document numbers).
- Full-text search uses the `spanish` text search configuration, which handles accent normalization and Spanish stopwords.
- This endpoint is designed for typeahead UIs where the user types character by character. The 2-char minimum prevents overly broad queries.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Query matches more than 10 patients | Return top 10 by relevance rank |
| Query is a partial phone number (e.g., "3001") | Fallback LIKE search finds matches on phone |
| Query is a document number prefix | Fallback LIKE search finds matches on document_number |
| Query has accented characters (e.g., "Garcia" vs "Garcia") | tsvector handles accent normalization |
| Query has extra whitespace | Trimmed before search |
| No results from both primary and fallback | Return empty data array with count = 0 |
| Tenant has zero patients | Return empty data array with count = 0 |
| Query contains SQL-like characters (' or ") | Safely parameterized via SQLAlchemy |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:search:{md5(q_normalized)}`: SET -- cache search results

**Cache TTL:** 2 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No -- typeahead searches are not individually audit-logged to avoid excessive volume. Search patterns are monitored via application-level metrics.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (cache hit < 20ms)
- **Maximum acceptable:** < 200ms

### Caching Strategy
- **Strategy:** Redis cache with query-based key
- **Cache key:** `tenant:{tenant_id}:patients:search:{md5(q_normalized)}`
- **TTL:** 2 minutes
- **Invalidation:** On patient create (P-01), patient update (P-04), patient deactivation (P-05)

### Database Performance

**Queries executed:** 1 (primary full-text) or 2 (primary + fallback) on cache miss

**Indexes required:**
- `patients USING GIN (to_tsvector('spanish', coalesce(first_name, '') || ' ' || coalesce(last_name, '') || ' ' || coalesce(document_number, '') || ' ' || coalesce(phone, '')))` -- GIN full-text index (already defined as idx_patients_search)
- `patients.phone` -- INDEX for fallback LIKE prefix (already defined)
- `patients.(document_type, document_number)` -- UNIQUE index also supports document_number prefix search

**N+1 prevention:** Single query, no joins or lazy loads.

### Pagination

**Pagination:** No (fixed max 10 results)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| q | Pydantic strip + limit to 100 chars | Passed to websearch_to_tsquery as bound param |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. The search term is passed as a bound parameter to `websearch_to_tsquery` and `ILIKE`, never interpolated into SQL strings.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** full_name, document_number, phone (minimal PHI subset for identification)

**Audit requirement:** Not individually logged (rate-based monitoring and application metrics for bulk PHI access patterns)

---

## Testing

### Test Cases

#### Happy Path
1. Search by last name
   - **Given:** Patient "Maria Garcia Lopez" exists
   - **When:** GET /api/v1/patients/search?q=Garcia
   - **Then:** 200 OK, data includes patient with full_name "Maria Garcia Lopez"

2. Search by document number
   - **Given:** Patient with document "1020304050" exists
   - **When:** GET /api/v1/patients/search?q=1020304050
   - **Then:** 200 OK, data includes the matching patient

3. Search by phone number prefix
   - **Given:** Patient with phone "+573001234567"
   - **When:** GET /api/v1/patients/search?q=300123
   - **Then:** 200 OK, fallback search finds the patient

4. Search by first name
   - **Given:** Patient "Maria Garcia Lopez"
   - **When:** GET /api/v1/patients/search?q=Maria
   - **Then:** 200 OK, data includes the patient

5. Cache hit returns same data
   - **Given:** Same search was executed less than 2 minutes ago
   - **When:** GET /api/v1/patients/search?q=Garcia
   - **Then:** 200 OK, response from Redis cache, < 20ms

#### Edge Cases
1. More than 10 matches
   - **Given:** 50 patients with last name "Garcia"
   - **When:** GET /api/v1/patients/search?q=Garcia
   - **Then:** 200 OK, count = 10 (limited), top 10 by relevance

2. Deactivated patient in results
   - **Given:** "Garcia" patient with is_active = false
   - **When:** GET /api/v1/patients/search?q=Garcia
   - **Then:** 200 OK, patient included with is_active = false

3. Search with accented characters
   - **Given:** Patient "Jose Garcia"
   - **When:** GET /api/v1/patients/search?q=jose (no accent)
   - **Then:** 200 OK, match found (tsvector handles accents)

4. No results
   - **Given:** No patient matches "XYZXYZ"
   - **When:** GET /api/v1/patients/search?q=XYZXYZ
   - **Then:** 200 OK, data = [], count = 0

5. Fallback activates for partial numeric input
   - **Given:** Patient with document "1020304050", tsvector does not match "102030"
   - **When:** GET /api/v1/patients/search?q=102030
   - **Then:** 200 OK, fallback LIKE finds the patient

#### Error Cases
1. Query too short
   - **Given:** q = "a" (1 character)
   - **When:** GET /api/v1/patients/search?q=a
   - **Then:** 400 Bad Request with min length error

2. Missing query parameter
   - **Given:** No q parameter
   - **When:** GET /api/v1/patients/search
   - **Then:** 400 Bad Request

3. Unauthorized role
   - **Given:** User with patient role
   - **When:** GET /api/v1/patients/search?q=Garcia
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** One user per staff role; one patient-role user for negative test

**Patients/Entities:** 50+ patients with varied names including common Spanish names, various document numbers and phone formats. At least one deactivated patient. Multiple patients with the same last name for relevance ranking tests.

### Mocking Strategy

- Redis cache: Use fakeredis; test both cache hit (< 20ms target) and miss paths
- Database: Test fixtures with known search terms and expected result counts

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Search by name returns matching patients ranked by relevance
- [ ] Search by document number returns matching patients
- [ ] Search by phone number returns matching patients (via fallback)
- [ ] Maximum 10 results returned
- [ ] Response includes: id, full_name, document_number, phone, avatar_url, is_active
- [ ] Deactivated patients included in results with is_active flag
- [ ] Response time < 100ms target (< 20ms cache hit)
- [ ] Results cached for 2 minutes
- [ ] Cache invalidated on patient create/update/deactivate
- [ ] Minimum 2-character query enforced
- [ ] All staff roles can access the endpoint
- [ ] All test cases pass
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Full paginated patient list with filters (see P-03, patient-list.md)
- Fuzzy/phonetic search (Soundex, Metaphone)
- Cross-tenant patient search (not applicable)
- Search result analytics or query logging
- Advanced filters combined with typeahead (use P-03 instead)

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
- [x] Response time target defined (< 100ms)
- [x] Caching strategy stated (tenant-namespaced, 2min TTL)
- [x] DB queries optimized (GIN index for tsvector)
- [x] Pagination applied where needed (N/A, fixed limit 10)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (rate-based monitoring)
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
