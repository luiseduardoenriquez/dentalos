# OD-03: Remove Odontogram Condition Spec

---

## Overview

**Feature:** Remove an active dental condition from a tooth zone, reverting that zone to an implicit "sano" (healthy) state. This is a soft-logical delete — the `odontogram_conditions` row is deleted but an immutable removal entry is written to `odontogram_history`, preserving full audit trail integrity. Only doctors can remove conditions (not assistants).

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-02 (odontogram-update-condition.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Assistants and receptionists are explicitly excluded from removals. This is intentional: removal of a diagnosis is a clinical decision that requires doctor authority.

---

## Endpoint

```
DELETE /api/v1/patients/{patient_id}/odontogram/conditions/{condition_id}
```

**Rate Limiting:**
- 30 requests per minute per user
- Removals should be rare; high rate could indicate erroneous automation.

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
| patient_id | Yes | UUID | Valid UUID v4 | Patient identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| condition_id | Yes | UUID | Valid UUID v4 | Condition record identifier from odontogram_conditions table | c1d2e3f4-a5b6-7890-abcd-123456789abc |

### Query Parameters

None.

### Request Body Schema

None (DELETE request). Optional body allowed for providing removal reason.

**Optional Body:**
```json
{
  "reason": "string (optional) — max 300 chars. Clinical reason for removal. Stored in history entry."
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
  "condition_id": "uuid (the removed condition)",
  "tooth_number": "integer",
  "zone": "string",
  "previous_condition_code": "string",
  "history_entry_id": "uuid",
  "removed_by": "uuid",
  "removed_at": "string (ISO 8601)"
}
```

**Example:**
```json
{
  "message": "Condicion eliminada correctamente. La zona ha sido revertida a estado sano.",
  "condition_id": "c1d2e3f4-a5b6-7890-abcd-123456789abc",
  "tooth_number": 36,
  "zone": "oclusal",
  "previous_condition_code": "caries",
  "history_entry_id": "h1i2j3k4-l5m6-7890-abcd-123456789def",
  "removed_by": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
  "removed_at": "2026-02-24T15:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is assistant, receptionist, or patient.

```json
{
  "error": "forbidden",
  "message": "Solo los medicos pueden eliminar condiciones del odontograma."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist in the tenant, or `condition_id` does not belong to this patient.

```json
{
  "error": "not_found",
  "message": "Condicion no encontrada o no pertenece al paciente especificado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure during deletion or history creation.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` and `condition_id` are valid UUID v4 formats.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role is in `[clinic_owner, doctor]`. Reject with 403 otherwise.
4. Fetch `odontogram_conditions` row by `condition_id` WHERE `patient_id = :patient_id`. If not found, return 404.
5. Capture snapshot of the condition before deletion: `{tooth_number, zone, condition_code, severity, notes}`.
6. Parse optional request body for `reason` field.
7. Within a single database transaction:
   a. DELETE the `odontogram_conditions` row.
   b. INSERT `odontogram_history` entry with `action = "remove"`, `previous_data` = captured snapshot, `new_data = null`, `reason` stored in `previous_data.reason` if provided, `performed_by` = current user id.
8. Delete Redis cache key `tenant:{tenant_id}:odontogram:{patient_id}`.
9. Write audit log entry (action: delete, resource: odontogram_condition, PHI: yes).
10. Return 200 with removal confirmation and history entry ID.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| condition_id | Valid UUID v4 | El identificador de la condicion no es valido. |
| condition_id | Must belong to specified patient_id | Condicion no encontrada o no pertenece al paciente especificado. |
| reason | Optional; max 300 chars; strip HTML | La razon de eliminacion no puede exceder 300 caracteres. |

**Business Rules:**

- Removal does NOT set the zone to a `"sano"` condition row in the database — it simply deletes the existing condition. The frontend interprets a null zone as healthy/sano.
- The history entry with `action = "remove"` is the permanent record that this zone ever had a condition. It is never deleted.
- A doctor cannot remove a condition belonging to a different patient, even within the same tenant.
- If the condition does not exist (already removed), return 404 — idempotent safety for retries is handled at the client level (the client should check OD-01 before retrying).
- `clinic_owner` inherits doctor-level access and can remove conditions for supervision/correction purposes.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Condition already removed (second DELETE call) | Return 404 (condition no longer exists) |
| Patient has multiple conditions on same tooth; only one zone removed | Other zones remain unaffected |
| Removal of a condition created by a different doctor | Allowed (any doctor in the tenant can correct another's entry) |
| Optional `reason` body not provided | History entry created without reason; `reason` field null in history JSONB |
| Condition linked to a treatment plan item | Remove condition from odontogram; treatment plan linkage (if any) is handled by treatment plans domain separately |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `odontogram_conditions`: DELETE — the condition row is permanently removed.
- `odontogram_history`: INSERT — immutable removal record created.

**Example query (SQLAlchemy):**
```python
# Fetch condition with patient ownership verification
condition = await session.execute(
    select(OdontogramCondition).where(
        OdontogramCondition.id == condition_id,
        OdontogramCondition.patient_id == patient_id,
    )
).scalar_one_or_none()

if not condition:
    raise NotFoundError("Condicion no encontrada o no pertenece al paciente especificado.")

previous_data = {
    "tooth_number": condition.tooth_number,
    "zone": condition.zone,
    "condition_code": condition.condition_code,
    "severity": condition.severity,
    "notes": condition.notes,
    "reason": data.reason if data else None,
}

await session.delete(condition)

history = OdontogramHistory(
    patient_id=patient_id,
    tooth_number=previous_data["tooth_number"],
    zone=previous_data["zone"],
    action="remove",
    condition_code=previous_data["condition_code"],
    previous_data=previous_data,
    new_data=None,
    performed_by=current_user.id,
)
session.add(history)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram:{patient_id}`: DELETE — invalidated after successful removal.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| odontogram | odontogram.condition_removed | { tenant_id, patient_id, tooth_number, zone, previous_condition_code, removed_by } | After successful deletion |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** delete
- **Resource:** odontogram_condition
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on delete; invalidates read cache.
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Deletes `tenant:{tenant_id}:odontogram:{patient_id}` on success.

### Database Performance

**Queries executed:** 2 (fetch condition for ownership check + delete + insert history in one transaction).

**Indexes required:**
- `odontogram_conditions.(id, patient_id)` — Composite lookup for ownership check; covered by existing indexes.
- `odontogram_history.(patient_id, created_at)` — INDEX (already defined).

**N+1 prevention:** Not applicable (single record operation).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Prevents path traversal via invalid UUIDs |
| condition_id | Pydantic UUID validator | Prevents path traversal via invalid UUIDs |
| reason | Pydantic strip() + bleach.clean() | Free text stored in audit history |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** The deleted condition data (tooth_number, zone, condition_code) is PHI. It is preserved in `odontogram_history` (not truly deleted from the system).

**Audit requirement:** All deletions logged with performer identity and timestamp.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor removes an existing condition
   - **Given:** Authenticated doctor, patient has caries on tooth 36 oclusal (condition_id known)
   - **When:** DELETE /api/v1/patients/{patient_id}/odontogram/conditions/{condition_id}
   - **Then:** 200 OK, history entry created with action=remove, cache invalidated

2. Doctor removes condition with reason
   - **Given:** Authenticated doctor, valid condition_id
   - **When:** DELETE with body `{"reason": "Diagnostico incorrecto, se reexamino el diente"}`
   - **Then:** 200 OK, reason stored in history previous_data JSONB

3. clinic_owner removes condition
   - **Given:** Authenticated clinic_owner role
   - **When:** DELETE valid condition
   - **Then:** 200 OK (clinic_owner inherits doctor access)

#### Edge Cases
1. Remove condition without optional reason body
   - **Given:** Authenticated doctor, valid condition
   - **When:** DELETE with no request body
   - **Then:** 200 OK, history entry created with reason=null

2. Other conditions on same tooth remain intact
   - **Given:** Tooth 36 has caries on oclusal AND restoration on mesial
   - **When:** DELETE the caries condition on oclusal
   - **Then:** 200 OK, mesial restoration remains; only oclusal zone reverts to null

#### Error Cases
1. Assistant attempts removal
   - **Given:** Authenticated user with assistant role
   - **When:** DELETE condition
   - **Then:** 403 Forbidden

2. Condition belongs to different patient
   - **Given:** Authenticated doctor, condition_id exists but belongs to patient_b, URL uses patient_a
   - **When:** DELETE /api/v1/patients/{patient_a_id}/odontogram/conditions/{condition_b_id}
   - **Then:** 404 Not Found (ownership check prevents cross-patient data access)

3. Condition already removed (double DELETE)
   - **Given:** Condition was already deleted
   - **When:** DELETE same condition_id again
   - **Then:** 404 Not Found

4. Invalid UUID for condition_id
   - **Given:** condition_id = "not-a-valid-uuid"
   - **When:** DELETE request
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** clinic_owner and doctor (should pass); assistant, receptionist, patient (should fail with 403).

**Patients/Entities:** Patient with multiple conditions on different teeth and zones; pre-existing condition with known condition_id.

### Mocking Strategy

- Redis: Use fakeredis to verify cache key deletion.
- RabbitMQ: Mock publish; assert `odontogram.condition_removed` payload contains correct tooth_number and zone.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Successful deletion returns 200 with removed condition details
- [ ] History entry created with action=remove and previous_data snapshot
- [ ] Redis cache invalidated after deletion
- [ ] Assistant role returns 403 Forbidden
- [ ] Cross-patient condition access returns 404
- [ ] Double deletion returns 404 (no error on first call)
- [ ] Optional reason stored in history when provided
- [ ] Audit log entry written with performer identity
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Bulk condition removal (OD-11 handles bulk operations)
- Soft-delete (conditions are hard-deleted; history preserves the record)
- Removing entire tooth's conditions at once (submit individual DELETEs per zone)
- Undo/restore deleted conditions (history is immutable, but a new condition can be added via OD-02)

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
- [x] Input sanitization defined (Pydantic UUID + bleach for reason)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail preserved in odontogram_history (immutable)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 150ms)
- [x] Caching strategy stated (write invalidates Redis)
- [x] DB queries optimized (ownership check + delete in one transaction)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (odontogram.condition_removed event)

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
