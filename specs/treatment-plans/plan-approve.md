# TP-08: Approve Treatment Plan Spec

---

## Overview

**Feature:** Record the patient's informed consent and digital approval of a treatment plan. Captures a hand-drawn digital signature (base64), signer identity (name and document), IP address, and timestamp. Transitions the plan from draft to active and automatically generates a quotation (B-16) if one does not already exist.

**Domain:** treatment-plans

**Priority:** High

**Dependencies:** TP-01 (plan-create.md), TP-04 (plan-update.md), DS-01 (digital-signatures), B-16 (quotation-generate), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, clinic_owner (on behalf of patient in clinic), patient (from portal — portal domain context)
- **Tenant context:** Required — resolved from JWT
- **Special rules:**
  - When called by clinic staff (doctor, clinic_owner), the patient is present and signs in the clinic on a tablet/device.
  - When called by `patient` role (portal context), the JWT must contain the patient's own identity and their patient_id must match the URL parameter.
  - The IP address is captured from the request for the audit trail.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/approve
```

**Rate Limiting:**
- 10 requests per minute per user (approval is not a high-frequency operation; rate-limit prevents replay attempts)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |
| X-Forwarded-For | No | string | Client IP (captured server-side) | 192.168.1.10 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | uuid | Valid UUID, must belong to tenant | Patient's unique identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| plan_id | Yes | uuid | Valid UUID, must belong to patient | Treatment plan's unique identifier | b2c3d4e5-f6a7-8901-bcde-f12345678901 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "signature": "string (required) — base64-encoded PNG image of the drawn signature, max 2MB decoded",
  "signer_name": "string (required) — full name of the signer, max 200 chars",
  "signer_document": "string (required) — national ID (cedula/CURP/RUT) of the signer, max 30 chars"
}
```

**Example Request:**
```json
{
  "signature": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "signer_name": "Maria Garcia Lopez",
  "signer_document": "1020304050"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "plan_id": "uuid",
  "patient_id": "uuid",
  "approval_status": "string (approved)",
  "approved_at": "string (ISO 8601 datetime)",
  "signer_name": "string",
  "signer_document": "string",
  "signature_id": "uuid",
  "signature_url": "string (S3 signed URL, expires in 1 hour)",
  "ip_address": "string",
  "plan_status": "string (active)",
  "quotation_id": "uuid | null",
  "quotation_generated": "boolean"
}
```

**Example:**
```json
{
  "plan_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "approval_status": "approved",
  "approved_at": "2026-02-24T14:00:00Z",
  "signer_name": "Maria Garcia Lopez",
  "signer_document": "1020304050",
  "signature_id": "f6a1b2c3-d4e5-6789-abcd-456789012345",
  "signature_url": "https://s3.amazonaws.com/dental-os-docs/signatures/f6a1b2c3...?X-Amz-Expires=3600",
  "ip_address": "192.168.1.10",
  "plan_status": "active",
  "quotation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "quotation_generated": true
}
```

### Error Responses

#### 400 Bad Request
**When:** Plan is already approved, or plan has no items to approve.

**Example:**
```json
{
  "error": "plan_already_approved",
  "message": "Este plan de tratamiento ya fue aprobado por el paciente.",
  "details": {
    "approved_at": "2026-02-15T09:30:00Z"
  }
}
```

**Example (no items):**
```json
{
  "error": "plan_has_no_items",
  "message": "No se puede aprobar un plan de tratamiento sin procedimientos."
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Patient role attempting to approve another patient's plan, or role not allowed.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para aprobar este plan de tratamiento."
}
```

#### 404 Not Found
**When:** patient_id or plan_id not found in tenant.

**Example:**
```json
{
  "error": "plan_not_found",
  "message": "Plan de tratamiento no encontrado."
}
```

#### 409 Conflict
**When:** Plan is in cancelled or completed status.

**Example:**
```json
{
  "error": "plan_not_approvable",
  "message": "Solo se pueden aprobar planes en estado 'draft'.",
  "details": {
    "plan_status": "cancelled"
  }
}
```

#### 422 Unprocessable Entity
**When:** Signature is not valid base64, exceeds size limit, or required fields missing.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "signature": ["La firma digital no es valida o supera el tamano maximo permitido (2MB)."],
    "signer_name": ["El nombre del firmante es obligatorio."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database, S3 upload failure, or quotation generation error.

---

## Business Logic

**Step-by-step process:**

1. Validate input against Pydantic schema (required fields, base64 format, size check).
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user permissions via RBAC. If patient role, verify patient_id in JWT matches URL patient_id.
4. Fetch plan; verify exists and belongs to patient.
5. Validate plan state:
   - Must be in 'draft' status; return 409 if cancelled or completed.
   - Must have approval_status = 'pending_approval'; return 400 if already approved.
   - Must have at least 1 non-cancelled item; return 400 if no items.
6. Decode and validate base64 signature:
   - Strip data URI prefix if present (data:image/png;base64,).
   - Verify decoded size <= 2MB.
   - Verify it is a valid PNG image (check PNG magic bytes).
7. Upload signature image to S3 bucket under tenant-scoped path: `tenants/{tenant_id}/signatures/{plan_id}/{uuid}.png`.
8. Insert `digital_signatures` record (DS-01) with:
   - `resource_type = 'treatment_plan'`
   - `resource_id = plan_id`
   - `signer_name`, `signer_document`
   - `signature_s3_key` (storage path)
   - `ip_address` (from X-Forwarded-For or remote_addr, normalized)
   - `signed_by = current_user.id`
   - `signed_at = now()`
9. Update `treatment_plans`:
   - `approval_status = 'approved'`
   - `status = 'active'`
   - `approved_at = now()`
   - `signature_id = digital_signature.id`
10. Check if quotation already exists for this plan (`quotation_id` is null). If no quotation exists, dispatch async job to generate quotation (B-16).
11. Write audit log entry (action: create, resource: digital_signature, PHI: yes).
12. Write audit log entry (action: update, resource: treatment_plan, PHI: yes, notes: "plan approved, status → active").
13. Invalidate plan cache.
14. Dispatch `treatment_plan.approved` event to RabbitMQ.
15. Generate a pre-signed S3 URL for the signature image (1 hour TTL) for the response.
16. Return 200 with approval confirmation.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| signature | Required, valid base64, decoded size <= 2MB, PNG format | La firma digital no es valida o supera el tamano maximo permitido (2MB). |
| signer_name | 1-200 chars, required | El nombre del firmante es obligatorio. |
| signer_document | 1-30 chars, alphanumeric + hyphens, required | El documento del firmante es obligatorio. |

**Business Rules:**

- Only plans in `draft` status with `approval_status = 'pending_approval'` can be approved.
- Approval is idempotent in the sense that re-attempting returns 400 with the original approval date (not an overwrite).
- The plan transitions `draft → active` atomically with the signature recording in a single database transaction.
- Quotation generation (B-16) is triggered asynchronously via the queue to avoid blocking the response; the quotation_id may be null in the response if generation has not yet completed — callers should poll or use the plan-get endpoint later.
- The signer may be the patient themselves (portal) or a guardian or authorized representative in the clinic (documented via signer_document).
- IP address is recorded from the HTTP request for legal evidentiary purposes; it is never taken from the request body.
- Signature PNG is stored encrypted at rest in S3 under the tenant's namespace.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient signs from portal (patient role) | Allowed; patient_id in JWT must match URL patient_id |
| Signature sent as plain base64 (no data URI prefix) | Accepted; code handles both formats |
| Plan has only cancelled items (items_count > 0 but all cancelled) | Return 400 plan_has_no_items — no active procedures to approve |
| Quotation already exists for plan | quotation_generated = false; existing quotation_id returned |
| S3 upload fails | Transaction rolled back; return 500; retry mechanism in place |
| signer_document differs from patient's document | Allowed — a guardian or spouse may sign on behalf of the patient |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `digital_signatures`: INSERT — approval record (DS-01 format)
- `treatment_plans`: UPDATE — approval_status, status, approved_at, signature_id

**Example query (SQLAlchemy):**
```python
# Within a single transaction:
signature = DigitalSignature(
    resource_type="treatment_plan",
    resource_id=plan_id,
    signer_name=data.signer_name,
    signer_document=data.signer_document,
    signature_s3_key=s3_key,
    ip_address=client_ip,
    signed_by=current_user.id,
    signed_at=datetime.utcnow(),
)
session.add(signature)
await session.flush()

await session.execute(
    update(TreatmentPlan)
    .where(TreatmentPlan.id == plan_id)
    .values(
        approval_status="approved",
        status="active",
        approved_at=datetime.utcnow(),
        signature_id=signature.id,
        updated_at=datetime.utcnow(),
    )
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plan:{plan_id}`: DELETE
- `tenant:{tenant_id}:patient:{patient_id}:treatment_plans:list:*`: INVALIDATE

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| treatment-plans | treatment_plan.approved | { tenant_id, patient_id, plan_id, signature_id, approved_by } | After successful approval |
| billing | quotation.generate | { tenant_id, patient_id, plan_id } | When no existing quotation exists |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create (for digital_signature) + update (for treatment_plan status)
- **Resource:** digital_signature, treatment_plan
- **PHI involved:** Yes (signer identity, clinical plan)

### Notifications

**Notifications triggered:** No (downstream notification triggered by queue consumer on treatment_plan.approved event)

---

## Performance

### Expected Response Time
- **Target:** < 500ms (includes S3 upload)
- **Maximum acceptable:** < 2000ms (S3 can be slow in some regions)

### Caching Strategy
- **Strategy:** No caching on write
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Plan detail and list caches invalidated on approval

### Database Performance

**Queries executed:** 3 (plan fetch + items count check, digital_signature insert, plan update — all in single transaction)

**Indexes required:**
- `digital_signatures.(resource_type, resource_id)` — UNIQUE INDEX (prevent duplicate approvals)
- `treatment_plans.(patient_id, id)` — INDEX (primary lookup)

**N+1 prevention:** Not applicable (single write operation).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| signature | Base64 decode + PNG magic byte validation | Prevents non-image data storage |
| signer_name | Pydantic `strip()` + strip_tags | Prevent XSS in legal documents |
| signer_document | Pydantic validator: alphanumeric + hyphens, max 30 | Prevent injection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, signer_name, signer_document (national ID), signature image (biometric-adjacent data), ip_address.

**Audit requirement:** All writes logged with PHI flag. Signature image stored encrypted at rest in S3 with tenant-scoped access controls.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor records patient approval in clinic
   - **Given:** Doctor JWT, draft plan with 2 items, valid signature, signer_name, signer_document
   - **When:** POST /approve
   - **Then:** 200 OK, approval_status = approved, plan_status = active, quotation generated, signature_id set

2. Patient approves from portal
   - **Given:** Patient JWT where patient_id matches URL, draft plan
   - **When:** POST /approve from portal
   - **Then:** 200 OK, same result as staff approval

3. Approval generates quotation (no existing quotation)
   - **Given:** Draft plan with no quotation
   - **When:** POST /approve
   - **Then:** 200 OK, quotation.generate job dispatched, quotation_generated = true (async)

4. Approval with existing quotation
   - **Given:** Draft plan with existing quotation_id
   - **When:** POST /approve
   - **Then:** 200 OK, quotation_generated = false, existing quotation_id returned

#### Edge Cases
1. Signature sent without data URI prefix (raw base64)
   - **Given:** Plain base64 PNG string
   - **When:** POST /approve
   - **Then:** 200 OK, accepted and stored correctly

2. Signer is guardian (signer_document differs from patient)
   - **Given:** signer_document = parent's cedula
   - **When:** POST /approve
   - **Then:** 200 OK, stored as-is

#### Error Cases
1. Plan already approved
   - **Given:** Plan with approval_status = approved
   - **When:** POST /approve
   - **Then:** 400 plan_already_approved with original approved_at

2. Plan has no items (or all cancelled)
   - **Given:** Draft plan with 0 items
   - **When:** POST /approve
   - **Then:** 400 plan_has_no_items

3. Cancelled plan
   - **Given:** Cancelled plan
   - **When:** POST /approve
   - **Then:** 409 plan_not_approvable

4. Signature exceeds 2MB
   - **Given:** base64 string decoding to > 2MB
   - **When:** POST /approve
   - **Then:** 422 validation error on signature field

5. Patient approving another patient's plan
   - **Given:** Patient JWT, URL patient_id belongs to different patient
   - **When:** POST /approve
   - **Then:** 403 Forbidden

6. S3 upload failure
   - **Given:** S3 service unavailable
   - **When:** POST /approve
   - **Then:** 500, transaction rolled back, no approval record created

### Test Data Requirements

**Users:** doctor, clinic_owner, patient (portal context)

**Patients/Entities:** Draft plan with 2 items; draft plan with 0 items; draft plan with all-cancelled items; approved plan; cancelled plan; plan with existing quotation.

### Mocking Strategy

- S3 upload: Mock boto3 put_object call, assert key format and content type
- RabbitMQ: Mock publish, assert treatment_plan.approved and quotation.generate payloads
- DS-01 digital signature service: Direct DB insert in test (no external service)
- Redis cache: fakeredis for invalidation tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Approval records digital_signature with signer identity, IP, and S3 key
- [ ] Plan transitions draft → active atomically with signature recording
- [ ] quotation.generate job dispatched when no existing quotation
- [ ] Plan already approved returns 400 (idempotent error)
- [ ] Plan with no active items returns 400
- [ ] Cancelled/completed plan returns 409
- [ ] Signature exceeding 2MB returns 422
- [ ] Patient role blocked from approving another patient's plan
- [ ] Audit logs written for both digital_signature and plan status change
- [ ] S3 upload failure rolls back transaction
- [ ] Plan cache invalidated after approval
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms including S3)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Plan rejection by patient (separate workflow, if required)
- Re-approval after plan modification (requires new approval record)
- Bulk plan approval
- Quotation generation details (see B-16)

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
- [x] Response time target defined (accounts for S3 latency)
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (two entries: signature + plan status)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services (S3, RabbitMQ)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
