# OD-06: Get Odontogram Snapshot Spec

---

## Overview

**Feature:** Retrieve a specific point-in-time odontogram snapshot by its ID. Returns the complete denormalized odontogram state as it existed at the moment the snapshot was taken, including all tooth zones, conditions, and snapshot metadata. Used for reviewing historical states and as input to the comparison endpoint (OD-08).

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-05 (odontogram-snapshot.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist and patient roles are excluded. Snapshots contain full clinical diagnosis history.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/odontogram/snapshots/{snapshot_id}
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
| snapshot_id | Yes | UUID | Valid UUID v4 | Snapshot identifier from odontogram_snapshots table | snap1a2b-3c4d-5e6f-7890-abcd12345678 |

### Query Parameters

None.

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

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
          "distal": { "condition_code": "string | null", "severity": "string | null", "notes": "string | null" },
          "vestibular": { "condition_code": "string | null", "severity": "string | null", "notes": "string | null" },
          "lingual": { "condition_code": "string | null", "severity": "string | null", "notes": "string | null" },
          "oclusal": { "condition_code": "string | null", "severity": "string | null", "notes": "string | null" },
          "root": { "condition_code": "string | null", "severity": "string | null", "notes": "string | null" }
        }
      }
    ],
    "total_conditions": "integer",
    "captured_at": "string (ISO 8601)"
  },
  "created_by": {
    "id": "uuid",
    "full_name": "string",
    "role": "string"
  },
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
  "conditions_count": 3,
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
      },
      {
        "tooth_number": 36,
        "zones": {
          "mesial": { "condition_code": null, "severity": null, "notes": null },
          "distal": { "condition_code": null, "severity": null, "notes": null },
          "vestibular": { "condition_code": null, "severity": null, "notes": null },
          "lingual": { "condition_code": null, "severity": null, "notes": null },
          "oclusal": { "condition_code": "restoration", "severity": null, "notes": "Restauracion compuesta clase I" },
          "root": { "condition_code": null, "severity": null, "notes": null }
        }
      }
    ],
    "total_conditions": 3,
    "captured_at": "2026-02-10T09:00:00Z"
  },
  "created_by": {
    "id": "d4e5f6a7-b1c2-7890-abcd-ef1234567890",
    "full_name": "Dr. Carlos Mendez",
    "role": "doctor"
  },
  "created_at": "2026-02-10T09:00:00Z"
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
**When:** `patient_id` does not exist, or `snapshot_id` does not exist, or the snapshot does not belong to this patient.

```json
{
  "error": "not_found",
  "message": "Instantanea no encontrada o no pertenece al paciente especificado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure during snapshot retrieval.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` and `snapshot_id` are valid UUID v4 formats.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role is in `[clinic_owner, doctor, assistant]`. Reject with 403 otherwise.
4. Query `odontogram_snapshots` WHERE `id = :snapshot_id AND patient_id = :patient_id`.
   - Combining both in the WHERE clause prevents cross-patient data access in a single query.
   - Return 404 if not found.
5. JOIN with `users` table to resolve `created_by` UUID to `{id, full_name, role}`.
6. Derive `conditions_count` from `snapshot_data.total_conditions` (stored in JSONB at creation time).
7. Write audit log entry (action: read, resource: odontogram_snapshot, PHI: yes).
8. Return 200 with full snapshot including `snapshot_data` JSONB.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| snapshot_id | Valid UUID v4 | El identificador de la instantanea no es valido. |

**Business Rules:**

- The `snapshot_data` JSONB is returned as-is from the database — it is the authoritative historical record.
- No live condition data is merged or refreshed; the snapshot is entirely self-contained.
- The `created_by` is resolved to a user profile for display purposes. If the user has since been deactivated, their name and role at time of snapshot are not preserved in JSONB (only the UUID is stored). The JOIN may return partial data if the user is deleted; handle gracefully with fallback.
- Ownership verification (`patient_id` in WHERE) ensures doctors cannot access snapshots of patients from other tenants even if they know the snapshot UUID.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| snapshot_id exists but belongs to a different patient in same tenant | Return 404 (ownership check rejects cross-patient access) |
| Snapshot creator user has been deactivated | JOIN returns data if user row exists; return created_by with available data or null fields |
| Snapshot has no label | Return label=null (not an error) |
| Snapshot has linked_treatment_plan_id for a plan that has since been deleted | Return the stored UUID as-is; do not validate link at read time (snapshot is historical) |
| snapshot_data JSONB was created with a different dentition set than current patient dentition | Return snapshot as stored; it reflects historical state |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint).

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram_snapshot:{snapshot_id}`: SET — cache snapshot response, TTL 3600s (1 hour). Snapshots are immutable so long TTL is safe.

**Cache TTL:** 3600 seconds (1 hour) — snapshots never change after creation.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** read
- **Resource:** odontogram_snapshot
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Redis cache per snapshot — snapshots are immutable so aggressive caching is safe.
- **Cache key:** `tenant:{tenant_id}:odontogram_snapshot:{snapshot_id}`
- **TTL:** 3600 seconds (1 hour)
- **Invalidation:** Never invalidated (snapshots are immutable). Cache expires naturally.

### Database Performance

**Queries executed:** 1 on cache miss (snapshot fetch with user JOIN).

**Indexes required:**
- `odontogram_snapshots.(patient_id, id)` — Composite index for ownership lookup (or covered by PK + `idx_odontogram_snapshots_patient`).
- `odontogram_snapshots.(patient_id, created_at)` — INDEX (already defined: `idx_odontogram_snapshots_date`).

**N+1 prevention:** Single JOIN to `users` within the snapshot query.

### Pagination

**Pagination:** No — single snapshot returned.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | |
| snapshot_id | Pydantic UUID validator | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Full `snapshot_data` JSONB (complete clinical odontogram data).

**Audit requirement:** All access logged.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor retrieves existing snapshot
   - **Given:** Authenticated doctor, snapshot with 3 conditions exists for patient
   - **When:** GET /api/v1/patients/{patient_id}/odontogram/snapshots/{snapshot_id}
   - **Then:** 200 OK, full snapshot_data returned with all teeth and zones

2. Assistant retrieves snapshot
   - **Given:** Authenticated assistant role
   - **When:** GET snapshot
   - **Then:** 200 OK (assistants have read access)

3. Cache hit on second request
   - **Given:** Same snapshot requested within 1 hour
   - **When:** GET snapshot again
   - **Then:** 200 OK served from Redis cache, < 20ms response time

#### Edge Cases
1. Snapshot with no label
   - **Given:** Snapshot created without label
   - **When:** GET snapshot
   - **Then:** 200 OK, label=null in response

2. Snapshot with deactivated creator user
   - **Given:** User who created snapshot has been deactivated
   - **When:** GET snapshot
   - **Then:** 200 OK, created_by returned with available user data

3. Snapshot with linked entities that were later deleted
   - **Given:** Snapshot linked_treatment_plan_id points to a deleted plan
   - **When:** GET snapshot
   - **Then:** 200 OK, linked_treatment_plan_id returned as stored UUID (no live validation)

#### Error Cases
1. Snapshot belongs to different patient
   - **Given:** snapshot_id is valid but belongs to patient_b; URL uses patient_a
   - **When:** GET /api/v1/patients/{patient_a_id}/odontogram/snapshots/{patient_b_snapshot_id}
   - **Then:** 404 Not Found

2. Receptionist access
   - **Given:** Authenticated receptionist role
   - **When:** GET snapshot
   - **Then:** 403 Forbidden

3. Non-existent snapshot_id
   - **Given:** Valid UUID but no matching snapshot
   - **When:** GET snapshot
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** doctor, assistant (pass); receptionist, patient (fail with 403).

**Patients/Entities:** Patient with at least 2 snapshots; snapshot with label; snapshot without label; snapshot with treatment plan link.

### Mocking Strategy

- Redis: Use fakeredis to test cache hit and miss paths.
- Time: Use fixed timestamps for deterministic `created_at` assertions.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Returns full snapshot_data JSONB for valid snapshot_id
- [ ] created_by resolved to full_name + role
- [ ] Cross-patient snapshot access returns 404
- [ ] Snapshot cached in Redis with 1 hour TTL after first fetch
- [ ] Receptionist and patient roles return 403
- [ ] Audit log entry written on every access
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms on cache miss, < 20ms on cache hit)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing all snapshots for a patient (OD-07)
- Comparing two snapshots (OD-08)
- Creating snapshots (OD-05)
- Deleting snapshots (snapshots are permanent)

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
- [x] Input sanitization defined (Pydantic UUID validators)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for snapshot access

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 150ms)
- [x] Caching strategy stated (Redis 1 hour — immutable data)
- [x] DB queries optimized (single JOIN, indexed lookup)
- [x] Pagination applied where needed (N/A — single record)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
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
