# E-05 — Confirmación de Cita

---

## Overview

**Feature:** Notificación multi-canal enviada al paciente cuando se crea o confirma una cita. Confirma los detalles de la cita (fecha, hora, doctor, tipo de procedimiento, dirección de la clínica) y proporciona links para cancelar o reagendar. Es el primer contacto de la clínica con el paciente vía comunicación digital.

**Domain:** emails / appointments / notifications

**Priority:** High

**Dependencies:** AP-01 (appointment-create), P-01 (patient-profile), N-04 (notification-preferences), N-05 (dispatch-engine), E-08 (appointment-cancelled)

---

## Trigger

**Evento:** `appointment_confirmed`

**Cuándo se dispara:**
1. Al crear una nueva cita (`POST /api/v1/appointments`)
2. Al confirmar una cita que estaba en estado `pending` (`PATCH /api/v1/appointments/{id}/confirm`)
3. Al reagendar una cita (se trata como nueva confirmación del nuevo horario)

**RabbitMQ routing key:** `notification.appointment.confirmed`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente de la cita | patient | Siempre — canal principal |
| Doctor asignado | doctor | In-app únicamente (no email, no WhatsApp) |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Para paciente — si tiene email registrado y no ha desactivado |
| whatsapp | Yes | Para paciente — si tiene teléfono registrado y canal activo en el tenant |
| sms | No | Solo para recordatorios (E-06), no para confirmación inicial |
| in-app | Yes | Para doctor asignado (notificación de nueva cita en su agenda) |

---

## Email Template

### Subject Line

```
Cita confirmada con {{doctor_display_name}} — {{appointment_date_short}}
```

**Ejemplo:** "Cita confirmada con Dra. Patricia Mora — Lunes 2 de marzo"

### Preheader

```
Tu cita en {{clinic_name}} está confirmada para el {{appointment_date}} a las {{appointment_time}}.
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica ({{clinic_logo_url}}) o DentalOS si no hay
  - Nombre de la clínica: {{clinic_name}}
  - Color de la clínica ({{clinic_primary_color}}) como línea de acento

[HERO — Fondo verde claro, ícono de checkmark]
  - Ícono: ✓ (checkmark verde grande)
  - Título H1: "¡Tu cita está confirmada!"
  - Subtítulo: "Hola {{patient_first_name}}, todo está listo para tu visita."

[CARD DE CITA — Diseño tipo ticket, border-left verde]
  Encabezado de la card: "Detalles de tu cita"

  Tabla de información:
  - 📅 Fecha: {{appointment_date_full}}
  - ⏰ Hora: {{appointment_time}} (duración aprox: {{duration_minutes}} min)
  - 👨‍⚕️ Doctor(a): {{doctor_display_name}}
  - 🦷 Tipo de consulta: {{appointment_type_display}}
  - 📍 Dirección: {{clinic_address}}
  - 🏥 Clínica: {{clinic_name}}

[MAPA / UBICACIÓN — si coordinates disponibles]
  Link: "Ver en Google Maps →"
  URL: https://maps.google.com/?q={{clinic_latitude}},{{clinic_longitude}}

[CTA PRIMARIO]
  Botón: "Ver mi cita"
  URL: {{patient_portal_appointment_url}}
  Color: #2563EB (azul)

[ACCIONES SECUNDARIAS — 2 botones de texto]
  Link texto: "Cancelar cita"
  URL: {{cancel_appointment_url}}

  Link texto: "Reagendar cita"
  URL: {{reschedule_appointment_url}}

[PREPARACIÓN PARA LA CITA]
  Título: "Antes de tu cita"
  Bullets dinámicos según appointment_type:

  Para consulta general:
  • Llega 10 minutos antes para el registro
  • Trae tu documento de identidad
  • Si tienes estudios o radiografías previas, tráelos

  Para cirugía oral / extracción:
  • No comas las 2 horas previas a la cita
  • Trae a alguien que te acompañe
  • Llega 15 minutos antes

  Para limpieza / profilaxis:
  • Cepilla tus dientes antes de llegar
  • Llega puntual para maximizar el tiempo de tu cita

[INFORMACIÓN DE CONTACTO DE LA CLÍNICA]
  - Teléfono: {{clinic_phone}}
  - Email: {{clinic_contact_email}}
  - Texto: "¿Tienes preguntas? Contáctanos directamente."

[FOOTER]
  - Logo DentalOS pequeño
  - "Servicio gestionado por DentalOS"
  - Unsubscribe: "Gestionar preferencias de notificaciones" → {{notification_preferences_url}}
  - Política de privacidad
```

### CTA Button

```
Texto: "Ver mi cita"
URL: {{patient_portal_appointment_url}}
Color: #2563EB
Texto: blanco, bold
```

### Plain-text Fallback

```
Tu cita está confirmada — {{clinic_name}}

Hola {{patient_first_name}},

Tu cita está confirmada:

Fecha: {{appointment_date_full}}
Hora: {{appointment_time}}
Doctor(a): {{doctor_display_name}}
Tipo: {{appointment_type_display}}
Dirección: {{clinic_address}}
Teléfono: {{clinic_phone}}

Ver tu cita: {{patient_portal_appointment_url}}
Cancelar: {{cancel_appointment_url}}
Reagendar: {{reschedule_appointment_url}}

© {{clinic_name}} | Gestionado por DentalOS
```

---

## WhatsApp Template

### Nombre del template Meta (HSM)

```
dentalos_appointment_confirmed_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text (aprobado por Meta)

```
Hola {{1}}, tu cita con {{2}} está confirmada para el {{3}} a las {{4}} en {{5}}.

Para ver los detalles o cancelar, visita: {{6}}

¿Tienes preguntas? Llámanos al {{7}}.
```

### Variables (en orden)

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | `patient_first_name` | "Ana" |
| {{2}} | `doctor_display_name` | "Dra. Patricia Mora" |
| {{3}} | `appointment_date_short` | "lunes 2 de marzo" |
| {{4}} | `appointment_time` | "10:30 AM" |
| {{5}} | `clinic_name` | "Clínica Smile" |
| {{6}} | `patient_portal_appointment_url` | "https://portal.dentalos.io/citas/abc123" |
| {{7}} | `clinic_phone` | "601-555-0100" |

### WhatsApp Buttons

```
Tipo: Quick Reply
Botón 1: "Ver cita" (URL: {{patient_portal_appointment_url}})
Botón 2: "Cancelar cita" (URL: {{cancel_appointment_url}})
```

### Límite de caracteres

El template completo con variables ejemplo: ~240 caracteres. Dentro del límite de 1024.

---

## In-App Notification (para el Doctor)

```json
{
  "type": "appointment",
  "title": "Nueva cita agendada",
  "body": "{{patient_full_name}} — {{appointment_type_display}} el {{appointment_date_short}} a las {{appointment_time}}",
  "action_url": "/appointments/{{appointment_id}}",
  "metadata": {
    "appointment_id": "{{appointment_id}}",
    "patient_id": "{{patient_id}}"
  }
}
```

**Color del ícono:** Azul (`#2563EB`) — tipo `appointment`

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{patient_full_name}}` | string | `tenant.patients.first_name + last_name` | "Ana Gómez" |
| `{{doctor_display_name}}` | string | `tenant.users.display_name` con prefijo Dr./Dra. | "Dra. Patricia Mora" |
| `{{appointment_date_full}}` | string | `appointments.start_at` en es-419 con día de semana | "Lunes, 2 de marzo de 2026" |
| `{{appointment_date_short}}` | string | Formato corto | "lunes 2 de marzo" |
| `{{appointment_time}}` | string | `appointments.start_at` en timezone del tenant | "10:30 AM" |
| `{{duration_minutes}}` | integer | `appointments.duration_minutes` | 45 |
| `{{appointment_type_display}}` | string | `appointments.type` convertido a display | "Consulta general" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{clinic_address}}` | string | `public.tenants.settings.address` | "Calle 72 # 15-30, Bogotá" |
| `{{clinic_phone}}` | string | `public.tenants.settings.phone` | "601-555-0100" |
| `{{clinic_logo_url}}` | string | `public.tenants.settings.logo_url` | CDN URL |
| `{{clinic_primary_color}}` | string | `public.tenants.settings.primary_color` | "#1D4ED8" |
| `{{clinic_latitude}}` | float | `public.tenants.settings.latitude` | 4.6765 |
| `{{clinic_longitude}}` | float | `public.tenants.settings.longitude` | -74.0477 |
| `{{clinic_contact_email}}` | string | `public.tenants.settings.contact_email` | "citas@smile.com" |
| `{{patient_portal_appointment_url}}` | string | `{portal_url}/citas/{appointment_id}` | URL |
| `{{cancel_appointment_url}}` | string | `{portal_url}/citas/{appointment_id}/cancelar?token={cancel_token}` | URL |
| `{{reschedule_appointment_url}}` | string | `{portal_url}/citas/{appointment_id}/reagendar?token={reschedule_token}` | URL |
| `{{notification_preferences_url}}` | string | `{portal_url}/preferencias/notificaciones` | URL |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al confirmarse la cita.
- **Prioridad:** High (priority: 7).
- **Latencia máxima email:** 2 minutos.
- **Latencia máxima WhatsApp:** 1 minuto.

### Deduplication
- **Idempotency key:** `appointment_confirmed:{appointment_id}`
- **Ventana:** 5 minutos — si la cita se confirma dos veces en 5 min (bug de frontend), solo un envío.

### Opt-out (Preferencias)
- Email: respeta las preferencias `appointment_confirmed.email` del paciente.
- WhatsApp: respeta `appointment_confirmed.whatsapp`. Además, el tenant debe tener WhatsApp habilitado.
- In-app para doctor: siempre enviado (in_app no se puede desactivar).

### Unsubscribe
- Incluye link "Gestionar preferencias de notificaciones" en el footer del email.
- NO es marketing — es transaccional de servicio. Sin SendGrid ASM unsubscribe group obligatorio, pero se incluye gestión de preferencias propia.

---

## Testing

### Test Cases

#### Happy Path
1. Cita creada — paciente con email y WhatsApp
   - **Given:** Cita creada para paciente con email y teléfono; tenant con WhatsApp habilitado
   - **When:** Evento `appointment_confirmed` publicado
   - **Then:** Email enviado al paciente; WhatsApp enviado al teléfono del paciente; In-app para el doctor; todos en < 2min

2. Cita creada — paciente solo con email
   - **Given:** Paciente sin teléfono registrado
   - **When:** Evento procesado
   - **Then:** Solo email enviado; WhatsApp skipped con log `skipped (no phone)`

3. Reagendamiento de cita
   - **Given:** Cita existente reagendada a nuevo horario
   - **When:** Nuevo evento `appointment_confirmed` para la misma cita
   - **Then:** Email con nuevos detalles enviado; idempotency key diferente (por fecha de reagendamiento)

#### Edge Cases
1. Doctor sin nombre configurado
   - **Given:** Usuario doctor sin `display_name` configurado
   - **When:** Template renderizado
   - **Then:** Usa `first_name + last_name` como fallback; no falla el envío

2. Clínica sin coordenadas (no aparece mapa)
   - **Given:** Tenant sin `latitude`/`longitude` en settings
   - **When:** Template renderizado
   - **Then:** Sección de mapa omitida; sin link broken

3. Paciente con preferencia appointment_confirmed.email = false
   - **Given:** Paciente desactivó emails de confirmación
   - **When:** Evento procesado
   - **Then:** Email skipped; WhatsApp enviado si habilitado; log `skipped (user_preference)`

#### Error Cases
1. WhatsApp template no aprobado por Meta
   - **Given:** Template `dentalos_appointment_confirmed_v1` no aprobado en Meta
   - **When:** WhatsApp envío intentado
   - **Then:** WhatsApp fallo permanente; email sigue enviándose; Sentry alert

### Test Data Requirements

- Paciente con email y teléfono válidos
- Paciente con solo email, sin teléfono
- Tenant con y sin WhatsApp habilitado
- Tenant con y sin logo/coordenadas configurados

### Mocking Strategy

- SendGrid: sandbox mode
- WhatsApp API: mock via respx interceptando graph.facebook.com
- RabbitMQ: Docker Compose broker para integración

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 2min con todos los detalles de la cita
- [ ] WhatsApp enviado cuando tenant tiene habilitado y paciente tiene teléfono
- [ ] In-app notification para el doctor con tipo `appointment` (azul)
- [ ] Cancel y reschedule links incluidos en email
- [ ] Preparación para la cita varía según el tipo de consulta
- [ ] Idempotencia: doble confirmación en < 5min no duplica envíos
- [ ] Preferencias del paciente respetadas (opt-out respetado)
- [ ] Logo de la clínica en el header
- [ ] Plain-text fallback válido
- [ ] WhatsApp template con 7 variables en formato Meta aprobado
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- Recordatorio de 24h (spec E-06)
- Recordatorio de 2h (spec E-07)
- Notificación de cancelación (spec E-08)
- El endpoint de gestión de citas (spec AP-01)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
