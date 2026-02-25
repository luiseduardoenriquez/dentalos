# N-02 — Notification Mark Read Spec

---

## Overview

**Feature:** Mark a single in-app notification as read for the currently authenticated user. Updates `read_at` timestamp on the notification record and invalidates the unread count cache. Returns the updated notification object.

**Domain:** notifications

**Priority:** Medium

**Dependencies:** N-01 (notification-list), A-01 (login), infra/authentication-rules.md, infra/caching-strategy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** A user can only mark their own notifications as read. Attempting to mark another user's notification returns 404 (not 403) to avoid information disclosure about notification existence.

---

## Endpoint

```
POST /api/v1/notifications/{notification_id}/read
```

**Rate Limiting:**
- 120 requests per minute per user
- Burst: 20 requests per 5 seconds per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Tenant identifier (auto-resolved from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| notification_id | Yes | string (UUID v4) | Valid UUID format | ID of the notification to mark as read | `a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6` |

### Query Parameters

None.

### Request Body Schema

None. POST with no body — the action is expressed entirely through the URL.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "uuid",
  "type": "string (notification type enum)",
  "title": "string",
  "body": "string",
  "read_at": "string (ISO 8601 datetime — now set)",
  "created_at": "string (ISO 8601 datetime)",
  "metadata": {
    "resource_type": "string",
    "resource_id": "string | null",
    "action_url": "string | null"
  }
}
```

**Example:**
```json
{
  "id": "a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6",
  "type": "appointment_reminder",
  "title": "Recordatorio de cita",
  "body": "Tiene una cita mañana a las 10:00 AM con el Dr. García.",
  "read_at": "2026-02-25T09:15:32Z",
  "created_at": "2026-02-25T08:00:00Z",
  "metadata": {
    "resource_type": "appointment",
    "resource_id": "b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7",
    "action_url": "/agenda/b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7"
  }
}
```

**Note:** If the notification is already marked as read, the existing `read_at` timestamp is preserved (idempotent — returns 200 with the current state, no update performed).

### Error Responses

#### 400 Bad Request
**When:** `notification_id` is not a valid UUID format.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "El identificador de notificación no tiene un formato válido.",
  "details": {
    "notification_id": ["Debe ser un UUID válido (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. See `infra/authentication-rules.md`.

#### 404 Not Found
**When:** No notification with the given `notification_id` exists for the current user in the current tenant schema. This also covers the case where the notification belongs to a different user (to avoid information disclosure).

**Example:**
```json
{
  "error": "notificacion_no_encontrada",
  "message": "La notificación solicitada no existe o no tiene acceso a ella.",
  "details": {}
}
```

#### 422 Unprocessable Entity
**When:** `notification_id` path parameter is syntactically valid UUID but database lookup logic fails due to unexpected format edge case (should not occur in normal flow — covered by 400).

**Example:**
```json
{
  "error": "validacion_fallida",
  "message": "Se encontraron errores de validación.",
  "details": {
    "notification_id": ["Formato de UUID no reconocido."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Database write failure, Redis cache invalidation failure (non-fatal — log and continue), or unhandled exception.

---

## Business Logic

**Step-by-step process:**

1. Validate and parse JWT — extract `user_id`, `tenant_id`, `role` from claims.
2. Validate `notification_id` path parameter — must be a valid UUID v4. Return 400 if not.
3. Within the tenant schema, query: `SELECT * FROM notifications WHERE id = :notification_id AND user_id = :user_id AND deleted_at IS NULL`. Return 404 if no row found.
4. Check if `read_at` is already set. If `read_at IS NOT NULL`, skip the UPDATE and return the existing notification (idempotent behavior).
5. If `read_at IS NULL`, execute: `UPDATE notifications SET read_at = NOW() WHERE id = :notification_id AND user_id = :user_id`. Use `RETURNING *` clause to get the updated row in a single round-trip.
6. Invalidate Redis cache key `tenant:{tenant_id}:user:{user_id}:notifications:unread_count` (DELETE).
7. Invalidate Redis cache pattern `tenant:{tenant_id}:user:{user_id}:notifications:list:*` (SCAN + DEL pattern).
8. Serialize and return the updated notification with 200 OK.
9. Emit structured log entry: `{"action": "notification.read", "notification_id": "...", "user_id": "...", "tenant_id": "..."}`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| notification_id | Must match UUID v4 pattern | El identificador de notificación no tiene un formato válido. |
| notification_id | Must exist in tenant schema for the current user | La notificación solicitada no existe o no tiene acceso a ella. |

**Business Rules:**

- The operation is idempotent. Calling this endpoint multiple times on an already-read notification returns 200 with the existing `read_at` value without re-updating the database.
- A user cannot mark another user's notification as read, even if they know the UUID. The query always includes `AND user_id = :user_id`.
- Soft-deleted notifications (`deleted_at IS NOT NULL`) return 404 as if they do not exist.
- The `read_at` timestamp is set to database `NOW()` in the tenant's timezone context, not the client's time.
- No partial success states — the operation is atomic. Either the notification is marked read and caches invalidated, or nothing changes and an error is returned.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Notification already read | Returns 200 with existing `read_at`, no DB UPDATE performed |
| Notification ID exists but belongs to another user in same tenant | Returns 404 (no information disclosure) |
| Valid UUID that has never existed | Returns 404 |
| Redis cache invalidation fails | Logs warning, does not return 500 — notification still marked read in DB |
| Concurrent requests to mark same notification read | Database UPDATE is idempotent; both requests return 200 |
| Notification soft-deleted before request completes | Returns 404 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `notifications`: UPDATE — sets `read_at = NOW()` where `id = :notification_id AND user_id = :user_id AND read_at IS NULL`.

**Example query (SQLAlchemy):**
```python
from sqlalchemy import update, select, and_
from app.models.notifications import Notification
import datetime

# Check existence and ownership
stmt_get = (
    select(Notification)
    .where(
        and_(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.deleted_at.is_(None),
        )
    )
)
result = await session.execute(stmt_get)
notification = result.scalar_one_or_none()
if not notification:
    raise NotFoundError("notificacion_no_encontrada")

# Idempotent update
if notification.read_at is None:
    stmt_update = (
        update(Notification)
        .where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
        .values(read_at=datetime.datetime.utcnow())
        .returning(Notification)
    )
    result = await session.execute(stmt_update)
    notification = result.scalar_one()
    await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:notifications:unread_count`: DELETE — invalidated so next N-01 request recomputes.
- `tenant:{tenant_id}:user:{user_id}:notifications:list:*`: INVALIDATE pattern — all list cache variants cleared.

**Cache TTL:** N/A (invalidation, not setting).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — marking a notification as read is not a PHI-modifying action. The underlying resources (appointments, invoices, etc.) maintain their own audit logs.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 100ms
- **Maximum acceptable:** < 250ms

### Caching Strategy
- **Strategy:** This endpoint writes, so it primarily invalidates rather than reads from cache.
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:notifications:unread_count` (DELETE on write)
- **TTL:** N/A
- **Invalidation:** Deletes unread_count key and all list cache variants for this user on every successful write.

### Database Performance

**Queries executed:** 2 (SELECT for existence check + UPDATE with RETURNING)

**Indexes required:**
- `notifications.(id, user_id, deleted_at)` — Primary lookup index (id is PK, composite with user_id + deleted_at for security filter)
- `notifications.(user_id, read_at)` — Supports unread count queries triggered by cache invalidation

**N+1 prevention:** Single SELECT + single UPDATE with RETURNING. No loops.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| notification_id | Pydantic UUID type validator on path parameter | Rejects non-UUID strings before DB query |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. Notification body stored sanitized at insert time.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Notification body may reference patient names. No PHI is written by this endpoint — only a timestamp is updated.

**Audit requirement:** Write-only logged — updating read_at is not a PHI-sensitive action. No audit entry generated.

---

## Testing

### Test Cases

#### Happy Path
1. Mark unread notification as read
   - **Given:** Authenticated user with 1 unread notification (read_at IS NULL)
   - **When:** POST /api/v1/notifications/{notification_id}/read
   - **Then:** 200 with notification where `read_at` is a valid ISO 8601 datetime; DB confirms `read_at` set; cache keys invalidated

2. Idempotent — mark already-read notification
   - **Given:** Authenticated user with 1 notification already read (read_at IS NOT NULL)
   - **When:** POST /api/v1/notifications/{notification_id}/read again
   - **Then:** 200 with the same `read_at` value as before; no DB UPDATE executed; no error

#### Edge Cases
1. Redis unavailable during cache invalidation
   - **Given:** Redis is down
   - **When:** POST /api/v1/notifications/{notification_id}/read for valid unread notification
   - **Then:** Notification marked read in DB, warning logged, 200 returned (cache invalidation failure is non-fatal)

2. Concurrent requests
   - **Given:** Two simultaneous requests to mark the same notification as read
   - **When:** Both POST simultaneously
   - **Then:** Both return 200, DB UPDATE is idempotent (first write wins, second is no-op due to read_at check)

#### Error Cases
1. Invalid UUID format
   - **Given:** Authenticated user
   - **When:** POST /api/v1/notifications/not-a-valid-uuid/read
   - **Then:** 400 with Spanish error about invalid UUID format

2. Notification not found
   - **Given:** Authenticated user
   - **When:** POST /api/v1/notifications/{uuid-that-does-not-exist}/read
   - **Then:** 404 with Spanish error

3. Another user's notification
   - **Given:** UserA and UserB in same tenant; UserB knows the notification_id of UserA's notification
   - **When:** UserB: POST /api/v1/notifications/{userA_notification_id}/read
   - **Then:** 404 (not 403) — no information disclosure

4. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** POST /api/v1/notifications/{notification_id}/read
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** doctor role user with 5 unread notifications; separate user in same tenant to test cross-user isolation.

**Patients/Entities:** Notifications in DB for the test user, with varying types and read states.

### Mocking Strategy

- Redis: fakeredis for unit tests; real Redis for integration tests.
- Database: Pytest fixtures with tenant schema seeded with notifications.
- JWT: Test JWT factory for role/tenant combinations.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST marks unread notification as read and returns updated notification
- [ ] `read_at` is set to current UTC timestamp on first call
- [ ] Idempotent: second call on same notification returns 200 without changing `read_at`
- [ ] 404 returned for notification IDs not belonging to the current user
- [ ] Redis cache keys invalidated on successful write
- [ ] Response time < 100ms under normal load
- [ ] Invalid UUID path parameter returns 400 with Spanish error
- [ ] Cross-user isolation verified: user cannot read another user's notification
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Marking multiple notifications read in a single request — see N-03 (mark-all-read)
- Unmarking (marking as unread) — not a v1 feature
- Push notification acknowledgement (mobile/browser)
- Admin marking notifications read on behalf of users
- Notification deletion

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
