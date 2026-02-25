# Invoice Create (B-01)

---

## Overview

**Feature:** Crear una factura para un paciente con items de procedimientos realizados, items de plan de tratamiento, o items manuales. Calcula impuestos segun el pais del tenant (IVA 19% Colombia para servicios no exentos, configurable por adaptador de cumplimiento). Asigna numero secuencial por tenant y anio (FAC-2026-0001). Soporta la conversion automatica desde cotizacion aprobada (auto-flow: Cotizacion → Factura).

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-14 (service-catalog.md), B-16 (quotation-create.md), treatment-plans (TreatmentPlan, TreatmentPlanItem), patients (Patient), infra/authentication-rules.md, database-architecture.md (`invoices`, `invoice_items`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** El paciente referenciado en la URL debe pertenecer al mismo tenant. Los doctores solo pueden crear facturas para sus propios pacientes a menos que tengan permiso especial. Los asistentes no pueden crear facturas.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/invoices
```

**Rate Limiting:**
- 60 requests por minuto por usuario
- Redis sliding window: `dentalos:rl:invoice_create:{user_id}` (TTL 60s)

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
| patient_id | Yes | UUID | UUID v4 valido | ID del paciente a quien se emite la factura | pt_550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "source": "string (optional) — manual | quotation | treatment_plan — default: manual",
  "quotation_id": "UUID (conditional) — requerido si source=quotation",
  "treatment_plan_id": "UUID (conditional) — requerido si source=treatment_plan",
  "items": [
    {
      "service_id": "UUID (optional) — resuelve descripcion y precio desde catalogo",
      "description": "string (required si no hay service_id) — descripcion libre del servicio",
      "quantity": "integer (optional) — default: 1, min: 1",
      "unit_price": "integer (required si no hay service_id) — precio en centavos de la moneda del tenant",
      "tax_exempt": "boolean (optional) — sobreescribe la exencion de impuesto del item, default: segun catalogo"
    }
  ],
  "discount_percentage": "number (optional) — descuento global 0-100, default: 0",
  "due_date": "string (optional) — fecha de vencimiento ISO8601 date, default: fecha actual + 30 dias",
  "notes": "string (optional) — notas internas o para el paciente, max 1000 chars",
  "doctor_id": "UUID (optional) — doctor responsable de la atencion, para comisiones"
}
```

**Example Request (desde cotizacion aprobada):**
```json
{
  "source": "quotation",
  "quotation_id": "quot_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "due_date": "2026-03-31",
  "doctor_id": "usr_550e8400-e29b-41d4-a716-446655440000"
}
```

**Example Request (manual con items):**
```json
{
  "source": "manual",
  "items": [
    {
      "service_id": "svc_aabb1122-ccdd-3344-eeff-556677889900",
      "quantity": 1,
      "description": "Consulta inicial y valoracion"
    },
    {
      "description": "Material de impresion dental",
      "quantity": 2,
      "unit_price": 75000,
      "tax_exempt": false
    }
  ],
  "discount_percentage": 5,
  "due_date": "2026-03-15",
  "notes": "Pago acordado en 2 cuotas.",
  "doctor_id": "usr_550e8400-e29b-41d4-a716-446655440000"
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
  "invoice_number": "string — FAC-{YYYY}-{NNNNN}",
  "patient_id": "UUID",
  "quotation_id": "UUID | null",
  "treatment_plan_id": "UUID | null",
  "doctor_id": "UUID | null",
  "status": "draft",
  "currency": "string — ISO 4217 (COP, MXN, CLP, ARS, PEN)",
  "subtotal": "integer — en centavos",
  "discount_percentage": "number",
  "discount_amount": "integer — en centavos",
  "tax_percentage": "number",
  "tax_amount": "integer — en centavos",
  "total": "integer — en centavos",
  "amount_paid": "integer — 0 en creacion",
  "balance_due": "integer — igual a total en creacion",
  "due_date": "string — ISO8601 date",
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
  "quotation_id": "quot_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "treatment_plan_id": null,
  "doctor_id": "usr_550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "currency": "COP",
  "subtotal": 162000000,
  "discount_percentage": 0,
  "discount_amount": 0,
  "tax_percentage": 0,
  "tax_amount": 0,
  "total": 162000000,
  "amount_paid": 0,
  "balance_due": 162000000,
  "due_date": "2026-03-31",
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
  "created_by": "usr_receptionist-0001-0000-0000-000000000000",
  "created_at": "2026-02-25T09:00:00Z",
  "updated_at": "2026-02-25T09:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** `source` invalido, ni items ni source valido provistos, ambos `quotation_id` e `items` presentes cuando source=manual.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Fuente de factura invalida. Debe especificar 'manual', 'quotation' o 'treatment_plan'.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol no autorizado (`assistant`, `patient`) o paciente pertenece a otro tenant.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para crear facturas para este paciente."
}
```

#### 404 Not Found
**When:** `patient_id`, `quotation_id`, `treatment_plan_id` o `doctor_id` no existen en el tenant.

```json
{
  "error": "patient_not_found",
  "message": "El paciente no fue encontrado."
}
```

#### 409 Conflict
**When:** Ya existe una factura activa para la misma cotizacion o plan de tratamiento.

```json
{
  "error": "invoice_already_exists",
  "message": "Ya existe una factura para esta cotizacion. Revisar FAC-2026-00001."
}
```

#### 422 Unprocessable Entity
**When:** Items invalidos, `service_id` no encontrado en catalogo, precio faltante para item manual, descuento fuera de rango.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "No se pudo crear la factura.",
  "details": {
    "items[1].unit_price": ["El precio unitario es requerido para items sin servicio del catalogo."],
    "discount_percentage": ["El descuento debe estar entre 0 y 100."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error al generar el numero secuencial o al persistir la factura en la base de datos.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `clinic_owner`, `receptionist` o `doctor`. Si no, retornar 403.
3. Validar body con schema Pydantic segun `source`:
   - Si `source=quotation`: `quotation_id` requerido, `items` no debe estar presente.
   - Si `source=treatment_plan`: `treatment_plan_id` requerido, `items` no debe estar presente.
   - Si `source=manual` o no se especifica: `items` debe tener al menos 1 elemento.
4. Verificar que el paciente (`patient_id`) existe y pertenece al tenant. Si no, 404.
5. Si `doctor_id` se provee, verificar que el usuario con ese ID existe y tiene rol `doctor` en el tenant. Si no, 404.
6. **Rama A — desde cotizacion:**
   a. Buscar cotizacion `WHERE id = quotation_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no, 404.
   b. Verificar que la cotizacion tiene `status = 'approved'`. Si tiene otro estado, 422 con mensaje descriptivo.
   c. Verificar que no exista factura activa para la cotizacion (`WHERE quotation_id = quotation_id AND status NOT IN ('cancelled')`). Si existe, 409.
   d. Copiar items de `quotation_items` a items de factura, preservando descripciones, cantidades y precios.
   e. Heredar `discount_percentage` y `tax_percentage` de la cotizacion.
7. **Rama B — desde plan de tratamiento:**
   a. Buscar plan `WHERE id = treatment_plan_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no, 404.
   b. Verificar que no exista factura activa para el plan. Si existe, 409.
   c. Cargar `treatment_plan_items` con JOIN a `service_catalog`. Resolver precios del catalogo para cada item.
   d. Construir items de factura con descripcion del procedimiento (incluyendo diente si aplica), cantidad, precio del catalogo.
8. **Rama C — manual:**
   a. Para cada item con `service_id`: buscar en `service_catalog` del tenant. Si no existe, agregar a errores.
   b. Si `unit_price` se provee en el item, usarlo; si no, usar el del catalogo.
   c. Si item no tiene `service_id` y no tiene `unit_price`, agregar a errores de validacion.
   d. Si hay errores acumulados, retornar 422.
9. Obtener configuracion de impuestos del tenant segun `tenant.country`:
   - Colombia (CO): servicios odontologicos exentos de IVA = 0%. Solo materiales no medicos pueden tener IVA 19%.
   - Mexico (MX): IVA 16% sobre todos los servicios.
   - Chile (CL), Argentina (AR), Peru (PE): 0% (configurar en adaptador de cumplimiento).
   - El campo `tax_exempt` por item permite sobreescribir.
10. Calcular totales (todos en centavos):
    - `subtotal` = suma de (quantity * unit_price) por item.
    - `discount_amount` = round(subtotal * discount_percentage / 100).
    - `subtotal_after_discount` = subtotal - discount_amount.
    - `taxable_subtotal` = suma de subtotales de items donde `tax_exempt = false`.
    - `tax_amount` = round(taxable_subtotal * tax_percentage / 100).
    - `total` = subtotal_after_discount + tax_amount.
    - `balance_due` = total (en creacion, sin pagos).
11. Generar numero secuencial con lock distribuido Redis:
    - Key: `tenant:{tenant_id}:invoice_sequence:{year}`.
    - Operacion atomica INCR. Formatear como `FAC-{YYYY}-{NNNNN}` con 5 digitos (ej: FAC-2026-00001).
12. Calcular `due_date`: si no se provee, fecha actual + 30 dias en timezone del tenant.
13. Iniciar transaccion de base de datos.
14. Insertar en `invoices` con `status = 'draft'`, `amount_paid = 0`.
15. Insertar en `invoice_items` (un registro por item).
16. Si viene de cotizacion, actualizar `quotations.invoice_id = invoice.id`.
17. Si viene de plan de tratamiento, actualizar `treatment_plans.invoice_id = invoice.id`.
18. Confirmar transaccion.
19. Registrar en audit log: accion `create`, recurso `invoice`, `tenant_id`, `user_id`, `patient_id`, `invoice_id`, `total`.
20. Retornar 201 Created con la factura completa.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | UUID v4, debe pertenecer al tenant | "El paciente no fue encontrado." |
| source | Enum: manual, quotation, treatment_plan | "Fuente de factura invalida." |
| quotation_id | UUID v4, cotizacion debe estar en estado approved | "La cotizacion debe estar aprobada para generar una factura." |
| items | Minimo 1 elemento cuando source=manual | "Debe incluir al menos un servicio." |
| items[].unit_price | Integer > 0 en centavos si no hay service_id | "El precio unitario es requerido." |
| discount_percentage | Float entre 0.0 y 100.0 | "El descuento debe estar entre 0 y 100." |
| due_date | Fecha futura (>= hoy) en formato ISO8601 | "La fecha de vencimiento no puede ser en el pasado." |
| notes | Max 1000 chars | "Las notas no pueden superar los 1000 caracteres." |

**Business Rules:**

- Todos los valores monetarios se almacenan y transmiten en centavos (integer) para evitar errores de punto flotante. COP cents = pesos / 100 (1 peso = 1 cent para precision).
- El numero de factura es secuencial por tenant y anio, e inmutable una vez asignado.
- La factura se crea siempre en estado `draft`. Para enviarla al paciente, usar B-05.
- Una cotizacion aprobada solo puede generar una factura activa (no cancelada).
- El impuesto se aplica sobre el subtotal de items no exentos, despues del descuento global.
- Si `source=quotation` y la cotizacion tiene descuento, se hereda; puede sobreescribirse con `discount_percentage` en el body.
- El campo `doctor_id` vincula la factura al doctor para el calculo de comisiones (B-12).
- Los recepcionistas y `clinic_owner` pueden crear facturas para cualquier paciente del tenant.
- Los doctores pueden crear facturas solo para sus propios pacientes (verificar asignacion en `patient_doctors`).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Cotizacion en estado `draft` (no aprobada) | 422: "La cotizacion debe estar aprobada para generar una factura." |
| Plan de tratamiento sin items | 422: "El plan de tratamiento no tiene procedimientos." |
| Descuento del 100% | Valido: total = tax_amount sobre items no exentos |
| Item con quantity = 0 | 422: la cantidad debe ser al menos 1 |
| Mismo paciente, multiple facturas draft | Permitido — no hay restriccion de una factura draft por paciente |
| due_date igual a hoy | Valido |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `invoices`: INSERT — nueva factura en estado draft con `amount_paid = 0`
- `invoice_items`: INSERT — un registro por item de la factura
- `quotations`: UPDATE — `invoice_id` si se genera desde cotizacion
- `treatment_plans`: UPDATE — `invoice_id` si se genera desde plan de tratamiento

**Example query (SQLAlchemy):**
```python
from sqlalchemy import insert, update

async with session.begin():
    invoice_result = await session.execute(
        insert(Invoice).values(
            tenant_id=tenant_id,
            patient_id=patient_id,
            quotation_id=body.quotation_id,
            treatment_plan_id=body.treatment_plan_id,
            doctor_id=body.doctor_id,
            invoice_number=invoice_number,
            status="draft",
            currency=tenant.currency,
            subtotal=subtotal,
            discount_percentage=body.discount_percentage or 0,
            discount_amount=discount_amount,
            tax_percentage=tax_percentage,
            tax_amount=tax_amount,
            total=total,
            amount_paid=0,
            balance_due=total,
            due_date=due_date,
            notes=body.notes,
            created_by=user_id,
        ).returning(Invoice.id)
    )
    invoice_id = invoice_result.scalar_one()

    for item in computed_items:
        await session.execute(
            insert(InvoiceItem).values(
                invoice_id=invoice_id,
                service_id=item.service_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.quantity * item.unit_price,
                tax_exempt=item.tax_exempt,
            )
        )

    if body.quotation_id:
        await session.execute(
            update(Quotation)
            .where(Quotation.id == body.quotation_id)
            .values(invoice_id=invoice_id)
        )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:invoice_sequence:{year}`: INCR atomico — contador secuencial de facturas

**Cache TTL:** Permanente para el contador (respaldado tambien en tabla `invoice_sequences`)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno en creacion (draft). El envio se realiza en B-05 (invoice-send).

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** invoice
- **PHI involved:** No (datos financieros, no clinicos directos)

### Notifications

**Notifications triggered:** No — la factura draft no genera notificacion. Ver B-05 (invoice-send) para notificacion al paciente.

---

## Performance

### Expected Response Time
- **Target:** < 500ms
- **Maximum acceptable:** < 1500ms (incluye lookup catalogo, calculos y transaccion multi-tabla)

### Caching Strategy
- **Strategy:** No se cachea la factura creada. Catalogo de servicios puede leerse desde cache (B-14, TTL 30min).
- **Cache key:** `tenant:{tenant_id}:invoice_sequence:{year}` (solo para secuencia)
- **TTL:** Permanente para secuencia
- **Invalidation:** N/A para secuencia; catalogo invalidado en updates de B-15

### Database Performance

**Queries executed:** 4-N (verificar paciente, resolver source, lookup catalogo IN query, insert invoice, insert N items, update source)

**Indexes required:**
- `invoices.patient_id` — INDEX
- `invoices.tenant_id` — INDEX
- `invoices.(quotation_id, status)` — INDEX COMPUESTO para verificacion de conflicto
- `invoices.(treatment_plan_id, status)` — INDEX COMPUESTO
- `invoices.invoice_number` — UNIQUE por tenant (parcial)
- `invoice_items.invoice_id` — INDEX
- `service_catalog.(tenant_id, id)` — INDEX COMPUESTO

**N+1 prevention:** Lookup de catalogo con una sola query `WHERE id = ANY(:service_ids) AND tenant_id = :tenant_id`.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID | |
| quotation_id | Pydantic UUID, opcional | |
| items[].description | Pydantic str, strip, max_length=500, bleach | Puede aparecer en PDF de factura |
| notes | Pydantic str, strip, max_length=1000, bleach | Aparece en PDF y emails |
| discount_percentage | Pydantic float, ge=0, le=100 | |
| items[].unit_price | Pydantic int, gt=0 | En centavos |
| due_date | Pydantic date, >= today | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic. Campos que van a PDF sanitizados con bleach antes de almacenar.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno directamente — datos financieros. El `patient_id` es referencia pero no expone datos clinicos.

**Audit requirement:** Write-only logged (creacion de factura)

---

## Testing

### Test Cases

#### Happy Path
1. Crear factura desde cotizacion aprobada
   - **Given:** Cotizacion `approved` con 3 items, tenant Colombia (IVA 0%), usuario `receptionist`
   - **When:** POST /api/v1/patients/{id}/invoices con `source: "quotation"`, `quotation_id`
   - **Then:** 201 Created, items heredados de la cotizacion, `invoice_number: "FAC-2026-00001"`, `tax_amount: 0`, `status: "draft"`

2. Crear factura manual con descuento
   - **Given:** 2 servicios en catalogo, `discount_percentage: 10`, tenant MX (IVA 16%)
   - **When:** POST con `source: "manual"`, items manuales
   - **Then:** 201 Created, `discount_amount` correcto, `tax_amount` calculado sobre subtotal post-descuento de items no exentos

3. Numero secuencial incrementa por anio
   - **Given:** Ultima factura del tenant es `FAC-2026-00005`
   - **When:** POST nueva factura
   - **Then:** `invoice_number: "FAC-2026-00006"`

4. Doctor_id vincula factura para comisiones
   - **Given:** `doctor_id` valido en el body
   - **When:** POST factura manual
   - **Then:** 201 Created, `doctor_id` en la respuesta

#### Edge Cases
1. due_date no especificada
   - **Given:** Body sin `due_date`
   - **When:** POST factura
   - **Then:** `due_date` = fecha actual + 30 dias del tenant

2. Cotizacion ya tiene factura activa
   - **Given:** Cotizacion `approved` con `invoice_id` ya asignado
   - **When:** POST con el mismo `quotation_id`
   - **Then:** 409 Conflict con referencia a la factura existente

3. Items con tax_exempt=false (tenant Colombia, material no medico)
   - **Given:** Item con `tax_exempt: false`, tenant CO
   - **When:** POST con ese item
   - **Then:** IVA 19% aplicado solo sobre ese item

#### Error Cases
1. Cotizacion en estado `draft` (no aprobada)
   - **Given:** Cotizacion con `status: "draft"`
   - **When:** POST con `source: "quotation"`, `quotation_id`
   - **Then:** 422 con mensaje sobre estado requerido

2. Paciente de otro tenant
   - **Given:** `patient_id` de tenant B, usuario en tenant A
   - **When:** POST
   - **Then:** 404 Not Found

3. Rol asistente
   - **Given:** Usuario con rol `assistant`
   - **When:** POST
   - **Then:** 403 Forbidden

4. Item manual sin `unit_price` ni `service_id`
   - **Given:** Item con solo `description`
   - **When:** POST con `source: "manual"`
   - **Then:** 422 con detalle del campo faltante

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `doctor`, un `assistant` (para 403).

**Patients:** Un paciente activo del tenant de prueba.

**Quotations:** Una cotizacion `approved`, una `draft`, una con factura ya asociada.

**Treatment Plans:** Un plan con 3 items, un plan sin items.

**Service Catalog:** 3 servicios con precios configurados.

### Mocking Strategy

- **Redis:** fakeredis para simular INCR atomico de secuencia
- **Database:** SQLite en memoria con esquema de billing
- **Service Catalog:** Mock del repositorio para tests unitarios
- **Compliance Adapter:** Mock de `get_tax_rate(country)` retornando 0 para CO, 16 para MX

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Factura desde cotizacion aprobada hereda items y totales correctamente
- [ ] Factura manual resuelve precios del catalogo
- [ ] Numero secuencial `FAC-{YYYY}-{NNNNN}` sin duplicados (lock Redis)
- [ ] IVA 0% Colombia (servicios exentos), IVA 16% Mexico
- [ ] `status` inicial siempre es `draft`
- [ ] `amount_paid = 0`, `balance_due = total` en creacion
- [ ] Conflicto detectado si ya existe factura activa para la cotizacion
- [ ] Rol `assistant` y `patient` retornan 403
- [ ] Todos los valores monetarios en centavos (integer)
- [ ] All test cases pass
- [ ] Performance targets met (< 1500ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Envio de factura al paciente (ver B-05 invoice-send.md)
- Generacion de PDF de factura (ver B-06 invoice-pdf.md)
- Registro de pagos (ver B-07 payment-record.md)
- DIAN e-invoicing electronica (ver specs/compliance/)
- Notas credito o facturas de ajuste
- Facturacion a aseguradoras (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (3 ramas: quotation, treatment_plan, manual)
- [x] All outputs defined (response model con items anidados y totales en centavos)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (bleach para campos en PDF)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure en logs o errores
- [x] Audit trail para creacion

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 1500ms)
- [x] Caching strategy stated (catalogo desde cache, secuencia Redis)
- [x] DB queries optimizados (IN query para catalogo, indexes listados)
- [x] Pagination N/A

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, patient_id, total incluidos)
- [x] Audit log entries defined (create, no PHI)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A en creacion draft)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (Redis, catalogo, compliance adapter)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
