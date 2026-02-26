# Quotation Send (B-18)

---

## Overview

**Feature:** Enviar una cotizacion existente en estado `draft` al paciente a traves de uno o mas canales (email, WhatsApp, notificacion en portal). Genera un PDF con el branding de la clinica, lista de procedimientos, precios y total, cambia el estado de la cotizacion a `sent` y encola el trabajo de envio en RabbitMQ.

**Domain:** billing

**Priority:** High

**Dependencies:** B-16 (quotation-create.md — la cotizacion debe existir en estado draft), E-20 (email template quotation_sent — nueva), notifications (para notificacion en portal), I-02 (authentication-rules.md)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** doctor, clinic_owner, receptionist
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Los asistentes NO pueden enviar cotizaciones. Solo roles con capacidad de comunicacion directa con el paciente. El paciente y la cotizacion deben pertenecer al mismo tenant.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/quotations/{quotation_id}/send
```

**Rate Limiting:**
- 20 requests por minuto por usuario
- Redis sliding window: `dentalos:rl:quotation_send:{user_id}` (TTL 60s)

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
| quotation_id | Yes | UUID | UUID v4 valido | ID de la cotizacion a enviar | quot_9a1b2c3d-e4f5-6789-abcd-ef0123456789 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "channels": ["string (optional) — email | whatsapp | portal — default: [email, portal] si no se especifica"],
  "message": "string (optional) — mensaje personalizado para el paciente, max 500 chars",
  "recipient_email": "string (optional) — email alternativo para envio, si difiere del email del paciente en sistema"
}
```

**Example Request:**
```json
{
  "channels": ["email", "whatsapp"],
  "message": "Estimado paciente, adjuntamos su cotizacion. Recuerde que esta vigente por 30 dias. Cualquier consulta con gusto la atendemos."
}
```

**Example Request (minimal — usar defaults):**
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
  "quotation_id": "UUID",
  "quotation_number": "string",
  "status": "sent",
  "sent_at": "ISO8601",
  "channels_dispatched": ["string"],
  "recipient_email": "string | null",
  "pdf_url": "string — URL firmada S3, expira en 24h"
}
```

**Example:**
```json
{
  "quotation_id": "quot_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "quotation_number": "COT-2026-00042",
  "status": "sent",
  "sent_at": "2026-02-24T15:00:00Z",
  "channels_dispatched": ["email", "whatsapp"],
  "recipient_email": "juan.perez@gmail.com",
  "pdf_url": "https://storage.dentalos.com/quotations/tn_7c9e/COT-2026-00042.pdf?X-Amz-Signature=...&X-Amz-Expires=86400"
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
**When:** Rol no autorizado (`assistant`) o cotizacion no pertenece al tenant del usuario.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para enviar esta cotizacion."
}
```

#### 404 Not Found
**When:** `patient_id` o `quotation_id` no existen en el tenant, o la cotizacion no pertenece al paciente.

```json
{
  "error": "quotation_not_found",
  "message": "La cotizacion no fue encontrada."
}
```

#### 409 Conflict
**When:** La cotizacion no esta en estado `draft` (ya fue enviada, pagada, rechazada o cancelada).

```json
{
  "error": "quotation_not_draft",
  "message": "Solo se pueden enviar cotizaciones en estado borrador. Esta cotizacion tiene estado: sent."
}
```

#### 422 Unprocessable Entity
**When:** Canal `whatsapp` solicitado pero la clinica no tiene WhatsApp configurado. Paciente sin email y se solicita canal `email`.

**Example:**
```json
{
  "error": "channel_not_available",
  "message": "El canal WhatsApp no esta configurado para esta clinica. Configure la integracion en el panel de administracion.",
  "details": {
    "channels": ["whatsapp no disponible — configurar en admin/integrations"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido (20/min por usuario).

#### 500 Internal Server Error
**When:** Error al generar el PDF o al encolar el trabajo de envio.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `doctor`, `clinic_owner` o `receptionist`. Si no, retornar 403.
3. Validar body: `channels` debe ser subconjunto de `["email", "whatsapp", "portal"]`. `message` max 500 chars.
4. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
5. Verificar que la cotizacion existe, pertenece al paciente y al tenant. Si no, 404.
6. Verificar que `quotation.status == "draft"`. Si no, 409 con el estado actual.
7. Determinar canales efectivos:
   - Si `channels` no se provee: usar `["email", "portal"]` como default.
   - Si `whatsapp` en canales: verificar que `tenant.whatsapp_configured == true`. Si no, 422.
   - Si `email` en canales: verificar que el paciente tiene email registrado (o se provee `recipient_email`). Si no, excluir canal email y loguear advertencia (no bloquear).
8. **Generar PDF:**
   a. Recopilar datos: branding del tenant (logo, nombre, NIT, direccion), datos del paciente (nombre, documento), items de cotizacion, totales, numero, vigencia, notas.
   b. Renderizar PDF con template HTML + Playwright. Incluir tabla de procedimientos, precios formateados en moneda del tenant, total destacado, fecha de validez.
   c. Subir PDF a S3 en ruta: `{tenant_id}/quotations/{quotation_number}.pdf`.
   d. Generar URL firmada con expiracion de 24 horas.
9. Actualizar `quotation.status = "sent"` y `quotation.sent_at = now()`.
10. Encolar trabajo en RabbitMQ (`notifications.quotation_sent`) con payload completo (ver Queue Jobs).
11. Registrar en log estructurado: `billing.quotation.sent` con canales, `quotation_id`, `patient_id`, `tenant_id`.
12. Retornar 200 OK con `status: sent`, `sent_at`, `channels_dispatched`, `pdf_url`.

**Nota:** El envio real de email/WhatsApp ocurre de forma asincrona en el worker de notificaciones. El endpoint retorna inmediatamente despues de encolar el trabajo.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| quotation_id (URL) | UUID v4, cotizacion debe ser del paciente y tenant | "La cotizacion no fue encontrada." |
| channels | Array, cada elemento en ["email", "whatsapp", "portal"] | "Los canales validos son: email, whatsapp, portal." |
| message | Max 500 chars | "El mensaje no puede superar los 500 caracteres." |
| recipient_email | Formato email valido si se provee | "El correo alternativo no tiene un formato valido." |

**Business Rules:**

- Solo se pueden enviar cotizaciones en estado `draft`. Si ya esta `sent`, el sistema no re-envia automaticamente (se necesita accion explicita de re-envio — endpoint separado no cubierto en esta spec).
- El canal `whatsapp` requiere que la integracion este configurada en el tenant (integracion con Twilio o Meta Business API).
- El PDF se genera sincrona antes de encolar el envio, para que la URL este disponible en la respuesta inmediata.
- El canal `portal` siempre esta disponible si el paciente tiene cuenta en el portal del paciente.
- Si el paciente no tiene email y se solicita canal `email`, se excluye silenciosamente ese canal (no error, solo advertencia en log).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Body completamente vacio `{}` | Usar canales default: ["email", "portal"] |
| Canal email sin email de paciente | Excluir email de `channels_dispatched`, continuar con otros canales |
| Canal portal sin cuenta de paciente | Excluir portal de `channels_dispatched`, continuar |
| Cotizacion ya en status `sent` | 409 Conflict |
| Cotizacion en status `paid` | 409 Conflict |
| PDF fallido (error S3) | 500, no cambiar estado de cotizacion (rollback) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `quotations`: UPDATE — `status = 'sent'`, `sent_at = now()`, `pdf_url`, `sent_by = user_id`

**Example query (SQLAlchemy):**
```python
from sqlalchemy import update

await session.execute(
    update(Quotation)
    .where(Quotation.id == quotation_id)
    .where(Quotation.tenant_id == tenant_id)
    .values(
        status="sent",
        sent_at=datetime.utcnow(),
        pdf_url=pdf_s3_path,
        sent_by=user_id,
    )
)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- Ninguna clave de cache se modifica directamente.

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications.quotation_sent | quotation_send | { quotation_id, patient_id, tenant_id, channels, recipient_email, pdf_url, message, quotation_number, total, currency, valid_until, clinic_name, clinic_logo_url } | Inmediatamente tras cambiar status a sent |

**Worker responsibilities (async):**
- Canal `email`: Renderizar template E-20 con datos de cotizacion, enviar via SMTP/SendGrid.
- Canal `whatsapp`: Enviar mensaje con enlace al PDF via Twilio o Meta Business API.
- Canal `portal`: Crear notificacion in-app para el paciente en el portal.

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** quotation
- **PHI involved:** No (datos financieros)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| email | E-20 (quotation_sent) | Paciente (email registrado o recipient_email) | Cuando canal email esta en channels_dispatched |
| whatsapp | Template WhatsApp aprobado por Meta | Paciente (numero de telefono registrado) | Cuando canal whatsapp esta en channels_dispatched |
| in-app (portal) | Notificacion portal: nueva cotizacion disponible | Cuenta de portal del paciente | Cuando canal portal esta en channels_dispatched |

---

## Performance

### Expected Response Time
- **Target:** < 800ms (incluye generacion sincrona de PDF)
- **Maximum acceptable:** < 2500ms (PDF de cotizacion con muchos items puede tardar mas)

### Caching Strategy
- **Strategy:** Sin cache para el resultado. El PDF generado se almacena en S3.
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 4 (verificar paciente, verificar cotizacion, cargar items para PDF, update status)

**Indexes required:**
- `quotations.(id, patient_id, tenant_id)` — INDEX COMPUESTO
- `quotation_items.quotation_id` — INDEX

**N+1 prevention:** Items cargados con una sola query. Datos del paciente y tenant cacheados en Redis (lectura desde cache si disponible).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, quotation_id (URL) | Pydantic UUID | |
| channels | Pydantic list[Enum] | Enum estricto de valores permitidos |
| message | Pydantic str, strip, max_length=500, bleach | Puede aparecer en email y PDF |
| recipient_email | Pydantic EmailStr | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings sanitizados con bleach antes de incluir en PDF y emails. Serializacion Pydantic para respuesta JSON.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno directamente. El PDF puede contener nombre del paciente y procedimientos (datos clinicos indirectos), pero el endpoint en si maneja datos financieros.

**Audit requirement:** Write-only logged (envio de cotizacion)

---

## Testing

### Test Cases

#### Happy Path
1. Enviar cotizacion por email y portal
   - **Given:** Cotizacion en estado `draft`, paciente con email registrado, usuario `doctor`
   - **When:** POST /api/v1/patients/{id}/quotations/{id}/send con `{"channels": ["email", "portal"]}`
   - **Then:** 200 OK, `status: "sent"`, `channels_dispatched: ["email", "portal"]`, `pdf_url` no nulo, job encolado en RabbitMQ

2. Enviar sin especificar canales (default)
   - **Given:** Cotizacion en draft, paciente con email
   - **When:** POST con body `{}`
   - **Then:** 200 OK, canales default `["email", "portal"]` usados

3. Enviar con mensaje personalizado
   - **Given:** Cotizacion en draft
   - **When:** POST con `message: "Su cotizacion esta lista."`
   - **Then:** 200 OK, mensaje incluido en payload del job RabbitMQ

4. Enviar por WhatsApp (integracion configurada)
   - **Given:** Tenant con `whatsapp_configured=true`, paciente con telefono
   - **When:** POST con `{"channels": ["whatsapp"]}`
   - **Then:** 200 OK, job encolado para WhatsApp

#### Edge Cases
1. Paciente sin email, canal email solicitado
   - **Given:** Paciente sin email registrado, `channels: ["email", "portal"]`
   - **When:** POST send
   - **Then:** 200 OK, `channels_dispatched: ["portal"]` (email excluido silenciosamente)

2. Body vacio (minimal)
   - **Given:** Cotizacion en draft
   - **When:** POST con `{}`
   - **Then:** 200 OK con canales default

#### Error Cases
1. Cotizacion ya enviada
   - **Given:** Cotizacion con `status: "sent"`
   - **When:** POST send nuevamente
   - **Then:** 409 Conflict con mensaje indicando estado actual

2. Canal whatsapp sin configuracion
   - **Given:** Tenant sin `whatsapp_configured`, `channels: ["whatsapp"]`
   - **When:** POST send
   - **Then:** 422 Unprocessable Entity con instrucciones de configuracion

3. Cotizacion de otro tenant
   - **Given:** `quotation_id` de tenant B, usuario en tenant A
   - **When:** POST send
   - **Then:** 404 Not Found

4. Rol no autorizado (assistant)
   - **Given:** Usuario con rol `assistant`
   - **When:** POST send
   - **Then:** 403 Forbidden

5. Canal invalido
   - **Given:** `channels: ["telegram"]`
   - **When:** POST send
   - **Then:** 400 Bad Request con valores permitidos

### Test Data Requirements

**Users:** Un `doctor`, un `clinic_owner`, un `receptionist`, un `assistant` (para test 403).

**Patients:** Un paciente con email, un paciente sin email.

**Quotations:** Una cotizacion `draft`, una cotizacion `sent`, una cotizacion `paid`.

**Tenant Config:** Un tenant con WhatsApp configurado, uno sin.

### Mocking Strategy

- **RabbitMQ:** Mock del publisher — verificar que el job fue encolado con el payload correcto
- **S3:** Mock de upload — retornar URL firmada simulada
- **Redis:** fakeredis para rate limiting
- **PDF Generator:** Mock para retornar bytes de PDF en unit tests; test real de generacion en integration tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST cambia estado de cotizacion de `draft` a `sent`
- [ ] PDF generado y URL firmada incluida en respuesta (expira 24h)
- [ ] Job `quotation_send` encolado en `notifications.quotation_sent`
- [ ] Canal default es `["email", "portal"]` si no se especifica
- [ ] Canal `whatsapp` rechaza con 422 si no esta configurado en tenant
- [ ] Cotizacion ya enviada retorna 409 con estado actual
- [ ] Rol `assistant` retorna 403
- [ ] Paciente sin email excluye canal email sin error
- [ ] All test cases pass
- [ ] Performance targets met (< 2500ms generacion PDF)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Re-envio de cotizacion ya enviada (endpoint separado)
- Aprobacion/rechazo de cotizacion por el paciente
- Generacion de factura desde cotizacion aprobada
- Template de email E-20 (referenciado pero definido en specs/emails/E-20.md)
- Configuracion de integracion WhatsApp (admin/integrations)
- Firma digital del paciente sobre la cotizacion

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response model)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated (incluyendo casos por canal)
- [x] Auth requirements explicit (role + tenant)
- [x] Side effects listed (DB update, queue job, S3 upload)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing domain, notificaciones asincronas)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (bleach para message en PDF/email)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure en logs (solo IDs, no datos clinicos)
- [x] Audit trail para envio

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 2500ms con PDF)
- [x] PDF generacion sincrona justificada (URL necesaria en respuesta)
- [x] Envio real asincrono via RabbitMQ
- [x] DB queries optimizados

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, quotation_id, canales incluidos)
- [x] Audit log entries defined (update, no PHI)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (workers de notificaciones)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy para RabbitMQ, S3, PDF generator
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
