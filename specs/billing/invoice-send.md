# Invoice Send (B-05)

---

## Overview

**Feature:** Enviar una factura en estado `draft` al paciente a traves de uno o mas canales (email, WhatsApp, portal del paciente). Genera el PDF de la factura con branding de la clinica, cambia el estado de `draft` a `sent`, y encola el trabajo de envio en RabbitMQ para procesamiento asincrono. Es el paso final del flujo de emision antes de la cobranza.

**Domain:** billing

**Priority:** Medium

**Dependencies:** B-01 (invoice-create.md), B-06 (invoice-pdf.md — generacion de PDF), patients (Patient), notifications, infra/authentication-rules.md, database-architecture.md (`invoices`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, receptionist, doctor
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Los asistentes no pueden enviar facturas. El paciente y la factura deben pertenecer al mismo tenant. Doctores pueden enviar facturas donde son el doctor asignado o el creador.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/invoices/{invoice_id}/send
```

**Rate Limiting:**
- 20 requests por minuto por usuario
- Redis sliding window: `dentalos:rl:invoice_send:{user_id}` (TTL 60s)

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
| invoice_id | Yes | UUID | UUID v4 valido | ID de la factura a enviar | inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "channels": ["string (optional) — email | whatsapp | portal — default: [email, portal]"],
  "message": "string (optional) — mensaje personalizado para el paciente, max 500 chars",
  "recipient_email": "string (optional) — email alternativo si difiere del email del paciente"
}
```

**Example Request:**
```json
{
  "channels": ["email", "whatsapp"],
  "message": "Estimado paciente, adjuntamos su factura FAC-2026-00001 por los servicios odontologicos prestados. Tiene plazo hasta el 31 de marzo. Gracias por confiar en nosotros."
}
```

**Example Request (minimal):**
```json
{}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "invoice_id": "UUID",
  "invoice_number": "string",
  "status": "sent",
  "sent_at": "ISO8601",
  "channels_dispatched": ["string"],
  "recipient_email": "string | null",
  "pdf_url": "string — URL firmada S3, expira en 24h",
  "total": "integer — en centavos",
  "balance_due": "integer — en centavos",
  "due_date": "string — ISO8601 date"
}
```

**Example:**
```json
{
  "invoice_id": "inv_1a2b3c4d-e5f6-7890-abcd-ef1234567890",
  "invoice_number": "FAC-2026-00001",
  "status": "sent",
  "sent_at": "2026-02-25T15:00:00Z",
  "channels_dispatched": ["email", "whatsapp"],
  "recipient_email": "juan.perez@gmail.com",
  "pdf_url": "https://storage.dentalos.com/invoices/tn_7c9e/FAC-2026-00001.pdf?X-Amz-Signature=...&X-Amz-Expires=86400",
  "total": 162000000,
  "balance_due": 162000000,
  "due_date": "2026-03-31"
}
```

### Error Responses

#### 400 Bad Request
**When:** Canal de envio invalido o `channels` con valor desconocido.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Canal de envio no valido.",
  "details": {
    "channels": ["Los canales validos son: email, whatsapp, portal."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol `assistant` o `patient`, o factura no pertenece al tenant.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para enviar esta factura."
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

#### 409 Conflict
**When:** La factura no esta en estado `draft`.

```json
{
  "error": "invoice_not_draft",
  "message": "Solo se pueden enviar facturas en estado borrador. Esta factura tiene estado: sent."
}
```

#### 422 Unprocessable Entity
**When:** Canal `whatsapp` solicitado pero clinica sin integracion configurada. Paciente sin email y canal `email` es el unico solicitado.

**Example:**
```json
{
  "error": "channel_not_available",
  "message": "El canal WhatsApp no esta configurado para esta clinica.",
  "details": {
    "channels": ["whatsapp no disponible — configurar integracion en panel de administracion"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error al generar el PDF o al encolar el job de envio.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `clinic_owner`, `receptionist` o `doctor`. Si no, 403.
3. Validar body: `channels` debe ser subconjunto de `["email", "whatsapp", "portal"]`. `message` max 500 chars. `recipient_email` formato valido si se provee.
4. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
5. Buscar la factura `WHERE id = invoice_id AND patient_id = patient_id AND tenant_id = tenant_id`. Si no, 404.
6. Verificar que `invoice.status == 'draft'`. Si no, 409 con el estado actual.
7. Si rol es `doctor`: verificar que `invoice.doctor_id == user_doctor_id OR invoice.created_by == user_id`. Si no, 403.
8. Determinar canales efectivos:
   - Si `channels` no se provee: usar `["email", "portal"]` como default.
   - Si `whatsapp` en canales: verificar `tenant.whatsapp_configured == true`. Si no, 422.
   - Si `email` en canales: verificar que el paciente tiene email o se provee `recipient_email`. Si no hay email, excluir canal silenciosamente y loguear advertencia.
   - Si `portal` en canales: verificar que el paciente tiene cuenta en el portal. Si no, excluir silenciosamente.
9. Verificar que queda al menos 1 canal efectivo. Si todos fueron excluidos, retornar 422.
10. **Generar PDF** (sincronamente — la URL se necesita en la respuesta inmediata):
    a. Cargar items de la factura y datos de la clinica (nombre, NIT/RUT, logo, direccion).
    b. Cargar datos del paciente (nombre, documento, email).
    c. Renderizar HTML con el template de factura (`invoice_pdf.html`).
    d. Convertir a PDF con Playwright.
    e. Subir a S3 en ruta `{tenant_id}/invoices/{invoice_number}.pdf`.
    f. Generar URL firmada con expiracion de 24 horas.
11. Actualizar `invoice.status = 'sent'`, `invoice.sent_at = now()`, `invoice.sent_by = user_id`, `invoice.pdf_url = pdf_s3_path`.
12. Encolar job en RabbitMQ:
    - Queue: `notifications.invoice_sent`
    - Payload: `{ invoice_id, patient_id, tenant_id, channels, recipient_email, pdf_url, message, invoice_number, total, currency, due_date, balance_due, clinic_name }`
13. Registrar en audit log: accion `update`, recurso `invoice`, campos `status: sent`, `sent_at`, `channels`.
14. Retornar 200 OK con resultado del envio.

**Nota:** El envio real de email/WhatsApp ocurre de forma asincrona en el worker de notificaciones. El endpoint retorna inmediatamente tras encolar el job.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| invoice_id (URL) | UUID v4, factura del paciente y tenant | "La factura no fue encontrada." |
| invoice.status | Debe ser "draft" | "Solo se pueden enviar facturas en estado borrador." |
| channels | Array, elementos en Enum ["email", "whatsapp", "portal"] | "Los canales validos son: email, whatsapp, portal." |
| message | Max 500 chars | "El mensaje no puede superar los 500 caracteres." |
| recipient_email | Formato email valido (EmailStr) | "El correo alternativo no tiene formato valido." |

**Business Rules:**

- Una vez enviada, la factura es inmutable. Para ajustes, usar notas credito (post-MVP).
- El PDF se genera sincrona para que el `pdf_url` este disponible en la respuesta.
- El envio real es asincrono (RabbitMQ) para no bloquear el endpoint con latencia de SMTP.
- La URL del PDF en S3 tiene expiracion de 24h. El frontend puede solicitar regeneracion via B-06.
- Canal `portal` notifica al paciente en la app del portal si tiene cuenta activa.
- Si se solicita solo `whatsapp` y no hay numero registrado, se retorna 422 para no dejar la factura en limbo (no se cambia estado si no hay canal efectivo).
- El estado cambia a `sent` DESPUES de generar el PDF exitosamente (atomicidad: si el PDF falla, el estado no cambia).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Body completamente vacio | Usar canales default: ["email", "portal"] |
| Paciente sin email, canales default | Usar solo "portal" si el paciente tiene cuenta; sino 422 sin canales efectivos |
| PDF S3 upload falla | 500, rollback — NO cambiar status a sent |
| Factura ya en status `sent` | 409 Conflict |
| Factura en status `paid` | 409 Conflict |
| recipient_email diferente al del paciente | Usar recipient_email para canal email; email del paciente en DB no se modifica |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `invoices`: UPDATE — `status = 'sent'`, `sent_at`, `sent_by`, `pdf_url`, `updated_at`

**Example query (SQLAlchemy):**
```python
from sqlalchemy import update

await session.execute(
    update(Invoice)
    .where(Invoice.id == invoice_id)
    .where(Invoice.tenant_id == tenant_id)
    .values(
        status="sent",
        sent_at=datetime.utcnow(),
        sent_by=user_id,
        pdf_url=pdf_s3_path,
        updated_at=datetime.utcnow(),
    )
)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:invoice:{invoice_id}`: DELETE — invalidar detalle cacheado
- `tenant:{tenant_id}:invoice_list:*`: DELETE PATTERN — invalidar listado

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications.invoice_sent | invoice_send | { invoice_id, patient_id, tenant_id, channels, recipient_email, pdf_url, message, invoice_number, total, currency, balance_due, due_date, clinic_name, clinic_logo_url } | Inmediatamente tras cambiar status a sent |

**Worker responsibilities (async):**
- Canal `email`: Renderizar template `invoice_sent` con datos, enviar via SMTP/SendGrid.
- Canal `whatsapp`: Enviar mensaje con enlace al PDF via Twilio o Meta Business API.
- Canal `portal`: Crear notificacion in-app para la cuenta del portal del paciente.

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** invoice
- **PHI involved:** No (datos financieros)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | invoice_sent | Paciente (email o recipient_email) | Canal email en channels_dispatched |
| whatsapp | Aprobado Meta: nueva factura disponible | Paciente (telefono registrado) | Canal whatsapp en channels_dispatched |
| in-app (portal) | Notificacion: nueva factura disponible | Cuenta portal del paciente | Canal portal en channels_dispatched |

---

## Performance

### Expected Response Time
- **Target:** < 800ms (incluye generacion sincrona de PDF)
- **Maximum acceptable:** < 3000ms (factura con muchos items + upload S3 lento)

### Caching Strategy
- **Strategy:** Sin cache para el resultado. PDF almacenado en S3.
- **Cache key:** N/A para resultado
- **TTL:** N/A
- **Invalidation:** Cache de factura y listado invalidados

### Database Performance

**Queries executed:** 4 (verificar paciente, buscar factura + items para PDF, update status)

**Indexes required:**
- `invoices.(id, patient_id, tenant_id)` — INDEX COMPUESTO
- `invoice_items.invoice_id` — INDEX

**N+1 prevention:** Items de la factura cargados con selectinload para generacion del PDF.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, invoice_id (URL) | Pydantic UUID | |
| channels | Pydantic list[Enum] — valores estrictos | |
| message | Pydantic str, strip, max_length=500, bleach | Aparece en email y PDF |
| recipient_email | Pydantic EmailStr | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Serializacion Pydantic. Contenido del PDF sanitizado con bleach.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** El PDF incluye nombre del paciente y procedimientos (datos clinicos indirectos). Transmision via SMTP y S3 cifrados (TLS).

**Audit requirement:** Write-only logged (envio de factura con canales)

---

## Testing

### Test Cases

#### Happy Path
1. Enviar factura por email y portal
   - **Given:** Factura `draft`, paciente con email, usuario `receptionist`
   - **When:** POST /send con `{"channels": ["email", "portal"]}`
   - **Then:** 200 OK, `status: "sent"`, PDF generado, job encolado en RabbitMQ

2. Enviar sin especificar canales (default)
   - **Given:** Factura `draft`, paciente con email
   - **When:** POST con body `{}`
   - **Then:** 200 OK, canales default `["email", "portal"]`

3. Enviar por WhatsApp (integracion configurada)
   - **Given:** Tenant con `whatsapp_configured=true`, paciente con telefono
   - **When:** POST con `{"channels": ["whatsapp"]}`
   - **Then:** 200 OK, job encolado para WhatsApp

4. Enviar con recipient_email alternativo
   - **Given:** Factura `draft`, paciente con email diferente
   - **When:** POST con `{ "recipient_email": "alternativo@gmail.com" }`
   - **Then:** 200 OK, job encolado con `recipient_email: "alternativo@gmail.com"`

#### Edge Cases
1. Paciente sin email, canal email solicitado
   - **Given:** Paciente sin email, `channels: ["email", "portal"]`
   - **When:** POST send
   - **Then:** 200 OK, `channels_dispatched: ["portal"]` (email excluido)

2. Factura con pdf_url ya generado (B-06 previo)
   - **Given:** Factura `draft` con PDF ya generado
   - **When:** POST send
   - **Then:** PDF se regenera con datos actualizados, nueva URL firmada

#### Error Cases
1. Factura ya en estado `sent`
   - **Given:** `invoice.status = "sent"`
   - **When:** POST send
   - **Then:** 409 Conflict con estado actual

2. Canal WhatsApp sin configuracion
   - **Given:** `tenant.whatsapp_configured = false`, `channels: ["whatsapp"]`
   - **When:** POST send
   - **Then:** 422 con instrucciones de configuracion

3. Rol `assistant`
   - **Given:** JWT con rol `assistant`
   - **When:** POST send
   - **Then:** 403 Forbidden

4. PDF upload a S3 falla
   - **Given:** S3 unavailable
   - **When:** POST send
   - **Then:** 500, estado de factura NO cambia (sigue en `draft`)

### Test Data Requirements

**Users:** Un `clinic_owner`, un `receptionist`, un `doctor`, un `assistant` (para 403).

**Patients:** Un paciente con email, uno sin email.

**Invoices:** Una factura `draft`, una `sent` (para 409).

**Tenant Config:** Tenant con y sin WhatsApp configurado.

### Mocking Strategy

- **RabbitMQ:** Mock del publisher — verificar job encolado con payload correcto
- **S3:** Mock de upload — retornar URL firmada simulada
- **Playwright:** Mock para retornar bytes de PDF en unit tests
- **Redis:** fakeredis para rate limiting

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Status cambia de `draft` a `sent` al enviar
- [ ] PDF generado y URL firmada incluida en respuesta (24h)
- [ ] Job `invoice_send` encolado en `notifications.invoice_sent`
- [ ] Default canales: `["email", "portal"]`
- [ ] WhatsApp rechaza con 422 si no configurado
- [ ] Factura no-draft retorna 409
- [ ] PDF fallo no cambia estado (rollback)
- [ ] Rol `assistant` retorna 403
- [ ] All test cases pass
- [ ] Performance targets met (< 3000ms con PDF)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Re-envio de factura ya enviada (endpoint separado, post-MVP)
- Generacion de PDF sin enviar (ver B-06 invoice-pdf.md)
- DIAN factura electronica (ver specs/compliance/)
- Configuracion de templates de email
- Firma electronica del paciente sobre la factura

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (channels como Enum, message, recipient_email)
- [x] All outputs defined (status, sent_at, pdf_url, channels_dispatched)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated (409 por estado, 422 por canal)
- [x] Auth requirements explicit (rol doctor restringido)
- [x] Side effects listed (DB, cache, RabbitMQ, S3)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing → notifications via RabbitMQ)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] PDF generacion sincrona justificada (URL requerida en response)

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization (bleach para message en PDF/email)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] Datos de paciente en PDF: TLS en transito
- [x] Audit trail para envio

### Hook 4: Performance & Scalability
- [x] Response time target (< 3000ms con PDF)
- [x] Envio real asincrono via RabbitMQ
- [x] Cache invalidacion en send
- [x] PDF generacion sincrona aceptable para este caso

### Hook 5: Observability
- [x] Structured logging (canales, invoice_id, tenant_id)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (RabbitMQ, S3, Playwright)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
