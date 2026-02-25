# E-12 — Confirmación de Pago Recibido

---

## Overview

**Feature:** Confirmación enviada al paciente cuando se registra un pago en DentalOS. Puede ser un pago en efectivo registrado por recepción, pago con tarjeta en clínica, o pago online. Incluye monto pagado, método de pago, número de recibo, saldo restante (si la factura no está saldada en su totalidad) y adjunto del recibo en PDF.

**Domain:** billing / notifications

**Priority:** High

**Dependencies:** B-08 (payment-record), B-09 (payment-online-webhook), E-11 (invoice-sent), N-04, N-05

---

## Trigger

**Evento:** `payment_received`

**Cuándo se dispara:**
1. Al registrar pago manual: `POST /api/v1/payments` exitoso
2. Al recibir webhook de pago online (PSE, tarjeta) con estado `success`
3. Al procesar cualquier pago parcial o total de una factura

**RabbitMQ routing key:** `notification.billing.payment_received`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente | patient | Siempre |
| Recepcionista / Clinic Owner | receptionist, clinic_owner | In-app únicamente (notificación de pago registrado) |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal; incluye recibo PDF adjunto |
| whatsapp | No | Confirmaciones de pago son más formales; email es suficiente |
| sms | No | No aplica |
| in-app | Yes | Para el paciente en el portal y para el staff de la clínica |

---

## Email Template

### Subject Line

Pago total:
```
Pago confirmado: ${{amount_paid_display}} recibido — {{clinic_name}}
```

Pago parcial:
```
Pago parcial de ${{amount_paid_display}} registrado — Saldo: ${{remaining_balance_display}}
```

### Preheader

```
Tu pago de ${{amount_paid_display}} en {{clinic_name}} fue registrado exitosamente. Recibo: #{{receipt_number}}.
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica

[HERO — Fondo verde, ícono de checkmark en círculo]
  - Ícono: ✓ (checkmark verde grande)
  - Título H1: "¡Pago confirmado!"
  - Subtítulo: "Hola {{patient_first_name}}, recibimos tu pago exitosamente."

[RESUMEN DEL PAGO — Card prominente con borde verde]
  Encabezado: "Detalles del pago"
  Tabla:
  - 🧾 Recibo #: {{receipt_number}}
  - 💰 Monto pagado: ${{amount_paid_display}}
  - 💳 Método de pago: {{payment_method_display}}
  - 📅 Fecha: {{payment_date}}
  - 🏥 Factura: #{{invoice_number}}
  - 👩‍💼 Recibido por: {{received_by_name}} (solo si es pago manual en clínica)

[ESTADO DE LA FACTURA]

  Si pago total (saldo = 0):
  Card con fondo verde claro, ícono de checkmark:
  "✓ Factura #{{invoice_number}} está PAGADA en su totalidad."
  Monto total factura: ${{invoice_total_display}}

  Si pago parcial (saldo > 0):
  Card con fondo amarillo claro:
  "📋 Pago parcial registrado."
  Tabla:
  - Total de la factura: ${{invoice_total_display}}
  - Total pagado: ${{total_paid_display}}
  - Saldo restante: ${{remaining_balance_display}}
  - Próximo vencimiento: {{due_date}}

[CTA]
  Botón: "Ver recibo completo"
  URL: {{patient_portal_receipt_url}}
  Color: #16A34A (verde)

[PDF ATTACHMENT NOTE]
  "Se adjunta tu recibo de pago en formato PDF."
  Nombre: "recibo_{{receipt_number}}.pdf"

[INFORMACIÓN DE CONTACTO]
  "¿Alguna pregunta sobre tu factura?"
  - Tel: {{clinic_phone}}

[FOOTER]
  - Logo DentalOS
  - Unsubscribe: Gestionar preferencias
  - Política de privacidad
```

### CTA Button

```
Texto: "Ver recibo completo"
URL: {{patient_portal_receipt_url}}
Color: #16A34A
Texto: blanco, bold
```

### Plain-text Fallback

```
Pago confirmado — {{clinic_name}}

Hola {{patient_first_name}},

Tu pago fue registrado exitosamente:

Recibo: #{{receipt_number}}
Monto: ${{amount_paid_display}}
Método: {{payment_method_display}}
Fecha: {{payment_date}}
Factura: #{{invoice_number}}

{{#if_paid_in_full}}Factura pagada en su totalidad.{{/if_paid_in_full}}
{{#if_partial}}Saldo restante: ${{remaining_balance_display}}{{/if_partial}}

Ver recibo: {{patient_portal_receipt_url}}
¿Preguntas? {{clinic_phone}}

© {{clinic_name}} | Gestionado por DentalOS
```

---

## In-App Notification (para el Paciente — Portal)

```json
{
  "type": "billing",
  "title": "Pago registrado",
  "body": "Tu pago de ${{amount_paid_display}} fue confirmado. Recibo #{{receipt_number}}.",
  "action_url": "/recibos/{{payment_id}}",
  "metadata": {
    "payment_id": "{{payment_id}}",
    "invoice_id": "{{invoice_id}}"
  }
}
```

---

## In-App Notification (para Staff — App Interna)

```json
{
  "type": "billing",
  "title": "Pago registrado",
  "body": "{{patient_full_name}} pagó ${{amount_paid_display}} {{#if_partial}}(pago parcial — saldo: ${{remaining_balance_display}}){{/if_partial}} {{#if_paid_in_full}}(factura saldada){{/if_paid_in_full}}",
  "action_url": "/billing/invoices/{{invoice_id}}",
  "metadata": {
    "invoice_id": "{{invoice_id}}",
    "payment_id": "{{payment_id}}"
  }
}
```

---

## Payment Method Display Names

| Método interno | Display |
|---------------|---------|
| `cash` | "Efectivo" |
| `credit_card` | "Tarjeta de crédito" |
| `debit_card` | "Tarjeta débito" |
| `pse` | "PSE (débito en línea)" |
| `bank_transfer` | "Transferencia bancaria" |
| `check` | "Cheque" |
| `other` | "Otro método" |

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{patient_full_name}}` | string | `tenant.patients.first_name + last_name` | "Ana Gómez" |
| `{{receipt_number}}` | string | `tenant.payments.receipt_number` | "REC-2026-0128" |
| `{{amount_paid_display}}` | string | `payments.amount` formateado en COP | "$350.000" |
| `{{payment_method_display}}` | string | Método convertido a display | "Efectivo" |
| `{{payment_date}}` | string | `payments.paid_at` formateado | "25 de febrero de 2026" |
| `{{invoice_number}}` | string | `invoices.invoice_number` | "F-2026-0042" |
| `{{invoice_total_display}}` | string | `invoices.total_amount` formateado | "$700.000" |
| `{{total_paid_display}}` | string | Suma de todos los pagos de la factura | "$350.000" |
| `{{remaining_balance_display}}` | string | `invoices.total - total_paid` | "$350.000" |
| `{{due_date}}` | string | `invoices.due_date` formateado | "7 de marzo de 2026" |
| `{{received_by_name}}` | string / null | `payments.received_by` nombre; null si es pago online | "Laura Torres" |
| `{{is_paid_in_full}}` | boolean | `invoices.status == 'paid'` | true |
| `{{payment_id}}` | uuid | `payments.id` | UUID |
| `{{invoice_id}}` | uuid | `invoices.id` | UUID |
| `{{patient_portal_receipt_url}}` | string | `{portal_url}/recibos/{payment_id}` | URL |
| `{{clinic_name}}` | string | Tenant name | "Clínica Smile" |
| `{{clinic_phone}}` | string | Tenant settings phone | "601-555-0100" |
| `{{clinic_logo_url}}` | string | Tenant settings logo | CDN URL |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al registrar el pago.
- **Prioridad:** High (priority: 7).
- **Latencia máxima:** 2 minutos — el paciente debe saber que su pago fue recibido.

### Deduplication
- **Idempotency key:** `payment_received:{payment_id}`
- **Ventana:** 24 horas.
- Los pagos son eventos únicos — la deduplication es principalmente para retries de RabbitMQ.

### Webhook de Pagos Online
- Cuando el pago llega via webhook (PSE / tarjeta), puede haber duplicados si el proveedor re-envía el webhook. La deduplication por `payment_id` maneja esto.
- El `payment_id` debe generarse antes de procesar el webhook (idempotent webhook processing).

### Pagos Parciales
- Si un paciente hace múltiples pagos parciales en la misma factura, cada pago genera su propia confirmación.
- El estado de la factura (total pagado, saldo restante) se actualiza en tiempo real.

---

## Testing

### Test Cases

#### Happy Path
1. Pago total en efectivo
   - **Given:** Paciente paga $360.000 COP en efectivo; factura de $360.000
   - **When:** Recepcionista registra pago
   - **Then:** Email con "Factura pagada en totalidad"; recibo PDF adjunto; in-app verde al paciente y al staff

2. Pago parcial
   - **Given:** Factura de $700.000; paciente paga $350.000
   - **When:** Pago registrado
   - **Then:** Email con pago parcial; saldo restante $350.000 visible; fecha de vencimiento; in-app con saldo

3. Pago online vía PSE
   - **Given:** Webhook de PSE recibido con pago exitoso
   - **When:** Webhook procesado
   - **Then:** Email enviado; `received_by_name` omitido (pago automático); método display "PSE"

#### Edge Cases
1. Webhook duplicado de PSE
   - **Given:** Proveedor re-envía el mismo webhook dentro de 5 minutos
   - **When:** Segundo webhook procesado
   - **Then:** Pago idempotente (no se crea segundo pago); notificación NO reenviada

2. Pago que salda una factura con saldo previo
   - **Given:** Factura con 2 pagos parciales previos; tercer pago salda el total
   - **When:** Tercer pago registrado
   - **Then:** Email muestra "Factura PAGADA" con historial total de pagos

#### Error Cases
1. PDF de recibo no disponible
   - **Given:** Error en la generación del PDF del recibo
   - **When:** Worker intenta adjuntar
   - **Then:** Email enviado sin adjunto; nota al paciente que puede descargarlo; warning loggado

### Test Data Requirements

- Factura con saldo pendiente parcial y total
- Métodos de pago: cash, credit_card, pse
- Paciente con email registrado

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 2min con detalles del pago
- [ ] Factura saldada en totalidad: "PAGADA" claramente visible
- [ ] Pago parcial: saldo restante y fecha de vencimiento visibles
- [ ] PDF del recibo adjunto al email
- [ ] Método de pago en español correcto
- [ ] In-app para paciente (portal) y para staff (app interna)
- [ ] Webhook duplicado: sin doble notificación
- [ ] Todos los test cases pasan

---

## Out of Scope

- El endpoint de registro de pago (spec B-08)
- El webhook de pagos online (spec B-09)
- Recordatorio de pago vencido (spec E-13)
- Conciliación de pagos con DIAN

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
