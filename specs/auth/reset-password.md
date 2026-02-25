# Reset Password (A-06)

---

## Overview

**Feature:** Restablecimiento de contrasena mediante token. El usuario recibe un enlace por email (generado en forgot-password), proporciona el token y una nueva contrasena. El sistema valida el token, actualiza el hash de la contrasena, revoca TODOS los refresh tokens del usuario (forzar re-login en todos los dispositivos), e invalida el token de reset.

**Domain:** auth

**Priority:** High

**Dependencies:** A-05 (forgot-password.md), I-02 (authentication-rules.md), database-architecture.md (users, user_sessions tables)

---

## Authentication

- **Level:** Public (autenticado via token de reset, no JWT)
- **Roles allowed:** N/A
- **Tenant context:** Not required — resuelto desde el token de reset almacenado en Redis
- **Special rules:** Token de un solo uso, valido por 1 hora.

---

## Endpoint

```
POST /api/v1/auth/reset-password
```

**Rate Limiting:**
- 5 requests por 15 minutos por IP
- Redis sliding window: `dentalos:reset_password_rate:{ip}`

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
  "token": "string (required) — token de restablecimiento recibido por email (UUID v4)",
  "new_password": "string (required) — nueva contrasena, min 8, max 128, 1 mayuscula, 1 digito"
}
```

**Example Request:**
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
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
  "message": "Contrasena actualizada exitosamente. Inicie sesion con su nueva contrasena."
}
```

### Error Responses

#### 400 Bad Request
**When:** Campos faltantes o formato invalido.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": { "token": ["Este campo es obligatorio."] }
}
```

#### 401 Unauthorized
**When:** Token invalido, expirado, o ya utilizado.

```json
{
  "error": "reset_token_invalid",
  "message": "El enlace de restablecimiento es invalido o ha expirado. Solicite uno nuevo."
}
```

#### 422 Unprocessable Entity
**When:** Nueva contrasena no cumple requisitos de seguridad.

```json
{
  "error": "weak_password",
  "message": "La contrasena no cumple los requisitos de seguridad.",
  "details": {
    "new_password": [
      "La contrasena debe tener al menos 8 caracteres.",
      "La contrasena debe contener al menos una letra mayuscula."
    ]
  }
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

1. Validar input contra schema Pydantic (token y new_password requeridos).
2. Verificar rate limit por IP en Redis.
3. Calcular SHA-256 hash del token recibido.
4. Buscar en Redis: `dentalos:password_reset:{token_hash}`.
5. Si no se encuentra, retornar 401 con `reset_token_invalid`.
6. Extraer metadata del token: `{user_id, tenant_id, email, created_at}`.
7. Validar fortaleza de la nueva contrasena (min 8, max 128, 1 uppercase, 1 digit, no contener email, no comun).
8. Resolver schema del tenant y buscar usuario en `{schema}.users` WHERE `id = user_id AND is_active = true`.
9. Si usuario no encontrado o inactivo, retornar 401 con `reset_token_invalid` (generico).
10. Hashear nueva contrasena con bcrypt (12 rounds).
11. Actualizar `users.password_hash` con el nuevo hash.
12. Resetear `users.failed_login_attempts = 0` y `users.locked_until = null`.
13. Revocar TODOS los refresh tokens del usuario: `UPDATE user_sessions SET is_revoked = true WHERE user_id = ? AND is_revoked = false`.
14. Establecer version de token en Redis: `SET dentalos:user_token_version:{user_id} {timestamp}` (invalida access tokens existentes).
15. Eliminar token de reset de Redis: `DEL dentalos:password_reset:{token_hash}`.
16. Eliminar referencia por email: `DEL dentalos:password_reset_email:{email_hash}`.
17. Registrar evento en audit_log del tenant.
18. Encolar notificacion por email confirmando el cambio de contrasena.
19. Retornar 200 OK.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| token | Requerido, formato UUID v4 | "Este campo es obligatorio." / "Formato de token invalido." |
| new_password | Min 8, max 128, 1 uppercase, 1 digit | "La contrasena debe tener al menos 8 caracteres." |
| new_password | No contener email del usuario | "La contrasena no debe contener su correo electronico." |
| new_password | No estar en lista comun | "Esta contrasena es muy comun. Elija una mas segura." |

**Business Rules:**

- Token de un solo uso — eliminado de Redis inmediatamente despues de uso exitoso.
- Al cambiar contrasena, se revocan TODAS las sesiones (refresh tokens) del usuario.
- Se establece user_token_version en Redis para invalidar access tokens existentes.
- El usuario debe iniciar sesion nuevamente en todos los dispositivos.
- El bloqueo de cuenta (locked_until) se resetea al completar el reset.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Token ya utilizado (no existe en Redis) | 401 con reset_token_invalid |
| Token expirado (TTL de Redis vencido) | 401 con reset_token_invalid (key no existe) |
| Nueva contrasena igual a la anterior | Permitido (no se compara con hash anterior) |
| Usuario desactivado entre solicitud y uso del token | 401 con reset_token_invalid |
| Token valido pero tenant cancelado | 401 con reset_token_invalid (generico) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: UPDATE — `password_hash`, `failed_login_attempts = 0`, `locked_until = null`, `updated_at`
- `user_sessions`: UPDATE — `is_revoked = true` para todas las sesiones activas del usuario
- `audit_log`: INSERT — registro de cambio de contrasena

### Cache Operations

**Cache keys affected:**
- `dentalos:password_reset:{token_hash}`: DELETE — consumir token
- `dentalos:password_reset_email:{email_hash}`: DELETE — limpiar referencia
- `dentalos:user_token_version:{user_id}`: SET — invalidar access tokens existentes
- `dentalos:reset_password_rate:{ip}`: INCR — rate limit

**Cache TTL:** Token version: sin TTL. Rate limit: 900s.

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | email.password_changed | { user_id, email, user_name, ip_address } | Despues de reset exitoso |

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** user (password_change via reset)
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | password_changed_confirmation | usuario | Al completar reset exitosamente |

---

## Performance

### Expected Response Time
- **Target:** < 350ms
- **Maximum acceptable:** < 800ms (incluye bcrypt hashing ~100-250ms)

### Caching Strategy
- **Strategy:** Redis para tokens de reset
- **Cache key:** `dentalos:password_reset:{token_hash}`
- **TTL:** 3600s (1 hora, establecido en forgot-password)
- **Invalidation:** Al usar el token exitosamente

### Database Performance

**Queries executed:** 3-4 (lookup usuario, update password, revoke sessions, insert audit)

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
| token | Validar formato UUID, strip | Prevenir inyeccion |
| new_password | No sanitizar (se hashea) | Solo validar fortaleza |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** Response es texto estatico.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** Write-only logged

---

## Testing

### Test Cases

#### Happy Path
1. Reset exitoso con token valido
   - **Given:** Token de reset valido en Redis para usuario activo
   - **When:** POST /api/v1/auth/reset-password con token y nueva contrasena valida
   - **Then:** 200 OK, password_hash actualizado, todas las sesiones revocadas, token eliminado de Redis

2. Login exitoso con nueva contrasena tras reset
   - **Given:** Reset completado exitosamente
   - **When:** POST /api/v1/auth/login con nueva contrasena
   - **Then:** 200 OK, login exitoso

#### Edge Cases
1. Cuenta bloqueada se desbloquea tras reset
   - **Given:** Usuario con locked_until en el futuro y token de reset valido
   - **When:** POST /api/v1/auth/reset-password
   - **Then:** 200 OK, locked_until reseteado a null, failed_login_attempts = 0

2. Reset con misma contrasena
   - **Given:** Nueva contrasena es igual a la actual
   - **When:** POST /api/v1/auth/reset-password
   - **Then:** 200 OK (permitido, no se compara con anterior)

#### Error Cases
1. Token ya utilizado
   - **Given:** Token que ya fue consumido (no existe en Redis)
   - **When:** POST /api/v1/auth/reset-password
   - **Then:** 401 con "El enlace de restablecimiento es invalido o ha expirado."

2. Token expirado
   - **Given:** Token cuyo TTL en Redis ha vencido
   - **When:** POST /api/v1/auth/reset-password
   - **Then:** 401 con reset_token_invalid

3. Contrasena debil
   - **Given:** Token valido pero new_password = "abc"
   - **When:** POST /api/v1/auth/reset-password
   - **Then:** 422 con detalles de validacion

4. Rate limit excedido
   - **Given:** 5 intentos en 15 min desde misma IP
   - **When:** POST /api/v1/auth/reset-password (6to intento)
   - **Then:** 429 Too Many Requests

### Test Data Requirements

**Users:** Un usuario activo con sesiones activas. Un usuario bloqueado.

**Redis:** Token de reset valido pre-insertado.

### Mocking Strategy

- **Redis:** fakeredis para tokens y rate limiting
- **RabbitMQ:** Mock — verificar que email de confirmacion fue encolado
- **bcrypt:** No mockear

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Token valido permite cambiar contrasena
- [ ] Token se consume (no reutilizable)
- [ ] Todas las sesiones del usuario se revocan
- [ ] Access tokens existentes se invalidan via user_token_version
- [ ] Bloqueo de cuenta se resetea
- [ ] Email de confirmacion encolado
- [ ] Token expirado o invalido retorna 401
- [ ] Contrasena debil retorna 422
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Generacion del token de reset (ver auth/forgot-password.md)
- Envio del email (ver integrations/email-engine.md)
- Reset de contrasena para pacientes del portal (separado)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (Public, token-based)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (auth domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Public, token-based)
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
