# INV-05 Create Sterilization Record Spec

---

## Overview

**Feature:** Record a sterilization cycle for dental instruments. Captures autoclave ID, load number, date, temperature, duration, biological and chemical indicator results, the list of instruments sterilized (linked to inventory items), the responsible user, and a required digital signature. Records are immutable after creation to ensure regulatory compliance with Colombian healthcare standards. All access is audit logged.

**Domain:** inventory

**Priority:** Low

**Dependencies:** INV-01 (item-create.md), INV-06 (sterilization-list.md), patients/digital-signature.md, infra/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner and assistant may record sterilization cycles. The `responsible_user_id` in the request must be a user with role assistant, doctor, or clinic_owner (the person who performed the sterilization). It may differ from the authenticated user (e.g., a clinic_owner entering a cycle performed by an assistant).

---

## Endpoint

```
POST /api/v1/inventory/sterilization
```

**Rate Limiting:**
- 30 requests per minute per user (sterilization records are created at most a few times per day)

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
  "autoclave_id": "string (required) — identifier of the autoclave unit, max 100 chars, e.g. AUTOCLAVE-01",
  "load_number": "string (required) — sequential load identifier for this cycle, max 50 chars, e.g. 2026-02-25-001",
  "date": "string (required) — ISO 8601 date of sterilization, cannot be in the future",
  "temperature_celsius": "number (required) — sterilization temperature, e.g. 121, 132, 134",
  "duration_minutes": "integer (required) — cycle duration in minutes, min 1",
  "biological_indicator": "string (required) — enum: positive, negative",
  "chemical_indicator": "string (required) — enum: pass, fail",
  "instruments": ["uuid (required) — array of inventory item IDs, min 1, max 100; must be category=instrument"],
  "responsible_user_id": "uuid (required) — user who performed the sterilization",
  "digital_signature": {
    "image_data": "string (required) — base64-encoded PNG of the responsible person's signature, max 2MB",
    "sha256_hash": "string (required) — SHA-256 hash of image_data for integrity verification"
  },
  "notes": "string (optional) — additional notes, max 1000 chars"
}
```

**Example Request:**
```json
{
  "autoclave_id": "AUTOCLAVE-01",
  "load_number": "2026-02-25-003",
  "date": "2026-02-25",
  "temperature_celsius": 134,
  "duration_minutes": 18,
  "biological_indicator": "negative",
  "chemical_indicator": "pass",
  "instruments": [
    "inv-aaaa-1111-bbbb-2222-cccc33334444",
    "inv-bbbb-2222-cccc-3333-dddd44445555",
    "inv-cccc-3333-dddd-4444-eeee55556666"
  ],
  "responsible_user_id": "usr-assistant-0001-000000000000",
  "digital_signature": {
    "image_data": "iVBORw0KGgoAAAANSUhEUgAA...(base64 PNG)...",
    "sha256_hash": "a3f5b8c2e1d9f4a7b6c0e3d8f2a1b5c9e8d3f7a2b4c6e0d1f9a8b3c5e2d7f4"
  },
  "notes": "Ciclo de rutina. Todos los indicadores dentro de parametros normales."
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
  "autoclave_id": "string",
  "load_number": "string",
  "date": "string ISO 8601 date",
  "temperature_celsius": "number",
  "duration_minutes": "integer",
  "biological_indicator": "string",
  "chemical_indicator": "string",
  "instruments": [
    {
      "id": "uuid",
      "name": "string",
      "category": "string",
      "lot_number": "string | null"
    }
  ],
  "responsible_user": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "role": "string"
  },
  "digital_signature": {
    "stored_at": "string ISO 8601",
    "sha256_hash": "string",
    "verified": "boolean — true if provided hash matches computed hash of image_data"
  },
  "notes": "string | null",
  "is_compliant": "boolean — true if both indicators pass (biological=negative AND chemical=pass)",
  "created_by": "uuid",
  "created_at": "string ISO 8601"
}
```

**Example:**
```json
{
  "id": "ster-aaaa-1111-bbbb-2222-cccc33334444",
  "autoclave_id": "AUTOCLAVE-01",
  "load_number": "2026-02-25-003",
  "date": "2026-02-25",
  "temperature_celsius": 134,
  "duration_minutes": 18,
  "biological_indicator": "negative",
  "chemical_indicator": "pass",
  "instruments": [
    { "id": "inv-aaaa-1111-bbbb-2222-cccc33334444", "name": "Forceps Extraccion Superior", "category": "instrument", "lot_number": null },
    { "id": "inv-bbbb-2222-cccc-3333-dddd44445555", "name": "Espejo Boca #5", "category": "instrument", "lot_number": null },
    { "id": "inv-cccc-3333-dddd-4444-eeee55556666", "name": "Sonda Periodontal OMS", "category": "instrument", "lot_number": null }
  ],
  "responsible_user": {
    "id": "usr-assistant-0001-000000000000",
    "first_name": "Ana",
    "last_name": "Jimenez",
    "role": "assistant"
  },
  "digital_signature": {
    "stored_at": "2026-02-25T17:00:00-05:00",
    "sha256_hash": "a3f5b8c2e1d9f4a7b6c0e3d8f2a1b5c9e8d3f7a2b4c6e0d1f9a8b3c5e2d7f4",
    "verified": true
  },
  "notes": "Ciclo de rutina. Todos los indicadores dentro de parametros normales.",
  "is_compliant": true,
  "created_by": "usr-clinic-owner-0001-000000000000",
  "created_at": "2026-02-25T17:00:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields, empty instruments array.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El registro de esterilizacion contiene campos requeridos faltantes.",
  "details": {
    "instruments": ["Debe incluir al menos un instrumento en el ciclo."],
    "digital_signature": ["La firma digital es requerida para registros de esterilizacion."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor or receptionist role.

#### 404 Not Found
**When:** `responsible_user_id` not found in tenant, or one or more `instrument` IDs not found in tenant inventory.

**Example:**
```json
{
  "error": "not_found",
  "message": "Los siguientes instrumentos no fueron encontrados en el inventario.",
  "details": {
    "missing_instrument_ids": ["inv-xxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"]
  }
}
```

#### 409 Conflict
**When:** A sterilization record with the same `autoclave_id` + `load_number` + `date` combination already exists for this tenant.

**Example:**
```json
{
  "error": "duplicate_record",
  "message": "Ya existe un registro de esterilizacion para la carga 2026-02-25-003 en AUTOCLAVE-01 en esta fecha."
}
```

#### 422 Unprocessable Entity
**When:** Invalid enum values, `date` in the future, `temperature_celsius` outside valid range, signature hash mismatch, instruments include non-instrument category items.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Los datos del ciclo de esterilizacion contienen errores.",
  "details": {
    "date": ["La fecha no puede ser futura."],
    "temperature_celsius": ["Temperatura invalida. Valores esperados: 121, 132, 134 grados Celsius."],
    "instruments[0]": ["El item inv-dddd-4444... no es un instrumento (categoria: material). Solo se pueden incluir instrumentos."],
    "digital_signature.sha256_hash": ["El hash SHA-256 no coincide con la imagen de firma proporcionada."]
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
2. Validate request body against Pydantic schema.
3. Validate `date` is not in the future.
4. Validate `temperature_celsius` is in expected range. Valid values: 121°C (gravity cycle), 132°C (flash), 134°C (pre-vacuum). Allow any value between 100-145 with a warning for non-standard values.
5. Validate `biological_indicator` enum: positive, negative.
6. Validate `chemical_indicator` enum: pass, fail.
7. Validate `instruments` array: non-empty, max 100 items, all valid UUID v4.
8. Validate digital signature:
   a. `image_data`: valid base64, decoded PNG magic bytes, decoded size <= 2MB.
   b. `sha256_hash`: compute `hashlib.sha256(image_data.encode()).hexdigest()`. Compare to provided hash. If mismatch, return 422 with "hash mismatch" error. This verifies the client correctly computed the hash.
9. Set `search_path` to tenant schema.
10. Check duplicate: `SELECT id FROM sterilization_records WHERE autoclave_id = :autoclave_id AND load_number = :load_number AND date = :date AND tenant_id = :tenant_id`. If exists, return 409.
11. Validate `responsible_user_id` exists in `users` table for this tenant. If not, return 404.
12. Validate all instrument IDs: `SELECT id, name, category FROM inventory_items WHERE id = ANY(:instrument_ids) AND tenant_id = :tenant_id`. Build a set of found IDs. If any IDs missing from result, return 404 with missing IDs. If any found item has `category != 'instrument'`, return 422.
13. Compute `is_compliant = biological_indicator == 'negative' AND chemical_indicator == 'pass'`.
14. Begin database transaction.
15. Insert into `sterilization_records`: all cycle metadata, `responsible_user_id`, `signature_data`, `signature_sha256_hash`, `is_compliant`, `created_by = user_id`, `created_at = now()`.
16. Insert into `sterilization_record_instruments` (junction table): one record per instrument in the load.
17. Commit transaction. **Record is now immutable — no UPDATE or DELETE operations are allowed on sterilization records.**
18. Write audit log: action `create`, resource `sterilization_record`, PHI=no, regulatory=yes.
19. If `is_compliant = false` (biological_indicator=positive or chemical_indicator=fail): dispatch `sterilization.non_compliant_alert` to RabbitMQ.
20. Return 201 with full record.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| autoclave_id | Non-empty string, max 100 chars | El identificador del autoclave es requerido. |
| load_number | Non-empty string, max 50 chars | El numero de carga es requerido. |
| date | Valid ISO 8601 date, not in the future | La fecha no puede ser futura. |
| temperature_celsius | Number between 100 and 145 | Temperatura invalida. |
| duration_minutes | Integer >= 1 | La duracion debe ser al menos 1 minuto. |
| biological_indicator | Enum: positive, negative | Indicador biologico invalido. |
| chemical_indicator | Enum: pass, fail | Indicador quimico invalido. |
| instruments | Non-empty array (min 1), max 100, all must exist in tenant, all must be category=instrument | Instrumento no encontrado / Solo se permiten instrumentos. |
| responsible_user_id | Valid UUID, must exist in tenant | Usuario responsable no encontrado. |
| digital_signature.image_data | Non-empty base64, valid PNG header, <= 2MB | Firma invalida. Debe ser imagen PNG en base64 (max 2MB). |
| digital_signature.sha256_hash | Must match computed hash of image_data | El hash SHA-256 no coincide con la firma. |
| (autoclave_id, load_number, date) | Unique per tenant | Ya existe un registro para esta carga en esta fecha. |

**Business Rules:**

- Sterilization records are legally required for dental clinic compliance in Colombia. They cannot be modified or deleted after creation. This is enforced at the database level: no UPDATE or DELETE permissions granted to the application on the `sterilization_records` table.
- The digital signature requirement ensures the responsible person has reviewed and confirmed the sterilization cycle parameters. The SHA-256 verification confirms the client sent the hash that matches the image.
- `is_compliant = false` triggers an immediate alert to clinic_owner. A non-compliant cycle (positive biological indicator or failed chemical indicator) means the instruments may not be sterile and cannot be used until re-sterilized.
- A non-compliant record should still be created (not rejected). The non-compliance is documented for regulatory reporting. The alert notifies staff to take corrective action.
- The `responsible_user_id` field allows a clerk or clinic_owner to record a cycle that was physically performed by a different user (e.g., a dental assistant). The signature belongs to the responsible user, not necessarily the caller.
- Instruments list references `inventory_items` with `category = 'instrument'`. This creates a traceability link between the sterilization record and specific instrument items.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Duplicate load_number for same autoclave on same date | 409 Conflict |
| Non-compliant cycle (positive biological indicator) | 201 Created with is_compliant=false; alert dispatched |
| responsible_user_id == authenticated user_id | Valid; the caller performed the sterilization |
| Non-standard temperature (e.g. 125°C) | 201 Created with warning logged; not rejected |
| instruments array contains same ID twice | Deduplication applied before insert; logged as warning |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `sterilization_records`: INSERT — new immutable record
- `sterilization_record_instruments`: INSERT — junction records per instrument
- `audit_logs`: INSERT — regulatory event

**Example query (SQLAlchemy):**
```python
async with session.begin():
    record = SterilizationRecord(
        tenant_id=tenant_id,
        autoclave_id=data.autoclave_id,
        load_number=data.load_number,
        date=data.date,
        temperature_celsius=data.temperature_celsius,
        duration_minutes=data.duration_minutes,
        biological_indicator=data.biological_indicator,
        chemical_indicator=data.chemical_indicator,
        responsible_user_id=data.responsible_user_id,
        signature_data=data.digital_signature.image_data,
        signature_sha256_hash=data.digital_signature.sha256_hash,
        notes=data.notes,
        is_compliant=is_compliant,
        created_by=user_id,
    )
    session.add(record)
    await session.flush()

    instrument_ids = list(set(data.instruments))  # deduplicate
    for instrument_id in instrument_ids:
        session.add(SterilizationRecordInstrument(
            sterilization_record_id=record.id,
            instrument_id=instrument_id,
        ))
```

### Cache Operations

**Cache keys affected:** None — sterilization records are written once and never change. The inventory list cache is not affected (sterilization does not change inventory quantities).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | sterilization.non_compliant_alert | { tenant_id, record_id, autoclave_id, load_number, date, biological_indicator, chemical_indicator, responsible_user_id } | When is_compliant=false |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** create
- **Resource:** sterilization_record
- **PHI involved:** No — regulatory/operational data
- **Regulatory flag:** Yes — sterilization records have elevated audit requirements for compliance reporting

### Notifications

**Notifications triggered:** Conditionally (non-compliant cycles only)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | sterilization_non_compliant | clinic_owner | When biological_indicator=positive or chemical_indicator=fail |
| in-app | sterilization_non_compliant | clinic_owner | Same condition |

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 600ms

### Caching Strategy
- **Strategy:** No caching (write operation; immutable records do not benefit from caching at write time)
- **Cache key:** N/A
- **TTL:** N/A

### Database Performance

**Queries executed:** 4-5 (duplicate check, user validation, instruments validation, insert record, insert junction records)

**Indexes required:**
- `sterilization_records.(tenant_id, autoclave_id, load_number, date)` — COMPOSITE UNIQUE INDEX for duplicate check
- `sterilization_record_instruments.sterilization_record_id` — INDEX
- `sterilization_records.(tenant_id, date DESC)` — COMPOSITE INDEX for list queries (INV-06)
- `sterilization_records.(tenant_id, responsible_user_id)` — INDEX for filtered list

**N+1 prevention:** Instrument validation uses single `WHERE id = ANY(:ids)` query. Junction records inserted in a loop within the same transaction (bounded by max 100 items).

### Pagination

**Pagination:** No — single record creation endpoint.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| autoclave_id | Pydantic strip(), max_length=100, `re.sub(r'[^\w\-]', '', v)` | Alphanumeric + hyphens |
| load_number | Pydantic strip(), max_length=50, `re.sub(r'[^\w\-]', '', v)` | |
| notes | Pydantic strip(), max_length=1000, bleach.clean | |
| digital_signature.image_data | Base64 decode validation, PNG magic bytes, size <= 2MB | |
| digital_signature.sha256_hash | Regex `^[a-f0-9]{64}$` — must be 64-char hex SHA-256 | Server-side verification performed |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — sterilization data is operational/regulatory.

**Audit requirement:** Write operation logged with regulatory flag.

### Regulatory Compliance

Record immutability is enforced by:
1. No UPDATE or DELETE routes exist for sterilization records (INV-05 create only, INV-06 list only).
2. Database-level: the application user has only INSERT and SELECT permissions on `sterilization_records` and `sterilization_record_instruments`.
3. Audit log records the creation event with record ID, sha256_hash, and timestamp.

---

## Testing

### Test Cases

#### Happy Path
1. Create compliant sterilization record
   - **Given:** Authenticated clinic_owner, 3 valid instrument items in inventory, valid PNG signature
   - **When:** POST /api/v1/inventory/sterilization with biological_indicator=negative, chemical_indicator=pass
   - **Then:** 201 Created, is_compliant=true, all instruments in response, signature.verified=true, no alert dispatched

2. Create non-compliant record (positive biological indicator)
   - **Given:** Valid cycle data with biological_indicator=positive
   - **When:** POST
   - **Then:** 201 Created, is_compliant=false, RabbitMQ non_compliant_alert dispatched

3. Responsible user differs from authenticated caller
   - **Given:** Authenticated clinic_owner, responsible_user_id = assistant's ID
   - **When:** POST
   - **Then:** 201 Created, responsible_user shows assistant info

#### Edge Cases
1. Instruments array with duplicate IDs
   - **Given:** instruments=[id1, id1, id2] (id1 repeated)
   - **When:** POST
   - **Then:** 201 Created, deduplicated to [id1, id2] in instruments response

2. Non-standard temperature (125°C)
   - **Given:** temperature_celsius=125
   - **When:** POST
   - **Then:** 201 Created (warning logged but not rejected)

#### Error Cases
1. Duplicate load_number for same autoclave and date
   - **Given:** Record with AUTOCLAVE-01 + 2026-02-25-003 already exists
   - **When:** POST same combination
   - **Then:** 409 Conflict

2. Instrument with wrong category (material, not instrument)
   - **Given:** instrument ID pointing to a material item
   - **When:** POST
   - **Then:** 422 with category error for that item

3. SHA-256 hash mismatch
   - **Given:** Valid image_data but sha256_hash is wrong
   - **When:** POST
   - **Then:** 422 with hash mismatch error

4. date = tomorrow
   - **Given:** date in the future
   - **When:** POST
   - **Then:** 422 with future date error

5. Doctor role
   - **Given:** Authenticated doctor
   - **When:** POST
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, assistant, doctor (403 test)

**Inventory Items:** 3 items with category=instrument; 1 item with category=material (for invalid category test)

**Existing Sterilization Record:** One record with known autoclave_id + load_number + date for duplicate test

### Mocking Strategy

- RabbitMQ: Mock publish; assert non_compliant_alert dispatched only for is_compliant=false
- Minimal valid 1x1 PNG in base64 for signature tests; compute actual SHA-256 for consistency tests
- Database: PostgreSQL test instance (recommended due to UNIQUE constraints and immutability rules)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/inventory/sterilization returns 201 with full record
- [ ] Immutable — no UPDATE/DELETE routes exist
- [ ] Digital signature stored with SHA-256; hash verified server-side
- [ ] SHA-256 mismatch returns 422
- [ ] Duplicate (autoclave_id + load_number + date) returns 409
- [ ] is_compliant computed from biological + chemical indicators
- [ ] Non-compliant records: created AND alert dispatched to RabbitMQ
- [ ] Only instruments (category=instrument) allowed in instruments list
- [ ] Non-instrument items return 422
- [ ] Only clinic_owner and assistant can create (403 for others)
- [ ] Audit log written with regulatory flag
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing sterilization records (see INV-06)
- Modifying or deleting sterilization records (immutable by design)
- Autoclave management/registration
- Sterilization cycle scheduling
- Integration with autoclave hardware/IoT devices (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (full cycle schema with signature)
- [x] All outputs defined
- [x] API contract defined
- [x] Validation rules stated (comprehensive regulatory rules)
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Immutability documented
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Immutable records (INSERT only at DB level)
- [x] SHA-256 server-side verification
- [x] Tenant isolation
- [x] Regulatory compliance documented

### Hook 3: Security & Privacy
- [x] Signature verification (hash mismatch → 422)
- [x] DB-level immutability
- [x] Regulatory audit log flag
- [x] No PHI

### Hook 4: Performance & Scalability
- [x] Target < 300ms
- [x] Composite UNIQUE index for duplicate check
- [x] Bounded instrument array (max 100)

### Hook 5: Observability
- [x] Audit log (regulatory flag)
- [x] Non-compliant alert via RabbitMQ
- [x] Structured logging

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] SHA-256 consistency test documented
- [x] RabbitMQ mock strategy
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
