# OD-09: Odontogram Conditions Catalog Spec

---

## Overview

**Feature:** Retrieve the complete catalog of all valid dental conditions recognized by DentalOS. This is static reference data that defines the 12 condition codes with their display properties (name, color, icon, description) and the zones where each condition applies. Used by the frontend to render the condition palette and by the backend for enum validation in OD-02 and OD-11. Aggressively cached since the catalog is global and never changes per-tenant.

**Domain:** odontogram

**Priority:** High

**Dependencies:** None

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient, superadmin
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Any authenticated user can read the conditions catalog. This is reference data, not PHI.

---

## Endpoint

```
GET /api/v1/odontogram/conditions
```

**Rate Limiting:**
- 60 requests per minute per user
- Aggressively cached; high rate limit because frontend may call this on app initialization.

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
| lang | No | string | enum: es, en. Default: es | Language for name and description fields | es |

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "conditions": [
    {
      "code": "string",
      "name_es": "string",
      "name_en": "string",
      "color_hex": "string (6-digit hex with # prefix)",
      "icon": "string (icon key/name for frontend rendering)",
      "description_es": "string",
      "description_en": "string",
      "applies_to_zones": ["string"],
      "severity_applicable": "boolean"
    }
  ],
  "total": "integer",
  "version": "string (catalog version for cache invalidation awareness)",
  "cached_at": "string (ISO 8601)"
}
```

**Example:**
```json
{
  "conditions": [
    {
      "code": "caries",
      "name_es": "Caries",
      "name_en": "Cavity",
      "color_hex": "#D32F2F",
      "icon": "tooth_caries",
      "description_es": "Lesion cariosa activa que destruye la estructura dental",
      "description_en": "Active carious lesion destroying tooth structure",
      "applies_to_zones": ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal"],
      "severity_applicable": true
    },
    {
      "code": "restoration",
      "name_es": "Restauracion",
      "name_en": "Restoration",
      "color_hex": "#1565C0",
      "icon": "tooth_restoration",
      "description_es": "Restauracion dental con composite, amalgama u otro material",
      "description_en": "Dental restoration with composite, amalgam or other material",
      "applies_to_zones": ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal"],
      "severity_applicable": false
    },
    {
      "code": "extraction",
      "name_es": "Exodoncia indicada",
      "name_en": "Extraction indicated",
      "color_hex": "#E65100",
      "icon": "tooth_extraction",
      "description_es": "Diente con indicacion de exodoncia",
      "description_en": "Tooth indicated for extraction",
      "applies_to_zones": ["full"],
      "severity_applicable": false
    },
    {
      "code": "absent",
      "name_es": "Ausente",
      "name_en": "Absent",
      "color_hex": "#757575",
      "icon": "tooth_absent",
      "description_es": "Diente ausente por exodoncia previa o agenesia",
      "description_en": "Missing tooth due to prior extraction or agenesis",
      "applies_to_zones": ["full"],
      "severity_applicable": false
    },
    {
      "code": "crown",
      "name_es": "Corona",
      "name_en": "Crown",
      "color_hex": "#FDD835",
      "icon": "tooth_crown",
      "description_es": "Corona dental fija sobre el diente",
      "description_en": "Fixed dental crown on the tooth",
      "applies_to_zones": ["full"],
      "severity_applicable": false
    },
    {
      "code": "endodontic",
      "name_es": "Endodoncia",
      "name_en": "Endodontic treatment",
      "color_hex": "#6A1B9A",
      "icon": "tooth_endodontic",
      "description_es": "Tratamiento de conductos radiculares realizado",
      "description_en": "Root canal treatment performed",
      "applies_to_zones": ["root"],
      "severity_applicable": false
    },
    {
      "code": "implant",
      "name_es": "Implante",
      "name_en": "Implant",
      "color_hex": "#00838F",
      "icon": "tooth_implant",
      "description_es": "Implante dental oseointegrado",
      "description_en": "Osseointegrated dental implant",
      "applies_to_zones": ["full"],
      "severity_applicable": false
    },
    {
      "code": "fracture",
      "name_es": "Fractura",
      "name_en": "Fracture",
      "color_hex": "#BF360C",
      "icon": "tooth_fracture",
      "description_es": "Fractura coronal o radicular del diente",
      "description_en": "Coronal or root fracture of the tooth",
      "applies_to_zones": ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal", "root"],
      "severity_applicable": true
    },
    {
      "code": "sealant",
      "name_es": "Sellante",
      "name_en": "Sealant",
      "color_hex": "#2E7D32",
      "icon": "tooth_sealant",
      "description_es": "Sellante de fisuras aplicado como prevencion",
      "description_en": "Fissure sealant applied as prevention",
      "applies_to_zones": ["oclusal"],
      "severity_applicable": false
    },
    {
      "code": "fluorosis",
      "name_es": "Fluorosis",
      "name_en": "Fluorosis",
      "color_hex": "#F9A825",
      "icon": "tooth_fluorosis",
      "description_es": "Hipomineralizacion del esmalte por exceso de fluor",
      "description_en": "Enamel hypomineralization due to excess fluoride",
      "applies_to_zones": ["vestibular", "lingual", "palatino"],
      "severity_applicable": true
    },
    {
      "code": "temporary",
      "name_es": "Temporal",
      "name_en": "Temporary restoration",
      "color_hex": "#78909C",
      "icon": "tooth_temporary",
      "description_es": "Restauracion provisional o temporal",
      "description_en": "Provisional or temporary restoration",
      "applies_to_zones": ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal"],
      "severity_applicable": false
    },
    {
      "code": "prosthesis",
      "name_es": "Protesis",
      "name_en": "Prosthesis",
      "color_hex": "#4527A0",
      "icon": "tooth_prosthesis",
      "description_es": "Protesis fija o removible sobre el diente",
      "description_en": "Fixed or removable prosthesis on the tooth",
      "applies_to_zones": ["full"],
      "severity_applicable": false
    }
  ],
  "total": 12,
  "version": "1.0.0",
  "cached_at": "2026-02-24T00:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 422 Unprocessable Entity
**When:** Invalid `lang` query parameter.

```json
{
  "error": "validation_failed",
  "message": "Parametro de idioma invalido. Use 'es' o 'en'.",
  "details": {
    "lang": ["El idioma debe ser 'es' o 'en'."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected failure serving catalog (should be extremely rare since catalog is in-memory).

---

## Business Logic

**Step-by-step process:**

1. Validate `lang` query parameter (if provided). Default to `"es"` if omitted.
2. Authenticate user (any role). No tenant-specific logic required.
3. Check Redis cache key `global:odontogram_conditions_catalog:{lang}`. If HIT, return cached response.
4. If MISS: load conditions catalog from in-memory constant (Python module-level constant, not a database table — catalog is static code, not dynamic data).
5. Build response array with all 12 conditions in the order they appear in the catalog constant.
6. Set `version = "1.0.0"` (catalog version, updated in code when conditions are changed).
7. Set `cached_at = now()`.
8. Write to Redis cache: key `global:odontogram_conditions_catalog:{lang}`, TTL 3600 seconds (1 hour).
9. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| lang | Optional; if provided, must be "es" or "en" | El idioma debe ser 'es' o 'en'. |

**Business Rules:**

- The conditions catalog is hardcoded in application code as a Python constant (not a database table). This is intentional: it is shared globally across all tenants and never changes at runtime.
- The cache key is `global:` prefixed (not `tenant:`) because the catalog is tenant-independent.
- `applies_to_zones` is the authoritative source for backend validation in OD-02 and OD-11. The backend validator must use the same source.
- `severity_applicable` tells the frontend whether to show a severity selector when this condition is chosen.
- Conditions with `applies_to_zones: ["full"]` apply to the whole tooth, not individual zones. Frontend renders these differently (no zone selection needed).
- If a condition needs to be added or modified, it requires a code change and re-deployment (not a runtime API call). Catalog version is bumped in the code constant.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| lang not provided | Default to "es"; return Spanish names and descriptions |
| lang=en | Return English names and descriptions |
| Cache miss on first boot | Serve from in-memory constant; populate Redis cache |
| Frontend requests catalog repeatedly (polling) | Served from Redis cache; negligible DB/CPU cost |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (catalog is served from in-memory constant).

### Cache Operations

**Cache keys affected:**
- `global:odontogram_conditions_catalog:es`: SET — Spanish catalog, TTL 3600s.
- `global:odontogram_conditions_catalog:en`: SET — English catalog, TTL 3600s.

**Cache TTL:** 3600 seconds (1 hour) — can be extended to 24 hours since catalog only changes on deployment.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — catalog is not PHI; no audit required for reference data access.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 20ms (cache hit — in-memory data)
- **Maximum acceptable:** < 100ms (cache miss from in-memory constant)

### Caching Strategy
- **Strategy:** Redis cache, globally shared (not tenant-namespaced — same catalog for all tenants).
- **Cache key:** `global:odontogram_conditions_catalog:{lang}`
- **TTL:** 3600 seconds (1 hour). Consider extending to 86400 (24 hours) since catalog changes only on deployment.
- **Invalidation:** Redis cache expires naturally. On deployment that changes the catalog, a startup script should flush `global:odontogram_conditions_catalog:*`.

### Database Performance

**Queries executed:** 0 (catalog served from in-memory Python constant + Redis cache).

**Indexes required:** None (no DB queries).

**N+1 prevention:** Not applicable.

### Pagination

**Pagination:** No — catalog has exactly 12 conditions, returned in full.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| lang | Pydantic enum validator (es, en) | Whitelist prevents injection via lang parameter |

### SQL Injection Prevention

**All queries use:** No database queries for this endpoint.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — catalog is reference data with no patient information.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. Get catalog in Spanish (default)
   - **Given:** Authenticated doctor (any role)
   - **When:** GET /api/v1/odontogram/conditions
   - **Then:** 200 OK, 12 conditions returned, names in Spanish, version="1.0.0"

2. Get catalog in English
   - **Given:** Authenticated user, lang=en
   - **When:** GET /api/v1/odontogram/conditions?lang=en
   - **Then:** 200 OK, names and descriptions in English

3. Cache hit path
   - **Given:** First request already cached
   - **When:** GET catalog again within 1 hour
   - **Then:** 200 OK, served from Redis, response time < 20ms

4. Receptionist can access catalog
   - **Given:** Authenticated receptionist role
   - **When:** GET catalog
   - **Then:** 200 OK (all authenticated roles can access)

5. Patient role can access catalog
   - **Given:** Authenticated patient role
   - **When:** GET catalog
   - **Then:** 200 OK (reference data, not restricted to clinical staff)

#### Edge Cases
1. lang parameter not provided
   - **Given:** Request without lang query param
   - **When:** GET /api/v1/odontogram/conditions
   - **Then:** 200 OK in Spanish (default)

2. Each condition has correct applies_to_zones
   - **Given:** Catalog returned
   - **When:** Validate endodontic condition
   - **Then:** applies_to_zones = ["root"] only

3. Full-tooth conditions have applies_to_zones=["full"]
   - **Given:** Catalog returned
   - **When:** Validate absent, implant, crown conditions
   - **Then:** All have applies_to_zones = ["full"]

#### Error Cases
1. Invalid lang value
   - **Given:** lang=fr (French, not supported)
   - **When:** GET /api/v1/odontogram/conditions?lang=fr
   - **Then:** 422 Unprocessable Entity

2. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** GET catalog
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Any authenticated user (all roles should pass).

**Patients/Entities:** None required (no patient data involved).

### Mocking Strategy

- Redis: Use fakeredis to test cache hit and cache miss paths.
- Catalog constant: Use actual production catalog constant in tests (no mocking needed — it is the code under test).

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Returns all 12 conditions with correct codes, colors, icons, and zone lists
- [ ] Spanish and English language support works via `lang` parameter
- [ ] Default language is Spanish when `lang` not provided
- [ ] Response served from Redis cache on subsequent requests within 1 hour
- [ ] Cache key is `global:` prefixed (not tenant-scoped)
- [ ] `applies_to_zones` matches the validation whitelist used in OD-02 and OD-11
- [ ] No database queries executed (zero DB round trips)
- [ ] All authenticated roles can access (including receptionist and patient)
- [ ] All test cases pass
- [ ] Performance targets met (< 20ms cache hit, < 100ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Adding or modifying conditions at runtime (requires code change + deployment)
- Per-tenant custom conditions (DentalOS uses a universal FDI-compliant catalog)
- Condition severity definitions (severity is free-form: mild/moderate/severe)
- Icon asset serving (icons are referenced by key; frontend bundle contains the assets)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models with all 12 conditions)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (lang enum only)
- [x] Error cases enumerated
- [x] Auth requirements explicit (any authenticated role)
- [x] Side effects listed
- [x] Examples provided (all 12 conditions shown)

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (reference data, no tenant context needed in query)
- [x] Uses tenant schema isolation (N/A — global catalog)
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md (no DB table — in-memory)

### Hook 3: Security & Privacy
- [x] Auth level stated (any authenticated user)
- [x] Input sanitization defined (Pydantic enum for lang)
- [x] SQL injection prevented (no DB queries)
- [x] No PHI exposure (catalog contains no patient data)
- [x] Audit trail not required (not PHI)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 20ms cache hit)
- [x] Caching strategy stated (global Redis key, 1 hour TTL)
- [x] DB queries optimized (zero queries — in-memory constant)
- [x] Pagination applied where needed (N/A — 12 items)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included for consistency)
- [x] Audit log entries defined (N/A — not PHI)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified (none required)
- [x] Mocking strategy for external services
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec — 12 conditions defined |
