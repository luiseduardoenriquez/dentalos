# TP-04: Update Treatment Plan Spec

---

## Overview

**Feature:** Update treatment plan metadata (title, description, diagnoses, priority, estimated duration) and manage status transitions. Enforces strict status-transition rules and prevents modification of approved plan items.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** TP-01 (plan-create.md), TP-02 (plan-get.md), DS-01 (digital-signatures), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** clinic_owner may override certain restrictions (e.g., cancelling an active plan). Assistants and receptionists cannot update plan metadata or status.

---

## Endpoint

```
PUT /api/v1/patients/{patient_id}/treatment-plans/{plan_id}
```

**Rate Limiting:**
- 30 requests per minute per user

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
| patient_id | Yes | uuid | Valid UUID, must belong to tenant | Patient's unique identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| plan_id | Yes | uuid | Valid UUID, must belong to patient | Treatment plan's unique identifier | b2c3d4e5-f6a7-8901-bcde-f12345678901 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "title": "string (optional) — max 200 chars",
  "description": "string (optional) — max 2000 chars, send null to clear",
  "diagnoses": "string[] (optional) — list of CIE-10 codes, max 20 items",
  "priority": "string (optional) — enum: high, medium, low",
  "estimated_duration_days": "integer (optional) — min 1, max 3650, send null to clear",
  "status": "string (optional) — enum: active, completed, cancelled — see transition rules"
}
```

**Example Request (metadata update):**
```json
{
  "title": "Plan integral actualizado",
  "priority": "high",
  "diagnoses": ["K02.1", "K05.1", "K08.2"]
}
```

**Example Request (status transition — activate plan):**
```json
{
  "status": "active"
}
```

**Example Request (cancel plan):**
```json
{
  "status": "cancelled"
}
```

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
  "priority": "string",
  "estimated_duration_days": "integer | null",
  "status": "string",
  "items_count": "integer",
  "completed_count": "integer",
  "total_cost_estimated": "number",
  "progress_pct": "number",
  "approval_status": "string",
  "quotation_id": "uuid | null",
  "updated_by": "uuid",
  "updated_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Plan integral actualizado",
  "description": "Plan completo para restaurar sectores posteriores.",
  "diagnoses": ["K02.1", "K05.1", "K08.2"],
  "priority": "high",
  "estimated_duration_days": 90,
  "status": "draft",
  "items_count": 3,
  "completed_count": 0,
  "total_cost_estimated": 850000.00,
  "progress_pct": 0.0,
  "approval_status": "pending_approval",
  "quotation_id": null,
  "updated_by": "d4e5f6a1-b2c3-4567-efab-234567890123",
  "updated_at": "2026-02-24T11:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or invalid status transition attempted.

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "No es posible cambiar el estado de 'completed' a 'draft'.",
  "details": {
    "current_status": "completed",
    "requested_status": "draft",
    "allowed_transitions": []
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is assistant or receptionist, or attempting to modify an approved plan's items.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para actualizar planes de tratamiento."
}
```

#### 404 Not Found
**When:** patient_id or plan_id does not exist in the tenant.

**Example:**
```json
{
  "error": "plan_not_found",
  "message": "Plan de tratamiento no encontrado."
}
```

#### 409 Conflict
**When:** Attempting to transition to active with no items, or complete a plan with pending items.

**Example:**
```json
{
  "error": "transition_not_allowed",
  "message": "El plan debe tener al menos un procedimiento para ser activado.",
  "details": {
    "items_count": 0
  }
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "priority": ["La prioridad no es valida. Opciones: high, medium, low."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (must be doctor or clinic_owner).
4. Fetch current plan state including items_count, current status, and approval_status.
5. If plan not found, return 404.
6. If `status` field is provided, validate the transition:
   - `draft → active`: allowed if items_count >= 1; blocked if items_count = 0 (return 409).
   - `active → completed`: allowed only if all items are in status completed or cancelled (no pending/scheduled); blocked otherwise (return 409).
   - `any → cancelled`: always allowed for clinic_owner; for doctor, allowed on draft and active plans only.
   - `completed → any`: never allowed; return 400 invalid_status_transition.
   - `cancelled → any`: never allowed; return 400 invalid_status_transition.
7. If plan is `approved` (approval_status = 'approved') and items would be affected, block modification with 403. Metadata updates (title, description, priority, estimated_duration_days) are still allowed on approved plans.
8. Apply PATCH-style update: only fields provided in the request body are updated; omitted fields retain their current values.
9. Normalize diagnoses (deduplicate, uppercase).
10. Update `updated_by` to current user ID and `updated_at` to now.
11. Write audit log entry (action: update, resource: treatment_plan, PHI: yes).
12. Invalidate plan cache and list cache.
13. If status changed, dispatch `treatment_plan.status_changed` event to RabbitMQ.
14. Return 200 with updated plan summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| title | 1-200 chars (if provided) | El titulo no puede superar 200 caracteres. |
| description | max 2000 chars (if provided) | La descripcion no puede superar 2000 caracteres. |
| diagnoses | max 20 items, valid CIE-10 format (if provided) | Codigo CIE-10 no valido. |
| priority | Must be one of: high, medium, low (if provided) | La prioridad no es valida. |
| estimated_duration_days | Integer 1-3650 or null (if provided) | La duracion estimada debe ser entre 1 y 3650 dias. |
| status | Must be a valid forward transition from current status | Transicion de estado no valida. |

**Business Rules:**

- Status transitions follow a strict directed graph: `draft → active → completed`; `any → cancelled` (except from completed or cancelled).
- Completed and cancelled are terminal states — no further status transitions allowed.
- An approved plan (approval_status = 'approved') may still have its metadata updated (title, description, priority, diagnoses), but its items cannot be added, removed, or modified without clinic_owner override.
- Only provided fields are updated (PUT acts as PATCH to avoid overwriting unrelated fields accidentally).
- `updated_by` is always set server-side from JWT.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Transition to active with 0 items | 409 Conflict — cannot activate empty plan |
| Transition to completed with 1 pending item | 409 Conflict — all items must be done or cancelled |
| Transition to completed with all items cancelled (0 completed) | Allowed — edge case of full-cancelled plan; status = completed |
| Cancel an already-cancelled plan | 400 invalid_status_transition (terminal state) |
| Update only priority on approved plan | 200 OK — metadata updates allowed on approved plans |
| Empty body sent | 422 — at least one field required |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `treatment_plans`: UPDATE — metadata and/or status fields

**Example query (SQLAlchemy):**
```python
stmt = (
    update(TreatmentPlan)
    .where(TreatmentPlan.id == plan_id)
    .where(TreatmentPlan.patient_id == patient_id)
    .values(
        title=data.title or plan.title,
        priority=data.priority or plan.priority,
        status=new_status,
        updated_by=current_user.id,
        updated_at=datetime.utcnow(),
    )
    .returning(TreatmentPlan)
)
result = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plan:{plan_id}`: DELETE
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plans:list:*`: INVALIDATE

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| treatment-plans | treatment_plan.status_changed | { tenant_id, patient_id, plan_id, old_status, new_status, changed_by } | When status field is updated |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** update
- **Resource:** treatment_plan
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No (status change notifications are handled downstream by the queue consumer)

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on update (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates plan detail cache and list cache on successful update

### Database Performance

**Queries executed:** 2 (fetch current plan, update plan)

**Indexes required:**
- `treatment_plans.(patient_id, id)` — UNIQUE (primary lookup)
- `treatment_plan_items.(plan_id, status)` — INDEX (for completed transition validation)

**N+1 prevention:** Item count and status check done in single aggregate query before update.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| title | Pydantic `strip()` + strip_tags | Prevent XSS |
| description | Pydantic `strip()` + bleach.clean | Free text |
| diagnoses[] | Uppercase strip, regex format | CIE-10 format |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, diagnoses, plan title/description.

**Audit requirement:** All writes logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Update plan title and priority
   - **Given:** Authenticated doctor, plan in draft status
   - **When:** PUT with new title and priority
   - **Then:** 200 OK, title and priority updated, other fields unchanged

2. Activate plan (draft → active)
   - **Given:** Draft plan with 2 items
   - **When:** PUT with status = active
   - **Then:** 200 OK, status = active

3. Cancel active plan
   - **Given:** Active plan
   - **When:** PUT with status = cancelled
   - **Then:** 200 OK, status = cancelled, RabbitMQ event dispatched

4. clinic_owner cancels completed plan (blocked for doctor)
   - **Given:** clinic_owner JWT, completed plan
   - **When:** PUT with status = cancelled
   - **Then:** 400 invalid_status_transition (terminal state, even for owner)

#### Edge Cases
1. Activate plan with 0 items
   - **Given:** Draft plan with no items
   - **When:** PUT with status = active
   - **Then:** 409 Conflict

2. Complete plan with pending item
   - **Given:** Active plan with 1 completed item and 1 pending item
   - **When:** PUT with status = completed
   - **Then:** 409 Conflict

3. Update metadata on approved plan
   - **Given:** Active plan with approval_status = approved
   - **When:** PUT with new title
   - **Then:** 200 OK (metadata update allowed)

#### Error Cases
1. Invalid transition (completed → draft)
   - **Given:** Completed plan
   - **When:** PUT with status = draft
   - **Then:** 400 invalid_status_transition

2. Non-doctor role
   - **Given:** User with assistant role
   - **When:** PUT request
   - **Then:** 403 Forbidden

3. Plan not found
   - **Given:** Non-existent plan_id
   - **When:** PUT request
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** doctor, clinic_owner, assistant (negative), receptionist (negative)

**Patients/Entities:** Draft plan with 0 items; draft plan with 2 items; active plan with mixed item statuses; approved plan; completed plan.

### Mocking Strategy

- RabbitMQ: Mock publish, assert payload on status change
- Redis cache: fakeredis, verify key deletion on update

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Metadata fields update correctly (only provided fields changed)
- [ ] draft → active transition allowed when items_count >= 1
- [ ] draft → active blocked when items_count = 0
- [ ] active → completed blocked when pending/scheduled items exist
- [ ] any → cancelled allowed (except completed/cancelled terminal states)
- [ ] Approved plan metadata updatable; items blocked without clinic_owner override
- [ ] treatment_plan.status_changed event dispatched on status change
- [ ] Plan detail and list caches invalidated
- [ ] Audit log written with PHI flag
- [ ] Non-doctor/owner returns 403
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Adding or modifying plan items (see TP-05, TP-06)
- Patient approval of plan (see TP-08 plan-approve.md)
- Deleting a plan (use cancel status instead; hard deletes not supported)

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
- [x] Pagination applied where needed (N/A)

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
