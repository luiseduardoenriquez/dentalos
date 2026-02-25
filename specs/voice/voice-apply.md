# Voice Apply Spec

> **Spec ID:** V-04
> **Status:** Draft
> **Last Updated:** 2026-02-24

---

## Overview

**Feature:** Takes a confirmed set of clinical findings — after the user has reviewed, edited, or removed items from the LLM parse output (V-03) — and applies them to the odontogram by calling the existing bulk update endpoint (OD-11) internally, tagging each change with `source: "voice"` for traceability. This is the final write step in the Voice-to-Odontogram pipeline. Human review before this step is mandatory unless the tenant has configured `confirmation_mode: auto_apply` in voice settings (V-05).

**Domain:** voice

**Priority:** High

**Dependencies:** V-01 (voice-capture.md), V-02 (voice-transcription.md), V-03 (voice-parse.md), V-05 (voice-settings.md), odontogram/OD-11 (bulk-update), I-01 (multi-tenancy.md), infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** The session must belong to the tenant resolved from JWT. The session must be in "open" or "parsed" status. A session can only be applied once (idempotent guard: re-applying returns the original result). Plan add-on check: Voice add-on must be active.

---

## Endpoint

```
POST /api/v1/voice/sessions/{session_id}/apply
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)
- No special voice-specific rate limit; apply is a low-frequency, human-triggered action

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
| session_id | Yes | UUID v4 | Must exist in tenant | The voice session to finalize | 9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e |

### Query Parameters

None.

### Request Body Schema

```json
{
  "parse_id": "string (required) — UUID v4. The specific parse result being confirmed. Must belong to this session.",
  "confirmed_findings": [
    {
      "tooth": "integer (required) — FDI tooth number",
      "zone": "string (optional) — dental zone",
      "condition": "string (required) — condition code",
      "note": "string (optional) — max 500 chars. Free-text annotation added by user during review."
    }
  ],
  "session_notes": "string (optional) — max 2000 chars. Text to append to the evolution note (from parse.notes, possibly edited by user)."
}
```

**Notes on `confirmed_findings`:**
- This array is the user-confirmed, possibly edited version of `parse.findings`.
- The user may have: removed findings (omitted from array), edited tooth numbers or zones, or added a `note` per finding.
- If `confirmed_findings` is an empty array, the session is still applied (marked as applied with zero changes). This is valid — the user may confirm that nothing should be recorded.

**Example Request:**
```json
{
  "parse_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
  "confirmed_findings": [
    {
      "tooth": 46,
      "zone": "oclusal",
      "condition": "caries",
      "note": null
    },
    {
      "tooth": 11,
      "zone": "vestibular",
      "condition": "fractura",
      "note": "Fractura parcial tipo I, sin exposicion pulpar"
    }
  ],
  "session_notes": "El paciente reporta sensibilidad en el cuadrante inferior derecho. Se programa control en 2 semanas."
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "session_id": "uuid",
  "parse_id": "uuid",
  "status": "string",
  "applied_count": "integer",
  "errors": [
    {
      "tooth": "integer",
      "zone": "string | null",
      "condition": "string",
      "error": "string"
    }
  ],
  "odontogram_update_ids": "string[]",
  "evolution_note_id": "string | null",
  "applied_at": "string (ISO 8601 datetime)"
}
```

**Example (all changes applied successfully):**
```json
{
  "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
  "parse_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
  "status": "applied",
  "applied_count": 2,
  "errors": [],
  "odontogram_update_ids": [
    "e5f6a7b8-c9d0-1234-ef01-345678901234",
    "f6a7b8c9-d0e1-2345-f012-456789012345"
  ],
  "evolution_note_id": "a7b8c9d0-e1f2-3456-0123-567890123456",
  "applied_at": "2026-02-24T15:20:00Z"
}
```

**Example (partial success — one finding had a conflicting condition):**
```json
{
  "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
  "parse_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
  "status": "applied_with_errors",
  "applied_count": 1,
  "errors": [
    {
      "tooth": 11,
      "zone": "vestibular",
      "condition": "fractura",
      "error": "El diente 11 ya tiene una condicion activa de 'corona' que es incompatible con 'fractura'. Actualice manualmente."
    }
  ],
  "odontogram_update_ids": [
    "e5f6a7b8-c9d0-1234-ef01-345678901234"
  ],
  "evolution_note_id": null,
  "applied_at": "2026-02-24T15:20:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** parse_id is missing, or confirmed_findings contains invalid tooth numbers or condition codes.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "confirmed_findings[1].condition": ["Condicion 'relleno' no es valida. Use los codigos de condicion definidos."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 402 Payment Required
**When:** Voice add-on is not active.

**Example:**
```json
{
  "error": "addon_required",
  "message": "La funcion de voz requiere el complemento de Voz activo.",
  "details": {
    "addon": "voice"
  }
}
```

#### 403 Forbidden
**When:** User role is not doctor or assistant.

#### 404 Not Found
**When:** session_id or parse_id does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "La sesion o el resultado de analisis no fue encontrado.",
  "details": {
    "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
    "parse_id": "d4e5f6a7-b8c9-0123-def0-234567890123"
  }
}
```

#### 409 Conflict
**When:** The session has already been applied (idempotency guard).

**Example:**
```json
{
  "error": "session_already_applied",
  "message": "Esta sesion ya fue aplicada al odontograma.",
  "details": {
    "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
    "applied_at": "2026-02-24T15:20:00Z",
    "applied_count": 2
  }
}
```

#### 422 Unprocessable Entity
**When:** parse_id does not belong to the given session, or tooth number is outside valid FDI range for the patient's dentition type.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "parse_id": ["El resultado de analisis no pertenece a esta sesion."]
  }
}
```

#### 500 Internal Server Error
**When:** OD-11 bulk update fails with an internal error, or database transaction fails.

---

## Business Logic

**Step-by-step process:**

1. Validate request body: `parse_id` is a valid UUID, `confirmed_findings` is an array (may be empty), each finding has valid `tooth` (integer) and `condition` (must be in the approved conditions list).
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Check user role (must be doctor or assistant).
4. Check Voice add-on status.
5. Fetch session: `SELECT id, status, patient_id FROM voice_sessions WHERE id = :sid`. If not found, return 404. If `status = 'applied'`, return 409 with prior apply details.
6. Verify parse_id: `SELECT id FROM voice_parse_results WHERE id = :pid AND session_id = :sid`. If not found or session mismatch, return 404/422.
7. Fetch patient's odontogram state: `SELECT id, dentition_type FROM odontogram_states WHERE patient_id = :pid`.
8. Validate tooth numbers in `confirmed_findings` against dentition type ranges. Flag invalid numbers in response `errors[]` — do not abort entire request.
9. Begin database transaction.
10. For each valid finding in `confirmed_findings`: call OD-11 bulk update logic internally (service layer call, not HTTP). Pass `source: "voice"`, `voice_session_id: session_id`, `voice_parse_id: parse_id` as metadata on each odontogram entry. Collect errors from OD-11 (e.g., incompatible condition conflicts) into `errors[]`.
11. If `session_notes` is provided and non-empty: create an evolution note entry for the patient (`evolution_notes` table) with `source: "voice"`, linking to the voice session. Set `evolution_note_id` in response.
12. Update `voice_sessions`: `status = 'applied'`, `applied_at = NOW()`, `applied_count = COUNT(successfully applied findings)`.
13. Update `voice_parse_results`: mark the used parse as `applied = true`.
14. Commit transaction.
15. Write audit log entries:
    - One entry for the voice session apply (action: update, resource: voice_session, PHI: yes)
    - One entry per successfully applied odontogram finding (action: create, resource: odontogram_finding, PHI: yes, with voice_session_id reference)
16. Return 200 with apply summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| parse_id | Valid UUID v4, must exist, must belong to session | El resultado de analisis no pertenece a esta sesion. |
| confirmed_findings[].tooth | Integer; valid FDI number for patient's dentition type | Numero de diente invalido para el tipo de denticion del paciente. |
| confirmed_findings[].condition | Must be in the approved condition codes list | Condicion no valida. Use los codigos de condicion definidos. |
| confirmed_findings[].note | Max 500 chars if provided | La nota no puede superar los 500 caracteres. |
| session_notes | Max 2000 chars if provided | Las notas de sesion no pueden superar los 2,000 caracteres. |

**Approved condition codes (same list as V-03 dental prompt):**
`caries`, `fractura`, `obturacion`, `corona`, `endodoncia`, `extraccion`, `implante`, `protesis`, `movilidad`, `erosion`, `abrasion`, `abfraccion`, `hipersensibilidad`, `mancha`, `calcificacion`, `reabsorcion`, `periapical`, `ausente`, `sano`, `sellante`, `furca`, `bolsa_periodontal`, `recesion`, `edema`, `fistula`, `quiste`

**Business Rules:**

- The apply operation uses a **partial success model**: if some findings succeed and others fail (e.g., condition conflict in OD-11), the successful ones are committed and the errors are reported. The session is marked `applied` regardless. This avoids blocking the entire evaluation over one conflicting tooth.
- The `source: "voice"` flag on each odontogram entry enables future filtering in the odontogram history ("show only voice-entered findings") and analytics on voice adoption.
- The `voice_session_id` and `voice_parse_id` fields stored on each odontogram entry create a full audit trail linking clinical data back to the original audio session.
- If `confirmed_findings` is empty: session is marked `applied` with `applied_count = 0`. This is a valid action meaning "I reviewed and decided nothing should be recorded." It differs from not calling apply at all (session stays open).
- Sessions that are not applied within 24 hours of creation are automatically expired by the maintenance worker (status set to `expired`). Audio is deleted from S3 by the lifecycle rule. Transcription and parse data remain in DB.
- The `auto_apply` confirmation mode (V-05): if enabled, the frontend may call this endpoint immediately after parse without user editing. The API does not enforce the mode — it is the frontend's responsibility. The API only requires that `parse_id` and `confirmed_findings` are provided.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| confirmed_findings is empty array | Apply succeeds, applied_count = 0, session marked applied, 200 OK |
| All findings conflict with existing OD data | applied_count = 0, errors[] populated for all, status = applied_with_errors, session marked applied |
| Same session applied twice (idempotency) | Second call returns 409 with original apply details (no duplicate writes) |
| parse_id belongs to an older parse (user re-parsed and wants to use first result) | Allowed — any parse_id belonging to the session is valid |
| session_notes is empty string | Treat as null; no evolution note created |
| OD-11 internal call returns a validation error for one finding | Add to errors[], continue processing remaining findings |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `voice_sessions`: UPDATE — `status = 'applied'`, `applied_at`, `applied_count`
- `voice_parse_results`: UPDATE — `applied = true` for the used parse_id
- `odontogram_findings`: INSERT (via OD-11 service layer) — one record per successfully applied finding, with `source = 'voice'`, `voice_session_id`, `voice_parse_id`
- `evolution_notes`: INSERT (conditional) — if session_notes provided and non-empty
- `audit_log`: INSERT — one entry for session apply + one per finding

**Example query (SQLAlchemy):**
```python
# Update session
stmt = (
    update(VoiceSession)
    .where(VoiceSession.id == session.id)
    .values(
        status="applied",
        applied_at=datetime.now(timezone.utc),
        applied_count=len(successfully_applied),
    )
)
await db_session.execute(stmt)

# Per finding via OD-11 service layer (not raw SQL)
for finding in confirmed_findings:
    await odontogram_service.apply_finding(
        patient_id=session.patient_id,
        tooth=finding.tooth,
        zone=finding.zone,
        condition=finding.condition,
        note=finding.note,
        source="voice",
        voice_session_id=session.id,
        voice_parse_id=parse_id,
        created_by=current_user.id,
    )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram:{patient_id}`: INVALIDATE — odontogram cache cleared after findings applied (same invalidation as OD-11)
- `tenant:{tenant_id}:voice:session_status:{session_id}`: INVALIDATE — session status changed to applied

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| maintenance | audit.write | { action: apply, resource: voice_session, session_id, applied_count, tenant_id, user_id } | After successful apply |

**Note:** Individual odontogram finding audit entries are written synchronously (via the OD-11 service layer) due to the medical-record nature of the data. The session-level audit entry is dispatched async to not add latency to the HTTP response.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** update (voice session → applied), create (each odontogram finding)
- **Resource:** voice_session, odontogram_finding
- **PHI involved:** Yes (findings are clinical diagnoses; evolution_note_id links to patient record)

**Audit fields logged:**
- `session_id`, `parse_id`, `patient_id`, `applied_count`, `error_count`, `user_id`, `tenant_id`, `applied_at`
- For each finding: `tooth`, `condition`, `source: "voice"`, `voice_session_id`
- Full finding text and notes are NOT stored in audit log body (stored in the tenant DB tables)

### Notifications

**Notifications triggered:** No (apply is a background clinical action; no user notifications needed for MVP)

---

## Performance

### Expected Response Time
- **Target:** < 500ms for up to 20 findings
- **Maximum acceptable:** < 2000ms for up to 20 findings
- **Note:** Each finding requires an OD-11 service call (one DB INSERT per finding). 20 findings * ~15ms each = ~300ms. Use batch insert where OD-11 service supports it.

### Caching Strategy
- **Strategy:** No caching on apply (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Odontogram cache and session status cache invalidated after apply

### Database Performance

**Queries executed:** 5 base + N per finding (session fetch, parse verify, odontogram state fetch, session update, parse update, + 1 INSERT per finding via OD-11)

**Indexes required:**
- `voice_sessions.status` — INDEX (for maintenance worker expiry cleanup)
- `voice_parse_results.(session_id, applied)` — INDEX (to retrieve latest unapplied parse)
- `odontogram_findings.(patient_id, tooth, zone)` — INDEX (for OD-11 conflict detection)
- `odontogram_findings.voice_session_id` — INDEX (for voice-originated finding queries)

**N+1 prevention:** Findings are inserted in a single transaction. The OD-11 service layer should use a batch insert path when called from voice apply. If OD-11 does not support batch, findings are inserted in a loop within the same transaction (acceptable for up to 20 findings per typical evaluation).

**Batch insert optimization (SQLAlchemy):**
```python
findings_to_insert = [
    OdontogramFinding(
        patient_id=session.patient_id,
        tooth=f.tooth,
        zone=f.zone,
        condition=f.condition,
        source="voice",
        voice_session_id=session.id,
        voice_parse_id=parse_id,
        created_by=current_user.id,
        note=f.note,
    )
    for f in valid_findings
]
db_session.add_all(findings_to_insert)
await db_session.flush()
```

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| parse_id | Pydantic UUID v4 validator | Parameterized in SQL query |
| confirmed_findings[].tooth | Pydantic integer, > 0 | Validated against FDI ranges server-side |
| confirmed_findings[].condition | Pydantic enum (approved list) | Rejects arbitrary strings |
| confirmed_findings[].note | Pydantic strip() + bleach.clean, max 500 | Free-text clinical note; sanitized before storage |
| session_notes | Pydantic strip() + bleach.clean, max 2000 | Free-text evolution note; sanitized before storage |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL. OD-11 service layer uses the same ORM.

### XSS Prevention

**Output encoding:** All string outputs escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** confirmed_findings (clinical diagnoses per tooth linked to patient), session_notes (clinical observations), evolution_note_id (links to patient evolution record)

**Audit requirement:** All write operations logged. This is the final write step that produces permanent clinical records — audit logging is critical. Voice session ID and parse ID are included in each odontogram finding record for full traceability.

---

## Testing

### Test Cases

#### Happy Path
1. Apply two confirmed findings from parse result
   - **Given:** Open session, parse completed with 3 findings, user confirms 2 (removes 1)
   - **When:** POST apply with parse_id and confirmed_findings (2 items)
   - **Then:** 200 OK, applied_count = 2, odontogram_update_ids has 2 entries, session status = applied

2. Apply with session_notes
   - **Given:** Valid session and parse, session_notes provided
   - **When:** POST apply with session_notes
   - **Then:** 200 OK, evolution_note_id is non-null, evolution note stored with source=voice

3. Apply with empty confirmed_findings (user decides no changes)
   - **Given:** Valid session and parse
   - **When:** POST apply with confirmed_findings = []
   - **Then:** 200 OK, applied_count = 0, status = applied, no odontogram records created

4. Apply using older parse_id after re-parse
   - **Given:** Session has 2 parse results; user wants to use the first one
   - **When:** POST apply with the first parse_id
   - **Then:** 200 OK with the first parse's findings applied

#### Edge Cases
1. One finding conflicts with existing odontogram condition
   - **Given:** Tooth 11 already has condition 'corona' in the odontogram
   - **When:** POST apply with finding {tooth:11, condition:'fractura'}
   - **Then:** 200 OK (partial success), applied_count = 0, errors contains the conflict message for tooth 11, status = applied_with_errors

2. Idempotency — apply called twice
   - **Given:** Session already applied
   - **When:** POST apply again
   - **Then:** 409 Conflict with original applied_at and applied_count

#### Error Cases
1. parse_id does not belong to session
   - **Given:** parse_id from a different session
   - **When:** POST apply
   - **Then:** 422 Unprocessable Entity

2. Invalid condition code in confirmed_findings
   - **Given:** confirmed_findings contains {condition: "relleno"} (not in approved list)
   - **When:** POST apply
   - **Then:** 400 Bad Request with condition validation error

3. Session not found
   - **Given:** session_id is a valid UUID but does not exist
   - **When:** POST apply
   - **Then:** 404 Not Found

4. Database transaction fails mid-apply
   - **Given:** DB connection drops after 1st finding INSERT
   - **When:** POST apply
   - **Then:** 500 Internal Server Error; transaction rolled back; no partial odontogram changes; session status remains open

### Test Data Requirements

**Users:** doctor, assistant

**Patients/Entities:** Patient with adult dentition, odontogram state, voice session with completed parse result, session with status=applied (for 409 test)

**Odontogram state:** Pre-existing condition on tooth 11 (condition=corona) for conflict test

### Mocking Strategy

- OD-11 service layer: Use real service layer with test DB; mock for unit tests via dependency injection
- Redis: `fakeredis` for cache invalidation tests
- RabbitMQ: Mock publish for audit.write job dispatch
- Database transaction failure: Use SQLAlchemy event listeners to simulate connection drop at specific point

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST apply writes confirmed findings to odontogram via OD-11 service layer with source=voice flag
- [ ] Each odontogram finding record contains voice_session_id and voice_parse_id for traceability
- [ ] Session status updated to applied with applied_count and applied_at
- [ ] Partial success model: successful findings committed even if some fail; errors[] populated for failures
- [ ] Evolution note created when session_notes is provided
- [ ] Empty confirmed_findings accepted; session marked applied with applied_count=0
- [ ] Idempotency: second apply call returns 409 with original apply details
- [ ] Odontogram cache invalidated after apply
- [ ] Audit log entry written for session apply and each individual finding
- [ ] Invalid condition code rejected with 400
- [ ] parse_id from wrong session rejected with 422
- [ ] Transaction rollback on DB failure — no partial state
- [ ] All test cases pass
- [ ] Performance target met (< 500ms for 20 findings)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- The OD-11 bulk update endpoint itself (separate spec)
- Undoing a voice apply (rollback of applied odontogram findings — future enhancement)
- Auto-apply mode enforcement at the API level (frontend responsibility)
- Batch apply across multiple sessions simultaneously
- Conflict resolution UI (frontend concern)
- Voice session listing or history browsing (future enhancement)

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
- [x] Follows service boundaries (calls OD-11 service layer, not HTTP)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md conventions

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access (voice_session_id on every finding)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 500ms for 20 findings)
- [x] Caching strategy stated (invalidation only)
- [x] DB queries optimized (batch insert pattern, indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (per session + per finding)
- [x] Error tracking (Sentry-compatible)
- [x] Partial success model logged for analytics

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
| 1.0 | 2026-02-24 | Initial spec — Voice-to-Odontogram MVP |
