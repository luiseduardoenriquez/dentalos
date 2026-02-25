# OD-10: Get Tooth Detail Spec

---

## Overview

**Feature:** Retrieve detailed information for a single tooth within a patient's odontogram, including all zone conditions, the complete condition history for that tooth, and links to associated treatments, photos, and X-rays. This is the drill-down view accessed when a doctor taps a specific tooth in the odontogram UI to see everything recorded for that tooth in one response.

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-01 (odontogram-get.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist and patient roles are excluded. Tooth-level clinical detail requires clinical staff access.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/odontogram/teeth/{tooth_number}
```

**Rate Limiting:**
- 120 requests per minute per user
- Frequently accessed during examination (doctor taps individual teeth).

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
| tooth_number | Yes | integer | Valid FDI notation (11-48 adult, 51-85 pediatric) | FDI tooth number | 36 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| include_history | No | boolean | Default: true | Include full condition history for this tooth | true |
| history_limit | No | integer | 1-50, default 10 | Max history entries to return | 10 |

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "patient_id": "uuid",
  "tooth_number": "integer",
  "tooth_name_es": "string",
  "tooth_name_en": "string",
  "tooth_type": "string (molar | premolar | canine | incisor)",
  "arch": "string (upper | lower)",
  "side": "string (right | left)",
  "is_pediatric": "boolean",
  "zones": {
    "mesial": {
      "condition_id": "uuid | null",
      "condition_code": "string | null",
      "condition_color": "string (hex) | null",
      "severity": "string | null",
      "notes": "string | null",
      "history_count": "integer",
      "last_updated": "string (ISO 8601) | null",
      "last_updated_by": { "id": "uuid", "full_name": "string" }
    },
    "distal": { "...same structure..." },
    "vestibular": { "...same structure..." },
    "lingual": { "...same structure..." },
    "oclusal": { "...same structure..." },
    "root": { "...same structure..." }
  },
  "active_conditions_count": "integer",
  "history": [
    {
      "id": "uuid",
      "zone": "string",
      "action": "string (add | update | remove)",
      "condition_code": "string",
      "previous_data": "object | null",
      "new_data": "object | null",
      "performed_by": { "id": "uuid", "full_name": "string", "role": "string" },
      "created_at": "string (ISO 8601)"
    }
  ],
  "history_total": "integer",
  "linked_treatments": [
    {
      "id": "uuid",
      "procedure_name": "string",
      "status": "string",
      "scheduled_date": "string (ISO 8601) | null"
    }
  ],
  "photos_count": "integer",
  "xrays_count": "integer"
}
```

**Example:**
```json
{
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "tooth_number": 36,
  "tooth_name_es": "Primer molar inferior izquierdo",
  "tooth_name_en": "Lower left first molar",
  "tooth_type": "molar",
  "arch": "lower",
  "side": "left",
  "is_pediatric": false,
  "zones": {
    "mesial": {
      "condition_id": null,
      "condition_code": null,
      "condition_color": null,
      "severity": null,
      "notes": null,
      "history_count": 0,
      "last_updated": null,
      "last_updated_by": null
    },
    "distal": {
      "condition_id": null,
      "condition_code": null,
      "condition_color": null,
      "severity": null,
      "notes": null,
      "history_count": 0,
      "last_updated": null,
      "last_updated_by": null
    },
    "vestibular": {
      "condition_id": null,
      "condition_code": null,
      "condition_color": null,
      "severity": null,
      "notes": null,
      "history_count": 0,
      "last_updated": null,
      "last_updated_by": null
    },
    "lingual": {
      "condition_id": null,
      "condition_code": null,
      "condition_color": null,
      "severity": null,
      "notes": null,
      "history_count": 0,
      "last_updated": null,
      "last_updated_by": null
    },
    "oclusal": {
      "condition_id": "c1d2e3f4-a5b6-7890-abcd-123456789abc",
      "condition_code": "caries",
      "condition_color": "#D32F2F",
      "severity": "moderate",
      "notes": "Caries oclusal con compromiso dentinario",
      "history_count": 2,
      "last_updated": "2026-02-20T10:30:00Z",
      "last_updated_by": { "id": "d4e5f6a7-b1c2-7890-abcd-ef1234567890", "full_name": "Dr. Carlos Mendez" }
    },
    "root": {
      "condition_id": null,
      "condition_code": null,
      "condition_color": null,
      "severity": null,
      "notes": null,
      "history_count": 0,
      "last_updated": null,
      "last_updated_by": null
    }
  },
  "active_conditions_count": 1,
  "history": [
    {
      "id": "h1i2j3k4-l5m6-7890-abcd-123456789def",
      "zone": "oclusal",
      "action": "update",
      "condition_code": "caries",
      "previous_data": { "condition_code": "caries", "severity": "mild", "notes": "Caries inicial" },
      "new_data": { "condition_code": "caries", "severity": "moderate", "notes": "Caries oclusal con compromiso dentinario", "source": "manual" },
      "performed_by": { "id": "d4e5f6a7-b1c2-7890-abcd-ef1234567890", "full_name": "Dr. Carlos Mendez", "role": "doctor" },
      "created_at": "2026-02-20T10:30:00Z"
    },
    {
      "id": "a9b8c7d6-e5f4-7890-abcd-321098765fed",
      "zone": "oclusal",
      "action": "add",
      "condition_code": "caries",
      "previous_data": null,
      "new_data": { "condition_code": "caries", "severity": "mild", "notes": "Caries inicial", "source": "manual" },
      "performed_by": { "id": "d4e5f6a7-b1c2-7890-abcd-ef1234567890", "full_name": "Dr. Carlos Mendez", "role": "doctor" },
      "created_at": "2026-01-15T09:00:00Z"
    }
  ],
  "history_total": 2,
  "linked_treatments": [
    {
      "id": "tx1a2b3c-d4e5-6789-abcd-012345678901",
      "procedure_name": "Restauracion compuesta clase I",
      "status": "scheduled",
      "scheduled_date": "2026-03-05T09:00:00Z"
    }
  ],
  "photos_count": 2,
  "xrays_count": 1
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is receptionist or patient.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver el detalle de este diente."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist, or `tooth_number` is not a valid FDI number for this patient's dentition type.

```json
{
  "error": "not_found",
  "message": "Diente no encontrado para el paciente especificado."
}
```

#### 422 Unprocessable Entity
**When:** `tooth_number` is not a valid integer or not in any FDI range.

```json
{
  "error": "validation_failed",
  "message": "El numero de diente no es valido en notacion FDI.",
  "details": {
    "tooth_number": ["El diente 99 no existe en la notacion FDI."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` UUID and `tooth_number` integer format.
2. Validate `tooth_number` is in a valid FDI range (11-48 or 51-85). Return 422 if not.
3. Resolve tenant from JWT; check user role is in `[clinic_owner, doctor, assistant]`.
4. Fetch patient and `odontogram_states` row to verify `tooth_number` is valid for the patient's `dentition_type`. Return 404 if tooth not applicable (e.g., adult tooth requested on pediatric-only patient).
5. Fetch all 6 zones for this tooth from `odontogram_conditions` WHERE `patient_id = :patient_id AND tooth_number = :tooth_number`.
6. Fetch history for this tooth from `odontogram_history` WHERE same conditions, ORDER BY `created_at DESC`, LIMIT `history_limit` (default 10). Also fetch `COUNT(*)` total for `history_total`.
7. JOIN users table to resolve `created_by` and `performed_by` UUIDs to names.
8. Look up tooth metadata from in-memory FDI tooth catalog: name_es, name_en, tooth_type, arch, side, is_pediatric.
9. Fetch count of linked treatment plan items referencing this tooth_number for this patient from `treatment_plan_items` table (or equivalent).
10. Fetch counts from document/photo tables: `photos_count`, `xrays_count` (via patient_documents table filtered by tooth_number if that field exists, else return 0 and note this is a future enhancement).
11. Enrich zone conditions with `condition_color` from catalog.
12. Calculate `active_conditions_count` = count of non-null zone conditions.
13. Write audit log (action: read, resource: odontogram_tooth_detail, PHI: yes).
14. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| tooth_number | Integer; must be in FDI range 11-18, 21-28, 31-38, 41-48, 51-55, 61-65, 71-75, or 81-85 | El numero de diente {n} no es valido en notacion FDI. |
| tooth_number | Must match patient's dentition type | Diente no aplicable para el tipo de denticion del paciente. |
| include_history | Boolean (if provided) | El parametro include_history debe ser true o false. |
| history_limit | Integer 1-50 (if provided) | El limite de historial debe ser entre 1 y 50. |

**Business Rules:**

- Each tooth has a canonical Spanish and English name derived from FDI notation (in-memory lookup table).
- If `include_history = false`, the `history` array is omitted from the response and `history_total = 0` (saves a DB query).
- `photos_count` and `xrays_count` are lightweight counts only; actual photos and X-rays are fetched via a separate documents endpoint.
- `linked_treatments` only shows treatment plan items whose `tooth_number` matches; not all treatments for the patient.
- History is returned most-recent-first, limited to `history_limit` entries. `history_total` always reflects the actual total count.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tooth exists in FDI but has no conditions or history | Return all null zones, empty history array, history_total=0 |
| Mixed dentition patient: request adult tooth number | Allowed (mixed dentition has both sets) |
| history_limit=0 | Return 422 (minimum is 1) |
| include_history=false | Skip history queries; return history=[] and history_total=0 |
| Tooth number 32 (wisdom tooth, may or may not be present) | Valid FDI number; return as-is with whatever conditions are recorded |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint).

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram_tooth:{patient_id}:{tooth_number}`: SET — cache tooth detail, TTL 120s.
- Invalidated by OD-02, OD-03, OD-11 when the specified tooth is modified.

**Cache TTL:** 120 seconds (2 minutes). Shorter than the full odontogram cache since tooth-level changes are more targeted.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** read
- **Resource:** odontogram_tooth_detail
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 250ms
- **Maximum acceptable:** < 600ms

### Caching Strategy
- **Strategy:** Redis cache per tooth per patient, tenant-namespaced.
- **Cache key:** `tenant:{tenant_id}:odontogram_tooth:{patient_id}:{tooth_number}`
- **TTL:** 120 seconds
- **Invalidation:** Deleted by OD-02/OD-03/OD-11 when the specific tooth_number is written for this patient.

### Database Performance

**Queries executed:** 3-5 (patient check, zone conditions, history + count, treatment links, document counts). Run concurrently where possible using `asyncio.gather`.

**Indexes required:**
- `odontogram_conditions.(patient_id, tooth_number)` — INDEX (already defined: `idx_odontogram_conditions_tooth`)
- `odontogram_history.(patient_id, tooth_number)` — INDEX (already defined: `idx_odontogram_history_tooth`)

**N+1 prevention:** All queries batched. User names resolved via JOIN within history query.

### Pagination

**Pagination:** Partial — history is limited via `history_limit` parameter (1-50). Full history available via OD-04.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | |
| tooth_number | Pydantic int validator + FDI range check | No string injection |
| include_history | Pydantic bool validator | |
| history_limit | Pydantic int with ge=1, le=50 | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** All zone conditions, history entries, notes, linked treatments are clinical PHI.

**Audit requirement:** All access logged.

---

## Testing

### Test Cases

#### Happy Path
1. Get tooth detail with conditions and history
   - **Given:** Authenticated doctor, tooth 36 has 1 active condition and 3 history entries
   - **When:** GET /api/v1/patients/{patient_id}/odontogram/teeth/36
   - **Then:** 200 OK, zones populated, history returns 3 entries (up to default limit 10), history_total=3

2. Get tooth detail with include_history=false
   - **Given:** Authenticated doctor
   - **When:** GET with include_history=false
   - **Then:** 200 OK, history=[], history_total=0 (history query skipped)

3. Get tooth with no conditions
   - **Given:** Tooth 11 has never had a condition recorded
   - **When:** GET tooth 11
   - **Then:** 200 OK, all zones null, active_conditions_count=0, history=[]

4. history_limit controls returned entries
   - **Given:** Tooth 36 has 15 history entries
   - **When:** GET with history_limit=5
   - **Then:** 200 OK, 5 history entries returned, history_total=15

#### Edge Cases
1. Pediatric tooth for mixed dentition patient
   - **Given:** Patient has mixed dentition (age 8), request tooth 75 (pediatric)
   - **When:** GET tooth 75
   - **Then:** 200 OK with pediatric tooth metadata

2. Tooth with linked treatments
   - **Given:** Treatment plan item referencing tooth 36
   - **When:** GET tooth 36
   - **Then:** 200 OK, linked_treatments array includes the treatment item

3. Wisdom tooth (tooth 18 or 28) with no conditions
   - **Given:** Wisdom tooth present but no conditions recorded
   - **When:** GET tooth 18
   - **Then:** 200 OK, all zones null

#### Error Cases
1. Invalid FDI tooth number
   - **Given:** tooth_number = 99
   - **When:** GET tooth 99
   - **Then:** 422 Unprocessable Entity

2. Adult tooth requested on pediatric patient
   - **Given:** Patient dentition_type=pediatric, request tooth 36 (adult)
   - **When:** GET tooth 36
   - **Then:** 404 Not Found (tooth not applicable for dentition type)

3. Receptionist access
   - **Given:** Authenticated receptionist
   - **When:** GET tooth detail
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** doctor, assistant (pass); receptionist, patient (fail with 403).

**Patients/Entities:** Patient with tooth 36 having 1 active condition and multiple history entries. Patient with mixed dentition. Treatment plan item linked to tooth 36.

### Mocking Strategy

- Redis: Use fakeredis to test cache hit and cache miss.
- FDI tooth catalog: In-memory constant fixture with all 52 teeth metadata.
- `asyncio.gather`: Verify concurrent DB queries (integration test).

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Returns all 6 zones for specified tooth with condition data
- [ ] Tooth metadata (name_es, name_en, tooth_type, arch, side) correctly populated from FDI catalog
- [ ] History returned in descending chronological order, limited by history_limit
- [ ] `history_total` always reflects full count regardless of history_limit
- [ ] `include_history=false` skips history query (performance optimization)
- [ ] Linked treatment count populated from treatment_plan_items
- [ ] Adult tooth on pediatric patient returns 404
- [ ] Cache hit returns tooth detail within 50ms
- [ ] Receptionist and patient roles return 403
- [ ] Audit log entry written on every access
- [ ] All test cases pass
- [ ] Performance targets met (< 250ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Fetching the actual photo or X-ray files (photos_count and xrays_count are counts only; file retrieval uses a separate documents endpoint)
- Modifying conditions (OD-02, OD-03)
- Full history (OD-04 handles paginated history for any tooth)
- Comparing tooth states across time (OD-08)

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
- [x] Input sanitization defined (Pydantic validators)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical tooth detail access

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 250ms)
- [x] Caching strategy stated (Redis 120s TTL, tooth-level cache)
- [x] DB queries optimized (indexed, concurrent with asyncio.gather)
- [x] Pagination applied (history_limit parameter, full history in OD-04)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, tooth_number included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A — read only)

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
