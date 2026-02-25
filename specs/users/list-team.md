# List Team Members Spec

---

## Overview

**Feature:** List all users (team members) within the current tenant. Restricted to `clinic_owner` role. Supports pagination, filtering by role, active status, and text search on name/email. Supports sorting by name, role, or created_at.

**Domain:** users

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy.md), A-01 (authentication)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required -- resolved from JWT
- **Special rules:** Only clinic_owner can list team members. Other roles receive 403.

---

## Endpoint

```
GET /api/v1/users
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

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| page | No | integer | >= 1, default 1 | Page number | 1 |
| page_size | No | integer | 1-100, default 20 | Items per page | 20 |
| role | No | string | One of: clinic_owner, doctor, assistant, receptionist | Filter by role | doctor |
| is_active | No | boolean | true or false | Filter by active status | true |
| search | No | string | 1-100 characters | Search by name or email (case-insensitive partial match) | martinez |
| sort_by | No | string | One of: name, role, created_at. Default: name | Sort field | name |
| sort_order | No | string | One of: asc, desc. Default: asc | Sort direction | asc |

### Request Body Schema

None (GET request).

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "uuid",
      "email": "string",
      "name": "string",
      "role": "string",
      "is_active": "boolean",
      "last_login_at": "datetime | null",
      "avatar_url": "string | null"
    }
  ],
  "pagination": {
    "page": "integer",
    "page_size": "integer",
    "total_items": "integer",
    "total_pages": "integer"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "email": "dra.martinez@clinicasonrisa.co",
      "name": "Dra. Laura Martinez",
      "role": "doctor",
      "is_active": true,
      "last_login_at": "2026-02-24T10:30:00Z",
      "avatar_url": "https://s3.dentalos.co/avatars/f47ac10b.jpg"
    },
    {
      "id": "a23bc45d-67ef-8901-b234-567890abcdef",
      "email": "carlos.gomez@clinicasonrisa.co",
      "name": "Carlos Gomez",
      "role": "receptionist",
      "is_active": true,
      "last_login_at": "2026-02-23T15:00:00Z",
      "avatar_url": null
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 2,
    "total_pages": 1
  }
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
  "message": "Solo el propietario de la clinica puede listar los miembros del equipo."
}
```

#### 422 Unprocessable Entity
**When:** Invalid query parameter values.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "role": ["Rol no valido. Opciones: clinic_owner, doctor, assistant, receptionist."],
    "page": ["El numero de pagina debe ser mayor o igual a 1."]
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

1. Validate JWT and extract `user_id` and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id`.
3. Verify user role is `clinic_owner`; otherwise return 403.
4. Parse and validate query parameters via Pydantic `ListTeamQueryParams`.
5. Build base query: `SELECT id, email, name, role, is_active, last_login_at, avatar_url FROM users`.
6. Apply filters:
   a. If `role` is provided, add `WHERE role = :role`.
   b. If `is_active` is provided, add `WHERE is_active = :is_active`.
   c. If `search` is provided, add `WHERE (lower(name) LIKE :search_pattern OR lower(email) LIKE :search_pattern)` using `%{search.lower()}%`.
7. Count total matching rows for pagination metadata.
8. Apply sorting: `ORDER BY :sort_by :sort_order`.
9. Apply pagination: `LIMIT :page_size OFFSET (:page - 1) * :page_size`.
10. Execute query and serialize results via Pydantic `TeamMemberListItem`.
11. Return 200 with `data` array and `pagination` metadata.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| page | Integer >= 1 | "El numero de pagina debe ser mayor o igual a 1." |
| page_size | Integer 1-100 | "El tamano de pagina debe estar entre 1 y 100." |
| role | One of valid roles or omitted | "Rol no valido. Opciones: clinic_owner, doctor, assistant, receptionist." |
| is_active | Boolean or omitted | "El filtro is_active debe ser true o false." |
| search | 1-100 characters or omitted | "El termino de busqueda debe tener entre 1 y 100 caracteres." |
| sort_by | One of: name, role, created_at | "Campo de ordenamiento no valido. Opciones: name, role, created_at." |
| sort_order | One of: asc, desc | "Direccion de ordenamiento no valida. Opciones: asc, desc." |

**Business Rules:**

- Only `clinic_owner` can access this endpoint.
- All users in the tenant are returned, including the clinic_owner themselves.
- The search filter uses case-insensitive `LIKE` with `%` wildcards on both sides.
- Default sort is by `name ASC`.
- Sensitive fields (password_hash, failed_login_attempts, locked_until) are NEVER included in the response.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant has only one user (the clinic_owner) | Return single-item array with pagination total_items = 1. |
| Search term matches no users | Return empty data array, total_items = 0. |
| page exceeds total_pages | Return empty data array with correct pagination metadata. |
| Search with special SQL characters (%, _) | Characters are escaped in the LIKE pattern to prevent injection. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None. This is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- None. Team listing is not cached due to frequent changes and filter/sort variability.

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No -- team listing is a routine admin operation.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 100ms
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** No caching (filter/sort combinations make cache impractical)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 2 (COUNT query + data query)

**Indexes required:**
- `users.role` -- INDEX (already exists: `idx_users_role`)
- `users.is_active` -- INDEX (already exists: `idx_users_is_active`)
- `users.email` -- UNIQUE INDEX on `lower(email)` (already exists: `idx_users_email`)

**N+1 prevention:** Not applicable (single query, no joins needed).

### Pagination

**Pagination:** Yes

- **Style:** offset-based
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| search | Pydantic strip + max length; LIKE wildcards `%` and `_` are escaped | Prevents SQL wildcard injection |
| role | Pydantic enum validator | Only valid role values accepted |
| page, page_size | Pydantic integer validators | Constrained to valid ranges |
| sort_by, sort_order | Pydantic enum validators | Only allowed column names; prevents SQL injection in ORDER BY |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL. Sort columns are mapped from validated enum values, not interpolated.

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
1. List all team members (default params)
   - **Given:** Authenticated clinic_owner, tenant has 5 users
   - **When:** GET /api/v1/users
   - **Then:** 200, 5 items returned, default sort by name asc, pagination metadata correct

2. Filter by role
   - **Given:** Tenant has 2 doctors, 1 receptionist, 1 assistant, 1 clinic_owner
   - **When:** GET /api/v1/users?role=doctor
   - **Then:** 200, 2 items returned, both with role "doctor"

3. Search by name
   - **Given:** Tenant has "Dra. Laura Martinez" and "Carlos Gomez"
   - **When:** GET /api/v1/users?search=martinez
   - **Then:** 200, 1 item returned matching "Martinez"

4. Paginated results
   - **Given:** Tenant has 25 users
   - **When:** GET /api/v1/users?page=2&page_size=10
   - **Then:** 200, 10 items on page 2, total_items=25, total_pages=3

5. Sort by created_at descending
   - **Given:** Tenant has multiple users
   - **When:** GET /api/v1/users?sort_by=created_at&sort_order=desc
   - **Then:** 200, users sorted newest first

#### Edge Cases
1. Empty tenant (only clinic_owner)
   - **Given:** Tenant has only the clinic_owner
   - **When:** GET /api/v1/users
   - **Then:** 200, 1 item (the clinic_owner), total_items=1

2. Search with no matches
   - **Given:** No users matching "zzz"
   - **When:** GET /api/v1/users?search=zzz
   - **Then:** 200, empty data array, total_items=0

3. Page beyond total
   - **Given:** 5 users, page_size=20
   - **When:** GET /api/v1/users?page=2
   - **Then:** 200, empty data array, total_items=5, total_pages=1

4. Filter is_active=false
   - **Given:** 1 deactivated user in tenant
   - **When:** GET /api/v1/users?is_active=false
   - **Then:** 200, only deactivated user(s) returned

#### Error Cases
1. Non-owner attempts to list team
   - **Given:** Authenticated doctor
   - **When:** GET /api/v1/users
   - **Then:** 403 Forbidden

2. Invalid role filter
   - **Given:** Authenticated clinic_owner
   - **When:** GET /api/v1/users?role=superadmin
   - **Then:** 422 Unprocessable Entity

3. Invalid page number
   - **Given:** Authenticated clinic_owner
   - **When:** GET /api/v1/users?page=0
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** 5+ users across all roles. At least 1 deactivated user.

**Patients/Entities:** None.

### Mocking Strategy

- Database: Use test tenant schema with seeded users.
- No external service mocks needed.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Only clinic_owner can access GET /api/v1/users
- [ ] Response includes correct fields (id, email, name, role, is_active, last_login_at, avatar_url)
- [ ] Filtering by role, is_active, and search works correctly
- [ ] Sorting by name, role, and created_at works in both directions
- [ ] Offset-based pagination works with correct metadata
- [ ] Sensitive fields are never exposed
- [ ] All query parameters are validated with Spanish error messages
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Viewing full profile of a single team member (see U-04: get-team-member.md)
- Inviting new team members (auth domain, user-invites spec)
- Updating team member roles or deactivating (see U-05, U-06)
- Cursor-based pagination (offset-based is sufficient for small team sizes, typically < 50 users)

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
