# OD-07: List Odontogram Snapshots Spec

---

## Overview

**Feature:** List all point-in-time odontogram snapshots for a patient, ordered by most recent first. Returns summary metadata for each snapshot (without full snapshot_data JSONB) to support efficient list rendering in the UI. Used to show a timeline of odontogram states and allow users to select a specific snapshot for full retrieval (OD-06) or comparison (OD-08).

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-05 (odontogram-snapshot.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist and patient roles are excluded.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/odontogram/snapshots
```

**Rate Limiting:**
- 60 requests per minute per user
- Inherits global rate limit baseline.

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

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| cursor | No | string | Opaque cursor from previous response | Cursor for pagination | eyJpZCI6IjEyMzQifQ== |
| limit | No | integer | 1–50, default 20 | Number of snapshots per page | 20 |

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "uuid",
      "label": "string | null",
      "dentition_type": "string (adult | pediatric | mixed)",
      "conditions_count": "integer",
      "linked_record_id": "uuid | null",
      "linked_treatment_plan_id": "uuid | null",
      "created_by": {
        "id": "uuid",
        "full_name": "string",
        "role": "string"
      },
      "created_at": "string (ISO 8601)"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_returned": "integer"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "snap3c4d-5e6f-7890-abcd-123456789xyz",
      "label": "Post-tratamiento blanqueamiento",
      "dentition_type": "adult",
      "conditions_count": 2,
      "linked_record_id": null,
      "linked_treatment_plan_id": null,
      "created_by": {
        "id": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
        "full_name": "Dr. Carlos Mendez",
        "role": "doctor"
      },
      "created_at": "2026-02-20T11:00:00Z"
    },
    {
      "id": "snap1a2b-3c4d-5e6f-7890-abcd12345678",
      "label": "Pre-tratamiento ortodoncia",
      "dentition_type": "adult",
      "conditions_count": 5,
      "linked_record_id": null,
      "linked_treatment_plan_id": "tp1a2b3c4-d5e6-7890-abcd-123456789abc",
      "created_by": {
        "id": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
        "full_name": "Dr. Carlos Mendez",
        "role": "doctor"
      },
      "created_at": "2026-02-10T09:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "total_returned": 2
  }
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
  "message": "No tiene permisos para ver las instantaneas del odontograma."
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
**When:** Invalid query parameter values.

```json
{
  "error": "validation_failed",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "limit": ["El limite debe ser entre 1 y 50."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure during snapshot list query.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` UUID format and query parameters.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role is in `[clinic_owner, doctor, assistant]`. Reject with 403 otherwise.
4. Verify patient exists in tenant schema. Return 404 if not found.
5. Query `odontogram_snapshots` WHERE `patient_id = :patient_id`.
6. Apply cursor-based pagination: if `cursor` provided, decode and apply `created_at < cursor_timestamp AND id < cursor_id`.
7. ORDER BY `created_at DESC, id DESC`.
8. Fetch `limit + 1` rows to determine `has_more`.
9. JOIN `users` table to resolve `created_by` to `{id, full_name, role}`.
10. Extract `conditions_count` from `snapshot_data->>'total_conditions'` JSONB path (stored at creation time in OD-05).
11. Return list WITHOUT `snapshot_data` body — summary only for performance.
12. If `total_returned = limit + 1`, pop last row, encode next cursor, set `has_more = true`.
13. Write audit log entry (action: read, resource: odontogram_snapshots, PHI: yes).
14. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| limit | Integer 1–50, default 20 | El limite debe ser entre 1 y 50. |
| cursor | Valid opaque cursor (if provided) | El cursor de paginacion no es valido. |

**Business Rules:**

- The list endpoint intentionally omits `snapshot_data` JSONB to avoid transmitting large payloads when only summary info is needed. Full data is retrieved per-snapshot via OD-06.
- `conditions_count` is extracted from the stored `snapshot_data` JSONB field `total_conditions` — no separate count query needed.
- Default page size is 20 (smaller than history's 50) because snapshot cards are larger UI elements and fewer fit per screen.
- List is ordered by most recent first to match typical clinical workflow (review latest snapshot first).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has zero snapshots | Return empty data array, has_more=false |
| limit=1 with many snapshots | Return 1 snapshot, has_more=true, next_cursor set |
| All snapshots have no label | All label fields null; valid response |
| Snapshot creator user deactivated | Return available user data from JOIN; full_name returned if user row exists |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint).

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram_snapshots_list:{patient_id}`: SET — cache list response, TTL 60s.
- Invalidated by OD-05 (snapshot.created event via `odontogram.snapshot_created` queue job).

**Cache TTL:** 60 seconds. Short TTL because new snapshots can be created, and the list should stay reasonably fresh.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** read
- **Resource:** odontogram_snapshots
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Redis cache for list, tenant-namespaced, short TTL.
- **Cache key:** `tenant:{tenant_id}:odontogram_snapshots_list:{patient_id}`
- **TTL:** 60 seconds
- **Invalidation:** Deleted when a new snapshot is created for this patient (via OD-05 queue job handler).

### Database Performance

**Queries executed:** 2 (patient existence check + snapshot list with user JOIN).

**Indexes required:**
- `odontogram_snapshots.(patient_id, created_at)` — INDEX (already defined: `idx_odontogram_snapshots_date`)

**N+1 prevention:** Single JOIN to `users` table within the list query. `conditions_count` extracted from JSONB, not from a separate COUNT query.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on `created_at DESC, id DESC`)
- **Default page size:** 20
- **Max page size:** 50

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | |
| limit | Pydantic int with ge=1, le=50 | |
| cursor | Base64 decode + JSON parse + extract timestamp/UUID | Reject malformed cursors |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Snapshot labels may contain clinical context. `conditions_count` is clinical data.

**Audit requirement:** All access logged.

---

## Testing

### Test Cases

#### Happy Path
1. List snapshots for patient with multiple snapshots
   - **Given:** Authenticated doctor, patient with 5 snapshots
   - **When:** GET /api/v1/patients/{patient_id}/odontogram/snapshots
   - **Then:** 200 OK, 5 snapshots returned ordered by date desc, no snapshot_data in response

2. Assistant lists snapshots
   - **Given:** Authenticated assistant role
   - **When:** GET snapshots list
   - **Then:** 200 OK

3. Pagination — first page
   - **Given:** Patient with 35 snapshots
   - **When:** GET with limit=20
   - **Then:** 200 OK, 20 snapshots returned, has_more=true, next_cursor set

4. Pagination — second page
   - **Given:** Previous next_cursor from first page
   - **When:** GET with cursor={next_cursor}
   - **Then:** 200 OK, 15 remaining snapshots, has_more=false

#### Edge Cases
1. Patient with zero snapshots
   - **Given:** Patient with no snapshots
   - **When:** GET snapshots list
   - **Then:** 200 OK, data=[], has_more=false

2. All snapshots have no label
   - **Given:** 3 snapshots all created without label
   - **When:** GET snapshots list
   - **Then:** 200 OK, all label fields null

3. Cache invalidation after new snapshot
   - **Given:** List cached; new snapshot created via OD-05
   - **When:** GET list again
   - **Then:** New snapshot appears (cache invalidated by queue job handler)

#### Error Cases
1. Receptionist access
   - **Given:** Authenticated receptionist role
   - **When:** GET snapshots list
   - **Then:** 403 Forbidden

2. Patient not found
   - **Given:** Non-existent patient_id
   - **When:** GET snapshots list
   - **Then:** 404 Not Found

3. limit exceeds maximum
   - **Given:** limit=100
   - **When:** GET snapshots list
   - **Then:** 422 with limit validation error

### Test Data Requirements

**Users:** doctor, assistant (pass); receptionist, patient (fail with 403).

**Patients/Entities:** Patient with 35 snapshots for pagination testing; patient with zero snapshots; patient with snapshots having various labels and linked entities.

### Mocking Strategy

- Redis: Use fakeredis; test cache set on first request, cache hit on second, cache invalidation after snapshot creation.
- Queue consumer: Mock the `odontogram.snapshot_created` handler to simulate cache invalidation.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Returns snapshots ordered by date descending (most recent first)
- [ ] Summary only — no `snapshot_data` JSONB in list response
- [ ] `conditions_count` extracted correctly from snapshot JSONB
- [ ] `created_by` resolved to full_name + role
- [ ] Cursor-based pagination works correctly across pages
- [ ] Cache invalidated when new snapshot created
- [ ] Receptionist and patient roles return 403
- [ ] Audit log entry written on every access
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Full snapshot data retrieval (OD-06)
- Snapshot comparison (OD-08)
- Filtering snapshots by date or label (future enhancement)
- Deleting snapshots from the list

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
- [x] Audit trail for snapshot list access

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 150ms)
- [x] Caching strategy stated (Redis 60s TTL, short to stay fresh)
- [x] DB queries optimized (indexed lookup, JOIN for user data)
- [x] Pagination applied (cursor-based, default 20, max 50)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A — read only; cache invalidation via queue)

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
