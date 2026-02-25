# Login (A-02)

---

## Overview

**Feature:** Autenticacion de usuarios con email y contrasena. Resuelve el tenant del usuario, verifica credenciales, aplica rate limiting por IP y bloqueo de cuenta por intentos fallidos, y retorna access token JWT + refresh token.

**Domain:** auth

**Priority:** Critical

**Dependencies:** I-02 (authentication-rules.md), database-architecture.md (users, user_sessions tables)

---

## Authentication

- **Level:** Public
- **Roles allowed:** N/A (endpoint publico)
- **Tenant context:** Not required — se resuelve internamente a partir del email del usuario
- **Special rules:** Rate limit estricto por IP (5/15min). Bloqueo de cuenta tras 5 intentos fallidos por 15 min. Mensajes de error genericos para prevenir enumeracion de usuarios.

---

## Endpoint

```
POST /api/v1/auth/login
```

**Rate Limiting:**
- 5 requests por 15 minutos por IP
- Redis sliding window: `dentalos:login_rate:{ip}` (TTL 900s)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Content-Type | Yes | string | Formato de request | application/json |

### URL Parameters

N/A

### Query Parameters

N/A

### Request Body Schema

```json
{
  "email": "string (required) — correo del usuario",
  "password": "string (required) — contrasena"
}
```

**Example Request:**
```json
{
  "email": "dra.martinez@clinicasonrisa.co",
  "password": "Segura2026!"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema (single tenant — auto-selected):**
```json
{
  "access_token": "string — JWT RS256",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "UUID",
    "email": "string",
    "name": "string",
    "role": "string",
    "avatar_url": "string | null"
  },
  "tenant": {
    "id": "UUID",
    "name": "string",
    "plan": "string",
    "country": "string"
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
  ]
}
```

**Schema (multiple tenants — selection required):**
```json
{
  "requires_tenant_selection": true,
  "user": {
    "id": "UUID",
    "email": "string",
    "name": "string",
    "avatar_url": "string | null"
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
  ]
}
```

When `requires_tenant_selection: true` is returned, no `access_token` is issued. The client must call `POST /api/v1/auth/select-tenant` with the chosen `tenant_id` to obtain the final tenant-scoped JWT pair.

**Example (single tenant):**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "usr_550e8400-e29b-41d4-a716-446655440000",
    "email": "dra.martinez@clinicasonrisa.co",
    "name": "Dra. Ana Martinez",
    "role": "clinic_owner",
    "avatar_url": null
  },
  "tenant": {
    "id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "name": "Clinica Dental Sonrisa",
    "plan": "professional",
    "country": "CO"
  },
  "tenants": [
    {
      "tenant_id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "tenant_name": "Clinica Dental Sonrisa",
      "clinic_name": "Clinica Dental Sonrisa",
      "role": "clinic_owner",
      "is_primary": true,
      "logo_url": "https://storage.dentalos.com/logos/tn_7c9e.png"
    }
  ]
}
```

**Example (multiple tenants):**
```json
{
  "requires_tenant_selection": true,
  "user": {
    "id": "usr_550e8400-e29b-41d4-a716-446655440000",
    "email": "dr.ramirez@gmail.com",
    "name": "Dr. Carlos Ramirez",
    "avatar_url": null
  },
  "tenants": [
    {
      "tenant_id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "tenant_name": "Clinica Dental Sonrisa",
      "clinic_name": "Clinica Dental Sonrisa",
      "role": "doctor",
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
    },
    {
      "tenant_id": "tn_9b2c5678-cd34-5678-efgh-234567890bcd",
      "tenant_name": "Centro Oral Norte",
      "clinic_name": "Centro Oral Norte",
      "role": "doctor",
      "is_primary": false,
      "logo_url": "https://storage.dentalos.com/logos/tn_9b2c.png"
    }
  ]
}
```

**Set-Cookie header (only issued when a tenant-scoped JWT is returned):**
```
Set-Cookie: refresh_token=<uuid>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=2592000
```

### Error Responses

#### 400 Bad Request
**When:** Campos faltantes o formato invalido.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": { "email": ["Este campo es obligatorio."] }
}
```

#### 401 Unauthorized
**When:** Email no existe o contrasena incorrecta. **Siempre el mismo mensaje** para prevenir enumeracion.

```json
{
  "error": "invalid_credentials",
  "message": "Correo electronico o contrasena incorrectos."
}
```

#### 403 Forbidden
**When:** Tenant suspendido o cancelado.

```json
{
  "error": "tenant_cancelled",
  "message": "La cuenta de esta clinica ha sido cancelada."
}
```

```json
{
  "error": "tenant_suspended",
  "message": "La cuenta de esta clinica esta suspendida. Solo se permiten operaciones de lectura."
}
```

**When:** Usuario sin ninguna membresia activa en ningun tenant.

```json
{
  "error": "no_active_clinics",
  "message": "No tienes acceso activo a ninguna clinica. Contacta al administrador de tu clinica."
}
```

#### 423 Locked
**When:** Cuenta bloqueada por intentos fallidos.

```json
{
  "error": "account_locked",
  "message": "La cuenta esta temporalmente bloqueada por demasiados intentos fallidos.",
  "details": { "retry_after_seconds": 900 }
}
```

#### 429 Too Many Requests
**When:** Excede 5 intentos en 15 min por IP.

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiados intentos de inicio de sesion. Intente nuevamente mas tarde.",
  "details": { "retry_after_seconds": 450 }
}
```

#### 503 Service Unavailable
**When:** Tenant en estado `provisioning`.

```json
{
  "error": "tenant_provisioning",
  "message": "Su clinica esta siendo configurada. Intente nuevamente en unos momentos."
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (email, password requeridos).
2. Normalizar email a lowercase, strip whitespace.
3. Verificar rate limit por IP en Redis (`dentalos:login_rate:{ip}`). Si excede 5 en 15min, retornar 429.
4. Buscar usuario por email en `public.users` via tabla de lookup `public.user_email_lookup` (email -> user_id). Si no encontrado: retornar 401 con `invalid_credentials`. **No revelar que el email no existe.**
5. Verificar estado de bloqueo de cuenta: si `locked_until > now()`, retornar 423.
6. Verificar contrasena con bcrypt `verify_password(password, user.password_hash)`.
7. Si contrasena incorrecta: incrementar `failed_login_attempts`, si alcanza 5: establecer `locked_until = now() + 15min`. Retornar 401.
8. Consultar `public.user_tenant_memberships` para obtener todos los tenants activos del usuario (WHERE `user_id = user.id` AND `status = 'active'`).
9. Si 0 membresias activas: retornar 403 con `no_active_clinics`.
10. Verificar estado de cada tenant retornado: excluir los tenants con status `cancelled`. Si el unico tenant esta `cancelled`, retornar 403. Si esta en `provisioning`, retornar 503.
11. Resetear `failed_login_attempts = 0` y `locked_until = null`.
12. Actualizar `last_login_at = now()`.
13. **Si solo 1 membresia activa:** Proceder como flujo normal — generar JWT con `tenant_id`, retornar tokens + datos del usuario/tenant + lista `tenants`.
14. **Si 2+ membresias activas:** Retornar `requires_tenant_selection: true` + lista de tenants. **No emitir JWT todavia.** El cliente debe llamar `POST /api/v1/auth/select-tenant` con el `tenant_id` elegido.
15. En caso de JWT emitido (paso 13): verificar limite de sesiones concurrentes (max 5), revocar la sesion mas antigua si se excede. Generar refresh token (UUID v4), hashear con SHA-256, almacenar en `public.refresh_tokens`.
16. Registrar evento `auth.login.success` en log estructurado.
17. Retornar 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| email | Requerido, formato email valido | "Este campo es obligatorio." / "Formato de correo electronico invalido." |
| password | Requerido, min 1 char | "Este campo es obligatorio." |

**Business Rules:**

- Mensajes de error de autenticacion SIEMPRE genericos (no revelar si email existe o si es la contrasena).
- Un usuario puede pertenecer a multiples tenants. La tabla `public.user_tenant_memberships` es la fuente de verdad para las membresias activas.
- Usuarios inactivos (`is_active=false`) no pueden iniciar sesion — tratados igual que no encontrados.
- Login permitido en tenants suspendidos (solo lectura se controla en otros endpoints).
- Login bloqueado en tenants cancelados.
- Solo se muestran al usuario las membresias con `status = 'active'`. Membresias suspendidas en un tenant no bloquean el acceso a otros tenants activos del mismo usuario.
- Cuando hay multiples tenants, NO se emite JWT hasta que el usuario seleccione un tenant via `POST /api/v1/auth/select-tenant`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Email existe pero usuario is_active=false | Retornar 401 generic (no revelar estado) |
| Cuenta bloqueada pero lockout ya expiro | Permitir login, resetear contador |
| Usuario con email_verified=false | Permitir login (verificacion no bloquea acceso en MVP) |
| 6ta sesion concurrente | Revocar sesion mas antigua, crear nueva |
| Tenant en status provisioning | Retornar 503 |
| Usuario con 0 membresias activas (todas suspendidas o removidas) | Retornar 403 con `no_active_clinics` |
| Usuario con membresia suspendida en una clinica pero activa en otra | Mostrar solo las clinicas con membresia activa; la clinica suspendida no aparece en la lista |
| Usuario con 1 sola membresia activa | Auto-seleccionar ese tenant, retornar JWT normal (sin `requires_tenant_selection`) |
| Usuario con 5 clinicas activas | Retornar `requires_tenant_selection: true` con lista de las 5 clinicas |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: UPDATE — `last_login_at`, `failed_login_attempts`, `locked_until`
- `user_sessions`: INSERT — nueva sesion con refresh token hash

### Cache Operations

**Cache keys affected:**
- `dentalos:login_rate:{ip}`: INCR — contador de intentos por IP
- `dentalos:tenant_info:{tenant_id}`: GET — lectura de cache de tenant

**Cache TTL:** Login rate: 900s. Tenant info: 300s.

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| analytics | auth.login | { user_id, tenant_id, ip, user_agent, timestamp } | En login exitoso |

### Audit Log

**Audit entry:** Yes

- **Action:** login
- **Resource:** user
- **PHI involved:** No

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 800ms (incluye bcrypt verification ~100-250ms)

### Caching Strategy
- **Strategy:** Redis cache para tenant info + rate limiting
- **Cache key:** `dentalos:tenant_info:{tenant_id}`
- **TTL:** 300s
- **Invalidation:** Al actualizar datos del tenant

### Database Performance

**Queries executed:** 3-4 (lookup usuario, verificar tenant, update login info, insert sesion)

**Indexes required:**
- `{schema}.users.lower(email)` — UNIQUE
- `{schema}.users.is_active` — INDEX
- `{schema}.user_sessions.user_id` — INDEX

**N+1 prevention:** Busqueda de usuario optimizada via lookup table o query directa al schema correcto.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| email | Pydantic EmailStr, lowercase, strip | Prevenir inyeccion |
| password | No sanitizar | Se compara contra hash |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** All access logged (login events)

---

## Testing

### Test Cases

#### Happy Path
1. Login exitoso con credenciales validas
   - **Given:** Usuario activo "test@clinica.co" con password "Test1234"
   - **When:** POST /api/v1/auth/login con credenciales correctas
   - **Then:** 200 OK, access_token en body, refresh_token en Set-Cookie

2. Login exitoso resetea contador de intentos fallidos
   - **Given:** Usuario con failed_login_attempts=3
   - **When:** Login con credenciales correctas
   - **Then:** failed_login_attempts se resetea a 0

#### Edge Cases
1. Login con cuenta previamente bloqueada cuyo lockout ya expiro
   - **Given:** Usuario con locked_until en el pasado
   - **When:** POST /api/v1/auth/login con credenciales correctas
   - **Then:** 200 OK, locked_until se resetea a null

2. Sexta sesion concurrente
   - **Given:** Usuario con 5 sesiones activas
   - **When:** POST /api/v1/auth/login (6to dispositivo)
   - **Then:** 200 OK, sesion mas antigua revocada

3. Login en tenant suspendido
   - **Given:** Tenant con status='suspended'
   - **When:** POST /api/v1/auth/login
   - **Then:** 200 OK (login permitido, restricciones en otros endpoints)

#### Error Cases
1. Email no registrado
   - **Given:** Email "noexiste@test.co" no existe en ningun tenant
   - **When:** POST /api/v1/auth/login
   - **Then:** 401 con "Correo electronico o contrasena incorrectos."

2. Contrasena incorrecta
   - **Given:** Email existe, contrasena incorrecta
   - **When:** POST /api/v1/auth/login
   - **Then:** 401, failed_login_attempts incrementado

3. Cuenta bloqueada
   - **Given:** Usuario con locked_until en el futuro
   - **When:** POST /api/v1/auth/login
   - **Then:** 423 con retry_after_seconds

4. Rate limit IP excedido
   - **Given:** 5 intentos previos desde misma IP en 15 min
   - **When:** POST /api/v1/auth/login (6to intento)
   - **Then:** 429 Too Many Requests

5. Tenant cancelado
   - **Given:** Tenant con status='cancelled'
   - **When:** POST /api/v1/auth/login
   - **Then:** 403 con "La cuenta de esta clinica ha sido cancelada."

### Test Data Requirements

**Users:** Un usuario activo por rol (clinic_owner, doctor, assistant, receptionist). Un usuario inactivo. Un usuario bloqueado.

**Tenants:** Un tenant activo, uno suspendido, uno cancelado, uno en provisioning.

### Mocking Strategy

- **Redis:** fakeredis para rate limiting en unit tests
- **bcrypt:** No mockear (usar hashes reales, passwords simples en tests)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Login exitoso retorna access_token en body y refresh_token en cookie HttpOnly
- [ ] Credenciales incorrectas siempre retornan el mismo mensaje generico
- [ ] Rate limit de 5/15min/IP funciona correctamente
- [ ] Bloqueo de cuenta tras 5 intentos fallidos por 15 minutos
- [ ] Login exitoso resetea contador de intentos fallidos
- [ ] Tenant suspendido permite login
- [ ] Tenant cancelado bloquea login
- [ ] Maximo 5 sesiones concurrentes (la mas antigua se revoca)
- [ ] Audit log registra todos los intentos de login
- [ ] All test cases pass
- [ ] Performance targets met (< 800ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Login de pacientes (portal separado: portal/auth/login.md)
- Login de superadmin (admin/superadmin-login.md)
- Login via OAuth/SSO (post-MVP)
- Multi-factor authentication (post-MVP)
- Seleccion de tenant post-login via UI avanzada (cubierto por `auth/select-tenant.md` y `auth/switch-tenant.md`)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (Public with rate limit)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (auth domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Public)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for login events

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

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
| 1.1 | 2026-02-24 | Added multi-clinic doctor login flow: tenant membership query, conditional JWT issuance, `requires_tenant_selection` response, `tenants` array, edge cases for 0/1/N memberships |
