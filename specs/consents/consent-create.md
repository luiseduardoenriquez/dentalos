# Consent Create Spec

---

## Overview

**Feature:** Create a new informed consent form for a patient from a selected template. The system pre-fills patient demographic data, doctor information, and clinic details into the template content. The consent is created in `draft` status and requires subsequent signing (see IC-05).

**Domain:** consents

**Priority:** High

**Dependencies:** IC-01 (consent-template-list.md), IC-03 (consent-template-get.md), patients/patient-get.md, auth/authentication-rules.md, I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** None

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/consents
```

**Rate Limiting:**
- 60 requests per hour per user
- Prevents accidental consent form spam; legitimate usage is low-frequency

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient to create consent for | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "template_id": "string (required) — UUID of consent template (built-in or custom)",
  "procedure_description": "string (required) — description of the procedure; max 1000 chars",
  "tooth_numbers": "integer[] (optional) — FDI notation tooth numbers; valid range 11-85",
  "treatment_plan_id": "string (optional) — UUID of linked treatment plan",
  "scheduled_date": "string (optional) — ISO 8601 date (YYYY-MM-DD); date of scheduled procedure"
}
```

**Example Request:**
```json
{
  "template_id": "a1b2c3d4-0000-4000-8000-000000000001",
  "procedure_description": "Extraccion quirurgica de tercer molar inferior derecho impactado (diente 48)",
  "tooth_numbers": [48],
  "treatment_plan_id": "b2c3d4e5-0000-4000-8000-000000000020",
  "scheduled_date": "2026-03-15"
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
  "patient_id": "uuid",
  "template_id": "uuid",
  "template_name": "string",
  "procedure_description": "string",
  "tooth_numbers": "integer[] | null",
  "treatment_plan_id": "uuid | null",
  "scheduled_date": "string (ISO 8601 date) | null",
  "status": "string (draft)",
  "content_rendered": "string (HTML with patient data pre-filled, placeholders replaced)",
  "content_snapshot": "string (original template content at creation time)",
  "signatures": [],
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-0000-4000-8000-000000000030",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "template_id": "a1b2c3d4-0000-4000-8000-000000000001",
  "template_name": "Consentimiento General Odontologico",
  "procedure_description": "Extraccion quirurgica de tercer molar inferior derecho impactado (diente 48)",
  "tooth_numbers": [48],
  "treatment_plan_id": "b2c3d4e5-0000-4000-8000-000000000020",
  "scheduled_date": "2026-03-15",
  "status": "draft",
  "content_rendered": "<h1>CONSENTIMIENTO INFORMADO</h1><p>Yo, <strong>Maria Garcia Lopez</strong>, identificada con cedula 1020304050, de 35 anos de edad, autorizo al Dr. Juan Perez...</p>",
  "content_snapshot": "<h1>CONSENTIMIENTO INFORMADO</h1><p>Yo, <strong>{{patient_name}}</strong>...</p>",
  "signatures": [],
  "created_by": "d4e5f6a7-0000-4000-8000-000000000004",
  "created_at": "2026-02-24T14:30:00Z"
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
**When:** User role not in allowed list, or patient does not belong to the user's tenant.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para crear consentimientos para este paciente."
}
```

#### 404 Not Found
**When:** `patient_id` or `template_id` not found.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente o plantilla de consentimiento no encontrado.",
  "details": {
    "resource": "patient",
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }
}
```

#### 422 Unprocessable Entity
**When:** Validation fails (invalid tooth number range, future-only date validation, invalid UUID format).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "tooth_numbers": ["Los numeros de dientes deben estar en notacion FDI (11-85)."],
    "procedure_description": ["La descripcion del procedimiento es obligatoria."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or template rendering failure.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions (must be clinic_owner, doctor, or assistant).
4. Verify `patient_id` exists in the tenant schema and `is_active = true`. Return 404 if not found.
5. Fetch patient record to collect: `first_name`, `last_name`, `document_number`, `birthdate` (to compute age).
6. Resolve template: search `public.consent_templates` then tenant `consent_templates` by `template_id`. Return 404 if not found.
7. If `treatment_plan_id` provided, verify it exists in tenant schema and belongs to `patient_id`. Return 404 if not found.
8. Compute patient age at time of consent creation from `birthdate`.
9. Fetch treating doctor info: `doctor_name`, `doctor_license` from user profile linked to current user.
10. Fetch clinic info: `clinic_name` from tenant profile.
11. Render `content_rendered`: replace all placeholders in template content:
    - `{{patient_name}}` → `{first_name} {last_name}`
    - `{{patient_cedula}}` → `document_number`
    - `{{patient_age}}` → computed age
    - `{{procedure}}` → `procedure_description`
    - `{{doctor_name}}` → doctor's full name
    - `{{doctor_license}}` → doctor's tarjeta profesional number
    - `{{clinic_name}}` → tenant clinic name
    - `{{date}}` → current date in `dd/MM/yyyy` format (Colombia locale)
12. Store `content_snapshot` (original template content with placeholders, for record integrity).
13. Insert consent record with `status = draft`, `signatures = []`.
14. Write audit log entry.
15. Return 201 with created consent record.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Must be valid UUID v4 | El identificador del paciente no es valido. |
| template_id | Must be valid UUID v4 | El identificador de la plantilla no es valido. |
| procedure_description | Required, 5–1000 chars | La descripcion del procedimiento es obligatoria (5-1000 caracteres). |
| tooth_numbers | Each element must be in FDI range 11–85 (if provided) | Los numeros de dientes deben estar en notacion FDI (11-85). |
| tooth_numbers | Max 32 items in array | No se pueden especificar mas de 32 dientes. |
| treatment_plan_id | Valid UUID v4 if provided | El identificador del plan de tratamiento no es valido. |
| scheduled_date | Valid ISO 8601 date if provided; must not be in the past | La fecha programada no puede ser en el pasado. |

**Business Rules:**

- `status` is always set to `draft` on creation; it cannot be specified by the client.
- `content_snapshot` stores the raw template at creation time so future template edits do not alter existing consents.
- `content_rendered` stores the fully substituted HTML — it is what the patient and doctor review and sign.
- If the treating doctor's license number is not set in their profile, render `{{doctor_license}}` as `[NO REGISTRADO]` and log a warning.
- A patient can have multiple draft consents simultaneously (e.g., for different procedures).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor has no license number in profile | Render `[NO REGISTRADO]` in place of `{{doctor_license}}`, proceed with creation |
| `treatment_plan_id` provided but belongs to different patient | Return 404 (treatment plan not found for this patient) |
| Template contains a placeholder not in standard list | Leave the placeholder unreplaced (output includes literal `{{unknown}}`) |
| Patient is inactive (`is_active = false`) | Return 404 — inactive patients cannot receive new consents |
| `tooth_numbers` is empty array `[]` | Accept; treat as equivalent to not provided |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `consents`: INSERT — new consent record with `status = draft`

**Example query (SQLAlchemy):**
```python
consent = Consent(
    patient_id=patient_id,
    template_id=data.template_id,
    template_name=template.name,
    procedure_description=data.procedure_description,
    tooth_numbers=data.tooth_numbers or [],
    treatment_plan_id=data.treatment_plan_id,
    scheduled_date=data.scheduled_date,
    status=ConsentStatus.DRAFT,
    content_rendered=rendered_html,
    content_snapshot=template.content,
    created_by=current_user.id,
)
session.add(consent)
await session.flush()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:{patient_id}:consents:list:*`: INVALIDATE — patient consent list caches

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| consents | consent.created | { tenant_id, consent_id, patient_id, created_by } | After successful insert |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** consent
- **PHI involved:** Yes (patient name, document number rendered in content)

### Notifications

**Notifications triggered:** No (notification sent when consent is sent for signing — separate workflow)

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 600ms

### Caching Strategy
- **Strategy:** No caching on create (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates patient consent list cache on success

### Database Performance

**Queries executed:** 4 (patient lookup, template lookup, optional treatment plan lookup, consent INSERT)

**Indexes required:**
- `{tenant}.consents.patient_id` — INDEX
- `{tenant}.consents.status` — INDEX
- `{tenant}.consents.template_id` — INDEX

**N+1 prevention:** All lookups are single-row fetches by PK/FK; no loops.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| procedure_description | Pydantic `strip()` + bleach.clean (strip_tags) | Free text stored in consent and rendered in PDF |
| tooth_numbers | Pydantic integer list with range validator | No string injection possible |
| template_id, patient_id, treatment_plan_id | Pydantic UUID validator | Reject malformed UUIDs |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** `content_rendered` HTML is generated from pre-sanitized template content (sanitized at template creation). Procedure description is strip_tags'd before insertion into template.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_name, patient_cedula, patient_age (rendered into consent content), procedure_description

**Audit requirement:** All access logged (write logged on create).

---

## Testing

### Test Cases

#### Happy Path
1. Create consent with all fields
   - **Given:** Authenticated doctor, active patient, valid built-in template, valid treatment plan
   - **When:** POST /api/v1/patients/{patient_id}/consents with full payload
   - **Then:** 201 Created, `status: "draft"`, content_rendered has all placeholders replaced with real values

2. Create consent with required fields only
   - **Given:** Authenticated doctor, active patient, valid template
   - **When:** POST with template_id and procedure_description only
   - **Then:** 201 Created, `tooth_numbers: []`, `treatment_plan_id: null`, `scheduled_date: null`

3. Create consent using custom tenant template
   - **Given:** Authenticated doctor, tenant has a custom template
   - **When:** POST with custom template_id
   - **Then:** 201 Created, template_name reflects custom template

4. Placeholders correctly replaced in content_rendered
   - **Given:** Patient "Maria Garcia", cedula "1020304050", doctor "Juan Perez" with license "MP-12345"
   - **When:** POST /api/v1/patients/{patient_id}/consents
   - **Then:** content_rendered contains "Maria Garcia", "1020304050", "Juan Perez", "MP-12345" — no remaining `{{...}}` patterns

#### Edge Cases
1. Doctor with missing license number
   - **Given:** Treating doctor has no tarjeta_profesional set in profile
   - **When:** POST /api/v1/patients/{patient_id}/consents
   - **Then:** 201 Created, `{{doctor_license}}` rendered as `[NO REGISTRADO]`, warning logged

2. Empty tooth_numbers array
   - **Given:** `tooth_numbers: []`
   - **When:** POST /api/v1/patients/{patient_id}/consents
   - **Then:** 201 Created, `tooth_numbers: []` stored

#### Error Cases
1. Patient not found
   - **Given:** `patient_id` does not exist in tenant
   - **When:** POST /api/v1/patients/{nonexistent_id}/consents
   - **Then:** 404 Not Found

2. Inactive patient
   - **Given:** Patient exists but `is_active = false`
   - **When:** POST /api/v1/patients/{patient_id}/consents
   - **Then:** 404 Not Found

3. Template not found
   - **Given:** `template_id` does not exist in public or tenant templates
   - **When:** POST /api/v1/patients/{patient_id}/consents
   - **Then:** 404 Not Found

4. Invalid tooth number
   - **Given:** `tooth_numbers: [99]` (out of FDI range)
   - **When:** POST /api/v1/patients/{patient_id}/consents
   - **Then:** 422 Unprocessable Entity

5. Patient role attempting creation
   - **Given:** User with patient role
   - **When:** POST /api/v1/patients/{patient_id}/consents
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, doctor (with and without license number), assistant, patient (negative test)

**Patients/Entities:** Active patient; inactive patient; patient with treatment plan; built-in templates seeded; custom tenant template.

### Mocking Strategy

- Redis cache: Use fakeredis for cache invalidation assertion
- RabbitMQ: Mock publish, assert `consent.created` payload
- Template rendering: Integration test with real template data

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Consent created in `draft` status with correct patient data rendered into content
- [ ] All 8 standard placeholders replaced with live data in `content_rendered`
- [ ] `content_snapshot` stores original template HTML unchanged
- [ ] Doctor with missing license: consent created with `[NO REGISTRADO]` placeholder
- [ ] Invalid tooth numbers return 422
- [ ] Inactive patient returns 404
- [ ] Patient consent list cache invalidated after creation
- [ ] Audit log entry written with PHI flag
- [ ] RabbitMQ `consent.created` event dispatched
- [ ] All test cases pass
- [ ] Performance target met (< 300ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Signing the consent (see IC-05 consent-sign.md)
- Sending the consent to the patient for remote signing (separate notification workflow)
- Voiding a consent (see IC-09 consent-void.md)
- Generating the PDF (see IC-08 consent-pdf.md)

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
- [x] Input sanitization defined (Pydantic + bleach)
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
