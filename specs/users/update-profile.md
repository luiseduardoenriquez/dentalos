# Update Own Profile Spec

---

## Overview

**Feature:** Allow an authenticated user to update their own profile fields (name, phone, avatar, and doctor-specific fields). Email and role are immutable via this endpoint. Avatar uploads go to S3. Invalidates the profile cache on success.

**Domain:** users

**Priority:** Critical

**Dependencies:** U-01 (get-profile.md), I-01 (multi-tenancy.md), A-01 (authentication)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required -- resolved from JWT
- **Special rules:** Doctors can update `professional_license` and `specialties`. Non-doctors submitting those fields receive a 403.

---

## Endpoint

```
PUT /api/v1/users/me
```

**Rate Limiting:**
- 20 requests per minute per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | multipart/form-data or application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_a1b2c3d4e5f6 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

When using `application/json` (no avatar upload):
```json
{
  "name": "string (optional, 2-200 chars)",
  "phone": "string (optional, E.164 format, max 20 chars)",
  "professional_license": "string (optional, doctors only, max 50 chars)",
  "specialties": ["string"] "(optional, doctors only, max 10 items, each max 100 chars)"
}
```

When using `multipart/form-data` (with avatar upload):
- `avatar` (file, optional): Image file. Max 5 MB. Allowed types: image/jpeg, image/png, image/webp.
- `name` (string, optional)
- `phone` (string, optional)
- `professional_license` (string, optional, doctors only)
- `specialties` (JSON string array, optional, doctors only)

**Example Request (JSON):**
```json
{
  "name": "Dra. Laura Martinez Gomez",
  "phone": "+573009876543",
  "specialties": ["ortodoncia", "endodoncia", "implantologia"]
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
  "email": "dra.martinez@clinicasonrisa.co",
  "name": "Dra. Laura Martinez Gomez",
  "phone": "+573009876543",
  "avatar_url": "https://s3.dentalos.co/avatars/f47ac10b-58cc-4372-a567-0e02b2c3d479.webp",
  "role": "doctor",
  "professional_license": "TP-12345-CO",
  "specialties": ["ortodoncia", "endodoncia", "implantologia"],
  "is_active": true,
  "email_verified": true,
  "last_login_at": "2026-02-24T10:30:00Z",
  "created_at": "2025-11-01T08:00:00Z"
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
**When:** Non-doctor user attempts to update `professional_license` or `specialties`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo los doctores pueden actualizar la licencia profesional y especialidades."
}
```

#### 413 Payload Too Large
**When:** Avatar file exceeds 5 MB.

**Example:**
```json
{
  "error": "file_too_large",
  "message": "El archivo excede el tamano maximo permitido de 5 MB."
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
    "phone": ["Formato de telefono no valido. Use formato E.164 (ej: +573001234567)."],
    "name": ["El nombre debe tener entre 2 y 200 caracteres."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** S3 upload failure or unexpected database error.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract `user_id` and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id`.
3. Parse and validate request body via Pydantic `UpdateProfileRequest` schema.
4. If `professional_license` or `specialties` are present and user role is not `doctor`, return 403.
5. If avatar file is included:
   a. Validate file type (jpeg, png, webp only) and size (max 5 MB).
   b. Generate S3 key: `tenants/{tenant_id}/avatars/{user_id}.{ext}`.
   c. Upload file to S3 with `public-read` ACL.
   d. If previous avatar existed, delete old S3 object.
   e. Set `avatar_url` to the new S3 public URL.
6. Build UPDATE statement with only provided (non-null) fields.
7. Set `updated_at = now()`.
8. Execute UPDATE on `users` table: `UPDATE users SET ... WHERE id = :user_id`.
9. Invalidate Redis cache key `tenant:{tenant_id}:user:{user_id}:profile`.
10. Fetch the updated row and serialize via `UserProfileResponse`.
11. Return 200 with the updated profile.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| name | 2-200 characters, stripped of leading/trailing whitespace | "El nombre debe tener entre 2 y 200 caracteres." |
| phone | E.164 format regex `^\+[1-9]\d{6,14}$`, or null to clear | "Formato de telefono no valido. Use formato E.164 (ej: +573001234567)." |
| avatar | Max 5 MB, MIME type in [image/jpeg, image/png, image/webp] | "Tipo de archivo no permitido. Use JPEG, PNG o WebP." / "El archivo excede el tamano maximo permitido de 5 MB." |
| professional_license | Max 50 characters, alphanumeric with hyphens allowed | "La licencia profesional debe tener maximo 50 caracteres alfanumericos." |
| specialties | Array of strings, max 10 items, each max 100 chars | "Maximo 10 especialidades permitidas." / "Cada especialidad debe tener maximo 100 caracteres." |

**Business Rules:**

- Users CANNOT change their `email` or `role` via this endpoint.
- Only fields present in the request body are updated (partial update semantics).
- An empty request body (no changes) returns 200 with the current profile (no-op).
- If avatar is uploaded, the previous avatar file in S3 is deleted to avoid orphaned objects.
- `specialties` replaces the entire array (not a merge/append operation).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Empty request body | Return 200 with current profile unchanged. |
| Avatar upload with corrupt image | Return 422 with "Tipo de archivo no permitido." after MIME type validation. |
| S3 upload fails | Return 500. Do not commit DB changes. Log error to Sentry. |
| Concurrent profile updates | Last write wins (optimistic -- no version conflict needed for self-edits). |
| Name with only whitespace | Validation rejects: name must be 2-200 chars after strip. |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: UPDATE -- updates name, phone, avatar_url, professional_license, specialties, updated_at.

**Example query (SQLAlchemy):**
```python
stmt = (
    update(User)
    .where(User.id == user_id)
    .values(**update_data, updated_at=func.now())
    .returning(User)
)
result = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:profile`: DELETE -- invalidated on successful update.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No -- self-profile updates are not audit-logged (non-clinical data). Clinic owner updates to team members (U-05) are logged.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 200ms (without avatar), < 1000ms (with avatar upload)
- **Maximum acceptable:** < 2000ms (with avatar upload)

### Caching Strategy
- **Strategy:** Cache invalidation on write
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:profile`
- **TTL:** N/A (key is deleted, re-populated on next GET)
- **Invalidation:** On successful profile update.

### Database Performance

**Queries executed:** 1 (UPDATE ... RETURNING)

**Indexes required:**
- `users.id` -- PRIMARY KEY (already exists)

**N+1 prevention:** Not applicable (single row update).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| name | Pydantic `strip()`, max length validator | Prevents leading/trailing whitespace |
| phone | Pydantic regex validator (E.164) | Strict format validation |
| professional_license | Pydantic alphanum+hyphen regex, max 50 | Prevents injection |
| specialties | Pydantic list[str] with per-item max length | Array validated |
| avatar | MIME type check + file size check | Server-side validation regardless of Content-Type header |

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
1. Update name and phone
   - **Given:** Authenticated doctor
   - **When:** PUT /api/v1/users/me with `{"name": "Dr. Nuevo Nombre", "phone": "+573001111111"}`
   - **Then:** 200, name and phone updated in response and DB

2. Upload avatar image
   - **Given:** Authenticated user, multipart/form-data with JPEG avatar
   - **When:** PUT /api/v1/users/me with avatar file
   - **Then:** 200, `avatar_url` updated to new S3 URL

3. Doctor updates specialties
   - **Given:** Authenticated doctor
   - **When:** PUT /api/v1/users/me with `{"specialties": ["ortodoncia"]}`
   - **Then:** 200, specialties array replaced in response

4. Cache invalidated on update
   - **Given:** Profile cached in Redis
   - **When:** PUT /api/v1/users/me with name change
   - **Then:** Redis key deleted; next GET fetches from DB

#### Edge Cases
1. Empty request body
   - **Given:** Authenticated user
   - **When:** PUT /api/v1/users/me with `{}`
   - **Then:** 200, profile returned unchanged

2. Replace existing avatar
   - **Given:** User with existing avatar_url
   - **When:** PUT /api/v1/users/me with new avatar
   - **Then:** Old S3 object deleted, new URL returned

#### Error Cases
1. Non-doctor updates professional_license
   - **Given:** Authenticated receptionist
   - **When:** PUT /api/v1/users/me with `{"professional_license": "XYZ"}`
   - **Then:** 403 Forbidden

2. Avatar exceeds 5 MB
   - **Given:** Authenticated user, 10 MB image
   - **When:** PUT /api/v1/users/me with oversized avatar
   - **Then:** 413 Payload Too Large

3. Invalid phone format
   - **Given:** Authenticated user
   - **When:** PUT /api/v1/users/me with `{"phone": "12345"}`
   - **Then:** 422 Unprocessable Entity

4. Invalid avatar MIME type
   - **Given:** Authenticated user, PDF file as avatar
   - **When:** PUT /api/v1/users/me with PDF file
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** One user per role (clinic_owner, doctor, assistant, receptionist).

**Patients/Entities:** None.

### Mocking Strategy

- S3: Mock `boto3` S3 client. Verify upload key, ACL, and delete calls.
- Redis: Use `fakeredis` to verify cache invalidation.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Authenticated user can update their own name, phone, avatar
- [ ] Doctors can additionally update professional_license and specialties
- [ ] Non-doctors receive 403 when submitting doctor-specific fields
- [ ] Avatar uploads go to S3 with correct key pattern
- [ ] Old avatars are deleted from S3 on replacement
- [ ] Email and role cannot be changed via this endpoint
- [ ] Redis profile cache is invalidated on successful update
- [ ] All validation rules are enforced with Spanish error messages
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Changing email address (requires separate verification flow, auth domain)
- Changing password (auth domain)
- Changing role (admin-only, see U-05)
- Avatar image resizing or thumbnail generation (handled by S3 Lambda or deferred job)
- Bulk profile updates

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
