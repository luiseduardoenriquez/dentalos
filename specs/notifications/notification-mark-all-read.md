# N-03 — Notification Mark All Read Spec

---

## Overview

**Feature:** Mark all unread in-app notifications as read for the currently authenticated user in a single operation. Performs a bulk UPDATE on the `notifications` table and returns the count of notifications that were marked. Invalidates related caches.

**Domain:** notifications

**Priority:** Medium

**Dependencies:** N-01 (notification-list), N-02 (notification-mark-read), A-01 (login), infra/authentication-rules.md, infra/caching-strategy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** This operation is strictly scoped to the current user. No user can mark another user's notifications as read. The bulk operation only affects the caller's own unread notifications.

---

## Endpoint

```
POST /api/v1/notifications/read-all
```

**Rate Limiting:**
- 10 requests per minute per user
- Intentionally low limit — this is a bulk operation. Users should not spam it.

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Tenant identifier (auto-resolved from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

Optional filter body — allows scoping the mark-all operation to a specific notification type. If body is omitted or empty, ALL unread notifications for the user are marked read.

```json
{
  "type": "string | null (optional) — filter to only mark a specific notification type as read"
}
```

**Example Request (mark all unread):**
```json
{}
```

**Example Request (mark only appointment reminders as read):**
```json
{
  "type": "appointment_reminder"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "marked_count": "integer — number of notifications that were updated",
  "type_filter": "string | null — the type filter applied, if any"
}
```

**Example (no filter, all marked):**
```json
{
  "marked_count": 12,
  "type_filter": null
}
```

**Example (type-filtered):**
```json
{
  "marked_count": 3,
  "type_filter": "appointment_reminder"
}
```

**Example (nothing to mark — all already read):**
```json
{
  "marked_count": 0,
  "type_filter": null
}
```

**Note:** A `marked_count` of 0 is a valid success response — it means all notifications were already read. The operation is idempotent.

### Error Responses

#### 400 Bad Request
**When:** Request body is provided but contains invalid JSON structure or `type` field has an unrecognized notification type value.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "El tipo de notificación especificado no es válido.",
  "details": {
    "type": ["Valor no reconocido: 'otro'. Tipos válidos: appointment_reminder, appointment_confirmed, appointment_cancelled, new_patient, payment_received, payment_overdue, treatment_plan_approved, consent_signed, message_received, inventory_alert, system_update."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. See `infra/authentication-rules.md`.

#### 422 Unprocessable Entity
**When:** Request body is provided but cannot be parsed as JSON (malformed JSON syntax).

**Example:**
```json
{
  "error": "validacion_fallida",
  "message": "El cuerpo de la solicitud no tiene un formato JSON válido.",
  "details": {}
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Database bulk UPDATE failure, transaction rollback, or unexpected exception.

---

## Business Logic

**Step-by-step process:**

1. Validate and parse JWT — extract `user_id`, `tenant_id`, `role` from claims.
2. Parse optional request body using Pydantic schema `MarkAllReadRequest`. If body is empty or `{}`, set `type=None`. If `type` field is present, validate against notification type enum. Return 400 if invalid.
3. Build SQLAlchemy bulk UPDATE statement against the tenant schema `notifications` table:
   - `WHERE user_id = :user_id AND read_at IS NULL AND deleted_at IS NULL`
   - If `type` is provided: add `AND type = :type`
   - `SET read_at = NOW()`
   - Use `rowcount` or `RETURNING COUNT(*)` to capture the number of affected rows.
4. Execute the UPDATE inside a database transaction. If any exception occurs, rollback.
5. Commit transaction.
6. Invalidate Redis cache keys:
   - DELETE `tenant:{tenant_id}:user:{user_id}:notifications:unread_count`
   - SCAN + DEL pattern `tenant:{tenant_id}:user:{user_id}:notifications:list:*`
7. Emit structured log entry: `{"action": "notification.mark_all_read", "marked_count": N, "type_filter": "...", "user_id": "...", "tenant_id": "..."}`.
8. Return 200 with `{"marked_count": N, "type_filter": type_or_null}`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| type | If provided, must be a valid notification type enum value | El tipo de notificación especificado no es válido. |

**Business Rules:**

- The operation exclusively affects the authenticated user's own notifications — `WHERE user_id = :user_id` is always enforced.
- Soft-deleted notifications (`deleted_at IS NOT NULL`) are never affected — they are filtered out.
- The operation is idempotent. If all notifications are already read, returns `{"marked_count": 0, "type_filter": null}` with 200 OK.
- The bulk UPDATE is performed in a single SQL statement — atomic at the DB level.
- Cache invalidation failure is non-fatal. If Redis is down, the UPDATE still commits and the response still returns 200. A warning is logged.
- `marked_count` reflects the exact number of rows updated, as returned by PostgreSQL's row count from the UPDATE statement.
- When `type` is provided, only notifications of that type are marked. Other unread types remain unread.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No unread notifications exist | Returns `{"marked_count": 0}`, 200 OK, no DB writes |
| `type` filter matches 0 notifications | Returns `{"marked_count": 0, "type_filter": "appointment_reminder"}`, 200 OK |
| User has 1000+ unread notifications | Single bulk UPDATE handles all atomically; no looping |
| Redis cache unavailable | DB UPDATE commits, warning logged, 200 returned without cache invalidation |
| Concurrent mark-all-read calls | Both execute bulk UPDATEs; second call's rowcount is 0 (already marked); both return 200 |
| Body is `null` | Treated as no body — all unread marked, no type filter |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `notifications`: UPDATE — bulk sets `read_at = NOW()` for all matching unread notifications belonging to the current user.

**Example query (SQLAlchemy):**
```python
from sqlalchemy import update, and_, func
from app.models.notifications import Notification
import datetime

stmt = (
    update(Notification)
    .where(
        and_(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
            Notification.deleted_at.is_(None),
        )
    )
    .values(read_at=datetime.datetime.utcnow())
)
if type_filter:
    stmt = stmt.where(Notification.type == type_filter)

result = await session.execute(stmt)
await session.commit()
marked_count = result.rowcount
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:notifications:unread_count`: DELETE — count is now 0 (or partial if type filter applied).
- `tenant:{tenant_id}:user:{user_id}:notifications:list:*`: INVALIDATE pattern — all cached pages stale.

**Cache TTL:** N/A (invalidation only).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — bulk marking notifications as read is not a PHI-modifying action.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 150ms (even for large notification counts)
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Write endpoint — primarily invalidates cache.
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:notifications:unread_count` (DELETE)
- **TTL:** N/A
- **Invalidation:** Deletes unread count key and all list cache pattern variants for this user on successful write.

### Database Performance

**Queries executed:** 1 (single bulk UPDATE)

**Indexes required:**
- `notifications.(user_id, read_at, deleted_at)` — Composite index for the bulk UPDATE's WHERE clause
- `notifications.(user_id, type, read_at)` — Supports type-filtered bulk UPDATE

**N+1 prevention:** Single bulk UPDATE SQL statement. No row-by-row iteration. PostgreSQL handles all matching rows atomically.

### Pagination

**Pagination:** No — bulk operation, returns scalar count.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| type | Pydantic enum validator — optional field | Rejects unknown values; null/absent is valid |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Response contains only integer `marked_count` and nullable string `type_filter`. No user-generated content echoed.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. This endpoint writes only a timestamp (`read_at`) and returns a count integer. No PHI is exposed in request or response.

**Audit requirement:** Not required. Marking notifications as read is not a PHI-sensitive action.

---

## Testing

### Test Cases

#### Happy Path
1. Mark all unread notifications as read (no filter)
   - **Given:** User has 15 unread notifications, 5 already read
   - **When:** POST /api/v1/notifications/read-all with empty body
   - **Then:** 200 with `{"marked_count": 15, "type_filter": null}`; DB confirms all previously unread now have `read_at` set; already-read notifications' `read_at` unchanged

2. Mark notifications of a specific type as read
   - **Given:** User has 5 unread `appointment_reminder` and 8 unread `payment_received` notifications
   - **When:** POST /api/v1/notifications/read-all with body `{"type": "appointment_reminder"}`
   - **Then:** 200 with `{"marked_count": 5, "type_filter": "appointment_reminder"}`; only appointment_reminder notifications marked; payment_received remain unread

3. All notifications already read (idempotent)
   - **Given:** User has 0 unread notifications
   - **When:** POST /api/v1/notifications/read-all
   - **Then:** 200 with `{"marked_count": 0, "type_filter": null}`

#### Edge Cases
1. Large number of unread notifications
   - **Given:** User has 500 unread notifications
   - **When:** POST /api/v1/notifications/read-all
   - **Then:** All 500 marked in single DB UPDATE within 400ms; `marked_count: 500`

2. Redis down during cache invalidation
   - **Given:** Redis unavailable
   - **When:** POST /api/v1/notifications/read-all for user with 10 unread
   - **Then:** DB UPDATE commits successfully, 200 returned with `marked_count: 10`; warning logged for cache failure

3. Empty body vs missing body
   - **Given:** Authenticated user with unread notifications
   - **When:** POST with `{}` body and POST with no body at all
   - **Then:** Both treated identically — all unread marked, `type_filter: null`

#### Error Cases
1. Invalid type value in body
   - **Given:** Authenticated user
   - **When:** POST /api/v1/notifications/read-all with body `{"type": "random_type"}`
   - **Then:** 400 with Spanish error listing valid type values

2. Rate limit exceeded
   - **Given:** User calls this endpoint 11 times within 1 minute
   - **When:** 11th request
   - **Then:** 429 Too Many Requests with Retry-After header

3. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** POST /api/v1/notifications/read-all
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** doctor user with 20 unread notifications across 4 different types; clinic_owner user with 0 unread notifications (for idempotent test).

**Patients/Entities:** Notifications table seeded with known counts per type and per user.

### Mocking Strategy

- Redis: fakeredis for unit tests; real Redis container for integration tests.
- Database: Pytest fixtures with per-test notification seeding.
- JWT: Test JWT factory.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] All unread notifications for the current user are marked read in a single DB call
- [ ] `marked_count` accurately reflects the number of rows updated
- [ ] Optional `type` filter correctly scopes the bulk operation
- [ ] Idempotent: returns `marked_count: 0` when nothing to mark, no error
- [ ] Redis cache invalidated for unread count and list keys
- [ ] Rate limit enforced at 10 requests/minute
- [ ] Invalid `type` value returns 400 with Spanish error message
- [ ] Cross-user isolation: only the current user's notifications are affected
- [ ] Performance: < 150ms for up to 1000 notifications
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Marking notifications as unread (reverse operation)
- Bulk deletion of notifications
- Scoping by date range (only unread status and type are supported filters)
- Admin marking notifications for another user
- Push notification acknowledgement
- Filtering by multiple types simultaneously

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
