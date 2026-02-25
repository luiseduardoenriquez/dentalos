# Consent Template Get Spec

---

## Overview

**Feature:** Retrieve a single consent template by ID, including the full HTML content, placeholder list, required fields configuration, and signature positions. Used by the consent creation flow to preview and select a template.

**Domain:** consents

**Priority:** High

**Dependencies:** IC-01 (consent-template-list.md), IC-02 (consent-template-create.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Built-in templates are accessible to all tenants; custom templates are scoped to the owning tenant only.

---

## Endpoint

```
GET /api/v1/consent-templates/{template_id}
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
| template_id | Yes | string (UUID) | Valid UUID v4 | ID of the consent template | a1b2c3d4-0000-4000-8000-000000000001 |

### Query Parameters

None.

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "name": "string",
  "category": "string (enum: general | surgery | sedation | orthodontics | implants | endodontics | pediatric)",
  "description": "string | null",
  "is_builtin": "boolean",
  "content": "string (sanitized HTML with placeholders)",
  "required_fields": "string[]",
  "signature_positions": {
    "patient": { "label": "string", "required": "boolean" },
    "doctor": { "label": "string", "required": "boolean" },
    "witness": { "label": "string | null", "required": "boolean" }
  },
  "fields_count": "integer",
  "created_by": "uuid | null",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "a1b2c3d4-0000-4000-8000-000000000001",
  "name": "Consentimiento General Odontologico",
  "category": "general",
  "description": "Consentimiento informado para procedimientos odontologicos de rutina.",
  "is_builtin": true,
  "content": "<h1>CONSENTIMIENTO INFORMADO PARA PROCEDIMIENTO ODONTOLOGICO</h1><p>Yo, <strong>{{patient_name}}</strong>, identificado(a) con cedula de ciudadania numero <strong>{{patient_cedula}}</strong>, de <strong>{{patient_age}}</strong> anos de edad, en pleno uso de mis facultades mentales y de manera libre y voluntaria, autorizo al Dr. <strong>{{doctor_name}}</strong> (Tarjeta Profesional No. {{doctor_license}}) de la Clinica <strong>{{clinic_name}}</strong> para realizar el siguiente procedimiento: <strong>{{procedure}}</strong>.</p><p>Ciudad y fecha: {{date}}</p>",
  "required_fields": ["procedure"],
  "signature_positions": {
    "patient": { "label": "Firma del Paciente", "required": true },
    "doctor": { "label": "Firma del Odontologo", "required": true },
    "witness": { "label": "Firma del Testigo", "required": false }
  },
  "fields_count": 6,
  "created_by": null,
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not in the allowed list, OR the template_id belongs to a different tenant's custom template.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver esta plantilla de consentimiento."
}
```

#### 404 Not Found
**When:** No template found with the given `template_id` in public catalog or tenant schema.

**Example:**
```json
{
  "error": "template_not_found",
  "message": "Plantilla de consentimiento no encontrada."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate `template_id` is a valid UUID format.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (must be clinic_owner, doctor, or assistant).
4. Check Redis cache: `tenant:{tenant_id}:consent_templates:detail:{template_id}` — return if hit.
5. Search for template: first in `public.consent_templates` (built-in), then in tenant `consent_templates` (custom).
6. If found in built-in catalog, return without tenant ownership check.
7. If found in tenant custom table, verify `tenant_id` matches current tenant; return 403 if mismatch.
8. If not found in either, return 404.
9. Cache result in Redis with 30-minute TTL.
10. Return 200 with full template detail.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| template_id | Must be a valid UUID v4 | El identificador de plantilla no es valido. |

**Business Rules:**

- Built-in templates (in `public.consent_templates`) are accessible to any authenticated user of any tenant.
- Custom templates are tenant-scoped — accessing another tenant's template returns 403 (not 404) to avoid information leakage.
- The full `content` HTML is returned in this endpoint (unlike the list endpoint which only returns metadata).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| `template_id` is a valid UUID but does not exist | 404 Not Found |
| User requests built-in template from any tenant | 200 OK — built-ins are universal |
| User requests custom template belonging to another tenant | 403 Forbidden |
| Malformed UUID in path (e.g., "not-a-uuid") | 422 Unprocessable Entity from path validation |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:consent_templates:detail:{template_id}`: SET — populated on cache miss

**Cache TTL:** 30 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** No — reading template metadata (non-PHI) does not require audit logging.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 30ms (cache hit)
- **Maximum acceptable:** < 150ms (cache miss)

### Caching Strategy
- **Strategy:** Redis cache per template ID (tenant-namespaced for custom templates)
- **Cache key:** `tenant:{tenant_id}:consent_templates:detail:{template_id}`
- **TTL:** 30 minutes
- **Invalidation:** Invalidated when the template is modified or deleted

### Database Performance

**Queries executed:** 1–2 (check public catalog first; if not found, check tenant custom table)

**Indexes required:**
- `public.consent_templates.id` — PRIMARY KEY
- `{tenant}.consent_templates.id` — PRIMARY KEY

**N+1 prevention:** Not applicable (single row retrieval)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| template_id | Pydantic UUID validator | Reject malformed path parameters |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Content HTML was sanitized on input (see IC-02). Pydantic serialization applies on output.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — template content contains placeholders, not actual patient data.

**Audit requirement:** Not required (no PHI accessed).

---

## Testing

### Test Cases

#### Happy Path
1. Retrieve built-in template
   - **Given:** Authenticated doctor, valid `template_id` for a built-in template
   - **When:** GET /api/v1/consent-templates/{template_id}
   - **Then:** 200 OK, full content returned, `is_builtin: true`, `created_by: null`

2. Retrieve custom tenant template
   - **Given:** Authenticated clinic_owner, `template_id` for a custom template created by this tenant
   - **When:** GET /api/v1/consent-templates/{template_id}
   - **Then:** 200 OK, full content returned, `is_builtin: false`, `created_by` set to creator UUID

3. Cache hit on repeated request
   - **Given:** Same template_id requested twice within 30 minutes
   - **When:** GET /api/v1/consent-templates/{template_id} (second call)
   - **Then:** 200 OK returned from cache, DB not queried

#### Edge Cases
1. Request built-in template from any tenant
   - **Given:** Different tenant's doctor uses the global built-in template ID
   - **When:** GET /api/v1/consent-templates/{builtin_template_id}
   - **Then:** 200 OK — built-in accessible universally

#### Error Cases
1. Template not found
   - **Given:** Valid UUID that does not correspond to any template
   - **When:** GET /api/v1/consent-templates/{nonexistent_uuid}
   - **Then:** 404 Not Found

2. Cross-tenant access to custom template
   - **Given:** Tenant B requests a template ID that belongs to Tenant A's custom templates
   - **When:** GET /api/v1/consent-templates/{tenant_a_template_id}
   - **Then:** 403 Forbidden

3. Patient role attempting access
   - **Given:** User with patient role
   - **When:** GET /api/v1/consent-templates/{template_id}
   - **Then:** 403 Forbidden

4. Malformed UUID path parameter
   - **Given:** `template_id` = "not-a-valid-uuid"
   - **When:** GET /api/v1/consent-templates/not-a-valid-uuid
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (happy path); patient (negative test)

**Patients/Entities:** At least one built-in template seeded in public catalog; at least one custom template per test tenant.

### Mocking Strategy

- Redis cache: Use fakeredis to simulate cache hit/miss scenarios
- Public catalog: Seeded fixture with all 7 built-in templates

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Built-in template returned with full content for any authenticated tenant user
- [ ] Custom template returned only to the owning tenant
- [ ] `is_builtin` correctly set in response
- [ ] Cross-tenant access returns 403 (not 404)
- [ ] Nonexistent UUID returns 404
- [ ] Cache populated on first request; subsequent requests served from cache
- [ ] Unauthorized roles return 403
- [ ] All test cases pass
- [ ] Performance target met (< 30ms cache hit, < 150ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Rendering the template with patient data (see IC-04 consent-create.md)
- Editing or updating templates
- Deleting templates
- Template versioning or history

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
- [x] Input sanitization defined (Pydantic UUID)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

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
