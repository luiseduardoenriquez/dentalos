# Prescription PDF Spec

---

## Overview

**Feature:** Generate and download a prescription PDF formatted like a physical Colombian prescription pad (receta medica). Includes clinic header with logo, full doctor credentials (including Tarjeta Profesional), patient information, and numbered Rp/ (recipe) medication list. Conforms to Colombian prescription format standards.

**Domain:** prescriptions

**Priority:** Medium

**Dependencies:** RX-01 (prescription-create.md), RX-02 (prescription-get.md), auth/authentication-rules.md, infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, patient (own prescriptions only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients can only download their own prescription PDFs.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/prescriptions/{rx_id}/pdf
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
| patient_id | Yes | string (UUID) | Valid UUID v4, must belong to tenant | Patient owning the prescription | f47ac10b-58cc-4372-a567-0e02b2c3d479 |
| rx_id | Yes | string (UUID) | Valid UUID v4, must belong to patient | Prescription to generate PDF for | rx1a2b3c-0000-4000-8000-000000000010 |

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
Content-Disposition: attachment; filename="receta_{rx_id_short}_{date}.pdf"
Content-Length: {bytes}
```

**Body:** Binary PDF file

**PDF Layout (Colombian Prescription Pad Format):**
```
┌─────────────────────────────────────────────────────────┐
│  [Clinic Logo]   CLINICA DENTAL SONRISA                 │
│                  Cra 7 # 45-10, Bogota, Colombia        │
│                  Tel: +571 3456789                      │
├─────────────────────────────────────────────────────────┤
│  Dr. Juan Carlos Perez Rodriguez                        │
│  Especialidad: Cirugia Oral y Maxilofacial              │
│  Tarjeta Profesional: MP-12345-COL                      │
├─────────────────────────────────────────────────────────┤
│  Paciente: Maria Garcia Lopez                           │
│  Cedula: 1020304050     Edad: 35 anos                   │
│  Fecha: 24/02/2026     Ciudad: Bogota                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Rp/                                                    │
│                                                         │
│  1. Amoxicilina 500mg                                   │
│     Via: Oral                                           │
│     Frecuencia: Cada 8 horas                            │
│     Duracion: 7 dias                                    │
│     Indicaciones: Tomar con los alimentos               │
│                                                         │
│  2. Clorhexidina 0.12% Enjuague Bucal 15ml             │
│     Via: Oral                                           │
│     Frecuencia: Dos veces al dia                        │
│     Duracion: 10 dias                                   │
│     Indicaciones: Enjuagarse 30 segundos...             │
│                                                         │
│  Observaciones: Post extraccion quirurgica diente 48.   │
│                                                         │
│  ____________________________                           │
│  Firma del Medico                                       │
│  [embedded signature image if available]                │
│                                                         │
│  ID Prescripcion: rx1a2b3c  |  Pagina 1 de 1          │
└─────────────────────────────────────────────────────────┘
```

### Error Responses

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role not allowed, or patient attempting to access another patient's prescription PDF.

**Example (JSON body):**
```json
{
  "error": "forbidden",
  "message": "No tiene permisos para descargar esta prescripcion."
}
```

#### 404 Not Found
**When:** `patient_id` or `rx_id` not found, or prescription does not belong to specified patient.

**Example (JSON body):**
```json
{
  "error": "not_found",
  "message": "Prescripcion no encontrada."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** PDF generation failure (template rendering error, missing required data).

---

## Business Logic

**Step-by-step process:**

1. Validate path parameters as valid UUIDs.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Check user role:
   - If `patient`: verify JWT sub matches `portal_user_id` for `patient_id`. Return 403 if mismatch.
   - If clinic staff: allow any patient in tenant.
4. Check object storage: look for cached PDF at `s3://bucket/tenant/{tenant_id}/prescriptions/{rx_id}/rx_{rx_id}.pdf`. If exists, stream directly (prescriptions are immutable).
5. If no cached PDF: fetch prescription record with all medications (JOIN).
6. Verify `prescription.patient_id == patient_id`. Return 404 if mismatch.
7. Fetch patient record for: `first_name`, `last_name`, `document_type`, `document_number`, `birthdate` (to compute age).
8. Fetch tenant profile: `clinic_name`, `address`, `phone`, `city`, `logo_url`.
9. Check if the prescribing doctor has a digital signature stored in `digital_signatures` table (linked by `user_id`). If found, embed the signature image in the PDF signature block.
10. Compose PDF using prescription pad template:
    - Page size: A4
    - Clinic header (logo + name + address + phone)
    - Doctor block (full name + specialty + Tarjeta Profesional)
    - Patient block (name + cedula/document + age + prescription date + city)
    - "Rp/" header
    - Numbered medication list (1 to N) with: name, dosage, route, frequency, duration, instructions
    - Notes block (if present)
    - Signature block (embedded PNG if available, or blank line)
    - Footer: prescription ID (last 8 chars), page number, clinic name
11. Upload generated PDF to object storage for future cache hits.
12. Write audit log entry.
13. Stream PDF as response.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | El identificador del paciente no es valido. |
| rx_id | Valid UUID v4 | El identificador de la prescripcion no es valido. |

**Business Rules:**

- Prescriptions are immutable. Once a PDF is generated and cached in S3, all future requests serve the cached version without re-generation.
- The doctor's digital signature (if available in `digital_signatures`) is embedded in the PDF signature block. This is the same PNG image used in consent signing.
- If no doctor signature is available, a blank signature line is rendered with the doctor's name printed below.
- The prescription date shown is `prescribed_at` formatted as `DD/MM/YYYY` in Colombia timezone (America/Bogota).
- `doctor_license` shown on PDF is the snapshot stored on the prescription record at creation time (not current profile).
- The PDF is not watermarked (prescriptions are always valid documents — no draft state).
- Tenant logo fetched from object storage; if unavailable, clinic name rendered as bold text.
- All text is in Spanish.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor has no digital signature stored | Blank signature line rendered with doctor name printed |
| Prescription has 10 medications | All 10 listed on PDF (may span to page 2) |
| Tenant has no logo | Clinic name rendered as text in header; no broken image placeholder |
| Prescription has no notes | Notes block omitted from PDF |
| Patient is very young (< 1 year) | Age displayed as "X meses" (months) |
| S3 cache hit | PDF streamed directly from S3; no re-generation |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None (read-only operation; S3 write is to object storage, not DB)

### Cache Operations

**Cache keys affected:**
- `s3://bucket/tenant/{tenant_id}/prescriptions/{rx_id}/rx_{rx_id}.pdf`: SET — uploaded to object storage after first generation

**Cache TTL:** Indefinite (prescriptions are immutable)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None (PDF generated synchronously on first request)

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** prescription_pdf
- **PHI involved:** Yes (PDF contains medications, patient name, cedula — health data)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (S3 cache hit)
- **Maximum acceptable:** < 2000ms (first-time PDF generation)

### Caching Strategy
- **Strategy:** S3 object storage (generated once per prescription, served indefinitely)
- **Cache key:** `s3://bucket/tenant/{tenant_id}/prescriptions/{rx_id}/rx_{rx_id}.pdf`
- **TTL:** Indefinite (prescriptions are immutable — no need to invalidate)
- **Invalidation:** Not applicable

### Database Performance

**Queries executed:** 2–3 (prescription + medications JOIN, patient lookup, optional doctor signature lookup)

**Indexes required:**
- `{tenant}.prescriptions.(patient_id, id)` — COMPOSITE INDEX (already required)
- `{tenant}.prescription_medications.prescription_id` — INDEX (already required)
- `{tenant}.digital_signatures.(user_id, signer_type)` — INDEX (for doctor signature lookup)

**N+1 prevention:** Medications fetched via single JOIN; doctor signature fetched in single query.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Reject malformed path params |
| rx_id | Pydantic UUID validator | Reject malformed path params |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** PDF is binary output — XSS not applicable. All text content written to PDF is escaped by the PDF rendering engine.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient full name, cedula/document, age, all medications (health data), diagnosis reference (if present)

**Audit requirement:** All access logged (PDF download is a high-value PHI access event).

---

## Testing

### Test Cases

#### Happy Path
1. Download prescription PDF (first generation)
   - **Given:** Authenticated doctor, prescription with 2 medications, no S3 cache
   - **When:** GET /api/v1/patients/{patient_id}/prescriptions/{rx_id}/pdf
   - **Then:** 200 OK, application/pdf response, PDF contains clinic header, doctor info with Tarjeta Profesional, patient info, Rp/ section with 2 numbered medications

2. Download prescription PDF (S3 cache hit)
   - **Given:** PDF already exists in S3 from prior request
   - **When:** GET (second call)
   - **Then:** 200 OK, streamed from S3 without re-generation, response in < 100ms

3. PDF includes doctor digital signature
   - **Given:** Prescribing doctor has a digital signature stored in `digital_signatures`
   - **When:** GET
   - **Then:** 200 OK, signature PNG embedded in doctor signature block

4. Patient downloads own prescription PDF
   - **Given:** Patient with portal access
   - **When:** GET (patient JWT)
   - **Then:** 200 OK, PDF returned with full prescription content

5. Prescription with no notes
   - **Given:** Prescription was created without `notes` field
   - **When:** GET
   - **Then:** 200 OK, PDF has no "Observaciones" section

#### Edge Cases
1. Prescription with 10 medications
   - **Given:** Prescription with maximum 10 medications
   - **When:** GET
   - **Then:** 200 OK, all 10 medications listed in Rp/ section, may span page 2

2. Doctor with no digital signature
   - **Given:** Prescribing doctor has no signature in `digital_signatures`
   - **When:** GET
   - **Then:** 200 OK, PDF has blank signature line with doctor name printed below

3. Tenant with no logo
   - **Given:** Tenant profile has no logo URL
   - **When:** GET
   - **Then:** 200 OK, PDF header shows clinic name as bold text

4. Doctor license is `[NO REGISTRADO]`
   - **Given:** Prescription was created when doctor had no tarjeta_profesional
   - **When:** GET
   - **Then:** 200 OK, PDF shows "Tarjeta Profesional: [NO REGISTRADO]"

#### Error Cases
1. Patient accessing another patient's prescription PDF
   - **Given:** Patient A's JWT, rx_id belonging to Patient B
   - **When:** GET
   - **Then:** 403 Forbidden (JSON response, not PDF)

2. Prescription not found
   - **Given:** Valid UUID not matching any prescription
   - **When:** GET
   - **Then:** 404 Not Found (JSON response)

3. Prescription belongs to different patient
   - **Given:** rx_id exists but belongs to different patient_id
   - **When:** GET
   - **Then:** 404 Not Found (JSON response)

4. Assistant role requesting PDF
   - **Given:** User with assistant role
   - **When:** GET
   - **Then:** 200 OK — assistants are in allowed roles

### Test Data Requirements

**Users:** doctor (with and without digital signature), assistant, clinic_owner, patient with portal access; patient without portal access

**Patients/Entities:** Prescription with 1 medication; prescription with 10 medications; prescription with all optional fields; prescription with no notes; tenant with and without logo.

### Mocking Strategy

- S3 / object storage: Mock GET (cache hit), mock PUT (first generation upload)
- PDF generation engine: Integration test with real engine (Playwright) in test environment; mock in unit tests
- Doctor signature lookup: Seeded test fixture with and without digital signature record

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] PDF generated with correct Colombian prescription pad layout (clinic header, doctor block, patient block, Rp/ section)
- [ ] Doctor's Tarjeta Profesional number displayed on PDF
- [ ] All medications listed with sequential numbering (1, 2, 3...)
- [ ] Doctor digital signature embedded when available; blank line when not
- [ ] Tenant logo included in header when available; text fallback when not
- [ ] Prescription date formatted as DD/MM/YYYY (Colombia timezone)
- [ ] PDF cached in S3 after first generation; subsequent requests served from cache
- [ ] Patient can only download their own prescription PDFs (403 otherwise)
- [ ] Audit log entry written for every PDF download
- [ ] Content-Disposition header set with correct filename format
- [ ] All test cases pass
- [ ] Performance target met (< 100ms S3 hit, < 2s first generation)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Sending the PDF to patient via email (separate notification workflow)
- PDF merging or combining multiple prescriptions into one file
- Electronic prescription submission to pharmacies
- QR code embedding for pharmacy verification
- Controlled substance DEA number display

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
- [x] Response time target defined (S3 cache vs. first-generation)
- [x] Caching strategy stated (S3 indefinite for immutable prescriptions)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A — single document)

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
