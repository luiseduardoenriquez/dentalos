# P-07 Patient Medical History Timeline Spec

---

## Overview

**Feature:** Retrieve the full medical history timeline for a patient, aggregating all clinical events (appointments, diagnoses, procedures, odontogram changes, prescriptions, consent signings) into a single paginated chronological feed ordered by date descending.

**Domain:** patients

**Priority:** High

**Dependencies:** P-01 (patient-create.md), appointments, clinical-records, odontogram, prescriptions, consents

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant, clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Every successful request is audit-logged as a PHI read because the response contains Protected Health Information.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/medical-history
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
| patient_id | Yes | UUID | Valid UUIDv4 | Target patient identifier | 550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| event_type | No | string | Comma-separated list. Values: appointment, diagnosis, procedure, odontogram_change, prescription, consent | Filter by event types | diagnosis,procedure |
| date_from | No | date | ISO 8601 (YYYY-MM-DD) | Start of date range (inclusive) | 2025-01-01 |
| date_to | No | date | ISO 8601 (YYYY-MM-DD) | End of date range (inclusive) | 2025-12-31 |
| page | No | integer | >= 1, default 1 | Page number | 1 |
| page_size | No | integer | 1-100, default 20 | Items per page | 20 |

### Request Body Schema

N/A — GET request with no body.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "uuid",
      "event_type": "string (appointment|diagnosis|procedure|odontogram_change|prescription|consent)",
      "event_date": "ISO 8601 datetime",
      "title": "string",
      "summary": "string",
      "details": {
        "record_id": "uuid",
        "doctor_name": "string (nullable)",
        "tooth_number": "integer (nullable)",
        "status": "string (nullable)",
        "extra": "object (type-specific fields)"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 150,
    "total_pages": 8
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "event_type": "procedure",
      "event_date": "2025-11-15T14:30:00-05:00",
      "title": "Restauracion resina compuesta",
      "summary": "Procedimiento CUPS 997300 realizado en diente 36 por Dr. Martinez",
      "details": {
        "record_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "doctor_name": "Dr. Carlos Martinez",
        "tooth_number": 36,
        "status": null,
        "extra": {
          "cups_code": "997300",
          "zones": ["oclusal", "mesial"],
          "materials_used": ["resina compuesta"]
        }
      }
    },
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "event_type": "diagnosis",
      "event_date": "2025-11-15T14:00:00-05:00",
      "title": "Caries de la dentina (K02.1)",
      "summary": "Diagnostico activo en diente 36 — severidad moderada",
      "details": {
        "record_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
        "doctor_name": "Dr. Carlos Martinez",
        "tooth_number": 36,
        "status": "active",
        "extra": {
          "cie10_code": "K02.1",
          "severity": "moderate"
        }
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 42,
    "total_pages": 3
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values (bad date format, unknown event_type).

```json
{
  "error": "invalid_input",
  "message": "El formato de fecha es invalido. Use AAAA-MM-DD.",
  "details": { "field": "date_from" }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not doctor, assistant, or clinic_owner.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para acceder al historial medico de este paciente."
}
```

#### 404 Not Found
**When:** patient_id does not exist or is inactive in the current tenant.

```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` UUID format via Pydantic path validator.
2. Resolve tenant from JWT claims, set `search_path`.
3. Check user role is in [doctor, assistant, clinic_owner] via RBAC dependency.
4. Query `patients` table — confirm patient exists and `is_active = true`.
5. Build a UNION ALL query across six source tables, each aliased to the common event schema:
   - `appointments` (event_type = 'appointment'): use `start_time` as event_date.
   - `diagnoses` (event_type = 'diagnosis'): use `created_at` as event_date.
   - `procedures` (event_type = 'procedure'): use `created_at` as event_date.
   - `odontogram_history` (event_type = 'odontogram_change'): use `created_at` as event_date.
   - `prescriptions` (event_type = 'prescription'): use `created_at` as event_date.
   - `consents` where status = 'signed' (event_type = 'consent'): use `signed_at` as event_date.
6. Apply optional filters: `event_type` (include only selected sub-queries), `date_from`/`date_to`.
7. Execute count query for total items (for pagination metadata).
8. Apply ORDER BY event_date DESC, then LIMIT/OFFSET for pagination.
9. Map each row to the response schema, joining user names for `doctor_name`/`performed_by`.
10. Write audit log entry: action=read, resource_type=patient_medical_history, PHI=true.
11. Return paginated response.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUIDv4 | "El ID del paciente no es un UUID valido." |
| event_type | Each value in allowed set | "Tipo de evento no valido: {value}. Valores permitidos: appointment, diagnosis, procedure, odontogram_change, prescription, consent." |
| date_from / date_to | ISO 8601 date; date_from <= date_to | "El rango de fechas es invalido. La fecha inicial no puede ser posterior a la fecha final." |
| page | Integer >= 1 | "El numero de pagina debe ser mayor o igual a 1." |
| page_size | Integer 1-100 | "El tamano de pagina debe estar entre 1 y 100." |

**Business Rules:**

- Inactive patients (is_active=false) return 404 to prevent data access on archived records.
- Only signed consents appear in the timeline (draft/voided are excluded).
- Cancelled appointments still appear (for historical completeness) but their status is visible.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient with zero clinical events | Return 200 with empty `data` array and total_items=0. |
| date_from equals date_to | Return events from that single day (00:00:00 to 23:59:59 in tenant timezone). |
| Filtering to a single event_type | Only that sub-query executes; others are skipped for performance. |
| Very old patient with thousands of events | Pagination prevents memory overload; LIMIT/OFFSET with indexed queries. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_log`: INSERT — PHI read audit entry.

### Cache Operations

**Cache keys affected:**
- None. Medical history is not cached due to PHI sensitivity and frequency of updates.

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** read
- **Resource:** patient_medical_history
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 800ms

### Caching Strategy
- **Strategy:** No caching (PHI data, audit requirement on every access)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 2 (count + paginated data via UNION ALL)

**Indexes required:**
- `appointments.patient_id` + `start_time` — composite INDEX (existing: `idx_appointments_patient`)
- `diagnoses.patient_id` + `created_at` — INDEX
- `procedures.patient_id` + `created_at` — INDEX (existing: `idx_procedures_date`)
- `odontogram_history.patient_id` + `created_at` — INDEX (existing: `idx_odontogram_history_date`)
- `prescriptions.patient_id` — INDEX (existing: `idx_prescriptions_patient`)
- `consents.patient_id` + `signed_at` — INDEX

**N+1 prevention:** Single UNION ALL query with LEFT JOIN to `users` for doctor names. No lazy loading.

### Pagination

**Pagination:** Yes

- **Style:** offset-based
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID values |
| event_type | Enum whitelist via Pydantic | Only allowed values pass |
| date_from / date_to | Pydantic date validator | Strict ISO 8601 |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. The UNION ALL is built with SQLAlchemy `union_all()` construct. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** diagnoses (cie10_code, description), procedures (description, materials_used), prescriptions (medications), allergies referenced, odontogram conditions.

**Audit requirement:** All access logged (every GET request creates an audit entry).

---

## Testing

### Test Cases

#### Happy Path
1. Full timeline retrieval
   - **Given:** Patient with 5 appointments, 3 diagnoses, 2 procedures, 1 prescription, 1 consent.
   - **When:** GET /api/v1/patients/{id}/medical-history
   - **Then:** Returns 200 with 12 events sorted by date DESC, correct pagination.

2. Filtered by event_type
   - **Given:** Same patient.
   - **When:** GET with ?event_type=diagnosis,procedure
   - **Then:** Returns 200 with only 5 events (3 diagnoses + 2 procedures).

3. Filtered by date range
   - **Given:** Events spanning 2024-2025.
   - **When:** GET with ?date_from=2025-01-01&date_to=2025-06-30
   - **Then:** Returns only events within range.

#### Edge Cases
1. Patient with no clinical history
   - **Given:** Newly created patient with no events.
   - **When:** GET medical history.
   - **Then:** Returns 200, empty data array, total_items=0.

2. Pagination boundary
   - **Given:** Patient with exactly 20 events.
   - **When:** GET with page=1&page_size=20
   - **Then:** Returns all 20, total_pages=1.

#### Error Cases
1. Unauthorized role
   - **Given:** User with role receptionist.
   - **When:** GET medical history.
   - **Then:** Returns 403.

2. Non-existent patient
   - **Given:** Random UUID.
   - **When:** GET medical history.
   - **Then:** Returns 404.

3. Invalid event_type filter
   - **Given:** ?event_type=surgery
   - **When:** GET request.
   - **Then:** Returns 400 with validation error.

### Test Data Requirements

**Users:** 1 clinic_owner, 1 doctor, 1 assistant, 1 receptionist (for 403 test).

**Patients/Entities:** 1 patient with mixed clinical events across all 6 source tables; 1 patient with no events.

### Mocking Strategy

- Database: Use test tenant schema with seeded data.
- Audit log: Verify INSERT after each request.
- No external services to mock.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] UNION ALL query returns correct aggregated timeline from 6 tables
- [ ] Pagination works correctly with total counts
- [ ] event_type filter correctly limits sub-queries
- [ ] date_from / date_to filters apply across all event types
- [ ] Audit log entry created for every successful request (PHI read)
- [ ] Inactive patients return 404
- [ ] Receptionist role receives 403
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms for typical patient)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Writing or modifying any clinical records (handled by their respective domain specs).
- Full-text search across clinical content (future analytics feature).
- Exporting the medical history to PDF (covered by a separate clinical-export spec).
- Patient portal access to their own medical history (covered in portal domain).

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
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (no cache — PHI)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

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
