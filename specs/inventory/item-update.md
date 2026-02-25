# INV-03 Update Inventory Item Spec

---

## Overview

**Feature:** Update an inventory item's quantity (with tracked reason) or other metadata fields. Quantity adjustments use an increment/decrement model with a mandatory reason code (received/consumed/discarded/adjustment). All quantity changes are recorded in a `quantity_history` array to provide a full audit trail of stock movements. Other updatable fields include lot_number, expiry_date, cost_per_unit, and minimum_stock.

**Domain:** inventory

**Priority:** Low

**Dependencies:** INV-01 (item-create.md), INV-02 (item-list.md), infra/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Same as creation — doctors and receptionists cannot modify inventory. Assistants can adjust quantities and update metadata. clinic_owner can perform all operations.

---

## Endpoint

```
PUT /api/v1/inventory/items/{item_id}
```

**Rate Limiting:**
- 60 requests per minute per user

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
| item_id | Yes | UUID | UUID v4, must exist in tenant | Inventory item to update | inv-aabb-1122-ccdd-3344-eeff55667788 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "quantity_delta": "number (optional) — signed number: positive to add stock, negative to remove. e.g. +10 means received 10 units, -3 means consumed 3",
  "quantity_reason": "string (required if quantity_delta provided) — enum: received, consumed, discarded, adjustment",
  "quantity_notes": "string (optional) — additional context for the quantity change, max 500 chars",
  "lot_number": "string (optional) — update lot number, max 100 chars",
  "expiry_date": "string | null (optional) — update expiry date or null to clear",
  "cost_per_unit": "integer (optional) — update cost in cents, >= 0",
  "minimum_stock": "number (optional) — update minimum stock threshold, >= 0",
  "location": "string | null (optional) — update storage location, max 100 chars",
  "name": "string (optional) — update item name, max 200 chars",
  "supplier": "string | null (optional) — update supplier name, max 200 chars"
}
```

**Example Request — receive stock:**
```json
{
  "quantity_delta": 12,
  "quantity_reason": "received",
  "quantity_notes": "Pedido de febrero 2026 - Factura #12345"
}
```

**Example Request — consume materials:**
```json
{
  "quantity_delta": -3,
  "quantity_reason": "consumed",
  "quantity_notes": "Utilizado en procedimientos del dia 25/02/2026"
}
```

**Example Request — update metadata only:**
```json
{
  "lot_number": "LOT-2026-011234",
  "expiry_date": "2028-01-31",
  "cost_per_unit": 48000,
  "minimum_stock": 8
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
  "name": "string",
  "category": "string",
  "quantity": "number — new quantity after delta applied",
  "unit": "string",
  "lot_number": "string | null",
  "expiry_date": "string ISO 8601 date | null",
  "expiry_status": "string — recomputed: ok | warning | critical | expired",
  "semaphore_color": "string — green | yellow | orange | red",
  "manufacturer": "string | null",
  "supplier": "string | null",
  "cost_per_unit": "integer | null",
  "minimum_stock": "number",
  "is_low_stock": "boolean",
  "location": "string | null",
  "last_quantity_change": {
    "delta": "number",
    "reason": "string",
    "notes": "string | null",
    "user_id": "uuid",
    "timestamp": "string ISO 8601"
  },
  "updated_at": "string ISO 8601",
  "updated_by": "uuid"
}
```

**Example:**
```json
{
  "id": "inv-aabb-1122-ccdd-3344-eeff55667788",
  "name": "Resina Compuesta A2",
  "category": "material",
  "quantity": 36,
  "unit": "units",
  "lot_number": "LOT-2025-081234",
  "expiry_date": "2027-08-31",
  "expiry_status": "ok",
  "semaphore_color": "green",
  "manufacturer": "3M ESPE",
  "supplier": "Dental Depot Colombia",
  "cost_per_unit": 45000,
  "minimum_stock": 5,
  "is_low_stock": false,
  "location": "Gabinete B2",
  "last_quantity_change": {
    "delta": 12,
    "reason": "received",
    "notes": "Pedido de febrero 2026 - Factura #12345",
    "user_id": "usr-assistant-0001-000000000000",
    "timestamp": "2026-02-25T10:00:00-05:00"
  },
  "updated_at": "2026-02-25T10:00:00-05:00",
  "updated_by": "usr-assistant-0001-000000000000"
}
```

### Error Responses

#### 400 Bad Request
**When:** `quantity_delta` provided without `quantity_reason`, or no updateable fields in request body.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El motivo del ajuste de cantidad es requerido.",
  "details": {
    "quantity_reason": ["Debe especificar el motivo cuando se ajusta la cantidad."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor or receptionist role.

#### 404 Not Found
**When:** `item_id` does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "El item de inventario no fue encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Resulting quantity would be negative, invalid quantity_reason enum, invalid field values.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "La actualizacion del inventario contiene errores.",
  "details": {
    "quantity_delta": ["La cantidad resultante no puede ser negativa. Cantidad actual: 2, delta: -5."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`. If not `clinic_owner` or `assistant`, return 403.
2. Validate `item_id` as UUID v4.
3. Validate request body. At least one field must be present.
4. If `quantity_delta` is present, `quantity_reason` must also be present.
5. Set `search_path` to tenant schema.
6. Load existing item: `SELECT * FROM inventory_items WHERE id = :item_id AND tenant_id = :tenant_id`. If not found, return 404.
7. If `quantity_delta` provided:
   a. Validate `quantity_reason` enum: received, consumed, discarded, adjustment.
   b. Compute new_quantity = `existing_item.quantity + quantity_delta`.
   c. If `new_quantity < 0`, return 422 with message showing current quantity and delta.
8. Build update dict (only provided fields — partial update).
9. Begin database transaction.
10. If `quantity_delta` provided:
    a. UPDATE `inventory_items SET quantity = new_quantity WHERE id = :item_id`.
    b. INSERT into `inventory_quantity_history`: `item_id`, `delta = quantity_delta`, `reason`, `notes = quantity_notes`, `previous_quantity = existing_quantity`, `new_quantity`, `user_id`, `timestamp = now()`.
11. Apply other field updates to `inventory_items` (name, lot_number, expiry_date, cost_per_unit, minimum_stock, location, supplier) with `updated_at = now()`, `updated_by = user_id`.
12. Commit transaction.
13. Reload item from DB to get fresh `expiry_status` (recomputed by generated column if expiry_date changed).
14. Write audit log: action=update, resource=inventory_item, includes quantity_delta and reason if applicable.
15. Invalidate inventory cache: DELETE `tenant:{tenant_id}:inventory:*`.
16. Return 200 with updated item.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| item_id (URL) | Valid UUID v4, must exist in tenant | El item de inventario no fue encontrado. |
| quantity_delta | Number (positive or negative), if provided: new_quantity >= 0 | La cantidad resultante no puede ser negativa. |
| quantity_reason | Required if quantity_delta present; enum: received, consumed, discarded, adjustment | Debe especificar el motivo del ajuste. |
| quantity_notes | Max 500 chars (if provided) | Las notas no pueden superar 500 caracteres. |
| cost_per_unit | Integer >= 0 (if provided) | El costo no puede ser negativo. |
| minimum_stock | Number >= 0 (if provided) | El stock minimo no puede ser negativo. |
| name | Non-empty, max 200 chars (if provided) | El nombre no puede estar vacio ni superar 200 caracteres. |
| lot_number | Max 100 chars (if provided) | El numero de lote no puede superar 100 caracteres. |
| location | Max 100 chars (if provided) | La ubicacion no puede superar 100 caracteres. |
| body | At least one field must be present | No hay campos para actualizar. |

**Business Rules:**

- `quantity_delta` is a signed number: positive = adding stock (received), negative = removing stock (consumed/discarded). The application validates the resulting quantity will not go below 0.
- The `quantity_history` table is append-only. It records every stock movement with timestamp, reason, user_id, and delta. This provides a complete audit trail for compliance and discrepancy investigation.
- `category`, `manufacturer`, and `unit` are immutable after creation (they define what the item fundamentally is). Changing these requires creating a new item.
- `expiry_date` can be updated when a new lot is received with a different expiry. Setting to null removes expiry tracking for this item. The `expiry_status` generated column is automatically recomputed by PostgreSQL.
- `reason` values are: `received` (new stock arrived), `consumed` (used in procedures), `discarded` (expired or damaged), `adjustment` (correction after physical inventory count).
- The `last_quantity_change` block in the response contains the most recent history entry if `quantity_delta` was provided in this request. If only metadata was updated, it reflects the last historical change.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| quantity_delta = +0 | Accepted; inserts history entry with delta=0, reason required |
| quantity = 0, quantity_delta = -1 | 422 — resulting quantity would be -1 |
| Only metadata update (no quantity_delta) | No history entry created; only fields updated |
| expiry_date updated to null | expiry_status recomputed to ok (no expiry date = no expiry risk) |
| expiry_date updated to next week | expiry_status recomputed to critical |
| Item is category=implant | Same update rules; quantity tracking critical for implant accountability |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `inventory_items`: UPDATE — quantity and/or metadata fields, updated_at, updated_by
- `inventory_quantity_history`: INSERT (conditional) — when quantity_delta is provided
- `audit_logs`: INSERT — update event

**Example query (SQLAlchemy):**
```python
async with session.begin():
    # Quantity adjustment
    if data.quantity_delta is not None:
        new_qty = existing_item.quantity + data.quantity_delta
        if new_qty < 0:
            raise ValidationError(f"Resulting quantity {new_qty} cannot be negative.")
        await session.execute(
            update(InventoryItem)
            .where(InventoryItem.id == item_id)
            .values(quantity=new_qty, updated_at=datetime.utcnow(), updated_by=user_id)
        )
        session.add(InventoryQuantityHistory(
            item_id=item_id,
            delta=data.quantity_delta,
            reason=data.quantity_reason,
            notes=data.quantity_notes,
            previous_quantity=existing_item.quantity,
            new_quantity=new_qty,
            user_id=user_id,
            timestamp=datetime.utcnow(),
        ))
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:inventory:*`: DELETE pattern — all inventory caches invalidated

**Cache TTL:** N/A — deletion only

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None for standard updates. If quantity goes below `minimum_stock` after an update, the alert job is triggered:

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | inventory.low_stock_alert | { tenant_id, item_id, item_name, quantity, minimum_stock } | When new_quantity < minimum_stock AND previous_quantity >= minimum_stock (threshold crossing) |

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** inventory_item
- **PHI involved:** No

### Notifications

**Notifications triggered:** Conditionally — only when stock falls below minimum threshold (threshold crossing, not already below).

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on write; pattern DELETE on inventory caches
- **Cache key:** `tenant:{tenant_id}:inventory:*` (DELETED)
- **TTL:** N/A

### Database Performance

**Queries executed:** 3 (load item, update item, optional history insert)

**Indexes required:**
- `inventory_items.(tenant_id, id)` — COMPOSITE UNIQUE INDEX
- `inventory_quantity_history.item_id` — INDEX for history queries
- `inventory_quantity_history.(item_id, timestamp DESC)` — COMPOSITE INDEX for recent history

**N+1 prevention:** Not applicable — single item update.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| item_id (URL) | Pydantic UUID | |
| quantity_delta | Pydantic float | Signed decimal |
| quantity_reason | Pydantic enum | Whitelist |
| quantity_notes | Pydantic strip(), max_length=500, bleach.clean | |
| name | Pydantic strip(), max_length=200, bleach.clean | |
| lot_number | Pydantic strip(), max_length=100, `re.sub(r'[^\w\-]', '', lot)` | Alphanumeric + hyphens only |
| cost_per_unit | Pydantic int, ge=0 | Integer cents |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — operational inventory data.

**Audit requirement:** Write operation logged (no PHI).

---

## Testing

### Test Cases

#### Happy Path
1. Receive stock (positive delta)
   - **Given:** Authenticated assistant, item with quantity=24
   - **When:** PUT with quantity_delta=12, quantity_reason=received
   - **Then:** 200 OK, quantity=36, history entry created, cache invalidated

2. Consume materials (negative delta)
   - **Given:** Item with quantity=10
   - **When:** PUT with quantity_delta=-3, quantity_reason=consumed
   - **Then:** 200 OK, quantity=7

3. Metadata-only update (lot_number + expiry_date)
   - **Given:** Item with old lot_number and expiry_date
   - **When:** PUT with new lot_number and extended expiry_date
   - **Then:** 200 OK, lot_number and expiry_date updated, expiry_status recomputed

4. Low stock threshold crossing dispatches notification
   - **Given:** Item with quantity=6, minimum_stock=5; quantity_delta=-2 will bring it to 4
   - **When:** PUT with quantity_delta=-2, reason=consumed
   - **Then:** 200 OK, is_low_stock=true, RabbitMQ low_stock_alert dispatched

#### Edge Cases
1. quantity_delta = 0
   - **Given:** Any item, quantity_delta=0, reason=adjustment
   - **When:** PUT
   - **Then:** 200 OK, quantity unchanged, history entry with delta=0 created

2. Update only minimum_stock (no quantity_delta)
   - **Given:** Item with minimum_stock=3
   - **When:** PUT with minimum_stock=10 only
   - **Then:** 200 OK, minimum_stock updated, is_low_stock possibly changes

#### Error Cases
1. quantity_delta present but no quantity_reason
   - **Given:** quantity_delta=5, no reason
   - **When:** PUT
   - **Then:** 400 Bad Request

2. Resulting quantity negative
   - **Given:** Item with quantity=2, quantity_delta=-5
   - **When:** PUT
   - **Then:** 422 with negative quantity error showing current quantity

3. Doctor role
   - **Given:** Authenticated doctor
   - **When:** PUT
   - **Then:** 403 Forbidden

4. item_id not in tenant
   - **Given:** Non-existent UUID
   - **When:** PUT
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** assistant, clinic_owner, doctor (403 test)

**Inventory Items:** Items with known quantities and minimum_stock values

### Mocking Strategy

- Redis: `fakeredis` for cache invalidation
- RabbitMQ: Mock publish; assert low_stock_alert only on threshold crossing

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] PUT returns 200 with updated item
- [ ] Quantity delta applied correctly (positive and negative)
- [ ] Resulting negative quantity rejected with 422
- [ ] quantity_reason required when quantity_delta present
- [ ] History entry created in inventory_quantity_history for each quantity change
- [ ] Metadata updates (lot_number, expiry_date, cost, minimum_stock) work independently
- [ ] expiry_status recomputed after expiry_date change
- [ ] Low stock alert dispatched to RabbitMQ when crossing threshold
- [ ] All inventory caches invalidated
- [ ] Audit log written
- [ ] Only clinic_owner and assistant can update (403 for others)
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating inventory items (see INV-01)
- Viewing quantity history (available as sub-resource, separate spec)
- Bulk quantity updates for multiple items
- Changing item category or unit (immutable)
- Sterilization tracking (see INV-05, INV-06)
- Implant linking (see INV-07)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (delta + reason + metadata fields)
- [x] All outputs defined (updated item + last_quantity_change)
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed (history insert, RabbitMQ conditional)
- [x] Examples provided (receive and consume)

### Hook 2: Architecture Compliance
- [x] Append-only quantity_history pattern
- [x] Category/unit immutability documented
- [x] Tenant isolation enforced

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] lot_number sanitized (alphanumeric only)
- [x] No PHI

### Hook 4: Performance & Scalability
- [x] Target < 200ms
- [x] Cache pattern delete on write
- [x] History table indexed

### Hook 5: Observability
- [x] Audit log (quantity_delta, reason)
- [x] RabbitMQ alert on threshold crossing
- [x] Structured logging

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Threshold crossing test case
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
