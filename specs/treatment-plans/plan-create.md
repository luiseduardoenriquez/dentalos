# TP-01: Create Treatment Plan Spec

---

## Overview

**Feature:** Create a new treatment plan for a patient, optionally auto-populating plan items from active odontogram findings. This is the entry point of the odontogram → treatment plan → quotation automated flow — a key product differentiator.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** P-01 (patient-create.md), CR-07 (odontogram findings), I-01 (multi-tenancy.md), I-02 (database-architecture.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** The doctor creating the plan becomes the plan's `created_by` and default responsible clinician.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/treatment-plans
```

**Rate Limiting:**
- 30 requests per minute per user
- Prevents accidental duplicate plan creation

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

### Query Parameters

None.

### Request Body Schema

```json
{
  "title": "string (required) — max 200 chars",
  "description": "string (optional) — max 2000 chars",
  "diagnoses": "string[] (optional) — list of CIE-10 codes, each max 10 chars, max 20 items",
  "priority": "string (required) — enum: high, medium, low",
  "estimated_duration_days": "integer (optional) — min 1, max 3650",
  "auto_from_odontogram": "boolean (optional) — default false; if true, reads all active odontogram conditions and suggests procedure items"
}
```

**Example Request (manual):**
```json
{
  "title": "Plan de tratamiento integral 2026",
  "description": "Plan completo para restaurar sectores posteriores y tratamiento periodontal.",
  "diagnoses": ["K02.1", "K05.1"],
  "priority": "high",
  "estimated_duration_days": 90
}
```

**Example Request (auto from odontogram):**
```json
{
  "title": "Plan generado desde odontograma",
  "priority": "medium",
  "estimated_duration_days": 60,
  "auto_from_odontogram": true
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
  "patient_id": "uuid",
  "title": "string",
  "description": "string | null",
  "diagnoses": "string[]",
  "priority": "string (high | medium | low)",
  "estimated_duration_days": "integer | null",
  "status": "string (draft)",
  "items_count": "integer",
  "completed_count": "integer",
  "total_cost_estimated": "number (decimal)",
  "progress_pct": "number (0.0 - 100.0)",
  "items": [
    {
      "id": "uuid",
      "cups_code": "string",
      "description": "string",
      "tooth_number": "string | null",
      "zone": "string | null",
      "estimated_cost": "number",
      "priority_order": "integer",
      "status": "string (pending)",
      "notes": "string | null",
      "source": "string (manual | odontogram)"
    }
  ],
  "approval_status": "string (pending_approval)",
  "quotation_id": "uuid | null",
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)",
  "updated_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Plan generado desde odontograma",
  "description": null,
  "diagnoses": ["K02.1", "K05.3"],
  "priority": "medium",
  "estimated_duration_days": 60,
  "status": "draft",
  "items_count": 3,
  "completed_count": 0,
  "total_cost_estimated": 850000.00,
  "progress_pct": 0.0,
  "items": [
    {
      "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
      "cups_code": "906513",
      "description": "Restauracion clase II amalgama diente 36",
      "tooth_number": "36",
      "zone": "posterior_inferior_izquierdo",
      "estimated_cost": 200000.00,
      "priority_order": 1,
      "status": "pending",
      "notes": "Hallazgo: caries profunda",
      "source": "odontogram"
    }
  ],
  "approval_status": "pending_approval",
  "quotation_id": null,
  "created_by": "d4e5f6a1-b2c3-4567-efab-234567890123",
  "created_at": "2026-02-24T10:00:00Z",
  "updated_at": "2026-02-24T10:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or missing required fields.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not doctor or clinic_owner.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para crear planes de tratamiento."
}
```

#### 404 Not Found
**When:** patient_id does not exist in the tenant.

**Example:**
```json
{
  "error": "patient_not_found",
  "message": "Paciente no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails (invalid CIE-10 format, invalid priority enum, etc.).

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "priority": ["El valor 'urgente' no es valido. Opciones: high, medium, low."],
    "diagnoses": ["Maximo 20 diagnosticos por plan."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure, or odontogram read error during auto-population.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema (field types, enums, lengths, CIE-10 code format).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC (must be doctor or clinic_owner).
4. Verify `patient_id` exists and belongs to the tenant (`is_active = true`).
5. If `auto_from_odontogram = true`:
   a. Query `odontogram_findings` for all active conditions linked to this patient.
   b. For each finding, look up the suggested CUPS procedure code using the condition-to-procedure mapping table.
   c. For each CUPS code, query the service catalog (B-14) to retrieve the default price for the tenant.
   d. Build a list of draft `TreatmentPlanItem` objects with `source = 'odontogram'`.
   e. If no active odontogram findings exist, proceed with an empty items list (no error).
6. Insert `TreatmentPlanItem` records within the same transaction.
7. Calculate `total_cost_estimated` as SUM of all item `estimated_cost` values.
8. Insert `TreatmentPlan` record with `status = 'draft'`, `approval_status = 'pending_approval'`, `progress_pct = 0.0`.
9. Write audit log entry (action: create, resource: treatment_plan, PHI: yes).
10. Invalidate treatment plan list cache for patient.
11. Dispatch `treatment_plan.created` event to RabbitMQ.
12. Return 201 with the created plan including all items.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| title | 1-200 chars, required | El titulo es obligatorio y no puede superar 200 caracteres. |
| description | max 2000 chars (if provided) | La descripcion no puede superar 2000 caracteres. |
| diagnoses | max 20 items; each item: valid CIE-10 format (letter + 2-4 digits, optional dot) | Codigo CIE-10 no valido: {code}. |
| priority | Must be one of: high, medium, low | La prioridad no es valida. Opciones: high, medium, low. |
| estimated_duration_days | Integer 1-3650 (if provided) | La duracion estimada debe ser entre 1 y 3650 dias. |
| auto_from_odontogram | Boolean (if provided) | El campo auto_from_odontogram debe ser verdadero o falso. |

**Business Rules:**

- A plan is always created with `status = 'draft'`; it cannot be created in any other status.
- `created_by` is set server-side from the JWT; it cannot be supplied by the client.
- If `auto_from_odontogram = true` and no odontogram findings exist, an empty-items draft plan is created (no error raised — the doctor may add items manually).
- Auto-populated items inherit their `estimated_cost` from the tenant's service catalog (B-14). If no catalog price exists for a CUPS code, `estimated_cost` defaults to `0.00` and a flag `price_not_found: true` is set on the item.
- CIE-10 codes are stored as provided (uppercase normalized) without validation against a full dictionary — only format is validated.
- A patient may have multiple active treatment plans simultaneously.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| `auto_from_odontogram = true` with no active findings | Creates plan with empty items list; `items_count = 0` |
| Service catalog has no price for a CUPS code | Item created with `estimated_cost = 0.00`, flagged in notes |
| Patient has no odontogram record initialized | Treat as no findings; proceed normally |
| `diagnoses` array contains duplicate CIE-10 codes | Deduplicate before storing |
| `estimated_duration_days` not provided | Stored as null; plan has no defined end date |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `treatment_plans`: INSERT — new plan record
- `treatment_plan_items`: INSERT — one row per item (0 or more, depending on auto_from_odontogram result)

**Example query (SQLAlchemy):**
```python
plan = TreatmentPlan(
    patient_id=patient_id,
    title=data.title,
    description=data.description,
    diagnoses=data.diagnoses or [],
    priority=data.priority,
    estimated_duration_days=data.estimated_duration_days,
    status="draft",
    approval_status="pending_approval",
    total_cost_estimated=Decimal("0.00"),
    progress_pct=Decimal("0.0"),
    created_by=current_user.id,
)
session.add(plan)
await session.flush()

for idx, item_data in enumerate(items):
    item = TreatmentPlanItem(
        plan_id=plan.id,
        cups_code=item_data.cups_code,
        description=item_data.description,
        tooth_number=item_data.tooth_number,
        zone=item_data.zone,
        estimated_cost=item_data.estimated_cost,
        priority_order=idx + 1,
        status="pending",
        source=item_data.source,
    )
    session.add(item)

plan.total_cost_estimated = sum(i.estimated_cost for i in items)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plans:list:*`: INVALIDATE — all list caches for this patient

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| treatment-plans | treatment_plan.created | { tenant_id, patient_id, plan_id, created_by, auto_from_odontogram } | After successful insert |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** treatment_plan
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms (without odontogram auto-population)
- **Maximum acceptable:** < 700ms (with odontogram auto-population + catalog lookups)

### Caching Strategy
- **Strategy:** No caching on create (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates patient treatment plan list cache on successful create

### Database Performance

**Queries executed:** 3-N (patient lookup, plan insert, item inserts; plus odontogram + catalog queries if auto_from_odontogram = true)

**Indexes required:**
- `treatment_plans.(patient_id, status)` — INDEX (for list queries)
- `treatment_plans.created_by` — INDEX
- `treatment_plan_items.plan_id` — INDEX
- `odontogram_findings.(patient_id, status)` — INDEX (for auto-population query)

**N+1 prevention:** Odontogram findings fetched in single query; catalog prices fetched in bulk by CUPS codes array.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| title | Pydantic `strip()` + strip_tags | Prevent XSS in stored titles |
| description | Pydantic `strip()` + bleach.clean | Free text field |
| diagnoses[] | Each item: uppercase strip, regex format check | CIE-10 format only |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, diagnoses (clinical data), plan title/description may contain clinical details.

**Audit requirement:** All writes logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Create manual plan with required fields only
   - **Given:** Authenticated doctor, active patient in tenant
   - **When:** POST /api/v1/patients/{patient_id}/treatment-plans with title and priority
   - **Then:** 201 Created, status = draft, items_count = 0, progress_pct = 0.0

2. Create plan with auto_from_odontogram = true, findings exist
   - **Given:** Authenticated doctor, patient has 3 active odontogram findings with catalog prices
   - **When:** POST with auto_from_odontogram = true
   - **Then:** 201 Created, items_count = 3, each item has estimated_cost from catalog, total_cost_estimated = sum

3. Create plan with diagnoses array
   - **Given:** Authenticated doctor, valid CIE-10 codes provided
   - **When:** POST with diagnoses = ["K02.1", "K05.1"]
   - **Then:** 201 Created, diagnoses stored correctly

#### Edge Cases
1. auto_from_odontogram = true, no active findings
   - **Given:** Patient has odontogram but no active findings
   - **When:** POST with auto_from_odontogram = true
   - **Then:** 201 Created, items_count = 0, total_cost_estimated = 0.00

2. Duplicate CIE-10 codes in diagnoses
   - **Given:** diagnoses = ["K02.1", "K02.1", "K05.1"]
   - **When:** POST request
   - **Then:** 201 Created, duplicates removed; diagnoses stored as ["K02.1", "K05.1"]

3. CUPS code not in service catalog
   - **Given:** Odontogram finding maps to CUPS code with no catalog price
   - **When:** POST with auto_from_odontogram = true
   - **Then:** 201 Created, item estimated_cost = 0.00, note indicates price not found

#### Error Cases
1. Patient not found
   - **Given:** Non-existent patient_id
   - **When:** POST /api/v1/patients/non-existent-id/treatment-plans
   - **Then:** 404 Not Found

2. Insufficient role
   - **Given:** User with receptionist role
   - **When:** POST treatment plan
   - **Then:** 403 Forbidden

3. Invalid priority enum
   - **Given:** priority = "urgente"
   - **When:** POST request
   - **Then:** 422 Unprocessable Entity with field error

4. Missing required title
   - **Given:** Request body without title field
   - **When:** POST request
   - **Then:** 422 Unprocessable Entity with title error

### Test Data Requirements

**Users:** doctor (primary), clinic_owner, receptionist (negative test)

**Patients/Entities:** Active patient with odontogram initialized; patient with 3 active odontogram findings; patient with no findings. Service catalog with known CUPS codes and prices.

### Mocking Strategy

- Odontogram findings query: Fixture returning predefined findings list
- Service catalog lookup: Fixture with known CUPS-to-price mappings
- RabbitMQ: Mock publish call, assert payload contains plan_id and auto_from_odontogram flag
- Redis cache: Use fakeredis for cache invalidation tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Plan created with required fields returns 201 with status = draft
- [ ] auto_from_odontogram = true populates items from active odontogram findings
- [ ] Each auto-populated item has estimated_cost from service catalog
- [ ] total_cost_estimated = sum of all item estimated_costs
- [ ] Duplicate diagnoses codes are deduplicated before storage
- [ ] Missing patient returns 404
- [ ] Non-doctor/owner role returns 403
- [ ] Audit log entry written with PHI flag
- [ ] RabbitMQ treatment_plan.created event dispatched
- [ ] Patient treatment plan list cache invalidated
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms manual, < 700ms auto)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Editing plan metadata after creation (see TP-04 plan-update.md)
- Adding individual items after creation (see TP-05 plan-item-add.md)
- Patient approval of the plan (see TP-08 plan-approve.md)
- PDF generation (see TP-09 plan-pdf.md)
- Quotation generation (handled downstream by B-16)

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
- [x] Pagination applied where needed (N/A for create)

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
