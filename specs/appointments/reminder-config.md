# AP-17 Get Reminder Configuration Spec

---

## Overview

**Feature:** Retrieve the current appointment reminder configuration for the authenticated clinic. Returns an array of reminder rules, each defining when (hours before appointment) and through which channels (email, WhatsApp, SMS) reminders are sent, along with any custom message templates defined per channel. This is a read-only settings endpoint accessible only by clinic_owner.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-18 (reminder-config-update.md), infra/authentication-rules.md, infra/caching.md, notifications domain (channel configuration)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner may view reminder configuration. Other roles (doctor, assistant, receptionist) return 403. Superadmin may access as part of tenant administration.

---

## Endpoint

```
GET /api/v1/settings/reminders
```

**Rate Limiting:**
- Inherits global rate limit (100 requests per minute per user)
- Redis key: `dentalos:rl:user:{user_id}` (shared with global limit)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

None — GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "reminders": [
    {
      "id": "uuid — stable ID for referencing this reminder rule",
      "hours_before": "integer — hours before appointment to send reminder",
      "channels": ["string — enum: email, whatsapp, sms"],
      "is_active": "boolean — whether this reminder rule is enabled",
      "templates": {
        "email": {
          "subject": "string | null — custom email subject, null uses default template",
          "body": "string | null — custom email body with template variables, null uses default"
        },
        "whatsapp": {
          "message": "string | null — custom WhatsApp message text, null uses default"
        },
        "sms": {
          "message": "string | null — custom SMS text, null uses default"
        }
      }
    }
  ],
  "default_channels": ["string — channels enabled by default when reminder rule has no override"],
  "template_variables": ["string — available template variable names, e.g. {{patient_name}}, {{appointment_date}}"],
  "max_reminders_allowed": "integer — maximum number of reminder rules allowed (5)",
  "updated_at": "string | null — ISO 8601 datetime of last configuration update",
  "updated_by": "uuid | null — user ID of last updater"
}
```

**Example:**
```json
{
  "reminders": [
    {
      "id": "rem-001-aaaa-bbbb-cccc-dddddddddddd",
      "hours_before": 24,
      "channels": ["email", "whatsapp"],
      "is_active": true,
      "templates": {
        "email": {
          "subject": "Recordatorio: Cita dental manana en {{clinic_name}}",
          "body": "Hola {{patient_name}}, te recordamos que tienes una cita manana {{appointment_date}} a las {{appointment_time}} con el Dr. {{doctor_name}}. Si necesitas cancelar llama al {{clinic_phone}}."
        },
        "whatsapp": {
          "message": "Hola {{patient_name}}! Recordatorio de tu cita dental manana {{appointment_date}} a las {{appointment_time}} en {{clinic_name}}. Confirma respondiendo SI."
        },
        "sms": {
          "message": null
        }
      }
    },
    {
      "id": "rem-002-eeee-ffff-0000-111111111111",
      "hours_before": 2,
      "channels": ["whatsapp", "sms"],
      "is_active": true,
      "templates": {
        "email": {
          "subject": null,
          "body": null
        },
        "whatsapp": {
          "message": "Recuerda tu cita hoy a las {{appointment_time}} en {{clinic_name}}. Te esperamos!"
        },
        "sms": {
          "message": "Cita dental hoy {{appointment_time}} - {{clinic_name}} {{clinic_phone}}"
        }
      }
    }
  ],
  "default_channels": ["email"],
  "template_variables": [
    "{{patient_name}}",
    "{{patient_first_name}}",
    "{{doctor_name}}",
    "{{appointment_date}}",
    "{{appointment_time}}",
    "{{clinic_name}}",
    "{{clinic_phone}}",
    "{{clinic_address}}",
    "{{confirmation_code}}"
  ],
  "max_reminders_allowed": 5,
  "updated_at": "2026-02-20T15:30:00-05:00",
  "updated_by": "usr-clinic-owner-0001-0000-000000000000"
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Authenticated user does not have role `clinic_owner` or `superadmin`.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede ver la configuracion de recordatorios."
}
```

#### 404 Not Found
**When:** Tenant has no reminder configuration saved yet (first-time access before any configuration is set). In this case, instead of 404, return defaults — see Business Rules.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract `tenant_id`, `user_id`, `role`.
2. Check role: if not `clinic_owner` or `superadmin`, return 403.
3. Check Redis cache: key `tenant:{tenant_id}:settings:reminders`. If cache hit, deserialize and return 200.
4. If cache miss, set `search_path` to tenant schema.
5. Query `reminder_configurations` table: `SELECT * FROM reminder_configurations WHERE tenant_id = :tenant_id ORDER BY hours_before DESC`.
6. If no records found, return the system default configuration (do not return 404 — return 200 with defaults). System defaults:
   - Rule 1: hours_before=24, channels=["email", "whatsapp"], is_active=true, all templates null (use system defaults)
   - Rule 2: hours_before=2, channels=["whatsapp", "sms"], is_active=true, all templates null
7. Load `tenant_settings.default_channels` — fallback channels if a reminder rule has an empty channels array.
8. Load `updated_at` and `updated_by` from the most recently modified reminder_configuration record.
9. Build response with `template_variables` list (static list of available interpolation variables).
10. Serialize and store in Redis cache: key `tenant:{tenant_id}:settings:reminders`, TTL = 600s (10 minutes).
11. Return 200 with full configuration object.

**Validation Rules:**

None — this is a read-only GET endpoint with no user-supplied parameters beyond the JWT.

**Business Rules:**

- If no reminder configuration exists for the tenant, return system defaults rather than 404. This ensures a smooth first-time experience for new tenants.
- The `template_variables` list is static and defined in code, not stored in the database. It represents all interpolation tokens available for custom templates.
- Template bodies with custom content are stored as-is; interpolation happens at notification send time (notification worker).
- The `id` field per reminder rule is a stable UUID used by the PUT endpoint (AP-18) to identify which rule to update. It must be present in the GET response.
- `default_channels` is a tenant-level setting that controls which channels are used when a reminder rule specifies no channels (empty array or null). It defaults to ["email"].
- `max_reminders_allowed = 5` is a system constant returned in the response for frontend validation. It is not stored per tenant.
- Both `updated_at` and `updated_by` may be null if the configuration has never been explicitly saved (using system defaults).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No reminder_configurations records in DB | Return 200 with system default rules (24h email+WA, 2h WA+SMS) |
| Some rules have is_active=false | Return all rules including inactive; frontend decides whether to show them |
| Custom template with unknown variable (e.g. {{unknown_var}}) | Returned as-is; validation is performed at write time (AP-18), not read time |
| Tenant has 5 reminder rules | Return all 5; max_reminders_allowed=5 indicates frontend should disable "add" button |
| updated_by user was deleted | Return updated_by UUID as-is; do not join to users table to avoid broken reference error |

---

## Side Effects

### Database Changes

**No write operations** — this is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:settings:reminders`: SET on cache miss

**Cache TTL:** 600 seconds (10 minutes)

**Cache invalidation:** Deleted by AP-18 (reminder-config-update) on any configuration change.

**Example cache read (Python):**
```python
cache_key = f"tenant:{tenant_id}:settings:reminders"
cached = await redis.get(cache_key)
if cached:
    return ReminderConfigResponse.model_validate_json(cached)

# DB query
rows = await session.execute(
    select(ReminderConfiguration)
    .where(ReminderConfiguration.tenant_id == tenant_id)
    .order_by(ReminderConfiguration.hours_before.desc())
)
reminders = rows.scalars().all()

if not reminders:
    reminders = get_default_reminder_rules()

response = build_response(reminders)
await redis.set(cache_key, response.model_dump_json(), ex=600)
return response
```

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — read-only endpoint.

### Audit Log

**Audit entry:** No — reading settings does not require audit logging. PHI is not involved.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 30ms (cache hit)
- **Target:** < 100ms (cache miss)
- **Maximum acceptable:** < 200ms (cache miss under load)

### Caching Strategy
- **Strategy:** Full response Redis cache with 10-minute TTL
- **Cache key:** `tenant:{tenant_id}:settings:reminders`
- **TTL:** 600 seconds
- **Invalidation:** Explicit key deletion by AP-18 on any update

### Database Performance

**Queries executed (cache miss only):** 1-2 (reminder configurations query, optional tenant settings for default_channels)

**Indexes required:**
- `reminder_configurations.tenant_id` — INDEX (reminder configs scoped per tenant)
- `reminder_configurations.(tenant_id, hours_before)` — COMPOSITE INDEX for ordered lookup

**N+1 prevention:** All reminder rules returned in a single query. No per-rule sub-queries.

### Pagination

**Pagination:** No — maximum 5 reminder rules per tenant; full list returned in single response.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| Authorization header | Pydantic Bearer token validator | Standard JWT validation |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. Custom template bodies were sanitized with bleach at write time (AP-18).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — reminder settings contain clinic operational data only, not patient health information.

**Audit requirement:** Not required.

---

## Testing

### Test Cases

#### Happy Path
1. Fetch configuration for tenant with custom reminders
   - **Given:** Authenticated clinic_owner, tenant has 2 reminder rules saved (24h and 2h), custom templates on the 24h rule
   - **When:** GET /api/v1/settings/reminders
   - **Then:** 200 OK, both rules returned with correct hours_before, channels, and templates

2. First-time fetch with no configured reminders returns defaults
   - **Given:** Authenticated clinic_owner, tenant has no reminder_configurations records
   - **When:** GET /api/v1/settings/reminders
   - **Then:** 200 OK, returns system defaults (24h email+WA, 2h WA+SMS), all template fields null, updated_at=null

3. Cache hit on second request
   - **Given:** First request populated Redis cache
   - **When:** Second GET within 10 minutes
   - **Then:** 200 OK, served from cache (no DB queries)

#### Edge Cases
1. Tenant has maximum 5 reminder rules
   - **Given:** 5 reminder rules configured
   - **When:** GET reminders
   - **Then:** 200 OK, reminders array has exactly 5 items, max_reminders_allowed=5

2. One reminder rule is inactive
   - **Given:** Rule with is_active=false exists
   - **When:** GET reminders
   - **Then:** All rules returned including the inactive one; is_active=false present in response

#### Error Cases
1. Role is receptionist
   - **Given:** Authenticated user with role=receptionist
   - **When:** GET /api/v1/settings/reminders
   - **Then:** 403 Forbidden with appropriate message

2. Role is doctor
   - **Given:** Authenticated user with role=doctor
   - **When:** GET /api/v1/settings/reminders
   - **Then:** 403 Forbidden

3. No JWT provided
   - **Given:** Request without Authorization header
   - **When:** GET /api/v1/settings/reminders
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** One clinic_owner, one doctor, one receptionist (all in same tenant)

**Reminder Configurations:** Tenant with 2 custom rules; tenant with no rules (defaults); tenant with 5 rules (max)

### Mocking Strategy

- Redis: Use `fakeredis` to test both cache hit and cache miss paths
- Database: SQLite in-memory for unit tests; seed reminder_configurations table

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/settings/reminders returns 200 with complete reminder config object
- [ ] System defaults returned when no configuration saved (not 404)
- [ ] Only clinic_owner and superadmin can access (other roles return 403)
- [ ] Response cached for 10 minutes
- [ ] template_variables list included in every response
- [ ] max_reminders_allowed=5 always present in response
- [ ] All test cases pass
- [ ] Performance targets met (< 30ms cache hit, < 100ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Updating reminder configuration (see AP-18 reminder-config-update.md)
- Sending reminders (handled by notification worker consuming RabbitMQ jobs)
- Per-doctor reminder overrides (post-MVP)
- Reminder delivery reports/logs (see notifications domain)
- Patient opt-out from reminders (see patient preferences spec)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (JWT only)
- [x] All outputs defined (full config with reminders array)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (role check only)
- [x] Error cases enumerated
- [x] Auth requirements explicit (clinic_owner only)
- [x] Side effects listed (cache write only)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (appointments/settings domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models consistent

### Hook 3: Security & Privacy
- [x] Auth level stated (clinic_owner only)
- [x] No PHI in response
- [x] SQL injection prevented
- [x] Audit not required (non-PHI settings read)

### Hook 4: Performance & Scalability
- [x] Response time targets defined
- [x] Full response caching (10min TTL)
- [x] DB queries minimal (1-2 on miss)
- [x] Pagination N/A (max 5 rules)

### Hook 5: Observability
- [x] Structured logging (tenant_id, cache hit/miss)
- [x] No PHI in logs
- [x] Error tracking compatible

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data specified
- [x] Mocking strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
