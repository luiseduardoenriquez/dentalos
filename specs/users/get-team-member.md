# Get Team Member Profile Spec

---

## Overview

**Feature:** Retrieve the full profile of any user (team member) within the current tenant. Restricted to `clinic_owner` role. Returns the same fields as the self-profile endpoint (U-01) but for any user in the tenant identified by `user_id`.

**Domain:** users

**Priority:** Critical

**Dependencies:** U-01 (get-profile.md), I-01 (multi-tenancy.md), A-01 (authentication)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required -- resolved from JWT
- **Special rules:** Only clinic_owner can view other users' full profiles. Other roles receive 403.

---

## Endpoint

```
GET /api/v1/users/{user_id}
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_a1b2c3d4e5f6 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| user_id | Yes | uuid | Valid UUID v4 | ID of the team member to retrieve | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

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
  "email": "dra.martinez@clinicasonrisa.co",
  "name": "Dra. Laura Martinez",
  "phone": "+573001234567",
  "avatar_url": "https://s3.dentalos.co/avatars/f47ac10b.jpg",
  "role": "doctor",
  "professional_license": "TP-12345-CO",
  "specialties": ["ortodoncia", "endodoncia"],
  "is_active": true,
  "email_verified": true,
  "last_login_at": "2026-02-24T10:30:00Z",
  "created_at": "2025-11-01T08:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure -- see infra/authentication-rules.md.

#### 403 Forbidden
**When:** Authenticated user does not have `clinic_owner` role.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede ver perfiles de otros miembros."
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
**When:** The `user_id` URL parameter is not a valid UUID.

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
**When:** Unexpected database or cache error.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract `requesting_user_id` and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id`.
3. Verify requesting user role is `clinic_owner`; otherwise return 403.
4. Validate `user_id` URL parameter is a valid UUID.
5. Check Redis cache for key `tenant:{tenant_id}:user:{user_id}:profile`.
6. If cache hit, return cached data directly (skip DB query).
7. If cache miss, query `users` table: `SELECT id, email, name, phone, avatar_url, role, professional_license, specialties, is_active, email_verified, last_login_at, created_at FROM users WHERE id = :user_id`.
8. If user not found, return 404.
9. Serialize response via Pydantic `UserProfileResponse` model.
10. For non-doctor users, `professional_license` and `specialties` return `null`.
11. Store result in Redis cache with TTL 300 seconds (5 min).
12. Return 200 with the profile payload.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| user_id | Valid UUID v4 format | "El ID de usuario debe ser un UUID valido." |

**Business Rules:**

- Only `clinic_owner` can access this endpoint.
- The target user must belong to the same tenant (guaranteed by schema isolation).
- `professional_license` and `specialties` are only populated for `role = 'doctor'`; for other roles they are `null`.
- The `password_hash`, `failed_login_attempts`, and `locked_until` fields are NEVER exposed.
- The clinic_owner CAN view their own profile via this endpoint (same result as U-01).
- Deactivated users are still returned (they exist in the tenant). The `is_active` field indicates their status.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Clinic_owner views their own profile via /users/{own_id} | Return 200. Same data as /users/me. |
| Target user is deactivated | Return 200 with `is_active: false`. Deactivated users are still queryable. |
| user_id is valid UUID but does not exist in tenant | Return 404. |
| user_id belongs to a different tenant | Return 404 (schema isolation prevents cross-tenant access). |
| Redis unavailable | Fallback to direct DB query. Log warning. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None. This is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:profile`: SET on cache miss -- stores serialized JSON profile.

**Cache TTL:** 300 seconds (5 minutes).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No -- routine admin profile lookups are not audit-logged.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 50ms (cache hit), < 150ms (cache miss)
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** Redis cache (shares the same cache key pattern as U-01)
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:profile`
- **TTL:** 300 seconds (5 minutes)
- **Invalidation:** On profile update (U-02), team member update (U-05), or deactivation (U-06).

### Database Performance

**Queries executed:** 0 (cache hit) or 1 (cache miss)

**Indexes required:**
- `users.id` -- PRIMARY KEY (already exists)

**N+1 prevention:** Not applicable (single row fetch).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| user_id | Pydantic UUID validator | Rejects non-UUID strings |
| Authorization header | JWT library validation | Standard Bearer token parsing |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) -- CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. User staff profiles are not PHI.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. Clinic_owner views a doctor's profile (cache miss)
   - **Given:** Authenticated clinic_owner, target doctor exists in tenant, cache empty
   - **When:** GET /api/v1/users/{doctor_id}
   - **Then:** 200 with full doctor profile including professional_license and specialties

2. Clinic_owner views a receptionist's profile (cache hit)
   - **Given:** Authenticated clinic_owner, receptionist profile cached
   - **When:** GET /api/v1/users/{receptionist_id}
   - **Then:** 200 with profile, professional_license and specialties are null

3. Clinic_owner views their own profile via this endpoint
   - **Given:** Authenticated clinic_owner
   - **When:** GET /api/v1/users/{own_id}
   - **Then:** 200 with own profile data

#### Edge Cases
1. View deactivated team member
   - **Given:** Target user has is_active = false
   - **When:** GET /api/v1/users/{deactivated_user_id}
   - **Then:** 200 with is_active = false in response

2. Redis unavailable -- graceful fallback
   - **Given:** Redis is down
   - **When:** GET /api/v1/users/{user_id}
   - **Then:** 200 from DB query; warning logged

3. Doctor with null specialties
   - **Given:** Doctor exists with specialties column as NULL
   - **When:** GET /api/v1/users/{doctor_id}
   - **Then:** 200 with `"specialties": null`

#### Error Cases
1. Non-owner attempts to view team member
   - **Given:** Authenticated doctor
   - **When:** GET /api/v1/users/{other_user_id}
   - **Then:** 403 Forbidden

2. User not found
   - **Given:** Authenticated clinic_owner, non-existent user_id
   - **When:** GET /api/v1/users/{random_uuid}
   - **Then:** 404 Not Found

3. Invalid UUID format
   - **Given:** Authenticated clinic_owner
   - **When:** GET /api/v1/users/not-a-uuid
   - **Then:** 422 Unprocessable Entity

4. Missing auth token
   - **Given:** No JWT
   - **When:** GET /api/v1/users/{user_id}
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** One clinic_owner, one doctor (with specialties), one doctor (without specialties), one assistant, one receptionist, one deactivated user.

**Patients/Entities:** None.

### Mocking Strategy

- Redis: Use `fakeredis` for cache tests; disconnect mock for fallback test.
- Database: Use test tenant schema with seeded users.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Only clinic_owner can access GET /api/v1/users/{user_id}
- [ ] Response includes all specified profile fields
- [ ] Doctor-specific fields return null for non-doctor roles
- [ ] Response is cached in Redis for 5 minutes (shared cache key with U-01)
- [ ] Cache fallback to DB works when Redis is unavailable
- [ ] Returns 404 for non-existent user_id within tenant
- [ ] Deactivated users are still returned with is_active = false
- [ ] Sensitive fields are never exposed
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Updating team member data (see U-05: update-team-member.md)
- Deactivating team members (see U-06: deactivate-user.md)
- Listing multiple users (see U-03: list-team.md)
- Cross-tenant user lookups (prohibited by schema isolation)
- Viewing patient profiles (patients domain)

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
