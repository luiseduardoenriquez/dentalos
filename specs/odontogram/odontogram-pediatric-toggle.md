# OD-12: Toggle Odontogram Dentition Type Spec

---

## Overview

**Feature:** Set or change the dentition type of a patient's odontogram between adult (32 teeth, FDI 11-48), pediatric (20 teeth, FDI 51-85), and mixed (both sets). The system auto-suggests the dentition type based on patient age, but the doctor makes the final clinical determination. When switching dentition types, existing conditions on shared tooth positions are preserved where applicable. This is a critical setup step for new patients and transition-age patients (6-12 years old).

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-01 (odontogram-get.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Assistants and receptionists cannot change dentition type. This is a clinical decision affecting the entire odontogram structure.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/odontogram/dentition
```

**Rate Limiting:**
- 10 requests per minute per user
- Dentition type changes should be rare; high rate indicates error or testing.

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
  "dentition_type": "string (required) — enum: adult, pediatric, mixed",
  "reason": "string (optional) — max 300 chars. Clinical reason for the change"
}
```

**Example Request:**
```json
{
  "dentition_type": "mixed",
  "reason": "Paciente de 8 anos en transicion, presenta dientes temporales y permanentes simultaneamente"
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
  "odontogram_id": "uuid",
  "previous_dentition_type": "string (adult | pediatric | mixed)",
  "new_dentition_type": "string (adult | pediatric | mixed)",
  "conditions_preserved": "integer",
  "conditions_removed": "integer",
  "recommended_type": "string (adult | pediatric | mixed)",
  "patient_age_years": "integer",
  "reason": "string | null",
  "changed_by": "uuid",
  "changed_at": "string (ISO 8601)"
}
```

**Example:**
```json
{
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "odontogram_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "previous_dentition_type": "pediatric",
  "new_dentition_type": "mixed",
  "conditions_preserved": 3,
  "conditions_removed": 0,
  "recommended_type": "mixed",
  "patient_age_years": 8,
  "reason": "Paciente de 8 anos en transicion, presenta dientes temporales y permanentes simultaneamente",
  "changed_by": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
  "changed_at": "2026-02-24T14:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON body.

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
  "message": "Solo los medicos pueden cambiar el tipo de denticion del odontograma."
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

#### 409 Conflict
**When:** The requested `dentition_type` is the same as the current one (no change needed).

```json
{
  "error": "no_change",
  "message": "El tipo de denticion ya es '{type}'. No se requiere cambio."
}
```

#### 422 Unprocessable Entity
**When:** Invalid `dentition_type` value.

```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "dentition_type": ["El tipo de denticion debe ser 'adult', 'pediatric' o 'mixed'."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected failure during dentition type update or condition migration.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema.
2. Resolve tenant from JWT; check user role is in `[clinic_owner, doctor]`. Return 403 otherwise.
3. Fetch patient record to get `birthdate` for age calculation.
4. Fetch `odontogram_states` row to get `current dentition_type`. Return 404 if not found.
5. If `dentition_type == current dentition_type`: return 409 Conflict (no-op guard).
6. Calculate patient age from `birthdate`:
   - Age < 6: recommended = `pediatric`
   - 6 <= age <= 12: recommended = `mixed`
   - Age > 12: recommended = `adult`
7. Determine condition migration strategy based on the transition:
   - **pediatric → adult**: pediatric conditions (FDI 51-85) are NOT automatically transferred to adult teeth (FDI 11-48). The relationship between primary and permanent teeth is not a 1:1 mapping. Pediatric conditions are PRESERVED (still exist in DB) but will not be visible in adult rendering. `conditions_removed` = 0, `conditions_preserved` = count of existing pediatric conditions.
   - **adult → pediatric**: adult conditions (FDI 11-48) are PRESERVED in DB but not visible. Same logic.
   - **any → mixed**: ALL existing conditions (both adult and pediatric FDI ranges) are preserved and displayed. `conditions_preserved` = total count of all existing conditions. `conditions_removed` = 0.
   - **mixed → adult**: pediatric conditions (FDI 51-85) are NOT deleted but become hidden. `conditions_removed` = 0 (they remain in DB for historical accuracy).
   - **mixed → pediatric**: adult conditions (FDI 11-48) are NOT deleted but become hidden.
8. Within a database transaction:
   a. UPDATE `odontogram_states` SET `dentition_type = :new_type`, `last_updated_by = :user_id`, `updated_at = now()`.
   b. Insert into `odontogram_history` a special entry with `action = "update"`, `condition_code = "dentition_change"`, `previous_data = {dentition_type: old}`, `new_data = {dentition_type: new, reason: reason}`, `performed_by = user_id`.
9. DELETE Redis cache key `tenant:{tenant_id}:odontogram:{patient_id}` (full odontogram re-fetched on next load).
10. Write audit log entry (action: update, resource: odontogram_dentition, PHI: yes).
11. Return 200 with change summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| dentition_type | Required; enum: adult, pediatric, mixed | El tipo de denticion debe ser 'adult', 'pediatric' o 'mixed'. |
| dentition_type | Must differ from current dentition type | El tipo de denticion ya es '{type}'. No se requiere cambio. |
| reason | Optional; max 300 chars; strip HTML | La razon no puede exceder 300 caracteres. |

**Business Rules:**

- The system calculates and returns `recommended_type` based on patient age, but the doctor's requested type takes precedence. No validation error is raised when the doctor selects a type different from the recommendation.
- Conditions are NEVER deleted when switching dentition types. Hidden conditions (from the non-active dentition set) remain in the DB for historical accuracy and can become visible again if the dentition is switched back.
- A special history entry with `condition_code = "dentition_change"` is recorded to make dentition type changes visible in the history timeline.
- `conditions_preserved` = count of conditions that remain fully visible after the change. `conditions_removed` is always 0 in the current design (conditions are preserved, not deleted).
- The `reason` field is stored in the history entry `new_data` JSONB for clinical documentation purposes.
- Mixed dentition shows ALL conditions from both adult and pediatric FDI ranges simultaneously. The UI groups them into separate arch views.

**Auto-suggestion Logic:**

| Patient Age | Recommended Dentition | Clinical Rationale |
|-------------|----------------------|-------------------|
| < 6 years | pediatric | Primary dentition phase |
| 6–12 years | mixed | Mixed dentition transitional phase |
| > 12 years | adult | Permanent dentition phase |

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Same dentition_type as current | Return 409 Conflict (no change, no DB write) |
| Adult patient (age 40) switched to pediatric by doctor | Allowed; no age-based restriction; `recommended_type` in response guides the doctor |
| Mixed → mixed (same type) | Return 409 |
| Patient with 50 pediatric conditions switched to adult | All 50 conditions preserved in DB; conditions_preserved=50; pediatric conditions hidden from adult rendering |
| Reason not provided | reason stored as null in history; no error |
| Patient birthdate missing (data integrity issue) | Age calculation returns null; recommended_type = null; operation still succeeds |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `odontogram_states`: UPDATE — `dentition_type`, `last_updated_by`, `updated_at`.
- `odontogram_history`: INSERT — special dentition change record with `condition_code = "dentition_change"`.

**Example query (SQLAlchemy):**
```python
# Update dentition type
odontogram_state.dentition_type = data.dentition_type
odontogram_state.last_updated_by = current_user.id
odontogram_state.updated_at = func.now()

# Record dentition change in history
history = OdontogramHistory(
    patient_id=patient_id,
    tooth_number=0,  # 0 = special value indicating whole-odontogram change
    zone="full",
    action="update",
    condition_code="dentition_change",
    previous_data={"dentition_type": previous_dentition_type},
    new_data={"dentition_type": data.dentition_type, "reason": data.reason},
    performed_by=current_user.id,
)
session.add(history)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram:{patient_id}`: DELETE — full odontogram cache invalidated (dentition type change affects which teeth are displayed).

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| odontogram | odontogram.dentition_changed | { tenant_id, patient_id, previous_type, new_type, changed_by } | After successful commit |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** update
- **Resource:** odontogram_dentition
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Write-only operation; invalidates read cache.
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Deletes `tenant:{tenant_id}:odontogram:{patient_id}` after commit.

### Database Performance

**Queries executed:** 3 (patient fetch with birthdate, odontogram_states fetch/update, history insert — in one transaction).

**Indexes required:**
- `odontogram_states.patient_id` — UNIQUE (already defined, ensures single row per patient).

**N+1 prevention:** Not applicable (single record update).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| dentition_type | Pydantic enum validator | Whitelist: adult, pediatric, mixed |
| reason | Pydantic strip() + bleach.clean() | Free text stored in history JSONB |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `dentition_type` change is clinical data. `reason` may contain clinical context. Both stored in history entry.

**Audit requirement:** All dentition type changes logged with performer identity.

---

## Testing

### Test Cases

#### Happy Path
1. Switch adult patient to mixed dentition
   - **Given:** Authenticated doctor, patient age=8 with dentition_type=adult and 5 conditions
   - **When:** POST with dentition_type=mixed
   - **Then:** 200 OK, new_dentition_type=mixed, conditions_preserved=5, conditions_removed=0, recommended_type=mixed, cache invalidated

2. Switch pediatric to adult
   - **Given:** Authenticated doctor, patient age=14, dentition_type=pediatric
   - **When:** POST with dentition_type=adult
   - **Then:** 200 OK, dentition changed, history entry with dentition_change recorded

3. Switch with reason
   - **Given:** Authenticated doctor
   - **When:** POST with dentition_type=adult and reason text
   - **Then:** 200 OK, reason stored in history new_data JSONB

4. clinic_owner changes dentition
   - **Given:** Authenticated clinic_owner role
   - **When:** POST dentition type change
   - **Then:** 200 OK

#### Edge Cases
1. Doctor overrides recommendation (adult patient set to pediatric)
   - **Given:** Patient age=40 (recommended=adult), doctor sends dentition_type=pediatric
   - **When:** POST
   - **Then:** 200 OK, change applied without error; recommended_type=adult shown in response for doctor's awareness

2. Switch without reason
   - **Given:** No reason field in body
   - **When:** POST with just dentition_type
   - **Then:** 200 OK, reason=null in response and history

3. Switch to mixed: all existing conditions preserved and visible
   - **Given:** Patient has 3 pediatric conditions and 2 adult conditions (in mixed mode)
   - **When:** POST dentition_type=adult (from mixed)
   - **Then:** 200 OK, all 5 conditions preserved in DB, only adult conditions visible in OD-01 response

#### Error Cases
1. Same dentition type as current
   - **Given:** Patient already has dentition_type=adult
   - **When:** POST with dentition_type=adult
   - **Then:** 409 Conflict with Spanish error message

2. Assistant attempts dentition change
   - **Given:** Authenticated assistant role
   - **When:** POST dentition change
   - **Then:** 403 Forbidden

3. Invalid dentition_type value
   - **Given:** dentition_type = "temporary"
   - **When:** POST
   - **Then:** 422 Unprocessable Entity

4. Patient not found
   - **Given:** Non-existent patient_id
   - **When:** POST
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** doctor, clinic_owner (pass); assistant, receptionist, patient (fail with 403).

**Patients/Entities:** Patient with adult dentition and conditions; patient with pediatric dentition; patient age=8 for mixed recommendation; patient age=40 for adult recommendation override test.

### Mocking Strategy

- Redis: Use fakeredis; verify cache key deleted after successful dentition change.
- RabbitMQ: Mock publish; assert `odontogram.dentition_changed` payload.
- `datetime.now()`: Mock for deterministic age calculation in tests.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Dentition type updated in `odontogram_states` table
- [ ] History entry with `condition_code="dentition_change"` created
- [ ] `recommended_type` correctly calculated from patient age
- [ ] No conditions deleted on any dentition type switch (conditions_removed=0 always)
- [ ] 409 returned when dentition_type is same as current (no DB writes)
- [ ] Redis odontogram cache invalidated after change
- [ ] Assistant role returns 403
- [ ] Audit log entry written with changed_by identity
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Automatic condition remapping between primary and permanent tooth numbers (FDI 51→11 mapping is not done automatically)
- Mixed dentition visualization logic (frontend concern)
- Condition deletion when switching dentition types (conditions are preserved by design)
- Age-based auto-switching at patient birthday (a periodic job in the background, not this endpoint)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (including same-type conflict)
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant — doctor only)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context — doctor only)
- [x] Input sanitization defined (Pydantic enum + bleach for reason)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for dentition type changes

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 200ms)
- [x] Caching strategy stated (write invalidates Redis)
- [x] DB queries optimized (3 queries in one transaction)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (with previous and new dentition type)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (odontogram.dentition_changed event)

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
