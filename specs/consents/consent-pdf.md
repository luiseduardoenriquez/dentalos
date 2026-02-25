# Consent PDF Spec

---

## Overview

**Feature:** Generate and download the PDF version of an informed consent form. Signed consents produce a final legal document with embedded signature images, timestamps, and tamper-detection hash. Draft consents produce a watermarked preview. The PDF is formatted as a legal A4 document with clinic header.

**Domain:** consents

**Priority:** High

**Dependencies:** IC-05 (consent-sign.md), IC-06 (consent-get.md), auth/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, patient (own consents only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients can only download PDFs of their own consents.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/consents/{consent_id}/pdf
```

**Rate Limiting:**
- 30 requests per minute per user
- PDF generation is CPU-intensive; throttled to prevent abuse

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |
| Accept | No | string | Expected response type | application/pdf |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient owning the consent | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| consent_id | Yes | string (UUID) | Valid UUID v4, must belong to patient | Consent whose PDF to download | c3d4e5f6-0000-4000-8000-000000000030 |

### Query Parameters

None.

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Content-Type:** `application/pdf`

**Headers:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="consentimiento_{consent_id_short}_{date}.pdf"
Content-Length: {bytes}
X-Content-Hash: {SHA256 hex of PDF file} — for signed consents only
```

**Body:** Binary PDF file

**PDF Structure (signed consent — legal document):**
```
[Clinic Header]
  - Clinic logo (if uploaded)
  - Clinic name, address, phone, NIT
  - Tenant branding colors

[Document Title]
  - "CONSENTIMIENTO INFORMADO"
  - Consent ID (last 8 chars) for reference

[Consent Body]
  - Full content_rendered HTML converted to PDF-safe layout
  - Patient info block: name, cedula, age
  - Procedure block: description, tooth numbers
  - Doctor block: name, specialty, Tarjeta Profesional number

[Signature Block]
  For each collected signature (patient, doctor, witness):
    - Signature image (PNG embedded)
    - Signer name
    - Signer document number
    - Signature type (Paciente / Odontologo / Testigo)
    - Timestamp: DD/MM/YYYY HH:MM:SS (Colombia TZ: America/Bogota)
    - IP address (last two octets masked for patient-facing copies)

[Footer]
  - Document hash: SHA256 prefix (first 16 chars) for tamper detection
  - "Este documento fue firmado digitalmente conforme a la Ley 527 de 1999 de la Republica de Colombia."
  - Generation timestamp
  - Page numbers: "Pagina X de Y"
```

**PDF Structure (draft consent — preview):**
```
[Same structure as above, but:]
  - Red diagonal watermark: "BORRADOR - NO VALIDO"
  - No signature block (no signatures yet)
  - Footer note: "Este documento es un borrador y no tiene validez legal."
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role not allowed, or patient attempting to access another patient's consent PDF.

**Example (JSON body, not PDF):**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para descargar este consentimiento."
}
```

#### 404 Not Found
**When:** `patient_id` or `consent_id` not found in tenant.

**Example (JSON body):**
```json
{
  "error": "not_found",
  "message": "Consentimiento no encontrado."
}
```

#### 409 Conflict
**When:** Consent is in `voided` status and the caller is not `clinic_owner`.

**Example:**
```json
{
  "error": "consent_voided",
  "message": "Este consentimiento fue anulado. Contacte al propietario de la clinica para acceder a este documento."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** PDF generation failure.

---

## Business Logic

**Step-by-step process:**

1. Validate path parameters.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role — if patient: verify JWT sub matches patient_id's portal user. Return 403 if mismatch.
4. Verify `patient_id` exists in tenant; verify `consent_id` exists and belongs to `patient_id`. Return 404 if not.
5. Check consent status:
   - If `voided` and requester is not `clinic_owner`: return 409.
   - If `voided` and requester is `clinic_owner`: generate PDF with void watermark.
6. Check object storage cache: look for pre-generated PDF at `s3://bucket/tenant/{tenant_id}/consents/{consent_id}/consent_{consent_id}.pdf`. If exists and consent is `signed` (immutable), return the cached PDF directly (no re-generation needed).
7. If no cached PDF (or consent is `draft`): generate PDF on demand using HTML-to-PDF engine (WeasyPrint or equivalent).
   - Fetch consent record with all signatures and signature image URLs.
   - Fetch tenant profile (logo URL, name, address, NIT, colors).
   - Compose PDF template with all sections per structure above.
   - Embed signature PNG images inline.
   - Add watermark if status is `draft` or `voided`.
8. For signed consents: verify `content_hash` matches SHA256 of stored `content_rendered` before including in PDF (tamper detection guard).
9. For signed consents: upload generated PDF to object storage for future cache hits.
10. Write audit log entry.
11. Stream PDF bytes as response.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| consent_id | Valid UUID v4 | El identificador del consentimiento no es valido. |

**Business Rules:**

- Signed consents have a pre-generated and cached PDF stored in S3 (generated asynchronously when all signatures are collected via IC-05). Direct download from S3 is preferred for performance.
- Draft consent PDFs are generated on-demand and are NOT cached (they change as signatures are collected).
- Voided consent PDFs are accessible only to `clinic_owner` for legal compliance and audit purposes.
- The PDF is streamed directly — not base64-encoded in a JSON response.
- If `content_hash` verification fails (tamper detected), return 500 and alert via Sentry — this should never occur in normal operation.
- Signature image URLs are fetched from object storage and embedded in the PDF; they are never returned in JSON responses.
- IP address in signature block: last two octets masked for patient-facing downloads (e.g., `190.25.x.x`); full IP shown for clinic staff.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Signed consent, pre-generated PDF exists in S3 | Stream directly from S3 (< 100ms); skip PDF generation |
| Draft consent PDF requested | Generate on-demand with "BORRADOR" watermark; do not cache |
| Voided consent requested by clinic_owner | Generate with "ANULADO" watermark and void reason in footer |
| Tenant has no logo | Render clinic name as text in header; no broken image |
| Consent has optional witness signature | Witness block included in signature section if witness signed |
| PDF generation fails mid-stream | Return 500; do not send partial PDF bytes |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `s3://bucket/tenant/{tenant_id}/consents/{consent_id}/consent_{consent_id}.pdf`: Pre-generated signed PDF stored in S3 (uploaded during IC-05 finalization, not on this request)

**Cache TTL:** Indefinite for signed consents (immutable documents). Draft PDFs not cached.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None (PDF generation for signed consents was already dispatched in IC-05)

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** consent_pdf
- **PHI involved:** Yes (PDF contains patient name, cedula, signature data)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (signed consent — S3 cache hit)
- **Maximum acceptable:** < 3000ms (draft consent — on-demand PDF generation)

### Caching Strategy
- **Strategy:** S3 object storage for signed consents (generated once, served forever)
- **Cache key:** `s3://bucket/tenant/{tenant_id}/consents/{consent_id}/consent_{consent_id}.pdf`
- **TTL:** Indefinite (signed consents are immutable)
- **Invalidation:** Not applicable for signed consents; draft PDFs never cached

### Database Performance

**Queries executed:** 1–2 (consent + signatures JOIN; tenant profile lookup for branding)

**Indexes required:**
- `{tenant}.consents.(patient_id, id)` — COMPOSITE INDEX (already required by IC-06)
- `{tenant}.digital_signatures.consent_id` — INDEX (already required by IC-05)

**N+1 prevention:** All signatures fetched via single JOIN; S3 URLs fetched in parallel for signature images.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Reject malformed path params |
| consent_id | Pydantic UUID validator | Reject malformed path params |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** PDF is binary output — XSS not applicable. HTML content sanitized at template creation time (IC-02) before inclusion in PDF.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient name, cedula, age, procedure description, signature images (biometric-equivalent), IP addresses (partial for patient copies)

**Audit requirement:** All access logged (PDF download is a high-value PHI access event).

---

## Testing

### Test Cases

#### Happy Path
1. Download signed consent PDF (from S3 cache)
   - **Given:** Signed consent with pre-generated S3 PDF, authenticated doctor
   - **When:** GET /api/v1/patients/{patient_id}/consents/{consent_id}/pdf
   - **Then:** 200 OK, application/pdf content, binary PDF returned with correct Content-Disposition header

2. Download draft consent PDF (on-demand)
   - **Given:** Draft consent (no signatures), authenticated doctor
   - **When:** GET /api/v1/patients/{patient_id}/consents/{consent_id}/pdf
   - **Then:** 200 OK, PDF has "BORRADOR" watermark, no signature block

3. Patient downloads own consent PDF
   - **Given:** Patient with portal access, signed consent
   - **When:** GET (patient JWT)
   - **Then:** 200 OK, PDF returned, IP addresses in signature block partially masked

4. Content hash verification passes
   - **Given:** Signed consent, content_hash matches stored content_rendered
   - **When:** GET
   - **Then:** PDF generated/streamed without tamper error

#### Edge Cases
1. No clinic logo uploaded
   - **Given:** Tenant has no logo in profile
   - **When:** GET
   - **Then:** 200 OK, PDF header shows clinic name as text (no broken image)

2. Voided consent accessed by clinic_owner
   - **Given:** Consent with status=voided, requester is clinic_owner
   - **When:** GET
   - **Then:** 200 OK, PDF has "ANULADO" watermark and void_reason in footer

3. Consent with optional witness signature
   - **Given:** Signed consent with patient, doctor, and witness signatures
   - **When:** GET
   - **Then:** 200 OK, PDF signature block contains all three signatures

#### Error Cases
1. Patient accessing another patient's PDF
   - **Given:** Patient A's JWT, consent_id belonging to Patient B
   - **When:** GET
   - **Then:** 403 Forbidden (JSON response, not PDF)

2. Consent not found
   - **Given:** Valid UUID not matching any consent
   - **When:** GET
   - **Then:** 404 Not Found (JSON response)

3. Voided consent accessed by non-clinic_owner
   - **Given:** Doctor requesting a voided consent PDF
   - **When:** GET
   - **Then:** 409 Conflict (JSON response)

4. Tamper detection failure (content_hash mismatch)
   - **Given:** Consent record has been tampered with (content_rendered differs from stored hash)
   - **When:** GET
   - **Then:** 500 Internal Server Error, Sentry alert triggered

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (happy path); patient with portal access; patient without portal access

**Patients/Entities:** Signed consent with pre-generated S3 PDF; draft consent; voided consent; consent with all three signatures; tenant with and without logo.

### Mocking Strategy

- S3 / object storage: Mock GET (return pre-built test PDF bytes), mock PUT
- PDF generation engine (WeasyPrint): Integration test with real engine in test environment; mock in unit tests
- Sentry: Mock capture_exception; assert called on tamper detection
- Signature image URLs: Mock S3 pre-signed URL response

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Signed consent PDF returned from S3 cache with correct Content-Type and Content-Disposition headers
- [ ] Draft consent PDF generated on-demand with "BORRADOR" watermark
- [ ] Voided consent PDF accessible to clinic_owner only with "ANULADO" watermark
- [ ] Signature images embedded in signed consent PDF
- [ ] Patient copies have IP addresses partially masked in signature block
- [ ] Content hash verification performed before PDF generation for signed consents
- [ ] Tamper detection failure triggers Sentry alert and returns 500
- [ ] Patient can only download their own consent PDFs (403 otherwise)
- [ ] Audit log entry written for every PDF download
- [ ] All test cases pass
- [ ] Performance target met (< 100ms S3 cache hit, < 3s on-demand generation)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Async pre-generation of the PDF (triggered from IC-05 via RabbitMQ)
- Sending the PDF to the patient via email (separate notification workflow)
- PDF merging with other clinical documents
- Electronic signature certificates (PKI-based) — only PNG signature images embedded

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
- [x] Input sanitization defined (Pydantic UUID)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined (two-tier: cache vs. on-demand)
- [x] Caching strategy stated (S3 for signed, no cache for draft)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A — single document)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible — tamper detection alert)
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
