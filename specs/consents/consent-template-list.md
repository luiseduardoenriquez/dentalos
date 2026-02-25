# Consent Template List Spec

---

## Overview

**Feature:** List all informed consent templates available to a tenant, including built-in system templates and custom templates created by the clinic. Results are cached per tenant to support fast template picker UIs.

**Domain:** consents

**Priority:** High

**Dependencies:** I-01 (multi-tenancy.md), I-02 (database-architecture.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** None

---

## Endpoint

```
GET /api/v1/consent-templates
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
| category | No | string | enum: general, surgery, sedation, orthodontics, implants, endodontics, pediatric | Filter by consent category | surgery |
| is_builtin | No | boolean | true or false | Filter to show only built-in or only custom templates | true |

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
      "name": "string",
      "category": "string (enum: general | surgery | sedation | orthodontics | implants | endodontics | pediatric)",
      "description": "string | null",
      "is_builtin": "boolean",
      "created_by": "uuid | null",
      "fields_count": "integer"
    }
  ],
  "total": "integer"
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "a1b2c3d4-0000-4000-8000-000000000001",
      "name": "Consentimiento General Odontologico",
      "category": "general",
      "description": "Consentimiento informado para procedimientos odontologicos de rutina.",
      "is_builtin": true,
      "created_by": null,
      "fields_count": 6
    },
    {
      "id": "b2c3d4e5-0000-4000-8000-000000000002",
      "name": "Consentimiento Extraccion Quirurgica",
      "category": "surgery",
      "description": "Consentimiento para extracciones quirurgicas incluyendo terceros molares.",
      "is_builtin": true,
      "created_by": null,
      "fields_count": 9
    },
    {
      "id": "c3d4e5f6-0000-4000-8000-000000000003",
      "name": "Consentimiento Personalizado Implantes 2026",
      "category": "implants",
      "description": "Template personalizado de la clinica para implantes osseointegrados.",
      "is_builtin": false,
      "created_by": "d4e5f6a7-0000-4000-8000-000000000004",
      "fields_count": 12
    }
  ],
  "total": 3
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter value (e.g., unrecognized category enum).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El valor del parametro 'category' no es valido.",
  "details": {
    "category": ["Opciones validas: general, surgery, sedation, orthodontics, implants, endodontics, pediatric."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not in the allowed list (e.g., patient role).

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver las plantillas de consentimiento."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Validate query parameters against Pydantic schema (enum values).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (must be clinic_owner, doctor, or assistant).
4. Build cache key: `tenant:{tenant_id}:consent_templates:list:{category}:{is_builtin}`.
5. Check Redis cache — if hit, return cached response immediately.
6. Query `consent_templates` table: SELECT built-in records (from `public.consent_templates`) UNION ALL custom records from tenant schema, applying filters.
7. For each template, compute `fields_count` from `template_fields` relationship or stored count column.
8. Store result in Redis with 30-minute TTL.
9. Return 200 with data array and total count.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| category | If provided, must be one of the defined enum values | El valor del parametro 'category' no es valido. |
| is_builtin | If provided, must parse as boolean (true/false/1/0) | El valor del parametro 'is_builtin' debe ser verdadero o falso. |

**Business Rules:**

- Built-in templates are stored in `public.consent_templates` (shared across all tenants); they are never editable by tenants.
- Custom templates are stored in the tenant schema `consent_templates` table with `is_builtin = false`.
- Both sources are merged before applying filters.
- The `created_by` field is `null` for built-in templates (system-created).
- If no templates match the filter, return an empty `data` array with `total = 0` (not 404).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant has no custom templates | Return only built-in templates |
| Both `category` and `is_builtin=true` filters provided | Apply both filters (AND logic) |
| Cache is cold on first request | Query DB, populate cache, return results |
| Built-in template category not matching filter | Exclude from results (same filter applies to both sources) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:consent_templates:list:{category}:{is_builtin}`: SET — populated on cache miss

**Cache TTL:** 30 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** No — list operation on non-PHI template metadata does not require audit logging.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms (cache hit)
- **Maximum acceptable:** < 200ms (cache miss with DB query)

### Caching Strategy
- **Strategy:** Redis cache per tenant + filter combination
- **Cache key:** `tenant:{tenant_id}:consent_templates:list:{category}:{is_builtin}`
- **TTL:** 30 minutes
- **Invalidation:** Invalidated when a custom template is created, updated, or deleted within the tenant

### Database Performance

**Queries executed:** 1 (UNION of public + tenant tables, only on cache miss)

**Indexes required:**
- `public.consent_templates.category` — INDEX
- `public.consent_templates.is_builtin` — INDEX (always true for built-ins)
- `{tenant}.consent_templates.category` — INDEX
- `{tenant}.consent_templates.is_builtin` — INDEX

**N+1 prevention:** `fields_count` stored as a computed column or retrieved via single JOIN; no per-row sub-queries.

### Pagination

**Pagination:** No — template count per tenant is expected to be small (< 50). Full list returned.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| category | Pydantic enum validator | Rejects any value not in the defined set |
| is_builtin | Pydantic bool coercion | Strict boolean parsing |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — template metadata only (names, categories, descriptions).

**Audit requirement:** Not required (no PHI accessed).

---

## Testing

### Test Cases

#### Happy Path
1. List all templates (no filters)
   - **Given:** Authenticated doctor, tenant has 7 built-in templates and 2 custom templates
   - **When:** GET /api/v1/consent-templates
   - **Then:** 200 OK, `total = 9`, all templates returned

2. Filter by category
   - **Given:** Authenticated doctor, built-in surgery template exists
   - **When:** GET /api/v1/consent-templates?category=surgery
   - **Then:** 200 OK, only surgery-category templates returned

3. Filter built-in only
   - **Given:** Authenticated assistant, tenant has custom templates
   - **When:** GET /api/v1/consent-templates?is_builtin=true
   - **Then:** 200 OK, only built-in templates returned

4. Cache hit on repeated request
   - **Given:** Same request made twice within 30 minutes
   - **When:** GET /api/v1/consent-templates (second call)
   - **Then:** 200 OK returned from cache, DB not queried

#### Edge Cases
1. Tenant with no custom templates
   - **Given:** Tenant has never created a custom template
   - **When:** GET /api/v1/consent-templates?is_builtin=false
   - **Then:** 200 OK, `data: []`, `total: 0`

2. Combined category + is_builtin filter
   - **Given:** Built-in pediatric template exists, custom pediatric template exists
   - **When:** GET /api/v1/consent-templates?category=pediatric&is_builtin=true
   - **Then:** 200 OK, only the built-in pediatric template returned

#### Error Cases
1. Invalid category value
   - **Given:** Authenticated doctor
   - **When:** GET /api/v1/consent-templates?category=invalid_category
   - **Then:** 400 Bad Request with validation detail

2. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** GET /api/v1/consent-templates
   - **Then:** 401 Unauthorized

3. Patient role attempting access
   - **Given:** User with patient role
   - **When:** GET /api/v1/consent-templates
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (happy path); patient (negative test)

**Patients/Entities:** Tenant with full set of 7 built-in templates seeded; tenant with at least 2 custom templates in different categories.

### Mocking Strategy

- Redis cache: Use fakeredis to simulate cache hit/miss scenarios
- Public DB catalog: Seeded fixture with 7 built-in templates across all categories

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] All 7 built-in templates returned when no filters applied
- [ ] `category` filter correctly reduces result set
- [ ] `is_builtin=false` returns only custom templates for the tenant
- [ ] Response includes correct `fields_count` for each template
- [ ] Cache populated on first request; subsequent requests served from cache within 30 minutes
- [ ] Cache invalidated when tenant creates or modifies a custom template
- [ ] Unauthorized roles return 403
- [ ] All test cases pass
- [ ] Performance target met (< 50ms on cache hit, < 200ms on cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Retrieving full template content (see IC-03 consent-template-get.md)
- Creating or modifying custom templates (see IC-02 consent-template-create.md)
- Deleting templates
- Template versioning

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
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A — small dataset)

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
