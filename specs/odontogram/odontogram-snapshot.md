# OD-05: Create Odontogram Snapshot Spec

---

## Overview

**Feature:** Create a point-in-time snapshot of a patient's complete odontogram state. Snapshots are denormalized JSONB copies of the full odontogram at the moment of capture, used for before/after treatment comparisons, documentation of initial examination findings, and linking to clinical records or treatment plans. Snapshots are immutable once created.

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-01 (odontogram-get.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Assistants and receptionists cannot create snapshots. Snapshot creation is a clinical documentation act requiring doctor authority.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/odontogram/snapshots
```

**Rate Limiting:**
- 20 requests per minute per user
- Snapshots are intentional acts; high frequency indicates automation or error.

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
| patient_id | Yes | UUID | Valid UUID v4 | Patient identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "label": "string (optional) — max 100 chars. Human-readable label for the snapshot",
  "linked_record_id": "uuid (optional) — UUID of a clinical record to link this snapshot to",
  "linked_treatment_plan_id": "uuid (optional) — UUID of a treatment plan to link this snapshot to"
}
```

**Example Request:**
```json
{
  "label": "Pre-tratamiento ortodoncia",
  "linked_treatment_plan_id": "tp1a2b3c4-d5e6-7890-abcd-123456789abc"
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
  "label": "string | null",
  "dentition_type": "string (adult | pediatric | mixed)",
  "conditions_count": "integer",
  "linked_record_id": "uuid | null",
  "linked_treatment_plan_id": "uuid | null",
  "snapshot_data": {
    "teeth": [
      {
        "tooth_number": "integer",
        "zones": {
          "mesial": { "condition_code": "string | null", "severity": "string | null", "notes": "string | null" },
          "distal": { "...same structure..." },
          "vestibular": { "...same structure..." },
          "lingual": { "...same structure..." },
          "oclusal": { "...same structure..." },
          "root": { "...same structure..." }
        }
      }
    ],
    "total_conditions": "integer",
    "captured_at": "string (ISO 8601)"
  },
  "created_by": "uuid",
  "created_at": "string (ISO 8601)"
}
```

**Example:**
```json
{
  "id": "snap1a2b-3c4d-5e6f-7890-abcd12345678",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "label": "Pre-tratamiento ortodoncia",
  "dentition_type": "adult",
  "conditions_count": 5,
  "linked_record_id": null,
  "linked_treatment_plan_id": "tp1a2b3c4-d5e6-7890-abcd-123456789abc",
  "snapshot_data": {
    "teeth": [
      {
        "tooth_number": 11,
        "zones": {
          "mesial": { "condition_code": null, "severity": null, "notes": null },
          "distal": { "condition_code": "caries", "severity": "mild", "notes": "Caries incipiente" },
          "vestibular": { "condition_code": null, "severity": null, "notes": null },
          "lingual": { "condition_code": null, "severity": null, "notes": null },
          "oclusal": { "condition_code": null, "severity": null, "notes": null },
          "root": { "condition_code": null, "severity": null, "notes": null }
        }
      }
    ],
    "total_conditions": 5,
    "captured_at": "2026-02-24T14:30:00Z"
  },
  "created_by": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
  "created_at": "2026-02-24T14:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or type mismatch on body fields.

```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is assistant, receptionist, or patient.

```json
{
  "error": "forbidden",
  "message": "Solo los medicos pueden crear instantaneas del odontograma."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist in the tenant, or `linked_record_id`/`linked_treatment_plan_id` do not exist in the tenant.

```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails (e.g., label too long, invalid UUID for linked IDs).

```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "label": ["La etiqueta no puede exceder 100 caracteres."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected failure during snapshot creation or odontogram state fetch.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role is in `[clinic_owner, doctor]`. Reject with 403 otherwise.
4. Verify patient exists in tenant schema. Return 404 if not.
5. Fetch `odontogram_states` row for the patient to get `dentition_type` and `odontogram_id`.
6. Fetch all current `odontogram_conditions` for the patient (same query as OD-01 minus history counts).
7. If `linked_record_id` provided: verify it exists in `clinical_records` table for this patient. Return 404 if not.
8. If `linked_treatment_plan_id` provided: verify it exists in `treatment_plans` table for this patient. Return 404 if not.
9. Build `snapshot_data` JSONB: full tooth/zone structure with current condition codes, severity, and notes. Include `captured_at` = current UTC timestamp. Include `total_conditions` count.
10. Insert into `odontogram_snapshots`:
    - `patient_id` = patient_id
    - `snapshot_data` = built JSONB
    - `dentition_type` = from odontogram_states
    - `reason` = `label` value (maps to `reason` column in DB)
    - `linked_record_id` = if provided
    - `linked_treatment_plan_id` = if provided
    - `created_by` = current user id
11. Write audit log entry (action: create, resource: odontogram_snapshot, PHI: yes).
12. Return 201 with the created snapshot including full `snapshot_data`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| label | Optional; max 100 chars; strip HTML | La etiqueta no puede exceder 100 caracteres. |
| linked_record_id | Optional; valid UUID v4; must exist in clinical_records for this patient | El registro clinico especificado no existe para este paciente. |
| linked_treatment_plan_id | Optional; valid UUID v4; must exist in treatment_plans for this patient | El plan de tratamiento especificado no existe para este paciente. |

**Business Rules:**

- Snapshots are immutable once created. There is no update endpoint for snapshots.
- A patient can have an unlimited number of snapshots.
- The `label` field maps to the `reason` column in the `odontogram_snapshots` database table.
- If the patient has zero conditions at the time of snapshot, a valid snapshot is still created with `total_conditions = 0`. This is useful to document a clean initial examination.
- The `snapshot_data` JSONB must be self-contained: it does not reference live condition IDs, so it remains valid even if conditions are later modified or removed.
- `created_by` is set server-side from JWT.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Snapshot with no label | Created successfully; label=null in response |
| Patient has zero conditions | Snapshot created with all-null zones; total_conditions=0 |
| Both linked_record_id and linked_treatment_plan_id provided | Both stored; allowed |
| linked_record_id belongs to a different patient | Return 404 (ownership validation prevents cross-patient linking) |
| Multiple snapshots on same day | Allowed; no uniqueness constraint on label or date |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `odontogram_snapshots`: INSERT — new snapshot record with JSONB snapshot_data.

**Example query (SQLAlchemy):**
```python
snapshot = OdontogramSnapshot(
    patient_id=patient_id,
    snapshot_data=build_snapshot_jsonb(conditions, dentition_type),
    dentition_type=odontogram_state.dentition_type,
    reason=data.label,
    linked_record_id=data.linked_record_id,
    linked_treatment_plan_id=data.linked_treatment_plan_id,
    created_by=current_user.id,
)
session.add(snapshot)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- None (snapshot creation does not invalidate the live odontogram cache).

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| odontogram | odontogram.snapshot_created | { tenant_id, patient_id, snapshot_id, label, created_by } | After successful insert |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** create
- **Resource:** odontogram_snapshot
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 700ms

### Caching Strategy
- **Strategy:** No caching on create.
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 3-4 (patient check, conditions fetch, optional linked entity checks, snapshot insert — all in one transaction).

**Indexes required:**
- `odontogram_snapshots.(patient_id, created_at)` — INDEX (already defined: `idx_odontogram_snapshots_date`)
- `odontogram_conditions.patient_id` — INDEX (already defined: `idx_odontogram_conditions_patient`)

**N+1 prevention:** All conditions fetched in a single query before snapshot construction.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| label | Pydantic strip() + bleach.clean() | Free text stored in JSONB |
| linked_record_id | Pydantic UUID validator | Prevents injection via link IDs |
| linked_treatment_plan_id | Pydantic UUID validator | Prevents injection via link IDs |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `snapshot_data` JSONB contains complete clinical condition data for the patient.

**Audit requirement:** All snapshot creation logged (write access to clinical data).

---

## Testing

### Test Cases

#### Happy Path
1. Create snapshot with label and treatment plan link
   - **Given:** Authenticated doctor, patient with 5 conditions, valid treatment plan ID
   - **When:** POST /api/v1/patients/{patient_id}/odontogram/snapshots with label and linked_treatment_plan_id
   - **Then:** 201 Created, snapshot_data contains all 5 conditions, conditions_count=5

2. Create snapshot with no body (minimal)
   - **Given:** Authenticated doctor, patient with conditions
   - **When:** POST with empty body `{}`
   - **Then:** 201 Created, label=null, both linked IDs null

3. Create snapshot for patient with zero conditions
   - **Given:** Patient with no recorded conditions
   - **When:** POST snapshot
   - **Then:** 201 Created, all zones null in snapshot_data, conditions_count=0

4. Create multiple snapshots for same patient
   - **Given:** Two snapshots created on same day
   - **When:** POST snapshot twice
   - **Then:** Both 201 Created (no uniqueness constraint)

#### Edge Cases
1. Snapshot before and after condition change
   - **Given:** Snapshot S1 created, then condition added, then snapshot S2 created
   - **When:** GET S1 and S2 via OD-06
   - **Then:** S1 and S2 reflect different states; live odontogram matches S2

2. Snapshot linked to clinical record
   - **Given:** Valid clinical record ID for this patient
   - **When:** POST with linked_record_id set
   - **Then:** 201 Created, linked_record_id stored in snapshot

#### Error Cases
1. Assistant attempts snapshot creation
   - **Given:** Authenticated user with assistant role
   - **When:** POST snapshot
   - **Then:** 403 Forbidden

2. linked_treatment_plan_id does not exist
   - **Given:** Valid UUID but no matching treatment plan for this patient
   - **When:** POST with invalid linked_treatment_plan_id
   - **Then:** 404 Not Found

3. label exceeds 100 characters
   - **Given:** label string of 150 characters
   - **When:** POST snapshot
   - **Then:** 422 with label validation error

### Test Data Requirements

**Users:** doctor, clinic_owner (pass); assistant, receptionist, patient (fail with 403).

**Patients/Entities:** Patient with multiple conditions, patient with zero conditions. Pre-created clinical record and treatment plan for link validation tests.

### Mocking Strategy

- RabbitMQ: Mock publish; assert `odontogram.snapshot_created` payload.
- Time: Mock `datetime.now()` to produce deterministic `captured_at` values in snapshot JSONB.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Snapshot created with full denormalized JSONB including all tooth zones
- [ ] `conditions_count` accurately reflects non-null zones at time of capture
- [ ] Snapshots created at different times show independent states (immutability verified)
- [ ] `linked_record_id` and `linked_treatment_plan_id` validated against actual records before storing
- [ ] Assistant and receptionist roles return 403
- [ ] Audit log entry written on creation
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Retrieving snapshots (OD-06, OD-07)
- Comparing snapshots (OD-08)
- Deleting snapshots (snapshots are permanent clinical records)
- Automatically triggering snapshots on treatment plan creation (that is a treatment-plans domain concern)

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
- [x] Auth level stated (role + tenant context — doctor only)
- [x] Input sanitization defined (Pydantic + bleach for label)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical snapshot creation

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 300ms)
- [x] Caching strategy stated (N/A — write operation)
- [x] DB queries optimized (single conditions fetch + insert)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (odontogram.snapshot_created event)

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
