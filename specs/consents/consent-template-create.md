# Consent Template Create Spec

---

## Overview

**Feature:** Create a custom informed consent template for a tenant clinic. Clinic owners can design templates with rich HTML content, placeholders for patient/doctor data, configurable required fields, and defined signature positions.

**Domain:** consents

**Priority:** High

**Dependencies:** IC-01 (consent-template-list.md), I-01 (multi-tenancy.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner can create templates. Doctors and assistants cannot.

---

## Endpoint

```
POST /api/v1/consent-templates
```

**Rate Limiting:**
- 20 requests per hour per user
- Template creation is infrequent; low limit prevents abuse

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "name": "string (required) — max 200 chars",
  "category": "string (required) — enum: general, surgery, sedation, orthodontics, implants, endodontics, pediatric",
  "description": "string (optional) — max 500 chars",
  "content": "string (required) — rich HTML with placeholders; max 50000 chars",
  "required_fields": "string[] (optional) — list of additional required field names; max 50 items",
  "signature_positions": {
    "patient": "object (required) — { label: string, required: boolean }",
    "doctor": "object (required) — { label: string, required: boolean }",
    "witness": "object (optional) — { label: string, required: boolean }"
  }
}
```

**Supported content placeholders:**
- `{{patient_name}}` — Full name of the patient
- `{{patient_cedula}}` — Patient document number
- `{{patient_age}}` — Patient age at time of consent creation
- `{{procedure}}` — Procedure description (entered when consent is created)
- `{{doctor_name}}` — Full name of the treating doctor
- `{{doctor_license}}` — Doctor's professional license number (Tarjeta Profesional)
- `{{clinic_name}}` — Clinic name from tenant profile
- `{{date}}` — Date the consent form is generated

**Example Request:**
```json
{
  "name": "Consentimiento Implante Osseointegrado Premium",
  "category": "implants",
  "description": "Template personalizado con informacion detallada de riesgos y alternativas para implantes.",
  "content": "<h1>CONSENTIMIENTO INFORMADO</h1><p>Yo, <strong>{{patient_name}}</strong>, identificado(a) con cedula {{patient_cedula}}, de {{patient_age}} anos de edad, por medio del presente documento autorizo al Dr. {{doctor_name}} (Tarjeta Profesional No. {{doctor_license}}) a realizar el procedimiento de implante osseointegrado.</p><p>Fecha: {{date}}</p>",
  "required_fields": ["procedure", "tooth_numbers"],
  "signature_positions": {
    "patient": { "label": "Firma del Paciente", "required": true },
    "doctor": { "label": "Firma del Odontologo Tratante", "required": true },
    "witness": { "label": "Firma del Testigo", "required": false }
  }
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "id": "uuid",
  "name": "string",
  "category": "string",
  "description": "string | null",
  "is_builtin": false,
  "content": "string (sanitized HTML)",
  "required_fields": "string[]",
  "signature_positions": {
    "patient": { "label": "string", "required": "boolean" },
    "doctor": { "label": "string", "required": "boolean" },
    "witness": { "label": "string", "required": "boolean" }
  },
  "fields_count": "integer",
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "e5f6a7b8-0000-4000-8000-000000000010",
  "name": "Consentimiento Implante Osseointegrado Premium",
  "category": "implants",
  "description": "Template personalizado con informacion detallada de riesgos y alternativas para implantes.",
  "is_builtin": false,
  "content": "<h1>CONSENTIMIENTO INFORMADO</h1><p>Yo, <strong>{{patient_name}}</strong>...</p>",
  "required_fields": ["procedure", "tooth_numbers"],
  "signature_positions": {
    "patient": { "label": "Firma del Paciente", "required": true },
    "doctor": { "label": "Firma del Odontologo Tratante", "required": true },
    "witness": { "label": "Firma del Testigo", "required": false }
  },
  "fields_count": 8,
  "created_by": "d4e5f6a7-0000-4000-8000-000000000004",
  "created_at": "2026-02-24T10:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or missing required fields.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not `clinic_owner`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede crear plantillas de consentimiento."
}
```

#### 409 Conflict
**When:** A template with the same name already exists for this tenant.

**Example:**
```json
{
  "error": "duplicate_template",
  "message": "Ya existe una plantilla con el nombre 'Consentimiento Implante Osseointegrado Premium'.",
  "details": {
    "existing_template_id": "e5f6a7b8-0000-4000-8000-000000000010"
  }
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails (invalid enum, content too long, invalid placeholder syntax).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "category": ["Categoria no valida. Opciones: general, surgery, sedation, orthodontics, implants, endodontics, pediatric."],
    "content": ["El contenido de la plantilla excede el maximo permitido de 50000 caracteres."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or content sanitization failure.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema (field types, lengths, enum values).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role — must be `clinic_owner`. Return 403 otherwise.
4. Check name uniqueness within tenant (`SELECT id FROM consent_templates WHERE name = :name`). Return 409 if exists.
5. Sanitize `content` HTML using `bleach.clean()` with an allowed-tags allowlist (h1–h6, p, strong, em, ul, ol, li, br, table, tr, td, th, span). Strip all script tags and event attributes.
6. Validate that placeholders in `content` use only the supported `{{variable}}` format — reject unknown placeholders.
7. Compute `fields_count` from the standard placeholders present in content plus `required_fields` count.
8. Insert record into tenant `consent_templates` table with `is_builtin = false`, `created_by = current_user.id`.
9. Invalidate tenant consent templates list cache in Redis.
10. Return 201 with the created template record.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| name | 1–200 chars, not blank | El nombre de la plantilla es obligatorio. |
| category | Must be one of the seven defined enums | Categoria no valida. |
| description | Max 500 chars (if provided) | La descripcion no puede exceder 500 caracteres. |
| content | Required, 10–50000 chars after sanitization | El contenido de la plantilla es obligatorio y no puede estar vacio. |
| content | May only contain allowed HTML tags (bleach allowlist) | El contenido contiene etiquetas HTML no permitidas. |
| content | Placeholders must match `{{allowed_key}}` pattern | La plantilla contiene marcadores de posicion desconocidos: {{unknown}}. |
| required_fields | Max 50 items, each item max 100 chars | La lista de campos requeridos no puede tener mas de 50 elementos. |
| signature_positions.patient | Required object with `label` (string) and `required` (boolean) | La posicion de firma del paciente es obligatoria. |
| signature_positions.doctor | Required object with `label` (string) and `required` (boolean) | La posicion de firma del medico es obligatoria. |

**Business Rules:**

- Built-in templates cannot be modified or deleted; this endpoint only creates tenant-custom templates.
- Name uniqueness is scoped per tenant (two tenants may have templates with the same name).
- `content` is sanitized server-side regardless of what the client sends — never trust client HTML.
- After sanitization, if the content becomes empty or shorter than 10 chars, reject with 422.
- `created_by` is always set server-side from JWT; it cannot be supplied by the client.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Content contains `<script>` tags | bleach strips them; sanitized content stored |
| Placeholder `{{unknown_var}}` present in content | Reject 422 with list of unknown placeholders |
| `required_fields` is empty array `[]` | Accept; stored as empty array |
| `witness` signature position omitted | Stored with `required: false` default |
| Template name matches a built-in template name | Allow; uniqueness check is tenant-scoped only |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `consent_templates`: INSERT — new custom template record

**Example query (SQLAlchemy):**
```python
template = ConsentTemplate(
    name=data.name,
    category=data.category,
    description=data.description,
    content=sanitized_content,
    required_fields=data.required_fields or [],
    signature_positions=data.signature_positions.model_dump(),
    is_builtin=False,
    fields_count=computed_fields_count,
    created_by=current_user.id,
)
session.add(template)
await session.flush()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:consent_templates:list:*`: INVALIDATE — all list cache variants for this tenant

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** consent_template
- **PHI involved:** No (template metadata only)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 800ms

### Caching Strategy
- **Strategy:** No caching on create (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates `tenant:{tenant_id}:consent_templates:list:*` on successful create

### Database Performance

**Queries executed:** 2 (uniqueness check, INSERT)

**Indexes required:**
- `{tenant}.consent_templates.name` — UNIQUE INDEX (per tenant)
- `{tenant}.consent_templates.category` — INDEX
- `{tenant}.consent_templates.is_builtin` — INDEX

**N+1 prevention:** Not applicable (single insert)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| name | Pydantic `strip()` + strip_tags | Prevent XSS in stored names |
| description | Pydantic `strip()` + bleach.clean | Free text field |
| content | bleach.clean() with strict allowlist | Primary XSS attack surface — sanitize rigorously |
| required_fields[] | Each item: strip + strip_tags, max 100 chars | Array of field name strings |
| signature_positions labels | Pydantic `strip()` + strip_tags | Label strings rendered in PDF |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** HTML content sanitized via bleach on input. Pydantic serialization escapes on output.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — template definitions are structural data, not patient data.

**Audit requirement:** Write-only logged (template creation event).

---

## Testing

### Test Cases

#### Happy Path
1. Create valid template with all fields
   - **Given:** Authenticated clinic_owner, unique template name
   - **When:** POST /api/v1/consent-templates with valid full payload
   - **Then:** 201 Created, template returned with sanitized content, `is_builtin: false`

2. Create template with minimal required fields only
   - **Given:** Authenticated clinic_owner
   - **When:** POST with only name, category, content, and patient + doctor signature positions
   - **Then:** 201 Created, `description: null`, `required_fields: []`, `witness.required: false`

3. Tenant list cache invalidated after create
   - **Given:** Cache populated from prior GET request
   - **When:** POST /api/v1/consent-templates succeeds
   - **Then:** Next GET /api/v1/consent-templates returns fresh data from DB (new template included)

#### Edge Cases
1. Content with disallowed HTML tags
   - **Given:** Content includes `<script>alert('xss')</script>` and `<style>` tags
   - **When:** POST /api/v1/consent-templates
   - **Then:** 201 Created, but stored content has script/style stripped by bleach

2. Unknown placeholder in content
   - **Given:** Content contains `{{unknown_field}}`
   - **When:** POST /api/v1/consent-templates
   - **Then:** 422 with details listing the unknown placeholder

3. Content exactly at max length (50000 chars)
   - **Given:** `content` is exactly 50000 characters
   - **When:** POST /api/v1/consent-templates
   - **Then:** 201 Created

#### Error Cases
1. Doctor role attempting to create template
   - **Given:** User with doctor role
   - **When:** POST /api/v1/consent-templates
   - **Then:** 403 Forbidden

2. Duplicate template name
   - **Given:** Template with name "Mi Template" already exists for tenant
   - **When:** POST /api/v1/consent-templates with same name
   - **Then:** 409 Conflict with existing template ID

3. Content exceeds max length
   - **Given:** `content` is 50001 characters
   - **When:** POST /api/v1/consent-templates
   - **Then:** 422 Unprocessable Entity

4. Missing `doctor` signature position
   - **Given:** Payload omits `signature_positions.doctor`
   - **When:** POST /api/v1/consent-templates
   - **Then:** 422 with signature_positions.doctor validation error

### Test Data Requirements

**Users:** clinic_owner (happy path); doctor, assistant (negative tests)

**Patients/Entities:** Tenant with no conflicting template names; pre-existing template for duplicate name test.

### Mocking Strategy

- Redis cache: Use fakeredis to verify cache invalidation
- bleach library: Use real bleach in tests (not mocked) to verify sanitization behavior

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Template created successfully with all fields returns 201
- [ ] `is_builtin` is always `false` for created templates
- [ ] `content` HTML sanitized via bleach before storage
- [ ] Unknown placeholders rejected with 422
- [ ] Duplicate name within tenant returns 409
- [ ] Only clinic_owner can create templates (403 for others)
- [ ] Tenant template list cache invalidated on success
- [ ] Audit log entry written for template creation
- [ ] All test cases pass
- [ ] Performance target met (< 300ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Updating or versioning existing templates
- Deleting templates
- Duplicating a built-in template as a starting point (separate workflow)
- Template preview rendering
- Template assignment to specific doctors

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
- [x] Input sanitization defined (bleach + Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced invalidation)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A for create)

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
