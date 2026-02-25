# OD-11: Bulk Update Odontogram Spec

---

## Overview

**Feature:** Apply multiple tooth/zone condition updates in a single transactional request. Used for two primary scenarios: (1) initial examination entry where a doctor rapidly registers all findings at once, and (2) the voice-to-odontogram pipeline (V-04) which parses an audio transcription into structured dental findings and submits them as a bulk update. All items in the batch succeed or all fail together (atomic transaction). A single cache invalidation is performed at the end regardless of batch size.

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-02 (odontogram-update-condition.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist and patient roles excluded. Same write restriction as OD-02. Assistants may use bulk update for initial examination data entry.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/odontogram/bulk
```

**Rate Limiting:**
- 10 requests per minute per user
- Bulk operations are heavyweight; 10/min is sufficient for any clinical workflow.

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
  "updates": [
    {
      "tooth_number": "integer (required) — FDI notation",
      "zone": "string (required) — enum: mesial, distal, vestibular, lingual, palatino, oclusal, incisal, root, full",
      "condition_code": "string (required) — must be in conditions catalog",
      "severity": "string (optional) — enum: mild, moderate, severe",
      "notes": "string (optional) — max 500 chars",
      "source": "string (required) — enum: manual, voice"
    }
  ],
  "session_notes": "string (optional) — max 1000 chars. Clinical note for the entire bulk update session"
}
```

**Constraints:**
- `updates` array: min 1 item, max 160 items (32 teeth × 5 active zones; root excluded from typical examination)
- Duplicate `(tooth_number, zone)` pairs within the same batch are rejected (last-write-wins ambiguity avoided)

**Example Request:**
```json
{
  "updates": [
    {
      "tooth_number": 11,
      "zone": "distal",
      "condition_code": "caries",
      "severity": "mild",
      "notes": "Caries incipiente en proximal",
      "source": "voice"
    },
    {
      "tooth_number": 36,
      "zone": "oclusal",
      "condition_code": "caries",
      "severity": "moderate",
      "source": "voice"
    },
    {
      "tooth_number": 46,
      "zone": "full",
      "condition_code": "absent",
      "source": "voice"
    },
    {
      "tooth_number": 26,
      "zone": "mesial",
      "condition_code": "restoration",
      "source": "manual"
    }
  ],
  "session_notes": "Examen inicial completo. Paciente con higiene regular, multiples caries activas en sector posterior."
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "patient_id": "uuid",
  "processed": "integer (total items processed)",
  "added": "integer (new conditions added)",
  "updated": "integer (existing conditions updated)",
  "history_entries_created": "integer",
  "session_notes": "string | null",
  "results": [
    {
      "tooth_number": "integer",
      "zone": "string",
      "condition_code": "string",
      "action": "string (add | update)",
      "previous_condition": "string | null",
      "condition_id": "uuid"
    }
  ],
  "performed_by": "uuid",
  "created_at": "string (ISO 8601)"
}
```

**Example:**
```json
{
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "processed": 4,
  "added": 3,
  "updated": 1,
  "history_entries_created": 4,
  "session_notes": "Examen inicial completo. Paciente con higiene regular, multiples caries activas en sector posterior.",
  "results": [
    {
      "tooth_number": 11,
      "zone": "distal",
      "condition_code": "caries",
      "action": "add",
      "previous_condition": null,
      "condition_id": "c1d2e3f4-a5b6-7890-abcd-123456789abc"
    },
    {
      "tooth_number": 36,
      "zone": "oclusal",
      "condition_code": "caries",
      "action": "update",
      "previous_condition": "restoration",
      "condition_id": "d2e3f4a5-b6c7-7890-abcd-234567890bcd"
    },
    {
      "tooth_number": 46,
      "zone": "full",
      "condition_code": "absent",
      "action": "add",
      "previous_condition": null,
      "condition_id": "e3f4a5b6-c7d8-7890-abcd-345678901cde"
    },
    {
      "tooth_number": 26,
      "zone": "mesial",
      "condition_code": "restoration",
      "action": "add",
      "previous_condition": null,
      "condition_id": "f4a5b6c7-d8e9-7890-abcd-456789012def"
    }
  ],
  "performed_by": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
  "created_at": "2026-02-24T14:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or missing required `updates` array.

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
**When:** User role is receptionist or patient.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para realizar actualizaciones masivas del odontograma."
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
**When:** Validation failures in the updates array (invalid FDI number, invalid zone, invalid condition_code, duplicate tooth/zone pairs, array size exceeded).

```json
{
  "error": "validation_failed",
  "message": "Errores de validacion en las actualizaciones masivas.",
  "details": {
    "updates[2].tooth_number": ["El numero de diente 99 no es valido en notacion FDI."],
    "updates[0,3]": ["Las posiciones 0 y 3 tienen el mismo diente y zona (36, oclusal). Las actualizaciones duplicadas no estan permitidas."],
    "updates": ["El maximo de actualizaciones por solicitud es 160. Se recibieron 165."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Transaction failure during bulk insert/update. Since the operation is atomic, no partial writes occur.

---

## Business Logic

**Step-by-step process:**

1. Validate request body against Pydantic schema:
   - `updates` array: min 1, max 160 items.
   - Each item: tooth_number, zone, condition_code validated against enums.
   - Check for duplicate `(tooth_number, zone)` pairs within the batch. Reject if any found.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role is in `[clinic_owner, doctor, assistant]`. Reject with 403 otherwise.
4. Validate ALL items against FDI tooth ranges and zone applicability rules BEFORE opening the transaction (fail fast, no partial work).
5. Verify patient exists and fetch `odontogram_states` row. Return 404 if not.
6. Auto-create `odontogram_states` row if missing (same logic as OD-02).
7. Open a single database transaction:
   a. Batch-fetch all existing `odontogram_conditions` for the patient matching ANY `(tooth_number, zone)` in the batch using IN clause:
      ```sql
      SELECT * FROM odontogram_conditions
      WHERE patient_id = :patient_id
      AND (tooth_number, zone) IN (:pairs)
      ```
   b. Build a lookup dict: `existing = {(tooth_number, zone): condition_row}`.
   c. For each item in `updates`:
      - If `(tooth_number, zone)` in existing: this is an UPDATE. Capture old values. Update condition row.
      - If not in existing: this is an ADD. Create new condition row.
   d. Bulk INSERT new conditions using `session.add_all()`.
   e. Batch-create all history entries using `session.add_all()`:
      - One history row per update item.
      - `performed_by` = current user id for all entries.
      - `source` stored in `new_data` JSONB.
   f. Commit transaction.
8. AFTER successful commit: DELETE Redis cache key `tenant:{tenant_id}:odontogram:{patient_id}` (single invalidation for entire batch).
9. Dispatch `odontogram.bulk_updated` event to RabbitMQ.
10. Write audit log entry (action: bulk_update, resource: odontogram, PHI: yes, item_count: N).
11. Return 200 with full results array.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| updates | Array, 1–160 items | El arreglo de actualizaciones debe tener entre 1 y 160 elementos. |
| updates[n].tooth_number | Integer in valid FDI range for patient's dentition | El numero de diente {n} no es valido en notacion FDI. |
| updates[n].zone | Valid zone enum | La zona '{zone}' no es valida. |
| updates[n].condition_code | Must be in conditions catalog | El codigo de condicion '{code}' no existe en el catalogo. |
| updates[n].source | Required; enum: manual, voice | La fuente de registro es obligatoria. |
| updates[n].notes | Optional; max 500 chars | Las notas no pueden exceder 500 caracteres. |
| updates (batch) | No duplicate (tooth_number, zone) pairs | Las posiciones {i} y {j} tienen el mismo diente y zona. |
| session_notes | Optional; max 1000 chars | Las notas de sesion no pueden exceder 1000 caracteres. |

**Business Rules:**

- The operation is atomic: if ANY validation fails, NO writes occur. All-or-nothing.
- Duplicate `(tooth_number, zone)` pairs in the batch are rejected at the Pydantic validation layer before hitting the DB. This prevents ambiguity about which update to apply last.
- The response `results` array preserves the same order as the input `updates` array.
- `history_entries_created` always equals `processed` (one history entry per update item, regardless of add or update action).
- `session_notes` is stored in the audit log and dispatched in the queue event payload. It is NOT stored per-condition in the DB — it is session-level metadata only.
- This endpoint is the designated target for the voice-to-odontogram pipeline (V-04): all voice-parsed conditions are submitted here with `source = "voice"`.
- Maximum of 160 items is derived from: 32 teeth × 5 practical zones (mesial, distal, vestibular, lingual, oclusal) — root and full are less common in bulk entry. The absolute limit (32 × 6 = 192) is intentionally set lower to add a safety margin.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Batch of 1 item | Valid; behaves like OD-02 but with bulk endpoint semantics |
| All 160 items are updates (no new conditions) | Transaction updates all 160 existing rows; history entries created for all |
| Mix of add and update in same batch | Both handled in single transaction; counted separately in response |
| Voice pipeline submits duplicate tooth/zone | Rejected with 422 (parser bug should be fixed at V-04 level) |
| DB constraint violation inside transaction | Transaction rolls back; 500 returned (all-or-nothing guaranteed) |
| Patient has no odontogram_states yet | Auto-created before first bulk insert |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `odontogram_conditions`: Multiple INSERTs and UPDATEs (up to 160) in a single transaction.
- `odontogram_history`: Multiple INSERTs (one per update item, up to 160) in the same transaction.
- `odontogram_states`: Possibly INSERT if missing; UPDATE `updated_at`.

**Example query (SQLAlchemy):**
```python
# Batch-fetch existing conditions
existing_rows = await session.execute(
    select(OdontogramCondition).where(
        OdontogramCondition.patient_id == patient_id,
        tuple_(OdontogramCondition.tooth_number, OdontogramCondition.zone).in_(
            [(item.tooth_number, item.zone) for item in data.updates]
        )
    )
).scalars().all()

existing_map = {(row.tooth_number, row.zone): row for row in existing_rows}

new_conditions = []
update_conditions = []
history_entries = []

for item in data.updates:
    key = (item.tooth_number, item.zone)
    if key in existing_map:
        existing = existing_map[key]
        previous_data = {"condition_code": existing.condition_code, "severity": existing.severity, "notes": existing.notes}
        existing.condition_code = item.condition_code
        existing.severity = item.severity
        existing.notes = item.notes
        existing.updated_at = func.now()
        action = "update"
    else:
        condition = OdontogramCondition(
            odontogram_id=odontogram.id,
            patient_id=patient_id,
            tooth_number=item.tooth_number,
            zone=item.zone,
            condition_code=item.condition_code,
            severity=item.severity,
            notes=item.notes,
            created_by=current_user.id,
        )
        session.add(condition)
        previous_data = None
        action = "add"

    history_entries.append(OdontogramHistory(
        patient_id=patient_id,
        tooth_number=item.tooth_number,
        zone=item.zone,
        action=action,
        condition_code=item.condition_code,
        previous_data=previous_data,
        new_data={"condition_code": item.condition_code, "severity": item.severity, "notes": item.notes, "source": item.source},
        performed_by=current_user.id,
    ))

session.add_all(history_entries)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram:{patient_id}`: DELETE — single invalidation after full transaction commit.
- Individual tooth cache keys `tenant:{tenant_id}:odontogram_tooth:{patient_id}:{tooth_number}`: DELETE for each unique tooth_number in the batch.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| odontogram | odontogram.bulk_updated | { tenant_id, patient_id, item_count, performed_by, session_notes, source_breakdown: { manual: N, voice: N } } | After successful commit |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** bulk_update
- **Resource:** odontogram
- **PHI involved:** Yes
- **Additional fields:** `item_count` (number of items processed), `source` breakdown (manual vs voice)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 500ms (for up to 160 items)
- **Maximum acceptable:** < 1500ms

### Caching Strategy
- **Strategy:** No caching on write; single cache invalidation at end.
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** `tenant:{tenant_id}:odontogram:{patient_id}` + per-tooth keys deleted after commit.

### Database Performance

**Queries executed:** 3 (patient check, batch existing conditions fetch, bulk insert/update + history insert in one transaction).

**Indexes required:**
- `odontogram_conditions.(patient_id, tooth_number, zone)` — Composite INDEX for batch lookup efficiency.
- `odontogram_history.patient_id` — INDEX (already defined).

**N+1 prevention:** Single batch IN query for existing conditions lookup. `session.add_all()` for bulk history insertion. No per-item DB round trips.

### Pagination

**Pagination:** No — all items processed in one transaction. Max 160 items per request enforced at validation layer.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| updates[n].tooth_number | Pydantic int validator + FDI range check | |
| updates[n].zone | Pydantic enum validator | Whitelist |
| updates[n].condition_code | Pydantic enum validator | Whitelist |
| updates[n].notes | Pydantic strip() + bleach.clean() | Free text per item |
| session_notes | Pydantic strip() + bleach.clean() | Session-level free text |
| updates[n].source | Pydantic enum validator | Whitelist |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. The batch IN clause uses SQLAlchemy `tuple_().in_()` which is parameterized. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** All condition data (tooth_number, zone, condition_code, notes) is clinical PHI. `session_notes` may contain clinical context.

**Audit requirement:** All bulk write access logged with item count and performer identity.

---

## Testing

### Test Cases

#### Happy Path
1. Bulk update with mix of adds and updates
   - **Given:** Authenticated doctor, batch of 4 items, 2 teeth with existing conditions, 2 teeth empty
   - **When:** POST /api/v1/patients/{patient_id}/odontogram/bulk with 4 updates
   - **Then:** 200 OK, processed=4, added=2, updated=2, 4 history entries, single cache invalidation

2. Voice-pipeline bulk update
   - **Given:** All items have source=voice, called by V-04
   - **When:** POST bulk with 8 voice-parsed conditions
   - **Then:** 200 OK, all source=voice stored in history new_data

3. Single-item bulk update
   - **Given:** updates array with 1 item
   - **When:** POST bulk
   - **Then:** 200 OK, processed=1, behaves correctly

4. Full 160-item batch
   - **Given:** 160 unique tooth/zone pairs
   - **When:** POST bulk
   - **Then:** 200 OK, all 160 processed, response within 1500ms

#### Edge Cases
1. All items are new conditions (no existing)
   - **Given:** Patient with no existing conditions
   - **When:** POST bulk with 10 items
   - **Then:** 200 OK, added=10, updated=0

2. All items overwrite existing conditions
   - **Given:** Patient with 10 existing conditions, all overwritten
   - **When:** POST bulk with same 10 tooth/zone pairs, different conditions
   - **Then:** 200 OK, added=0, updated=10

3. session_notes stored in audit but not in conditions
   - **Given:** POST with session_notes
   - **When:** Check DB and audit log
   - **Then:** session_notes NOT in odontogram_conditions or odontogram_history; present in audit log and queue event

#### Error Cases
1. Duplicate tooth/zone pair in batch
   - **Given:** updates[0] and updates[2] both have tooth_number=36, zone=oclusal
   - **When:** POST bulk
   - **Then:** 422 with duplicate pair error listing positions 0 and 2

2. Batch exceeds 160 items
   - **Given:** updates array with 161 items
   - **When:** POST bulk
   - **Then:** 422 with size validation error

3. One item has invalid condition_code
   - **Given:** updates[3].condition_code = "cavity" (not in catalog)
   - **When:** POST bulk
   - **Then:** 422 with position-specific error; NO writes to DB (all-or-nothing)

4. Receptionist attempts bulk update
   - **Given:** Authenticated receptionist
   - **When:** POST bulk
   - **Then:** 403 Forbidden

5. Transaction failure (simulated DB error)
   - **Given:** DB error during commit
   - **When:** POST bulk
   - **Then:** 500 Internal Server Error, zero conditions written (transaction rolled back)

### Test Data Requirements

**Users:** doctor, assistant (pass); receptionist, patient (fail with 403).

**Patients/Entities:** Patient with 10 known existing conditions; patient with zero conditions.

### Mocking Strategy

- Redis: Use fakeredis; verify single DELETE call for odontogram cache key.
- RabbitMQ: Mock publish; assert `odontogram.bulk_updated` payload with correct item_count.
- DB transaction rollback: Patch `session.commit()` to raise exception; verify no rows written.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] All items processed atomically (all succeed or all fail, no partial writes)
- [ ] Duplicate tooth/zone pairs in batch rejected with 422 before any DB writes
- [ ] Maximum 160 items enforced at validation layer
- [ ] Single batch-fetch query for existing conditions (no N+1)
- [ ] Single Redis cache invalidation after full commit
- [ ] `history_entries_created` = `processed` (one history per item)
- [ ] `source` field from each item stored in history new_data JSONB
- [ ] Voice-sourced bulk update (source=voice) stored correctly
- [ ] Receptionist and patient roles return 403
- [ ] Audit log entry written with item_count
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms for typical batch)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Bulk removal of conditions (submit individual DELETEs via OD-03)
- Voice transcription and parsing (V-01 through V-04 specs)
- Partial success mode (all-or-nothing is intentional; no partial batch processing)
- CSV import for bulk patient odontogram initialization (separate import feature)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas with batch constraints)
- [x] All outputs defined (response models with per-item results)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (including duplicate detection)
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
- [x] Input sanitization defined (Pydantic + bleach for notes)
- [x] SQL injection prevented (SQLAlchemy ORM, parameterized IN clause)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for bulk clinical write operations

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 500ms for 160 items)
- [x] Caching strategy stated (single invalidation at commit)
- [x] DB queries optimized (batch IN query, add_all for history)
- [x] Pagination applied where needed (N/A — max 160 items per call)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, item_count included)
- [x] Audit log entries defined (with item_count and source breakdown)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (odontogram.bulk_updated event with source_breakdown)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services (DB rollback test)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
