# TP-05: Add Item to Treatment Plan Spec

---

## Overview

**Feature:** Add a single procedure item to an existing treatment plan. Supports automatic price lookup from the tenant's service catalog (B-14). Recalculates the plan's total estimated cost after each item addition.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** TP-01 (plan-create.md), TP-04 (plan-update.md), B-14 (service-catalog), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** clinic_owner may add items to active plans (override). Doctors may only add items to draft plans. Active plans with approval require clinic_owner role.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items
```

**Rate Limiting:**
- 60 requests per minute per user (items added rapidly during plan construction)

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
  "cups_code": "string (required) — CUPS procedure code, 6-10 chars",
  "description": "string (required) — max 500 chars",
  "tooth_number": "string (optional) — FDI notation: '11' to '85', or null for full-mouth procedures",
  "zone": "string (optional) — enum: anterior_superior, anterior_inferior, posterior_superior_derecho, posterior_superior_izquierdo, posterior_inferior_derecho, posterior_inferior_izquierdo, full_mouth",
  "estimated_cost": "number (optional) — decimal, min 0; if not provided, auto-looked up from service catalog",
  "priority_order": "integer (optional) — position in plan; if not provided, appended at end",
  "notes": "string (optional) — max 1000 chars"
}
```

**Example Request (with auto-price lookup):**
```json
{
  "cups_code": "906513",
  "description": "Restauracion clase II amalgama diente 36",
  "tooth_number": "36",
  "zone": "posterior_inferior_izquierdo",
  "notes": "Caries profunda diagnosticada en odontograma"
}
```

**Example Request (manual price):**
```json
{
  "cups_code": "906601",
  "description": "Detartraje supragingival completo",
  "zone": "full_mouth",
  "estimated_cost": 150000.00,
  "priority_order": 1
}
```

---

## Response

### Success Response

**Status:** 201 Created

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
  "actual_cost": "null",
  "priority_order": "integer",
  "status": "string (pending)",
  "notes": "string | null",
  "source": "string (manual)",
  "price_from_catalog": "boolean",
  "procedure_id": "null",
  "completed_at": "null",
  "created_at": "string (ISO 8601 datetime)",
  "plan_summary": {
    "items_count": "integer",
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
  "estimated_cost": 200000.00,
  "actual_cost": null,
  "priority_order": 3,
  "status": "pending",
  "notes": "Caries profunda diagnosticada en odontograma",
  "source": "manual",
  "price_from_catalog": true,
  "procedure_id": null,
  "completed_at": null,
  "created_at": "2026-02-24T11:30:00Z",
  "plan_summary": {
    "items_count": 3,
    "total_cost_estimated": 600000.00,
    "progress_pct": 0.0
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or plan is in a state that does not allow adding items.

**Example:**
```json
{
  "error": "plan_not_editable",
  "message": "No se pueden agregar procedimientos a un plan en estado 'completed'.",
  "details": {
    "plan_status": "completed"
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Doctor attempting to add item to an active plan (requires clinic_owner), or role is not allowed.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede agregar procedimientos a un plan activo."
}
```

#### 404 Not Found
**When:** patient_id or plan_id not found in tenant.

**Example:**
```json
{
  "error": "plan_not_found",
  "message": "Plan de tratamiento no encontrado."
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
    "cups_code": ["El codigo CUPS no puede superar 10 caracteres."],
    "estimated_cost": ["El costo estimado no puede ser negativo."]
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
3. Check user permissions via RBAC.
4. Fetch plan by plan_id + patient_id; return 404 if not found.
5. Check plan editability:
   - `draft`: allowed for all authorized roles.
   - `active`: allowed only for clinic_owner (doctor returns 403).
   - `completed` or `cancelled`: blocked for all (return 400).
6. If `estimated_cost` not provided:
   a. Query service catalog (B-14) for tenant's price of cups_code.
   b. If found, set estimated_cost from catalog and set `price_from_catalog = true`.
   c. If not found, set estimated_cost = 0.00 and append note "Precio no encontrado en catalogo" to notes.
7. If `priority_order` not provided, set to current `MAX(priority_order) + 1` for the plan.
8. If `priority_order` provided and conflicts with existing item order, shift existing items' priority_order >= new value upward by 1.
9. Insert new `TreatmentPlanItem` with `status = 'pending'`, `source = 'manual'`.
10. Recalculate `total_cost_estimated` on the plan: `SUM(estimated_cost WHERE status != 'cancelled')`.
11. Update `treatment_plans.updated_at`.
12. Write audit log entry (action: create, resource: treatment_plan_item, PHI: yes).
13. Invalidate plan cache.
14. Return 201 with new item and updated plan summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| cups_code | 6-10 chars, alphanumeric | El codigo CUPS debe tener entre 6 y 10 caracteres alfanumericos. |
| description | 1-500 chars | La descripcion es obligatoria y no puede superar 500 caracteres. |
| tooth_number | FDI notation: string "11"-"85" or null (if provided) | El numero de diente no es valido. Use notacion FDI. |
| zone | Must be one of the defined zone enums (if provided) | La zona no es valida. |
| estimated_cost | Decimal >= 0 (if provided) | El costo estimado no puede ser negativo. |
| priority_order | Integer >= 1 (if provided) | El orden de prioridad debe ser mayor a 0. |
| notes | max 1000 chars (if provided) | Las notas no pueden superar 1000 caracteres. |

**Business Rules:**

- Items can only be added to draft plans by doctors; active plans require clinic_owner override.
- Completed and cancelled plans are locked — no items can be added.
- Auto-price lookup uses the tenant's service catalog (B-14); prices are tenant-specific (clinic sets their own fees).
- `source` is always set to `'manual'` for items added via this endpoint (vs. `'odontogram'` for auto-generated items).
- Adding an item to an approved active plan (approval_status = 'approved') is only allowed for clinic_owner and records the override in the audit log.
- `total_cost_estimated` excludes cancelled items from the sum.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| cups_code not in service catalog | Item created with estimated_cost = 0.00, price_from_catalog = false |
| priority_order = 1 on a plan with existing items | Existing items shifted: their priority_order incremented by 1 |
| tooth_number for full-mouth procedure | Allow null tooth_number with zone = full_mouth |
| Doctor adds item to approved active plan | 403 Forbidden; only clinic_owner allowed |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `treatment_plan_items`: INSERT — new item record
- `treatment_plans`: UPDATE — total_cost_estimated recalculated, updated_at refreshed
- `treatment_plan_items`: UPDATE — priority_order incremented for conflicting items (if priority_order insertion)

**Example query (SQLAlchemy):**
```python
item = TreatmentPlanItem(
    plan_id=plan_id,
    cups_code=data.cups_code,
    description=data.description,
    tooth_number=data.tooth_number,
    zone=data.zone,
    estimated_cost=estimated_cost,
    priority_order=resolved_priority_order,
    status="pending",
    source="manual",
    notes=resolved_notes,
    price_from_catalog=price_from_catalog,
)
session.add(item)
await session.flush()

# Recalculate total
new_total = await session.scalar(
    select(func.sum(TreatmentPlanItem.estimated_cost))
    .where(TreatmentPlanItem.plan_id == plan_id)
    .where(TreatmentPlanItem.status != "cancelled")
)
await session.execute(
    update(TreatmentPlan)
    .where(TreatmentPlan.id == plan_id)
    .values(total_cost_estimated=new_total, updated_at=datetime.utcnow())
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
| treatment-plans | treatment_plan.item_added | { tenant_id, patient_id, plan_id, item_id, cups_code } | After successful insert |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** treatment_plan_item
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 250ms (with catalog lookup)
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on write
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates plan detail and list cache

### Database Performance

**Queries executed:** 4 (plan fetch, catalog lookup, priority_order resolution, item insert + plan total update in transaction)

**Indexes required:**
- `treatment_plan_items.(plan_id, priority_order)` — INDEX (ordering + conflict detection)
- `treatment_plan_items.(plan_id, status)` — INDEX (total cost recalculation)
- `service_catalog.(tenant_id, cups_code)` — UNIQUE INDEX (catalog lookup)

**N+1 prevention:** Not applicable (single item insert).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| cups_code | Pydantic regex validator: alphanumeric only | Prevent injection |
| description | Pydantic `strip()` + strip_tags | Prevent XSS |
| notes | Pydantic `strip()` + bleach.clean | Free text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, cups_code, description (clinical procedure), tooth_number, notes.

**Audit requirement:** All writes logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Add item with auto-price lookup
   - **Given:** Doctor, draft plan, cups_code exists in service catalog
   - **When:** POST item without estimated_cost
   - **Then:** 201 Created, estimated_cost from catalog, price_from_catalog = true, plan total recalculated

2. Add item with manual price
   - **Given:** Doctor, draft plan
   - **When:** POST item with estimated_cost = 150000
   - **Then:** 201 Created, estimated_cost = 150000, price_from_catalog = false

3. Add item at specific priority_order (insert at position 1)
   - **Given:** Draft plan with 2 items (orders 1, 2)
   - **When:** POST item with priority_order = 1
   - **Then:** 201 Created, new item at order 1; existing items shifted to orders 2, 3

4. clinic_owner adds item to active plan
   - **Given:** clinic_owner JWT, active plan
   - **When:** POST item
   - **Then:** 201 Created successfully

#### Edge Cases
1. cups_code not in service catalog
   - **Given:** cups_code with no catalog price
   - **When:** POST without estimated_cost
   - **Then:** 201 Created, estimated_cost = 0.00, price_from_catalog = false

2. priority_order not provided
   - **Given:** Plan with 3 items (max order = 3)
   - **When:** POST without priority_order
   - **Then:** 201 Created, new item has priority_order = 4

#### Error Cases
1. Doctor attempts to add item to active plan
   - **Given:** Doctor JWT, active (not clinic_owner)
   - **When:** POST item
   - **Then:** 403 Forbidden

2. Plan in completed state
   - **Given:** Completed plan
   - **When:** POST item
   - **Then:** 400 plan_not_editable

3. Negative estimated_cost
   - **Given:** estimated_cost = -5000
   - **When:** POST item
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** doctor, clinic_owner

**Patients/Entities:** Draft plan; active plan; completed plan; service catalog with known CUPS codes; service catalog missing a specific CUPS code.

### Mocking Strategy

- Service catalog (B-14): Fixture with known CUPS-to-price mappings
- RabbitMQ: Mock publish, assert item_added payload
- Redis cache: fakeredis for invalidation tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Item added to draft plan returns 201 with item and updated plan_summary
- [ ] Auto-price from catalog populated when estimated_cost not provided
- [ ] price_from_catalog = false when cost supplied manually
- [ ] total_cost_estimated on plan recalculated after item add
- [ ] priority_order insertion shifts existing items correctly
- [ ] Active plan addition requires clinic_owner role
- [ ] Completed/cancelled plan returns 400
- [ ] Audit log written with PHI flag
- [ ] Plan cache invalidated after item add
- [ ] All test cases pass
- [ ] Performance targets met (< 250ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Updating an existing item (see TP-06 plan-item-update.md)
- Marking an item as complete (see TP-07 plan-item-complete.md)
- Auto-populating items from odontogram (handled at plan creation in TP-01)

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
