# N-04 — Notification Preferences Spec

---

## Overview

**Feature:** Get and update user notification preferences. Returns and modifies a matrix of toggles for 7 event types across 4 delivery channels (email, sms, whatsapp, in_app), totaling up to 28 configurable toggles per user. GET retrieves current preferences, PATCH updates specific toggles without resetting unspecified ones.

**Domain:** notifications

**Priority:** Medium

**Dependencies:** N-01 (notification-list), A-02 (me), users/get-profile.md, infra/authentication-rules.md, infra/caching-strategy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Each user manages their own preferences only. No user can read or modify another user's preferences. `in_app` channel cannot be fully disabled — users always receive in-app notifications (only external channels are toggleable).

---

## Endpoint

```
GET  /api/v1/notifications/preferences
PATCH /api/v1/notifications/preferences
```

Both operations are on the same resource. This spec covers both GET and PATCH.

**Rate Limiting:**
- GET: 60 requests per minute per user
- PATCH: 30 requests per minute per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | PATCH only | string | Must be application/json for PATCH | application/json |
| X-Tenant-ID | No | string | Tenant identifier (auto-resolved from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters (GET only)

None.

### Request Body Schema (PATCH only)

Partial update — only include the preferences to change. Unspecified event_type/channel combinations remain unchanged.

```json
{
  "preferences": [
    {
      "event_type": "string (required) — notification event type enum",
      "channel": "string (required) — delivery channel enum: email | sms | whatsapp | in_app",
      "enabled": "boolean (required) — true to enable, false to disable"
    }
  ]
}
```

**PATCH Example Request:**
```json
{
  "preferences": [
    {
      "event_type": "appointment_reminder",
      "channel": "whatsapp",
      "enabled": true
    },
    {
      "event_type": "appointment_reminder",
      "channel": "sms",
      "enabled": false
    },
    {
      "event_type": "payment_overdue",
      "channel": "email",
      "enabled": true
    }
  ]
}
```

---

## Response

### Success Response (GET)

**Status:** 200 OK

**Schema:**
```json
{
  "user_id": "uuid",
  "preferences": {
    "appointment_reminder": {
      "email": "boolean",
      "sms": "boolean",
      "whatsapp": "boolean",
      "in_app": "boolean (always true, read-only)"
    },
    "appointment_confirmed": {
      "email": "boolean",
      "sms": "boolean",
      "whatsapp": "boolean",
      "in_app": "boolean (always true)"
    },
    "appointment_cancelled": {
      "email": "boolean",
      "sms": "boolean",
      "whatsapp": "boolean",
      "in_app": "boolean (always true)"
    },
    "new_patient": {
      "email": "boolean",
      "sms": "boolean",
      "whatsapp": "boolean",
      "in_app": "boolean (always true)"
    },
    "payment_received": {
      "email": "boolean",
      "sms": "boolean",
      "whatsapp": "boolean",
      "in_app": "boolean (always true)"
    },
    "payment_overdue": {
      "email": "boolean",
      "sms": "boolean",
      "whatsapp": "boolean",
      "in_app": "boolean (always true)"
    },
    "inventory_alert": {
      "email": "boolean",
      "sms": "boolean",
      "whatsapp": "boolean",
      "in_app": "boolean (always true)"
    }
  },
  "updated_at": "string | null (ISO 8601 datetime of last preference change)"
}
```

**GET Example:**
```json
{
  "user_id": "a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6",
  "preferences": {
    "appointment_reminder": {
      "email": true,
      "sms": false,
      "whatsapp": true,
      "in_app": true
    },
    "appointment_confirmed": {
      "email": true,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    },
    "appointment_cancelled": {
      "email": true,
      "sms": true,
      "whatsapp": true,
      "in_app": true
    },
    "new_patient": {
      "email": true,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    },
    "payment_received": {
      "email": true,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    },
    "payment_overdue": {
      "email": true,
      "sms": true,
      "whatsapp": true,
      "in_app": true
    },
    "inventory_alert": {
      "email": false,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    }
  },
  "updated_at": "2026-02-20T14:30:00Z"
}
```

### Success Response (PATCH)

**Status:** 200 OK — returns the full updated preferences object (same schema as GET response).

### Error Responses

#### 400 Bad Request
**When:** PATCH body contains invalid `event_type` value, invalid `channel` value, attempt to set `in_app` to `false`, or `preferences` array is empty.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "Se encontraron errores en las preferencias enviadas.",
  "details": {
    "preferences[0].event_type": ["Tipo de evento no válido: 'cita'. Valores válidos: appointment_reminder, appointment_confirmed, appointment_cancelled, new_patient, payment_received, payment_overdue, inventory_alert."],
    "preferences[1].channel": ["El canal 'in_app' no puede deshabilitarse. Las notificaciones en la aplicación siempre están activas."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. See `infra/authentication-rules.md`.

#### 422 Unprocessable Entity
**When:** PATCH body cannot be parsed as JSON, or `preferences` array is missing required fields (`event_type`, `channel`, `enabled`).

**Example:**
```json
{
  "error": "validacion_fallida",
  "message": "El cuerpo de la solicitud tiene errores de validación.",
  "details": {
    "preferences[0].enabled": ["Este campo es requerido."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Database read/write failure, JSONB update error.

---

## Business Logic

**Step-by-step process (GET):**

1. Validate and parse JWT — extract `user_id`, `tenant_id` from claims.
2. Check Redis cache key `tenant:{tenant_id}:user:{user_id}:notification_preferences`. If HIT, return cached response immediately.
3. Query `notification_preferences` table: `SELECT * FROM notification_preferences WHERE user_id = :user_id`.
4. If no row found (new user, first time), return default preferences (see defaults below). Do not insert a row yet — lazy initialization.
5. Serialize preferences into the 7×4 matrix response format.
6. Store result in Redis with 300-second TTL.
7. Return 200.

**Step-by-step process (PATCH):**

1. Validate and parse JWT — extract `user_id`, `tenant_id` from claims.
2. Parse and validate PATCH body using Pydantic schema `UpdateNotificationPreferencesRequest`.
3. Validate each preference item in the array:
   - `event_type` must be one of the 7 valid event types.
   - `channel` must be one of: `email`, `sms`, `whatsapp`, `in_app`.
   - If `channel == "in_app"` and `enabled == false`, return 400 (in_app cannot be disabled).
4. If any validation error, return 400 with details for all failing items.
5. Check if a `notification_preferences` row exists for the user. If not, INSERT with default values first.
6. For each preference item in the validated request, execute a targeted JSONB update:
   - UPDATE the `preferences` JSONB column at the specific path `[event_type][channel]`.
   - Use PostgreSQL JSONB path update: `jsonb_set(preferences, '{event_type, channel}', 'true/false')`.
   - All updates can be batched into a single UPDATE statement using nested `jsonb_set` calls.
7. Update `updated_at = NOW()`.
8. Invalidate Redis cache key `tenant:{tenant_id}:user:{user_id}:notification_preferences`.
9. Re-fetch updated preferences from DB and return full matrix with 200 OK.

**Default Preferences (new users):**

| Event Type | email | sms | whatsapp | in_app |
|------------|-------|-----|----------|--------|
| appointment_reminder | true | false | true | true |
| appointment_confirmed | true | false | false | true |
| appointment_cancelled | true | false | true | true |
| new_patient | true | false | false | true |
| payment_received | true | false | false | true |
| payment_overdue | true | false | false | true |
| inventory_alert | true | false | false | true |

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| event_type | Must be one of 7 valid event types | Tipo de evento no válido. |
| channel | Must be one of: email, sms, whatsapp, in_app | Canal de notificación no válido. |
| enabled (in_app) | Cannot be set to false | El canal 'in_app' no puede deshabilitarse. |
| preferences (PATCH) | Array must not be empty | Debe incluir al menos una preferencia a actualizar. |

**Business Rules:**

- `in_app` channel is always `true` for all event types — it is read-only from the client's perspective. The API enforces this constraint.
- Preferences are stored per-user, not per-role. Each user has individual preferences.
- The N-05 dispatch engine reads these preferences at send time to decide which channels to use for a given event type and recipient.
- If a user's phone number is not registered in their profile, SMS and WhatsApp are effectively non-functional even if enabled. The dispatch engine handles this gracefully.
- Tenant-level overrides (e.g., clinic has no WhatsApp Business API subscription) can suppress channels regardless of user preferences. This override logic lives in N-05, not here.
- Partial PATCH is supported — only the specified event_type/channel pairs are updated; others remain unchanged.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| New user — no preferences row in DB | GET returns defaults without DB write; PATCH triggers lazy INSERT then UPDATE |
| Attempt to disable in_app channel | 400 with clear Spanish error message |
| PATCH with 0 items in preferences array | 400 — preferences array must not be empty |
| PATCH with duplicate event_type/channel pairs in same request | Last occurrence wins; no error |
| Same preference value set (e.g., already true, set to true) | Idempotent — no error, DB UPDATE still executes, updated_at refreshed |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `notification_preferences`: SELECT (GET), INSERT (first-time PATCH), UPDATE (PATCH).

**Schema for `notification_preferences` table:**
```sql
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ,
    UNIQUE(user_id)
);
```

**Example PATCH query (SQLAlchemy):**
```python
from sqlalchemy import update, func
from sqlalchemy.dialects.postgresql import JSONB
from app.models.notification_preferences import NotificationPreference

# Build nested jsonb_set for all updates in one statement
# Example for two updates: appointment_reminder.whatsapp=true, payment_overdue.email=true
stmt = (
    update(NotificationPreference)
    .where(NotificationPreference.user_id == current_user.id)
    .values(
        preferences=func.jsonb_set(
            func.jsonb_set(
                NotificationPreference.preferences,
                "{appointment_reminder,whatsapp}",
                "true",
                True,
            ),
            "{payment_overdue,email}",
            "true",
            True,
        ),
        updated_at=func.now(),
    )
    .returning(NotificationPreference)
)
result = await session.execute(stmt)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:notification_preferences`: SET on GET (300s TTL); DELETE on PATCH write.

**Cache TTL:** 300 seconds (GET caches full preferences matrix).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — preference changes are not PHI. Structured log is sufficient.

### Notifications

**Notifications triggered:** No — preference changes are administrative, not notification-generating.

---

## Performance

### Expected Response Time
- **Target:** < 50ms (cached GET), < 100ms (DB GET), < 200ms (PATCH)
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** Redis cache for GET; invalidate on PATCH
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:notification_preferences`
- **TTL:** 300 seconds
- **Invalidation:** DELETE on successful PATCH write

### Database Performance

**Queries executed:** 1 (GET — SELECT or lazy INSERT) / 2 (PATCH — SELECT + UPDATE)

**Indexes required:**
- `notification_preferences.(user_id)` — UNIQUE index (already enforced by UNIQUE constraint)

**N+1 prevention:** Single row per user. All 28 preferences stored as JSONB in one row. No joins.

### Pagination

**Pagination:** No — single row per user.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| event_type | Pydantic enum validator | Rejects unknown values |
| channel | Pydantic enum validator | Rejects unknown values |
| enabled | Pydantic bool validator | Strict boolean only |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. JSONB path updates use parameterized path arrays.

### XSS Prevention

**Output encoding:** Response is a structured JSON object with boolean values and enum strings. No user-generated free-text content.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Preferences are administrative configuration data only.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. GET preferences for new user (defaults)
   - **Given:** User with no existing preferences row
   - **When:** GET /api/v1/notifications/preferences
   - **Then:** 200 with default preferences matrix; `in_app` true for all events; `updated_at: null`

2. GET preferences for user with existing preferences
   - **Given:** User has a preferences row with customized values
   - **When:** GET /api/v1/notifications/preferences
   - **Then:** 200 with correct values from DB; `in_app` always true regardless of stored value

3. PATCH single preference
   - **Given:** User with existing preferences (appointment_reminder.whatsapp = false)
   - **When:** PATCH with `[{"event_type": "appointment_reminder", "channel": "whatsapp", "enabled": true}]`
   - **Then:** 200 with full matrix; `appointment_reminder.whatsapp = true`; all other preferences unchanged

4. PATCH multiple preferences
   - **Given:** User with default preferences
   - **When:** PATCH with 3 updates across 2 event types and 2 channels
   - **Then:** 200 with all 3 updates applied; other 25 toggles unchanged

5. GET after PATCH (cache invalidation)
   - **Given:** User just PATCHed preferences
   - **When:** GET /api/v1/notifications/preferences
   - **Then:** Returns updated values (not stale cache); cached fresh values for next 300s

#### Edge Cases
1. GET with Redis cache HIT
   - **Given:** User previously fetched preferences; value in Redis cache
   - **When:** GET /api/v1/notifications/preferences
   - **Then:** Response served from cache; no DB query

2. Idempotent PATCH (same value)
   - **Given:** appointment_reminder.email is already true
   - **When:** PATCH with `enabled: true` for same field
   - **Then:** 200; no error; `updated_at` refreshed

#### Error Cases
1. Attempt to disable in_app channel
   - **Given:** Authenticated user
   - **When:** PATCH with `{"event_type": "appointment_reminder", "channel": "in_app", "enabled": false}`
   - **Then:** 400 with Spanish error about in_app being always active

2. Invalid event_type
   - **Given:** Authenticated user
   - **When:** PATCH with `{"event_type": "new_message", "channel": "email", "enabled": true}`
   - **Then:** 400 with Spanish error listing valid event types

3. Empty preferences array
   - **Given:** Authenticated user
   - **When:** PATCH with `{"preferences": []}`
   - **Then:** 400 — array must not be empty

### Test Data Requirements

**Users:** doctor user with no preferences row (defaults test); clinic_owner user with fully customized preferences row.

**Patients/Entities:** `notification_preferences` table in tenant schema bootstrapped by migration.

### Mocking Strategy

- Redis: fakeredis for unit tests.
- Database: Pytest fixtures with per-test preference rows.
- JWT: Test JWT factory with role/tenant.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns 7×4 preference matrix with correct defaults for new users
- [ ] GET serves from Redis cache on subsequent requests (verified with cache HIT log)
- [ ] PATCH updates only specified preferences; others unchanged
- [ ] `in_app` cannot be set to false — 400 returned with Spanish error
- [ ] Invalid `event_type` or `channel` returns 400 with Spanish error listing valid values
- [ ] Empty `preferences` array in PATCH body returns 400
- [ ] Cache invalidated on PATCH; subsequent GET reflects new values
- [ ] Lazy insert creates default row on first PATCH for new user
- [ ] Response time < 50ms cached, < 200ms on PATCH
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Tenant-level notification channel configuration (e.g., disabling WhatsApp for entire clinic)
- Notification frequency/digest settings (e.g., daily summary vs instant)
- Patient-specific notification settings (patients have a separate limited preference set)
- Push notification (mobile/browser) channel preferences
- Admin overriding user preferences
- Event types beyond the 7 defined (new types require spec update)

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
