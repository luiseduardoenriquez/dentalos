# AN-05 — Clinical Analytics Spec

---

## Overview

**Feature:** Clinical analytics endpoint. Returns clinical practice metrics: most common diagnoses (CIE-10 codes), most performed procedures (CUPS codes), average treatment plan duration in days, treatment plan completion rates, and average number of procedures performed per patient. Supports date range and doctor-scope filtering. clinic_owner sees clinic-wide; doctor sees own clinical activity.

**Domain:** analytics

**Priority:** Medium

**Dependencies:** AN-01 (dashboard), clinical-records (sprint 5-6), treatment-plans (sprint 7-8), odontogram (sprint 5-6), infra/caching-strategy.md, infra/audit-logging.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** doctor role automatically scoped to their own clinical records and treatment plans. clinic_owner sees all clinical data across the clinic. Clinical data is PHI-adjacent — access is audit-logged with read classification.

---

## Endpoint

```
GET /api/v1/analytics/clinical
```

**Rate Limiting:**
- 20 requests per minute per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Tenant identifier (auto-resolved from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| period | No | string | Enum: `today`, `this_week`, `this_month`, `this_quarter`, `this_year`, `custom`. Default: `this_month` | Date range preset | `this_year` |
| date_from | Conditional | string | ISO 8601 date. Required when period=custom | Custom range start | `2026-01-01` |
| date_to | Conditional | string | ISO 8601 date. Required when period=custom; >= date_from; max 366 days | Custom range end | `2026-12-31` |
| top_n | No | integer | Min: 5, Max: 50, Default: 10 | Number of top diagnoses and procedures to return | `10` |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "period": {
    "preset": "string | null",
    "date_from": "string (YYYY-MM-DD)",
    "date_to": "string (YYYY-MM-DD)",
    "timezone": "string (IANA)"
  },
  "summary": {
    "total_clinical_records_in_period": "integer",
    "total_procedures_performed": "integer",
    "total_treatment_plans_created": "integer",
    "total_treatment_plans_completed": "integer",
    "treatment_plan_completion_rate": "number (percentage)",
    "average_procedures_per_patient": "number",
    "average_treatment_plan_duration_days": "number | null"
  },
  "top_diagnoses": [
    {
      "cie10_code": "string (CIE-10 diagnosis code)",
      "cie10_description": "string (Spanish description)",
      "count": "integer (times this diagnosis recorded in period)",
      "rank": "integer",
      "percentage_of_total_diagnoses": "number"
    }
  ],
  "top_procedures": [
    {
      "cups_code": "string (CUPS procedure code)",
      "cups_description": "string (Spanish description)",
      "count": "integer (times this procedure performed in period)",
      "rank": "integer",
      "percentage_of_total_procedures": "number",
      "average_duration_minutes": "number | null"
    }
  ],
  "treatment_plan_analysis": {
    "average_duration_days": "number | null",
    "median_duration_days": "number | null",
    "completion_rate_by_plan_type": [
      {
        "plan_type": "string",
        "total": "integer",
        "completed": "integer",
        "completion_rate": "number (percentage)"
      }
    ],
    "average_procedures_per_plan": "number",
    "plans_by_status": {
      "draft": "integer",
      "active": "integer",
      "completed": "integer",
      "abandoned": "integer"
    }
  },
  "procedure_volume_over_time": [
    {
      "month": "string (YYYY-MM)",
      "total_procedures": "integer"
    }
  ],
  "generated_at": "string (ISO 8601 datetime)",
  "cache_hit": "boolean"
}
```

**Example:**
```json
{
  "period": {
    "preset": "this_year",
    "date_from": "2026-01-01",
    "date_to": "2026-12-31",
    "timezone": "America/Bogota"
  },
  "summary": {
    "total_clinical_records_in_period": 524,
    "total_procedures_performed": 1248,
    "total_treatment_plans_created": 142,
    "total_treatment_plans_completed": 98,
    "treatment_plan_completion_rate": 69.0,
    "average_procedures_per_patient": 3.6,
    "average_treatment_plan_duration_days": 45.2
  },
  "top_diagnoses": [
    {"cie10_code": "K02.9", "cie10_description": "Caries dental, sin otra especificación", "count": 312, "rank": 1, "percentage_of_total_diagnoses": 28.4},
    {"cie10_code": "K04.0", "cie10_description": "Pulpitis", "count": 186, "rank": 2, "percentage_of_total_diagnoses": 16.9},
    {"cie10_code": "K05.1", "cie10_description": "Periodontitis crónica", "count": 142, "rank": 3, "percentage_of_total_diagnoses": 12.9},
    {"cie10_code": "K08.1", "cie10_description": "Pérdida de dientes debida a accidente, extracción o enfermedad periodontal", "count": 98, "rank": 4, "percentage_of_total_diagnoses": 8.9},
    {"cie10_code": "K00.6", "cie10_description": "Alteraciones de la erupción dentaria", "count": 72, "rank": 5, "percentage_of_total_diagnoses": 6.5}
  ],
  "top_procedures": [
    {"cups_code": "89.07.01.01", "cups_description": "Consulta odontológica de primera vez", "count": 245, "rank": 1, "percentage_of_total_procedures": 19.6, "average_duration_minutes": 30.0},
    {"cups_code": "23.11.01.01", "cups_description": "Restauración en resina", "count": 198, "rank": 2, "percentage_of_total_procedures": 15.9, "average_duration_minutes": 45.0},
    {"cups_code": "23.09.02.01", "cups_description": "Tratamiento endodóntico de diente unirradicular", "count": 124, "rank": 3, "percentage_of_total_procedures": 9.9, "average_duration_minutes": 90.0},
    {"cups_code": "23.01.02.01", "cups_description": "Extracción dental simple de diente permanente", "count": 112, "rank": 4, "percentage_of_total_procedures": 9.0, "average_duration_minutes": 30.0},
    {"cups_code": "89.31.14.01", "cups_description": "Detartraje y pulido coronal", "count": 108, "rank": 5, "percentage_of_total_procedures": 8.7, "average_duration_minutes": 60.0}
  ],
  "treatment_plan_analysis": {
    "average_duration_days": 45.2,
    "median_duration_days": 38.0,
    "completion_rate_by_plan_type": [
      {"plan_type": "Rehabilitación oral completa", "total": 28, "completed": 18, "completion_rate": 64.3},
      {"plan_type": "Ortodoncia", "total": 45, "completed": 32, "completion_rate": 71.1},
      {"plan_type": "Periodoncia", "total": 38, "completed": 29, "completion_rate": 76.3},
      {"plan_type": "General / preventivo", "total": 31, "completed": 19, "completion_rate": 61.3}
    ],
    "average_procedures_per_plan": 6.8,
    "plans_by_status": {
      "draft": 12,
      "active": 32,
      "completed": 98,
      "abandoned": 4
    }
  },
  "procedure_volume_over_time": [
    {"month": "2026-01", "total_procedures": 198},
    {"month": "2026-02", "total_procedures": 224}
  ],
  "generated_at": "2026-02-25T10:30:00Z",
  "cache_hit": false
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid `period` or `top_n` value, custom period missing dates, invalid date range.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "El valor de 'top_n' debe estar entre 5 y 50.",
  "details": {
    "top_n": ["Valor recibido: 100. Máximo permitido: 50."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token.

#### 403 Forbidden
**When:** Role not in `[clinic_owner, doctor]`.

#### 422 Unprocessable Entity
**When:** Date strings cannot be parsed as valid ISO 8601 dates.

#### 429 Too Many Requests
**When:** Rate limit exceeded.

#### 500 Internal Server Error
**When:** Aggregation query failure or CIE-10/CUPS lookup failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT — extract `user_id`, `tenant_id`, `role`. Authorize.
2. Parse and validate query parameters. Validate `top_n` range (5-50). Compute date range in tenant timezone.
3. Determine scope filter: `doctor_filter = current_user.id` for doctor role, `None` for clinic_owner.
4. Build Redis cache key and check cache.
5. On cache miss, execute concurrent queries:

   **Summary counts:** COUNT clinical_records, SUM procedures, COUNT treatment_plans with status breakdown, AVG treatment_plan_duration, AVG procedures per patient.

   **Top diagnoses:** `SELECT cie10_code, COUNT(*) FROM clinical_record_diagnoses JOIN clinical_records WHERE [period] AND [scope] GROUP BY cie10_code ORDER BY COUNT(*) DESC LIMIT :top_n`. JOIN with `cie10_catalog` table for descriptions.

   **Top procedures:** `SELECT cups_code, COUNT(*), AVG(actual_duration_minutes) FROM clinical_record_procedures WHERE [period] AND [scope] GROUP BY cups_code ORDER BY COUNT(*) DESC LIMIT :top_n`. JOIN with `cups_catalog` for descriptions.

   **Treatment plan analysis:** Duration = `AVG(completed_at - created_at)` for completed plans. Median computed via `PERCENTILE_CONT(0.5)`. Status counts via GROUP BY.

   **Completion rate by plan type:** `GROUP BY plan_type, status` — compute rate per type.

   **Procedure volume over time:** `DATE_TRUNC('month', performed_at) GROUP BY` ordered ascending.

6. Compute percentages for diagnoses and procedures.
7. Assemble response and cache with 300s TTL.
8. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| period | Enum: today, this_week, this_month, this_quarter, this_year, custom | Período no válido. |
| top_n | Integer between 5 and 50 | El valor de 'top_n' debe estar entre 5 y 50. |
| date_from | Valid ISO date, required for custom | La fecha de inicio es requerida. |
| date_to | Valid ISO date, >= date_from, max 366 days | La fecha de fin no es válida. |

**Business Rules:**

- CIE-10 and CUPS descriptions are fetched from shared catalog tables in the public schema (`public.cie10_catalog`, `public.cups_catalog`) — shared across all tenants. If a code is not found in the catalog (custom codes), `description` = `"Código personalizado: {code}"`.
- `treatment_plan_duration_days` = `(completed_at - created_at)` in days. Includes only plans with status `completed`. Null if no completed plans exist.
- `average_procedures_per_patient` = `total_procedures / COUNT(DISTINCT patient_id)`.
- `percentage_of_total_diagnoses` is computed relative to all diagnoses recorded in the period (even those not in top N). Sum of top N percentages may be < 100% if there are codes outside the top N.
- Abandoned treatment plans are excluded from `average_treatment_plan_duration_days` computation (incomplete — not meaningful duration data).
- Procedure volume over time uses monthly granularity always (sufficient for year-long analysis). For shorter periods, monthly may produce 1-3 data points, which is acceptable.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No clinical records in period | All counts = 0, empty top arrays, analysis fields null |
| top_n=5 but only 3 unique diagnoses exist | Returns 3 diagnoses, not error |
| CIE-10 code not in catalog | Description set to "Código personalizado: {code}" |
| No completed treatment plans | average_treatment_plan_duration_days = null, median = null |
| Single patient with 100 procedures | average_procedures_per_patient = 100 (correct) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- All queries READ-ONLY.
- Also reads from `public.cie10_catalog` and `public.cups_catalog` (shared cross-tenant read).

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:analytics:clinical:{doctor_filter}:{date_from}:{date_to}:{top_n}`: SET, 300s TTL.

**Cache TTL:** 300 seconds.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — clinical data access (PHI-adjacent).
- **Action:** read
- **Resource:** analytics_clinical
- **PHI involved:** Indirect — aggregated clinical codes and frequencies. No individual patient data returned. Audit entry logs user, tenant, date range, and timestamp.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 300ms (cached), < 2500ms (cache miss — catalog JOINs add latency)
- **Maximum acceptable:** < 5000ms

### Caching Strategy
- **Strategy:** Redis cache, 5-minute TTL
- **Cache key:** `tenant:{tenant_id}:analytics:clinical:{doctor_filter_hash}:{date_from}:{date_to}:{top_n}`
- **TTL:** 300 seconds
- **Invalidation:** Time-based expiry

### Database Performance

**Queries executed:** 6-8 concurrent async queries including cross-schema JOINs

**Indexes required:**
- `clinical_records.(doctor_id, created_at)` — scope + period filter
- `clinical_record_diagnoses.(clinical_record_id, cie10_code)` — diagnosis counts
- `clinical_record_procedures.(clinical_record_id, cups_code, performed_at)` — procedure counts and time-series
- `treatment_plans.(doctor_id, status, created_at, completed_at)` — plan analysis
- `public.cie10_catalog.(code)` — shared catalog lookup
- `public.cups_catalog.(code)` — shared catalog lookup

**N+1 prevention:** All GROUP BY aggregate queries. Catalog JOINs are single JOIN operations per query.

### Pagination

**Pagination:** No.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| period | Pydantic enum | |
| top_n | Pydantic int with ge=5, le=50 | |
| date_from / date_to | Pydantic date | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** Pydantic serialization. CIE-10 and CUPS descriptions from catalog are system data, not user-generated.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Clinical codes (CIE-10, CUPS) are statistical aggregates. No individual patient diagnoses or identifiers are returned. The aggregated diagnostic patterns of a clinic are not individually identifiable PHI.

**Audit requirement:** All access logged — clinical analytics is PHI-adjacent.

---

## Testing

### Test Cases

#### Happy Path
1. clinic_owner — full clinical analytics for this_year
   - **Given:** 524 clinical records with 15 unique CIE-10 codes and 20 CUPS codes
   - **When:** GET /api/v1/analytics/clinical?period=this_year&top_n=10
   - **Then:** top_diagnoses has 10 items sorted by count desc; top_procedures has 10 items; completion_rate computed correctly

2. doctor role — scoped
   - **Given:** Doctor has 120 of 524 total clinical records
   - **When:** GET /api/v1/analytics/clinical
   - **Then:** total_clinical_records_in_period = 120; top codes reflect only this doctor's patients

3. top_n parameter
   - **Given:** 8 unique diagnosis codes in period
   - **When:** GET /api/v1/analytics/clinical?top_n=5
   - **Then:** top_diagnoses has 5 items (top 5 by count); percentage_of_total based on all 8 codes' counts

#### Edge Cases
1. CIE-10 code not in catalog
   - **Given:** Clinical records with custom code "K99.99"
   - **When:** GET /api/v1/analytics/clinical
   - **Then:** "K99.99" appears with description "Código personalizado: K99.99"

2. No completed treatment plans
   - **Given:** All treatment plans in active or draft status
   - **When:** GET /api/v1/analytics/clinical
   - **Then:** treatment_plan_analysis.average_duration_days = null, median = null; no error

3. Empty period
   - **Given:** No clinical activity in selected period
   - **When:** GET /api/v1/analytics/clinical
   - **Then:** All counts = 0, top arrays empty

#### Error Cases
1. top_n > 50
   - **When:** GET ?top_n=100
   - **Then:** 400 with Spanish error

2. Unauthorized role (assistant)
   - **When:** assistant requests endpoint
   - **Then:** 403

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (for 403).

**Patients/Entities:** 50+ clinical records with varied CIE-10 diagnoses (min 5 unique codes), CUPS procedures (min 5 unique codes), treatment plans with varied statuses and completion dates. `public.cie10_catalog` and `public.cups_catalog` tables seeded in test DB.

### Mocking Strategy

- Redis: fakeredis.
- Database: Full tenant schema with clinical data; shared public schema with CIE-10 and CUPS catalogs.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Top diagnoses (CIE-10) returned sorted by count, with Spanish descriptions from catalog
- [ ] Top procedures (CUPS) returned sorted by count, with average duration
- [ ] Treatment plan completion rate and duration computed correctly
- [ ] `average_procedures_per_patient` correctly computed across distinct patients
- [ ] Unknown CIE-10/CUPS codes use fallback description (no 500 error)
- [ ] doctor role scoped to own clinical data
- [ ] Audit log entry generated for every access
- [ ] 5-minute Redis cache applied
- [ ] 403 for unauthorized roles
- [ ] top_n validated: 400 if outside 5-50 range
- [ ] All test cases pass
- [ ] Performance targets met (< 2500ms cache miss including catalog JOINs)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Per-patient clinical history drill-down
- Epidemiological trend analysis
- ICD-11 support (v1 uses CIE-10 per Colombian regulations)
- Clinical outcome tracking (post-treatment follow-up)
- Imaging analytics (radiograph patterns)
- Voice-to-Odontogram classification analytics

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Uses tenant schema isolation
- [x] Cross-schema public catalog reads documented
- [x] Matches FastAPI conventions

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization defined
- [x] SQL injection prevented
- [x] No individual PHI in response
- [x] Audit trail defined (mandatory — clinical data)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized (cross-schema indexes)
- [x] Pagination defined

### Hook 5: Observability
- [x] Structured logging
- [x] Audit log entries defined
- [x] Error tracking
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data requirements specified
- [x] Mocking strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
