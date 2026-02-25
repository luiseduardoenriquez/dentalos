# Deactivate Patient Spec

---

## Overview

**Feature:** Soft-deactivate a patient record by setting `is_active = false`. This preserves all clinical records (legal and regulatory requirement in LATAM). Future appointments are automatically cancelled. Only the clinic_owner role can perform this action. Patients can be reactivated later via the patient-update endpoint (P-04).

**Domain:** patients

**Priority:** Critical

**Dependencies:** P-01 (patient-create.md), P-04 (patient-update.md), I-02 (database-architecture.md), auth/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner can deactivate patients. This is a restricted action due to its impact on clinical continuity and scheduled appointments.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/deactivate
```

**Rate Limiting:**
- 10 requests per minute per user (restricted action)

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
| patient_id | Yes | uuid | Valid UUID v4 | The unique patient identifier | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "reason": "string (optional) -- max 500 chars, reason for deactivation"
}
```

**Example Request:**
```json
{
  "reason": "Paciente se mudo a otra ciudad y solicito transferencia de historia clinica."
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
  "first_name": "string",
  "last_name": "string",
  "is_active": false,
  "deactivated_at": "string (ISO 8601 datetime)",
  "deactivated_by": "uuid",
  "reason": "string | null",
  "cancelled_appointments_count": "integer",
  "message": "string"
}
```

**Example:**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "first_name": "Maria",
  "last_name": "Garcia Lopez",
  "is_active": false,
  "deactivated_at": "2026-02-24T16:00:00Z",
  "deactivated_by": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "reason": "Paciente se mudo a otra ciudad y solicito transferencia de historia clinica.",
  "cancelled_appointments_count": 3,
  "message": "Paciente desactivado exitosamente. Se cancelaron 3 citas futuras."
}
```

### Error Responses

#### 400 Bad Request
**When:** Patient is already deactivated.

**Example:**
```json
{
  "error": "already_deactivated",
  "message": "El paciente ya se encuentra desactivado.",
  "details": {
    "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "is_active": false
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure -- see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User role is not clinic_owner.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede desactivar pacientes."
}
```

#### 404 Not Found
**When:** Patient with the given ID does not exist in the tenant schema.

**Example:**
```json
{
  "error": "not_found",
  "message": "Paciente no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Reason exceeds max length.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "reason": ["El motivo no puede exceder 500 caracteres."]
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

1. Validate `patient_id` is a valid UUID v4.
2. Validate optional `reason` field (max 500 chars).
3. Resolve tenant from JWT claims; set `search_path` to tenant schema.
4. Check user permissions: MUST be clinic_owner. Return 403 otherwise.
5. Fetch patient by ID. If not found, return 404.
6. If patient `is_active = false`, return 400 (already deactivated).
7. Begin database transaction:
   a. Update `patients` set `is_active = false`, `updated_at = now()`.
   b. Cancel all future appointments: `UPDATE appointments SET status = 'cancelled', cancellation_reason = 'Paciente desactivado', cancelled_by = :user_id, updated_at = now() WHERE patient_id = :patient_id AND start_time > now() AND status IN ('scheduled', 'confirmed')`. Capture count.
   c. Cancel active waitlist entries: `UPDATE waitlist SET status = 'cancelled' WHERE patient_id = :patient_id AND status = 'waiting'`.
8. Commit transaction.
9. Write audit log entry (action: update, resource: patient, metadata includes reason and cancelled_appointments_count).
10. Invalidate Redis caches: patient profile, patient list, search, affected appointment caches.
11. Dispatch `patient.deactivated` event to RabbitMQ.
12. Dispatch `appointments.bulk_cancelled` event for notification processing (notify affected doctors).
13. Return 200 with deactivation confirmation.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 | Identificador de paciente no valido. |
| reason | Max 500 chars (if provided) | El motivo no puede exceder 500 caracteres. |

**Business Rules:**

- Only `clinic_owner` can deactivate patients. This is intentionally more restrictive than other patient operations to prevent accidental loss of clinical access.
- Deactivation is a soft operation: `is_active = false`. NO data is deleted. All clinical records (clinical_records, diagnoses, treatment_plans, procedures, odontogram data, consents, invoices) remain intact.
- All future appointments (status = scheduled or confirmed) are automatically cancelled with a system-generated cancellation reason.
- Past appointments (completed, cancelled, no_show) are not affected.
- Active waitlist entries are cancelled.
- Reactivation is done via P-04 (patient-update) by setting `is_active = true`. This requires plan limit re-validation.
- The deactivation reason is stored in the audit log, not in the patient record itself.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no future appointments | Deactivate successfully, cancelled_appointments_count = 0 |
| Patient has in_progress appointment right now | Do NOT cancel (status is not scheduled/confirmed) |
| Patient has outstanding invoices | Deactivate anyway; invoices remain for collection |
| Patient has active treatment plans | Deactivate anyway; treatment plans remain but cannot proceed |
| Patient has portal access | Deactivate patient; portal access is separately revoked via event |
| Concurrent deactivation requests | First succeeds, second gets 400 (already deactivated) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `patients`: UPDATE -- set is_active = false, updated_at
- `appointments`: UPDATE -- cancel future scheduled/confirmed appointments
- `waitlist`: UPDATE -- cancel active waitlist entries

**Example query (SQLAlchemy):**
```python
# Deactivate patient
await session.execute(
    update(Patient)
    .where(Patient.id == patient_id)
    .values(is_active=False, updated_at=func.now())
)

# Cancel future appointments
result = await session.execute(
    update(Appointment)
    .where(
        Appointment.patient_id == patient_id,
        Appointment.start_time > func.now(),
        Appointment.status.in_(['scheduled', 'confirmed'])
    )
    .values(
        status='cancelled',
        cancellation_reason='Paciente desactivado',
        cancelled_by=current_user.id,
        updated_at=func.now()
    )
)
cancelled_count = result.rowcount

# Cancel waitlist entries
await session.execute(
    update(Waitlist)
    .where(
        Waitlist.patient_id == patient_id,
        Waitlist.status == 'waiting'
    )
    .values(status='cancelled')
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:profile`: DELETE
- `tenant:{tenant_id}:patients:list:*`: DELETE
- `tenant:{tenant_id}:patients:search:*`: DELETE
- `tenant:{tenant_id}:patients:count`: DELETE
- `tenant:{tenant_id}:appointments:*`: DELETE (affected appointment caches)

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| patients | patient.deactivated | { tenant_id, patient_id, deactivated_by, reason } | After successful deactivation |
| appointments | appointments.bulk_cancelled | { tenant_id, patient_id, appointment_ids[], cancelled_by } | If appointments were cancelled |
| notifications | notification.deactivation_alert | { tenant_id, patient_id, doctor_ids[] } | Notify doctors of cancelled appointments |

### Audit Log

**Audit entry:** Yes -- see infra/audit-logging.md

**If Yes:**
- **Action:** update
- **Resource:** patient
- **PHI involved:** Yes

**Audit payload:**
```json
{
  "old_value": { "is_active": true },
  "new_value": { "is_active": false },
  "metadata": {
    "reason": "Paciente se mudo a otra ciudad",
    "cancelled_appointments_count": 3,
    "cancelled_appointment_ids": ["uuid1", "uuid2", "uuid3"]
  }
}
```

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | patient_deactivation_notice | Doctors with cancelled appointments | When their appointments are cancelled |

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 800ms (may be slower if many appointments to cancel)

### Caching Strategy
- **Strategy:** No caching on write
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates patient profile, list, search, count, and appointment caches

### Database Performance

**Queries executed:** 4 (1 SELECT patient, 1 UPDATE patient, 1 UPDATE appointments, 1 UPDATE waitlist) within a single transaction

**Indexes required:**
- `patients.id` -- PRIMARY KEY (already defined)
- `appointments.(patient_id)` -- INDEX (already defined)
- `appointments.status` -- INDEX (already defined)
- `waitlist.status` -- INDEX (already defined)

**N+1 prevention:** Bulk UPDATE for appointments (single query cancels all matching).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID validator | Rejects non-UUID |
| reason | Pydantic strip + bleach.clean, max 500 chars | Free text stored in audit log |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, first_name, last_name (in response). No PHI in the deactivation action itself beyond identity.

**Audit requirement:** All deactivations logged with reason and side effects

---

## Testing

### Test Cases

#### Happy Path
1. Deactivate patient with future appointments
   - **Given:** Active patient with 3 future scheduled appointments, user is clinic_owner
   - **When:** POST /api/v1/patients/{id}/deactivate with reason
   - **Then:** 200 OK, is_active = false, cancelled_appointments_count = 3, all 3 appointments cancelled

2. Deactivate patient with no future appointments
   - **Given:** Active patient with no future appointments
   - **When:** POST /api/v1/patients/{id}/deactivate
   - **Then:** 200 OK, is_active = false, cancelled_appointments_count = 0

3. Deactivate patient without reason
   - **Given:** Active patient, no reason provided
   - **When:** POST /api/v1/patients/{id}/deactivate with empty body or `{}`
   - **Then:** 200 OK, reason = null in response

#### Edge Cases
1. Patient with in-progress appointment
   - **Given:** Patient has an appointment with status = 'in_progress'
   - **When:** POST /api/v1/patients/{id}/deactivate
   - **Then:** 200 OK, in-progress appointment NOT cancelled (only scheduled/confirmed are cancelled)

2. Patient with outstanding invoices
   - **Given:** Patient has unpaid invoices
   - **When:** POST /api/v1/patients/{id}/deactivate
   - **Then:** 200 OK, invoices remain unchanged

3. Patient with active waitlist entry
   - **Given:** Patient on waitlist
   - **When:** POST /api/v1/patients/{id}/deactivate
   - **Then:** 200 OK, waitlist entry cancelled

#### Error Cases
1. Non-clinic_owner attempts deactivation
   - **Given:** User with doctor role
   - **When:** POST /api/v1/patients/{id}/deactivate
   - **Then:** 403 Forbidden

2. Already deactivated patient
   - **Given:** Patient with is_active = false
   - **When:** POST /api/v1/patients/{id}/deactivate
   - **Then:** 400 Bad Request (already deactivated)

3. Non-existent patient
   - **Given:** Random UUID
   - **When:** POST /api/v1/patients/{random_uuid}/deactivate
   - **Then:** 404 Not Found

4. Reason too long
   - **Given:** Reason with 600 characters
   - **When:** POST /api/v1/patients/{id}/deactivate
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** clinic_owner (for success tests), doctor/assistant/receptionist (for 403 tests)

**Patients/Entities:** Active patient with: future scheduled appointments, in-progress appointment, waitlist entries, outstanding invoices. Already-deactivated patient.

### Mocking Strategy

- Redis cache: Use fakeredis for invalidation verification
- RabbitMQ: Mock publish calls, assert event payloads for patient.deactivated and appointments.bulk_cancelled
- Notifications: Mock notification dispatch, verify doctor notification payload

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] clinic_owner can deactivate an active patient
- [ ] Non-clinic_owner roles receive 403
- [ ] Patient is_active set to false (soft delete, no data removed)
- [ ] All future scheduled/confirmed appointments are cancelled
- [ ] Active waitlist entries are cancelled
- [ ] Past and in-progress appointments are NOT affected
- [ ] Clinical records, invoices, treatment plans preserved
- [ ] Already-deactivated patient returns 400
- [ ] Audit log entry includes reason and cancelled appointment details
- [ ] Cache invalidated (patient profile, list, search, appointments)
- [ ] RabbitMQ events dispatched (patient.deactivated, appointments.bulk_cancelled)
- [ ] Doctor notification sent for cancelled appointments
- [ ] Patient can be reactivated via P-04 (is_active: true)
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Hard deletion of patient data (not supported; violates LATAM clinical record retention laws)
- Patient data export before deactivation (separate endpoint)
- Portal access revocation (handled by separate event consumer)
- Automated reactivation rules or workflows
- Bulk patient deactivation

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
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
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
