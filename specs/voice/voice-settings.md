# Voice Settings Spec

> **Spec ID:** V-05
> **Status:** Draft
> **Last Updated:** 2026-02-24

---

## Overview

**Feature:** Provides tenant-level configuration for the Voice-to-Odontogram feature. A GET endpoint allows any authenticated user to retrieve the current voice settings (to know if voice is enabled and how it is configured). A PUT endpoint allows the clinic_owner to update settings. The `enabled` flag acts as the master switch and is gated by the tenant's Voice add-on subscription status. Settings are cached in Redis for fast access since every voice endpoint (V-01 through V-04) checks them.

**Domain:** voice

**Priority:** High

**Dependencies:** V-01 (voice-capture.md), V-02 (voice-transcription.md), V-03 (voice-parse.md), V-04 (voice-apply.md), I-01 (multi-tenancy.md), infra/caching-strategy.md, tenants/tenant-settings-get.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:**
  - GET: clinic_owner, doctor, assistant, receptionist (any authenticated staff)
  - PUT: clinic_owner only
- **Tenant context:** Required — resolved from JWT
- **Special rules:** The Voice add-on subscription status is checked on PUT when setting `enabled: true`. If the add-on is not active in `public.tenant_addons`, enabling voice returns 402. The `enabled` field cannot be set to `true` without an active add-on.

---

## Endpoints

```
GET /api/v1/settings/voice
PUT /api/v1/settings/voice
```

---

## GET /api/v1/settings/voice

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

### Request

#### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

#### URL Parameters

None.

#### Query Parameters

None.

#### Request Body

None.

### Response

#### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "enabled": "boolean",
  "addon_active": "boolean",
  "confirmation_mode": "string",
  "default_context": "string",
  "language": "string",
  "whisper_model": "string",
  "max_session_minutes": "integer",
  "updated_at": "string (ISO 8601 datetime) | null",
  "updated_by": "string (uuid) | null"
}
```

**Example (voice enabled, review-first mode):**
```json
{
  "enabled": true,
  "addon_active": true,
  "confirmation_mode": "review_first",
  "default_context": "odontogram",
  "language": "es",
  "whisper_model": "large-v3",
  "max_session_minutes": 30,
  "updated_at": "2026-02-24T10:00:00Z",
  "updated_by": "c3d4e5f6-a1b2-7890-abcd-1234567890ef"
}
```

**Example (add-on not purchased — voice disabled):**
```json
{
  "enabled": false,
  "addon_active": false,
  "confirmation_mode": "review_first",
  "default_context": "odontogram",
  "language": "es",
  "whisper_model": "large-v3",
  "max_session_minutes": 30,
  "updated_at": null,
  "updated_by": null
}
```

#### Error Responses

##### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

##### 403 Forbidden
**When:** User role is not allowed (e.g., patient role).

---

### Business Logic (GET)

**Step-by-step process:**

1. Resolve tenant from JWT.
2. Check user role (must be any staff role: clinic_owner, doctor, assistant, receptionist).
3. Check Redis cache: `tenant:{tenant_id}:settings:voice`. If hit, return cached value.
4. Fetch voice settings from `tenant_voice_settings` table. If no row exists (new tenant), return defaults.
5. Fetch add-on status from `public.tenant_addons` where `tenant_id = :tid AND addon = 'voice'`. Set `addon_active` accordingly.
6. If `addon_active = false` and stored `enabled = true`: return `enabled = false` (add-on revocation disables voice without modifying stored settings — allows re-enabling by re-activating add-on).
7. Store result in Redis cache with 5-minute TTL.
8. Return 200 with settings.

**Caching note:** The 5-minute TTL balances freshness with performance. Voice-active endpoints (V-01 to V-04) read settings on every request. At 50 sessions/hour per doctor, that is < 1 uncached add-on check per 5 minutes per doctor.

---

## PUT /api/v1/settings/voice

**Rate Limiting:**
- 20 requests per hour per user (settings changes are infrequent; throttle prevents config spam)
- Rate limit key: `voice:settings_update:{user_id}`

### Request

#### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

#### URL Parameters

None.

#### Query Parameters

None.

#### Request Body Schema

All fields are optional. Only provided fields are updated (PATCH semantics on a PUT endpoint).

```json
{
  "enabled": "boolean (optional) — requires active Voice add-on to set to true",
  "confirmation_mode": "string (optional) — enum: review_first | auto_apply",
  "default_context": "string (optional) — enum: odontogram | evolution",
  "language": "string (optional) — enum: es | es-CO | es-MX",
  "whisper_model": "string (optional) — enum: large-v3 (only valid value for MVP)",
  "max_session_minutes": "integer (optional) — fixed at 30 for MVP; field accepted but ignored with a warning"
}
```

**Example Request (enable voice with auto_apply for an experienced dentist):**
```json
{
  "enabled": true,
  "confirmation_mode": "auto_apply",
  "default_context": "odontogram",
  "language": "es-CO"
}
```

**Example Request (disable voice):**
```json
{
  "enabled": false
}
```

### Response

#### Success Response

**Status:** 200 OK

**Schema:** Same as GET response, plus optional `warnings` field.

```json
{
  "enabled": "boolean",
  "addon_active": "boolean",
  "confirmation_mode": "string",
  "default_context": "string",
  "language": "string",
  "whisper_model": "string",
  "max_session_minutes": "integer",
  "updated_at": "string (ISO 8601 datetime)",
  "updated_by": "string (uuid)",
  "warnings": "string[] (optional)"
}
```

**Example:**
```json
{
  "enabled": true,
  "addon_active": true,
  "confirmation_mode": "auto_apply",
  "default_context": "odontogram",
  "language": "es-CO",
  "whisper_model": "large-v3",
  "max_session_minutes": 30,
  "updated_at": "2026-02-24T14:30:00Z",
  "updated_by": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "warnings": [
    "El modo 'auto_apply' aplica hallazgos automaticamente sin revision humana. Use con precaucion en entornos clinicos."
  ]
}
```

**Example (max_session_minutes overridden ignored):**
```json
{
  "enabled": true,
  "addon_active": true,
  "confirmation_mode": "review_first",
  "default_context": "odontogram",
  "language": "es",
  "whisper_model": "large-v3",
  "max_session_minutes": 30,
  "updated_at": "2026-02-24T14:30:00Z",
  "updated_by": "c3d4e5f6-a1b2-7890-abcd-1234567890ef",
  "warnings": [
    "El campo 'max_session_minutes' es fijo en 30 minutos para esta version. El valor proporcionado fue ignorado."
  ]
}
```

#### Error Responses

##### 400 Bad Request
**When:** Invalid field values (unknown enum, wrong type).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "language": ["Idioma no valido. Opciones: es, es-CO, es-MX."]
  }
}
```

##### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

##### 402 Payment Required
**When:** Attempting to set `enabled: true` but the Voice add-on is not active.

**Example:**
```json
{
  "error": "addon_required",
  "message": "No se puede activar la funcion de voz sin el complemento de Voz activo. Contacte a su administrador de cuenta para adquirirlo.",
  "details": {
    "addon": "voice",
    "upgrade_url": "/settings/billing/addons"
  }
}
```

##### 403 Forbidden
**When:** User role is not clinic_owner.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clinica puede modificar la configuracion de voz."
}
```

##### 422 Unprocessable Entity
**When:** Body is valid JSON but field values fail business validation.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "whisper_model": ["El modelo 'whisper-small' no esta disponible. Solo 'large-v3' esta soportado en esta version."]
  }
}
```

##### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

##### 500 Internal Server Error
**When:** Unexpected database failure.

---

### Business Logic (PUT)

**Step-by-step process:**

1. Validate request body against Pydantic schema (all fields optional; at least one must be provided or return 400).
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Check user role: must be clinic_owner. If not, return 403.
4. If `enabled = true` is being set: check `public.tenant_addons` for active Voice add-on. If not active, return 402.
5. If `whisper_model` is provided and is not "large-v3": return 422 (only supported model in MVP).
6. If `max_session_minutes` is provided: note it in `warnings[]` — the value is ignored, and 30 is always stored.
7. If `confirmation_mode = "auto_apply"` is being set: add warning to `warnings[]` about bypassing human review.
8. Fetch existing settings row: `SELECT * FROM tenant_voice_settings WHERE tenant_id = :tid FOR UPDATE`.
9. If no row exists: INSERT new row with provided values merged over defaults.
10. If row exists: UPDATE only the provided fields (PATCH semantics — missing fields keep their current values).
11. Invalidate Redis cache: `DELETE tenant:{tenant_id}:settings:voice`.
12. Write audit log (action: update, resource: tenant_voice_settings, PHI: no — settings are configuration, not patient data).
13. Return 200 with updated settings and any warnings.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| enabled | Boolean; requires add-on if true | No se puede activar sin el complemento de Voz. |
| confirmation_mode | Enum: review_first, auto_apply | Modo de confirmacion no valido. Opciones: review_first, auto_apply. |
| default_context | Enum: odontogram, evolution | Contexto predeterminado no valido. Opciones: odontogram, evolution. |
| language | Enum: es, es-CO, es-MX | Idioma no valido. Opciones: es, es-CO, es-MX. |
| whisper_model | Enum: large-v3 (only) | Solo 'large-v3' esta soportado en esta version. |
| max_session_minutes | Integer; ignored in MVP | Ignorado. Fijo en 30 minutos. (warning, not error) |

**Default Values (when no settings row exists):**

| Field | Default |
|-------|---------|
| enabled | false |
| confirmation_mode | review_first |
| default_context | odontogram |
| language | es |
| whisper_model | large-v3 |
| max_session_minutes | 30 |

**Business Rules:**

- Only clinic_owner can update settings. This prevents a rogue doctor or assistant from enabling auto_apply without authorization.
- Disabling voice (`enabled: false`) does not terminate open voice sessions. Those sessions continue until they expire naturally (30-minute inactivity timeout). New session creation (V-01) will be blocked by the enabled check.
- Language setting controls the `language` parameter sent to Whisper (V-02). `es-CO` and `es-MX` are mapped to `es` with a regional hint in the prompt (Whisper supports `es` as the language code; regional variants are handled by prompt engineering in V-03).
- `confirmation_mode: auto_apply` is an advanced setting. The API returns a persistent warning when this is set. The mode is enforced by the frontend, not by the API (the apply endpoint V-04 works the same regardless of mode).
- The `whisper_model` field is exposed for future extensibility (e.g., when OpenAI releases new models or when we add self-hosted Whisper). For MVP, only `large-v3` is supported.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| PUT with empty body `{}` | Return 400: at least one field must be provided |
| PUT enabled=false when voice is already disabled | Accept (idempotent); return 200 with current settings |
| PUT only language change (no enabled change) | Update only language; add-on check NOT required (not changing enabled) |
| Add-on lapses after enabled=true is set | GET returns enabled=false (computed from addon_active check); stored enabled value remains true (re-activating add-on re-enables voice without another PUT) |
| clinic_owner role not provisioned in tenant | Standard 403 from RBAC; no special handling |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `tenant_voice_settings`: INSERT or UPDATE — voice configuration for the tenant

**Example query (SQLAlchemy — upsert pattern):**
```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

values = {k: v for k, v in data.dict().items() if v is not None}
values["updated_at"] = datetime.now(timezone.utc)
values["updated_by"] = current_user.id
values["tenant_id"] = tenant_id

stmt = pg_insert(TenantVoiceSettings).values(**values)
stmt = stmt.on_conflict_do_update(
    index_elements=["tenant_id"],
    set_={k: stmt.excluded[k] for k in values if k != "tenant_id"},
)
await db_session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:settings:voice`: SET (GET) or DELETE/INVALIDATE (PUT) — voice settings cache

**Cache TTL:**
- GET: 5 minutes (TTL set on write to cache)
- PUT: Key deleted on settings update; next GET will repopulate

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes (GET):**
- **Action:** read
- **Resource:** tenant_voice_settings
- **PHI involved:** No (settings are configuration, not patient data)

**If Yes (PUT):**
- **Action:** update
- **Resource:** tenant_voice_settings
- **PHI involved:** No
- **Additional fields logged:** `changed_fields`, `previous_values` (for settings changes — enable complete change history without PHI concerns)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target (GET):** < 50ms (served from Redis cache in most cases)
- **Maximum acceptable (GET):** < 200ms (DB fallback)
- **Target (PUT):** < 200ms
- **Maximum acceptable (PUT):** < 500ms

### Caching Strategy
- **Strategy:** Redis cache with 5-minute TTL (aggressive caching since every voice endpoint reads settings)
- **Cache key:** `tenant:{tenant_id}:settings:voice`
- **TTL:** 300 seconds (5 minutes)
- **Invalidation:** Immediately on PUT (DELETE key)
- **Serialization:** JSON string stored in Redis; deserialized to Pydantic model on retrieval

### Database Performance

**Queries executed (GET):** 1 (settings fetch) + 1 (add-on check) — only on cache miss

**Queries executed (PUT):** 2 (add-on check + upsert) + 1 (read-back for response)

**Indexes required:**
- `tenant_voice_settings.tenant_id` — UNIQUE (one row per tenant; primary index for upsert)
- `public.tenant_addons.(tenant_id, addon)` — UNIQUE INDEX (already defined; used for add-on check)

**N+1 prevention:** Single query for settings + single query for add-on status. No joins or loops.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| enabled | Pydantic boolean | Strict bool; no truthy strings accepted |
| confirmation_mode | Pydantic enum validator | Only review_first or auto_apply |
| default_context | Pydantic enum validator | Only odontogram or evolution |
| language | Pydantic enum validator | Only es, es-CO, es-MX |
| whisper_model | Pydantic enum validator | Only large-v3 for MVP |
| max_session_minutes | Pydantic integer; value ignored | Accepted to avoid breaking future clients |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. PostgreSQL upsert via `pg_insert(...).on_conflict_do_update(...)`. No raw SQL.

### XSS Prevention

**Output encoding:** All outputs are enum values or booleans/integers. No user-supplied free text in settings. Pydantic serialization escapes by default.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Voice settings are clinic configuration, not patient data.

**Audit requirement:** PUT operations logged with changed_fields and previous_values for compliance change tracking. GET operations logged at DEBUG level only (high-frequency, no PHI).

---

## Testing

### Test Cases

#### Happy Path
1. GET settings for tenant with Voice add-on active
   - **Given:** Tenant has Voice add-on, settings row exists with enabled=true, review_first
   - **When:** GET /api/v1/settings/voice as doctor
   - **Then:** 200 OK with all fields, enabled=true, addon_active=true

2. GET settings served from cache on second call
   - **Given:** First GET populated Redis cache
   - **When:** Second GET within 5-minute window
   - **Then:** 200 OK, no DB query executed (verified via query counter or mock)

3. GET settings for tenant without Voice add-on (returns defaults)
   - **Given:** Tenant without Voice add-on, no settings row
   - **When:** GET as doctor
   - **Then:** 200 OK, enabled=false, addon_active=false, all defaults

4. PUT by clinic_owner enables voice
   - **Given:** Voice add-on active, current enabled=false
   - **When:** PUT with {enabled: true, confirmation_mode: "review_first"}
   - **Then:** 200 OK, enabled=true, confirmation_mode=review_first, Redis cache invalidated

5. PUT sets auto_apply with warning
   - **Given:** Voice add-on active
   - **When:** PUT with {confirmation_mode: "auto_apply"}
   - **Then:** 200 OK, confirmation_mode=auto_apply, warnings contains auto_apply caution message

6. PUT ignores max_session_minutes with warning
   - **Given:** Any valid state
   - **When:** PUT with {max_session_minutes: 60}
   - **Then:** 200 OK, max_session_minutes=30 (unchanged), warnings contains field-ignored message

7. GET after add-on lapses (enabled stored as true, add-on inactive)
   - **Given:** Settings row has enabled=true, but add-on is now inactive
   - **When:** GET
   - **Then:** 200 OK, enabled=false (computed), addon_active=false (stored true overridden by add-on check)

#### Edge Cases
1. GET with no settings row (fresh tenant)
   - **Given:** New tenant, no voice settings row in DB
   - **When:** GET
   - **Then:** 200 OK with all default values, enabled=false

2. PUT only language change (no enabled field)
   - **Given:** enabled=true already, add-on active
   - **When:** PUT with {language: "es-MX"}
   - **Then:** 200 OK, language=es-MX, enabled=true unchanged, no add-on check triggered

3. PUT with empty body
   - **Given:** Any state
   - **When:** PUT with {}
   - **Then:** 400 Bad Request (at least one field required)

#### Error Cases
1. PUT enable=true without add-on
   - **Given:** Tenant does not have Voice add-on
   - **When:** PUT with {enabled: true}
   - **Then:** 402 Payment Required with upgrade_url

2. PUT by doctor (not clinic_owner)
   - **Given:** Authenticated as doctor
   - **When:** PUT with {enabled: false}
   - **Then:** 403 Forbidden

3. GET by patient role
   - **Given:** Authenticated as patient
   - **When:** GET /api/v1/settings/voice
   - **Then:** 403 Forbidden

4. Invalid language value
   - **Given:** Any valid auth
   - **When:** PUT with {language: "en"}
   - **Then:** 422 Unprocessable Entity with language validation error

### Test Data Requirements

**Users:** clinic_owner (primary for PUT), doctor (GET test), patient role (negative test)

**Tenants:** Tenant with Voice add-on active, tenant without Voice add-on, tenant with settings row, tenant without settings row (fresh)

### Mocking Strategy

- Redis: `fakeredis` for cache hit/miss tests
- Add-on check: Fixture with known addon states (active/inactive)
- Database: Real PostgreSQL for integration tests (upsert behavior requires real DB); SQLAlchemy mock for unit tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns current voice settings for any authenticated staff role
- [ ] GET returns defaults when no settings row exists (fresh tenant)
- [ ] GET result served from Redis cache (5-min TTL) on subsequent calls
- [ ] GET returns enabled=false when add-on is inactive, even if stored as true
- [ ] PUT updates only provided fields (PATCH semantics)
- [ ] PUT by non-clinic_owner returns 403
- [ ] PUT with enabled=true without active add-on returns 402
- [ ] PUT with auto_apply returns warning in response
- [ ] PUT with max_session_minutes returns warning and uses fixed value 30
- [ ] PUT invalidates Redis cache immediately
- [ ] Audit log entry written for PUT with changed_fields
- [ ] All test cases pass
- [ ] Performance target met (< 50ms GET from cache, < 200ms PUT)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Per-doctor voice settings (only tenant-level for MVP; per-doctor preferences are a future enhancement)
- Voice usage analytics or cost dashboards (analytics domain)
- Add-on purchase flow (billing domain)
- Voice feature flag rollout by region or plan tier (infrastructure concern)
- Whisper model selection beyond large-v3 (future spec when new models are available)
- Custom dental vocabulary lists per tenant (future enhancement to V-03 prompt)
- Auto_apply confirmation logic enforcement in the API (frontend responsibility)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant, different roles for GET vs PUT)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md conventions

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context; different roles for GET vs PUT)
- [x] Input sanitization defined (Pydantic enum validators)
- [x] SQL injection prevented (SQLAlchemy ORM, pg_insert upsert)
- [x] No PHI in settings (configuration data only)
- [x] Audit trail for settings changes (changed_fields logged)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 50ms GET from cache)
- [x] Caching strategy stated (tenant-namespaced, 5-min TTL)
- [x] DB queries optimized (indexes listed, upsert pattern)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (PUT only; GET at DEBUG level)
- [x] Error tracking (Sentry-compatible)
- [x] Cache hit/miss observable via Redis metrics

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services (Redis, add-on check)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec — Voice-to-Odontogram MVP |
