# Patient Referral (P-15)

---

## Overview

**Feature:** Gestionar referidos inter-especialistas dentro de la misma clinica. Un doctor puede referir a un paciente a otro especialista del mismo tenant, ambos pueden agregar notas clinicas, el especialista receptor acepta el referido y al completar el tratamiento ambos firman digitalmente. Incluye el endpoint de creacion (POST) y de listado (GET) de referidos de un paciente.

**Domain:** patients

**Priority:** High

**Dependencies:** users (tabla `users` con roles y especialidades), patients (tabla `patients`), digital-signatures (firma digital conforme Ley 527/1999 Colombia), notifications (notificacion in-app y email al doctor receptor), I-02 (authentication-rules.md), database-architecture.md (`referrals`, `referral_notes`, `referral_signatures`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** doctor (solo) para creacion. Para listado: doctor, assistant, clinic_owner.
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:**
  - Un doctor no puede referirse a si mismo (`from_doctor_id != to_doctor_id`).
  - El doctor receptor (`to_doctor_id`) debe pertenecer al mismo tenant.
  - Solo doctores pueden crear referidos; los asistentes pueden listar pero no crear.

---

## Endpoints

### Crear Referido

```
POST /api/v1/patients/{patient_id}/referrals
```

### Listar Referidos del Paciente

```
GET /api/v1/patients/{patient_id}/referrals
```

**Rate Limiting:**
- POST: 30 requests por minuto por usuario
- GET: Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes (POST) | string | Formato de request | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | UUID v4 valido | ID del paciente que se refiere | pt_550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters (solo para GET)

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| status | No | enum | pending, accepted, in_progress, completed, cancelled | Filtrar por estado | pending |
| page | No | integer | >= 1, default: 1 | Pagina actual | 1 |
| page_size | No | integer | 1–50, default: 10 | Registros por pagina | 10 |

### Request Body Schema (POST)

```json
{
  "to_doctor_id": "UUID (required) — ID del especialista receptor",
  "reason": "string (required) — motivo clinico del referido, max 2000 chars",
  "priority": "string (required) — enum: urgent | normal | low",
  "specialty": "string (required) — enum: ortodoncia | endodoncia | periodoncia | rehabilitacion | cirugia | otro",
  "notes": "string (optional) — notas adicionales del doctor remitente, max 2000 chars"
}
```

**Example Request (POST):**
```json
{
  "to_doctor_id": "usr_660e8400-e29b-41d4-a716-446655440001",
  "reason": "Paciente presenta lesion periapical en diente 21. Requiere valoracion endodontica y posible tratamiento de conductos. RX adjunta en historia clinica.",
  "priority": "normal",
  "specialty": "endodoncia",
  "notes": "Paciente con alta sensibilidad a anestesia lidocaina. Usar articaina."
}
```

---

## Response

### Success Response — POST

**Status:** 201 Created

**Schema:**
```json
{
  "id": "UUID",
  "patient_id": "UUID",
  "from_doctor": {
    "id": "UUID",
    "name": "string",
    "specialty": "string"
  },
  "to_doctor": {
    "id": "UUID",
    "name": "string",
    "specialty": "string"
  },
  "reason": "string",
  "priority": "urgent | normal | low",
  "specialty": "string",
  "status": "pending",
  "notes": [
    {
      "id": "UUID",
      "author_id": "UUID",
      "author_name": "string",
      "text": "string",
      "created_at": "ISO8601"
    }
  ],
  "signatures": [],
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Example (POST 201):**
```json
{
  "id": "ref_1a2b3c4d-e5f6-7890-abcd-ef0123456789",
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "from_doctor": {
    "id": "usr_550e8400-e29b-41d4-a716-446655440000",
    "name": "Dra. Ana Martinez",
    "specialty": "Odontologia General"
  },
  "to_doctor": {
    "id": "usr_660e8400-e29b-41d4-a716-446655440001",
    "name": "Dr. Carlos Gomez",
    "specialty": "Endodoncia"
  },
  "reason": "Paciente presenta lesion periapical en diente 21.",
  "priority": "normal",
  "specialty": "endodoncia",
  "status": "pending",
  "notes": [
    {
      "id": "rn_aabb1122-ccdd-3344-eeff-556677889900",
      "author_id": "usr_550e8400-e29b-41d4-a716-446655440000",
      "author_name": "Dra. Ana Martinez",
      "text": "Paciente con alta sensibilidad a anestesia lidocaina. Usar articaina.",
      "created_at": "2026-02-24T10:00:00Z"
    }
  ],
  "signatures": [],
  "created_at": "2026-02-24T10:00:00Z",
  "updated_at": "2026-02-24T10:00:00Z"
}
```

### Success Response — GET (Listado)

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "UUID",
      "from_doctor": { "id": "UUID", "name": "string", "specialty": "string" },
      "to_doctor": { "id": "UUID", "name": "string", "specialty": "string" },
      "reason": "string",
      "priority": "string",
      "specialty": "string",
      "status": "string",
      "notes_count": "integer",
      "signatures_count": "integer",
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }
  ],
  "pagination": {
    "page": "integer",
    "page_size": "integer",
    "total": "integer",
    "total_pages": "integer"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Campo requerido faltante, enum invalido o auto-referido.

**Example:**
```json
{
  "error": "self_referral_not_allowed",
  "message": "No puedes crear un referido hacia ti mismo."
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol no autorizado para crear referidos (`assistant`, `receptionist`, `clinic_owner`). O paciente de otro tenant.

```json
{
  "error": "forbidden",
  "message": "Solo los medicos pueden crear referidos entre especialistas."
}
```

#### 404 Not Found
**When:** `patient_id` no existe en el tenant, o `to_doctor_id` no existe en el tenant.

```json
{
  "error": "doctor_not_found",
  "message": "El especialista receptor no fue encontrado en esta clinica."
}
```

#### 409 Conflict
**When:** Ya existe un referido `pending` o `accepted` del mismo doctor al mismo especialista para el mismo paciente en la misma especialidad.

```json
{
  "error": "referral_already_active",
  "message": "Ya existe un referido activo de endodoncia para este paciente con el Dr. Carlos Gomez."
}
```

#### 422 Unprocessable Entity
**When:** `to_doctor_id` existe pero pertenece a otro tenant.

```json
{
  "error": "validation_failed",
  "message": "El especialista receptor no pertenece a esta clinica.",
  "details": {
    "to_doctor_id": ["El doctor debe ser parte del mismo tenant."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al crear el referido o al encolar notificacion.

---

## Business Logic

**Step-by-step process (POST — crear referido):**

1. Validar JWT y extraer `tenant_id`, `user_id` (= `from_doctor_id`), `role`.
2. Verificar que el rol sea `doctor`. Si no, retornar 403.
3. Validar body con Pydantic: campos requeridos, enums correctos, max lengths.
4. Verificar que `to_doctor_id != user_id`. Si son iguales, retornar 400 con `self_referral_not_allowed`.
5. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
6. Verificar que el doctor receptor (`to_doctor_id`) existe en `users` del mismo tenant y tiene `role = 'doctor'`. Si no existe en el tenant, 404. Si existe pero es de otro tenant, 422.
7. Verificar unicidad: `SELECT 1 FROM referrals WHERE patient_id = :patient_id AND to_doctor_id = :to_doctor_id AND specialty = :specialty AND status IN ('pending', 'accepted', 'in_progress')`. Si existe, 409.
8. Iniciar transaccion.
9. Insertar en `referrals`:
   - `from_doctor_id = user_id`
   - `to_doctor_id` del body
   - `status = 'pending'`
   - `reason`, `priority`, `specialty` del body
10. Si `notes` viene en el body: insertar en `referral_notes` con `author_id = user_id`.
11. Confirmar transaccion.
12. Encolar job en RabbitMQ (`notifications.referral_created`) para notificar al doctor receptor (in-app + email).
13. Registrar en audit log: `patients.referral.created`.
14. Retornar 201 Created con el referido completo.

**Step-by-step process (GET — listar referidos):**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `doctor`, `assistant` o `clinic_owner`. Si no, 403.
3. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
4. Aplicar filtros de query (status, paginacion).
5. Query: referidos donde `patient_id = :patient_id` + JOIN con usuarios (`from_doctor`, `to_doctor`) para obtener nombres.
6. Retornar 200 con lista paginada y conteos de notas y firmas.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| to_doctor_id | UUID v4, existe en tenant, rol=doctor, diferente al usuario autenticado | "El especialista receptor no fue encontrado." / "No puedes referirte a ti mismo." |
| reason | Requerido, max 2000 chars | "El motivo del referido es obligatorio." |
| priority | Enum: urgent, normal, low | "La prioridad debe ser: urgent, normal o low." |
| specialty | Enum: ortodoncia, endodoncia, periodoncia, rehabilitacion, cirugia, otro | "La especialidad no es valida." |
| notes | Max 2000 chars | "Las notas no pueden superar los 2000 caracteres." |

**Business Rules:**

- Solo doctores del mismo tenant pueden participar en un referido.
- El flujo de estados del referido es: `pending` → `accepted` → `in_progress` → `completed` (o `cancelled` en cualquier punto).
- Al completar el referido, ambos doctores (remitente y receptor) deben agregar firma digital (ver digital-signatures spec).
- Ambos doctores pueden agregar notas clinicas en cualquier momento mientras el referido no este `completed` o `cancelled`.
- El doctor receptor acepta el referido via un endpoint separado (PATCH /referrals/{id}/accept — fuera de esta spec).
- Los referidos son parte de la historia clinica del paciente — acceso protegido por tenant.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor receptor no tiene especialidad en el sistema | Permitido: la `specialty` del referido describe lo requerido, no el perfil del doctor |
| Referido previo completado o cancelado para mismo duo | Permitido crear nuevo referido (no conflicto con estados terminales) |
| Paciente con muchos referidos activos | No hay limite de referidos activos por paciente; cada uno con diferente especialista/especialidad puede coexistir |
| Doctor remitente es tambien receptor en otro referido del mismo paciente | Permitido: los roles de remitente/receptor son independientes por referido |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `referrals`: INSERT — nuevo referido con status pending
- `referral_notes`: INSERT (condicional) — nota inicial si `notes` viene en body

**Example query (SQLAlchemy):**
```python
from sqlalchemy import insert, select

async with session.begin():
    # Verificar existencia de doctor receptor en tenant
    doctor_check = await session.execute(
        select(User.id).where(
            User.id == body.to_doctor_id,
            User.tenant_id == tenant_id,
            User.role == "doctor",
            User.is_active == True,
        )
    )
    if not doctor_check.scalar_one_or_none():
        raise DoctorNotFoundException()

    # Insertar referido
    referral_result = await session.execute(
        insert(Referral).values(
            patient_id=patient_id,
            tenant_id=tenant_id,
            from_doctor_id=user_id,
            to_doctor_id=body.to_doctor_id,
            reason=body.reason,
            priority=body.priority,
            specialty=body.specialty,
            status="pending",
        ).returning(Referral.id)
    )
    referral_id = referral_result.scalar_one()

    # Insertar nota inicial si existe
    if body.notes:
        await session.execute(
            insert(ReferralNote).values(
                referral_id=referral_id,
                author_id=user_id,
                text=body.notes,
            )
        )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:referrals:*`: DELETE (invalidacion de cache de listado)

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications.referral_created | referral_notify | { referral_id, patient_id, patient_name, from_doctor_id, from_doctor_name, to_doctor_id, to_doctor_email, reason_preview, priority, specialty, tenant_id } | Al crear referido exitosamente |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** referral
- **PHI involved:** Yes (el referido incluye razon clinica y datos del paciente)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | referral_received | Doctor receptor (to_doctor) | Al crear referido |
| email | referral_notification | Doctor receptor (email del usuario) | Al crear referido |

---

## Performance

### Expected Response Time
- **Target:** < 400ms
- **Maximum acceptable:** < 1000ms (incluye verificaciones multi-tabla y encolado)

### Caching Strategy
- **Strategy:** No se cachea el referido individual. El listado puede cachearse por 5 minutos.
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:referrals:{filter_hash}`
- **TTL:** 300s (5 minutos)
- **Invalidation:** Al crear, actualizar o cancelar un referido del paciente

### Database Performance

**Queries executed (POST):** 5 (verificar paciente, verificar doctor receptor, verificar unicidad, insert referral, insert nota)

**Indexes required:**
- `referrals.patient_id` — INDEX
- `referrals.tenant_id` — INDEX
- `referrals.(patient_id, to_doctor_id, specialty, status)` — INDEX COMPUESTO para verificacion de unicidad
- `referrals.from_doctor_id` — INDEX
- `referral_notes.referral_id` — INDEX

**N+1 prevention:** Para el listado, datos de doctores (nombre, especialidad) cargados con JOIN en una sola query.

### Pagination

**Pagination:** Yes (GET)

- **Style:** offset-based
- **Default page size:** 10
- **Max page size:** 50

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID | |
| to_doctor_id | Pydantic UUID | |
| reason | Pydantic str, strip, max_length=2000, bleach | PHI — puede contener diagnostico |
| notes | Pydantic str, strip, max_length=2000, bleach | PHI — notas clinicas |
| priority | Pydantic Enum | |
| specialty | Pydantic Enum | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Campos `reason` y `notes` sanitizados con bleach (strip HTML). Serializacion Pydantic para respuesta.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `reason` (motivo clinico), `notes` (notas clinicas del doctor) — ambos contienen informacion de salud del paciente.

**Audit requirement:** All access logged — creacion y lectura de referidos auditados por contener PHI clinica.

---

## Testing

### Test Cases

#### Happy Path
1. Crear referido a endodoncista con motivo y nota
   - **Given:** Dra. Martinez (doctor, tenant A) y Dr. Gomez (doctor, tenant A), paciente activo
   - **When:** POST /api/v1/patients/{id}/referrals con `to_doctor_id`, `reason`, `specialty: "endodoncia"`, `priority: "normal"`, `notes`
   - **Then:** 201 Created, `status: "pending"`, nota inicial en `notes[]`, job encolado para notificar a Dr. Gomez

2. Listar referidos del paciente (GET)
   - **Given:** Paciente con 3 referidos (1 pending, 1 accepted, 1 completed), usuario `doctor`
   - **When:** GET /api/v1/patients/{id}/referrals
   - **Then:** 200 OK, `total: 3`, datos de ambos doctores en cada referido

3. Filtrar referidos por status
   - **Given:** Paciente con referidos en distintos estados
   - **When:** GET /api/v1/patients/{id}/referrals?status=pending
   - **Then:** 200 OK, solo referidos con `status: "pending"`

4. Assistant puede listar referidos
   - **Given:** Usuario con rol `assistant`
   - **When:** GET /api/v1/patients/{id}/referrals
   - **Then:** 200 OK

#### Edge Cases
1. Referido previo completado no bloquea nuevo referido
   - **Given:** Referido previo entre mismos doctores y misma especialidad en `status: "completed"`
   - **When:** POST nuevo referido con mismos datos
   - **Then:** 201 Created (referidos en estados terminales no generan conflicto)

2. Body sin campo `notes` opcional
   - **Given:** Doctor crea referido sin notas adicionales
   - **When:** POST sin campo `notes`
   - **Then:** 201 Created, `notes: []`

#### Error Cases
1. Auto-referido (doctor se refiere a si mismo)
   - **Given:** `to_doctor_id` es el mismo que el usuario autenticado
   - **When:** POST /api/v1/patients/{id}/referrals
   - **Then:** 400 Bad Request con `self_referral_not_allowed`

2. Doctor receptor de otro tenant
   - **Given:** `to_doctor_id` existe pero pertenece a tenant B
   - **When:** POST desde tenant A
   - **Then:** 404 Not Found (no revelar que existe en otro tenant)

3. Referido activo duplicado
   - **Given:** Referido `pending` ya existe entre mismos actores y especialidad
   - **When:** POST identico
   - **Then:** 409 Conflict con descripcion del referido existente

4. Rol no autorizado para crear (assistant)
   - **Given:** Usuario con rol `assistant`
   - **When:** POST /api/v1/patients/{id}/referrals
   - **Then:** 403 Forbidden

5. Specialty invalido
   - **Given:** `specialty: "implantes"` (fuera del enum)
   - **When:** POST
   - **Then:** 422 Unprocessable Entity

### Test Data Requirements

**Users:** Dos doctores del tenant A (remitente y receptor), un doctor del tenant B, un assistant del tenant A, un receptionist.

**Patients:** Un paciente activo del tenant A.

**Referrals:** Ninguno inicialmente (estado limpio), mas referidos seeded para tests de listado y conflicto.

### Mocking Strategy

- **RabbitMQ:** Mock del publisher — verificar payload del job de notificacion
- **Redis:** fakeredis para rate limiting e invalidacion de cache
- **Database:** SQLite en memoria con esquema de referidos

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST crea referido en estado `pending` y retorna 201 con datos completos
- [ ] Auto-referido rechazado con 400 (`self_referral_not_allowed`)
- [ ] Doctor de otro tenant retorna 404
- [ ] Referido activo duplicado retorna 409
- [ ] Notificacion al doctor receptor encolada en RabbitMQ
- [ ] GET lista referidos del paciente con paginacion
- [ ] Filtro por `status` funciona correctamente
- [ ] Assistant puede listar pero no crear (403 en POST)
- [ ] PHI (reason, notes) auditado en access log
- [ ] All test cases pass
- [ ] Performance targets met (< 1000ms POST)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Aceptacion/rechazo del referido por el doctor receptor (PATCH /referrals/{id}/accept)
- Agregar notas al referido despues de creado (POST /referrals/{id}/notes)
- Firma digital al completar el referido (POST /referrals/{id}/sign — ver digital-signatures spec)
- Cancelacion de referido
- Referidos externos (a especialistas fuera del tenant)
- Historial de cambios de estado del referido

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas para POST y GET)
- [x] All outputs defined (response models para creacion y listado)
- [x] API contract defined (OpenAPI compatible, 2 endpoints documentados)
- [x] Validation rules stated
- [x] Error cases enumerated (incluyendo auto-referido, cross-tenant, duplicate)
- [x] Auth requirements explicit (doctor-only para POST, doctor/assistant/owner para GET)
- [x] Side effects listed (DB, queue, audit log PHI)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (patients domain)
- [x] Uses tenant schema isolation (doctor receptor validado en mismo tenant)
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (bleach para campos PHI: reason, notes)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] PHI identificado y auditado (reason y notes contienen informacion clinica)
- [x] Audit trail para creacion y lectura (PHI requerido)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 1000ms POST)
- [x] Caching strategy stated (listado cacheado 5min)
- [x] DB queries optimizados (indexes listados, JOIN para nombres de doctores)
- [x] Pagination para GET (offset-based, max 50)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, patient_id, referral_id incluidos)
- [x] Audit log entries defined (create, PHI=Yes)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (notificaciones al doctor receptor)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error, incluyendo ambos endpoints)
- [x] Test data requirements specified
- [x] Mocking strategy para RabbitMQ y Redis
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
