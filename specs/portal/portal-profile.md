# PP-02 Portal Profile Spec

---

## Overview

**Feature:** Return the authenticated patient's own profile from the portal. Provides a limited, patient-safe view of their data — clinical notes, internal flags, full billing history, and staff-only fields are excluded. Read-only endpoint.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), I-01 (multi-tenancy.md), P-01 (patient-create.md), infra/auth-rules.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT (portal JWT contains tenant_id claim)
- **Special rules:** Portal-scoped JWT required (scope=portal). Clinic staff JWT tokens with role=doctor/receptionist etc. are rejected even if they pass role check — scope mismatch middleware enforces this. Patient can only see their own record (enforced at query level by filtering on patient_id from JWT sub claim).

---

## Endpoint

```
GET /api/v1/portal/me
```

**Rate Limiting:**
- 60 requests per minute per patient (generous; this is the primary portal landing data)
- Inherits global portal rate limit

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal, role=patient) | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "first_name": "string",
  "last_name": "string",
  "document_type": "string — enum: cedula, curp, rut, passport, other",
  "document_number": "string",
  "birthdate": "string (ISO 8601 date)",
  "gender": "string — enum: male, female, other",
  "phone": "string | null",
  "email": "string | null",
  "phone_secondary": "string | null",
  "address": "string | null",
  "city": "string | null",
  "state_province": "string | null",
  "emergency_contact_name": "string | null",
  "emergency_contact_phone": "string | null",
  "insurance_provider": "string | null",
  "insurance_policy_number": "string | null",
  "blood_type": "string | null",
  "allergies": "string[]",
  "chronic_conditions": "string[]",
  "portal_access": "boolean — always true here",
  "clinic": {
    "name": "string",
    "phone": "string | null",
    "address": "string | null",
    "logo_url": "string | null"
  },
  "outstanding_balance": "number (decimal) — total unpaid invoices in COP",
  "next_appointment": {
    "id": "uuid | null",
    "scheduled_at": "string (ISO 8601 datetime) | null",
    "doctor_name": "string | null",
    "appointment_type": "string | null"
  },
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "first_name": "Maria",
  "last_name": "Garcia Lopez",
  "document_type": "cedula",
  "document_number": "1020304050",
  "birthdate": "1990-05-15",
  "gender": "female",
  "phone": "+573001234567",
  "email": "maria.garcia@email.com",
  "phone_secondary": null,
  "address": "Calle 80 # 10-20, Apto 301",
  "city": "Bogota",
  "state_province": "Cundinamarca",
  "emergency_contact_name": "Carlos Garcia",
  "emergency_contact_phone": "+573009876543",
  "insurance_provider": "Sura EPS",
  "insurance_policy_number": "EPS-12345",
  "blood_type": "O+",
  "allergies": ["penicilina", "latex"],
  "chronic_conditions": ["diabetes tipo 2"],
  "portal_access": true,
  "clinic": {
    "name": "Clinica Dental Sonrisa",
    "phone": "+5716001234",
    "address": "Av. El Dorado # 68B-31, Bogota",
    "logo_url": "https://cdn.dentaios.com/tenants/tn_abc123/logo.png"
  },
  "outstanding_balance": 150000.00,
  "next_appointment": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "scheduled_at": "2026-03-10T10:00:00-05:00",
    "doctor_name": "Dr. Juan Martinez",
    "appointment_type": "Limpieza dental"
  },
  "created_at": "2025-08-01T09:15:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Missing, expired, or invalid JWT token.

**Example:**
```json
{
  "error": "unauthorized",
  "message": "Token de autenticacion invalido o expirado."
}
```

#### 403 Forbidden
**When:** JWT scope is not "portal" (staff JWT used on portal endpoint), or role is not "patient".

**Example:**
```json
{
  "error": "forbidden",
  "message": "Acceso no autorizado al portal de pacientes."
}
```

#### 404 Not Found
**When:** Patient record not found in tenant (should not occur in normal flow; indicates data integrity issue).

**Example:**
```json
{
  "error": "patient_not_found",
  "message": "No se encontro el registro del paciente."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate Authorization header: extract and verify portal JWT signature and expiry.
2. Check JWT claims: `scope` must be "portal", `role` must be "patient". Reject if either fails.
3. Resolve tenant from `tenant_id` JWT claim; set `search_path` to tenant schema.
4. Extract `patient_id` from JWT `sub` claim.
5. Fetch patient record using patient_id — single query with LEFT JOINs for clinic info and next appointment:
   - `patients` table filtered strictly by `id = patient_id` (no other filter needed; ownership is enforced by JWT sub).
   - JOIN `public.tenants` for clinic name, phone, address, logo.
   - Subquery for `next_appointment`: first future confirmed appointment ordered by scheduled_at ASC.
6. Fetch outstanding balance: `SUM(invoices.total_amount - invoices.paid_amount) WHERE status IN ('pending', 'partial') AND patient_id = :pid`.
7. Filter response fields: exclude `notes`, `referral_source`, `no_show_count`, `is_active`, `created_by`, and any staff-internal fields.
8. Cache result in Redis with short TTL.
9. Return 200 with filtered profile.

**Excluded Fields (never returned to patient):**
- `notes` — internal clinical notes by staff
- `referral_source` — internal marketing field
- `no_show_count` — internal operational metric
- `is_active` — internal status flag
- `created_by` — internal user reference
- Full invoice details (only aggregate balance returned here; full list in PP-06)
- `portal_credentials.password_hash`, `failed_attempts`, `last_login_at`

**Business Rules:**

- Patient data ownership is enforced at query level: `WHERE patients.id = {jwt.sub}`. Middleware alone is not sufficient.
- Clinic logo URL is served as a CDN-signed URL if the tenant has uploaded a logo; null otherwise.
- Outstanding balance is computed at query time (not cached separately); included here for dashboard display.
- Next appointment shows only the single closest future appointment; full list available via PP-03.
- If patient has no future appointments, `next_appointment` object has all null values (not absent).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no upcoming appointments | next_appointment object returned with all null fields |
| Patient has zero outstanding balance | outstanding_balance = 0.00 |
| Tenant has no logo uploaded | clinic.logo_url = null |
| Patient's allergies array is empty | allergies = [] (empty array, not null) |
| JWT sub does not match any patient | Return 404 (data integrity alert logged) |

---

## Side Effects

### Database Changes

None. Read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:profile`: SET — cached patient profile response, TTL 5 minutes

**Cache TTL:** 5 minutes (short enough to reflect staff updates promptly)

**Cache invalidation triggers:**
- Patient record updated by staff (P-02 patient-update.md)
- Portal credentials updated
- New appointment booked or cancelled

### Queue Jobs (RabbitMQ)

None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** portal_patient_profile
- **PHI involved:** Yes (patient reads their own PHI; logged for compliance with Resolución 1888)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (with cache hit)
- **Maximum acceptable:** < 200ms (cache miss, DB query)

### Caching Strategy
- **Strategy:** Redis cache, tenant-namespaced, patient-specific
- **Cache key:** `tenant:{tenant_id}:portal:patient:{patient_id}:profile`
- **TTL:** 5 minutes
- **Invalidation:** On patient record update, appointment change, invoice payment

### Database Performance

**Queries executed:** 2 (patient + clinic JOIN, outstanding balance aggregate)

**Indexes required:**
- `patients.id` — PRIMARY KEY (already exists)
- `appointments.patient_id, appointments.scheduled_at, appointments.status` — COMPOSITE INDEX (for next appointment subquery)
- `invoices.patient_id, invoices.status` — COMPOSITE INDEX (for balance aggregate)

**N+1 prevention:** Single JOIN query for patient + clinic; separate aggregate query for balance. Both executed in parallel via asyncio.gather.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| JWT token | Verified signature + expiry + claims | No user-supplied query params |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. Patient_id from JWT (validated UUID) used as parameter.

### XSS Prevention

**Output encoding:** All string outputs escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** first_name, last_name, document_number, birthdate, phone, email, address, emergency_contact_name, emergency_contact_phone, insurance_provider, insurance_policy_number, blood_type, allergies, chronic_conditions

**Audit requirement:** All access logged (patient self-access of PHI logged per Resolución 1888 requirements)

---

## Testing

### Test Cases

#### Happy Path
1. Patient fetches own profile with all fields populated
   - **Given:** Authenticated patient with portal JWT, complete profile data
   - **When:** GET /api/v1/portal/me
   - **Then:** 200 OK with all allowed fields; excluded fields absent; clinic info included

2. Patient with next appointment
   - **Given:** Patient has 2 future confirmed appointments
   - **When:** GET /api/v1/portal/me
   - **Then:** next_appointment shows closest future appointment only

3. Patient with outstanding balance
   - **Given:** Patient has 2 partial-paid invoices totaling 200,000 COP outstanding
   - **When:** GET /api/v1/portal/me
   - **Then:** outstanding_balance = 200000.00

4. Cached response on second request
   - **Given:** Patient fetches profile twice within 5 minutes
   - **When:** Second GET /api/v1/portal/me
   - **Then:** Response served from Redis cache (no DB query on second call)

#### Edge Cases
1. Patient with no appointments
   - **Given:** Newly created patient, no appointments scheduled
   - **When:** GET /api/v1/portal/me
   - **Then:** next_appointment object present with all null values

2. Patient with zero balance
   - **Given:** All invoices fully paid
   - **When:** GET /api/v1/portal/me
   - **Then:** outstanding_balance = 0.00

3. Tenant without logo
   - **Given:** Tenant has not uploaded a logo
   - **When:** GET /api/v1/portal/me
   - **Then:** clinic.logo_url = null

#### Error Cases
1. Staff JWT on portal endpoint
   - **Given:** Doctor authenticated with staff JWT (scope=staff)
   - **When:** GET /api/v1/portal/me with staff token
   - **Then:** 403 Forbidden — scope mismatch

2. Expired portal token
   - **Given:** Portal JWT expired 5 minutes ago
   - **When:** GET /api/v1/portal/me
   - **Then:** 401 Unauthorized

3. Internal notes not leaked
   - **Given:** Patient record has notes="Paciente dificil, no paga"
   - **When:** GET /api/v1/portal/me
   - **Then:** Response body does not include `notes` field

### Test Data Requirements

**Users:** Patient with portal_access=true and complete profile; patient with minimal profile (no optional fields).

**Patients/Entities:** 2 future appointments for next_appointment test; at least one partial invoice for balance test.

### Mocking Strategy

- Redis: fakeredis for cache operations
- asyncio.gather: test both parallel queries execute correctly

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient can fetch their own profile via portal JWT
- [ ] Staff JWT (non-portal scope) returns 403
- [ ] Internal fields (notes, referral_source, no_show_count, created_by) are never returned
- [ ] Clinic info block included with correct tenant data
- [ ] Outstanding balance correctly computed from invoices
- [ ] Next appointment returns closest future appointment or null
- [ ] Response cached for 5 minutes in Redis
- [ ] Audit log entry written for PHI access
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms cache hit, < 200ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Patient updating their own profile (read-only portal endpoint)
- Full invoice list (see PP-06 portal-invoices.md)
- Full appointment list (see PP-03 portal-appointments.md)
- Full document list (see PP-07 portal-documents.md)
- Clinical records or odontogram (see PP-13 portal-odontogram.md)
- Changing portal password or email

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
- [x] Input sanitization defined (JWT claims only)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for PHI access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced, patient-specific)
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
| 1.0 | 2026-02-25 | Initial spec |
