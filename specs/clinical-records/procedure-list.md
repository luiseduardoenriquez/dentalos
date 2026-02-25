# Listar Procedimientos del Paciente (CR-13)

---

## Overview

**Feature:** Lista los procedimientos completados para un paciente con filtros por rango de fechas, doctor, codigo CUPS y numero de diente. Paginado con cursor. Retorna resumen con datos clave por procedimiento incluyendo costo si esta disponible desde el modulo de facturacion.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-12 (procedure-create.md), CR-11 (cups-search.md), infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** La recepcionista NO tiene acceso a listado de procedimientos clinicos. Toda lectura es auditada (PHI).

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/procedures
```

**Rate Limiting:**
- 120 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:procedures_read:{user_id}`

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
| date_from | No | string | Formato YYYY-MM-DD | Inicio del rango de fechas | 2026-01-01 |
| date_to | No | string | Formato YYYY-MM-DD | Fin del rango de fechas | 2026-02-28 |
| doctor_id | No | UUID | Doctor activo en el tenant | Filtrar por doctor que realizo el procedimiento | usr_doctor_001 |
| cups_code | No | string | Codigo CUPS exacto | Filtrar por tipo de procedimiento | 89.01.02.01 |
| tooth_number | No | integer | Rango 11-48 (FDI) | Filtrar por diente tratado | 16 |
| cursor | No | string | Cursor opaco del response anterior | Cursor para paginacion | eyJpZCI6InBy... |
| limit | No | integer | 1-50, default 20 | Cantidad de items por pagina | 20 |

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
      "cups_code": "string",
      "cups_description": "string",
      "custom_description": "string | null",
      "tooth_number": "integer | null",
      "tooth_notation_fdi": "string | null",
      "zones": "array<string>",
      "doctor": {
        "id": "UUID",
        "name": "string"
      },
      "duration_minutes": "integer | null",
      "appointment_id": "UUID | null",
      "treatment_plan_item_id": "UUID | null",
      "has_evolution_note": "boolean",
      "cost": "number | null — costo del procedimiento si esta disponible en facturacion",
      "cost_currency": "string | null — ej: COP",
      "created_at": "ISO8601 datetime"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  },
  "filters_applied": {
    "date_from": "string | null",
    "date_to": "string | null",
    "doctor_id": "UUID | null",
    "cups_code": "string | null",
    "tooth_number": "integer | null"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "proc_e1f2a3b4-c5d6-7890-ef12-345678901234",
      "cups_code": "89.01.02.01",
      "cups_description": "Restauracion en resina compuesta de una superficie en diente permanente",
      "custom_description": "Restauracion clase I oclusal diente 16",
      "tooth_number": 16,
      "tooth_notation_fdi": "16",
      "zones": ["oclusal"],
      "doctor": {
        "id": "usr_doctor_001",
        "name": "Dra. Ana Martinez"
      },
      "duration_minutes": 45,
      "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "treatment_plan_item_id": "tpi_789abc12-3456-7890-abcd-ef1234567890",
      "has_evolution_note": true,
      "cost": 150000.00,
      "cost_currency": "COP",
      "created_at": "2026-02-24T11:00:00Z"
    },
    {
      "id": "proc_a2b3c4d5-e6f7-8901-ab23-456789012345",
      "cups_code": "89.13.01.01",
      "cups_description": "Exodoncia de diente permanente",
      "custom_description": null,
      "tooth_number": 38,
      "tooth_notation_fdi": "38",
      "zones": [],
      "doctor": {
        "id": "usr_doctor_001",
        "name": "Dra. Ana Martinez"
      },
      "duration_minutes": 30,
      "appointment_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "treatment_plan_item_id": null,
      "has_evolution_note": false,
      "cost": 80000.00,
      "cost_currency": "COP",
      "created_at": "2026-02-10T09:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "total_count": 2
  },
  "filters_applied": {
    "date_from": null,
    "date_to": null,
    "doctor_id": null,
    "cups_code": null,
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
    "date_from": ["Formato de fecha invalido. Use YYYY-MM-DD."],
    "tooth_number": ["El numero de diente debe estar entre 11 y 48 (FDI)."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 403 Forbidden
**When:** Rol sin acceso (receptionist).

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para acceder a los procedimientos del paciente."
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
**When:** Error inesperado al recuperar los procedimientos.

---

## Business Logic

**Step-by-step process:**

1. Validar parametros de URL y query con Pydantic.
2. Resolver tenant desde JWT. Verificar rol (doctor o assistant). Receptionist retorna 403.
3. Verificar que `patient_id` existe en el tenant.
4. Construir query base: `SELECT * FROM procedures WHERE patient_id=patient_id AND tenant_id=tenant_id`.
5. Aplicar filtros opcionales: `date_from`/`date_to` sobre `created_at`, `doctor_id`, `cups_code` (exacto), `tooth_number`.
6. Si `cursor` provisto: decodificar y aplicar keyset pagination (`WHERE (created_at, id) < (cursor_created_at, cursor_id)`).
7. Ordenar por `created_at DESC, id DESC`.
8. Limitar a `limit + 1` para detectar `has_more`.
9. Para cada procedimiento: verificar si tiene nota de evolucion asociada (`has_evolution_note`).
10. Para cada procedimiento: intentar obtener el costo desde el modulo de facturacion (join con `billing_items` o campo `cost` en `procedures`). Si no esta disponible: `cost: null`.
11. Calcular `total_count` con COUNT query separado.
12. Registrar entrada de auditoria (action=list, resource=procedures, phi=true).
13. Retornar 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| date_from | Formato YYYY-MM-DD | "Formato de fecha invalido." |
| date_to | Formato YYYY-MM-DD | "Formato de fecha invalido." |
| date_from + date_to | date_from <= date_to | "La fecha de inicio no puede ser posterior a la fecha de fin." |
| tooth_number | Entero 11-48 si provisto | "El numero de diente debe estar entre 11 y 48 (FDI)." |
| limit | Entero 1-50, default 20 | "El limite debe ser entre 1 y 50." |

**Business Rules:**

- La recepcionista no puede acceder al listado de procedimientos (contiene informacion clinica y de costo que es sensible).
- El campo `cost` se obtiene del modulo de facturacion. Si el procedimiento no tiene item de factura asociado, `cost: null`.
- El campo `has_evolution_note` es un boolean calculado (no retornar el contenido de la nota aqui — usar CR-14 para el detalle completo).
- Los procedimientos se ordenan por fecha descendente (mas recientes primero).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Paciente sin procedimientos | `data: []`, `total_count: 0`, `has_more: false` |
| Procedimiento sin costo en facturacion | `cost: null`, `cost_currency: null` |
| cups_code en minusculas | Normalizar antes de filtrar |
| doctor_id que no existe en el tenant | Retornar lista vacia (filtro aplica; no 404 por doctor_id) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_logs`: INSERT — entrada de auditoria de lectura

**Example query (SQLAlchemy):**
```python
stmt = (
    select(Procedure)
    .options(joinedload(Procedure.doctor))
    .where(
        Procedure.patient_id == patient_id,
        Procedure.tenant_id == tenant_id,
    )
)
if filters.date_from:
    stmt = stmt.where(Procedure.created_at >= filters.date_from)
if filters.date_to:
    stmt = stmt.where(Procedure.created_at <= filters.date_to)
if filters.doctor_id:
    stmt = stmt.where(Procedure.doctor_id == filters.doctor_id)
if filters.cups_code:
    stmt = stmt.where(Procedure.cups_code == filters.cups_code.upper())
if filters.tooth_number:
    stmt = stmt.where(Procedure.tooth_number == filters.tooth_number)
if cursor:
    stmt = stmt.where(
        tuple_(Procedure.created_at, Procedure.id) < (cursor.created_at, cursor.id)
    )
stmt = stmt.order_by(Procedure.created_at.desc(), Procedure.id.desc()).limit(limit + 1)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:procedures:list:{hash(filters+cursor+limit)}`: GET — lectura desde cache

**Cache TTL:** 120s (2 minutos; invalidado al crear procedimientos via CR-12)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | procedures.list | { patient_id, user_id, role, filters, result_count, tenant_id, timestamp } | Siempre al listar |

### Audit Log

**Audit entry:** Yes

- **Action:** list
- **Resource:** procedures
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 350ms

### Caching Strategy
- **Strategy:** Redis cache con TTL de 2 minutos
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:procedures:list:{hash(filters+cursor+limit)}`
- **TTL:** 120s
- **Invalidation:** Al crear procedimiento (CR-12)

### Database Performance

**Queries executed:** 2 (1 para listado con filtros + 1 COUNT para total)

**Indexes required:**
- `procedures.(patient_id, tenant_id, created_at DESC)` — INDEX compuesto para ordenamiento
- `procedures.doctor_id` — INDEX
- `procedures.cups_code` — INDEX
- `procedures.tooth_number` — INDEX
- `procedures.(created_at, id)` — INDEX compuesto para keyset pagination

**N+1 prevention:** Doctor info cargada con `joinedload`. `has_evolution_note` calculado con EXISTS subquery o LEFT JOIN COUNT.

### Pagination

**Pagination:** Yes

- **Style:** cursor-based (keyset pagination)
- **Default page size:** 20
- **Max page size:** 50

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | Prevenir inyeccion |
| cups_code | Pydantic str + uppercase + strip | Normalizar |
| tooth_number | Pydantic int, rango 11-48 | Prevenir valores fuera de rango |
| date_from / date_to | Pydantic date | Prevenir inyeccion |
| doctor_id | Pydantic UUID, optional | Prevenir inyeccion |
| cursor | Base64 decode + JSON validate | Prevenir cursor poisoning |
| limit | Pydantic int, rango 1-50 | Prevenir DoS |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `cups_code` + `cups_description` (revela procedimiento medico), `tooth_number`, `cost`

**Audit requirement:** All access logged — toda lectura auditada.

---

## Testing

### Test Cases

#### Happy Path
1. Listar procedimientos sin filtros
   - **Given:** Doctor autenticado, paciente con 3 procedimientos
   - **When:** GET /api/v1/patients/{pid}/procedures
   - **Then:** 200 OK, 3 procedimientos retornados con todos los campos

2. Filtrar por cups_code
   - **Given:** Paciente con procedimientos de tipos variados
   - **When:** GET con cups_code=89.01.02.01
   - **Then:** Solo restauraciones retornadas

3. Paginacion cursor-based
   - **Given:** Paciente con 30 procedimientos, limit=10
   - **When:** Primera y segunda pagina con cursor
   - **Then:** Paginacion correcta, has_more y next_cursor correctos

#### Edge Cases
1. Paciente sin procedimientos
   - **Given:** Paciente nuevo sin procedimientos
   - **When:** GET del listado
   - **Then:** 200 OK, `data: []`, `total_count: 0`

2. Procedimiento sin costo en facturacion
   - **Given:** Procedimiento sin item de factura
   - **When:** GET del listado
   - **Then:** `cost: null`, `cost_currency: null`

#### Error Cases
1. Recepcionista intenta acceder
   - **Given:** Usuario con rol receptionist
   - **When:** GET del endpoint
   - **Then:** 403 Forbidden

2. date_from posterior a date_to
   - **Given:** date_from=2026-03-01, date_to=2026-01-01
   - **When:** GET con esos parametros
   - **Then:** 422 con error de rango de fechas

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista (para probar 403)

**Patients/Entities:** Paciente con procedimientos variados (diferentes tipos, dientes, doctores), algunos con items de factura y otros sin

### Mocking Strategy

- **Redis:** fakeredis para cache en unit tests
- **Billing module:** Mock que retorna costo para algunos procedimientos y null para otros

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Listado de procedimientos retornado con todos los campos definidos
- [ ] Todos los filtros funcionan (date_range, doctor_id, cups_code, tooth_number)
- [ ] Paginacion cursor-based funciona correctamente
- [ ] `has_evolution_note` calculado correctamente para cada procedimiento
- [ ] `cost` retornado cuando esta disponible en facturacion, `null` cuando no
- [ ] Recepcionista recibe 403
- [ ] Auditoria registrada en cada listado
- [ ] Cache de 2min funcional; invalidado al crear procedimientos
- [ ] All test cases pass
- [ ] Performance targets met (< 350ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Detalle completo de un procedimiento (ver CR-14)
- Crear procedimientos (ver CR-12)
- Facturacion de procedimientos (ver billing/)
- Exportar listado de procedimientos a PDF

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models con cost y has_evolution_note)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (doctor + assistant; NO receptionist)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing module integrado como fuente de costo)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (doctor + assistant; receptionist bloqueada)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail para listados de PHI

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (2min TTL)
- [x] DB queries optimized (indexes compuestos, keyset pagination)
- [x] Pagination: cursor-based (max 50)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (billing mock)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
