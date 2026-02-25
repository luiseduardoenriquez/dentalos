# Notification Preferences Spec

---

## Overview

**Feature:** Read and update a user's notification preferences per event type and per channel. Allows any authenticated user to control which events trigger notifications and through which channels (email, SMS, WhatsApp, in-app) they receive them.

**Domain:** users

**Priority:** Medium

**Dependencies:** U-01 (get-profile.md), N-01 (notifications domain spec)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist (own preferences only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Users can only read and update their own notification preferences. There is no admin override for another user's notification preferences in v1.

---

## Endpoints

### GET — Read Current Preferences

```
GET /api/v1/users/me/notifications
```

### PUT — Update Preferences

```
PUT /api/v1/users/me/notifications
```

**Rate Limiting:**
- GET: Inherits global rate limit (100/min per user)
- PUT: 20 requests per minute per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes (PUT only) | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_a1b2c3d4e5f6 |

### URL Parameters

None. Always operates on the authenticated user (`me`).

### Query Parameters

None.

### Request Body Schema (PUT only)

```json
{
  "preferences": {
    "event_type": {
      "email": "boolean (required)",
      "sms": "boolean (required)",
      "whatsapp": "boolean (required)",
      "in_app": "boolean (required)"
    }
  }
}
```

**Supported event_type keys:**
- `appointment_reminder` — Reminder before scheduled appointment
- `appointment_cancelled` — Appointment was cancelled
- `new_patient` — New patient assigned to this doctor/clinic
- `treatment_plan_approved` — Patient approved a treatment plan
- `payment_received` — Payment confirmed for a service
- `new_message` — New message received in the messaging module
- `referral_received` — Referral sent by another doctor

All 7 event types must be included in the PUT body. Missing event types are rejected with 422.

**Example Request (PUT):**
```json
{
  "preferences": {
    "appointment_reminder": {
      "email": true,
      "sms": true,
      "whatsapp": true,
      "in_app": true
    },
    "appointment_cancelled": {
      "email": true,
      "sms": false,
      "whatsapp": true,
      "in_app": true
    },
    "new_patient": {
      "email": true,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    },
    "treatment_plan_approved": {
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
    "new_message": {
      "email": false,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    },
    "referral_received": {
      "email": true,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    }
  }
}
```

---

## Response

### Success Response (GET and PUT)

**Status:** 200 OK

**Schema:**
```json
{
  "user_id": "uuid",
  "preferences": {
    "event_type": {
      "email": "boolean",
      "sms": "boolean",
      "whatsapp": "boolean",
      "in_app": "boolean"
    }
  },
  "updated_at": "datetime | null"
}
```

**Example (GET):**
```json
{
  "user_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "preferences": {
    "appointment_reminder": {
      "email": true,
      "sms": true,
      "whatsapp": true,
      "in_app": true
    },
    "appointment_cancelled": {
      "email": true,
      "sms": false,
      "whatsapp": true,
      "in_app": true
    },
    "new_patient": {
      "email": true,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    },
    "treatment_plan_approved": {
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
    "new_message": {
      "email": false,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    },
    "referral_received": {
      "email": true,
      "sms": false,
      "whatsapp": false,
      "in_app": true
    }
  },
  "updated_at": "2026-02-24T10:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON body in PUT request.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es JSON valido.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 422 Unprocessable Entity
**When:** Missing event types, unknown event type keys, or non-boolean channel values.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Las preferencias de notificacion contienen errores.",
  "details": {
    "preferences.appointment_reminder": ["Este tipo de evento es obligatorio."],
    "preferences.unknown_event": ["Tipo de evento desconocido."],
    "preferences.new_patient.sms": ["Debe ser un valor booleano (true o false)."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache error.

---

## Business Logic

### GET /api/v1/users/me/notifications

**Step-by-step process:**

1. Validate JWT and extract `user_id` and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id`.
3. Check Redis cache for key `tenant:{tenant_id}:user:{user_id}:notification_prefs`.
4. If cache hit, return cached preferences.
5. If cache miss, query `user_notification_preferences` table for the user's row.
6. If no row exists (user has never configured preferences), return system defaults (all channels enabled for all events).
7. Serialize via Pydantic `NotificationPreferencesResponse`.
8. Cache result with TTL 600 seconds (10 minutes).
9. Return 200.

### PUT /api/v1/users/me/notifications

**Step-by-step process:**

1. Validate JWT and extract `user_id` and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id`.
3. Parse and validate request body via Pydantic `NotificationPreferencesUpdateRequest`.
4. Verify all 7 required event types are present.
5. Verify no unknown event type keys are included.
6. Verify all channel values are booleans.
7. If validation fails, return 422 with field-level details.
8. Upsert `user_notification_preferences` table: full replace of the user's preferences row.
9. Invalidate Redis cache key `tenant:{tenant_id}:user:{user_id}:notification_prefs`.
10. Serialize updated preferences via `NotificationPreferencesResponse`.
11. Return 200 with updated preferences.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| preferences | Must be an object containing all 7 required event type keys | "Los siguientes tipos de evento son obligatorios: {missing_list}." |
| preferences keys | Must only contain the 7 defined event type keys | "Tipo de evento desconocido: {key}." |
| preferences[event_type] | Must contain exactly the 4 channel keys: email, sms, whatsapp, in_app | "Los canales email, sms, whatsapp e in_app son obligatorios para cada evento." |
| preferences[event_type][channel] | Must be boolean (true or false) | "Debe ser un valor booleano (true o false)." |

**Business Rules:**

- The PUT replaces all preferences atomically. Partial updates are not supported.
- System defaults (all true) are returned if no preference row exists for the user on GET.
- Disabling all channels for an event type is valid — the user will receive no notifications for that event.
- Channel availability is governed by tenant plan and add-on configuration; disabling a channel here does not affect tenant-level channel enablement. If the tenant has SMS disabled, the preference is stored but ignored at dispatch time.
- The `in_app` channel cannot be disabled for `new_message` events if the tenant has the messaging module enabled. However, validation at this endpoint does not enforce that rule — the notification dispatcher handles it.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| User has never set preferences (first GET) | Return system defaults: all channels true for all events |
| User disables all channels for all events | Valid — 200 OK; no notifications dispatched for any event |
| Tenant does not have WhatsApp add-on | Preference stored as-is; notification dispatcher skips WhatsApp channel at send time |
| Redis cache unavailable (GET) | Fallback to direct DB query; warning logged |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `user_notification_preferences`: UPSERT — full replace of the user's single preferences row.

**Example query (SQLAlchemy):**
```python
stmt = insert(UserNotificationPreferences).values(
    user_id=user_id,
    preferences=preferences_json,
    updated_at=datetime.utcnow()
).on_conflict_do_update(
    index_elements=["user_id"],
    set_={
        "preferences": preferences_json,
        "updated_at": datetime.utcnow()
    }
)
await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:notification_prefs`: SET (GET, on cache miss, TTL 600s) / DELETE (PUT, after upsert).

**Cache TTL:** 600 seconds (10 minutes) for GET caching.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None. Preference changes are immediate; no background work needed.

### Audit Log

**Audit entry:** No — notification preference changes are user settings, not clinical operations. Not audit-logged.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 50ms (GET cache hit), < 150ms (GET cache miss), < 200ms (PUT)
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Redis cache (GET only)
- **Cache key:** `tenant:{tenant_id}:user:{user_id}:notification_prefs`
- **TTL:** 600 seconds (10 minutes)
- **Invalidation:** On PUT (preference update).

### Database Performance

**Queries executed:** 0 (GET cache hit) or 1 (GET cache miss) or 1 (PUT upsert)

**Indexes required:**
- `user_notification_preferences.user_id` — UNIQUE INDEX (one preferences row per user; enables fast upsert)

**N+1 prevention:** Not applicable — single user row.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| preferences (PUT body) | Pydantic strict model with enum event_type keys | Rejects unknown keys; validates boolean types |
| channel values | Pydantic `bool` type — strict parsing | No coercion from strings ("true"/"false") |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Notification preferences are user settings, not PHI.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. User reads own preferences (cache miss — no prior preferences)
   - **Given:** Authenticated doctor, no preference row in DB
   - **When:** GET /api/v1/users/me/notifications
   - **Then:** 200 with all events, all channels set to `true` (system defaults)

2. User reads own preferences (cache hit)
   - **Given:** Authenticated user, preferences cached in Redis
   - **When:** GET /api/v1/users/me/notifications
   - **Then:** 200 from cache within 50ms

3. User updates preferences successfully
   - **Given:** Authenticated receptionist, valid 7-event payload
   - **When:** PUT /api/v1/users/me/notifications with full payload
   - **Then:** 200 with updated preferences; cache invalidated

4. User disables all SMS and WhatsApp
   - **Given:** Valid payload with sms=false and whatsapp=false on all events
   - **When:** PUT /api/v1/users/me/notifications
   - **Then:** 200 — valid configuration accepted

5. User updates preferences then immediately reads them
   - **Given:** PUT succeeded, cache invalidated
   - **When:** GET /api/v1/users/me/notifications
   - **Then:** 200 with updated preferences from DB (cache miss after invalidation)

#### Edge Cases
1. Redis unavailable during GET
   - **Given:** Redis is down, valid JWT
   - **When:** GET /api/v1/users/me/notifications
   - **Then:** 200 from DB; warning logged

2. User disables all channels for all events
   - **Given:** All channels false in payload
   - **When:** PUT /api/v1/users/me/notifications
   - **Then:** 200 — valid

#### Error Cases
1. Missing event type in PUT body
   - **Given:** Payload omits `referral_received`
   - **When:** PUT /api/v1/users/me/notifications
   - **Then:** 422 listing missing event type

2. Unknown event type key in PUT body
   - **Given:** Payload includes `"prescription_ready": {...}`
   - **When:** PUT /api/v1/users/me/notifications
   - **Then:** 422 "Tipo de evento desconocido: prescription_ready."

3. Non-boolean channel value
   - **Given:** `"email": "yes"` in payload
   - **When:** PUT /api/v1/users/me/notifications
   - **Then:** 422 "Debe ser un valor booleano (true o false)."

4. Missing Authorization header
   - **Given:** No JWT
   - **When:** GET or PUT /api/v1/users/me/notifications
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** One user per role (clinic_owner, doctor, assistant, receptionist). One user with no prior preference row. One user with existing preference row.

**Patients/Entities:** None.

### Mocking Strategy

- Redis: Use `fakeredis` for cache tests; disconnect mock for fallback test.
- Database: Use test tenant schema with seeded `user_notification_preferences` rows.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/users/me/notifications returns 200 with all 7 event types and 4 channels each
- [ ] System defaults (all true) returned when no preference row exists
- [ ] GET response cached in Redis for 10 minutes
- [ ] Cache fallback to DB works when Redis is unavailable
- [ ] PUT /api/v1/users/me/notifications returns 200 with updated preferences
- [ ] All 7 event types required in PUT body; missing types rejected with 422
- [ ] Unknown event types rejected with 422
- [ ] Non-boolean channel values rejected with 422
- [ ] Cache invalidated after successful PUT
- [ ] Both endpoints restricted to own preferences only (no user_id param)
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Admin override of another user's notification preferences
- Tenant-level notification settings (e.g., disabling SMS globally for the clinic)
- Adding new event types beyond the 7 defined here (requires a new spec version)
- The actual notification dispatch logic (notifications domain)
- Patient-facing notification preferences (patients manage their own preferences via the patient portal)

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
