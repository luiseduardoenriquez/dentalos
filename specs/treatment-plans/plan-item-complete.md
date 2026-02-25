# TP-07: Complete Treatment Plan Item Spec

---

## Overview

**Feature:** Mark a treatment plan item as completed after the procedure has been performed. Links the item to the recorded clinical procedure (CR-12), records the actual cost, and automatically transitions the plan to 'completed' status if all items are done or cancelled.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** TP-05 (plan-item-add.md), TP-06 (plan-item-update.md), CR-12 (procedure-record), TP-04 (plan-update.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only the doctor performing the procedure or clinic_owner can complete an item. The procedure_id (CR-12) must belong to the same patient and tenant.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items/{item_id}/complete
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
| item_id | Yes | uuid | Valid UUID, must belong to plan | Plan item's unique identifier | e5f6a1b2-c3d4-5678-abcd-345678901234 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "procedure_id": "uuid (required) — ID of the recorded procedure from clinical records (CR-12)",
  "actual_cost": "number (optional) — decimal, min 0; defaults to item's estimated_cost if not provided",
  "notes": "string (optional) — max 1000 chars"
}
```

**Example Request:**
```json
{
  "procedure_id": "d4e5f6a1-b2c3-4567-efab-234567890123",
  "actual_cost": 210000.00,
  "notes": "Procedimiento completado sin complicaciones. Material: amalgama GC."
}
```

**Example Request (defaults to estimated cost):**
```json
{
  "procedure_id": "d4e5f6a1-b2c3-4567-efab-234567890123"
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
  "plan_id": "uuid",
  "cups_code": "string",
  "description": "string",
  "tooth_number": "string | null",
  "zone": "string | null",
  "estimated_cost": "number",
  "actual_cost": "number",
  "priority_order": "integer",
  "status": "string (completed)",
  "notes": "string | null",
  "source": "string",
  "procedure_id": "uuid",
  "completed_at": "string (ISO 8601 datetime)",
  "completed_by": "uuid",
  "plan_summary": {
    "status": "string (active | completed)",
    "items_count": "integer",
    "completed_count": "integer",
    "total_cost_estimated": "number",
    "total_cost_actual": "number",
    "progress_pct": "number",
    "auto_completed": "boolean"
  }
}
```

**Example:**
```json
{
  "id": "e5f6a1b2-c3d4-5678-abcd-345678901234",
  "plan_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "cups_code": "906513",
  "description": "Restauracion clase II amalgama diente 36",
  "tooth_number": "36",
  "zone": "posterior_inferior_izquierdo",
  "estimated_cost": 200000.00,
  "actual_cost": 210000.00,
  "priority_order": 1,
  "status": "completed",
  "notes": "Procedimiento completado sin complicaciones. Material: amalgama GC.",
  "source": "odontogram",
  "procedure_id": "d4e5f6a1-b2c3-4567-efab-234567890123",
  "completed_at": "2026-02-24T13:00:00Z",
  "completed_by": "d4e5f6a1-b2c3-4567-efab-234567890123",
  "plan_summary": {
    "status": "completed",
    "items_count": 2,
    "completed_count": 2,
    "total_cost_estimated": 400000.00,
    "total_cost_actual": 410000.00,
    "progress_pct": 100.0,
    "auto_completed": true
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Item is already completed, or plan is in a state that does not allow completions.

**Example:**
```json
{
  "error": "item_already_completed",
  "message": "Este procedimiento ya fue marcado como completado.",
  "details": {
    "completed_at": "2026-02-20T14:00:00Z"
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role not allowed or procedure belongs to a different patient.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para completar este procedimiento."
}
```

#### 404 Not Found
**When:** patient_id, plan_id, item_id, or procedure_id not found in tenant.

**Example:**
```json
{
  "error": "procedure_not_found",
  "message": "El registro clinico del procedimiento no fue encontrado."
}
```

#### 409 Conflict
**When:** Plan is in cancelled or draft status; completing an item requires an active plan.

**Example:**
```json
{
  "error": "plan_not_active",
  "message": "Solo se pueden completar procedimientos de planes activos.",
  "details": {
    "plan_status": "draft"
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
    "actual_cost": ["El costo real no puede ser negativo."],
    "procedure_id": ["El campo procedure_id es obligatorio."]
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

1. Validate input against Pydantic schema (procedure_id required, actual_cost >= 0 if provided).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (must be doctor or clinic_owner).
4. Fetch plan and item; verify both exist and belong to the correct patient and tenant.
5. If item.status = 'completed', return 400 (idempotency protection).
6. If plan.status != 'active', return 409 (items can only be completed on active plans; draft requires activation first).
7. If item.status = 'cancelled', return 400 (cancelled items cannot be completed).
8. Validate procedure_id: fetch clinical procedure record (CR-12) and verify:
   - It exists in the tenant.
   - Its patient_id matches this patient_id.
   - It is not already linked to another plan item (prevent duplicate linking).
9. If `actual_cost` not provided, default to item's `estimated_cost`.
10. Update item: `status = 'completed'`, `procedure_id`, `actual_cost`, `completed_at = now()`, `completed_by = current_user.id`.
11. Recalculate plan progress:
    - `completed_count` = COUNT of items with status = 'completed'.
    - `progress_pct` = completed_count / items_count * 100.
    - `total_cost_actual` = SUM of actual_cost for completed items.
12. Check auto-complete condition: if all items are in status 'completed' or 'cancelled', auto-transition plan to 'completed' status.
13. Update `treatment_plans.updated_at` and `progress_pct`.
14. Write audit log entry (action: update, resource: treatment_plan_item, PHI: yes, notes: "item completed").
15. Write audit log entry for plan status change if auto-completed.
16. Invalidate plan cache.
17. If plan auto-completed, dispatch `treatment_plan.completed` event to RabbitMQ.
18. Return 200 with completed item and updated plan_summary including `auto_completed` flag.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| procedure_id | Valid UUID, required | El procedimiento es obligatorio para completar el item. |
| actual_cost | Decimal >= 0 (if provided) | El costo real no puede ser negativo. |
| notes | max 1000 chars (if provided) | Las notas no pueden superar 1000 caracteres. |

**Business Rules:**

- This endpoint is the ONLY way to set item status to 'completed'; TP-06 explicitly blocks this transition.
- `procedure_id` is mandatory — items cannot be completed without linking to a clinical record. This maintains clinical integrity and the audit trail.
- A procedure record can be linked to at most one plan item (one-to-one relationship enforced by unique constraint on `treatment_plan_items.procedure_id`).
- If actual_cost differs from estimated_cost, the difference is informational (no automatic billing adjustment — billing handled by B-14/B-16 domain).
- Auto-completion of plan: when the last non-cancelled item is completed, the plan transitions to 'completed' status automatically without requiring a separate call to TP-04.
- Only items on `active` plans can be completed; doctors must activate a draft plan (TP-04) before they can complete items.
- `completed_by` is always set server-side from the JWT.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Last item completed — all others cancelled | Plan auto-transitions to completed; auto_completed = true |
| actual_cost = 0.00 (provided explicitly) | Accepted; procedure performed at no charge |
| procedure_id already linked to another item | Return 409 — procedure already associated |
| Plan already completed (all items done) | Attempting to complete a sub-item returns 400 (idempotency) |
| Item in scheduled status | Allowed to complete directly (scheduled → completed) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `treatment_plan_items`: UPDATE — status, procedure_id, actual_cost, completed_at, completed_by, notes
- `treatment_plans`: UPDATE — progress_pct, total_cost_actual, updated_at; optionally status = 'completed'
- `clinical_procedures`: UPDATE — linked_plan_item_id set (back-reference on CR-12 record)

**Example query (SQLAlchemy):**
```python
# Update item
await session.execute(
    update(TreatmentPlanItem)
    .where(TreatmentPlanItem.id == item_id)
    .values(
        status="completed",
        procedure_id=data.procedure_id,
        actual_cost=actual_cost,
        completed_at=datetime.utcnow(),
        completed_by=current_user.id,
        notes=data.notes,
    )
)

# Recalculate plan totals
agg = await session.execute(
    select(
        func.count().filter(TreatmentPlanItem.status == "completed").label("completed_count"),
        func.count().label("total_count"),
        func.sum(TreatmentPlanItem.actual_cost).filter(TreatmentPlanItem.status == "completed").label("total_actual"),
    ).where(TreatmentPlanItem.plan_id == plan_id)
)
row = agg.one()
progress_pct = (row.completed_count / row.total_count) * 100 if row.total_count > 0 else 0
new_status = "completed" if row.completed_count + cancelled_count == row.total_count else plan.status

await session.execute(
    update(TreatmentPlan)
    .where(TreatmentPlan.id == plan_id)
    .values(
        progress_pct=progress_pct,
        total_cost_actual=row.total_actual,
        status=new_status,
        updated_at=datetime.utcnow(),
    )
)
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
| treatment-plans | treatment_plan.item_completed | { tenant_id, patient_id, plan_id, item_id, procedure_id, actual_cost } | After item marked complete |
| treatment-plans | treatment_plan.completed | { tenant_id, patient_id, plan_id, total_cost_actual, completed_by } | When plan auto-transitions to completed |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** update
- **Resource:** treatment_plan_item
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No (downstream handlers may trigger notifications from queue consumer)

---

## Performance

### Expected Response Time
- **Target:** < 250ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on write
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Plan cache invalidated on completion

### Database Performance

**Queries executed:** 4 (plan + item fetch, procedure validation, item update, plan aggregate update — single transaction)

**Indexes required:**
- `treatment_plan_items.(plan_id, status)` — INDEX (progress recalculation aggregate)
- `treatment_plan_items.procedure_id` — UNIQUE INDEX (prevent duplicate procedure linking)
- `clinical_procedures.(id, patient_id)` — INDEX (procedure validation)

**N+1 prevention:** Aggregate counts in single GROUP BY query; no per-item reads.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| procedure_id | Pydantic UUID validator | Path + body parameter |
| actual_cost | Pydantic Decimal validator, min 0 | Prevents negative cost injection |
| notes | Pydantic `strip()` + bleach.clean | Free text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, cups_code, description, notes (clinical completion details), procedure_id (links to clinical record), actual_cost.

**Audit requirement:** All writes logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Complete item with actual_cost
   - **Given:** Doctor, active plan with pending item, valid procedure_id
   - **When:** POST /complete with procedure_id and actual_cost = 210000
   - **Then:** 200 OK, item status = completed, actual_cost = 210000, plan progress recalculated

2. Complete item without actual_cost (defaults to estimated)
   - **Given:** Item with estimated_cost = 200000
   - **When:** POST /complete with only procedure_id
   - **Then:** 200 OK, actual_cost = 200000 (from estimated)

3. Completing last item auto-completes plan
   - **Given:** Active plan with 2 items; first already completed, second being completed now
   - **When:** POST /complete on second item
   - **Then:** 200 OK, plan_summary.status = completed, auto_completed = true, treatment_plan.completed event dispatched

4. Complete scheduled item
   - **Given:** Item with status = scheduled
   - **When:** POST /complete
   - **Then:** 200 OK, item transitions scheduled → completed

#### Edge Cases
1. All remaining items cancelled, last non-cancelled completed
   - **Given:** Plan with 3 items: 2 cancelled, 1 pending
   - **When:** Complete the pending item
   - **Then:** Plan auto-completes, auto_completed = true

2. actual_cost = 0.00
   - **Given:** Procedure performed at no charge
   - **When:** POST with actual_cost = 0.00
   - **Then:** 200 OK, actual_cost = 0.00 stored correctly

#### Error Cases
1. Item already completed
   - **Given:** Item with status = completed
   - **When:** POST /complete again
   - **Then:** 400 item_already_completed

2. Plan in draft status
   - **Given:** Draft plan
   - **When:** POST /complete on item
   - **Then:** 409 plan_not_active

3. procedure_id belongs to different patient
   - **Given:** procedure_id from different patient
   - **When:** POST /complete
   - **Then:** 404 procedure_not_found

4. procedure_id already linked to another item
   - **Given:** procedure_id already used in another plan item
   - **When:** POST /complete with same procedure_id
   - **Then:** 409 Conflict

5. Negative actual_cost
   - **Given:** actual_cost = -1000
   - **When:** POST /complete
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** doctor, clinic_owner

**Patients/Entities:** Active plan with multiple items in various statuses; valid clinical procedure records (CR-12); a plan with only one remaining non-cancelled item.

### Mocking Strategy

- Clinical records (CR-12): Fixture with known procedure_ids and patient links
- RabbitMQ: Mock publish, assert both item_completed and treatment_plan.completed payloads
- Redis cache: fakeredis for invalidation tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Item status set to completed with procedure_id and actual_cost recorded
- [ ] actual_cost defaults to estimated_cost when not provided
- [ ] progress_pct and total_cost_actual correctly recalculated on plan
- [ ] Auto-completion triggers when all items are completed or cancelled
- [ ] treatment_plan.completed event dispatched when plan auto-completes
- [ ] procedure_id validated against patient's clinical records
- [ ] Duplicate procedure_id linking returns 409
- [ ] Draft plan returns 409 (must activate first)
- [ ] Audit log written with PHI flag for item and plan status change
- [ ] Plan cache invalidated
- [ ] All test cases pass
- [ ] Performance targets met (< 250ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- General item status updates (see TP-06 plan-item-update.md)
- Plan status management (see TP-04 plan-update.md)
- Billing/invoicing triggered by procedure completion (B-14/B-16 domain)

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
