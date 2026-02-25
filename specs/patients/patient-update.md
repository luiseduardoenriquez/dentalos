# Update Patient Spec

---

## Overview

**Feature:** Update an existing patient record by ID. All fields are mutable except `document_type` and `document_number` (immutable for legal and audit compliance). Changes are audit-logged with old_value/new_value diffs, and relevant caches are invalidated.

**Domain:** patients

**Priority:** Critical

**Dependencies:** P-01 (patient-create.md), P-02 (patient-get.md), I-02 (database-architecture.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** None

---

## Endpoint

```
PUT /api/v1/patients/{patient_id}
```

**Rate Limiting:**
- 30 requests per minute per user

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
| patient_id | Yes | uuid | Valid UUID v4 | The unique patient identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

All fields are optional (partial update semantics). Only provided fields are updated.

```json
{
  "first_name": "string (optional) -- max 100 chars",
  "last_name": "string (optional) -- max 100 chars",
  "birthdate": "string (optional) -- ISO 8601 date (YYYY-MM-DD)",
  "gender": "string (optional) -- enum: male, female, other",
  "phone": "string (optional) -- max 20 chars",
  "phone_secondary": "string | null (optional) -- max 20 chars",
  "email": "string | null (optional) -- max 320 chars",
  "address": "string | null (optional) -- max 500 chars",
  "city": "string | null (optional) -- max 100 chars",
  "state_province": "string | null (optional) -- max 100 chars",
  "emergency_contact_name": "string | null (optional) -- max 200 chars",
  "emergency_contact_phone": "string | null (optional) -- max 20 chars",
  "insurance_provider": "string | null (optional) -- max 200 chars",
  "insurance_policy_number": "string | null (optional) -- max 50 chars",
  "blood_type": "string | null (optional) -- enum: A+, A-, B+, B-, AB+, AB-, O+, O-",
  "allergies": "string[] | null (optional)",
  "chronic_conditions": "string[] | null (optional)",
  "referral_source": "string | null (optional) -- max 50 chars",
  "notes": "string | null (optional) -- max 2000 chars",
  "is_active": "boolean (optional) -- reactivation only; use P-05 for deactivation"
}
```

**Example Request:**
```json
{
  "phone": "+573009999999",
  "email": "maria.garcia.new@email.com",
  "insurance_provider": "Nueva EPS",
  "insurance_policy_number": "NEPS-67890",
  "allergies": ["penicilina", "latex", "ibuprofeno"],
  "notes": "Actualizado: cambio de aseguradora en febrero 2026"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "document_type": "string",
  "document_number": "string",
  "first_name": "string",
  "last_name": "string",
  "birthdate": "string (ISO 8601 date)",
  "gender": "string",
  "phone": "string",
  "phone_secondary": "string | null",
  "email": "string | null",
  "address": "string | null",
  "city": "string | null",
  "state_province": "string | null",
  "emergency_contact_name": "string | null",
  "emergency_contact_phone": "string | null",
  "insurance_provider": "string | null",
  "insurance_policy_number": "string | null",
  "blood_type": "string | null",
  "allergies": "string[]",
  "chronic_conditions": "string[]",
  "referral_source": "string | null",
  "notes": "string | null",
  "is_active": "boolean",
  "avatar_url": "string | null",
  "updated_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "document_type": "cedula",
  "document_number": "1020304050",
  "first_name": "Maria",
  "last_name": "Garcia Lopez",
  "birthdate": "1990-05-15",
  "gender": "female",
  "phone": "+573009999999",
  "phone_secondary": null,
  "email": "maria.garcia.new@email.com",
  "address": null,
  "city": "Bogota",
  "state_province": "Cundinamarca",
  "emergency_contact_name": "Carlos Garcia",
  "emergency_contact_phone": "+573009876543",
  "insurance_provider": "Nueva EPS",
  "insurance_policy_number": "NEPS-67890",
  "blood_type": "O+",
  "allergies": ["penicilina", "latex", "ibuprofeno"],
  "chronic_conditions": ["diabetes tipo 2"],
  "referral_source": "recomendacion",
  "notes": "Actualizado: cambio de aseguradora en febrero 2026",
  "is_active": true,
  "avatar_url": null,
  "updated_at": "2026-02-24T15:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Request body contains `document_type` or `document_number` fields (immutable), or empty body.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "No se puede modificar el tipo o numero de documento.",
  "details": {
    "document_type": ["Este campo no se puede modificar."],
    "document_number": ["Este campo no se puede modificar."]
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
  "message": "No tiene permisos para actualizar pacientes."
}
```

#### 404 Not Found
**When:** Patient with the given ID does not exist in the tenant schema.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "birthdate": ["La fecha de nacimiento no puede ser en el futuro."],
    "blood_type": ["Tipo de sangre no valido."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` is a valid UUID v4 format.
2. Validate request body against Pydantic schema. Reject if `document_type` or `document_number` is present.
3. Reject if the request body is empty (no fields to update).
4. Resolve tenant from JWT claims; set `search_path` to tenant schema.
5. Check user permissions via RBAC (clinic_owner, doctor, assistant, or receptionist).
6. Fetch existing patient record by ID. If not found, return 404.
7. Compute diff: for each provided field, compare old_value vs new_value. Skip fields where values are identical.
8. If no actual changes detected (all values identical), return 200 with existing record (no DB write).
9. If `birthdate` changed, recalculate dentition type and update `odontogram_states` if necessary.
10. Update `patients` record: set changed fields + `updated_at = now()`.
11. If `is_active` changed from `false` to `true` (reactivation), re-check plan limit (same as P-01 step 4-5).
12. Write audit log entry with old_value/new_value JSONB diff.
13. Invalidate Redis caches: patient profile, patient list.
14. Dispatch `patient.updated` event to RabbitMQ with changed fields.
15. Return 200 with the updated patient record.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | Identificador de paciente no valido. |
| document_type | Must NOT be present in body | Este campo no se puede modificar. |
| document_number | Must NOT be present in body | Este campo no se puede modificar. |
| first_name | 1-100 chars (if provided) | El nombre no es valido. |
| last_name | 1-100 chars (if provided) | El apellido no es valido. |
| birthdate | Valid date, not future (if provided) | La fecha de nacimiento no es valida. |
| gender | enum: male, female, other (if provided) | Genero no valido. |
| phone | 5-20 chars, digits and + (if provided) | El telefono no es valido. |
| email | Valid email format (if provided) | El correo electronico no es valido. |
| blood_type | enum: A+, A-, B+, B-, AB+, AB-, O+, O- (if provided) | Tipo de sangre no valido. |
| is_active | Boolean (if provided); true only (deactivation via P-05) | Use el endpoint de desactivacion para desactivar pacientes. |

**Business Rules:**

- `document_type` and `document_number` are immutable after creation (legal audit requirement).
- Setting `is_active = true` via this endpoint is allowed (reactivation), but setting `is_active = false` must use P-05 (patient-deactivate) because deactivation has additional side effects (cancelling appointments).
- If `birthdate` changes and the new age crosses a dentition threshold (e.g., from 11 to 12), the odontogram `dentition_type` is updated.
- The `updated_at` timestamp is always set server-side.
- A no-change update (all values identical to current) returns 200 without writing to the database.
- Null values are supported for optional fields to clear previously set data.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Empty request body `{}` | Return 400: no fields to update |
| All provided values identical to current | Return 200 without DB write or audit log |
| Setting email to null | Clears the email field (sets NULL in DB) |
| Reactivating patient when plan at limit | Return 402 (plan limit check applies) |
| Changing birthdate crosses dentition threshold | Update odontogram_states.dentition_type |
| Attempting is_active = false | Return 400 with redirect to P-05 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `patients`: UPDATE -- changed fields + updated_at
- `odontogram_states`: UPDATE (conditional) -- only if birthdate change affects dentition_type

**Example query (SQLAlchemy):**
```python
stmt = (
    update(Patient)
    .where(Patient.id == patient_id)
    .values(**changed_fields, updated_at=func.now())
)
await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:profile`: DELETE -- invalidate full profile cache
- `tenant:{tenant_id}:patients:list:*`: DELETE -- invalidate all list caches
- `tenant:{tenant_id}:patients:search:*`: DELETE -- invalidate search caches

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| patients | patient.updated | { tenant_id, patient_id, changed_fields, updated_by } | After successful update |

### Audit Log

**Audit entry:** Yes -- see infra/audit-logging.md

**If Yes:**
- **Action:** update
- **Resource:** patient
- **PHI involved:** Yes

**Audit payload includes:**
```json
{
  "old_value": { "phone": "+573001234567", "insurance_provider": "Sura EPS" },
  "new_value": { "phone": "+573009999999", "insurance_provider": "Nueva EPS" }
}
```

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on update (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates patient profile, list, and search caches

### Database Performance

**Queries executed:** 2-3 (1 SELECT existing, 1 UPDATE patient, conditional 1 UPDATE odontogram)

**Indexes required:**
- `patients.id` -- PRIMARY KEY (already defined)
- `odontogram_states.patient_id` -- UNIQUE (already defined)

**N+1 prevention:** Not applicable (single record update)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID |
| first_name, last_name | Pydantic strip + strip_tags | Prevent XSS |
| notes | Pydantic strip + bleach.clean | Free text |
| allergies[], chronic_conditions[] | Each item: strip + strip_tags | Array items |
| phone, phone_secondary | Regex: `^\+?[0-9]{5,20}$` | Phone format |
| email | Pydantic EmailStr validator | Standard email |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** All patient fields are PHI. The audit log records old_value and new_value for changed PHI fields.

**Audit requirement:** All updates logged with field-level diff (old_value/new_value)

---

## Testing

### Test Cases

#### Happy Path
1. Update single field
   - **Given:** Existing patient, user with doctor role
   - **When:** PUT /api/v1/patients/{id} with `{"phone": "+573009999999"}`
   - **Then:** 200 OK, phone updated, audit log contains old/new phone

2. Update multiple fields
   - **Given:** Existing patient
   - **When:** PUT with phone, email, insurance_provider, allergies
   - **Then:** 200 OK, all fields updated, audit log contains all changes

3. Clear optional field with null
   - **Given:** Patient with email set
   - **When:** PUT with `{"email": null}`
   - **Then:** 200 OK, email is null in response and DB

4. Reactivate patient
   - **Given:** Deactivated patient, plan has capacity
   - **When:** PUT with `{"is_active": true}`
   - **Then:** 200 OK, is_active = true

#### Edge Cases
1. No actual changes
   - **Given:** Patient with phone "+573001234567"
   - **When:** PUT with `{"phone": "+573001234567"}` (same value)
   - **Then:** 200 OK, no DB write, no audit log entry

2. Birthdate change affects dentition
   - **Given:** Patient age 11 (mixed), new birthdate makes age 13 (adult)
   - **When:** PUT with new birthdate
   - **Then:** 200 OK, odontogram_states.dentition_type updated to "adult"

3. Reactivation at plan limit
   - **Given:** Deactivated patient, tenant at max_patients
   - **When:** PUT with `{"is_active": true}`
   - **Then:** 402 Payment Required

#### Error Cases
1. Attempt to change document_type
   - **Given:** Existing patient
   - **When:** PUT with `{"document_type": "passport"}`
   - **Then:** 400 Bad Request

2. Attempt to change document_number
   - **Given:** Existing patient
   - **When:** PUT with `{"document_number": "9999999"}`
   - **Then:** 400 Bad Request

3. Empty body
   - **Given:** Existing patient
   - **When:** PUT with `{}`
   - **Then:** 400 Bad Request

4. Attempt to deactivate via update
   - **Given:** Active patient
   - **When:** PUT with `{"is_active": false}`
   - **Then:** 400 Bad Request with message to use deactivation endpoint

5. Patient not found
   - **Given:** Non-existent patient_id
   - **When:** PUT /api/v1/patients/{random_uuid}
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant, receptionist

**Patients/Entities:** Active patient with full profile, deactivated patient for reactivation tests. Tenant at plan limit for reactivation limit test.

### Mocking Strategy

- Redis cache: Use fakeredis for invalidation verification
- RabbitMQ: Mock publish call, assert changed_fields in payload
- Plan lookup: Fixture with known max_patients for reactivation test

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Single and multiple field updates work correctly
- [ ] document_type and document_number are rejected if present in body
- [ ] Empty body returns 400
- [ ] No-change update returns 200 without DB write
- [ ] Audit log records old_value/new_value diff for changed fields
- [ ] Reactivation (is_active: true) respects plan limits
- [ ] Deactivation (is_active: false) rejected with message to use P-05
- [ ] Birthdate change triggers dentition type recalculation
- [ ] Cache invalidated (patient profile, list, search)
- [ ] RabbitMQ event dispatched with changed_fields
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Patient avatar upload/update (separate file upload endpoint)
- Patient deactivation (see P-05, patient-deactivate.md)
- Patient portal access changes (separate workflow)
- Bulk patient updates (separate endpoint)
- Document type/number change (requires admin override process, out of scope)

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
- [x] Pagination applied where needed (N/A for update)

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
