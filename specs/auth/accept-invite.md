# Accept Invite (A-10)

---

## Overview

**Feature:** Aceptacion de una invitacion para unirse a un tenant. El usuario invitado proporciona el token de invitacion, su contrasena, nombre, telefono, y licencia profesional (si es doctor). El sistema valida el token, crea el usuario en el schema del tenant, marca la invitacion como aceptada, y retorna tokens JWT para inicio de sesion inmediato.

**Domain:** auth

**Priority:** High

**Dependencies:** A-09 (invite-user.md), I-02 (authentication-rules.md), database-architecture.md (users, user_invites, user_sessions tables)

---

## Authentication

- **Level:** Public (autenticado via token de invitacion, no JWT)
- **Roles allowed:** N/A
- **Tenant context:** Not required — resuelto desde el token de invitacion
- **Special rules:** Token de un solo uso, valido por 7 dias.

---

## Endpoint

```
POST /api/v1/auth/accept-invite
```

**Rate Limiting:**
- 5 requests por 15 minutos por IP
- Redis sliding window: `dentalos:accept_invite_rate:{ip}`

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
  "token": "string (required) — token de invitacion recibido por email (UUID v4)",
  "password": "string (required) — contrasena, min 8, max 128, 1 mayuscula, 1 digito",
  "name": "string (required) — nombre completo, max 200 chars",
  "phone": "string (optional) — telefono, max 20 chars",
  "professional_license": "string (optional, required if role=doctor) — licencia profesional"
}
```

**Example Request:**
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "password": "MiContrasena2026!",
  "name": "Dr. Carlos Garcia",
  "phone": "+573009876543",
  "professional_license": "MP-54321"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
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
  }
}
```

**Example:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "usr_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "dr.garcia@email.com",
    "name": "Dr. Carlos Garcia",
    "role": "doctor",
    "avatar_url": null
  },
  "tenant": {
    "id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "name": "Clinica Dental Sonrisa",
    "plan": "professional",
    "country": "CO"
  }
}
```

**Set-Cookie header:**
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
  "details": { "password": ["Este campo es obligatorio."] }
}
```

#### 401 Unauthorized
**When:** Token de invitacion invalido, expirado, o ya utilizado.

```json
{
  "error": "invite_token_invalid",
  "message": "La invitacion es invalida o ha expirado. Solicite una nueva invitacion al propietario de la clinica."
}
```

#### 409 Conflict
**When:** El email ya esta registrado en el tenant (otro usuario lo creo mientras la invitacion estaba pendiente).

```json
{
  "error": "user_already_exists",
  "message": "Ya existe un usuario con este correo electronico en esta clinica."
}
```

#### 422 Unprocessable Entity
**When:** Contrasena debil o licencia profesional faltante para doctor.

```json
{
  "error": "weak_password",
  "message": "La contrasena no cumple los requisitos de seguridad.",
  "details": { "password": ["La contrasena debe tener al menos 8 caracteres."] }
}
```

```json
{
  "error": "professional_license_required",
  "message": "La licencia profesional es obligatoria para el rol de doctor."
}
```

#### 429 Too Many Requests
**When:** Excede rate limit.

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiados intentos. Intente nuevamente mas tarde.",
  "details": { "retry_after_seconds": 600 }
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (token, password, name requeridos).
2. Verificar rate limit por IP en Redis.
3. Calcular SHA-256 hash del token recibido.
4. Buscar invitacion en el tenant schema correspondiente. Para esto, se busca en todos los schemas: `SELECT * FROM {schema}.user_invites WHERE token_hash = ? AND status = 'pending'`. (Alternativa optimizada: tabla de lookup global o inclusion del tenant_id en la URL de invitacion).
5. Si no se encuentra, retornar 401 con `invite_token_invalid`.
6. Verificar que `expires_at > now()`. Si expirado, actualizar status a 'expired' y retornar 401.
7. Extraer datos de la invitacion: email, role, tenant schema.
8. Validar fortaleza de contrasena (min 8, max 128, 1 uppercase, 1 digit, no contener email, no comun).
9. Si el rol es `doctor`, verificar que `professional_license` esta presente. Si no, retornar 422.
10. Verificar que no existe usuario activo con ese email en el schema del tenant.
11. Si existe, retornar 409 con `user_already_exists`.
12. Re-verificar limite de plan (puede haber cambiado desde la invitacion):
    a. Contar usuarios activos en el tenant.
    b. Si excede `max_users` del plan, retornar 422 con `plan_limit_reached`.
13. Hashear contrasena con bcrypt (12 rounds).
14. Crear usuario en `{schema}.users` con: email (de la invitacion), password_hash, name, phone, role (de la invitacion), professional_license, is_active=true, email_verified=true (email verificado implicitamente al aceptar invitacion via email).
15. Marcar invitacion como aceptada: `UPDATE user_invites SET status='accepted', accepted_at=now() WHERE id = invite_id`.
16. Cargar datos del tenant desde `public.tenants`.
17. Generar access token JWT con claims del nuevo usuario.
18. Generar refresh token (UUID v4), hashear y almacenar en `user_sessions`.
19. Registrar evento en audit_log.
20. Encolar notificacion al clinic_owner informando que la invitacion fue aceptada.
21. Retornar 200 con tokens y datos de usuario/tenant.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| token | Requerido, formato UUID v4 | "Este campo es obligatorio." |
| password | Min 8, max 128, 1 uppercase, 1 digit | "La contrasena debe tener al menos 8 caracteres." |
| password | No contener email | "La contrasena no debe contener su correo electronico." |
| password | No estar en lista comun | "Esta contrasena es muy comun. Elija una mas segura." |
| name | Requerido, min 2, max 200 chars | "El nombre debe tener entre 2 y 200 caracteres." |
| phone | Regex E.164, max 20 chars (opcional) | "Formato de telefono invalido." |
| professional_license | Requerido si role=doctor, max 50 chars | "La licencia profesional es obligatoria para el rol de doctor." |

**Business Rules:**

- Token de invitacion es de un solo uso.
- El email del nuevo usuario proviene de la invitacion (no del request body) — no puede cambiarse.
- El rol del nuevo usuario proviene de la invitacion — no puede cambiarse.
- El email se considera verificado (el usuario accedio al enlace via su correo).
- La licencia profesional es obligatoria para doctores (regulacion LATAM).
- El limite del plan se re-verifica al momento de aceptar (proteccion contra race conditions).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Token valido pero plan ya lleno | 422 plan_limit_reached (aunque la invitacion existe) |
| Multiples clicks en el enlace de aceptacion | Primer click crea usuario, siguientes fallan con invite_token_invalid |
| Email de invitacion difiere del esperado | El email SIEMPRE proviene de la invitacion, no del input |
| Invitacion expirada pero token correcto | 401 con invite_token_invalid, status actualizado a 'expired' |
| Tenant cancelado despues de la invitacion | 401 con invite_token_invalid (tenant no activo) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: INSERT — nuevo usuario con datos de la invitacion
- `user_invites`: UPDATE — `status='accepted'`, `accepted_at=now()`
- `user_sessions`: INSERT — sesion con refresh token hash
- `audit_log`: INSERT — registro de aceptacion de invitacion

### Cache Operations

**Cache keys affected:**
- `dentalos:accept_invite_rate:{ip}`: INCR — rate limit
- `dentalos:tenant_info:{tenant_id}`: GET — lectura de cache

**Cache TTL:** Rate limit: 900s.

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | email.invite_accepted | { clinic_owner_email, new_user_name, new_user_role, tenant_name } | Al aceptar invitacion exitosamente |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** user (via invite acceptance)
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | invite_accepted | clinic_owner | Al aceptar invitacion |
| in-app | invite_accepted | clinic_owner | Al aceptar invitacion |

---

## Performance

### Expected Response Time
- **Target:** < 400ms
- **Maximum acceptable:** < 800ms (incluye bcrypt hashing)

### Caching Strategy
- **Strategy:** Redis para rate limiting + tenant info cache
- **Cache key:** `dentalos:tenant_info:{tenant_id}`
- **TTL:** 300s
- **Invalidation:** Al actualizar datos del tenant

### Database Performance

**Queries executed:** 5-6 (lookup invite, check user exists, count users, insert user, update invite, insert session)

**Indexes required:**
- `{schema}.user_invites.token_hash` — INDEX
- `{schema}.user_invites.status` — INDEX
- `{schema}.users.lower(email)` — UNIQUE

**N+1 prevention:** No aplica.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| token | Validar formato UUID, strip | Prevenir inyeccion |
| password | No sanitizar (se hashea) | Solo validar fortaleza |
| name | strip_tags, max length | Prevenir XSS |
| phone | Regex E.164 | Solo digitos y + |
| professional_license | strip, max length | Alfanumerico |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** Write-only logged

---

## Testing

### Test Cases

#### Happy Path
1. Aceptacion exitosa de invitacion de doctor
   - **Given:** Invitacion pendiente con role=doctor, token valido
   - **When:** POST /api/v1/auth/accept-invite con token, password, name, professional_license
   - **Then:** 200 OK, usuario creado con role=doctor, tokens retornados, invitacion marcada como accepted

2. Aceptacion exitosa de invitacion de receptionist
   - **Given:** Invitacion pendiente con role=receptionist
   - **When:** POST /api/v1/auth/accept-invite sin professional_license
   - **Then:** 200 OK, usuario creado con role=receptionist

3. Login exitoso despues de aceptar invitacion
   - **Given:** Invitacion aceptada
   - **When:** POST /api/v1/auth/login con email y password del nuevo usuario
   - **Then:** 200 OK, login exitoso

#### Edge Cases
1. Doctor sin licencia profesional
   - **Given:** Invitacion con role=doctor
   - **When:** POST /api/v1/auth/accept-invite sin professional_license
   - **Then:** 422 con "La licencia profesional es obligatoria para el rol de doctor."

2. Plan lleno al momento de aceptar
   - **Given:** Invitacion valida pero plan max_users alcanzado despues de invitar
   - **When:** POST /api/v1/auth/accept-invite
   - **Then:** 422 con plan_limit_reached

3. Doble click en enlace de invitacion
   - **Given:** Primer request exitoso, segundo con mismo token
   - **When:** Dos requests rapidos
   - **Then:** Primero 200 OK, segundo 401 invite_token_invalid

#### Error Cases
1. Token invalido
   - **Given:** Token UUID que no corresponde a ninguna invitacion
   - **When:** POST /api/v1/auth/accept-invite
   - **Then:** 401 con invite_token_invalid

2. Token expirado
   - **Given:** Invitacion con expires_at en el pasado
   - **When:** POST /api/v1/auth/accept-invite
   - **Then:** 401 con invite_token_invalid

3. Contrasena debil
   - **Given:** Token valido pero password="abc"
   - **When:** POST /api/v1/auth/accept-invite
   - **Then:** 422 con weak_password

4. Email ya registrado en tenant
   - **Given:** Otro usuario creo cuenta con ese email entre invitacion y aceptacion
   - **When:** POST /api/v1/auth/accept-invite
   - **Then:** 409 con user_already_exists

### Test Data Requirements

**Users:** Un clinic_owner en el tenant.

**Invites:** Una invitacion pendiente valida (role=doctor), una expirada.

**Plans:** Plan con espacio disponible, plan lleno.

### Mocking Strategy

- **Redis:** fakeredis para rate limiting
- **RabbitMQ:** Mock — verificar que notificacion al owner fue encolada
- **bcrypt:** No mockear

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Token valido crea usuario en el tenant con rol correcto
- [ ] Email y rol provienen de la invitacion (no del input)
- [ ] Contrasena validada con requisitos de seguridad
- [ ] Licencia profesional requerida para doctores
- [ ] Invitacion marcada como 'accepted'
- [ ] email_verified=true para el nuevo usuario
- [ ] Tokens JWT retornados para sesion inmediata
- [ ] Limite de plan re-verificado al aceptar
- [ ] Notificacion al clinic_owner encolada
- [ ] Token expirado o invalido retorna 401
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creacion de la invitacion (ver auth/invite-user.md)
- Consulta de informacion de invitacion antes de aceptar (GET /api/v1/auth/invite-info?token=...)
- Flujo de aceptacion de invitacion para pacientes del portal

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (Public, invite-token)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (auth domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Public, invite-token)
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for user creation

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized
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
