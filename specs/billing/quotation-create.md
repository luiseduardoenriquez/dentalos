# Quotation Create (B-16)

---

## Overview

**Feature:** Generar una cotizacion para el paciente, ya sea automaticamente a partir de un plan de tratamiento (eliminando la "triple digitacion") o como cotizacion standalone con items manuales. La cotizacion resuelve precios desde el catalogo de servicios del tenant, aplica descuento opcional, calcula impuestos segun el pais del tenant, genera numero secuencial por tenant y queda en estado `draft`.

**Domain:** billing

**Priority:** High

**Dependencies:** B-14 (service-catalog.md — precios por servicio), treatment-plans (TreatmentPlan, TreatmentPlanItem), patients (Patient), I-02 (authentication-rules.md), database-architecture.md (`quotations`, `quotation_items`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** doctor, clinic_owner, assistant
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** El paciente referenciado en la URL debe pertenecer al mismo tenant. Los recepcionistas no pueden crear cotizaciones directamente (deben solicitarlo al doctor).

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/quotations
```

**Rate Limiting:**
- 60 requests por minuto por usuario
- Redis sliding window: `dentalos:rl:quotation_create:{user_id}` (TTL 60s)

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
| patient_id | Yes | UUID | UUID v4 valido | ID del paciente a quien se emite la cotizacion | pt_550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "treatment_plan_id": "UUID (optional) — si se provee, auto-genera items desde el plan de tratamiento",
  "items": [
    {
      "service_id": "UUID (conditional) — requerido si no hay treatment_plan_id",
      "description": "string (optional) — descripcion personalizada, sobreescribe la del catalogo",
      "quantity": "integer (optional) — default: 1",
      "unit_price": "number (optional) — sobreescribe precio del catalogo si se provee"
    }
  ],
  "discount_percentage": "number (optional) — porcentaje de descuento global 0-100, default: 0",
  "notes": "string (optional) — notas para el paciente, max 1000 chars",
  "valid_days": "integer (optional) — dias de validez de la cotizacion, default: 30, max: 365"
}
```

**Example Request (desde plan de tratamiento):**
```json
{
  "treatment_plan_id": "tp_7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "discount_percentage": 10,
  "notes": "Cotizacion especial. Incluye materiales premium.",
  "valid_days": 30
}
```

**Example Request (cotizacion standalone):**
```json
{
  "items": [
    {
      "service_id": "svc_aabb1122-ccdd-3344-eeff-556677889900",
      "quantity": 1,
      "description": "Consulta de valoracion inicial"
    },
    {
      "service_id": "svc_bbcc2233-ddee-4455-ff00-667788990011",
      "quantity": 2,
      "unit_price": 180000
    }
  ],
  "discount_percentage": 0,
  "valid_days": 15
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
  "quotation_number": "string — numero secuencial por tenant (ej: COT-2026-00042)",
  "patient_id": "UUID",
  "treatment_plan_id": "UUID | null",
  "status": "draft",
  "currency": "string — ISO 4217 (ej: COP, USD, MXN)",
  "subtotal": "number",
  "discount_percentage": "number",
  "discount_amount": "number",
  "tax_percentage": "number",
  "tax_amount": "number",
  "total": "number",
  "valid_until": "ISO8601 date",
  "notes": "string | null",
  "items": [
    {
      "id": "UUID",
      "service_id": "UUID | null",
      "description": "string",
      "quantity": "integer",
      "unit_price": "number",
      "subtotal": "number"
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
  "id": "quot_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "quotation_number": "COT-2026-00042",
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "treatment_plan_id": "tp_7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "draft",
  "currency": "COP",
  "subtotal": 1800000,
  "discount_percentage": 10,
  "discount_amount": 180000,
  "tax_percentage": 0,
  "tax_amount": 0,
  "total": 1620000,
  "valid_until": "2026-03-26",
  "notes": "Cotizacion especial. Incluye materiales premium.",
  "items": [
    {
      "id": "qi_aabb1122-ccdd-3344-eeff-556677889900",
      "service_id": "svc_aabb1122-ccdd-3344-eeff-556677889900",
      "description": "Resina Oclusal — Diente 16",
      "quantity": 1,
      "unit_price": 350000,
      "subtotal": 350000
    },
    {
      "id": "qi_bbcc2233-ddee-4455-ff00-667788990011",
      "service_id": "svc_bbcc2233-ddee-4455-ff00-667788990011",
      "description": "Endodoncia Unirradicular — Diente 21",
      "quantity": 1,
      "unit_price": 850000,
      "subtotal": 850000
    },
    {
      "id": "qi_ccdd3344-eeff-5566-0011-778899001122",
      "service_id": "svc_ccdd3344-eeff-5566-0011-778899001122",
      "description": "Limpieza y Profilaxis",
      "quantity": 1,
      "unit_price": 600000,
      "subtotal": 600000
    }
  ],
  "created_by": "usr_550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-02-24T14:30:00Z",
  "updated_at": "2026-02-24T14:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Body malformado, ni `treatment_plan_id` ni `items` provistos, o ambos provistos simultaneamente.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Debe proporcionar un plan de tratamiento o una lista de servicios, no ambos.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol no autorizado o paciente pertenece a otro tenant.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para crear cotizaciones para este paciente."
}
```

#### 404 Not Found
**When:** `patient_id` no existe en el tenant, o `treatment_plan_id` no existe o no pertenece al paciente.

```json
{
  "error": "patient_not_found",
  "message": "El paciente no fue encontrado."
}
```

```json
{
  "error": "treatment_plan_not_found",
  "message": "El plan de tratamiento no fue encontrado o no pertenece a este paciente."
}
```

#### 409 Conflict
**When:** Ya existe una cotizacion en estado `draft` o `sent` para el mismo plan de tratamiento.

```json
{
  "error": "quotation_already_exists",
  "message": "Ya existe una cotizacion activa para este plan de tratamiento. Revisar COT-2026-00038."
}
```

#### 422 Unprocessable Entity
**When:** Items con `service_id` no encontrado en catalogo, precio cero en catalogo sin `unit_price` manual, descuento fuera de rango.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "No se pudo generar la cotizacion.",
  "details": {
    "items[1].service_id": ["El servicio no existe en el catalogo de la clinica."],
    "discount_percentage": ["El descuento debe estar entre 0 y 100."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al generar el numero secuencial o al persistir la cotizacion.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `doctor`, `clinic_owner` o `assistant`. Si no, retornar 403.
3. Validar body con schema Pydantic:
   - Exactamente uno de `treatment_plan_id` o `items` debe estar presente (no ambos, no ninguno).
   - `discount_percentage` entre 0 y 100.
   - `valid_days` entre 1 y 365.
4. Verificar que el paciente (`patient_id` en URL) existe y pertenece al `tenant_id` del JWT. Si no, 404.
5. **Rama A — desde plan de tratamiento:**
   a. Buscar `treatment_plan` donde `id = treatment_plan_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no existe, 404.
   b. Verificar que no exista cotizacion activa (`status IN ('draft', 'sent')`) para el mismo `treatment_plan_id`. Si existe, 409 con el numero de cotizacion existente.
   c. Cargar todos los `treatment_plan_items` del plan (JOIN con `procedures`).
   d. Para cada item, buscar precio en `service_catalog` del tenant (`WHERE service_id = item.service_id AND tenant_id = tenant_id`). Si no tiene precio configurado y no se provee `unit_price` manual, registrar advertencia en log pero usar precio 0 (no bloquear).
   e. Construir lista de items de cotizacion con: descripcion del procedimiento + diente si aplica, cantidad, precio unitario del catalogo.
6. **Rama B — cotizacion standalone:**
   a. Validar que `items` tenga al menos 1 elemento.
   b. Para cada item, buscar `service_id` en `service_catalog` del tenant. Si no existe, agregar a errores de validacion y retornar 422 al final.
   c. Si `unit_price` se provee en el item, usarlo; si no, usar el precio del catalogo.
7. Calcular totales:
   - `subtotal` = suma de (quantity * unit_price) por item
   - `discount_amount` = subtotal * (discount_percentage / 100)
   - `subtotal_con_descuento` = subtotal - discount_amount
   - `tax_percentage` = segun `tenant.country`: Colombia (CO) = 0% (servicios medicos exentos de IVA), Mexico (MX) = 16%, otros = 0%
   - `tax_amount` = subtotal_con_descuento * (tax_percentage / 100)
   - `total` = subtotal_con_descuento + tax_amount
8. Generar numero secuencial de cotizacion con lock distribuido en Redis:
   - Key: `tenant:{tenant_id}:quotation_sequence`
   - Operacion atomica INCR en Redis, obtener nuevo valor.
   - Formatear como `COT-{YYYY}-{numero_con_ceros_5_digitos}` (ej: `COT-2026-00042`).
9. Calcular `valid_until`: `fecha_hoy + valid_days` en la zona horaria del tenant.
10. Iniciar transaccion de base de datos.
11. Insertar en `quotations`.
12. Insertar en `quotation_items` (un registro por item).
13. Si viene de plan de tratamiento, actualizar `treatment_plans.last_quotation_id = quotation.id`.
14. Confirmar transaccion.
15. Registrar en log estructurado: `billing.quotation.created` con `tenant_id`, `user_id`, `patient_id`, `quotation_id`, `total`.
16. Retornar 201 Created con la cotizacion completa.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | UUID v4, paciente debe pertenecer al tenant | "El paciente no fue encontrado." |
| treatment_plan_id | UUID v4, plan debe pertenecer al paciente y al tenant | "El plan de tratamiento no fue encontrado." |
| items | Requerido si no hay treatment_plan_id, min 1 elemento | "Debe incluir al menos un servicio." |
| discount_percentage | Float entre 0.0 y 100.0 | "El descuento debe estar entre 0 y 100." |
| valid_days | Integer entre 1 y 365, default 30 | "Los dias de validez deben estar entre 1 y 365." |
| notes | Max 1000 chars | "Las notas no pueden superar los 1000 caracteres." |

**Business Rules:**

- Los impuestos se calculan segun el pais del tenant: Colombia (CO) servicios odontologicos son exentos de IVA (0%). Mexico (MX) IVA 16%. El campo `tax_percentage` en la respuesta refleja el porcentaje aplicado.
- Una cotizacion desde plan de tratamiento no puede generarse si ya existe una cotizacion `draft` o `sent` para el mismo plan.
- El numero de cotizacion es secuencial por tenant e inmutable una vez asignado.
- El descuento se aplica sobre el subtotal total, no sobre cada item individualmente.
- El precio del catalogo puede ser sobreescrito con `unit_price` manual en items standalone.
- La cotizacion se crea siempre en estado `draft`. Para enviarla al paciente, usar B-18.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Plan de tratamiento sin items | Retornar 422: "El plan de tratamiento no tiene procedimientos." |
| Servicio sin precio en catalogo | Log de advertencia, precio 0 en ese item, continuar |
| valid_days=0 | 422: debe ser al menos 1 |
| discount_percentage=100 | Valido: total = 0 + impuesto (0 en Colombia) |
| Cotizacion rechazada existe (status=rejected) | No es conflicto, se puede crear nueva cotizacion |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `quotations`: INSERT — nueva cotizacion en estado draft
- `quotation_items`: INSERT — un registro por cada item de la cotizacion
- `treatment_plans`: UPDATE — `last_quotation_id` si viene de plan de tratamiento

**Example query (SQLAlchemy):**
```python
from sqlalchemy import insert, update, select

async with session.begin():
    # Generar numero secuencial (Redis INCR ya ejecutado antes)
    quotation_result = await session.execute(
        insert(Quotation).values(
            patient_id=patient_id,
            tenant_id=tenant_id,
            treatment_plan_id=body.treatment_plan_id,
            quotation_number=quotation_number,
            status="draft",
            currency=tenant.currency,
            subtotal=subtotal,
            discount_percentage=body.discount_percentage or 0,
            discount_amount=discount_amount,
            tax_percentage=tax_percentage,
            tax_amount=tax_amount,
            total=total,
            valid_until=valid_until,
            notes=body.notes,
            created_by=user_id,
        ).returning(Quotation.id)
    )
    quotation_id = quotation_result.scalar_one()

    # Insertar items
    for item in computed_items:
        await session.execute(
            insert(QuotationItem).values(
                quotation_id=quotation_id,
                service_id=item.service_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.quantity * item.unit_price,
            )
        )

    # Actualizar plan de tratamiento si aplica
    if body.treatment_plan_id:
        await session.execute(
            update(TreatmentPlan)
            .where(TreatmentPlan.id == body.treatment_plan_id)
            .values(last_quotation_id=quotation_id)
        )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:quotation_sequence`: INCR atomico — contador de numero secuencial

**Cache TTL:** Persistente (sin TTL — el contador vive indefinidamente en Redis y tambien se persiste en tabla `quotation_sequences` como backup)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno en creacion (draft). El envio al paciente se dispara en B-18.

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** quotation
- **PHI involved:** No (datos financieros, no clinicos)

### Notifications

**Notifications triggered:** No — la cotizacion draft no genera notificacion. Ver B-18 (quotation-send) para el envio al paciente.

---

## Performance

### Expected Response Time
- **Target:** < 400ms
- **Maximum acceptable:** < 1200ms (incluye lookup de catalogo, calculos y transaccion multi-tabla)

### Caching Strategy
- **Strategy:** No se cachea la cotizacion creada. El catalogo de servicios puede cachearse separadamente (B-14).
- **Cache key:** `tenant:{tenant_id}:quotation_sequence` (solo para secuencia numerica)
- **TTL:** Permanente para secuencia
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 5-N (verificar paciente, verificar plan, verificar conflicto, lookup catalogo por cada item, insert quotation, insert N items, update plan)

**Indexes required:**
- `quotations.patient_id` — INDEX
- `quotations.tenant_id` — INDEX
- `quotations.(treatment_plan_id, status)` — INDEX COMPUESTO para verificacion de conflicto
- `quotations.quotation_number` — UNIQUE per tenant (parcial)
- `quotation_items.quotation_id` — INDEX
- `service_catalog.(tenant_id, service_id)` — INDEX COMPUESTO

**N+1 prevention:** El lookup de precios del catalogo se hace con una sola query IN: `WHERE service_id = ANY(:service_ids) AND tenant_id = :tenant_id`. No se hace una query por item.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id (URL) | Pydantic UUID | |
| treatment_plan_id | Pydantic UUID, opcional | |
| items[].description | Pydantic str, strip, max_length=500, bleach | Puede aparecer en PDF |
| notes | Pydantic str, strip, max_length=1000, bleach | Puede aparecer en PDF |
| discount_percentage | Pydantic float, ge=0, le=100 | |
| valid_days | Pydantic int, ge=1, le=365 | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic. Los campos que van a PDF (`notes`, `items[].description`) se sanitizan con bleach antes de almacenar.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno directamente — la cotizacion contiene informacion financiera. El `patient_id` es referencia pero no datos clinicos.

**Audit requirement:** Write-only logged (creacion de cotizacion)

---

## Testing

### Test Cases

#### Happy Path
1. Generar cotizacion desde plan de tratamiento con 3 items
   - **Given:** Plan de tratamiento con 3 procedimientos, catalogo de precios configurado, usuario `doctor`
   - **When:** POST /api/v1/patients/{id}/quotations con `treatment_plan_id`
   - **Then:** 201 Created, `items` con 3 elementos, precios del catalogo, `subtotal` correcto, numero `COT-2026-XXXXX` generado

2. Generar cotizacion standalone con descuento
   - **Given:** 2 servicios con precios en catalogo, `discount_percentage: 15`
   - **When:** POST con lista de items manuales
   - **Then:** 201 Created, `discount_amount` = 15% del subtotal, `total` = subtotal - descuento

3. Impuesto segun pais (Colombia)
   - **Given:** Tenant con `country: "CO"`
   - **When:** POST /api/v1/patients/{id}/quotations
   - **Then:** `tax_percentage: 0`, `tax_amount: 0` (IVA exento para servicios medicos)

4. Numero secuencial incrementa
   - **Given:** Ultima cotizacion tiene numero `COT-2026-00005`
   - **When:** POST nueva cotizacion
   - **Then:** Nueva cotizacion tiene `quotation_number: "COT-2026-00006"`

#### Edge Cases
1. Plan de tratamiento sin items
   - **Given:** Plan de tratamiento vacio (sin procedimientos)
   - **When:** POST con `treatment_plan_id`
   - **Then:** 422 Unprocessable Entity con mensaje descriptivo

2. Descuento del 100%
   - **Given:** Tenant CO (IVA 0%), descuento 100%
   - **When:** POST con `discount_percentage: 100`
   - **Then:** 201, `total: 0`, `discount_amount` = subtotal total

3. Cotizacion rechazada preexistente no bloquea
   - **Given:** Existe cotizacion con `status: "rejected"` para el mismo plan
   - **When:** POST nueva cotizacion con el mismo `treatment_plan_id`
   - **Then:** 201 Created (no hay conflicto con cotizaciones rechazadas)

#### Error Cases
1. Paciente de otro tenant
   - **Given:** `patient_id` pertenece a tenant B, usuario en tenant A
   - **When:** POST /api/v1/patients/{patient_id_tenant_B}/quotations
   - **Then:** 404 Not Found

2. Cotizacion draft ya existe para el plan
   - **Given:** Cotizacion `draft` COT-2026-00038 para el mismo plan
   - **When:** POST con el mismo `treatment_plan_id`
   - **Then:** 409 Conflict con referencia al numero existente

3. Servicio no existe en catalogo (standalone)
   - **Given:** `service_id` inexistente en catalogo del tenant
   - **When:** POST con items manuales
   - **Then:** 422 con detalle del item fallido

4. Ambos `treatment_plan_id` e `items` presentes
   - **Given:** Body con ambos campos
   - **When:** POST
   - **Then:** 400 Bad Request

### Test Data Requirements

**Users:** Un `doctor`, un `clinic_owner`, un `assistant`, un `receptionist` (para test de 403 si aplica).

**Patients:** Un paciente activo del tenant de prueba.

**Treatment Plans:** Un plan con 3 items, un plan sin items.

**Service Catalog:** 3 servicios con precios configurados en el catalogo del tenant.

### Mocking Strategy

- **Redis:** fakeredis para simular INCR atomico de secuencia
- **Database:** SQLite en memoria con esquema de billing completo
- **Service Catalog:** Mock del repositorio de catalogo para tests unitarios

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Cotizacion desde plan de tratamiento auto-resuelve precios del catalogo (elimina "triple digitacion")
- [ ] Cotizacion standalone con items manuales funciona correctamente
- [ ] Numero secuencial `COT-{YYYY}-{NNNNN}` se genera sin duplicados (lock Redis)
- [ ] Descuento se aplica sobre subtotal total
- [ ] Impuesto 0% para Colombia, 16% para Mexico
- [ ] Conflicto detectado si ya existe cotizacion draft/sent para el mismo plan
- [ ] Paciente de otro tenant retorna 404
- [ ] `status` inicial siempre es `draft`
- [ ] Rol `receptionist` y `patient` retornan 403
- [ ] All test cases pass
- [ ] Performance targets met (< 1200ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Envio de cotizacion al paciente (ver B-18 quotation-send.md)
- Conversion de cotizacion en factura
- Aprobacion/rechazo de cotizacion por el paciente
- Cotizaciones con items de seguros (post-MVP)
- Historial de versiones de cotizacion

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas — ambas ramas: from plan y standalone)
- [x] All outputs defined (response model con items anidados)
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
- [x] Input sanitization defined (bleach para campos que van a PDF)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure (cotizacion contiene datos financieros, no clinicos)
- [x] Audit trail para creacion

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 1200ms)
- [x] Caching strategy stated (solo para secuencia numerica)
- [x] DB queries optimized (IN query para catalogo, indexes listados)
- [x] Pagination N/A

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, patient_id, total incluidos)
- [x] Audit log entries defined (create, no PHI)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A en creacion)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services (Redis fakeredis, catalogo mock)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
