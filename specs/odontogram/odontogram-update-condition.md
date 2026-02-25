# OD-02: Update Odontogram Condition Spec

---

## Overview

**Feature:** Add or update a dental condition on a specific tooth zone within a patient's odontogram. This is the primary write operation for the odontogram — triggered by the doctor or assistant selecting a condition from the palette during examination. Supports max 2-tap UX flow (select tooth -> select condition). Creates an immutable history entry on every change.

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-01 (odontogram-get.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist does NOT have write access to the odontogram. Patient role is explicitly excluded.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/odontogram/conditions
```

**Rate Limiting:**
- 60 requests per minute per user
- Prevents accidental rapid-fire taps from flooding history.

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
  "tooth_number": "integer (required) — FDI notation. Adult: 11-18, 21-28, 31-38, 41-48. Pediatric: 51-55, 61-65, 71-75, 81-85",
  "zone": "string (required) — enum: mesial, distal, vestibular, lingual, palatino, oclusal, incisal, root, full",
  "condition_code": "string (required) — enum: caries, restoration, extraction, absent, crown, endodontic, implant, fracture, sealant, fluorosis, temporary, prosthesis",
  "severity": "string (optional) — enum: mild, moderate, severe. Default: moderate",
  "notes": "string (optional) — max 500 chars. Free text clinical note",
  "source": "string (required) — enum: manual, voice. Indicates how the condition was registered"
}
```

**Example Request:**
```json
{
  "tooth_number": 36,
  "zone": "oclusal",
  "condition_code": "caries",
  "severity": "moderate",
  "notes": "Caries detectada en control de rutina, paciente refiere sensibilidad al frio",
  "source": "manual"
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "condition_id": "uuid",
  "odontogram_id": "uuid",
  "patient_id": "uuid",
  "tooth_number": "integer",
  "zone": "string",
  "condition_code": "string",
  "condition_color": "string (hex)",
  "severity": "string | null",
  "notes": "string | null",
  "source": "string",
  "history_entry_id": "uuid",
  "action": "string (add | update)",
  "previous_condition": "string | null",
  "created_by": "uuid",
  "created_at": "string (ISO 8601)"
}
```

**Example:**
```json
{
  "condition_id": "c1d2e3f4-a5b6-7890-abcd-123456789abc",
  "odontogram_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "tooth_number": 36,
  "zone": "oclusal",
  "condition_code": "caries",
  "condition_color": "#D32F2F",
  "severity": "moderate",
  "notes": "Caries detectada en control de rutina, paciente refiere sensibilidad al frio",
  "source": "manual",
  "history_entry_id": "h1i2j3k4-l5m6-7890-abcd-123456789def",
  "action": "add",
  "previous_condition": null,
  "created_by": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
  "created_at": "2026-02-24T14:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or missing required fields.

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
**When:** User role is receptionist or patient (not authorized to write conditions).

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para registrar condiciones en el odontograma."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist in the tenant.

```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails — invalid FDI number, invalid zone, invalid condition code, or tooth/zone mismatch with dentition type.

```json
{
  "error": "validation_failed",
  "message": "Errores de validacion en los datos del odontograma.",
  "details": {
    "tooth_number": ["El numero de diente 99 no es valido en notacion FDI."],
    "zone": ["La zona 'oclusal' no aplica para el diente 11 (incisivo). Use: mesial, distal, vestibular, lingual, incisal."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure during condition insert or history creation.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema (field types, enums, string lengths).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role is in `[clinic_owner, doctor, assistant]`. Reject with 403 otherwise.
4. Validate `tooth_number` is in valid FDI range (adult: 11–18, 21–28, 31–38, 41–48; pediatric: 51–55, 61–65, 71–75, 81–85).
5. Fetch patient and their `odontogram_states` row to determine `dentition_type`. Return 404 if not found.
6. Cross-validate `tooth_number` against `dentition_type`: adult teeth not allowed on pediatric-only odontogram and vice versa (mixed dentition allows both sets).
7. Validate `zone` against the allowed zone set for the specific tooth type (e.g., anterior teeth use `incisal` not `oclusal`; root applies to all teeth).
8. Validate `condition_code` is in the active conditions catalog.
9. Check if an `odontogram_conditions` row already exists for this `(patient_id, tooth_number, zone)`:
   - If exists: this is an UPDATE. Store `previous_condition` from the existing row. Update `condition_code`, `severity`, `notes`, `updated_at`.
   - If not exists: this is an ADD. INSERT new row. `previous_condition = null`.
10. Insert into `odontogram_history`: `action` = `"add"` or `"update"`, `previous_data` = old JSONB snapshot, `new_data` = new JSONB snapshot, `performed_by` = current user id, `source` stored in new_data JSONB.
11. Delete Redis cache key `tenant:{tenant_id}:odontogram:{patient_id}` to force re-fetch.
12. Write audit log entry (action: update, resource: odontogram, PHI: yes).
13. Return 201 with the condition record and history entry ID.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| tooth_number | Integer, must be in valid FDI range for patient's dentition type | El numero de diente {n} no es valido en notacion FDI para el tipo de denticion del paciente. |
| zone | Must be one of: mesial, distal, vestibular, lingual, palatino, oclusal, incisal, root, full | La zona especificada no es valida. |
| condition_code | Must match one of 12 catalog codes | El codigo de condicion '{code}' no existe en el catalogo. |
| severity | Optional; if provided must be: mild, moderate, severe | El nivel de severidad no es valido. |
| notes | Optional; max 500 chars; strip HTML tags | Las notas no pueden exceder 500 caracteres. |
| source | Required; must be: manual, voice | La fuente de registro no es valida. |

**Business Rules:**

- A tooth/zone combination can only have ONE active condition at a time. A second write to the same tooth/zone replaces the previous condition (UPDATE, not duplicate INSERT).
- `created_by` is always set server-side from JWT; the client cannot supply it.
- The `source` field distinguishes between manual tap (doctor interaction) and voice-to-odontogram (OD-11/V-04 pipeline). Both use this endpoint but with different `source` values.
- The history entry is immutable — it is never updated or deleted. Audit trail integrity depends on this.
- Zone validation depends on tooth morphology: molars and premolars have `oclusal`; anterior teeth (11-13, 21-23, 31-33, 41-43) use `incisal` instead of `oclusal`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Same zone receives same condition_code again | Treated as UPDATE; history entry created with identical old/new data; notes/severity updated. |
| `odontogram_states` row missing (race condition after patient create) | Auto-create `odontogram_states` row for patient before inserting condition. |
| Mixed dentition patient: write to adult tooth | Allowed; mixed dentition permits both adult and pediatric FDI numbers. |
| Zone `full` submitted | Valid for whole-tooth conditions like `absent`, `implant`, `crown`. |
| `notes` submitted with HTML tags | Strip all HTML tags before persisting; reject if result is empty after stripping and was required. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `odontogram_conditions`: INSERT (new condition) or UPDATE (existing condition for same tooth/zone).
- `odontogram_history`: INSERT — one immutable history entry per call.
- `odontogram_states`: UPDATE — `updated_at` timestamp; INSERT if missing (auto-create).

**Example query (SQLAlchemy):**
```python
# Check for existing condition
existing = await session.execute(
    select(OdontogramCondition).where(
        OdontogramCondition.patient_id == patient_id,
        OdontogramCondition.tooth_number == data.tooth_number,
        OdontogramCondition.zone == data.zone,
    )
).scalar_one_or_none()

if existing:
    previous_data = {"condition_code": existing.condition_code, "severity": existing.severity, "notes": existing.notes}
    existing.condition_code = data.condition_code
    existing.severity = data.severity
    existing.notes = data.notes
    existing.updated_at = func.now()
    action = "update"
else:
    condition = OdontogramCondition(
        odontogram_id=odontogram.id,
        patient_id=patient_id,
        tooth_number=data.tooth_number,
        zone=data.zone,
        condition_code=data.condition_code,
        severity=data.severity,
        notes=data.notes,
        created_by=current_user.id,
    )
    session.add(condition)
    previous_data = None
    action = "add"

history = OdontogramHistory(
    patient_id=patient_id,
    tooth_number=data.tooth_number,
    zone=data.zone,
    action=action,
    condition_code=data.condition_code,
    previous_data=previous_data,
    new_data={"condition_code": data.condition_code, "severity": data.severity, "notes": data.notes, "source": data.source},
    performed_by=current_user.id,
)
session.add(history)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram:{patient_id}`: DELETE — invalidated on every successful write.

**Cache TTL:** N/A (invalidation only on write).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| odontogram | odontogram.condition_updated | { tenant_id, patient_id, tooth_number, zone, condition_code, action, performed_by } | After successful commit |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** update
- **Resource:** odontogram
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on write; invalidates read cache.
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Deletes `tenant:{tenant_id}:odontogram:{patient_id}` on success.

### Database Performance

**Queries executed:** 4 (patient check, odontogram_states fetch/create, upsert condition, insert history — in one transaction).

**Indexes required:**
- `odontogram_conditions.(patient_id, tooth_number, zone)` — INDEX for upsert lookup (consider UNIQUE constraint to enforce one condition per tooth/zone).
- `odontogram_history.(patient_id, created_at)` — INDEX (already defined: `idx_odontogram_history_date`).

**N+1 prevention:** Not applicable (single record write).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| tooth_number | Pydantic int validator + FDI range check | No string injection possible |
| zone | Pydantic enum validator | Whitelist validation |
| condition_code | Pydantic enum validator | Whitelist validation |
| notes | Pydantic strip() + bleach.clean() | Free text; strip all HTML |
| source | Pydantic enum validator | Whitelist validation |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization. `notes` field sanitized with bleach before storage.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `tooth_number`, `zone`, `condition_code`, `notes` (all are clinical health data).

**Audit requirement:** All write access logged with performer identity.

---

## Testing

### Test Cases

#### Happy Path
1. Add new condition to empty zone
   - **Given:** Authenticated doctor, patient with adult dentition, tooth 36 zone oclusal has no condition
   - **When:** POST with tooth_number=36, zone=oclusal, condition_code=caries, source=manual
   - **Then:** 201 Created, action=add, history_entry created, cache invalidated

2. Update existing condition on same zone
   - **Given:** Tooth 36 oclusal already has condition_code=caries
   - **When:** POST with tooth_number=36, zone=oclusal, condition_code=restoration, source=manual
   - **Then:** 201 Created, action=update, previous_condition=caries, history_entry created

3. Assistant registers condition
   - **Given:** Authenticated user with assistant role
   - **When:** POST valid condition
   - **Then:** 201 Created (assistants are authorized)

4. Voice-sourced condition
   - **Given:** Authenticated doctor, source=voice
   - **When:** POST condition
   - **Then:** 201 Created, source=voice stored in history new_data JSONB

#### Edge Cases
1. Write to tooth 11 with zone=oclusal (invalid for anterior)
   - **Given:** Patient has adult dentition, tooth 11 is an incisor
   - **When:** POST with zone=oclusal for tooth 11
   - **Then:** 422 with zone validation error specifying valid zones for anterior teeth

2. Auto-create missing odontogram_states
   - **Given:** Patient exists but odontogram_states row was deleted externally
   - **When:** POST valid condition
   - **Then:** 201 Created, odontogram_states auto-created, condition inserted

3. Condition with full zone (absent tooth)
   - **Given:** Doctor marks tooth as absent
   - **When:** POST with zone=full, condition_code=absent
   - **Then:** 201 Created with zone=full persisted

#### Error Cases
1. Invalid FDI tooth number
   - **Given:** tooth_number = 99
   - **When:** POST condition
   - **Then:** 422 with tooth_number validation error

2. Receptionist attempts write
   - **Given:** Authenticated user with receptionist role
   - **When:** POST condition
   - **Then:** 403 Forbidden

3. Invalid condition_code
   - **Given:** condition_code = "cavity" (not in catalog)
   - **When:** POST condition
   - **Then:** 422 with condition_code validation error

4. Patient not found
   - **Given:** Non-existent patient_id in URL
   - **When:** POST condition
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** doctor, assistant (should pass); receptionist, patient (should fail with 403).

**Patients/Entities:** Adult patient with some conditions, pediatric patient, patient with missing odontogram_states.

### Mocking Strategy

- Redis: Use fakeredis to verify cache key deletion after write.
- RabbitMQ: Mock publish call; assert `odontogram.condition_updated` payload.
- Conditions catalog: In-memory fixture with all 12 condition codes.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] New condition insertion returns 201 with action=add
- [ ] Overwriting existing condition returns 201 with action=update and previous_condition set
- [ ] History entry created for every call (immutable audit trail)
- [ ] Redis cache key invalidated after every successful write
- [ ] Invalid FDI number returns 422 with clear Spanish error
- [ ] Invalid zone for tooth morphology returns 422
- [ ] Receptionist and patient roles return 403
- [ ] `source` field stored in history new_data JSONB
- [ ] Audit log entry written
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Bulk updates (see OD-11 odontogram-bulk-update.md)
- Removing conditions (see OD-03 odontogram-remove-condition.md)
- Voice parsing logic (V-01 through V-05 specs)
- Treatment plan linkage (separate domain)

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
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 200ms)
- [x] Caching strategy stated (write invalidates Redis)
- [x] DB queries optimized (indexes listed, single transaction)
- [x] Pagination applied where needed (N/A — single record write)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (odontogram.condition_updated event)

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
