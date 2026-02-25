# Prescription Medication Search Spec

---

## Overview

**Feature:** Typeahead search endpoint for the medication catalog used when creating prescriptions. Searches across generic names, brand names, and active ingredients. Returns structured medication data to populate the prescription creation form. The catalog is shared across all tenants (public catalog).

**Domain:** prescriptions

**Priority:** Medium

**Dependencies:** RX-01 (prescription-create.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Authenticated (any authenticated user)
- **Roles allowed:** clinic_owner, doctor, assistant, patient, superadmin — any role with a valid JWT
- **Tenant context:** Not required — the catalog is global (`public.catalog_medications`) and has no tenant scope
- **Special rules:** No tenant isolation needed; the same catalog is shared across all tenants.

---

## Endpoint

```
GET /api/v1/catalog/medications
```

**Rate Limiting:**
- 200 requests per minute per user
- Typeahead endpoint; high rate limit needed for real-time search UX

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| q | Yes | string | min: 2 chars, max: 100 chars | Search term — matches against generic_name, brand_name, active_ingredient | amox |

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
      "generic_name": "string",
      "brand_names": "string[]",
      "active_ingredient": "string | null",
      "presentations": "string[]",
      "default_dosage": "string | null",
      "default_route": "string | null"
    }
  ],
  "total": "integer — total matches (may be more than returned)",
  "query": "string — the search term used",
  "limit": "integer — max results returned (always 20)"
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "m1a2b3c4-0000-4000-8000-000000000001",
      "generic_name": "Amoxicilina",
      "brand_names": ["Amoxil", "Trimox", "Clavulanato"],
      "active_ingredient": "amoxicillin trihydrate",
      "presentations": ["Capsulas 250mg", "Capsulas 500mg", "Suspension 125mg/5ml", "Suspension 250mg/5ml"],
      "default_dosage": "500mg",
      "default_route": "oral"
    },
    {
      "id": "m2b3c4d5-0000-4000-8000-000000000002",
      "generic_name": "Amoxicilina + Acido Clavulanico",
      "brand_names": ["Augmentin", "Clavulin"],
      "active_ingredient": "amoxicillin + clavulanic acid",
      "presentations": ["Tabletas 500mg/125mg", "Suspension 250mg/62.5mg"],
      "default_dosage": "500mg/125mg",
      "default_route": "oral"
    }
  ],
  "total": 2,
  "query": "amox",
  "limit": 20
}
```

### Error Responses

#### 400 Bad Request
**When:** `q` parameter is missing or shorter than 2 characters.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El termino de busqueda debe tener al menos 2 caracteres.",
  "details": {
    "q": ["El termino de busqueda debe tener al menos 2 caracteres."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Validate `q` parameter: must be present, minimum 2 characters, maximum 100 characters. Trim whitespace.
2. Verify JWT authentication (any role accepted; no tenant resolution required).
3. Sanitize `q`: strip HTML tags, lowercase for search normalization.
4. Build cache key: `global:catalog:medications:search:{q_normalized}`.
5. Check Redis cache — if hit, return cached results immediately.
6. Query `public.catalog_medications` using full-text or ILIKE search:
   - `generic_name ILIKE '%{q}%'` OR
   - `brand_names @> '{q}'` (array contains) OR
   - `active_ingredient ILIKE '%{q}%'`
7. Order results by relevance:
   - Exact prefix match on `generic_name` first
   - Partial match on `generic_name` second
   - Brand name or active ingredient matches last
8. Limit results to 20 items.
9. Cache result in Redis with 1-hour TTL (shared across all tenants; no tenant namespacing needed).
10. Return 200 with results.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| q | Required, 2–100 chars after trimming | El termino de busqueda debe tener al menos 2 caracteres. |
| q | Strip HTML tags before search | (sanitized silently) |

**Business Rules:**

- The catalog is global (`public.catalog_medications`) — no tenant isolation applies.
- Search is case-insensitive.
- Maximum 20 results returned per query (optimized for typeahead UX — no pagination).
- Results are ordered by relevance: prefix match on `generic_name` ranks highest.
- If `q` matches zero medications, return empty `data: []` with `total: 0` (not 404).
- Cache is shared globally (not per-tenant) since the catalog has no tenant ownership.
- The endpoint is intentionally lightweight — response target is < 100ms.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| `q` is exactly 2 characters | Accept and search |
| `q` matches > 20 medications | Return top 20 by relevance; `total` reflects actual count |
| `q` contains only whitespace | Trim to empty string; return 400 (treated as missing) |
| `q` contains special regex characters | Escape before building SQL ILIKE pattern |
| Search term has accented characters (e.g., "ibuprofeno") | Case-insensitive and accent-insensitive search (unaccented index) |
| Cache miss for uncommon query | Query DB, cache for 1 hour, return results |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- None (read-only operation on `public.catalog_medications`)

### Cache Operations

**Cache keys affected:**
- `global:catalog:medications:search:{q_normalized}`: SET — populated on cache miss

**Cache TTL:** 1 hour (shared across all tenants)

**Note:** Cache is stored in the `global:` namespace (not tenant-namespaced) since the catalog is public.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** No — medication catalog search is non-PHI, non-clinical data access. No audit required.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms (cache hit)
- **Maximum acceptable:** < 100ms (cache miss — typeahead requirement)

### Caching Strategy
- **Strategy:** Redis global cache (not tenant-namespaced)
- **Cache key:** `global:catalog:medications:search:{q_normalized}`
- **TTL:** 1 hour
- **Invalidation:** Catalog is updated by system administrators; cache TTL expiry is sufficient for normal operations. Admin-triggered manual cache clear for emergency updates.

### Database Performance

**Queries executed:** 1 (ILIKE search against public catalog on cache miss)

**Indexes required:**
- `public.catalog_medications.generic_name` — GIN index with `pg_trgm` extension for fast ILIKE search
- `public.catalog_medications.active_ingredient` — GIN index with `pg_trgm`
- `public.catalog_medications.brand_names` — GIN index (for array containment searches)

**N+1 prevention:** Not applicable (single query against catalog)

### Pagination

**Pagination:** No — fixed limit of 20 results. Typeahead UX does not require full pagination.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| q | strip() + strip_tags + bleach.clean | Prevent XSS via search term; escape ILIKE special chars (%_\) |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. ILIKE patterns use `bindparam()` with the `%` wildcard prepended/appended in Python, not in raw SQL.

### XSS Prevention

**Output encoding:** All string fields escaped via Pydantic serialization on output.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — medication catalog is public, non-patient data.

**Audit requirement:** Not required (no PHI accessed).

---

## Testing

### Test Cases

#### Happy Path
1. Search by generic name prefix
   - **Given:** Authenticated doctor, catalog has "Amoxicilina" and "Amoxicilina + Acido Clavulanico"
   - **When:** GET /api/v1/catalog/medications?q=amox
   - **Then:** 200 OK, both medications returned, generic_name prefix match ordered first

2. Search by brand name
   - **Given:** Catalog has medication with brand_names including "Augmentin"
   - **When:** GET /api/v1/catalog/medications?q=augm
   - **Then:** 200 OK, "Amoxicilina + Acido Clavulanico" returned (matched via brand_name)

3. Search by active ingredient
   - **Given:** Catalog has medication with active_ingredient = "ibuprofen"
   - **When:** GET /api/v1/catalog/medications?q=ibuprofen
   - **Then:** 200 OK, matching medication returned

4. Cache hit on repeated search
   - **Given:** Same `q` searched twice within 1 hour
   - **When:** GET /api/v1/catalog/medications?q=amox (second call)
   - **Then:** 200 OK returned from cache, DB not queried

5. Search from assistant role
   - **Given:** User with assistant role
   - **When:** GET /api/v1/catalog/medications?q=ibu
   - **Then:** 200 OK — any authenticated role can search

6. Search with exactly 2 characters
   - **Given:** `q=am`
   - **When:** GET
   - **Then:** 200 OK, results returned (broad search)

#### Edge Cases
1. Search returning > 20 results
   - **Given:** Many medications match `q=a`
   - **When:** GET /api/v1/catalog/medications?q=am
   - **Then:** 200 OK, exactly 20 results returned, `total` shows actual match count

2. Search with no results
   - **Given:** `q=xyznoexist`
   - **When:** GET
   - **Then:** 200 OK, `data: []`, `total: 0`

3. Search with accented character
   - **Given:** Catalog has "Ibuprofeno"
   - **When:** GET ?q=ibuprofeno
   - **Then:** 200 OK, found (case and accent insensitive)

4. Search with special SQL character in `q`
   - **Given:** `q=amox%_`
   - **When:** GET
   - **Then:** 200 OK, `%` and `_` characters properly escaped before SQL execution, no injection

#### Error Cases
1. Missing `q` parameter
   - **Given:** No `q` provided
   - **When:** GET /api/v1/catalog/medications
   - **Then:** 400 Bad Request

2. `q` is 1 character
   - **Given:** `q=a`
   - **When:** GET
   - **Then:** 400 Bad Request with validation message

3. `q` is whitespace only
   - **Given:** `q=   ` (spaces only)
   - **When:** GET
   - **Then:** 400 Bad Request (treated as empty after trimming)

4. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** GET
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** doctor, assistant (any authenticated user)

**Patients/Entities:** `public.catalog_medications` seeded with at least 30 medications covering multiple generic names, brand names, and active ingredients. Must include medications with accented Spanish names.

### Mocking Strategy

- Redis cache: Use fakeredis to test cache hit/miss behavior
- Catalog DB: Integration test with seeded `public.catalog_medications` fixture (do not mock the catalog)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Search results returned in < 100ms (including on first cache miss)
- [ ] Generic name, brand name, and active ingredient all searchable
- [ ] Results ordered by relevance (prefix match on generic_name ranks first)
- [ ] Maximum 20 results returned; `total` shows actual match count
- [ ] `q` less than 2 characters returns 400
- [ ] Missing `q` returns 400
- [ ] No tenant context required (global catalog, no schema switching)
- [ ] Cache populated for 1 hour on first search; subsequent identical searches served from cache
- [ ] ILIKE special characters (`%`, `_`, `\`) properly escaped
- [ ] Any authenticated role can access (no role restriction)
- [ ] No audit log written (non-PHI endpoint)
- [ ] All test cases pass
- [ ] Performance target met (< 50ms cache hit, < 100ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Adding, updating, or deleting medications from the catalog (superadmin operation)
- Browsing full medication detail pages
- Filtering by medication class or therapeutic category
- Drug interaction checking
- Formulary management (EPS-specific approved medications)
- Medication shortage alerts

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
- [x] Uses public schema (explicitly no tenant isolation — by design)
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (any authenticated role)
- [x] Input sanitization defined (bleach + ILIKE escape)
- [x] SQL injection prevented (SQLAlchemy ORM parameterized ILIKE)
- [x] No PHI exposure in logs or errors
- [x] Audit trail not required (non-PHI)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 100ms — typeahead requirement)
- [x] Caching strategy stated (global 1-hour cache)
- [x] DB queries optimized (GIN trigram indexes)
- [x] Pagination applied where needed (N/A — fixed 20-result limit for typeahead)

### Hook 5: Observability
- [x] Structured logging (JSON, no tenant_id — global endpoint)
- [x] Audit log entries defined (N/A — no PHI)
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
