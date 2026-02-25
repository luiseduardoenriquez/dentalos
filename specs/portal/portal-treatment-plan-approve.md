# PP-05 Portal Treatment Plan Approve Spec

---

## Overview

**Feature:** Patient approves a treatment plan from the portal via digital signature. Captures a base64-encoded PNG signature image, records timestamp, client IP, and device/user-agent. The approval is immutable once signed — it cannot be revoked or re-signed from the portal. Legally equivalent to a written signature under Colombia Ley 527/1999.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-04 (portal-treatment-plans.md), TP-04 (treatment-plan-approve.md), patients/digital-signature.md, infra/audit-logging.md, infra/multi-tenancy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT (portal JWT contains tenant_id claim)
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient can only approve their own treatment plans — enforced at query level. Once approved, the endpoint returns 409 on re-submission.

---

## Endpoint

```
POST /api/v1/portal/treatment-plans/{plan_id}/approve
```

**Rate Limiting:**
- 10 requests per hour per patient (approval is intentional; low rate limit protects against automated abuse)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |
| X-Forwarded-For | No | string | Patient's real IP (set by reverse proxy) | 190.25.1.45 |
| User-Agent | No | string | Patient's browser/device info | Mozilla/5.0... |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| plan_id | Yes | string (UUID) | Valid UUID v4 | Treatment plan to approve | c3d4e5f6-a1b2-7890-abcd-ef1234567890 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "signature_data": "string (required) — base64-encoded PNG of patient signature, max 500KB decoded",
  "agreed_to_terms": "boolean (required) — must be true; patient confirms they have read and agree to the treatment plan",
  "full_name_confirmation": "string (required) — patient types their full name as confirmation, max 200 chars"
}
```

**Example Request:**
```json
{
  "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "agreed_to_terms": true,
  "full_name_confirmation": "Maria Garcia Lopez"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "status": "string — always 'approved'",
  "plan_id": "uuid",
  "approved_at": "string (ISO 8601 datetime)",
  "signature": {
    "hash": "string — SHA-256 hash of the signature PNG bytes (hex encoded)",
    "signed_by_name": "string — full_name_confirmation as recorded",
    "signed_at": "string (ISO 8601 datetime)",
    "signed_from_ip": "string — anonymized IP (last octet masked for privacy display)",
    "device_info": "string — user agent string truncated to 200 chars"
  },
  "document_url": "string — signed S3 URL to the stamped approval document PDF (valid 60 minutes)"
}
```

**Example:**
```json
{
  "status": "approved",
  "plan_id": "c3d4e5f6-a1b2-7890-abcd-ef1234567890",
  "approved_at": "2026-02-25T15:45:00-05:00",
  "signature": {
    "hash": "a3f5c8e1b2d4f67890abcdef1234567890abcdef1234567890abcdef12345678",
    "signed_by_name": "Maria Garcia Lopez",
    "signed_at": "2026-02-25T15:45:00-05:00",
    "signed_from_ip": "190.25.1.XXX",
    "device_info": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/537.36"
  },
  "document_url": "https://s3.amazonaws.com/dentaios-docs/tn_abc123/approvals/c3d4e5f6.pdf?X-Amz-Expires=3600&..."
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields, signature_data not valid base64, agreed_to_terms is false.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "agreed_to_terms": ["Debe aceptar los terminos del plan de tratamiento para continuar."],
    "signature_data": ["La firma no es valida. Se requiere imagen PNG en formato base64."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal", role is not "patient", or the treatment plan belongs to a different patient.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para aprobar este plan de tratamiento."
}
```

#### 404 Not Found
**When:** Treatment plan with given plan_id not found in tenant, or does not belong to this patient.

**Example:**
```json
{
  "error": "treatment_plan_not_found",
  "message": "Plan de tratamiento no encontrado."
}
```

#### 409 Conflict
**When:** Treatment plan has already been approved (patient_approved = true). Approval is immutable.

**Example:**
```json
{
  "error": "already_approved",
  "message": "Este plan de tratamiento ya fue aprobado el 2026-01-17T14:30:00-05:00. La aprobacion no puede modificarse.",
  "details": {
    "approved_at": "2026-01-17T14:30:00-05:00",
    "signed_by_name": "Maria Garcia Lopez"
  }
}
```

#### 422 Unprocessable Entity
**When:** Plan is in a status that does not allow patient approval (e.g., draft, cancelled, completed).

**Example:**
```json
{
  "error": "plan_not_approvable",
  "message": "Solo se pueden aprobar planes en estado 'activo' o 'pendiente de aprobacion'. El estado actual es: completado."
}
```

#### 413 Payload Too Large
**When:** signature_data decoded PNG exceeds 500KB.

**Example:**
```json
{
  "error": "signature_too_large",
  "message": "La imagen de firma no puede superar los 500KB."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded (10/hour per patient). See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected failure during signature storage or document generation.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Validate request body: required fields, agreed_to_terms must be true, base64 format check.
3. Decode signature_data from base64; verify it is a valid PNG (check magic bytes: `\x89PNG\r\n\x1a\n`). If not valid PNG, return 400.
4. Check decoded size <= 500KB. If larger, return 413.
5. Resolve tenant schema; set `search_path`.
6. Fetch treatment plan: `SELECT ... FROM treatment_plans WHERE id = :plan_id AND patient_id = :patient_id`. If not found, return 404.
7. Check plan status: must be 'pending_approval' or 'active' and `requires_patient_approval=true`. If already approved (patient_approved=true), return 409 with approval details. If status is draft/cancelled/completed, return 422.
8. Compute SHA-256 hash of decoded PNG bytes (hex string, 64 chars).
9. Store signature PNG to S3: `s3://dentaios-docs/{tenant_id}/signatures/plan_{plan_id}_patient_{patient_id}_{timestamp}.png`.
10. Extract client IP from `X-Forwarded-For` header (first IP in chain); fallback to request.client.host. Record full IP internally; mask last octet in response.
11. Extract User-Agent, truncate to 200 chars.
12. Within a database transaction:
    a. UPDATE treatment_plans SET patient_approved=true, patient_approved_at=NOW(), approval_signature_hash=:hash, approval_signature_url=:s3_url, approval_full_name=:full_name, approval_ip=:ip, approval_user_agent=:ua WHERE id=:plan_id.
    b. INSERT into audit_log: action='patient_approve_treatment_plan', resource='treatment_plan', resource_id=plan_id, actor_id=patient_id, actor_type='patient', metadata={hash, ip, device_info}.
13. Dispatch RabbitMQ job: generate approval document PDF (includes plan details + embedded signature image) and store to S3; generate pre-signed URL (TTL 60 minutes).
14. Dispatch notification job: notify clinic staff (receptionist/doctor) that patient approved the plan.
15. Invalidate treatment plan cache for this patient.
16. Return 200 with approval confirmation and document URL.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| plan_id | Valid UUID v4 | Plan de tratamiento no encontrado. |
| signature_data | Valid base64 string; decodes to PNG (magic bytes check); decoded size <= 500KB | La firma no es valida. |
| agreed_to_terms | Must be boolean true (not false, not null) | Debe aceptar los terminos. |
| full_name_confirmation | Required string, 1-200 chars, strip whitespace | El nombre de confirmacion es obligatorio. |

**Business Rules:**

- Approval is **immutable**: once patient_approved=true, this endpoint returns 409 on any re-submission. No undo from portal.
- Only clinic staff (clinic_owner) can revoke approval via admin endpoint (future enhancement).
- The `full_name_confirmation` is stored as typed by the patient and compared for audit purposes — NOT validated against patient's actual name (patients may use nicknames or middle names).
- Signature PNG is stored raw (not processed); hash ensures integrity.
- Document PDF is generated asynchronously; a pre-signed URL to the eventual PDF is returned (PDF may take a few seconds to generate). Client should handle 404 on the URL with a brief retry.
- Colombia Ley 527/1999: digital signatures with IP, timestamp, and hash are legally binding.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Plan does not require patient approval (requires_patient_approval=false) | Return 422: this plan does not require patient approval |
| S3 upload fails | Rollback DB transaction; return 500; no partial state |
| Patient signs from mobile device | User-Agent stored; IP from X-Forwarded-For; behavior identical |
| Plan moves to 'cancelled' while patient is signing | Plan status check in transaction; return 422 |
| Very small signature (few pixels) | Accept if valid PNG and <= 500KB; no minimum size enforced |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `treatment_plans`: UPDATE — patient_approved=true, patient_approved_at, approval_signature_hash, approval_signature_url, approval_full_name, approval_ip, approval_user_agent

**Example query (SQLAlchemy):**
```python
stmt = (
    update(TreatmentPlan)
    .where(
        TreatmentPlan.id == plan_id,
        TreatmentPlan.patient_id == patient_id,
    )
    .values(
        patient_approved=True,
        patient_approved_at=func.now(),
        approval_signature_hash=signature_hash,
        approval_signature_url=s3_url,
        approval_full_name=data.full_name_confirmation,
        approval_ip=client_ip,
        approval_user_agent=user_agent[:200],
    )
)
await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:treatment_plans:*`: INVALIDATE — all treatment plan list caches for this patient
- `tenant:{tenant_id}:treatment_plan:{plan_id}`: INVALIDATE — plan detail cache used by clinic staff

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| documents | generate_approval_pdf | { tenant_id, plan_id, patient_id, signature_url, approved_at } | After successful DB update |
| notifications | treatment_plan_approved_by_patient | { tenant_id, plan_id, patient_id, approved_at } | After successful DB update |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** patient_approve
- **Resource:** treatment_plan
- **PHI involved:** Yes (treatment plan content + patient signature = clinical PHI + legal document)

**Additional audit fields:**
- `signature_hash`: SHA-256 hash of signature PNG
- `client_ip`: full IP address (not masked in audit log)
- `user_agent`: browser/device info
- `full_name_as_signed`: text typed by patient

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | treatment_plan_patient_approved | clinic staff (doctor + receptionist) | On successful approval |
| email | treatment_plan_approved_staff | doctor assigned to plan | On successful approval |

---

## Performance

### Expected Response Time
- **Target:** < 500ms (S3 upload dominates; parallel with DB update)
- **Maximum acceptable:** < 2000ms (PDF generation is async; not in response time budget)

### Caching Strategy
- **Strategy:** No caching on write; invalidation of treatment plan caches
- **Cache key:** N/A (write operation)
- **TTL:** N/A
- **Invalidation:** All treatment plan caches for this patient and plan invalidated on success

### Database Performance

**Queries executed:** 2 (plan fetch + update in transaction)

**Indexes required:**
- `treatment_plans.(id, patient_id)` — COMPOSITE INDEX (ownership check + fetch)
- `treatment_plans.patient_approved` — INDEX (for filtering approvable plans)

**N+1 prevention:** Not applicable (single plan update).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| plan_id | UUID v4 regex validation | Path parameter |
| signature_data | Base64 decode; PNG magic byte check; size check | Never stored raw in DB — only S3 URL and hash stored |
| agreed_to_terms | Boolean strict validation (Pydantic StrictBool) | Must be exactly true |
| full_name_confirmation | Pydantic strip + strip_tags; max 200 chars | Free text; sanitized before storage |
| X-Forwarded-For | First IP extracted; validated as IP address format | Used for audit only |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. plan_id and patient_id from validated sources.

### XSS Prevention

**Output encoding:** All string outputs escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Treatment plan content (clinical), patient signature (biometric PII), full_name_confirmation, client IP

**Audit requirement:** All writes logged with full metadata (IP, hash, device) — required for legal validity under Ley 527/1999.

### Signature Integrity

- SHA-256 hash computed from raw decoded PNG bytes before S3 upload.
- Hash stored in database alongside S3 URL.
- Integrity can be verified at any time by re-downloading from S3 and recomputing hash.

---

## Testing

### Test Cases

#### Happy Path
1. Patient approves plan with valid signature
   - **Given:** Treatment plan in 'pending_approval' status, patient_approved=false
   - **When:** POST /api/v1/portal/treatment-plans/{id}/approve with valid signature PNG
   - **Then:** 200 OK, patient_approved=true in DB, audit log written, notifications dispatched, document URL returned

2. Approval from mobile device
   - **Given:** Valid plan awaiting approval
   - **When:** POST with mobile User-Agent, X-Forwarded-For from mobile IP
   - **Then:** 200 OK, IP and device info correctly recorded in DB

3. Approval of active plan (not yet approved)
   - **Given:** Plan status='active', requires_patient_approval=true, patient_approved=false
   - **When:** POST approval
   - **Then:** 200 OK — status='active' plans with requires_patient_approval=true are approvable

#### Edge Cases
1. Very short signature (minimal strokes)
   - **Given:** Valid but minimal PNG (signature with one stroke)
   - **When:** POST approval
   - **Then:** 200 OK — no minimum signature complexity enforced

2. Concurrent approval requests
   - **Given:** Two simultaneous approval requests for same plan
   - **When:** Both POSTed simultaneously
   - **Then:** One succeeds (200), second returns 409 (idempotency via DB update row lock)

#### Error Cases
1. Plan already approved
   - **Given:** patient_approved=true already set on plan
   - **When:** POST approval again
   - **Then:** 409 Conflict with approved_at and signed_by_name in details

2. agreed_to_terms is false
   - **Given:** Valid signature, full_name provided
   - **When:** POST with agreed_to_terms=false
   - **Then:** 400 Bad Request with validation error

3. Plan belongs to different patient
   - **Given:** plan_id exists but belongs to another patient in the same tenant
   - **When:** POST from current patient's JWT
   - **Then:** 404 Not Found (treat as not found, not 403, to avoid info leak)

4. Signature is not a PNG
   - **Given:** base64-encoded JPEG submitted as signature_data
   - **When:** POST approval
   - **Then:** 400 Bad Request — invalid PNG magic bytes

5. Signature too large
   - **Given:** base64-encoded PNG that decodes to 600KB
   - **When:** POST approval
   - **Then:** 413 Payload Too Large

### Test Data Requirements

**Users:** Patient with portal_access=true; treatment plan in pending_approval status with requires_patient_approval=true.

**Patients/Entities:** Valid base64 PNG fixture for signature; S3 mock; RabbitMQ mock.

### Mocking Strategy

- S3: moto library for S3 mocking in tests
- RabbitMQ: Mock publish, assert job type and payload
- SHA-256: real computation (deterministic)
- Time: pytest-freezegun for reproducible timestamps

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient can approve their own treatment plan with a valid PNG signature
- [ ] Approval sets patient_approved=true with timestamp, hash, IP, device info in DB
- [ ] Signature PNG stored to S3 with correct path convention
- [ ] SHA-256 hash computed and stored alongside S3 URL
- [ ] Approval is immutable — re-submission returns 409 with original approval details
- [ ] agreed_to_terms=false returns 400 before any processing
- [ ] Plan belonging to different patient returns 404
- [ ] Cancelled/draft/completed plans return 422
- [ ] S3 upload failure rolls back DB changes (atomicity)
- [ ] Audit log written with full metadata (IP, hash, name, device)
- [ ] RabbitMQ jobs dispatched for PDF generation and staff notification
- [ ] Treatment plan caches invalidated
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms for sync operations)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Revoking patient approval (clinic_owner admin function only)
- Signing consent forms (see PP-12 portal-consent-sign.md — similar pattern)
- Viewing the approval document PDF (see PP-07 portal-documents.md for download)
- Countersignature by doctor (separate clinic-side flow)
- Bulk approval of multiple plans

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
- [x] Input sanitization defined (PNG validation, base64, strict bool)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail with full legal metadata (Ley 527/1999 compliance)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 500ms sync; PDF async)
- [x] Caching strategy stated (invalidation on write)
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
- [x] Mocking strategy for S3 and RabbitMQ
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
