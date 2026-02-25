# E-08 — Notificación de Cancelación de Cita

---

## Overview

**Feature:** Notificación enviada al paciente cuando su cita es cancelada por el personal de la clínica (doctor, asistente o recepcionista). Informa la razón de la cancelación (si se proporcionó), muestra los detalles de la cita cancelada y ofrece un link para reagendar. También notifica in-app al doctor si la cancelación fue iniciada por otro miembro del equipo.

**Domain:** appointments / notifications

**Priority:** High

**Dependencies:** AP-04 (appointment-cancel), E-05 (appointment-confirmation), N-04, N-05

---

## Trigger

**Evento:** `appointment_cancelled`

**Cuándo se dispara:** Al completar `PATCH /api/v1/appointments/{id}/cancel` con éxito, cuando el `cancelled_by` es un usuario de la clínica (no el paciente mismo). Si el paciente cancela desde el portal, se usa el mismo evento pero con `cancelled_by_role = 'patient'` — el template puede variar ligeramente.

**RabbitMQ routing key:** `notification.appointment.cancelled`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente de la cita | patient | Siempre — canal principal |
| Doctor asignado | doctor | In-app únicamente; solo si la cancelación fue hecha por otro miembro del equipo |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Si paciente tiene email |
| whatsapp | Yes | Si paciente tiene teléfono y tenant habilitado |
| sms | No | Cancelaciones se manejan por email/WhatsApp — SMS muy corto para el contexto |
| in-app | Yes | Para el doctor (si canceló otro miembro del equipo) |

---

## Email Template

### Subject Line

Sin razón de cancelación:
```
Tu cita del {{appointment_date_short}} fue cancelada — {{clinic_name}}
```

Con razón de cancelación:
```
Cita cancelada: {{cancellation_reason_short}} — {{clinic_name}}
```

**Ejemplo sin razón:** "Tu cita del lunes 2 de marzo fue cancelada — Clínica Smile"
**Ejemplo con razón:** "Cita cancelada: El doctor no estará disponible — Clínica Smile"

### Preheader

```
Lo sentimos, tu cita con {{doctor_display_name}} fue cancelada. Puedes reagendar cuando quieras.
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica
  - Color primario de la clínica

[HERO — Fondo gris claro, ícono de X en círculo gris]
  - Ícono: ✖ (X roja o gris)
  - Título H1: "Tu cita fue cancelada"
  - Subtítulo: "Hola {{patient_first_name}}, lamentamos informarte que tu cita fue cancelada."

[CARD DE CITA CANCELADA — Estilo ticket tachado, borde rojo claro]
  Encabezado: "Cita cancelada"
  Información (texto en gris / tachado visualmente):
  - ~~📅 Fecha: {{appointment_date_full}}~~
  - ~~⏰ Hora: {{appointment_time}}~~
  - 👨‍⚕️ Doctor(a): {{doctor_display_name}}
  - 🦷 Servicio: {{appointment_type_display}}

[RAZÓN DE CANCELACIÓN — Solo si cancellation_reason != null]
  Card con fondo amarillo claro, ícono de información:
  Título: "Motivo de cancelación:"
  Texto: "{{cancellation_reason}}"

  Si no hay razón:
  Texto: "No se especificó un motivo para esta cancelación."

[CTA PRINCIPAL — Reagendar]
  Párrafo: "¿Te gustaría reagendar tu cita?"
  Botón verde: "Reagendar cita"
  URL: {{reschedule_url}}

[ALTERNATIVA — Contactar directamente]
  Texto: "También puedes contactarnos directamente para elegir un nuevo horario:"
  - 📞 {{clinic_phone}}
  - 📧 {{clinic_contact_email}}

[DISCULPA DE LA CLÍNICA]
  "Pedimos disculpas por los inconvenientes causados. En {{clinic_name}} valoramos
  tu tiempo y haremos lo posible para atenderte pronto."

[FOOTER]
  - Logo DentalOS
  - Unsubscribe: "Gestionar preferencias" → {{notification_preferences_url}}
  - Política de privacidad
```

### CTA Button

```
Texto: "Reagendar cita"
URL: {{reschedule_url}}
Color: #16A34A (verde — acción positiva de recuperación)
Texto: blanco, bold
```

### Plain-text Fallback

```
Tu cita fue cancelada — {{clinic_name}}

Hola {{patient_first_name}},

Tu cita fue cancelada:
Fecha original: {{appointment_date_full}}
Hora: {{appointment_time}}
Doctor(a): {{doctor_display_name}}
Servicio: {{appointment_type_display}}

{{#if cancellation_reason}}Motivo: {{cancellation_reason}}{{/if}}

Para reagendar: {{reschedule_url}}
Contáctanos: {{clinic_phone}} | {{clinic_contact_email}}

Pedimos disculpas por los inconvenientes.

© {{clinic_name}} | Gestionado por DentalOS
```

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_appointment_cancelled_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text (sin razón)

```
Hola {{1}}, lamentamos informarte que tu cita con {{2}} del {{3}} a las {{4}} en {{5}} fue cancelada.

Para reagendar, visita: {{6}}

O llámanos al {{7}}.
```

### Variables

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | `patient_first_name` | "Ana" |
| {{2}} | `doctor_display_name` | "Dra. Patricia Mora" |
| {{3}} | `appointment_date_short` | "lunes 2 de marzo" |
| {{4}} | `appointment_time` | "10:30 AM" |
| {{5}} | `clinic_name` | "Clínica Smile" |
| {{6}} | `reschedule_url` | "dtos.io/r/abc12" |
| {{7}} | `clinic_phone` | "601-555-0100" |

### WhatsApp Buttons

```
Tipo: Quick Reply
Botón 1: "Reagendar cita" (URL: {{reschedule_url}})
```

---

## In-App Notification (para el Doctor)

```json
{
  "type": "appointment",
  "title": "Cita cancelada",
  "body": "La cita de {{patient_full_name}} del {{appointment_date_short}} a las {{appointment_time}} fue cancelada por {{cancelled_by_name}}",
  "action_url": "/appointments/{{appointment_id}}",
  "metadata": {
    "appointment_id": "{{appointment_id}}",
    "cancelled_by": "{{cancelled_by_id}}"
  }
}
```

**Color del ícono:** Naranja/rojo (`#DC2626`) — cancelación de cita.

**Condición de envío in-app al doctor:** Solo si `cancelled_by_id != doctor_id` (es decir, alguien más canceló su cita).

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{patient_full_name}}` | string | `tenant.patients.first_name + last_name` | "Ana Gómez" |
| `{{doctor_display_name}}` | string | `tenant.users.display_name` | "Dra. Patricia Mora" |
| `{{appointment_date_full}}` | string | `appointments.start_at` formateado | "Lunes, 2 de marzo de 2026" |
| `{{appointment_date_short}}` | string | Formato corto | "lunes 2 de marzo" |
| `{{appointment_time}}` | string | Formateado en timezone del tenant | "10:30 AM" |
| `{{appointment_type_display}}` | string | Tipo convertido | "Consulta general" |
| `{{cancellation_reason}}` | string / null | `appointments.cancellation_reason` | "El doctor no estará disponible ese día" |
| `{{cancellation_reason_short}}` | string / null | Primeros 50 chars de cancellation_reason | Para el subject line |
| `{{cancelled_by_name}}` | string | Nombre del usuario que canceló | "Recepcionista: Laura Torres" |
| `{{cancelled_by_id}}` | uuid | `appointments.cancelled_by` | UUID |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{clinic_phone}}` | string | `public.tenants.settings.phone` | "601-555-0100" |
| `{{clinic_contact_email}}` | string | `public.tenants.settings.contact_email` | "citas@smile.com" |
| `{{clinic_logo_url}}` | string | `public.tenants.settings.logo_url` | CDN URL |
| `{{clinic_primary_color}}` | string | `public.tenants.settings.primary_color` | "#1D4ED8" |
| `{{reschedule_url}}` | string | `{portal_url}/citas/nueva?doctor={doctor_id}&from_cancelled={appointment_id}` | URL |
| `{{notification_preferences_url}}` | string | Portal preferences URL | URL |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al recibir el evento de cancelación.
- **Prioridad:** High (priority: 7) — el paciente debe saber lo antes posible.
- **Latencia máxima:** 2 minutos.

### Deduplication
- **Idempotency key:** `appointment_cancelled:{appointment_id}`
- **Ventana:** 24 horas.
- Una cita solo puede cancelarse una vez — la deduplicación es por si RabbitMQ re-entrega el mensaje.

### Cancelación por el Paciente
- Si la cancelación es iniciada por el paciente (desde el portal), no se envía esta notificación al paciente (él ya sabe que canceló).
- En su lugar, se envía una notificación in-app al doctor y recepcionista informando que el paciente canceló.
- Esta lógica se determina por `cancelled_by_role` en el payload del evento.

### Opt-out
- Respeta `appointment_cancelled.email` y `appointment_cancelled.whatsapp` en preferencias del paciente.
- Cancelaciones son consideradas transaccionales de servicio — se recomienda tenerlos habilitados, pero el paciente puede desactivarlos.

---

## Testing

### Test Cases

#### Happy Path
1. Cancelación por recepcionista con razón
   - **Given:** Cita en estado `confirmed`; recepcionista cancela con razón "El doctor estará de vacaciones"
   - **When:** `PATCH /appointments/{id}/cancel` con razón
   - **Then:** Email al paciente con razón visible; WhatsApp enviado; in-app al doctor (no fue él quien canceló); todos en < 2min

2. Cancelación por doctor (no in-app para el mismo doctor)
   - **Given:** Doctor cancela su propia cita
   - **When:** `PATCH /appointments/{id}/cancel`
   - **Then:** Email y WhatsApp al paciente enviados; in-app al doctor NO enviado (él mismo canceló)

3. Cancelación sin razón
   - **Given:** Cita cancelada sin especificar motivo
   - **When:** Evento procesado
   - **Then:** Email muestra "No se especificó un motivo"; subject usa template sin razón

#### Edge Cases
1. Cancelación por paciente desde el portal
   - **Given:** `cancelled_by_role = 'patient'` en el evento
   - **When:** Evento procesado
   - **Then:** Email al paciente NO enviado; WhatsApp al paciente NO enviado; in-app a doctor y recepcionista enviado informando la cancelación del paciente

2. Cita que ya tenía recordatorios enviados
   - **Given:** Cita con `reminder_24h_sent = true` y/o `reminder_2h_sent = true`
   - **When:** Cancelada
   - **Then:** Notificación de cancelación enviada normalmente; los flags de reminder no afectan este flujo

3. Paciente sin email
   - **Given:** Paciente sin email registrado
   - **When:** Evento procesado
   - **Then:** Email skipped; WhatsApp enviado si tiene teléfono; log correcto

4. Razón de cancelación con caracteres especiales
   - **Given:** Razón contiene `< > & "` u otros caracteres HTML
   - **When:** Template renderizado
   - **Then:** Caracteres escapados correctamente en HTML; sin XSS

#### Error Cases
1. appointment_id no existe en tenant (mensaje huérfano)
   - **Given:** Evento con appointment_id que fue eliminado de la DB
   - **When:** Worker intenta cargar los datos de la cita
   - **Then:** Fallo permanente; DLQ entry; Sentry alert (no hay suficiente info para renderizar)

### Test Data Requirements

- Cita confirmada con paciente con email y teléfono
- Cita confirmada con paciente solo con email
- Cancelación por recepcionista, por doctor, por paciente
- Razones de cancelación: con texto, nula, con caracteres especiales

### Mocking Strategy

- SendGrid, WhatsApp, RabbitMQ: mocks estándar
- Portal URL: configurado como variable de entorno en tests

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 2min con detalles de la cita cancelada
- [ ] Razón de cancelación incluida en email si fue proporcionada
- [ ] Subject varía según si hay razón de cancelación o no
- [ ] Botón "Reagendar cita" con URL correcta
- [ ] WhatsApp enviado con template aprobado y botón de reagendar
- [ ] In-app para el doctor solo si otro miembro del equipo canceló
- [ ] Cancelación por paciente: no enviar al paciente, sí notificar al staff
- [ ] Caracteres especiales en razón de cancelación correctamente escapados
- [ ] Idempotencia: re-entrega del evento no duplica envíos
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- Notificación de reagendamiento (se trata como nueva confirmación — E-05)
- La lógica de cancelación en sí (spec AP-04)
- Política de cancelación con tiempo mínimo
- Penalidades por cancelación tardía

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
