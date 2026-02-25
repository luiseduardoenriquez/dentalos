# Listar Registros Clinicos (CR-03)

---

## Overview

**Feature:** Lista los registros clinicos de un paciente con soporte de filtros por tipo, rango de fechas, doctor y numero de diente. Paginado por cursor (default 20 items). Retorna resumen (sin contenido completo) ordenado por fecha descendente.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-01 (record-create.md), CR-02 (record-get.md), infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant, receptionist
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** La recepcionista tiene acceso de solo lectura. Toda lectura de PHI es auditada.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/clinical-records
```

**Rate Limiting:**
- 120 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:clinical_records_read:{user_id}`

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto desde JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | Debe existir en el tenant | ID del paciente | 550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| type | No | string | Enum: anamnesis, examination, evolution_note, procedure | Filtrar por tipo de registro | evolution_note |
| date_from | No | string | Formato ISO8601 date | Inicio del rango de fechas | 2026-01-01 |
| date_to | No | string | Formato ISO8601 date | Fin del rango de fechas | 2026-02-28 |
| doctor_id | No | UUID | Debe ser doctor activo en el tenant | Filtrar por doctor | usr_doctor_001 |
| tooth_number | No | integer | Rango 11-48 (FDI) | Filtrar por numero de diente | 16 |
| cursor | No | string | Opaque cursor del response anterior | Cursor para paginacion | eyJpZCI6ImNy... |
| limit | No | integer | 1-100, default 20 | Cantidad de items por pagina | 20 |

### Request Body Schema

N/A (GET request)

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "UUID",
      "type": "string",
      "summary": "string — primeros 150 chars del contenido o descripcion corta generada",
      "appointment_id": "UUID | null",
      "tooth_numbers": "array<integer>",
      "diagnosis_count": "integer",
      "attachment_count": "integer",
      "doctor": {
        "id": "UUID",
        "name": "string"
      },
      "created_at": "ISO8601 datetime",
      "updated_at": "ISO8601 datetime",
      "is_editable": "boolean"
    }
  ],
  "pagination": {
    "next_cursor": "string | null — null si no hay mas paginas",
    "has_more": "boolean",
    "total_count": "integer — total de registros con los filtros aplicados"
  },
  "filters_applied": {
    "type": "string | null",
    "date_from": "string | null",
    "date_to": "string | null",
    "doctor_id": "UUID | null",
    "tooth_number": "integer | null"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "cr_f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "type": "evolution_note",
      "summary": "Paciente refiere dolor leve en cuadrante superior derecho. Sensibilidad a percusion en diente 16...",
      "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "tooth_numbers": [16],
      "diagnosis_count": 1,
      "attachment_count": 1,
      "doctor": {
        "id": "usr_doctor_001",
        "name": "Dra. Ana Martinez"
      },
      "created_at": "2026-02-24T10:30:00Z",
      "updated_at": "2026-02-24T10:30:00Z",
      "is_editable": true
    },
    {
      "id": "cr_b9d2e1a3-4567-89ab-cdef-012345678901",
      "type": "examination",
      "summary": "Examen clinico inicial. Diente 38 semierupcionado con pericoronitis leve.",
      "appointment_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "tooth_numbers": [38],
      "diagnosis_count": 2,
      "attachment_count": 0,
      "doctor": {
        "id": "usr_doctor_001",
        "name": "Dra. Ana Martinez"
      },
      "created_at": "2026-02-10T09:00:00Z",
      "updated_at": "2026-02-10T09:00:00Z",
      "is_editable": false
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6ImNyX2I5ZDJlMWEzIiwiY3JlYXRlZF9hdCI6IjIwMjYtMDItMTBUMDk6MDA6MDBaIn0=",
    "has_more": true,
    "total_count": 47
  },
  "filters_applied": {
    "type": null,
    "date_from": null,
    "date_to": null,
    "doctor_id": null,
    "tooth_number": null
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Parametros de query invalidos (fecha mal formateada, tooth_number fuera de rango, limit fuera de rango).

```json
{
  "error": "invalid_input",
  "message": "Los parametros de busqueda no son validos.",
  "details": {
    "date_from": ["Formato de fecha invalido. Use YYYY-MM-DD."],
    "tooth_number": ["El numero de diente debe estar entre 11 y 48 (FDI)."],
    "limit": ["El limite debe ser entre 1 y 100."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** El usuario no tiene permiso para ver registros clinicos.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para acceder a registros clinicos."
}
```

#### 404 Not Found
**When:** `patient_id` no existe en el tenant.

```json
{
  "error": "not_found",
  "message": "El paciente especificado no existe."
}
```

#### 422 Unprocessable Entity
**When:** `date_from` es posterior a `date_to`.

```json
{
  "error": "validation_failed",
  "message": "El rango de fechas es invalido.",
  "details": {
    "date_range": ["La fecha de inicio no puede ser posterior a la fecha de fin."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado al recuperar los registros.

---

## Business Logic

**Step-by-step process:**

1. Validar parametros de URL y query con Pydantic.
2. Resolver tenant desde JWT. Verificar rol del usuario (doctor, assistant, receptionist).
3. Verificar que `patient_id` existe en el schema del tenant.
4. Construir query base sobre `clinical_records` filtrando por `patient_id` y `tenant_id`.
5. Aplicar filtros opcionales: `type`, `date_from`/`date_to` (sobre `created_at`), `doctor_id`, `tooth_number` (JOIN con `clinical_record_teeth`).
6. Si `cursor` provisto: decodificar cursor (base64 JSON con `id` y `created_at`) y agregar condicion `WHERE (created_at, id) < (cursor_created_at, cursor_id)` (keyset pagination).
7. Ordenar por `created_at DESC, id DESC`.
8. Limitar a `limit + 1` resultados (para detectar si hay mas paginas).
9. Si se obtienen `limit + 1` resultados: hay mas paginas (`has_more=true`), retornar solo `limit` items y generar `next_cursor` del ultimo item.
10. Para cada registro: generar `summary` (primeros 150 caracteres del contenido textual o descripcion del tipo).
11. Calcular `is_editable` para cada registro.
12. Calcular `total_count` con COUNT query separado (con mismos filtros, sin limit/cursor).
13. Registrar entrada de auditoria (action=list, resource=clinical_records, phi=true).
14. Retornar 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| type | Enum opcional: anamnesis, examination, evolution_note, procedure | "Tipo de registro invalido." |
| date_from | Formato ISO8601 date (YYYY-MM-DD) | "Formato de fecha invalido. Use YYYY-MM-DD." |
| date_to | Formato ISO8601 date (YYYY-MM-DD) | "Formato de fecha invalido. Use YYYY-MM-DD." |
| date_from + date_to | date_from <= date_to | "La fecha de inicio no puede ser posterior a la fecha de fin." |
| tooth_number | Entero entre 11 y 48 | "El numero de diente debe estar entre 11 y 48 (FDI)." |
| limit | Entero entre 1 y 100, default 20 | "El limite debe ser entre 1 y 100." |
| cursor | String base64 valido si provisto | "El cursor de paginacion es invalido." |

**Business Rules:**

- El listado NO retorna el `content` completo del registro. Para el contenido completo, usar CR-02 (record-get).
- El `summary` se genera extrayendo texto plano del `content` (removiendo keys JSON, tomando primeros 150 chars).
- La paginacion es keyset/cursor-based para eficiencia en tablas grandes. No se usa offset.
- El `total_count` refleja el total de registros con los filtros aplicados, no el total global del paciente.
- Los registros de tipo `anamnesis` pueden aparecer en el listado como cualquier otro tipo.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Paciente sin registros clinicos | `data: []`, `pagination.total_count: 0`, `has_more: false` |
| Filtro con 0 resultados | `data: []`, `pagination.total_count: 0` |
| cursor invalido o manipulado | Retornar 400 con "El cursor de paginacion es invalido." |
| date_from y date_to iguales | Retornar registros del dia exacto |
| limit=1 | Retornar 1 registro, next_cursor si hay mas |
| doctor_id que no existe en tenant | Retornar lista vacia (el filtro aplica igual; no retornar 404 por doctor_id) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_logs`: INSERT — entrada de auditoria de lectura de listado PHI

**Example query (SQLAlchemy):**
```python
stmt = (
    select(ClinicalRecord)
    .outerjoin(ClinicalRecordTooth, ClinicalRecordTooth.clinical_record_id == ClinicalRecord.id)
    .options(joinedload(ClinicalRecord.doctor))
    .where(
        ClinicalRecord.patient_id == patient_id,
        ClinicalRecord.tenant_id == tenant_id,
    )
)
if filters.type:
    stmt = stmt.where(ClinicalRecord.type == filters.type)
if filters.date_from:
    stmt = stmt.where(ClinicalRecord.created_at >= filters.date_from)
if filters.date_to:
    stmt = stmt.where(ClinicalRecord.created_at <= filters.date_to)
if filters.doctor_id:
    stmt = stmt.where(ClinicalRecord.doctor_id == filters.doctor_id)
if filters.tooth_number:
    stmt = stmt.where(ClinicalRecordTooth.tooth_number == filters.tooth_number)
if cursor:
    stmt = stmt.where(
        tuple_(ClinicalRecord.created_at, ClinicalRecord.id) < (cursor.created_at, cursor.id)
    )
stmt = stmt.order_by(ClinicalRecord.created_at.desc(), ClinicalRecord.id.desc()).limit(limit + 1)
results = await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:clinical_records:list`: GET — lectura desde cache si disponible

**Cache TTL:** 60 segundos (listados tienen TTL corto; se invalida al crear/actualizar registros)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | clinical_records.list | { patient_id, user_id, role, filters, tenant_id, result_count, timestamp } | Siempre al listar |

### Audit Log

**Audit entry:** Yes

- **Action:** list
- **Resource:** clinical_records
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 350ms

### Caching Strategy
- **Strategy:** Redis cache con TTL corto; cache key incluye filtros y cursor para evitar colisiones
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:clinical_records:list:{hash(filters+cursor+limit)}`
- **TTL:** 60s
- **Invalidation:** Al crear (CR-01) o actualizar (CR-04) cualquier registro del paciente

### Database Performance

**Queries executed:** 2 (1 query paginada + 1 COUNT para total_count)

**Indexes required:**
- `clinical_records.(patient_id, tenant_id, created_at DESC)` — INDEX compuesto para ordenamiento
- `clinical_records.type` — INDEX
- `clinical_records.doctor_id` — INDEX
- `clinical_records.(created_at, id)` — INDEX compuesto para keyset pagination
- `clinical_record_teeth.tooth_number` — INDEX

**N+1 prevention:** Doctor info cargada con `joinedload`. Counts de diagnoses y attachments calculados con subconsultas o columnas precalculadas.

### Pagination

**Pagination:** Yes

- **Style:** cursor-based (keyset pagination)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | Prevenir inyeccion |
| type | Pydantic Literal enum | Prevenir valores arbitrarios |
| date_from / date_to | Pydantic date | Prevenir inyeccion en fechas |
| doctor_id | Pydantic UUID, optional | Prevenir inyeccion |
| tooth_number | Pydantic int, rango 11-48 | Prevenir valores fuera de rango |
| cursor | Base64 decode + JSON parse validado | Prevenir cursor poisoning |
| limit | Pydantic int, rango 1-100 | Prevenir DoS por limit enorme |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `summary` (extracto del contenido clinico), `tooth_numbers`, `diagnosis_count` (puede revelar condicion medica indirectamente)

**Audit requirement:** All access logged — toda lectura de PHI auditada incluyendo listados.

---

## Testing

### Test Cases

#### Happy Path
1. Listar registros sin filtros
   - **Given:** Paciente con 5 registros clinicos, doctor autenticado
   - **When:** GET /api/v1/patients/{pid}/clinical-records
   - **Then:** 200 OK, 5 registros en data (o 20 si hay mas), paginacion correcta

2. Filtrar por tipo
   - **Given:** Paciente con 3 evolution_note y 2 examination
   - **When:** GET con type=evolution_note
   - **Then:** 200 OK, solo 3 registros de tipo evolution_note

3. Paginacion con cursor
   - **Given:** Paciente con 25 registros, limit=10
   - **When:** Primera pagina sin cursor, segunda pagina con next_cursor
   - **Then:** Primera pagina: 10 items, has_more=true. Segunda pagina: 10 items, has_more=true. Tercera: 5 items, has_more=false

4. Filtrar por tooth_number
   - **Given:** Registros con dientes variados
   - **When:** GET con tooth_number=16
   - **Then:** Solo registros que incluyen diente 16

#### Edge Cases
1. Paciente sin registros
   - **Given:** Paciente nuevo sin registros
   - **When:** GET del listado
   - **Then:** 200 OK, `data: []`, `total_count: 0`

2. Cursor invalido
   - **Given:** Cursor manipulado o malformado
   - **When:** GET con cursor invalido
   - **Then:** 400 con mensaje de error de cursor

3. date_from posterior a date_to
   - **Given:** date_from=2026-03-01, date_to=2026-01-01
   - **When:** GET con esos parametros
   - **Then:** 422 con error de rango de fechas

#### Error Cases
1. Paciente inexistente
   - **Given:** patient_id que no existe en el tenant
   - **When:** GET del listado
   - **Then:** 404 Not Found

2. Rol sin permiso
   - **Given:** Usuario con rol no permitido
   - **When:** GET del listado
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista activa

**Patients/Entities:** Paciente con al menos 25 registros de tipos variados y dientes variados, para pruebas de paginacion y filtros

### Mocking Strategy

- **Redis:** fakeredis para cache en unit tests
- **Audit service:** Mock que verifica que se llama con los parametros correctos

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Listado retorna registros correctamente sin filtros
- [ ] Todos los filtros funcionan correctamente (type, date_range, doctor_id, tooth_number)
- [ ] Paginacion cursor-based funciona (next_cursor, has_more, total_count)
- [ ] `summary` generado correctamente (primeros 150 chars del contenido)
- [ ] `is_editable` calculado correctamente para cada registro
- [ ] Auditoria registrada en cada listado
- [ ] Cache con TTL 60s funcional; invalidado al crear/actualizar registros
- [ ] Filtros combinados funcionan correctamente
- [ ] All test cases pass
- [ ] Performance targets met (< 350ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Obtener el contenido completo de un registro (ver CR-02)
- Busqueda full-text sobre el contenido de registros (post-MVP)
- Exportacion de registros a PDF (ver admin/export.md)
- Listado de procedimientos (ver CR-13)
- Listado de diagnosticos (ver CR-08)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed, keyset pagination)
- [x] Pagination applied (cursor-based)

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
