# Get Own Profile Spec

---

## Overview

**Feature:** Retrieve the authenticated user's own profile, including personal data, role, professional details (for doctors), and account status. Cached for 5 minutes in Redis.

**Domain:** users

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy.md), A-01 (authentication)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required -- resolved from JWT
- **Special rules:** None. Any authenticated user can read their own profile.

---

## Endpoint

```
GET /api/v1/users/me
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

None.

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

**Example:**
```json
{
  "error": "unauthorized",
  "message": "Token de acceso no valido o expirado."
}
```

#### 403 Forbidden
**When:** User's account is deactivated (`is_active=false`). Deactivated users cannot access any endpoint.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Su cuenta ha sido desactivada. Contacte al administrador de la clinica."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache error.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract `user_id` and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id` (cached in Redis, TTL 5 min).
3. Check Redis cache for key `tenant:{tenant_id}:user:{user_id}:profile`.
4. If cache hit, return cached data directly (skip DB query).
5. If cache miss, query `users` table: `SELECT id, email, name, phone, avatar_url, role, professional_license, specialties, is_active, email_verified, last_login_at, created_at FROM users WHERE id = :user_id`.
6. If user not found (should not happen for a valid JWT), return 401.
7. If `is_active = false`, return 403.
8. Serialize response via Pydantic `UserProfileResponse` model.
9. For non-doctor roles, `professional_license` and `specialties` return `null`.
10. Store result in Redis with TTL 300 seconds (5 min).
11. Return 200 with the profile payload.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| Authorization header | Must be a valid, non-expired JWT | "Token de acceso no valido o expirado." |

**Business Rules:**

- Any authenticated user can read their own profile regardless of role.
- `professional_license` and `specialties` are only populated for users with `role = 'doctor'`; for other roles they are serialized as `null`.
- Deactivated users (`is_active = false`) are rejected at the auth middleware layer with 403.
- The `password_hash`, `failed_login_attempts`, and `locked_until` fields are NEVER exposed in the response.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| User was deactivated between JWT issuance and request | Return 403. Auth middleware checks `is_active`. |
| User record deleted (hard delete -- should not happen) | Return 401 as if token is invalid. |
| Redis cache unavailable | Fallback to direct DB query. Log warning. Do not fail the request. |
| Doctor with empty specialties array | Return `"specialties": []` (empty list, not null). |

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

**Audit entry:** No -- routine self-profile reads are not audit-logged to avoid log bloat.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 50ms (cache hit), < 150ms (cache miss)
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** Redis cache
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
1. Doctor retrieves own profile (cache miss)
   - **Given:** Authenticated doctor user, empty cache
   - **When:** GET /api/v1/users/me
   - **Then:** 200 with full profile including `professional_license` and `specialties`

2. Receptionist retrieves own profile (cache hit)
   - **Given:** Authenticated receptionist, profile cached in Redis
   - **When:** GET /api/v1/users/me
   - **Then:** 200 with profile, `professional_license: null`, `specialties: null`

3. Clinic owner retrieves own profile
   - **Given:** Authenticated clinic_owner user
   - **When:** GET /api/v1/users/me
   - **Then:** 200 with profile, role = "clinic_owner"

#### Edge Cases
1. Redis unavailable -- graceful fallback
   - **Given:** Redis is down
   - **When:** GET /api/v1/users/me
   - **Then:** 200 from DB query; warning logged

2. Doctor with empty specialties
   - **Given:** Doctor with `specialties = '{}'` in DB
   - **When:** GET /api/v1/users/me
   - **Then:** 200 with `"specialties": []`

#### Error Cases
1. Missing Authorization header
   - **Given:** No JWT provided
   - **When:** GET /api/v1/users/me
   - **Then:** 401 Unauthorized

2. Expired JWT
   - **Given:** JWT with past expiration
   - **When:** GET /api/v1/users/me
   - **Then:** 401 Unauthorized

3. Deactivated user
   - **Given:** User with `is_active = false`
   - **When:** GET /api/v1/users/me
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** One user per role (clinic_owner, doctor, assistant, receptionist). One deactivated user.

**Patients/Entities:** None.

### Mocking Strategy

- Redis: Use `fakeredis` for cache tests; disconnect mock for fallback test.
- Database: Use test tenant schema with seeded users.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Authenticated user can retrieve their own profile via GET /api/v1/users/me
- [ ] Response includes all specified fields
- [ ] Doctor-specific fields return null for non-doctor roles
- [ ] Response is cached in Redis for 5 minutes
- [ ] Cache fallback to DB works when Redis is unavailable
- [ ] Deactivated users receive 403
- [ ] Sensitive fields (password_hash, failed_login_attempts, locked_until) are never exposed
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Updating profile data (see U-02: update-profile.md)
- Viewing other users' profiles (see U-04: get-team-member.md)
- Uploading or changing avatar images (handled in U-02)
- Password change or email verification flows (auth domain)

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
