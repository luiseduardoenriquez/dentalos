# Forgot Password (A-05)

---

## Overview

**Feature:** Solicitud de restablecimiento de contrasena. Recibe un email y, si existe un usuario con ese correo, encola un email con un enlace de restablecimiento que contiene un token de un solo uso valido por 1 hora. **Siempre retorna 200 OK** independientemente de si el email existe o no, para prevenir enumeracion de usuarios.

**Domain:** auth

**Priority:** High

**Dependencies:** I-02 (authentication-rules.md), database-architecture.md (users table)

---

## Authentication

- **Level:** Public
- **Roles allowed:** N/A
- **Tenant context:** Not required — resuelto internamente si el email existe
- **Special rules:** NUNCA revelar si el email existe. Rate limit estricto.

---

## Endpoint

```
POST /api/v1/auth/forgot-password
```

**Rate Limiting:**
- 3 requests por hora por IP
- Redis sliding window: `dentalos:forgot_password_rate:{ip}` (TTL 3600s)

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
  "email": "string (required) — correo del usuario"
}
```

**Example Request:**
```json
{
  "email": "dra.martinez@clinicasonrisa.co"
}
```

---

## Response

### Success Response

**Status:** 200 OK

**SIEMPRE retorna este response, sin importar si el email existe o no.**

**Schema:**
```json
{
  "message": "string"
}
```

**Example:**
```json
{
  "message": "Si existe una cuenta con ese correo electronico, recibira un enlace para restablecer su contrasena."
}
```

### Error Responses

#### 400 Bad Request
**When:** Formato de email invalido.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": { "email": ["Formato de correo electronico invalido."] }
}
```

#### 429 Too Many Requests
**When:** Excede 3 solicitudes por hora por IP.

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiadas solicitudes. Intente nuevamente mas tarde.",
  "details": { "retry_after_seconds": 1800 }
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (email requerido, formato valido).
2. Normalizar email a lowercase, strip whitespace.
3. Verificar rate limit por IP en Redis (`dentalos:forgot_password_rate:{ip}`). Si excede 3/hora, retornar 429.
4. Buscar usuario por email en todos los tenant schemas (via lookup table o iteracion).
5. **Si el email NO existe:** Retornar 200 OK con el mensaje generico. No hacer nada mas. (Tiempo de respuesta constante para prevenir timing attacks).
6. **Si el email existe:**
   a. Generar token de restablecimiento (UUID v4).
   b. Calcular hash SHA-256 del token.
   c. Almacenar hash en Redis con TTL de 1 hora: `dentalos:password_reset:{token_hash}` -> `{user_id, tenant_id, email, created_at}`.
   d. Encolar job de envio de email via RabbitMQ con el enlace: `https://app.dentalos.com/auth/reset-password?token={raw_token}`.
7. Retornar 200 OK con el mensaje generico.
8. **Importante:** El tiempo de respuesta debe ser el mismo (aprox) independientemente de si el email existe, para prevenir timing attacks. Agregar delay artificial si es necesario.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| email | Requerido, formato email valido, max 320 chars | "Este campo es obligatorio." / "Formato de correo electronico invalido." |

**Business Rules:**

- SIEMPRE retornar 200 OK con el mismo mensaje, exista o no el email.
- Si ya existe un token de reset activo para el mismo email, invalidar el anterior y generar uno nuevo.
- El token es valido por 1 hora desde su generacion.
- El token es de un solo uso (consumido en reset-password).
- Solo usuarios activos (`is_active=true`) pueden solicitar reset.
- Usuarios de tenants cancelados no reciben email (pero la respuesta sigue siendo 200).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Email no existe | 200 OK, sin email enviado, misma latencia de respuesta |
| Email existe pero usuario inactivo | 200 OK, sin email enviado |
| Email existe pero tenant cancelado | 200 OK, sin email enviado |
| Token de reset previo activo | Token anterior invalidado, nuevo token generado |
| Multiples solicitudes rapidas (dentro del rate limit) | Cada una genera nuevo token, anteriores invalidados |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- Ninguno — los tokens de reset se almacenan en Redis, no en PostgreSQL.

### Cache Operations

**Cache keys affected:**
- `dentalos:forgot_password_rate:{ip}`: INCR — contador de rate limit
- `dentalos:password_reset:{token_hash}`: SET — almacenar token con metadata
- `dentalos:password_reset_email:{email_hash}`: SET — referencia al token activo (para invalidar anteriores)

**Cache TTL:** Rate limit: 3600s. Reset token: 3600s. Email reference: 3600s.

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | email.password_reset | { email, reset_url, user_name, tenant_name } | Solo si el email existe y el usuario esta activo |

### Audit Log

**Audit entry:** Yes (solo si el email existe)

- **Action:** create
- **Resource:** password_reset_token
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes (solo si el email existe)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | password_reset | usuario | Solo si el email existe y esta activo |

---

## Performance

### Expected Response Time
- **Target:** 200-400ms (constante, independiente de si el email existe)
- **Maximum acceptable:** < 600ms

### Caching Strategy
- **Strategy:** Redis para tokens de reset y rate limiting
- **Cache key:** `dentalos:password_reset:{token_hash}`
- **TTL:** 3600s (1 hora)
- **Invalidation:** Al usar el token o generar uno nuevo para el mismo email

### Database Performance

**Queries executed:** 0-1 (lookup de usuario, solo si email valido)

**Indexes required:**
- `{schema}.users.lower(email)` — UNIQUE (ya existente)

**N+1 prevention:** No aplica.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| email | Pydantic EmailStr, lowercase, strip | Prevenir inyeccion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** Response body es texto estatico, sin datos del usuario.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None

**Audit requirement:** Write-only logged (creacion de token)

### Anti-Enumeration

**Critical:** Este endpoint NO debe revelar si un email existe. Medidas:
1. Siempre retornar 200 OK con el mismo mensaje.
2. Tiempo de respuesta constante (~300ms) independiente del resultado.
3. Rate limit para prevenir fuerza bruta.

---

## Testing

### Test Cases

#### Happy Path
1. Solicitud con email existente
   - **Given:** Usuario activo "test@clinica.co" existe
   - **When:** POST /api/v1/auth/forgot-password con ese email
   - **Then:** 200 OK con mensaje generico. Email de reset encolado en RabbitMQ.

2. Solicitud con email inexistente
   - **Given:** Email "noexiste@test.co" no esta registrado
   - **When:** POST /api/v1/auth/forgot-password con ese email
   - **Then:** 200 OK con el **mismo** mensaje generico. Ningun email encolado.

#### Edge Cases
1. Token de reset previo activo
   - **Given:** Usuario ya solicito reset hace 10 min (token activo en Redis)
   - **When:** POST /api/v1/auth/forgot-password nuevamente
   - **Then:** 200 OK, token anterior invalidado, nuevo token creado

2. Tiempo de respuesta constante
   - **Given:** Email existente y email inexistente
   - **When:** Comparar tiempos de respuesta de ambos requests
   - **Then:** Diferencia < 50ms (no revelable via timing attack)

3. Email de usuario inactivo
   - **Given:** Usuario con is_active=false
   - **When:** POST /api/v1/auth/forgot-password
   - **Then:** 200 OK, sin email enviado

#### Error Cases
1. Formato de email invalido
   - **Given:** Email "no-es-email"
   - **When:** POST /api/v1/auth/forgot-password
   - **Then:** 400 Bad Request

2. Rate limit excedido
   - **Given:** 3 solicitudes previas desde misma IP en la ultima hora
   - **When:** POST /api/v1/auth/forgot-password (4ta solicitud)
   - **Then:** 429 Too Many Requests

3. Campo email vacio
   - **Given:** Body sin campo email o email vacio
   - **When:** POST /api/v1/auth/forgot-password
   - **Then:** 400 Bad Request

### Test Data Requirements

**Users:** Un usuario activo, un usuario inactivo.

**Tenants:** Un tenant activo, uno cancelado.

### Mocking Strategy

- **Redis:** fakeredis para rate limiting y almacenamiento de tokens
- **RabbitMQ:** Mock — verificar que el job fue encolado con payload correcto
- **Time:** Mock para verificar latencia constante

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Siempre retorna 200 OK independientemente de si el email existe
- [ ] Token de reset almacenado en Redis con TTL de 1 hora
- [ ] Email de restablecimiento encolado solo para usuarios activos
- [ ] Rate limit de 3/hora/IP funciona correctamente
- [ ] Tiempo de respuesta constante (anti timing attack)
- [ ] Token anterior invalidado al generar uno nuevo
- [ ] Formato del enlace de reset correcto
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- El proceso de reset de contrasena en si (ver auth/reset-password.md)
- Envio del email (ver integrations/email-engine.md)
- Forgot password para portal de pacientes (separado)
- Notificacion de seguridad post-reset (cubierto en reset-password.md)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (Public)
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
- [x] Anti-enumeration measures documented

### Hook 4: Performance & Scalability
- [x] Response time target defined (constant)
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
