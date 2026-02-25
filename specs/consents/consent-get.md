# Consent Get Spec

---

## Overview

**Feature:** Retrieve the full detail of a single informed consent form for a patient, including rendered content, all collected signatures, current status, and a link to the signed PDF if the consent is finalized.

**Domain:** consents

**Priority:** High

**Dependencies:** IC-04 (consent-create.md), IC-05 (consent-sign.md), IC-08 (consent-pdf.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, patient (own consents only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients can only access their own consents. All clinic staff can access any consent within their tenant.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/consents/{consent_id}
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

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
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient owning the consent | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| consent_id | Yes | string (UUID) | Valid UUID v4, must belong to patient | Consent to retrieve | c3d4e5f6-0000-4000-8000-000000000030 |

### Query Parameters

None.

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "template_id": "uuid",
  "template_name": "string",
  "procedure_description": "string",
  "tooth_numbers": "integer[]",
  "treatment_plan_id": "uuid | null",
  "scheduled_date": "string (ISO 8601 date) | null",
  "status": "string (draft | pending_signatures | signed | voided)",
  "content_rendered": "string (HTML — patient data pre-filled)",
  "content_hash": "string (SHA256 hex) | null — only if status=signed",
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
  "pending_signatures": "string[] — signer_types still required",
  "pdf_url": "string | null — relative URL if signed, null otherwise",
  "void_reason": "string | null — populated only if status=voided",
  "voided_by": "uuid | null",
  "voided_at": "string (ISO 8601 datetime) | null",
  "locked_at": "string (ISO 8601 datetime) | null",
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example (signed consent):**
```json
{
  "id": "c3d4e5f6-0000-4000-8000-000000000030",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "template_id": "a1b2c3d4-0000-4000-8000-000000000001",
  "template_name": "Consentimiento General Odontologico",
  "procedure_description": "Extraccion quirurgica de tercer molar inferior derecho impactado (diente 48)",
  "tooth_numbers": [48],
  "treatment_plan_id": null,
  "scheduled_date": "2026-03-15",
  "status": "signed",
  "content_rendered": "<h1>CONSENTIMIENTO INFORMADO</h1><p>Yo, <strong>Maria Garcia Lopez</strong>...</p>",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "signatures": [
    {
      "id": "s1a2b3c4-0000-4000-8000-000000000050",
      "signer_type": "doctor",
      "signer_name": "Juan Carlos Perez Rodriguez",
      "signer_document": "79512345",
      "signed_at": "2026-02-24T14:30:00Z",
      "ip_address": "190.25.1.45",
      "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)"
    },
    {
      "id": "s2b3c4d5-0000-4000-8000-000000000051",
      "signer_type": "patient",
      "signer_name": "Maria Garcia Lopez",
      "signer_document": "1020304050",
      "signed_at": "2026-02-24T14:32:00Z",
      "ip_address": "190.25.1.45",
      "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)"
    }
  ],
  "pending_signatures": [],
  "pdf_url": "/api/v1/patients/f47ac10b-58cc-4372-a567-0e02b2c3d479/consents/c3d4e5f6-0000-4000-8000-000000000030/pdf",
  "void_reason": null,
  "voided_by": null,
  "voided_at": null,
  "locked_at": "2026-02-24T14:32:05Z",
  "created_by": "d4e5f6a7-0000-4000-8000-000000000004",
  "created_at": "2026-02-24T14:15:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role not allowed, or patient attempting to access another patient's consent.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para ver este consentimiento."
}
```

#### 404 Not Found
**When:** `patient_id` or `consent_id` not found in tenant, or `consent_id` does not belong to the specified `patient_id`.

**Example:**
```json
{
  "error": "not_found",
  "message": "Consentimiento no encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate path parameters are valid UUIDs.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role:
   - If `patient`: verify JWT sub matches the `portal_user_id` associated with `patient_id`. If mismatch, return 403.
   - If `doctor`, `assistant`, `clinic_owner`: allow any patient in the tenant.
4. Check Redis cache: `tenant:{tenant_id}:patients:{patient_id}:consents:{consent_id}`. Return if hit.
5. Fetch consent record including related `digital_signatures` rows (JOIN).
6. Verify `consent.patient_id == patient_id` in path. Return 404 if not matched.
7. Compute `pending_signatures` from template's required signature types minus collected signer_types.
8. Set `pdf_url` to the PDF endpoint URL if `status == signed`; otherwise `null`.
9. Cache result in Redis with 5-minute TTL (short TTL because consent status can change rapidly).
10. Write audit log for PHI access.
11. Return 200 with full consent detail.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| consent_id | Valid UUID v4 | El identificador del consentimiento no es valido. |

**Business Rules:**

- `content_rendered` always includes the pre-filled patient data — even in draft and voided states.
- `content_hash` is only present when `status == signed`; it is `null` otherwise.
- `signature` image URLs are NOT returned in the detail response — only metadata (signer_name, signer_document, timestamps). Signature images are embedded in the PDF only.
- All fields are returned regardless of status — no conditional field hiding.
- Voided consents remain fully readable (void_reason and voided_by included).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Consent in `draft` status | Return full detail with `signatures: []`, `pdf_url: null`, `content_hash: null` |
| Consent in `voided` status | Return full detail with `void_reason` and `voided_at` populated |
| `pending_signatures` when only doctor has signed | Returns `["patient"]` if patient signature required |
| Patient accesses their own signed consent | 200 OK, full detail including signatures metadata and pdf_url |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation)

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patients:{patient_id}:consents:{consent_id}`: SET — populated on cache miss

**Cache TTL:** 5 minutes (short, due to active signing workflows)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** consent
- **PHI involved:** Yes (content_rendered includes patient name, document number)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 80ms (cache hit)
- **Maximum acceptable:** < 250ms (cache miss with JOIN)

### Caching Strategy
- **Strategy:** Redis cache per consent ID (tenant-namespaced)
- **Cache key:** `tenant:{tenant_id}:patients:{patient_id}:consents:{consent_id}`
- **TTL:** 5 minutes
- **Invalidation:** Invalidated on sign, void, or any update to the consent record

### Database Performance

**Queries executed:** 1 (consent + signatures JOIN, single query)

**Indexes required:**
- `{tenant}.consents.(patient_id, id)` — COMPOSITE INDEX
- `{tenant}.digital_signatures.consent_id` — INDEX

**N+1 prevention:** Signatures fetched via single JOIN on consent query; no per-signature sub-queries.

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

**Output encoding:** content_rendered is pre-sanitized HTML (sanitized at template creation). Pydantic serialization on all output fields.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** content_rendered (patient name, cedula, age, procedure), signer_name, signer_document, ip_address

**Audit requirement:** All access logged (every read of PHI-containing consent detail is audited).

---

## Testing

### Test Cases

#### Happy Path
1. Doctor retrieves a signed consent
   - **Given:** Authenticated doctor, signed consent with 2 signatures (patient + doctor)
   - **When:** GET /api/v1/patients/{patient_id}/consents/{consent_id}
   - **Then:** 200 OK, status=signed, 2 signatures returned, pdf_url populated, content_hash present

2. Doctor retrieves a draft consent
   - **Given:** Authenticated doctor, draft consent (no signatures yet)
   - **When:** GET /api/v1/patients/{patient_id}/consents/{consent_id}
   - **Then:** 200 OK, status=draft, signatures=[], pdf_url=null, content_hash=null

3. Patient retrieves their own consent
   - **Given:** Patient with portal access, consent belonging to this patient
   - **When:** GET /api/v1/patients/{patient_id}/consents/{consent_id} (patient JWT)
   - **Then:** 200 OK, full detail returned

4. Cache hit on repeated request
   - **Given:** Same consent requested twice within 5 minutes
   - **When:** GET (second call)
   - **Then:** 200 OK from cache, DB not queried

#### Edge Cases
1. Voided consent retrieved
   - **Given:** Consent with status=voided
   - **When:** GET
   - **Then:** 200 OK, void_reason and voided_at populated, content still readable

2. Consent with only doctor signature (pending_signatures)
   - **Given:** Doctor signed, patient has not yet signed
   - **When:** GET
   - **Then:** 200 OK, status=pending_signatures, pending_signatures=["patient"]

#### Error Cases
1. Consent not found
   - **Given:** Valid UUID not matching any consent
   - **When:** GET /api/v1/patients/{patient_id}/consents/{nonexistent_id}
   - **Then:** 404 Not Found

2. Consent belongs to different patient
   - **Given:** consent_id belongs to a different patient in same tenant
   - **When:** GET with mismatched patient_id
   - **Then:** 404 Not Found

3. Patient accessing another patient's consent
   - **Given:** Patient A's JWT, URL uses Patient B's patient_id
   - **When:** GET
   - **Then:** 403 Forbidden

4. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** GET
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (happy path); patient with portal access; patient without portal access (negative)

**Patients/Entities:** Consent in each status (draft, pending_signatures, signed, voided); consent with multiple signatures.

### Mocking Strategy

- Redis cache: Use fakeredis to test cache hit/miss
- Audit log: Mock audit service; assert PHI=true write logged

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Signed consent returns full detail with signatures, pdf_url, and content_hash
- [ ] Draft consent returns `signatures: []` and `pdf_url: null`
- [ ] Voided consent returns void_reason and voided_at
- [ ] `pending_signatures` correctly computed from template requirements
- [ ] Patient can only access their own consents (403 otherwise)
- [ ] `ip_address` not exposed in public patient-facing response (mask last octet for patient role)
- [ ] Audit log entry written for every read (PHI=true)
- [ ] Cache populated on first request; short 5-minute TTL
- [ ] All test cases pass
- [ ] Performance target met (< 80ms cache hit, < 250ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Downloading the PDF (see IC-08 consent-pdf.md)
- Listing all consents for a patient (see IC-07 consent-list.md)
- Signing the consent (see IC-05 consent-sign.md)
- Voiding the consent (see IC-09 consent-void.md)

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
- [x] Response time target defined
- [x] Caching strategy stated (short TTL for active consents)
- [x] DB queries optimized (indexes listed, JOIN strategy)
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
