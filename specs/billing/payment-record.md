# Payment Record (B-07)

---

## Overview

**Feature:** Registrar un pago aplicado a una factura especifica. Soporta pagos totales y parciales, multiples metodos de pago (efectivo, tarjeta, transferencia, seguro, plan de pago) y referencia de transaccion. Actualiza automaticamente `amount_paid` y `balance_due` de la factura. Cuando `balance_due` llega a 0, la factura se marca como `paid` automaticamente. Toda transaccion financiera queda en el audit log.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), B-02 (invoice-get.md), patients (Patient), infra/authentication-rules.md, infra/audit-logging.md, database-architecture.md (`invoices`, `payments`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Solo `clinic_owner` y `receptionist` pueden registrar pagos — son los responsables de la caja. Los doctores y asistentes no registran pagos. La factura debe pertenecer al paciente y al tenant.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/invoices/{invoice_id}/payments
```

**Rate Limiting:**
- 30 requests por minuto por usuario
- Redis sliding window: `dentalos:rl:payment_record:{user_id}` (TTL 60s)

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
| invoice_id | Yes | UUID | UUID v4 valido | ID de la factura a pagar | inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "amount": "integer (required) — monto del pago en centavos de la moneda del tenant, debe ser > 0",
  "method": "string (required) — cash | credit_card | debit_card | bank_transfer | insurance | payment_plan",
  "payment_date": "string (required) — ISO8601 date, fecha efectiva del pago (puede ser retroactiva max 30d)",
  "reference_number": "string (optional) — numero de referencia/transaccion, max 100 chars",
  "notes": "string (optional) — notas internas, max 500 chars",
  "payment_plan_id": "UUID (conditional) — requerido si method=payment_plan, ID del plan de pago"
}
```

**Example Request (pago en efectivo, total):**
```json
{
  "amount": 162000000,
  "method": "cash",
  "payment_date": "2026-02-25",
  "notes": "Pago total en efectivo. Recibo entregado."
}
```

**Example Request (pago parcial con transferencia):**
```json
{
  "amount": 80000000,
  "method": "bank_transfer",
  "payment_date": "2026-02-25",
  "reference_number": "TRF-20260225-001",
  "notes": "Primera cuota acordada."
}
```

**Example Request (pago via seguro):**
```json
{
  "amount": 120000000,
  "method": "insurance",
  "payment_date": "2026-02-25",
  "reference_number": "SEG-SURA-20260225-A",
  "notes": "Cubierto por seguro Sura. Copago del paciente pendiente."
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "payment": {
    "id": "UUID",
    "invoice_id": "UUID",
    "amount": "integer — en centavos",
    "method": "string",
    "payment_date": "string — ISO8601 date",
    "reference_number": "string | null",
    "notes": "string | null",
    "recorded_by": "UUID",
    "recorded_at": "ISO8601"
  },
  "invoice_updated": {
    "invoice_id": "UUID",
    "invoice_number": "string",
    "previous_balance": "integer — saldo antes del pago, en centavos",
    "amount_paid": "integer — total pagado acumulado, en centavos",
    "balance_due": "integer — saldo pendiente despues del pago, en centavos",
    "status": "string — status actualizado de la factura (puede haber cambiado a 'paid')"
  }
}
```

**Example (pago parcial):**
```json
{
  "payment": {
    "id": "pay_1111aaaa-2222-3333-4444-555566667777",
    "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
    "amount": 80000000,
    "method": "bank_transfer",
    "payment_date": "2026-02-25",
    "reference_number": "TRF-20260225-001",
    "notes": "Primera cuota acordada.",
    "recorded_by": "usr_receptionist-0001-0000-0000-000000000000",
    "recorded_at": "2026-02-25T11:30:00Z"
  },
  "invoice_updated": {
    "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
    "invoice_number": "FAC-2026-00001",
    "previous_balance": 162000000,
    "amount_paid": 80000000,
    "balance_due": 82000000,
    "status": "sent"
  }
}
```

**Example (pago total — factura marcada como paid):**
```json
{
  "payment": {
    "id": "pay_2222bbbb-3333-4444-5555-666677778888",
    "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
    "amount": 82000000,
    "method": "cash",
    "payment_date": "2026-02-28",
    "reference_number": null,
    "notes": "Saldo pendiente cancelado. Pago total completado.",
    "recorded_by": "usr_receptionist-0001-0000-0000-000000000000",
    "recorded_at": "2026-02-28T09:00:00Z"
  },
  "invoice_updated": {
    "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
    "invoice_number": "FAC-2026-00001",
    "previous_balance": 82000000,
    "amount_paid": 162000000,
    "balance_due": 0,
    "status": "paid"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Body malformado, `amount` = 0 o negativo, `method` invalido, `payment_date` en formato incorrecto.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El monto del pago debe ser mayor a cero.",
  "details": {
    "amount": ["El monto debe ser un entero positivo en centavos."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol no autorizado (`doctor`, `assistant`, `patient`).

```json
{
  "error": "forbidden",
  "message": "Solo recepcionistas y administradores pueden registrar pagos."
}
```

#### 404 Not Found
**When:** `patient_id` o `invoice_id` no existen en el tenant.

```json
{
  "error": "invoice_not_found",
  "message": "La factura no fue encontrada."
}
```

#### 409 Conflict
**When:** La factura ya esta en estado `paid` o `cancelled`.

```json
{
  "error": "invoice_already_settled",
  "message": "No se pueden registrar pagos en una factura ya pagada o cancelada."
}
```

#### 422 Unprocessable Entity
**When:** `amount` supera el `balance_due` de la factura, `payment_date` mas de 30 dias en el pasado, `method=payment_plan` sin `payment_plan_id`.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "El monto del pago supera el saldo pendiente de la factura.",
  "details": {
    "amount": ["El monto 200000000 supera el saldo pendiente de 82000000. Usar el saldo exacto para liquidar."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error durante la transaccion de base de datos.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `clinic_owner` o `receptionist`. Si no, 403.
3. Validar body con schema Pydantic:
   - `amount` debe ser integer > 0.
   - `method` debe ser uno de los valores del Enum.
   - `payment_date` formato ISO8601 date valido.
   - Si `method == 'payment_plan'`: `payment_plan_id` requerido.
4. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
5. Buscar la factura `WHERE id = invoice_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no, 404.
6. Verificar que `invoice.status NOT IN ('paid', 'cancelled')`. Si esta en esos estados, 409.
7. Verificar `payment_date`:
   - No puede ser fecha futura (> hoy).
   - No puede ser mas de 30 dias en el pasado (para evitar antedatacion excesiva).
   - Si viola estas reglas, 422 con mensaje descriptivo.
8. Verificar que `amount <= invoice.balance_due`. Si supera el saldo, 422.
9. Si `method == 'payment_plan'`: buscar `payment_plan WHERE id = payment_plan_id AND patient_id = patient_id`. Si no existe, 404.
10. Iniciar transaccion de base de datos:
    a. Insertar registro en `payments`: `invoice_id`, `amount`, `method`, `payment_date`, `reference_number`, `notes`, `recorded_by = user_id`, `recorded_at = now()`.
    b. Calcular nuevo `amount_paid = invoice.amount_paid + amount`.
    c. Calcular nuevo `balance_due = invoice.total - new_amount_paid`.
    d. Determinar nuevo status:
       - Si `balance_due == 0`: `status = 'paid'`, `paid_at = now()`.
       - Si `balance_due > 0` y `invoice.status == 'overdue'`: mantener `overdue` (pago parcial en factura vencida).
       - Si `balance_due > 0` y `invoice.status == 'sent'`: mantener `sent`.
       - Si `balance_due > 0` y `invoice.status == 'draft'`: mantener `draft` (pago en factura aun borrador, permitido).
    e. UPDATE `invoices` SET `amount_paid = new_amount_paid`, `balance_due = new_balance_due`, `status = new_status`, `paid_at = ...`, `updated_at = now()`.
11. Confirmar transaccion.
12. Si `balance_due == 0`: encolar notificacion de pago completo (opcional, via RabbitMQ).
13. Invalidar cache de la factura: DELETE `tenant:{tenant_id}:invoice:{invoice_id}`.
14. Registrar en audit log (critico para transacciones financieras): accion `create`, recurso `payment`, `tenant_id`, `user_id`, `patient_id`, `invoice_id`, `amount`, `method`, `payment_date`.
15. Retornar 201 Created con el pago registrado y el estado actualizado de la factura.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| amount | Integer > 0, <= invoice.balance_due | "El monto debe ser positivo y no superar el saldo pendiente." |
| method | Enum: cash, credit_card, debit_card, bank_transfer, insurance, payment_plan | "Metodo de pago no valido." |
| payment_date | ISO8601 date, no futura, max 30 dias en el pasado | "La fecha de pago no puede ser futura ni mas de 30 dias en el pasado." |
| reference_number | Max 100 chars, caracteres alfanumericos + guion/punto | "La referencia no puede superar los 100 caracteres." |
| notes | Max 500 chars | "Las notas no pueden superar los 500 caracteres." |
| payment_plan_id | UUID v4 requerido si method=payment_plan | "El ID del plan de pago es requerido para este metodo." |

**Business Rules:**

- Un pago no puede superar el saldo pendiente de la factura. No se permiten "sobrepagos" (usar `amount == balance_due` para liquidar exactamente).
- Cuando `balance_due == 0` tras registrar el pago, la factura cambia automaticamente a `paid`.
- Los pagos son inmutables una vez registrados (no hay endpoint de delete/update — usar el audit log para correcciones).
- La fecha de pago puede ser retroactiva hasta 30 dias (para registrar pagos recibidos en efectivo el dia anterior, etc.). No se permite antedatacion de mas de 30 dias.
- La fecha de pago no puede ser futura.
- El registro de pago siempre entra en el audit log con nivel FINANCIAL (alta importancia).
- `method=payment_plan` linkea el pago a un plan de cuotas y puede actualizar el estado de la cuota correspondiente.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Pago exacto al balance_due | `balance_due: 0`, `status: "paid"` automaticamente |
| Pago en factura `draft` | Permitido — `balance_due` se actualiza, status sigue `draft` |
| Pago en factura `overdue` | Permitido — si `balance_due > 0` queda en `overdue`, si = 0 pasa a `paid` |
| Multiples pagos parciales | Cada uno suma a `amount_paid`, la factura pasa a `paid` cuando `balance_due = 0` |
| payment_date = hoy | Valido |
| payment_date = hace 29 dias | Valido |
| payment_date = hace 31 dias | 422: antedatacion excesiva |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `payments`: INSERT — registro del pago con metodo, monto, fecha, referencia
- `invoices`: UPDATE — `amount_paid`, `balance_due`, `status` (posible a `paid`), `paid_at` si aplica

**Example query (SQLAlchemy):**
```python
from sqlalchemy import insert, update

async with session.begin():
    # Insertar pago
    payment_result = await session.execute(
        insert(Payment).values(
            invoice_id=invoice_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            amount=body.amount,
            method=body.method,
            payment_date=body.payment_date,
            reference_number=body.reference_number,
            notes=body.notes,
            payment_plan_id=body.payment_plan_id,
            recorded_by=user_id,
            recorded_at=datetime.utcnow(),
        ).returning(Payment.id)
    )
    payment_id = payment_result.scalar_one()

    # Actualizar factura
    new_amount_paid = invoice.amount_paid + body.amount
    new_balance_due = invoice.total - new_amount_paid
    new_status = "paid" if new_balance_due == 0 else invoice.status
    paid_at = datetime.utcnow() if new_balance_due == 0 else invoice.paid_at

    await session.execute(
        update(Invoice)
        .where(Invoice.id == invoice_id)
        .values(
            amount_paid=new_amount_paid,
            balance_due=new_balance_due,
            status=new_status,
            paid_at=paid_at,
            updated_at=datetime.utcnow(),
        )
    )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:invoice:{invoice_id}`: DELETE — invalida detalle cacheado
- `tenant:{tenant_id}:invoice_list:*`: DELETE PATTERN — invalida listado
- `tenant:{tenant_id}:patient_balance:{patient_id}`: DELETE — invalida balance del paciente (B-09)

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications.invoice_paid | invoice_paid | { invoice_id, patient_id, tenant_id, invoice_number, total, paid_at, clinic_name } | Solo cuando balance_due == 0 (factura completamente pagada) |

### Audit Log

**Audit entry:** Yes — CRITICO para transacciones financieras

- **Action:** create
- **Resource:** payment
- **PHI involved:** No directamente (datos financieros; patient_id como referencia)
- **Financial transaction:** Si — nivel FINANCIAL en el audit log (inmutable, con user_id, timestamp, amount, method, reference)

### Notifications

**Notifications triggered:** Yes (solo cuando la factura queda completamente pagada)

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app (portal) | Factura pagada completamente | Paciente | balance_due == 0 |
| email | invoice_paid | Paciente (opcional, configurable por tenant) | balance_due == 0 |

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 800ms (incluye transaccion multi-tabla y cache invalidation)

### Caching Strategy
- **Strategy:** Sin cache para la respuesta. Invalidacion de caches relacionados.
- **Cache key:** N/A para respuesta
- **TTL:** N/A
- **Invalidation:** Inmediata en cada pago exitoso

### Database Performance

**Queries executed:** 4 (verificar paciente, buscar factura, insert payment, update invoice — todo en transaccion)

**Indexes required:**
- `payments.invoice_id` — INDEX
- `payments.patient_id` — INDEX
- `payments.(tenant_id, payment_date)` — INDEX COMPUESTO para reportes futuros
- `invoices.(id, patient_id, tenant_id, status)` — INDEX COMPUESTO

**N+1 prevention:** No aplica — operacion simple de insert+update.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, invoice_id (URL) | Pydantic UUID | |
| amount | Pydantic int, gt=0 | En centavos — no float |
| method | Pydantic Enum estricto | |
| payment_date | Pydantic date, validacion adicional de rango | |
| reference_number | Pydantic str, strip, max_length=100, regex alfanumerico | |
| notes | Pydantic str, strip, max_length=500, bleach | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Serializacion Pydantic. `notes` sanitizado con bleach.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno directamente. Datos de pago son financieros.

**Audit requirement:** All access logged con nivel FINANCIAL (transaccion financiera critica)

---

## Testing

### Test Cases

#### Happy Path
1. Pago parcial por transferencia
   - **Given:** Factura `sent`, `balance_due: 162000000`, usuario `receptionist`
   - **When:** POST /payments con `amount: 80000000`, `method: "bank_transfer"`, `reference_number: "TRF-001"`
   - **Then:** 201 Created, `balance_due: 82000000`, `invoice.status: "sent"` (sin cambio)

2. Pago total en efectivo — factura se marca como paid
   - **Given:** Factura `sent`, `balance_due: 162000000`
   - **When:** POST con `amount: 162000000`, `method: "cash"`
   - **Then:** 201 Created, `balance_due: 0`, `invoice.status: "paid"`, job encolado en RabbitMQ

3. Pago del saldo restante (ultimo pago de varios parciales)
   - **Given:** Factura con `amount_paid: 80000000`, `balance_due: 82000000`
   - **When:** POST con `amount: 82000000`
   - **Then:** 201 Created, `balance_due: 0`, `status: "paid"`

4. Pago retroactivo (fecha de ayer)
   - **Given:** Factura `sent`
   - **When:** POST con `payment_date: "2026-02-24"` (ayer)
   - **Then:** 201 Created, `payment.payment_date: "2026-02-24"`

#### Edge Cases
1. Pago en factura `overdue` con saldo parcial
   - **Given:** Factura `overdue`, `balance_due: 45000000`
   - **When:** POST con `amount: 20000000`
   - **Then:** 201 Created, `balance_due: 25000000`, `status: "overdue"` (sigue vencida)

2. Pago en factura `draft` (antes de enviar)
   - **Given:** Factura `draft`, `balance_due: 100000000`
   - **When:** POST con `amount: 50000000`
   - **Then:** 201 Created, `balance_due: 50000000`, `status: "draft"`

3. Pago via seguro con referencia
   - **Given:** Factura `sent`
   - **When:** POST con `method: "insurance"`, `reference_number: "SEG-SURA-001"`
   - **Then:** 201 Created, pago registrado con referencia del seguro

#### Error Cases
1. Monto supera balance_due
   - **Given:** `balance_due: 50000000`
   - **When:** POST con `amount: 100000000`
   - **Then:** 422 con mensaje sobre monto excedido

2. Factura ya pagada
   - **Given:** `invoice.status: "paid"`
   - **When:** POST pago
   - **Then:** 409 Conflict

3. Rol `doctor` intenta registrar pago
   - **Given:** JWT con rol `doctor`
   - **When:** POST
   - **Then:** 403 Forbidden

4. payment_date futura
   - **Given:** `payment_date: "2026-12-31"` (futuro)
   - **When:** POST
   - **Then:** 422 con mensaje sobre fecha futura

5. Antedatacion excesiva (> 30 dias)
   - **Given:** `payment_date: "2025-12-01"` (3 meses atras)
   - **When:** POST
   - **Then:** 422 con mensaje sobre limite de antedatacion

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `doctor` (para 403), un `assistant` (para 403).

**Patients:** Un paciente activo del tenant.

**Invoices:** Una `sent` con `balance_due` completo, una `overdue`, una `paid` (para 409), una `draft`.

### Mocking Strategy

- **Redis:** fakeredis para cache invalidation y rate limiting
- **Database:** SQLite en memoria con esquema de billing y payments
- **RabbitMQ:** Mock del publisher para verificar job encolado en pago total
- **Date:** Mockear `date.today()` para tests de payment_date

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Pago parcial actualiza `amount_paid` y `balance_due` correctamente
- [ ] Pago total cambia `status` a `paid` y registra `paid_at`
- [ ] No se puede superar el `balance_due` con un pago
- [ ] Facturas `paid` y `cancelled` retornan 409
- [ ] Solo `clinic_owner` y `receptionist` pueden registrar pagos (403 para otros roles)
- [ ] Audit log FINANCIAL registrado en cada pago
- [ ] Cache de factura y balance del paciente invalidados
- [ ] `payment_date` valida: no futura, max 30 dias pasado
- [ ] Notificacion encolada cuando factura queda completamente pagada
- [ ] All test cases pass
- [ ] Performance targets met (< 800ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Eliminacion o modificacion de pagos (inmutables por integridad financiera)
- Listado de pagos de una factura (ver B-02 invoice-get.md — incluidos en detalle)
- Listado de todos los pagos de un paciente (ver B-08 payment-list.md)
- Devolucion o reembolso de pagos (post-MVP)
- Pago con QR o link de pago en linea (post-MVP)
- Procesamiento de tarjeta de credito en tiempo real (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (amount en centavos, method Enum, payment_date, reference)
- [x] All outputs defined (pago registrado + invoice_updated con nuevo balance)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (no superar balance, no antedatacion excesiva)
- [x] Error cases enumerated
- [x] Auth requirements explicit (solo receptionist y clinic_owner)
- [x] Side effects listed (DB transaccion atomica, cache, RabbitMQ, audit FINANCIAL)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Transaccion atomica para payment + invoice update
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level estricto (solo 2 roles)
- [x] Input sanitization (amount en centavos como int, no float)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] Audit FINANCIAL inmutable
- [x] No PHI en los datos del pago

### Hook 4: Performance & Scalability
- [x] Response time target (< 800ms)
- [x] Transaccion atomica eficiente
- [x] Cache invalidacion inmediata
- [x] Indexes para queries de reporte

### Hook 5: Observability
- [x] Audit log FINANCIAL (nivel critico)
- [x] Structured logging con amount, method, invoice_id
- [x] Error tracking (Sentry-compatible)
- [x] RabbitMQ job monitoring para notificacion paid

### Hook 6: Testability
- [x] Test cases enumerated (pago parcial, total, overdue, draft)
- [x] Test data requirements specified
- [x] Mocking strategy (Redis, RabbitMQ, date)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
