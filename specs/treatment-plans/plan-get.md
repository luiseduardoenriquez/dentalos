# TP-02: Get Treatment Plan Spec

---

## Overview

**Feature:** Retrieve a single treatment plan by ID, including all items, progress percentage, linked quotation reference, approval status, and patient digital signature information.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** TP-01 (plan-create.md), P-01 (patient-create.md), DS-01 (digital-signatures), B-16 (quotations)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patient role may access this endpoint from the portal (see portal domain spec); in that context, they may only retrieve their own plans.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/treatment-plans/{plan_id}
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

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
| patient_id | Yes | uuid | Valid UUID, must belong to tenant | Patient's unique identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| plan_id | Yes | uuid | Valid UUID, must belong to patient | Treatment plan's unique identifier | b2c3d4e5-f6a7-8901-bcde-f12345678901 |

### Query Parameters

None.

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "title": "string",
  "description": "string | null",
  "diagnoses": "string[]",
  "priority": "string (high | medium | low)",
  "estimated_duration_days": "integer | null",
  "status": "string (draft | active | completed | cancelled)",
  "items_count": "integer",
  "completed_count": "integer",
  "total_cost_estimated": "number (decimal)",
  "total_cost_actual": "number (decimal) | null",
  "progress_pct": "number (0.0 - 100.0)",
  "items": [
    {
      "id": "uuid",
      "cups_code": "string",
      "description": "string",
      "tooth_number": "string | null",
      "zone": "string | null",
      "estimated_cost": "number",
      "actual_cost": "number | null",
      "priority_order": "integer",
      "status": "string (pending | scheduled | completed | cancelled)",
      "notes": "string | null",
      "source": "string (manual | odontogram)",
      "procedure_id": "uuid | null",
      "completed_at": "string (ISO 8601 datetime) | null"
    }
  ],
  "diagnoses_detail": [
    {
      "code": "string",
      "description": "string | null"
    }
  ],
  "approval_status": "string (pending_approval | approved | rejected)",
  "approval": {
    "approved_at": "string (ISO 8601 datetime) | null",
    "signer_name": "string | null",
    "signer_document": "string | null",
    "signature_id": "uuid | null",
    "ip_address": "string | null"
  },
  "quotation_id": "uuid | null",
  "quotation_url": "string | null",
  "created_by": "uuid",
  "created_by_name": "string",
  "created_at": "string (ISO 8601 datetime)",
  "updated_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Plan de tratamiento integral 2026",
  "description": "Plan completo para restaurar sectores posteriores y tratamiento periodontal.",
  "diagnoses": ["K02.1", "K05.1"],
  "priority": "high",
  "estimated_duration_days": 90,
  "status": "active",
  "items_count": 3,
  "completed_count": 1,
  "total_cost_estimated": 850000.00,
  "total_cost_actual": null,
  "progress_pct": 33.33,
  "items": [
    {
      "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
      "cups_code": "906513",
      "description": "Restauracion clase II amalgama diente 36",
      "tooth_number": "36",
      "zone": "posterior_inferior_izquierdo",
      "estimated_cost": 200000.00,
      "actual_cost": 200000.00,
      "priority_order": 1,
      "status": "completed",
      "notes": null,
      "source": "odontogram",
      "procedure_id": "d4e5f6a1-b2c3-4567-efab-234567890123",
      "completed_at": "2026-02-20T14:00:00Z"
    },
    {
      "id": "e5f6a1b2-c3d4-5678-abcd-345678901234",
      "cups_code": "906601",
      "description": "Detartraje supragingival",
      "tooth_number": null,
      "zone": "full_mouth",
      "estimated_cost": 150000.00,
      "actual_cost": null,
      "priority_order": 2,
      "status": "scheduled",
      "notes": "Cita agendada para 2026-03-01",
      "source": "manual",
      "procedure_id": null,
      "completed_at": null
    }
  ],
  "diagnoses_detail": [
    { "code": "K02.1", "description": "Caries de la dentina" },
    { "code": "K05.1", "description": "Periodontitis cronica" }
  ],
  "approval_status": "approved",
  "approval": {
    "approved_at": "2026-02-15T09:30:00Z",
    "signer_name": "Maria Garcia Lopez",
    "signer_document": "1020304050",
    "signature_id": "f6a1b2c3-d4e5-6789-abcd-456789012345",
    "ip_address": "192.168.1.10"
  },
  "quotation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "quotation_url": "/api/v1/billing/quotations/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_by": "d4e5f6a1-b2c3-4567-efab-234567890123",
  "created_by_name": "Dr. Carlos Ruiz",
  "created_at": "2026-02-14T10:00:00Z",
  "updated_at": "2026-02-20T14:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not allowed, or patient role attempting to access another patient's plan.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver este plan de tratamiento."
}
```

#### 404 Not Found
**When:** patient_id or plan_id does not exist in the tenant, or plan does not belong to the given patient.

**Example:**
```json
{
  "error": "plan_not_found",
  "message": "Plan de tratamiento no encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate URL parameters (valid UUIDs).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (must be doctor, clinic_owner, assistant, or receptionist).
4. Verify `patient_id` exists and belongs to the tenant.
5. Fetch `treatment_plan` by `plan_id` WHERE `patient_id` matches and `tenant scope` is correct.
6. If not found, return 404.
7. Fetch all `treatment_plan_items` for the plan in a single query, ordered by `priority_order`.
8. Fetch approval record from `digital_signatures` WHERE `resource_type = 'treatment_plan'` AND `resource_id = plan_id` (if plan has been approved).
9. Calculate `progress_pct` = (completed_count / items_count) * 100; if items_count = 0, progress_pct = 0.
10. Calculate `total_cost_actual` = SUM of `actual_cost` for completed items (null if no items completed).
11. Look up `created_by_name` from users table via JOIN.
12. Compose and return 200 response.
13. Write audit log entry (action: read, resource: treatment_plan, PHI: yes).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID format | Identificador de paciente no valido. |
| plan_id | Valid UUID format | Identificador de plan no valido. |

**Business Rules:**

- A plan belongs to a patient; plan_id must be verified against patient_id to prevent cross-patient data leakage.
- `progress_pct` is computed on read (not stored) to stay accurate: `(items with status='completed') / total_items * 100`. If items_count = 0, returns 0.0.
- `total_cost_actual` is the sum of `actual_cost` for completed items only. If no items are completed, returns null.
- `approval.ip_address` is only included in the response for clinic staff (doctor, clinic_owner); omitted or masked for patient-role access.
- The `quotation_url` field is only populated if a quotation has been generated (quotation_id is not null).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Plan has 0 items | items = [], items_count = 0, progress_pct = 0.0 |
| Plan not yet approved | approval_status = "pending_approval", approval fields all null |
| All items cancelled | progress_pct = 0.0 (cancelled items do not count as completed) |
| Quotation not yet generated | quotation_id = null, quotation_url = null |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plan:{plan_id}`: SET on first read, return from cache on subsequent reads.

**Cache TTL:** 300 seconds (5 minutes)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** treatment_plan
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (cache hit)
- **Maximum acceptable:** < 300ms (cache miss)

### Caching Strategy
- **Strategy:** Redis cache with tenant-namespaced key
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:treatment_plan:{plan_id}`
- **TTL:** 300 seconds
- **Invalidation:** On any write to treatment_plan or treatment_plan_items for this plan_id (TP-04, TP-05, TP-06, TP-07, TP-08)

### Database Performance

**Queries executed:** 3 (plan fetch with JOIN on users, items fetch, digital_signature fetch)

**Indexes required:**
- `treatment_plans.(patient_id, id)` — UNIQUE (primary lookup)
- `treatment_plan_items.(plan_id, priority_order)` — INDEX (ordered items fetch)
- `digital_signatures.(resource_type, resource_id)` — INDEX (approval lookup)

**N+1 prevention:** Items fetched in single query via plan_id filter; user name resolved via JOIN on plan query.

### Pagination

**Pagination:** No (plan items returned in full; plans are expected to have < 50 items)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Path parameter |
| plan_id | Pydantic UUID validator | Path parameter |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, diagnoses, signer_name, signer_document, approval.ip_address (staff only), all item descriptions and procedure links.

**Audit requirement:** All access logged.

---

## Testing

### Test Cases

#### Happy Path
1. Get approved, active plan with completed and pending items
   - **Given:** Authenticated doctor, plan exists with 3 items (1 completed, 2 pending), plan is approved
   - **When:** GET /api/v1/patients/{patient_id}/treatment-plans/{plan_id}
   - **Then:** 200 OK, progress_pct = 33.33, approval fields populated, all items returned

2. Get draft plan with no items
   - **Given:** Plan in draft status, 0 items
   - **When:** GET request
   - **Then:** 200 OK, items = [], items_count = 0, progress_pct = 0.0, approval_status = pending_approval

3. Get plan with linked quotation
   - **Given:** Plan has quotation_id set
   - **When:** GET request
   - **Then:** 200 OK, quotation_id and quotation_url populated

#### Edge Cases
1. All items cancelled
   - **Given:** Plan with 3 items, all status = cancelled
   - **When:** GET request
   - **Then:** progress_pct = 0.0, completed_count = 0

2. Cache hit
   - **Given:** Plan was recently fetched (cache populated)
   - **When:** GET request again
   - **Then:** Response served from Redis in < 100ms

#### Error Cases
1. plan_id not found
   - **Given:** Non-existent plan_id
   - **When:** GET request
   - **Then:** 404 Not Found

2. plan_id belongs to a different patient
   - **Given:** Valid plan_id but wrong patient_id in URL
   - **When:** GET request
   - **Then:** 404 Not Found (no cross-patient leakage)

3. Receptionist cannot see another tenant's plan
   - **Given:** JWT from tenant A, plan_id from tenant B
   - **When:** GET request
   - **Then:** 404 Not Found (tenant isolation)

### Test Data Requirements

**Users:** doctor, clinic_owner, assistant, receptionist (all allowed)

**Patients/Entities:** Patient with a treatment plan containing various item statuses; approved plan with digital signature record; plan with linked quotation.

### Mocking Strategy

- Redis cache: fakeredis for cache hit/miss tests
- digital_signatures: Fixture with known approval record

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] 200 OK returned with full plan including all items
- [ ] progress_pct correctly computed as completed_count / items_count * 100
- [ ] total_cost_actual computed from completed items' actual_cost
- [ ] Approval fields populated when plan is approved
- [ ] Plan belonging to different patient returns 404
- [ ] ip_address masked for non-staff roles
- [ ] Response cached with 5-minute TTL
- [ ] Audit log entry written on every read (PHI)
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms cache, < 300ms cold)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing all plans for a patient (see TP-03 plan-list.md)
- Updating plan metadata (see TP-04 plan-update.md)
- PDF generation (see TP-09 plan-pdf.md)

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
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A — items < 50)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

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
