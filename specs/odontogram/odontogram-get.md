# OD-01: Get Odontogram Spec

---

## Overview

**Feature:** Retrieve the current odontogram state for a patient, returning all teeth with their zone conditions, rendering mode from tenant settings, and patient dentition type. This is the primary read endpoint powering both classic (grid) and anatomic (arch) rendering modes.

**Domain:** odontogram

**Priority:** High

**Dependencies:** P-01 (patient-get.md), T-06 (tenant-settings.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist is read-only; no write access granted from this endpoint.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/odontogram
```

**Rate Limiting:**
- 120 requests per minute per user
- Higher limit justified: this is polled frequently during active examination sessions.

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
  "patient_id": "uuid",
  "odontogram_id": "uuid",
  "dentition_type": "string (adult | pediatric | mixed)",
  "rendering_mode": "string (classic | anatomic)",
  "teeth": [
    {
      "tooth_number": "integer (FDI notation)",
      "zones": {
        "mesial": {
          "condition_id": "uuid | null",
          "condition_code": "string | null",
          "condition_color": "string (hex) | null",
          "notes": "string | null",
          "severity": "string | null",
          "history_count": "integer",
          "last_updated": "string (ISO 8601) | null",
          "last_updated_by": "uuid | null"
        },
        "distal": { "...same structure..." },
        "vestibular": { "...same structure..." },
        "lingual": { "...same structure..." },
        "oclusal": { "...same structure..." },
        "root": { "...same structure..." }
      }
    }
  ],
  "total_conditions": "integer",
  "last_modified": "string (ISO 8601) | null",
  "generated_at": "string (ISO 8601)"
}
```

**Example:**
```json
{
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "odontogram_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "dentition_type": "adult",
  "rendering_mode": "classic",
  "teeth": [
    {
      "tooth_number": 11,
      "zones": {
        "mesial": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        },
        "distal": {
          "condition_id": "c1d2e3f4-a5b6-7890-abcd-123456789abc",
          "condition_code": "caries",
          "condition_color": "#D32F2F",
          "notes": "Caries incipiente detectada en revision",
          "severity": "mild",
          "history_count": 1,
          "last_updated": "2026-02-20T10:30:00Z",
          "last_updated_by": "d4e5f6a7-b1c2-7890-abcd-ef1234567890"
        },
        "vestibular": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        },
        "lingual": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        },
        "oclusal": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        },
        "root": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        }
      }
    },
    {
      "tooth_number": 36,
      "zones": {
        "mesial": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        },
        "distal": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        },
        "vestibular": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        },
        "lingual": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        },
        "oclusal": {
          "condition_id": "e5f6a7b8-c1d2-7890-abcd-234567890abc",
          "condition_code": "restoration",
          "condition_color": "#1565C0",
          "notes": null,
          "severity": null,
          "history_count": 2,
          "last_updated": "2026-01-15T09:00:00Z",
          "last_updated_by": "d4e5f6a7-b1c2-7890-abcd-ef1234567890"
        },
        "root": {
          "condition_id": null,
          "condition_code": null,
          "condition_color": null,
          "notes": null,
          "severity": null,
          "history_count": 0,
          "last_updated": null,
          "last_updated_by": null
        }
      }
    }
  ],
  "total_conditions": 2,
  "last_modified": "2026-02-20T10:30:00Z",
  "generated_at": "2026-02-24T14:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Authenticated user's role is not in the allowed list.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver el odontograma de este paciente."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist in the tenant, or the patient has no `odontogram_states` row.

```json
{
  "error": "not_found",
  "message": "Paciente no encontrado o sin odontograma inicializado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure during odontogram query.

---

## Business Logic

**Step-by-step process:**

1. Validate `patient_id` is a valid UUID v4 format.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role is in `[clinic_owner, doctor, assistant, receptionist]`.
4. Check Redis cache key `tenant:{tenant_id}:odontogram:{patient_id}`. If HIT, return cached response immediately.
5. Verify patient exists in tenant schema (`SELECT id FROM patients WHERE id = :patient_id`). If not found, return 404.
6. Fetch `odontogram_states` row for the patient. If not found, return 404.
7. Read `odontogram_mode` from tenant `settings` JSONB (`public.tenants.settings->>'odontogram_mode'`, cached). Default to `classic`.
8. Execute single JOIN query to fetch all conditions for the patient:
   ```sql
   SELECT oc.*, COUNT(oh.id) AS history_count
   FROM odontogram_conditions oc
   LEFT JOIN odontogram_history oh ON oh.patient_id = oc.patient_id
     AND oh.tooth_number = oc.tooth_number AND oh.zone = oc.zone
   WHERE oc.patient_id = :patient_id
   GROUP BY oc.id
   ```
9. Determine the complete tooth set based on `dentition_type`:
   - `adult`: teeth 11–18, 21–28, 31–38, 41–48 (32 teeth total).
   - `pediatric`: teeth 51–55, 61–65, 71–75, 81–85 (20 teeth total).
   - `mixed`: both adult and pediatric sets (52 teeth displayed; UI groups by eruption status).
10. Build response: for each tooth in the expected set, for each of 6 zones (`mesial`, `distal`, `vestibular`, `lingual`, `oclusal`, `root`), populate condition data from query results or null defaults.
11. Enrich each non-null condition with `condition_color` from in-memory conditions catalog.
12. Calculate `total_conditions` (count of non-null condition zones) and `last_modified` (MAX updated_at across all conditions).
13. Write response to Redis cache: key `tenant:{tenant_id}:odontogram:{patient_id}`, TTL 300 seconds (5 minutes).
14. Write audit log entry (action: read, resource: odontogram, PHI: yes).
15. Return 200 with full odontogram response.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |

**Business Rules:**

- Zones with no recorded condition return all fields as `null` (not omitted); this allows the frontend to render blank zones consistently.
- `rendering_mode` is a tenant-level setting (T-06), not per-patient. The response always includes it so the frontend knows which renderer to activate.
- `history_count` reflects the total number of historical changes for that tooth/zone, not just for the current condition.
- Teeth with no conditions at all are still included in the response array with all-null zones.
- The conditions catalog color mapping is done server-side; the frontend must not hardcode hex colors.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient exists but has zero conditions recorded | Return full tooth structure with all-null zones; `total_conditions = 0`. |
| Patient's `odontogram_states` row is missing (data integrity issue) | Return 404 with clear message. |
| Tenant setting `odontogram_mode` is missing from JSONB | Default to `"classic"`. |
| Mixed dentition: both adult and pediatric teeth shown | Return all 52 teeth grouped; UI handles rendering separation. |
| Cache hit with stale data (race condition) | Acceptable: Redis TTL is 5 min; OD-02 and OD-11 invalidate on write. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only endpoint).

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:odontogram:{patient_id}`: SET — full odontogram response, TTL 300s.
- `tenant:{tenant_id}:tenant_settings`: READ — for `odontogram_mode` (separate key, cached 300s).

**Cache TTL:** 300 seconds (5 minutes) for odontogram data.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

- **Action:** read
- **Resource:** odontogram
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms (including cache miss path)
- **Maximum acceptable:** < 800ms

### Caching Strategy
- **Strategy:** Redis cache per patient, tenant-namespaced
- **Cache key:** `tenant:{tenant_id}:odontogram:{patient_id}`
- **TTL:** 300 seconds
- **Invalidation:** Deleted by OD-02 (update condition), OD-03 (remove condition), OD-11 (bulk update), OD-12 (dentition toggle) on any write for this patient.

### Database Performance

**Queries executed:** 3 on cache miss (patient existence check, odontogram_states fetch, conditions JOIN query).

**Indexes required:**
- `odontogram_conditions.patient_id` — INDEX (already defined: `idx_odontogram_conditions_patient`)
- `odontogram_conditions.(patient_id, tooth_number)` — INDEX (already defined: `idx_odontogram_conditions_tooth`)
- `odontogram_history.(patient_id, tooth_number)` — INDEX (already defined: `idx_odontogram_history_tooth`)
- `odontogram_states.patient_id` — UNIQUE (already defined)

**N+1 prevention:** Single JOIN query fetches all conditions and history counts in one round trip. No per-tooth or per-zone queries.

### Pagination

**Pagination:** No — entire odontogram returned in one response (max 52 teeth × 6 zones = 312 zone objects).

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID strings before DB query |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** All zone condition data (tooth conditions are protected health information).

**Audit requirement:** All access logged.

---

## Testing

### Test Cases

#### Happy Path
1. Get odontogram for adult patient with conditions
   - **Given:** Authenticated doctor, patient with dentition_type=adult, 3 conditions recorded across 2 teeth
   - **When:** GET /api/v1/patients/{patient_id}/odontogram
   - **Then:** 200 OK, 32 teeth returned, 3 zones non-null, rendering_mode matches tenant setting

2. Get odontogram for pediatric patient
   - **Given:** Authenticated doctor, patient with dentition_type=pediatric
   - **When:** GET /api/v1/patients/{patient_id}/odontogram
   - **Then:** 200 OK, 20 teeth returned (FDI 51-85)

3. Cache hit path
   - **Given:** Same request made within 5 minutes of previous request
   - **When:** GET /api/v1/patients/{patient_id}/odontogram
   - **Then:** 200 OK returned from Redis cache, no DB query executed, response time < 50ms

4. Receptionist read access
   - **Given:** Authenticated receptionist role
   - **When:** GET /api/v1/patients/{patient_id}/odontogram
   - **Then:** 200 OK (read allowed)

#### Edge Cases
1. Patient with zero conditions
   - **Given:** Patient exists, odontogram_states row exists, no conditions recorded
   - **When:** GET /api/v1/patients/{patient_id}/odontogram
   - **Then:** 200 OK, all 32 teeth returned, all zones null, total_conditions=0

2. Tenant with anatomic rendering mode
   - **Given:** Tenant settings has odontogram_mode="anatomic"
   - **When:** GET /api/v1/patients/{patient_id}/odontogram
   - **Then:** 200 OK, rendering_mode="anatomic" in response

3. Mixed dentition patient
   - **Given:** Patient dentition_type=mixed
   - **When:** GET /api/v1/patients/{patient_id}/odontogram
   - **Then:** 200 OK, both adult and pediatric tooth sets returned

#### Error Cases
1. Patient not found
   - **Given:** Non-existent patient_id
   - **When:** GET /api/v1/patients/{non_existent_uuid}/odontogram
   - **Then:** 404 Not Found

2. Invalid patient_id format
   - **Given:** patient_id = "not-a-uuid"
   - **When:** GET /api/v1/patients/not-a-uuid/odontogram
   - **Then:** 422 Unprocessable Entity

3. Unauthorized role
   - **Given:** Authenticated user with patient role
   - **When:** GET /api/v1/patients/{patient_id}/odontogram
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant, receptionist (all should pass), patient role (should fail with 403).

**Patients/Entities:** Patient with adult dentition and at least 3 conditions; patient with pediatric dentition; patient with mixed dentition; patient with zero conditions.

### Mocking Strategy

- Redis: Use fakeredis to test both cache hit and cache miss paths.
- Tenant settings: Fixture with both `classic` and `anatomic` modes.
- Conditions catalog: In-memory fixture with all 12 condition codes and colors.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Returns 32 teeth for adult patients and 20 for pediatric
- [ ] All 6 zones returned per tooth, null-filled when no condition
- [ ] `rendering_mode` correctly reflects tenant setting T-06
- [ ] Redis cache populated on first request and served on subsequent requests within 5 min
- [ ] Cache invalidated after any write operation (OD-02, OD-03, OD-11, OD-12)
- [ ] Response time < 300ms on cache miss, < 50ms on cache hit
- [ ] Audit log entry written on every access
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Rendering the odontogram UI (frontend concern)
- Voice-to-odontogram parsing (V-01 through V-05)
- Treatment plan tooth mapping
- Photo or X-ray retrieval (OD-10 handles per-tooth detail)

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
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 300ms)
- [x] Caching strategy stated (tenant-namespaced Redis, 5 min TTL)
- [x] DB queries optimized (indexes listed, single JOIN)
- [x] Pagination applied where needed (N/A — full odontogram returned)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A — no jobs dispatched)

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
