# P-10 Patient Merge (Deduplicate) Spec

---

## Overview

**Feature:** Merge two duplicate patient records into one. All clinical records, odontogram data, appointments, invoices, payments, prescriptions, consents, and documents are moved from the secondary patient to the primary patient. The secondary patient is deactivated. This operation is irreversible and requires explicit confirmation.

**Domain:** patients

**Priority:** High

**Dependencies:** P-01 (patient-create.md), odontogram, clinical-records, appointments, billing, prescriptions, consents, patient-documents

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner can merge patients due to the destructive and irreversible nature of the operation. A confirmation flag (`confirm=true`) is required in the request body.

---

## Endpoint

```
POST /api/v1/patients/merge
```

**Rate Limiting:**
- 10 requests per hour per tenant

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
  "primary_patient_id": "UUID (required) — the patient record that survives",
  "secondary_patient_id": "UUID (required) — the patient record that will be deactivated",
  "confirm": "boolean (required) — must be true to execute"
}
```

**Example Request:**
```json
{
  "primary_patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "secondary_patient_id": "660f9511-f3a0-52e5-b827-557766551111",
  "confirm": true
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "message": "string",
  "primary_patient_id": "UUID",
  "secondary_patient_id": "UUID",
  "merge_summary": {
    "appointments_moved": "integer",
    "clinical_records_moved": "integer",
    "diagnoses_moved": "integer",
    "procedures_moved": "integer",
    "odontogram_conditions_merged": "integer",
    "prescriptions_moved": "integer",
    "consents_moved": "integer",
    "documents_moved": "integer",
    "invoices_moved": "integer",
    "payments_moved": "integer",
    "message_threads_moved": "integer"
  }
}
```

**Example:**
```json
{
  "message": "Pacientes fusionados exitosamente. El registro secundario ha sido desactivado.",
  "primary_patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "secondary_patient_id": "660f9511-f3a0-52e5-b827-557766551111",
  "merge_summary": {
    "appointments_moved": 5,
    "clinical_records_moved": 3,
    "diagnoses_moved": 2,
    "procedures_moved": 4,
    "odontogram_conditions_merged": 8,
    "prescriptions_moved": 1,
    "consents_moved": 2,
    "documents_moved": 6,
    "invoices_moved": 3,
    "payments_moved": 2,
    "message_threads_moved": 1
  }
}
```

### Preview Response (confirm=false)

**Status:** 200 OK

When `confirm=false`, the endpoint returns a preview of what would be merged without executing the merge:

```json
{
  "message": "Vista previa de fusion. Envie confirm=true para ejecutar.",
  "primary_patient": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Juan Perez",
    "document": "CC 1234567890",
    "created_at": "2024-06-15T10:00:00-05:00"
  },
  "secondary_patient": {
    "id": "660f9511-f3a0-52e5-b827-557766551111",
    "name": "Juan A. Perez",
    "document": "CC 1234567891",
    "created_at": "2025-01-20T14:30:00-05:00"
  },
  "merge_preview": {
    "appointments_to_move": 5,
    "clinical_records_to_move": 3,
    "diagnoses_to_move": 2,
    "procedures_to_move": 4,
    "odontogram_conditions_to_merge": 8,
    "prescriptions_to_move": 1,
    "consents_to_move": 2,
    "documents_to_move": 6,
    "invoices_to_move": 3,
    "payments_to_move": 2,
    "message_threads_to_move": 1
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** `confirm` not provided, or primary_patient_id equals secondary_patient_id.

```json
{
  "error": "invalid_input",
  "message": "El paciente primario y el secundario no pueden ser el mismo.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not clinic_owner.

```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede fusionar registros de pacientes."
}
```

#### 404 Not Found
**When:** Either patient_id does not exist in the current tenant.

```json
{
  "error": "not_found",
  "message": "Paciente secundario no encontrado.",
  "details": { "patient_id": "660f9511-f3a0-52e5-b827-557766551111" }
}
```

#### 409 Conflict
**When:** Secondary patient is already inactive (previously merged or deactivated).

```json
{
  "error": "conflict",
  "message": "El paciente secundario ya esta inactivo y no puede ser fusionado."
}
```

#### 422 Unprocessable Entity
**When:** confirm field is missing or not a boolean.

```json
{
  "error": "validation_failed",
  "message": "El campo 'confirm' es requerido y debe ser true o false.",
  "details": { "confirm": ["Este campo es requerido."] }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract tenant context; verify role = clinic_owner.
2. Validate request body via Pydantic: both UUIDs present, confirm is boolean.
3. Reject if primary_patient_id == secondary_patient_id.
4. Set search_path to tenant schema.
5. Load both patients from DB; return 404 if either not found.
6. Verify secondary patient is_active=true; return 409 if inactive.
7. If `confirm=false`: execute count queries and return preview (no mutations).
8. If `confirm=true`: execute merge within a single database transaction:
   a. UPDATE `appointments` SET patient_id = primary WHERE patient_id = secondary.
   b. UPDATE `clinical_records` SET patient_id = primary WHERE patient_id = secondary.
   c. UPDATE `diagnoses` SET patient_id = primary WHERE patient_id = secondary.
   d. UPDATE `procedures` SET patient_id = primary WHERE patient_id = secondary.
   e. Merge odontogram: if primary has no odontogram_state, move secondary's. If both have one, move secondary's conditions to primary's odontogram and delete secondary's odontogram_state.
   f. UPDATE `odontogram_history` SET patient_id = primary WHERE patient_id = secondary.
   g. UPDATE `prescriptions` SET patient_id = primary WHERE patient_id = secondary.
   h. UPDATE `consents` SET patient_id = primary WHERE patient_id = secondary.
   i. UPDATE `patient_documents` SET patient_id = primary WHERE patient_id = secondary.
   j. UPDATE `invoices` SET patient_id = primary WHERE patient_id = secondary.
   k. UPDATE `payments` SET patient_id = primary WHERE patient_id = secondary.
   l. UPDATE `message_threads` SET patient_id = primary WHERE patient_id = secondary.
   m. UPDATE `anamnesis`: merge secondary into primary (keep primary, append secondary notes).
   n. Copy any non-null fields from secondary to primary where primary has null (phone_secondary, insurance, emergency contact).
   o. UPDATE secondary patient: set is_active=false, add merge note to `notes` field.
   p. UPDATE primary patient: set updated_at=now().
9. Commit transaction (atomic — all or nothing).
10. Invalidate caches for both patient IDs.
11. Write extensive audit log entries (before and after states for both patients + all moved records).
12. Return merge summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| primary_patient_id | Valid UUIDv4 | "El ID del paciente primario no es un UUID valido." |
| secondary_patient_id | Valid UUIDv4 | "El ID del paciente secundario no es un UUID valido." |
| confirm | Boolean, required | "El campo 'confirm' es requerido." |
| primary != secondary | IDs must differ | "El paciente primario y el secundario no pueden ser el mismo." |

**Business Rules:**

- Merge is irreversible. The secondary patient cannot be restored.
- The secondary patient is soft-deleted (is_active=false) with a note indicating the merge.
- The primary patient's existing data always takes precedence over the secondary's.
- Only null fields on the primary are filled from the secondary (e.g., if primary has no phone_secondary but secondary does, it is copied).
- Odontogram merge: if conflicting conditions exist on the same tooth+zone, primary's conditions are kept and secondary's are logged in odontogram_history.
- The entire merge runs in a single transaction for atomicity.
- Merge note appended to secondary: "Fusionado con paciente {primary_id} el {date} por {user_name}."

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Secondary has no related records | Merge succeeds; all counts are 0; secondary deactivated. |
| Both patients have odontogram with same tooth conditions | Primary conditions kept; secondary conditions logged in history as 'merge_superseded'. |
| Secondary has portal_access=true | Portal access is revoked on secondary; tokens invalidated. |
| Primary patient is inactive | Return 404 (inactive patients are not found). |
| Concurrent merge attempt on same pair | Database transaction lock prevents double-merge; second request gets 409. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: UPDATE patient_id
- `clinical_records`: UPDATE patient_id
- `diagnoses`: UPDATE patient_id
- `procedures`: UPDATE patient_id
- `odontogram_states`: UPDATE or DELETE (secondary)
- `odontogram_conditions`: UPDATE odontogram_id and patient_id
- `odontogram_history`: UPDATE patient_id
- `prescriptions`: UPDATE patient_id
- `consents`: UPDATE patient_id
- `patient_documents`: UPDATE patient_id
- `invoices`: UPDATE patient_id
- `payments`: UPDATE patient_id
- `message_threads`: UPDATE patient_id
- `anamnesis`: UPDATE (merge content)
- `patients` (secondary): UPDATE is_active=false, notes appended
- `patients` (primary): UPDATE updated_at, possibly null fields filled
- `audit_log`: INSERT (extensive merge audit entries)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{primary_patient_id}:*`: INVALIDATE
- `tenant:{tenant_id}:patient:{secondary_patient_id}:*`: INVALIDATE
- `tenant:{tenant_id}:patients:list:*`: INVALIDATE
- `tenant:{tenant_id}:patients:count`: DELETE

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | patient_merged | { tenant_id, primary_id, secondary_id, merged_by } | After successful merge |

### Audit Log

**Audit entry:** Yes (multiple entries)

- **Action:** update (merge)
- **Resource:** patient_merge
- **PHI involved:** Yes
- **Details logged:** Both patient snapshots before merge, all record counts moved, user who performed merge, IP address.

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | patient_merged | clinic_owner | After successful merge |

---

## Performance

### Expected Response Time
- **Target (preview):** < 300ms
- **Target (confirmed merge):** < 2000ms
- **Maximum acceptable:** < 5000ms

### Caching Strategy
- **Strategy:** Cache invalidation on merge.
- **Cache key:** Both patient keys + list cache.
- **TTL:** N/A
- **Invalidation:** Immediate on merge completion.

### Database Performance

**Queries executed:** 15-20 UPDATE statements within a single transaction.

**Indexes required:**
- All `patient_id` foreign key indexes on affected tables (already exist per database-architecture.md).
- `patients.id` — PRIMARY KEY

**N+1 prevention:** Batch UPDATE per table. No individual row updates.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| primary_patient_id | Pydantic UUID validator | Rejects non-UUID |
| secondary_patient_id | Pydantic UUID validator | Rejects non-UUID |
| confirm | Pydantic bool validator | Must be boolean |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. All UPDATE statements use ORM `.where()` clauses.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** All patient PII and clinical data is involved in the merge operation.

**Audit requirement:** All access and mutations logged extensively. Before-and-after snapshots stored in audit log.

---

## Testing

### Test Cases

#### Happy Path
1. Successful merge with all record types
   - **Given:** Primary patient with 2 appointments, secondary with 3 appointments + 2 invoices + odontogram.
   - **When:** POST merge with confirm=true.
   - **Then:** Returns 200, all records moved, secondary deactivated, audit log written.

2. Preview mode
   - **Given:** Two patients with related records.
   - **When:** POST merge with confirm=false.
   - **Then:** Returns 200 with preview counts, no data modified.

3. Merge fills null fields on primary
   - **Given:** Primary has null phone_secondary; secondary has a value.
   - **When:** POST merge with confirm=true.
   - **Then:** Primary's phone_secondary is now filled from secondary.

#### Edge Cases
1. Secondary patient with no related records
   - **Given:** Secondary with zero appointments, zero records.
   - **When:** POST merge with confirm=true.
   - **Then:** Merge succeeds, all counts 0, secondary deactivated.

2. Both patients have odontogram on same tooth
   - **Given:** Both have conditions on tooth 36.
   - **When:** POST merge.
   - **Then:** Primary's conditions kept, secondary's logged in history.

#### Error Cases
1. Same patient IDs
   - **Given:** primary_patient_id == secondary_patient_id.
   - **When:** POST merge.
   - **Then:** Returns 400.

2. Non-clinic_owner role
   - **Given:** Doctor user.
   - **When:** POST merge.
   - **Then:** Returns 403.

3. Secondary already inactive
   - **Given:** Secondary patient is_active=false.
   - **When:** POST merge.
   - **Then:** Returns 409.

4. Non-existent patient
   - **Given:** Random UUID for secondary.
   - **When:** POST merge.
   - **Then:** Returns 404.

### Test Data Requirements

**Users:** 1 clinic_owner, 1 doctor (for 403 test).

**Patients/Entities:** 2 active patients with overlapping and non-overlapping related records across all tables. 1 inactive patient for 409 test.

### Mocking Strategy

- Database: Full integration test with test tenant schema.
- Cache: Verify invalidation calls.
- No external services to mock.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Merge moves all related records from secondary to primary (all 12+ tables)
- [ ] Secondary patient is deactivated with merge note
- [ ] Primary patient's null fields filled from secondary
- [ ] Odontogram merge handles conflicts correctly
- [ ] Preview mode (confirm=false) returns accurate counts without mutations
- [ ] Entire merge is atomic (single transaction, rolls back on any failure)
- [ ] Extensive audit log created with before/after snapshots
- [ ] Only clinic_owner can perform merges
- [ ] Proper error handling for all edge cases
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Automatic duplicate detection / suggestion (future feature for patient matching algorithms).
- Undo/rollback of a completed merge (by design, merges are irreversible).
- Merging more than 2 patients at once (chain merges can be done sequentially).
- Cross-tenant patient merging (not applicable in schema-per-tenant model).

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
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized (batch UPDATEs, indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (notification job)

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
