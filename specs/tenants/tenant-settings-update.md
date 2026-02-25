# Tenant Settings Update Spec

---

## Overview

**Feature:** Clinic owner endpoint to update tenant settings: clinic_name, address, phone, logo (file upload), timezone, locale, odontogram_mode, notification preferences, and branding colors. Validates plan constraints (e.g., anatomic odontogram only if plan allows it). Invalidates cached settings after update.

**Domain:** tenants

**Priority:** High

**Spec ID:** T-07

**Dependencies:** T-06 (tenant-settings-get.md), T-01 (tenant-provision.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Blocked for suspended tenants (write operation).

---

## Endpoint

```
PUT /api/v1/settings
```

**Rate Limiting:**
- 20 requests per minute per user

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json or multipart/form-data (if logo upload) |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

All fields are optional. Only provided fields are updated (partial update semantics via deep merge).

```json
{
  "clinic_name": "string (optional) — display name for the clinic",
  "address": "string (optional) — clinic physical address",
  "phone": "string (optional) — clinic phone number",
  "timezone": "string (optional) — IANA timezone",
  "locale": "string (optional) — locale code: es, en, pt",
  "odontogram_mode": "string (optional) — classic or anatomic",
  "default_appointment_duration_min": "integer (optional) — 15, 30, 45, 60",
  "cancellation_policy_hours": "integer (optional) — 0-72",
  "reminder_channels": "array (optional) — [whatsapp, email, sms]",
  "reminder_timing_hours": "array (optional) — e.g. [24, 2]",
  "branding": {
    "primary_color": "string (optional) — hex color code",
    "clinic_name_display": "string (optional) — display override"
  }
}
```

For logo upload, use `multipart/form-data` with a `logo` file field alongside a `settings` JSON field.

**Example Request (JSON):**
```json
{
  "clinic_name": "Clínica Dental Sonrisa Premium",
  "odontogram_mode": "anatomic",
  "branding": {
    "primary_color": "#10B981"
  },
  "reminder_channels": ["whatsapp", "email"]
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "message": "string",
  "clinic": {
    "name": "string",
    "address": "string | null",
    "phone": "string | null",
    "logo_url": "string | null"
  },
  "preferences": {
    "odontogram_mode": "string",
    "default_appointment_duration_min": "integer",
    "cancellation_policy_hours": "integer",
    "reminder_channels": ["string"],
    "reminder_timing_hours": ["integer"]
  },
  "branding": {
    "primary_color": "string",
    "clinic_name_display": "string"
  },
  "updated_at": "datetime"
}
```

**Example:**
```json
{
  "message": "Configuración actualizada exitosamente.",
  "clinic": {
    "name": "Clínica Dental Sonrisa Premium",
    "address": "Calle 100 #15-20, Bogotá",
    "phone": "+573001234567",
    "logo_url": "https://cdn.dentalos.app/tenants/a1b2c3d4/logo.png"
  },
  "preferences": {
    "odontogram_mode": "anatomic",
    "default_appointment_duration_min": 30,
    "cancellation_policy_hours": 24,
    "reminder_channels": ["whatsapp", "email"],
    "reminder_timing_hours": [24, 2]
  },
  "branding": {
    "primary_color": "#10B981",
    "clinic_name_display": "Clínica Dental Sonrisa Premium"
  },
  "updated_at": "2026-02-24T16:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid field values or format.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Datos de entrada inválidos.",
  "details": {
    "branding.primary_color": ["El color debe ser un código hexadecimal válido (ej: #FF5733)."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT.

#### 403 Forbidden
**When:** User is not clinic_owner, or tenant is suspended.

**Example (not owner):**
```json
{
  "error": "forbidden",
  "message": "Solo el propietario de la clínica puede modificar la configuración."
}
```

**Example (suspended):**
```json
{
  "error": "tenant_suspended",
  "message": "La cuenta está suspendida. No se permiten modificaciones. Contacte soporte."
}
```

#### 409 Conflict
**When:** Trying to set odontogram_mode=anatomic but plan does not include that feature.

**Example:**
```json
{
  "error": "feature_not_available",
  "message": "El modo de odontograma anatómico no está disponible en su plan actual. Actualice a un plan superior."
}
```

#### 413 Payload Too Large
**When:** Logo file exceeds 2MB.

**Example:**
```json
{
  "error": "file_too_large",
  "message": "El archivo del logo no debe superar 2 MB."
}
```

#### 422 Unprocessable Entity
**When:** Validation failures.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validación.",
  "details": {
    "timezone": ["Zona horaria inválida."],
    "locale": ["Idioma no soportado. Opciones: es, en, pt."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded.

---

## Business Logic

**Step-by-step process:**

1. Extract tenant_id and user_id from JWT claims.
2. Resolve tenant context via TenantMiddleware.
3. Verify user role is `clinic_owner` (from JWT `role` claim).
4. Verify tenant status is `active` (writes blocked for suspended).
5. Validate request body against Pydantic schema (`TenantSettingsUpdateRequest`).
6. If `odontogram_mode = 'anatomic'`: check plan features include `odontogram_anatomic = true`. If not, return 409.
7. If `reminder_channels` includes `whatsapp`: check plan features include `whatsapp_reminders = true`. If not, return 409.
8. If logo file provided:
   a. Validate file type (PNG, JPG, SVG only) and size (max 2MB).
   b. Upload to S3 bucket: `tenants/{tenant_id}/logo.{ext}`.
   c. Generate CDN URL.
   d. Set `logo_url` on tenant record.
9. Update `public.tenants` fields:
   a. `name` = clinic_name (if provided)
   b. `phone` = phone (if provided)
   c. `address` = address (if provided)
   d. `timezone` = timezone (if provided)
   e. `locale` = locale (if provided)
   f. Deep merge `settings` JSONB with preference/branding changes.
10. Set `updated_at = now()`.
11. Invalidate Redis caches: `tenant:{tenant_id}:info`, `tenant:{tenant_id}:settings:resolved`.
12. Log audit entry.
13. Return updated settings.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| clinic_name | 2-200 characters | El nombre de la clínica debe tener entre 2 y 200 caracteres. |
| address | Max 500 characters | La dirección no debe superar 500 caracteres. |
| phone | E.164 format or 7-20 digits | Formato de teléfono inválido. |
| timezone | Valid IANA timezone | Zona horaria inválida. |
| locale | Enum: es, en, pt | Idioma no soportado. Opciones: es, en, pt. |
| odontogram_mode | Enum: classic, anatomic | Modo de odontograma inválido. |
| default_appointment_duration_min | Enum: 15, 30, 45, 60 | Duración de cita no válida. Opciones: 15, 30, 45, 60 minutos. |
| cancellation_policy_hours | Integer 0-72 | Las horas de cancelación deben estar entre 0 y 72. |
| reminder_channels | Array of: whatsapp, email, sms | Canal de recordatorio no válido. |
| reminder_timing_hours | Array of integers 1-168 | Las horas de recordatorio deben estar entre 1 y 168. |
| branding.primary_color | Hex color `^#[0-9A-Fa-f]{6}$` | El color debe ser un código hexadecimal válido. |
| branding.clinic_name_display | 2-100 characters | El nombre de exhibición debe tener entre 2 y 100 caracteres. |
| logo file | PNG/JPG/SVG, max 2MB | Formato de archivo no soportado o archivo demasiado grande. |

**Business Rules:**

- Only `clinic_owner` can update settings. Other roles get 403.
- Plan-gated features (anatomic odontogram, WhatsApp) must be validated before saving.
- Logo upload replaces the previous logo (no versioning).
- Settings use deep merge: existing keys not in the request body are preserved.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Empty request body | 200 OK, no changes made. |
| Setting odontogram_mode back to classic | Always allowed regardless of plan. |
| Logo upload with invalid MIME type | 400 Bad Request. |
| Concurrent settings updates | Last-write-wins; updated_at prevents stale reads. |

---

## Side Effects

### Database Changes

**Public schema tables affected:**
- `public.tenants`: UPDATE — name, phone, address, logo_url, timezone, locale, settings, updated_at

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:info`: INVALIDATE
- `tenant:{tenant_id}:settings:resolved`: INVALIDATE

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| file_processing | logo.upload | { tenant_id, file_path, content_type } | When logo file provided |

### Audit Log

**Audit entry:** Yes — tenant settings change.

- **Action:** update
- **Resource:** tenant_settings
- **PHI involved:** No

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms (without logo), < 2000ms (with logo upload)
- **Maximum acceptable:** < 500ms (without logo), < 5000ms (with logo)

### Caching Strategy
- **Strategy:** Cache invalidation on update
- **Cache key:** `tenant:{tenant_id}:info`, `tenant:{tenant_id}:settings:resolved`
- **TTL:** Invalidated on update
- **Invalidation:** Immediate

### Database Performance

**Queries executed:** 2 (load tenant + plan for validation, update tenant)

**Indexes required:**
- `public.tenants.id` — PRIMARY KEY

**N+1 prevention:** Not applicable (single resource update)

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| clinic_name | Pydantic strip, HTML stripped | Max 200 chars |
| address | Pydantic strip, HTML stripped | Max 500 chars |
| phone | Pydantic regex validator | E.164 or digits only |
| branding.primary_color | Pydantic regex ^#[0-9A-Fa-f]{6}$ | Hex only |
| logo file | MIME type validation, size check | PNG/JPG/SVG, max 2MB |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None (clinic settings, not patient data)

**Audit requirement:** Write-only logged

---

## Testing

### Test Cases

#### Happy Path
1. Update clinic name and branding
   - **Given:** Authenticated clinic_owner
   - **When:** PUT with clinic_name and branding.primary_color
   - **Then:** 200 OK, settings updated, cache invalidated

2. Upload logo
   - **Given:** Authenticated clinic_owner
   - **When:** PUT multipart with logo file (PNG, 500KB)
   - **Then:** 200 OK, logo_url updated

3. Change odontogram mode to anatomic
   - **Given:** Plan includes odontogram_anatomic feature
   - **When:** PUT with odontogram_mode=anatomic
   - **Then:** 200 OK

#### Edge Cases
1. Empty body
   - **Given:** Valid auth
   - **When:** PUT with {}
   - **Then:** 200 OK, no changes

2. Deep merge preserves existing settings
   - **Given:** Existing branding with primary_color and clinic_name_display
   - **When:** PUT with only branding.primary_color
   - **Then:** clinic_name_display preserved

#### Error Cases
1. Non-owner role
   - **Given:** User with doctor role
   - **When:** PUT
   - **Then:** 403 Forbidden

2. Anatomic odontogram on free plan
   - **Given:** Plan does not include odontogram_anatomic
   - **When:** PUT with odontogram_mode=anatomic
   - **Then:** 409 Conflict (feature_not_available)

3. Logo too large
   - **Given:** Logo file 5MB
   - **When:** PUT multipart
   - **Then:** 413 Payload Too Large

4. Suspended tenant
   - **Given:** Tenant is suspended
   - **When:** PUT
   - **Then:** 403 Forbidden (tenant_suspended)

### Test Data Requirements

**Users:** clinic_owner, doctor (for permission test)

**Entities:** Active tenant with starter plan and professional plan (for feature gating)

### Mocking Strategy

- S3/file storage: Mock upload service
- Redis: Mock or use test Redis instance

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Clinic owner can update all settings fields
- [ ] Logo upload works with PNG, JPG, SVG
- [ ] Plan-gated features validated (odontogram_anatomic, whatsapp)
- [ ] Deep merge preserves unmodified settings
- [ ] Cache invalidated after update
- [ ] Non-owner roles get 403
- [ ] Suspended tenants get 403
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Reading settings (see T-06)
- Plan upgrades/downgrades (see T-04, billing domain)
- Custom domain or white-label configuration
- Email template customization

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
- [x] Audit trail for settings change

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidation)
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
