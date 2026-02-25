# E-06 — Recordatorio de Cita (24 Horas)

---

## Overview

**Feature:** Recordatorio enviado al paciente 24 horas antes de su cita. Canal multi (email + WhatsApp + SMS). Busca reducir el no-show (ausentismo) confirmando la asistencia y facilitando la cancelación con tiempo suficiente para reasignar el espacio. Incluye link de confirmación y cancelación.

**Domain:** emails / appointments / notifications

**Priority:** High

**Dependencies:** AP-01 (appointment-create), AP-07 (appointment-reminder-cron), N-04 (notification-preferences), N-05 (dispatch-engine), E-07 (2h reminder)

---

## Trigger

**Evento:** `appointment_reminder_24h`

**Cuándo se dispara:** Cron job que se ejecuta cada 15 minutos y busca citas con `start_at BETWEEN NOW() + 23.75h AND NOW() + 24.25h` en estado `confirmed` o `pending`. Publica un evento por cada cita encontrada.

**RabbitMQ routing key:** `notification.appointment.reminder_24h`

**Cron schedule:** `*/15 * * * *` (cada 15 minutos)

**Query de selección:**
```sql
SELECT a.*, p.email, p.phone, p.first_name, u.display_name as doctor_name
FROM appointments a
JOIN patients p ON a.patient_id = p.id
JOIN users u ON a.doctor_id = u.id
WHERE a.start_at BETWEEN (NOW() + INTERVAL '23 hours 45 minutes')
                     AND (NOW() + INTERVAL '24 hours 15 minutes')
  AND a.status IN ('confirmed', 'pending')
  AND a.reminder_24h_sent = false
  AND a.deleted_at IS NULL
```

**Post-procesamiento:** Una vez publicado el evento, marcar `reminder_24h_sent = true` en la cita para evitar re-envíos.

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente de la cita | patient | Siempre — canal principal |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Si paciente tiene email y preferencia habilitada |
| whatsapp | Yes | Si paciente tiene teléfono y tenant tiene WhatsApp; incluye botón de confirmación |
| sms | Yes | Si paciente tiene teléfono; fallback cuando WhatsApp no disponible o como canal adicional según preferencias |
| in-app | No | Recordatorios 24h no son notificaciones in-app — el paciente usa el portal, no la app de clínica |

---

## Email Template

### Subject Line

```
Recordatorio: Tu cita mañana a las {{appointment_time}} — {{clinic_name}}
```

**Ejemplo:** "Recordatorio: Tu cita mañana a las 10:30 AM — Clínica Smile"

### Preheader

```
Mañana tienes cita con {{doctor_display_name}}. ¿Confirmas tu asistencia?
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica
  - Color primario de la clínica

[HERO — Fondo azul claro, ícono de campana de recordatorio]
  - Ícono: 🔔
  - Título H1: "Recordatorio de cita"
  - Subtítulo: "Hola {{patient_first_name}}, tienes una cita mañana."

[CARD DE CITA — Estilo ticket]
  - 📅 Mañana: {{appointment_date_full}}
  - ⏰ Hora: {{appointment_time}} ({{duration_minutes}} min aprox)
  - 👨‍⚕️ Doctor(a): {{doctor_display_name}}
  - 🦷 Servicio: {{appointment_type_display}}
  - 📍 {{clinic_address}}

[CONFIRMACIÓN DE ASISTENCIA — Card con borde azul]
  Título: "¿Confirmas tu asistencia?"
  Subtítulo: "Ayúdanos a organizar mejor el tiempo de tu doctor(a)."

  Dos botones lado a lado:
  Botón Verde: "✓ Sí, asistiré"
    URL: {{confirm_attendance_url}}
  Botón Rojo outline: "✗ No puedo ir"
    URL: {{cancel_appointment_url}}

[CTA SECUNDARIO]
  Link: "Ver detalles completos →"
  URL: {{patient_portal_appointment_url}}

  Link: "Reagendar esta cita →"
  URL: {{reschedule_appointment_url}}

[PREPARACIÓN RECORDATORIO]
  Título: "Recuerda para mañana:"
  Bullets dinámicos según tipo de cita (mismo lógica que E-05)

[INFORMACIÓN DE CONTACTO]
  "¿Necesitas cambiar tu cita? Contáctanos:"
  - Tel: {{clinic_phone}}
  - Email: {{clinic_contact_email}}
  Nota: "Por favor avísanos con al menos 2 horas de anticipación."

[FOOTER]
  - Logo DentalOS
  - Unsubscribe: "Gestionar recordatorios" → {{notification_preferences_url}}
  - Política de privacidad
```

### Plain-text Fallback

```
Recordatorio de cita — {{clinic_name}}

Hola {{patient_first_name}},

Tienes una cita mañana:

Fecha: {{appointment_date_full}}
Hora: {{appointment_time}}
Doctor(a): {{doctor_display_name}}
Servicio: {{appointment_type_display}}
Dirección: {{clinic_address}}
Teléfono: {{clinic_phone}}

Confirmar asistencia: {{confirm_attendance_url}}
Cancelar cita: {{cancel_appointment_url}}
Reagendar: {{reschedule_appointment_url}}

Por favor avísanos con al menos 2 horas de anticipación si no puedes asistir.

© {{clinic_name}} | Gestionado por DentalOS
Para gestionar recordatorios: {{notification_preferences_url}}
```

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_appointment_reminder_24h_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text

```
Recuerda: mañana {{1}} tienes cita con {{2}} a las {{3}} en {{4}}.

¿Confirmas tu asistencia? Responde:
✅ SÍ para confirmar
❌ NO para cancelar

O visita: {{5}}
```

### Variables

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | `appointment_date_short` | "lunes 2 de marzo" |
| {{2}} | `doctor_display_name` | "Dra. Patricia Mora" |
| {{3}} | `appointment_time` | "10:30 AM" |
| {{4}} | `clinic_name` | "Clínica Smile" |
| {{5}} | `patient_portal_appointment_url` | "https://portal.dentalos.io/citas/abc123" |

### WhatsApp Buttons (Interactive)

```
Tipo: Quick Reply
Botón 1: "✅ Confirmar"  (reply: "CONFIRMAR:{appointment_id}")
Botón 2: "❌ Cancelar"   (reply: "CANCELAR:{appointment_id}")
```

**Manejo de respuestas de WhatsApp:** Un webhook de WhatsApp Business procesa las respuestas "CONFIRMAR:" y "CANCELAR:" para actualizar el estado de la cita automáticamente. Esto es procesado por el servicio de appointments, no por este template.

---

## SMS Template

### Texto del SMS

```
DentalOS: Cita mañana {{appointment_time}} con Dr. {{doctor_last_name}} en {{clinic_name}}. Confirma: {{sms_short_url}} o cancela: {{sms_cancel_url}}
```

### Variables SMS

| Variable | Ejemplo | Notas |
|----------|---------|-------|
| `{{appointment_time}}` | "10:30 AM" | Formato 12h |
| `{{doctor_last_name}}` | "Mora" | Solo apellido para ahorrar caracteres |
| `{{clinic_name}}` | "Dental Smile" | Truncar a 15 chars si necesario |
| `{{sms_short_url}}` | "dtos.io/c/abc12" | URL acortada para SMS; máximo 20 chars |
| `{{sms_cancel_url}}` | "dtos.io/x/abc12" | URL acortada para cancelación |

### Longitud del SMS

Template completo: ~155 caracteres. Dentro del límite de 160 para SMS simple.

### URL Shortener

- Servicio interno de short links: `dtos.io` (configurado en tenant settings o dominio DentalOS)
- Short codes de 5 caracteres alfanuméricos: `dtos.io/c/{5chars}` para confirmar, `dtos.io/x/{5chars}` para cancelar
- TTL del short link: 25 horas (expira después de la cita)

---

## Placeholders / Variables (Completo)

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{doctor_display_name}}` | string | `tenant.users.display_name` | "Dra. Patricia Mora" |
| `{{doctor_last_name}}` | string | `tenant.users.last_name` | "Mora" |
| `{{appointment_date_full}}` | string | `appointments.start_at` en timezone del tenant | "Lunes, 2 de marzo de 2026" |
| `{{appointment_date_short}}` | string | Formato corto | "lunes 2 de marzo" |
| `{{appointment_time}}` | string | Formateado en timezone del tenant | "10:30 AM" |
| `{{duration_minutes}}` | integer | `appointments.duration_minutes` | 45 |
| `{{appointment_type_display}}` | string | Tipo convertido a display | "Consulta general" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{clinic_address}}` | string | `public.tenants.settings.address` | "Calle 72 # 15-30, Bogotá" |
| `{{clinic_phone}}` | string | `public.tenants.settings.phone` | "601-555-0100" |
| `{{clinic_logo_url}}` | string | `public.tenants.settings.logo_url` | CDN URL |
| `{{clinic_primary_color}}` | string | `public.tenants.settings.primary_color` | "#1D4ED8" |
| `{{clinic_contact_email}}` | string | `public.tenants.settings.contact_email` | "citas@smile.com" |
| `{{confirm_attendance_url}}` | string | `{portal_url}/citas/{id}/confirmar?token={token}` | URL |
| `{{cancel_appointment_url}}` | string | `{portal_url}/citas/{id}/cancelar?token={token}` | URL |
| `{{reschedule_appointment_url}}` | string | `{portal_url}/citas/{id}/reagendar?token={token}` | URL |
| `{{patient_portal_appointment_url}}` | string | `{portal_url}/citas/{id}` | URL |
| `{{sms_short_url}}` | string | Short link generado | "dtos.io/c/abc12" |
| `{{sms_cancel_url}}` | string | Short link generado | "dtos.io/x/abc12" |
| `{{notification_preferences_url}}` | string | `{portal_url}/preferencias/notificaciones` | URL |

---

## Sending Rules

### Timing
- **Cron:** Cada 15 minutos, buscando citas en la ventana `[23h45min, 24h15min]` desde ahora.
- **Timezone:** El `start_at` de la cita se almacena en UTC; el cálculo de la ventana es en UTC. Las citas se encuentran por `start_at`, no por hora local de la clínica.
- **Prioridad de cola:** High (priority: 7).

### Deduplication
- **Flag en DB:** `appointments.reminder_24h_sent = true` — se marca inmediatamente al publicar el evento al cron. Esto previene doble envío si el cron se ejecuta dos veces seguidas.
- **Idempotency key en RabbitMQ:** `appointment_reminder_24h:{appointment_id}:{date_hour}` — TTL 2 horas en Redis. Previene doble procesamiento si el mensaje es re-entregado.

### Cancelaciones antes del recordatorio
- Si la cita es cancelada antes de que se procese el recordatorio, el estado `appointments.status = 'cancelled'` excluye la cita de la query del cron.
- Verificación adicional en el worker: antes de enviar, re-verificar que la cita sigue en estado válido. Si fue cancelada, no enviar y loggear como `skipped (appointment_cancelled)`.

### Opt-out
- Respeta `appointment_reminder.email`, `appointment_reminder.whatsapp`, `appointment_reminder.sms` en las preferencias del paciente.
- Si el paciente no tiene preferencias registradas, se usan los defaults (email=true, whatsapp=true, sms=false).

---

## Testing

### Test Cases

#### Happy Path
1. Recordatorio enviado 24h antes — todos los canales
   - **Given:** Cita confirmada en 24h; paciente con email, teléfono; tenant con WhatsApp; cron se ejecuta
   - **When:** Cron query encuentra la cita
   - **Then:** Email enviado; WhatsApp enviado con botones de confirmación/cancelación; SMS enviado; `reminder_24h_sent = true` en DB

2. Paciente confirma asistencia via WhatsApp
   - **Given:** Recordatorio WhatsApp enviado; paciente responde "CONFIRMAR"
   - **When:** Webhook de WhatsApp recibe la respuesta
   - **Then:** `appointments.status = 'confirmed_by_patient'`; notificación in-app al staff

3. Paciente cancela via SMS link
   - **Given:** Recordatorio SMS enviado; paciente hace clic en link de cancelación
   - **When:** Endpoint de cancelación procesado
   - **Then:** Cita cancelada; notificación E-08 disparada; doctor notificado

#### Edge Cases
1. Cita cancelada entre el cron y el procesamiento del mensaje
   - **Given:** Cita en cola de recordatorio; cancelada manualmente antes de que el worker procese
   - **When:** Worker intenta enviar
   - **Then:** Worker re-verifica estado; cita cancelada → skipped; log `skipped (appointment_cancelled)`

2. Doble ejecución del cron (concurrencia)
   - **Given:** `reminder_24h_sent = false`; dos workers procesan la misma cita simultáneamente (race condition)
   - **When:** Ambos intentan marcar y enviar
   - **Then:** Uso de `SELECT ... FOR UPDATE SKIP LOCKED` en la query del cron para serializar; solo un worker procesa

3. Paciente sin teléfono — solo email
   - **Given:** Paciente sin `phone` registrado
   - **When:** Recordatorio enviado
   - **Then:** Email enviado; WhatsApp y SMS skipped con log correcto

#### Error Cases
1. Fallo del cron job
   - **Given:** Worker de cron falla durante la query
   - **When:** Error de DB en la query de selección
   - **Then:** Cron loggea error; no marca `reminder_24h_sent`; siguiente ejecución en 15 min reintenta

### Test Data Requirements

- Citas creadas con `start_at = NOW() + 24h` en UTC
- Pacientes con y sin teléfono registrado
- Tenant con y sin WhatsApp habilitado
- Preferencias de notificación variadas por paciente

### Mocking Strategy

- Cron: APScheduler en modo de prueba, ejecución manual vía test
- SendGrid/Twilio/WhatsApp: mocks completos
- DB: Fixtures con citas en ventana de 24h

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Cron ejecuta cada 15 minutos y detecta citas en ventana de 24h
- [ ] Email enviado con detalles de cita y botones de confirmar/cancelar/reagendar
- [ ] WhatsApp enviado con template aprobado y quick reply buttons
- [ ] SMS enviado con URL acortada (< 160 chars)
- [ ] `reminder_24h_sent = true` en DB después del envío
- [ ] Idempotencia: cita ya procesada no genera doble envío
- [ ] Cita cancelada antes del recordatorio: skipped correctamente
- [ ] Preferencias del paciente respetadas
- [ ] Race condition prevenida con `SELECT FOR UPDATE SKIP LOCKED`
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- Recordatorio de 2h (spec E-07)
- Procesamiento de respuestas de WhatsApp (webhook de confirmación — spec AP-08)
- El endpoint del short link service
- Recordatorios para staff / doctores (in-app únicamente)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
