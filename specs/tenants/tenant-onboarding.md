# Tenant Onboarding Wizard Spec

---

## Overview

**Feature:** Multi-step onboarding wizard for new tenants. The clinic_owner completes 4 steps: step 1 (clinic info), step 2 (first doctor profile), step 3 (odontogram preference), step 4 (optional patient CSV import). Each POST advances the onboarding_step counter. The endpoint validates the current step, updates tenant settings accordingly, and returns the next step or completion status.

**Domain:** tenants

**Priority:** Critical

**Spec ID:** T-10

**Dependencies:** T-01 (tenant-provision.md), T-06 (tenant-settings-get.md), T-07 (tenant-settings-update.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only accessible when `onboarding_step < 4`. After completion, returns 409 Conflict.

---

## Endpoint

```
POST /api/v1/onboarding
```

**Rate Limiting:**
- 30 requests per minute per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | application/json or multipart/form-data (step 4) | application/json |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

The request body varies per step. The `step` field is always required.

**Step 1 — Clinic Info:**
```json
{
  "step": 1,
  "clinic_name": "string (required) — clinic display name",
  "address": "string (optional) — physical address",
  "phone": "string (required) — clinic phone",
  "country": "string (required) — ISO 3166-1 alpha-2 (confirm or change)",
  "timezone": "string (optional) — IANA timezone"
}
```

**Step 2 — First Doctor Profile:**
```json
{
  "step": 2,
  "doctor_name": "string (required) — full name",
  "doctor_email": "string (required) — professional email",
  "professional_license": "string (optional) — tarjeta profesional or equivalent",
  "specialties": ["string (optional) — e.g. 'endodoncia', 'ortodoncia'"]
}
```

**Step 3 — Odontogram Preference:**
```json
{
  "step": 3,
  "odontogram_mode": "string (required) — classic or anatomic",
  "default_appointment_duration_min": "integer (optional) — 15, 30, 45, 60"
}
```

**Step 4 — Patient Import (optional):**
```json
{
  "step": 4,
  "skip_import": "boolean (optional, default false) — skip CSV import",
  "csv_file": "file (optional) — CSV with patient data (multipart/form-data)"
}
```

**Example Request (Step 1):**
```json
{
  "step": 1,
  "clinic_name": "Clínica Dental Sonrisa",
  "phone": "+573001234567",
  "country": "CO",
  "address": "Calle 100 #15-20, Bogotá"
}
```

**Example Request (Step 3):**
```json
{
  "step": 3,
  "odontogram_mode": "classic",
  "default_appointment_duration_min": 30
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "current_step": "integer — the step just completed",
  "next_step": "integer | null — next step to complete, null if done",
  "onboarding_complete": "boolean",
  "message": "string",
  "data": "object — step-specific response data"
}
```

**Example (Step 1 completed):**
```json
{
  "current_step": 1,
  "next_step": 2,
  "onboarding_complete": false,
  "message": "Información de la clínica guardada. Ahora configure su primer doctor.",
  "data": {
    "clinic_name": "Clínica Dental Sonrisa",
    "country": "CO",
    "timezone": "America/Bogota"
  }
}
```

**Example (Step 2 completed):**
```json
{
  "current_step": 2,
  "next_step": 3,
  "onboarding_complete": false,
  "message": "Perfil del doctor creado exitosamente. Ahora seleccione sus preferencias.",
  "data": {
    "doctor_id": "d1e2f3a4-b5c6-7890-abcd-ef1234567890",
    "doctor_name": "Dr. Carlos López",
    "doctor_email": "carlos@clinicasonrisa.com"
  }
}
```

**Example (Step 3 completed):**
```json
{
  "current_step": 3,
  "next_step": 4,
  "onboarding_complete": false,
  "message": "Preferencias guardadas. Opcionalmente, importe sus pacientes existentes.",
  "data": {
    "odontogram_mode": "classic",
    "default_appointment_duration_min": 30
  }
}
```

**Example (Step 4 completed — with import):**
```json
{
  "current_step": 4,
  "next_step": null,
  "onboarding_complete": true,
  "message": "¡Bienvenido a DentalOS! La importación de pacientes se procesará en segundo plano. Recibirá una notificación cuando finalice.",
  "data": {
    "import_job_id": "j1k2l3m4-n5o6-7890-pqrs-t12345678901",
    "patients_in_csv": 150,
    "estimated_time_seconds": 30
  }
}
```

**Example (Step 4 completed — skipped import):**
```json
{
  "current_step": 4,
  "next_step": null,
  "onboarding_complete": true,
  "message": "¡Bienvenido a DentalOS! Su clínica está lista. Puede agregar pacientes manualmente.",
  "data": {
    "import_skipped": true
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields for the step, or invalid step number.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Datos de entrada inválidos para el paso 1.",
  "details": {
    "clinic_name": ["El nombre de la clínica es obligatorio."],
    "phone": ["El teléfono de la clínica es obligatorio."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT.

#### 403 Forbidden
**When:** User is not clinic_owner, or tenant is suspended.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clínica puede completar el proceso de configuración."
}
```

#### 409 Conflict
**When:** Onboarding already completed (onboarding_step >= 4), or step out of sequence.

**Example (already complete):**
```json
{
  "error": "onboarding_complete",
  "message": "El proceso de configuración ya fue completado. Use la sección de ajustes para realizar cambios."
}
```

**Example (wrong step):**
```json
{
  "error": "step_out_of_sequence",
  "message": "No se puede completar el paso 3. Primero complete el paso 2."
}
```

#### 413 Payload Too Large
**When:** CSV file exceeds 10MB.

**Example:**
```json
{
  "error": "file_too_large",
  "message": "El archivo CSV no debe superar 10 MB."
}
```

#### 422 Unprocessable Entity
**When:** Validation failures, invalid CSV format, or plan restriction violated.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validación.",
  "details": {
    "odontogram_mode": ["El modo anatómico no está disponible en su plan actual."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

---

## Business Logic

**Step-by-step process:**

1. Extract tenant_id and user_id from JWT claims.
2. Resolve tenant context via TenantMiddleware.
3. Verify user role is `clinic_owner`.
4. Load current `onboarding_step` from `public.tenants`.
5. If `onboarding_step >= 4`, return 409 (already complete).
6. Validate that request `step` == `onboarding_step + 1` (sequential only).
7. Process step-specific logic (see below).
8. Update `public.tenants.onboarding_step = step`.
9. Invalidate cache.
10. Return response with next step info.

**Step 1 — Clinic Info:**
1. Validate clinic_name, phone (required), country, address, timezone.
2. Update `public.tenants`: name, phone, address, country (if changed), timezone.
3. Deep merge settings with any defaults for the country.
4. Advance onboarding_step to 1.

**Step 2 — First Doctor Profile:**
1. Validate doctor_name, doctor_email (required).
2. If the clinic_owner is also the doctor (owner_email == doctor_email):
   - Update the existing clinic_owner user record with professional_license and specialties.
3. If different email:
   - Create a new user in `{schema}.users` with role = 'doctor'.
   - Set temporary password, dispatch welcome email.
4. Advance onboarding_step to 2.

**Step 3 — Odontogram Preference:**
1. Validate odontogram_mode.
2. If `anatomic` and plan does not include `odontogram_anatomic`: return 422.
3. Update `public.tenants.settings.odontogram_mode`.
4. Update `public.tenants.settings.default_appointment_duration_min`.
5. Advance onboarding_step to 3.

**Step 4 — Patient Import:**
1. If `skip_import = true`: advance to step 4, mark complete, return.
2. If CSV file provided:
   a. Validate file type (CSV only), size (max 10MB).
   b. Parse header row, validate columns: nombre, apellido, documento_tipo, documento_numero, telefono, email, fecha_nacimiento.
   c. Validate row count does not exceed plan's max_patients limit.
   d. Dispatch async import job to RabbitMQ.
   e. Advance onboarding_step to 4.
3. If neither skip_import nor csv_file: return 400 (must skip or provide file).

**CSV column mapping:**

| CSV Column | Patient Field | Required |
|------------|--------------|----------|
| nombre | first_name | Yes |
| apellido | last_name | Yes |
| documento_tipo | document_type | Yes |
| documento_numero | document_number | Yes |
| telefono | phone | No |
| email | email | No |
| fecha_nacimiento | birthdate (YYYY-MM-DD) | Yes |
| genero | gender (M/F/O) | No |

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| step | Integer 1-4 | Número de paso inválido. Debe ser entre 1 y 4. |
| clinic_name | 2-200 chars (step 1) | El nombre de la clínica debe tener entre 2 y 200 caracteres. |
| phone | E.164 or 7-20 digits (step 1) | Formato de teléfono inválido. |
| country | ISO 3166-1 alpha-2 (step 1) | Código de país inválido. |
| doctor_name | 2-200 chars (step 2) | El nombre del doctor debe tener entre 2 y 200 caracteres. |
| doctor_email | Valid email (step 2) | Formato de correo electrónico inválido. |
| odontogram_mode | Enum: classic, anatomic (step 3) | Modo de odontograma inválido. |
| default_appointment_duration_min | Enum: 15, 30, 45, 60 (step 3) | Duración de cita inválida. |
| csv_file | CSV, max 10MB, max plan patients (step 4) | Formato de archivo inválido o excede el límite del plan. |

**Business Rules:**

- Steps must be completed in order (1 -> 2 -> 3 -> 4). Cannot skip steps.
- Step 4 can be skipped by setting `skip_import = true`.
- Once completed (step 4), onboarding cannot be re-entered. Use settings endpoints instead.
- If the owner is also the doctor (step 2), no new user is created — the existing user is updated.
- CSV import is async. The response includes a job ID for tracking.
- Patient import respects plan limits. If CSV has more patients than max_patients, return 422.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Re-submitting the same step | 409 Conflict (step already completed). |
| Owner email matches doctor email in step 2 | Update existing user, do not create duplicate. |
| CSV has duplicate document_numbers | Import job deduplicates; duplicates are skipped with a warning in the job result. |
| CSV has more rows than plan limit | 422 before dispatching import job. |
| Network failure during step 2 user creation | Transaction rolls back. onboarding_step stays at 1. User can retry. |
| Step 4 with empty CSV (headers only) | Treated as skip_import = true. |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `public.tenants`: UPDATE — name, phone, address, country, timezone, settings, onboarding_step, updated_at

**Tenant schema tables affected:**
- `{schema}.users`: INSERT or UPDATE (step 2 — doctor profile)
- `{schema}.patients`: INSERT via async job (step 4 — CSV import)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:info`: INVALIDATE after each step
- `tenant:{tenant_id}:settings:resolved`: INVALIDATE after steps 1, 3

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | user.welcome_doctor | { doctor_email, doctor_name, tenant_name, temp_password } | Step 2, if new doctor user created |
| data_import | patients.csv_import | { tenant_id, schema_name, job_id, file_path, row_count } | Step 4, if CSV provided |

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** tenant_onboarding
- **PHI involved:** No (step 1-3). Yes for step 4 (patient data import).

### Notifications

**Notifications triggered:** Yes (conditional)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | welcome_doctor | doctor_email | Step 2, new doctor user created |
| in-app | import_complete | clinic_owner | Step 4 async import finished |
| in-app | import_failed | clinic_owner | Step 4 async import failed |

---

## Performance

### Expected Response Time
- **Target:** < 300ms (steps 1, 2, 3), < 2000ms (step 4 with CSV validation)
- **Maximum acceptable:** < 500ms (steps 1-3), < 5000ms (step 4)

### Caching Strategy
- **Strategy:** Cache invalidation after each step
- **Cache key:** `tenant:{tenant_id}:info`
- **TTL:** Invalidated
- **Invalidation:** After each step completion

### Database Performance

**Queries executed:** 2-3 per step (load tenant, validate, update/insert)

**Indexes required:**
- `public.tenants.id` — PRIMARY KEY
- `{schema}.users.email` — UNIQUE (for doctor duplicate check)

**N+1 prevention:** Not applicable (single resource operations per step)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| clinic_name | Pydantic strip, HTML stripped | Max 200 chars |
| phone | Pydantic regex validator | E.164 or digits |
| doctor_name | Pydantic strip, HTML stripped | Max 200 chars |
| doctor_email | Pydantic EmailStr, lowercase | Normalized |
| csv_file | MIME type check, size limit, header validation | CSV only, max 10MB |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. CSV data is inserted via parameterized batch inserts.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Step 4 CSV contains patient data (names, document numbers, birthdates).

**Audit requirement:** All access logged for step 4. PHI from CSV is not logged — only metadata (row count, job ID).

---

## Testing

### Test Cases

#### Happy Path
1. Complete step 1
   - **Given:** New tenant, onboarding_step = 0
   - **When:** POST with step=1 and clinic info
   - **Then:** 200 OK, onboarding_step = 1, next_step = 2

2. Complete step 2 (new doctor)
   - **Given:** onboarding_step = 1, doctor_email != owner_email
   - **When:** POST with step=2 and doctor info
   - **Then:** 200 OK, new user created, welcome email dispatched

3. Complete step 2 (owner is doctor)
   - **Given:** onboarding_step = 1, doctor_email == owner_email
   - **When:** POST with step=2
   - **Then:** 200 OK, existing user updated (no duplicate)

4. Complete step 3
   - **Given:** onboarding_step = 2
   - **When:** POST with step=3 and odontogram_mode=classic
   - **Then:** 200 OK, settings updated

5. Complete step 4 with CSV
   - **Given:** onboarding_step = 3, CSV with 50 patients
   - **When:** POST multipart with step=4 and csv_file
   - **Then:** 200 OK, import job dispatched, onboarding_complete=true

6. Skip step 4
   - **Given:** onboarding_step = 3
   - **When:** POST with step=4 and skip_import=true
   - **Then:** 200 OK, onboarding_complete=true

#### Edge Cases
1. Step out of sequence
   - **Given:** onboarding_step = 1
   - **When:** POST with step=3
   - **Then:** 409 Conflict (step_out_of_sequence)

2. CSV exceeds plan limit
   - **Given:** Plan max_patients = 50, CSV has 100 rows
   - **When:** POST step 4
   - **Then:** 422 Unprocessable Entity

#### Error Cases
1. Onboarding already complete
   - **Given:** onboarding_step = 4
   - **When:** POST any step
   - **Then:** 409 Conflict (onboarding_complete)

2. Non-owner role
   - **Given:** User with doctor role
   - **When:** POST
   - **Then:** 403 Forbidden

3. Missing required fields
   - **Given:** Step 1 without clinic_name
   - **When:** POST
   - **Then:** 400 Bad Request

4. Anatomic odontogram on free plan
   - **Given:** Free plan, step 3
   - **When:** POST with odontogram_mode=anatomic
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** clinic_owner user (with and without doctor role overlap)

**Entities:** Active tenant with onboarding_step at 0, 1, 2, 3, and 4. Sample CSV files (valid and invalid).

### Mocking Strategy

- RabbitMQ: Mock queue publisher for import jobs and email jobs
- S3/file storage: Mock file upload for CSV
- Email service: Mock SMTP

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] All 4 onboarding steps can be completed in sequence
- [ ] Step 4 CSV import dispatches async job correctly
- [ ] Step 4 can be skipped
- [ ] Out-of-sequence steps return 409
- [ ] Completed onboarding cannot be re-entered
- [ ] Plan constraints enforced (odontogram_anatomic, max_patients)
- [ ] Doctor user creation works for new email and owner-is-doctor case
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed
- [ ] Audit logging verified for step 4 (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Resetting onboarding (admin feature, separate spec)
- CSV import progress tracking (separate polling endpoint)
- Import error report download
- Onboarding for non-owner users (they skip onboarding)
- Welcome tour / UI walkthrough (frontend-only)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (per-step Pydantic schemas)
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
- [x] Input sanitization defined (Pydantic + CSV validation)
- [x] SQL injection prevented (SQLAlchemy ORM, parameterized CSV inserts)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for step 4 (PHI import)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized (indexes listed)
- [x] Pagination not needed

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (import job tracking)

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
