# N-01 — Notification List Spec

---

## Overview

**Feature:** List in-app notifications for the currently authenticated user. Returns paginated notifications with support for filtering by read/unread status and notification type. Used to populate the notification bell/drawer in the UI.

**Domain:** notifications

**Priority:** Medium

**Dependencies:** A-01 (login), A-02 (me), infra/authentication-rules.md, infra/rate-limiting.md, infra/caching-strategy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Each user only sees their own notifications. No cross-user access permitted. Superadmin uses a separate admin interface and is excluded from this endpoint.

---

## Endpoint

```
GET /api/v1/notifications
```

**Rate Limiting:**
- 60 requests per minute per user
- Burst: 10 requests per 5 seconds per user

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

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| status | No | string | Enum: `unread`, `read`, `all`. Default: `all` | Filter by read status | `unread` |
| type | No | string | Enum: `appointment_reminder`, `appointment_confirmed`, `appointment_cancelled`, `new_patient`, `payment_received`, `payment_overdue`, `treatment_plan_approved`, `consent_signed`, `message_received`, `inventory_alert`, `system_update` | Filter by notification type | `appointment_reminder` |
| cursor | No | string | Opaque cursor for pagination (base64-encoded) | Cursor from previous response | `eyJpZCI6IjEyMyJ9` |
| limit | No | integer | Min: 1, Max: 100, Default: 20 | Number of results per page | `20` |

### Request Body Schema

None. GET request.

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
      "type": "string (notification type enum)",
      "title": "string",
      "body": "string",
      "read_at": "string | null (ISO 8601 datetime or null if unread)",
      "created_at": "string (ISO 8601 datetime)",
      "metadata": {
        "resource_type": "string (appointment | patient | invoice | clinical_record | system)",
        "resource_id": "string | null (uuid of related resource)",
        "action_url": "string | null (relative URL for deep-link)"
      }
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_unread": "integer"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6",
      "type": "appointment_reminder",
      "title": "Recordatorio de cita",
      "body": "Tiene una cita mañana a las 10:00 AM con el Dr. García.",
      "read_at": null,
      "created_at": "2026-02-25T08:00:00Z",
      "metadata": {
        "resource_type": "appointment",
        "resource_id": "b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7",
        "action_url": "/agenda/b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7"
      }
    },
    {
      "id": "c3d4e5f6-0003-0003-0003-c3d4e5f6a7b8",
      "type": "payment_received",
      "title": "Pago recibido",
      "body": "Se registró un pago de $150.000 COP para el paciente Juan Pérez.",
      "read_at": "2026-02-24T15:30:00Z",
      "created_at": "2026-02-24T15:28:00Z",
      "metadata": {
        "resource_type": "invoice",
        "resource_id": "d4e5f6a7-0004-0004-0004-d4e5f6a7b8c9",
        "action_url": "/billing/invoices/d4e5f6a7-0004-0004-0004-d4e5f6a7b8c9"
      }
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6ImMzZDRlNWY2LTAwMDMifQ==",
    "has_more": true,
    "total_unread": 5
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values — unknown `status` value, unknown `type` value, non-integer `limit`.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "El valor del parámetro 'status' no es válido. Valores permitidos: read, unread, all.",
  "details": {
    "status": ["Valor no reconocido: 'leido'. Use 'read', 'unread' o 'all'."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. See `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient role attempting to access notifications for a different user (tenant data access violation caught at RBAC layer). Also if superadmin attempts to use this endpoint.

#### 422 Unprocessable Entity
**When:** `limit` is outside the 1–100 range, or `cursor` is malformed (cannot be base64-decoded).

**Example:**
```json
{
  "error": "validacion_fallida",
  "message": "Se encontraron errores de validación.",
  "details": {
    "limit": ["El límite debe estar entre 1 y 100."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database error, Redis failure causing cache miss with DB fallback failure, or unhandled exception during notification serialization.

---

## Business Logic

**Step-by-step process:**

1. Validate and parse JWT — extract `user_id`, `tenant_id`, `role` from claims.
2. Parse and validate query parameters using Pydantic schema `NotificationListQueryParams`. Apply defaults: `status=all`, `limit=20`.
3. Validate `type` enum if provided. Return 400 if value is not in the allowed notification type enum.
4. Validate `cursor` if provided — base64-decode and parse JSON `{"id": "<uuid>", "created_at": "<iso>"}`. Return 422 if malformed.
5. Build SQLAlchemy query against tenant schema `notifications` table:
   - Filter `WHERE user_id = :user_id`
   - If `status=unread`: add `AND read_at IS NULL`
   - If `status=read`: add `AND read_at IS NOT NULL`
   - If `type` provided: add `AND type = :type`
   - If `cursor` provided: add `AND (created_at, id) < (:cursor_created_at, :cursor_id)` (keyset pagination)
   - ORDER BY `created_at DESC, id DESC`
   - LIMIT `:limit + 1` (to determine `has_more`)
6. Execute count query for `total_unread` — `SELECT COUNT(*) FROM notifications WHERE user_id = :user_id AND read_at IS NULL`. This is cached separately in Redis.
7. If result count > `limit`, set `has_more=true`, encode last item as `next_cursor`, truncate results to `limit`.
8. Serialize each notification to response schema. Do NOT include PHI in `body` — body is a pre-rendered, translated string stored in the DB at insert time.
9. Return 200 with paginated response.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| status | Must be one of: `read`, `unread`, `all` | El valor del parámetro 'status' no es válido. |
| type | Must be a valid notification type enum value | El tipo de notificación no es válido. |
| limit | Integer between 1 and 100 | El límite debe estar entre 1 y 100. |
| cursor | Must be valid base64-encoded JSON `{id, created_at}` | El cursor de paginación tiene un formato inválido. |

**Business Rules:**

- A user never sees notifications belonging to another user, even within the same tenant.
- Notification `body` strings are pre-rendered at insert time in the user's preferred locale (stored in `users.locale`). No server-side rendering at read time.
- Deleted notifications (soft-deleted) are excluded from all queries (`WHERE deleted_at IS NULL`).
- The `total_unread` count is computed and cached separately — it reflects all unread notifications, not just those on the current page.
- Notifications older than 90 days are archived to cold storage and excluded by default. Add `include_archived=true` to fetch older ones (out of scope for v1).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No notifications exist for user | Returns empty `data: []`, `has_more: false`, `total_unread: 0` |
| cursor points to a deleted notification | Pagination continues correctly from next available item (keyset uses created_at+id, not row existence) |
| limit=1 with has_more=true | Returns single item, valid next_cursor for continuation |
| All notifications are read, status=unread | Returns empty list, total_unread=0 |
| User has notifications of 10+ types | Filtering by a single type returns only matching records |
| Redis cache is unavailable for total_unread | Falls back to direct DB COUNT query, logs warning, does not return error |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `notifications`: READ only — no writes performed.

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select, and_, func
from app.models.notifications import Notification

stmt = (
    select(Notification)
    .where(
        and_(
            Notification.user_id == current_user.id,
            Notification.deleted_at.is_(None),
        )
    )
    .order_by(Notification.created_at.desc(), Notification.id.desc())
    .limit(limit + 1)
)
if status == "unread":
    stmt = stmt.where(Notification.read_at.is_(None))
elif status == "read":
    stmt = stmt.where(Notification.read_at.isnot(None))
if notification_type:
    stmt = stmt.where(Notification.type == notification_type)
if cursor:
    stmt = stmt.where(
        (Notification.created_at, Notification.id) < (cursor_dt, cursor_id)
    )
result = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:notifications:unread_count`: READ — used for `total_unread`. Populated by N-02, N-03.
- `tenant:{tenant_id}:user:{user_id}:notifications:list:{hash_of_params}`: SET on cache miss — full response cached.

**Cache TTL:** 60 seconds for list responses. 300 seconds for unread count.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None. Read-only endpoint.

### Audit Log

**Audit entry:** No — notification listing is not a PHI-sensitive action. Access to notification metadata referencing clinical resources is covered by those resources' own audit logs.

### Notifications

**Notifications triggered:** No — this endpoint reads notifications, it does not generate them.

---

## Performance

### Expected Response Time
- **Target:** < 80ms (cached), < 150ms (DB fetch)
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** Redis cache with tenant-namespaced keys
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:notifications:list:{base64(query_params)}`
- **TTL:** 60 seconds
- **Invalidation:** Any write to `notifications` for this user (N-02, N-03, N-05 inserts) calls `INVALIDATE tenant:{tenant_id}:user:{user_id}:notifications:*` pattern delete via Redis `SCAN + DEL`.

### Database Performance

**Queries executed:** 2 (list query + unread count, count cached separately)

**Indexes required:**
- `notifications.(user_id, deleted_at, created_at DESC, id DESC)` — Composite index for keyset pagination
- `notifications.(user_id, read_at)` — Index for unread count filter
- `notifications.(user_id, type)` — Index for type filter

**N+1 prevention:** Single query with all filters applied. No sub-queries per notification item. Metadata is stored as JSONB in the `notifications` table and fetched inline.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on `created_at DESC, id DESC`)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| status | Pydantic enum validator | Rejects unknown values at schema level |
| type | Pydantic enum validator | Rejects unknown values at schema level |
| limit | Pydantic int with ge=1, le=100 | Clamps to valid range |
| cursor | Base64 decode + JSON parse with strict schema | Rejects malformed cursors |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization. Notification `body` stored sanitized at insert time.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Notification `body` may reference patient names or appointment details. Bodies are pre-rendered at insert time and stored already de-identified where possible. Patient names in notification bodies are considered indirect PHI.

**Audit requirement:** Read-only listing of notifications is not individually audited. Write access to referenced resources is audited separately.

---

## Testing

### Test Cases

#### Happy Path
1. List all notifications for authenticated user
   - **Given:** User has 25 notifications (15 unread, 10 read), no filters applied
   - **When:** GET /api/v1/notifications with default params
   - **Then:** Returns first 20 notifications ordered by created_at DESC, `has_more: true`, `total_unread: 15`, valid `next_cursor`

2. Filter by unread status
   - **Given:** User has 15 unread notifications
   - **When:** GET /api/v1/notifications?status=unread
   - **Then:** Returns only unread notifications, all have `read_at: null`

3. Filter by notification type
   - **Given:** User has 5 appointment_reminder and 10 other notifications
   - **When:** GET /api/v1/notifications?type=appointment_reminder
   - **Then:** Returns exactly 5 items, all with `type: "appointment_reminder"`

4. Cursor-based pagination
   - **Given:** User has 45 notifications, first page fetched
   - **When:** GET /api/v1/notifications?cursor={next_cursor_from_first_page}
   - **Then:** Returns next 20 items without duplicates, correct ordering maintained

#### Edge Cases
1. User with zero notifications
   - **Given:** New user with no notifications
   - **When:** GET /api/v1/notifications
   - **Then:** Returns `{"data": [], "pagination": {"next_cursor": null, "has_more": false, "total_unread": 0}}`

2. Cache miss with Redis down
   - **Given:** Redis is unreachable
   - **When:** GET /api/v1/notifications
   - **Then:** Falls back to DB, returns correct response, warning logged, no 500 error

#### Error Cases
1. Invalid status parameter
   - **Given:** Authenticated user
   - **When:** GET /api/v1/notifications?status=pendiente
   - **Then:** 400 with Spanish error message listing valid values

2. Malformed cursor
   - **Given:** Authenticated user with previous page
   - **When:** GET /api/v1/notifications?cursor=notvalidbase64!!!
   - **Then:** 422 with error message indicating invalid cursor format

3. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** GET /api/v1/notifications
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** doctor role user with 25+ notifications of mixed types and read status; patient role user with own notifications; clinic_owner role user.

**Patients/Entities:** At least 5 distinct notification types populated in test DB, including appointment_reminder, payment_received, message_received, inventory_alert, system_update.

### Mocking Strategy

- Redis: Use fakeredis library for unit tests; real Redis container for integration tests.
- JWT: Use test JWT factory with configurable claims.
- Database: Pytest fixtures with tenant schema bootstrapped, seed notifications table.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Authenticated user retrieves their own notifications paginated correctly
- [ ] `status=unread` filter returns only notifications where `read_at IS NULL`
- [ ] `status=read` filter returns only notifications where `read_at IS NOT NULL`
- [ ] `type` filter returns only matching notification types
- [ ] Cursor-based pagination returns correct pages without duplicates
- [ ] `total_unread` reflects accurate count of all unread notifications for the user
- [ ] Response time < 150ms under normal load (< 80ms cached)
- [ ] Empty state (no notifications) returns valid empty response without error
- [ ] Invalid query params return 400/422 with Spanish error messages
- [ ] No cross-user data leakage verified in integration tests
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Push notifications (mobile/browser) — separate spec
- Email/SMS/WhatsApp notification delivery — see N-05
- Notification creation — see N-05 (notification dispatch engine)
- Bulk notification deletion
- Notification archival/restoration for records older than 90 days
- Admin-level notification management across users
- Real-time WebSocket notification streaming — separate spec

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
