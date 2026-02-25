# Change Password (A-07)

---

## Overview

**Feature:** Cambio de contrasena para usuarios autenticados. Requiere la contrasena actual para verificar identidad y una nueva contrasena que cumpla los requisitos de seguridad. Al completar, revoca todas las demas sesiones del usuario (excepto la actual) y registra el evento en el audit log.

**Domain:** auth

**Priority:** High

**Dependencies:** I-02 (authentication-rules.md), database-architecture.md (users, user_sessions tables)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist (todos los roles de staff)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Requiere verificacion de contrasena actual (re-autenticacion implicita).

---

## Endpoint

```
POST /api/v1/auth/change-password
```

**Rate Limiting:**
- 5 requests por hora per user
- Redis sliding window: `dentalos:change_password_rate:{user_id}`

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT access token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Formato de request | application/json |

### URL Parameters

N/A

### Query Parameters

N/A

### Request Body Schema

```json
{
  "current_password": "string (required) — contrasena actual",
  "new_password": "string (required) — nueva contrasena, min 8, max 128, 1 mayuscula, 1 digito"
}
```

**Example Request:**
```json
{
  "current_password": "MiContrasenaActual1",
  "new_password": "NuevaSegura2026!"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "message": "string"
}
```

**Example:**
```json
{
  "message": "Contrasena actualizada exitosamente. Otras sesiones han sido cerradas."
}
```

**Set-Cookie header (nuevo refresh token para sesion actual):**
```
Set-Cookie: refresh_token=<new_uuid>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=2592000
```

### Error Responses

#### 400 Bad Request
**When:** Campos faltantes.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": { "current_password": ["Este campo es obligatorio."] }
}
```

#### 401 Unauthorized
**When:** Token de acceso invalido o expirado.

Standard auth failure — see infra/authentication-rules.md

#### 403 Forbidden
**When:** Contrasena actual incorrecta.

```json
{
  "error": "invalid_current_password",
  "message": "La contrasena actual es incorrecta."
}
```

#### 422 Unprocessable Entity
**When:** Nueva contrasena no cumple requisitos, o es igual a la actual.

```json
{
  "error": "weak_password",
  "message": "La contrasena no cumple los requisitos de seguridad.",
  "details": {
    "new_password": ["La contrasena debe tener al menos una letra mayuscula."]
  }
}
```

```json
{
  "error": "same_password",
  "message": "La nueva contrasena debe ser diferente a la actual."
}
```

#### 429 Too Many Requests
**When:** Excede 5 cambios por hora por usuario.

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiados intentos de cambio de contrasena. Intente nuevamente mas tarde.",
  "details": { "retry_after_seconds": 1800 }
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar access token JWT via dependency `get_current_user()`.
2. Validar input contra schema Pydantic (current_password y new_password requeridos).
3. Verificar rate limit por usuario en Redis (`dentalos:change_password_rate:{user_id}`).
4. Cargar usuario completo desde `{schema}.users` WHERE `id = user_id`.
5. Verificar contrasena actual con bcrypt `verify_password(current_password, user.password_hash)`.
6. Si contrasena actual incorrecta, retornar 403 con `invalid_current_password`.
7. Verificar que nueva contrasena != contrasena actual (comparar con bcrypt verify).
8. Si son iguales, retornar 422 con `same_password`.
9. Validar fortaleza de nueva contrasena (min 8, max 128, 1 uppercase, 1 digit, no contener email, no comun).
10. Hashear nueva contrasena con bcrypt (12 rounds).
11. Actualizar `users.password_hash` con el nuevo hash.
12. Identificar la sesion actual del usuario (via el refresh token de la cookie, si presente).
13. Revocar TODAS las sesiones del usuario EXCEPTO la actual: `UPDATE user_sessions SET is_revoked = true WHERE user_id = ? AND id != current_session_id AND is_revoked = false`.
14. Establecer user_token_version en Redis: `SET dentalos:user_token_version:{user_id} {timestamp}`.
15. Generar nuevo refresh token para la sesion actual, almacenar en `user_sessions`.
16. Registrar evento en `audit_log`.
17. Encolar notificacion por email confirmando el cambio.
18. Retornar 200 OK con nuevo refresh token en Set-Cookie.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| current_password | Requerido | "Este campo es obligatorio." |
| new_password | Min 8, max 128 chars | "La contrasena debe tener al menos 8 caracteres." / "La contrasena no debe exceder 128 caracteres." |
| new_password | Al menos 1 uppercase | "La contrasena debe contener al menos una letra mayuscula." |
| new_password | Al menos 1 digito | "La contrasena debe contener al menos un numero." |
| new_password | No contener email | "La contrasena no debe contener su correo electronico." |
| new_password | No estar en lista comun | "Esta contrasena es muy comun. Elija una mas segura." |
| new_password | Diferente a la actual | "La nueva contrasena debe ser diferente a la actual." |

**Business Rules:**

- La contrasena actual debe ser verificada antes de permitir el cambio.
- La nueva contrasena no puede ser igual a la actual.
- Todas las sesiones EXCEPTO la actual se revocan (el usuario no pierde su sesion activa).
- Access tokens emitidos antes del cambio se invalidan via user_token_version (excepto el actual, que el usuario ya tiene).
- El evento queda registrado en audit_log.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Usuario tiene una sola sesion (la actual) | No se revocan sesiones, solo se actualiza password |
| Request sin cookie de refresh token | Revocar TODAS las sesiones (no se puede identificar la actual) |
| Contrasena actual correcta pero nueva igual | 422 con same_password |
| Cambio inmediatamente despues de otro cambio | Permitido si dentro del rate limit |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: UPDATE — `password_hash`, `updated_at`
- `user_sessions`: UPDATE — `is_revoked = true` para otras sesiones
- `user_sessions`: INSERT — nueva sesion (nuevo refresh token para sesion actual)
- `audit_log`: INSERT — registro de cambio de contrasena

### Cache Operations

**Cache keys affected:**
- `dentalos:user_token_version:{user_id}`: SET — invalidar access tokens previos
- `dentalos:change_password_rate:{user_id}`: INCR — rate limit

**Cache TTL:** Token version: sin TTL. Rate limit: 3600s.

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | email.password_changed | { user_id, email, user_name, ip_address, timestamp } | Despues del cambio exitoso |

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** user (password_change)
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | password_changed_confirmation | usuario | Al completar cambio exitosamente |

---

## Performance

### Expected Response Time
- **Target:** < 400ms
- **Maximum acceptable:** < 900ms (incluye 2x bcrypt: verify + hash)

### Caching Strategy
- **Strategy:** Redis para rate limiting y token version
- **Cache key:** `dentalos:change_password_rate:{user_id}`
- **TTL:** 3600s
- **Invalidation:** N/A (expira por TTL)

### Database Performance

**Queries executed:** 4-5 (load user, update password, revoke sessions, insert new session, insert audit)

**Indexes required:**
- `{schema}.users.id` — PRIMARY KEY
- `{schema}.user_sessions.user_id` — INDEX

**N+1 prevention:** No aplica.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| current_password | No sanitizar | Se compara contra hash |
| new_password | No sanitizar (se hashea) | Solo validar fortaleza |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** Response es texto estatico.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** All access logged (security event)

---

## Testing

### Test Cases

#### Happy Path
1. Cambio de contrasena exitoso
   - **Given:** Usuario autenticado con contrasena "Actual1234"
   - **When:** POST /api/v1/auth/change-password con current_password correcto y nueva contrasena valida
   - **Then:** 200 OK, password_hash actualizado, otras sesiones revocadas, nuevo refresh token en cookie

2. Sesiones de otros dispositivos revocadas
   - **Given:** Usuario con 3 sesiones activas
   - **When:** Cambio de contrasena desde sesion 1
   - **Then:** Sesiones 2 y 3 revocadas, sesion 1 mantiene nuevo refresh token

#### Edge Cases
1. Usuario con una sola sesion
   - **Given:** Usuario con solo la sesion actual
   - **When:** POST /api/v1/auth/change-password
   - **Then:** 200 OK, ninguna sesion revocada (solo la actual, que se renueva)

2. Request sin cookie de refresh token
   - **Given:** Access token valido pero sin cookie
   - **When:** POST /api/v1/auth/change-password
   - **Then:** 200 OK, TODAS las sesiones revocadas, usuario debe re-login

#### Error Cases
1. Contrasena actual incorrecta
   - **Given:** current_password no coincide con hash almacenado
   - **When:** POST /api/v1/auth/change-password
   - **Then:** 403 con "La contrasena actual es incorrecta."

2. Nueva contrasena igual a la actual
   - **Given:** new_password == current_password
   - **When:** POST /api/v1/auth/change-password
   - **Then:** 422 con "La nueva contrasena debe ser diferente a la actual."

3. Nueva contrasena debil
   - **Given:** new_password = "abc"
   - **When:** POST /api/v1/auth/change-password
   - **Then:** 422 con detalles de validacion

4. Rate limit excedido
   - **Given:** 5 cambios en la ultima hora
   - **When:** POST /api/v1/auth/change-password (6to intento)
   - **Then:** 429 Too Many Requests

### Test Data Requirements

**Users:** Un usuario activo con multiples sesiones.

**Sessions:** 3 sesiones activas para el mismo usuario.

### Mocking Strategy

- **Redis:** fakeredis para rate limiting y token version
- **RabbitMQ:** Mock — verificar que email de confirmacion fue encolado
- **bcrypt:** No mockear

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Contrasena actual verificada antes de permitir cambio
- [ ] Nueva contrasena no puede ser igual a la actual
- [ ] Validacion de fortaleza con mensajes en espanol
- [ ] Otras sesiones revocadas tras cambio exitoso
- [ ] Sesion actual mantenida con nuevo refresh token
- [ ] Access tokens previos invalidados via user_token_version
- [ ] Audit log registra el evento
- [ ] Email de confirmacion encolado
- [ ] Rate limit por usuario funciona
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Reset de contrasena (sin conocer la actual) — ver auth/reset-password.md
- Cambio de contrasena para pacientes del portal
- Historial de contrasenas (prevenir reutilizacion) — post-MVP
- Politica de expiracion de contrasena — post-MVP

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (Authenticated)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (auth domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Authenticated)
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for password change

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
