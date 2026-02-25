# Payment Plan Get (B-11)

---

## Overview

**Feature:** Obtener el detalle completo de un plan de pagos, incluyendo el calendario de cuotas con estado individual de cada cuota (pendiente, pagada, vencida), el progreso del plan (cuotas pagadas vs totales), el monto pagado y el monto restante. Permite al recepcionista y al paciente hacer seguimiento del acuerdo de pago.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-10 (payment-plan-create.md), B-07 (payment-record.md), patients (Patient), infra/authentication-rules.md, database-architecture.md (`payment_plans`, `payment_plan_installments`, `payments`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor, patient
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Un paciente (rol `patient`) solo puede ver sus propios planes de pago. Los doctores pueden ver planes de sus pacientes asignados.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/payment-plans/{plan_id}
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
| plan_id | Yes | UUID | UUID v4 valido | ID del plan de pago | pp_aabb1122-ccdd-3344-eeff-556677889900 |

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
  "id": "UUID",
  "invoice_id": "UUID",
  "invoice_number": "string",
  "invoice_status": "string",
  "patient_id": "UUID",
  "patient_name": "string",
  "status": "string — active | completed | cancelled",
  "currency": "string",
  "total_amount": "integer — monto original del plan (balance_due al crear), en centavos",
  "paid_amount": "integer — suma de pagos registrados en el plan, en centavos",
  "remaining_amount": "integer — total_amount - paid_amount, en centavos",
  "installment_count": "integer",
  "paid_installments": "integer",
  "pending_installments": "integer",
  "overdue_installments": "integer",
  "frequency": "string",
  "notes": "string | null",
  "installments": [
    {
      "id": "UUID",
      "installment_number": "integer",
      "due_date": "string — ISO8601 date",
      "amount": "integer — en centavos",
      "status": "string — pending | paid | overdue",
      "days_overdue": "integer | null — null si no esta vencida",
      "paid_at": "ISO8601 | null",
      "payment_id": "UUID | null — ID del pago que cubrió esta cuota",
      "payment_method": "string | null — metodo de pago usado"
    }
  ],
  "next_installment": {
    "installment_number": "integer",
    "due_date": "string",
    "amount": "integer",
    "status": "string",
    "days_until_due": "integer — negativo si ya esta vencida"
  } | null,
  "completion_percentage": "number — porcentaje completado (0-100)",
  "created_by_name": "string",
  "created_at": "ISO8601",
  "completed_at": "ISO8601 | null"
}
```

**Example (plan en progreso, 1 cuota pagada de 3):**
```json
{
  "id": "pp_aabb1122-ccdd-3344-eeff-556677889900",
  "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
  "invoice_number": "FAC-2026-00001",
  "invoice_status": "sent",
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "patient_name": "Juan Carlos Perez Gomez",
  "status": "active",
  "currency": "COP",
  "total_amount": 162000000,
  "paid_amount": 54000000,
  "remaining_amount": 108000000,
  "installment_count": 3,
  "paid_installments": 1,
  "pending_installments": 2,
  "overdue_installments": 0,
  "frequency": "monthly",
  "notes": "Acuerdo de pago en 3 cuotas mensuales.",
  "installments": [
    {
      "id": "ppi_1111aaaa-2222-3333-4444-555566667777",
      "installment_number": 1,
      "due_date": "2026-03-01",
      "amount": 54000000,
      "status": "paid",
      "days_overdue": null,
      "paid_at": "2026-03-01T10:30:00Z",
      "payment_id": "pay_cccc3333-4444-5555-6666-777788889999",
      "payment_method": "cash"
    },
    {
      "id": "ppi_2222bbbb-3333-4444-5555-666677778888",
      "installment_number": 2,
      "due_date": "2026-04-01",
      "amount": 54000000,
      "status": "pending",
      "days_overdue": null,
      "paid_at": null,
      "payment_id": null,
      "payment_method": null
    },
    {
      "id": "ppi_3333cccc-4444-5555-6666-777788889999",
      "installment_number": 3,
      "due_date": "2026-05-01",
      "amount": 54000000,
      "status": "pending",
      "days_overdue": null,
      "paid_at": null,
      "payment_id": null,
      "payment_method": null
    }
  ],
  "next_installment": {
    "installment_number": 2,
    "due_date": "2026-04-01",
    "amount": 54000000,
    "status": "pending",
    "days_until_due": 35
  },
  "completion_percentage": 33.33,
  "created_by_name": "Maria Gonzalez (Recepcion)",
  "created_at": "2026-02-25T16:00:00Z",
  "completed_at": null
}
```

### Error Responses

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol `patient` intentando ver plan de otro paciente, o rol `assistant`.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver este plan de pago."
}
```

#### 404 Not Found
**When:** `patient_id` o `plan_id` no existen, o el plan no pertenece al paciente.

```json
{
  "error": "payment_plan_not_found",
  "message": "El plan de pago no fue encontrado."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado al consultar o calcular el estado del plan.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea uno de: `clinic_owner`, `receptionist`, `doctor`, `patient`. Si es `assistant`, 403.
3. Verificar que el paciente existe en el tenant. Si no, 404.
4. Si rol es `patient`: verificar que `user.patient_id == patient_id`. Si no, 403.
5. Si rol es `doctor`: verificar que el paciente esta asignado al doctor. Si no, 403.
6. Buscar el plan: `WHERE id = plan_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no, 404.
7. Cargar cuotas: `SELECT * FROM payment_plan_installments WHERE plan_id = :plan_id ORDER BY installment_number ASC`.
8. Cargar datos del pagos asociados a las cuotas pagadas: JOIN con `payments` para obtener `payment_method` de las cuotas pagadas.
9. Cargar datos de la factura: `invoice_number`, `invoice_status`.
10. Cargar nombre del creador del plan (`created_by_name`).
11. **Calcular estado lazy de cuotas (actualizar a overdue si aplica):**
    - Para cada cuota con `status = 'pending'` y `due_date < hoy`: marcar como `overdue` en DB.
    - Actualizar `overdue_installments` en el plan.
    - Si todo el plan puede haber cambiado de estado (todas pagadas → completed), actualizar `payment_plan.status = 'completed'` y `completed_at = now()`.
12. **Calcular campos derivados:**
    - `paid_installments` = COUNT WHERE status = 'paid'
    - `pending_installments` = COUNT WHERE status = 'pending'
    - `overdue_installments` = COUNT WHERE status = 'overdue'
    - `completion_percentage` = (paid_installments / installment_count) * 100
    - `next_installment` = primera cuota con status IN ('pending', 'overdue') ORDER BY installment_number ASC
    - `days_until_due` del `next_installment` = `due_date - hoy` (negativo si ya vencio)
    - Para cuotas `overdue`: `days_overdue = (hoy - due_date).days`
13. Almacenar en cache (si no hubo lazy updates de estado).
14. Registrar en audit log: accion `read`, recurso `payment_plan`, `tenant_id`, `user_id`, `plan_id`.
15. Retornar 200 OK con el plan completo.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | UUID v4, pertenece al tenant | "El paciente no fue encontrado." |
| plan_id (URL) | UUID v4, plan del paciente y tenant | "El plan de pago no fue encontrado." |

**Business Rules:**

- El estado de cada cuota se actualiza lazy en este endpoint (similar a facturas overdue).
- `completion_percentage` se calcula siempre dinamicamente (no almacenado).
- `next_installment` es null cuando todas las cuotas estan pagadas (plan completed).
- `days_until_due` es negativo cuando la cuota ya esta vencida (permite saber cuanto tiempo lleva vencida la proxima cuota).
- Si el plan esta `cancelled`, se retorna de igual forma con todas las cuotas en su ultimo estado.
- `paid_amount` = suma de los pagos vinculados al plan (via `payment_plan_id` en la tabla `payments`).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Plan completado (todas pagadas) | `status: "completed"`, `completion_percentage: 100`, `next_installment: null` |
| Plan con cuota vencida | Lazy update a `overdue`, `days_overdue` calculado, `overdue_installments: N` |
| Plan cancelado | Retornar con `status: "cancelled"`, cuotas en su estado final |
| Cuota pagada con pago via `bank_transfer` | `payment_method: "bank_transfer"` en la cuota |
| Unica cuota pendiente (2 de 3 pagadas) | `next_installment` con la ultima cuota, `completion_percentage: 66.67` |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `payment_plan_installments`: UPDATE — `status = 'overdue'` para cuotas vencidas (lazy update)
- `payment_plans`: UPDATE — `status = 'completed'`, `completed_at` si todas las cuotas estan pagadas (lazy update)

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

# Cargar plan con cuotas
stmt = (
    select(PaymentPlan)
    .where(PaymentPlan.id == plan_id)
    .where(PaymentPlan.patient_id == patient_id)
    .where(PaymentPlan.tenant_id == tenant_id)
    .options(selectinload(PaymentPlan.installments))
)
plan = (await session.execute(stmt)).scalar_one_or_none()

# Lazy update de cuotas vencidas
today = date.today()
overdue_ids = [
    inst.id for inst in plan.installments
    if inst.status == "pending" and inst.due_date < today
]
if overdue_ids:
    await session.execute(
        update(PaymentPlanInstallment)
        .where(PaymentPlanInstallment.id.in_(overdue_ids))
        .values(status="overdue")
    )
    await session.commit()

# Verificar si el plan se completo
all_paid = all(inst.status == "paid" for inst in plan.installments)
if all_paid and plan.status == "active":
    await session.execute(
        update(PaymentPlan)
        .where(PaymentPlan.id == plan_id)
        .values(status="completed", completed_at=datetime.utcnow())
    )
    await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:payment_plan:{plan_id}`: SET — cache del detalle del plan

**Cache TTL:** 5 minutos (invalida en pagos nuevos que actualicen el plan)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno.

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** payment_plan
- **PHI involved:** No (datos financieros con PII del paciente)

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 150ms (con cache)
- **Maximum acceptable:** < 500ms (sin cache, con lazy updates)

### Caching Strategy
- **Strategy:** Cache del detalle del plan serializado
- **Cache key:** `tenant:{tenant_id}:payment_plan:{plan_id}`
- **TTL:** 5 minutos
- **Invalidation:** En cada pago registrado para el plan (B-07 con `payment_plan_id`)

### Database Performance

**Queries ejecutadas:** 2-4 (buscar plan + cuotas via selectinload, JOIN pagos para method, lazy updates si aplica)

**Indexes required:**
- `payment_plans.(id, patient_id, tenant_id)` — INDEX COMPUESTO
- `payment_plan_installments.(plan_id, status)` — INDEX COMPUESTO
- `payment_plan_installments.(plan_id, installment_number)` — INDEX COMPUESTO
- `payments.payment_plan_id` — INDEX (para lookup de metodo de pago)

**N+1 prevention:** Cuotas cargadas con `selectinload`. Pagos vinculados con JOIN en query de cuotas.

### Pagination

**Pagination:** No — retorna todas las cuotas del plan (bounded por max 36 cuotas)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID | |
| plan_id (URL) | Pydantic UUID | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Serializacion Pydantic. Nombres escapados.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Nombre del paciente (PII). No hay datos clinicos.

**Audit requirement:** All access logged (acceso a datos de plan de pago)

---

## Testing

### Test Cases

#### Happy Path
1. Plan en progreso (1 cuota pagada de 3)
   - **Given:** Plan activo, 1 cuota pagada con `payment_method: "cash"`, 2 pendientes, usuario `receptionist`
   - **When:** GET /api/v1/patients/{id}/payment-plans/{plan_id}
   - **Then:** 200 OK, `paid_installments: 1`, `completion_percentage: 33.33`, `next_installment` con cuota 2, `payment_method: "cash"` en cuota 1

2. Plan completado (todas pagadas)
   - **Given:** Todas las cuotas con `status: "paid"`
   - **When:** GET
   - **Then:** `status: "completed"`, `completion_percentage: 100`, `next_installment: null`, `completed_at` no null

3. Cuota vencida (lazy update)
   - **Given:** Cuota 1 con `due_date: "2026-01-15"` (pasada), `status: "pending"`
   - **When:** GET
   - **Then:** Cuota 1 actualizada a `status: "overdue"`, `days_overdue: N`, `overdue_installments: 1`

4. Paciente ve su propio plan (rol patient)
   - **Given:** JWT con rol `patient`
   - **When:** GET
   - **Then:** 200 OK con detalle completo

5. `days_until_due` negativo (proxima cuota ya vencida)
   - **Given:** `next_installment.due_date` en el pasado
   - **When:** GET
   - **Then:** `next_installment.days_until_due` = valor negativo

#### Edge Cases
1. Plan con enganche (cuota 1 diferente en monto)
   - **Given:** Plan con cuota 1 de 40000000 y cuotas 2-3 de 25000000
   - **When:** GET
   - **Then:** Cuota 1 con amount 40000000, cuotas 2-3 con amount 25000000

2. Plan cancelado
   - **Given:** `plan.status: "cancelled"`
   - **When:** GET
   - **Then:** 200 OK con `status: "cancelled"`, cuotas en su ultimo estado

#### Error Cases
1. Paciente ve plan de otro paciente (rol patient)
   - **Given:** JWT `patient` con `patient_id` diferente al de la URL
   - **When:** GET
   - **Then:** 403 Forbidden

2. plan_id no existe
   - **Given:** UUID inexistente
   - **When:** GET
   - **Then:** 404 Not Found

3. Rol `assistant`
   - **Given:** JWT con rol `assistant`
   - **When:** GET
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `patient` (vinculado), un `assistant` (para 403).

**Patients:** Un paciente con plan de pago.

**Payment Plans:** Un plan activo con 3 cuotas (1 pagada, 2 pendientes), un plan completado, un plan con cuota vencida.

**Payments:** Pago vinculado a la cuota 1 con `payment_plan_id` y `method`.

### Mocking Strategy

- **Redis:** fakeredis para cache del plan
- **Database:** SQLite en memoria con esquema completo
- **Date:** Mockear `date.today()` para tests de overdue y days_until_due

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Plan retorna todas las cuotas con estado y montos correctos
- [ ] `completion_percentage` calculado correctamente
- [ ] `next_installment` con `days_until_due` correcto (positivo futuro, negativo pasado)
- [ ] Lazy update de cuotas a `overdue` funciona en lectura
- [ ] Plan se marca `completed` automáticamente cuando todas las cuotas estan pagadas
- [ ] `payment_method` visible en cuotas pagadas
- [ ] Rol `patient` solo ve sus propios planes
- [ ] Rol `assistant` retorna 403
- [ ] Cache de 5 minutos implementado
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms sin cache)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listado de todos los planes de un paciente (simplificado en B-09 balance)
- Modificacion de planes de pago
- Cancelacion de planes de pago
- Vinculacion de pagos a cuotas especificas (logica en B-07)
- Alertas automaticas de cuotas proximas a vencer

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (URL params, sin body)
- [x] All outputs defined (plan completo con cuotas enriquecidas)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (patient self-only)
- [x] Error cases enumerated
- [x] Auth requirements explicit (restriccion patient, assistant forbidden)
- [x] Side effects listed (lazy updates, cache, audit)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] selectinload para evitar N+1
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated con restricciones por rol
- [x] Input sanitization (UUID validation)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] Audit trail para acceso

### Hook 4: Performance & Scalability
- [x] Response time targets (< 150ms cache, < 500ms sin cache)
- [x] Cache de 5min con invalidacion correcta
- [x] Bounded result (max 36 cuotas — no paginacion necesaria)

### Hook 5: Observability
- [x] Structured logging con plan_id y lazy_updates_made
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)

### Hook 6: Testability
- [x] Test cases enumerated (in-progress, completado, overdue, edge cases)
- [x] Test data requirements specified
- [x] Mocking strategy (Redis, date)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
