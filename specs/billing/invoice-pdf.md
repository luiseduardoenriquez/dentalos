# Invoice PDF (B-06)

---

## Overview

**Feature:** Generar y descargar el PDF de una factura con el branding completo de la clinica (logo, nombre, NIT/RUT/RFC segun pais, direccion, telefono), informacion del paciente, tabla de items con precios, totales desglosados (subtotal, descuento, impuesto, total), informacion de pago (saldo pendiente, metodos aceptados) y pie de pagina legal. El PDF se genera on-demand y se almacena en S3 para reutilizacion. Disponible para facturas en cualquier estado excepto `cancelled`.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), B-02 (invoice-get.md — datos de la factura), tenants (clinic branding), patients (Patient), infra/authentication-rules.md, database-architecture.md (`invoices`, `invoice_items`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor, patient
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Un paciente solo puede descargar PDFs de sus propias facturas. Los doctores pueden descargar PDFs de facturas de sus pacientes. La factura no puede estar en estado `cancelled`.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/invoices/{invoice_id}/pdf
```

**Rate Limiting:**
- 30 requests por minuto por usuario (PDF generation es costoso)
- Redis sliding window: `dentalos:rl:invoice_pdf:{user_id}` (TTL 60s)

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

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| download | No | boolean | true/false, default: false | Si true, retorna redirect con URL firmada S3 para descarga directa. Si false, retorna JSON con pdf_url | false |
| regenerate | No | boolean | true/false, default: false | Si true, fuerza regeneracion del PDF aunque exista en S3 | false |

### Request Body Schema

N/A — GET request

---

## Response

### Success Response (download=false — default)

**Status:** 200 OK

**Schema:**
```json
{
  "invoice_id": "UUID",
  "invoice_number": "string",
  "pdf_url": "string — URL firmada S3, expira en 1 hora",
  "pdf_size_bytes": "integer",
  "generated_at": "ISO8601",
  "expires_at": "ISO8601 — cuando expira la URL firmada"
}
```

**Example:**
```json
{
  "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
  "invoice_number": "FAC-2026-00001",
  "pdf_url": "https://storage.dentalos.com/invoices/tn_7c9e/FAC-2026-00001.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc123...&X-Amz-Expires=3600",
  "pdf_size_bytes": 124580,
  "generated_at": "2026-02-25T15:00:00Z",
  "expires_at": "2026-02-25T16:00:00Z"
}
```

### Success Response (download=true)

**Status:** 302 Found

**Headers:**
```
Location: https://storage.dentalos.com/invoices/tn_7c9e/FAC-2026-00001.pdf?X-Amz-Signature=...
Content-Disposition: attachment; filename="FAC-2026-00001.pdf"
```

### Error Responses

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol `patient` intentando descargar PDF de otro paciente.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para descargar esta factura."
}
```

#### 404 Not Found
**When:** `patient_id` o `invoice_id` no existen, o factura no pertenece al paciente.

```json
{
  "error": "invoice_not_found",
  "message": "La factura no fue encontrada."
}
```

#### 409 Conflict
**When:** La factura esta en estado `cancelled`.

```json
{
  "error": "invoice_cancelled",
  "message": "No se puede generar PDF de una factura cancelada."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido (30/min — PDF generation es costoso).

#### 500 Internal Server Error
**When:** Error al renderizar el HTML, generar el PDF con WeasyPrint, o subir a S3.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
3. Buscar la factura `WHERE id = invoice_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no, 404.
4. Si rol es `patient`: verificar que `user.patient_id == patient_id`. Si no, 403.
5. Si `invoice.status == 'cancelled'`: retornar 409.
6. **Verificar si existe PDF cacheado en S3:**
   a. Si `invoice.pdf_url` no es null y `regenerate != true`: intentar generar URL firmada nueva para el path existente en S3.
   b. Si la URL existente ya no es valida o S3 retorna 404 al head-check: proceder a regenerar.
   c. Si `regenerate == true`: siempre regenerar.
7. **Generar PDF:**
   a. Cargar datos de la clinica (tenant): nombre, NIT/RFC/RUT segun `tenant.country`, logo URL, direccion, telefono, email clinica.
   b. Cargar datos del paciente: nombre completo, numero de documento, email, telefono.
   c. Cargar items de la factura con `selectinload`.
   d. Cargar historial de pagos.
   e. Preparar contexto para el template:
      - Formatear montos en la moneda del tenant (ej: "$1.620.000 COP" o "$ 1,620,000.00 MXN").
      - Formatear fechas en formato local del pais del tenant.
      - Calcular `balance_due = total - amount_paid`.
   f. Renderizar template HTML `invoice_pdf.html` con Jinja2.
   g. Convertir HTML a PDF con WeasyPrint (`HTML(string=html_content).write_pdf()`).
   h. Subir bytes del PDF a S3: `{tenant_id}/invoices/{invoice_number}.pdf`.
   i. Generar URL firmada con expiracion de 1 hora.
   j. Actualizar `invoice.pdf_url` con el path S3 (sin firma — la firma se genera on-demand).
8. Si `download == true`: retornar 302 redirect a la URL firmada con header `Content-Disposition: attachment`.
9. Si `download == false`: retornar 200 JSON con `pdf_url`, `pdf_size_bytes`, `generated_at`, `expires_at`.
10. Registrar en audit log: accion `read`, recurso `invoice_pdf`, `tenant_id`, `user_id`, `invoice_id`.

**Contenido del PDF:**

El PDF de la factura contiene las siguientes secciones en orden:
1. **Encabezado:** Logo de la clinica (120x60px max), nombre de la clinica, NIT/RFC, direccion, telefono, email.
2. **Titulo:** "FACTURA" en grande, numero de factura (`FAC-2026-00001`), fecha de emision, fecha de vencimiento.
3. **Datos del paciente:** Nombre completo, tipo y numero de documento, email (si disponible).
4. **Tabla de servicios:** Columnas: Descripcion, Cantidad, Precio Unitario, Subtotal. Alternado de colores por fila.
5. **Totales:** Subtotal, Descuento (si aplica con porcentaje), IVA (si aplica), **Total en negrita**, Pagado, **Saldo Pendiente en color rojo si > 0**.
6. **Pagos recibidos:** Si hay pagos, tabla con: Fecha, Metodo, Referencia, Monto.
7. **Informacion de pago:** Metodos aceptados (efectivo, tarjeta, transferencia), datos bancarios si el tenant los tiene configurados.
8. **Pie de pagina:** Texto legal configurado por tenant, numero de pagina, URL del portal del paciente.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id (URL) | UUID v4, pertenece al tenant | "El paciente no fue encontrado." |
| invoice_id (URL) | UUID v4, factura del paciente y tenant | "La factura no fue encontrada." |
| invoice.status | No debe ser "cancelled" | "No se puede generar PDF de una factura cancelada." |
| download | Boolean, default false | |
| regenerate | Boolean, default false | |

**Business Rules:**

- El PDF se genera una vez y se almacena en S3. Las solicitudes subsiguientes sin `regenerate=true` reutilizan el PDF existente (solo regeneran la URL firmada).
- Una URL firmada expira en 1 hora (mas corta que la de cotizaciones — facturas son documentos mas sensibles).
- Si la factura cambia (B-04 update) mientras esta en `draft`, el PDF existente puede quedar desactualizado. La logica de B-04 invalida el `pdf_url` almacenado.
- Para facturas `sent` o `paid`, el PDF es un snapshot de los datos en el momento del envio. Si se solicita `regenerate=true` sobre una factura `sent`, el PDF se regenera con los datos actuales (incluyendo pagos nuevos).
- El formato de moneda sigue el locale del pais del tenant (COP: punto como separador de miles, sin decimales; MXN: coma decimal, 2 decimales).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Factura sin pagos | Seccion "Pagos Recibidos" omitida del PDF |
| Paciente sin email | Campo email omitido del PDF |
| Tenant sin logo | PDF sin logo — solo nombre de clinica en texto |
| `regenerate=true` en factura `paid` | PDF regenerado con todos los pagos; `pdf_url` en DB actualizado |
| PDF en S3 eliminado manualmente | Head-check falla → PDF regenerado automaticamente |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `invoices`: UPDATE — `pdf_url` (path S3 sin firma), `pdf_generated_at` si cambia

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

# Cargar factura con items y pagos
stmt = (
    select(Invoice)
    .where(Invoice.id == invoice_id)
    .options(
        selectinload(Invoice.items),
        selectinload(Invoice.payments),
    )
)
invoice = (await session.execute(stmt)).scalar_one()

# Despues de generar el PDF y subir a S3:
await session.execute(
    update(Invoice)
    .where(Invoice.id == invoice_id)
    .values(
        pdf_url=f"{tenant_id}/invoices/{invoice.invoice_number}.pdf",
        pdf_generated_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:invoice:{invoice_id}`: DELETE — si se regenera el PDF (pdf_url cambia)
- `tenant:{tenant_id}:invoice_pdf:{invoice_id}`: SET — cache de la URL firmada generada (TTL 55min — ligeramente menor al TTL de la URL para evitar servir URLs expiradas)

**Cache TTL:** 55 minutos para URL firmada (URL firmada vive 60min, cache vive 55min)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno.

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** invoice_pdf
- **PHI involved:** Si — el PDF contiene nombre del paciente y descripcion de procedimientos

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 100ms (si PDF existe en S3 — solo regenerar URL firmada)
- **Maximum acceptable:** < 4000ms (generacion completa de PDF con WeasyPrint)

### Caching Strategy
- **Strategy:** S3 para persistencia del archivo; Redis para URL firmada cacheada
- **Cache key:** `tenant:{tenant_id}:invoice_pdf:{invoice_id}` — URL firmada
- **TTL:** 55 minutos
- **Invalidation:** En updates de factura (B-04) que invalidan el PDF

### Database Performance

**Queries executed:** 2-3 (buscar factura, cargar items+pagos via selectinload, update pdf_url)

**Indexes required:**
- `invoices.(id, patient_id, tenant_id)` — INDEX COMPUESTO
- `invoice_items.invoice_id` — INDEX
- `payments.invoice_id` — INDEX

**N+1 prevention:** Items y pagos cargados con `selectinload` en una query.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, invoice_id (URL) | Pydantic UUID | |
| download | Pydantic bool | |
| regenerate | Pydantic bool | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los datos insertados en el template HTML del PDF se escapan con Jinja2 autoescaping. El PDF renderizado no puede ejecutar scripts.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** El PDF contiene nombre del paciente, documento de identidad, y descripcion de procedimientos odontologicos. Es un documento con PHI.

**Audit requirement:** All access logged (descarga de PDF con PHI)

---

## Testing

### Test Cases

#### Happy Path
1. Obtener URL de PDF (PDF ya existe en S3)
   - **Given:** Factura `sent` con `pdf_url` no null (PDF en S3)
   - **When:** GET /pdf sin `regenerate`
   - **Then:** 200 OK, URL firmada nueva generada, `pdf_size_bytes` correcto, `expires_at` = now + 1h

2. Generar PDF por primera vez
   - **Given:** Factura `draft` sin `pdf_url`
   - **When:** GET /pdf
   - **Then:** 200 OK, PDF generado y subido a S3, URL firmada retornada, `invoice.pdf_url` actualizado en DB

3. Descarga directa (download=true)
   - **Given:** Factura con PDF en S3
   - **When:** GET /pdf?download=true
   - **Then:** 302 redirect a URL S3 con `Content-Disposition: attachment`

4. Forzar regeneracion (regenerate=true)
   - **Given:** Factura `paid` con pagos nuevos despues del PDF inicial
   - **When:** GET /pdf?regenerate=true
   - **Then:** 200 OK, PDF nuevo generado con todos los pagos incluidos

5. Paciente descarga su propia factura
   - **Given:** JWT con rol `patient`, `patient_id` coincide
   - **When:** GET /pdf
   - **Then:** 200 OK, PDF retornado

#### Edge Cases
1. PDF en S3 eliminado (head-check 404)
   - **Given:** `invoice.pdf_url` no null pero S3 retorna 404
   - **When:** GET /pdf
   - **Then:** PDF regenerado automaticamente, 200 OK

2. Factura sin logo de clinica
   - **Given:** Tenant sin logo configurado
   - **When:** GET /pdf
   - **Then:** 200 OK, PDF generado con nombre de clinica en texto plano

3. URL firmada en cache (request repetido dentro del TTL)
   - **Given:** Mismo invoice_id solicitado dos veces en < 55min
   - **When:** GET /pdf segunda vez
   - **Then:** 200 OK, URL desde cache (< 50ms), sin regenerar PDF

#### Error Cases
1. Factura cancelada
   - **Given:** `invoice.status = "cancelled"`
   - **When:** GET /pdf
   - **Then:** 409 Conflict

2. Paciente descarga factura de otro paciente
   - **Given:** JWT `patient`, `patient_id` no coincide
   - **When:** GET /pdf
   - **Then:** 403 Forbidden

3. Rate limit excedido
   - **Given:** 30 requests en 60 segundos
   - **When:** Request 31
   - **Then:** 429 Too Many Requests

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `patient` (con patient vinculado), un `patient` diferente (para 403).

**Patients:** Un paciente con email y telefono.

**Invoices:** Una factura `draft` sin PDF, una `sent` con PDF en S3, una `cancelled`.

**Tenant Config:** Tenant con logo, tenant sin logo.

### Mocking Strategy

- **S3:** Mock de boto3 con response simulado para put_object y generate_presigned_url; mock de head_object para verificar existencia
- **WeasyPrint:** Mock en unit tests (retorna bytes fijos); test real en integration tests
- **Jinja2:** Usar templates reales pero con datos de prueba
- **Redis:** fakeredis para cache de URL firmada

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] PDF generado con branding de clinica (logo, nombre, NIT/RFC, direccion)
- [ ] PDF incluye tabla de items, totales desglosados y historial de pagos
- [ ] PDF reutilizado desde S3 si existe (no regeneracion innecesaria)
- [ ] `regenerate=true` fuerza nueva generacion
- [ ] `download=true` retorna 302 redirect para descarga directa
- [ ] URL firmada expira en 1 hora
- [ ] Rol `patient` solo puede descargar sus propias facturas
- [ ] Factura `cancelled` retorna 409
- [ ] PHI en PDF auditado (all access logged)
- [ ] Rate limit de 30/min aplicado (generacion costosa)
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms desde cache, < 4000ms generacion)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Generacion de factura electronica DIAN (ver specs/compliance/)
- PDF de cotizacion (ver B-18 quotation-send.md)
- Plantillas de PDF personalizables por clinica (post-MVP)
- PDF en idioma diferente al espanol
- QR code de pago en el PDF (post-MVP)
- Firma digital del PDF (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (URL params + query params download/regenerate)
- [x] All outputs defined (JSON con pdf_url O 302 redirect)
- [x] API contract defined (OpenAPI compatible, dos responses posibles)
- [x] Validation rules stated
- [x] Error cases enumerated (cancelled invoice, forbidden patient)
- [x] Auth requirements explicit (patient restriction)
- [x] Side effects listed (S3, DB, cache, audit)
- [x] PDF content specification detallada

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, StreamingResponse o RedirectResponse)
- [x] S3 + WeasyPrint como dependencias externas documentadas

### Hook 3: Security & Privacy
- [x] Auth level stated (patient restriction)
- [x] Jinja2 autoescaping para prevenir XSS en PDF
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] PHI en PDF — all access logged
- [x] URL firmada con expiracion (no URLs permanentes)

### Hook 4: Performance & Scalability
- [x] Response time targets definidos (< 100ms cache, < 4000ms generacion)
- [x] S3 como almacenamiento persistente (no regenerar en cada request)
- [x] Redis para cache de URL firmada (55min)
- [x] Rate limit de 30/min (generacion costosa)

### Hook 5: Observability
- [x] Structured logging (invoice_id, tenant_id, regenerated flag)
- [x] Audit log entries defined (PHI access)
- [x] Error tracking (Sentry-compatible)

### Hook 6: Testability
- [x] Test cases enumerated (cache hit, S3 miss, generacion)
- [x] Mocking strategy (S3, WeasyPrint, Redis)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
