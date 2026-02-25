# AP-07 Complete Appointment Spec

---

## Overview

**Feature:** Mark an appointment as completed after the patient visit ends. Links the appointment to clinical records created during the session. Transitions status to completed and records the completion timestamp. Only doctors and clinic_owners may complete an appointment.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create.md), AP-06 (appointment-confirm.md), clinical-records specs (CR-01+), infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only the assigned doctor or a clinic_owner may mark an appointment as complete. Receptionists, assistants, and patients cannot complete appointments.

---

## Endpoint

```
POST /api/v1/appointments/{appointment_id}/complete
```

**Rate Limiting:**
- 30 requests per minute per user

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
| appointment_id | Yes | uuid | Must be valid UUID; must exist in tenant | Appointment to complete | c3d4e5f6-a1b2-7890-abcd-1234567890ef |

### Query Parameters

None.

### Request Body Schema

```json
{
  "clinical_record_ids": "uuid[] (optional) — list of clinical record IDs created during this appointment to link; max 20 items",
  "completion_notes": "string (optional) — max 2000 chars; post-appointment clinical summary note"
}
```

**Example Request:**
```json
{
  "clinical_record_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
  "completion_notes": "Limpieza completada. Proximo control en 6 meses."
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "status": "string (completed)",
  "completed_at": "string (ISO 8601 datetime)",
  "completed_by": "uuid",
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "start_time": "string (ISO 8601 datetime)",
  "end_time": "string (ISO 8601 datetime)",
  "type": "string",
  "completion_notes": "string | null",
  "clinical_records": [
    {
      "id": "uuid",
      "type": "string",
      "created_at": "string (ISO 8601 datetime)"
    }
  ]
}
```

**Example:**
```json
{
  "id": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "status": "completed",
  "completed_at": "2026-03-15T09:35:00-05:00",
  "completed_by": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time": "2026-03-15T09:00:00-05:00",
  "end_time": "2026-03-15T09:30:00-05:00",
  "type": "consultation",
  "completion_notes": "Limpieza completada. Proximo control en 6 meses.",
  "clinical_records": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "type": "evolution_note",
      "created_at": "2026-03-15T09:30:00-05:00"
    }
  ]
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Caller is not a doctor assigned to this appointment or a clinic_owner. Receptionists, assistants, and patients always receive 403.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el doctor asignado o el administrador puede completar una cita."
}
```

#### 404 Not Found
**When:** appointment_id does not exist in the tenant, or a provided clinical_record_id does not exist.

**Example:**
```json
{
  "error": "not_found",
  "message": "Cita no encontrada."
}
```

#### 422 Unprocessable Entity
**When:** Appointment is already completed, cancelled, or no_show. Or appointment status is scheduled (must be at least confirmed or in_progress to complete).

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "La cita debe estar en estado confirmada o en progreso para ser completada.",
  "details": {
    "current_status": "scheduled",
    "allowed_from": ["confirmed", "in_progress"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or system failure.

---

## Business Logic

**Step-by-step process:**

1. Validate `appointment_id` as valid UUID. Validate request body.
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Load appointment from DB. Return 404 if not found.
4. Check RBAC: caller must be clinic_owner or the doctor with `appointment.doctor_id == caller_user_id`. Return 403 otherwise.
5. Validate `appointment.status` is confirmed or in_progress. Return 422 if scheduled, cancelled, completed, or no_show.
6. If `clinical_record_ids` provided: validate each UUID exists in `clinical_records` table and belongs to `appointment.patient_id`. Return 404 for any not found or mismatched.
7. Execute UPDATE: `status = 'completed'`, `completed_at = now()`, `completed_by = caller_user_id`, `completion_notes = data.completion_notes`.
8. If `clinical_record_ids` provided: UPDATE `clinical_records SET appointment_id = :appointment_id WHERE id IN (...)`. Links records to the appointment.
9. Write audit log entry.
10. Invalidate cache: appointment detail, calendar list, patient clinical records cache.
11. Dispatch `appointment.completed` event to RabbitMQ.
12. If treatment_plan_item_id set on appointment: dispatch `treatment_plan.item_progress` event so treatment plan worker can update item status.
13. Return 200 with completed appointment including linked clinical records summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| appointment_id | Valid UUID, exists in tenant | Cita no encontrada. |
| appointment.status | Must be confirmed or in_progress | La cita debe estar confirmada o en progreso para completarse. |
| clinical_record_ids | Each must be valid UUID, exist in tenant, belong to appointment.patient_id | Registro clinico no encontrado. |
| clinical_record_ids | Max 20 items | No se pueden vincular mas de 20 registros a una cita. |
| completion_notes | Max 2000 chars if provided | Las notas no pueden superar 2000 caracteres. |

**Business Rules:**

- Can be completed from confirmed or in_progress status. Scheduled appointments must first be confirmed (or transitioned to in_progress).
- `completed_by` is always set from JWT; cannot be supplied by client.
- `completion_notes` is stored separately from the main appointment notes field; it represents a post-visit summary.
- Linking clinical records is optional; appointment can be completed with no records (e.g., patient didn't require clinical documentation).
- Treatment plan item progression is handled asynchronously via event; this endpoint does not directly update the treatment plan.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No clinical_record_ids provided | Complete appointment with empty clinical_records list |
| clinical_record_id belongs to correct patient but already linked to a different appointment | Allow — a record can reference one appointment; override previous link |
| Appointment completed_at is before end_time (doctor completes early) | Allow — actual completion time may differ from scheduled end |
| completion_notes is null | Store as null, return null in response |
| appointment.status = in_progress (started but not yet done) | Allow completion directly from in_progress |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `appointments`: UPDATE — status, completed_at, completed_by, completion_notes
- `clinical_records`: UPDATE — appointment_id linked for each provided record
- `audit_logs`: INSERT — complete event with PHI flag

**Example query (SQLAlchemy):**
```python
# Complete appointment
stmt = (
    update(Appointment)
    .where(Appointment.id == appointment_id)
    .values(
        status=AppointmentStatus.COMPLETED,
        completed_at=utcnow(),
        completed_by=current_user.id,
        completion_notes=data.completion_notes,
    )
    .returning(Appointment)
)
await session.execute(stmt)

# Link clinical records
if data.clinical_record_ids:
    link_stmt = (
        update(ClinicalRecord)
        .where(ClinicalRecord.id.in_(data.clinical_record_ids))
        .values(appointment_id=appointment_id)
    )
    await session.execute(link_stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:appointment:{appointment_id}`: INVALIDATE
- `tenant:{tenant_id}:appointments:calendar:{doctor_id}:{date}`: INVALIDATE
- `tenant:{tenant_id}:appointments:list:*`: INVALIDATE
- `tenant:{tenant_id}:patient:{patient_id}:clinical_records:*`: INVALIDATE — if records were linked

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | appointment.completed | { tenant_id, appointment_id, patient_id, doctor_id, clinical_record_ids } | After successful complete |
| treatment-plans | treatment_plan.item_progress | { tenant_id, treatment_plan_item_id, appointment_id } | If treatment_plan_item_id set on appointment |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** update
- **Resource:** appointment
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No. No patient notification sent on appointment completion.

---

## Performance

### Expected Response Time
- **Target:** < 250ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on complete (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates appointment detail, calendar, list, and clinical records caches

### Database Performance

**Queries executed:** 3 (load appointment, validate clinical_record_ids, update appointment + update records)

**Indexes required:**
- `appointments.id` — PRIMARY KEY (exists)
- `appointments.doctor_id` — INDEX (for RBAC check)
- `clinical_records.id` — PRIMARY KEY (exists)
- `clinical_records.patient_id` — INDEX (for ownership validation)
- `clinical_records.appointment_id` — INDEX (for reverse lookup)

**N+1 prevention:** Clinical record validation uses `WHERE id IN (...)` batch query; clinical records summary loaded with `selectinload`.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| appointment_id | Pydantic UUID validator | URL param |
| clinical_record_ids | Pydantic list of UUID validators | Each item validated |
| completion_notes | Pydantic strip() + bleach.clean, max 2000 chars | Clinical free-text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** completion_notes (clinical summary), clinical_record_ids (references to PHI records)

**Audit requirement:** All completion events logged with PHI flag and clinical_record_ids in audit payload.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor completes confirmed appointment with linked clinical record
   - **Given:** Doctor JWT (own appointment), appointment status=confirmed, valid clinical_record_id belonging to patient
   - **When:** POST /api/v1/appointments/{id}/complete with clinical_record_ids
   - **Then:** 200 with status=completed, clinical_records array populated, appointment.completed event dispatched

2. Clinic owner completes in_progress appointment
   - **Given:** clinic_owner JWT, appointment status=in_progress
   - **When:** POST /api/v1/appointments/{id}/complete with completion_notes
   - **Then:** 200 with status=completed, completed_by set to clinic_owner UUID

3. Complete appointment with no clinical records
   - **Given:** Doctor JWT, appointment status=confirmed
   - **When:** POST without clinical_record_ids
   - **Then:** 200 with clinical_records=[], appointment completed

#### Edge Cases
1. Appointment completed slightly before scheduled end_time
   - **Given:** Doctor completes at T+25min, scheduled end at T+30min
   - **When:** POST complete
   - **Then:** 200 with completed_at = actual time (before end_time); no error

2. clinical_record previously linked to different appointment
   - **Given:** Record has appointment_id set to old appointment
   - **When:** POST complete with that record_id
   - **Then:** 200 — record re-linked to new appointment (override allowed)

#### Error Cases
1. Receptionist attempts to complete
   - **Given:** Receptionist JWT
   - **When:** POST complete
   - **Then:** 403 Forbidden

2. Appointment in scheduled status
   - **Given:** Appointment status=scheduled (not yet confirmed)
   - **When:** POST complete
   - **Then:** 422 invalid_status_transition with allowed_from=["confirmed","in_progress"]

3. clinical_record_id belongs to different patient
   - **Given:** Valid record_id but patient_id mismatch
   - **When:** POST complete with that record_id
   - **Then:** 404 Registro clinico no encontrado

4. Doctor completing another doctor's appointment
   - **Given:** Doctor A JWT, appointment.doctor_id = Doctor B
   - **When:** POST complete
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, two doctors, receptionist (for negative test)

**Patients/Entities:** Appointments in confirmed and in_progress status; clinical records linked to patient; treatment plan with item linked to appointment

### Mocking Strategy

- RabbitMQ: Mock publish; assert `appointment.completed` and `treatment_plan.item_progress` dispatched
- Redis: Use `fakeredis`; verify cache keys invalidated

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/appointments/{id}/complete returns 200 with status=completed
- [ ] Only doctor (own) or clinic_owner can complete (403 for others)
- [ ] Allowed from confirmed and in_progress status only (422 otherwise)
- [ ] clinical_record_ids validated for patient ownership
- [ ] Clinical records linked to appointment in DB
- [ ] completion_notes stored correctly
- [ ] appointment.completed event dispatched to RabbitMQ
- [ ] treatment_plan.item_progress event dispatched if treatment_plan_item_id set
- [ ] Cache invalidated for detail, calendar, list, clinical records keys
- [ ] Audit log written with PHI flag
- [ ] All test cases pass
- [ ] Performance targets met (< 250ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Transitioning appointment to in_progress (implicit — auto-set when doctor opens clinical record during appointment)
- Billing/invoicing after appointment completion (separate billing workflow)
- Generating clinical reports from completion data
- Patient feedback/review after appointment

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
