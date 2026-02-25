# E-13 — Recordatorio de Pago Vencido

---

## Overview

**Feature:** Recordatorio enviado al paciente cuando una factura está vencida. Se envía en tres instancias: a los 7, 15 y 30 días de vencimiento. El tono escala de amistoso (7d) a firme (30d). Máximo 3 recordatorios por factura. Incluye link de pago online si está habilitado.

**Domain:** billing / notifications

**Priority:** Medium

**Dependencies:** B-05 (invoice-send), B-11 (overdue-cron), E-11 (invoice-sent), E-12 (payment-confirmation), N-04, N-05

---

## Trigger

**Evento:** `invoice_payment_overdue`

**Cuándo se dispara:** Cron job diario (`0 9 * * *` — 9 AM en timezone de la clínica) que busca facturas con:
- `due_date < TODAY`
- `status IN ('sent', 'partial')`
- `total_paid < total_amount`
- Días de vencimiento = 7, 15 o 30 (tolerancia ±1 día para casos de horario de cron)

**Payload del evento:**
```json
{
  "event_type": "invoice_payment_overdue",
  "invoice_id": "uuid",
  "tenant_id": "uuid",
  "days_overdue": 7,
  "reminder_sequence": 1
}
```

**RabbitMQ routing key:** `notification.billing.payment_overdue`

**Query del cron:**
```sql
SELECT i.*, p.email, p.phone, p.first_name
FROM invoices i
JOIN patients p ON i.patient_id = p.id
WHERE i.due_date < CURRENT_DATE
  AND i.status IN ('sent', 'partial')
  AND (i.total_amount - COALESCE(i.total_paid, 0)) > 0
  AND i.overdue_reminder_count < 3
  AND (
    CURRENT_DATE - i.due_date::date = 7   -- primer recordatorio
    OR CURRENT_DATE - i.due_date::date = 15  -- segundo
    OR CURRENT_DATE - i.due_date::date = 30  -- tercero
  )
  AND i.deleted_at IS NULL
```

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente deudor | patient | Siempre |
| Clinic owner / recepcionista | clinic_owner, receptionist | In-app solo en el tercero (30d) como alerta de cobro |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal |
| whatsapp | Yes | Para mayor visibilidad de recordatorio de pago |
| sms | No | No aplica para recordatorios de pago |
| in-app | Yes | Para el paciente (portal) y para staff en el 3er recordatorio |

---

## Email Templates por Secuencia

### Template 1 — Amistoso (7 días vencido)

**Subject:**
```
Recordatorio de pago — Factura #{{invoice_number}} vencida hace {{days_overdue}} días
```

**Tono:** Amistoso, entendedor. Podría ser un olvido.

**Hero:**
```
[HERO — Fondo azul claro, ícono de campana]
Título: "Te recordamos sobre tu factura"
Subtítulo: "Hola {{patient_first_name}}, notamos que tienes un saldo pendiente en {{clinic_name}}."
```

**Párrafo:**
```
"Entendemos que a veces los pagos se nos pasan de largo. Te recordamos amablemente
que tienes una factura pendiente de ${{remaining_balance_display}} que venció el {{due_date}}."
```

---

### Template 2 — Recordatorio claro (15 días vencido)

**Subject:**
```
Segundo aviso: Factura #{{invoice_number}} lleva {{days_overdue}} días vencida — {{clinic_name}}
```

**Tono:** Más directo. Indica que es el segundo aviso. Menciona consecuencias potenciales.

**Hero:**
```
[HERO — Fondo amarillo claro, ícono de alerta]
Título: "Segundo aviso de pago"
Subtítulo: "Hola {{patient_first_name}}, tu factura de ${{remaining_balance_display}} lleva {{days_overdue}} días vencida."
```

**Párrafo:**
```
"Este es nuestro segundo aviso. Para evitar inconvenientes en tus próximas citas,
te pedimos que regularices tu pago a la brevedad posible."
```

---

### Template 3 — Urgente (30 días vencido)

**Subject:**
```
⚠ Último aviso: Factura #{{invoice_number}} con {{days_overdue}} días de mora — {{clinic_name}}
```

**Tono:** Firme. Último aviso. Posibles consecuencias de no pago.

**Hero:**
```
[HERO — Fondo rojo claro, ícono de alerta roja]
Título: "Último aviso de pago"
Subtítulo: "Hola {{patient_first_name}}, este es nuestro último aviso antes de escalar el cobro."
```

**Párrafo:**
```
"Tu cuenta en {{clinic_name}} tiene un saldo vencido de ${{remaining_balance_display}} con
{{days_overdue}} días de mora. Este es el tercer y último aviso automático.
Te pedimos que te comuniques con nosotros para regularizar o acordar un plan de pago."
```

---

## HTML Structure (Común para los 3)

```
[HEADER]
  - Logo clínica
  - Nombre clínica

[HERO — Variable según secuencia (ver arriba)]

[RESUMEN DE DEUDA — Card]
  Encabezado: "Estado de tu cuenta"
  Tabla:
  - Factura: #{{invoice_number}}
  - Fecha de vencimiento: {{due_date}}
  - Días vencida: {{days_overdue}} días
  - Total de la factura: ${{invoice_total_display}}
  - Ya pagado: ${{total_paid_display}}
  - **Saldo pendiente: ${{remaining_balance_display}}**

[CTA PRINCIPAL]
  Si pagos online habilitados:
  Botón verde (T1) / naranja (T2) / rojo (T3): "Pagar ahora — ${{remaining_balance_display}}"
  URL: {{payment_link_url}}

  Si NO habilitados:
  Botón: "Contactar {{clinic_name}}"
  URL: {{clinic_contact_url}}

[OPCIONES — Si no hay pago online]
  "Para pagar, contacta a {{clinic_name}}:"
  - Tel: {{clinic_phone}}
  - Email: {{clinic_contact_email}}
  - "También puedes ir directamente a nuestra clínica en {{clinic_address}}"

[DISCLAIMER — Solo en Template 3]
  "Nota: Si no recibimos respuesta, nos veremos en la necesidad de escalar el proceso
  de cobro según nuestras políticas. Queremos resolver esto contigo de forma amistosa."

[FOOTER]
  - Logo DentalOS
  - Unsubscribe: Gestionar recordatorios de pago → {{notification_preferences_url}}
  - Política de privacidad
```

---

## WhatsApp Templates

### Template WA-1 (7 días)

```
dentalos_payment_overdue_1_v1:
Hola {{1}}, tienes un saldo pendiente de ${{2}} en {{3}} (factura #{{4}}, vencida hace {{5}} días).
{{6}}¿Podemos ayudarte a regularizarlo?
```

### Template WA-2 (15 días)

```
dentalos_payment_overdue_2_v1:
📋 Segundo aviso — {{1}}: tu factura #{{2}} por ${{3}} lleva {{4}} días vencida. Para evitar inconvenientes, por favor regulariza tu pago: {{5}}
```

### Template WA-3 (30 días)

```
dentalos_payment_overdue_3_v1:
⚠ Último aviso — {{1}}: factura #{{2}} por ${{3}} con {{4}} días de mora. Contáctanos para acordar un plan de pago: {{5}} o llama al {{6}}.
```

---

## In-App Notification (para el Paciente — Portal)

```json
{
  "type": "billing",
  "title": "Recordatorio de pago",
  "body": "Tienes un saldo pendiente de ${{remaining_balance_display}} en la factura #{{invoice_number}} ({{days_overdue}} días vencida).",
  "action_url": "/facturas/{{invoice_id}}",
  "metadata": {
    "invoice_id": "{{invoice_id}}",
    "reminder_sequence": "{{reminder_sequence}}"
  }
}
```

---

## In-App Notification (para Staff — Solo en 3er recordatorio)

```json
{
  "type": "billing",
  "title": "Alerta: Deuda de 30 días",
  "body": "{{patient_full_name}} tiene ${{remaining_balance_display}} en mora (30 días). Factura #{{invoice_number}}.",
  "action_url": "/billing/invoices/{{invoice_id}}",
  "metadata": {
    "invoice_id": "{{invoice_id}}",
    "urgency": "high"
  }
}
```

**Color:** Naranja (`#EA580C`) en 1er y 2do; Rojo (`#DC2626`) en 3er.

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{patient_full_name}}` | string | Nombre completo | "Ana Gómez" |
| `{{invoice_number}}` | string | `invoices.invoice_number` | "F-2026-0042" |
| `{{invoice_total_display}}` | string | Total factura formateado | "$700.000" |
| `{{total_paid_display}}` | string | Total pagado | "$0" o "$350.000" |
| `{{remaining_balance_display}}` | string | Saldo pendiente | "$700.000" |
| `{{due_date}}` | string | `invoices.due_date` formateado | "15 de febrero de 2026" |
| `{{days_overdue}}` | integer | `TODAY - invoices.due_date` | 7, 15, o 30 |
| `{{reminder_sequence}}` | integer | 1, 2, o 3 | 1 |
| `{{payment_link_url}}` | string / null | Link de pago si habilitado | URL |
| `{{clinic_name}}` | string | Tenant name | "Clínica Smile" |
| `{{clinic_phone}}` | string | Tenant settings | "601-555-0100" |
| `{{clinic_address}}` | string | Tenant settings | "Calle 72 #15-30, Bogotá" |
| `{{clinic_contact_email}}` | string | Tenant settings | "admin@smile.com" |
| `{{clinic_contact_url}}` | string | Portal contact page | URL |
| `{{invoice_id}}` | uuid | `invoices.id` | UUID |
| `{{notification_preferences_url}}` | string | Portal preferencias | URL |

---

## Sending Rules

### Timing
- **Cron:** Diario a las 9 AM en el timezone de CADA TENANT (no en UTC global).
- **Implementación timezone:** El cron global corre en UTC; para cada tenant, calcula si son las 9 AM en su timezone antes de incluir sus facturas en el batch.

### Deduplication
- **Flag en DB:** `invoices.overdue_reminder_count` — incrementado después de cada envío.
- **Idempotency key:** `payment_overdue:{invoice_id}:reminder_{sequence}` con TTL 48 horas.
- **Máximo 3 recordatorios** por factura en total. Una vez `overdue_reminder_count >= 3`, no se envían más.

### Condición de Parada
Los recordatorios automáticos cesan si:
1. La factura es pagada en su totalidad (`status = 'paid'`)
2. Se alcanza el máximo de 3 recordatorios
3. El clinic_owner o staff marca la factura como `dispute` o `written_off`
4. El paciente paga un monto parcial (se reinicia el ciclo de días desde el nuevo saldo, NO desde la fecha de vencimiento original)

### Opt-out
- El paciente puede desactivar recordatorios de pago desde sus preferencias.
- Sin embargo, es un campo diferente a otros tipos de notificación: `billing_reminders.email` y `billing_reminders.whatsapp`.
- Las clínicas pueden configurar si permiten que los pacientes desactiven estos recordatorios (en la mayoría de los casos, deben mantenerse activos).

---

## Testing

### Test Cases

#### Happy Path
1. Tres secuencias de recordatorio para factura no pagada
   - **Given:** Factura vencida; cron ejecuta en días 7, 15, y 30 post-vencimiento
   - **When:** Cron job ejecutado cada día
   - **Then:** Template 1 enviado el día 7 (amistoso); Template 2 el día 15 (directo); Template 3 el día 30 (firme); `overdue_reminder_count` incrementado

2. Factura pagada antes del segundo recordatorio
   - **Given:** Primer recordatorio enviado; paciente paga en día 10
   - **When:** Cron del día 15 ejecuta
   - **Then:** Factura con `status = 'paid'`; segundo recordatorio NO enviado; `overdue_reminder_count = 1`

3. Tercer recordatorio activa in-app para staff
   - **Given:** Factura con 30 días de mora
   - **When:** Cron envía tercer recordatorio
   - **Then:** In-app al paciente Y in-app al staff (clinic_owner + receptionist) con alerta de cobro

#### Edge Cases
1. Pago parcial entre recordatorios
   - **Given:** Factura de $700k; primer recordatorio enviado; paciente paga $350k (parcial)
   - **When:** Cron del día 15 ejecuta
   - **Then:** Segundo recordatorio enviado con saldo actualizado de $350k (NO los $700k originales)

2. Factura en disputa (no enviar más recordatorios)
   - **Given:** Staff marca la factura como `dispute`
   - **When:** Cron del día 15 ejecuta
   - **Then:** Recordatorio NOT enviado; status `dispute` excluye la factura de la query

3. Tenant en timezone Colombia (UTC-5) — cron a las 9 AM local
   - **Given:** Tenant en Bogotá (UTC-5); cron UTC corre a las 14:00 UTC
   - **When:** Cron ejecuta
   - **Then:** Para tenants con timezone `America/Bogota`, el envío ocurre aproximadamente a las 9 AM hora local

#### Error Cases
1. overdue_reminder_count ya en 3 (max superado)
   - **Given:** Factura ya recibió 3 recordatorios; sigue vencida en día 45
   - **When:** Cron ejecuta
   - **Then:** Factura excluida de la query (`overdue_reminder_count >= 3`); NO se envía 4to recordatorio

### Test Data Requirements

- Facturas vencidas en día 7, 15, 30 exactos
- Factura con pago parcial intermedio
- Factura en estado `dispute`
- Tenant con timezone Colombia

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Cron diario a las 9 AM timezone del tenant detecta facturas en días 7/15/30
- [ ] Template 1 (7d): tono amistoso; Template 2 (15d): directo; Template 3 (30d): firme
- [ ] Subject varía según secuencia de recordatorio
- [ ] Botón de pago online visible si habilitado; info de pago en clínica si no
- [ ] `overdue_reminder_count` incrementado después de cada envío
- [ ] Máximo 3 recordatorios — sin 4to recordatorio
- [ ] Factura pagada: recordatorios cesados
- [ ] In-app al staff en el 3er recordatorio con color rojo
- [ ] Opt-out respetado
- [ ] Todos los test cases pasan

---

## Out of Scope

- El proceso de cobro manual (gestión de cartera — fuera del scope de DentalOS v1)
- Integración con agencias de cobro
- Intereses por mora
- Acuerdos de pago (planes de pago — future feature)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
