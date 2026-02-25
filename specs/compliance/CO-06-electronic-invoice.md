# CO-06 — Electronic Invoice (E-Invoice) Spec

## Overview

**Feature:** Generate and submit an electronic invoice to the tax authority via country-specific adapter. For Colombia, this means generating a DIAN-compliant XML document (UBL 2.1 format), digitally signing it, and submitting it to DIAN through the MATIAS API (Casa de Software model). Each clinic invoices under its own NIT. Processing is asynchronous; returns an e_invoice_id for status polling via CO-07.

**Domain:** compliance / billing

**Priority:** Low (Sprint 13-14)

**Dependencies:** billing/B-01 (invoice), infra/bg-processing.md, infra/audit-logging.md, CO-07 (e-invoice status), CO-08 (country-config)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only available for tenants with e-invoicing enabled (`e_invoicing_enabled = true` in tenant settings). In Colombia, this requires that the clinic has completed DIAN habilitación (registration) and provided NIT + certificate to DentalOS. Attempting to generate e-invoice without DIAN setup returns 402.

---

## Endpoint

```
POST /api/v1/compliance/e-invoice
```

**Rate Limiting:**
- 100 requests per hour per tenant (aligned with DIAN rate limits)
- Burst: 10 per minute

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "invoice_id": "string (UUID, required) — ID of the DentalOS invoice to electronically invoice",
  "force_resend": "boolean (optional, default=false) — re-submit even if already submitted (use for DIAN rejection recovery)"
}
```

**Example Request:**
```json
{
  "invoice_id": "inv_f1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "force_resend": false
}
```

---

## Response

### Success Response

**Status:** 202 Accepted (async processing)

**Schema:**
```json
{
  "e_invoice_id": "string (UUID) — ID of the e-invoice record",
  "invoice_id": "string (UUID) — source DentalOS invoice ID",
  "invoice_number": "string — human-readable invoice number (e.g. FV-2026-0042)",
  "period": "string — invoice date period (YYYY-MM)",
  "status": "string — enum: pending",
  "country_adapter": "string — co | mx | ...",
  "colombia_specific": {
    "cufe_placeholder": "null — populated when DIAN accepts",
    "nit_prestador": "string — clinic NIT",
    "matias_submission_id": "null — populated after submission",
    "dian_document_type": "string — 01 (FV) | 02 (ND) | 03 (NC)"
  },
  "created_at": "string (ISO 8601)",
  "poll_url": "string — URL to check status (CO-07)",
  "xml_url": "null — populated once XML is generated",
  "pdf_url": "null — populated once PDF is generated",
  "message": "string"
}
```

**Example:**
```json
{
  "e_invoice_id": "ei_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "invoice_id": "inv_f1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "invoice_number": "FV-2026-0042",
  "period": "2026-02",
  "status": "pending",
  "country_adapter": "co",
  "colombia_specific": {
    "cufe_placeholder": null,
    "nit_prestador": "900123456",
    "matias_submission_id": null,
    "dian_document_type": "01"
  },
  "created_at": "2026-02-25T10:00:00Z",
  "poll_url": "/api/v1/compliance/e-invoice/ei_a1b2c3d4-e5f6-7890-abcd-ef1234567890/status",
  "xml_url": null,
  "pdf_url": null,
  "message": "E-invoice queued for processing. Use poll_url to track status."
}
```

### Error Responses

#### 400 Bad Request
**When:** `invoice_id` references an invoice that is not in a billable state (e.g., draft, voided, already credited).

**Example:**
```json
{
  "error": "invoice_not_billable",
  "message": "Invoice is in draft status and cannot be electronically invoiced",
  "details": {
    "invoice_id": "inv_f1a2b3c4",
    "current_status": "draft",
    "required_status": ["issued", "pending_payment"]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token — see `infra/authentication-rules.md`.

#### 402 Payment Required
**When:** Tenant has not completed DIAN registration (habilitación) or MATIAS API credentials are missing.

**Example:**
```json
{
  "error": "dian_not_configured",
  "message": "Electronic invoicing is not configured for this clinic. Please complete DIAN registration.",
  "details": {
    "setup_url": "/settings/billing/e-invoice-setup",
    "missing_requirements": ["dian_certificate", "nit_verified"]
  }
}
```

#### 403 Forbidden
**When:** Caller role is not clinic_owner or receptionist.

#### 404 Not Found
**When:** Invoice with the given `invoice_id` does not exist in the tenant context.

**Example:**
```json
{
  "error": "invoice_not_found",
  "message": "Invoice not found",
  "details": { "invoice_id": "inv_f1a2b3c4" }
}
```

#### 409 Conflict
**When:** Invoice already has an accepted e-invoice (CUFE assigned) and `force_resend=false`.

**Example:**
```json
{
  "error": "already_invoiced",
  "message": "This invoice already has an accepted electronic invoice",
  "details": {
    "existing_e_invoice_id": "ei_prev1234",
    "cufe": "abc123def456...",
    "accepted_at": "2026-02-20T09:00:00Z",
    "hint": "Use force_resend=true to resubmit after a DIAN rejection"
  }
}
```

#### 422 Unprocessable Entity
**When:** Request body validation fails.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "invoice_id": ["value is not a valid UUID"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database error or queue unavailable.

---

## Business Logic

**Step-by-step process:**

1. Validate request body via Pydantic schema `EInvoiceCreateRequest`.
2. Resolve tenant_id from JWT; resolve country adapter via `ComplianceAdapterFactory.get(tenant.country)`.
3. Verify caller has `clinic_owner` or `receptionist` role.
4. Fetch invoice from tenant schema WHERE `id = invoice_id AND tenant_id = tenant_id`. Return 404 if not found.
5. Validate invoice status: must be `issued` or `pending_payment`. Draft/voided/credited invoices cannot be electronically invoiced.
6. Check DIAN configuration completeness: verify `tenant_einvoice_config` has `nit`, `certificate_path`, `matias_api_key`, `dian_environment` (habilitacion/production). Return 402 if incomplete.
7. Check for existing e-invoice: query `e_invoices` WHERE `invoice_id = X AND status = 'accepted'`. If found and `force_resend=false`, return 409.
8. If `force_resend=true` and existing e-invoice exists with status `rejected`, mark prior e-invoice as `superseded`.
9. Create `e_invoices` record with `status = 'pending'`, `country = 'co'`, `invoice_id`, `tenant_id`, `created_by`.
10. Publish to RabbitMQ `einvoice.generation` queue with payload: `{ e_invoice_id, tenant_id, invoice_id, country: 'co' }`.
11. Write audit log: action=`einvoice_requested`, resource=`e_invoice`, resource_id=`e_invoice_id`.
12. Return 202 Accepted.

**Background Worker — Colombian adapter:**

13. Worker dequeues from `einvoice.generation`.
14. Set `e_invoice.status = 'generating'`.
15. Load invoice data: patient info, line items (procedures), tax totals, clinic NIT, practitioner.
16. Build UBL 2.1 XML document per DIAN technical specification (Resolución DIAN 000042/2020 and updates):
    - `InvoiceTypeCode`: 01 (Factura de Venta)
    - `IssueDate`, `IssueTime`
    - `AccountingSupplierParty`: clinic NIT, address, DV (check digit)
    - `AccountingCustomerParty`: patient ID, name, address
    - `InvoiceLine[]`: each procedure as a line item with CUPS code, quantity, unit price, VAT (IVA 0% for health services per DIAN)
    - `LegalMonetaryTotal`: subtotal, tax total, payable amount
    - `TaxTotal`: health services are exempt from IVA (0%); ICA may apply depending on municipality
17. Compute CUFE (Código Único de Factura Electrónica): SHA-384 hash of required DIAN fields concatenated per DIAN formula.
18. Digitally sign XML using clinic's DIAN software certificate (X.509) — certificate retrieved from encrypted storage.
19. Store signed XML to object storage path `einvoices/{tenant_id}/{e_invoice_id}/invoice.xml`.
20. Generate PDF representation (QR code with CUFE + invoice data).
21. Submit to MATIAS API: `POST /api/v1/send-invoice` with signed XML + metadata. MATIAS routes to DIAN as the Casa de Software intermediary.
22. Update `e_invoices`: set `status = 'submitted'`, `matias_submission_id`, `xml_url`, `pdf_url`.
23. Poll or webhook from MATIAS for DIAN response (within 30s typically):
    - If accepted: set `status = 'accepted'`, `cufe`, `dian_response_code = '00'`, `accepted_at`.
    - If rejected: set `status = 'rejected'`, `dian_response_code`, `dian_response_message`.
24. Update `invoices.e_invoice_status` field on the source invoice record.
25. Send in-app notification to clinic_owner with result.

**DIAN-specific notes:**
- Health services (`servicios de salud`) are exempt from IVA per DIAN classification.
- CUFE computation uses: NIT emisor + número factura + fecha + hora + valor total + cod impuesto1 + valor impuesto1 + val base impuesto1 + cod impuesto2 + val impuesto2 + val base impuesto2 + cod impuesto3 + val impuesto3 + val base impuesto3 + NIT receptor + tipo código receptor + valor neto + NumCUFE (random nonce) + ambiente. All SHA-384 hashed.
- MATIAS API "Casa de Software" model: DentalOS holds a software registration with DIAN; each clinic uses their own NIT but routes through DentalOS's software PIN.
- DIAN habilitación environment (testing) uses a separate endpoint from production; controlled by `dian_environment` config field.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| invoice_id | Valid UUID v4 | "invoice_id must be a valid UUID" |
| force_resend | Boolean | "force_resend must be boolean" |
| invoice.status | Must be issued or pending_payment | "Solo facturas emitidas pueden facturarse electrónicamente" |

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| MATIAS API is down | Worker retries up to 3 times with exponential backoff; after 3 failures, sets status=failed and notifies clinic_owner |
| DIAN returns rejection for technical error | Status set to rejected; clinic_owner can correct and use force_resend=true |
| Certificate expired | Worker catches certificate validation error; status=failed with failure_reason="certificate_expired"; 402 returned on next attempt until configured |
| Patient is anonymous (cash walk-in) | Use DIAN anonymous consumer NIT: 222222222222 |
| Invoice in habilitación (test) environment | CUFE prefixed with "test_" in response; not legally valid |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `e_invoices`: INSERT (new e-invoice record)
- `invoices`: UPDATE `e_invoice_status`, `e_invoice_id` (after worker completes)

**Public schema tables affected:**
- None

**Example query (SQLAlchemy):**
```python
e_invoice = EInvoice(
    id=uuid4(),
    tenant_id=tenant_id,
    invoice_id=body.invoice_id,
    country="co",
    status=EInvoiceStatus.PENDING,
    created_by=current_user.id,
    nit_prestador=tenant_einvoice_config.nit,
)
session.add(e_invoice)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:invoice:{invoice_id}`: INVALIDATE (e_invoice_status updated)
- `tenant:{tenant_id}:einvoice:{e_invoice_id}`: SET by CO-07 status checks

**Cache TTL:** N/A (invalidation on POST; CO-07 sets cache on status polls)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| einvoice.generation | einvoice_generate | `{ e_invoice_id, tenant_id, invoice_id, country: 'co' }` | After e_invoice row created |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** create
- **Resource:** e_invoice
- **PHI involved:** Yes — invoice contains patient identity + health service data

### Notifications

**Notifications triggered:** Yes (async, via worker)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | einvoice_accepted | clinic_owner | DIAN accepts; includes CUFE |
| in-app | einvoice_rejected | clinic_owner | DIAN rejects; includes rejection code and reason |
| email | einvoice_accepted_pdf | patient | DIAN accepts; sends PDF + CUFE to patient email |

---

## Performance

### Expected Response Time
- **Target:** < 400ms (HTTP handler — enqueue and return 202)
- **Maximum acceptable:** < 1,000ms

### Caching Strategy
- **Strategy:** No caching on POST handler
- **Tenant DIAN config:** Cached in Redis for 1h: `tenant:{tenant_id}:einvoice_config`

### Database Performance

**Queries executed (HTTP handler):** 4–5
1. Resolve tenant + country
2. Fetch invoice
3. Check existing e-invoice
4. Insert e_invoice record
5. Mark prior as superseded (only if force_resend=true)

**Indexes required:**
- `e_invoices.(tenant_id, invoice_id)` — COMPOSITE INDEX for conflict check
- `e_invoices.(tenant_id, status)` — COMPOSITE INDEX for status filtering
- `e_invoices.(tenant_id, created_at DESC)` — INDEX for history

**N+1 prevention:** Invoice and line items loaded in single query with joinedload.

### Pagination

**Pagination:** No (POST endpoint returns single e-invoice reference)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| invoice_id | UUID validation via Pydantic | Rejects non-UUID strings |
| force_resend | Boolean coercion | Prevents string injection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Invoice data contains patient identity (name, document number) and health service codes (CUPS). All PHI is:
- Stored encrypted in object storage (XML file)
- Transmitted over HTTPS only
- Never logged in application logs (only IDs logged)

**Audit requirement:** All e-invoice submissions logged. PHI access logged at batch level.

### DIAN Certificate Security

- DIAN software certificates stored encrypted (AES-256) in tenant secrets vault
- Certificate path stored in `tenant_einvoice_config.certificate_path` (never in regular DB columns)
- Decryption key held in application secret store (not in DB)
- Certificate access logged separately in security audit log

---

## Testing

### Test Cases

#### Happy Path
1. Generate e-invoice for a valid issued invoice
   - **Given:** clinic_owner JWT, invoice in 'issued' status, DIAN config complete, habilitación environment
   - **When:** POST /api/v1/compliance/e-invoice with invoice_id
   - **Then:** 202 Accepted, e_invoice_id returned, status=pending, job enqueued

2. Worker processes and DIAN accepts
   - **Given:** e-invoice in pending status, MATIAS API mock returns acceptance
   - **When:** Worker processes job
   - **Then:** e_invoice.status=accepted, cufe populated, xml_url and pdf_url set, notification sent

#### Edge Cases
1. force_resend after rejection
   - **Given:** Invoice has rejected e-invoice
   - **When:** POST with force_resend=true
   - **Then:** 202 Accepted, prior e-invoice marked superseded, new job queued

2. MATIAS API timeout (retry)
   - **Given:** Worker dequeues job, MATIAS API times out
   - **When:** Worker retries 3 times
   - **Then:** After 3 failures, status=failed, failure_reason set, clinic_owner notified

#### Error Cases
1. Invoice not found
   - **Given:** Non-existent invoice_id
   - **When:** POST with that invoice_id
   - **Then:** 404 Not Found

2. DIAN not configured
   - **Given:** Tenant without DIAN certificate
   - **When:** POST to generate e-invoice
   - **Then:** 402 Payment Required, setup_url provided

3. Already invoiced (no force_resend)
   - **Given:** Invoice with accepted e-invoice
   - **When:** POST without force_resend
   - **Then:** 409 Conflict with existing CUFE details

### Test Data Requirements

**Users:** clinic_owner (with DIAN config), clinic_owner (without DIAN config), receptionist

**Patients/Entities:** Invoice in issued status with line items; DIAN test environment credentials; MATIAS API mock server

### Mocking Strategy

- MATIAS API: Mock server returning configurable responses (acceptance, rejection, timeout)
- Digital signing: Mock signer returning deterministic test CUFE
- Object storage: Mock file writes
- RabbitMQ: In-memory broker for unit tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST returns 202 with e_invoice_id and poll_url
- [ ] Job published to einvoice.generation queue
- [ ] Worker generates valid UBL 2.1 XML
- [ ] CUFE computed per DIAN formula
- [ ] XML digitally signed with tenant certificate
- [ ] XML submitted to MATIAS API
- [ ] Status updated on DIAN acceptance (cufe populated)
- [ ] Status updated on DIAN rejection (dian_response_code set)
- [ ] 402 returned when DIAN not configured
- [ ] 409 returned for already-accepted invoice
- [ ] force_resend=true supersedes prior rejected e-invoice
- [ ] Patient notified by email on acceptance
- [ ] All test cases pass
- [ ] Performance target: < 400ms HTTP handler
- [ ] Quality Hooks passed
- [ ] Audit logging and PHI security verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- DIAN registration / habilitación setup (separate admin setup flow)
- Credit notes (notas crédito, document type 03) — separate spec
- Debit notes (document type 02) — separate spec
- Electronic payroll (nómina electrónica) — different DIAN system
- Mexico SAT e-invoicing (CFDI) — separate country adapter
- Batch e-invoicing (multiple invoices in one request)
- DIAN technical validation document (DTV) queries

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
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

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
| 1.0 | 2026-02-25 | Initial spec |
