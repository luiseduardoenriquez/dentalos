# PP-06 Portal Invoices Spec

---

## Overview

**Feature:** List a patient's own invoices and payment history from the portal. Shows outstanding balance, invoice details, payment records, and a payment link if online payments are enabled by the tenant. Read-only except for triggering payment flow. Paginated.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-02 (portal-profile.md), billing domain (B-01 through B-18), infra/multi-tenancy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient sees only their own invoices — enforced at query level by patient_id from JWT sub.

---

## Endpoint

```
GET /api/v1/portal/invoices
```

**Rate Limiting:**
- 30 requests per minute per patient

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| status | No | string | enum: pending, partial, paid, cancelled, all; default: all | Filter invoices by payment status | pending |
| cursor | No | string | Opaque cursor from previous response | Pagination cursor | eyJpZCI6... |
| limit | No | integer | 1-100; default: 20 | Results per page | 20 |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "summary": {
    "total_invoiced": "number (decimal) — total amount across all non-cancelled invoices",
    "total_paid": "number (decimal)",
    "outstanding_balance": "number (decimal) — total_invoiced - total_paid for unpaid/partial invoices",
    "currency": "string — ISO 4217, e.g. 'COP'"
  },
  "items": [
    {
      "id": "uuid",
      "invoice_number": "string — human-readable invoice number, e.g. 'FAC-2026-001'",
      "issued_at": "string (ISO 8601 datetime)",
      "due_at": "string (ISO 8601 date) | null",
      "status": "string — enum: pending, partial, paid, cancelled",
      "total_amount": "number (decimal)",
      "discount_amount": "number (decimal)",
      "tax_amount": "number (decimal)",
      "net_amount": "number (decimal) — total after discount, before tax",
      "paid_amount": "number (decimal)",
      "pending_amount": "number (decimal) — net_amount - paid_amount",
      "currency": "string",
      "description": "string | null — brief description of what was billed",
      "treatment_plan_id": "uuid | null",
      "appointment_id": "uuid | null",
      "payment_link": "string | null — payment URL if online_payments_enabled for tenant",
      "payments": [
        {
          "id": "uuid",
          "paid_at": "string (ISO 8601 datetime)",
          "amount": "number (decimal)",
          "method": "string — enum: cash, card, transfer, online",
          "reference": "string | null — transaction reference number"
        }
      ],
      "download_url": "string | null — signed S3 URL to invoice PDF (valid 60 minutes)"
    }
  ],
  "pagination": {
    "cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  }
}
```

**Example:**
```json
{
  "summary": {
    "total_invoiced": 1200000.00,
    "total_paid": 400000.00,
    "outstanding_balance": 800000.00,
    "currency": "COP"
  },
  "items": [
    {
      "id": "d4e5f6a7-b8c9-0123-abcd-ef1234567890",
      "invoice_number": "FAC-2026-0042",
      "issued_at": "2026-02-10T10:00:00-05:00",
      "due_at": "2026-03-10",
      "status": "partial",
      "total_amount": 1200000.00,
      "discount_amount": 120000.00,
      "tax_amount": 0.00,
      "net_amount": 1080000.00,
      "paid_amount": 400000.00,
      "pending_amount": 680000.00,
      "currency": "COP",
      "description": "Endodoncia + Extraccion - Plan de Tratamiento Integral",
      "treatment_plan_id": "c3d4e5f6-a1b2-7890-abcd-ef1234567890",
      "appointment_id": null,
      "payment_link": "https://pay.dentaios.com/i/tn_abc123/FAC-2026-0042",
      "payments": [
        {
          "id": "e5f6a7b8-c9d0-1234-abcd-567890123456",
          "paid_at": "2026-02-10T10:30:00-05:00",
          "amount": 400000.00,
          "method": "cash",
          "reference": null
        }
      ],
      "download_url": "https://s3.amazonaws.com/dentaios-docs/tn_abc123/invoices/FAC-2026-0042.pdf?X-Amz-Expires=3600&..."
    }
  ],
  "pagination": {
    "cursor": null,
    "has_more": false,
    "total_count": 1
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta no validos.",
  "details": {
    "status": ["Estado no valido. Opciones: pending, partial, paid, cancelled, all."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal" or role is not "patient".

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or S3 presign failure.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Validate query parameters.
3. Resolve tenant schema; set `search_path`.
4. Build base query: `SELECT ... FROM invoices WHERE patient_id = :patient_id`.
5. Apply status filter if provided; default = all non-deleted invoices.
6. Fetch invoices with LEFT JOIN payments on invoice.id to get payment records.
7. Apply cursor-based pagination on `(issued_at DESC, id DESC)`.
8. For each invoice, check if `tenant_settings.online_payments_enabled = true`. If yes, construct payment_link URL using invoice_number and tenant identifier. If no or invoice is paid/cancelled, payment_link = null.
9. For each invoice, generate a pre-signed S3 URL (TTL 60 minutes) if the invoice PDF exists at the expected S3 path. If PDF not yet generated (async job pending), download_url = null.
10. Compute summary aggregates:
    - `total_invoiced`: SUM(net_amount) WHERE status != 'cancelled'
    - `total_paid`: SUM(paid_amount) WHERE status != 'cancelled'
    - `outstanding_balance`: SUM(pending_amount) WHERE status IN ('pending', 'partial')
11. Compute pagination cursor.
12. Cache result with short TTL.
13. Return 200.

**Excluded Fields (never returned to patient):**
- Internal billing notes (staff-only)
- Cost-center or account codes
- DIAN e-invoice XML or raw CUFE (Colombia electronic invoice identifier; available via download)
- Payment processor raw responses

**Business Rules:**

- `pending_amount` = `net_amount - paid_amount`. Always >= 0.
- `payment_link` shown only if: tenant has online payments enabled AND invoice status is 'pending' or 'partial'.
- Invoice PDF generation is asynchronous (triggered at invoice creation); `download_url` may be null if PDF not yet ready.
- Currency is always the tenant's configured currency (default 'COP' for Colombia).
- Cancelled invoices shown with their full history but no payment_link.
- Payments list sorted by paid_at DESC (most recent first).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no invoices | items=[], summary all zeros |
| Invoice with no payments | payments=[], paid_amount=0.00 |
| Invoice PDF not yet generated | download_url=null (async job may still be running) |
| Online payments disabled for tenant | payment_link=null for all invoices |
| Tax amount zero (no IVA on dental services in Colombia) | tax_amount=0.00 shown explicitly |

---

## Side Effects

### Database Changes

None. Read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:invoices:{status}:{cursor}:{limit}`: SET — TTL 3 minutes

**Cache TTL:** 3 minutes

**Cache invalidation triggers:**
- New invoice created for patient
- Payment recorded against patient's invoice
- Invoice status changed

### Queue Jobs (RabbitMQ)

None directly from this endpoint. (Pre-signed URLs are generated synchronously; PDF generation is handled by billing domain jobs.)

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** patient_invoices
- **PHI involved:** Yes (financial PHI: amounts, treatment descriptions)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms (with cache hit)
- **Maximum acceptable:** < 300ms (cache miss, aggregate + items query)

### Caching Strategy
- **Strategy:** Redis cache, patient-namespaced
- **Cache key:** `tenant:{tenant_id}:portal:patient:{patient_id}:invoices:{status}:{cursor_hash}:{limit}`
- **TTL:** 3 minutes
- **Invalidation:** On invoice or payment change for this patient

### Database Performance

**Queries executed:** 3 (invoices + joined payments; summary aggregate; tenant settings for payment link)

**Indexes required:**
- `invoices.(patient_id, issued_at)` — COMPOSITE INDEX (primary sort + filter)
- `invoices.(patient_id, status)` — COMPOSITE INDEX (status filter)
- `payments.invoice_id` — INDEX (for JOIN)
- `tenant_settings.tenant_id` — INDEX (settings lookup)

**N+1 prevention:** Payments fetched via single IN query across all invoice IDs in page.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on issued_at + id)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| status | Pydantic Literal enum | Strict allowlist |
| cursor | Base64 decode + datetime/UUID validation | Malformed returns 400 |
| limit | Pydantic int ge=1, le=100 | Bounded integer |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** invoice amounts, treatment descriptions, payment history (financial PHI)

**Audit requirement:** Access logged per Resolución 1888 (financial records are part of clinical record).

---

## Testing

### Test Cases

#### Happy Path
1. Patient fetches all invoices
   - **Given:** Patient with 2 invoices (1 partial, 1 paid)
   - **When:** GET /api/v1/portal/invoices
   - **Then:** 200 OK, both invoices returned, summary accurate

2. Filter by pending invoices
   - **Given:** Patient with 1 pending, 1 paid invoice
   - **When:** GET /api/v1/portal/invoices?status=pending
   - **Then:** Only pending invoice returned

3. Payment link shown when online payments enabled
   - **Given:** Tenant has online_payments_enabled=true; invoice status=partial
   - **When:** GET /api/v1/portal/invoices
   - **Then:** payment_link populated with correct URL

4. Payment link hidden when paid
   - **Given:** Invoice status=paid
   - **When:** GET /api/v1/portal/invoices
   - **Then:** payment_link=null

#### Edge Cases
1. No invoices
   - **Given:** Patient with no billing history
   - **When:** GET /api/v1/portal/invoices
   - **Then:** items=[], summary all zeros

2. Invoice PDF not yet generated
   - **Given:** Invoice created 5 seconds ago, PDF job still processing
   - **When:** GET /api/v1/portal/invoices
   - **Then:** download_url=null (no error)

3. Online payments disabled
   - **Given:** tenant_settings.online_payments_enabled=false
   - **When:** GET /api/v1/portal/invoices
   - **Then:** All payment_links=null

#### Error Cases
1. Invalid status filter
   - **Given:** Patient authenticated
   - **When:** GET /api/v1/portal/invoices?status=overdue
   - **Then:** 400 Bad Request

2. Staff token
   - **Given:** Doctor JWT (scope=staff)
   - **When:** GET /api/v1/portal/invoices
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Patient with portal_access=true, 3+ invoices with varying statuses and payment records.

**Patients/Entities:** Tenant with online_payments_enabled=true; S3 mock with pre-existing invoice PDF; RabbitMQ mock.

### Mocking Strategy

- Redis: fakeredis
- S3: moto (verify pre-signed URL generation)
- tenant_settings: fixture with online_payments_enabled toggle

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient sees only their own invoices (query-level enforcement)
- [ ] Summary block (total_invoiced, total_paid, outstanding_balance) accurate
- [ ] Payments nested per invoice, sorted by paid_at DESC
- [ ] payment_link shown only for pending/partial when online payments enabled
- [ ] download_url generated as pre-signed S3 URL (60-min TTL); null if PDF not yet ready
- [ ] Status filter works correctly
- [ ] Cursor-based pagination works (20 default, 100 max)
- [ ] Cache 3 minutes; invalidated on invoice or payment change
- [ ] PHI access audited
- [ ] Staff JWT returns 403
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms cache hit, < 300ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Online payment processing (handled by payment gateway integration — separate spec)
- Invoice creation or modification (billing domain — clinic staff only)
- DIAN e-invoice CUFE verification (compliance domain)
- Refund requests from portal (future enhancement)
- Detailed financial reporting or export

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
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (patient portal scope)
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for financial PHI access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized (composite indexes)
- [x] Pagination applied (cursor-based)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A for read)

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
| 1.0 | 2026-02-25 | Initial spec |
