# AP-14 Notify Waitlist Patient Spec

---

## Overview

**Feature:** Manually trigger a notification to a waitlist patient about an available time slot. Staff selects a waitlist entry and an available slot, and the system sends a notification via the patient's preferred channels (WhatsApp, SMS, email). Updates the waitlist entry's notification_count and last_notified_at.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-12 (waitlist-add.md), AP-13 (waitlist-list.md), AP-09 (availability-get.md), infra/authentication-rules.md, notifications/reminder-config.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Any staff role may trigger waitlist notifications. Patients cannot trigger this endpoint. Doctor role may only notify patients on their own waitlist (doctor_id = own ID).

---

## Endpoint

```
POST /api/v1/appointments/waitlist/{entry_id}/notify
```

**Rate Limiting:**
- 20 requests per minute per user — prevents notification spam

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| entry_id | Yes | uuid | Must be valid UUID; must exist in tenant | Waitlist entry to notify | e5f6a1b2-c3d4-7890-abcd-34567890abcd |

### Query Parameters

None.

### Request Body Schema

```json
{
  "available_slot_start": "string (required) — ISO 8601 datetime of available slot to offer",
  "available_slot_end": "string (required) — ISO 8601 datetime of slot end",
  "doctor_id": "uuid (required) — doctor whose slot is being offered",
  "channels": "string[] (optional) — enum values: email, whatsapp, sms; if omitted, uses tenant notification settings",
  "custom_message": "string (optional) — max 500 chars; additional context appended to standard template"
}
```

**Example Request:**
```json
{
  "available_slot_start": "2026-03-16T09:00:00-05:00",
  "available_slot_end": "2026-03-16T09:30:00-05:00",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "channels": ["whatsapp", "sms"],
  "custom_message": "Este horario acaba de liberarse por una cancelacion."
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "entry_id": "uuid",
  "patient_id": "uuid",
  "notifications_dispatched": [
    {
      "channel": "string (email | whatsapp | sms)",
      "status": "string (queued | failed)",
      "error": "string | null"
    }
  ],
  "notification_count": "integer",
  "last_notified_at": "string (ISO 8601 datetime)",
  "available_slot_start": "string (ISO 8601 datetime)",
  "available_slot_end": "string (ISO 8601 datetime)",
  "doctor_id": "uuid"
}
```

**Example:**
```json
{
  "entry_id": "e5f6a1b2-c3d4-7890-abcd-34567890abcd",
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "notifications_dispatched": [
    {
      "channel": "whatsapp",
      "status": "queued",
      "error": null
    },
    {
      "channel": "sms",
      "status": "queued",
      "error": null
    }
  ],
  "notification_count": 2,
  "last_notified_at": "2026-03-14T11:00:00-05:00",
  "available_slot_start": "2026-03-16T09:00:00-05:00",
  "available_slot_end": "2026-03-16T09:30:00-05:00",
  "doctor_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Error Responses

#### 400 Bad Request
**When:** available_slot_start >= available_slot_end, or slot is in the past.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El horario disponible ofrecido no es valido.",
  "details": {
    "available_slot_start": ["El horario no puede ser en el pasado."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Doctor attempts to notify patient from another doctor's waitlist.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para notificar pacientes de la lista de espera de otro doctor."
}
```

#### 404 Not Found
**When:** entry_id does not exist in the tenant, or doctor_id not found.

**Example:**
```json
{
  "error": "not_found",
  "message": "Entrada de lista de espera no encontrada."
}
```

#### 409 Conflict
**When:** Patient was notified for this waitlist entry within the last 2 hours (anti-spam protection).

**Example:**
```json
{
  "error": "notification_cooldown",
  "message": "El paciente fue notificado recientemente. Espere al menos 2 horas antes de volver a notificar.",
  "details": {
    "last_notified_at": "2026-03-14T09:30:00-05:00",
    "cooldown_expires_at": "2026-03-14T11:30:00-05:00"
  }
}
```

#### 422 Unprocessable Entity
**When:** Waitlist entry status is not active or notified (cannot notify booked, expired, or cancelled entries).

**Example:**
```json
{
  "error": "invalid_entry_status",
  "message": "Solo se pueden notificar entradas activas o notificadas.",
  "details": {
    "current_status": "booked"
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or queue error.

---

## Business Logic

**Step-by-step process:**

1. Validate `entry_id` as UUID. Validate request body.
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Load waitlist entry from DB. Return 404 if not found.
4. If caller role = doctor: assert `entry.preferred_doctor_id == caller_user_id`. Return 403 if mismatch.
5. Validate entry status is active or notified. Return 422 if booked, expired, or cancelled.
6. Validate `doctor_id` exists and has role=doctor. Return 404 if not.
7. Validate `available_slot_start < available_slot_end` and `available_slot_start` is in the future. Return 400 if not.
8. Anti-spam check: if `entry.last_notified_at` is not null and `now() - entry.last_notified_at < 2 hours`, return 409 with cooldown details.
9. Determine notification channels: use `channels` from request if provided; otherwise load tenant's configured channels from settings.
10. Dispatch `waitlist.notify` job to RabbitMQ notifications queue — worker handles channel routing, template rendering, and actual delivery.
11. Update waitlist entry: `status = 'notified'`, `notification_count += 1`, `last_notified_at = now()`.
12. Invalidate waitlist list cache for tenant.
13. Write audit log entry.
14. Return 200 with notification dispatch summary.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| entry_id | Valid UUID, exists in tenant | Entrada de lista de espera no encontrada. |
| entry.status | Must be active or notified | Solo se pueden notificar entradas activas o notificadas. |
| available_slot_start | ISO 8601 datetime, must be in the future | El horario no puede ser en el pasado. |
| available_slot_end | ISO 8601 datetime, must be after available_slot_start | La hora de fin debe ser posterior a la hora de inicio. |
| doctor_id | Valid UUID, role=doctor | Doctor no encontrado. |
| channels | Array of enum values: email, whatsapp, sms (if provided) | Canal de notificacion no valido. |
| custom_message | Max 500 chars (if provided) | El mensaje no puede superar 500 caracteres. |
| Cooldown | last_notified_at must be > 2 hours ago | El paciente fue notificado recientemente. |

**Business Rules:**

- Notification delivery is asynchronous via RabbitMQ. The API returns 200 after dispatching the job, not after delivery confirmation.
- The `notifications_dispatched` array reflects which channels were queued, not whether delivery succeeded.
- `notification_count` is incremented per manual notification call, not per channel.
- If patient has no phone or email registered, the corresponding channel queues gracefully fail with logged warnings.
- Status transitions to `notified` on first notification. Further notifications keep status as `notified`.
- Booking the slot (AP-01) after receiving notification transitions entry to `booked` (handled by a separate listener on `appointment.created`).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| channels = ["email"] but patient has no email | Channel status = failed with error "No email on file"; other channels proceed |
| Notification sent exactly at 2h cooldown boundary | Allow (boundary is > 2h, not >= 2h) |
| Available slot is no longer free | Warning dispatched but no validation error — slot availability is not re-checked here |
| custom_message contains HTML | Sanitized before appending to template |
| Entry with preferred_doctor_id = null | Any staff can notify; doctor_id in request must still be valid |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `waitlist_entries`: UPDATE — status, notification_count, last_notified_at
- `audit_logs`: INSERT — waitlist notify event

**Example query (SQLAlchemy):**
```python
stmt = (
    update(WaitlistEntry)
    .where(WaitlistEntry.id == entry_id)
    .values(
        status=WaitlistStatus.NOTIFIED,
        notification_count=WaitlistEntry.notification_count + 1,
        last_notified_at=utcnow(),
    )
    .returning(WaitlistEntry)
)
result = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:waitlist:list:*`: INVALIDATE — all waitlist list caches

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | waitlist.notify | { tenant_id, entry_id, patient_id, channels, available_slot_start, available_slot_end, doctor_id, custom_message } | After DB update |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

**If Yes:**
- **Action:** update
- **Resource:** waitlist_entry
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | waitlist_slot_available | patient | When email in channels |
| whatsapp | waitlist_slot_available_wa | patient | When whatsapp in channels |
| sms | waitlist_slot_available_sms | patient | When sms in channels |

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on notify (write operation)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Invalidates waitlist list caches

### Database Performance

**Queries executed:** 3 (load entry, anti-spam check via entry.last_notified_at, update)

**Indexes required:**
- `waitlist_entries.id` — PRIMARY KEY (exists)
- `waitlist_entries.(preferred_doctor_id, status)` — COMPOSITE INDEX (for RBAC check)
- `waitlist_entries.last_notified_at` — INDEX (for cooldown check)

**N+1 prevention:** Not applicable — single entry operation.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| entry_id | Pydantic UUID validator | URL param |
| available_slot_start, available_slot_end | Pydantic datetime validator | ISO 8601 strict |
| doctor_id | Pydantic UUID validator | Required body field |
| channels | Pydantic list[enum] | Whitelist values |
| custom_message | Pydantic strip() + bleach.clean, max 500 | Free-text |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** patient_id, available_slot (implies health appointment), custom_message

**Audit requirement:** All notification events logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Receptionist notifies active waitlist patient via WhatsApp and SMS
   - **Given:** Receptionist JWT, active waitlist entry, last_notified_at=null
   - **When:** POST /api/v1/appointments/waitlist/{entry_id}/notify with valid slot and channels
   - **Then:** 200 with 2 queued channels, notification_count=1, last_notified_at set

2. Second notification after 3 hours (past cooldown)
   - **Given:** Entry last_notified_at = 3 hours ago
   - **When:** POST notify again
   - **Then:** 200 with notification_count=2

3. No channels specified — uses tenant defaults
   - **Given:** Tenant configured for email+whatsapp; no channels in request
   - **When:** POST notify without channels field
   - **Then:** 200 with email and whatsapp queued

#### Edge Cases
1. Patient has no email registered
   - **Given:** channels=["email"], patient.email=null
   - **When:** POST notify
   - **Then:** 200 with notifications_dispatched[0].status="failed" and error="No email registrado"

2. Entry is already notified (second notification within allowed window)
   - **Given:** Entry status=notified, last_notified_at > 2h ago
   - **When:** POST notify
   - **Then:** 200 — allows re-notification, increments count

#### Error Cases
1. Notification within 2h cooldown
   - **Given:** Entry last_notified_at = 1 hour ago
   - **When:** POST notify
   - **Then:** 409 notification_cooldown with cooldown_expires_at

2. Entry status=booked
   - **Given:** Entry status=booked (patient already made appointment)
   - **When:** POST notify
   - **Then:** 422 invalid_entry_status

3. Doctor notifying from another doctor's entry
   - **Given:** Doctor A JWT, entry.preferred_doctor_id = Doctor B
   - **When:** POST notify
   - **Then:** 403 Forbidden

4. entry_id does not exist
   - **Given:** Random UUID
   - **When:** POST notify
   - **Then:** 404 Entrada no encontrada

### Test Data Requirements

**Users:** clinic_owner, two doctors, receptionist

**Patients/Entities:** Waitlist entries in active, notified, booked, expired status; patient with and without email; tenant with configured notification channels

### Mocking Strategy

- RabbitMQ: Mock publish; assert `waitlist.notify` event dispatched with correct payload
- Redis: Use `fakeredis`; verify list cache invalidated
- Notification worker: Not tested here; test via integration test in notification specs

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/appointments/waitlist/{entry_id}/notify returns 200 with dispatch summary
- [ ] notification_count incremented, last_notified_at updated
- [ ] 2-hour cooldown enforced (409 if too soon)
- [ ] Only active and notified entries can be notified (422 for others)
- [ ] Doctor restricted to own waitlist entries (403)
- [ ] Channels defaulted from tenant settings when not in request
- [ ] waitlist.notify event dispatched to RabbitMQ
- [ ] Waitlist list cache invalidated
- [ ] Audit log written with PHI flag
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Automatic notification when slot opens (triggered by AP-05/AP-08 via waitlist.slot_opened event — handled by notification worker)
- Booking the slot from the waitlist notification (patient contacts clinic or uses public booking link)
- Marking waitlist entry as booked (handled by appointment.created event listener)
- Deleting waitlist entries

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
