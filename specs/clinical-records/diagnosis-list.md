# Listar Diagnosticos del Paciente (CR-08)

---

## Overview

**Feature:** Lista los diagnosticos de un paciente con filtros por estado, rango de fechas y codigo CIE-10. Retorna informacion completa del diagnostico incluyendo descripcion oficial del catalogo, diente involucrado, severidad, estado, doctor y fecha.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-07 (diagnosis-create.md), CR-10 (cie10-search.md), infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** La recepcionista NO tiene acceso a diagnosticos (contienen informacion clinica sensible). Toda lectura es auditada.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/diagnoses
```

**Rate Limiting:**
- 120 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:diagnoses_read:{user_id}`

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
| status | No | string | Enum: active, resolved, all. Default: active | Filtrar por estado | active |
| date_from | No | string | Formato YYYY-MM-DD | Inicio del rango de fechas de creacion | 2026-01-01 |
| date_to | No | string | Formato YYYY-MM-DD | Fin del rango de fechas de creacion | 2026-02-28 |
| cie10_code | No | string | Codigo CIE-10 exacto | Filtrar por codigo CIE-10 | K02.1 |
| tooth_number | No | integer | Rango 11-48 (FDI) | Filtrar por diente afectado | 16 |

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
      "cie10_code": "string",
      "cie10_description": "string — descripcion oficial en espanol",
      "custom_description": "string | null — descripcion adicional del doctor",
      "tooth_number": "integer | null",
      "tooth_notation_fdi": "string | null",
      "severity": "string — mild | moderate | severe",
      "status": "string — active | resolved",
      "notes": "string | null",
      "doctor": {
        "id": "UUID",
        "name": "string"
      },
      "created_at": "ISO8601 datetime",
      "resolved_at": "ISO8601 datetime | null",
      "resolved_by": {
        "id": "UUID",
        "name": "string"
      }
    }
  ],
  "summary": {
    "total": "integer — total de diagnosticos (con filtros)",
    "active_count": "integer",
    "resolved_count": "integer"
  },
  "filters_applied": {
    "status": "string",
    "date_from": "string | null",
    "date_to": "string | null",
    "cie10_code": "string | null",
    "tooth_number": "integer | null"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "dx_d9e8f7a6-b5c4-3210-fedc-ba9876543210",
      "cie10_code": "K02.1",
      "cie10_description": "Caries de la dentina",
      "custom_description": "Caries de la dentina en diente 16 con cavidad oclusal",
      "tooth_number": 16,
      "tooth_notation_fdi": "16",
      "severity": "moderate",
      "status": "active",
      "notes": "Caries oclusal profunda. Requiere radiografia periapical.",
      "doctor": {
        "id": "usr_doctor_001",
        "name": "Dra. Ana Martinez"
      },
      "created_at": "2026-02-24T10:30:00Z",
      "resolved_at": null,
      "resolved_by": null
    },
    {
      "id": "dx_e1f2a3b4-c5d6-7890-ef12-345678901234",
      "cie10_code": "K05.1",
      "cie10_description": "Gingivitis cronica",
      "custom_description": null,
      "tooth_number": null,
      "tooth_notation_fdi": null,
      "severity": "mild",
      "status": "active",
      "notes": null,
      "doctor": {
        "id": "usr_doctor_001",
        "name": "Dra. Ana Martinez"
      },
      "created_at": "2026-01-15T09:00:00Z",
      "resolved_at": null,
      "resolved_by": null
    }
  ],
  "summary": {
    "total": 2,
    "active_count": 2,
    "resolved_count": 0
  },
  "filters_applied": {
    "status": "active",
    "date_from": null,
    "date_to": null,
    "cie10_code": null,
    "tooth_number": null
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Parametros de query invalidos.

```json
{
  "error": "invalid_input",
  "message": "Los parametros de busqueda no son validos.",
  "details": {
    "status": ["Estado invalido. Opciones: active, resolved, all."],
    "tooth_number": ["El numero de diente debe estar entre 11 y 48 (FDI)."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 403 Forbidden
**When:** La recepcionista intenta acceder a diagnosticos.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para acceder a los diagnosticos del paciente."
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

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al recuperar diagnosticos.

---

## Business Logic

**Step-by-step process:**

1. Validar parametros de URL y query con Pydantic.
2. Resolver tenant desde JWT. Verificar rol (doctor o assistant). Receptionist retorna 403.
3. Verificar que `patient_id` existe en el schema del tenant.
4. Construir query base: `SELECT * FROM diagnoses WHERE patient_id=patient_id AND tenant_id=tenant_id`.
5. Aplicar filtro de `status`:
   - `active`: WHERE status = 'active'
   - `resolved`: WHERE status = 'resolved'
   - `all`: sin filtro de status
   - Default: `active`
6. Aplicar filtros opcionales: `date_from`/`date_to` sobre `created_at`, `cie10_code` (exacto), `tooth_number`.
7. Calcular `summary.active_count` y `summary.resolved_count` via subquery o COUNT con GROUP BY (siempre sobre el total del paciente, no sobre los filtros aplicados).
8. Cargar doctor info via JOIN.
9. Ordenar por `created_at DESC`.
10. Registrar entrada de auditoria (action=list, resource=diagnoses, phi=true).
11. Retornar 200.

**Nota:** Este endpoint no es paginado — la cantidad de diagnosticos por paciente es tipicamente pequena (< 50). Si se detecta un paciente con mas de 100 diagnosticos activos en el futuro, se agrega paginacion como mejora.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| status | Enum: active, resolved, all | "Estado invalido. Opciones: active, resolved, all." |
| date_from | Formato YYYY-MM-DD | "Formato de fecha invalido. Use YYYY-MM-DD." |
| date_to | Formato YYYY-MM-DD | "Formato de fecha invalido. Use YYYY-MM-DD." |
| date_from + date_to | date_from <= date_to si ambos provistos | "La fecha de inicio no puede ser posterior a la fecha de fin." |
| cie10_code | String valido, maximo 10 chars | "Formato de codigo CIE-10 invalido." |
| tooth_number | Entero 11-48 si provisto | "El numero de diente debe estar entre 11 y 48 (FDI)." |

**Business Rules:**

- El filtro de `status` por default es `active` (muestra solo diagnosticos activos). Para ver historico completo, usar `status=all`.
- `summary.active_count` y `summary.resolved_count` son contadores del TOTAL de diagnosticos del paciente, independientemente de los filtros aplicados. Esto permite que el frontend siempre muestre el resumen completo.
- La recepcionista no tiene acceso a diagnosticos para proteger informacion clinica sensible que puede revelar condiciones medicas del paciente.
- Los diagnosticos se retornan ordenados por `created_at DESC` (mas recientes primero).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Paciente sin diagnosticos | `data: []`, `summary` con todos los contadores en 0 |
| Filtro cie10_code con codigo que no existe en el paciente | `data: []`, `summary` con contadores reales del paciente |
| status=all | Retorna activos y resueltos juntos, ordenados por fecha |
| date_from igual a date_to | Retorna diagnosticos del dia exacto |
| cie10_code en minusculas | Normalizar a mayusculas antes de filtrar |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_logs`: INSERT — entrada de auditoria de lectura

**Example query (SQLAlchemy):**
```python
stmt = (
    select(Diagnosis)
    .options(joinedload(Diagnosis.doctor))
    .where(
        Diagnosis.patient_id == patient_id,
        Diagnosis.tenant_id == tenant_id,
    )
)
if filters.status != "all":
    stmt = stmt.where(Diagnosis.status == filters.status)
if filters.date_from:
    stmt = stmt.where(Diagnosis.created_at >= filters.date_from)
if filters.date_to:
    stmt = stmt.where(Diagnosis.created_at <= filters.date_to)
if filters.cie10_code:
    stmt = stmt.where(Diagnosis.cie10_code == filters.cie10_code.upper())
if filters.tooth_number:
    stmt = stmt.where(Diagnosis.tooth_number == filters.tooth_number)
stmt = stmt.order_by(Diagnosis.created_at.desc())

# Summary query (siempre sobre el total del paciente)
summary_stmt = (
    select(
        func.count().filter(Diagnosis.status == "active").label("active_count"),
        func.count().filter(Diagnosis.status == "resolved").label("resolved_count"),
    )
    .where(Diagnosis.patient_id == patient_id, Diagnosis.tenant_id == tenant_id)
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:diagnoses:list:{hash(filters)}`: GET — cache del listado con filtros

**Cache TTL:** 120s (2 minutos; invalidado al crear o actualizar diagnosticos)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | diagnoses.list | { patient_id, user_id, role, filters, result_count, tenant_id, timestamp } | Siempre al listar |

### Audit Log

**Audit entry:** Yes

- **Action:** list
- **Resource:** diagnoses
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms
- **Maximum acceptable:** < 250ms

### Caching Strategy
- **Strategy:** Redis cache con TTL de 2 minutos
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:diagnoses:list:{hash(filters)}`
- **TTL:** 120s
- **Invalidation:** Al crear (CR-07) o actualizar (CR-09) cualquier diagnostico del paciente

### Database Performance

**Queries executed:** 2 (1 para listado con filtros + 1 para summary counts)

**Indexes required:**
- `diagnoses.(patient_id, tenant_id, status)` — INDEX compuesto
- `diagnoses.(patient_id, tenant_id, created_at DESC)` — INDEX para ordenamiento
- `diagnoses.cie10_code` — INDEX para filtro por codigo
- `diagnoses.tooth_number` — INDEX para filtro por diente

**N+1 prevention:** Doctor info cargada con `joinedload` en la query principal.

### Pagination

**Pagination:** No (tipicamente < 50 diagnosticos por paciente en MVP)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | Prevenir inyeccion |
| status | Pydantic Literal enum | Prevenir valores arbitrarios |
| cie10_code | Pydantic str + uppercase + strip | Normalizar formato |
| tooth_number | Pydantic int, rango 11-48 | Prevenir valores fuera de rango |
| date_from / date_to | Pydantic date | Prevenir inyeccion en fechas |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `cie10_code` + `cie10_description` (revela condicion medica), `tooth_number`, `notes`, `severity`

**Audit requirement:** All access logged — toda lectura de diagnosticos auditada.

---

## Testing

### Test Cases

#### Happy Path
1. Listar diagnosticos activos (default)
   - **Given:** Doctor autenticado, paciente con 3 diagnosticos activos y 2 resueltos
   - **When:** GET sin parametros de query
   - **Then:** 200 OK, 3 diagnosticos activos, summary muestra 3 activos y 2 resueltos

2. Filtrar por status=all
   - **Given:** Doctor autenticado, paciente con diagnosticos activos y resueltos
   - **When:** GET con status=all
   - **Then:** 200 OK, todos los diagnosticos (5), summary correcto

3. Filtrar por cie10_code
   - **Given:** Paciente con 2 diagnosticos K02.1 y 1 K05.1
   - **When:** GET con cie10_code=K02.1
   - **Then:** 200 OK, 2 diagnosticos retornados

4. Filtrar por tooth_number
   - **Given:** Paciente con diagnosticos en dientes variados
   - **When:** GET con tooth_number=16
   - **Then:** Solo diagnosticos del diente 16

#### Edge Cases
1. Paciente sin diagnosticos
   - **Given:** Paciente sin diagnosticos
   - **When:** GET del listado
   - **Then:** 200 OK, `data: []`, todos los contadores en 0

2. cie10_code en minusculas en query
   - **Given:** Diagnostico K02.1 existente
   - **When:** GET con cie10_code=k02.1
   - **Then:** 200 OK, diagnostico encontrado (normalizado)

#### Error Cases
1. Recepcionista intenta acceder
   - **Given:** Usuario con rol receptionist
   - **When:** GET del endpoint
   - **Then:** 403 Forbidden

2. Paciente inexistente
   - **Given:** patient_id que no existe
   - **When:** GET del listado
   - **Then:** 404 Not Found

3. status con valor invalido
   - **Given:** Doctor autenticado
   - **When:** GET con status=pending (no valido)
   - **Then:** 400 Bad Request con detalle

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista (para probar 403)

**Patients/Entities:** Paciente con 5 diagnosticos (3 activos, 2 resueltos), en dientes variados y con codigos CIE-10 variados

### Mocking Strategy

- **Redis:** fakeredis para cache en unit tests
- **Audit service:** Mock que verifica llamada con PHI=true

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Listado de diagnosticos retornado con todos los campos definidos
- [ ] Filtro de status funciona (active, resolved, all); default=active
- [ ] Filtros de date_range, cie10_code, tooth_number funcionan correctamente
- [ ] summary siempre muestra contadores del total del paciente (no solo de los filtros)
- [ ] Recepcionista recibe 403 (no tiene acceso a diagnosticos)
- [ ] Auditoria registrada en cada listado
- [ ] Cache de 2min funcional; invalidado al crear/actualizar diagnosticos
- [ ] All test cases pass
- [ ] Performance targets met (< 250ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Obtener detalle individual de un diagnostico (agregar GET /diagnoses/{id} si es necesario en el futuro)
- Crear diagnosticos (ver CR-07)
- Actualizar estado de diagnosticos (ver CR-09)
- Busqueda full-text sobre notas de diagnosticos (post-MVP)
- Exportar diagnosticos a PDF

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models con summary)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (doctor + assistant; NO receptionist)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (doctor + assistant; receptionist bloqueada)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail para diagnosticos clinicos

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 250ms)
- [x] Caching strategy stated (2min TTL)
- [x] DB queries optimized (indexes compuestos)
- [x] Pagination: no requerida en MVP (tipicamente < 50 por paciente)

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
