# B-15 Service Catalog Update Spec

---

## Overview

**Feature:** Update a service/procedure entry in the tenant's price catalog. Allows clinic_owner to modify the service name, description, default price, active status, or category. Invalidates the service catalog cache on any successful update. All changes are audit logged. Prices are stored in integer cents.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-14 (service-catalog.md), infra/caching.md, infra/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner may modify the service catalog. All other roles return 403. Superadmin may update as part of tenant administration.

---

## Endpoint

```
PUT /api/v1/billing/services/{service_id}
```

**Rate Limiting:**
- 30 requests per minute per user (catalog updates are infrequent; lower limit than read operations)
- Redis sliding window: `dentalos:rl:service_update:{user_id}` (TTL 60s)

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
| service_id | Yes | UUID | UUID v4, must exist in tenant | ID of the service to update | svc-aabb-1122-ccdd-3344-eeff55667788 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "name": "string (optional) — service name, max 200 chars",
  "description": "string | null (optional) — detailed description, max 1000 chars; null to clear",
  "default_price": "integer (optional) — price in cents, min 0",
  "is_active": "boolean (optional) — activate or deactivate this service",
  "category": "string (optional) — enum: diagnostico, cirugia, periodoncia, operatoria, endodoncia, protesis, ortodoncia, prevencion, otros"
}
```

**Example Request — price update only:**
```json
{
  "default_price": 85000
}
```

**Example Request — full update:**
```json
{
  "name": "Resina Compuesta Posterior",
  "description": "Restauracion con resina compuesta de 2 o mas superficies en diente posterior.",
  "default_price": 90000,
  "is_active": true,
  "category": "operatoria"
}
```

**Example Request — deactivate service:**
```json
{
  "is_active": false
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
  "cups_code": "string | null",
  "name": "string",
  "description": "string | null",
  "default_price": "integer — cents",
  "category": "string",
  "is_active": "boolean",
  "updated_at": "string ISO 8601",
  "updated_by": "uuid"
}
```

**Example:**
```json
{
  "id": "svc-aabb-1122-ccdd-3344-eeff55667788",
  "cups_code": "895101",
  "name": "Resina Compuesta Posterior",
  "description": "Restauracion con resina compuesta de 2 o mas superficies en diente posterior.",
  "default_price": 90000,
  "category": "operatoria",
  "is_active": true,
  "updated_at": "2026-02-25T15:45:00-05:00",
  "updated_by": "usr-clinic-owner-0001-0000-000000000000"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or no updateable fields provided (empty body).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no contiene campos para actualizar.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Authenticated user does not have role `clinic_owner` or `superadmin`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede modificar el catalogo de servicios."
}
```

#### 404 Not Found
**When:** `service_id` does not exist in the tenant's service catalog.

**Example:**
```json
{
  "error": "not_found",
  "message": "El servicio no fue encontrado en el catalogo."
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails — name too long, price negative, invalid category, description too long.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Los datos del servicio contienen errores.",
  "details": {
    "default_price": ["El precio no puede ser negativo."],
    "name": ["El nombre no puede superar 200 caracteres."],
    "category": ["Categoria invalida. Opciones: diagnostico, cirugia, periodoncia, operatoria, endodoncia, protesis, ortodoncia, prevencion, otros."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. Check role: if not `clinic_owner` or `superadmin`, return 403.
3. Validate `service_id` URL parameter as UUID v4.
4. Validate request body against Pydantic schema. At least one field must be present. If empty body or all fields None, return 400.
5. Validate individual fields:
   - `name`: max 200 chars, non-empty string if provided.
   - `description`: max 1000 chars if provided (null is valid to clear the field).
   - `default_price`: integer >= 0 if provided. Zero means free/included. Negative not allowed.
   - `category`: must be in enum if provided.
   - `is_active`: boolean.
6. Set `search_path` to tenant schema.
7. Query `service_catalog WHERE id = :service_id AND tenant_id = :tenant_id`. If not found, return 404. Load the existing record for comparison in audit log.
8. Build update SET clause with only the provided fields (partial update — fields not in request body are not changed). Do not overwrite `cups_code` — it is immutable once set.
9. Set `updated_at = now()`, `updated_by = user_id`.
10. Execute UPDATE and commit.
11. Write audit log: action `update`, resource `service_catalog`, fields_changed (list of field names that changed), previous_values, new_values, tenant_id, user_id, service_id.
12. Invalidate service catalog cache: `DELETE tenant:{tenant_id}:billing:services:*` pattern (all cached queries for this tenant's catalog).
13. Return 200 with the updated service record.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| service_id (URL) | Valid UUID v4, must exist in tenant | El servicio no fue encontrado en el catalogo. |
| name | Non-empty string, max 200 chars (if provided) | El nombre es requerido y no puede superar 200 caracteres. |
| description | Max 1000 chars (if provided); null allowed to clear | La descripcion no puede superar 1000 caracteres. |
| default_price | Integer >= 0 (if provided) | El precio no puede ser negativo. |
| category | Enum value (if provided) | Categoria invalida. |
| body | At least one field must be present | El cuerpo de la solicitud no contiene campos para actualizar. |

**Business Rules:**

- This is a partial update (PATCH semantics, but uses PUT verb for simplicity). Only fields present in the request body are updated. Absent fields retain their current values.
- `cups_code` is intentionally excluded from the updatable fields. It is set at catalog initialization and is immutable. CUPS codes are standardized — changing them would break RIPS compliance reporting.
- `default_price = 0` is valid and means the procedure is included at no charge (common for follow-up consultations or bundled procedures).
- Deactivating a service (`is_active = false`) does not retroactively affect existing invoice items or quotations that reference this service. It only prevents the service from appearing in new invoice/quotation creation forms.
- The audit log captures both previous and new values for each changed field to support price history reconstruction. This is important for tax compliance and dispute resolution.
- Cache invalidation uses a wildcard pattern delete (`tenant:{tenant_id}:billing:services:*`) to clear all pages and search queries from cache. This is acceptable given the 30-minute TTL and infrequency of catalog updates.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| default_price = 0 | Valid — service marked as free |
| is_active toggled from true to false | Service hidden from catalog (is_active=true default filter); existing invoices unaffected |
| description: null | Description field cleared to null |
| name unchanged (same value as current) | Update proceeds; updated_at changes; audit log records no change on name field |
| Updating CUPS-seeded service (system default) | Allowed — tenant customization of default CUPS prices is the expected use case |
| Service_id valid UUID but from different tenant | Returns 404 (tenant isolation enforced) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `service_catalog`: UPDATE — partial update of provided fields plus updated_at, updated_by
- `audit_logs`: INSERT — catalog update event with field-level change tracking

**Example query (SQLAlchemy):**
```python
# Load existing for audit comparison
existing = await session.get(ServiceCatalog, service_id)
if not existing or existing.tenant_id != tenant_id:
    raise NotFoundError()

# Build update dict (only provided fields)
update_data = {}
if body.name is not None:
    update_data["name"] = body.name
if "description" in body.model_fields_set:  # explicitly provided, including null
    update_data["description"] = body.description
if body.default_price is not None:
    update_data["default_price"] = body.default_price
if body.is_active is not None:
    update_data["is_active"] = body.is_active
if body.category is not None:
    update_data["category"] = body.category

if not update_data:
    raise InvalidInputError("No fields to update")

update_data["updated_at"] = datetime.utcnow()
update_data["updated_by"] = user_id

await session.execute(
    update(ServiceCatalog)
    .where(ServiceCatalog.id == service_id, ServiceCatalog.tenant_id == tenant_id)
    .values(**update_data)
)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:billing:services:*`: DELETE pattern — all cached service catalog queries invalidated

**Cache TTL:** N/A — deletion only

**Cache invalidation strategy:** Use Redis `SCAN` + `DEL` pattern to delete all matching keys for the tenant's service catalog. This ensures any query combination (search, category, page) is refreshed.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** update
- **Resource:** service_catalog
- **PHI involved:** No — pricing data only

**Audit log payload:**
```json
{
  "action": "update",
  "resource": "service_catalog",
  "resource_id": "service_id",
  "tenant_id": "tenant_id",
  "user_id": "user_id",
  "changes": {
    "name": { "from": "old_name", "to": "new_name" },
    "default_price": { "from": 70000, "to": 85000 }
  }
}
```

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms (includes cache invalidation)

### Caching Strategy
- **Strategy:** No caching on write; invalidates existing cache
- **Cache key:** `tenant:{tenant_id}:billing:services:*` (DELETED)
- **TTL:** N/A
- **Invalidation:** Immediate pattern delete on successful commit

### Database Performance

**Queries executed:** 2 (SELECT existing, UPDATE)

**Indexes required:**
- `service_catalog.(tenant_id, id)` — COMPOSITE INDEX UNIQUE for efficient lookup and tenant isolation

**N+1 prevention:** Not applicable — single record update.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| service_id (URL) | Pydantic UUID validator | Prevents non-UUID path injection |
| name | Pydantic strip(), max_length=200, bleach.clean | May appear in invoices and PDFs |
| description | Pydantic strip(), max_length=1000, bleach.clean | May appear in invoices and PDFs |
| default_price | Pydantic int, ge=0 | Integer cents |
| category | Pydantic enum | Whitelist |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. `name` and `description` sanitized with `bleach.clean()` before storage since they render in invoices and quotation PDFs.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — service catalog contains pricing and procedure data only.

**Audit requirement:** Write-only logged (price and catalog changes).

---

## Testing

### Test Cases

#### Happy Path
1. Update price only
   - **Given:** Authenticated clinic_owner, existing service with default_price=70000
   - **When:** PUT /api/v1/billing/services/{id} with `{ "default_price": 85000 }`
   - **Then:** 200 OK, service returned with new price, other fields unchanged, cache invalidated, audit log created

2. Deactivate service
   - **Given:** Active service (is_active=true)
   - **When:** PUT with `{ "is_active": false }`
   - **Then:** 200 OK, is_active=false in response; service no longer appears in default catalog query

3. Full update with all fields
   - **Given:** Existing service
   - **When:** PUT with all updatable fields
   - **Then:** 200 OK, all fields updated, audit log records all changes

4. Clear description (set to null)
   - **Given:** Service with description set
   - **When:** PUT with `{ "description": null }`
   - **Then:** 200 OK, description=null in response

#### Edge Cases
1. default_price = 0 (free service)
   - **Given:** Service with default_price > 0
   - **When:** PUT with `{ "default_price": 0 }`
   - **Then:** 200 OK, default_price=0 in response

2. Name unchanged (same value)
   - **Given:** Service with name "Resina Compuesta"
   - **When:** PUT with `{ "name": "Resina Compuesta" }` (same name)
   - **Then:** 200 OK, updated_at changes, audit log shows name as unchanged (from==to)

3. cups_code not in request — not modified
   - **Given:** Service has cups_code=895101
   - **When:** PUT with any other field
   - **Then:** cups_code=895101 preserved in response

#### Error Cases
1. Empty body
   - **Given:** PUT request with empty JSON `{}`
   - **When:** Request sent
   - **Then:** 400 Bad Request with no-fields-to-update message

2. Negative price
   - **Given:** `{ "default_price": -1000 }`
   - **When:** PUT
   - **Then:** 422 with negative price error

3. Unknown service_id
   - **Given:** service_id not in tenant
   - **When:** PUT
   - **Then:** 404 Not Found

4. Doctor role
   - **Given:** Authenticated doctor
   - **When:** PUT
   - **Then:** 403 Forbidden

5. name too long (201 chars)
   - **Given:** name string of 201 characters
   - **When:** PUT
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** clinic_owner, doctor (for 403 test)

**Service Catalog:** 3 services with known prices, names, categories; 1 CUPS-seeded service

### Mocking Strategy

- Redis: `fakeredis`; verify SCAN+DEL pattern executed on update
- Audit log: Mock or seeded DB; verify insert after update

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] PUT /api/v1/billing/services/{service_id} returns 200 with updated service
- [ ] Partial update — only provided fields changed; others preserved
- [ ] cups_code cannot be changed (excluded from updatable fields)
- [ ] default_price=0 is valid (free service)
- [ ] Negative price rejected with 422
- [ ] Empty body returns 400
- [ ] Service from different tenant returns 404
- [ ] Only clinic_owner can update (403 for other roles)
- [ ] Cache pattern `tenant:{tenant_id}:billing:services:*` deleted on update
- [ ] Audit log created with field-level change tracking
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating new custom services (to be added as POST /api/v1/billing/services)
- Deleting services (soft-delete via is_active=false is sufficient)
- Bulk price updates for multiple services at once
- Updating CUPS codes (immutable by design)
- Service catalog import from external source

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (partial update schema)
- [x] All outputs defined (updated service record)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (clinic_owner only)
- [x] Side effects listed (DB update, cache invalidate, audit)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Tenant isolation enforced in WHERE clause
- [x] Partial update pattern (PATCH semantics via PUT)
- [x] cups_code immutability enforced

### Hook 3: Security & Privacy
- [x] Auth level stated (clinic_owner only)
- [x] Input sanitization (bleach for fields in PDFs)
- [x] SQL injection prevented
- [x] No PHI

### Hook 4: Performance & Scalability
- [x] Response time target (< 200ms)
- [x] Cache pattern delete on write
- [x] 2 queries (select + update)

### Hook 5: Observability
- [x] Audit log with field-level change tracking
- [x] Structured logging (tenant_id, service_id, fields_changed)
- [x] Error tracking compatible

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data specified
- [x] Mocking strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
