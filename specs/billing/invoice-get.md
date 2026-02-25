# Invoice Get (B-02)

---

## Overview

**Feature:** Obtener el detalle completo de una factura especifica para un paciente, incluyendo todos los items de linea, historial de pagos aplicados, saldo pendiente y metadatos de emision. Es el endpoint principal para vista de detalle de factura en el flujo de atencion y en el portal del paciente.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), B-07 (payment-record.md), patients (Patient), infra/authentication-rules.md, database-architecture.md (`invoices`, `invoice_items`, `payments`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor, patient
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Un paciente (rol `patient`) solo puede ver sus propias facturas. Los doctores pueden ver facturas de sus pacientes. Recepcionistas y `clinic_owner` pueden ver todas las facturas del tenant.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/invoices/{invoice_id}
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
| invoice_id | Yes | UUID | UUID v4 valido | ID de la factura | inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890 |

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
  "invoice_number": "string — FAC-{YYYY}-{NNNNN}",
  "patient_id": "UUID",
  "patient": {
    "id": "UUID",
    "full_name": "string",
    "document_number": "string",
    "email": "string | null",
    "phone": "string | null"
  },
  "quotation_id": "UUID | null",
  "treatment_plan_id": "UUID | null",
  "doctor_id": "UUID | null",
  "doctor_name": "string | null",
  "status": "string — draft | sent | paid | overdue | cancelled",
  "currency": "string — ISO 4217",
  "subtotal": "integer — en centavos",
  "discount_percentage": "number",
  "discount_amount": "integer — en centavos",
  "tax_percentage": "number",
  "tax_amount": "integer — en centavos",
  "total": "integer — en centavos",
  "amount_paid": "integer — total pagado acumulado en centavos",
  "balance_due": "integer — saldo pendiente en centavos",
  "due_date": "string — ISO8601 date",
  "sent_at": "ISO8601 | null",
  "paid_at": "ISO8601 | null",
  "cancelled_at": "ISO8601 | null",
  "notes": "string | null",
  "items": [
    {
      "id": "UUID",
      "service_id": "UUID | null",
      "description": "string",
      "quantity": "integer",
      "unit_price": "integer — en centavos",
      "subtotal": "integer — en centavos",
      "tax_exempt": "boolean"
    }
  ],
  "payments": [
    {
      "id": "UUID",
      "amount": "integer — en centavos",
      "method": "string — cash | credit_card | debit_card | bank_transfer | insurance | payment_plan",
      "payment_date": "string — ISO8601 date",
      "reference_number": "string | null",
      "notes": "string | null",
      "recorded_by": "UUID",
      "recorded_at": "ISO8601"
    }
  ],
  "pdf_url": "string | null — URL firmada S3, puede estar expirada",
  "created_by": "UUID",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Example:**
```json
{
  "id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
  "invoice_number": "FAC-2026-00001",
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "patient": {
    "id": "pt_550e8400-e29b-41d4-a716-446655440000",
    "full_name": "Juan Carlos Perez Gomez",
    "document_number": "1020304050",
    "email": "juan.perez@gmail.com",
    "phone": "+573001234567"
  },
  "quotation_id": "quot_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "treatment_plan_id": null,
  "doctor_id": "usr_550e8400-e29b-41d4-a716-446655440000",
  "doctor_name": "Dra. Maria Lopez Vargas",
  "status": "sent",
  "currency": "COP",
  "subtotal": 162000000,
  "discount_percentage": 0,
  "discount_amount": 0,
  "tax_percentage": 0,
  "tax_amount": 0,
  "total": 162000000,
  "amount_paid": 80000000,
  "balance_due": 82000000,
  "due_date": "2026-03-31",
  "sent_at": "2026-02-25T10:00:00Z",
  "paid_at": null,
  "cancelled_at": null,
  "notes": null,
  "items": [
    {
      "id": "ii_aabb1122-ccdd-3344-eeff-556677889900",
      "service_id": "svc_aabb1122-ccdd-3344-eeff-556677889900",
      "description": "Resina Oclusal — Diente 16",
      "quantity": 1,
      "unit_price": 35000000,
      "subtotal": 35000000,
      "tax_exempt": true
    },
    {
      "id": "ii_bbcc2233-ddee-4455-ff00-667788990011",
      "service_id": "svc_bbcc2233-ddee-4455-ff00-667788990011",
      "description": "Endodoncia Unirradicular — Diente 21",
      "quantity": 1,
      "unit_price": 85000000,
      "subtotal": 85000000,
      "tax_exempt": true
    },
    {
      "id": "ii_ccdd3344-eeff-5566-0011-778899001122",
      "service_id": "svc_ccdd3344-eeff-5566-0011-778899001122",
      "description": "Limpieza y Profilaxis",
      "quantity": 1,
      "unit_price": 42000000,
      "subtotal": 42000000,
      "tax_exempt": true
    }
  ],
  "payments": [
    {
      "id": "pay_1111aaaa-2222-3333-4444-555566667777",
      "amount": 80000000,
      "method": "bank_transfer",
      "payment_date": "2026-02-25",
      "reference_number": "TRF-20260225-001",
      "notes": "Pago inicial acordado",
      "recorded_by": "usr_receptionist-0001-0000-0000-000000000000",
      "recorded_at": "2026-02-25T11:30:00Z"
    }
  ],
  "pdf_url": "https://storage.dentalos.com/invoices/tn_7c9e/FAC-2026-00001.pdf?X-Amz-Signature=...&X-Amz-Expires=86400",
  "created_by": "usr_receptionist-0001-0000-0000-000000000000",
  "created_at": "2026-02-25T09:00:00Z",
  "updated_at": "2026-02-25T11:30:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol `patient` intentando ver facturas de otro paciente. Rol no autorizado.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver esta factura."
}
```

#### 404 Not Found
**When:** `patient_id` o `invoice_id` no existen en el tenant, o la factura no pertenece al paciente.

```json
{
  "error": "invoice_not_found",
  "message": "La factura no fue encontrada."
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
2. Verificar que el rol sea uno de: `clinic_owner`, `receptionist`, `doctor`, `patient`. Si no, retornar 403.
3. Verificar que el paciente (`patient_id`) existe y pertenece al tenant. Si no, 404.
4. Si el rol es `patient`: verificar que `user.patient_id == patient_id`. Si no coincide, retornar 403 (un paciente no puede ver facturas de otro).
5. Buscar la factura `WHERE id = invoice_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no existe, 404.
6. Cargar datos del paciente para la respuesta (nombre, documento, email, telefono).
7. Cargar nombre del doctor si `doctor_id` no es null.
8. Cargar `invoice_items` (JOIN con `service_catalog` para datos adicionales si se necesitan).
9. Cargar `payments` asociados a la factura, ordenados por `payment_date ASC`.
10. Verificar si la factura debe marcarse como `overdue`:
    - Si `status = 'sent'` y `due_date < hoy` y `balance_due > 0`: actualizar `status = 'overdue'` en base de datos (operacion lazy).
11. Construir la respuesta con todos los datos consolidados.
12. Registrar en audit log: accion `read`, recurso `invoice`, `tenant_id`, `user_id`, `invoice_id`.
13. Retornar 200 OK con la factura completa.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | UUID v4, debe pertenecer al tenant | "El paciente no fue encontrado." |
| invoice_id (URL) | UUID v4, factura debe pertenecer al paciente y tenant | "La factura no fue encontrada." |

**Business Rules:**

- El saldo `balance_due` se calcula siempre como `total - amount_paid`. El campo `amount_paid` se actualiza en cada pago registrado (B-07).
- Si la factura tiene `status = 'sent'` y `due_date` ya paso y aun hay saldo, se actualiza lazy a `overdue` en la respuesta de este endpoint.
- El `pdf_url` puede estar expirado (URL S3 firmada de 24h). El frontend debe detectar esto y solicitar regeneracion via B-06.
- Los pagos se retornan ordenados por fecha ascendente para facilitar la visualizacion del historial.
- Rol `patient` solo puede acceder a facturas de su propio perfil de paciente.
- El campo `patient` en la respuesta incluye datos de contacto para facilitar la vista de detalle sin llamadas adicionales.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Factura sin pagos | `payments: []`, `amount_paid: 0`, `balance_due = total` |
| Factura totalmente pagada | `status: "paid"`, `balance_due: 0`, `paid_at` con timestamp |
| Factura vencida (sent + due_date pasada) | `status: "overdue"` actualizado lazy en este GET |
| Paciente sin email ni telefono | Campos `email: null`, `phone: null` en objeto `patient` |
| `pdf_url` expirada | Se retorna la URL almacenada aunque este expirada — frontend maneja regeneracion |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `invoices`: UPDATE — `status = 'overdue'` si aplica (lazy update en lectura)

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Cargar factura con items y pagos en una query eficiente
stmt = (
    select(Invoice)
    .where(Invoice.id == invoice_id)
    .where(Invoice.patient_id == patient_id)
    .where(Invoice.tenant_id == tenant_id)
    .options(
        selectinload(Invoice.items),
        selectinload(Invoice.payments),
    )
)
result = await session.execute(stmt)
invoice = result.scalar_one_or_none()

# Lazy overdue update
if invoice and invoice.status == "sent" and invoice.due_date < date.today() and invoice.balance_due > 0:
    invoice.status = "overdue"
    await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:invoice:{invoice_id}`: SET — cache de detalle de factura

**Cache TTL:** 5 minutos (invalida en updates de B-04, B-05, B-07)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno.

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** invoice
- **PHI involved:** No (datos financieros; nombre del paciente es PII pero no PHI clinico)

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 150ms (con cache)
- **Maximum acceptable:** < 400ms (sin cache, con JOINs)

### Caching Strategy
- **Strategy:** Redis cache del detalle de factura serializado
- **Cache key:** `tenant:{tenant_id}:invoice:{invoice_id}`
- **TTL:** 5 minutos
- **Invalidation:** En cualquier UPDATE de la factura (B-04, B-05, B-07) o nuevo pago

### Database Performance

**Queries executed:** 1-3 (factura + items + pagos via selectinload, o 1 query con JOINs)

**Indexes required:**
- `invoices.(id, patient_id, tenant_id)` — INDEX COMPUESTO (clave principal de lookup)
- `invoice_items.invoice_id` — INDEX
- `payments.invoice_id` — INDEX
- `invoices.status` — INDEX (para lazy overdue check)
- `invoices.due_date` — INDEX

**N+1 prevention:** Items y pagos cargados con `selectinload` en una sola query (eager loading). Datos del paciente con JOIN en la misma query o desde cache.

### Pagination

**Pagination:** No — retorna todos los items y pagos de la factura (bounded por la naturaleza del dato)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID | |
| invoice_id (URL) | Pydantic UUID | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Nombre del paciente, numero de documento (PII). No hay datos clinicos en la factura.

**Audit requirement:** All access logged (lectura de datos de factura con PII del paciente)

---

## Testing

### Test Cases

#### Happy Path
1. Obtener factura con pagos parciales
   - **Given:** Factura `sent` con total 1.620.000 COP, un pago de 800.000 COP registrado
   - **When:** GET /api/v1/patients/{id}/invoices/{invoice_id}
   - **Then:** 200 OK, `amount_paid: 80000000`, `balance_due: 82000000`, `payments` con 1 elemento

2. Paciente ve su propia factura (rol patient)
   - **Given:** Usuario con rol `patient`, `patient_id` coincide con el de la URL
   - **When:** GET con JWT de paciente
   - **Then:** 200 OK con datos completos de la factura

3. Factura sin pagos
   - **Given:** Factura `draft` recien creada
   - **When:** GET
   - **Then:** 200 OK, `payments: []`, `amount_paid: 0`, `balance_due = total`

4. Lazy overdue update
   - **Given:** Factura `sent`, `due_date: "2026-01-15"` (pasada), `balance_due > 0`
   - **When:** GET
   - **Then:** 200 OK con `status: "overdue"` (actualizado en DB durante la consulta)

#### Edge Cases
1. Factura totalmente pagada
   - **Given:** Factura `paid`, todos los pagos registrados
   - **When:** GET
   - **Then:** 200 OK, `balance_due: 0`, `paid_at` con timestamp

2. Doctor_id null (factura sin doctor asignado)
   - **Given:** Factura creada sin `doctor_id`
   - **When:** GET
   - **Then:** 200 OK, `doctor_id: null`, `doctor_name: null`

#### Error Cases
1. Paciente ve factura de otro paciente (rol patient)
   - **Given:** Usuario `patient` cuyo `patient_id` no coincide con la URL
   - **When:** GET /api/v1/patients/{otro_patient_id}/invoices/{invoice_id}
   - **Then:** 403 Forbidden

2. Factura de otro tenant
   - **Given:** `invoice_id` de tenant B, usuario en tenant A
   - **When:** GET
   - **Then:** 404 Not Found

3. patient_id no existe
   - **Given:** UUID inexistente en el tenant
   - **When:** GET
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `doctor`, un `patient` (con `patient_id` vinculado).

**Patients:** Un paciente con email y telefono, un paciente sin datos de contacto.

**Invoices:** Una factura `draft` sin pagos, una `sent` con pagos parciales, una `paid`, una vencida.

**Payments:** 1-2 pagos asociados a la factura de prueba.

### Mocking Strategy

- **Redis:** fakeredis para cache de detalle
- **Database:** SQLite en memoria con esquema completo de billing
- **Date:** Mockear `date.today()` para probar lazy overdue update

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Retorna factura completa con items y pagos anidados
- [ ] `balance_due` siempre es `total - amount_paid` (calculado, no almacenado stale)
- [ ] Rol `patient` solo puede ver sus propias facturas (403 en las ajenas)
- [ ] Lazy overdue update funciona correctamente
- [ ] Cache de 5 minutos implementado y verificado
- [ ] `pdf_url` incluido en respuesta aunque este expirado
- [ ] Datos del paciente incluidos en la respuesta (sin llamada adicional)
- [ ] All test cases pass
- [ ] Performance targets met (< 400ms sin cache)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listado de multiples facturas (ver B-03 invoice-list.md)
- Actualizacion de factura (ver B-04 invoice-update.md)
- Generacion de PDF (ver B-06 invoice-pdf.md)
- Registro de pagos (ver B-07 payment-record.md)
- Descarga del documento DIAN electronico

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (URL params, no body)
- [x] All outputs defined (response completo con items y pagos anidados)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant, restriccion patient)
- [x] Side effects listed (lazy overdue update, audit log, cache)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, selectinload)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context, patient restriction)
- [x] Input sanitization defined (UUID validation)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] PII en respuesta (nombre paciente) — logged
- [x] Audit trail para lectura

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 400ms, < 150ms con cache)
- [x] Caching strategy (Redis 5min, invalidacion en writes)
- [x] DB queries optimizados (selectinload, indexes listados)
- [x] Pagination N/A (factura es un objeto bounded)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, invoice_id incluidos)
- [x] Audit log entries defined (read)
- [x] Error tracking (Sentry-compatible)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (Redis, date mock para overdue)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
