# Patient Balance (B-09)

---

## Overview

**Feature:** Obtener el estado de cuenta completo de un paciente: facturas pendientes (por estado), total pagado historico, saldo total pendiente, planes de pago activos con proximas cuotas, y el resumen financiero agrupado por estado de factura. Es el endpoint central para la vista de "Cuenta del Paciente" en la pantalla de caja y en el portal del paciente.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), B-07 (payment-record.md), B-10 (payment-plan-create.md), patients (Patient), infra/authentication-rules.md, database-architecture.md (`invoices`, `payments`, `payment_plans`, `payment_plan_installments`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor, patient
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Un paciente (rol `patient`) solo puede ver su propio balance. Los doctores pueden ver el balance de sus pacientes asignados. Este endpoint es de solo lectura — para registrar pagos usar B-07.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/balance
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

N/A

### Request Body Schema

N/A — GET request

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "patient_id": "UUID",
  "patient_name": "string",
  "currency": "string — ISO 4217",
  "balance_summary": {
    "total_invoiced": "integer — suma de todos los 'total' de facturas no canceladas, en centavos",
    "total_paid": "integer — suma de todos los pagos realizados, en centavos",
    "total_outstanding": "integer — suma de balance_due de facturas pendientes (no paid/cancelled), en centavos",
    "total_overdue": "integer — suma de balance_due de facturas overdue, en centavos",
    "invoices_by_status": {
      "draft": "integer — numero de facturas en draft",
      "sent": "integer",
      "paid": "integer",
      "overdue": "integer",
      "cancelled": "integer"
    }
  },
  "outstanding_invoices": [
    {
      "invoice_id": "UUID",
      "invoice_number": "string",
      "status": "string",
      "total": "integer",
      "amount_paid": "integer",
      "balance_due": "integer",
      "due_date": "string — ISO8601 date",
      "days_overdue": "integer | null — null si no esta vencida",
      "sent_at": "ISO8601 | null"
    }
  ],
  "payment_plans": [
    {
      "plan_id": "UUID",
      "invoice_id": "UUID",
      "invoice_number": "string",
      "total_amount": "integer",
      "paid_amount": "integer",
      "remaining_amount": "integer",
      "installment_count": "integer",
      "paid_installments": "integer",
      "next_installment": {
        "installment_number": "integer",
        "due_date": "string",
        "amount": "integer",
        "status": "string — pending | overdue"
      } | null
    }
  ],
  "recent_payments": [
    {
      "payment_id": "UUID",
      "invoice_number": "string",
      "amount": "integer",
      "method": "string",
      "payment_date": "string",
      "reference_number": "string | null"
    }
  ],
  "calculated_at": "ISO8601 — timestamp del calculo"
}
```

**Example:**
```json
{
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "patient_name": "Juan Carlos Perez Gomez",
  "currency": "COP",
  "balance_summary": {
    "total_invoiced": 282000000,
    "total_paid": 162000000,
    "total_outstanding": 120000000,
    "total_overdue": 45000000,
    "invoices_by_status": {
      "draft": 0,
      "sent": 1,
      "paid": 1,
      "overdue": 1,
      "cancelled": 0
    }
  },
  "outstanding_invoices": [
    {
      "invoice_id": "inv_2b3c4d5e-f6a7-8901-bcde-f12345678901",
      "invoice_number": "FAC-2026-00002",
      "status": "overdue",
      "total": 45000000,
      "amount_paid": 0,
      "balance_due": 45000000,
      "due_date": "2026-01-31",
      "days_overdue": 25,
      "sent_at": "2026-01-25T14:00:00Z"
    },
    {
      "invoice_id": "inv_3c4d5e6f-a7b8-9012-cdef-123456789012",
      "invoice_number": "FAC-2026-00003",
      "status": "sent",
      "total": 75000000,
      "amount_paid": 0,
      "balance_due": 75000000,
      "due_date": "2026-03-15",
      "days_overdue": null,
      "sent_at": "2026-02-20T10:00:00Z"
    }
  ],
  "payment_plans": [
    {
      "plan_id": "pp_aabb1122-ccdd-3344-eeff-556677889900",
      "invoice_id": "inv_3c4d5e6f-a7b8-9012-cdef-123456789012",
      "invoice_number": "FAC-2026-00003",
      "total_amount": 75000000,
      "paid_amount": 0,
      "remaining_amount": 75000000,
      "installment_count": 3,
      "paid_installments": 0,
      "next_installment": {
        "installment_number": 1,
        "due_date": "2026-03-01",
        "amount": 25000000,
        "status": "pending"
      }
    }
  ],
  "recent_payments": [
    {
      "payment_id": "pay_1111aaaa-2222-3333-4444-555566667777",
      "invoice_number": "FAC-2026-00001",
      "amount": 162000000,
      "method": "bank_transfer",
      "payment_date": "2026-02-25",
      "reference_number": "TRF-20260225-001"
    }
  ],
  "calculated_at": "2026-02-25T16:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol `patient` intentando ver balance de otro paciente, o rol `assistant`.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver el balance de este paciente."
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
**When:** Error inesperado al calcular el balance.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea uno de: `clinic_owner`, `receptionist`, `doctor`, `patient`. Si es `assistant`, 403.
3. Verificar que el paciente existe en el tenant. Si no, 404.
4. Si rol es `patient`: verificar que `user.patient_id == patient_id`. Si no, 403.
5. Si rol es `doctor`: verificar que el paciente esta asignado al doctor. Si no, 403.
6. Verificar si existe cache valido: `tenant:{tenant_id}:patient_balance:{patient_id}`. Si existe y `age < 2min`, retornar desde cache.
7. **Calcular balance_summary:**
   - Query de agrupacion sobre `invoices WHERE patient_id = :patient_id AND tenant_id = :tenant_id AND status != 'cancelled'`:
     - `total_invoiced` = SUM(total)
     - `total_outstanding` = SUM(balance_due) WHERE status NOT IN ('paid', 'cancelled')
     - `total_overdue` = SUM(balance_due) WHERE status = 'overdue'
   - `total_paid` = SUM(payments.amount) WHERE patient_id = :patient_id AND tenant_id = :tenant_id
   - `invoices_by_status` = COUNT GROUP BY status (incluir todos los estados con 0)
8. **Obtener outstanding_invoices:**
   - SELECT facturas WHERE `status NOT IN ('paid', 'cancelled') AND patient_id = :patient_id`
   - Para cada factura, calcular `days_overdue`:
     - Si `status = 'overdue'` o (`status IN ('sent', 'draft')` y `due_date < hoy`): `days_overdue = (hoy - due_date).days`
     - Si no: `days_overdue = null`
   - Ordenar por `days_overdue DESC, due_date ASC` (las mas urgentes primero)
9. **Obtener payment_plans activos:**
   - SELECT planes de pago `WHERE patient_id = :patient_id AND status = 'active'`
   - Para cada plan, cargar la proxima cuota pendiente (`installments WHERE status IN ('pending', 'overdue') ORDER BY installment_number ASC LIMIT 1`)
   - Calcular `paid_amount` y `remaining_amount` del plan
10. **Obtener recent_payments:**
    - SELECT ultimos 5 pagos del paciente, ordenados por `payment_date DESC`
    - JOIN con invoices para obtener `invoice_number`
11. Construir respuesta con `calculated_at = now()`.
12. Almacenar en cache Redis con TTL 2 minutos.
13. Registrar en audit log: accion `read`, recurso `patient_balance`, `tenant_id`, `user_id`, `patient_id`.
14. Retornar 200 OK.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | UUID v4, pertenece al tenant | "El paciente no fue encontrado." |

**Business Rules:**

- El balance es calculado en tiempo real (o desde cache de 2 minutos) — no es un campo almacenado para evitar inconsistencias.
- `total_outstanding` no incluye facturas canceladas ni pagadas.
- `total_overdue` es solo facturas cuyo `status = 'overdue'`.
- `outstanding_invoices` se limita a las facturas con `balance_due > 0` que aun no esten pagadas o canceladas.
- `recent_payments` siempre son los ultimos 5 (sin paginacion — para vista rapida).
- `payment_plans` solo incluye planes activos (status = 'active'), no los completados.
- `days_overdue` es positivo si la factura esta vencida, null si no.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Paciente sin facturas | Todos los totales en 0, arrays vacios |
| Paciente con solo facturas pagadas | `total_outstanding: 0`, `outstanding_invoices: []` |
| Factura vencida el mismo dia de consulta | `days_overdue: 0` |
| Plan de pago con todas las cuotas pagadas | No aparece en `payment_plans` (status completed) |
| Multiples planes de pago activos | Todos aparecen en `payment_plans` |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:** Ninguna (solo lectura).

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select, func, case

# Balance summary en una sola query de agregacion
summary_stmt = (
    select(
        func.sum(Invoice.total).label("total_invoiced"),
        func.sum(
            case((Invoice.status.notin_(["paid", "cancelled"]), Invoice.balance_due), else_=0)
        ).label("total_outstanding"),
        func.sum(
            case((Invoice.status == "overdue", Invoice.balance_due), else_=0)
        ).label("total_overdue"),
        func.count(Invoice.id).label("total_invoices"),
    )
    .where(Invoice.patient_id == patient_id)
    .where(Invoice.tenant_id == tenant_id)
    .where(Invoice.status != "cancelled")
)

# Outstanding invoices
outstanding_stmt = (
    select(Invoice)
    .where(Invoice.patient_id == patient_id)
    .where(Invoice.tenant_id == tenant_id)
    .where(Invoice.status.notin_(["paid", "cancelled"]))
    .where(Invoice.balance_due > 0)
    .order_by(Invoice.due_date.asc())
)

# Recent payments (ultimos 5)
recent_payments_stmt = (
    select(Payment, Invoice.invoice_number)
    .join(Invoice, Payment.invoice_id == Invoice.id)
    .where(Payment.patient_id == patient_id)
    .where(Payment.tenant_id == tenant_id)
    .order_by(Payment.payment_date.desc())
    .limit(5)
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient_balance:{patient_id}`: SET — cache del balance completo

**Cache TTL:** 2 minutos (balance cambia con cada pago nuevo)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno.

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** patient_balance
- **PHI involved:** No (datos financieros con nombre PII del paciente)

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 100ms (con cache)
- **Maximum acceptable:** < 600ms (sin cache, multiples aggregation queries)

### Caching Strategy
- **Strategy:** Cache del objeto balance completo serializado en Redis
- **Cache key:** `tenant:{tenant_id}:patient_balance:{patient_id}`
- **TTL:** 2 minutos
- **Invalidation:** En cada pago registrado (B-07), nueva factura (B-01), o cambio de estado de plan de pago (B-10)

### Database Performance

**Queries ejecutadas:** 4-5 (summary aggregate, outstanding invoices, total_paid aggregate, payment_plans, recent_payments)

**Indexes required:**
- `invoices.(patient_id, tenant_id, status)` — INDEX COMPUESTO (summary y outstanding)
- `payments.(patient_id, tenant_id, payment_date)` — INDEX COMPUESTO (total_paid y recent)
- `payment_plans.(patient_id, status)` — INDEX COMPUESTO
- `payment_plan_installments.(plan_id, status, installment_number)` — INDEX COMPUESTO

**N+1 prevention:** Queries de agregacion en lote, no por factura individual. `recent_payments` con LIMIT 5.

### Pagination

**Pagination:** No — balance es una vista consolidada. `outstanding_invoices` puede ser larga pero es bounded por la realidad del negocio (< 50 facturas pendientes por paciente tipicamente).

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Serializacion Pydantic. Nombres de paciente escapados.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Nombre del paciente (PII). No hay datos clinicos directos.

**Audit requirement:** All access logged (acceso a estado financiero del paciente)

---

## Testing

### Test Cases

#### Happy Path
1. Balance de paciente con facturas mixtas
   - **Given:** Paciente con 1 factura pagada, 1 sent, 1 overdue, usuario `receptionist`
   - **When:** GET /api/v1/patients/{id}/balance
   - **Then:** 200 OK, `total_outstanding` = sent.balance_due + overdue.balance_due, `total_overdue` = overdue.balance_due, `outstanding_invoices` con 2 elementos

2. Balance de paciente sin facturas
   - **Given:** Paciente nuevo sin historial
   - **When:** GET
   - **Then:** 200 OK, todos los totales en 0, arrays vacios, `invoices_by_status` todos en 0

3. Balance con plan de pago activo
   - **Given:** Factura con plan de 3 cuotas, 0 pagadas
   - **When:** GET
   - **Then:** `payment_plans` con 1 plan, `next_installment` con la primera cuota

4. Paciente ve su propio balance (rol patient)
   - **Given:** JWT con rol `patient`
   - **When:** GET
   - **Then:** 200 OK con su propio balance

5. Cache funciona correctamente
   - **Given:** Balance calculado y cacheado
   - **When:** Segunda consulta dentro de 2 minutos
   - **Then:** Response < 100ms (desde cache), `calculated_at` igual al primero

#### Edge Cases
1. Todas las facturas pagadas
   - **Given:** Paciente con historial completo, todas pagadas
   - **When:** GET
   - **Then:** `total_outstanding: 0`, `outstanding_invoices: []`, `total_paid` correcto

2. Factura vencida exactamente hoy
   - **Given:** `due_date = hoy`, `status = 'sent'`
   - **When:** GET
   - **Then:** `days_overdue: 0` (vencida hoy)

3. Plan de pago completado
   - **Given:** Plan con todas las cuotas pagadas (status=completed)
   - **When:** GET
   - **Then:** No aparece en `payment_plans`

#### Error Cases
1. Paciente ve balance de otro paciente (rol patient)
   - **Given:** JWT `patient` con `patient_id` diferente al de la URL
   - **When:** GET
   - **Then:** 403 Forbidden

2. patient_id inexistente
   - **Given:** UUID no existente en el tenant
   - **When:** GET
   - **Then:** 404 Not Found

3. Rol `assistant`
   - **Given:** JWT con rol `assistant`
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `patient` (vinculado), un `assistant` (para 403).

**Patients:** Un paciente con historial completo (facturas y pagos), un paciente nuevo sin datos.

**Invoices:** Mix de estados: 1 draft, 1 sent, 1 paid, 1 overdue.

**Payments:** Varios pagos para el paciente con historial.

**Payment Plans:** 1 plan activo con cuotas pendientes.

### Mocking Strategy

- **Redis:** fakeredis para cache de balance
- **Database:** SQLite en memoria con seed completo de billing
- **Date:** Mockear `date.today()` para calcular `days_overdue` correctamente

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] `balance_summary` calcula correctamente todos los totales
- [ ] `outstanding_invoices` lista facturas no pagadas/canceladas con `days_overdue`
- [ ] `payment_plans` incluye proxima cuota de cada plan activo
- [ ] `recent_payments` retorna los ultimos 5 pagos
- [ ] Cache de 2 minutos implementado y funciona
- [ ] Rol `patient` solo ve su propio balance
- [ ] Rol `assistant` retorna 403
- [ ] Paciente sin facturas retorna respuesta vacia valida (no error)
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms cache, < 600ms sin cache)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Registro de pagos (ver B-07 payment-record.md)
- Historial completo de pagos paginado (ver B-08 payment-list.md)
- Detalle de plan de pago con todas las cuotas (ver B-11 payment-plan-get.md)
- Balance a nivel de tenant (dashboard de cobranza — ver B-13 billing-summary.md)
- Exportacion de estado de cuenta a PDF

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (solo URL param patient_id)
- [x] All outputs defined (balance_summary, outstanding_invoices, payment_plans, recent_payments)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (patient restriction)
- [x] Error cases enumerated
- [x] Auth requirements explicit (patient self-only, assistant forbidden)
- [x] Side effects listed (cache, audit)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain, aggregation endpoint)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, aggregation queries)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (patient self-only, assistant forbidden)
- [x] Input sanitization (UUID validation)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] Audit trail para acceso a balance financiero

### Hook 4: Performance & Scalability
- [x] Response time targets (< 100ms cache, < 600ms sin cache)
- [x] Cache de 2min del balance completo
- [x] Aggregation queries eficientes con indexes
- [x] No paginacion — vista consolidada bounded

### Hook 5: Observability
- [x] Structured logging (patient_id, tenant_id, cache_hit flag)
- [x] Audit log entries defined (read patient_balance)
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
