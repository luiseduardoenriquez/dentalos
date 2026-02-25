# Refresh Token (A-03)

---

## Overview

**Feature:** Rotacion de tokens. Recibe el refresh token actual (via cookie HttpOnly), lo invalida, y emite un nuevo par de access token + refresh token. Implementa deteccion de reutilizacion: si un refresh token ya revocado es presentado, se revocan TODAS las sesiones del usuario por seguridad.

**Domain:** auth

**Priority:** Critical

**Dependencies:** I-02 (authentication-rules.md), database-architecture.md (user_sessions table)

---

## Authentication

- **Level:** Public (no requiere access token, usa refresh token via cookie)
- **Roles allowed:** N/A
- **Tenant context:** Resuelto internamente desde el refresh token -> user -> tenant
- **Special rules:** El refresh token es de un solo uso. La reutilizacion dispara revocacion total de sesiones.

---

## Endpoint

```
POST /api/v1/auth/refresh-token
```

**Rate Limiting:**
- Inherits global rate limit (100/min per IP)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Cookie | Yes | string | Refresh token en cookie HttpOnly | refresh_token=550e8400-e29b-41d4... |

### URL Parameters

N/A

### Query Parameters

N/A

### Request Body Schema

N/A — El refresh token se extrae de la cookie.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "access_token": "string — JWT RS256",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Example:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Set-Cookie header (nuevo refresh token):**
```
Set-Cookie: refresh_token=<new_uuid>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=2592000
```

### Error Responses

#### 401 Unauthorized
**When:** Refresh token no proporcionado, invalido, expirado o ya revocado.

**Token no encontrado en cookie:**
```json
{
  "error": "refresh_token_missing",
  "message": "No se encontro token de sesion. Inicie sesion nuevamente."
}
```

**Token no existe en base de datos:**
```json
{
  "error": "refresh_token_invalid",
  "message": "Token de sesion invalido. Inicie sesion nuevamente."
}
```

**Token expirado:**
```json
{
  "error": "refresh_token_expired",
  "message": "Su sesion ha expirado. Inicie sesion nuevamente."
}
```

**Token ya fue utilizado (deteccion de reutilizacion — posible robo de sesion):**
```json
{
  "error": "session_compromised",
  "message": "Sesion comprometida. Todas las sesiones han sido revocadas por seguridad. Inicie sesion nuevamente."
}
```

---

## Business Logic

**Step-by-step process:**

1. Extraer refresh token de la cookie `refresh_token`.
2. Si no hay cookie, retornar 401 con `refresh_token_missing`.
3. Calcular SHA-256 hash del token recibido.
4. Buscar en `user_sessions` por `refresh_token_hash` (en el schema del tenant correspondiente).
5. Si no se encuentra, retornar 401 con `refresh_token_invalid`.
6. **Si `is_revoked = true` (DETECCION DE REUTILIZACION):**
   a. Este token ya fue usado y revocado — posible robo de sesion.
   b. Revocar TODAS las sesiones activas del usuario: `UPDATE user_sessions SET is_revoked = true WHERE user_id = ? AND is_revoked = false`.
   c. Establecer version de token en Redis: `SET dentalos:user_token_version:{user_id} {timestamp}`.
   d. Registrar evento de seguridad en audit_log con severity SECURITY.
   e. Retornar 401 con `session_compromised`.
7. Si `expires_at < now()`, retornar 401 con `refresh_token_expired`.
8. Revocar el token actual: `UPDATE user_sessions SET is_revoked = true WHERE id = ?`.
9. Cargar datos del usuario desde `users` table.
10. Cargar datos del tenant desde `public.tenants` (con cache Redis).
11. Generar nuevo access token JWT con claims actualizados.
12. Generar nuevo refresh token (UUID v4), hashear SHA-256, insertar en `user_sessions`.
13. Retornar 200 con nuevo access token en body y nuevo refresh token en Set-Cookie.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| refresh_token (cookie) | UUID v4 valido, presente | "No se encontro token de sesion. Inicie sesion nuevamente." |

**Business Rules:**

- Cada refresh token es de **un solo uso**. Una vez utilizado, queda marcado como revocado.
- La reutilizacion de un token revocado indica posible compromiso de sesion y dispara revocacion total.
- El nuevo refresh token hereda el mismo TTL (30 dias desde el momento de emision).
- Los claims del access token se regeneran con datos frescos del usuario (en caso de cambio de rol u otros datos).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Refresh token valido pero usuario desactivado | Retornar 401 (usuario is_active=false) |
| Refresh token valido pero tenant cancelado | Retornar 403 con tenant_cancelled |
| Dos requests simultaneos con el mismo refresh token | El primero tiene exito, el segundo dispara deteccion de reutilizacion |
| Token en formato invalido (no UUID) | Retornar 401 con refresh_token_invalid |
| Cookie presente pero vacia | Retornar 401 con refresh_token_missing |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `user_sessions`: UPDATE — revocar token actual (`is_revoked = true`)
- `user_sessions`: INSERT — nueva sesion con nuevo refresh token hash
- `user_sessions`: UPDATE (en caso de replay) — revocar TODAS las sesiones del usuario

### Cache Operations

**Cache keys affected:**
- `dentalos:tenant_info:{tenant_id}`: GET — lectura de cache
- `dentalos:user_token_version:{user_id}`: SET (solo en replay detection) — invalidar access tokens previos

**Cache TTL:** Tenant info: 300s. Token version: sin TTL.

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| security | auth.session_compromised | { user_id, tenant_id, ip, timestamp } | Solo cuando se detecta reutilizacion |

### Audit Log

**Audit entry:** Yes (solo en deteccion de reutilizacion)

- **Action:** update (revocacion masiva de sesiones)
- **Resource:** user_sessions
- **PHI involved:** No

### Notifications

**Notifications triggered:** No (post-MVP: alerta de seguridad por email en deteccion de reutilizacion)

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Redis cache para tenant info
- **Cache key:** `dentalos:tenant_info:{tenant_id}`
- **TTL:** 300s
- **Invalidation:** Al actualizar datos del tenant

### Database Performance

**Queries executed:** 3-4 (lookup sesion, revocar, insert nueva, load usuario)

**Indexes required:**
- `user_sessions.refresh_token_hash` — INDEX (para lookup)
- `user_sessions.user_id` — INDEX (para revocacion masiva)
- `user_sessions.expires_at WHERE is_revoked = false` — partial INDEX

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

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** Cookie SameSite=Strict + Path restringido a /api/v1/auth. CSRF no aplica dado que el cookie solo se envia a endpoints de auth.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** Write-only logged (en caso de security event)

---

## Testing

### Test Cases

#### Happy Path
1. Rotacion exitosa de tokens
   - **Given:** Usuario con sesion activa y refresh token valido en cookie
   - **When:** POST /api/v1/auth/refresh-token
   - **Then:** 200 OK, nuevo access_token en body, nuevo refresh_token en Set-Cookie, token anterior revocado

2. Claims del access token actualizados tras cambio de datos
   - **Given:** Nombre del usuario cambio desde la ultima emision
   - **When:** POST /api/v1/auth/refresh-token
   - **Then:** Nuevo access token contiene el nombre actualizado

#### Edge Cases
1. Dos requests simultaneos con mismo refresh token
   - **Given:** Mismo refresh token enviado en paralelo
   - **When:** Ambos requests llegan al servidor
   - **Then:** Primero tiene exito (200), segundo dispara revocacion total (401 session_compromised)

2. Refresh token a punto de expirar (< 1 minuto restante)
   - **Given:** Token con expires_at = now() + 30s
   - **When:** POST /api/v1/auth/refresh-token
   - **Then:** 200 OK, nuevo token con TTL completo de 30 dias

#### Error Cases
1. Sin cookie de refresh token
   - **Given:** Request sin cookie refresh_token
   - **When:** POST /api/v1/auth/refresh-token
   - **Then:** 401 con "No se encontro token de sesion."

2. Refresh token expirado
   - **Given:** Token con expires_at en el pasado
   - **When:** POST /api/v1/auth/refresh-token
   - **Then:** 401 con "Su sesion ha expirado."

3. Deteccion de reutilizacion (replay attack)
   - **Given:** Refresh token que ya fue rotado (is_revoked=true)
   - **When:** POST /api/v1/auth/refresh-token con token revocado
   - **Then:** 401 con "Sesion comprometida.", TODAS las sesiones del usuario revocadas

4. Token no existe en DB
   - **Given:** UUID aleatorio que no corresponde a ningun token
   - **When:** POST /api/v1/auth/refresh-token
   - **Then:** 401 con "Token de sesion invalido."

5. Usuario desactivado
   - **Given:** Usuario con is_active=false pero sesion existente
   - **When:** POST /api/v1/auth/refresh-token
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Un usuario activo con sesion. Un usuario desactivado con sesion.

**Sessions:** Una sesion activa, una sesion expirada, una sesion revocada.

### Mocking Strategy

- **Redis:** fakeredis para token version checks
- **Crypto (SHA-256):** No mockear (determinista)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Refresh token valido genera nuevo par de tokens
- [ ] Token anterior queda revocado tras rotacion exitosa
- [ ] Nuevo refresh token entregado via Set-Cookie HttpOnly Secure
- [ ] Reutilizacion de token revocado dispara revocacion total de sesiones
- [ ] Deteccion de reutilizacion establece version de token en Redis
- [ ] Security event registrado en audit_log
- [ ] Tokens expirados retornan 401
- [ ] All test cases pass
- [ ] Performance targets met (< 400ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Refresh token del portal de pacientes (portal separado)
- Listado de sesiones activas (post-MVP)
- Notificacion de seguridad por email en replay detection (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (cookie)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (refresh token via cookie)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (auth domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Public, cookie-based)
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Security event audit trail

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
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
