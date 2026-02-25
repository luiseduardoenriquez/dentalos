# Tenant Suspend Spec

---

## Overview

**Feature:** Superadmin endpoint to suspend a tenant. Sets status to `suspended`, which makes the tenant read-only (writes blocked by TenantMiddleware). Invalidates all caches and logs an audit entry. The tenant's users can still log in and read data for export purposes.

**Domain:** tenants

**Priority:** High

**Spec ID:** T-05

**Dependencies:** T-01 (tenant-provision.md), T-04 (tenant-update.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required (superadmin operates on `public` schema)
- **Special rules:** None

---

## Endpoint

```
POST /api/v1/superadmin/tenants/{tenant_id}/suspend
```

**Rate Limiting:**
- 10 requests per minute per superadmin user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT (superadmin) | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| tenant_id | Yes | uuid | Valid UUID v4 | Tenant identifier | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "reason": "string (required) — reason for suspension",
  "notify_owner": "boolean (optional, default true) — send email to owner"
}
```

**Example Request:**
```json
{
  "reason": "Falta de pago por más de 30 días.",
  "notify_owner": true
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
  "slug": "string",
  "name": "string",
  "status": "suspended",
  "suspended_at": "datetime",
  "suspension_reason": "string",
  "message": "string"
}
```

**Example:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "slug": "clinica-sonrisa",
  "name": "Clínica Dental Sonrisa",
  "status": "suspended",
  "suspended_at": "2026-02-24T16:00:00Z",
  "suspension_reason": "Falta de pago por más de 30 días.",
  "message": "Tenant suspendido exitosamente. Acceso de solo lectura habilitado."
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing or empty reason field.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Datos de entrada inválidos.",
  "details": {
    "reason": ["La razón de suspensión es obligatoria."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or invalid superadmin JWT.

#### 403 Forbidden
**When:** JWT does not belong to a superadmin user.

#### 404 Not Found
**When:** Tenant with the given `tenant_id` does not exist.

**Example:**
```json
{
  "error": "tenant_not_found",
  "message": "No se encontró el tenant con el ID proporcionado."
}
```

#### 409 Conflict
**When:** Tenant is already suspended, or is in a non-suspendable state (provisioning, cancelled).

**Example:**
```json
{
  "error": "invalid_status_transition",
  "message": "El tenant ya se encuentra suspendido."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

---

## Business Logic

**Step-by-step process:**

1. Validate `tenant_id` as a valid UUID.
2. Validate request body against Pydantic schema (`TenantSuspendRequest`).
3. Authenticate superadmin from JWT claims.
4. Load tenant from `public.tenants` WHERE `id = tenant_id`.
5. If not found, return 404.
6. Validate current status allows suspension:
   - `active` -> `suspended`: allowed
   - `suspended` -> `suspended`: return 409 (already suspended)
   - `provisioning` -> `suspended`: return 409 (cannot suspend during provisioning)
   - `cancelled` -> `suspended`: return 409 (cancelled is terminal)
7. Update `public.tenants`:
   - `status = 'suspended'`
   - `suspended_at = now()`
   - `settings['suspension_reason'] = reason`
   - `updated_at = now()`
8. Invalidate all Redis cache keys for this tenant:
   - `tenant:{tenant_id}:info`
   - `tenant:{tenant_id}:plan`
   - `tenant:{tenant_id}:settings`
9. Revoke all active user sessions by dispatching a session invalidation job.
10. Log audit entry (platform-level).
11. If `notify_owner = true`, dispatch suspension email.
12. Return success response.

**Post-suspension behavior (enforced by TenantMiddleware):**

- GET/HEAD/OPTIONS requests: allowed (read-only access)
- POST/PUT/PATCH/DELETE requests: blocked with 403 `tenant_suspended` error
- Login: allowed (users can still authenticate to export data)
- New user invites: blocked
- Appointment scheduling: blocked
- Patient creation: blocked

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| tenant_id | Valid UUID v4 | ID de tenant inválido. |
| reason | 5-500 characters | La razón de suspensión debe tener entre 5 y 500 caracteres. |
| notify_owner | Boolean | Valor booleano inválido. |

**Business Rules:**

- Suspension is reversible (superadmin can reactivate via T-04 PUT with status=active).
- Suspended tenants retain all data. No data is deleted.
- Active user sessions are invalidated to force re-authentication (new tokens will reflect suspended status).
- The suspension reason is stored in the tenant's settings JSONB for audit purposes.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant has active appointments in the future | Suspension proceeds. Appointments remain but no new ones can be created. Existing reminders continue. |
| Owner is currently logged in | Session invalidation forces re-login. Next login works but writes are blocked. |
| Suspending a tenant with ongoing async jobs | Jobs complete but no new jobs can be dispatched from the tenant. |
| Double suspension request | 409 Conflict, idempotent protection. |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `public.tenants`: UPDATE — status, suspended_at, settings (reason), updated_at

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:info`: INVALIDATE
- `tenant:{tenant_id}:plan`: INVALIDATE
- `tenant:{tenant_id}:settings`: INVALIDATE
- `tenant:{tenant_id}:sessions:*`: INVALIDATE (all user sessions)

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| auth | sessions.invalidate_all | { tenant_id } | Always on suspension |
| notifications | tenant.suspended_notice | { tenant_id, owner_email, reason, suspended_at } | When notify_owner = true |

### Audit Log

**Audit entry:** Yes — platform-level audit.

- **Action:** update
- **Resource:** tenant
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes (conditional)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | tenant_suspended | owner_email | When notify_owner = true |

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Full cache invalidation for the tenant
- **Cache key:** All `tenant:{tenant_id}:*` keys
- **TTL:** N/A
- **Invalidation:** Immediate

### Database Performance

**Queries executed:** 2 (load tenant, update tenant)

**Indexes required:**
- `public.tenants.id` — PRIMARY KEY

**N+1 prevention:** Not applicable (single resource)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| tenant_id | Pydantic UUID validator | Only valid UUIDs |
| reason | Pydantic strip, max 500 chars | HTML stripped |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** Write-only logged (superadmin action, state change)

---

## Testing

### Test Cases

#### Happy Path
1. Suspend active tenant
   - **Given:** Tenant is active
   - **When:** POST /api/v1/superadmin/tenants/{id}/suspend with valid reason
   - **Then:** 200 OK, status=suspended, cache invalidated, email sent

2. Suspend without notification
   - **Given:** Tenant is active
   - **When:** POST with notify_owner=false
   - **Then:** 200 OK, status=suspended, no email dispatched

#### Edge Cases
1. Tenant has future appointments
   - **Given:** Tenant has 10 upcoming appointments
   - **When:** Suspend
   - **Then:** Suspension succeeds, appointments preserved but no new scheduling

#### Error Cases
1. Already suspended
   - **Given:** Tenant is already suspended
   - **When:** POST suspend
   - **Then:** 409 Conflict

2. Cancelled tenant
   - **Given:** Tenant is cancelled
   - **When:** POST suspend
   - **Then:** 409 Conflict

3. Missing reason
   - **Given:** Empty request body
   - **When:** POST suspend
   - **Then:** 400 Bad Request

4. Non-superadmin
   - **Given:** Regular user JWT
   - **When:** POST
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** One superadmin user

**Entities:** Tenants in active, suspended, and cancelled statuses

### Mocking Strategy

- RabbitMQ: Mock queue publisher
- Redis: Mock or use test Redis instance
- Email: Mock email service

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Superadmin can suspend an active tenant
- [ ] Suspended tenant is read-only (writes blocked by middleware)
- [ ] All caches invalidated
- [ ] User sessions invalidated
- [ ] Suspension email sent when notify_owner=true
- [ ] Audit entry created
- [ ] Already-suspended returns 409
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Tenant reactivation (handled by T-04 tenant-update with status=active)
- Automatic suspension via billing webhook
- Data export during suspension period
- Grace period logic before permanent deletion

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
- [x] Audit trail for superadmin action

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (full invalidation)
- [x] DB queries optimized (indexes listed)
- [x] Pagination not needed

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
