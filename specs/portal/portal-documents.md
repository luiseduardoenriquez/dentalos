# PP-07 Portal Documents Spec

---

## Overview

**Feature:** List all documents available to a patient from the portal — X-rays, consent forms (signed), treatment plan PDFs, prescriptions, and clinical reports. Each document is served via a pre-signed S3 URL (valid 60 minutes). Documents are organized by type. Paginated.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), patients/photo-tooth.md (P-16), consents domain, prescriptions domain, billing domain, infra/multi-tenancy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Portal-scoped JWT required. All document queries filtered by patient_id from JWT sub — no cross-patient document access possible.

---

## Endpoint

```
GET /api/v1/portal/documents
```

**Rate Limiting:**
- 30 requests per minute per patient
- Pre-signed URL generation: 60 requests per minute per patient (URL refresh scenario)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| type | No | string | enum: xray, consent, treatment_plan, prescription, report, photo, all; default: all | Filter by document type | xray |
| cursor | No | string | Opaque cursor from previous response | Pagination cursor | eyJpZCI6... |
| limit | No | integer | 1-100; default: 20 | Results per page | 20 |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "items": [
    {
      "id": "uuid",
      "type": "string — enum: xray, consent, treatment_plan, prescription, report, photo",
      "title": "string — human-readable document name",
      "description": "string | null — optional description",
      "created_at": "string (ISO 8601 datetime)",
      "uploaded_by": "string — 'Dr. Name' or 'Clinica' (not staff user ID)",
      "file_size_bytes": "integer | null",
      "mime_type": "string — e.g. 'application/pdf', 'image/jpeg'",
      "download_url": "string — pre-signed S3 URL, valid 60 minutes",
      "thumbnail_url": "string | null — pre-signed URL for thumbnail if available (images/X-rays)",
      "related_to": {
        "type": "string | null — enum: appointment, treatment_plan, consent",
        "id": "uuid | null",
        "label": "string | null — human-readable reference, e.g. 'Cita 10-Mar-2026'"
      }
    }
  ],
  "pagination": {
    "cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  },
  "type_counts": {
    "xray": "integer",
    "consent": "integer",
    "treatment_plan": "integer",
    "prescription": "integer",
    "report": "integer",
    "photo": "integer"
  }
}
```

**Example:**
```json
{
  "items": [
    {
      "id": "f7a8b9c0-d1e2-3456-abcd-ef1234567890",
      "type": "consent",
      "title": "Consentimiento Informado - Endodoncia",
      "description": "Firmado el 17 de enero de 2026",
      "created_at": "2026-01-17T14:30:00-05:00",
      "uploaded_by": "Clinica Dental Sonrisa",
      "file_size_bytes": 245760,
      "mime_type": "application/pdf",
      "download_url": "https://s3.amazonaws.com/dentaios-docs/tn_abc123/consents/consent_c3d4.pdf?X-Amz-Expires=3600&...",
      "thumbnail_url": null,
      "related_to": {
        "type": "treatment_plan",
        "id": "c3d4e5f6-a1b2-7890-abcd-ef1234567890",
        "label": "Plan de Tratamiento Integral"
      }
    },
    {
      "id": "a8b9c0d1-e2f3-4567-bcde-f01234567890",
      "type": "xray",
      "title": "Radiografia Panoramica",
      "description": "Radiografia tomada el 15 de enero de 2026",
      "created_at": "2026-01-15T09:00:00-05:00",
      "uploaded_by": "Dr. Juan Martinez",
      "file_size_bytes": 2097152,
      "mime_type": "image/jpeg",
      "download_url": "https://s3.amazonaws.com/dentaios-docs/tn_abc123/xrays/pano_f47a.jpg?X-Amz-Expires=3600&...",
      "thumbnail_url": "https://s3.amazonaws.com/dentaios-docs/tn_abc123/xrays/thumbnails/pano_f47a_thumb.jpg?X-Amz-Expires=3600&...",
      "related_to": {
        "type": "appointment",
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "label": "Cita 15-Ene-2026"
      }
    }
  ],
  "pagination": {
    "cursor": null,
    "has_more": false,
    "total_count": 2
  },
  "type_counts": {
    "xray": 1,
    "consent": 1,
    "treatment_plan": 0,
    "prescription": 0,
    "report": 0,
    "photo": 0
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta no validos.",
  "details": {
    "type": ["Tipo de documento no valido. Opciones: xray, consent, treatment_plan, prescription, report, photo, all."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal" or role is not "patient".

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** S3 pre-signed URL generation failure or database error.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Validate query parameters (type enum, limit range, cursor format).
3. Resolve tenant schema; set `search_path`.
4. Query `patient_documents` view (unified view across multiple source tables):
   - X-rays from `patient_photos` WHERE type='xray' AND patient_id = :pid
   - Consents from `consent_forms` WHERE signed=true AND patient_id = :pid, link to S3 PDF
   - Treatment plans from `treatment_plans` WHERE patient_id = :pid AND approval_document_url IS NOT NULL
   - Prescriptions from `prescriptions` WHERE patient_id = :pid AND pdf_url IS NOT NULL
   - Reports from `clinical_reports` WHERE patient_id = :pid AND pdf_url IS NOT NULL
   - Photos from `patient_photos` WHERE type='photo' AND patient_id = :pid
5. Apply type filter (WHERE document_type = :type) if not 'all'.
6. Apply cursor-based pagination on `(created_at DESC, id DESC)`.
7. For each document, generate pre-signed S3 URL (60-minute TTL). If S3 object does not exist, skip URL generation (download_url = null with a note logged to Sentry — indicates async job not completed).
8. For images and X-rays, also generate thumbnail pre-signed URL if thumbnail exists.
9. Build `uploaded_by` string: map staff user_id to "Dr./Dra. Name" or "Clinica" (not expose user UUIDs).
10. Build `related_to` block from foreign key references.
11. Compute type_counts (COUNT per type, not paginated — always full counts).
12. Cache result.
13. Return 200.

**Document Source Mapping:**

| Document Type | Source Table | Condition |
|---------------|-------------|-----------|
| xray | patient_photos | type = 'xray' |
| photo | patient_photos | type = 'photo' |
| consent | consent_forms | signed = true, pdf_url IS NOT NULL |
| treatment_plan | treatment_plans | patient_approved = true, approval_document_url IS NOT NULL |
| prescription | prescriptions | pdf_url IS NOT NULL |
| report | clinical_reports | pdf_url IS NOT NULL |

**Business Rules:**

- Unsigned consent forms are NOT shown to the patient (they appear in PP-12 for signing, not here).
- Draft/unapproved treatment plan documents are NOT shown.
- Only documents with an existing S3 URL (PDF/image generated) are included in the list.
- Staff user IDs are never exposed; shown as "Dr. Name" or "Clinica".
- Pre-signed URLs expire in 60 minutes; client should refresh by calling this endpoint again.
- `type_counts` reflects ALL documents regardless of pagination; always computed across full result set.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No documents of any type | items=[], all type_counts=0 |
| PDF generation job still pending | Document excluded from list (pdf_url still null in source table) |
| Thumbnail does not exist for X-ray | thumbnail_url=null, download_url still valid |
| Document S3 object deleted externally | download_url generation fails; exclude document; log to Sentry |
| Patient has both xray and photo types | Both appear in type_counts; filtered correctly by type param |

---

## Side Effects

### Database Changes

None. Read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:documents:{type}:{cursor}:{limit}`: SET — TTL 5 minutes

**Cache TTL:** 5 minutes (pre-signed URLs are 60 min; 5 min cache is safe within URL validity window)

**Cache invalidation triggers:**
- New document added for patient (X-ray uploaded, consent signed, treatment plan approved, prescription created)

### Queue Jobs (RabbitMQ)

None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** patient_documents
- **PHI involved:** Yes (X-rays, clinical reports, prescriptions are clinical PHI)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms (with cache hit; S3 URL generation is fast but multiplied by item count)
- **Maximum acceptable:** < 500ms (cache miss; up to 20 S3 presign calls)

### Caching Strategy
- **Strategy:** Redis cache, patient-namespaced
- **Cache key:** `tenant:{tenant_id}:portal:patient:{patient_id}:documents:{type}:{cursor_hash}:{limit}`
- **TTL:** 5 minutes (safe window before 60-min pre-signed URL expiry)
- **Invalidation:** On new document creation for this patient

### Database Performance

**Queries executed:** 3-4 (UNION query across document source tables; type_counts aggregate; uploaded_by user name resolution)

**Indexes required:**
- `patient_photos.(patient_id, type, created_at)` — COMPOSITE INDEX
- `consent_forms.(patient_id, signed, created_at)` — COMPOSITE INDEX
- `treatment_plans.(patient_id, patient_approved, created_at)` — COMPOSITE INDEX
- `prescriptions.(patient_id, created_at)` — COMPOSITE INDEX

**N+1 prevention:** UNION query fetches all document types in one pass. S3 presign calls batched using asyncio.gather per page.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on created_at + id across UNION result)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| type | Pydantic Literal enum | Strict allowlist |
| cursor | Base64 decode + validation | Malformed returns 400 |
| limit | Pydantic int ge=1, le=100 | Bounded integer |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries (UNION constructed programmatically).

### XSS Prevention

**Output encoding:** All string outputs escaped by Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Document titles (may reveal diagnoses), S3 URLs (time-limited, access-controlled), X-ray images, clinical report content

**Audit requirement:** All PHI document list accesses logged (Resolución 1888 compliance for clinical record access)

---

## Testing

### Test Cases

#### Happy Path
1. Patient fetches all documents (multiple types)
   - **Given:** Patient with 1 xray, 1 signed consent, 1 prescription
   - **When:** GET /api/v1/portal/documents
   - **Then:** 200 OK, 3 items, type_counts accurate, download_url populated for each

2. Filter by type=xray
   - **Given:** Patient with 2 xrays and 1 consent
   - **When:** GET /api/v1/portal/documents?type=xray
   - **Then:** 2 xray items, type_counts still shows all types

3. Thumbnail URL for X-ray
   - **Given:** X-ray document with thumbnail generated
   - **When:** GET /api/v1/portal/documents?type=xray
   - **Then:** thumbnail_url populated; download_url also populated

4. Unsigned consent not shown
   - **Given:** Consent form exists but signed=false
   - **When:** GET /api/v1/portal/documents
   - **Then:** Unsigned consent NOT in items list

#### Edge Cases
1. No documents at all
   - **Given:** New patient with no documents
   - **When:** GET /api/v1/portal/documents
   - **Then:** items=[], all type_counts=0, pagination.total_count=0

2. PDF still being generated
   - **Given:** Prescription created 10 seconds ago; pdf_url still null
   - **When:** GET /api/v1/portal/documents?type=prescription
   - **Then:** Prescription NOT in list (excluded until pdf_url is set)

3. X-ray without thumbnail
   - **Given:** X-ray uploaded without thumbnail generation
   - **When:** GET /api/v1/portal/documents?type=xray
   - **Then:** thumbnail_url=null; download_url valid

#### Error Cases
1. Invalid type filter
   - **Given:** Patient authenticated
   - **When:** GET /api/v1/portal/documents?type=invoice
   - **Then:** 400 Bad Request

2. Staff token
   - **Given:** Receptionist JWT (scope=staff)
   - **When:** GET /api/v1/portal/documents
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Patient with portal_access=true; documents across all 6 types in various states.

**Patients/Entities:** S3 mock with existing objects for documents; consent form in both signed and unsigned states.

### Mocking Strategy

- Redis: fakeredis
- S3: moto (simulate presign calls, test missing object handling)
- asyncio.gather: verify batch presign calls

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient sees all their documents across 6 types
- [ ] Unsigned consent forms excluded from list
- [ ] Draft treatment plan documents excluded
- [ ] Pre-signed S3 URLs generated with 60-minute TTL
- [ ] Thumbnail URLs generated for image types (xray, photo)
- [ ] type_counts reflect full count independent of pagination
- [ ] uploaded_by shows "Dr. Name" or "Clinica" (not staff UUID)
- [ ] Type filter works correctly
- [ ] Cursor-based pagination works (20 default, 100 max)
- [ ] PHI access audited
- [ ] Cache 5 minutes; invalidated on new document added
- [ ] Staff JWT returns 403
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms cache hit, < 500ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Uploading documents from the portal (clinic staff function only)
- Signing unsigned consent forms (see PP-12 portal-consent-sign.md)
- Viewing clinical record details or odontogram (see PP-13)
- DICOM viewer for X-rays (future enhancement)
- Document sharing with external parties

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization defined
- [x] SQL injection prevented
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical PHI access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized (UNION with indexes; batch S3 presign)
- [x] Pagination applied (cursor-based)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry for missing S3 objects)
- [x] Queue job monitoring (N/A for read)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (moto for S3, fakeredis)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
