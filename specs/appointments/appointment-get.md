# AP-02 Get Appointment Spec

---

## Overview

**Feature:** Retrieve full detail for a single appointment by ID, including patient summary, doctor summary, linked treatment plan item, and clinical records created during the appointment. Used by the appointment detail drawer/modal in the calendar view and by the patient portal.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create.md), P-01 (patient-get.md), U-01 (get-profile.md), infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients may only retrieve appointments where `patient_id` matches their own user-linked patient record. Doctors may retrieve any appointment in the tenant. Assistants and receptionists may retrieve any appointment in the tenant.

---

## Endpoint

```
GET /api/v1/appointments/{appointment_id}
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
| appointment_id | Yes | uuid | Must be valid UUID; must exist in tenant | The appointment's unique identifier | c3d4e5f6-a1b2-7890-abcd-1234567890ef |

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
  "doctor_id": "uuid",
  "start_time": "string (ISO 8601 datetime)",
  "end_time": "string (ISO 8601 datetime)",
  "duration_minutes": "integer",
  "type": "string (consultation | procedure | emergency | follow_up)",
  "status": "string (scheduled | confirmed | in_progress | completed | cancelled | no_show)",
  "notes": "string | null",
  "treatment_plan_item_id": "uuid | null",
  "cancellation_reason": "string | null",
  "no_show_at": "string | null (ISO 8601 datetime)",
  "completed_at": "string | null (ISO 8601 datetime)",
  "patient": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "document_type": "string",
    "document_number": "string",
    "phone": "string",
    "email": "string | null",
    "birthdate": "string (ISO 8601 date)",
    "no_show_count": "integer"
  },
  "doctor": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "specialty": "string | null"
  },
  "treatment_plan_item": {
    "id": "uuid",
    "procedure_name": "string",
    "tooth_number": "string | null",
    "status": "string"
  } | null,
  "clinical_records": [
    {
      "id": "uuid",
      "type": "string",
      "created_at": "string (ISO 8601 datetime)"
    }
  ],
  "created_by": "uuid",
  "created_at": "string (ISO 8601 datetime)",
  "updated_at": "string | null (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T09:00:00-05:00",
  "end_time": "2026-03-15T09:30:00-05:00",
  "duration_minutes": 30,
  "type": "consultation",
  "status": "confirmed",
  "notes": "Primera consulta, revisar radiografias previas.",
  "treatment_plan_item_id": null,
  "cancellation_reason": null,
  "no_show_at": null,
  "completed_at": null,
  "patient": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "first_name": "Maria",
    "last_name": "Garcia Lopez",
    "document_type": "cedula",
    "document_number": "1020304050",
    "phone": "+573001234567",
    "email": "maria.garcia@email.com",
    "birthdate": "1990-05-15",
    "no_show_count": 1
  },
  "doctor": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "first_name": "Carlos",
    "last_name": "Mendez",
    "specialty": "Endodoncia"
  },
  "treatment_plan_item": null,
  "clinical_records": [],
  "created_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "created_at": "2026-03-10T14:30:00-05:00",
  "updated_at": "2026-03-14T08:00:00-05:00"
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient user attempts to retrieve an appointment not linked to their own patient record.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para ver esta cita."
}
```

#### 404 Not Found
**When:** `appointment_id` does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "Cita no encontrada."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache error.

---

## Business Logic

**Step-by-step process:**

1. Validate `appointment_id` as a valid UUID via Pydantic path parameter validator.
2. Resolve tenant from JWT claims; set `search_path` to tenant schema.
3. Extract caller role and caller_user_id from JWT.
4. Query `appointments` table for the given `appointment_id`. Return 404 if not found.
5. If caller role = patient, look up the patient record linked to caller's user account. Assert `appointment.patient_id == caller_patient_id`. Return 403 if mismatch.
6. Check Redis cache: `tenant:{tenant_id}:appointment:{appointment_id}`. Return cached response if hit.
7. If cache miss, execute full JOIN query to load patient, doctor, treatment_plan_item, and clinical_records summary.
8. Serialize via Pydantic `AppointmentDetailResponse`.
9. Cache result with TTL 120 seconds (short TTL because status changes frequently).
10. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| appointment_id | Must be valid UUID format | ID de cita invalido. |
| appointment_id | Must exist in tenant schema | Cita no encontrada. |

**Business Rules:**

- Patients see only their own appointments; all staff roles see any appointment in the tenant.
- `cancellation_reason` is only populated when status = cancelled.
- `no_show_at` is only populated when status = no_show.
- `completed_at` is only populated when status = completed.
- `clinical_records` returns a summary list (id + type + created_at only); full record detail is fetched via clinical-records endpoints.
- PHI fields in the patient sub-object are always included for staff roles; for patient role, only their own data is returned (same record, no extra restriction needed since it is already their own).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient user linked to no patient record | Return 403 with generic forbidden message |
| Appointment in cancelled status | Return full detail including cancellation_reason |
| clinical_records list is empty | Return empty array, not null |
| treatment_plan_item deleted after appointment created | Return treatment_plan_item: null gracefully |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None. This is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:appointment:{appointment_id}`: SET on cache miss — stores serialized appointment detail.

**Cache TTL:** 120 seconds (2 minutes) — short TTL to capture frequent status transitions.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** read
- **Resource:** appointment
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 80ms (cache hit), < 200ms (cache miss)
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Redis cache
- **Cache key:** `tenant:{tenant_id}:appointment:{appointment_id}`
- **TTL:** 120 seconds
- **Invalidation:** On any status transition (AP-04, AP-05, AP-06, AP-07, AP-08) and on appointment update

### Database Performance

**Queries executed:** 0 (cache hit) or 1 (cache miss — single JOIN query)

**Indexes required:**
- `appointments.id` — PRIMARY KEY (exists)
- `appointments.patient_id` — INDEX (for patient-scoped access check)
- `clinical_records.appointment_id` — INDEX (for reverse lookup)

**N+1 prevention:** Single JOIN query loads patient, doctor, treatment_plan_item, and clinical_records summary in one round-trip using SQLAlchemy `joinedload` / `selectinload`.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_id (URL param) | Pydantic UUID validator | Rejects non-UUID strings before DB query |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient.first_name, patient.last_name, patient.document_number, patient.phone, patient.email, patient.birthdate, notes

**Audit requirement:** All access logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Clinic owner retrieves completed appointment (cache miss)
   - **Given:** Valid clinic_owner JWT, appointment exists with status=completed
   - **When:** GET /api/v1/appointments/{appointment_id}
   - **Then:** 200 with full detail including completed_at, clinical_records list

2. Receptionist retrieves scheduled appointment (cache hit)
   - **Given:** Valid receptionist JWT, appointment cached in Redis
   - **When:** GET /api/v1/appointments/{appointment_id}
   - **Then:** 200 from cache within 80ms

3. Patient retrieves own appointment
   - **Given:** Valid patient JWT, appointment.patient_id matches caller's linked patient
   - **When:** GET /api/v1/appointments/{appointment_id}
   - **Then:** 200 with full appointment detail

4. Cancelled appointment includes cancellation_reason
   - **Given:** Appointment status=cancelled with reason set
   - **When:** GET /api/v1/appointments/{appointment_id}
   - **Then:** 200 with cancellation_reason populated

#### Edge Cases
1. Redis unavailable — graceful fallback
   - **Given:** Redis is down, valid clinic_owner JWT
   - **When:** GET /api/v1/appointments/{appointment_id}
   - **Then:** 200 from DB; warning logged

2. treatment_plan_item was deleted
   - **Given:** Appointment has treatment_plan_item_id but the item was removed
   - **When:** GET /api/v1/appointments/{appointment_id}
   - **Then:** 200 with treatment_plan_item: null

#### Error Cases
1. Patient requests another patient's appointment
   - **Given:** Valid patient JWT, appointment belongs to different patient
   - **When:** GET /api/v1/appointments/{other_appointment_id}
   - **Then:** 403 Forbidden

2. appointment_id does not exist
   - **Given:** Valid clinic_owner JWT, random UUID
   - **When:** GET /api/v1/appointments/{fake_id}
   - **Then:** 404 Cita no encontrada

3. Invalid UUID format
   - **Given:** appointment_id = "not-a-uuid"
   - **When:** GET /api/v1/appointments/not-a-uuid
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** clinic_owner, doctor, receptionist, patient (linked to patient record), second patient (for negative test)

**Patients/Entities:** Appointments in each status: scheduled, confirmed, completed (with clinical_records), cancelled (with reason), no_show; one appointment with treatment_plan_item linked

### Mocking Strategy

- Redis: Use `fakeredis`; disconnect mock for fallback test
- Database: Test tenant schema with seeded appointments and related records

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/appointments/{appointment_id} returns 200 with full appointment detail
- [ ] Patient sub-object includes no_show_count
- [ ] clinical_records returns summary array (not null)
- [ ] treatment_plan_item returns null gracefully when deleted
- [ ] Patient role restricted to own appointments; 403 for others
- [ ] Staff roles can read any appointment in tenant
- [ ] Response cached for 120 seconds
- [ ] Cache fallback to DB works when Redis unavailable
- [ ] audit_log entry written with PHI flag
- [ ] All test cases pass
- [ ] Performance targets met (< 80ms cache hit, < 200ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listing multiple appointments (see AP-03)
- Updating appointment data (see AP-04)
- Status transitions (see AP-05 through AP-08)
- Full clinical record detail (see clinical-records specs)

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
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

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
| 1.0 | 2026-02-25 | Initial spec |
