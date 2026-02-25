# Logout (A-08)

---

## Overview

**Feature:** Cierre de sesion del usuario. Revoca el refresh token actual, agrega el JTI del access token a la blacklist de Redis (para invalidacion inmediata), y limpia la cookie de refresh token. Retorna 204 No Content.

**Domain:** auth

**Priority:** High

**Dependencies:** I-02 (authentication-rules.md), database-architecture.md (user_sessions table)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist (todos los roles de staff)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** El endpoint acepta el request incluso si el refresh token en la cookie ya es invalido (logout graceful).

---

## Endpoint

```
POST /api/v1/auth/logout
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT access token | Bearer eyJhbGc... |
| Cookie | No | string | Refresh token (si presente, se revoca) | refresh_token=550e8400... |

### URL Parameters

N/A

### Query Parameters

N/A

### Request Body Schema

N/A — no requiere body.

---

## Response

### Success Response

**Status:** 204 No Content

**Body:** Vacio.

**Set-Cookie header (limpieza):**
```
Set-Cookie: refresh_token=; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT
```

### Error Responses

#### 401 Unauthorized
**When:** Access token invalido o expirado.

Standard auth failure — see infra/authentication-rules.md

```json
{
  "error": "token_expired",
  "message": "El token de acceso ha expirado. Use el refresh token para obtener uno nuevo."
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar access token JWT via dependency `get_current_user()`.
2. Extraer `jti` del access token para blacklist.
3. Agregar JTI a Redis blacklist: `SET dentalos:token_blacklist:{jti} "1"` con TTL = segundos restantes del token (max 900s).
4. Si hay cookie `refresh_token` presente:
   a. Calcular SHA-256 hash del refresh token.
   b. Buscar en `{schema}.user_sessions` por `refresh_token_hash`.
   c. Si se encuentra y no esta revocado: `UPDATE user_sessions SET is_revoked = true WHERE id = session_id`.
5. Enviar header `Set-Cookie` para limpiar la cookie de refresh token (Max-Age=0).
6. Registrar evento `auth.logout` en log estructurado.
7. Retornar 204 No Content.

**Validation Rules:**

N/A — no acepta input del usuario mas alla del JWT y cookie.

**Business Rules:**

- El logout es **graceful**: si el refresh token no existe o ya esta revocado, el endpoint no falla. Solo revoca lo que pueda.
- El access token se invalida inmediatamente via blacklist en Redis.
- La blacklist tiene TTL igual al tiempo restante del access token (evita crecimiento infinito).
- El refresh token se revoca en la base de datos con `is_revoked = true`.
- La cookie se limpia con `Max-Age=0`.
- **No se dispara revocacion masiva** (eso es solo para change-password, reset-password, y replay detection).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Sin cookie de refresh token | 204 OK, solo blacklist del access token |
| Cookie con refresh token ya revocado | 204 OK, no error (graceful) |
| Cookie con refresh token inexistente en DB | 204 OK, no error (graceful) |
| Cookie con refresh token expirado | 204 OK, no error (graceful) |
| Access token a punto de expirar (< 10s) | Blacklist con TTL minimo (10s floor) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `user_sessions`: UPDATE — `is_revoked = true` para la sesion actual (si refresh token presente)

### Cache Operations

**Cache keys affected:**
- `dentalos:token_blacklist:{jti}`: SET "1" — invalidar access token inmediatamente
  - TTL: segundos restantes del token (calculado como `exp - now()`, minimo 10s)

**Cache TTL:** Blacklist: max 900s (15 min = TTL del access token).

### Queue Jobs (RabbitMQ)

N/A — no se encolan jobs.

### Audit Log

**Audit entry:** No — logout no requiere audit log formal. Se registra en log estructurado para observabilidad.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms
- **Maximum acceptable:** < 150ms

### Caching Strategy
- **Strategy:** Redis para blacklist de access tokens
- **Cache key:** `dentalos:token_blacklist:{jti}`
- **TTL:** Segundos restantes del access token (max 900s)
- **Invalidation:** Auto-expira por TTL

### Database Performance

**Queries executed:** 0-1 (update sesion, solo si refresh token presente y valido)

**Indexes required:**
- `{schema}.user_sessions.refresh_token_hash` — INDEX (ya existente)

**N+1 prevention:** No aplica.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| refresh_token (cookie) | Validar formato UUID | Prevenir inyeccion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** Sin body en respuesta (204).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** Not required (logged via structured logging)

---

## Testing

### Test Cases

#### Happy Path
1. Logout exitoso con access token y refresh token
   - **Given:** Usuario autenticado con sesion activa y cookie de refresh token
   - **When:** POST /api/v1/auth/logout
   - **Then:** 204 No Content, refresh token revocado, JTI en blacklist, cookie limpiada

2. Access token rechazado despues de logout
   - **Given:** Logout completado
   - **When:** GET /api/v1/auth/me con el access token anterior
   - **Then:** 401 con error "token_revoked"

#### Edge Cases
1. Logout sin cookie de refresh token
   - **Given:** Access token valido pero sin cookie
   - **When:** POST /api/v1/auth/logout
   - **Then:** 204 No Content, solo JTI en blacklist, cookie header de limpieza enviado

2. Logout con refresh token ya revocado
   - **Given:** Cookie con refresh token previamente revocado
   - **When:** POST /api/v1/auth/logout
   - **Then:** 204 No Content (graceful, sin error)

3. Logout con access token a punto de expirar
   - **Given:** Access token con < 10s de vida
   - **When:** POST /api/v1/auth/logout
   - **Then:** 204 No Content, blacklist con TTL minimo de 10s

#### Error Cases
1. Sin access token
   - **Given:** Request sin header Authorization
   - **When:** POST /api/v1/auth/logout
   - **Then:** 401 Unauthorized

2. Access token expirado
   - **Given:** Access token con exp en el pasado
   - **When:** POST /api/v1/auth/logout
   - **Then:** 401 con error "token_expired"

### Test Data Requirements

**Users:** Un usuario autenticado con sesion activa.

**Sessions:** Una sesion activa con refresh token valido.

### Mocking Strategy

- **Redis:** fakeredis para blacklist
- **Database:** SQLite in-memory o test PostgreSQL

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/auth/logout retorna 204 No Content
- [ ] JTI del access token agregado a blacklist de Redis con TTL correcto
- [ ] Refresh token revocado en user_sessions (si cookie presente)
- [ ] Cookie de refresh token limpiada via Set-Cookie con Max-Age=0
- [ ] Access token rechazado inmediatamente despues de logout
- [ ] Logout graceful cuando refresh token no existe o ya esta revocado
- [ ] All test cases pass
- [ ] Performance targets met (< 150ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Logout de todos los dispositivos (logout-all, disparado por change-password/reset-password)
- Logout del portal de pacientes (portal separado)
- Notificacion de logout

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (JWT + cookie)
- [x] All outputs defined (204 No Content)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (N/A)
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
- [x] Audit trail (structured logging)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (blacklist)
- [x] DB queries optimized
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (structured log)
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
