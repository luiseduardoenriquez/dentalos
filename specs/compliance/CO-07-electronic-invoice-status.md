# CO-07 — Electronic Invoice Status Spec

## Overview

**Feature:** Poll the status of an electronic invoice submission with the tax authority. For Colombia, checks the DIAN acceptance/rejection status via MATIAS API or from the locally cached DIAN response. Returns full status details including CUFE, DIAN response codes, human-readable messages, and document download URLs. Designed to be called repeatedly after CO-06 until a terminal status is reached.

**Domain:** compliance / billing

**Priority:** Low (Sprint 13-14)

**Dependencies:** CO-06 (electronic-invoice), infra/caching.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** E-invoice record must belong to the requesting tenant. All access is tenant-isolated.

---

## Endpoint

```
GET /api/v1/compliance/e-invoice/{e_invoice_id}/status
```

**Rate Limiting:**
- 60 requests per minute per tenant (polling-friendly; most polls hit Redis cache)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| e_invoice_id | Yes | string (UUID) | Valid UUID v4 | E-invoice record ID returned by CO-06 | ei_a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| force_refresh | No | boolean | default=false | Force re-query to MATIAS API even if locally cached as accepted/rejected | false |
| include_xml_preview | No | boolean | default=false | Include first 500 chars of signed XML in response (for debugging) | false |

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "e_invoice_id": "string (UUID)",
  "invoice_id": "string (UUID)",
  "invoice_number": "string — human-readable invoice number",
  "status": "string — enum: pending | generating | submitted | accepted | rejected | failed | superseded",
  "status_display": "string — Spanish label for UI",
  "status_color": "string — green | yellow | red | gray (UI badge)",
  "is_terminal": "boolean — true if status is accepted, rejected, failed, or superseded",
  "country_adapter": "string — co | mx | ...",
  "colombia_specific": {
    "cufe": "string | null — assigned by DIAN on acceptance",
    "nit_prestador": "string — clinic NIT",
    "matias_submission_id": "string | null",
    "matias_transaction_id": "string | null — MATIAS tracking ID",
    "dian_environment": "string — habilitacion | production",
    "dian_response_code": "string | null — DIAN status code",
    "dian_response_message": "string | null — DIAN human-readable message in Spanish",
    "dian_accepted_at": "string (ISO 8601) | null",
    "dian_rejected_at": "string (ISO 8601) | null",
    "dian_rejection_errors": "array[DIANError] | null — populated on rejection"
  },
  "xml_url": "string | null — pre-signed URL to download signed XML (1h TTL)",
  "pdf_url": "string | null — pre-signed URL to download PDF representation (1h TTL)",
  "xml_preview": "string | null — first 500 chars of XML (only if include_xml_preview=true)",
  "created_at": "string (ISO 8601)",
  "submitted_at": "string (ISO 8601) | null",
  "accepted_at": "string (ISO 8601) | null",
  "failed_at": "string (ISO 8601) | null",
  "failure_reason": "string | null — set if status=failed",
  "retry_count": "integer — number of MATIAS submission attempts",
  "next_retry_at": "string (ISO 8601) | null — when next auto-retry is scheduled (if pending)",
  "superseded_by": "string (UUID) | null — ID of the new e-invoice that superseded this one"
}
```

**DIANError schema:**
```json
{
  "error_code": "string — DIAN error code",
  "error_description": "string — DIAN error description in Spanish",
  "field": "string | null — UBL field that caused the error",
  "corrective_action": "string — guidance to fix"
}
```

**Example (accepted):**
```json
{
  "e_invoice_id": "ei_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "invoice_id": "inv_f1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "invoice_number": "FV-2026-0042",
  "status": "accepted",
  "status_display": "Aceptada por DIAN",
  "status_color": "green",
  "is_terminal": true,
  "country_adapter": "co",
  "colombia_specific": {
    "cufe": "a4f8b2c1d3e5f7890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12",
    "nit_prestador": "900123456",
    "matias_submission_id": "mat_sub_789xyz",
    "matias_transaction_id": "mat_txn_456abc",
    "dian_environment": "production",
    "dian_response_code": "00",
    "dian_response_message": "Documento procesado correctamente.",
    "dian_accepted_at": "2026-02-25T10:01:35Z",
    "dian_rejected_at": null,
    "dian_rejection_errors": null
  },
  "xml_url": "https://storage.dentalos.io/einvoices/tn_abc/ei_a1b2/invoice.xml?token=xyz&expires=...",
  "pdf_url": "https://storage.dentalos.io/einvoices/tn_abc/ei_a1b2/invoice.pdf?token=xyz&expires=...",
  "xml_preview": null,
  "created_at": "2026-02-25T10:00:00Z",
  "submitted_at": "2026-02-25T10:00:58Z",
  "accepted_at": "2026-02-25T10:01:35Z",
  "failed_at": null,
  "failure_reason": null,
  "retry_count": 1,
  "next_retry_at": null,
  "superseded_by": null
}
```

**Example (rejected):**
```json
{
  "e_invoice_id": "ei_b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "invoice_id": "inv_a2b3c4d5",
  "invoice_number": "FV-2026-0043",
  "status": "rejected",
  "status_display": "Rechazada por DIAN",
  "status_color": "red",
  "is_terminal": true,
  "country_adapter": "co",
  "colombia_specific": {
    "cufe": null,
    "nit_prestador": "900123456",
    "matias_submission_id": "mat_sub_790abc",
    "matias_transaction_id": "mat_txn_457def",
    "dian_environment": "production",
    "dian_response_code": "99",
    "dian_response_message": "Documento rechazado. Verifique los errores de validación.",
    "dian_accepted_at": null,
    "dian_rejected_at": "2026-02-25T11:00:12Z",
    "dian_rejection_errors": [
      {
        "error_code": "FAU10",
        "error_description": "El NIT del adquiriente no existe en el RUT.",
        "field": "AccountingCustomerParty.PartyIdentification.ID",
        "corrective_action": "Verifique el NIT o cédula del paciente en el registro del paciente."
      }
    ]
  },
  "xml_url": "https://storage.dentalos.io/einvoices/tn_abc/ei_b2c3/invoice.xml?token=...",
  "pdf_url": null,
  "xml_preview": null,
  "created_at": "2026-02-25T10:55:00Z",
  "submitted_at": "2026-02-25T10:55:30Z",
  "accepted_at": null,
  "failed_at": null,
  "failure_reason": null,
  "retry_count": 1,
  "next_retry_at": null,
  "superseded_by": null
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Caller does not have `clinic_owner` or `receptionist` role, or e-invoice belongs to a different tenant.

#### 404 Not Found
**When:** E-invoice with given `e_invoice_id` does not exist in the tenant context.

**Example:**
```json
{
  "error": "e_invoice_not_found",
  "message": "Electronic invoice not found",
  "details": { "e_invoice_id": "ei_a1b2c3d4" }
}
```

#### 422 Unprocessable Entity
**When:** `e_invoice_id` is not a valid UUID format.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** MATIAS API unreachable during force_refresh; unexpected DB error.

---

## Business Logic

**Step-by-step process:**

1. Validate `e_invoice_id` as valid UUID v4.
2. Resolve tenant_id from JWT.
3. Verify caller has `clinic_owner` or `receptionist` role.
4. Check cache: `tenant:{tenant_id}:einvoice:{e_invoice_id}` — if hit and `force_refresh=false` and status is terminal, return cached response.
5. Fetch `e_invoices` record WHERE `id = e_invoice_id AND tenant_id = tenant_id`. Return 404 if not found.
6. If status is NOT terminal (pending, generating, submitted) and `force_refresh=false`:
   - Check `last_status_check_at` on the record.
   - If checked within last 10 seconds, return locally stored status (avoid hammering MATIAS).
   - Otherwise, query MATIAS API for status update: `GET /api/v1/status/{matias_submission_id}`.
   - Update local `e_invoices` record with latest MATIAS/DIAN response.
7. If `force_refresh=true`:
   - Always re-query MATIAS API regardless of current status.
   - Update local record.
8. Generate pre-signed URLs for `xml_url` and `pdf_url` if files exist in object storage.
9. If `include_xml_preview=true` and XML exists, read first 500 characters from storage.
10. Build response model from local record (enriched with MATIAS response if refreshed).
11. Cache response: `tenant:{tenant_id}:einvoice:{e_invoice_id}` TTL 30s (short, since status changes).
    - For terminal statuses (accepted, rejected, failed): TTL 3600s (no further changes expected).
12. Update `e_invoices.last_status_check_at = now()`.
13. Write audit log: action=`einvoice_status_read`, resource=`e_invoice`, resource_id=`e_invoice_id`.
14. Return 200 OK.

**MATIAS Status Query:**
- Endpoint: `GET https://api.matias.com.co/v1/invoices/{matias_submission_id}/status`
- Headers: `X-Matias-Key: {tenant_matias_key}`, `X-Tenant-NIT: {nit}`
- Response mapped to internal statuses:
  - MATIAS `PENDIENTE` → `submitted`
  - MATIAS `ACEPTADO` → `accepted`; extract CUFE from response
  - MATIAS `RECHAZADO` → `rejected`; extract DIAN errors
  - MATIAS `ERROR` → `failed`; extract technical failure reason

**Status Transition Chart:**

```
pending → generating → submitted → accepted (terminal)
                                 → rejected (terminal)
                    → failed (terminal)
any → superseded (terminal, when force_resend=true creates replacement)
```

**Status Display Mapping:**

| Status | status_display | status_color | is_terminal |
|--------|---------------|--------------|-------------|
| pending | En cola | gray | false |
| generating | Generando... | gray | false |
| submitted | Enviado a DIAN | yellow | false |
| accepted | Aceptada por DIAN | green | true |
| rejected | Rechazada por DIAN | red | true |
| failed | Error técnico | red | true |
| superseded | Reemplazada | gray | true |

**Business Rules:**

- Polling is rate-limited to prevent MATIAS API abuse. A 10-second local debounce prevents repeated MATIAS calls within the same second.
- DIAN `response_code = "00"` means accepted; any other code means rejected or error.
- `cufe` is only populated on acceptance. CUFE must be displayed on the invoice PDF for legal compliance.
- If `force_refresh=true` is called on an accepted e-invoice, the MATIAS response is re-fetched but the status cannot be downgraded from accepted.
- `dian_rejection_errors` are mapped from MATIAS's translation of raw DIAN error codes to human-readable descriptions in Spanish.
- For rejected e-invoices, the `corrective_action` in each `DIANError` references the specific patient/invoice field to fix before resubmitting.
- `xml_preview` (when enabled) is provided for debugging only; first 500 characters of the signed XML header (no patient PHI in XML header section).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| e_invoice_id | Valid UUID v4 | "e_invoice_id must be a valid UUID" |
| force_refresh | Boolean | "force_refresh must be boolean" |
| include_xml_preview | Boolean | "include_xml_preview must be boolean" |

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| MATIAS API returns 503 during status check | Use locally stored status; add flag `status_source: "local_cache"` to response |
| E-invoice still pending after 30 minutes | Worker marks as failed with failure_reason="timeout"; status=failed |
| Multiple status checks within 10 seconds | Returns locally stored status; no MATIAS API call; flag `status_source: "local_cache"` |
| Accepted e-invoice force_refresh | MATIAS re-queried; if it still says accepted, data refreshed; status stays accepted |
| superseded e-invoice | Status=superseded, superseded_by populated with new e_invoice_id |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `e_invoices`: UPDATE `status`, `cufe`, `dian_response_code`, `dian_response_message`, `accepted_at`, `rejected_at`, `last_status_check_at`, `dian_rejection_errors`

**Public schema tables affected:**
- None

**Example query (SQLAlchemy):**
```python
# Update after MATIAS status check
await session.execute(
    update(EInvoice)
    .where(EInvoice.id == e_invoice_id, EInvoice.tenant_id == tenant_id)
    .values(
        status=mapped_status,
        cufe=matias_response.cufe,
        dian_response_code=matias_response.response_code,
        dian_response_message=matias_response.response_message,
        accepted_at=matias_response.accepted_at,
        last_status_check_at=utcnow(),
    )
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:einvoice:{e_invoice_id}`: SET
  - TTL: 30s for non-terminal statuses
  - TTL: 3600s for terminal statuses (accepted, rejected, failed, superseded)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — this is a read/query endpoint.

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** read
- **Resource:** e_invoice
- **PHI involved:** No (status metadata; PHI is inside the XML/PDF files, not in status fields)

### Notifications

**Notifications triggered:** No (notifications sent by CO-06 worker on status change, not by this polling endpoint)

---

## Performance

### Expected Response Time
- **Target:** < 100ms (cache hit or non-terminal with recent local check)
- **Maximum acceptable:** < 2,000ms (force_refresh requiring MATIAS API roundtrip)

### Caching Strategy
- **Strategy:** Redis cache with adaptive TTL
- **Cache key:** `tenant:{tenant_id}:einvoice:{e_invoice_id}`
- **TTL:** 30s (non-terminal), 3600s (terminal)
- **Invalidation:** Force invalidated by force_refresh=true

### Database Performance

**Queries executed:** 1–2 (fetch e_invoice, optional UPDATE after MATIAS call)

**Indexes required:**
- `e_invoices.(id, tenant_id)` — COMPOSITE UNIQUE (primary lookup)
- `e_invoices.(tenant_id, status, created_at DESC)` — COMPOSITE INDEX for history queries

**N+1 prevention:** Single record fetch; no joins required.

### Pagination

**Pagination:** No (single record endpoint)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| e_invoice_id | UUID validation via Pydantic Path | Rejects non-UUID strings |
| force_refresh | Boolean coercion | Prevents injection |
| include_xml_preview | Boolean coercion | Prevents injection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. `xml_preview` is returned as a plain string with no HTML rendering.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None in JSON response body. `xml_preview` returns only XML header (no patient PHI). Full XML/PDF downloads via pre-signed URLs are protected by HTTPS + 1-hour URL expiry.

**Audit requirement:** All status reads logged.

### MATIAS API Security

- MATIAS API key stored in encrypted tenant config, never in response body
- MATIAS calls made server-side only (key never exposed to client)
- MATIAS API responses logged at INFO level (response codes only; no patient data)

---

## Testing

### Test Cases

#### Happy Path
1. Poll pending e-invoice (first poll)
   - **Given:** clinic_owner JWT, e-invoice in pending status, no cache
   - **When:** GET /api/v1/compliance/e-invoice/{e_invoice_id}/status
   - **Then:** 200 OK, status=pending, is_terminal=false, next_retry_at populated

2. Poll submitted e-invoice; MATIAS returns accepted
   - **Given:** e-invoice in submitted status, MATIAS mock returns ACEPTADO
   - **When:** GET status
   - **Then:** 200 OK, status=accepted, cufe populated, is_terminal=true, xml_url and pdf_url populated

3. Poll submitted e-invoice; MATIAS returns rejected
   - **Given:** e-invoice submitted, MATIAS mock returns RECHAZADO with error FAU10
   - **When:** GET status
   - **Then:** 200 OK, status=rejected, dian_rejection_errors has 1 entry with FAU10, corrective_action populated

4. Cache hit (terminal status)
   - **Given:** Cached accepted e-invoice (TTL 3600s)
   - **When:** GET status
   - **Then:** 200 OK from cache in < 50ms; cache_hit=true

5. force_refresh on accepted e-invoice
   - **Given:** Accepted e-invoice in cache
   - **When:** GET with force_refresh=true
   - **Then:** 200 OK, MATIAS re-queried, status still accepted

#### Edge Cases
1. Rapid polling (within 10s of last check)
   - **Given:** e-invoice last checked 5 seconds ago
   - **When:** GET status without force_refresh
   - **Then:** 200 OK, uses local DB value; status_source=local_cache; no MATIAS call

2. MATIAS API unavailable
   - **Given:** MATIAS returns 503
   - **When:** GET status with force_refresh=true
   - **Then:** 200 OK, last known status returned with status_source=local_cache; warning flag in response

3. superseded e-invoice
   - **Given:** E-invoice was superseded by force_resend
   - **When:** GET status
   - **Then:** 200 OK, status=superseded, superseded_by populated with new e_invoice_id

#### Error Cases
1. E-invoice not found
   - **Given:** Non-existent e_invoice_id
   - **When:** GET status
   - **Then:** 404 Not Found

2. Cross-tenant access attempt
   - **Given:** E-invoice from tenant_B, JWT from tenant_A
   - **When:** GET status
   - **Then:** 404 Not Found (no cross-tenant info leakage)

3. Receptionist has access
   - **Given:** Receptionist JWT
   - **When:** GET status
   - **Then:** 200 OK (receptionist is allowed for this endpoint)

### Test Data Requirements

**Users:** clinic_owner, receptionist (both should get 200), doctor (should get 403)

**Patients/Entities:** E-invoices in each status; MATIAS mock server with configurable response; test CUFE string

### Mocking Strategy

- MATIAS API: Mock server (configurable response per e_invoice_id)
- Redis: Use fakeredis; test both cache-hit and miss paths
- Object storage: Mock presigned URL generation

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns correct status for all 7 status values
- [ ] MATIAS API queried for non-terminal statuses (unless recent check < 10s)
- [ ] cufe populated on acceptance
- [ ] dian_rejection_errors populated on rejection with corrective_action
- [ ] is_terminal correctly set for accepted, rejected, failed, superseded
- [ ] Pre-signed xml_url and pdf_url generated when files exist
- [ ] Cache used with 30s TTL (non-terminal) and 3600s TTL (terminal)
- [ ] force_refresh bypasses cache and re-queries MATIAS
- [ ] 404 for missing or cross-tenant e-invoice
- [ ] Receptionist can access (not just clinic_owner)
- [ ] All test cases pass
- [ ] Performance target: < 100ms cached, < 2s with MATIAS call
- [ ] Quality Hooks passed
- [ ] Audit logging verified

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Generating the e-invoice (see CO-06)
- Listing all e-invoices for a tenant (separate billing/e-invoice list endpoint)
- Resubmitting a rejected e-invoice (see CO-06 with force_resend=true)
- DIAN technical validation document (DTV) format
- Mexico SAT status checking
- Sending the PDF to the patient (handled by notification worker in CO-06)

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
- [x] Caching strategy stated (adaptive TTL)
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
