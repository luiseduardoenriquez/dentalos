# B-19 Quotation Approve Spec

---

## Overview

**Feature:** Allow a patient (or staff acting with patient present) to approve a quotation by providing a digital signature. Upon approval, automatically creates: (1) an active treatment plan from the quotation items, and (2) an invoice draft. Implements the auto-flow: Quotation → Treatment Plan + Invoice Draft. The digital signature is stored with its SHA-256 hash for legal integrity. The quotation becomes immutable after approval. Compliant with Colombia Ley 527/1999.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-17 (quotation-get.md), B-16 (quotation-create.md), B-01 (invoice-create.md), treatment-plans domain (TreatmentPlan, TreatmentPlanItem), patients/digital-signature.md, infra/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (own quotations via portal), clinic_owner, doctor, receptionist, assistant (staff acting on behalf of patient present)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patient role may only approve their own quotation. Staff may approve any quotation within the tenant when the patient is physically present (digital signature still required). The approval is immutable — no role can reverse it.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/quotations/{quotation_id}/approve
```

**Rate Limiting:**
- 10 requests per minute per user (approval is a deliberate action; low limit prevents accidental double-submit)
- Redis idempotency key: `tenant:{tenant_id}:quotation_approve:{quotation_id}` (TTL 300s) — prevents double approval within 5 minutes

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
| patient_id | Yes | UUID | UUID v4, must exist in tenant | Patient who owns the quotation | pt_550e8400-e29b-41d4-a716-446655440000 |
| quotation_id | Yes | UUID | UUID v4, must belong to patient | Quotation to approve | quot-9a1b-2c3d-e4f5-6789abcdef01 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "signature_data": "string (required) — base64-encoded PNG of the hand-drawn signature canvas, max 2MB",
  "signed_by": "string (required) — enum: patient_self, staff_on_behalf",
  "signer_name": "string (required if signed_by=staff_on_behalf) — name of the staff member confirming patient signature, max 200 chars",
  "ip_address": "string (optional) — patient's IP at time of signature for portal signings; auto-extracted from request if not provided",
  "terms_accepted": "boolean (required) — must be true; patient confirms understanding of quotation terms"
}
```

**Example Request (patient signing via portal):**
```json
{
  "signature_data": "iVBORw0KGgoAAAANSUhEUgAA...(base64 PNG)...",
  "signed_by": "patient_self",
  "terms_accepted": true
}
```

**Example Request (staff approving on behalf of patient present in clinic):**
```json
{
  "signature_data": "iVBORw0KGgoAAAANSUhEUgAA...(base64 PNG)...",
  "signed_by": "staff_on_behalf",
  "signer_name": "Carlos Mendez - Doctor",
  "terms_accepted": true
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "quotation": {
    "id": "uuid",
    "quotation_number": "string",
    "status": "approved",
    "approved_at": "string ISO 8601",
    "total": "integer — cents"
  },
  "treatment_plan": {
    "id": "uuid",
    "treatment_plan_number": "string — TP-{YYYY}-{NNNN}",
    "status": "active",
    "item_count": "integer",
    "created_at": "string ISO 8601"
  },
  "invoice": {
    "id": "uuid",
    "invoice_number": "string — FAC-{YYYY}-{NNNNN}",
    "status": "draft",
    "total": "integer — cents",
    "created_at": "string ISO 8601"
  },
  "signature": {
    "stored_at": "string ISO 8601",
    "sha256_hash": "string — hex SHA-256 of the base64 signature_data",
    "signed_by": "string — patient_self or staff_on_behalf",
    "signer_name": "string | null"
  }
}
```

**Example:**
```json
{
  "quotation": {
    "id": "quot-9a1b-2c3d-e4f5-6789abcdef01",
    "quotation_number": "COT-2026-0001",
    "status": "approved",
    "approved_at": "2026-02-25T15:30:00-05:00",
    "total": 155000
  },
  "treatment_plan": {
    "id": "tp-aaaa-1111-bbbb-2222-cccc33334444",
    "treatment_plan_number": "TP-2026-0003",
    "status": "active",
    "item_count": 2,
    "created_at": "2026-02-25T15:30:00-05:00"
  },
  "invoice": {
    "id": "inv-dddd-5555-eeee-6666-ffff77778888",
    "invoice_number": "FAC-2026-00007",
    "status": "draft",
    "total": 155000,
    "created_at": "2026-02-25T15:30:00-05:00"
  },
  "signature": {
    "stored_at": "2026-02-25T15:30:00-05:00",
    "sha256_hash": "a3f5b8c2e1d9f4a7b6c0e3d8f2a1b5c9e8d3f7a2b4c6e0d1f9a8b3c5e2d7f4",
    "signed_by": "patient_self",
    "signer_name": null
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** `terms_accepted = false`, missing required fields, `signature_data` empty.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El paciente debe aceptar los terminos para aprobar la cotizacion.",
  "details": {
    "terms_accepted": ["Debe aceptar los terminos para continuar."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient role tries to approve another patient's quotation.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para aprobar esta cotizacion."
}
```

#### 404 Not Found
**When:** `patient_id` or `quotation_id` not found, or quotation does not belong to the patient.

**Example:**
```json
{
  "error": "not_found",
  "message": "La cotizacion no fue encontrada."
}
```

#### 409 Conflict
**When:** Quotation is not in a state that allows approval — must be `status IN ('sent', 'draft')`. Expired or already approved/rejected quotations return 409.

**Example:**
```json
{
  "error": "quotation_not_approvable",
  "message": "La cotizacion no puede ser aprobada en su estado actual.",
  "details": {
    "current_status": "expired",
    "message": "La cotizacion ha expirado. Solicita una nueva cotizacion al consultorio."
  }
}
```

#### 422 Unprocessable Entity
**When:** `signature_data` is not valid base64, decoded size exceeds 2MB, or decoded data is not a valid PNG image header.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "La firma digital no es valida.",
  "details": {
    "signature_data": ["La firma debe ser una imagen PNG en formato base64. Tamaño maximo: 2MB."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure or failure to generate sequential numbers.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. If `role = patient`: verify `user_id` maps to patient record with `patient_id`. If not, return 403.
3. Validate request body:
   - `terms_accepted` must be `true`. If false, return 400.
   - `signature_data` must be non-empty string, valid base64.
   - Decode base64: validate decoded byte size <= 2MB (2,097,152 bytes).
   - Validate PNG magic bytes: decoded data must start with `\x89PNG\r\n\x1a\n` (8 bytes). If not PNG, return 422.
   - If `signed_by = 'staff_on_behalf'`: `signer_name` required.
4. Check idempotency key in Redis: `tenant:{tenant_id}:quotation_approve:{quotation_id}`. If exists, return the cached success response (idempotent retry within 5 minutes).
5. Set `search_path` to tenant schema.
6. Load quotation: `SELECT * FROM quotations WHERE id = :quotation_id AND patient_id = :patient_id AND tenant_id = :tenant_id`. If not found, return 404.
7. Check quotation status: must be `draft` or `sent`. If `approved`, `rejected`, or `expired`, return 409 with current status in details.
8. Compute SHA-256 hash of `signature_data` (the raw base64 string): `hashlib.sha256(signature_data.encode()).hexdigest()`.
9. Store signature: insert into `patient_signatures` table with: `quotation_id`, `patient_id`, `signature_data` (base64 PNG), `sha256_hash`, `signed_by`, `signer_name`, `ip_address`, `signed_at = now()`, `user_id = caller_user_id`.
10. Begin database transaction.
11. Update quotation: `status = 'approved'`, `approved_at = now()`, `approved_by = user_id`.
12. Generate treatment plan sequential number: `INCR tenant:{tenant_id}:treatment_plan_sequence:{year}`. Format as `TP-{YYYY}-{NNNN}`.
13. Create treatment plan: `INSERT INTO treatment_plans (patient_id, doctor_id, status='active', plan_number, source='quotation', quotation_id, created_by) VALUES (...)`.
14. For each `quotation_item`, create a corresponding `treatment_plan_item`: `INSERT INTO treatment_plan_items (treatment_plan_id, service_id, procedure_name, tooth_number, quantity, unit_price, status='pending', sort_order)`.
15. Generate invoice sequential number: `INCR tenant:{tenant_id}:invoice_sequence:{year}`. Format as `FAC-{YYYY}-{NNNNN}`.
16. Create invoice draft: `INSERT INTO invoices (patient_id, doctor_id, quotation_id, treatment_plan_id, status='draft', invoice_number, subtotal, discount_amount, tax_amount, total, balance_due=total, amount_paid=0, created_by)`.
17. Create invoice_items from quotation_items: `INSERT INTO invoice_items (invoice_id, service_id, description, quantity, unit_price, subtotal, tax_exempt)` for each item.
18. Update quotation: set `invoice_id = created_invoice_id`, `treatment_plan_id = created_treatment_plan_id`.
19. Commit transaction.
20. Write audit log: action `approve`, resource `quotation`, PHI=yes, includes signature_hash (not the signature data itself).
21. Set idempotency key in Redis: `tenant:{tenant_id}:quotation_approve:{quotation_id}` = serialized success response. TTL = 300s.
22. Dispatch `quotation.approved` event to RabbitMQ (triggers patient notification).
23. Return 200 with summary of created resources.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | Valid UUID v4, must exist in tenant | La cotizacion no fue encontrada. |
| quotation_id (URL) | Valid UUID v4, must belong to patient | La cotizacion no fue encontrada. |
| terms_accepted | Must be boolean true | Debe aceptar los terminos para continuar. |
| signature_data | Non-empty base64 string, decoded <= 2MB, valid PNG header | La firma debe ser una imagen PNG en formato base64. |
| signed_by | Enum: patient_self, staff_on_behalf | Valor de firmante invalido. |
| signer_name | Required and max 200 chars if signed_by=staff_on_behalf | El nombre del firmante es requerido cuando el personal aprueba en nombre del paciente. |
| quotation.status | Must be draft or sent | La cotizacion no puede ser aprobada en su estado actual. |

**Business Rules:**

- Approval is irreversible. Once `status = 'approved'`, no endpoint allows reverting to draft or sent. This is required for legal compliance under Colombia Ley 527/1999 (digital signatures).
- The SHA-256 hash is computed from the raw base64 string of the signature image (not the decoded binary). This allows later verification without storing or decoding the image: `sha256(base64_string) == stored_hash`.
- The signature PNG image is stored in the `patient_signatures` table (stored as text column containing base64). For storage efficiency at scale, this should be migrated to S3 with reference stored in DB (post-MVP optimization).
- The auto-flow creates both treatment_plan and invoice_draft atomically in a single database transaction. If either fails, both are rolled back and the quotation status is not changed.
- The created invoice has `status = 'draft'`. It must be explicitly sent to the patient via B-05 (invoice-send). This allows staff to review the invoice before sending.
- The treatment plan items inherit status `pending` — the individual procedures have not yet been performed.
- `signed_by = 'staff_on_behalf'` is used when a receptionist or doctor approves the quotation while the patient is physically present and signs on a tablet or paper. The `signer_name` records which staff member witnessed/facilitated the signing.
- The IP address is extracted from the request headers (`X-Forwarded-For` if set by trusted proxy, else request.client.host). It is stored for legal traceability in the portal self-signing flow.
- A draft quotation can also be approved (bypassing the sent step). This handles the scenario where staff creates a quotation and the patient approves it immediately in person.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Quotation already approved (409) | Return 409; idempotency key also prevents double-approval |
| Quotation expired | Return 409 with current_status=expired |
| Quotation in draft status (not yet sent) | Valid — approval allowed on draft quotations |
| Retry within 5 minutes (same request) | Return 200 with cached success response (idempotent) |
| Patient account linked to patient_id but JWT role=doctor | Treated as staff role; signed_by should be staff_on_behalf |
| base64 data is valid but decodes to empty image (all white) | Valid — system does not validate signature content, only format and size |
| Transaction fails at treatment_plan creation | Full rollback; quotation status unchanged; signature deleted if stored before transaction |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `quotations`: UPDATE — `status = 'approved'`, `approved_at`, `approved_by`, `treatment_plan_id`, `invoice_id`
- `patient_signatures`: INSERT — digital signature with sha256_hash, signed_by, ip_address
- `treatment_plans`: INSERT — new active treatment plan from quotation
- `treatment_plan_items`: INSERT — N items (one per quotation_item)
- `invoices`: INSERT — new invoice draft with total from quotation
- `invoice_items`: INSERT — N items (one per quotation_item)
- `audit_logs`: INSERT — approval event with PHI flag

**Example transaction (SQLAlchemy):**
```python
async with session.begin():
    # Store signature
    sig = PatientSignature(
        quotation_id=quotation_id,
        patient_id=patient_id,
        signature_data=body.signature_data,
        sha256_hash=hashlib.sha256(body.signature_data.encode()).hexdigest(),
        signed_by=body.signed_by,
        signer_name=body.signer_name,
        ip_address=client_ip,
        signed_at=datetime.utcnow(),
        signed_by_user_id=user_id,
    )
    session.add(sig)
    await session.flush()

    # Update quotation
    await session.execute(
        update(Quotation)
        .where(Quotation.id == quotation_id)
        .values(status="approved", approved_at=datetime.utcnow(), approved_by=user_id)
    )

    # Create treatment plan
    tp_number = await get_next_treatment_plan_number(redis, tenant_id)
    tp = TreatmentPlan(
        patient_id=patient_id,
        doctor_id=quotation.doctor_id,
        status="active",
        plan_number=tp_number,
        source="quotation",
        quotation_id=quotation_id,
        created_by=user_id,
    )
    session.add(tp)
    await session.flush()

    for item in quotation_items:
        tp_item = TreatmentPlanItem(
            treatment_plan_id=tp.id,
            service_id=item.service_id,
            procedure_name=item.procedure_name,
            tooth_number=item.tooth_number,
            quantity=item.quantity,
            unit_price=item.unit_price,
            status="pending",
            sort_order=item.sort_order,
        )
        session.add(tp_item)

    # Create invoice draft
    inv_number = await get_next_invoice_number(redis, tenant_id)
    inv = Invoice(
        patient_id=patient_id,
        doctor_id=quotation.doctor_id,
        quotation_id=quotation_id,
        treatment_plan_id=tp.id,
        invoice_number=inv_number,
        status="draft",
        currency=tenant.currency,
        subtotal=quotation.subtotal,
        discount_amount=quotation.global_discount_amount,
        tax_amount=quotation.tax_amount,
        total=quotation.total,
        amount_paid=0,
        balance_due=quotation.total,
        created_by=user_id,
    )
    session.add(inv)
    await session.flush()

    # Update quotation with linked IDs
    await session.execute(
        update(Quotation)
        .where(Quotation.id == quotation_id)
        .values(treatment_plan_id=tp.id, invoice_id=inv.id)
    )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:quotation_approve:{quotation_id}`: SET — idempotency key, TTL 300s
- `tenant:{tenant_id}:billing:summary:*`: DELETE pattern — billing summary now stale
- `tenant:{tenant_id}:treatment_plans:patient:{patient_id}:*`: DELETE pattern — treatment plan list cache

**Cache TTL:** 300s for idempotency key

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | quotation.approved | { tenant_id, patient_id, quotation_id, quotation_number, treatment_plan_id, invoice_id, total } | After successful commit |
| notifications | invoice.draft_created | { tenant_id, patient_id, invoice_id, invoice_number } | After successful commit (alerts staff to review draft) |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** approve
- **Resource:** quotation
- **PHI involved:** Yes

**Audit log captures:** quotation_id, patient_id, user_id, signature_sha256_hash, signed_by, treatment_plan_id (created), invoice_id (created), total_amount, timestamp.

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | quotation_approved_confirmation | patient | After successful approval |
| in-app | quotation_approved | clinic staff (clinic_owner, receptionist) | After successful approval to notify of new treatment plan and invoice draft |

---

## Performance

### Expected Response Time
- **Target:** < 500ms
- **Maximum acceptable:** < 1500ms (includes PNG validation, SHA-256, multi-table transaction, two INCR operations)

### Caching Strategy
- **Strategy:** Idempotency cache for duplicate request protection; billing/treatment plan caches invalidated
- **Cache key:** `tenant:{tenant_id}:quotation_approve:{quotation_id}` (idempotency key)
- **TTL:** 300 seconds
- **Invalidation:** billing summary and treatment plan list caches invalidated

### Database Performance

**Queries executed:** 6-8 (quotation load, quotation items load, signature insert, quotation update, treatment_plan insert, N treatment_plan_items inserts, invoice insert, invoice_items inserts)

**Indexes required:**
- `quotations.(tenant_id, patient_id, id)` — COMPOSITE INDEX
- `patient_signatures.quotation_id` — INDEX
- `treatment_plans.(tenant_id, patient_id)` — COMPOSITE INDEX
- `invoices.quotation_id` — INDEX

**N+1 prevention:** All quotation items loaded in a single query before the transaction loop. Bulk inserts for treatment_plan_items and invoice_items within the transaction.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, quotation_id (URL) | Pydantic UUID validators | |
| signature_data | Base64 decode validation, PNG magic bytes check, size limit 2MB | Binary data validation |
| signed_by | Pydantic enum | Whitelist |
| signer_name | Pydantic strip(), max_length=200, bleach.clean | |
| terms_accepted | Pydantic bool, must be true | Strict boolean |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. Signature data stored as base64 text — not rendered in browser.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient identification (via patient_id), signature image (biometric data — high sensitivity), financial totals

**Audit requirement:** All write operations logged with PHI flag. SHA-256 hash logged (not the signature image itself) to preserve privacy in audit records.

### Legal Compliance

**Colombia Ley 527/1999 (Digital Signatures):** The signature workflow satisfies this law by:
1. Capturing a hand-drawn signature canvas as PNG
2. Computing SHA-256 hash for integrity verification
3. Recording IP address for portal signings (origin attribution)
4. Storing `signed_by` and timestamp for non-repudiation
5. Logging the approval event in the immutable audit log
6. Making the approval irreversible

---

## Testing

### Test Cases

#### Happy Path
1. Patient approves quotation via portal
   - **Given:** Authenticated patient, quotation with status=sent, 2 items, valid_until in future
   - **When:** POST approve with valid base64 PNG signature, terms_accepted=true, signed_by=patient_self
   - **Then:** 200 OK, quotation.status=approved, treatment_plan created with 2 items, invoice draft created, sha256_hash in response, notifications dispatched

2. Staff approves on behalf of patient present in clinic
   - **Given:** Authenticated receptionist, patient with sent quotation
   - **When:** POST approve with signed_by=staff_on_behalf, signer_name provided
   - **Then:** 200 OK, signer_name stored, same auto-flow result

3. Approve a draft quotation (not yet sent)
   - **Given:** Quotation with status=draft
   - **When:** POST approve
   - **Then:** 200 OK — draft quotations can be approved directly

4. Idempotent retry within 5 minutes
   - **Given:** Quotation successfully approved, same request retried
   - **When:** POST approve again within 5 min
   - **Then:** 200 OK, same success response from cache, no duplicate records created

#### Edge Cases
1. Quotation with item-level discounts and global discount
   - **Given:** Quotation with mixed discounts
   - **When:** Approve
   - **Then:** Invoice inherits exact subtotals and totals from quotation

2. Large signature image (near 2MB limit)
   - **Given:** Valid PNG signature, decoded size 1.9MB
   - **When:** POST approve
   - **Then:** 200 OK

#### Error Cases
1. Approve expired quotation
   - **Given:** Quotation with status=expired
   - **When:** POST approve
   - **Then:** 409 Conflict with current_status=expired

2. Approve already-approved quotation (outside idempotency window)
   - **Given:** Quotation with status=approved, idempotency key expired
   - **When:** POST approve
   - **Then:** 409 Conflict with current_status=approved

3. terms_accepted=false
   - **Given:** Valid body but terms_accepted=false
   - **When:** POST
   - **Then:** 400 Bad Request

4. Invalid PNG (JPEG sent as base64)
   - **Given:** Base64-encoded JPEG (not PNG)
   - **When:** POST
   - **Then:** 422 with invalid signature error

5. signature_data exceeds 2MB
   - **Given:** Base64 string that decodes to 3MB image
   - **When:** POST
   - **Then:** 422 with size limit error

6. Patient approving another patient's quotation
   - **Given:** Patient A authenticated, quotation_id belongs to Patient B
   - **When:** POST with Patient B's patient_id
   - **Then:** 403 Forbidden

7. signed_by=staff_on_behalf but no signer_name
   - **Given:** signed_by=staff_on_behalf, signer_name omitted
   - **When:** POST
   - **Then:** 422 with signer_name required error

### Test Data Requirements

**Users:** Patient (linked to patient record), receptionist, clinic_owner

**Patients:** Patient A with quotation in sent status; Patient B for cross-patient access test

**Quotations:** Sent quotation with 2 items; draft quotation; expired quotation; already-approved quotation

**Service Catalog:** Seeded services matching quotation items

### Mocking Strategy

- Redis: `fakeredis` for INCR (sequential numbers) and idempotency key simulation
- RabbitMQ: Mock publish; assert quotation.approved and invoice.draft_created events
- PNG validation: Use a minimal valid 1x1 PNG in base64 for happy path tests
- SHA-256: No mocking needed — deterministic computation

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST approve returns 200 with quotation, treatment_plan, invoice, and signature summary
- [ ] Quotation status transitions to approved (irreversible)
- [ ] Treatment plan created with correct items and status=active
- [ ] Invoice draft created with correct totals from quotation
- [ ] quotation.invoice_id and quotation.treatment_plan_id populated
- [ ] Signature stored with SHA-256 hash, signed_by, ip_address
- [ ] Approval is idempotent — duplicate within 5 minutes returns cached 200
- [ ] Expired/approved/rejected quotations return 409
- [ ] terms_accepted=false returns 400
- [ ] Invalid/oversized signature returns 422
- [ ] Patient can only approve own quotation (403 for others)
- [ ] Audit log written with PHI flag and signature_hash
- [ ] quotation.approved notification dispatched to RabbitMQ
- [ ] Billing summary cache invalidated
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Patient rejecting a quotation (separate endpoint)
- Sending the quotation to patient (see B-18 quotation-send.md)
- Getting quotation detail (see B-17 quotation-get.md)
- Sending the created invoice to patient (see B-05 invoice-send.md)
- Marking treatment plan items as completed (treatment-plans domain)
- Long-term signature storage migration to S3 (infrastructure concern, post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (signature schema + approval metadata)
- [x] All outputs defined (3 created/updated resources + signature summary)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (signature, status, terms)
- [x] Error cases enumerated
- [x] Auth requirements explicit (patient own, staff any)
- [x] Side effects listed (5 table writes + cache + RabbitMQ)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Auto-flow: Quotation → TreatmentPlan + Invoice in single transaction
- [x] Tenant schema isolation
- [x] Immutability enforced post-approval
- [x] Colombia Ley 527/1999 compliance documented

### Hook 3: Security & Privacy
- [x] Signature PNG validation (magic bytes + size)
- [x] SHA-256 hash stored (not raw in audit log)
- [x] Patient ownership enforced
- [x] PHI audit log
- [x] SQL injection prevented

### Hook 4: Performance & Scalability
- [x] Target < 500ms (multi-table transaction)
- [x] Idempotency key prevents double-submit
- [x] Atomic transaction (all-or-nothing)

### Hook 5: Observability
- [x] Audit log (PHI flag, signature hash, created resource IDs)
- [x] RabbitMQ job monitoring
- [x] Structured logging (tenant_id, patient_id, quotation_id)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data specified
- [x] Mocking strategy (fakeredis, RabbitMQ, minimal PNG)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
