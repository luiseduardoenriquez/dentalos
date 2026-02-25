# Registro de Clinica (A-01)

---

## Overview

**Feature:** Registro de una nueva clinica dental. Crea el tenant (schema PostgreSQL), el primer usuario con rol `clinic_owner`, siembra datos por defecto (plantillas de consentimiento, catalogo de servicios), y retorna tokens JWT para inicio de sesion inmediato.

**Domain:** auth

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy.md), I-02 (authentication-rules.md), database-architecture.md (public.tenants, public.plans, tenant schema template)

---

## Authentication

- **Level:** Public
- **Roles allowed:** N/A (endpoint publico)
- **Tenant context:** Not required (se crea durante la ejecucion)
- **Special rules:** Rate limit estricto por IP para prevenir abuso de provisionamiento de schemas.

---

## Endpoint

```
POST /api/v1/auth/register
```

**Rate Limiting:**
- 3 requests por hora por IP
- Implementado via Redis sliding window: `dentalos:register_rate:{ip}`

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Content-Type | Yes | string | Formato de request | application/json |
| X-Forwarded-For | No | string | IP real del cliente (detrás de proxy) | 190.25.100.50 |

### URL Parameters

N/A

### Query Parameters

N/A

### Request Body Schema

```json
{
  "email": "string (required) — correo del owner, max 320 chars",
  "password": "string (required) — min 8, max 128 chars, 1 mayuscula, 1 digito",
  "name": "string (required) — nombre completo del owner, max 200 chars",
  "clinic_name": "string (required) — nombre de la clinica, max 200 chars",
  "country": "string (required) — ISO 3166-1 alpha-2: CO, MX, CL, AR, PE, EC",
  "phone": "string (optional) — telefono del owner, max 20 chars"
}
```

**Example Request:**
```json
{
  "email": "dra.martinez@clinicasonrisa.co",
  "password": "Segura2026!",
  "name": "Dra. Ana Martinez",
  "clinic_name": "Clinica Dental Sonrisa",
  "country": "CO",
  "phone": "+573001234567"
}
```

---

## Response

### Success Response

**Status:** 201 Created

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
    "role": "clinic_owner",
    "avatar_url": "string | null"
  },
  "tenant": {
    "id": "UUID",
    "name": "string",
    "slug": "string",
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
    "id": "usr_550e8400-e29b-41d4-a716-446655440000",
    "email": "dra.martinez@clinicasonrisa.co",
    "name": "Dra. Ana Martinez",
    "role": "clinic_owner",
    "avatar_url": null
  },
  "tenant": {
    "id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "name": "Clinica Dental Sonrisa",
    "slug": "clinica-dental-sonrisa",
    "plan": "free",
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
**When:** Campos faltantes o formato invalido que no pasa validacion Pydantic.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": { "email": ["Formato de correo electronico invalido."] }
}
```

#### 409 Conflict
**When:** Ya existe un usuario registrado con ese email en cualquier tenant.

```json
{
  "error": "email_already_registered",
  "message": "Este correo electronico ya esta registrado."
}
```

#### 422 Unprocessable Entity
**When:** Contrasena no cumple requisitos de seguridad.

```json
{
  "error": "weak_password",
  "message": "La contrasena no cumple los requisitos de seguridad.",
  "details": { "password": ["La contrasena debe tener al menos 8 caracteres.", "La contrasena debe contener al menos una letra mayuscula."] }
}
```

#### 429 Too Many Requests
**When:** Excede 3 registros por hora por IP.

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiados intentos de registro. Intente nuevamente mas tarde.",
  "details": { "retry_after_seconds": 1800 }
}
```

#### 500 Internal Server Error
**When:** Fallo en la creacion del schema o provisionamiento del tenant.

```json
{
  "error": "provisioning_failed",
  "message": "Error al crear la clinica. Por favor intente nuevamente."
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (email, password, name, clinic_name, country, phone).
2. Verificar rate limit por IP en Redis (`dentalos:register_rate:{ip}`). Si excede 3/hora, retornar 429.
3. Normalizar email a lowercase y aplicar `strip()`.
4. Validar fortaleza de contrasena (min 8, max 128, 1 mayuscula, 1 digito, no contener email, no estar en lista de contrasenas comunes).
5. Verificar que el email no exista en ninguna tabla `users` de ningun tenant schema (busqueda en `public.tenants` + iteracion o tabla de lookup global).
6. Generar slug unico a partir de `clinic_name` (slugify + sufijo numerico si hay colision).
7. Crear registro en `public.tenants` con `status='provisioning'`, asignar plan `free` por defecto.
8. Generar `schema_name` = `tn_` + primeros 12 caracteres del tenant UUID (sin guiones).
9. Crear schema PostgreSQL: `CREATE SCHEMA {schema_name}`.
10. Ejecutar todas las migraciones de tenant contra el nuevo schema (tablas: users, user_sessions, user_invites, patients, etc.).
11. Sembrar datos por defecto en el schema: plantillas de consentimiento del sistema, catalogo de servicios base segun pais.
12. Hashear contrasena con bcrypt (12 rounds).
13. Crear usuario `clinic_owner` en `{schema_name}.users`.
14. Actualizar `public.tenants.status` a `'active'`.
15. Generar access token JWT (RS256, TTL 15min) y refresh token (UUID v4).
16. Hashear refresh token (SHA-256) y almacenar en `{schema_name}.user_sessions`.
17. Encolar job para enviar email de verificacion via RabbitMQ.
18. Registrar evento en audit_log del tenant.
19. Retornar 201 con tokens, datos del usuario y tenant.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| email | Email valido, max 320 chars, lowercase | "Formato de correo electronico invalido." |
| password | Min 8, max 128, 1 uppercase, 1 digit | "La contrasena debe tener al menos 8 caracteres." / "La contrasena debe contener al menos una letra mayuscula." / "La contrasena debe contener al menos un numero." |
| password | No contener email | "La contrasena no debe contener su correo electronico." |
| password | No estar en lista de comunes | "Esta contrasena es muy comun. Elija una mas segura." |
| name | Min 2, max 200 chars | "El nombre debe tener entre 2 y 200 caracteres." |
| clinic_name | Min 2, max 200 chars | "El nombre de la clinica debe tener entre 2 y 200 caracteres." |
| country | ISO 3166-1 alpha-2, dentro de: CO, MX, CL, AR, PE, EC | "Pais no soportado." |
| phone | Regex E.164, max 20 chars (opcional) | "Formato de telefono invalido." |

**Business Rules:**

- Un email solo puede estar registrado en un tenant (restriccion MVP de un-usuario-un-tenant).
- El plan inicial siempre es `free`.
- El provisionamiento del schema es transaccional: si falla cualquier paso, se revierte todo (DROP SCHEMA IF EXISTS).
- El usuario se crea con `email_verified=false`.
- El tenant se crea con `onboarding_step=0`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Slug de clinica ya existe | Agregar sufijo numerico: "clinica-dental-sonrisa-2" |
| Creacion de schema falla | Rollback completo, retornar 500, limpiar registro en public.tenants |
| Email con mayusculas y espacios | Normalizar a lowercase, strip whitespace |
| Pais no soportado (ej: "US") | Retornar 422 con "Pais no soportado." |
| Request duplicado rapido (doble click) | El segundo falla con 409 si el primero ya completo |

---

## Side Effects

### Database Changes

**Public schema:**
- `public.tenants`: INSERT — nuevo registro de tenant
- `public.plans`: READ — obtener plan free por defecto

**Tenant schema (recien creado):**
- `{schema}.users`: INSERT — crear clinic_owner
- `{schema}.user_sessions`: INSERT — almacenar refresh token hash
- `{schema}.consent_templates`: INSERT — plantillas del sistema
- `{schema}.service_catalog`: INSERT — servicios base segun pais
- `{schema}.audit_log`: INSERT — registro de creacion

### Cache Operations

**Cache keys affected:**
- `dentalos:register_rate:{ip}`: INCR — incrementar contador de rate limit
- `dentalos:tenant_info:{tenant_id}`: SET — cachear info del nuevo tenant

**Cache TTL:** Rate limit: 3600s. Tenant info: 300s.

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | email.verification | { user_id, email, token, tenant_name } | Despues de crear usuario exitosamente |
| analytics | tenant.created | { tenant_id, country, plan, created_at } | Despues de provisionamiento exitoso |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** tenant + user
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | email_verification | clinic_owner | Al completar registro |

---

## Performance

### Expected Response Time
- **Target:** < 2000ms (incluye creacion de schema y migraciones)
- **Maximum acceptable:** < 5000ms

### Caching Strategy
- **Strategy:** No caching para el endpoint. Post-creacion: cachear tenant_info en Redis.
- **Cache key:** `dentalos:tenant_info:{tenant_id}`
- **TTL:** 300s
- **Invalidation:** Al actualizar datos del tenant.

### Database Performance

**Queries executed:** ~15-20 (creacion de schema, migraciones, inserts de seed data)

**Indexes required:**
- `public.tenants.slug` — UNIQUE
- `public.tenants.schema_name` — UNIQUE
- `{schema}.users.email` — UNIQUE (lower)

**N+1 prevention:** No aplica (operacion de escritura masiva unica).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| email | Pydantic EmailStr, lowercase, strip | Prevenir inyeccion en email |
| name | strip_tags, max length | Prevenir XSS en nombre |
| clinic_name | strip_tags, max length | Prevenir XSS en nombre de clinica |
| password | No sanitizar (se hashea) | Solo validar fortaleza |
| phone | Regex E.164 | Solo digitos y + |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. La creacion del schema usa formato seguro con validacion de nombre.

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
1. Registro exitoso con todos los campos
   - **Given:** No existe usuario con email "test@clinica.co"
   - **When:** POST /api/v1/auth/register con datos validos
   - **Then:** 201 Created, retorna access_token y refresh_token en cookie, tenant creado con status 'active'

2. Registro exitoso sin telefono
   - **Given:** No existe usuario con email "test2@clinica.co"
   - **When:** POST /api/v1/auth/register sin campo phone
   - **Then:** 201 Created, usuario creado con phone=null

#### Edge Cases
1. Email con mayusculas y espacios
   - **Given:** Email enviado como "  DrA.Test@Clinica.CO  "
   - **When:** POST /api/v1/auth/register
   - **Then:** Email normalizado a "dra.test@clinica.co", registro exitoso

2. Slug de clinica duplicado
   - **Given:** Ya existe tenant con slug "clinica-dental"
   - **When:** Registrar clinica con nombre "Clinica Dental"
   - **Then:** Slug generado como "clinica-dental-2"

3. Request concurrente con mismo email
   - **Given:** Dos requests simultaneos con mismo email
   - **When:** Ambos llegan al servidor
   - **Then:** Uno tiene exito (201), el otro falla (409)

#### Error Cases
1. Email ya registrado
   - **Given:** Existe usuario con email "existente@clinica.co"
   - **When:** POST /api/v1/auth/register con ese email
   - **Then:** 409 Conflict con error "email_already_registered"

2. Contrasena debil
   - **Given:** Password "12345678" (sin mayuscula)
   - **When:** POST /api/v1/auth/register
   - **Then:** 422 con error "weak_password"

3. Rate limit excedido
   - **Given:** 3 registros previos desde la misma IP en la ultima hora
   - **When:** POST /api/v1/auth/register (4to intento)
   - **Then:** 429 Too Many Requests

4. Pais no soportado
   - **Given:** Country = "US"
   - **When:** POST /api/v1/auth/register
   - **Then:** 422 con error "Pais no soportado."

### Test Data Requirements

**Users:** Ninguno preexistente para happy path. Un usuario existente para test de duplicado.

**Tenants:** Un tenant existente con slug predecible para test de colision.

### Mocking Strategy

- **PostgreSQL schema creation:** Mock en tests unitarios, real en tests de integracion
- **RabbitMQ (email queue):** Mock — verificar que el job fue encolado con payload correcto
- **Redis:** Usar fakeredis en tests unitarios

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/auth/register crea tenant, schema, usuario y retorna tokens
- [ ] Email duplicado retorna 409
- [ ] Contrasena debil retorna 422 con mensajes especificos en espanol
- [ ] Rate limit de 3/hora/IP funciona correctamente
- [ ] Schema PostgreSQL se crea con todas las tablas del template
- [ ] Datos seed (consent_templates, service_catalog) se insertan correctamente
- [ ] Email de verificacion se encola en RabbitMQ
- [ ] Refresh token se entrega via Set-Cookie HttpOnly Secure
- [ ] Rollback completo si falla el provisionamiento
- [ ] All test cases pass
- [ ] Performance targets met (< 5000ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Verificacion de email (ver auth/verify-email.md)
- Flujo de onboarding post-registro (ver tenants/onboarding.md)
- Registro de pacientes (flujo separado via portal)
- Registro via OAuth/SSO (post-MVP)
- Seleccion de plan al registrarse (siempre empieza en free)

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
- [x] Auth level stated (Public with rate limit)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for tenant creation

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (post-creation tenant cache)
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
