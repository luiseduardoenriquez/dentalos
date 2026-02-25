# AP-18 Update Reminder Configuration Spec

---

## Overview

**Feature:** Update the appointment reminder configuration for the authenticated clinic. Accepts a full array of reminder rules defining when (hours_before) and through which channels reminders are sent, along with optional custom message templates per channel. Validates rules, updates Redis cache, and triggers a background job to recalculate pending reminders for future appointments. Clinic_owner only.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-17 (reminder-config.md), infra/authentication-rules.md, infra/caching.md, notifications domain, RabbitMQ queue configuration

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner may modify reminder configuration. Superadmin may also update as part of tenant administration. All other roles receive 403.

---

## Endpoint

```
PUT /api/v1/settings/reminders
```

**Rate Limiting:**
- 10 requests per minute per user (settings update is infrequent; low limit prevents misconfiguration spam)
- Redis sliding window: `dentalos:rl:reminder_config_update:{user_id}` (TTL 60s)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "reminders": [
    {
      "id": "uuid (optional) — if provided, updates existing rule; if omitted, creates new rule",
      "hours_before": "integer (required) — hours before appointment, min 1, max 168 (7 days)",
      "channels": ["string (required) — array of enum: email, whatsapp, sms; min 1 channel per rule"],
      "is_active": "boolean (optional) — default true",
      "templates": {
        "email": {
          "subject": "string | null (optional) — custom subject, max 200 chars; null resets to system default",
          "body": "string | null (optional) — custom body with {{variables}}, max 2000 chars; null resets"
        },
        "whatsapp": {
          "message": "string | null (optional) — custom message, max 1000 chars; null resets"
        },
        "sms": {
          "message": "string | null (optional) — custom SMS text, max 160 chars; null resets"
        }
      }
    }
  ],
  "default_channels": ["string (optional) — array of enum: email, whatsapp, sms"]
}
```

**Example Request:**
```json
{
  "reminders": [
    {
      "hours_before": 48,
      "channels": ["email"],
      "is_active": true,
      "templates": {
        "email": {
          "subject": "Recordatorio: Tu cita dental en {{clinic_name}}",
          "body": "Hola {{patient_first_name}}, tienes una cita el {{appointment_date}} a las {{appointment_time}} con el Dr. {{doctor_name}}. Para cancelar o reprogramar llama al {{clinic_phone}}."
        },
        "whatsapp": { "message": null },
        "sms": { "message": null }
      }
    },
    {
      "hours_before": 2,
      "channels": ["whatsapp", "sms"],
      "is_active": true,
      "templates": {
        "email": { "subject": null, "body": null },
        "whatsapp": {
          "message": "Recordatorio: Tienes cita hoy a las {{appointment_time}} en {{clinic_name}}."
        },
        "sms": {
          "message": "Cita dental hoy {{appointment_time}} - {{clinic_name}} {{clinic_phone}}"
        }
      }
    }
  ],
  "default_channels": ["email"]
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "reminders": [
    {
      "id": "uuid",
      "hours_before": "integer",
      "channels": ["string"],
      "is_active": "boolean",
      "templates": {
        "email": { "subject": "string | null", "body": "string | null" },
        "whatsapp": { "message": "string | null" },
        "sms": { "message": "string | null" }
      }
    }
  ],
  "default_channels": ["string"],
  "pending_reminders_recalculated": "integer — count of future appointments for which reminders were re-queued",
  "updated_at": "string ISO 8601",
  "updated_by": "uuid"
}
```

**Example:**
```json
{
  "reminders": [
    {
      "id": "rem-new-aaaa-1111-bbbb-222222222222",
      "hours_before": 48,
      "channels": ["email"],
      "is_active": true,
      "templates": {
        "email": {
          "subject": "Recordatorio: Tu cita dental en {{clinic_name}}",
          "body": "Hola {{patient_first_name}}, tienes una cita el {{appointment_date}} a las {{appointment_time}}..."
        },
        "whatsapp": { "message": null },
        "sms": { "message": null }
      }
    },
    {
      "id": "rem-new-cccc-3333-dddd-444444444444",
      "hours_before": 2,
      "channels": ["whatsapp", "sms"],
      "is_active": true,
      "templates": {
        "email": { "subject": null, "body": null },
        "whatsapp": { "message": "Recordatorio: Tienes cita hoy a las {{appointment_time}} en {{clinic_name}}." },
        "sms": { "message": "Cita dental hoy {{appointment_time}} - {{clinic_name}} {{clinic_phone}}" }
      }
    }
  ],
  "default_channels": ["email"],
  "pending_reminders_recalculated": 23,
  "updated_at": "2026-02-25T10:15:00-05:00",
  "updated_by": "usr-clinic-owner-0001-0000-000000000000"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or missing required fields in reminders array.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud contiene errores.",
  "details": {
    "reminders": ["El campo reminders es requerido y debe ser un arreglo."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Authenticated user does not have role `clinic_owner` or `superadmin`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede modificar la configuracion de recordatorios."
}
```

#### 422 Unprocessable Entity
**When:** Validation fails — more than 5 reminder rules, hours_before < 1 or > 168, no channels in a rule, duplicate hours_before values, invalid channel enum, template variable with unknown name, SMS template exceeds 160 chars, email body exceeds 2000 chars.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "La configuracion de recordatorios tiene errores.",
  "details": {
    "reminders[0].hours_before": ["El minimo es 1 hora. El maximo es 168 horas (7 dias)."],
    "reminders[1].channels": ["Debe especificar al menos un canal por regla."],
    "reminders": ["No se permiten mas de 5 reglas de recordatorio."],
    "reminders[2].templates.sms.message": ["El mensaje SMS no puede superar 160 caracteres."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure or RabbitMQ dispatch error.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. Check role: if not `clinic_owner` or `superadmin`, return 403.
3. Validate request body against Pydantic schema.
4. Validate `reminders` array:
   a. Array length must be 1 to 5 (inclusive). If 0 or > 5, return 422.
   b. Each rule: `hours_before` must be integer >= 1 and <= 168.
   c. Each rule: `channels` must be non-empty array; each element must be enum value: email, whatsapp, sms.
   d. No two rules may have the same `hours_before` value — return 422 with "Dos reglas no pueden tener el mismo numero de horas."
   e. Template field validations:
      - `email.subject`: max 200 chars if provided
      - `email.body`: max 2000 chars if provided; validate all `{{variable}}` tokens against allowed list
      - `whatsapp.message`: max 1000 chars if provided; validate variables
      - `sms.message`: max 160 chars if provided; validate variables
   f. Allowed template variables: `{{patient_name}}`, `{{patient_first_name}}`, `{{doctor_name}}`, `{{appointment_date}}`, `{{appointment_time}}`, `{{clinic_name}}`, `{{clinic_phone}}`, `{{clinic_address}}`, `{{confirmation_code}}`. Any other `{{...}}` token returns 422.
5. If `default_channels` provided, validate each channel enum value.
6. Begin database transaction (tenant schema).
7. Delete all existing `reminder_configurations` records for this tenant (`DELETE WHERE tenant_id = :tenant_id`). This is a full replacement strategy.
8. Insert new reminder rules from the provided array. Assign new UUIDs for rules without an `id`; for rules with an existing `id` (from GET response), use the provided ID to maintain stability (re-insert with same ID).
9. Update `tenant_settings.default_channels` and `reminder_config_updated_at = now()`, `reminder_config_updated_by = user_id`.
10. Commit transaction.
11. Delete Redis cache key: `tenant:{tenant_id}:settings:reminders` (force cache miss on next GET).
12. Load future appointments needing reminder recalculation: query `appointments WHERE tenant_id = :tenant_id AND status IN ('scheduled', 'confirmed') AND start_time > now()`. Count them.
13. Dispatch `reminders.recalculate` job to RabbitMQ with payload `{ tenant_id, updated_at }`. The notification worker will re-schedule or cancel pending reminder jobs based on the new configuration. This is async.
14. Write audit log: action `update`, resource `reminder_configuration`, tenant_id, user_id, previous_rules_count, new_rules_count.
15. Return 200 with the saved configuration and `pending_reminders_recalculated` count.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| reminders | Array, min 1, max 5 elements | No se permiten mas de 5 reglas de recordatorio. |
| reminders[].hours_before | Integer, min 1, max 168 | El minimo es 1 hora. El maximo es 168 horas (7 dias). |
| reminders[].channels | Non-empty array, each: email/whatsapp/sms | Debe especificar al menos un canal. Canal invalido: {value}. |
| reminders hours_before uniqueness | No two rules with same hours_before | Dos reglas no pueden tener el mismo numero de horas antes. |
| reminders[].templates.email.subject | Max 200 chars (if not null) | El asunto del email no puede superar 200 caracteres. |
| reminders[].templates.email.body | Max 2000 chars, valid {{variables}} only | El cuerpo del email no puede superar 2000 caracteres. Variable {{x}} no es valida. |
| reminders[].templates.whatsapp.message | Max 1000 chars, valid {{variables}} only | El mensaje de WhatsApp no puede superar 1000 caracteres. |
| reminders[].templates.sms.message | Max 160 chars, valid {{variables}} only | El mensaje SMS no puede superar 160 caracteres (limite de un SMS). |
| default_channels | Array, each: email/whatsapp/sms (if provided) | Canal por defecto invalido: {value}. |

**Business Rules:**

- The PUT operation is a full replacement: all existing reminder rules are deleted and the new set is inserted. This simplifies the API and avoids partial update complexity.
- If a rule `id` is provided in the request (matching an ID from the GET response), the new rule is inserted with that same UUID to preserve any external references (e.g., scheduled jobs referencing the rule ID).
- The `reminders.recalculate` job dispatched to RabbitMQ is asynchronous. The endpoint does not wait for recalculation to complete before returning. The `pending_reminders_recalculated` count in the response is an estimate (count of future scheduled/confirmed appointments), not the exact count of re-queued jobs.
- Setting `is_active = false` on a rule retains the rule in the configuration but disables sending reminders for that timing. The notification worker checks `is_active` before dispatching.
- Sending an empty `reminders: []` array is not allowed (min 1 rule). If the clinic wants to disable all reminders, they must set all rules to `is_active: false`.
- Custom templates persist through updates. To reset a channel template to the system default, send `null` for that template field.
- The `default_channels` field is optional. If omitted, the existing `default_channels` setting is preserved.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| reminders: [] (empty array) | 422 — must have at least 1 rule |
| Duplicate hours_before (e.g., two rules with hours_before=24) | 422 — duplicates not allowed |
| Template body uses {{patient_name}} | Valid — in allowed list |
| Template body uses {{custom_field}} | 422 — unknown template variable |
| Rule id provided but does not match any existing rule | Treated as new rule; a new UUID is assigned and the provided id is ignored |
| All rules set to is_active=false | Valid — returns 200; effectively disables all reminders |
| 6 rules in array | 422 — max 5 |
| hours_before = 0 | 422 — minimum is 1 |
| hours_before = 168 (7 days) | Valid |
| hours_before = 169 | 422 — maximum is 168 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `reminder_configurations`: DELETE all for tenant, then INSERT new set — full replacement
- `tenant_settings`: UPDATE — `default_channels`, `reminder_config_updated_at`, `reminder_config_updated_by`
- `audit_logs`: INSERT — configuration update event

**Example query (SQLAlchemy):**
```python
async with session.begin():
    # Full replacement
    await session.execute(
        delete(ReminderConfiguration).where(
            ReminderConfiguration.tenant_id == tenant_id
        )
    )
    for rule in validated_rules:
        rule_id = rule.id or uuid4()
        await session.execute(
            insert(ReminderConfiguration).values(
                id=rule_id,
                tenant_id=tenant_id,
                hours_before=rule.hours_before,
                channels=rule.channels,
                is_active=rule.is_active,
                template_email_subject=rule.templates.email.subject if rule.templates else None,
                template_email_body=rule.templates.email.body if rule.templates else None,
                template_whatsapp=rule.templates.whatsapp.message if rule.templates else None,
                template_sms=rule.templates.sms.message if rule.templates else None,
            )
        )
    await session.execute(
        update(TenantSettings)
        .where(TenantSettings.tenant_id == tenant_id)
        .values(
            default_channels=body.default_channels or existing_settings.default_channels,
            reminder_config_updated_at=datetime.utcnow(),
            reminder_config_updated_by=user_id,
        )
    )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:settings:reminders`: DELETE — force cache miss on next GET (AP-17)

**Cache TTL:** N/A — deletion only

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | reminders.recalculate | { tenant_id, updated_at, new_rules: [{id, hours_before, channels, is_active}] } | After successful DB commit |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`

- **Action:** update
- **Resource:** reminder_configuration
- **PHI involved:** No — operational settings, not patient data

### Notifications

**Notifications triggered:** No — the reminder recalculation is handled asynchronously by the notification worker consuming the RabbitMQ job.

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 600ms

### Caching Strategy
- **Strategy:** No caching on write; invalidates existing cache
- **Cache key:** `tenant:{tenant_id}:settings:reminders` (DELETED on write)
- **TTL:** N/A — deletion
- **Invalidation:** Immediate on successful commit

### Database Performance

**Queries executed:** 4 (delete existing, insert N new rules, update tenant_settings, count future appointments)

**Indexes required:**
- `reminder_configurations.tenant_id` — INDEX (for DELETE WHERE tenant_id)
- `appointments.(tenant_id, status, start_time)` — COMPOSITE INDEX for pending count query

**N+1 prevention:** All reminder rules inserted with individual INSERT statements within a single transaction (N is bounded by max 5). No per-rule sub-queries.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| reminders[].hours_before | Pydantic int, ge=1, le=168 | Strict numeric range |
| reminders[].channels | Pydantic List[Enum] | Whitelist approach |
| templates.email.subject | Pydantic str, strip, max_length=200, bleach.clean | Rendered in email; sanitize HTML |
| templates.email.body | Pydantic str, strip, max_length=2000, bleach.clean + variable validation | Rendered in email |
| templates.whatsapp.message | Pydantic str, strip, max_length=1000, bleach.clean + variable validation | Sent as plain text |
| templates.sms.message | Pydantic str, strip, max_length=160 | SMS length limit |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. Template bodies sanitized with bleach before storage to prevent stored XSS via email templates.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — reminder settings are operational configuration only.

**Audit requirement:** Write-only logged (configuration update event without PHI).

---

## Testing

### Test Cases

#### Happy Path
1. Update reminders with two new rules
   - **Given:** Authenticated clinic_owner, tenant has existing 2 rules, future appointments exist
   - **When:** PUT /api/v1/settings/reminders with 2 new rules (48h email, 2h WA+SMS)
   - **Then:** 200 OK, old rules replaced, new rules in response with UUIDs, cache key deleted, RabbitMQ job dispatched, pending_reminders_recalculated > 0

2. Update rules preserving existing rule ID
   - **Given:** Existing rule with known id `rem-001-...`
   - **When:** PUT with rule including same `id` field
   - **Then:** 200 OK, rule saved with same UUID

3. Reset a custom template to system default
   - **Given:** Existing rule with custom WhatsApp message
   - **When:** PUT with same rule but `templates.whatsapp.message: null`
   - **Then:** 200 OK, whatsapp.message = null in response

#### Edge Cases
1. All rules set to is_active=false
   - **Given:** Valid 2-rule configuration
   - **When:** PUT with is_active=false on both rules
   - **Then:** 200 OK, both rules saved with is_active=false

2. Single reminder rule (minimum)
   - **Given:** Valid 1-rule configuration
   - **When:** PUT with 1 rule
   - **Then:** 200 OK, reminders array has 1 item

3. Maximum 5 rules
   - **Given:** 5 rules with distinct hours_before values
   - **When:** PUT with 5 rules
   - **Then:** 200 OK, all 5 saved

#### Error Cases
1. More than 5 rules
   - **Given:** Array with 6 reminder rules
   - **When:** PUT
   - **Then:** 422 with max rules error

2. Duplicate hours_before values
   - **Given:** Two rules both with hours_before=24
   - **When:** PUT
   - **Then:** 422 with duplicate hours error

3. Invalid template variable
   - **Given:** email.body contains `{{patient_age}}`
   - **When:** PUT
   - **Then:** 422 with unknown variable error mentioning `{{patient_age}}`

4. SMS message exceeds 160 chars
   - **Given:** sms.message = 161-character string
   - **When:** PUT
   - **Then:** 422 with SMS length error

5. Role is assistant
   - **Given:** User with role=assistant
   - **When:** PUT
   - **Then:** 403 Forbidden

6. Empty channels array on a rule
   - **Given:** Rule with `channels: []`
   - **When:** PUT
   - **Then:** 422 with channel required error

### Test Data Requirements

**Users:** One clinic_owner, one doctor (for 403 test), one assistant (for 403 test)

**Appointments:** 5 future scheduled appointments in the tenant (for pending_reminders_recalculated count)

**Existing Reminder Config:** Tenant with pre-existing 2 reminder rules for replacement test

### Mocking Strategy

- Redis: `fakeredis` — verify cache key deletion after successful PUT
- RabbitMQ: Mock publish; assert `reminders.recalculate` job dispatched with correct tenant_id
- Database: SQLite in-memory; seed existing reminder_configurations and tenant_settings

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] PUT /api/v1/settings/reminders returns 200 with updated configuration
- [ ] Full replacement strategy — old rules deleted, new rules inserted atomically
- [ ] Max 5 rules enforced — 6+ rules returns 422
- [ ] hours_before min=1, max=168 enforced
- [ ] Duplicate hours_before values rejected with 422
- [ ] Template variable validation enforced — unknown variables return 422
- [ ] SMS template max 160 chars enforced
- [ ] Only clinic_owner can update (all other roles return 403)
- [ ] Redis cache key deleted on successful update
- [ ] `reminders.recalculate` job dispatched to RabbitMQ
- [ ] Audit log written
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Reading reminder configuration (see AP-17 reminder-config.md)
- Per-doctor reminder rule overrides (post-MVP)
- Actual reminder dispatch logic (notification worker)
- Patient opt-out from reminders (patient preferences spec)
- WhatsApp Business API template approval workflow (handled at infrastructure level)
- SMS provider management

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (full reminders array schema)
- [x] All outputs defined (saved config + metadata)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (comprehensive)
- [x] Error cases enumerated
- [x] Auth requirements explicit (clinic_owner only)
- [x] Side effects listed (DB replace, cache delete, RabbitMQ job)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (appointments/settings domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Full replacement atomic transaction

### Hook 3: Security & Privacy
- [x] Auth level stated (clinic_owner only)
- [x] Input sanitization (bleach on templates rendered in email)
- [x] SQL injection prevented
- [x] Template variable whitelist enforced
- [x] No PHI involved

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 300ms)
- [x] Cache invalidation on write
- [x] DB transaction bounded (max 5 inserts)
- [x] Async recalculation via RabbitMQ

### Hook 5: Observability
- [x] Structured logging (tenant_id, user_id, rules_count)
- [x] Audit log entries defined
- [x] RabbitMQ job monitoring
- [x] Error tracking compatible

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data specified
- [x] Mocking strategy (fakeredis, RabbitMQ mock)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
