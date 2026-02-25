# Invite User (A-09)

---

## Overview

**Feature:** Invitacion de un nuevo usuario al tenant. Solo el `clinic_owner` puede invitar miembros del equipo (doctor, assistant, receptionist). Crea un registro en `user_invites`, genera un token de invitacion de un solo uso valido por 7 dias, y encola un email con el enlace de aceptacion. Verifica limites del plan antes de crear la invitacion.

**Domain:** auth

**Priority:** High

**Dependencies:** I-02 (authentication-rules.md), database-architecture.md (users, user_invites tables), public.plans (max_users)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Solo clinic_owner puede invitar. Verificacion de limite de usuarios del plan.

---

## Endpoint

```
POST /api/v1/auth/invite
```

**Rate Limiting:**
- 10 requests por hora per user
- Redis sliding window: `dentalos:invite_rate:{user_id}`

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
  "email": "string (required) — correo del invitado, max 320 chars",
  "role": "string (required) — rol asignado: doctor, assistant, receptionist",
  "name": "string (required) — nombre del invitado, max 200 chars"
}
```

**Example Request:**
```json
{
  "email": "dr.garcia@email.com",
  "role": "doctor",
  "name": "Dr. Carlos Garcia"
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "id": "UUID",
  "email": "string",
  "role": "string",
  "name": "string",
  "status": "pending",
  "expires_at": "ISO 8601 datetime",
  "created_at": "ISO 8601 datetime"
}
```

**Example:**
```json
{
  "id": "inv_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "dr.garcia@email.com",
  "role": "doctor",
  "name": "Dr. Carlos Garcia",
  "status": "pending",
  "expires_at": "2026-03-03T10:00:00Z",
  "created_at": "2026-02-24T10:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Campos faltantes o formato invalido.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": { "role": ["Rol invalido. Valores permitidos: doctor, assistant, receptionist."] }
}
```

#### 401 Unauthorized
**When:** Token invalido o expirado. Standard auth failure.

#### 403 Forbidden
**When:** Usuario no es clinic_owner.

```json
{
  "error": "insufficient_role",
  "message": "Solo el propietario de la clinica puede invitar nuevos usuarios.",
  "details": { "required_roles": ["clinic_owner"], "current_role": "doctor" }
}
```

#### 409 Conflict
**When:** Email ya registrado en el tenant, o invitacion pendiente activa para ese email.

```json
{
  "error": "user_already_exists",
  "message": "Ya existe un usuario con este correo electronico en su clinica."
}
```

```json
{
  "error": "invite_already_pending",
  "message": "Ya existe una invitacion pendiente para este correo electronico.",
  "details": { "invite_id": "inv_a1b2c3d4...", "expires_at": "2026-03-01T10:00:00Z" }
}
```

#### 422 Unprocessable Entity
**When:** Rol no permitido o limite de plan excedido.

```json
{
  "error": "invalid_role",
  "message": "No se puede invitar con el rol especificado. Roles permitidos: doctor, assistant, receptionist."
}
```

```json
{
  "error": "plan_limit_reached",
  "message": "Ha alcanzado el limite de usuarios de su plan. Actualice su plan para agregar mas miembros.",
  "details": { "max_users": 3, "current_users": 3, "plan": "free" }
}
```

#### 429 Too Many Requests
**When:** Excede rate limit.

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiadas invitaciones enviadas. Intente nuevamente mas tarde.",
  "details": { "retry_after_seconds": 1800 }
}
```

---

## Business Logic

**Step-by-step process:**

1. Validar access token JWT via dependency `require_role(["clinic_owner"])`.
2. Validar input contra schema Pydantic (email, role, name requeridos).
3. Verificar rate limit por usuario en Redis.
4. Normalizar email a lowercase, strip whitespace.
5. Validar que el rol es uno de: `doctor`, `assistant`, `receptionist`. Rechazar `clinic_owner`, `patient`, `superadmin`.
6. Verificar que no existe un usuario activo con ese email en el tenant: `SELECT id FROM {schema}.users WHERE lower(email) = ? AND is_active = true`.
7. Si existe, retornar 409 con `user_already_exists`.
8. Verificar que no existe una invitacion pendiente activa para ese email: `SELECT id, expires_at FROM {schema}.user_invites WHERE lower(email) = ? AND status = 'pending' AND expires_at > now()`.
9. Si existe invitacion pendiente, retornar 409 con `invite_already_pending`.
10. Verificar limite de usuarios del plan:
    a. Contar usuarios activos: `SELECT COUNT(*) FROM {schema}.users WHERE is_active = true`.
    b. Contar invitaciones pendientes: `SELECT COUNT(*) FROM {schema}.user_invites WHERE status = 'pending' AND expires_at > now()`.
    c. Obtener `max_users` del plan del tenant.
    d. Si `current_users + pending_invites >= max_users`, retornar 422 con `plan_limit_reached`.
11. Generar token de invitacion (UUID v4).
12. Calcular SHA-256 hash del token.
13. Crear registro en `{schema}.user_invites` con: email, role, invited_by, token_hash, status='pending', expires_at=now()+7dias.
14. Encolar job de envio de email via RabbitMQ con enlace: `https://app.dentalos.com/auth/accept-invite?token={raw_token}`.
15. Registrar evento en audit_log.
16. Retornar 201 Created con datos de la invitacion.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| email | Requerido, email valido, max 320 chars | "Este campo es obligatorio." / "Formato de correo electronico invalido." |
| role | Requerido, uno de: doctor, assistant, receptionist | "Rol invalido. Valores permitidos: doctor, assistant, receptionist." |
| name | Requerido, min 2, max 200 chars | "El nombre debe tener entre 2 y 200 caracteres." |

**Business Rules:**

- Solo `clinic_owner` puede invitar (verificado via RBAC).
- Roles invitables: `doctor`, `assistant`, `receptionist`. NO se puede invitar `clinic_owner` (solo uno por tenant), `patient` (flujo separado), `superadmin`.
- Si existe invitacion expirada para el mismo email, se puede crear una nueva (la expirada se ignora).
- El limite de plan cuenta usuarios activos + invitaciones pendientes.
- Token de invitacion valido por 7 dias.
- Token almacenado como hash SHA-256 (el raw token solo viaja en el email).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Email ya existe como usuario inactivo | Permitir invitacion (usuario inactivo no cuenta) |
| Invitacion previa expirada para mismo email | Permitir nueva invitacion |
| Invitacion previa cancelada para mismo email | Permitir nueva invitacion |
| Limite de plan alcanzado exactamente | 422 plan_limit_reached |
| clinic_owner se invita a si mismo | 409 user_already_exists |
| Email del invitado existe en otro tenant | Permitir (MVP: un email puede existir en multiples tenants via invitaciones, se resolvera al aceptar) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `user_invites`: INSERT — nueva invitacion con token hash, status='pending'
- `audit_log`: INSERT — registro de invitacion creada

### Cache Operations

**Cache keys affected:**
- `dentalos:invite_rate:{user_id}`: INCR — rate limit

**Cache TTL:** Rate limit: 3600s.

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | email.user_invite | { email, name, role, invite_url, clinic_name, invited_by_name, expires_at } | Al crear invitacion exitosamente |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** user_invite
- **PHI involved:** No

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | user_invite | invitado (email) | Al crear invitacion |

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Redis para rate limiting
- **Cache key:** `dentalos:invite_rate:{user_id}`
- **TTL:** 3600s
- **Invalidation:** Auto-expira por TTL

### Database Performance

**Queries executed:** 4-5 (check user exists, check invite exists, count users, count invites, insert invite)

**Indexes required:**
- `{schema}.user_invites.lower(email)` — INDEX
- `{schema}.user_invites.status` — INDEX
- `{schema}.users.lower(email)` — UNIQUE
- `{schema}.users.is_active` — INDEX

**N+1 prevention:** No aplica.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| email | Pydantic EmailStr, lowercase, strip | Prevenir inyeccion |
| name | strip_tags, max length | Prevenir XSS |
| role | Pydantic Literal validator | Solo valores permitidos |

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
1. Invitacion exitosa de doctor
   - **Given:** clinic_owner autenticado, plan con espacio para mas usuarios
   - **When:** POST /api/v1/auth/invite con email nuevo, role="doctor", name valido
   - **Then:** 201 Created, invitacion creada con status='pending', email encolado

2. Invitacion exitosa de receptionist
   - **Given:** clinic_owner autenticado
   - **When:** POST /api/v1/auth/invite con role="receptionist"
   - **Then:** 201 Created

3. Re-invitacion despues de invitacion expirada
   - **Given:** Invitacion previa para "test@email.com" con status='expired'
   - **When:** POST /api/v1/auth/invite con mismo email
   - **Then:** 201 Created, nueva invitacion creada

#### Edge Cases
1. Invitacion con email de usuario inactivo
   - **Given:** Existe usuario inactivo con email "viejo@email.com" en el tenant
   - **When:** POST /api/v1/auth/invite con ese email
   - **Then:** 201 Created (usuario inactivo no cuenta)

2. Limite de plan al borde
   - **Given:** Plan max_users=3, actualmente 2 usuarios activos + 0 invitaciones pendientes
   - **When:** POST /api/v1/auth/invite
   - **Then:** 201 Created (3/3 incluyendo nueva invitacion)

#### Error Cases
1. Usuario no es clinic_owner
   - **Given:** Doctor autenticado
   - **When:** POST /api/v1/auth/invite
   - **Then:** 403 con insufficient_role

2. Email ya registrado en tenant
   - **Given:** Usuario activo con email "existente@email.com" en el tenant
   - **When:** POST /api/v1/auth/invite con ese email
   - **Then:** 409 con user_already_exists

3. Invitacion pendiente activa
   - **Given:** Invitacion pendiente no expirada para "pendiente@email.com"
   - **When:** POST /api/v1/auth/invite con ese email
   - **Then:** 409 con invite_already_pending

4. Limite de plan excedido
   - **Given:** Plan max_users=3, ya hay 3 usuarios activos
   - **When:** POST /api/v1/auth/invite
   - **Then:** 422 con plan_limit_reached

5. Rol no permitido (clinic_owner)
   - **Given:** clinic_owner intenta invitar con role="clinic_owner"
   - **When:** POST /api/v1/auth/invite
   - **Then:** 422 con invalid_role

6. Rol no permitido (patient)
   - **Given:** role="patient"
   - **When:** POST /api/v1/auth/invite
   - **Then:** 422 con invalid_role

### Test Data Requirements

**Users:** Un clinic_owner. Un doctor (para test de permisos). Usuarios existentes para test de duplicados.

**Plans:** Plan free (max_users=3), plan professional (max_users=10).

**Invites:** Una invitacion pendiente activa, una expirada.

### Mocking Strategy

- **Redis:** fakeredis para rate limiting
- **RabbitMQ:** Mock — verificar payload del email encolado
- **SHA-256:** No mockear (determinista)

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Solo clinic_owner puede crear invitaciones
- [ ] Roles permitidos: doctor, assistant, receptionist
- [ ] Email duplicado en tenant retorna 409
- [ ] Invitacion pendiente activa retorna 409
- [ ] Limite de plan verificado (usuarios activos + invitaciones pendientes)
- [ ] Token de invitacion generado y almacenado como hash
- [ ] Email de invitacion encolado con URL correcta
- [ ] Invitacion creada con expires_at = now() + 7 dias
- [ ] Audit log registrado
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Aceptacion de invitacion (ver auth/accept-invite.md)
- Revocacion de invitacion (ver users/revoke-invite.md)
- Listado de invitaciones (ver users/list-invites.md)
- Re-envio de email de invitacion (post-MVP)
- Invitacion de pacientes al portal (flujo separado)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (Privileged, clinic_owner)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (auth domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match database-architecture.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Privileged)
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for invite creation

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
