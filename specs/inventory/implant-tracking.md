# INV-07 Implant Tracking Spec

---

## Overview

**Feature:** Link a placed implant inventory item to a specific patient procedure, creating a traceability chain from manufacturer lot to patient. Records placement details including FDI tooth number, placement date, serial number, and surgical notes. Decrements the implant's inventory quantity on successful linking. Provides a recall search endpoint to find all patients who received implants from a specific lot number. Critical for patient safety and regulatory compliance.

**Domain:** inventory

**Priority:** Low

**Dependencies:** INV-01 (item-create.md), INV-03 (item-update.md), P-01 (patient-get.md), treatment-plans domain, infra/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor (for linking implant to procedure)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner and doctor can link implants to patients (clinical procedure). The recall search endpoint (GET) is available to clinic_owner and assistant for regulatory audit purposes.

---

## Endpoints

### Link Implant to Patient Procedure

```
POST /api/v1/inventory/implants/{item_id}/link
```

### Recall Search

```
GET /api/v1/inventory/implants/search
```

**Rate Limiting:**
- POST link: 30 requests per minute per user
- GET search: Inherits global rate limit (100 requests per minute per user)

---

## Request — POST Link

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| item_id | Yes | UUID | UUID v4, must be category=implant | Inventory implant item to link | inv-aaaa-1111-bbbb-2222-cccc33334444 |

### Query Parameters (POST)

None.

### Request Body Schema

```json
{
  "patient_id": "uuid (required) — patient who received the implant",
  "procedure_id": "uuid (optional) — treatment plan item or clinical procedure ID for traceability",
  "tooth_number": "integer (required) — FDI notation tooth number, 11-85 (standard dentition range)",
  "placement_date": "string (required) — ISO 8601 date, cannot be in the future",
  "serial_number": "string (optional) — manufacturer serial number, max 100 chars",
  "lot_number": "string (required) — lot/batch number for recall traceability, max 100 chars",
  "manufacturer": "string (required) — implant manufacturer name, max 200 chars",
  "notes": "string (optional) — surgical notes, max 1000 chars"
}
```

**Example Request:**
```json
{
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "procedure_id": "tp-item-aaaa-1111-bbbb-2222-cccc33334444",
  "tooth_number": 46,
  "placement_date": "2026-02-25",
  "serial_number": "IMP-2025-SN-009876",
  "lot_number": "IMPL-BATCH-2025-03",
  "manufacturer": "Nobel Biocare",
  "notes": "Implante colocado sin complicaciones. Torque de insercion 35 Ncm. ISQ 72."
}
```

---

## Response — POST Link

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "id": "uuid — implant_placement record ID",
  "item": {
    "id": "uuid",
    "name": "string",
    "quantity_after": "number — quantity remaining after this placement"
  },
  "patient": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string"
  },
  "procedure_id": "uuid | null",
  "tooth_number": "integer — FDI notation",
  "placement_date": "string ISO 8601 date",
  "serial_number": "string | null",
  "lot_number": "string",
  "manufacturer": "string",
  "notes": "string | null",
  "created_at": "string ISO 8601",
  "created_by": "uuid"
}
```

**Example:**
```json
{
  "id": "impl-aaaa-1111-bbbb-2222-cccc33334444",
  "item": {
    "id": "inv-aaaa-1111-bbbb-2222-cccc33334444",
    "name": "Implante Nobel Active 4.3x10mm",
    "quantity_after": 2
  },
  "patient": {
    "id": "pt_550e8400-e29b-41d4-a716-446655440000",
    "first_name": "Maria",
    "last_name": "Garcia Lopez"
  },
  "procedure_id": "tp-item-aaaa-1111-bbbb-2222-cccc33334444",
  "tooth_number": 46,
  "placement_date": "2026-02-25",
  "serial_number": "IMP-2025-SN-009876",
  "lot_number": "IMPL-BATCH-2025-03",
  "manufacturer": "Nobel Biocare",
  "notes": "Implante colocado sin complicaciones. Torque de insercion 35 Ncm. ISQ 72.",
  "created_at": "2026-02-25T14:00:00-05:00",
  "created_by": "usr-doctor-0001-000000000000"
}
```

---

## Request — GET Recall Search

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters (GET)

None.

### Query Parameters (GET)

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| lot_number | Yes | string | Min 3 chars, max 100 chars | Lot number to search for affected patients | IMPL-BATCH-2025-03 |
| manufacturer | No | string | Max 200 chars | Filter by manufacturer | Nobel Biocare |

---

## Response — GET Recall Search

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "lot_number": "string — searched lot number",
  "manufacturer": "string | null — filter applied",
  "affected_patients": [
    {
      "placement_id": "uuid",
      "patient": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string",
        "document_number": "string | null",
        "phone": "string | null",
        "email": "string | null"
      },
      "tooth_number": "integer",
      "placement_date": "string ISO 8601 date",
      "serial_number": "string | null",
      "item_name": "string — implant item name",
      "notes": "string | null"
    }
  ],
  "total_affected": "integer",
  "searched_at": "string ISO 8601"
}
```

**Example:**
```json
{
  "lot_number": "IMPL-BATCH-2025-03",
  "manufacturer": null,
  "affected_patients": [
    {
      "placement_id": "impl-aaaa-1111-bbbb-2222-cccc33334444",
      "patient": {
        "id": "pt_550e8400-e29b-41d4-a716-446655440000",
        "first_name": "Maria",
        "last_name": "Garcia Lopez",
        "document_number": "1020304050",
        "phone": "+573001234567",
        "email": "maria.garcia@email.com"
      },
      "tooth_number": 46,
      "placement_date": "2026-02-25",
      "serial_number": "IMP-2025-SN-009876",
      "item_name": "Implante Nobel Active 4.3x10mm",
      "notes": "Implante colocado sin complicaciones."
    }
  ],
  "total_affected": 1,
  "searched_at": "2026-02-25T16:00:00-05:00"
}
```

---

## Error Responses (Both Endpoints)

#### 400 Bad Request
**When (POST):** Missing required fields.
**When (GET):** `lot_number` missing or less than 3 characters.

**Example (GET):**
```json
{
  "error": "invalid_input",
  "message": "El numero de lote es requerido para la busqueda de recall.",
  "details": {
    "lot_number": ["El numero de lote es requerido. Minimo 3 caracteres."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing or invalid.

#### 403 Forbidden
**When (POST):** Role is assistant or receptionist.
**When (GET):** Role is doctor, receptionist, or patient.

#### 404 Not Found
**When (POST):** `item_id` not found, `patient_id` not found, `procedure_id` not found, or `item.category != 'implant'`.

**Example:**
```json
{
  "error": "not_found",
  "message": "El item especificado no es un implante o no fue encontrado en el inventario."
}
```

#### 409 Conflict
**When (POST):** Item quantity is 0 (no stock to place).

**Example:**
```json
{
  "error": "out_of_stock",
  "message": "No hay stock disponible de este implante. Cantidad actual: 0."
}
```

#### 422 Unprocessable Entity
**When (POST):** `tooth_number` outside valid FDI range, `placement_date` in the future.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Los datos de colocacion del implante contienen errores.",
  "details": {
    "tooth_number": ["Numero de diente invalido. Use notacion FDI (11-85)."],
    "placement_date": ["La fecha de colocacion no puede ser futura."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic — POST Link

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`. If not `clinic_owner` or `doctor`, return 403.
2. Validate `item_id` as UUID v4.
3. Validate request body: all required fields present, tooth_number in FDI range 11-85, placement_date not future.
4. Set `search_path` to tenant schema.
5. Load inventory item: `SELECT id, name, category, quantity FROM inventory_items WHERE id = :item_id AND tenant_id = :tenant_id`. If not found or category != 'implant', return 404.
6. Check quantity > 0. If quantity == 0, return 409 (out of stock).
7. Validate `patient_id` exists in tenant `patients` table. If not, return 404.
8. If `procedure_id` provided: validate it exists in `treatment_plan_items` or `clinical_records` table. If not, return 404.
9. Validate `lot_number` in request matches the inventory item's `lot_number` (if item has a lot_number set). If mismatch, return 422 with warning but allow override (items may have multiple lots tracked in placement records).
10. Begin database transaction.
11. Insert into `implant_placements`: all fields, `item_id`, `tenant_id`, `created_by = user_id`.
12. Decrement inventory: `UPDATE inventory_items SET quantity = quantity - 1 WHERE id = :item_id AND quantity > 0`. If 0 rows affected (race condition), rollback and return 409.
13. Insert quantity history: `INSERT INTO inventory_quantity_history (item_id, delta=-1, reason='consumed', notes='Implante colocado - Paciente {patient_id} - Diente {tooth_number}', user_id)`.
14. Commit transaction.
15. Write audit log: action `create`, resource `implant_placement`, PHI=yes.
16. Invalidate inventory cache: `tenant:{tenant_id}:inventory:*`.
17. Return 201 with placement record and updated item quantity.

## Business Logic — GET Recall Search

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`. If not `clinic_owner` or `assistant`, return 403.
2. Validate `lot_number` query param: required, min 3 chars.
3. Set `search_path` to tenant schema.
4. Execute recall search:
   ```sql
   SELECT ip.id, ip.tooth_number, ip.placement_date, ip.serial_number, ip.notes,
     ii.name AS item_name,
     p.id AS patient_id, p.first_name, p.last_name, p.document_number, p.phone, p.email
   FROM implant_placements ip
   JOIN inventory_items ii ON ii.id = ip.item_id
   JOIN patients p ON p.id = ip.patient_id
   WHERE ip.tenant_id = :tenant_id
     AND ip.lot_number ILIKE :lot_pattern
     AND (:manufacturer IS NULL OR ip.manufacturer ILIKE :mfr_pattern)
   ORDER BY ip.placement_date DESC
   ```
5. Write audit log: action `search`, resource `implant_recall`, PHI=yes (patient data in results).
6. Return 200 with affected patients list.

**Validation Rules (POST):**

| Field | Rule | Error Message |
|-------|------|---------------|
| item_id (URL) | Valid UUID v4, must exist, must be category=implant | El item no es un implante o no fue encontrado. |
| patient_id | Valid UUID v4, must exist in tenant | Paciente no encontrado. |
| tooth_number | Integer in FDI range 11-85 | Numero de diente invalido. Use notacion FDI (11-85). |
| placement_date | ISO 8601 date, not future | La fecha de colocacion no puede ser futura. |
| lot_number | Non-empty, max 100 chars | El numero de lote es requerido. |
| manufacturer | Non-empty, max 200 chars | El fabricante es requerido. |
| item.quantity | Must be > 0 before placement | No hay stock disponible. |

**Validation Rules (GET):**

| Field | Rule | Error Message |
|-------|------|---------------|
| lot_number | Required, min 3 chars, max 100 chars | El numero de lote es requerido. Minimo 3 caracteres. |

**Business Rules:**

- Every implant placement decrements the inventory quantity by exactly 1 unit, regardless of the item's `unit` (implants are always counted in `units`).
- The quantity decrement uses `UPDATE WHERE quantity > 0` with row count check to prevent race conditions where two concurrent placements try to use the last unit.
- The `lot_number` in the implant_placement record comes from the request body (not necessarily from the inventory item). This allows tracking different lots within the same item if the item was restocked with a new lot.
- Recall search uses `ILIKE` with partial matching to handle lot number prefix searches (e.g., searching "IMPL-BATCH-2025" finds all 2025 batch placements).
- Recall search results include patient contact information to facilitate contacting affected patients in case of manufacturer recall.
- Recall search is scoped to the current tenant. Cross-tenant recall queries require superadmin access (out of scope for this spec).
- The recall search audit log is marked with PHI=yes and regulatory=yes since it involves accessing patient data for safety purposes.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| item.quantity = 1 (last unit) | Link succeeds; quantity_after = 0; is_low_stock becomes true if minimum_stock > 0 |
| Two concurrent placements on last unit | One succeeds (201); the other gets 409 (optimistic locking via UPDATE WHERE quantity > 0) |
| lot_number in request differs from item.lot_number | Allowed; placement records its own lot_number; warning logged |
| Recall search finds 0 patients | 200 OK, affected_patients=[], total_affected=0 |
| Recall search with partial lot number | ILIKE pattern finds all matching placements |
| procedure_id not provided | Valid; placement recorded without procedure link |

---

## Side Effects

### Database Changes

**Tenant schema tables affected (POST):**
- `implant_placements`: INSERT — new placement record
- `inventory_items`: UPDATE — `quantity = quantity - 1`
- `inventory_quantity_history`: INSERT — consumption record
- `audit_logs`: INSERT — placement event with PHI flag

**Example transaction (SQLAlchemy):**
```python
async with session.begin():
    placement = ImplantPlacement(
        tenant_id=tenant_id,
        item_id=item_id,
        patient_id=data.patient_id,
        procedure_id=data.procedure_id,
        tooth_number=data.tooth_number,
        placement_date=data.placement_date,
        serial_number=data.serial_number,
        lot_number=data.lot_number,
        manufacturer=data.manufacturer,
        notes=data.notes,
        created_by=user_id,
    )
    session.add(placement)

    # Atomic decrement with optimistic locking
    result = await session.execute(
        update(InventoryItem)
        .where(
            InventoryItem.id == item_id,
            InventoryItem.quantity > 0  # Prevent going below 0
        )
        .values(quantity=InventoryItem.quantity - 1)
        .returning(InventoryItem.quantity)
    )
    new_qty = result.scalar_one_or_none()
    if new_qty is None:
        raise OutOfStockError()

    session.add(InventoryQuantityHistory(
        item_id=item_id,
        delta=-1,
        reason="consumed",
        notes=f"Implante colocado - Paciente {data.patient_id} - Diente {data.tooth_number}",
        previous_quantity=new_qty + 1,
        new_quantity=new_qty,
        user_id=user_id,
    ))
```

### Cache Operations

**Cache keys affected (POST):**
- `tenant:{tenant_id}:inventory:*`: DELETE pattern — quantity changed

### Queue Jobs (RabbitMQ)

**Jobs dispatched (POST):**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | inventory.low_stock_alert | { tenant_id, item_id, item_name, quantity, minimum_stock } | When new quantity falls below minimum_stock (threshold crossing) |

### Audit Log

**Audit entry:** Yes — both POST and GET recall search

- **POST Action:** create
- **POST Resource:** implant_placement
- **POST PHI involved:** Yes — patient_id linked to clinical implant data

- **GET Action:** search
- **GET Resource:** implant_recall
- **GET PHI involved:** Yes — patient contact info in results
- **GET Regulatory flag:** Yes

### Notifications

**Notifications triggered:** Conditionally — only on low stock threshold crossing (same as INV-03 logic).

---

## Performance

### Expected Response Time
- **POST Target:** < 300ms
- **GET Recall Target:** < 200ms
- **Maximum acceptable:** < 500ms for both

### Caching Strategy
- **Strategy:** No response caching; inventory cache invalidated on POST
- **Cache key:** `tenant:{tenant_id}:inventory:*` (DELETED on POST)

### Database Performance

**POST Queries:** 4-5 (item validation, patient validation, insert placement, atomic update inventory, insert history)

**GET Queries:** 1 (single JOIN query for recall search)

**Indexes required:**
- `implant_placements.(tenant_id, lot_number)` — COMPOSITE INDEX for recall search
- `implant_placements.(tenant_id, patient_id)` — COMPOSITE INDEX for patient history
- `implant_placements.(tenant_id, item_id)` — COMPOSITE INDEX for item traceability
- `implant_placements.placement_date` — INDEX for date filtering
- `inventory_items.(tenant_id, id, category)` — for category validation
- `lot_number` — additional GIN-like index for ILIKE: `CREATE INDEX ON implant_placements (tenant_id, lot_number varchar_pattern_ops)`

**N+1 prevention:** Recall search uses single JOIN query. POST creates records in single transaction.

### Pagination

**Pagination:** POST — No. GET — No (recall search returns all affected patients; bounded by clinic patient count per lot).

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| item_id (URL) | Pydantic UUID | |
| patient_id | Pydantic UUID | |
| tooth_number | Pydantic int, ge=11, le=85 | FDI range |
| lot_number (POST) | Pydantic strip(), max_length=100, `re.sub(r'[^\w\-]', '', v)` | |
| lot_number (GET) | Pydantic strip(), min_length=3, max_length=100 | ILIKE pattern |
| serial_number | Pydantic strip(), max_length=100 | |
| manufacturer | Pydantic strip(), max_length=200, bleach.clean | |
| notes | Pydantic strip(), max_length=1000, bleach.clean | May contain PHI |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL. ILIKE uses bound parameter (`%:lot%`), not string interpolation.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields (POST):** patient_id, notes (surgical information), tooth_number (clinical data)
**PHI fields (GET):** patient first_name, last_name, document_number, phone, email

**Audit requirement:** Both POST and GET recall search are fully audit logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Link implant to patient procedure
   - **Given:** Authenticated doctor, implant item with quantity=3, valid patient, FDI tooth 46
   - **When:** POST /api/v1/inventory/implants/{id}/link with valid body
   - **Then:** 201 Created, quantity_after=2, placement record created, inventory history entry created, cache invalidated

2. Recall search finds affected patients
   - **Given:** 2 placements with same lot_number="IMPL-BATCH-2025-03"
   - **When:** GET /api/v1/inventory/implants/search?lot_number=IMPL-BATCH-2025-03
   - **Then:** 200 OK, total_affected=2, both patients with contact info returned

3. Partial lot number search
   - **Given:** Placements with lots "IMPL-BATCH-2025-03" and "IMPL-BATCH-2025-04"
   - **When:** GET with lot_number=IMPL-BATCH-2025
   - **Then:** Both placements returned

4. Last unit placement triggers low stock alert
   - **Given:** Implant with quantity=1, minimum_stock=1
   - **When:** POST link
   - **Then:** 201 Created, quantity_after=0, RabbitMQ low_stock_alert dispatched

#### Edge Cases
1. Race condition — two concurrent placements on last unit
   - **Given:** Implant with quantity=1
   - **When:** Two simultaneous POST requests
   - **Then:** One gets 201; the other gets 409 (optimistic locking)

2. Recall search finds no patients
   - **Given:** lot_number="UNKNOWN-LOT"
   - **When:** GET search
   - **Then:** 200 OK, total_affected=0, affected_patients=[]

#### Error Cases
1. item is not an implant (category=material)
   - **Given:** item_id pointing to a material
   - **When:** POST link
   - **Then:** 404 with "not an implant" message

2. Item out of stock (quantity=0)
   - **Given:** Implant with quantity=0
   - **When:** POST link
   - **Then:** 409 out_of_stock

3. tooth_number outside FDI range (e.g. 99)
   - **Given:** tooth_number=99
   - **When:** POST
   - **Then:** 422 validation error

4. placement_date in the future
   - **Given:** placement_date = tomorrow
   - **When:** POST
   - **Then:** 422 validation error

5. Assistant tries to link implant
   - **Given:** Authenticated assistant
   - **When:** POST link
   - **Then:** 403 Forbidden

6. Doctor tries recall search
   - **Given:** Authenticated doctor
   - **When:** GET recall search
   - **Then:** 403 Forbidden

7. lot_number less than 3 chars
   - **Given:** lot_number="AB" (2 chars)
   - **When:** GET search
   - **Then:** 400 Bad Request

### Test Data Requirements

**Users:** doctor, clinic_owner, assistant (for recall search), receptionist (for 403 tests)

**Inventory Items:** Implant with quantity=3 (for successful links); implant with quantity=0 (for out-of-stock); material item (for wrong-category test)

**Patients:** Active patient in tenant

**Existing Placements:** 2 placements with same lot_number for recall search test

### Mocking Strategy

- Database: PostgreSQL test instance recommended (for atomic UPDATE WHERE and RETURNING compatibility)
- Redis: `fakeredis` for cache invalidation
- RabbitMQ: Mock publish; assert low_stock_alert on threshold crossing

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/inventory/implants/{id}/link returns 201 with placement and updated quantity
- [ ] item must be category=implant (404 for others)
- [ ] Inventory quantity decremented atomically (race condition safe via UPDATE WHERE quantity > 0)
- [ ] Inventory quantity history entry created with reason=consumed
- [ ] patient_id, tooth_number (FDI), placement_date all validated
- [ ] GET recall search returns all patients who received implants with matching lot_number
- [ ] ILIKE enables partial lot number search
- [ ] Recall search returns patient contact information
- [ ] Both endpoints audit logged with PHI flag
- [ ] Only clinic_owner and doctor can link; only clinic_owner and assistant can recall search
- [ ] Out of stock returns 409
- [ ] Inventory cache invalidated after successful POST
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms POST, < 200ms GET)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating inventory items (see INV-01)
- Viewing all implant placements for a patient (patient history spec)
- Cross-tenant recall searches (superadmin function)
- Implant follow-up scheduling (treatment plans domain)
- Implant removal recording (separate spec)
- Integration with manufacturer recall databases

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] Two endpoints defined (POST link + GET recall search)
- [x] All inputs defined for both
- [x] All outputs defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (different roles for each endpoint)
- [x] Side effects listed (atomic decrement + history)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Atomic quantity decrement (UPDATE WHERE quantity > 0 + RETURNING)
- [x] Traceability chain documented
- [x] FDI notation enforced
- [x] Tenant isolation

### Hook 3: Security & Privacy
- [x] PHI audit log for both POST and recall search
- [x] ILIKE parameterized (not interpolated)
- [x] lot_number sanitized
- [x] Notes may contain PHI — sanitized

### Hook 4: Performance & Scalability
- [x] Targets defined (POST vs GET)
- [x] Race condition handled (optimistic locking)
- [x] ILIKE index documented
- [x] Cache invalidation on POST

### Hook 5: Observability
- [x] Audit log (PHI + regulatory flags)
- [x] RabbitMQ alert on low stock
- [x] Structured logging

### Hook 6: Testability
- [x] Test cases enumerated (including race condition)
- [x] PostgreSQL recommended for atomic ops
- [x] RabbitMQ mock strategy
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
