# Deactivate User Spec

---

## Overview

**Feature:** Soft-deactivate a team member. Sets `is_active = false`, revokes all active sessions, and preserves all clinical records. The clinic_owner cannot deactivate themselves. If the target user is a doctor with pending/scheduled appointments, a warning is returned with affected appointment details. All actions are recorded in the audit log.

**Domain:** users

**Priority:** Critical

**Dependencies:** U-05 (update-team-member.md), I-01 (multi-tenancy.md), A-01 (authentication)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required -- resolved from JWT
- **Special rules:** The clinic_owner cannot deactivate themselves. The action is irreversible via this endpoint (reactivation requires U-05 with `is_active: true`).

---

## Endpoint

```
POST /api/v1/users/{user_id}/deactivate
```

**Rate Limiting:**
- 10 requests per minute per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_a1b2c3d4e5f6 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| user_id | Yes | uuid | Valid UUID v4 | ID of the user to deactivate | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "reason": "string (optional, max 500 chars)",
  "confirm": "boolean (required)"
}
```

**Example Request:**
```json
{
  "reason": "Renuncia voluntaria del empleado.",
  "confirm": true
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
  "email": "string",
  "name": "string",
  "role": "string",
  "is_active": false,
  "deactivated_at": "datetime",
  "sessions_revoked": "integer",
  "warnings": [
    {
      "type": "string",
      "message": "string",
      "details": {}
    }
  ]
}
```

**Example (non-doctor):**
```json
{
  "id": "a23bc45d-67ef-8901-b234-567890abcdef",
  "email": "carlos.gomez@clinicasonrisa.co",
  "name": "Carlos Gomez",
  "role": "receptionist",
  "is_active": false,
  "deactivated_at": "2026-02-24T14:30:00Z",
  "sessions_revoked": 2,
  "warnings": []
}
```

**Example (doctor with pending appointments):**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "email": "dra.martinez@clinicasonrisa.co",
  "name": "Dra. Laura Martinez",
  "role": "doctor",
  "is_active": false,
  "deactivated_at": "2026-02-24T14:30:00Z",
  "sessions_revoked": 3,
  "warnings": [
    {
      "type": "pending_appointments",
      "message": "La doctora tiene 5 citas pendientes que deben ser reasignadas.",
      "details": {
        "pending_count": 5,
        "earliest": "2026-02-25T09:00:00Z",
        "latest": "2026-03-15T16:00:00Z",
        "appointment_ids": [
          "11111111-1111-1111-1111-111111111111",
          "22222222-2222-2222-2222-222222222222",
          "33333333-3333-3333-3333-333333333333",
          "44444444-4444-4444-4444-444444444444",
          "55555555-5555-5555-5555-555555555555"
        ]
      }
    }
  ]
}
```

### Error Responses

#### 400 Bad Request
**When:** Request body is malformed or `confirm` field is missing/false.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Debe confirmar la desactivacion enviando 'confirm': true."
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure -- see infra/authentication-rules.md.

#### 403 Forbidden
**When:** User is not `clinic_owner`, or attempting to deactivate themselves.

**Examples:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede desactivar usuarios."
}
```
```json
{
  "error": "forbidden",
  "message": "No puede desactivar su propia cuenta."
}
```

#### 404 Not Found
**When:** The `user_id` does not exist within the current tenant schema.

**Example:**
```json
{
  "error": "not_found",
  "message": "Usuario no encontrado."
}
```

#### 409 Conflict
**When:** The user is already deactivated (`is_active = false`).

**Example:**
```json
{
  "error": "conflict",
  "message": "El usuario ya se encuentra desactivado.",
  "details": {
    "deactivated_since": "2026-01-15T10:00:00Z"
  }
}
```

#### 422 Unprocessable Entity
**When:** The `user_id` is not a valid UUID or the `confirm` field is not boolean.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "user_id": ["El ID de usuario debe ser un UUID valido."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database error.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract `requesting_user_id` and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id`.
3. Verify requesting user role is `clinic_owner`; otherwise return 403.
4. Validate `user_id` URL parameter is a valid UUID.
5. Parse and validate request body via Pydantic `DeactivateUserRequest`.
6. If `confirm` is not `true`, return 400.
7. If `requesting_user_id == user_id`, return 403 ("No puede desactivar su propia cuenta.").
8. Fetch target user from `users` table by `user_id`. If not found, return 404.
9. If `is_active` is already `false`, return 409 with the `updated_at` timestamp as `deactivated_since`.
10. If target user role is `doctor`:
    a. Query `appointments` table for appointments where `doctor_id = user_id` AND `status IN ('scheduled', 'confirmed')` AND `start_time > now()`.
    b. Collect appointment IDs, count, earliest and latest dates.
    c. Build warning object for inclusion in response.
11. Begin database transaction:
    a. `UPDATE users SET is_active = false, updated_at = now() WHERE id = :user_id`.
    b. `UPDATE user_sessions SET is_revoked = true WHERE user_id = :user_id AND is_revoked = false`. Capture count of revoked sessions.
    c. Insert audit log entry with action `update`, resource `user`, old_value (is_active: true), new_value (is_active: false), and metadata including `reason` and `pending_appointments_count`.
12. Commit transaction.
13. Invalidate Redis cache key `tenant:{tenant_id}:user:{user_id}:profile`.
14. If doctor with pending appointments, dispatch RabbitMQ job to notify clinic_owner about pending appointment reassignment.
15. Return 200 with deactivation summary, revoked session count, and warnings.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| user_id | Valid UUID v4 format | "El ID de usuario debe ser un UUID valido." |
| confirm | Must be `true` | "Debe confirmar la desactivacion enviando 'confirm': true." |
| reason | Max 500 characters, optional | "El motivo no debe exceder 500 caracteres." |

**Business Rules:**

- Only `clinic_owner` can deactivate users.
- The `clinic_owner` CANNOT deactivate themselves (prevents clinic lockout).
- Deactivation is a soft delete: `is_active = false`. The user record is preserved.
- ALL active sessions for the deactivated user are revoked immediately.
- Clinical records (appointments, procedures, clinical_records, prescriptions) are NEVER deleted or modified.
- If the deactivated user is a doctor, pending appointments are NOT automatically cancelled or reassigned -- only a warning is returned.
- The deactivation reason is stored in the audit log metadata, not on the user record.
- A deactivated user can be reactivated via U-05 by setting `is_active = true`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Clinic_owner tries to deactivate themselves | Return 403. |
| User is already deactivated | Return 409 Conflict with timestamp. |
| Doctor with 0 pending appointments | Deactivate normally, empty warnings array. |
| Doctor with 100+ pending appointments | Return all appointment_ids in warnings (no pagination on warnings). |
| User has no active sessions | Deactivate normally, sessions_revoked = 0. |
| confirm is false | Return 400. Deactivation not performed. |
| confirm field is missing | Return 400. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: UPDATE -- sets `is_active = false`, `updated_at = now()`.
- `user_sessions`: UPDATE -- sets `is_revoked = true` for all active sessions of the user.
- `audit_log`: INSERT -- records deactivation with old/new values and reason.

**Example query (SQLAlchemy):**
```python
# Deactivate user
await session.execute(
    update(User)
    .where(User.id == user_id)
    .values(is_active=False, updated_at=func.now())
)

# Revoke sessions
result = await session.execute(
    update(UserSession)
    .where(UserSession.user_id == user_id, UserSession.is_revoked == False)
    .values(is_revoked=True)
)
revoked_count = result.rowcount

# Audit log
session.add(AuditLog(
    user_id=requesting_user_id,
    action="update",
    resource_type="user",
    resource_id=user_id,
    old_value={"is_active": True},
    new_value={"is_active": False},
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    metadata={
        "operation": "deactivate",
        "reason": reason,
        "sessions_revoked": revoked_count,
        "pending_appointments": pending_count,
    },
))
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:profile`: DELETE -- invalidated on deactivation.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | user.deactivated.appointment_warning | { tenant_id, user_id, user_name, pending_appointment_ids, pending_count } | Only when deactivated user is a doctor with pending appointments |

### Audit Log

**Audit entry:** Yes -- see infra/audit-logging.md.

- **Action:** update
- **Resource:** user
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes (conditional).

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | doctor_deactivated_appointments | clinic_owner | When deactivated doctor has pending appointments |

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 1000ms (if doctor with many appointments to query)

### Caching Strategy
- **Strategy:** Cache invalidation on write
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:profile`
- **TTL:** N/A (key is deleted)
- **Invalidation:** On successful deactivation.

### Database Performance

**Queries executed:** 3-5 (SELECT user, optional SELECT appointments, UPDATE user, UPDATE sessions, INSERT audit_log)

**Indexes required:**
- `users.id` -- PRIMARY KEY (already exists)
- `user_sessions.user_id` -- INDEX (already exists: `idx_user_sessions_user_id`)
- `appointments.doctor_id` + `appointments.status` -- INDEX (already exists: `idx_appointments_doctor_date`)
- `appointments.start_time` -- INDEX (already exists: `idx_appointments_date`)

**N+1 prevention:** Single query to fetch pending appointments (no joins needed).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| user_id | Pydantic UUID validator | Rejects non-UUID strings |
| confirm | Pydantic bool validator | Type-enforced, must be true |
| reason | Pydantic strip() + max 500 chars | Optional freetext, sanitized |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Deactivation metadata does not contain PHI. Appointment IDs in warnings do not expose patient data.

**Audit requirement:** Write-only logged (deactivation audited with reason).

---

## Testing

### Test Cases

#### Happy Path
1. Deactivate a receptionist (no appointments)
   - **Given:** Authenticated clinic_owner, target receptionist is active
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true}`
   - **Then:** 200, is_active=false, sessions_revoked count > 0, empty warnings, audit logged

2. Deactivate a doctor with pending appointments
   - **Given:** Authenticated clinic_owner, target doctor has 3 scheduled appointments
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true, "reason": "Cambio de clinica"}`
   - **Then:** 200, is_active=false, warnings array contains pending_appointments with count=3 and appointment IDs

3. Deactivate a doctor with no pending appointments
   - **Given:** Authenticated clinic_owner, target doctor has 0 future appointments
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true}`
   - **Then:** 200, empty warnings array

4. Deactivation with reason
   - **Given:** Authenticated clinic_owner
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true, "reason": "Terminacion de contrato"}`
   - **Then:** 200, reason stored in audit_log metadata

#### Edge Cases
1. User has no active sessions
   - **Given:** Target user has no sessions (never logged in or all expired)
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true}`
   - **Then:** 200, sessions_revoked = 0

2. Doctor with only past/completed appointments
   - **Given:** Doctor has appointments but all in the past or status=completed
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true}`
   - **Then:** 200, empty warnings (past appointments not flagged)

3. Deactivation without reason
   - **Given:** No reason field provided
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true}`
   - **Then:** 200, audit_log metadata has reason=null

#### Error Cases
1. Clinic_owner tries to deactivate themselves
   - **Given:** Authenticated clinic_owner
   - **When:** POST /api/v1/users/{own_id}/deactivate with `{"confirm": true}`
   - **Then:** 403 Forbidden

2. Non-owner attempts deactivation
   - **Given:** Authenticated doctor
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true}`
   - **Then:** 403 Forbidden

3. User already deactivated
   - **Given:** Target user is_active=false
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": true}`
   - **Then:** 409 Conflict

4. confirm is false
   - **Given:** Authenticated clinic_owner
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{"confirm": false}`
   - **Then:** 400 Bad Request

5. confirm field missing
   - **Given:** Authenticated clinic_owner
   - **When:** POST /api/v1/users/{user_id}/deactivate with `{}`
   - **Then:** 400 Bad Request

6. User not found
   - **Given:** Non-existent user_id
   - **When:** POST /api/v1/users/{random_uuid}/deactivate with `{"confirm": true}`
   - **Then:** 404 Not Found

7. Invalid UUID format
   - **Given:** Malformed user_id
   - **When:** POST /api/v1/users/not-a-uuid/deactivate with `{"confirm": true}`
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** One clinic_owner, two doctors (one with pending appointments, one without), one receptionist, one already-deactivated user. Users should have active sessions.

**Patients/Entities:** Appointments linked to the doctor with pending appointments (status = 'scheduled' or 'confirmed', start_time in the future).

### Mocking Strategy

- Redis: Use `fakeredis` to verify cache invalidation.
- RabbitMQ: Mock the message publisher. Verify job payload when doctor has pending appointments.
- Database: Use test tenant schema with seeded users, sessions, and appointments.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Only clinic_owner can deactivate users via POST /api/v1/users/{user_id}/deactivate
- [ ] Clinic_owner cannot deactivate themselves
- [ ] User's is_active is set to false (soft delete)
- [ ] All active sessions for the user are revoked
- [ ] Clinical records, appointments, and procedures are preserved unchanged
- [ ] If target is a doctor with pending appointments, warnings are returned in response
- [ ] RabbitMQ notification job dispatched for doctor deactivations with pending appointments
- [ ] Deactivation is recorded in audit_log with reason in metadata
- [ ] Already-deactivated users return 409 Conflict
- [ ] confirm=true is required to proceed
- [ ] Redis profile cache is invalidated
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Reactivating a user (use U-05 with `is_active: true`)
- Automatically reassigning appointments (manual action by clinic_owner after deactivation)
- Cancelling appointments of deactivated doctor (handled separately by appointments domain)
- Hard-deleting a user record (not supported -- soft delete only for compliance)
- Transferring clinical record ownership to another doctor
- Notifying the deactivated user via email (future enhancement)

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
| 1.0 | 2026-02-24 | Initial spec |
