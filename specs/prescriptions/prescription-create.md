# Prescription Create Spec

---

## Overview

**Feature:** Create a digital dental prescription for a patient. Supports multiple medications per prescription, each with dosage, frequency, duration, route, and instructions. Auto-includes doctor credentials (name, professional license / Tarjeta Profesional) and clinic information, as required by Colombian regulation.

**Domain:** prescriptions

**Priority:** Medium

**Dependencies:** patients/patient-get.md, RX-05 (prescription-medication-search.md), auth/authentication-rules.md, I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor ONLY
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only doctors can create prescriptions. Assistants and clinic_owner cannot prescribe medications.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/prescriptions
```

**Rate Limiting:**
- 60 requests per hour per user
- Prevents accidental duplicate prescription creation

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
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient to prescribe to | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "medications": [
    {
      "medication_id": "string (optional) — UUID from public.catalog_medications; provide this OR medication_name",
      "medication_name": "string (optional) — free-text name if not in catalog; max 200 chars",
      "dosage": "string (required) — e.g., '500mg', '250mg/5ml'; max 100 chars",
      "frequency": "string (required) — e.g., 'Cada 8 horas', 'Dos veces al dia'; max 200 chars",
      "duration": "string (required) — e.g., '5 dias', '1 semana'; max 100 chars",
      "route": "string (required) — enum: oral, topical, inhalation, injection, sublingual, other",
      "instructions": "string (optional) — special instructions; max 500 chars"
    }
  ],
  "diagnosis_id": "string (optional) — UUID of linked clinical diagnosis record",
  "notes": "string (optional) — general prescription notes; max 1000 chars"
}
```

**Example Request:**
```json
{
  "medications": [
    {
      "medication_id": "m1a2b3c4-0000-4000-8000-000000000001",
      "dosage": "500mg",
      "frequency": "Cada 8 horas",
      "duration": "7 dias",
      "route": "oral",
      "instructions": "Tomar con los alimentos para evitar irritacion gastrica."
    },
    {
      "medication_name": "Clorhexidina 0.12% Enjuague Bucal",
      "dosage": "15ml",
      "frequency": "Dos veces al dia",
      "duration": "10 dias",
      "route": "oral",
      "instructions": "Enjuagarse durante 30 segundos y no tragar. No comer ni beber por 30 minutos despues."
    }
  ],
  "diagnosis_id": null,
  "notes": "Post extraccion quirurgica diente 48. Iniciar antibiotico de inmediato."
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
  "doctor_id": "uuid",
  "doctor_name": "string",
  "doctor_license": "string — Tarjeta Profesional number",
  "doctor_specialty": "string | null",
  "clinic_name": "string",
  "clinic_address": "string | null",
  "clinic_phone": "string | null",
  "medications": [
    {
      "id": "uuid",
      "medication_id": "uuid | null",
      "medication_name": "string",
      "generic_name": "string | null",
      "dosage": "string",
      "frequency": "string",
      "duration": "string",
      "route": "string",
      "instructions": "string | null",
      "order_number": "integer — 1-based sequence for Rp/ display"
    }
  ],
  "diagnosis_id": "uuid | null",
  "notes": "string | null",
  "prescribed_at": "string (ISO 8601 datetime)",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "rx1a2b3c-0000-4000-8000-000000000010",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "d4e5f6a7-0000-4000-8000-000000000004",
  "doctor_name": "Juan Carlos Perez Rodriguez",
  "doctor_license": "MP-12345-COL",
  "doctor_specialty": "Cirugia Oral y Maxilofacial",
  "clinic_name": "Clinica Dental Sonrisa",
  "clinic_address": "Cra 7 # 45-10, Bogota",
  "clinic_phone": "+571 3456789",
  "medications": [
    {
      "id": "rxm1a2b3-0000-4000-8000-000000000020",
      "medication_id": "m1a2b3c4-0000-4000-8000-000000000001",
      "medication_name": "Amoxicilina",
      "generic_name": "amoxicillin",
      "dosage": "500mg",
      "frequency": "Cada 8 horas",
      "duration": "7 dias",
      "route": "oral",
      "instructions": "Tomar con los alimentos para evitar irritacion gastrica.",
      "order_number": 1
    },
    {
      "id": "rxm2b3c4-0000-4000-8000-000000000021",
      "medication_id": null,
      "medication_name": "Clorhexidina 0.12% Enjuague Bucal",
      "generic_name": null,
      "dosage": "15ml",
      "frequency": "Dos veces al dia",
      "duration": "10 dias",
      "route": "oral",
      "instructions": "Enjuagarse durante 30 segundos y no tragar.",
      "order_number": 2
    }
  ],
  "diagnosis_id": null,
  "notes": "Post extraccion quirurgica diente 48. Iniciar antibiotico de inmediato.",
  "prescribed_at": "2026-02-24T14:30:00Z",
  "created_at": "2026-02-24T14:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or `medications` array is empty.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "La prescripcion debe incluir al menos un medicamento.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not `doctor`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo los medicos pueden crear prescripciones."
}
```

#### 404 Not Found
**When:** `patient_id` not found, or `diagnosis_id` not found for this patient.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Validation errors (invalid route enum, dosage missing, medication_id not in catalog).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "medications[0].route": ["Via de administracion no valida. Opciones: oral, topical, inhalation, injection, sublingual, other."],
    "medications[0].dosage": ["La dosis es obligatoria."],
    "medications[1].medication_id": ["Medicamento no encontrado en el catalogo. Verifique el ID o use medication_name."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema.
2. Verify `medications` array is not empty (min 1, max 10 items). Return 400 if empty.
3. Resolve tenant from JWT claims; set `search_path` to tenant schema.
4. Check user role — must be `doctor`. Return 403 otherwise.
5. Verify `patient_id` exists and `is_active = true` in tenant schema. Return 404 if not.
6. For each medication item in `medications`:
   a. If `medication_id` is provided: validate it exists in `public.catalog_medications`. Return 422 if not found. Populate `medication_name` and `generic_name` from catalog.
   b. If only `medication_name` is provided: accept as free-text (off-catalog medication). Set `generic_name = null`.
   c. If neither provided: return 422 validation error.
7. If `diagnosis_id` provided: verify it exists in tenant schema and belongs to `patient_id`. Return 404 if not.
8. Fetch doctor profile from tenant `users` table: `full_name`, `tarjeta_profesional` (license), `specialty`.
9. If doctor's `tarjeta_profesional` is not set: proceed but log warning. Set `doctor_license = "[NO REGISTRADO]"`.
10. Fetch tenant clinic info: `clinic_name`, `address`, `phone`.
11. Insert prescription record into `prescriptions` table with `prescribed_at = server UTC now()`.
12. Insert each medication as a row in `prescription_medications` table with sequential `order_number` (1-based).
13. Write audit log entry.
14. Invalidate patient prescription list cache.
15. Dispatch `prescription.created` event to RabbitMQ.
16. Return 201 with full prescription detail.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| medications | Required array, min 1 item, max 10 items | La prescripcion debe incluir al menos un medicamento (maximo 10). |
| medications[n].medication_id or medication_name | At least one must be provided per medication item | Debe especificar medication_id o medication_name para cada medicamento. |
| medications[n].dosage | Required, 1–100 chars | La dosis es obligatoria. |
| medications[n].frequency | Required, 1–200 chars | La frecuencia es obligatoria. |
| medications[n].duration | Required, 1–100 chars | La duracion es obligatoria. |
| medications[n].route | Required, must be one of enum values | Via de administracion no valida. |
| medications[n].instructions | Max 500 chars (if provided) | Las instrucciones no pueden exceder 500 caracteres. |
| notes | Max 1000 chars (if provided) | Las notas no pueden exceder 1000 caracteres. |

**Business Rules:**

- Doctor credentials (name, license, specialty) are auto-included server-side from the doctor's user profile. The client cannot override these values.
- Clinic information is auto-included from the tenant profile.
- `prescribed_at` is always set server-side to the current UTC timestamp.
- `medication_id` is validated against the shared `public.catalog_medications` table (cross-tenant catalog).
- If `medication_id` is provided, `medication_name` is populated from the catalog (client-supplied `medication_name` is ignored when `medication_id` is given).
- Prescriptions are immutable after creation — no editing endpoint. A new prescription must be created to correct errors.
- `order_number` is assigned sequentially (1, 2, 3...) in the order medications are provided in the request.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor has no tarjeta_profesional set | Create prescription with `doctor_license = "[NO REGISTRADO]"`, log warning |
| Both `medication_id` and `medication_name` provided | `medication_id` takes precedence; catalog name used; warning logged |
| Medication from catalog but catalog entry has no default_dosage | Accept; use client-provided `dosage` |
| `diagnosis_id` belongs to different patient | Return 404 (diagnosis not found for this patient) |
| `medications` array has 10 items | Accept (maximum allowed) |
| `medications` array has 11 items | Return 422 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `prescriptions`: INSERT — new prescription record
- `prescription_medications`: INSERT (multiple) — one row per medication in the prescription

**Example query (SQLAlchemy):**
```python
prescription = Prescription(
    patient_id=patient_id,
    doctor_id=current_user.id,
    doctor_name=doctor_profile.full_name,
    doctor_license=doctor_profile.tarjeta_profesional or "[NO REGISTRADO]",
    doctor_specialty=doctor_profile.specialty,
    clinic_name=tenant_profile.clinic_name,
    clinic_address=tenant_profile.address,
    clinic_phone=tenant_profile.phone,
    diagnosis_id=data.diagnosis_id,
    notes=data.notes,
    prescribed_at=datetime.utcnow(),
)
session.add(prescription)
await session.flush()

for idx, med in enumerate(data.medications, start=1):
    rx_med = PrescriptionMedication(
        prescription_id=prescription.id,
        medication_id=med.medication_id,
        medication_name=resolved_name,
        generic_name=resolved_generic,
        dosage=med.dosage,
        frequency=med.frequency,
        duration=med.duration,
        route=med.route,
        instructions=med.instructions,
        order_number=idx,
    )
    session.add(rx_med)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:{patient_id}:prescriptions:list:*`: INVALIDATE

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| prescriptions | prescription.created | { tenant_id, prescription_id, patient_id, doctor_id } | After successful insert |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** prescription
- **PHI involved:** Yes (patient_id, medications, diagnosis reference)

### Notifications

**Notifications triggered:** No (prescriptions are typically printed/downloaded immediately via RX-04)

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 600ms

### Caching Strategy
- **Strategy:** No caching on create (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates patient prescription list cache on success

### Database Performance

**Queries executed:** 4–6 (patient lookup, catalog lookup per medication, doctor profile, tenant profile, prescription INSERT, medications INSERT batch)

**Indexes required:**
- `{tenant}.prescriptions.patient_id` — INDEX
- `{tenant}.prescriptions.doctor_id` — INDEX
- `{tenant}.prescription_medications.prescription_id` — INDEX
- `public.catalog_medications.id` — PRIMARY KEY (already indexed)

**N+1 prevention:** Medication catalog lookups batched in a single IN query (`WHERE id IN (...)`); not per-medication individual queries.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| medication_name | Pydantic `strip()` + strip_tags | Free text stored in prescription |
| dosage, frequency, duration | Pydantic `strip()` + max-length enforcement | Clinical text fields |
| instructions | Pydantic `strip()` + bleach.clean (strip_tags) | Free text; rendered in PDF |
| notes | Pydantic `strip()` + bleach.clean (strip_tags) | General free text |
| medication_id, diagnosis_id | Pydantic UUID validator | Reject malformed UUIDs |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, medications (health data), diagnosis_id (clinical data), notes (clinical notes)

**Audit requirement:** All access logged (write logged on create, PHI=true).

---

## Testing

### Test Cases

#### Happy Path
1. Create prescription with catalog medication
   - **Given:** Authenticated doctor, active patient, valid `medication_id` in catalog
   - **When:** POST /api/v1/patients/{patient_id}/prescriptions with one catalog medication
   - **Then:** 201 Created, `medication_name` populated from catalog, `order_number: 1`

2. Create prescription with multiple medications (one catalog, one free-text)
   - **Given:** Authenticated doctor, active patient
   - **When:** POST with medications array of 2 items (one with medication_id, one with medication_name)
   - **Then:** 201 Created, both medications stored, `order_number` 1 and 2

3. Doctor credentials auto-included
   - **Given:** Doctor has `tarjeta_profesional = "MP-12345-COL"` in profile
   - **When:** POST prescription
   - **Then:** Response includes `doctor_license: "MP-12345-COL"`, cannot be overridden by client

4. Create prescription with diagnosis link
   - **Given:** Active patient with an existing diagnosis record
   - **When:** POST with valid `diagnosis_id`
   - **Then:** 201 Created, `diagnosis_id` linked

#### Edge Cases
1. Doctor with missing license number
   - **Given:** Doctor has no `tarjeta_profesional` set in profile
   - **When:** POST prescription
   - **Then:** 201 Created, `doctor_license: "[NO REGISTRADO]"`, warning logged

2. Maximum 10 medications
   - **Given:** `medications` array has exactly 10 items
   - **When:** POST
   - **Then:** 201 Created, all 10 medications stored with sequential order_numbers

#### Error Cases
1. Assistant role attempting to create prescription
   - **Given:** User with assistant role
   - **When:** POST /api/v1/patients/{patient_id}/prescriptions
   - **Then:** 403 Forbidden

2. clinic_owner attempting to prescribe
   - **Given:** User with clinic_owner role
   - **When:** POST
   - **Then:** 403 Forbidden

3. Empty medications array
   - **Given:** `medications: []`
   - **When:** POST
   - **Then:** 400 Bad Request

4. More than 10 medications
   - **Given:** `medications` array has 11 items
   - **When:** POST
   - **Then:** 422 Unprocessable Entity

5. Invalid `medication_id` not in catalog
   - **Given:** `medication_id` is a valid UUID but not in `public.catalog_medications`
   - **When:** POST
   - **Then:** 422 with `medications[0].medication_id` error

6. Invalid `route` enum
   - **Given:** `route: "intravenous"` (not in enum)
   - **When:** POST
   - **Then:** 422 Unprocessable Entity

7. Patient not found
   - **Given:** `patient_id` does not exist
   - **When:** POST
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** doctor (with and without tarjeta_profesional); assistant, clinic_owner (negative tests)

**Patients/Entities:** Active patient; inactive patient; `public.catalog_medications` seeded with at least 5 medications; diagnosis record linked to test patient.

### Mocking Strategy

- Redis cache: Use fakeredis to verify cache invalidation
- RabbitMQ: Mock publish; assert `prescription.created` payload
- Catalog lookup: Integration test with seeded fixture data in public schema

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Prescription created with at least one medication returns 201
- [ ] Catalog medications resolved from `public.catalog_medications` by `medication_id`
- [ ] Free-text `medication_name` accepted when `medication_id` not provided
- [ ] `order_number` correctly assigned sequentially (1-based) per medications array order
- [ ] Doctor credentials (name, license, specialty) auto-included from user profile
- [ ] Clinic info auto-included from tenant profile
- [ ] Doctor with missing license creates prescription with `[NO REGISTRADO]` (no error)
- [ ] Only `doctor` role can create prescriptions (403 for others)
- [ ] Empty medications array returns 400
- [ ] More than 10 medications returns 422
- [ ] Patient prescription list cache invalidated after creation
- [ ] Audit log entry written with PHI=true
- [ ] RabbitMQ `prescription.created` event dispatched
- [ ] All test cases pass
- [ ] Performance target met (< 300ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Editing or modifying an existing prescription (prescriptions are immutable; create a new one)
- Deleting prescriptions
- Prescription PDF generation (see RX-04 prescription-pdf.md)
- Medication catalog management (see RX-05 prescription-medication-search.md)
- Controlled substance tracking or DEA number requirements
- E-prescribing integrations with pharmacies

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
- [x] Auth level stated (doctor ONLY)
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation on write)
- [x] DB queries optimized (batched catalog lookup)
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
