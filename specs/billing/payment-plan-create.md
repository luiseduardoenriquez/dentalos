# Payment Plan Create (B-10)

---

## Overview

**Feature:** Crear un plan de pagos (cuotas) para una factura especifica. El paciente y la clinica acuerdan dividir el total de la factura en cuotas periodicas (semanales, quincenales o mensuales). El sistema genera automaticamente el calendario de cuotas con fechas de vencimiento. El plan de pagos se vincula a la factura y los pagos posteriores (B-07 con `method=payment_plan`) se registran contra cuotas especificas.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), B-07 (payment-record.md), patients (Patient), infra/authentication-rules.md, database-architecture.md (`payment_plans`, `payment_plan_installments`, `invoices`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Solo `clinic_owner` y `receptionist` pueden crear planes de pago. La factura debe existir y tener `balance_due > 0`. No se puede crear un plan sobre una factura cancelada o completamente pagada.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/payment-plans
```

**Rate Limiting:**
- 30 requests por minuto por usuario
- Redis sliding window: `dentalos:rl:payment_plan_create:{user_id}` (TTL 60s)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Formato de request | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | UUID v4 valido | ID del paciente | pt_550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "invoice_id": "UUID (required) — factura sobre la que se crea el plan de pagos",
  "installment_count": "integer (required) — numero de cuotas, min: 2, max: 36",
  "frequency": "string (required) — weekly | biweekly | monthly — frecuencia de las cuotas",
  "start_date": "string (required) — ISO8601 date — fecha de la primera cuota (debe ser >= hoy)",
  "notes": "string (optional) — notas internas sobre el acuerdo, max 500 chars",
  "require_down_payment": "boolean (optional) — si true, la primera cuota (enganche) se marca como debida inmediatamente, default: false",
  "down_payment_amount": "integer (optional) — monto del enganche en centavos, sobreescribe la cuota calculada para la primera cuota"
}
```

**Example Request (plan mensual de 3 cuotas):**
```json
{
  "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
  "installment_count": 3,
  "frequency": "monthly",
  "start_date": "2026-03-01",
  "notes": "Acuerdo de pago en 3 cuotas mensuales. Firmado el 2026-02-25."
}
```

**Example Request (plan quincenal con enganche):**
```json
{
  "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
  "installment_count": 4,
  "frequency": "biweekly",
  "start_date": "2026-03-01",
  "require_down_payment": true,
  "down_payment_amount": 40000000,
  "notes": "Enganche de 40000 COP, 3 cuotas quincenales restantes."
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
  "invoice_id": "UUID",
  "invoice_number": "string",
  "patient_id": "UUID",
  "status": "active",
  "total_amount": "integer — balance_due de la factura al momento de crear el plan, en centavos",
  "paid_amount": "integer — 0 en creacion",
  "remaining_amount": "integer — igual a total_amount en creacion",
  "installment_count": "integer",
  "paid_installments": "integer — 0 en creacion",
  "frequency": "string",
  "notes": "string | null",
  "installments": [
    {
      "id": "UUID",
      "installment_number": "integer — 1 a N",
      "due_date": "string — ISO8601 date",
      "amount": "integer — en centavos",
      "status": "string — pending | overdue | paid",
      "paid_at": "ISO8601 | null",
      "payment_id": "UUID | null"
    }
  ],
  "created_by": "UUID",
  "created_at": "ISO8601"
}
```

**Example:**
```json
{
  "id": "pp_aabb1122-ccdd-3344-eeff-556677889900",
  "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
  "invoice_number": "FAC-2026-00001",
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "total_amount": 162000000,
  "paid_amount": 0,
  "remaining_amount": 162000000,
  "installment_count": 3,
  "paid_installments": 0,
  "frequency": "monthly",
  "notes": "Acuerdo de pago en 3 cuotas mensuales.",
  "installments": [
    {
      "id": "ppi_1111aaaa-2222-3333-4444-555566667777",
      "installment_number": 1,
      "due_date": "2026-03-01",
      "amount": 54000000,
      "status": "pending",
      "paid_at": null,
      "payment_id": null
    },
    {
      "id": "ppi_2222bbbb-3333-4444-5555-666677778888",
      "installment_number": 2,
      "due_date": "2026-04-01",
      "amount": 54000000,
      "status": "pending",
      "paid_at": null,
      "payment_id": null
    },
    {
      "id": "ppi_3333cccc-4444-5555-6666-777788889999",
      "installment_number": 3,
      "due_date": "2026-05-01",
      "amount": 54000000,
      "status": "pending",
      "paid_at": null,
      "payment_id": null
    }
  ],
  "created_by": "usr_receptionist-0001-0000-0000-000000000000",
  "created_at": "2026-02-25T16:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Body malformado, `installment_count` fuera de rango, `frequency` invalido, `start_date` en formato incorrecto.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El numero de cuotas debe estar entre 2 y 36.",
  "details": {
    "installment_count": ["Valor 50 fuera del rango permitido (2-36)."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido.

#### 403 Forbidden
**When:** Rol no autorizado (`doctor`, `assistant`, `patient`).

```json
{
  "error": "forbidden",
  "message": "Solo recepcionistas y administradores pueden crear planes de pago."
}
```

#### 404 Not Found
**When:** `patient_id` o `invoice_id` no existen en el tenant.

#### 409 Conflict
**When:** Ya existe un plan de pago activo para la misma factura.

```json
{
  "error": "payment_plan_already_exists",
  "message": "Ya existe un plan de pago activo para esta factura."
}
```

#### 422 Unprocessable Entity
**When:** Factura en estado `paid` o `cancelled`, `balance_due == 0`, `start_date` en el pasado, `down_payment_amount` mayor al `total_amount`.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "No se puede crear un plan de pago.",
  "details": {
    "invoice_id": ["La factura ya esta completamente pagada."],
    "start_date": ["La fecha de inicio no puede ser en el pasado."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error al generar el calendario de cuotas o al persistir el plan.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `clinic_owner` o `receptionist`. Si no, 403.
3. Validar body con schema Pydantic.
4. Verificar que el paciente existe en el tenant. Si no, 404.
5. Buscar la factura `WHERE id = invoice_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no, 404.
6. Verificar que `invoice.status NOT IN ('paid', 'cancelled')`. Si no, 422.
7. Verificar que `invoice.balance_due > 0`. Si es 0, 422.
8. Verificar que no exista plan activo para la factura: `SELECT 1 FROM payment_plans WHERE invoice_id = :invoice_id AND status = 'active'`. Si existe, 409.
9. Verificar `start_date >= hoy`. Si es en el pasado, 422.
10. Si `down_payment_amount` se provee: verificar que `down_payment_amount < invoice.balance_due` (no puede ser el total completo como enganche). Si viola, 422.
11. **Calcular calendario de cuotas:**
    - `total_to_distribute = invoice.balance_due`
    - Si `down_payment_amount` se provee: `cuota_1_amount = down_payment_amount`, `remaining_for_rest = total_to_distribute - down_payment_amount`, `cuotas_restantes = installment_count - 1`, `cuota_regular = remaining_for_rest // cuotas_restantes`.
    - Si no: `cuota_regular = total_to_distribute // installment_count`.
    - Para manejar el residuo de la division entera: la ultima cuota absorbe el residuo. `cuota_ultima = total_to_distribute - (cuota_regular * (installment_count - 1))` (si sin enganche) o `total_to_distribute - down_payment_amount - (cuota_regular * (installment_count - 2))` (si con enganche).
    - Calcular fechas de cuotas segun `frequency`:
      - `weekly`: cada 7 dias desde `start_date`
      - `biweekly`: cada 14 dias desde `start_date`
      - `monthly`: mismo dia del mes siguiente, mes siguiente, etc. (ej: 1 de marzo, 1 de abril, 1 de mayo). Si el dia no existe en el mes (ej: 31 de febrero), usar el ultimo dia del mes.
    - Generar lista de cuotas: `installment_number`, `due_date`, `amount`, `status = 'pending'`.
12. Iniciar transaccion de base de datos:
    a. Insertar en `payment_plans`: `invoice_id`, `patient_id`, `tenant_id`, `total_amount = invoice.balance_due`, `paid_amount = 0`, `remaining_amount = invoice.balance_due`, `installment_count`, `frequency`, `status = 'active'`, `notes`, `created_by`.
    b. Insertar en `payment_plan_installments`: un registro por cada cuota generada.
13. Confirmar transaccion.
14. Invalidar cache del balance del paciente: DELETE `tenant:{tenant_id}:patient_balance:{patient_id}`.
15. Registrar en audit log: accion `create`, recurso `payment_plan`, `tenant_id`, `user_id`, `patient_id`, `invoice_id`, `total_amount`, `installment_count`.
16. Retornar 201 Created con el plan completo y el calendario de cuotas.

**Validacion de distribucion de cuotas:**
- La suma de todas las cuotas debe ser igual a `invoice.balance_due` (verificacion post-calculo).
- Ninguna cuota puede ser <= 0.
- La ultima cuota puede diferir de las regulares en hasta `installment_count - 1` centavos (residuo de division entera).

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| invoice_id | UUID v4, factura del paciente y tenant | "La factura no fue encontrada." |
| invoice.status | No debe ser 'paid' o 'cancelled' | "No se puede crear plan de pago para una factura pagada o cancelada." |
| invoice.balance_due | Debe ser > 0 | "La factura no tiene saldo pendiente." |
| installment_count | Integer entre 2 y 36 | "El numero de cuotas debe estar entre 2 y 36." |
| frequency | Enum: weekly, biweekly, monthly | "La frecuencia debe ser semanal, quincenal o mensual." |
| start_date | ISO8601 date, >= hoy | "La fecha de inicio no puede ser en el pasado." |
| down_payment_amount | Si se provee: integer > 0 y < total_amount | "El enganche debe ser mayor a 0 y menor al total." |
| notes | Max 500 chars | "Las notas no pueden superar los 500 caracteres." |

**Business Rules:**

- Un plan de pago es por factura — si el paciente tiene 2 facturas pendientes, necesita 2 planes de pago.
- Solo puede existir un plan activo por factura. Si el plan existente se cancela, se puede crear uno nuevo.
- La suma de cuotas siempre debe ser exactamente `invoice.balance_due` (residuo en ultima cuota).
- Los planes de pago no bloquean pagos directos adicionales via B-07 (el paciente puede pagar mas en cualquier momento).
- `frequency=monthly` con start_date=31 genera fechas como: 31/03, 30/04 (ultimo dia), 31/05. El algoritmo usa `monthend` para meses cortos.
- El plan se crea siempre en status `active`. No hay status `draft` para planes de pago.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| balance_due no divisible entre cuotas | Ultima cuota absorbe el residuo |
| start_date = hoy | Valido — primera cuota es inmediata |
| installment_count = 2 | Valido — minimo permitido |
| installment_count = 36 | Valido — maximo permitido (3 anios mensual) |
| down_payment_amount = total_amount - 1 | 422: el enganche deja una cuota de 1 centavo — debe ser razonable (validar minimo cuota > 100 centavos) |
| frequency=monthly, start_date=31 enero | Cuota 2 = 28/29 febrero (ultimo dia del mes), cuota 3 = 31 marzo |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `payment_plans`: INSERT — nuevo plan de pago activo
- `payment_plan_installments`: INSERT — N registros (uno por cuota)

**Example query (SQLAlchemy):**
```python
from sqlalchemy import insert

async with session.begin():
    plan_result = await session.execute(
        insert(PaymentPlan).values(
            invoice_id=body.invoice_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            total_amount=invoice.balance_due,
            paid_amount=0,
            remaining_amount=invoice.balance_due,
            installment_count=body.installment_count,
            frequency=body.frequency,
            status="active",
            notes=body.notes,
            created_by=user_id,
        ).returning(PaymentPlan.id)
    )
    plan_id = plan_result.scalar_one()

    for installment in computed_installments:
        await session.execute(
            insert(PaymentPlanInstallment).values(
                plan_id=plan_id,
                installment_number=installment.number,
                due_date=installment.due_date,
                amount=installment.amount,
                status="pending",
            )
        )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient_balance:{patient_id}`: DELETE — balance del paciente cambia con nuevo plan

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications.payment_plan_created | payment_plan_created | { plan_id, patient_id, tenant_id, installment_count, frequency, total_amount, first_due_date, clinic_name } | Al crear el plan exitosamente |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** payment_plan
- **PHI involved:** No (datos financieros)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app (portal) | Plan de pago creado | Paciente | Al crear plan |
| email | payment_plan_summary | Paciente (configurable) | Al crear plan |

---

## Performance

### Expected Response Time
- **Target:** < 400ms
- **Maximum acceptable:** < 1000ms (incluye calculo de calendario y transaccion multi-tabla)

### Caching Strategy
- **Strategy:** Sin cache para la respuesta. Invalidacion de cache de balance del paciente.
- **Cache key:** N/A para respuesta
- **TTL:** N/A
- **Invalidation:** Cache de balance del paciente

### Database Performance

**Queries executed:** 4-N (verificar paciente, buscar factura, verificar plan existente, insert plan, insert N cuotas)

**Indexes required:**
- `payment_plans.(invoice_id, status)` — INDEX COMPUESTO (verificar plan existente)
- `payment_plans.(patient_id, tenant_id, status)` — INDEX COMPUESTO
- `payment_plan_installments.(plan_id, status)` — INDEX COMPUESTO
- `payment_plan_installments.(plan_id, installment_number)` — INDEX COMPUESTO

**N+1 prevention:** Cuotas insertadas en lote (una transaccion, multiples inserts en loop dentro de la misma transaccion).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID | |
| invoice_id | Pydantic UUID | |
| installment_count | Pydantic int, ge=2, le=36 | |
| frequency | Pydantic Enum estricto | |
| start_date | Pydantic date, >= today | |
| down_payment_amount | Pydantic int, gt=0 opcional | En centavos |
| notes | Pydantic str, strip, max_length=500, bleach | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Serializacion Pydantic. `notes` sanitizado.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno. Datos financieros.

**Audit requirement:** Write-only logged (creacion de plan de pago)

---

## Testing

### Test Cases

#### Happy Path
1. Plan mensual de 3 cuotas iguales
   - **Given:** Factura `sent`, `balance_due: 150000000` (divisible por 3), usuario `receptionist`
   - **When:** POST con `installment_count: 3`, `frequency: "monthly"`, `start_date: "2026-03-01"`
   - **Then:** 201 Created, 3 cuotas de 50000000 cada una, fechas: 2026-03-01, 2026-04-01, 2026-05-01

2. Plan con residuo en ultima cuota
   - **Given:** `balance_due: 100000000` (no divisible por 3)
   - **When:** POST con `installment_count: 3`, `frequency: "monthly"`
   - **Then:** Cuotas: 33333333, 33333333, 33333334 (residuo en ultima), suma = 100000000

3. Plan quincenal con enganche
   - **Given:** `balance_due: 162000000`, `down_payment_amount: 40000000`, `installment_count: 4`
   - **When:** POST con `require_down_payment: true`, `down_payment_amount: 40000000`
   - **Then:** Cuota 1: 40000000, cuotas 2-4: 40666666 cada una (o similar para cubrir residuo)

4. Plan semanal de 2 cuotas
   - **Given:** `balance_due: 80000000`
   - **When:** POST con `installment_count: 2`, `frequency: "weekly"`, `start_date: "2026-03-01"`
   - **Then:** 2 cuotas: 2026-03-01 y 2026-03-08

#### Edge Cases
1. start_date = hoy
   - **Given:** `start_date = hoy`
   - **When:** POST
   - **Then:** 201 Created, primera cuota con fecha de hoy

2. Plan mensual desde el 31
   - **Given:** `start_date: "2026-01-31"`, `installment_count: 3`, `frequency: "monthly"`
   - **When:** POST
   - **Then:** Fechas: 31/01, 28/02 (ultimo dia feb), 31/03

#### Error Cases
1. Ya existe plan activo para la factura
   - **Given:** Plan activo existente para la misma `invoice_id`
   - **When:** POST
   - **Then:** 409 Conflict

2. Factura completamente pagada
   - **Given:** `invoice.status: "paid"`, `balance_due: 0`
   - **When:** POST
   - **Then:** 422 con mensaje

3. start_date en el pasado
   - **Given:** `start_date: "2026-01-01"` (pasado)
   - **When:** POST
   - **Then:** 422 con mensaje

4. Rol `doctor`
   - **Given:** JWT con rol `doctor`
   - **When:** POST
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `doctor` (para 403).

**Patients:** Un paciente activo.

**Invoices:** Una `sent` con saldo, una `paid` (para 422), una con plan activo (para 409).

### Mocking Strategy

- **Redis:** fakeredis para cache invalidation
- **Database:** SQLite en memoria con esquema de billing
- **Date:** Mockear `date.today()` para tests de start_date
- **RabbitMQ:** Mock del publisher para notificacion

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Plan de pago generado con calendario de cuotas correcto
- [ ] Suma de cuotas = `invoice.balance_due` exactamente (residuo en ultima cuota)
- [ ] Fechas de cuotas calculadas correctamente para los 3 frecuencias
- [ ] Frecuencia monthly maneja meses cortos (ultimo dia del mes)
- [ ] Solo 1 plan activo por factura (409 si existe)
- [ ] Factura `paid`/`cancelled` retorna 422
- [ ] Solo `clinic_owner` y `receptionist` pueden crear planes (403 para otros)
- [ ] Cache de balance del paciente invalidado
- [ ] All test cases pass
- [ ] Performance targets met (< 1000ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Obtener detalle del plan de pago (ver B-11 payment-plan-get.md)
- Cancelacion de plan de pago (endpoint separado, post-MVP)
- Modificacion de plan de pago existente (post-MVP)
- Pago automatico de cuotas via tarjeta en archivo (post-MVP)
- Intereses o recargos por mora en el plan (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (invoice_id, installment_count, frequency, start_date, down_payment)
- [x] All outputs defined (plan con calendario de cuotas)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (suma exacta, residuo en ultima cuota)
- [x] Error cases enumerated (plan existente, factura pagada)
- [x] Auth requirements explicit (solo 2 roles)
- [x] Side effects listed (DB, cache, RabbitMQ)
- [x] Algoritmo de calculo de cuotas detallado

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Transaccion atomica para plan + cuotas
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level estricto (solo 2 roles)
- [x] Input sanitization (centavos como int, Enum para frequency)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] Audit trail para creacion de plan financiero

### Hook 4: Performance & Scalability
- [x] Response time target (< 1000ms)
- [x] Transaccion atomica eficiente
- [x] Indexes para plan existente check y listado de cuotas

### Hook 5: Observability
- [x] Audit log entries defined (create payment_plan)
- [x] Structured logging (invoice_id, installment_count, total)
- [x] RabbitMQ job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error, incluyendo residuo y meses cortos)
- [x] Test data requirements specified
- [x] Mocking strategy (Redis, RabbitMQ, date)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
