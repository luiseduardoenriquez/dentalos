# Payment List (B-08)

---

## Overview

**Feature:** Listar todos los pagos realizados por un paciente especifico a traves de todas sus facturas. Proporciona un historial financiero completo del paciente con agrupacion opcional por factura, filtro por metodo de pago y rango de fechas. Util para la vista de historial de cobros del recepcionista y para que el paciente vea sus comprobantes en el portal.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-07 (payment-record.md), B-01 (invoice-create.md), patients (Patient), infra/authentication-rules.md, database-architecture.md (`payments`, `invoices`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor, patient
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Un paciente (rol `patient`) solo puede ver sus propios pagos. Los doctores pueden ver pagos de sus pacientes asignados. Recepcionistas y `clinic_owner` ven todos los pagos del tenant filtrados por paciente.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/payments
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

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | UUID v4 valido | ID del paciente | pt_550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| method | No | string | cash, credit_card, debit_card, bank_transfer, insurance, payment_plan | Filtrar por metodo de pago | bank_transfer |
| date_from | No | string | ISO8601 date | Fecha de pago desde (inclusivo) | 2026-01-01 |
| date_to | No | string | ISO8601 date | Fecha de pago hasta (inclusivo) | 2026-01-31 |
| invoice_id | No | UUID | UUID v4 | Filtrar pagos de una factura especifica | inv_1a2b3c4d... |
| cursor | No | string | Opaque cursor string | Cursor para paginacion | eyJpZCI6IjEyMy4uLiJ9 |
| limit | No | integer | 1-100, default: 20 | Numero de resultados por pagina | 20 |
| sort | No | string | payment_date, amount, recorded_at | Campo de ordenamiento, default: payment_date | payment_date |
| order | No | string | asc, desc, default: desc | Direccion de ordenamiento | desc |

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
      "invoice_id": "UUID",
      "invoice_number": "string",
      "invoice_status": "string",
      "amount": "integer — en centavos",
      "method": "string",
      "payment_date": "string — ISO8601 date",
      "reference_number": "string | null",
      "notes": "string | null",
      "recorded_by_name": "string — nombre del usuario que registro el pago",
      "recorded_at": "ISO8601"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "limit": "integer"
  },
  "summary": {
    "total_paid": "integer — suma total de todos los pagos del paciente en centavos",
    "payment_count": "integer — numero total de pagos",
    "by_method": {
      "cash": "integer — suma en centavos",
      "credit_card": "integer",
      "debit_card": "integer",
      "bank_transfer": "integer",
      "insurance": "integer",
      "payment_plan": "integer"
    },
    "currency": "string — ISO 4217"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "pay_2222bbbb-3333-4444-5555-666677778888",
      "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
      "invoice_number": "FAC-2026-00001",
      "invoice_status": "paid",
      "amount": 82000000,
      "method": "cash",
      "payment_date": "2026-02-28",
      "reference_number": null,
      "notes": "Saldo cancelado.",
      "recorded_by_name": "Maria Gonzalez (Recepcion)",
      "recorded_at": "2026-02-28T09:00:00Z"
    },
    {
      "id": "pay_1111aaaa-2222-3333-4444-555566667777",
      "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
      "invoice_number": "FAC-2026-00001",
      "invoice_status": "paid",
      "amount": 80000000,
      "method": "bank_transfer",
      "payment_date": "2026-02-25",
      "reference_number": "TRF-20260225-001",
      "notes": "Primera cuota acordada.",
      "recorded_by_name": "Maria Gonzalez (Recepcion)",
      "recorded_at": "2026-02-25T11:30:00Z"
    }
  ],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "limit": 20
  },
  "summary": {
    "total_paid": 162000000,
    "payment_count": 2,
    "by_method": {
      "cash": 82000000,
      "credit_card": 0,
      "debit_card": 0,
      "bank_transfer": 80000000,
      "insurance": 0,
      "payment_plan": 0
    },
    "currency": "COP"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Parametros de query invalidos (method no reconocido, fechas mal formateadas, `date_from` > `date_to`, limit fuera de rango).

**Example:**
```json
{
  "error": "invalid_query_params",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "method": ["Metodo de pago no valido. Valores permitidos: cash, credit_card, debit_card, bank_transfer, insurance, payment_plan."],
    "date_from": ["La fecha de inicio no puede ser posterior a la fecha de fin."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol `patient` intentando ver pagos de otro paciente, o rol `assistant`.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver los pagos de este paciente."
}
```

#### 404 Not Found
**When:** `patient_id` no existe en el tenant.

```json
{
  "error": "patient_not_found",
  "message": "El paciente no fue encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado al consultar la base de datos.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea uno de: `clinic_owner`, `receptionist`, `doctor`, `patient`. Si es `assistant`, retornar 403.
3. Validar query params con schema Pydantic.
4. Verificar que el paciente existe en el tenant. Si no, 404.
5. Si rol es `patient`: verificar que `user.patient_id == patient_id`. Si no, 403.
6. Si rol es `doctor`: verificar que el paciente esta asignado al doctor (tabla `patient_doctors`). Si no, 403.
7. Construir query base:
   - `SELECT payments.*, invoices.invoice_number, invoices.status as invoice_status, CONCAT(users.first_name, ' ', users.last_name) as recorded_by_name`
   - `FROM payments`
   - `JOIN invoices ON payments.invoice_id = invoices.id`
   - `JOIN users ON payments.recorded_by = users.id`
   - `WHERE payments.patient_id = :patient_id AND payments.tenant_id = :tenant_id`
8. Aplicar filtros opcionales:
   - `method`: `WHERE payments.method = :method`
   - `date_from`/`date_to`: `WHERE payments.payment_date BETWEEN :date_from AND :date_to`
   - `invoice_id`: `WHERE payments.invoice_id = :invoice_id`
9. Calcular `summary` con COUNT y SUM sobre la query filtrada (antes de paginar):
   - `total_paid`: SUM de `payments.amount`
   - `payment_count`: COUNT
   - `by_method`: GROUP BY method, SUM amount
10. Aplicar paginacion cursor-based:
    - Si `cursor` se provee: decodificar para obtener `last_payment_date` y `last_id`.
    - Keyset: `WHERE (payment_date, id) < (last_date, last_id)` para orden desc.
11. Aplicar `ORDER BY {sort} {order}, id {order}`.
12. Aplicar `LIMIT = limit + 1` para detectar `has_more`.
13. Si se obtienen `limit + 1` resultados: generar `next_cursor` y remover el ultimo item.
14. Registrar en audit log: accion `read`, recurso `payment_list`, `tenant_id`, `user_id`, `patient_id`, `filter_count`.
15. Retornar 200 OK con `data`, `pagination` y `summary`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | UUID v4, pertenece al tenant | "El paciente no fue encontrado." |
| method | Enum de metodos de pago | "Metodo de pago no valido." |
| date_from | ISO8601 date | "Formato de fecha invalido." |
| date_to | ISO8601 date, >= date_from | "La fecha de fin no puede ser anterior a la de inicio." |
| invoice_id | UUID v4 valido si se provee | "El formato del ID de factura no es valido." |
| limit | Integer 1-100 | "El limite debe estar entre 1 y 100." |
| sort | Enum: payment_date, amount, recorded_at | "Campo de ordenamiento invalido." |

**Business Rules:**

- Los pagos son inmutables — este endpoint es solo de lectura.
- El `summary.by_method` siempre incluye todos los metodos (con 0 para los no usados) para facilitar visualizacion de graficos.
- El `summary` calcula sobre el conjunto completo filtrado, no solo la pagina actual.
- Los pagos se ordenan por defecto por `payment_date DESC` (mas recientes primero).
- El campo `recorded_by_name` muestra quien registro el pago (para transparencia con el paciente).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Paciente sin pagos | `data: []`, `summary.total_paid: 0`, `payment_count: 0`, todos los metodos en 0 |
| Filtro por invoice_id sin pagos | `data: []`, summary en 0 |
| Paciente con mas de 100 pagos | Paginacion correcta, `has_more: true` |
| sort=amount, order=asc | Primero los pagos de menor monto |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:** Ninguna (solo lectura).

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select, func

# Query base con JOINs
stmt = (
    select(
        Payment,
        Invoice.invoice_number,
        Invoice.status.label("invoice_status"),
        func.concat(User.first_name, " ", User.last_name).label("recorded_by_name"),
    )
    .join(Invoice, Payment.invoice_id == Invoice.id)
    .join(User, Payment.recorded_by == User.id)
    .where(Payment.patient_id == patient_id)
    .where(Payment.tenant_id == tenant_id)
)

if filters.method:
    stmt = stmt.where(Payment.method == filters.method)
if filters.date_from:
    stmt = stmt.where(Payment.payment_date >= filters.date_from)
if filters.date_to:
    stmt = stmt.where(Payment.payment_date <= filters.date_to)

# Summary query
summary_stmt = (
    select(
        func.sum(Payment.amount).label("total_paid"),
        func.count(Payment.id).label("payment_count"),
        Payment.method,
        func.sum(Payment.amount).label("method_total"),
    )
    .where(Payment.patient_id == patient_id)
    .where(Payment.tenant_id == tenant_id)
    .group_by(Payment.method)
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:payment_list:{patient_id}:{hash_of_filters}`: SET — cache de pagina de resultados

**Cache TTL:** 5 minutos (pagos son inmutables una vez registrados, pero pueden agregarse nuevos)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno.

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** payment_list
- **PHI involved:** No (datos financieros con PII del registrador)

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 200ms (con cache)
- **Maximum acceptable:** < 500ms (sin cache, con JOINs y summary)

### Caching Strategy
- **Strategy:** Cache de paginas de resultados por filtros
- **Cache key:** `tenant:{tenant_id}:payment_list:{patient_id}:{sha256(sorted_params)}`
- **TTL:** 5 minutos
- **Invalidation:** En cada nuevo pago registrado para el paciente (B-07)

### Database Performance

**Queries executed:** 2 (una para summary con GROUP BY, una para la pagina paginada con JOINs)

**Indexes required:**
- `payments.(patient_id, tenant_id)` — INDEX COMPUESTO (lookup principal)
- `payments.invoice_id` — INDEX
- `payments.payment_date` — INDEX
- `payments.method` — INDEX
- `payments.(patient_id, payment_date)` — INDEX COMPUESTO para paginacion

**N+1 prevention:** JOINs en query principal para invoice_number, invoice_status y recorded_by_name. Sin cargar objetos completos — solo campos necesarios.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset pagination por payment_date + id)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID | |
| method | Pydantic Enum estricto | |
| date_from, date_to | Pydantic date | |
| invoice_id | Pydantic UUID opcional | |
| limit | Pydantic int, ge=1, le=100 | |
| cursor | Base64 decode + JSON parse con validacion | |
| sort | Pydantic Enum de campos permitidos | Previene column injection |
| order | Pydantic Enum: asc, desc | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM. Columna de sort mapeada via Enum, nunca como string directo.

### XSS Prevention

**Output encoding:** Serializacion Pydantic. Nombres y notas escapados.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno. Datos de pago con PII del registrador (nombre del staff).

**Audit requirement:** All access logged (historial financiero del paciente)

---

## Testing

### Test Cases

#### Happy Path
1. Listar todos los pagos de un paciente
   - **Given:** 2 pagos para el paciente (TRF y cash), usuario `receptionist`
   - **When:** GET /api/v1/patients/{id}/payments
   - **Then:** 200 OK, 2 pagos retornados, `summary.total_paid` correcto, `by_method` correcto

2. Filtrar por metodo de pago
   - **Given:** 3 pagos (2 bank_transfer, 1 cash)
   - **When:** GET ?method=bank_transfer
   - **Then:** 2 pagos retornados, `summary` solo para bank_transfer

3. Filtrar por rango de fechas
   - **Given:** Pagos en enero y febrero 2026
   - **When:** GET ?date_from=2026-01-01&date_to=2026-01-31
   - **Then:** Solo pagos de enero

4. Paciente ve sus propios pagos (rol patient)
   - **Given:** JWT con rol `patient`, `patient_id` coincide
   - **When:** GET
   - **Then:** 200 OK con pagos del paciente, `recorded_by_name` visible

5. Filtrar por invoice_id especifico
   - **Given:** 2 facturas con pagos, filtrar por una sola
   - **When:** GET ?invoice_id={invoice_id}
   - **Then:** Solo pagos de esa factura, `invoice_number` en cada pago

#### Edge Cases
1. Paciente sin pagos
   - **Given:** Paciente activo sin historial de pagos
   - **When:** GET
   - **Then:** 200 OK, `data: []`, `summary.total_paid: 0`, todos `by_method` en 0

2. Paginacion con cursor
   - **Given:** 50 pagos para el paciente
   - **When:** GET ?limit=10, luego con cursor
   - **Then:** Paginacion correcta, datos consistentes entre paginas

3. summary con filtro de metodo
   - **Given:** 3 pagos: 2 cash (50k, 30k), 1 bank_transfer (80k)
   - **When:** GET ?method=cash
   - **Then:** `summary.total_paid: 80000000`, `by_method.cash: 80000000`, `by_method.bank_transfer: 0`

#### Error Cases
1. Paciente ve pagos de otro paciente (rol patient)
   - **Given:** JWT `patient` con `patient_id` diferente al de la URL
   - **When:** GET
   - **Then:** 403 Forbidden

2. Metodo invalido
   - **Given:** `?method=efectivo`
   - **When:** GET
   - **Then:** 400 Bad Request

3. patient_id inexistente
   - **Given:** UUID que no existe en el tenant
   - **When:** GET
   - **Then:** 404 Not Found

4. Rol `assistant`
   - **Given:** JWT con rol `assistant`
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `doctor`, un `patient` (vinculado), un `assistant` (para 403).

**Patients:** Un paciente con varios pagos, un paciente sin pagos.

**Payments:** 5-10 pagos con distintos metodos y fechas para el paciente de prueba.

**Invoices:** 2-3 facturas con pagos asociados.

### Mocking Strategy

- **Redis:** fakeredis para cache de listado
- **Database:** SQLite en memoria con datos de seed
- **Date:** Mockear `date.today()` para tests de filtro de fechas

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Lista todos los pagos del paciente con `invoice_number` e `invoice_status` incluidos
- [ ] Filtros por `method`, `date_from`/`date_to`, `invoice_id` funcionan correctamente
- [ ] `summary` con `total_paid`, `payment_count` y `by_method` correcto
- [ ] `by_method` incluye siempre todos los metodos (con 0 para los no usados)
- [ ] Paginacion cursor-based correcta
- [ ] Rol `patient` solo ve sus propios pagos
- [ ] Rol `assistant` retorna 403
- [ ] Cache de 5 minutos implementado
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms sin cache)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Registro de pagos (ver B-07 payment-record.md)
- Listado de pagos a nivel de tenant (sin filtro por paciente) — endpoints de reporte (B-13)
- Exportacion de historial de pagos a CSV
- Comprobante de pago individual en PDF

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (URL + query params con tipos y restricciones)
- [x] All outputs defined (data con pagos enriquecidos, pagination, summary)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (patient restriction, assistant forbidden)
- [x] Side effects listed (cache, audit)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, Pydantic query params)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated con restricciones por rol
- [x] Input sanitization (Enum para method y sort)
- [x] SQL injection prevented (SQLAlchemy ORM, sort via Enum)
- [x] Audit trail para lectura de historial financiero

### Hook 4: Performance & Scalability
- [x] Response time targets definidos
- [x] Cache de pagina por filtros (5min)
- [x] DB queries optimizados (JOINs, indexes, keyset pagination)
- [x] Summary calculado en query separada para no mezclar con paginacion

### Hook 5: Observability
- [x] Structured logging (patient_id, filtros, result_count)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy definida
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
