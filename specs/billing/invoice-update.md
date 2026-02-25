# Invoice Update (B-04)

---

## Overview

**Feature:** Actualizar una factura en estado `draft`. Permite agregar, modificar o remover items de linea, ajustar el descuento global, cambiar la fecha de vencimiento, actualizar notas y reasignar el doctor responsable. Solo operable mientras la factura esta en estado `draft` — una vez enviada o pagada, es inmutable (usar notas credito para ajustes posteriores).

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), B-02 (invoice-get.md), B-14 (service-catalog.md), patients (Patient), infra/authentication-rules.md, database-architecture.md (`invoices`, `invoice_items`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Solo facturas en estado `draft` pueden modificarse. Los doctores solo pueden actualizar facturas donde son el doctor asignado o donde son el creador. Los asistentes no pueden actualizar facturas.

---

## Endpoint

```
PUT /api/v1/patients/{patient_id}/invoices/{invoice_id}
```

**Rate Limiting:**
- 60 requests por minuto por usuario
- Redis sliding window: `dentalos:rl:invoice_update:{user_id}` (TTL 60s)

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
| invoice_id | Yes | UUID | UUID v4 valido | ID de la factura a actualizar | inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "items": [
    {
      "id": "UUID (optional) — si se provee, actualiza item existente; si no, crea nuevo item",
      "service_id": "UUID (optional) — si se provee, resuelve precio del catalogo",
      "description": "string (required si no hay service_id) — descripcion del item",
      "quantity": "integer (optional) — default: 1, min: 1",
      "unit_price": "integer (optional) — en centavos, sobreescribe precio del catalogo",
      "tax_exempt": "boolean (optional) — default segun catalogo o configuracion del tenant",
      "_delete": "boolean (optional) — true para eliminar el item con este id"
    }
  ],
  "discount_percentage": "number (optional) — 0-100, sobreescribe el descuento existente",
  "due_date": "string (optional) — ISO8601 date, fecha de vencimiento nueva",
  "notes": "string (optional) — max 1000 chars, reemplaza las notas actuales",
  "doctor_id": "UUID (optional) — reasignar doctor responsable"
}
```

**Example Request (agregar item y cambiar descuento):**
```json
{
  "items": [
    {
      "id": "ii_aabb1122-ccdd-3344-eeff-556677889900",
      "quantity": 2
    },
    {
      "service_id": "svc_ddee4455-ff66-7788-9900-aabbccddeeff",
      "description": "Radiografia periapical adicional",
      "quantity": 1
    }
  ],
  "discount_percentage": 10,
  "notes": "Se agrego una radiografia adicional solicitada por el doctor."
}
```

**Example Request (eliminar item):**
```json
{
  "items": [
    {
      "id": "ii_ccdd3344-eeff-5566-0011-778899001122",
      "_delete": true
    }
  ]
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:** Identico al response de B-02 (invoice-get.md) — factura completa actualizada con items recalculados.

```json
{
  "id": "UUID",
  "invoice_number": "string",
  "patient_id": "UUID",
  "quotation_id": "UUID | null",
  "treatment_plan_id": "UUID | null",
  "doctor_id": "UUID | null",
  "status": "draft",
  "currency": "string",
  "subtotal": "integer",
  "discount_percentage": "number",
  "discount_amount": "integer",
  "tax_percentage": "number",
  "tax_amount": "integer",
  "total": "integer",
  "amount_paid": "integer",
  "balance_due": "integer",
  "due_date": "string",
  "notes": "string | null",
  "items": ["array de items actualizados"],
  "payments": ["array de pagos — inalterados"],
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
  "quotation_id": null,
  "treatment_plan_id": null,
  "doctor_id": "usr_550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "currency": "COP",
  "subtotal": 232000000,
  "discount_percentage": 10,
  "discount_amount": 23200000,
  "tax_percentage": 0,
  "tax_amount": 0,
  "total": 208800000,
  "amount_paid": 0,
  "balance_due": 208800000,
  "due_date": "2026-03-31",
  "notes": "Se agrego una radiografia adicional.",
  "items": [
    {
      "id": "ii_aabb1122-ccdd-3344-eeff-556677889900",
      "service_id": "svc_aabb1122-ccdd-3344-eeff-556677889900",
      "description": "Resina Oclusal — Diente 16",
      "quantity": 2,
      "unit_price": 35000000,
      "subtotal": 70000000,
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
      "id": "ii_eeFF5566-aabb-ccdd-eeff-001122334455",
      "service_id": "svc_ddee4455-ff66-7788-9900-aabbccddeeff",
      "description": "Radiografia periapical adicional",
      "quantity": 1,
      "unit_price": 77000000,
      "subtotal": 77000000,
      "tax_exempt": true
    }
  ],
  "payments": [],
  "created_by": "usr_receptionist-0001-0000-0000-000000000000",
  "created_at": "2026-02-25T09:00:00Z",
  "updated_at": "2026-02-25T14:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Body malformado, intentar eliminar un item que no existe, o item con `_delete: true` sin `id`.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "No se puede eliminar un item sin especificar su ID.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol no autorizado, o factura no pertenece al tenant del usuario.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para modificar esta factura."
}
```

#### 404 Not Found
**When:** `patient_id`, `invoice_id` o un `item.id` referenciado no existen en el tenant.

```json
{
  "error": "invoice_not_found",
  "message": "La factura no fue encontrada."
}
```

#### 409 Conflict
**When:** La factura no esta en estado `draft` (ya fue enviada, pagada, vencida o cancelada).

```json
{
  "error": "invoice_not_draft",
  "message": "Solo se pueden modificar facturas en estado borrador. Esta factura tiene estado: sent."
}
```

#### 422 Unprocessable Entity
**When:** `service_id` no existe en catalogo, item manual sin `unit_price`, resultado de la actualizacion deja 0 items, descuento fuera de rango.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "No se pudo actualizar la factura.",
  "details": {
    "items": ["La factura debe tener al menos un item activo."],
    "discount_percentage": ["El descuento debe estar entre 0 y 100."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado durante la transaccion de actualizacion.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `clinic_owner`, `receptionist` o `doctor`. Si no, retornar 403.
3. Validar body con schema Pydantic.
4. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
5. Buscar la factura `WHERE id = invoice_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no, 404.
6. Verificar que `invoice.status == 'draft'`. Si no, 409 con el estado actual.
7. Si el rol es `doctor`: verificar que `invoice.doctor_id == user_doctor_id OR invoice.created_by == user_id`. Si no, 403.
8. Cargar todos los `invoice_items` actuales de la factura.
9. Procesar la lista de items del body:
   - Item con `id` + `_delete: true`: marcar para eliminacion. Verificar que el `id` existe en los items actuales. Si no, 404 con detalle del item.
   - Item con `id` sin `_delete`: actualizar `quantity`, `unit_price`, `description` o `tax_exempt` si se proveen. Campos no presentes en el body no se modifican.
   - Item sin `id`: crear nuevo item. Si tiene `service_id`, resolver desde catalogo. Si no, verificar que tiene `description` y `unit_price`.
10. Calcular el estado final de items: items existentes no modificados + items actualizados + items nuevos - items eliminados.
11. Verificar que el resultado final tiene al menos 1 item activo. Si no, 422.
12. Si se provee `doctor_id`: verificar que el usuario existe y tiene rol `doctor` en el tenant. Si no, 404.
13. Recalcular todos los totales con el estado final de items (mismo algoritmo que B-01 paso 10).
14. Iniciar transaccion de base de datos:
    a. UPDATE `invoices` con nuevos totales, `discount_percentage`, `due_date`, `notes`, `doctor_id`, `updated_at`.
    b. Para items a eliminar: DELETE `invoice_items WHERE id IN (deleted_ids)`.
    c. Para items actualizados: UPDATE `invoice_items` con nuevos valores.
    d. Para items nuevos: INSERT `invoice_items`.
15. Confirmar transaccion.
16. Invalidar cache de la factura: DELETE `tenant:{tenant_id}:invoice:{invoice_id}`.
17. Invalidar cache de listado: DELETE `tenant:{tenant_id}:invoice_list:*` (patron).
18. Registrar en audit log: accion `update`, recurso `invoice`, campos modificados.
19. Retornar 200 OK con la factura actualizada completa.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| invoice_id (URL) | UUID v4, debe pertenecer al paciente y tenant | "La factura no fue encontrada." |
| invoice.status | Debe ser "draft" | "Solo se pueden modificar facturas en estado borrador." |
| items[].id | Si se provee, debe existir en los items actuales de la factura | "El item con ID {id} no existe en esta factura." |
| items[].quantity | Integer >= 1 | "La cantidad debe ser al menos 1." |
| items[].unit_price | Integer > 0 en centavos | "El precio debe ser mayor a 0." |
| items final count | Al menos 1 item activo despues de cambios | "La factura debe tener al menos un item." |
| discount_percentage | Float 0-100 | "El descuento debe estar entre 0 y 100." |
| due_date | Fecha >= hoy en formato ISO8601 | "La fecha de vencimiento no puede ser en el pasado." |
| notes | Max 1000 chars | "Las notas no pueden superar los 1000 caracteres." |

**Business Rules:**

- Solo facturas en estado `draft` pueden modificarse. Una factura `sent` o `paid` es inmutable para mantener integridad financiera.
- El numero de factura nunca cambia con una actualizacion.
- Si se modifica el descuento, se recalculan `discount_amount`, `tax_amount` y `total`.
- Los `payments` existentes no se ven afectados por la actualizacion de items (ya estan aplicados al `amount_paid`). Solo se recalcula `balance_due = new_total - amount_paid`.
- Si el body no incluye el campo `items`, los items existentes no se modifican.
- Un item nuevo sin `service_id` requiere obligatoriamente `description` y `unit_price` (item libre).
- La actualizacion es idempotente si se envian los mismos valores.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Body completamente vacio `{}` | 200 OK sin cambios (no-op) |
| Eliminar todos los items | 422: la factura debe tener al menos un item |
| Actualizar cantidad a 0 | 422: la cantidad debe ser al menos 1 |
| Factura con pago parcial, se modifica total | `balance_due` = nuevo_total - amount_paid_existente |
| Item nuevo con service_id no en catalogo | 422 con detalle del servicio no encontrado |
| Mismo item en lista dos veces | 400: IDs de item no pueden repetirse en el body |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `invoices`: UPDATE — totales recalculados, metadatos opcionales, `updated_at`
- `invoice_items`: INSERT (nuevos) + UPDATE (modificados) + DELETE (eliminados)

**Example query (SQLAlchemy):**
```python
from sqlalchemy import update, delete, insert

async with session.begin():
    # Actualizar cabecera de factura
    await session.execute(
        update(Invoice)
        .where(Invoice.id == invoice_id)
        .values(
            subtotal=new_subtotal,
            discount_percentage=new_discount_pct,
            discount_amount=new_discount_amount,
            tax_amount=new_tax_amount,
            total=new_total,
            balance_due=new_total - invoice.amount_paid,
            due_date=body.due_date or invoice.due_date,
            notes=body.notes if body.notes is not None else invoice.notes,
            doctor_id=body.doctor_id or invoice.doctor_id,
            updated_at=datetime.utcnow(),
        )
    )

    # Eliminar items marcados para borrado
    if items_to_delete:
        await session.execute(
            delete(InvoiceItem).where(InvoiceItem.id.in_(items_to_delete))
        )

    # Actualizar items modificados
    for item_update in items_to_update:
        await session.execute(
            update(InvoiceItem)
            .where(InvoiceItem.id == item_update.id)
            .values(**item_update.dict(exclude_unset=True))
        )

    # Insertar items nuevos
    for new_item in items_to_insert:
        await session.execute(insert(InvoiceItem).values(**new_item))
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:invoice:{invoice_id}`: DELETE — invalidar cache de detalle
- `tenant:{tenant_id}:invoice_list:*`: DELETE PATTERN — invalidar cache de listado

**Cache TTL:** N/A (invalidacion en update)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno.

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** invoice
- **PHI involved:** No (datos financieros)

### Notifications

**Notifications triggered:** No — la actualizacion de draft no notifica al paciente.

---

## Performance

### Expected Response Time
- **Target:** < 400ms
- **Maximum acceptable:** < 1000ms (operacion multi-tabla con recalculo)

### Caching Strategy
- **Strategy:** Invalidar cache de detalle y listado en update
- **Cache key:** `tenant:{tenant_id}:invoice:{invoice_id}` — DELETE
- **TTL:** N/A
- **Invalidation:** Inmediata en cada update exitoso

### Database Performance

**Queries executed:** 4-N (buscar factura, cargar items, transaccion con update + delete + insert por item)

**Indexes required:**
- `invoices.(id, patient_id, tenant_id)` — INDEX COMPUESTO
- `invoice_items.(invoice_id, id)` — INDEX COMPUESTO para lookup de items especificos

**N+1 prevention:** Items actuales cargados en una sola query. Operaciones de delete/update/insert en lote dentro de la transaccion.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, invoice_id (URL) | Pydantic UUID | |
| items[].id | Pydantic UUID opcional | |
| items[].description | Pydantic str, strip, max_length=500, bleach | Aparece en PDF si se regenera |
| items[].unit_price | Pydantic int, gt=0 | En centavos |
| items[].quantity | Pydantic int, ge=1 | |
| discount_percentage | Pydantic float, ge=0, le=100 | |
| notes | Pydantic str, strip, max_length=1000, bleach | |
| due_date | Pydantic date, >= today | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Serializacion Pydantic. Campos de texto sanitizados con bleach antes de almacenar.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno. Datos financieros.

**Audit requirement:** Write-only logged (actualizacion de factura con campos modificados)

---

## Testing

### Test Cases

#### Happy Path
1. Agregar nuevo item a la factura
   - **Given:** Factura `draft` con 2 items, usuario `receptionist`
   - **When:** PUT con nuevo item en el array (sin `id`)
   - **Then:** 200 OK, factura ahora tiene 3 items, totales recalculados

2. Modificar cantidad de un item existente
   - **Given:** Item con `quantity: 1`, `unit_price: 35000000`
   - **When:** PUT con `{ "items": [{ "id": "{item_id}", "quantity": 3 }] }`
   - **Then:** 200 OK, `subtotal` del item = 105000000, `total` recalculado

3. Eliminar un item
   - **Given:** Factura con 3 items
   - **When:** PUT con `{ "items": [{ "id": "{item_id}", "_delete": true }] }`
   - **Then:** 200 OK, factura ahora tiene 2 items, totales recalculados

4. Cambiar descuento
   - **Given:** Factura sin descuento, `total: 162000000`
   - **When:** PUT con `{ "discount_percentage": 15 }`
   - **Then:** 200 OK, `discount_amount: 24300000`, `total: 137700000`

5. Body vacio (no-op)
   - **Given:** Factura `draft`
   - **When:** PUT con `{}`
   - **Then:** 200 OK con la factura sin cambios, `updated_at` actualizado

#### Edge Cases
1. Factura con pago parcial, se cambia total
   - **Given:** `amount_paid: 50000000`, `total: 100000000`. Se elimina item → nuevo `total: 80000000`
   - **When:** PUT con item eliminado
   - **Then:** 200 OK, `balance_due: 30000000` (80000000 - 50000000)

2. Intentar eliminar el ultimo item
   - **Given:** Factura con 1 solo item
   - **When:** PUT con `{ "items": [{ "id": "{item_id}", "_delete": true }] }`
   - **Then:** 422: "La factura debe tener al menos un item."

#### Error Cases
1. Factura en estado `sent`
   - **Given:** Factura con `status: "sent"`
   - **When:** PUT
   - **Then:** 409 Conflict con estado actual

2. Item ID no pertenece a la factura
   - **Given:** `item_id` de otra factura del mismo tenant
   - **When:** PUT con ese `item_id`
   - **Then:** 404 con detalle del item no encontrado

3. Rol `assistant`
   - **Given:** JWT con rol `assistant`
   - **When:** PUT
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `doctor` (con factura asignada), un `assistant` (para 403).

**Patients:** Un paciente activo.

**Invoices:** Una factura `draft` con 3 items, una `sent`, una con pago parcial.

**Service Catalog:** 3 servicios disponibles.

### Mocking Strategy

- **Redis:** fakeredis para cache invalidation
- **Database:** SQLite en memoria con esquema de billing
- **Service Catalog:** Mock del repositorio para nuevos items

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Items se pueden agregar, modificar y eliminar en facturas `draft`
- [ ] Totales se recalculan correctamente despues de cada cambio
- [ ] `balance_due` respeta `amount_paid` existente en recalculo
- [ ] Facturas en estado no-draft retornan 409
- [ ] Cache invalidado en cada update exitoso
- [ ] No se pueden eliminar todos los items (minimo 1)
- [ ] Body vacio es no-op valido (200 OK)
- [ ] Rol `assistant` retorna 403
- [ ] All test cases pass
- [ ] Performance targets met (< 1000ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Cambio de estado de factura (ver B-05 invoice-send.md)
- Cancelacion de factura (endpoint separado, post-MVP)
- Notas credito o ajustes post-envio
- Historial de versiones de factura (audit log cubre esto)
- Actualizacion masiva de facturas

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (operaciones por item: create/update/delete)
- [x] All outputs defined (factura completa recalculada)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (restriccion draft-only prominente)
- [x] Error cases enumerated
- [x] Auth requirements explicit (restriccion doctor a sus facturas)
- [x] Side effects listed (invalidacion cache)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, transaccion atomica)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (draft-only enforcement)
- [x] Input sanitization definida
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure
- [x] Audit trail para updates

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 1000ms)
- [x] Cache invalidacion explicita
- [x] DB transaccion atomica con operaciones en lote
- [x] Pagination N/A

### Hook 5: Observability
- [x] Structured logging con campos modificados
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
