# Me — Perfil del Usuario Actual (A-04)

---

## Overview

**Feature:** Obtiene el perfil completo del usuario autenticado incluyendo datos personales, rol, permisos, contexto del tenant (nombre, plan, pais, modo de odontograma), y feature flags activos. Este endpoint es llamado por el frontend al inicializar la aplicacion y tras cada refresh de token.

**Domain:** auth

**Priority:** Critical

**Dependencies:** I-02 (authentication-rules.md), database-architecture.md (users table, public.tenants, public.plans)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist (todos los roles de staff)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** None

---

## Endpoint

```
GET /api/v1/auth/me
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT access token | Bearer eyJhbGc... |

### URL Parameters

N/A

### Query Parameters

N/A

### Request Body Schema

N/A — GET request sin body.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "user": {
    "id": "UUID",
    "email": "string",
    "name": "string",
    "phone": "string | null",
    "avatar_url": "string | null",
    "role": "string",
    "professional_license": "string | null",
    "specialties": ["string"],
    "email_verified": "boolean",
    "created_at": "ISO 8601 datetime"
  },
  "permissions": ["string"],
  "tenant": {
    "id": "UUID",
    "name": "string",
    "slug": "string",
    "plan": "string",
    "country": "string",
    "timezone": "string",
    "locale": "string",
    "logo_url": "string | null",
    "settings": {
      "odontogram_mode": "string",
      "default_appointment_duration_min": "number",
      "cancellation_policy_hours": "number",
      "reminder_channels": ["string"]
    }
  },
  "plan_limits": {
    "max_patients": "number",
    "max_doctors": "number",
    "max_users": "number",
    "max_storage_mb": "number"
  },
  "feature_flags": {
    "appointments": "boolean",
    "billing": "boolean",
    "patient_portal": "boolean",
    "treatment_plans": "boolean",
    "prescriptions": "boolean",
    "analytics_advanced": "boolean",
    "whatsapp_reminders": "boolean",
    "electronic_invoice": "boolean"
  },
  "current_tenant": {
    "tenant_id": "UUID",
    "tenant_name": "string",
    "clinic_name": "string",
    "role": "string",
    "is_primary": "boolean",
    "logo_url": "string | null"
  },
  "tenants": [
    {
      "tenant_id": "UUID",
      "tenant_name": "string",
      "clinic_name": "string",
      "role": "string",
      "is_primary": "boolean",
      "logo_url": "string | null"
    }
  ],
  "can_switch_tenant": "boolean"
}
```

**Example:**
```json
{
  "user": {
    "id": "usr_550e8400-e29b-41d4-a716-446655440000",
    "email": "dra.martinez@clinicasonrisa.co",
    "name": "Dra. Ana Martinez",
    "phone": "+573001234567",
    "avatar_url": null,
    "role": "clinic_owner",
    "professional_license": "MP-12345",
    "specialties": ["ortodoncia", "endodoncia"],
    "email_verified": true,
    "created_at": "2026-02-20T10:00:00Z"
  },
  "permissions": [
    "patients:read", "patients:write", "patients:update", "patients:delete",
    "odontogram:read", "odontogram:write",
    "team:read", "team:write", "team:update", "team:delete",
    "settings:read", "settings:manage"
  ],
  "tenant": {
    "id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "name": "Clinica Dental Sonrisa",
    "slug": "clinica-dental-sonrisa",
    "plan": "professional",
    "country": "CO",
    "timezone": "America/Bogota",
    "locale": "es",
    "logo_url": "https://storage.dentalos.com/logos/tn_7c9e.png",
    "settings": {
      "odontogram_mode": "classic",
      "default_appointment_duration_min": 30,
      "cancellation_policy_hours": 24,
      "reminder_channels": ["whatsapp", "email"]
    }
  },
  "plan_limits": {
    "max_patients": 500,
    "max_doctors": 5,
    "max_users": 10,
    "max_storage_mb": 5120
  },
  "feature_flags": {
    "appointments": true,
    "billing": true,
    "patient_portal": false,
    "treatment_plans": true,
    "prescriptions": true,
    "analytics_advanced": false,
    "whatsapp_reminders": false,
    "electronic_invoice": false
  },
  "current_tenant": {
    "tenant_id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "tenant_name": "Clinica Dental Sonrisa",
    "clinic_name": "Clinica Dental Sonrisa",
    "role": "clinic_owner",
    "is_primary": true,
    "logo_url": "https://storage.dentalos.com/logos/tn_7c9e.png"
  },
  "tenants": [
    {
      "tenant_id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "tenant_name": "Clinica Dental Sonrisa",
      "clinic_name": "Clinica Dental Sonrisa",
      "role": "clinic_owner",
      "is_primary": true,
      "logo_url": "https://storage.dentalos.com/logos/tn_7c9e.png"
    },
    {
      "tenant_id": "tn_3f8a1234-ab12-4321-bcde-123456789abc",
      "tenant_name": "OdontoPlus Chapinero",
      "clinic_name": "OdontoPlus Chapinero",
      "role": "doctor",
      "is_primary": false,
      "logo_url": null
    }
  ],
  "can_switch_tenant": true
}
```

### Error Responses

#### 401 Unauthorized
**When:** Standard auth failure — see infra/authentication-rules.md

```json
{
  "error": "token_expired",
  "message": "El token de acceso ha expirado. Use el refresh token para obtener uno nuevo."
}
```

```json
{
  "error": "token_invalid",
  "message": "El token de acceso es invalido."
}
```

#### 403 Forbidden
**When:** Tenant cancelado.

```json
{
  "error": "tenant_cancelled",
  "message": "La cuenta de esta clinica ha sido cancelada."
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar access token JWT via dependency `get_current_user()`.
2. Extraer user_id y tenant_id del JWT claims.
3. Consultar datos completos del usuario desde `{schema}.users` WHERE `id = user_id`.
4. Consultar datos del tenant desde cache Redis (`dentalos:tenant_info:{tenant_id}`) con fallback a `public.tenants JOIN public.plans`.
5. Computar permisos del usuario basado en su rol (desde constante ROLE_PERMISSIONS).
6. Extraer feature flags del campo `plans.features` JSONB.
7. Extraer settings del tenant del campo `tenants.settings` JSONB.
8. Consultar `public.user_tenant_memberships` para obtener todas las membresias activas del usuario (WHERE `user_id = user.id` AND `status = 'active'`). Incluir `tenant_name`, `clinic_name`, `role`, `is_primary`, `logo_url` para cada entrada.
9. Construir `current_tenant` a partir del `tenant_id` del JWT (el tenant activo en esta sesion).
10. Calcular `can_switch_tenant = len(active_memberships) >= 2`.
11. Construir respuesta completa y retornar 200.

**Validation Rules:**

N/A — endpoint de lectura, sin input del usuario.

**Business Rules:**

- Los permisos retornados son los mismos del JWT, computados desde ROLE_PERMISSIONS.
- Los feature flags provienen del plan del tenant, no del JWT.
- Los datos de settings del tenant incluyen configuraciones visibles para el frontend (odontogram_mode, duracion de citas, etc.).
- El campo `plan_limits` permite al frontend mostrar barras de uso y alertas de limite.
- `current_tenant` refleja el tenant del JWT activo (la clinica en la que el usuario esta trabajando en esta sesion).
- `tenants` contiene TODAS las membresias activas del usuario, independientemente del tenant actual. Permite al frontend mostrar un selector de clinica.
- `can_switch_tenant` es `true` si el usuario tiene 2 o mas membresias activas. El frontend usa este campo para mostrar/ocultar el boton de cambio de clinica.
- Las preferencias personales del doctor (templates, configuracion de voz) viven en su perfil de usuario en `public.users` y estan disponibles independientemente del tenant activo.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Usuario existe en JWT pero fue desactivado en DB | Retornar datos actuales (JWT aun valido por su TTL) |
| Tenant settings JSONB incompleto | Retornar valores por defecto para campos faltantes |
| Plan del tenant fue actualizado entre emision de JWT y request a /me | Retornar datos frescos del plan (consultados en tiempo real) |
| Usuario con 1 sola membresia activa | `tenants` contiene 1 elemento, `can_switch_tenant = false` |
| Usuario con 5 clinicas activas | `tenants` contiene 5 elementos, `can_switch_tenant = true` |
| Membresia suspendida en una clinica mientras trabaja en otra | La clinica suspendida NO aparece en `tenants` (solo se retornan membresias activas) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: READ — lectura de datos del usuario

### Cache Operations

**Cache keys affected:**
- `dentalos:tenant_info:{tenant_id}`: GET — lectura de cache de tenant
- `dentalos:user_profile:{user_id}`: GET/SET — cache de perfil de usuario (opcional)

**Cache TTL:** Tenant info: 300s. User profile: 60s.

### Queue Jobs (RabbitMQ)

N/A — endpoint de lectura pura.

### Audit Log

**Audit entry:** No — lectura de datos propios no requiere audit.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms (con cache hit)
- **Maximum acceptable:** < 200ms (con cache miss)

### Caching Strategy
- **Strategy:** Redis cache para tenant info y perfil de usuario
- **Cache key:** `dentalos:tenant_info:{tenant_id}`, `dentalos:user_profile:{tenant_id}:{user_id}`
- **TTL:** Tenant: 300s. User profile: 60s.
- **Invalidation:** Al actualizar perfil de usuario o configuracion del tenant.

### Database Performance

**Queries executed:** 2-3 (usuario + tenant/plan si cache miss + membresias de tenant)

**Indexes required:**
- `{schema}.users.id` — PRIMARY KEY
- `public.tenants.id` — PRIMARY KEY
- `public.plans.id` — PRIMARY KEY
- `public.user_tenant_memberships.user_id` — INDEX (para lookup de membresias del usuario)

**N+1 prevention:** Single query con JOIN tenant + plan si cache miss. Membresias obtenidas en una sola query con JOIN a `public.tenants` para obtener `tenant_name`, `clinic_name`, `logo_url`.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

N/A — no acepta input del usuario mas alla del JWT.

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None (datos propios del usuario, no datos clinicos)

**Audit requirement:** Not required

---

## Testing

### Test Cases

#### Happy Path
1. Obtener perfil de clinic_owner
   - **Given:** Usuario autenticado con rol clinic_owner
   - **When:** GET /api/v1/auth/me
   - **Then:** 200 OK con todos los campos: user, permissions, tenant, plan_limits, feature_flags

2. Obtener perfil de doctor
   - **Given:** Usuario autenticado con rol doctor
   - **When:** GET /api/v1/auth/me
   - **Then:** 200 OK, permissions contiene solo permisos de doctor, professional_license presente

3. Datos de plan actualizados en tiempo real
   - **Given:** Plan del tenant cambio de "free" a "professional" (cache expirado)
   - **When:** GET /api/v1/auth/me
   - **Then:** plan_limits y feature_flags reflejan el plan "professional"

#### Edge Cases
1. Tenant sin logo
   - **Given:** Tenant con logo_url = null
   - **When:** GET /api/v1/auth/me
   - **Then:** logo_url es null en la respuesta

2. Settings JSONB parcialmente definido
   - **Given:** Tenant con settings que no incluye todos los campos esperados
   - **When:** GET /api/v1/auth/me
   - **Then:** Campos faltantes usan valores por defecto

#### Error Cases
1. Token expirado
   - **Given:** Access token con exp en el pasado
   - **When:** GET /api/v1/auth/me
   - **Then:** 401 con error "token_expired"

2. Token invalido
   - **Given:** Token con firma incorrecta
   - **When:** GET /api/v1/auth/me
   - **Then:** 401 con error "token_invalid"

3. Token revocado (post-logout)
   - **Given:** JTI del token en blacklist de Redis
   - **When:** GET /api/v1/auth/me
   - **Then:** 401 con error "token_revoked"

### Test Data Requirements

**Users:** Un usuario por cada rol (clinic_owner, doctor, assistant, receptionist).

**Tenants:** Un tenant activo con plan free, uno con plan professional.

### Mocking Strategy

- **Redis:** fakeredis para cache en unit tests
- **JWT:** Generar tokens de prueba con clave RSA de test

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/auth/me retorna perfil completo del usuario autenticado
- [ ] Permisos corresponden al rol del usuario
- [ ] Feature flags corresponden al plan del tenant
- [ ] Settings del tenant incluyen odontogram_mode
- [ ] Plan limits correctamente mapeados
- [ ] Cache hit responde en < 50ms
- [ ] Token expirado retorna 401
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Actualizacion del perfil (ver users/update-profile.md)
- Cambio de avatar (ver users/upload-avatar.md)
- Perfil del paciente en portal (portal/me.md)
- Datos de uso actual (cuantos pacientes/doctores hay) — ver analytics/

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (JWT only)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (N/A for GET)
- [x] Error cases enumerated
- [x] Auth requirements explicit (Authenticated)
- [x] Side effects listed (read-only)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (auth domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Authenticated)
- [x] Input sanitization defined (N/A)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail (not required for own profile read)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (N/A)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

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
| 1.1 | 2026-02-24 | Added multi-clinic support: `tenants` array (all active memberships), `current_tenant` object (active JWT tenant), `can_switch_tenant` boolean |
