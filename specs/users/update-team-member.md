# Update Team Member Spec

---

## Overview

**Feature:** Allow the `clinic_owner` to update a team member's profile: name, role, phone, specialties, and is_active status. The clinic_owner cannot change their own role and cannot promote anyone to `clinic_owner`. All changes are recorded in the audit log.

**Domain:** users

**Priority:** Critical

**Dependencies:** U-04 (get-team-member.md), I-01 (multi-tenancy.md), A-01 (authentication)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required -- resolved from JWT
- **Special rules:** The clinic_owner cannot change their own role. Cannot assign `clinic_owner` role to another user.

---

## Endpoint

```
PUT /api/v1/users/{user_id}
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
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_a1b2c3d4e5f6 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| user_id | Yes | uuid | Valid UUID v4 | ID of the team member to update | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "name": "string (optional, 2-200 chars)",
  "role": "string (optional, one of: doctor, assistant, receptionist)",
  "phone": "string (optional, E.164 format, max 20 chars)",
  "specialties": ["string"] "(optional, max 10 items, each max 100 chars)",
  "is_active": "boolean (optional)"
}
```

**Example Request:**
```json
{
  "name": "Dr. Carlos Ramirez",
  "role": "doctor",
  "phone": "+573005551234",
  "specialties": ["cirugia oral", "periodoncia"]
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
  "phone": "string | null",
  "avatar_url": "string | null",
  "role": "string",
  "professional_license": "string | null",
  "specialties": ["string"] | null,
  "is_active": "boolean",
  "email_verified": "boolean",
  "last_login_at": "datetime | null",
  "created_at": "datetime"
}
```

**Example:**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "email": "carlos.ramirez@clinicasonrisa.co",
  "name": "Dr. Carlos Ramirez",
  "phone": "+573005551234",
  "avatar_url": "https://s3.dentalos.co/avatars/f47ac10b.jpg",
  "role": "doctor",
  "professional_license": null,
  "specialties": ["cirugia oral", "periodoncia"],
  "is_active": true,
  "email_verified": true,
  "last_login_at": "2026-02-23T15:00:00Z",
  "created_at": "2025-12-15T09:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Request body is malformed or cannot be parsed.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido."
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure -- see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Authenticated user is not `clinic_owner`, OR attempting to change own role, OR attempting to assign `clinic_owner` role.

**Examples:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede actualizar miembros del equipo."
}
```
```json
{
  "error": "forbidden",
  "message": "No puede cambiar su propio rol."
}
```
```json
{
  "error": "forbidden",
  "message": "No se puede asignar el rol de propietario de clinica a otro usuario."
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

#### 422 Unprocessable Entity
**When:** Validation failures on fields.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "role": ["Rol no valido. Opciones: doctor, assistant, receptionist."],
    "name": ["El nombre debe tener entre 2 y 200 caracteres."]
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
5. Parse and validate request body via Pydantic `UpdateTeamMemberRequest`.
6. Fetch target user from `users` table by `user_id`. If not found, return 404.
7. Apply business rule checks:
   a. If `requesting_user_id == user_id` and `role` field is present, return 403 ("No puede cambiar su propio rol.").
   b. If `role` is `clinic_owner`, return 403 ("No se puede asignar el rol de propietario de clinica a otro usuario.").
   c. If `specialties` is provided and the resulting role (new or existing) is not `doctor`, return 422 ("Especialidades solo aplican para el rol de doctor.").
8. Capture old values for audit log (snapshot of fields being changed).
9. Build UPDATE statement with only provided (non-null) fields.
10. Set `updated_at = now()`.
11. Execute UPDATE: `UPDATE users SET ... WHERE id = :user_id`.
12. If `role` was changed from `doctor` to a non-doctor role, clear `professional_license` and `specialties`.
13. If `is_active` was changed to `false`, revoke all active sessions (see U-06 pattern).
14. Invalidate Redis cache key `tenant:{tenant_id}:user:{user_id}:profile`.
15. Write audit log entry with old and new values.
16. Fetch updated user and serialize via `UserProfileResponse`.
17. Return 200 with the updated profile.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| user_id | Valid UUID v4 format | "El ID de usuario debe ser un UUID valido." |
| name | 2-200 characters, stripped of whitespace | "El nombre debe tener entre 2 y 200 caracteres." |
| role | One of: doctor, assistant, receptionist (NOT clinic_owner) | "Rol no valido. Opciones: doctor, assistant, receptionist." |
| phone | E.164 format regex `^\+[1-9]\d{6,14}$`, or null to clear | "Formato de telefono no valido. Use formato E.164 (ej: +573001234567)." |
| specialties | Array of strings, max 10 items, each max 100 chars | "Maximo 10 especialidades permitidas." / "Cada especialidad debe tener maximo 100 caracteres." |
| is_active | Boolean | "El campo is_active debe ser true o false." |

**Business Rules:**

- Only `clinic_owner` can update team members.
- The `clinic_owner` CANNOT change their own role (prevents accidental demotion or lockout).
- The `clinic_owner` CANNOT assign the `clinic_owner` role to another user (role transfer is not supported via this endpoint).
- When changing a user's role FROM `doctor` to a non-doctor role, `professional_license` and `specialties` are automatically cleared.
- When setting `specialties` on a user who is not (and will not become) a doctor, return 422.
- Email CANNOT be changed via this endpoint.
- Setting `is_active = false` also revokes all active sessions for that user.
- All changes are recorded in the audit log with before/after values.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Clinic_owner tries to change own role | Return 403. |
| Changing role from doctor to assistant | Clear specialties and professional_license automatically. |
| Setting specialties while also changing role to receptionist | Return 422 (specialties incompatible with receptionist role). |
| Empty request body | Return 200 with unchanged profile (no-op). |
| Deactivating via is_active=false | Revoke sessions AND update is_active. Same user can be reactivated later via is_active=true. |
| Reactivating a deactivated user | Set is_active=true. User must log in again (sessions were revoked). |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: UPDATE -- updates name, role, phone, specialties, is_active, professional_license, updated_at.
- `user_sessions`: UPDATE -- sets `is_revoked = true` for all sessions if `is_active` changed to `false`.
- `audit_log`: INSERT -- records the change with old and new values.

**Example query (SQLAlchemy):**
```python
stmt = (
    update(User)
    .where(User.id == user_id)
    .values(**update_data, updated_at=func.now())
    .returning(User)
)
result = await session.execute(stmt)

# If deactivating, revoke sessions
if update_data.get("is_active") is False:
    await session.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.is_revoked == False)
        .values(is_revoked=True)
    )

# Audit log
audit_entry = AuditLog(
    user_id=requesting_user_id,
    action="update",
    resource_type="user",
    resource_id=user_id,
    old_value=old_values_json,
    new_value=new_values_json,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
)
session.add(audit_entry)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:profile`: DELETE -- invalidated on successful update.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes -- see infra/audit-logging.md.

- **Action:** update
- **Resource:** user
- **PHI involved:** No

### Notifications

**Notifications triggered:** No. (Future: in-app notification to the affected user when their role changes.)

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Cache invalidation on write
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:profile`
- **TTL:** N/A (key is deleted, re-populated on next GET)
- **Invalidation:** On successful team member update.

### Database Performance

**Queries executed:** 2-4 (SELECT target user, UPDATE user, optional UPDATE sessions, INSERT audit_log)

**Indexes required:**
- `users.id` -- PRIMARY KEY (already exists)
- `user_sessions.user_id` -- INDEX (already exists: `idx_user_sessions_user_id`)

**N+1 prevention:** Not applicable (single user update, no joins).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| user_id | Pydantic UUID validator | Rejects non-UUID strings |
| name | Pydantic strip() + max length | Prevents whitespace-only names |
| role | Pydantic enum validator | Only valid non-owner roles accepted |
| phone | Pydantic regex validator (E.164) | Strict format validation |
| specialties | Pydantic list[str] with per-item validation | Array and item lengths validated |
| is_active | Pydantic bool validator | Type-enforced |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. User staff profiles are not PHI.

**Audit requirement:** Write-only logged (all changes audited).

---

## Testing

### Test Cases

#### Happy Path
1. Update team member name and phone
   - **Given:** Authenticated clinic_owner, target user exists
   - **When:** PUT /api/v1/users/{user_id} with `{"name": "New Name", "phone": "+573001111111"}`
   - **Then:** 200, fields updated, audit log written

2. Change role from assistant to doctor
   - **Given:** Authenticated clinic_owner, target is assistant
   - **When:** PUT /api/v1/users/{user_id} with `{"role": "doctor"}`
   - **Then:** 200, role changed to doctor

3. Change role from doctor to receptionist
   - **Given:** Authenticated clinic_owner, target is doctor with specialties
   - **When:** PUT /api/v1/users/{user_id} with `{"role": "receptionist"}`
   - **Then:** 200, role changed, specialties and professional_license cleared

4. Deactivate team member
   - **Given:** Authenticated clinic_owner, target user is active
   - **When:** PUT /api/v1/users/{user_id} with `{"is_active": false}`
   - **Then:** 200, is_active=false, all sessions revoked, audit logged

5. Reactivate team member
   - **Given:** Authenticated clinic_owner, target user is_active=false
   - **When:** PUT /api/v1/users/{user_id} with `{"is_active": true}`
   - **Then:** 200, is_active=true, audit logged

#### Edge Cases
1. Empty request body
   - **Given:** Authenticated clinic_owner
   - **When:** PUT /api/v1/users/{user_id} with `{}`
   - **Then:** 200, no changes, no audit entry

2. Set specialties while changing to doctor
   - **Given:** Target is currently receptionist
   - **When:** PUT /api/v1/users/{user_id} with `{"role": "doctor", "specialties": ["ortodoncia"]}`
   - **Then:** 200, role=doctor, specialties set

#### Error Cases
1. Non-owner attempts update
   - **Given:** Authenticated doctor
   - **When:** PUT /api/v1/users/{user_id}
   - **Then:** 403 Forbidden

2. Clinic_owner tries to change own role
   - **Given:** Authenticated clinic_owner
   - **When:** PUT /api/v1/users/{own_id} with `{"role": "doctor"}`
   - **Then:** 403 Forbidden

3. Attempt to assign clinic_owner role
   - **Given:** Authenticated clinic_owner
   - **When:** PUT /api/v1/users/{user_id} with `{"role": "clinic_owner"}`
   - **Then:** 403 Forbidden

4. Target user not found
   - **Given:** Authenticated clinic_owner
   - **When:** PUT /api/v1/users/{non_existent_id}
   - **Then:** 404 Not Found

5. Set specialties for non-doctor
   - **Given:** Target is receptionist, not changing role
   - **When:** PUT /api/v1/users/{user_id} with `{"specialties": ["ortodoncia"]}`
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** One clinic_owner, two doctors (one with specialties), one assistant, one receptionist, one deactivated user.

**Patients/Entities:** None.

### Mocking Strategy

- Redis: Use `fakeredis` to verify cache invalidation.
- Database: Use test tenant schema with seeded users. Verify audit_log entries.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Only clinic_owner can access PUT /api/v1/users/{user_id}
- [ ] Name, role, phone, specialties, and is_active can be updated
- [ ] Clinic_owner cannot change their own role
- [ ] Clinic_owner cannot assign clinic_owner role to anyone
- [ ] Changing from doctor to non-doctor clears specialties and professional_license
- [ ] Setting is_active=false revokes all user sessions
- [ ] All changes are recorded in audit_log with old/new values
- [ ] Redis profile cache is invalidated on update
- [ ] Email cannot be changed via this endpoint
- [ ] All validation rules enforced with Spanish error messages
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Self-profile updates (see U-02: update-profile.md)
- Dedicated deactivation endpoint with appointment warnings (see U-06: deactivate-user.md)
- Changing user email address (requires separate verification flow)
- Transferring clinic_owner role (separate admin flow, not yet specified)
- Avatar upload for team members (team members manage their own avatar via U-02)

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
