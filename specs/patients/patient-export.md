# P-09 Patient List Export (CSV) Spec

---

## Overview

**Feature:** Export the filtered patient list to CSV as a streaming download. Includes basic demographic data (name, document, phone, email, birthdate, gender, created_at, last_visit_at). Explicitly excludes PHI clinical details (medical conditions, allergies, diagnoses). Audit logged as a data export event.

**Domain:** patients

**Priority:** High

**Dependencies:** P-02 (patient-list.md), infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Export is restricted to clinic_owner only due to bulk data access. Every export is audit logged with metadata about the filters used and row count exported.

---

## Endpoint

```
GET /api/v1/patients/export
```

**Rate Limiting:**
- 10 requests per hour per tenant

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |
| Accept | No | string | Expected response type | text/csv |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| search | No | string | Max 100 chars | Full-text search (name, document, phone) | Juan |
| is_active | No | boolean | true/false | Filter by active status | true |
| gender | No | string | male, female, other | Filter by gender | female |
| created_from | No | date | ISO 8601 | Patients created from this date | 2025-01-01 |
| created_to | No | date | ISO 8601 | Patients created up to this date | 2025-12-31 |
| last_visit_from | No | date | ISO 8601 | Last visit from date | 2025-06-01 |
| last_visit_to | No | date | ISO 8601 | Last visit up to date | 2025-12-31 |
| insurance_provider | No | string | Max 200 chars | Filter by insurance | Sura EPS |
| referral_source | No | string | Max 50 chars | Filter by referral source | instagram |

### Request Body Schema

N/A — GET request with no body.

---

## Response

### Success Response

**Status:** 200 OK

**Content-Type:** text/csv; charset=utf-8

**Content-Disposition:** attachment; filename="pacientes_export_{tenant_slug}_{YYYYMMDD}.csv"

**Streaming CSV body:**
```csv
nombres,apellidos,tipo_documento,numero_documento,telefono,telefono_secundario,email,fecha_nacimiento,genero,ciudad,departamento,aseguradora,poliza,fuente_referido,fecha_registro,ultima_visita,estado
Juan,Perez,cedula,1234567890,+573001234567,,juan@email.com,1985-03-15,masculino,Bogota,Cundinamarca,Sura EPS,POL-12345,instagram,2025-01-10,2025-11-15,activo
Maria,Lopez,cedula,9876543210,+573009876543,+573005551234,maria@email.com,1990-07-22,femenino,Medellin,Antioquia,,,referido,2025-02-20,2025-10-28,activo
```

**CSV Column Definitions:**

| CSV Column | Source Field | Description |
|------------|-------------|-------------|
| nombres | first_name | Patient first name |
| apellidos | last_name | Patient last name |
| tipo_documento | document_type | Document type (cedula, curp, etc.) |
| numero_documento | document_number | Document number |
| telefono | phone | Primary phone |
| telefono_secundario | phone_secondary | Secondary phone |
| email | email | Email address |
| fecha_nacimiento | birthdate | Birthdate (YYYY-MM-DD) |
| genero | gender | Gender (masculino/femenino/otro) |
| ciudad | city | City |
| departamento | state_province | State/province |
| aseguradora | insurance_provider | Insurance provider |
| poliza | insurance_policy_number | Policy number |
| fuente_referido | referral_source | Referral source |
| fecha_registro | created_at | Registration date (YYYY-MM-DD) |
| ultima_visita | last_visit_at | Last visit date (YYYY-MM-DD or empty) |
| estado | is_active | Status (activo/inactivo) |

### Error Responses

#### 400 Bad Request
**When:** Invalid filter parameter values.

```json
{
  "error": "invalid_input",
  "message": "El formato de fecha es invalido. Use AAAA-MM-DD.",
  "details": { "field": "created_from" }
}
```

#### 401 Unauthorized
**When:** Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not clinic_owner.

```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede exportar datos de pacientes."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded (10 exports/hour).

#### 500 Internal Server Error
**When:** Database error during streaming; connection lost mid-export.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract tenant context; verify role = clinic_owner.
2. Parse and validate all query parameters via Pydantic.
3. Write audit log entry BEFORE starting the export: action=export, resource_type=patient_list, metadata includes filters used.
4. Build SQLAlchemy query on `patients` table with applied filters (same logic as patient-list endpoint).
5. Set up a StreamingResponse with `text/csv` content type.
6. Write CSV header row.
7. Execute query with server-side cursor (stream_results=True) to avoid loading all rows into memory.
8. For each row, map database fields to CSV columns (gender: male->masculino, etc.) and write to stream.
9. Update audit log with total row count exported (via a post-export callback).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| search | Max 100 characters | "El termino de busqueda no puede exceder 100 caracteres." |
| is_active | Boolean | "El valor de 'is_active' debe ser true o false." |
| gender | Must be in: male, female, other | "Genero no valido." |
| created_from / created_to | ISO 8601 date; from <= to | "El rango de fechas es invalido." |
| last_visit_from / last_visit_to | ISO 8601 date; from <= to | "El rango de fechas de ultima visita es invalido." |

**Business Rules:**

- Gender is exported in Spanish: male -> masculino, female -> femenino, other -> otro.
- Status is exported in Spanish: active -> activo, inactive -> inactivo.
- Dates are exported in YYYY-MM-DD format regardless of tenant locale.
- Null values are exported as empty strings.
- CSV uses UTF-8 encoding with BOM for Excel compatibility.
- PHI clinical data (allergies, chronic_conditions, blood_type) is explicitly excluded.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No patients match filters | Return 200 with CSV containing only the header row. |
| Tenant with 50,000 patients (no filters) | Streaming response handles large datasets without memory issues. |
| Client disconnects mid-stream | Server logs the disconnection; audit log still records the export attempt. |
| Patient has null email, phone, city | Empty strings in those CSV columns. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_log`: INSERT — data export audit entry.

### Cache Operations

**Cache keys affected:**
- None. Export does not modify or invalidate any cache.

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** export
- **Resource:** patient_list
- **PHI involved:** Yes (patient PII in bulk)
- **Metadata:** `{ "filters": {...}, "row_count": 2500, "format": "csv" }`

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target (time to first byte):** < 200ms
- **Maximum acceptable (time to first byte):** < 500ms
- **Throughput:** ~5,000 rows/second streaming

### Caching Strategy
- **Strategy:** No caching (dynamic filtered export)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 1 (streaming query with server-side cursor)

**Indexes required:**
- `patients.is_active` — INDEX (existing: `idx_patients_is_active`)
- `patients.created_at` — INDEX (existing: `idx_patients_created_at`)
- `patients` full-text search — GIN INDEX (existing: `idx_patients_search`)

**N+1 prevention:** Single query with all filters applied. No joins needed (all columns from patients table).

### Pagination

**Pagination:** No — streaming response delivers all matching rows.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| search | Pydantic str validator, max length | Passed to plainto_tsquery |
| All string params | Pydantic validators, max length | Type-checked and constrained |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Search terms are passed via `plainto_tsquery()`.

### XSS Prevention

**Output encoding:** CSV output; no HTML context. Values with commas or quotes are escaped per RFC 4180.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** first_name, last_name, document_number, phone, email, birthdate, address, insurance info.

**Excluded PHI fields:** allergies, chronic_conditions, blood_type, emergency_contact (clinical PHI excluded by design).

**Audit requirement:** All exports logged with filter metadata and row count.

---

## Testing

### Test Cases

#### Happy Path
1. Export all active patients
   - **Given:** 50 active patients, clinic_owner user.
   - **When:** GET /api/v1/patients/export?is_active=true
   - **Then:** Returns 200 with CSV, 50 data rows + header, UTF-8 BOM present.

2. Export with search filter
   - **Given:** 50 patients, 3 named "Juan".
   - **When:** GET with ?search=Juan
   - **Then:** CSV contains 3 data rows.

3. Export with date range
   - **Given:** Patients created across 2024-2025.
   - **When:** GET with ?created_from=2025-01-01&created_to=2025-06-30
   - **Then:** Only patients within range exported.

#### Edge Cases
1. Empty result set
   - **Given:** No patients match filters.
   - **When:** GET with restrictive filters.
   - **Then:** Returns 200 with CSV header row only.

2. Patient with special characters in name
   - **Given:** Patient named 'Maria "La Doctora" O\'Neil'.
   - **When:** Export.
   - **Then:** CSV properly escapes quotes and special characters.

#### Error Cases
1. Non-clinic_owner role
   - **Given:** Doctor user.
   - **When:** GET export.
   - **Then:** Returns 403.

2. Invalid date format
   - **Given:** ?created_from=15/01/2025
   - **When:** GET export.
   - **Then:** Returns 400 with validation error.

3. Rate limit exceeded
   - **Given:** 11th export request in the same hour.
   - **When:** GET export.
   - **Then:** Returns 429.

### Test Data Requirements

**Users:** 1 clinic_owner, 1 doctor (for 403 test).

**Patients/Entities:** 50+ patients with varied demographics, some with null optional fields, some with special characters.

### Mocking Strategy

- Database: Use test tenant schema with seeded patients.
- Audit log: Verify INSERT after export.
- No external services to mock.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Streaming CSV response with correct headers and column mapping
- [ ] All patient-list filters work identically to the list endpoint
- [ ] Gender and status exported in Spanish
- [ ] UTF-8 BOM included for Excel compatibility
- [ ] PHI clinical fields (allergies, conditions, blood_type) excluded
- [ ] Audit log entry created with filters and row count
- [ ] Only clinic_owner can access the endpoint
- [ ] Streaming handles large datasets (10k+ patients) without memory issues
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Exporting clinical data (diagnoses, procedures, allergies) — requires a separate clinical export spec with stricter controls.
- Export to Excel (.xlsx) or PDF formats (future enhancement).
- Scheduled/automated exports (cron-based).
- Export with custom column selection by user.

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
- [x] Audit trail for data export

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (none — dynamic export)
- [x] DB queries optimized (streaming cursor, indexes listed)
- [x] Pagination applied where needed (N/A — streaming)

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
