# PP-12 Portal Consent Sign Spec

---

## Overview

**Feature:** Patient signs an informed consent form from the portal. Displays the full consent document text, captures a base64-encoded PNG signature, and records timestamp, IP, and device info. Uses the same signing logic as the clinic-side consent signing flow. The signature is immutable once recorded. Legally valid under Colombia Ley 527/1999.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-07 (portal-documents.md), PP-05 (portal-treatment-plan-approve.md for signature pattern), consents domain (IC-01 through IC-09), patients/digital-signature.md, infra/audit-logging.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient can only sign consent forms addressed to them — ownership enforced at query level by patient_id = jwt.sub. Once signed, the endpoint returns 409 on re-submission.

---

## Endpoint

```
POST /api/v1/portal/consents/{consent_id}/sign
```

**Rate Limiting:**
- 10 requests per hour per patient (signing is intentional; low rate limit prevents automation)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |
| X-Forwarded-For | No | string | Patient's real IP (set by reverse proxy) | 190.25.1.45 |
| User-Agent | No | string | Patient's device/browser info | Mozilla/5.0... |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| consent_id | Yes | string (UUID) | Valid UUID v4 | Consent form to sign | d4e5f6a7-b8c9-0123-abcd-ef1234567890 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "signature_data": "string (required) — base64-encoded PNG of patient signature, max 500KB decoded",
  "agreed_to_document": "boolean (required) — must be true; patient confirms they have read and understood the consent document",
  "full_name_confirmation": "string (required) — patient types their full name as confirmation, max 200 chars",
  "document_hash": "string (required) — SHA-256 hash of the consent document content as displayed to patient; prevents signing a document that changed"
}
```

**Example Request:**
```json
{
  "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "agreed_to_document": true,
  "full_name_confirmation": "Maria Garcia Lopez",
  "document_hash": "b94f5c8e1b2d4f67890abcdef1234567890abcdef1234567890abcdef12345678"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "status": "string — always 'signed'",
  "consent_id": "uuid",
  "consent_type": "string — name of the consent form",
  "signed_at": "string (ISO 8601 datetime)",
  "signature": {
    "hash": "string — SHA-256 hash of the signature PNG bytes (hex, 64 chars)",
    "signed_by_name": "string — full_name_confirmation as recorded",
    "signed_at": "string (ISO 8601 datetime)",
    "signed_from_ip": "string — anonymized IP (last octet masked for display)",
    "device_info": "string — user agent truncated to 200 chars",
    "document_hash": "string — SHA-256 of the document content at time of signing"
  },
  "document_url": "string — signed S3 URL to the signed consent PDF (valid 60 minutes)"
}
```

**Example:**
```json
{
  "status": "signed",
  "consent_id": "d4e5f6a7-b8c9-0123-abcd-ef1234567890",
  "consent_type": "Consentimiento Informado para Endodoncia",
  "signed_at": "2026-02-25T17:30:00-05:00",
  "signature": {
    "hash": "c5e7f9a1b3d5f7890abcdef1234567890abcdef1234567890abcdef12345678ab",
    "signed_by_name": "Maria Garcia Lopez",
    "signed_at": "2026-02-25T17:30:00-05:00",
    "signed_from_ip": "190.25.1.XXX",
    "device_info": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/537.36",
    "document_hash": "b94f5c8e1b2d4f67890abcdef1234567890abcdef1234567890abcdef12345678"
  },
  "document_url": "https://s3.amazonaws.com/dentaios-docs/tn_abc123/consents/consent_d4e5.pdf?X-Amz-Expires=3600&..."
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing fields, agreed_to_document=false, invalid base64 or non-PNG signature.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "agreed_to_document": ["Debe confirmar que ha leido y comprendido el documento de consentimiento."],
    "signature_data": ["La firma no es valida. Se requiere imagen PNG en formato base64."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal", role is not "patient", or consent does not belong to this patient.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para firmar este consentimiento."
}
```

#### 404 Not Found
**When:** Consent form not found in tenant, or belongs to a different patient.

**Example:**
```json
{
  "error": "consent_not_found",
  "message": "Consentimiento informado no encontrado."
}
```

#### 409 Conflict
**When:** Consent form already signed. Signature is immutable.

**Example:**
```json
{
  "error": "already_signed",
  "message": "Este consentimiento ya fue firmado el 2026-01-17T14:30:00-05:00. La firma no puede modificarse.",
  "details": {
    "signed_at": "2026-01-17T14:30:00-05:00",
    "signed_by_name": "Maria Garcia Lopez"
  }
}
```

#### 410 Gone
**When:** Consent form has been revoked by clinic (cannot be signed if revoked).

**Example:**
```json
{
  "error": "consent_revoked",
  "message": "Este consentimiento informado ha sido revocado. Por favor contacte a la clinica."
}
```

#### 422 Unprocessable Entity
**When:** document_hash mismatch (document changed since patient started reading it) or consent status does not allow signing.

**Example:**
```json
{
  "error": "document_changed",
  "message": "El documento de consentimiento ha cambiado desde que inicio la firma. Por favor recargue y vuelva a intentarlo."
}
```

#### 413 Payload Too Large
**When:** signature_data decoded PNG exceeds 500KB.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** S3 upload or PDF generation failure.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Validate path parameter: consent_id must be valid UUID v4.
3. Validate request body: required fields, agreed_to_document must be true.
4. Decode signature_data from base64; verify PNG magic bytes (`\x89PNG\r\n\x1a\n`). Return 400 if invalid.
5. Check decoded signature size <= 500KB. Return 413 if larger.
6. Check rate limit: 10 signings/hour per patient_id.
7. Resolve tenant schema; set `search_path`.
8. Fetch consent form: `SELECT * FROM consent_forms WHERE id = :consent_id AND patient_id = :patient_id`. If not found → 404.
9. Check consent status:
   - If status = 'signed' → 409 with signed_at and signed_by_name.
   - If status = 'revoked' → 410 Gone.
   - If status NOT IN ('pending_signature', 'sent') → 422 consent_not_signable.
10. Verify document_hash: compute SHA-256 of `consent_forms.document_content` (the canonical text). Compare to `data.document_hash`. If mismatch → 422 document_changed (document was updated after patient started reading).
11. Compute signature hash: SHA-256 of decoded PNG bytes (hex, 64 chars).
12. Extract client IP from `X-Forwarded-For`; mask last octet for response (store full IP in DB).
13. Extract and truncate User-Agent to 200 chars.
14. Upload signature PNG to S3: `s3://dentaios-docs/{tenant_id}/consents/signatures/consent_{consent_id}_patient_{patient_id}_{timestamp}.png`.
15. Within a database transaction:
    a. UPDATE consent_forms SET status='signed', signed_at=NOW(), signed_by_patient_id=patient_id, signature_hash=:hash, signature_url=:s3_url, signed_full_name=:full_name, signed_from_ip=:ip, signed_user_agent=:ua, document_hash_at_signing=:document_hash WHERE id=:consent_id.
    b. INSERT audit log: action='patient_sign_consent', resource='consent_form', resource_id=consent_id, actor=patient_id, metadata={hash, ip, device, document_hash}.
16. Dispatch RabbitMQ job: generate signed consent PDF (consent text + embedded signature image + metadata block) and store to S3.
17. Dispatch RabbitMQ job: notify clinic staff that patient signed consent.
18. Invalidate document cache for this patient.
19. Return 200 with signed confirmation and document URL.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| consent_id | Valid UUID v4 | Consentimiento informado no encontrado. |
| signature_data | Valid base64; decodes to PNG; decoded size <= 500KB | La firma no es valida. |
| agreed_to_document | Must be boolean true | Debe confirmar que ha leido el consentimiento. |
| full_name_confirmation | Required; 1-200 chars; strip whitespace | El nombre de confirmacion es obligatorio. |
| document_hash | SHA-256 hex string (64 chars) | Hash del documento no valido. |

**Business Rules:**

- Consent signature is **immutable** — once signed, returns 409 on any re-submission. Only clinic_owner can invalidate via admin flow.
- `document_hash` mechanism ensures patient signed exactly the document content shown to them (tamper-evident). The hash is computed server-side from `consent_forms.document_content` and compared to client-provided hash.
- Full IP stored in DB for legal audit; only masked version returned in API response.
- The `signed_full_name` is stored verbatim as typed by patient (for legal record).
- Colombia Ley 527/1999: this digital signature (hash + IP + timestamp + biometric signature image) constitutes a legally valid electronic signature.
- If consent requires witness or guardian signature (e.g., minor patient), that is handled clinic-side (IC-07) and is out of scope for portal.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Consent document updated by clinic while patient is reading | document_hash mismatch → 422 document_changed |
| Consent in 'draft' status (not yet sent to patient) | 422 consent_not_signable |
| Minor patient (under 18) consent | Portal signing allowed; clinic must verify guardian separately (out of scope here) |
| Patient uploads consent from a different patient's portal session | 404 (ownership enforced at query level) |
| S3 upload fails | Rollback DB transaction; 500 returned; no partial state |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `consent_forms`: UPDATE — status='signed', signed_at, signed_by_patient_id, signature_hash, signature_url, signed_full_name, signed_from_ip, signed_user_agent, document_hash_at_signing

**Example query (SQLAlchemy):**
```python
stmt = (
    update(ConsentForm)
    .where(
        ConsentForm.id == consent_id,
        ConsentForm.patient_id == patient_id,
        ConsentForm.status.in_(["pending_signature", "sent"]),
    )
    .values(
        status="signed",
        signed_at=func.now(),
        signed_by_patient_id=patient_id,
        signature_hash=signature_hash,
        signature_url=s3_url,
        signed_full_name=data.full_name_confirmation,
        signed_from_ip=client_ip,
        signed_user_agent=user_agent[:200],
        document_hash_at_signing=data.document_hash,
    )
    .returning(ConsentForm.consent_type)
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:documents:*`: INVALIDATE — documents list (signed consent now appears)

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| documents | generate_signed_consent_pdf | { tenant_id, consent_id, patient_id, signature_url, signed_at } | After successful DB update |
| notifications | consent_signed_by_patient | { tenant_id, consent_id, patient_id } | After successful DB update |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** patient_sign
- **Resource:** consent_form
- **PHI involved:** Yes (consent form content + patient biometric signature)

**Additional audit fields:**
- `signature_hash`: SHA-256 of signature PNG
- `document_hash_at_signing`: SHA-256 of consent document content
- `client_ip`: full IP address (not masked in audit log)
- `user_agent`: browser/device info
- `full_name_as_signed`: text typed by patient

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | consent_signed_patient | clinic staff (doctor assigned) | On successful signing |
| email | consent_signed_staff | doctor + receptionist | On successful signing |

---

## Performance

### Expected Response Time
- **Target:** < 500ms (S3 upload + DB update; parallel where possible)
- **Maximum acceptable:** < 2000ms (PDF generation is async)

### Caching Strategy
- **Strategy:** No caching on write; cache invalidation
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Patient documents list invalidated

### Database Performance

**Queries executed:** 2 (consent fetch + update in transaction)

**Indexes required:**
- `consent_forms.(id, patient_id)` — COMPOSITE INDEX (ownership check)
- `consent_forms.(patient_id, status)` — COMPOSITE INDEX (status filter for pending consent list)

**N+1 prevention:** Not applicable (single update).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| consent_id | UUID v4 validation (path param) | Ownership verified via DB query |
| signature_data | Base64 decode + PNG magic byte check + size check | Never stored raw in DB; only S3 URL and hash |
| agreed_to_document | Pydantic StrictBool (must be exactly true) | Hard requirement |
| full_name_confirmation | Pydantic strip + strip_tags; max 200 chars | Legal record; stored verbatim after sanitization |
| document_hash | SHA-256 hex string validation (64 chars, [0-9a-f]) | Used for tamper detection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs escaped by Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** consent form content (clinical procedures), patient signature (biometric PII), full_name_confirmation, client IP

**Audit requirement:** Full audit trail with all metadata required for legal validity (Ley 527/1999 + Resolución 1888).

---

## Testing

### Test Cases

#### Happy Path
1. Patient signs pending consent form
   - **Given:** Consent form in 'pending_signature' status, patient_id matches JWT
   - **When:** POST /api/v1/portal/consents/{id}/sign with valid signature + correct document_hash
   - **Then:** 200 OK, status='signed' in DB, PDF generation job dispatched, notifications sent

2. Patient signs from mobile device
   - **Given:** Valid pending consent
   - **When:** POST with mobile User-Agent
   - **Then:** 200 OK, device_info recorded, IP from X-Forwarded-For

3. Document URL in response
   - **Given:** PDF generation job pre-seeded in S3 mock
   - **When:** POST sign
   - **Then:** document_url populated with pre-signed S3 URL (60-min expiry)

#### Edge Cases
1. Document updated while patient was reading (hash mismatch)
   - **Given:** Consent document_content updated by clinic; patient sends old document_hash
   - **When:** POST sign with outdated hash
   - **Then:** 422 document_changed

2. Concurrent signing attempts
   - **Given:** Two simultaneous sign requests for same consent
   - **When:** Both POST simultaneously
   - **Then:** One succeeds (200), second returns 409 (DB row lock on UPDATE)

#### Error Cases
1. Consent already signed
   - **Given:** consent_forms.status='signed'
   - **When:** POST sign
   - **Then:** 409 already_signed with signed_at in details

2. agreed_to_document=false
   - **Given:** Valid consent, valid signature
   - **When:** POST with agreed_to_document=false
   - **Then:** 400 Bad Request before any processing

3. Revoked consent
   - **Given:** consent_forms.status='revoked'
   - **When:** POST sign
   - **Then:** 410 Gone

4. Signature file too large
   - **Given:** PNG decodes to 600KB
   - **When:** POST sign
   - **Then:** 413 Payload Too Large

5. Consent belongs to different patient
   - **Given:** consent_id exists but patient_id mismatch
   - **When:** POST from current patient's JWT
   - **Then:** 404 consent_not_found

### Test Data Requirements

**Users:** Patient with portal_access=true; consent forms in pending_signature, signed, revoked statuses.

**Patients/Entities:** Valid base64 PNG fixture; SHA-256 of consent document content pre-computed; S3 mock; RabbitMQ mock.

### Mocking Strategy

- S3: moto library for upload and pre-signed URL testing
- RabbitMQ: Mock publish; assert both PDF generation and notification jobs dispatched
- SHA-256: real computation (deterministic); test hash mismatch scenario

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient can sign pending consent form with valid PNG signature
- [ ] Status updated to 'signed' with all metadata in DB (IP, hash, device, name, document_hash)
- [ ] Signature PNG stored to S3 at correct path
- [ ] SHA-256 hash of signature PNG computed and stored
- [ ] document_hash verified against server-computed hash; mismatch returns 422
- [ ] Signature is immutable — re-submission returns 409
- [ ] Revoked consent returns 410 Gone
- [ ] agreed_to_document=false returns 400 before processing
- [ ] PDF generation job dispatched asynchronously
- [ ] Staff notifications dispatched via RabbitMQ
- [ ] Patient documents cache invalidated
- [ ] Audit log written with full legal metadata
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating consent forms (consents domain — IC-01 through IC-09)
- Viewing consent document content (separate GET endpoint)
- Guardian/witness signatures for minors (clinic-side flow — IC-07)
- Revoking a patient signature (clinic_owner admin function)
- Bulk consent signing
- Consent form templates management

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
- [x] Input sanitization defined (PNG validation, strict bool, document hash)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Full legal audit trail (Ley 527/1999 + Resolución 1888)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized
- [x] Pagination N/A

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (full metadata)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (moto, fakeredis, RabbitMQ)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
