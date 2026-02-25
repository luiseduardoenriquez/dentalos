# Create Patient Spec

---

## Overview

**Feature:** Create a new patient record within a tenant clinic, including validation of document uniqueness, plan limit enforcement, and automatic odontogram state initialization based on patient age.

**Domain:** patients

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy.md), I-02 (database-architecture.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** None

---

## Endpoint

```
POST /api/v1/patients
```

**Rate Limiting:**
- 30 requests per minute per user
- Prevents bulk import abuse; bulk import has a separate endpoint

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
  "document_type": "string (required) — enum: cedula, curp, rut, passport, other",
  "document_number": "string (required) — max 30 chars",
  "first_name": "string (required) — max 100 chars",
  "last_name": "string (required) — max 100 chars",
  "birthdate": "string (required) — ISO 8601 date (YYYY-MM-DD)",
  "gender": "string (required) — enum: male, female, other",
  "phone": "string (required) — max 20 chars, E.164 recommended",
  "email": "string (optional) — max 320 chars, valid email format",
  "phone_secondary": "string (optional) — max 20 chars",
  "address": "string (optional) — max 500 chars",
  "city": "string (optional) — max 100 chars",
  "state_province": "string (optional) — max 100 chars",
  "emergency_contact_name": "string (optional) — max 200 chars",
  "emergency_contact_phone": "string (optional) — max 20 chars",
  "insurance_provider": "string (optional) — max 200 chars",
  "insurance_policy_number": "string (optional) — max 50 chars",
  "blood_type": "string (optional) — enum: A+, A-, B+, B-, AB+, AB-, O+, O-",
  "allergies": "string[] (optional) — list of known allergies",
  "chronic_conditions": "string[] (optional) — list of chronic conditions",
  "referral_source": "string (optional) — max 50 chars",
  "notes": "string (optional) — max 2000 chars"
}
```

**Example Request:**
```json
{
  "document_type": "cedula",
  "document_number": "1020304050",
  "first_name": "Maria",
  "last_name": "Garcia Lopez",
  "birthdate": "1990-05-15",
  "gender": "female",
  "phone": "+573001234567",
  "email": "maria.garcia@email.com",
  "city": "Bogota",
  "state_province": "Cundinamarca",
  "emergency_contact_name": "Carlos Garcia",
  "emergency_contact_phone": "+573009876543",
  "insurance_provider": "Sura EPS",
  "insurance_policy_number": "EPS-12345",
  "blood_type": "O+",
  "allergies": ["penicilina", "latex"],
  "chronic_conditions": ["diabetes tipo 2"],
  "referral_source": "recomendacion",
  "notes": "Paciente remitida por Dr. Rodriguez"
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
  "document_type": "string",
  "document_number": "string",
  "first_name": "string",
  "last_name": "string",
  "birthdate": "string (ISO 8601 date)",
  "gender": "string",
  "phone": "string",
  "email": "string | null",
  "phone_secondary": "string | null",
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
  "is_active": true,
  "odontogram_state": {
    "id": "uuid",
    "dentition_type": "string (adult | pediatric | mixed)"
  },
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)"
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
  "phone": "+573001234567",
  "email": "maria.garcia@email.com",
  "is_active": true,
  "odontogram_state": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "dentition_type": "adult"
  },
  "created_by": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
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
**When:** Missing or expired JWT token. Standard auth failure -- see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not in the allowed list (e.g., patient role attempting to create).

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para registrar pacientes."
}
```

#### 409 Conflict
**When:** A patient with the same document_type + document_number already exists in the tenant.

**Example:**
```json
{
  "error": "duplicate_patient",
  "message": "Ya existe un paciente con este tipo y numero de documento.",
  "details": {
    "document_type": "cedula",
    "document_number": "1020304050",
    "existing_patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails (invalid enum, future birthdate, etc.).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "birthdate": ["La fecha de nacimiento no puede ser en el futuro."],
    "document_type": ["Tipo de documento no valido. Opciones: cedula, curp, rut, passport, other."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 402 Payment Required
**When:** Tenant has reached the max_patients limit defined by their subscription plan.

**Example:**
```json
{
  "error": "plan_limit_reached",
  "message": "Ha alcanzado el limite de pacientes de su plan ({max_patients}). Actualice su plan para continuar.",
  "details": {
    "current_count": 500,
    "max_allowed": 500,
    "plan_name": "Profesional"
  }
}
```

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema (field types, enums, lengths).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (must be clinic_owner, doctor, assistant, or receptionist).
4. Count current active patients in tenant (`SELECT COUNT(*) FROM patients WHERE is_active = true`).
5. Look up tenant plan from `public.plans` and compare `current_count` against `max_patients`. If at limit, return 402.
6. Check document uniqueness: `SELECT id FROM patients WHERE document_type = :type AND document_number = :number`. If exists, return 409.
7. Calculate patient age from `birthdate` to determine dentition type.
8. Insert patient record into `patients` table with `created_by` set to current user ID.
9. Auto-create `odontogram_states` row: `adult` if age >= 12, `pediatric` if age < 6, `mixed` if 6 <= age < 12.
10. Write audit log entry (action: create, resource: patient, PHI: yes).
11. Invalidate patient list cache for the tenant.
12. Dispatch `patient.created` event to RabbitMQ.
13. Return 201 with the created patient record.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| document_type | Must be one of: cedula, curp, rut, passport, other | Tipo de documento no valido. |
| document_number | 1-30 chars, alphanumeric + hyphens only | Numero de documento no valido. |
| first_name | 1-100 chars, no leading/trailing whitespace | El nombre es obligatorio. |
| last_name | 1-100 chars, no leading/trailing whitespace | El apellido es obligatorio. |
| birthdate | Valid date, not in the future, not before 1900-01-01 | La fecha de nacimiento no es valida. |
| gender | Must be one of: male, female, other | Genero no valido. |
| phone | 5-20 chars, digits and + only | El telefono no es valido. |
| email | Valid email format (if provided) | El correo electronico no es valido. |
| blood_type | Must be one of: A+, A-, B+, B-, AB+, AB-, O+, O- (if provided) | Tipo de sangre no valido. |
| allergies | Max 50 items, each max 200 chars | Lista de alergias no valida. |
| chronic_conditions | Max 50 items, each max 200 chars | Lista de condiciones cronicas no valida. |

**Business Rules:**

- The unique constraint is `document_type + document_number` per tenant (not globally).
- Plan limit check counts only `is_active = true` patients to allow re-registering deactivated patients.
- The `created_by` field is always set server-side from the JWT; it cannot be supplied by the client.
- Odontogram dentition type: `age >= 12` -> adult, `6 <= age < 12` -> mixed, `age < 6` -> pediatric.
- Patient is created with `is_active = true`, `no_show_count = 0`, `portal_access = false`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Birthdate is today (newborn) | Accept; age = 0; dentition_type = pediatric. |
| Patient with same document exists but is deactivated | Return 409 (document uniqueness applies regardless of is_active). |
| Plan limit is exactly at max | Return 402 before inserting. |
| Empty allergies array `[]` | Accept; store as empty PostgreSQL array. |
| Document number with leading zeros | Preserve as-is (string field). |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `patients`: INSERT -- new patient record
- `odontogram_states`: INSERT -- auto-created odontogram state

**Example query (SQLAlchemy):**
```python
patient = Patient(
    document_type=data.document_type,
    document_number=data.document_number,
    first_name=data.first_name,
    last_name=data.last_name,
    birthdate=data.birthdate,
    gender=data.gender,
    phone=data.phone,
    created_by=current_user.id,
)
session.add(patient)
await session.flush()

odontogram = OdontogramState(
    patient_id=patient.id,
    dentition_type=determine_dentition_type(data.birthdate),
    last_updated_by=current_user.id,
)
session.add(odontogram)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:list:*`: INVALIDATE -- all paginated list caches
- `tenant:{tenant_id}:patients:count`: INVALIDATE -- patient count cache

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| patients | patient.created | { tenant_id, patient_id, created_by } | After successful insert |

### Audit Log

**Audit entry:** Yes -- see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** patient
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on create (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates list and count caches on successful create

### Database Performance

**Queries executed:** 3 (count check, uniqueness check, insert patient + insert odontogram in one transaction)

**Indexes required:**
- `patients.(document_type, document_number)` -- UNIQUE (already defined)
- `patients.is_active` -- INDEX (for count query)

**N+1 prevention:** Not applicable (single insert)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| first_name, last_name | Pydantic `strip()` + strip_tags | Prevent XSS in stored names |
| document_number | Pydantic validator: alphanumeric + hyphens only | Prevent injection via document IDs |
| notes | Pydantic `strip()` + bleach.clean | User-supplied free text |
| allergies[], chronic_conditions[] | Each item: strip + strip_tags | Array of free-text strings |
| phone, phone_secondary | Regex: `^\+?[0-9]{5,20}$` | Enforce phone format |
| email | Pydantic EmailStr validator | Standard email validation |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** first_name, last_name, document_number, birthdate, phone, email, address, emergency_contact_name, emergency_contact_phone, insurance_provider, insurance_policy_number, blood_type, allergies, chronic_conditions

**Audit requirement:** All access logged (write logged on create)

---

## Testing

### Test Cases

#### Happy Path
1. Create patient with all required fields
   - **Given:** Authenticated user with doctor role, tenant with available patient slots
   - **When:** POST /api/v1/patients with valid required fields
   - **Then:** 201 Created, patient record returned, odontogram_state created with adult dentition

2. Create patient with all optional fields
   - **Given:** Authenticated user with receptionist role
   - **When:** POST /api/v1/patients with all required + optional fields
   - **Then:** 201 Created, all fields persisted correctly

3. Create pediatric patient (age < 6)
   - **Given:** Authenticated user, patient birthdate = 3 years ago
   - **When:** POST /api/v1/patients
   - **Then:** 201 Created, odontogram_state.dentition_type = "pediatric"

4. Create mixed dentition patient (age 6-11)
   - **Given:** Authenticated user, patient birthdate = 8 years ago
   - **When:** POST /api/v1/patients
   - **Then:** 201 Created, odontogram_state.dentition_type = "mixed"

#### Edge Cases
1. Patient at plan limit boundary
   - **Given:** Tenant has 499/500 patients (plan max = 500)
   - **When:** POST /api/v1/patients
   - **Then:** 201 Created (exactly at limit after insert)

2. Empty optional arrays
   - **Given:** `allergies: [], chronic_conditions: []`
   - **When:** POST /api/v1/patients
   - **Then:** 201 Created with empty arrays stored

#### Error Cases
1. Duplicate document
   - **Given:** Patient with cedula 1020304050 already exists
   - **When:** POST /api/v1/patients with same document_type and document_number
   - **Then:** 409 Conflict with existing_patient_id

2. Plan limit exceeded
   - **Given:** Tenant has 500/500 patients
   - **When:** POST /api/v1/patients
   - **Then:** 402 Payment Required with plan details

3. Invalid role
   - **Given:** User with patient role
   - **When:** POST /api/v1/patients
   - **Then:** 403 Forbidden

4. Future birthdate
   - **Given:** birthdate = tomorrow
   - **When:** POST /api/v1/patients
   - **Then:** 422 with birthdate validation error

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant, receptionist, patient (for negative test)

**Patients/Entities:** Pre-existing patient with cedula "9999999999" for duplicate tests. Tenant with plan at max_patients limit.

### Mocking Strategy

- Redis cache: Use fakeredis for cache invalidation tests
- RabbitMQ: Mock publish call, assert payload structure
- Plan lookup: Fixture with known max_patients values

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient created with all required fields returns 201
- [ ] All optional fields are correctly persisted when provided
- [ ] Odontogram state auto-created with correct dentition type (adult/mixed/pediatric)
- [ ] Duplicate document_type + document_number returns 409
- [ ] Plan limit exceeded returns 402 with current count and max
- [ ] Unauthorized roles return 403
- [ ] Audit log entry written with PHI flag
- [ ] Patient list cache invalidated after create
- [ ] RabbitMQ patient.created event dispatched
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Bulk patient import (separate endpoint)
- Patient avatar upload (separate endpoint using file upload)
- Patient portal access provisioning (separate workflow)
- Patient merge/deduplication across tenants
- Patient data import from external systems

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
