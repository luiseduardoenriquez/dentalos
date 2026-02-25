# P-14 Patient Document Delete Spec

---

## Overview

**Feature:** Delete a document from a patient record. Removes both the S3 object and the database record. Signed consent PDFs cannot be deleted (returns 403). The deletion is audit logged with full file metadata for traceability.

**Domain:** patients

**Priority:** High

**Dependencies:** P-12 (patient-documents.md), P-13 (patient-document-upload.md), infra/storage-architecture.md, consents

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner and doctor can delete documents. Assistants and receptionists cannot delete. Signed consent documents are protected from deletion regardless of role.

---

## Endpoint

```
DELETE /api/v1/patients/{patient_id}/documents/{doc_id}
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
| patient_id | Yes | UUID | Valid UUIDv4 | Patient identifier | 550e8400-e29b-41d4-a716-446655440000 |
| doc_id | Yes | UUID | Valid UUIDv4 | Document identifier | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

None.

### Request Body Schema

N/A — DELETE request with no body.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "message": "string",
  "deleted_document": {
    "id": "uuid",
    "file_name": "string",
    "document_type": "string",
    "file_size_bytes": "integer",
    "mime_type": "string",
    "deleted_at": "ISO 8601 datetime"
  }
}
```

**Example:**
```json
{
  "message": "Documento eliminado exitosamente.",
  "deleted_document": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "file_name": "radiografia_periapical_36.jpg",
    "document_type": "xray",
    "file_size_bytes": 2456789,
    "mime_type": "image/jpeg",
    "deleted_at": "2025-11-15T16:00:00-05:00"
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not clinic_owner or doctor, OR the document is a signed consent PDF.

**Role-based 403:**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para eliminar documentos de pacientes."
}
```

**Signed consent 403:**
```json
{
  "error": "forbidden",
  "message": "No se puede eliminar un consentimiento firmado. Los consentimientos firmados son registros legales protegidos.",
  "details": {
    "document_type": "consent",
    "reason": "signed_consent_protected"
  }
}
```

#### 404 Not Found
**When:** patient_id or doc_id does not exist, patient is inactive, or document does not belong to the specified patient.

```json
{
  "error": "not_found",
  "message": "Documento no encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** S3 deletion fails but DB record is already marked for deletion.

```json
{
  "error": "internal_error",
  "message": "Error al eliminar el archivo del almacenamiento. El equipo de soporte ha sido notificado."
}
```

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract tenant context; verify role in [clinic_owner, doctor].
2. Validate patient_id and doc_id UUID format via Pydantic.
3. Set search_path to tenant schema.
4. Load patient from DB; return 404 if not found or is_active=false.
5. Load document from `patient_documents` WHERE id=doc_id AND patient_id=patient_id; return 404 if not found.
6. Check if document is a signed consent:
   a. If document_type='consent': query `consents` table for any consent with `signed_pdf_path` matching this document's `file_path` and `status='signed'`.
   b. If a matching signed consent exists, return 403 with signed_consent_protected error.
7. Capture full document metadata for audit log BEFORE deletion.
8. Delete file from S3 at the document's `file_path`.
9. If S3 deletion fails: log error, raise alert, return 500 (do NOT delete DB record if S3 delete fails).
10. DELETE record from `patient_documents` table.
11. Update storage usage cache.
12. Write audit log entry: action=delete, resource_type=patient_document, PHI=true, old_value contains full file metadata.
13. Return 200 with deleted document metadata.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUIDv4 | "El ID del paciente no es un UUID valido." |
| doc_id | Valid UUIDv4 | "El ID del documento no es un UUID valido." |

**Business Rules:**

- Signed consent PDFs are legally protected records and MUST NOT be deleted. This is enforced by cross-referencing the `consents` table.
- S3 deletion and DB deletion are NOT wrapped in a single transaction (S3 is not transactional). The order is: S3 first, then DB. If S3 fails, the DB record is preserved for retry.
- The audit log entry captures the complete file metadata (file_name, document_type, file_size_bytes, mime_type, file_path, uploaded_by, created_at) so that the deletion is fully traceable.
- The actual file content is not recoverable after deletion (hard delete from S3).
- Voided consents (status='voided') CAN be deleted since they are no longer legally binding.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Document exists in DB but S3 object already missing | Log warning; delete DB record; return 200 (idempotent cleanup). |
| Document is a consent but unsigned (draft/voided) | Allowed to delete. Only signed consents are protected. |
| doc_id exists but belongs to a different patient | Return 404 (patient_id mismatch). |
| Concurrent delete of same document | First request succeeds; second returns 404 (already deleted). |
| Doctor deletes a document uploaded by another doctor | Allowed. Role check is sufficient; no ownership restriction. |
| S3 returns 500 during deletion | Return 500; DB record preserved; alert raised for manual intervention. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `patient_documents`: DELETE — document record removed.
- `audit_log`: INSERT — deletion audit entry with full metadata.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:documents:count`: DELETE — document count changed.
- `tenant:{tenant_id}:storage_used`: DELETE — storage usage decreased.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes

- **Action:** delete
- **Resource:** patient_document
- **PHI involved:** Yes
- **old_value:** Complete file metadata: `{ "id": "...", "file_name": "...", "document_type": "xray", "file_size_bytes": 2456789, "mime_type": "image/jpeg", "file_path": "...", "uploaded_by": "...", "created_at": "..." }`

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 500ms
- **Maximum acceptable:** < 1000ms

### Caching Strategy
- **Strategy:** Cache invalidation for document counts and storage usage.
- **Cache key:** Document count + storage usage keys.
- **TTL:** N/A
- **Invalidation:** Immediate on successful deletion.

### Database Performance

**Queries executed:** 3-4 (load patient, load document, check consent status, delete record)

**Indexes required:**
- `patient_documents.patient_id` — INDEX (existing: `idx_patient_documents_patient`)
- `patient_documents.id` — PRIMARY KEY (existing)
- `consents.signed_pdf_path` — INDEX (add if not exists, for consent protection check)

**N+1 prevention:** Not applicable (single document operation).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID |
| doc_id | Pydantic UUID validator | Rejects non-UUID |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** The deleted document may contain PHI (X-rays, lab results). File metadata is preserved in the audit log.

**Audit requirement:** All deletions logged with complete file metadata for traceability.

---

## Testing

### Test Cases

#### Happy Path
1. Delete an X-ray document
   - **Given:** Patient with an X-ray document, doctor user.
   - **When:** DELETE /api/v1/patients/{patient_id}/documents/{doc_id}
   - **Then:** Returns 200, S3 object deleted, DB record removed, audit log created.

2. Delete a draft consent document
   - **Given:** Patient with an unsigned (draft) consent document.
   - **When:** DELETE request.
   - **Then:** Returns 200 (draft consents are deletable).

3. Delete a voided consent document
   - **Given:** Patient with a voided consent document.
   - **When:** DELETE request.
   - **Then:** Returns 200 (voided consents are deletable).

#### Edge Cases
1. Document in DB but missing from S3
   - **Given:** DB record exists but S3 object was already deleted externally.
   - **When:** DELETE request.
   - **Then:** Returns 200, DB record cleaned up, warning logged.

2. Concurrent delete
   - **Given:** Two simultaneous DELETE requests for the same document.
   - **When:** Both execute.
   - **Then:** First returns 200, second returns 404.

#### Error Cases
1. Delete signed consent
   - **Given:** Patient with a signed consent PDF (consents.status='signed').
   - **When:** DELETE request.
   - **Then:** Returns 403 with signed_consent_protected error.

2. Document belongs to different patient
   - **Given:** Valid doc_id but mismatched patient_id.
   - **When:** DELETE request.
   - **Then:** Returns 404.

3. Assistant role
   - **Given:** Assistant user.
   - **When:** DELETE request.
   - **Then:** Returns 403.

4. Receptionist role
   - **Given:** Receptionist user.
   - **When:** DELETE request.
   - **Then:** Returns 403.

5. Non-existent document
   - **Given:** Random UUID for doc_id.
   - **When:** DELETE request.
   - **Then:** Returns 404.

6. S3 deletion failure
   - **Given:** S3 returns error during deletion.
   - **When:** DELETE request.
   - **Then:** Returns 500, DB record preserved.

### Test Data Requirements

**Users:** 1 clinic_owner, 1 doctor, 1 assistant, 1 receptionist (for role tests).

**Patients/Entities:** 1 patient with: 1 xray document, 1 signed consent document, 1 draft consent document, 1 voided consent document, 1 photo document.

### Mocking Strategy

- S3: Mock delete_object; simulate success and failure scenarios.
- Database: Use test tenant schema with seeded documents and consent records.
- Audit log: Verify INSERT with complete metadata.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Document deleted from both S3 and database on success
- [ ] Signed consent PDFs return 403 (protected from deletion)
- [ ] Unsigned (draft) and voided consents CAN be deleted
- [ ] Audit log captures complete file metadata on deletion
- [ ] S3 failure prevents DB deletion (consistency preserved)
- [ ] Only clinic_owner and doctor roles can delete
- [ ] Document-patient ownership verified (cross-patient access prevented)
- [ ] Storage usage cache invalidated
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Soft-delete / recycle bin for documents (hard delete only in v1).
- Bulk document deletion (delete one at a time).
- Document archival to cold storage (future cost optimization).
- Automatic cleanup of orphaned S3 objects (covered in infra maintenance tasks).

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
- [x] Audit trail for document deletions

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

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
