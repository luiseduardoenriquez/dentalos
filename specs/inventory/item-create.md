# INV-01 Create Inventory Item Spec

---

## Overview

**Feature:** Create a new item in the clinic's inventory. Tracks materials, instruments, implants, and medications with lot numbers, expiry dates, costs, supplier info, and minimum stock thresholds. A PostgreSQL generated column computes `expiry_status` dynamically based on the expiry date. Accessible by clinic_owner and assistant roles.

**Domain:** inventory

**Priority:** Low

**Dependencies:** infra/authentication-rules.md, infra/multi-tenancy.md, infra/audit-logging.md, INV-02 (item-list.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Doctors and receptionists cannot create inventory items. Assistants can create items but not delete them (soft-delete by setting quantity=0 is handled via INV-03).

---

## Endpoint

```
POST /api/v1/inventory/items
```

**Rate Limiting:**
- 60 requests per minute per user
- Redis sliding window: `dentalos:rl:inventory_create:{user_id}` (TTL 60s)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "name": "string (required) — item name, max 200 chars",
  "category": "string (required) — enum: material, instrument, implant, medication",
  "quantity": "number (required) — current stock, >= 0",
  "unit": "string (required) — enum: units, ml, g, boxes",
  "lot_number": "string (optional) — manufacturer lot/batch number, max 100 chars",
  "expiry_date": "string (optional) — ISO 8601 date, e.g. 2027-06-30",
  "manufacturer": "string (optional) — manufacturer name, max 200 chars",
  "supplier": "string (optional) — supplier/vendor name, max 200 chars",
  "cost_per_unit": "integer (optional) — cost in cents of tenant currency, >= 0",
  "minimum_stock": "number (optional) — alert threshold, default 0",
  "location": "string (optional) — storage location in clinic, max 100 chars, e.g. Gabinete A3"
}
```

**Example Request:**
```json
{
  "name": "Resina Compuesta A2",
  "category": "material",
  "quantity": 24,
  "unit": "units",
  "lot_number": "LOT-2025-081234",
  "expiry_date": "2027-08-31",
  "manufacturer": "3M ESPE",
  "supplier": "Dental Depot Colombia",
  "cost_per_unit": 45000,
  "minimum_stock": 5,
  "location": "Gabinete B2"
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
  "name": "string",
  "category": "string",
  "quantity": "number",
  "unit": "string",
  "lot_number": "string | null",
  "expiry_date": "string ISO 8601 date | null",
  "expiry_status": "string — generated: ok | warning | critical | expired",
  "manufacturer": "string | null",
  "supplier": "string | null",
  "cost_per_unit": "integer | null — cents",
  "minimum_stock": "number",
  "is_low_stock": "boolean — quantity < minimum_stock",
  "location": "string | null",
  "created_at": "string ISO 8601",
  "created_by": "uuid"
}
```

**Example:**
```json
{
  "id": "inv-aabb-1122-ccdd-3344-eeff55667788",
  "name": "Resina Compuesta A2",
  "category": "material",
  "quantity": 24,
  "unit": "units",
  "lot_number": "LOT-2025-081234",
  "expiry_date": "2027-08-31",
  "expiry_status": "ok",
  "manufacturer": "3M ESPE",
  "supplier": "Dental Depot Colombia",
  "cost_per_unit": 45000,
  "minimum_stock": 5,
  "is_low_stock": false,
  "location": "Gabinete B2",
  "created_at": "2026-02-25T09:00:00-05:00",
  "created_by": "usr-assistant-0001-000000000000"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or missing required fields.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud contiene errores.",
  "details": {
    "name": ["El nombre del item es requerido."],
    "category": ["La categoria es requerida."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor or receptionist attempts to create inventory items.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para crear items de inventario."
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails — invalid category, quantity < 0, expiry_date in the past (warning allowed), invalid unit.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Los datos del item de inventario contienen errores.",
  "details": {
    "category": ["Categoria invalida. Opciones: material, instrument, implant, medication."],
    "quantity": ["La cantidad no puede ser negativa."],
    "unit": ["Unidad invalida. Opciones: units, ml, g, boxes."]
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

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. Check role: if not `clinic_owner` or `assistant`, return 403.
3. Validate request body against Pydantic schema.
4. Validate individual fields:
   - `quantity` >= 0 (zero is valid — item exists but out of stock).
   - `cost_per_unit` >= 0 if provided.
   - `minimum_stock` >= 0, default 0.
   - `expiry_date`: if provided, must be a valid ISO 8601 date. Past expiry dates are allowed (item may have already expired on entry — `expiry_status` will reflect this). Warn but do not reject.
5. Set `search_path` to tenant schema.
6. Insert into `inventory_items` table. The `expiry_status` column is a PostgreSQL generated column (GENERATED ALWAYS AS):
   ```sql
   expiry_status VARCHAR GENERATED ALWAYS AS (
     CASE
       WHEN expiry_date IS NULL THEN 'ok'
       WHEN expiry_date < CURRENT_DATE THEN 'expired'
       WHEN expiry_date < CURRENT_DATE + INTERVAL '30 days' THEN 'critical'
       WHEN expiry_date < CURRENT_DATE + INTERVAL '60 days' THEN 'warning'
       ELSE 'ok'
     END
   ) STORED
   ```
7. Compute `is_low_stock = quantity < minimum_stock` in application layer for response.
8. Write audit log: action `create`, resource `inventory_item`.
9. Invalidate inventory list cache: `tenant:{tenant_id}:inventory:items:*`.
10. Return 201 with the created item including computed `expiry_status`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| name | Non-empty, max 200 chars | El nombre es requerido y no puede superar 200 caracteres. |
| category | Enum: material, instrument, implant, medication | Categoria invalida. |
| quantity | Number >= 0 | La cantidad no puede ser negativa. |
| unit | Enum: units, ml, g, boxes | Unidad invalida. |
| cost_per_unit | Integer >= 0 (if provided) | El costo no puede ser negativo. |
| minimum_stock | Number >= 0 (if provided) | El stock minimo no puede ser negativo. |
| lot_number | Max 100 chars (if provided) | El numero de lote no puede superar 100 caracteres. |
| expiry_date | Valid ISO 8601 date (if provided) — past dates allowed with warning | Formato de fecha invalido. |
| location | Max 100 chars (if provided) | La ubicacion no puede superar 100 caracteres. |
| manufacturer | Max 200 chars (if provided) | El fabricante no puede superar 200 caracteres. |
| supplier | Max 200 chars (if provided) | El proveedor no puede superar 200 caracteres. |

**Business Rules:**

- `expiry_status` is a PostgreSQL GENERATED ALWAYS AS STORED column. It is computed by the database automatically and cannot be set by the application. The application reads the value from the DB after insert.
- `quantity` allows decimals for liquid/weight items (e.g., 250.5 ml). `minimum_stock` also allows decimals.
- `cost_per_unit` is stored in integer cents of the tenant's currency. For liquids/weight, it represents cost per base unit (per 1 ml, per 1 g, per 1 box).
- Items with `category = 'implant'` must be trackable to specific patient procedures via INV-07. Creating an implant item does not automatically start tracking — tracking begins when the implant is linked via INV-07.
- `is_low_stock` is computed in the application layer as `quantity < minimum_stock`. If `minimum_stock = 0`, `is_low_stock` is always false.
- An item with `expiry_date` in the past is allowed to be created (e.g., when entering existing inventory that has already expired for disposal tracking). The `expiry_status` will immediately be `expired`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| expiry_date = today | expiry_status=critical (within 30 days — today is < today + 30 days) |
| expiry_date = yesterday (past) | expiry_status=expired; item created with warning in response |
| expiry_date = null | expiry_status=ok |
| quantity = 0, minimum_stock = 0 | is_low_stock=false |
| quantity = 0, minimum_stock = 5 | is_low_stock=true |
| quantity = 2.5 (liquid) | Valid; stored as numeric |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `inventory_items`: INSERT — new item with generated expiry_status
- `audit_logs`: INSERT — item creation event

**Example query (SQLAlchemy):**
```python
item = InventoryItem(
    tenant_id=tenant_id,
    name=data.name,
    category=data.category,
    quantity=data.quantity,
    unit=data.unit,
    lot_number=data.lot_number,
    expiry_date=data.expiry_date,
    manufacturer=data.manufacturer,
    supplier=data.supplier,
    cost_per_unit=data.cost_per_unit,
    minimum_stock=data.minimum_stock or 0,
    location=data.location,
    created_by=user_id,
)
session.add(item)
await session.flush()
# expiry_status is a GENERATED ALWAYS AS column — read from DB after flush
await session.refresh(item)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:inventory:items:*`: DELETE pattern — invalidate all paginated list caches and alert counts

**Cache TTL:** N/A — deletion only

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None on item creation.

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** inventory_item
- **PHI involved:** No — operational data

### Notifications

**Notifications triggered:** No on creation.

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on write; invalidates list cache
- **Cache key:** `tenant:{tenant_id}:inventory:items:*` (DELETED)
- **TTL:** N/A

### Database Performance

**Queries executed:** 2 (insert, refresh to get generated column)

**Indexes required:**
- `inventory_items.(tenant_id, category)` — COMPOSITE INDEX for list filtering
- `inventory_items.(tenant_id, expiry_date)` — COMPOSITE INDEX for expiry-sorted queries
- `inventory_items.(tenant_id, expiry_status)` — COMPOSITE INDEX (since it's a stored generated column)
- `inventory_items.lot_number` — INDEX for lot-based searches (INV-07)

**N+1 prevention:** Not applicable — single item insert.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| name | Pydantic strip(), max_length=200, bleach.clean | May appear in reports |
| category | Pydantic enum | Whitelist |
| unit | Pydantic enum | Whitelist |
| lot_number | Pydantic strip(), max_length=100, alphanumeric + hyphens | Traceability field |
| manufacturer, supplier | Pydantic strip(), max_length=200 | |
| location | Pydantic strip(), max_length=100 | |
| expiry_date | Pydantic date | Strict ISO 8601 |
| cost_per_unit | Pydantic int, ge=0 | Integer cents |
| quantity, minimum_stock | Pydantic float, ge=0 | Allows decimals |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — inventory data is operational, not clinical.

**Audit requirement:** Write operation logged (no PHI).

---

## Testing

### Test Cases

#### Happy Path
1. Create material with expiry date (ok status)
   - **Given:** Authenticated assistant, valid request body, expiry_date = 2 years from now
   - **When:** POST /api/v1/inventory/items
   - **Then:** 201 Created, expiry_status=ok, is_low_stock=false (quantity=24, minimum_stock=5)

2. Create implant category item
   - **Given:** clinic_owner role, category=implant
   - **When:** POST
   - **Then:** 201 Created, category=implant

3. Create item with expiry in 20 days (critical)
   - **Given:** expiry_date = today + 20 days
   - **When:** POST
   - **Then:** 201 Created, expiry_status=critical

4. Create item with past expiry (expired on entry)
   - **Given:** expiry_date = yesterday
   - **When:** POST
   - **Then:** 201 Created, expiry_status=expired

5. Create liquid item with decimal quantity
   - **Given:** quantity=250.5, unit=ml
   - **When:** POST
   - **Then:** 201 Created, quantity=250.5

#### Error Cases
1. Doctor role
   - **Given:** Authenticated doctor
   - **When:** POST
   - **Then:** 403 Forbidden

2. Negative quantity
   - **Given:** quantity=-1
   - **When:** POST
   - **Then:** 422 validation error

3. Invalid category
   - **Given:** category=unknown
   - **When:** POST
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** assistant, clinic_owner, doctor (for 403)

### Mocking Strategy

- Database: SQLite in-memory (note: GENERATED ALWAYS AS is PostgreSQL-specific; in tests compute expiry_status in application layer as fallback for SQLite compatibility)
- Redis: `fakeredis` for cache invalidation verification

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/inventory/items returns 201 with created item
- [ ] expiry_status correctly computed via PostgreSQL GENERATED ALWAYS column
- [ ] is_low_stock computed correctly (quantity < minimum_stock)
- [ ] category=implant items creatable (for INV-07 tracking)
- [ ] Decimal quantities supported (for ml and g units)
- [ ] Only clinic_owner and assistant can create (403 for others)
- [ ] Inventory list cache invalidated
- [ ] Audit log written
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing inventory items (see INV-02)
- Updating quantity or other fields (see INV-03)
- Viewing alerts (see INV-04)
- Sterilization tracking (see INV-05, INV-06)
- Implant-to-patient linking (see INV-07)
- Barcode/QR scanning integration (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (full item schema)
- [x] All outputs defined (item with generated expiry_status)
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (clinic_owner, assistant)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] PostgreSQL GENERATED ALWAYS AS column documented
- [x] Tenant schema isolation
- [x] Matches FastAPI conventions

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization defined
- [x] No PHI
- [x] SQL injection prevented

### Hook 4: Performance & Scalability
- [x] Target < 200ms
- [x] Cache invalidation on write
- [x] Indexes for filtered queries

### Hook 5: Observability
- [x] Audit log (non-PHI)
- [x] Structured logging

### Hook 6: Testability
- [x] Test cases enumerated
- [x] SQLite GENERATED ALWAYS fallback documented
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
