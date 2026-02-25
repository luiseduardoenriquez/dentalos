# B-17 Get Quotation Detail Spec

---

## Overview

**Feature:** Retrieve the full detail of a single quotation for a patient. Returns the complete quotation with its sequential number (COT-2026-0001), patient and clinic information, line items with procedure details per tooth, calculated totals, current status, validity period, and any notes. Supports the auto-flow review step before patient approval.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-16 (quotation-create.md), B-19 (quotation-approve.md), P-01 (patient-get.md), B-14 (service-catalog.md), infra/authentication-rules.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient (own quotations only via portal)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients can only access their own quotations when accessing via the patient portal. Staff roles can access any quotation within their tenant.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/quotations/{quotation_id}
```

**Rate Limiting:**
- Inherits global rate limit (100 requests per minute per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | UUID v4, must exist in tenant | Patient who owns the quotation | pt_550e8400-e29b-41d4-a716-446655440000 |
| quotation_id | Yes | UUID | UUID v4, must belong to patient | Quotation to retrieve | quot-9a1b-2c3d-e4f5-6789abcdef01 |

### Query Parameters

None.

### Request Body Schema

None — GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "quotation_number": "string — sequential: COT-{YYYY}-{NNNN}",
  "patient": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "document_type": "string",
    "document_number": "string",
    "email": "string | null",
    "phone": "string | null"
  },
  "clinic": {
    "name": "string",
    "address": "string | null",
    "phone": "string | null",
    "email": "string | null",
    "nit": "string | null — clinic tax ID for quotation header"
  },
  "doctor": {
    "id": "uuid | null",
    "first_name": "string | null",
    "last_name": "string | null",
    "specialty": "string | null"
  },
  "status": "string — enum: draft, sent, approved, rejected, expired",
  "items": [
    {
      "id": "uuid",
      "service_id": "uuid | null",
      "cups_code": "string | null",
      "procedure_name": "string",
      "tooth_number": "string | null — FDI notation, e.g. 16, or range 12-14",
      "description": "string | null — additional notes on the item",
      "quantity": "integer",
      "unit_price": "integer — cents",
      "discount_percentage": "number — item-level discount 0-100",
      "discount_amount": "integer — cents",
      "subtotal": "integer — cents after item-level discount",
      "tax_exempt": "boolean"
    }
  ],
  "currency": "string — ISO 4217",
  "subtotal": "integer — cents — sum of item subtotals before global discount",
  "global_discount_percentage": "number",
  "global_discount_amount": "integer — cents",
  "tax_percentage": "number",
  "tax_amount": "integer — cents",
  "total": "integer — cents",
  "valid_until": "string ISO 8601 date — expiry date (created_at + 30 days by default)",
  "days_until_expiry": "integer | null — null if already expired or approved/rejected",
  "notes": "string | null",
  "created_at": "string ISO 8601",
  "updated_at": "string ISO 8601",
  "created_by": "uuid",
  "sent_at": "string ISO 8601 | null",
  "approved_at": "string ISO 8601 | null",
  "rejected_at": "string ISO 8601 | null",
  "invoice_id": "uuid | null — populated after approval and invoice creation"
}
```

**Example:**
```json
{
  "id": "quot-9a1b-2c3d-e4f5-6789abcdef01",
  "quotation_number": "COT-2026-0001",
  "patient": {
    "id": "pt_550e8400-e29b-41d4-a716-446655440000",
    "first_name": "Maria",
    "last_name": "Garcia Lopez",
    "document_type": "cc",
    "document_number": "1020304050",
    "email": "maria.garcia@email.com",
    "phone": "+573001234567"
  },
  "clinic": {
    "name": "Clinica Dental San Jose",
    "address": "Calle 45 #12-34, Bogota",
    "phone": "+5716001234",
    "email": "contacto@clinicasanjose.com",
    "nit": "900123456-7"
  },
  "doctor": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "first_name": "Carlos",
    "last_name": "Mendez",
    "specialty": "Odontologia General"
  },
  "status": "sent",
  "items": [
    {
      "id": "qi-aabb-1122-ccdd-3344-eeff55667788",
      "service_id": "svc-aabb-1122-ccdd-3344-eeff55667788",
      "cups_code": "895101",
      "procedure_name": "Resina Compuesta",
      "tooth_number": "16",
      "description": null,
      "quantity": 1,
      "unit_price": 70000,
      "discount_percentage": 0,
      "discount_amount": 0,
      "subtotal": 70000,
      "tax_exempt": true
    },
    {
      "id": "qi-bbcc-2233-ddee-4455-ff0066778899",
      "service_id": "svc-ccdd-3344-eeff-5566-001177889900",
      "cups_code": "895501",
      "procedure_name": "Endodoncia Unirradicular",
      "tooth_number": "21",
      "description": "Incluye radiografias diagnosticas",
      "quantity": 1,
      "unit_price": 85000,
      "discount_percentage": 0,
      "discount_amount": 0,
      "subtotal": 85000,
      "tax_exempt": true
    }
  ],
  "currency": "COP",
  "subtotal": 155000,
  "global_discount_percentage": 0,
  "global_discount_amount": 0,
  "tax_percentage": 0,
  "tax_amount": 0,
  "total": 155000,
  "valid_until": "2026-03-26",
  "days_until_expiry": 29,
  "notes": "Presupuesto sujeto a cambios si se requieren procedimientos adicionales durante el tratamiento.",
  "created_at": "2026-02-25T10:00:00-05:00",
  "updated_at": "2026-02-25T10:00:00-05:00",
  "created_by": "usr-doctor-0001-0000-000000000000",
  "sent_at": "2026-02-25T10:05:00-05:00",
  "approved_at": null,
  "rejected_at": null,
  "invoice_id": null
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient role tries to access another patient's quotation. Also returned if the `patient_id` in the URL does not match the JWT when caller is `role = patient`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver esta cotizacion."
}
```

#### 404 Not Found
**When:** `patient_id` not found in tenant, `quotation_id` not found, or quotation does not belong to the specified patient.

**Example:**
```json
{
  "error": "not_found",
  "message": "La cotizacion no fue encontrada."
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
2. If `role = patient`: verify that `user_id` matches the patient record linked to `patient_id`. If not, return 403.
3. Validate `patient_id` and `quotation_id` as UUID v4.
4. Set `search_path` to tenant schema.
5. Verify `patient_id` exists in `patients` table for this tenant. If not, return 404.
6. Query quotation: `SELECT * FROM quotations WHERE id = :quotation_id AND patient_id = :patient_id AND tenant_id = :tenant_id`. If not found, return 404.
7. Load quotation items with service catalog join: `SELECT qi.*, sc.cups_code FROM quotation_items qi LEFT JOIN service_catalog sc ON sc.id = qi.service_id WHERE qi.quotation_id = :quotation_id ORDER BY qi.sort_order ASC, qi.created_at ASC`.
8. Load patient summary fields (first_name, last_name, document_type, document_number, email, phone).
9. Load doctor summary if `quotation.doctor_id` is set.
10. Load clinic info from tenant settings (name, address, phone, email, nit).
11. Compute `days_until_expiry`:
    - If `status IN ('approved', 'rejected', 'expired')`: return null.
    - Else: `max(0, (valid_until - today).days)`. If 0 and status=sent, the quotation should be transitioned to expired (but this GET endpoint only reads — expiry transition is handled by a background cron job).
12. Build response object with all computed fields.
13. Write audit log: action `read`, resource `quotation`, PHI=yes (patient info in response).
14. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | Valid UUID v4, must exist in tenant | La cotizacion no fue encontrada. |
| quotation_id (URL) | Valid UUID v4, must belong to patient_id | La cotizacion no fue encontrada. |

**Business Rules:**

- Quotations are patient-scoped: the URL structure `patients/{patient_id}/quotations/{quotation_id}` enforces ownership. A quotation_id that exists but belongs to a different patient returns 404 (not 403) to avoid revealing quotation existence.
- The `valid_until` date defaults to `created_at + 30 days`. It is calculated at creation time and stored in the DB. Clinics may customize this default via settings.
- `days_until_expiry` is computed server-side at read time (not cached) to always be accurate.
- The `clinic` block is populated from tenant settings, not from a separate clinic record. NIT (tax ID) is included for use in quotation PDF headers.
- `status = 'expired'` is set by a background cron job when `valid_until < today` and `status = 'sent'`. The GET endpoint reflects whatever status is stored.
- Once `status = 'approved'`, the `invoice_id` field will be populated (set during approval flow in B-19). Staff can use this to navigate directly to the resulting invoice.
- Item-level discounts and global discount can both be non-zero. The total is calculated as: `sum(item.subtotal) - global_discount_amount + tax_amount`, where `item.subtotal = quantity * unit_price * (1 - item.discount_percentage/100)`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Quotation expired (past valid_until) but status not yet updated | days_until_expiry=0, status still shows stored value; cron will update status |
| Patient role accessing own quotation | 200 OK with full detail |
| Patient role accessing another patient's quotation | 403 Forbidden |
| Doctor on quotation was deleted (inactive) | doctor block shows stored name fields; does not error |
| No doctor assigned to quotation | doctor block: all null fields |
| quotation_id exists but belongs to different patient | 404 Not Found (not 403) |

---

## Side Effects

### Database Changes

**No write operations** — read-only endpoint.

### Cache Operations

**Cache keys affected:** None — quotation detail is not cached (read-through to DB always; quotation status changes frequently enough that caching adds complexity without significant benefit at this granularity).

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** read
- **Resource:** quotation
- **PHI involved:** Yes — patient contact info and financial data returned

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms
- **Maximum acceptable:** < 200ms

### Caching Strategy
- **Strategy:** No response caching (quotation status and days_until_expiry change frequently)
- **Cache key:** N/A
- **TTL:** N/A

### Database Performance

**Queries executed:** 4 (patient lookup, quotation lookup, quotation_items with JOIN, tenant settings for clinic info)

**Indexes required:**
- `quotations.(tenant_id, patient_id, id)` — COMPOSITE INDEX for ownership check
- `quotation_items.quotation_id` — INDEX
- `quotation_items.sort_order` — INDEX for ordered retrieval
- `patients.(tenant_id, id)` — COMPOSITE INDEX

**N+1 prevention:** Quotation items loaded in single query with LEFT JOIN to service_catalog. Patient, doctor, and clinic loaded in separate targeted queries (not per-item).

### Pagination

**Pagination:** No — single quotation detail, items returned as complete array.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID validator | |
| quotation_id (URL) | Pydantic UUID validator | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient first_name, last_name, document_number, email, phone; financial totals

**Audit requirement:** All access logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Staff fetches quotation in sent status
   - **Given:** Authenticated receptionist, quotation with status=sent, 2 items, valid_until in 10 days
   - **When:** GET /api/v1/patients/{pid}/quotations/{qid}
   - **Then:** 200 OK, full quotation with correct totals, days_until_expiry=10, items include cups_code

2. Patient accesses own quotation
   - **Given:** Authenticated patient, quotation belongs to that patient
   - **When:** GET request with matching patient_id
   - **Then:** 200 OK with full quotation detail

3. Approved quotation shows invoice_id
   - **Given:** Quotation with status=approved, invoice_id populated
   - **When:** GET
   - **Then:** invoice_id present, approved_at timestamp set, days_until_expiry=null

#### Edge Cases
1. Quotation with no doctor assigned
   - **Given:** Quotation where doctor_id=null
   - **When:** GET
   - **Then:** doctor block with all null fields

2. Quotation past valid_until but status still=sent
   - **Given:** valid_until=yesterday, status=sent (cron not run yet)
   - **When:** GET
   - **Then:** days_until_expiry=0, status=sent (reflects DB state)

3. Global discount = 0, item discounts > 0
   - **Given:** Items with individual discounts, no global discount
   - **When:** GET
   - **Then:** Correct subtotals per item reflecting item-level discounts

#### Error Cases
1. Patient accessing another patient's quotation
   - **Given:** Patient A authenticated, quotation_id belongs to Patient B
   - **When:** GET with Patient B's patient_id in URL
   - **Then:** 403 Forbidden

2. quotation_id exists but for different patient
   - **Given:** quotation_id valid but belongs to different patient_id
   - **When:** GET
   - **Then:** 404 Not Found

3. patient_id not in tenant
   - **Given:** patient_id from different tenant
   - **When:** GET
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** clinic_owner, receptionist, doctor, patient (linked to a patient record)

**Patients:** Patient A with 2 quotations; Patient B with 1 quotation

**Quotations:** Draft, sent, approved (with invoice_id), rejected; one expired (past valid_until)

**Quotation Items:** Mix of service_id-linked items and manual-description items; items with per-item discounts

### Mocking Strategy

- Database: SQLite in-memory; seed quotations, quotation_items, patients, service_catalog with known data
- `days_until_expiry` computation: use fixed `today` in tests to ensure deterministic results

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns 200 with full quotation detail including all sections
- [ ] Quotation number format COT-{YYYY}-{NNNN} present
- [ ] cups_code included on items where service_id is set
- [ ] days_until_expiry computed correctly (null for terminal statuses)
- [ ] Totals correct: item subtotals, global discount, tax, total
- [ ] Patient role can access own quotation; cannot access others (403)
- [ ] quotation_id from different patient returns 404
- [ ] Audit log written with PHI flag
- [ ] All monetary values in cents
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating quotations (see B-16 quotation-create.md)
- Sending quotation to patient (see B-18 quotation-send.md)
- Patient approving quotation (see B-19 quotation-approve.md)
- Listing all quotations for a patient (separate list spec)
- PDF export of quotation
- Quotation rejection by patient

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (URL params only)
- [x] All outputs defined (complete quotation with items, totals, clinic, patient)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (ownership validation)
- [x] Error cases enumerated
- [x] Auth requirements explicit (staff + patient own quotation)
- [x] Side effects listed (audit log only)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Patient-scoped URL enforces ownership
- [x] Tenant schema isolation
- [x] Matches FastAPI conventions

### Hook 3: Security & Privacy
- [x] Patient role access control (own only)
- [x] quotation_id/patient_id ownership check (404 not 403 for wrong patient)
- [x] PHI audit log
- [x] SQL injection prevented

### Hook 4: Performance & Scalability
- [x] Target < 100ms
- [x] No caching (status changes frequently)
- [x] Efficient queries with composite indexes

### Hook 5: Observability
- [x] Audit log (PHI flag)
- [x] Structured logging (tenant_id, patient_id, quotation_id)

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data specified
- [x] Deterministic days_until_expiry via fixed today in tests
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
