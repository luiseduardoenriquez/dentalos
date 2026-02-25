# TP-06: Update Treatment Plan Item Spec

---

## Overview

**Feature:** Update the details of an existing treatment plan item, including description, estimated cost, priority order (for drag-and-drop reordering), item status progression, and notes. Recalculates plan total on cost changes.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** TP-05 (plan-item-add.md), TP-01 (plan-create.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Approved plan items are read-only for doctors; clinic_owner may still update them. Use TP-07 for marking items as completed (has its own endpoint to enforce procedure linking).

---

## Endpoint

```
PUT /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items/{item_id}
```

**Rate Limiting:**
- 60 requests per minute per user (reordering may trigger multiple rapid calls)

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
  "description": "string (optional) — max 500 chars",
  "estimated_cost": "number (optional) — decimal, min 0",
  "priority_order": "integer (optional) — min 1; triggers reorder of other items",
  "status": "string (optional) — enum: pending, scheduled, cancelled — see rules (completed via TP-07 only)",
  "notes": "string (optional) — max 1000 chars, send null to clear"
}
```

**Example Request (update cost and notes):**
```json
{
  "estimated_cost": 220000.00,
  "notes": "Precio ajustado por complejidad del caso"
}
```

**Example Request (reorder item — drag-and-drop):**
```json
{
  "priority_order": 1
}
```

**Example Request (schedule item):**
```json
{
  "status": "scheduled",
  "notes": "Cita agendada para 2026-03-01"
}
```

**Example Request (cancel item):**
```json
{
  "status": "cancelled",
  "notes": "Paciente rechaza el procedimiento"
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
  "actual_cost": "number | null",
  "priority_order": "integer",
  "status": "string",
  "notes": "string | null",
  "source": "string",
  "price_from_catalog": "boolean",
  "updated_at": "string (ISO 8601 datetime)",
  "plan_summary": {
    "items_count": "integer",
    "completed_count": "integer",
    "total_cost_estimated": "number",
    "progress_pct": "number"
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
  "estimated_cost": 220000.00,
  "actual_cost": null,
  "priority_order": 2,
  "status": "scheduled",
  "notes": "Cita agendada para 2026-03-01",
  "source": "odontogram",
  "price_from_catalog": true,
  "updated_at": "2026-02-24T12:00:00Z",
  "plan_summary": {
    "items_count": 3,
    "completed_count": 0,
    "total_cost_estimated": 620000.00,
    "progress_pct": 0.0
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Attempting to set status = completed via this endpoint (must use TP-07), or invalid status transition.

**Example:**
```json
{
  "error": "invalid_status",
  "message": "Para marcar un procedimiento como completado use el endpoint de completar procedimiento.",
  "details": {
    "use_endpoint": "POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items/{item_id}/complete"
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Doctor attempting to update item on an approved plan, or role not allowed.

**Example:**
```json
{
  "error": "forbidden",
  "message": "El plan esta aprobado. Solo el propietario de la clinica puede modificar los procedimientos."
}
```

#### 404 Not Found
**When:** patient_id, plan_id, or item_id not found in tenant.

**Example:**
```json
{
  "error": "item_not_found",
  "message": "Procedimiento no encontrado en el plan de tratamiento."
}
```

#### 409 Conflict
**When:** Attempting to modify a completed item.

**Example:**
```json
{
  "error": "item_already_completed",
  "message": "No se puede modificar un procedimiento ya completado."
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
    "estimated_cost": ["El costo estimado no puede ser negativo."],
    "status": ["Estado no valido. Opciones: pending, scheduled, cancelled."]
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
4. Fetch plan (validate exists and belongs to patient) and item (validate exists and belongs to plan).
5. If item status = 'completed', return 409 (cannot modify completed items — use TP-07 context).
6. If `status = 'completed'` is requested in body, return 400 directing to TP-07 endpoint.
7. Validate item status transition:
   - `pending → scheduled`: allowed.
   - `pending → cancelled`: allowed.
   - `scheduled → pending`: allowed (unschedule).
   - `scheduled → cancelled`: allowed.
   - `cancelled → pending`: allowed (reopen).
   - `completed → any`: blocked (409).
8. If plan.approval_status = 'approved' and user is not clinic_owner, return 403.
9. If `priority_order` changes:
   - Fetch all current items ordered by priority_order.
   - Recompute ordering: remove item from current position, insert at new position.
   - Bulk-update priority_order for all affected items in a single transaction.
10. Apply PATCH-style update to item: only provided fields changed.
11. If `estimated_cost` changed: recalculate `total_cost_estimated` on plan (SUM of non-cancelled items).
12. Update `treatment_plans.updated_at`.
13. Write audit log entry (action: update, resource: treatment_plan_item, PHI: yes).
14. Invalidate plan cache.
15. Return 200 with updated item and plan summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| description | 1-500 chars (if provided) | La descripcion no puede superar 500 caracteres. |
| estimated_cost | Decimal >= 0 (if provided) | El costo estimado no puede ser negativo. |
| priority_order | Integer >= 1 (if provided) | El orden de prioridad debe ser mayor a 0. |
| status | Must be one of: pending, scheduled, cancelled (if provided) | Estado no valido. No puede marcar como completado aqui. |
| notes | max 1000 chars or null (if provided) | Las notas no pueden superar 1000 caracteres. |

**Business Rules:**

- `status = 'completed'` is explicitly blocked on this endpoint; completion must go through TP-07 (plan-item-complete.md) to enforce procedure linking.
- Completed items are immutable — no field can be changed once an item is completed.
- Reordering (priority_order change) triggers a bulk update of all items in the plan to maintain a consistent integer sequence starting at 1.
- Cost changes cascade to plan's total_cost_estimated immediately.
- Cancelling an item reduces total_cost_estimated (cancelled items excluded from sum).
- `cups_code` and `tooth_number` are NOT updatable via this endpoint to preserve procedure integrity. A cancelled item must be created fresh if these need changing.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| priority_order = current value | No-op on ordering; item updated, no bulk reorder needed |
| All items cancelled after this update | total_cost_estimated = 0.00 |
| Set priority_order > max items | Item placed at end (max position); no error |
| Cancel item on approved plan | clinic_owner only; updates plan total_cost_estimated |
| Reopen cancelled item (cancelled → pending) | Allowed; re-adds estimated_cost to total |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `treatment_plan_items`: UPDATE — item fields updated
- `treatment_plan_items`: UPDATE (bulk) — priority_order resequencing for sibling items (if priority_order changed)
- `treatment_plans`: UPDATE — total_cost_estimated, progress_pct, updated_at (if cost or status changed)

**Example query (SQLAlchemy — reorder):**
```python
# Reorder: remove item from current position, insert at new
all_items = await session.scalars(
    select(TreatmentPlanItem)
    .where(TreatmentPlanItem.plan_id == plan_id)
    .where(TreatmentPlanItem.id != item_id)
    .order_by(TreatmentPlanItem.priority_order)
)
items_list = list(all_items)
items_list.insert(new_priority_order - 1, target_item)
for idx, item in enumerate(items_list):
    item.priority_order = idx + 1
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plan:{plan_id}`: DELETE
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plans:list:*`: INVALIDATE (cost or progress changed)

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| treatment-plans | treatment_plan.item_updated | { tenant_id, patient_id, plan_id, item_id, status_changed, new_status } | After successful update |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** update
- **Resource:** treatment_plan_item
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms (no reorder)
- **Maximum acceptable:** < 400ms (with bulk reorder)

### Caching Strategy
- **Strategy:** No caching on write
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates plan detail cache on any update

### Database Performance

**Queries executed:** 2-N (plan + item fetch, item update, optional bulk reorder, plan total update — all in single transaction)

**Indexes required:**
- `treatment_plan_items.(plan_id, priority_order)` — INDEX (reorder query + sequence)
- `treatment_plan_items.(plan_id, status)` — INDEX (total cost recalculation)

**N+1 prevention:** Bulk reorder executes as a single UPDATE via bulk statement; total recalculation is a single SUM aggregate.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| description | Pydantic `strip()` + strip_tags | Prevent XSS |
| notes | Pydantic `strip()` + bleach.clean | Free text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, description, notes (clinical details), cups_code.

**Audit requirement:** All writes logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Update item description and notes
   - **Given:** Doctor, draft plan, pending item
   - **When:** PUT with new description and notes
   - **Then:** 200 OK, description and notes updated, plan_summary unchanged

2. Update estimated_cost — plan total recalculated
   - **Given:** Plan total = 600000, item estimated_cost = 200000
   - **When:** PUT item with estimated_cost = 250000
   - **Then:** 200 OK, item cost = 250000, plan total = 650000

3. Reorder item from position 3 to position 1
   - **Given:** Plan with 3 items at orders 1, 2, 3; update item at order 3
   - **When:** PUT with priority_order = 1
   - **Then:** 200 OK, item at order 1; former items at orders 2 and 3; sequence is 1, 2, 3

4. Cancel item — plan total decreases
   - **Given:** Plan total = 600000, item estimated_cost = 200000
   - **When:** PUT item with status = cancelled
   - **Then:** 200 OK, plan total = 400000 (cancelled item excluded)

5. Mark item as scheduled
   - **Given:** Pending item
   - **When:** PUT with status = scheduled
   - **Then:** 200 OK, status = scheduled

#### Edge Cases
1. Set priority_order > total item count
   - **Given:** Plan with 3 items, PUT with priority_order = 99
   - **When:** Request
   - **Then:** 200 OK, item placed at last position (order = 3)

2. Reopen cancelled item (cancelled → pending)
   - **Given:** Cancelled item, estimated_cost = 200000
   - **When:** PUT with status = pending
   - **Then:** 200 OK, status = pending, estimated_cost re-added to plan total

#### Error Cases
1. Attempt to set status = completed
   - **Given:** Any item
   - **When:** PUT with status = completed
   - **Then:** 400 with redirect to complete endpoint

2. Modify completed item
   - **Given:** Completed item
   - **When:** PUT with any field
   - **Then:** 409 item_already_completed

3. Doctor on approved plan
   - **Given:** Doctor JWT, approved active plan
   - **When:** PUT item
   - **Then:** 403 Forbidden

4. Item not found
   - **Given:** Non-existent item_id
   - **When:** PUT request
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** doctor, clinic_owner

**Patients/Entities:** Draft plan with 3 items in various statuses; active approved plan with pending items; plan with completed and cancelled items.

### Mocking Strategy

- RabbitMQ: Mock publish, assert item_updated payload
- Redis cache: fakeredis, verify key deletion

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Item fields updated correctly (only provided fields changed)
- [ ] priority_order change triggers correct bulk resequencing of all plan items
- [ ] estimated_cost change recalculates plan total_cost_estimated
- [ ] Cancelled items excluded from plan total
- [ ] status = completed blocked, returns 400 with correct endpoint reference
- [ ] Completed items return 409 on any modification
- [ ] Approved plan items protected for non-owner roles
- [ ] Audit log written with PHI flag
- [ ] Plan cache invalidated after update
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms no reorder, < 400ms with reorder)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Marking item as completed (see TP-07 plan-item-complete.md)
- Bulk reordering via a dedicated reorder endpoint (handled via individual PUT calls)
- Updating cups_code or tooth_number (cancel item and create new one via TP-05)

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
- [x] DB queries optimized (indexes listed, bulk reorder)
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
