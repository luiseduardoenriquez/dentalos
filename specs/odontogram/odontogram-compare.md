# OD-08: Compare Odontogram Snapshots Spec

---

## Overview

**Feature:** Compare two odontogram states side by side and return a structured diff showing exactly what changed between them: conditions added, removed, or changed per tooth and zone. Supports comparing two snapshots, or comparing a snapshot against the current live odontogram state. This is the clinical "before/after" feature used to demonstrate treatment progress and document outcomes.

**Domain:** odontogram

**Priority:** High

**Dependencies:** OD-05 (odontogram-snapshot.md), OD-06 (odontogram-snapshot-get.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Assistants can view history (OD-04) but the clinical comparison report is restricted to doctors. Receptionist and patient roles excluded.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/odontogram/compare
```

**Rate Limiting:**
- 30 requests per minute per user
- Comparison is computationally heavier than a simple read.

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
| snapshot_a | Yes | string | UUID or literal string "current" | The baseline state (earlier/reference). Use "current" to compare a snapshot against the current live state. | snap1a2b-3c4d-5e6f-7890-abcd12345678 |
| snapshot_b | Yes | string | UUID or literal string "current" | The comparison state (later/target). Use "current" to compare a snapshot against the current live state. | current |

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
  "comparison": {
    "state_a": {
      "type": "string (snapshot | current)",
      "snapshot_id": "uuid | null",
      "label": "string | null",
      "captured_at": "string (ISO 8601)",
      "conditions_count": "integer"
    },
    "state_b": {
      "type": "string (snapshot | current)",
      "snapshot_id": "uuid | null",
      "label": "string | null",
      "captured_at": "string (ISO 8601)",
      "conditions_count": "integer"
    },
    "summary": {
      "conditions_added": "integer",
      "conditions_removed": "integer",
      "conditions_changed": "integer",
      "teeth_affected": "integer",
      "net_change": "integer (positive = worsened, negative = improved)"
    },
    "diff": [
      {
        "tooth_number": "integer",
        "zone": "string",
        "change_type": "string (added | removed | changed | unchanged)",
        "state_a_condition": {
          "condition_code": "string | null",
          "condition_color": "string (hex) | null",
          "severity": "string | null"
        },
        "state_b_condition": {
          "condition_code": "string | null",
          "condition_color": "string (hex) | null",
          "severity": "string | null"
        }
      }
    ]
  },
  "generated_at": "string (ISO 8601)"
}
```

**Example:**
```json
{
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "comparison": {
    "state_a": {
      "type": "snapshot",
      "snapshot_id": "snap1a2b-3c4d-5e6f-7890-abcd12345678",
      "label": "Pre-tratamiento ortodoncia",
      "captured_at": "2026-02-10T09:00:00Z",
      "conditions_count": 5
    },
    "state_b": {
      "type": "current",
      "snapshot_id": null,
      "label": null,
      "captured_at": "2026-02-24T14:00:00Z",
      "conditions_count": 3
    },
    "summary": {
      "conditions_added": 1,
      "conditions_removed": 3,
      "conditions_changed": 1,
      "teeth_affected": 3,
      "net_change": -2
    },
    "diff": [
      {
        "tooth_number": 11,
        "zone": "distal",
        "change_type": "changed",
        "state_a_condition": {
          "condition_code": "caries",
          "condition_color": "#D32F2F",
          "severity": "mild"
        },
        "state_b_condition": {
          "condition_code": "restoration",
          "condition_color": "#1565C0",
          "severity": null
        }
      },
      {
        "tooth_number": 36,
        "zone": "oclusal",
        "change_type": "removed",
        "state_a_condition": {
          "condition_code": "caries",
          "condition_color": "#D32F2F",
          "severity": "moderate"
        },
        "state_b_condition": {
          "condition_code": null,
          "condition_color": null,
          "severity": null
        }
      },
      {
        "tooth_number": 47,
        "zone": "mesial",
        "change_type": "added",
        "state_a_condition": {
          "condition_code": null,
          "condition_color": null,
          "severity": null
        },
        "state_b_condition": {
          "condition_code": "caries",
          "condition_color": "#D32F2F",
          "severity": "mild"
        }
      }
    ]
  },
  "generated_at": "2026-02-24T14:05:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Both `snapshot_a` and `snapshot_b` are "current" (comparing current to current is meaningless).

```json
{
  "error": "invalid_comparison",
  "message": "No es posible comparar el estado actual consigo mismo. Proporcione al menos un identificador de instantanea."
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is assistant, receptionist, or patient.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para comparar instantaneas del odontograma."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist, or a provided snapshot UUID does not belong to this patient.

```json
{
  "error": "not_found",
  "message": "Una o mas instantaneas no fueron encontradas para este paciente."
}
```

#### 422 Unprocessable Entity
**When:** `snapshot_a` or `snapshot_b` is neither a valid UUID nor the literal string "current".

```json
{
  "error": "validation_failed",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "snapshot_a": ["Debe ser un UUID valido o el valor 'current'."],
    "snapshot_b": ["Debe ser un UUID valido o el valor 'current'."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected failure during state retrieval or diff computation.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` UUID format and query parameters.
2. Reject if both `snapshot_a` and `snapshot_b` are "current" (400 Bad Request).
3. Validate that non-"current" parameters are valid UUID v4 strings.
4. Resolve tenant from JWT; check user role is in `[clinic_owner, doctor]`.
5. Verify patient exists; return 404 if not.
6. Resolve State A:
   - If `snapshot_a = "current"`: fetch live odontogram state (same logic as OD-01, including Redis cache check).
   - If `snapshot_a` is a UUID: fetch `odontogram_snapshots` WHERE `id = :snapshot_a AND patient_id = :patient_id`. Return 404 if not found.
7. Resolve State B:
   - If `snapshot_b = "current"`: fetch live odontogram state (can reuse cached result from step 6 if also current).
   - If `snapshot_b` is a UUID: fetch snapshot same as step 6.
8. Normalize both states into the same zone-keyed structure: `{tooth_number: {zone: {condition_code, severity}}}`.
9. Compute diff by iterating over the union of all tooth/zone pairs across both states:
   - `added`: zone has null in A but non-null in B.
   - `removed`: zone has non-null in A but null in B.
   - `changed`: both A and B have conditions but condition_code differs, OR same condition_code but severity differs.
   - `unchanged`: same condition_code and severity in both (excluded from diff array unless frontend needs it — only include changes).
10. Enrich diff entries with `condition_color` from in-memory conditions catalog.
11. Compute summary: count added/removed/changed; count unique teeth affected; compute net_change (added - removed).
12. Write audit log (action: read, resource: odontogram_comparison, PHI: yes).
13. Return 200 with full comparison result.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| snapshot_a | Must be valid UUID v4 OR literal "current" | Debe ser un UUID valido o el valor 'current'. |
| snapshot_b | Must be valid UUID v4 OR literal "current" | Debe ser un UUID valido o el valor 'current'. |
| snapshot_a, snapshot_b | Cannot both be "current" | No es posible comparar el estado actual consigo mismo. |
| snapshot_a UUID | Must belong to specified patient_id | Instantanea no encontrada o no pertenece al paciente especificado. |
| snapshot_b UUID | Must belong to specified patient_id | Instantanea no encontrada o no pertenece al paciente especificado. |

**Business Rules:**

- The diff array only includes zones with `change_type` of `added`, `removed`, or `changed`. Unchanged zones are excluded to keep the response lean.
- `net_change` is a signed integer: negative means improvement (fewer conditions), positive means deterioration (more conditions). Equal is zero.
- The `diff` is ordered by `tooth_number ASC, zone ASC` for deterministic, predictable output.
- When `snapshot_a` is a UUID and `snapshot_b` is "current", this represents the most common clinical use case: comparing the pre-treatment snapshot to today's state.
- Both states' `captured_at` timestamps are included for temporal context in the UI.
- Comparison is computed in memory (Python) after fetching both states; no complex SQL diff query.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Both snapshots have identical states | diff=[], summary all zeros, net_change=0 |
| State A has more teeth than State B (dentition changed) | All teeth from both states included; missing teeth treated as all-null zones |
| snapshot_a is chronologically AFTER snapshot_b | Valid comparison; no temporal ordering enforced by API — UI labels accordingly |
| Very large diff (all 192 zones changed) | Full diff returned; no pagination (max 192 items is manageable) |
| One snapshot from adult dentition, one from pediatric | Diff includes teeth from both sets; change_type=added/removed for the entire tooth's zones |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint).

### Cache Operations

**Cache keys affected:**
- Comparison results are NOT cached (too many permutations of snapshot_a / snapshot_b pairs).
- Live odontogram state (if "current" used): served from `tenant:{tenant_id}:odontogram:{patient_id}` Redis cache if available (reuses OD-01 cache).

**Cache TTL:** N/A for comparison results.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** read
- **Resource:** odontogram_comparison
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 400ms (snapshot pair comparison)
- **Maximum acceptable:** < 900ms

### Caching Strategy
- **Strategy:** No caching for comparison results. However, individual states are served from cache when available (OD-01 Redis cache for live state, OD-06 Redis cache for snapshots).
- **Cache key:** N/A for comparison output.
- **TTL:** N/A.
- **Invalidation:** N/A.

### Database Performance

**Queries executed:** 1–3 (patient check, 0–2 snapshot fetches depending on how many UUIDs provided vs "current"). Live state served from Redis cache if warm.

**Indexes required:**
- `odontogram_snapshots.(id, patient_id)` — for ownership-safe snapshot retrieval.
- `odontogram_conditions.patient_id` — for live state fetch (already defined).

**N+1 prevention:** Both states fetched independently; diff computed in memory. No per-tooth queries.

### Pagination

**Pagination:** No — diff array is at most 192 items (32 teeth × 6 zones), well within a single response.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | |
| snapshot_a | Custom validator: UUID v4 OR literal "current" | Prevents injection via snapshot ID |
| snapshot_b | Custom validator: UUID v4 OR literal "current" | Prevents injection via snapshot ID |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Diff contains clinical condition data. `notes` field from conditions is intentionally excluded from comparison output (only condition_code and severity diffed) to reduce PHI in the comparison response.

**Audit requirement:** All access logged.

---

## Testing

### Test Cases

#### Happy Path
1. Compare snapshot to current state
   - **Given:** Authenticated doctor, snapshot S1 from 2 weeks ago, current state has 2 fewer conditions and 1 new condition
   - **When:** GET /api/v1/patients/{patient_id}/odontogram/compare?snapshot_a={S1_id}&snapshot_b=current
   - **Then:** 200 OK, diff shows 2 removed + 1 added, summary correctly computed, net_change=-1

2. Compare two snapshots
   - **Given:** Two snapshots S1 (older) and S2 (newer) for same patient
   - **When:** GET with snapshot_a={S1_id}&snapshot_b={S2_id}
   - **Then:** 200 OK, diff reflects changes between S1 and S2

3. Compare identical states
   - **Given:** Two snapshots created at same moment with same conditions
   - **When:** GET compare
   - **Then:** 200 OK, diff=[], all summary fields=0, net_change=0

#### Edge Cases
1. Compare snapshots from different dentition periods
   - **Given:** S1 was pediatric dentition, S2 is adult dentition
   - **When:** GET compare
   - **Then:** 200 OK, all pediatric zones show removed, all adult zones with conditions show added

2. Compare with reversed chronological order (newer as A, older as B)
   - **Given:** snapshot_a is more recent than snapshot_b
   - **When:** GET compare
   - **Then:** 200 OK with valid diff; temporal ordering not enforced

3. All zones changed (maximum diff)
   - **Given:** All 192 zones differ between A and B
   - **When:** GET compare
   - **Then:** 200 OK with all 192 diff items, no truncation

#### Error Cases
1. Both parameters are "current"
   - **Given:** snapshot_a=current&snapshot_b=current
   - **When:** GET compare
   - **Then:** 400 Bad Request with Spanish error message

2. snapshot_a UUID belongs to different patient
   - **Given:** snapshot_a is a snapshot from patient_b, URL uses patient_a
   - **When:** GET compare
   - **Then:** 404 Not Found

3. Assistant attempts comparison
   - **Given:** Authenticated assistant role
   - **When:** GET compare
   - **Then:** 403 Forbidden

4. Invalid snapshot_a value (not UUID or "current")
   - **Given:** snapshot_a="yesterday"
   - **When:** GET compare
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** doctor, clinic_owner (pass); assistant, receptionist, patient (fail with 403).

**Patients/Entities:** Patient with at least 2 snapshots at different states. Pre-computed expected diffs for assertion.

### Mocking Strategy

- Redis: Use fakeredis; verify live state served from cache when snapshot_b=current.
- Conditions catalog: In-memory fixture for color hex lookups.
- Time: Fixed timestamps for deterministic `generated_at` assertions.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Comparison between two snapshot UUIDs returns correct diff
- [ ] Comparison with "current" fetches live state (with cache reuse)
- [ ] diff array contains only changed zones (added/removed/changed)
- [ ] summary fields (conditions_added, removed, changed, net_change) correctly computed
- [ ] Both states' metadata (type, label, captured_at, conditions_count) included
- [ ] Both snapshot_a and snapshot_b = "current" returns 400 with Spanish error
- [ ] Cross-patient snapshot access returns 404
- [ ] Assistant role returns 403
- [ ] Audit log entry written on every access
- [ ] All test cases pass
- [ ] Performance targets met (< 400ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Rendering before/after views (frontend concern)
- Exporting comparison as PDF (future feature)
- Comparing more than two states (multi-state comparison)
- Semantic comparison (e.g., "total caries burden improved by 40%") — analytics domain

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
- [x] Input sanitization defined (custom UUID-or-current validator)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical comparison access

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 400ms)
- [x] Caching strategy stated (reuses OD-01 cache for live state)
- [x] DB queries optimized (max 2 snapshot fetches + 1 patient check)
- [x] Pagination applied where needed (N/A — max 192 diff items)

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
