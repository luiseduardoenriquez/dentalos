# CO-05 — RDA Status Spec

## Overview

**Feature:** Check the RDA (Registro Dental Automatizado) compliance status for the tenant's clinic, as required by Colombia Resolución 1888 with a deadline of April 2026. Returns an overall compliance percentage, field-by-field capture status, identified gaps, and actionable recommendations to reach full compliance before the deadline.

**Domain:** compliance

**Priority:** High (Sprint 13-14, but high urgency given April 2026 deadline)

**Dependencies:** patients/P-01, odontogram/OD-01, clinical-records/CR-01, CO-08 (country-config), infra/caching.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only available for `country = "CO"` tenants. Returns 403 for non-Colombian tenants. Response is a snapshot computed from current data; it does not modify any records.

---

## Endpoint

```
GET /api/v1/compliance/rda/status
```

**Rate Limiting:**
- 20 requests per minute per tenant (status checks can be frequent; computation is cached)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| refresh | No | boolean | default=false | Force cache bypass and recompute | true |
| include_patient_breakdown | No | boolean | default=false | Include per-patient compliance breakdown (may be large) | false |
| since_date | No | string | ISO 8601 date | Only evaluate records created on or after this date | 2026-01-01 |

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "computed_at": "string (ISO 8601) — when this snapshot was computed",
  "cache_hit": "boolean — was this result from cache",
  "deadline": "string — ISO 8601 date of RDA compliance deadline (2026-04-01 for Colombia)",
  "days_until_deadline": "integer",
  "overall_compliance_percentage": "number — 0.0 to 100.0 (rounded to 1 decimal)",
  "is_compliant": "boolean — true if overall_compliance_percentage >= 95.0",
  "compliance_level": "string — critical (<50%) | at_risk (50–79%) | improving (80–94%) | compliant (>=95%)",
  "compliance_level_display": "string — Spanish label",
  "regulatory_reference": "string — 'Colombia Resolución 1888 de 2021'",
  "scope": {
    "total_patients_evaluated": "integer",
    "total_clinical_records_evaluated": "integer",
    "total_odontograms_evaluated": "integer",
    "evaluation_period": "string — ISO 8601 date range"
  },
  "required_fields_status": [
    {
      "field_id": "string — machine identifier",
      "field_name": "string — human-readable field name in Spanish",
      "module": "string — patients | odontogram | clinical_records | treatment_plans",
      "is_required_by_rda": "boolean",
      "total_records": "integer — records that should have this field",
      "captured_count": "integer — records where field is populated",
      "missing_count": "integer",
      "percentage_complete": "number — 0.0 to 100.0",
      "is_compliant": "boolean — percentage_complete >= threshold (usually 100% for critical fields)",
      "compliant_threshold": "number — minimum % required",
      "rda_article": "string — article in Resolución 1888 requiring this field",
      "severity": "string — critical | required | recommended"
    }
  ],
  "gaps": [
    {
      "gap_id": "string",
      "title": "string — short gap description in Spanish",
      "description": "string — detailed explanation in Spanish",
      "module": "string",
      "field_ids": "array[string] — related field_ids",
      "affected_record_count": "integer",
      "severity": "string — critical | required | recommended",
      "compliance_impact": "number — percentage points this gap costs",
      "recommended_action": "string — actionable step in Spanish",
      "action_url": "string | null — deep-link to the relevant module in the app",
      "estimated_fix_time": "string — e.g. '2 semanas' (rough estimate for planning)"
    }
  ],
  "module_breakdown": {
    "patients": {
      "module": "patients",
      "compliance_percentage": "number",
      "fields_total": "integer",
      "fields_compliant": "integer",
      "critical_gaps": "integer"
    },
    "odontogram": {
      "module": "odontogram",
      "compliance_percentage": "number",
      "fields_total": "integer",
      "fields_compliant": "integer",
      "critical_gaps": "integer"
    },
    "clinical_records": {
      "module": "clinical_records",
      "compliance_percentage": "number",
      "fields_total": "integer",
      "fields_compliant": "integer",
      "critical_gaps": "integer"
    },
    "treatment_plans": {
      "module": "treatment_plans",
      "compliance_percentage": "number",
      "fields_total": "integer",
      "fields_compliant": "integer",
      "critical_gaps": "integer"
    }
  },
  "patient_breakdown": "array[PatientComplianceItem] | null — only if include_patient_breakdown=true"
}
```

**PatientComplianceItem schema (when include_patient_breakdown=true):**
```json
{
  "patient_id": "string",
  "patient_display": "string — first name + last initial (PHI-safe display)",
  "compliance_percentage": "number",
  "missing_fields": "array[string] — field_ids missing for this patient",
  "last_visit": "string (ISO 8601) | null"
}
```

**Example:**
```json
{
  "computed_at": "2026-02-25T09:00:00Z",
  "cache_hit": true,
  "deadline": "2026-04-01",
  "days_until_deadline": 35,
  "overall_compliance_percentage": 78.4,
  "is_compliant": false,
  "compliance_level": "at_risk",
  "compliance_level_display": "En riesgo",
  "regulatory_reference": "Colombia Resolución 1888 de 2021",
  "scope": {
    "total_patients_evaluated": 312,
    "total_clinical_records_evaluated": 1847,
    "total_odontograms_evaluated": 289,
    "evaluation_period": "2021-01-01/2026-02-25"
  },
  "required_fields_status": [
    {
      "field_id": "patient.tipo_documento",
      "field_name": "Tipo de documento de identidad",
      "module": "patients",
      "is_required_by_rda": true,
      "total_records": 312,
      "captured_count": 312,
      "missing_count": 0,
      "percentage_complete": 100.0,
      "is_compliant": true,
      "compliant_threshold": 100.0,
      "rda_article": "Art. 5, Parágrafo 1",
      "severity": "critical"
    },
    {
      "field_id": "odontogram.initial_exam_date",
      "field_name": "Fecha del examen odontológico inicial",
      "module": "odontogram",
      "is_required_by_rda": true,
      "total_records": 312,
      "captured_count": 245,
      "missing_count": 67,
      "percentage_complete": 78.5,
      "is_compliant": false,
      "compliant_threshold": 100.0,
      "rda_article": "Art. 8, Literal b",
      "severity": "critical"
    }
  ],
  "gaps": [
    {
      "gap_id": "gap_001",
      "title": "Odontograma inicial faltante en 67 pacientes",
      "description": "La Resolución 1888 exige un examen odontológico inicial completo para todos los pacientes. 67 pacientes no tienen odontograma registrado.",
      "module": "odontogram",
      "field_ids": ["odontogram.initial_exam_date", "odontogram.initial_condition"],
      "affected_record_count": 67,
      "severity": "critical",
      "compliance_impact": 4.2,
      "recommended_action": "Realice y registre el odontograma inicial para los 67 pacientes identificados. Priorice pacientes con citas activas.",
      "action_url": "/patients?filter=missing_odontogram",
      "estimated_fix_time": "2–3 semanas con atención dedicada"
    }
  ],
  "module_breakdown": {
    "patients": { "module": "patients", "compliance_percentage": 97.2, "fields_total": 12, "fields_compliant": 11, "critical_gaps": 0 },
    "odontogram": { "module": "odontogram", "compliance_percentage": 68.3, "fields_total": 8, "fields_compliant": 5, "critical_gaps": 2 },
    "clinical_records": { "module": "clinical_records", "compliance_percentage": 82.1, "fields_total": 15, "fields_compliant": 12, "critical_gaps": 1 },
    "treatment_plans": { "module": "treatment_plans", "compliance_percentage": 74.0, "fields_total": 6, "fields_compliant": 4, "critical_gaps": 1 }
  },
  "patient_breakdown": null
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Caller does not have `clinic_owner` role, or tenant country is not Colombia.

**Example:**
```json
{
  "error": "forbidden",
  "message": "RDA compliance status is only available for Colombian clinics (country=CO)",
  "details": {}
}
```

#### 422 Unprocessable Entity
**When:** `since_date` is not a valid ISO 8601 date, or query param type errors.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "since_date": ["invalid date format; expected YYYY-MM-DD"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Compliance engine failure or unexpected DB error.

---

## Business Logic

**Step-by-step process:**

1. Validate query parameters via Pydantic schema `RDAStatusParams`.
2. Resolve tenant_id from JWT; verify `tenant.country == "CO"`.
3. Verify caller has `clinic_owner` role.
4. Check cache: `tenant:{tenant_id}:rda:status` — if hit and `refresh=false`, return cached response.
5. Load RDA field requirements from `compliance_config` (country adapter for Colombia, CO-08). This defines:
   - All required fields (41 total in Resolución 1888)
   - The source table/column for each field
   - The severity (critical/required/recommended)
   - The RDA article reference
   - The compliance threshold (usually 100% for critical, 90% for required, 80% for recommended)
6. For each required field, execute COUNT aggregate query on the tenant schema:
   - `total_records`: COUNT of records where this field applies (e.g., all patients, all clinical records in the period)
   - `captured_count`: COUNT of records where the field is non-null AND non-empty
7. Compute `percentage_complete` = `captured_count / total_records * 100`.
8. Compute `overall_compliance_percentage`: weighted average across all required fields (critical fields weighted 3x, required 2x, recommended 1x).
9. Determine `compliance_level`:
   - `>= 95.0%`: compliant
   - `80.0–94.9%`: improving
   - `50.0–79.9%`: at_risk
   - `< 50.0%`: critical
10. Build `gaps` list: for each field that is not compliant, group related fields into actionable gap descriptions. Sort gaps by compliance_impact descending (largest impact first).
11. Build `module_breakdown` from aggregated field results per module.
12. Compute `days_until_deadline` from current date to `2026-04-01`.
13. If `include_patient_breakdown=true`, execute per-patient queries (expensive; only for export/reporting use). Limit to 500 patients max in response.
14. Store result in Redis cache: `tenant:{tenant_id}:rda:status` TTL 3600s.
15. Write audit log: action=`rda_status_read`, resource=`rda_compliance`, resource_id=null.
16. Return 200 OK.

**RDA Required Fields (41 fields per Resolución 1888):**

The complete field list is stored in the country adapter config and is not hardcoded in this spec. Representative examples:

| Module | Field ID | Article | Severity |
|--------|----------|---------|---------|
| patients | patient.tipo_documento | Art. 5 §1 | critical |
| patients | patient.numero_documento | Art. 5 §1 | critical |
| patients | patient.fecha_nacimiento | Art. 5 §2 | critical |
| patients | patient.genero | Art. 5 §2 | critical |
| patients | patient.municipio_residencia | Art. 5 §3 | required |
| patients | patient.eps_code | Art. 6 | required |
| odontogram | odontogram.initial_exam_date | Art. 8b | critical |
| odontogram | odontogram.initial_condition | Art. 8b | critical |
| odontogram | odontogram.dentition_type | Art. 8c | required |
| clinical_records | clinical_record.motivo_consulta | Art. 9 §1 | critical |
| clinical_records | clinical_record.diagnostico_principal | Art. 9 §3 | critical |
| clinical_records | clinical_record.cups_procedure_code | Art. 10 §1 | critical |
| treatment_plans | treatment_plan.signed_by_patient | Art. 12 | required |

**Business Rules:**

- Compliance percentage is a point-in-time snapshot; it reflects current state of the database.
- `is_compliant` threshold is 95% (not 100%) to account for edge cases (e.g., anonymous patients, walk-in urgencies without full demographic capture).
- `compliance_impact` on each gap is the contribution of that gap to the overall non-compliance percentage.
- Records created before clinic joined DentalOS are excluded if `since_date` is provided.
- The `action_url` deep-links use the DentalOS frontend URL scheme; backend appends the tenant-appropriate path.
- RDA compliance status is never a hard blocker on clinical operations — it is informational/regulatory only.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| since_date | Valid ISO 8601 date if provided | "since_date must be a valid date (YYYY-MM-DD)" |
| refresh | Boolean | "refresh must be boolean" |
| include_patient_breakdown | Boolean | "include_patient_breakdown must be boolean" |

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant is brand new, zero patients | overall_compliance_percentage = 100.0 (no records to evaluate means no gaps); is_compliant = true; scope shows zero records |
| All fields 100% complete | compliance_level=compliant, is_compliant=true, gaps=[] |
| refresh=true | Bypasses cache; recomputes from DB; updates cache with fresh result |
| include_patient_breakdown=true with 2000 patients | Returns first 500 patients; patient_breakdown_truncated=true flag added |
| Deadline has passed | days_until_deadline=0 (or negative); displayed as "Plazo vencido"; does not change functionality |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- Multiple tables: SELECT only (patients, odontograms, clinical_records, treatment_plans)

**Public schema tables affected:**
- None — read-only

**Example query (SQLAlchemy):**
```python
# Example: compute patient document type compliance
total_patients = await session.scalar(
    select(func.count()).select_from(Patient).where(Patient.tenant_id == tenant_id)
)
patients_with_doc_type = await session.scalar(
    select(func.count()).select_from(Patient).where(
        Patient.tenant_id == tenant_id,
        Patient.tipo_documento.isnot(None),
        Patient.tipo_documento != "",
    )
)
percentage = (patients_with_doc_type / total_patients * 100) if total_patients > 0 else 100.0
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:rda:status`: SET (full response, 3600s) | BYPASS if refresh=true

**Cache TTL:** 3600 seconds (1 hour)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — synchronous endpoint.

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** read
- **Resource:** rda_compliance
- **PHI involved:** No (aggregate statistics; no individual patient data in response unless include_patient_breakdown=true)

### Notifications

**Notifications triggered:** No (status is pull-only; proactive compliance reminders are handled by a scheduled job separate from this endpoint)

---

## Performance

### Expected Response Time
- **Target:** < 200ms (cache hit)
- **Maximum acceptable:** < 3,000ms (cache miss; aggregate queries across all tenant records)

### Caching Strategy
- **Strategy:** Redis cache with 1-hour TTL
- **Cache key:** `tenant:{tenant_id}:rda:status`
- **TTL:** 3600 seconds
- **Invalidation:** Not auto-invalidated (clinic owners refresh manually using `refresh=true`; cache expires naturally after 1 hour)

### Database Performance

**Queries executed:** ~41 aggregate COUNT queries (one per required field), plus 4 module breakdown queries. Total: ~45 queries.

**Optimization:** Batch related field queries per table into single multi-aggregate SELECT to reduce round trips:
```sql
SELECT
  COUNT(*) as total,
  COUNT(tipo_documento) FILTER (WHERE tipo_documento IS NOT NULL AND tipo_documento != '') as doc_type_count,
  COUNT(numero_documento) FILTER (WHERE numero_documento IS NOT NULL AND numero_documento != '') as doc_num_count,
  -- ... all patient fields in one query
FROM patients WHERE tenant_id = $1
```
This reduces 12 patient field queries to 1.

**Indexes required:**
- `patients.(tenant_id)` — INDEX (already exists)
- `odontograms.(tenant_id, patient_id)` — COMPOSITE INDEX
- `clinical_records.(tenant_id, created_at)` — COMPOSITE INDEX for since_date filter
- `treatment_plans.(tenant_id)` — INDEX

**N+1 prevention:** All compliance metrics computed in batch aggregate queries, not per-patient loops.

### Pagination

**Pagination:** No (summary response). Patient breakdown list capped at 500 entries.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| since_date | Pydantic date validator | Validates ISO 8601 format |
| refresh | Pydantic bool | Boolean coercion |
| include_patient_breakdown | Pydantic bool | Boolean coercion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Patient breakdown (when enabled) shows `patient_display` as first name + last initial only (e.g., "María T."). Full names, document numbers, and clinical details are not exposed in this endpoint.

**Audit requirement:** All compliance status checks logged.

---

## Testing

### Test Cases

#### Happy Path
1. Fully compliant clinic
   - **Given:** All 41 RDA fields populated for all patients
   - **When:** GET /api/v1/compliance/rda/status
   - **Then:** 200 OK, overall_compliance_percentage=100.0, is_compliant=true, gaps=[]

2. At-risk clinic (78% compliance)
   - **Given:** Odontogram fields missing for 30% of patients; some clinical record fields empty
   - **When:** GET /api/v1/compliance/rda/status
   - **Then:** 200 OK, compliance_level=at_risk, gaps list populated, module_breakdown shows odontogram low

3. Cache hit
   - **Given:** Cached result exists
   - **When:** GET /api/v1/compliance/rda/status
   - **Then:** 200 OK, cache_hit=true, response in < 200ms

4. Force refresh
   - **Given:** Cached result exists
   - **When:** GET /api/v1/compliance/rda/status?refresh=true
   - **Then:** 200 OK, cache_hit=false, fresh computation

#### Edge Cases
1. Brand new clinic (no patients)
   - **Given:** Tenant created today, zero patients
   - **When:** GET status
   - **Then:** 200 OK, scope shows zero records, overall_compliance_percentage=100.0, is_compliant=true

2. Deadline in the past
   - **Given:** Current date is 2026-05-01 (after April 2026 deadline)
   - **When:** GET status
   - **Then:** 200 OK, days_until_deadline <= 0, deadline shown as passed

#### Error Cases
1. Non-Colombian tenant
   - **Given:** Tenant with country=MX
   - **When:** GET /api/v1/compliance/rda/status
   - **Then:** 403 Forbidden

2. Non-owner access
   - **Given:** Doctor JWT
   - **When:** GET /api/v1/compliance/rda/status
   - **Then:** 403 Forbidden

3. Invalid since_date
   - **Given:** clinic_owner JWT
   - **When:** GET with since_date=notadate
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** clinic_owner for Colombian tenant, doctor (for 403 test), clinic_owner for non-Colombian tenant

**Patients/Entities:** Fixtures with varying field completeness; 50 patients with all fields, 30 with missing odontograms, 20 with incomplete demographics

### Mocking Strategy

- Redis: Use fakeredis; test both cache-hit and cache-miss paths
- Country adapter config: Load test fixture with known 41 field definitions

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns overall_compliance_percentage computed from all 41 RDA fields
- [ ] required_fields_status populated for each field with total/captured/missing counts
- [ ] gaps[] list populated with actionable remediation steps
- [ ] module_breakdown shows per-module compliance percentages
- [ ] compliance_level correctly set (critical/at_risk/improving/compliant)
- [ ] days_until_deadline computed from current date to 2026-04-01
- [ ] Redis cache used (1h TTL); refresh=true bypasses cache
- [ ] 403 for non-Colombian tenants and non-owners
- [ ] All test cases pass
- [ ] Performance target: < 200ms cached, < 3s cold
- [ ] Quality Hooks passed
- [ ] Audit logging verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Automatic data correction (fixing missing fields — that is done in respective module UIs)
- RDA file submission (DentalOS does not directly submit to the MinSalud RDA registry; clinics do so via the government portal)
- Historical compliance tracking over time (trend dashboard — analytics module)
- Non-Colombian compliance (other countries have different field requirements)
- Batch patient record updates (separate admin feature)

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
- [x] Caching strategy stated (1h Redis)
- [x] DB queries optimized (batch aggregates)
- [x] Pagination applied where needed

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
| 1.0 | 2026-02-25 | Initial spec |
