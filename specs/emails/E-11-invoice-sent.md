# E-11 — Factura Enviada al Paciente

---

## Overview

**Feature:** Notificación enviada al paciente cuando se emite y envía una factura por servicios dentales. Incluye resumen de los ítems facturados, monto total, fecha de vencimiento, link al portal para ver la factura completa y link de pago (si el tenant tiene pagos online habilitados). Adjunta el PDF de la factura en el email.

**Domain:** billing / notifications

**Priority:** High

**Dependencies:** B-05 (invoice-send), B-01 (invoice-create), P-14 (patient-portal), N-04, N-05

---

## Trigger

**Evento:** `invoice_sent`

**Cuándo se dispara:** Al ejecutar `POST /api/v1/invoices/{id}/send` o al cambiar el status de la factura a `sent`. Puede ser enviada manualmente por el staff o automáticamente al finalizar un procedimiento (según configuración del tenant).

**RabbitMQ routing key:** `notification.billing.invoice_sent`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente del invoice | patient | Siempre |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal; incluye PDF adjunto |
| whatsapp | Yes | Resumen corto con link al portal |
| sms | No | Información financiera requiere más contexto |
| in-app | Yes | Notificación en portal del paciente |

---

## Email Template

### Subject Line

```
Factura #{{invoice_number}} de {{clinic_name}} — ${{total_amount_display}}
```

**Ejemplo:** "Factura #F-2026-0042 de Clínica Smile — $350.000 COP"

### Preheader

```
Tu factura está lista. Vence el {{due_date_short}}. {{#if payment_link_enabled}}Paga en línea de forma segura.{{/if}}
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica

[HERO — Fondo verde muy claro, ícono de factura/documento]
  - Ícono: 🧾
  - Título H1: "Tu factura está lista"
  - Subtítulo: "Hola {{patient_first_name}}, aquí está el resumen de los servicios recibidos en {{clinic_name}}."

[RESUMEN DE FACTURA — Card prominente]
  Encabezado:
  - Número de factura: #{{invoice_number}}
  - Fecha: {{invoice_date}}
  - Vence: {{due_date}} ({{days_until_due}} días)

  Tabla de ítems (máximo 5 rows; si más, mostrar primeros 4 + "Ver factura completa"):
  | Procedimiento          | Cantidad | Precio    |
  |------------------------|----------|-----------|
  | {{item_1_description}} | {{item_1_qty}} | ${{item_1_amount}} |
  | {{item_2_description}} | {{item_2_qty}} | ${{item_2_amount}} |
  ... hasta 4 ítems ...
  | [Si hay más] Ver todos los servicios → |

  Separador
  | Subtotal    | ${{subtotal_display}} |
  | IVA ({{tax_rate}}%) | ${{tax_amount_display}} |
  | **TOTAL** | **${{total_amount_display}}** |

  Si hay saldo previo:
  | Saldo anterior | ${{previous_balance_display}} |
  | **Total con saldo** | **${{total_with_balance_display}}** |

[CTA PRINCIPAL — Condicional]

  Si pagos online habilitados:
  Botón verde grande: "Pagar ahora — ${{total_amount_display}}"
  URL: {{payment_link_url}}
  Subtexto: "Pago seguro vía {{payment_provider_display}}" (e.g., "PSE / Tarjeta de crédito")

  Si pagos online no habilitados:
  Botón azul: "Ver factura completa"
  URL: {{patient_portal_invoice_url}}

[MÉTODOS DE PAGO — Si pagos online no habilitados]
  Título: "¿Cómo pagar?"
  Información según configuración de la clínica:
  - Efectivo en clínica
  - Transferencia a {{clinic_bank_info}}
  - Tarjeta en clínica

[PDF ATTACHMENT NOTE]
  Ícono de PDF: "Se adjunta la factura en formato PDF para tus registros."
  (El PDF real va como attachment en el email — ver PDF Attachment section)

[INFORMACIÓN DE LA FACTURA ELECTRÓNICA — Si DIAN e-invoice]
  Si `dian_cufe != null`:
  Texto: "Esta es una factura electrónica válida ante la DIAN."
  CUFE: {{dian_cufe}} (texto pequeño, gris)

[FOOTER]
  - Logo DentalOS
  - Unsubscribe: Gestionar preferencias
  - Política de privacidad
```

### CTA Button

```
Con pagos online:
Texto: "Pagar ahora — ${{total_amount_display}}"
URL: {{payment_link_url}}
Color: #16A34A (verde — dinero/pago)

Sin pagos online:
Texto: "Ver factura completa"
URL: {{patient_portal_invoice_url}}
Color: #2563EB (azul)
```

### PDF Attachment

```
Archivo adjunto: factura_{{invoice_number}}.pdf
Generado por: servicio de generación de PDFs (Playwright headless Chromium)
Tamaño máximo: 2MB
Contenido: Factura completa con logo, detalles, tabla de ítems, totales, firma electrónica (si DIAN)
```

**Nota de implementación:** El PDF se genera sincrónicamente antes de publicar el evento a RabbitMQ, y su URL (CDN) se incluye en el payload del evento. El worker de notificaciones descarga el PDF desde CDN y lo adjunta al email via SendGrid API.

### Plain-text Fallback

```
Factura #{{invoice_number}} — {{clinic_name}}

Hola {{patient_first_name}},

Tu factura está lista:

Número: #{{invoice_number}}
Fecha: {{invoice_date}}
Vence: {{due_date}}
Total: ${{total_amount_display}}

Para ver tu factura: {{patient_portal_invoice_url}}
{{#if payment_link_enabled}}Para pagar en línea: {{payment_link_url}}{{/if}}

¿Preguntas? Llama al {{clinic_phone}}

© {{clinic_name}} | Gestionado por DentalOS
```

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_invoice_sent_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text

```
Hola {{1}}, {{2}} te envió la factura #{{3}} por ${{4}}.

{{#if_var 5}}Para pagar en línea: {{5}}{{/if_var}}

Para ver tu factura: {{6}}

Vence el {{7}}.
```

**Nota:** WhatsApp no soporta condicionales en templates aprobados. Se usarán dos templates separados: uno con link de pago y otro sin.

### Template A (con pago online)

```
dentalos_invoice_sent_with_payment_v1:
Hola {{1}}, {{2}} te envió la factura #{{3}} por ${{4}}. Paga en línea: {{5}} o ve el detalle: {{6}}. Vence el {{7}}.
```

### Template B (sin pago online)

```
dentalos_invoice_sent_no_payment_v1:
Hola {{1}}, {{2}} te envió la factura #{{3}} por ${{4}}. Ve el detalle en: {{5}}. Vence el {{6}}. ¿Preguntas? {{7}}
```

---

## In-App Notification (para el Paciente — Portal)

```json
{
  "type": "billing",
  "title": "Nueva factura disponible",
  "body": "{{clinic_name}} envió la factura #{{invoice_number}} por ${{total_amount_display}}. Vence el {{due_date_short}}.",
  "action_url": "/facturas/{{invoice_id}}",
  "metadata": {
    "invoice_id": "{{invoice_id}}",
    "amount": "{{total_amount_cents}}"
  }
}
```

**Color del ícono:** Verde (`#16A34A`) — tipo `billing`

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{invoice_number}}` | string | `tenant.invoices.invoice_number` | "F-2026-0042" |
| `{{invoice_date}}` | string | `invoices.issued_at` formateado | "25 de febrero de 2026" |
| `{{due_date}}` | string | `invoices.due_date` formateado completo | "7 de marzo de 2026" |
| `{{due_date_short}}` | string | Formato corto | "7 de marzo" |
| `{{days_until_due}}` | integer | `due_date - today` | 10 |
| `{{subtotal_display}}` | string | Subtotal formateado COP | "$302.521" |
| `{{tax_rate}}` | integer | `invoices.tax_rate_pct` | 19 |
| `{{tax_amount_display}}` | string | Monto IVA formateado | "$57.479" |
| `{{total_amount_display}}` | string | Total formateado COP | "$360.000" |
| `{{total_amount_cents}}` | integer | Total en centavos | 36000000 |
| `{{previous_balance_display}}` | string / null | Saldo previo si existe | "$50.000" |
| `{{item_1_description}}` .. `{{item_4_description}}` | string | `invoice_items[i].description` | "Extracción de molar" |
| `{{item_1_qty}}` .. `{{item_4_qty}}` | integer | Cantidad | 1 |
| `{{item_1_amount}}` .. `{{item_4_amount}}` | string | Precio formateado | "$150.000" |
| `{{remaining_items_count}}` | integer | `invoice_items.count - 4` (si > 4) | 3 |
| `{{payment_link_url}}` | string / null | Generado si pagos online habilitados | URL |
| `{{payment_link_enabled}}` | boolean | `tenant.settings.online_payments_enabled` | true |
| `{{payment_provider_display}}` | string | Proveedor de pagos del tenant | "PSE / Tarjeta" |
| `{{patient_portal_invoice_url}}` | string | `{portal_url}/facturas/{invoice_id}` | URL |
| `{{pdf_attachment_url}}` | string | CDN URL del PDF generado | URL |
| `{{dian_cufe}}` | string / null | CUFE DIAN si es factura electrónica | Hash |
| `{{clinic_name}}` | string | Tenant name | "Clínica Smile" |
| `{{clinic_phone}}` | string | Tenant settings | "601-555-0100" |
| `{{clinic_bank_info}}` | string / null | Info bancaria si configurado | "Bancolombia 123-456789" |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al cambiar estado a `sent`.
- **Prioridad:** High (priority: 7).

### Deduplication
- **Idempotency key:** `invoice_sent:{invoice_id}`
- Re-envío manual por staff genera nuevo event con `{invoice_id}:{resend_timestamp}`.

### PDF Generation
- El PDF debe estar generado y disponible en CDN antes de que el worker intente adjuntarlo.
- Si el PDF no está disponible, el worker espera máximo 10s (polling con backoff). Si sigue sin disponible, envía el email sin adjunto y loggea warning. El paciente puede descargarlo desde el portal.

---

## Testing

### Test Cases

#### Happy Path
1. Factura con 3 ítems y pagos online habilitados
   - **Given:** Invoice con 3 items, tenant con PSE habilitado
   - **When:** Invoice enviado
   - **Then:** Email con tabla de ítems, botón "Pagar ahora", PDF adjunto; WhatsApp template A; in-app verde

2. Factura con más de 4 ítems
   - **Given:** Invoice con 7 items
   - **When:** Template renderizado
   - **Then:** Muestra 4 ítems + "Ver 3 más en portal"; no trunca datos financieros

3. Factura electrónica DIAN
   - **Given:** Factura con CUFE no nulo
   - **When:** Email enviado
   - **Then:** CUFE visible en el email; texto "factura electrónica válida ante la DIAN"

#### Edge Cases
1. PDF no disponible en CDN a tiempo
   - **Given:** Generación de PDF tarda más de 10s
   - **When:** Worker intenta adjuntar
   - **Then:** Email enviado sin adjunto; nota al paciente que puede descargarlo desde el portal; warning en logs

2. Pagos online no habilitados
   - **Given:** `tenant.settings.online_payments_enabled = false`
   - **When:** Email y WhatsApp enviados
   - **Then:** Email usa template sin botón de pago; WhatsApp usa template B; se muestra info de pago en clínica

3. Factura con saldo anterior
   - **Given:** `previous_balance != null`
   - **When:** Template renderizado
   - **Then:** Fila de "Saldo anterior" incluida; total con saldo mostrado prominentemente

#### Error Cases
1. PDF supera 2MB
   - **Given:** PDF de factura excepcionalmente grande (imágenes de radiografías, etc.)
   - **When:** Worker intenta adjuntar
   - **Then:** PDF omitido del adjunto; email enviado con link de descarga al portal; Sentry warning

### Mocking Strategy

- SendGrid: mock con captura de attachments para verificar PDF
- PDF CDN: mock URL que devuelve un PDF de prueba válido
- WhatsApp: respx mock

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado con tabla de ítems (máx 4 + "ver más")
- [ ] PDF de la factura adjunto al email
- [ ] Botón de pago online visible si tenant habilitado
- [ ] WhatsApp template correcto (A o B) según configuración de pagos
- [ ] In-app con tipo `billing` (verde) en portal del paciente
- [ ] CUFE DIAN visible si es factura electrónica
- [ ] PDF no disponible: email enviado sin adjunto con nota de descarga
- [ ] Saldo anterior incluido si existe
- [ ] Todos los test cases pasan

---

## Out of Scope

- El endpoint de envío de factura (spec B-05)
- El proceso de pago online (spec B-10)
- Recordatorio de pago vencido (spec E-13)
- Generación del PDF (spec B-06)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
