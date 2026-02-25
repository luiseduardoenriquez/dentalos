# Get Patient Profile Spec

---

## Overview

**Feature:** Retrieve the full profile of a single patient by ID, including all demographic fields, calculated age, and a medical summary with active diagnoses count, active treatment plans count, last visit date, upcoming appointment, and outstanding balance.

**Domain:** patients

**Priority:** Critical

**Dependencies:** P-01 (patient-create.md), I-02 (database-architecture.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** All reads of patient data are audit-logged as PHI access.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}
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
| patient_id | Yes | uuid | Valid UUID v4 | The unique patient identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

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
  "document_type": "string",
  "document_number": "string",
  "first_name": "string",
  "last_name": "string",
  "full_name": "string (computed: first_name + last_name)",
  "birthdate": "string (ISO 8601 date)",
  "age": "integer (calculated from birthdate)",
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
  "avatar_url": "string | null",
  "is_active": "boolean",
  "no_show_count": "integer",
  "portal_access": "boolean",
  "last_visit_at": "string | null (ISO 8601 datetime)",
  "medical_summary": {
    "active_diagnoses_count": "integer",
    "active_treatment_plans_count": "integer",
    "last_visit_date": "string | null (ISO 8601 date)",
    "upcoming_appointment": {
      "id": "uuid",
      "start_time": "string (ISO 8601 datetime)",
      "doctor_name": "string",
      "appointment_type": "string"
    } | null,
    "balance_cents": "integer (outstanding balance in cents)",
    "currency": "string (e.g., COP)"
  },
  "odontogram_state": {
    "id": "uuid",
    "dentition_type": "string"
  },
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)",
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
  "full_name": "Maria Garcia Lopez",
  "birthdate": "1990-05-15",
  "age": 35,
  "gender": "female",
  "phone": "+573001234567",
  "phone_secondary": null,
  "email": "maria.garcia@email.com",
  "address": null,
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
  "notes": "Paciente remitida por Dr. Rodriguez",
  "avatar_url": null,
  "is_active": true,
  "no_show_count": 1,
  "portal_access": false,
  "last_visit_at": "2026-02-10T10:00:00Z",
  "medical_summary": {
    "active_diagnoses_count": 3,
    "active_treatment_plans_count": 1,
    "last_visit_date": "2026-02-10",
    "upcoming_appointment": {
      "id": "b2c3d4e5-f6a7-8901-bcde-234567890abc",
      "start_time": "2026-03-01T09:00:00Z",
      "doctor_name": "Dr. Juan Perez",
      "appointment_type": "procedure"
    },
    "balance_cents": 150000,
    "currency": "COP"
  },
  "odontogram_state": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "dentition_type": "adult"
  },
  "created_by": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "created_at": "2026-01-15T14:30:00Z",
  "updated_at": "2026-02-10T11:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure -- see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not in the allowed list.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver la informacion de pacientes."
}
```

#### 404 Not Found
**When:** Patient with the given ID does not exist in the tenant schema, or the UUID format is invalid.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
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
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (any staff role is allowed).
4. Check Redis cache for key `tenant:{tenant_id}:patient:{patient_id}:profile`.
5. If cache hit, return cached response (skip to step 11).
6. Query `patients` table by `id`, including `odontogram_states` via JOIN.
7. If not found, return 404.
8. Build medical_summary via aggregation queries:
   - `SELECT COUNT(*) FROM diagnoses WHERE patient_id = :id AND status = 'active'`
   - `SELECT COUNT(*) FROM treatment_plans WHERE patient_id = :id AND status IN ('draft', 'active')`
   - `SELECT start_time, doctor_id, appointment_type FROM appointments WHERE patient_id = :id AND start_time > now() AND status IN ('scheduled', 'confirmed') ORDER BY start_time LIMIT 1`
   - `SELECT COALESCE(SUM(total_cents - paid_cents), 0) FROM invoices WHERE patient_id = :id AND status IN ('sent', 'partial', 'overdue')`
9. Calculate `age` from `birthdate` using current date.
10. Store result in Redis cache with TTL 5 minutes.
11. Write audit log entry (action: read, resource: patient, PHI: yes).
12. Return 200 with full patient profile.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | Identificador de paciente no valido. |

**Business Rules:**

- All staff roles can view patient profiles (PHI access is audit-logged).
- The `age` field is always calculated server-side from `birthdate`; it is never stored.
- The `full_name` field is computed as `first_name + " " + last_name`.
- The `balance_cents` represents the total outstanding amount across all unpaid invoices.
- The `upcoming_appointment` returns only the next future appointment that is scheduled or confirmed.
- Deactivated patients (is_active = false) are still retrievable by ID.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient exists but has no diagnoses, treatment plans, appointments, or invoices | medical_summary returns zeros and nulls |
| Patient is deactivated | Return profile with is_active = false |
| Patient ID exists in another tenant | Return 404 (schema isolation) |
| Multiple unpaid invoices | balance_cents is the sum across all |
| Birthday is today | Age increments to new year value |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:profile`: SET -- cache the full profile response

**Cache TTL:** 5 minutes

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes -- see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** patient
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms (cache hit), < 300ms (cache miss)
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Redis cache
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:profile`
- **TTL:** 5 minutes
- **Invalidation:** On patient update (P-04), patient deactivation (P-05), appointment changes, invoice changes, diagnosis changes, treatment plan changes

### Database Performance

**Queries executed:** 5 on cache miss (1 patient + odontogram JOIN, 4 aggregation queries for medical summary)

**Indexes required:**
- `patients.id` -- PRIMARY KEY (already defined)
- `odontogram_states.patient_id` -- UNIQUE (already defined)
- `diagnoses.(patient_id, status)` -- INDEX (already defined)
- `treatment_plans.(patient_id, status)` -- INDEX (already defined)
- `appointments.(patient_id)` -- INDEX (already defined)
- `invoices.(patient_id)` -- INDEX (already defined)

**N+1 prevention:** Single query for patient + odontogram via JOIN. Medical summary uses targeted aggregate queries, not iteration.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID strings |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** first_name, last_name, document_number, birthdate, phone, email, address, emergency_contact_name, emergency_contact_phone, insurance_provider, insurance_policy_number, blood_type, allergies, chronic_conditions, notes, medical_summary (diagnoses count, treatment data, balance)

**Audit requirement:** All access logged (every read is logged because this returns PHI)

---

## Testing

### Test Cases

#### Happy Path
1. Get existing patient with full profile
   - **Given:** Patient f47ac10b exists with diagnoses, appointments, invoices
   - **When:** GET /api/v1/patients/f47ac10b-58cc-4372-a567-0e02b2c3d479
   - **Then:** 200 OK, full profile with medical summary populated

2. Cache hit returns same data
   - **Given:** Patient profile was fetched within the last 5 minutes
   - **When:** GET /api/v1/patients/{id} again
   - **Then:** 200 OK, response from Redis cache, no DB queries

3. All staff roles can access
   - **Given:** Users with roles: clinic_owner, doctor, assistant, receptionist
   - **When:** Each user fetches same patient
   - **Then:** 200 OK for all four roles

#### Edge Cases
1. Patient with no medical history
   - **Given:** Newly created patient with no diagnoses, appointments, or invoices
   - **When:** GET /api/v1/patients/{id}
   - **Then:** medical_summary has all counts = 0, upcoming_appointment = null, balance_cents = 0

2. Deactivated patient
   - **Given:** Patient with is_active = false
   - **When:** GET /api/v1/patients/{id}
   - **Then:** 200 OK with is_active = false in response

3. Age calculation on birthday
   - **Given:** Patient birthdate = today's date 30 years ago
   - **When:** GET /api/v1/patients/{id}
   - **Then:** age = 30

#### Error Cases
1. Non-existent patient ID
   - **Given:** No patient with the given UUID
   - **When:** GET /api/v1/patients/{random_uuid}
   - **Then:** 404 Not Found

2. Invalid UUID format
   - **Given:** patient_id = "not-a-uuid"
   - **When:** GET /api/v1/patients/not-a-uuid
   - **Then:** 404 Not Found (or 422 depending on framework path validation)

3. Cross-tenant access attempt
   - **Given:** Patient exists in tenant A, user belongs to tenant B
   - **When:** GET /api/v1/patients/{patient_id_from_tenant_A}
   - **Then:** 404 Not Found (schema isolation)

### Test Data Requirements

**Users:** One user per staff role (clinic_owner, doctor, assistant, receptionist)

**Patients/Entities:** Patient with complete profile, patient with empty medical history, deactivated patient. Related diagnoses, treatment plans, appointments, and invoices for medical summary testing.

### Mocking Strategy

- Redis cache: Use fakeredis; test both cache hit and miss paths
- Database: Use test fixtures with known aggregate values

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Full patient profile returned with all fields for existing patient
- [ ] Calculated age is correct based on birthdate
- [ ] medical_summary includes accurate counts and upcoming appointment
- [ ] balance_cents is correct sum of outstanding invoices
- [ ] Response cached in Redis for 5 minutes
- [ ] Cache hit path skips DB queries
- [ ] 404 returned for non-existent or cross-tenant patient IDs
- [ ] Audit log entry written for every read (PHI access)
- [ ] All staff roles can access the endpoint
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Patient document/file listing (separate endpoint)
- Full clinical record history (separate endpoint under clinical-records domain)
- Odontogram condition details (separate endpoint under odontogram domain)
- Patient portal view (different auth context and response shape)

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
- [x] Pagination applied where needed (N/A for single resource)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A for read)

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
