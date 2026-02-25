# DS-01 — Digital Signature Spec

## Overview

**Feature:** Create and verify legally-valid digital signatures under Colombia Ley 527/1999. Captures a handwritten signature from a canvas element (base64 PNG), generates a SHA-256 integrity hash of the signature data + document identity + timestamp, and stores the hash with full audit metadata. Provides a verification endpoint that recomputes the hash and confirms whether the signature is intact or has been tampered with. Used by consents (IC-05), treatment plans (TP-08), prescriptions (RX-01), and sterilization records (INV-05).

**Domain:** signatures (cross-cutting service)

**Priority:** High (Sprint 7-8 — needed before consents and treatment plans go live)

**Dependencies:** infra/audit-logging.md, infra/security.md, patients/P-01, users/U-01

---

## Authentication

- **Level:** Authenticated
- **Roles allowed (POST):** doctor, clinic_owner, assistant, receptionist, patient (all roles may sign documents assigned to them)
- **Roles allowed (GET verify):** clinic_owner, doctor, assistant, receptionist (read-only verification); superadmin
- **Tenant context:** Required — resolved from JWT
- **Special rules:**
  - A `signer_type=doctor` signature may only be created by a user with role=doctor or clinic_owner.
  - A `signer_type=patient` signature can be created by any staff role acting on behalf of the patient (for in-clinic tablet capture) or by the patient themselves via portal.
  - Signatures are immutable after creation — no update or delete.
  - `patient` role may only sign documents where `signer_id` matches their own patient_id.

---

## Endpoints

```
POST /api/v1/signatures
GET  /api/v1/signatures/{signature_id}/verify
```

**Rate Limiting:**
- POST: 30 requests per minute per user (signatures per session)
- GET: 60 requests per minute per user

---

## Request — POST /api/v1/signatures

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
  "signer_type": "string (required) — doctor | patient",
  "signer_id": "string (UUID, required) — UUID of the signer; doctor's user_id OR patient's patient_id",
  "document_type": "string (required) — consent | treatment_plan | prescription | sterilization",
  "document_id": "string (UUID, required) — UUID of the document being signed",
  "signature_data": "string (required) — base64-encoded PNG image of the handwritten signature from canvas (max 500KB decoded)",
  "canvas_metadata": {
    "width": "integer (required) — canvas width in pixels",
    "height": "integer (required) — canvas height in pixels",
    "device_type": "string (optional) — tablet | desktop | mobile",
    "input_method": "string (optional) — stylus | finger | mouse"
  },
  "consent_statement": "string (optional, max 1000) — the consent text that was displayed to the signer at time of signing (captured for legal record)",
  "location_context": "string (optional, max 200) — where the signing occurred, e.g. 'Consultorio 1, piso 3'"
}
```

**Example Request:**
```json
{
  "signer_type": "patient",
  "signer_id": "pat_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "document_type": "consent",
  "document_id": "consent_f1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "signature_data": "iVBORw0KGgoAAAANSUhEUgAA...(base64 PNG truncated)...AASUVORK5CYII=",
  "canvas_metadata": {
    "width": 600,
    "height": 200,
    "device_type": "tablet",
    "input_method": "stylus"
  },
  "consent_statement": "Yo, María García, autorizo a la Clínica Dental Torres a realizar los procedimientos indicados en el plan de tratamiento, habiendo comprendido los riesgos y beneficios explicados por la Dra. Torres.",
  "location_context": "Consultorio 1"
}
```

---

## Response — POST /api/v1/signatures

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "signature_id": "string (UUID) — unique identifier of the signature record",
  "hash": "string — SHA-256 hex digest of the canonical signing payload",
  "hash_algorithm": "string — SHA-256",
  "canonical_payload_preview": "string — preview of what was hashed (not the full payload, for debugging only)",
  "document_type": "string",
  "document_id": "string (UUID)",
  "signer_type": "string",
  "signer_id": "string (UUID)",
  "signer_name": "string — resolved full name of signer",
  "signed_at": "string (ISO 8601) — UTC timestamp embedded in the hash",
  "ip_address": "string — captured from request (auto)",
  "user_agent_hash": "string — SHA-256 of User-Agent (not raw UA for privacy)",
  "tenant_id": "string",
  "verification_url": "string — URL to verify this signature",
  "legal_framework": "string — Colombia Ley 527 de 1999",
  "storage_url": "string | null — URL to download the signed image (pre-signed, 24h)",
  "integrity_notice": "string — notice about immutability"
}
```

**Example:**
```json
{
  "signature_id": "sig_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "hash": "a4f8b2c1d3e5f7890abcdef1234567890abcdef1234567890abcdef1234567891234567890abcdef12",
  "hash_algorithm": "SHA-256",
  "canonical_payload_preview": "sig_a1b2c3d4|consent|consent_f1a2b3|pat_a1b2c3|2026-02-25T10:00:00.000000Z|a4f8b2...(signature_data hash)",
  "document_type": "consent",
  "document_id": "consent_f1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "signer_type": "patient",
  "signer_id": "pat_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "signer_name": "María García",
  "signed_at": "2026-02-25T10:00:00.000000Z",
  "ip_address": "203.0.113.42",
  "user_agent_hash": "8f14e45fceea167a5a36dedd4bea2543",
  "tenant_id": "tn_abc123",
  "verification_url": "/api/v1/signatures/sig_a1b2c3d4-e5f6-7890-abcd-ef1234567890/verify",
  "legal_framework": "Colombia Ley 527 de 1999",
  "storage_url": "https://storage.dentalos.io/signatures/tn_abc123/sig_a1b2c3d4/signature.png?token=xyz&expires=...",
  "integrity_notice": "This signature is immutable. Any modification to the underlying document or signature image will invalidate the hash and be detected during verification."
}
```

---

## Request — GET /api/v1/signatures/{signature_id}/verify

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| signature_id | Yes | string (UUID) | Valid UUID v4 | Signature to verify | sig_a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

None.

---

## Response — GET /api/v1/signatures/{signature_id}/verify

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "signature_id": "string (UUID)",
  "verification_result": "string — valid | tampered | missing",
  "is_valid": "boolean",
  "verified_at": "string (ISO 8601) — when this verification was performed",
  "stored_hash": "string — hash stored at signing time",
  "recomputed_hash": "string — hash recomputed now from stored data",
  "hashes_match": "boolean",
  "signature_details": {
    "document_type": "string",
    "document_id": "string (UUID)",
    "signer_type": "string",
    "signer_id": "string (UUID)",
    "signer_name": "string",
    "signed_at": "string (ISO 8601)",
    "tenant_id": "string",
    "ip_address": "string",
    "canvas_metadata": "object",
    "legal_framework": "string"
  },
  "tamper_details": "object | null — populated if is_valid=false",
  "verification_certificate": {
    "certificate_id": "string — UUID of this verification record",
    "verified_by_user_id": "string",
    "verified_by_name": "string",
    "verified_at": "string (ISO 8601)",
    "platform_version": "string — DentalOS version at verification time"
  }
}
```

**tamper_details schema (when is_valid=false):**
```json
{
  "mismatch_detected": "boolean",
  "stored_hash": "string",
  "recomputed_hash": "string",
  "possible_cause": "string — signature_image_modified | document_record_modified | storage_corruption",
  "tamper_detected_at": "string (ISO 8601)",
  "recommended_action": "string"
}
```

**Example (valid):**
```json
{
  "signature_id": "sig_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "verification_result": "valid",
  "is_valid": true,
  "verified_at": "2026-03-01T14:00:00Z",
  "stored_hash": "a4f8b2c1d3e5f7890abcdef1234567890abcdef1234567890abcdef1234567891234567890abcdef12",
  "recomputed_hash": "a4f8b2c1d3e5f7890abcdef1234567890abcdef1234567890abcdef1234567891234567890abcdef12",
  "hashes_match": true,
  "signature_details": {
    "document_type": "consent",
    "document_id": "consent_f1a2b3c4-d5e6-7890-abcd-ef1234567890",
    "signer_type": "patient",
    "signer_id": "pat_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "signer_name": "María García",
    "signed_at": "2026-02-25T10:00:00.000000Z",
    "tenant_id": "tn_abc123",
    "ip_address": "203.0.113.42",
    "canvas_metadata": { "width": 600, "height": 200, "device_type": "tablet", "input_method": "stylus" },
    "legal_framework": "Colombia Ley 527 de 1999"
  },
  "tamper_details": null,
  "verification_certificate": {
    "certificate_id": "vc_xyz789",
    "verified_by_user_id": "user_doctor123",
    "verified_by_name": "Dra. María Torres",
    "verified_at": "2026-03-01T14:00:00Z",
    "platform_version": "1.0.0"
  }
}
```

### Error Responses (both endpoints)

#### 400 Bad Request
**When (POST):** `signature_data` exceeds 500KB decoded; `signer_type` is invalid; `document_type` is invalid; base64 is malformed or does not decode to a valid PNG image.

**Example:**
```json
{
  "error": "invalid_signature_data",
  "message": "Signature data validation failed",
  "details": {
    "signature_data": ["Decoded image exceeds maximum size of 500KB", "signature_data must be a valid base64-encoded PNG image"]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When (POST signer_type=doctor):** Caller is not a doctor or clinic_owner. When `signer_type=patient`: caller is patient but `signer_id` does not match their own patient_id.

**Example:**
```json
{
  "error": "signer_permission_denied",
  "message": "You do not have permission to sign on behalf of this signer",
  "details": {
    "signer_type": "doctor",
    "required_roles": ["doctor", "clinic_owner"]
  }
}
```

#### 404 Not Found
**When:** `document_id` does not exist in the tenant's context (for POST); `signature_id` not found (for GET verify).

**Example:**
```json
{
  "error": "document_not_found",
  "message": "The referenced document does not exist",
  "details": { "document_type": "consent", "document_id": "consent_f1a2b3c4" }
}
```

#### 409 Conflict
**When (POST):** Document already has a signature of this signer_type (e.g., a consent already signed by the patient; a treatment plan already signed by the doctor). Use force update only if the existing signature was from a test/draft context.

**Example:**
```json
{
  "error": "document_already_signed",
  "message": "This document already has a patient signature",
  "details": {
    "existing_signature_id": "sig_prev123",
    "signed_at": "2026-02-20T09:00:00Z",
    "signer_name": "María García"
  }
}
```

#### 422 Unprocessable Entity
**When:** Pydantic validation fails on body or path params.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

---

## Business Logic

**POST — Step-by-step process:**

1. Validate request body via Pydantic schema `DigitalSignatureCreateRequest`.
2. Resolve tenant_id from JWT.
3. Verify caller permissions based on `signer_type`:
   - `signer_type=doctor`: caller must have role=doctor or clinic_owner.
   - `signer_type=patient`: caller may be any staff role (signing on behalf of patient on clinic tablet) OR must be patient role with `signer_id == own patient_id`.
4. Verify `document_id` exists in the tenant schema for the given `document_type`:
   - consent → query `informed_consents` table
   - treatment_plan → query `treatment_plans` table
   - prescription → query `prescriptions` table
   - sterilization → query `sterilization_records` table
   Return 404 if not found.
5. Check for existing signature: query `digital_signatures` WHERE `document_type=X AND document_id=Y AND signer_type=Z AND tenant_id=T AND is_active=true`. If found, return 409.
6. Validate `signature_data`:
   - Decode base64; verify it is a valid PNG header (`\x89PNG\r\n\x1a\n`).
   - Check decoded size <= 500KB.
   - Reject transparent/blank images (entropy check: if image has < 5% non-white pixels, reject as likely blank).
7. Capture `ip_address` from request (from `X-Forwarded-For` or connection IP — auto, not from client body).
8. Capture `user_agent` from `User-Agent` header; SHA-256 hash it before storage (privacy — raw UA not stored).
9. Generate `signed_at` = `datetime.utcnow()` with microsecond precision (ISO 8601 format with 6 decimal places).
10. Compute `signature_id` = new UUID v4.
11. Compute canonical signing payload for hash:
    ```
    canonical = f"{signature_id}|{document_type}|{document_id}|{signer_id}|{signed_at}|{sha256(signature_data_bytes)}"
    ```
    - The signature_data is included as its own SHA-256 hash within the canonical payload (so the full image is not re-hashed on every verification; only the image hash is embedded).
12. Compute final hash: `signature_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()`.
13. Store signature image to object storage: `signatures/{tenant_id}/{signature_id}/signature.png`.
14. INSERT `digital_signatures` record:
    - `id`, `tenant_id`, `document_type`, `document_id`, `signer_type`, `signer_id`, `signed_at`, `ip_address`, `user_agent_hash`, `canonical_payload`, `signature_hash`, `image_storage_path`, `canvas_metadata`, `consent_statement`, `location_context`, `signed_by_user_id` (JWT sub), `is_active=true`
15. Link to document: UPDATE the referenced document's table to set `has_signature=true`, `signature_id=sig_id` (for consent/treatment_plan).
16. Write audit log: action=`signature_created`, resource=`digital_signature`, resource_id=`signature_id`, PHI=true.
17. Generate pre-signed URL for signature image (TTL 24h).
18. Return 201.

**GET /verify — Step-by-step process:**

1. Validate `signature_id` as UUID.
2. Resolve tenant_id from JWT; verify caller has authorized role.
3. Fetch signature record from `digital_signatures` WHERE `id = signature_id AND tenant_id = tenant_id`. Return 404 if not found.
4. Recompute canonical payload from stored data (same formula as at signing time):
   ```
   canonical = f"{signature_id}|{document_type}|{document_id}|{signer_id}|{signed_at}|{sha256(image_bytes)}"
   ```
   - Read signature image bytes from object storage to recompute image hash.
5. Compute `recomputed_hash = sha256(canonical)`.
6. Compare `recomputed_hash == stored signature_hash`:
   - Match: `is_valid=true`, `verification_result="valid"`.
   - Mismatch: `is_valid=false`, `verification_result="tampered"`.
7. If image not found in storage: `is_valid=false`, `verification_result="missing"`.
8. Create `signature_verifications` record: `id`, `signature_id`, `verified_by`, `verified_at`, `is_valid`, `recomputed_hash`.
9. Write audit log: action=`signature_verified`, resource=`digital_signature`, resource_id=`signature_id`.
10. Return 200.

**Canonical Payload Format:**
```
{signature_id}|{document_type}|{document_id}|{signer_id}|{signed_at_microseconds_utc}|{sha256_hex_of_image_bytes}
```

Example:
```
sig_a1b2c3d4-e5f6-7890-abcd-ef1234567890|consent|consent_f1a2b3c4-d5e6-7890-abcd-ef1234567890|pat_a1b2c3d4-e5f6-7890-abcd-ef1234567890|2026-02-25T10:00:00.123456Z|a4f8b2c1d3e5f7890abcdef12...
```

**Legal Framework — Colombia Ley 527/1999:**
- Article 7: Electronic signatures have legal validity equivalent to handwritten signatures when they meet integrity, authenticity, and non-repudiation requirements.
- Article 8: Electronic signatures are reliable if the method used is appropriate for the purpose of communication.
- SHA-256 hash + timestamp + IP address + device metadata satisfies the "uniqueness and authenticity" requirements.
- The stored image provides the "visual representation" element.
- The audit trail provides "non-repudiation".

**Blank Signature Detection:**
```python
from PIL import Image
import io
import base64

def is_blank_signature(b64_data: str) -> bool:
    img_bytes = base64.b64decode(b64_data)
    img = Image.open(io.BytesIO(img_bytes)).convert("L")  # grayscale
    pixels = list(img.getdata())
    non_white = sum(1 for p in pixels if p < 240)
    return non_white / len(pixels) < 0.05  # less than 5% ink
```

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| signer_type | doctor or patient | "signer_type must be doctor or patient" |
| signer_id | Valid UUID | "signer_id must be a valid UUID" |
| document_type | consent, treatment_plan, prescription, sterilization | "document_type not recognized" |
| document_id | Valid UUID | "document_id must be a valid UUID" |
| signature_data | Valid base64; decodes to PNG; < 500KB decoded; not blank | "signature_data must be a valid non-blank PNG image <= 500KB" |
| canvas_metadata.width | Integer > 0 | "canvas width must be positive" |
| canvas_metadata.height | Integer > 0 | "canvas height must be positive" |
| consent_statement | Max 1000 chars if provided | "consent_statement exceeds 1000 characters" |

**Business Rules:**

- Signatures are immutable — no endpoint to update or delete (only soft-flag: `is_active=false` via internal API for legal team only).
- One signature per (document_type, document_id, signer_type) combination. A consent can have one patient signature AND one doctor co-sign, but not two patient signatures.
- `ip_address` and `user_agent` are captured server-side from the HTTP request — not provided by the client in the body (prevents spoofing).
- `consent_statement` snapshot is captured at signing time because the document text may change after signing. The snapshot is the legally relevant version.
- Pre-signed storage URLs are valid for 24 hours (longer than the standard 1h since signatures may be retrieved for compliance audits).
- Verification results are stored as `signature_verifications` records — creating an immutable verification audit trail.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Blank signature submitted | 400 Bad Request, "signature_data appears to be blank" |
| Image too large (> 500KB decoded) | 400 Bad Request, size exceeded |
| Document already signed by patient; doctor tries to sign | Allowed — patient signature and doctor signature are different signer_types |
| Document signed, then document record is modified | Verification detects tamper (canonical hash includes document_id but not document content — spec note: canonical payload covers document identity, not document content; content integrity is a separate document-level concern) |
| Storage unavailable at signing time | Transaction rolled back; 500 returned; no partial signature records |
| Image bytes corrupted in storage at verify time | is_valid=false, verification_result=tampered, possible_cause=storage_corruption |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `digital_signatures`: INSERT — new signature record
- `informed_consents` / `treatment_plans` / `prescriptions` / `sterilization_records`: UPDATE `has_signature=true`, `signature_id`
- `signature_verifications`: INSERT — on GET /verify

**Example query (SQLAlchemy):**
```python
sig = DigitalSignature(
    id=signature_id,
    tenant_id=tenant_id,
    document_type=body.document_type,
    document_id=body.document_id,
    signer_type=body.signer_type,
    signer_id=body.signer_id,
    signed_at=signed_at,
    ip_address=client_ip,
    user_agent_hash=user_agent_hash,
    canonical_payload=canonical_payload,
    signature_hash=signature_hash,
    image_storage_path=storage_path,
    canvas_metadata=body.canvas_metadata.dict(),
    consent_statement=body.consent_statement,
    location_context=body.location_context,
    signed_by_user_id=current_user.id,
    is_active=True,
)
session.add(sig)
# Update referencing document
await session.execute(
    update(InformedConsent)
    .where(InformedConsent.id == body.document_id)
    .values(has_signature=True, signature_id=signature_id)
)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:consent:{document_id}`: INVALIDATE (has_signature updated)
- `tenant:{tenant_id}:treatment_plan:{document_id}`: INVALIDATE (has_signature updated)

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications.internal | signature_created | `{ signature_id, document_type, document_id, signer_type, signer_name, tenant_id }` | After successful INSERT |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action (POST):** create
- **Resource:** digital_signature
- **PHI involved:** Yes — signature image captures patient biometric (handwriting pattern); signer identity is PHI

- **Action (GET verify):** read
- **Resource:** digital_signature
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** Yes (post-creation)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | consent_signed | doctor, clinic_owner | Patient signs a consent |
| in-app | treatment_plan_signed | doctor | Patient signs a treatment plan |
| email | document_signed_confirmation | patient | Patient signs any document (confirmation copy) |

---

## Performance

### Expected Response Time
- **POST Target:** < 600ms (image validation + storage write + DB insert)
- **GET verify Target:** < 500ms (storage read for image hash + DB read + compare)

### Caching Strategy
- **Strategy:** No caching of signatures (immutable records fetched from DB)
- **Storage image:** Pre-signed URLs cached client-side; server re-generates on each request

### Database Performance

**POST Queries:** 4 (permission check, document existence, duplicate check, INSERT + UPDATE)

**GET Queries:** 2 (fetch signature record, INSERT verification record)

**Indexes required:**
- `digital_signatures.(id, tenant_id)` — COMPOSITE UNIQUE (primary lookup)
- `digital_signatures.(document_type, document_id, signer_type, tenant_id, is_active)` — COMPOSITE UNIQUE INDEX (duplicate prevention)
- `digital_signatures.(tenant_id, signed_at DESC)` — COMPOSITE INDEX for audit trail queries
- `digital_signatures.(signer_id, tenant_id)` — COMPOSITE INDEX for patient/doctor signature history
- `signature_verifications.(signature_id, verified_at DESC)` — COMPOSITE INDEX

**N+1 prevention:** All checks done in individual queries; no joins needed for core flow.

### Pagination

**Pagination:** No (single record operations)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| signer_id | UUID validation | Non-UUID rejected |
| document_id | UUID validation | Non-UUID rejected |
| signer_type | Pydantic Literal enum | Only doctor or patient |
| document_type | Pydantic Literal enum | Only known document types |
| signature_data | Base64 decode + PNG header check + size check + entropy check | Full image validation pipeline |
| consent_statement | Pydantic max_length=1000, strip whitespace | Plain text; no HTML |
| location_context | Pydantic max_length=200, strip | Plain text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:**
- `signature_data` (base64 PNG): biometric data (handwriting pattern) — stored encrypted at rest (AES-256 in object storage)
- `signer_id` referencing patient identity
- `ip_address`: logged but not returned in non-verify responses
- `consent_statement`: may contain personal health information
- `user_agent_hash`: SHA-256 hashed before storage (raw UA not stored)

**Audit requirement:** All signature operations logged. PHI access logged at field level.

**Data Retention:** Signatures retained for 10 years per `retention_rules.consents_years` (Colombia Ley 23/1981). Deletion only via explicit legal team request through a privileged internal API.

### Cryptographic Integrity

- **Hash algorithm:** SHA-256 (256-bit output; computationally infeasible to forge)
- **Canonical payload:** deterministic construction; any modification to any included field changes the hash
- **No private key required** for this implementation (HMAC-SHA256 or asymmetric signing may be added in a future version for stronger non-repudiation)
- **Timestamp precision:** microsecond-precision UTC to prevent collision attacks on the canonical payload

---

## Testing

### Test Cases

#### Happy Path
1. Patient signs a consent form
   - **Given:** doctor JWT, patient exists, consent exists and unsigned
   - **When:** POST /api/v1/signatures with signer_type=patient, document_type=consent, valid PNG base64
   - **Then:** 201 Created, signature_id returned, hash computed, storage_url set, consent.has_signature=true

2. Doctor signs a prescription
   - **Given:** doctor JWT, prescription exists
   - **When:** POST with signer_type=doctor, document_type=prescription
   - **Then:** 201 Created, doctor signature linked to prescription

3. Verify valid signature (no tampering)
   - **Given:** Existing valid signature, image intact in storage
   - **When:** GET /api/v1/signatures/{id}/verify
   - **Then:** 200 OK, is_valid=true, hashes_match=true, verification_certificate populated

4. Detect tampered signature (image modified in storage)
   - **Given:** Signature record with hash H; image file in storage replaced with different content
   - **When:** GET /verify
   - **Then:** 200 OK, is_valid=false, verification_result=tampered, recomputed_hash != stored_hash

#### Edge Cases
1. Patient signs consent via portal (patient role JWT)
   - **Given:** patient JWT with patient_id=pat_xyz, signer_id=pat_xyz
   - **When:** POST with signer_type=patient, signer_id=pat_xyz
   - **Then:** 201 Created (patient role can sign their own documents)

2. Staff signs consent on behalf of patient (in-clinic tablet)
   - **Given:** receptionist JWT, patient exists, consent exists
   - **When:** POST with signer_type=patient, signer_id=pat_xyz
   - **Then:** 201 Created (receptionist can capture patient signature on tablet)

3. Same document signed by patient AND doctor (both allowed)
   - **Given:** Consent with patient signature already recorded
   - **When:** POST with signer_type=doctor for same consent
   - **Then:** 201 Created (different signer_type, no conflict)

4. Duplicate patient signature on same consent
   - **Given:** Consent already has patient signature
   - **When:** POST patient signature for same consent again
   - **Then:** 409 Conflict, document_already_signed

#### Error Cases
1. Blank signature image
   - **Given:** Base64 encoding of all-white 600x200 PNG
   - **When:** POST signature
   - **Then:** 400 Bad Request, "signature_data appears to be blank"

2. Too-large image (> 500KB)
   - **Given:** Large base64 encoded image
   - **When:** POST signature
   - **Then:** 400 Bad Request, size exceeded

3. Doctor role tries to sign as signer_type=doctor but is actually a receptionist
   - **Given:** receptionist JWT
   - **When:** POST with signer_type=doctor
   - **Then:** 403 Forbidden, signer_permission_denied

4. Patient signs someone else's document (patient JWT, different signer_id)
   - **Given:** patient JWT with patient_id=pat_A, signer_id=pat_B
   - **When:** POST signature
   - **Then:** 403 Forbidden

5. Document not found
   - **Given:** Non-existent document_id
   - **When:** POST signature
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** doctor, receptionist, patient (for portal signing), clinic_owner

**Patients/Entities:** Patient with linked consent, prescription, treatment plan, sterilization record (each in unsigned state); valid base64 PNG fixture (~100KB); blank PNG fixture; large PNG fixture (> 500KB)

### Mocking Strategy

- Object storage: Mock `StorageService.write()` and `StorageService.read()` — in-memory for unit tests
- PIL image processing: Use real PIL in unit tests (fast enough; uses small test images)
- SHA-256: Use real hashlib (no mocking needed; deterministic)
- IP extraction: Mock request.client.host to return known IP in tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST creates signature record with SHA-256 hash of canonical payload
- [ ] Hash includes: signature_id, document_type, document_id, signer_id, signed_at (microseconds), sha256(image)
- [ ] Signature image stored in object storage
- [ ] Document record updated (has_signature=true, signature_id set)
- [ ] 409 for duplicate signature on same document + signer_type
- [ ] 403 for role violations (doctor signing as patient role; patient signing other patient's docs)
- [ ] Blank signature detection rejects empty canvases (< 5% non-white pixels)
- [ ] GET /verify recomputes hash from stored data; returns is_valid=true or is_valid=false
- [ ] Tampered signature detected (image modified in storage)
- [ ] Verification certificate created (signature_verifications record)
- [ ] ip_address auto-captured from request (not client-provided)
- [ ] user_agent SHA-256 hashed before storage
- [ ] consent_statement snapshot stored with signature
- [ ] Audit log entries for create and verify (PHI flagged)
- [ ] In-app notification on consent/treatment_plan signing
- [ ] All test cases pass
- [ ] Performance targets met (< 600ms POST, < 500ms verify)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- PKI/X.509 digital certificates for stronger non-repudiation (future v2 enhancement)
- HMAC-SHA256 with a server-side secret key (planned for v1.1)
- Electronic signatures for emails (separate system)
- Batch signing of multiple documents
- Signature revocation (legal process via privileged internal API; not end-user facing)
- Biometric signature analysis (handwriting verification AI — future add-on)
- Witness signatures (two-party signing flow — future feature for specific document types)
- QR code generation for in-document signature verification (document generation module)
- Multi-country signature legal frameworks (Mexico NOM-151, etc. — future adapters)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models — both POST and GET /verify)
- [x] API contract defined (OpenAPI compatible)
- [x] Canonical payload format documented precisely
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (signer_type permission rules)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (cross-cutting service)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models documented

### Hook 3: Security & Privacy
- [x] Auth level stated with detailed signer_type permission rules
- [x] Input sanitization defined (image validation pipeline)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] ip_address server-captured (not client-provided)
- [x] user_agent SHA-256 hashed (privacy)
- [x] Biometric data encryption at rest noted
- [x] Audit trail for all operations (PHI flagged)
- [x] Legal framework documented (Ley 527/1999)

### Hook 4: Performance & Scalability
- [x] Response time targets defined
- [x] Database indexes listed
- [x] Storage considerations documented

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries for create and verify
- [x] verification_certificate record created on every verify

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error — 12 cases)
- [x] Test data requirements specified (blank PNG fixture, large PNG fixture)
- [x] Mocking strategy for storage and image processing
- [x] Acceptance criteria stated (18 criteria)

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
