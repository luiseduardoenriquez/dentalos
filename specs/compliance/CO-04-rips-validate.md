# CO-04 — RIPS Validate Spec

## Overview

**Feature:** Validate a generated RIPS batch against MinSalud rules before submission to the government portal. Runs a comprehensive set of Colombian MinSalud validation rules against each record in each file, returning structured errors and warnings with references to the specific patient/procedure/clinical records that need correction. Designed to be run after CO-01 generation and before manual submission.

**Domain:** compliance

**Priority:** Low (Sprint 13-14)

**Dependencies:** CO-01 (rips-generate), CO-02 (rips-get), infra/bg-processing.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Batch must belong to the requesting tenant. Only available for `country = "CO"` tenants. Batch must be in a validatable state (generated or generated_with_errors); cannot validate a queued, generating, or failed batch.

---

## Endpoint

```
POST /api/v1/compliance/rips/{batch_id}/validate
```

**Rate Limiting:**
- 10 requests per hour per tenant (validation is compute-intensive)
- 429 with retry-after if limit exceeded

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| batch_id | Yes | string (UUID) | Valid UUID v4 | Batch to validate | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "rule_sets": "array[string] (optional) — specific rule sets to run: [structure, codes, demographics, cross_file, completeness]; omit to run all",
  "severity_threshold": "string (optional, default=warning) — minimum severity to report: error | warning",
  "max_errors_per_file": "integer (optional, default=200, max=500) — cap errors returned per file type to avoid oversized responses"
}
```

**Example Request:**
```json
{
  "rule_sets": ["structure", "codes", "demographics", "cross_file", "completeness"],
  "severity_threshold": "warning",
  "max_errors_per_file": 200
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "batch_id": "string (UUID)",
  "period": "string — YYYY-MM",
  "validated_at": "string (ISO 8601)",
  "is_valid": "boolean — true only if error_count == 0",
  "is_submittable": "boolean — true if error_count == 0 (warnings alone do not block submission)",
  "summary": {
    "total_records_checked": "integer",
    "error_count": "integer",
    "warning_count": "integer",
    "files_with_errors": "array[string] — file types that have at least one error",
    "files_clean": "array[string] — file types with no errors or warnings",
    "rule_sets_run": "array[string]"
  },
  "results_by_file": {
    "AF": {
      "file_type": "AF",
      "records_checked": "integer",
      "error_count": "integer",
      "warning_count": "integer",
      "is_valid": "boolean",
      "errors_truncated": "boolean"
    }
  },
  "errors": [
    {
      "error_id": "string (UUID)",
      "file_type": "string — AF | AC | AP | AT | AM | AN | AU",
      "severity": "string — error | warning",
      "rule_code": "string — MinSalud rule identifier",
      "rule_description": "string — plain-language rule being violated",
      "message": "string — specific violation message in Spanish",
      "record_ref": "string — internal record identifier for linking",
      "record_type": "string — appointment | clinical_record | prescription | patient",
      "field_name": "string | null — which RIPS field failed",
      "field_value_preview": "string | null — preview of the invalid value (PHI-safe)",
      "corrective_action": "string — step-by-step fix guidance in Spanish",
      "correction_url": "string | null — deep-link to the record in the app",
      "fix_priority": "string — immediate | before_submission | advisory"
    }
  ],
  "warnings": [
    {
      "error_id": "string (UUID)",
      "file_type": "string",
      "severity": "warning",
      "rule_code": "string",
      "message": "string",
      "record_ref": "string | null",
      "corrective_action": "string"
    }
  ],
  "rule_set_results": {
    "structure": { "passed": "boolean", "error_count": "integer", "warning_count": "integer" },
    "codes": { "passed": "boolean", "error_count": "integer", "warning_count": "integer" },
    "demographics": { "passed": "boolean", "error_count": "integer", "warning_count": "integer" },
    "cross_file": { "passed": "boolean", "error_count": "integer", "warning_count": "integer" },
    "completeness": { "passed": "boolean", "error_count": "integer", "warning_count": "integer" }
  }
}
```

**Example:**
```json
{
  "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "period": "2026-01",
  "validated_at": "2026-02-01T10:00:00Z",
  "is_valid": false,
  "is_submittable": false,
  "summary": {
    "total_records_checked": 832,
    "error_count": 15,
    "warning_count": 3,
    "files_with_errors": ["AF", "AU"],
    "files_clean": ["AC", "AP", "AT", "AM", "AN"],
    "rule_sets_run": ["structure", "codes", "demographics", "cross_file", "completeness"]
  },
  "results_by_file": {
    "AF": {
      "file_type": "AF",
      "records_checked": 214,
      "error_count": 10,
      "warning_count": 2,
      "is_valid": false,
      "errors_truncated": false
    },
    "AU": {
      "file_type": "AU",
      "records_checked": 148,
      "error_count": 5,
      "warning_count": 1,
      "is_valid": false,
      "errors_truncated": false
    }
  },
  "errors": [
    {
      "error_id": "err-001-uuid",
      "file_type": "AF",
      "severity": "error",
      "rule_code": "RIPS-AF-012",
      "rule_description": "El código de diagnóstico principal debe ser un código CIE-10 válido de 4 caracteres",
      "message": "Código de diagnóstico 'K021' no encontrado en tabla CIE-10 vigente",
      "record_ref": "appt_abc123",
      "record_type": "appointment",
      "field_name": "cod_diagnostico_principal",
      "field_value_preview": "K021",
      "corrective_action": "Corrija el diagnóstico en el registro clínico del paciente. Verifique el código CIE-10 correcto (posiblemente K02.1).",
      "correction_url": "/patients/pat_xyz/records/cr_123",
      "fix_priority": "immediate"
    }
  ],
  "warnings": [
    {
      "error_id": "warn-001-uuid",
      "file_type": "AF",
      "severity": "warning",
      "rule_code": "RIPS-AF-W03",
      "message": "Número de consultas para este paciente excede el promedio mensual esperado (>20)",
      "record_ref": "pat_xyz456",
      "corrective_action": "Verifique que todas las consultas sean clínicamente justificadas."
    }
  ],
  "rule_set_results": {
    "structure": { "passed": true, "error_count": 0, "warning_count": 0 },
    "codes": { "passed": false, "error_count": 10, "warning_count": 0 },
    "demographics": { "passed": false, "error_count": 5, "warning_count": 1 },
    "cross_file": { "passed": true, "error_count": 0, "warning_count": 2 },
    "completeness": { "passed": true, "error_count": 0, "warning_count": 0 }
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid `rule_sets` values; `max_errors_per_file` exceeds 500; `severity_threshold` not valid.

**Example:**
```json
{
  "error": "invalid_rule_set",
  "message": "rule_sets contains unrecognized values",
  "details": {
    "rule_sets": ["'financial' is not a valid rule set. Choose from: structure, codes, demographics, cross_file, completeness"]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Caller does not have `clinic_owner` role, or tenant country is not Colombia, or batch belongs to different tenant.

#### 404 Not Found
**When:** Batch with given batch_id does not exist in the tenant context.

#### 409 Conflict
**When:** Batch is in a non-validatable state: queued, generating, or failed.

**Example:**
```json
{
  "error": "batch_not_validatable",
  "message": "Batch cannot be validated in its current state",
  "details": {
    "current_status": "generating",
    "validatable_statuses": ["generated", "generated_with_errors", "validated", "submitted", "rejected"]
  }
}
```

#### 422 Unprocessable Entity
**When:** Request body fails Pydantic validation; batch_id is not a valid UUID.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "batch_id": ["value is not a valid UUID"],
    "max_errors_per_file": ["ensure this value is less than or equal to 500"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded (10 validations/hour per tenant). See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Validation engine encounter unrecoverable error; file not found in storage.

---

## Business Logic

**Step-by-step process:**

1. Validate request body and path parameter via Pydantic schema `RIPSValidateRequest`.
2. Resolve tenant_id from JWT; verify `tenant.country == "CO"`.
3. Verify caller has `clinic_owner` role.
4. Fetch batch from `rips_batches` WHERE `id = batch_id AND tenant_id = tenant_id`. Return 404 if not found.
5. Check batch status: must be `generated`, `generated_with_errors`, `validated`, `submitted`, or `rejected`. Return 409 for other statuses.
6. Normalize `rule_sets`: default to all five if omitted.
7. Read each requested RIPS file from object storage (streaming, to avoid memory overload).
8. Run validation rule sets in sequence:

   **Structure rules (`RIPS-*-S*`):**
   - Record count matches header
   - Field widths conform to MinSalud column specification
   - Required columns present and non-empty
   - Date fields in correct format (YYYYMMDD)
   - Numeric fields are valid numbers

   **Code validation rules (`RIPS-*-C*`):**
   - `cod_diagnostico_*` fields are valid CIE-10 codes (lookup in `cie10_codes` reference table, version in use per CO-08)
   - `cod_procedimiento` values are valid CUPS codes (lookup in `cups_codes` reference table)
   - `cod_medicamento` values are valid CUMS codes for AM file
   - `tipo_documento_id` values are in MinSalud-accepted document type list
   - `cod_entidad` (insurance entity codes) are valid RIPS entity codes

   **Demographics rules (`RIPS-*-D*`):**
   - `numero_id_usuario` (patient identifier) is non-empty and matches allowed formats per document type
   - Age calculations are consistent with birth date + service date
   - Gender codes are valid (M, F, I for intersex/indeterminate)
   - Department/municipality codes (DANE codes) are valid

   **Cross-file consistency rules (`RIPS-X-*`):**
   - Every patient in AF/AC/AP/AT/AM/AN must have a corresponding record in AU
   - Appointment dates in AF/AC are within the declared report period
   - Procedure codes in AC must reference appointments in AF
   - Prescription records in AM reference patients in AU

   **Completeness rules (`RIPS-*-P*`):**
   - All mandatory fields populated (no empty strings in required columns)
   - No duplicate records within same file (same patient + date + procedure combination)
   - NIT prestador is consistent across all records

9. Aggregate errors and warnings. Cap per-file error list at `max_errors_per_file`.
10. Persist validation results to `rips_batch_validations` table; update `rips_batch_errors` table.
11. Update batch status:
    - If `error_count == 0`: set status to `validated`
    - If `error_count > 0`: status remains `generated_with_errors`; update `error_count` and `warning_count`
12. Write audit log: action=`rips_validate`, resource=`rips_batch`, resource_id=`batch_id`.
13. Return 200 with full validation result.

**MinSalud Rule Code Format:**

`RIPS-{FILE_TYPE}-{CATEGORY}{NUM}`
- FILE_TYPE: AF, AC, AP, AT, AM, AN, AU, X (cross-file)
- CATEGORY: S (structure), C (code), D (demographics), P (completeness)
- NUM: 3-digit number

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| batch_id | Valid UUID v4 | "batch_id must be a valid UUID" |
| rule_sets | Array of structure, codes, demographics, cross_file, completeness | "Conjunto de reglas no válido" |
| severity_threshold | error or warning | "severity_threshold must be 'error' or 'warning'" |
| max_errors_per_file | Integer, 1–500 | "max_errors_per_file debe estar entre 1 y 500" |

**Business Rules:**

- `is_valid = true` only when `error_count == 0`. Warnings do not affect `is_valid`.
- `is_submittable` mirrors `is_valid` in the current spec (may be relaxed in future for certain warning-only scenarios).
- Re-running validation on an already-validated batch is allowed; previous validation results are overwritten.
- `correction_url` links to the DentalOS record (appointment, clinical record, patient) where the fix must be made. After fixing, CO-01 must be re-run to regenerate the affected files.
- `field_value_preview` for PHI fields (NUIP, patient name) shows only a partial value or a safe alternative to avoid logging PHI. Example: "K021" (a diagnosis code) is not PHI and is shown in full; a NUIP would be shown as "***1234".
- Validation is synchronous (runs in the request/response cycle) for batches up to 2,000 records. For larger batches, validation is dispatched as an async job returning 202 with a validation_job_id (implementation detail; spec assumes synchronous for typical clinic sizes).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| All 7 files pass validation | is_valid=true, is_submittable=true, status updated to 'validated' |
| Batch has zero records (empty month) | Validation passes; structure rules check header consistency; is_valid=true |
| CIE-10 reference table not loaded | Returns 503 with "validation_service_unavailable"; batch status unchanged |
| Re-validate already-validated batch | Allowed; fresh validation replaces previous results; status may revert to generated_with_errors if new errors found |
| errors exceed max_errors_per_file | First max_errors_per_file errors returned per file; errors_truncated=true on that file |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `rips_batches`: UPDATE `status`, `error_count`, `warning_count`, `validated_at`
- `rips_batch_errors`: DELETE (prior errors for batch) + INSERT (new errors from this validation run)
- `rips_batch_validations`: INSERT — full validation run record with summary stats

**Example query (SQLAlchemy):**
```python
# Update batch after validation
await session.execute(
    update(RIPSBatch)
    .where(RIPSBatch.id == batch_id)
    .values(
        status=new_status,
        error_count=error_count,
        warning_count=warning_count,
        validated_at=utcnow(),
    )
)

# Upsert validation run record
validation_run = RIPSBatchValidation(
    id=uuid4(),
    batch_id=batch_id,
    rule_sets_run=rule_sets,
    total_records_checked=total_records,
    error_count=error_count,
    warning_count=warning_count,
    validated_by=current_user.id,
    validated_at=utcnow(),
)
session.add(validation_run)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:rips:batch:{batch_id}`: INVALIDATE — status changed
- `tenant:{tenant_id}:rips:list:*`: INVALIDATE (wildcard) — list must reflect updated status

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None for synchronous path.

For async path (large batches > 2,000 records):
| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| rips.validation | rips_validate_async | `{ batch_id, tenant_id, rule_sets, max_errors_per_file }` | Batch record count > 2,000 |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** update
- **Resource:** rips_batch
- **PHI involved:** Yes — validation reads patient clinical records

### Notifications

**Notifications triggered:** Yes (on completion if async)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | rips_validation_passed | clinic_owner | Async validation completes with is_valid=true |
| in-app | rips_validation_failed | clinic_owner | Async validation completes with error_count > 0 |

---

## Performance

### Expected Response Time
- **Target:** < 5,000ms for batches up to 2,000 records (synchronous)
- **Maximum acceptable:** < 10,000ms before switching to async path
- **Async path:** immediate 202 response; validation job completes within 5 minutes

### Caching Strategy
- **Strategy:** No caching on validation response (results must be fresh)
- **Reference tables (CIE-10, CUPS):** Pre-loaded into Redis as sorted sets for O(1) code lookup
  - `reference:cie10_codes` — Redis set of valid codes
  - `reference:cups_codes` — Redis set of valid codes
  - TTL: 24 hours (refreshed when MinSalud catalog is updated)

### Database Performance

**Queries executed:** 4–8 (batch fetch, file reads from storage, reference lookups via Redis, batch update, error inserts)

**Indexes required:**
- `rips_batch_errors.(batch_id)` — INDEX for clearing prior errors
- `rips_batch_validations.(batch_id, validated_at DESC)` — COMPOSITE INDEX for validation history

**N+1 prevention:** Reference code lookups use Redis set membership (SISMEMBER), not DB queries, to avoid N+1 on code validation.

### Pagination

**Pagination:** No (errors are capped via max_errors_per_file; full list available via CO-02 with include_errors=true)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| batch_id | UUID validation via Pydantic Path | Rejects non-UUID strings |
| rule_sets | Pydantic Literal array validation | Only known rule set names |
| severity_threshold | Pydantic Literal enum | Only "error" or "warning" |
| max_errors_per_file | Pydantic integer, ge=1, le=500 | Bounded to prevent oversized response |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. `field_value_preview` truncated and sanitized before inclusion in response.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `field_value_preview` may contain diagnosis codes (CIE-10 — not PHI) or document type codes. Patient names and full NUIP numbers are never included in error responses. record_ref contains internal record IDs only.

**Audit requirement:** All validation runs logged; PHI accessed by the validation engine is not logged at the field level.

---

## Testing

### Test Cases

#### Happy Path
1. Validate clean batch (no errors)
   - **Given:** batch with status=generated, all records have valid CIE-10/CUPS codes, complete demographics
   - **When:** POST /api/v1/compliance/rips/{batch_id}/validate
   - **Then:** 200 OK, is_valid=true, error_count=0, batch status updated to validated

2. Validate batch with code errors
   - **Given:** batch with 5 invalid CIE-10 codes and 3 invalid CUPS codes
   - **When:** POST with default rule_sets
   - **Then:** 200 OK, is_valid=false, error_count=8, errors include rule_code=RIPS-AF-C*, correction_url populated

3. Run only codes rule set
   - **Given:** batch with structural and code errors
   - **When:** POST with rule_sets=["codes"]
   - **Then:** 200 OK, only code errors returned; rule_set_results shows only codes key populated

#### Edge Cases
1. Re-validate already-validated batch
   - **Given:** batch with status=validated from previous run
   - **When:** POST validate again
   - **Then:** 200 OK, fresh validation runs; if no changes, is_valid=true again

2. Empty period (zero records)
   - **Given:** batch with status=generated, record_count=0
   - **When:** POST validate
   - **Then:** 200 OK, is_valid=true (headers valid), total_records_checked=0

#### Error Cases
1. Validate generating batch
   - **Given:** batch with status=generating
   - **When:** POST /api/v1/compliance/rips/{batch_id}/validate
   - **Then:** 409 Conflict, "batch_not_validatable"

2. Invalid rule_set value
   - **Given:** clinic_owner JWT
   - **When:** POST with rule_sets=["financial"]
   - **Then:** 400 Bad Request, invalid_rule_set

3. Non-owner attempts validation
   - **Given:** doctor JWT
   - **When:** POST validate
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner for Colombian tenant, doctor (for 403 test)

**Patients/Entities:** Multiple rips_batch fixtures with known error profiles; Redis loaded with CIE-10 and CUPS reference data; batch with intentionally invalid codes for error-path testing

### Mocking Strategy

- Storage service: Mock file reads returning known RIPS file content
- Redis reference tables: Preload known valid/invalid codes into test Redis instance
- CIE-10/CUPS lookup: Use small fixture-based reference sets

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST returns 200 with is_valid=true when all rules pass
- [ ] POST returns 200 with is_valid=false and structured errors when rules fail
- [ ] All 5 rule sets functional (structure, codes, demographics, cross_file, completeness)
- [ ] Errors contain rule_code, message, record_ref, correction_url
- [ ] Batch status updated to validated (on pass) or remains generated_with_errors (on fail)
- [ ] 409 returned for non-validatable statuses
- [ ] CIE-10 and CUPS code lookups use Redis reference sets
- [ ] max_errors_per_file cap enforced; errors_truncated flag set correctly
- [ ] is_valid and is_submittable correctly computed
- [ ] All test cases pass
- [ ] Performance target: < 5s for 2,000 records
- [ ] Quality Hooks passed
- [ ] Audit logging verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Automatic submission to MinSalud (submission is manual; DentalOS generates and validates only)
- Fixing records (correction is done in clinical/patient modules, then files must be re-generated)
- XML-format RIPS (this spec covers the MinSalud delimited text format)
- Validation of RIPS files uploaded from external sources (only internally generated batches)
- Real-time validation during clinical record entry (that is handled in clinical-records/ specs)

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
- [x] Caching strategy stated (Redis reference tables)
- [x] DB queries optimized (indexes listed)
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
