# Verify Email (A-11)

---

## Overview

**Feature:** Verificacion de correo electronico mediante token. Cuando un usuario se registra (A-01), recibe un email con un enlace de verificacion que contiene un token de un solo uso valido por 24 horas. Al hacer POST con el token, se actualiza `email_verified=true` en el registro del usuario.

**Domain:** auth

**Priority:** Medium

**Dependencies:** A-01 (register.md), I-02 (authentication-rules.md), database-architecture.md (users table)

---

## Authentication

- **Level:** Public (autenticado via token de verificacion, no JWT)
- **Roles allowed:** N/A
- **Tenant context:** Not required — resuelto desde el token almacenado en Redis
- **Special rules:** Token de un solo uso, valido por 24 horas. No bloquea acceso (MVP: login permitido sin verificar email).

---

## Endpoint

```
POST /api/v1/auth/verify-email
```

**Rate Limiting:**
- 10 requests por hora por IP
- Redis sliding window: `dentalos:verify_email_rate:{ip}`

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
  "token": "string (required) — token de verificacion recibido por email (UUID v4)"
}
```

**Example Request:**
```json
{
  "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
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
  "message": "Correo electronico verificado exitosamente."
}
```

### Error Responses

#### 400 Bad Request
**When:** Campo token faltante o formato invalido.

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
  "error": "verification_token_invalid",
  "message": "El enlace de verificacion es invalido o ha expirado. Solicite uno nuevo."
}
```

#### 409 Conflict
**When:** Email ya verificado.

```json
{
  "error": "email_already_verified",
  "message": "Su correo electronico ya ha sido verificado."
}
```

#### 429 Too Many Requests
**When:** Excede rate limit.

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiados intentos. Intente nuevamente mas tarde.",
  "details": { "retry_after_seconds": 1800 }
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (token requerido, formato UUID).
2. Verificar rate limit por IP en Redis.
3. Calcular SHA-256 hash del token recibido.
4. Buscar en Redis: `dentalos:email_verification:{token_hash}`.
5. Si no se encuentra, retornar 401 con `verification_token_invalid`.
6. Extraer metadata del token: `{user_id, tenant_id, email, created_at}`.
7. Resolver schema del tenant y buscar usuario en `{schema}.users` WHERE `id = user_id`.
8. Si usuario no encontrado, retornar 401 con `verification_token_invalid` (generico).
9. Si `email_verified = true`, retornar 409 con `email_already_verified`.
10. Actualizar usuario: `UPDATE users SET email_verified = true, updated_at = now() WHERE id = user_id`.
11. Eliminar token de Redis: `DEL dentalos:email_verification:{token_hash}`.
12. Registrar evento en audit_log.
13. Retornar 200 OK.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| token | Requerido, formato UUID v4 | "Este campo es obligatorio." / "Formato de token invalido." |

**Business Rules:**

- Token de un solo uso, eliminado de Redis tras uso exitoso.
- Token valido por 24 horas (TTL de Redis).
- La verificacion de email NO es bloqueante en MVP. Los usuarios pueden iniciar sesion y usar la plataforma sin verificar el email.
- Si el email ya esta verificado, retornar 409 (informativo, no error critico).
- Un usuario puede solicitar un nuevo email de verificacion si el token expira (endpoint separado: POST /api/v1/auth/resend-verification).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Token ya utilizado (no existe en Redis) | 401 con verification_token_invalid |
| Token expirado (TTL de Redis vencido) | 401 con verification_token_invalid |
| Email ya verificado | 409 con email_already_verified |
| Usuario desactivado despues del registro | 401 con verification_token_invalid (generico) |
| Multiples clicks en el enlace | Primer click verifica, siguientes retornan 401 o 409 |
| Token valido pero tenant cancelado | 401 con verification_token_invalid |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `users`: UPDATE — `email_verified = true`, `updated_at = now()`
- `audit_log`: INSERT — registro de verificacion de email

### Cache Operations

**Cache keys affected:**
- `dentalos:email_verification:{token_hash}`: DELETE — consumir token
- `dentalos:verify_email_rate:{ip}`: INCR — rate limit
- `dentalos:user_profile:{tenant_id}:{user_id}`: DELETE — invalidar cache de perfil

**Cache TTL:** Rate limit: 3600s. Verification token: 86400s (24 horas, establecido en register).

### Queue Jobs (RabbitMQ)

N/A — no se encolan jobs adicionales.

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** user (email_verification)
- **PHI involved:** No

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms
- **Maximum acceptable:** < 300ms

### Caching Strategy
- **Strategy:** Redis para tokens de verificacion
- **Cache key:** `dentalos:email_verification:{token_hash}`
- **TTL:** 86400s (24 horas, establecido en el registro)
- **Invalidation:** Al usar el token exitosamente

### Database Performance

**Queries executed:** 2 (load user, update email_verified)

**Indexes required:**
- `{schema}.users.id` — PRIMARY KEY

**N+1 prevention:** No aplica.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| token | Validar formato UUID, strip | Prevenir inyeccion |

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
1. Verificacion exitosa con token valido
   - **Given:** Token de verificacion valido en Redis para usuario con email_verified=false
   - **When:** POST /api/v1/auth/verify-email con token correcto
   - **Then:** 200 OK, email_verified actualizado a true, token eliminado de Redis

2. GET /me refleja email verificado
   - **Given:** Email recien verificado
   - **When:** GET /api/v1/auth/me
   - **Then:** user.email_verified = true

#### Edge Cases
1. Email ya verificado
   - **Given:** Usuario con email_verified=true y token aun valido
   - **When:** POST /api/v1/auth/verify-email
   - **Then:** 409 con "Su correo electronico ya ha sido verificado."

2. Multiples clicks rapidos en el enlace
   - **Given:** Token valido
   - **When:** Dos requests simultaneos
   - **Then:** Primero 200 OK, segundo 401 (token consumido) o 409 (ya verificado)

3. Verificacion despues de cambio de datos de usuario
   - **Given:** Usuario cambio su nombre despues del registro
   - **When:** POST /api/v1/auth/verify-email con token original
   - **Then:** 200 OK (token sigue valido, se referencia por user_id)

#### Error Cases
1. Token invalido (no existe)
   - **Given:** UUID aleatorio que no corresponde a ningun token
   - **When:** POST /api/v1/auth/verify-email
   - **Then:** 401 con "El enlace de verificacion es invalido o ha expirado."

2. Token expirado (TTL vencido en Redis)
   - **Given:** Token cuyo TTL de 24h ha vencido
   - **When:** POST /api/v1/auth/verify-email
   - **Then:** 401 con verification_token_invalid

3. Token ya utilizado
   - **Given:** Token que ya fue consumido (eliminado de Redis)
   - **When:** POST /api/v1/auth/verify-email
   - **Then:** 401 con verification_token_invalid

4. Rate limit excedido
   - **Given:** 10 intentos en la ultima hora desde misma IP
   - **When:** POST /api/v1/auth/verify-email (11vo intento)
   - **Then:** 429 Too Many Requests

5. Formato de token invalido
   - **Given:** Token = "not-a-uuid"
   - **When:** POST /api/v1/auth/verify-email
   - **Then:** 400 Bad Request

### Test Data Requirements

**Users:** Un usuario con email_verified=false. Un usuario con email_verified=true.

**Redis:** Token de verificacion valido pre-insertado.

### Mocking Strategy

- **Redis:** fakeredis para tokens y rate limiting
- **Database:** Test PostgreSQL o SQLite in-memory

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Token valido actualiza email_verified a true
- [ ] Token se consume (no reutilizable)
- [ ] Token expirado (24h) retorna 401
- [ ] Email ya verificado retorna 409
- [ ] Rate limit de 10/hora/IP funciona
- [ ] Cache de perfil de usuario invalidado despues de verificacion
- [ ] Audit log registrado
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Generacion del token de verificacion (ver auth/register.md)
- Re-envio del email de verificacion (POST /api/v1/auth/resend-verification — spec separado)
- Verificacion de email al cambiar email (post-MVP)
- Bloqueo de funcionalidades para emails no verificados (MVP: sin bloqueo)
- Verificacion de email para pacientes del portal

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (Public, verification-token)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (auth domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Public, verification-token)
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for email verification

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
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
