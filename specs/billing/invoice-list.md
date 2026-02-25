# Invoice List (B-03)

---

## Overview

**Feature:** Listar facturas a nivel de tenant (endpoint global, no anidado bajo paciente). Soporta filtrado por estado, rango de fechas, paciente especifico, doctor responsable y metodo de pago. Paginacion cursor-based. Diseñado para la vista de gestion de facturacion del recepcionista y del `clinic_owner`, incluyendo el dashboard de cobros pendientes.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), patients (Patient), users (User), infra/authentication-rules.md, database-architecture.md (`invoices`, `invoice_items`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Los doctores solo ven facturas donde son el `doctor_id` asignado. Recepcionistas y `clinic_owner` ven todas las facturas del tenant. El rol `patient` no puede usar este endpoint global (debe usar B-02 nested bajo su perfil).

---

## Endpoint

```
GET /api/v1/invoices
```

**Rate Limiting:**
- Inherits global rate limit (100/min por usuario)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

N/A

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| status | No | string | draft, sent, paid, overdue, cancelled | Filtrar por estado de la factura | sent |
| patient_id | No | UUID | UUID v4 | Filtrar por paciente especifico | pt_550e8400... |
| doctor_id | No | UUID | UUID v4 | Filtrar por doctor responsable | usr_abc123... |
| date_from | No | string | ISO8601 date | Fecha de creacion desde (inclusivo) | 2026-01-01 |
| date_to | No | string | ISO8601 date | Fecha de creacion hasta (inclusivo) | 2026-01-31 |
| due_from | No | string | ISO8601 date | Fecha de vencimiento desde | 2026-02-01 |
| due_to | No | string | ISO8601 date | Fecha de vencimiento hasta | 2026-03-31 |
| overdue_only | No | boolean | true/false, default: false | Solo facturas vencidas con saldo | true |
| cursor | No | string | Opaque cursor string | Cursor para paginacion | eyJpZCI6IjEyMy4uLiJ9 |
| limit | No | integer | 1-100, default: 20 | Numero de resultados por pagina | 20 |
| sort | No | string | created_at, due_date, total, invoice_number | Campo de ordenamiento | due_date |
| order | No | string | asc, desc, default: desc | Direccion de ordenamiento | asc |

### Request Body Schema

N/A — GET request

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
      "invoice_number": "string",
      "patient_id": "UUID",
      "patient_name": "string",
      "doctor_id": "UUID | null",
      "doctor_name": "string | null",
      "status": "string",
      "currency": "string",
      "total": "integer — en centavos",
      "amount_paid": "integer — en centavos",
      "balance_due": "integer — en centavos",
      "due_date": "string — ISO8601 date",
      "sent_at": "ISO8601 | null",
      "paid_at": "ISO8601 | null",
      "created_at": "ISO8601",
      "item_count": "integer — numero de items en la factura"
    }
  ],
  "pagination": {
    "next_cursor": "string | null — null si es la ultima pagina",
    "has_more": "boolean",
    "limit": "integer"
  },
  "summary": {
    "total_count": "integer — total de facturas que cumplen los filtros",
    "total_outstanding": "integer — suma de balance_due de facturas no pagadas/canceladas, en centavos",
    "total_overdue": "integer — suma de balance_due de facturas overdue, en centavos",
    "currency": "string"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
      "invoice_number": "FAC-2026-00001",
      "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
      "patient_name": "Juan Carlos Perez Gomez",
      "doctor_id": "usr_550e8400-e29b-41d4-a716-446655440000",
      "doctor_name": "Dra. Maria Lopez Vargas",
      "status": "sent",
      "currency": "COP",
      "total": 162000000,
      "amount_paid": 80000000,
      "balance_due": 82000000,
      "due_date": "2026-03-31",
      "sent_at": "2026-02-25T10:00:00Z",
      "paid_at": null,
      "created_at": "2026-02-25T09:00:00Z",
      "item_count": 3
    },
    {
      "id": "inv_2b3c4d5e-f6a7-8901-bcde-f12345678901",
      "invoice_number": "FAC-2026-00002",
      "patient_id": "pt_661f9511-f3ac-52e5-b827-557766551111",
      "patient_name": "Ana Sofia Rodriguez Medina",
      "doctor_id": null,
      "doctor_name": null,
      "status": "overdue",
      "currency": "COP",
      "total": 45000000,
      "amount_paid": 0,
      "balance_due": 45000000,
      "due_date": "2026-01-31",
      "sent_at": "2026-01-25T14:00:00Z",
      "paid_at": null,
      "created_at": "2026-01-24T09:00:00Z",
      "item_count": 1
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6Imludl8yYjNjNGQ1ZS4uLiIsImNyZWF0ZWRfYXQiOiIyMDI2LTAxLTI0In0=",
    "has_more": true,
    "limit": 20
  },
  "summary": {
    "total_count": 47,
    "total_outstanding": 3250000000,
    "total_overdue": 450000000,
    "currency": "COP"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Parametros de query invalidos (fecha mal formateada, `status` no reconocido, `limit` fuera de rango, `date_from` > `date_to`).

**Example:**
```json
{
  "error": "invalid_query_params",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "status": ["El estado 'archivado' no es valido. Valores permitidos: draft, sent, paid, overdue, cancelled."],
    "date_from": ["La fecha de inicio no puede ser posterior a la fecha de fin."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol `patient` o `assistant` intentando acceder al endpoint global.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para listar facturas del tenant."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado al construir la query o serializar la respuesta.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `clinic_owner`, `receptionist` o `doctor`. Si no, retornar 403.
3. Validar query params con schema Pydantic:
   - `status` debe ser uno de los valores del enum de estados.
   - `date_from` <= `date_to` si ambos se proveen.
   - `due_from` <= `due_to` si ambos se proveen.
   - `limit` entre 1 y 100.
   - `sort` es uno de los campos permitidos.
4. Construir la query base:
   - `WHERE invoices.tenant_id = :tenant_id`
5. Si el rol es `doctor`: agregar filtro `WHERE invoices.doctor_id = :user_doctor_id` (doctores solo ven sus propias facturas). Ignorar el parametro `doctor_id` de query si se provee (o verificar que coincida con el propio).
6. Aplicar filtros opcionales:
   - `status`: `WHERE invoices.status = :status`
   - `patient_id`: `WHERE invoices.patient_id = :patient_id` (verificar que pertenece al tenant)
   - `doctor_id` (solo si rol != doctor): `WHERE invoices.doctor_id = :doctor_id`
   - `date_from`/`date_to`: `WHERE invoices.created_at BETWEEN :date_from AND :date_to`
   - `due_from`/`due_to`: `WHERE invoices.due_date BETWEEN :due_from AND :due_to`
   - `overdue_only=true`: `WHERE invoices.status IN ('sent', 'overdue') AND invoices.due_date < CURRENT_DATE AND invoices.balance_due > 0`
7. Antes de paginar, calcular el `summary` con un COUNT y SUM en la misma query filtrada (o subquery separada para performance):
   - `total_count`: COUNT de facturas que cumplen filtros.
   - `total_outstanding`: SUM de `balance_due` WHERE `status NOT IN ('paid', 'cancelled')`.
   - `total_overdue`: SUM de `balance_due` WHERE `status = 'overdue'`.
8. Aplicar paginacion cursor-based:
   - Si `cursor` se provee: decodificar (base64 JSON) para obtener `last_id` y `last_sort_value`.
   - Query con `WHERE (sort_field, id) > (last_sort_value, last_id)` (keyset pagination).
   - Si no hay cursor: query desde el inicio.
9. Aplicar ordenamiento `ORDER BY {sort} {order}, id {order}` (doble para determinismo).
10. Aplicar `LIMIT = limit + 1` para detectar si hay mas paginas.
11. Si se obtienen `limit + 1` resultados: hay mas paginas. Remover el ultimo item. Generar `next_cursor` del penultimo item (base64 JSON con id y sort_value).
12. JOIN con `patients` para obtener `patient_name` (nombre completo).
13. LEFT JOIN con `users` para obtener `doctor_name`.
14. Registrar en log estructurado: `billing.invoices.listed` con `tenant_id`, `user_id`, `filters_applied`, `result_count`.
15. Retornar 200 OK con `data`, `pagination` y `summary`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| status | Enum: draft, sent, paid, overdue, cancelled | "Estado invalido. Valores: draft, sent, paid, overdue, cancelled." |
| patient_id | UUID v4 valido si se provee | "El formato del ID de paciente no es valido." |
| doctor_id | UUID v4 valido si se provee | "El formato del ID de doctor no es valido." |
| date_from, date_to | ISO8601 date, date_from <= date_to | "La fecha de inicio no puede ser posterior a la de fin." |
| limit | Integer 1-100 | "El limite debe estar entre 1 y 100." |
| sort | Enum: created_at, due_date, total, invoice_number | "Campo de ordenamiento invalido." |
| order | Enum: asc, desc | "Direccion de ordenamiento invalida." |

**Business Rules:**

- El endpoint es global (no anidado bajo paciente) para soportar el dashboard de cobranza del recepcionista.
- Los doctores tienen una vista restringida: solo ven facturas donde son el doctor asignado.
- El `summary` siempre refleja la totalidad de los filtros aplicados, no solo la pagina actual.
- Las facturas vencidas (`overdue`) se detectan dinamicamente: `status IN ('sent')` y `due_date < hoy` y `balance_due > 0`. El endpoint puede hacer lazy update de status en la query o en procesamiento post-query.
- El campo `balance_due` en la lista es el valor persistido en DB (actualizado por B-07 en cada pago).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Sin filtros aplicados | Retorna todas las facturas del tenant paginadas |
| `limit` no especificado | Default 20 |
| Tenant sin facturas | `data: []`, `summary.total_count: 0`, `pagination.has_more: false` |
| `overdue_only=true` + `status=paid` | 400: filtros contradictorios |
| Doctor filtrando por otro `doctor_id` | Se ignora el filtro, retorna solo las suyas |
| Cursor expirado o manipulado | 400 con mensaje sobre cursor invalido |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:** Ninguna (solo lectura). Posible lazy update de `status` a `overdue` en lote si se implementa actualizacion en procesamiento.

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select, func
from sqlalchemy.orm import aliased

PatientAlias = aliased(Patient)
DoctorAlias = aliased(User)

stmt = (
    select(
        Invoice,
        func.concat(PatientAlias.first_name, " ", PatientAlias.last_name).label("patient_name"),
        func.concat(DoctorAlias.first_name, " ", DoctorAlias.last_name).label("doctor_name"),
    )
    .join(PatientAlias, Invoice.patient_id == PatientAlias.id)
    .outerjoin(DoctorAlias, Invoice.doctor_id == DoctorAlias.id)
    .where(Invoice.tenant_id == tenant_id)
)

if filters.status:
    stmt = stmt.where(Invoice.status == filters.status)
if filters.patient_id:
    stmt = stmt.where(Invoice.patient_id == filters.patient_id)
if filters.date_from:
    stmt = stmt.where(Invoice.created_at >= filters.date_from)
if filters.date_to:
    stmt = stmt.where(Invoice.created_at <= filters.date_to)
if role == "doctor":
    stmt = stmt.where(Invoice.doctor_id == user_doctor_id)

stmt = stmt.order_by(sort_col, Invoice.id).limit(limit + 1)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:invoice_list:{hash_of_filters}`: SET — cache de pagina de resultados

**Cache TTL:** 2 minutos (datos de listado cambian frecuentemente con pagos y nuevas facturas)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno.

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** invoice_list
- **PHI involved:** No (lista financiera con nombres de pacientes — PII)

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 200ms (con cache o query optimizada)
- **Maximum acceptable:** < 600ms (sin cache, filtros complejos, muchas facturas)

### Caching Strategy
- **Strategy:** Cache de paginas de resultados por combinacion de filtros (hash del query string)
- **Cache key:** `tenant:{tenant_id}:invoice_list:{sha256(sorted_query_params)}`
- **TTL:** 2 minutos
- **Invalidation:** En cualquier INSERT/UPDATE de factura en el tenant

### Database Performance

**Queries executed:** 2 (una para summary/count, una para la pagina paginada con JOINs)

**Indexes required:**
- `invoices.tenant_id` — INDEX
- `invoices.status` — INDEX
- `invoices.patient_id` — INDEX
- `invoices.doctor_id` — INDEX
- `invoices.created_at` — INDEX
- `invoices.due_date` — INDEX
- `invoices.(tenant_id, status, due_date)` — INDEX COMPUESTO para filtro overdue
- `invoices.(tenant_id, created_at)` — INDEX COMPUESTO para paginacion por fecha

**N+1 prevention:** JOINs en la query principal. Sin cargar items individuales (solo `item_count` via subquery o campo desnormalizado).

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset pagination)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| status | Pydantic Enum estricto | |
| patient_id | Pydantic UUID | |
| doctor_id | Pydantic UUID | |
| date_from, date_to | Pydantic date | |
| due_from, due_to | Pydantic date | |
| limit | Pydantic int, ge=1, le=100 | |
| cursor | Base64 decode + JSON parse con validacion | No confiar en contenido del cursor |
| sort | Pydantic Enum de campos permitidos | Previene column injection |
| order | Pydantic Enum: asc, desc | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con columnas de sort en Enum controlado. No se usa el valor de `sort` directamente como string en SQL.

### XSS Prevention

**Output encoding:** Serializacion Pydantic. Nombres de pacientes y doctores escapados.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Nombre del paciente (PII). No hay datos clinicos.

**Audit requirement:** All access logged (listado de datos financieros con PII)

---

## Testing

### Test Cases

#### Happy Path
1. Listar todas las facturas sin filtros (clinic_owner)
   - **Given:** 10 facturas en el tenant en distintos estados
   - **When:** GET /api/v1/invoices (sin query params)
   - **Then:** 200 OK, hasta 20 resultados, `summary.total_count: 10`, paginacion correcta

2. Filtrar por estado `overdue`
   - **Given:** 3 facturas overdue, 7 en otros estados
   - **When:** GET /api/v1/invoices?status=overdue
   - **Then:** 200 OK, `data` con 3 facturas, `summary.total_outstanding` = suma de balance_due

3. Filtrar por patient_id
   - **Given:** 5 facturas para el paciente A, 5 para el paciente B
   - **When:** GET /api/v1/invoices?patient_id={patient_A_id}
   - **Then:** 200 OK, solo facturas del paciente A

4. Doctor ve solo sus facturas
   - **Given:** 10 facturas, 4 asignadas al doctor X, 6 a otros
   - **When:** GET /api/v1/invoices con JWT del doctor X
   - **Then:** 200 OK, solo 4 facturas del doctor X

5. Paginacion cursor-based
   - **Given:** 50 facturas en el tenant
   - **When:** GET /api/v1/invoices?limit=10, luego con cursor de la respuesta
   - **Then:** Primera pagina: 10 facturas, `has_more: true`. Segunda pagina: siguientes 10.

#### Edge Cases
1. Tenant sin facturas
   - **Given:** Tenant nuevo sin facturas
   - **When:** GET /api/v1/invoices
   - **Then:** 200 OK, `data: []`, `summary.total_count: 0`, `has_more: false`

2. Rango de fechas sin resultados
   - **Given:** Sin facturas en el rango especificado
   - **When:** GET /api/v1/invoices?date_from=2020-01-01&date_to=2020-12-31
   - **Then:** 200 OK, `data: []`, `summary.total_count: 0`

3. Limite maximo
   - **Given:** 200 facturas en el tenant
   - **When:** GET /api/v1/invoices?limit=100
   - **Then:** 200 OK, 100 resultados, `has_more: true`

#### Error Cases
1. Estado invalido
   - **Given:** Query `?status=archivado`
   - **When:** GET
   - **Then:** 400 Bad Request con valores permitidos

2. date_from posterior a date_to
   - **Given:** `?date_from=2026-12-01&date_to=2026-01-01`
   - **When:** GET
   - **Then:** 400 Bad Request

3. Rol patient accede al endpoint global
   - **Given:** JWT con rol `patient`
   - **When:** GET /api/v1/invoices
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `doctor` (con facturas asignadas), un `patient` (para 403).

**Patients:** 3 pacientes con facturas en distintos estados.

**Invoices:** 15-20 facturas distribuidas entre estados (draft, sent, paid, overdue, cancelled) y pacientes.

**Payments:** Varios pagos parciales para probar `amount_paid` y `balance_due`.

### Mocking Strategy

- **Redis:** fakeredis para cache de listado
- **Database:** SQLite en memoria con datos de seed para billing
- **Date:** Mockear `date.today()` para probar facturas vencidas

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Listado global de facturas por tenant funciona sin filtros
- [ ] Todos los filtros (status, patient_id, doctor_id, fechas, overdue_only) funcionan individualmente y en combinacion
- [ ] Paginacion cursor-based retorna resultados correctos y consistentes
- [ ] `summary` refleja totales del conjunto completo (no solo la pagina)
- [ ] Doctores solo ven sus propias facturas
- [ ] Rol `patient` retorna 403
- [ ] Cache de 2 minutos implementado
- [ ] Ordenamiento por los 4 campos permitidos funciona
- [ ] All test cases pass
- [ ] Performance targets met (< 600ms sin cache)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Detalle de factura individual (ver B-02 invoice-get.md)
- Exportacion de listado a CSV o Excel (post-MVP)
- Filtro por metodo de pago en la lista de facturas
- Busqueda por numero de factura (implementar como filtro adicional post-MVP)
- Facturas de multiples clinicas para un doctor multi-tenant (se maneja por cambio de tenant)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (todos los query params con tipos y restricciones)
- [x] All outputs defined (response con data, pagination y summary)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (restriccion por rol doctor)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain, endpoint global)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, Pydantic query params)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (rol doctor restringido a sus facturas)
- [x] Input sanitization (Enum para sort, evita column injection)
- [x] SQL injection prevented (SQLAlchemy ORM, sort via Enum)
- [x] PII nombres en respuesta — logged
- [x] Audit trail para listado

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 600ms)
- [x] Caching strategy (2min por pagina de filtros)
- [x] DB queries optimizados (JOINs, indexes, keyset pagination)
- [x] Pagination cursor-based implementada

### Hook 5: Observability
- [x] Structured logging (filtros aplicados y resultado_count incluidos)
- [x] Audit log entries defined (read list)
- [x] Error tracking (Sentry-compatible)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (Redis, date, seed data)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
