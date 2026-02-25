# Prescription Get Spec

---

## Overview

**Feature:** Retrieve the full detail of a single prescription for a patient, including all medications with complete catalog information, doctor credentials, clinic info, and any linked diagnosis. Used by the prescription detail view and as data source for PDF generation.

**Domain:** prescriptions

**Priority:** Medium

**Dependencies:** RX-01 (prescription-create.md), RX-04 (prescription-pdf.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, patient (own prescriptions only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients can only access their own prescriptions via the patient portal.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/prescriptions/{rx_id}
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
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient owning the prescription | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| rx_id | Yes | string (UUID) | Valid UUID v4, must belong to patient | Prescription to retrieve | rx1a2b3c-0000-4000-8000-000000000010 |

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
  "patient": {
    "id": "uuid",
    "full_name": "string",
    "document_type": "string",
    "document_number": "string",
    "age": "integer",
    "birthdate": "string (ISO 8601 date)"
  },
  "doctor": {
    "id": "uuid",
    "full_name": "string",
    "license_number": "string — Tarjeta Profesional",
    "specialty": "string | null"
  },
  "clinic": {
    "name": "string",
    "address": "string | null",
    "phone": "string | null",
    "city": "string | null"
  },
  "medications": [
    {
      "id": "uuid",
      "medication_id": "uuid | null",
      "medication_name": "string",
      "generic_name": "string | null",
      "active_ingredient": "string | null",
      "presentations": "string[] | null — from catalog if medication_id provided",
      "dosage": "string",
      "frequency": "string",
      "duration": "string",
      "route": "string",
      "instructions": "string | null",
      "order_number": "integer"
    }
  ],
  "diagnosis": {
    "id": "uuid",
    "description": "string",
    "code": "string | null — ICD-10 or dental code"
  },
  "notes": "string | null",
  "prescribed_at": "string (ISO 8601 datetime)",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "rx1a2b3c-0000-4000-8000-000000000010",
  "patient": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "full_name": "Maria Garcia Lopez",
    "document_type": "cedula",
    "document_number": "1020304050",
    "age": 35,
    "birthdate": "1990-05-15"
  },
  "doctor": {
    "id": "d4e5f6a7-0000-4000-8000-000000000004",
    "full_name": "Juan Carlos Perez Rodriguez",
    "license_number": "MP-12345-COL",
    "specialty": "Cirugia Oral y Maxilofacial"
  },
  "clinic": {
    "name": "Clinica Dental Sonrisa",
    "address": "Cra 7 # 45-10, Bogota",
    "phone": "+571 3456789",
    "city": "Bogota"
  },
  "medications": [
    {
      "id": "rxm1a2b3-0000-4000-8000-000000000020",
      "medication_id": "m1a2b3c4-0000-4000-8000-000000000001",
      "medication_name": "Amoxicilina",
      "generic_name": "amoxicillin",
      "active_ingredient": "amoxicillin trihydrate",
      "presentations": ["Capsulas 500mg", "Suspension 250mg/5ml"],
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
      "active_ingredient": null,
      "presentations": null,
      "dosage": "15ml",
      "frequency": "Dos veces al dia",
      "duration": "10 dias",
      "route": "oral",
      "instructions": "Enjuagarse durante 30 segundos y no tragar.",
      "order_number": 2
    }
  ],
  "diagnosis": null,
  "notes": "Post extraccion quirurgica diente 48. Iniciar antibiotico de inmediato.",
  "prescribed_at": "2026-02-24T14:30:00Z",
  "created_at": "2026-02-24T14:30:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role not allowed, or patient attempting to access another patient's prescription.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver esta prescripcion."
}
```

#### 404 Not Found
**When:** `patient_id` or `rx_id` not found, or prescription does not belong to the specified patient.

**Example:**
```json
{
  "error": "not_found",
  "message": "Prescripcion no encontrada."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate path parameters as valid UUIDs.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role:
   - If `patient`: verify JWT sub matches `portal_user_id` linked to `patient_id`. Return 403 if mismatch.
   - If clinic staff: allow any patient within tenant.
4. Check Redis cache: `tenant:{tenant_id}:patients:{patient_id}:prescriptions:{rx_id}`. Return if hit.
5. Fetch prescription record, JOIN `prescription_medications`, JOIN patient record (for current age calculation).
6. Verify `prescription.patient_id == patient_id` from path. Return 404 if mismatch.
7. For each medication with a `medication_id`: fetch catalog details (active_ingredient, presentations) from `public.catalog_medications`. Batch these into a single IN query.
8. Compute patient `age` from `birthdate` at query time.
9. If `diagnosis_id` present: fetch diagnosis record from tenant schema.
10. Cache result in Redis with 10-minute TTL.
11. Write audit log entry for PHI access.
12. Return 200 with full prescription detail.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| rx_id | Valid UUID v4 | El identificador de la prescripcion no es valido. |

**Business Rules:**

- Doctor credentials stored at prescription creation time are returned (snapshot of doctor info at time of prescribing). Current doctor profile changes do not retroactively alter old prescriptions.
- Patient age is computed dynamically at read time from `birthdate` (not stored).
- Catalog enrichment (active_ingredient, presentations) is fetched for catalog medications only. Free-text medications have `null` for catalog fields.
- The prescription is immutable — this endpoint is read-only.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Medication was catalog-based but catalog entry deleted later | Return stored `medication_name`; catalog enrichment fields return null (graceful fallback) |
| Patient age computation on birthday | Correctly computed based on today's date |
| `diagnosis` was deleted from patient record | Return `diagnosis: null` in response (soft reference; no cascade) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:{patient_id}:prescriptions:{rx_id}`: SET — populated on cache miss

**Cache TTL:** 10 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** prescription
- **PHI involved:** Yes (medications = health data; patient demographic data)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 60ms (cache hit)
- **Maximum acceptable:** < 250ms (cache miss with JOINs and catalog enrichment)

### Caching Strategy
- **Strategy:** Redis cache per prescription ID (tenant-namespaced)
- **Cache key:** `tenant:{tenant_id}:patients:{patient_id}:prescriptions:{rx_id}`
- **TTL:** 10 minutes
- **Invalidation:** Prescriptions are immutable; no invalidation needed. Cache expires naturally via TTL.

### Database Performance

**Queries executed:** 2–3 (prescription + medications JOIN, catalog enrichment IN query, optional diagnosis lookup)

**Indexes required:**
- `{tenant}.prescriptions.(patient_id, id)` — COMPOSITE INDEX
- `{tenant}.prescription_medications.prescription_id` — INDEX
- `public.catalog_medications.id` — PRIMARY KEY

**N+1 prevention:** All prescription medications fetched via single JOIN; catalog enrichment batched into single IN query by medication IDs.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Reject malformed path params |
| rx_id | Pydantic UUID validator | Reject malformed path params |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string fields escaped via Pydantic serialization on output.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient full_name, document_number, birthdate/age, medications (health data), diagnosis description

**Audit requirement:** All access logged (PHI read audited per request).

---

## Testing

### Test Cases

#### Happy Path
1. Retrieve prescription with catalog medication
   - **Given:** Authenticated doctor, prescription with one catalog medication
   - **When:** GET /api/v1/patients/{patient_id}/prescriptions/{rx_id}
   - **Then:** 200 OK, full patient and doctor info included, catalog enrichment (active_ingredient, presentations) populated

2. Retrieve prescription with free-text medication
   - **Given:** Prescription with one free-text medication (no medication_id)
   - **When:** GET
   - **Then:** 200 OK, `medication_id: null`, `active_ingredient: null`, `presentations: null`

3. Patient retrieves own prescription
   - **Given:** Patient with portal access, prescription belonging to this patient
   - **When:** GET (patient JWT)
   - **Then:** 200 OK, full detail returned

4. Cache hit on repeated request
   - **Given:** Same rx_id requested twice within 10 minutes
   - **When:** GET (second call)
   - **Then:** 200 OK returned from cache, DB not queried

#### Edge Cases
1. Catalog medication deleted after prescription created
   - **Given:** Prescription references medication_id that no longer exists in catalog
   - **When:** GET
   - **Then:** 200 OK, stored `medication_name` returned, catalog fields null (graceful)

#### Error Cases
1. Prescription not found
   - **Given:** Valid UUID not matching any prescription
   - **When:** GET /api/v1/patients/{patient_id}/prescriptions/{nonexistent_rx_id}
   - **Then:** 404 Not Found

2. Prescription belongs to different patient
   - **Given:** rx_id exists but belongs to different patient
   - **When:** GET with mismatched patient_id
   - **Then:** 404 Not Found

3. Patient accessing another patient's prescription
   - **Given:** Patient A's JWT, URL uses Patient B's patient_id
   - **When:** GET
   - **Then:** 403 Forbidden

4. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** GET
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** doctor, assistant, clinic_owner (happy path); patient with portal access; patient without portal access

**Patients/Entities:** Prescription with catalog medications; prescription with free-text medications; prescription with diagnosis link.

### Mocking Strategy

- Redis cache: Use fakeredis to test cache hit/miss
- Catalog lookup: Integration test with seeded public catalog fixture
- Audit log: Mock audit service; assert PHI=true

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Prescription returned with full patient info including age (computed dynamically)
- [ ] Doctor credentials from prescription record returned (snapshot at creation time)
- [ ] Catalog medications enriched with active_ingredient and presentations
- [ ] Free-text medications return null for catalog fields
- [ ] Medications returned in `order_number` sequence
- [ ] Patient can only access their own prescriptions (403 otherwise)
- [ ] Prescription not belonging to specified patient returns 404
- [ ] Cache populated on first request (10-minute TTL)
- [ ] Audit log entry written with PHI=true
- [ ] All test cases pass
- [ ] Performance target met (< 60ms cache hit, < 250ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing prescriptions (see RX-03 prescription-list.md)
- Downloading the PDF (see RX-04 prescription-pdf.md)
- Editing prescriptions (prescriptions are immutable)
- Medication catalog management (see RX-05 prescription-medication-search.md)

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
- [x] Caching strategy stated (10-minute TTL — prescriptions are immutable)
- [x] DB queries optimized (batched catalog enrichment)
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
