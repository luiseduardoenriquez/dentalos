# Consent Sign Spec

---

## Overview

**Feature:** Sign an informed consent form with a digital signature. Supports patient, doctor, and optional witness signatures. Once all required signatures are collected, the consent transitions to `signed` status, becomes permanently immutable, and the final PDF is generated. Complies with Colombia Ley 527/1999 on digital signatures.

**Domain:** consents

**Priority:** High

**Dependencies:** IC-04 (consent-create.md), IC-06 (consent-get.md), IC-08 (consent-pdf.md), auth/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:**
  - Doctor signature: doctor, clinic_owner
  - Patient signature: patient (from portal or in-clinic tablet session), doctor, clinic_owner (when signing on patient's behalf in-clinic with patient physically present)
  - Witness signature: doctor, clinic_owner, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:**
  - Patient can only sign their own consents
  - In-clinic patient signing uses a temporary in-clinic session token; patient portal signing uses the patient's own JWT
  - A user cannot sign both as `doctor` and as `witness` on the same consent

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/consents/{consent_id}/sign
```

**Rate Limiting:**
- 10 requests per minute per user
- Prevents signature replay attacks

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
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient owning the consent | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| consent_id | Yes | string (UUID) | Valid UUID v4, must belong to patient | Consent to be signed | c3d4e5f6-0000-4000-8000-000000000030 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "signer_type": "string (required) — enum: patient, doctor, witness",
  "signature": "string (required) — base64-encoded PNG image of the signature; max 500KB decoded",
  "signer_name": "string (required) — full name of the signer; max 200 chars",
  "signer_document": "string (required) — cedula/document number of the signer; max 30 chars"
}
```

**Example Request (doctor signing):**
```json
{
  "signer_type": "doctor",
  "signature": "iVBORw0KGgoAAAANSUhEUgAA...",
  "signer_name": "Juan Carlos Perez Rodriguez",
  "signer_document": "79512345"
}
```

**Example Request (patient signing):**
```json
{
  "signer_type": "patient",
  "signature": "iVBORw0KGgoAAAANSUhEUgAA...",
  "signer_name": "Maria Garcia Lopez",
  "signer_document": "1020304050"
}
```

---

## Response

### Success Response (signature added, not yet complete)

**Status:** 200 OK

**Schema:**
```json
{
  "consent_id": "uuid",
  "status": "string (draft | pending_signatures)",
  "signatures": [
    {
      "id": "uuid",
      "signer_type": "string (patient | doctor | witness)",
      "signer_name": "string",
      "signer_document": "string",
      "signed_at": "string (ISO 8601 datetime)",
      "ip_address": "string",
      "user_agent": "string"
    }
  ],
  "pending_signatures": "string[] — list of signer_types still required",
  "pdf_url": "null"
}
```

### Success Response (all signatures collected — consent finalized)

**Status:** 200 OK

```json
{
  "consent_id": "uuid",
  "status": "signed",
  "signatures": [
    {
      "id": "uuid",
      "signer_type": "doctor",
      "signer_name": "Juan Carlos Perez Rodriguez",
      "signer_document": "79512345",
      "signed_at": "2026-02-24T14:30:00Z",
      "ip_address": "190.25.1.45",
      "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0)"
    },
    {
      "id": "uuid",
      "signer_type": "patient",
      "signer_name": "Maria Garcia Lopez",
      "signer_document": "1020304050",
      "signed_at": "2026-02-24T14:32:00Z",
      "ip_address": "190.25.1.45",
      "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0)"
    }
  ],
  "pending_signatures": [],
  "pdf_url": "/api/v1/patients/f47ac10b/consents/c3d4e5f6/pdf"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON, base64 signature data is invalid, or decoded image exceeds 500KB.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Los datos de firma no son validos o exceden el tamano maximo permitido (500KB).",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User not authorized for the specified `signer_type`, or patient attempting to sign another patient's consent.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para firmar este consentimiento como 'doctor'."
}
```

#### 404 Not Found
**When:** `patient_id` or `consent_id` not found in tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Consentimiento no encontrado."
}
```

#### 409 Conflict
**When:** The same `signer_type` has already signed this consent, OR the consent is not in a signable status (`signed` or `voided`).

**Example:**
```json
{
  "error": "already_signed",
  "message": "Este consentimiento ya fue firmado por el 'doctor'."
}
```

**Example (consent already finalized):**
```json
{
  "error": "consent_immutable",
  "message": "Este consentimiento ya fue firmado por todas las partes y no puede modificarse."
}
```

#### 422 Unprocessable Entity
**When:** `signer_type` invalid enum value, signature image not decodable, or `signer_name` empty.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "signer_type": ["Tipo de firmante no valido. Opciones: patient, doctor, witness."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected failure during signature storage or PDF generation trigger.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Verify `patient_id` exists and belongs to the tenant.
4. Verify `consent_id` exists and belongs to `patient_id`.
5. Check consent status — if `signed` or `voided`, return 409 (`consent_immutable`).
6. Validate authorization for the requested `signer_type`:
   - `doctor`: must have role `doctor` or `clinic_owner`
   - `patient`: must be the patient themselves (JWT sub matches patient's portal user ID), or a doctor/clinic_owner signing physically on behalf of present patient (requires `in_clinic_signing=true` in JWT context or header flag)
   - `witness`: must have role `doctor`, `clinic_owner`, or `assistant`
7. Verify the same `signer_type` has not already signed this consent. Return 409 if duplicate.
8. Verify a user is not signing as both `doctor` and `witness` on this consent.
9. Decode and validate base64 signature:
   - Must be valid base64
   - Decoded bytes must form a valid PNG image (validate magic bytes)
   - Decoded size must be <= 500KB
10. Store signature image in object storage (S3-compatible); obtain `signature_url`.
11. Create `digital_signatures` record with: `consent_id`, `signer_type`, `signer_name`, `signer_document`, `signature_url`, `signed_at` (server UTC timestamp), `ip_address` (from request), `user_agent` (from request headers), `user_id` (JWT sub).
12. Update consent `status`:
    - After any first signature: `draft` → `pending_signatures`
    - After all required signatures collected: `pending_signatures` → `signed`
13. If `status` becomes `signed`:
    - Freeze consent: set `locked_at = now()`, `content_hash = SHA256(content_rendered)` for tamper detection
    - Dispatch `consent.generate_pdf` job to RabbitMQ
14. Write audit log entry.
15. Invalidate patient consent list and detail caches.
16. Return 200 with updated consent signature state.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| signer_type | Must be one of: patient, doctor, witness | Tipo de firmante no valido. |
| signature | Must be valid base64 string | Los datos de firma deben estar codificados en base64. |
| signature | Decoded PNG <= 500KB | La imagen de firma excede el tamano maximo de 500KB. |
| signature | Decoded bytes must be valid PNG (PNG magic header: 89 50 4E 47) | El archivo de firma no es una imagen PNG valida. |
| signer_name | Required, 2–200 chars | El nombre del firmante es obligatorio. |
| signer_document | Required, 5–30 chars, alphanumeric + hyphens | El documento del firmante es obligatorio. |

**Business Rules:**

- Consent immutability: once `status = signed`, no further signatures can be added and no field can be modified. This is a legal requirement under Colombian law.
- Required signatures are defined by the template's `signature_positions` (patient.required, doctor.required). The witness signature is only required if `witness.required = true` in the template.
- The `content_hash` (SHA256) is stored at signing time to enable future tamper verification.
- The IP address and user agent are captured from the HTTP request — they are legal traceability data (Ley 527/1999).
- `signed_at` is always server-side UTC time — never accepted from the client.
- Signature images are stored in object storage, not in the database (only the URL is stored).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Witness signature submitted when `witness.required = false` | Accept as optional; include in signatures array; does not block finalization |
| Only patient signs and template requires both patient and doctor | Status remains `pending_signatures`; no PDF generated yet |
| Patient portal signing from remote (different IP from clinic) | Accepted; IP + user_agent recorded from patient's actual device |
| Doctor role signs as `patient` signer_type (in-clinic physical signing) | Allowed if in-clinic session context is present; recorded with signer_type = patient |
| Base64 string is valid but decodes to JPEG, not PNG | Reject 422 — only PNG accepted |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `digital_signatures`: INSERT — new signature record for this consent
- `consents`: UPDATE — update `status`, and if fully signed: set `locked_at`, `content_hash`

**Example query (SQLAlchemy):**
```python
sig = DigitalSignature(
    consent_id=consent_id,
    signer_type=data.signer_type,
    signer_name=data.signer_name,
    signer_document=data.signer_document,
    signature_url=stored_signature_url,
    ip_address=request.client.host,
    user_agent=request.headers.get("User-Agent", ""),
    user_id=current_user.id,
    signed_at=datetime.utcnow(),
)
session.add(sig)
await session.flush()

# Update consent status
await session.execute(
    update(Consent)
    .where(Consent.id == consent_id)
    .values(status=new_status, locked_at=locked_at, content_hash=content_hash)
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:{patient_id}:consents:list:*`: INVALIDATE
- `tenant:{tenant_id}:patients:{patient_id}:consents:{consent_id}`: INVALIDATE

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| consents | consent.generate_pdf | { tenant_id, consent_id, patient_id } | When all required signatures collected (status → signed) |
| audit | audit.log | { action, resource_id, signer_type, ip, user_agent } | On every sign event |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** sign
- **Resource:** consent
- **PHI involved:** Yes (patient name, document number, signature image URL)

### Notifications

**Notifications triggered:** Yes — when consent reaches `signed` status

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | consent_signed_confirmation | Patient (if email on file) | consent.status == signed |
| in-app | consent_signed | Doctor/clinic | consent.status == signed |

---

## Performance

### Expected Response Time
- **Target:** < 400ms
- **Maximum acceptable:** < 800ms (includes S3 upload for signature image)

### Caching Strategy
- **Strategy:** No caching on write (invalidation only)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Consent list and detail caches invalidated on every sign event

### Database Performance

**Queries executed:** 4–5 (consent lookup, existing signature check, signature INSERT, consent status UPDATE, optional: fetch all signatures to check completeness)

**Indexes required:**
- `{tenant}.digital_signatures.consent_id` — INDEX
- `{tenant}.digital_signatures.(consent_id, signer_type)` — UNIQUE INDEX (prevents duplicate signer_type per consent)
- `{tenant}.consents.status` — INDEX
- `{tenant}.consents.(patient_id, id)` — INDEX

**N+1 prevention:** All signature records for completeness check fetched in a single query.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| signer_type | Pydantic enum validator | Strictly constrained to allowed values |
| signature | Base64 decode + PNG magic byte validation | Prevents non-image payloads |
| signer_name | Pydantic `strip()` + strip_tags | Prevent XSS in legal document fields |
| signer_document | Pydantic: alphanumeric + hyphens, max 30 chars | Prevent injection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Pydantic serialization escapes all string fields on output.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** signer_name, signer_document, signature image (biometric-equivalent data), ip_address (traceability)

**Audit requirement:** All access logged (every sign event individually audited as legal record).

---

## Testing

### Test Cases

#### Happy Path
1. Doctor signs first, then patient signs (complete consent)
   - **Given:** Draft consent requiring patient + doctor signatures
   - **When:** Doctor signs (POST with signer_type=doctor), then patient signs (POST with signer_type=patient)
   - **Then:** After doctor signs: status = pending_signatures; after patient signs: status = signed, pdf_url returned, PDF generation job dispatched

2. Single signature from doctor on a doctor-only template
   - **Given:** Template requires only doctor signature
   - **When:** Doctor signs
   - **Then:** Status immediately becomes `signed`, PDF generation triggered

3. Patient signing from patient portal (remote)
   - **Given:** Patient has portal access, consent in pending_signatures
   - **When:** Patient signs via portal JWT
   - **Then:** 200 OK, signature recorded with patient's IP and user agent

4. Optional witness signature
   - **Given:** Template has `witness.required = false`, consent is signed by patient + doctor
   - **When:** Witness signs (optional)
   - **Then:** 200 OK, witness signature recorded, status remains `signed`

#### Edge Cases
1. Witness signature submitted before finalization on non-required witness template
   - **Given:** Consent in pending_signatures, template witness.required=false
   - **When:** Witness signs
   - **Then:** 200 OK, signature recorded; completeness still determined by patient + doctor only

#### Error Cases
1. Attempt to sign an already-signed consent
   - **Given:** Consent is in `signed` status
   - **When:** POST sign with any signer_type
   - **Then:** 409 Conflict with `consent_immutable` error

2. Same signer_type signs twice
   - **Given:** Doctor has already signed the consent
   - **When:** Another (or same) doctor attempts to sign with signer_type=doctor
   - **Then:** 409 Conflict with `already_signed` error

3. Invalid base64 signature
   - **Given:** `signature` field contains non-base64 string
   - **When:** POST sign
   - **Then:** 422 Unprocessable Entity

4. Signature decodes to JPEG instead of PNG
   - **Given:** Valid base64 but image is JPEG format
   - **When:** POST sign
   - **Then:** 422 — only PNG accepted

5. Patient attempting to sign another patient's consent
   - **Given:** Patient A's JWT, consent belonging to Patient B
   - **When:** POST /api/v1/patients/{patient_b_id}/consents/{consent_id}/sign
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** doctor, clinic_owner, assistant, patient (portal access enabled)

**Patients/Entities:** Draft consent; consent in pending_signatures; signed consent (for immutability test); consent with different required signature configs.

### Mocking Strategy

- S3 / object storage: Mock upload; return predictable URL
- RabbitMQ: Mock publish; assert `consent.generate_pdf` payload dispatched when status becomes signed
- IP address extraction: Inject mock request object with controlled `client.host`
- Redis cache: Use fakeredis to verify cache invalidation

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Doctor + patient signatures collected transitions consent to `signed` status
- [ ] `content_hash` (SHA256) stored when consent is finalized
- [ ] `locked_at` timestamp set when consent is signed
- [ ] Signed consent rejects any further modification (409 immutable)
- [ ] Duplicate `signer_type` returns 409
- [ ] Invalid PNG or non-base64 data returns 422
- [ ] Patient cannot sign another patient's consent (403)
- [ ] IP address and user agent recorded for every signature
- [ ] `consent.generate_pdf` RabbitMQ job dispatched when fully signed
- [ ] Audit log entry written for every signature event
- [ ] Patient email notification sent on final signing
- [ ] All test cases pass
- [ ] Performance target met (< 400ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- PDF generation (triggered asynchronously via RabbitMQ job — see IC-08)
- Sending consent link to patient for remote signing (separate notification workflow)
- Voiding a signed consent (see IC-09)
- Signature image rendering in PDF (handled by PDF generation service)
- Biometric signature verification (beyond PNG image storage)

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
- [x] Input sanitization defined (Pydantic + PNG validation)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation on write)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

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
| 1.0 | 2026-02-24 | Initial spec |
