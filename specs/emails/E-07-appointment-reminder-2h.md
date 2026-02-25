# E-07 — Recordatorio de Cita (2 Horas)

---

## Overview

**Feature:** Recordatorio de última hora enviado al paciente 2 horas antes de su cita. Canal WhatsApp y SMS únicamente — no se envía email por ser una comunicación demasiado cercana a la cita (el email tiene baja tasa de apertura inmediata). El mensaje es corto, directo y busca que el paciente esté en camino. Complementa el recordatorio de 24h (E-06).

**Domain:** appointments / notifications

**Priority:** Medium

**Dependencies:** AP-01 (appointment-create), AP-07 (reminder-cron), E-06 (24h reminder), N-04, N-05

---

## Trigger

**Evento:** `appointment_reminder_2h`

**Cuándo se dispara:** Cron job que se ejecuta cada 5 minutos y busca citas con `start_at BETWEEN NOW() + 1h50min AND NOW() + 2h10min` en estado `confirmed` o `pending` con `reminder_2h_sent = false`.

**RabbitMQ routing key:** `notification.appointment.reminder_2h`

**Cron schedule:** `*/5 * * * *` (cada 5 minutos — mayor frecuencia por menor ventana de tiempo)

**Query de selección:**
```sql
SELECT a.*, p.phone, p.first_name, u.display_name as doctor_name, u.last_name as doctor_last_name
FROM appointments a
JOIN patients p ON a.patient_id = p.id
JOIN users u ON a.doctor_id = u.id
WHERE a.start_at BETWEEN (NOW() + INTERVAL '1 hour 50 minutes')
                     AND (NOW() + INTERVAL '2 hours 10 minutes')
  AND a.status IN ('confirmed', 'pending')
  AND a.reminder_2h_sent = false
  AND p.phone IS NOT NULL
  AND a.deleted_at IS NULL
```

**Nota:** La query solo selecciona citas de pacientes con teléfono registrado (`p.phone IS NOT NULL`), ya que este recordatorio es exclusivamente WhatsApp y SMS.

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente de la cita | patient | Solo si tiene teléfono registrado |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | No | Muy cercano a la cita — baja utilidad; no enviar |
| whatsapp | Yes | Canal principal para este recordatorio; si tenant habilitado |
| sms | Yes | Si tenant tiene Twilio configurado; enviar junto con o en lugar de WhatsApp |
| in-app | No | Paciente no usa la app interna de la clínica |

**Lógica de canal:** Si el tenant tiene WhatsApp habilitado, se envía WhatsApp. Si tiene SMS habilitado, se envía SMS también (son canales independientes). No es WhatsApp OR SMS, es WhatsApp AND/OR SMS según configuración del tenant y preferencias del paciente.

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_appointment_reminder_2h_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text

```
Tu cita en {{1}} es en 2 horas ({{2}}) con {{3}}. ¿Ya estás en camino? 🦷

{{4}}
```

### Variables

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | `clinic_name` | "Clínica Smile" |
| {{2}} | `appointment_time` | "10:30 AM" |
| {{3}} | `doctor_display_name` | "Dra. Patricia Mora" |
| {{4}} | `sms_short_url` | "dtos.io/c/abc12" (link portal) |

### Longitud aproximada del template

Con variables de ejemplo: ~110 caracteres. Dentro del límite de 1024.

### WhatsApp Buttons

```
Tipo: Quick Reply
Botón 1: "✅ Voy en camino" (reply: "EN_CAMINO:{appointment_id}")
Botón 2: "❌ No puedo ir"   (reply: "CANCELAR:{appointment_id}")
```

**Nota de UX:** Responder "EN_CAMINO" es informacional — no actualiza el estado de la cita pero puede usarse para un dashboard de confirmaciones. Responder "CANCELAR" sí dispara el flujo de cancelación.

---

## SMS Template

### Texto del SMS

```
DentalOS: Cita en 2h ({{appointment_time}}) con Dr. {{doctor_last_name}} en {{clinic_short_name}}. Info: {{sms_short_url}}
```

### Variables SMS

| Variable | Ejemplo | Notas |
|----------|---------|-------|
| `{{appointment_time}}` | "10:30 AM" | Formato 12h |
| `{{doctor_last_name}}` | "Mora" | Solo apellido |
| `{{clinic_short_name}}` | "Dental Smile" | Truncar a 12 chars si es necesario |
| `{{sms_short_url}}` | "dtos.io/v/abc12" | Link al portal de la cita; "v" = ver |

### Longitud del SMS

Template completo con variables: ~120 caracteres. Dentro del límite de 160.

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{patient_phone}}` | string | `tenant.patients.phone` en E.164 | "+573001234567" |
| `{{doctor_display_name}}` | string | `tenant.users.display_name` | "Dra. Patricia Mora" |
| `{{doctor_last_name}}` | string | `tenant.users.last_name` | "Mora" |
| `{{appointment_time}}` | string | `appointments.start_at` en timezone del tenant | "10:30 AM" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{clinic_short_name}}` | string | `public.tenants.name` truncado a 12 chars | "Dental Smile" |
| `{{sms_short_url}}` | string | Short link generado | "dtos.io/v/abc12" |
| `{{appointment_id}}` | uuid | `appointments.id` | Para los reply buttons de WA |

---

## Sending Rules

### Timing
- **Cron:** Cada 5 minutos, ventana `[1h50min, 2h10min]` desde ahora.
- **No enviar si** la cita fue cancelada (status check previo al envío).
- **Prioridad de cola:** High (priority: 8) — tiempo crítico.

### Deduplication
- **Flag en DB:** `appointments.reminder_2h_sent = true` — marcado inmediatamente al publicar evento.
- **Idempotency key:** `appointment_reminder_2h:{appointment_id}` con TTL 3 horas en Redis.
- **SELECT FOR UPDATE SKIP LOCKED** para prevenir race conditions en entornos con múltiples workers del cron.

### Condición de No-Envío
- Si `reminder_24h_sent = false` (el recordatorio de 24h no fue enviado), enviar el de 2h igualmente — no depende del recordatorio previo.
- Si el paciente no tiene teléfono: cita excluida de la query (query filtra `p.phone IS NOT NULL`).
- Si la cita fue cancelada: skipped.

### Relación con E-06 (24h)
- El recordatorio de 2h es INDEPENDIENTE del de 24h. Si el de 24h falló o no se envió, el de 2h se envía igual.
- No hay estado compartido entre ambos recordatorios más allá de la cita misma.

### Opt-out
- Respeta `appointment_reminder.whatsapp` y `appointment_reminder.sms` en preferencias del paciente.
- No hay preferencia específica para "2h" vs "24h" — ambos usan el mismo toggle `appointment_reminder`.

---

## Diferencias con E-06 (24h reminder)

| Aspecto | E-06 (24h) | E-07 (2h) |
|---------|-----------|-----------|
| Canales | Email + WhatsApp + SMS | Solo WhatsApp + SMS |
| Cron frecuencia | Cada 15 min | Cada 5 min |
| Longitud del mensaje | Detallado | Corto y directo |
| Preparación para cita | Sí (bullets) | No |
| Cancel link en email | Sí | No aplica (no email) |
| Tono | Informativo | Urgente / recordatorio |

---

## Testing

### Test Cases

#### Happy Path
1. Recordatorio 2h — WhatsApp y SMS enviados
   - **Given:** Cita en 2h; paciente con teléfono; tenant con WhatsApp y SMS habilitados; `reminder_2h_sent = false`
   - **When:** Cron ejecuta
   - **Then:** WhatsApp enviado con template y buttons; SMS enviado < 160 chars; `reminder_2h_sent = true`; delivery log registrado

2. Solo SMS (tenant sin WhatsApp)
   - **Given:** Tenant no tiene WhatsApp Business API configurado
   - **When:** Cron ejecuta
   - **Then:** Solo SMS enviado; WhatsApp skipped con log `skipped (channel_not_configured)`

3. Paciente responde "CANCELAR" en WhatsApp
   - **Given:** Recordatorio enviado con botón de cancelar
   - **When:** Paciente toca "❌ No puedo ir"
   - **Then:** Webhook procesa cancelación; cita cancelada; notificación a clínica; E-08 disparado

#### Edge Cases
1. Cita cancelada entre cron y envío
   - **Given:** Cita en cola; cancelada manualmente justo antes del procesamiento
   - **When:** Worker verifica estado antes de enviar
   - **Then:** Envío skipped; log `skipped (appointment_cancelled)`; `reminder_2h_sent` NO marcado (cita ya cancelada)

2. Recordatorio 24h y 2h simultáneos (edge case de citas nuevas)
   - **Given:** Cita creada exactamente 24h y 2h antes al mismo tiempo (improbable pero posible)
   - **When:** Ambos crons ejecutan
   - **Then:** Solo el de 2h aplica (no tiene sentido el de 24h si ya fue enviado o si el de 2h es más relevante); en la práctica el de 24h ya habría sido enviado antes

3. Paciente con preferencia `appointment_reminder.whatsapp = false`
   - **Given:** Paciente desactivó WhatsApp para recordatorios
   - **When:** Cron ejecuta
   - **Then:** WhatsApp skipped; SMS enviado si habilitado

4. Doctor con apellido muy largo (SMS truncado)
   - **Given:** Doctor con last_name de 30 caracteres
   - **When:** SMS renderizado
   - **Then:** `doctor_last_name` truncado a 20 chars para mantener SMS dentro de 160 chars

#### Error Cases
1. Twilio rate limit (1 SMS/seg por número)
   - **Given:** Múltiples citas en la misma ventana de tiempo (clínica grande)
   - **When:** Cron procesa 50 citas simultáneamente
   - **Then:** SMS queue con rate limiting interno; envíos distribuidos en tiempo; sin pérdida de mensajes

2. WhatsApp template rechazado
   - **Given:** Template no aprobado en Meta
   - **When:** WhatsApp envío intentado
   - **Then:** Fallo permanente para canal WhatsApp; SMS enviado independientemente; Sentry alert

### Test Data Requirements

- Citas con `start_at = NOW() + 2h` en UTC
- Pacientes con teléfono en formato E.164 válido
- Tenant con WhatsApp y SMS habilitados; tenant sin WhatsApp

### Mocking Strategy

- WhatsApp API: mock via respx
- Twilio: test credentials con mock
- Cron: ejecución manual en tests vía pytest fixture

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Cron ejecuta cada 5 minutos con query correcta (ventana 1h50m - 2h10m)
- [ ] WhatsApp enviado con template aprobado y botones de respuesta
- [ ] SMS enviado con texto < 160 caracteres
- [ ] `reminder_2h_sent = true` después del procesamiento
- [ ] Email NO enviado (este recordatorio es solo WhatsApp/SMS)
- [ ] Cita cancelada: envío skipped correctamente
- [ ] Sin paciente teléfono: excluido de la query
- [ ] Race condition prevenida con `SELECT FOR UPDATE SKIP LOCKED`
- [ ] Independiente del recordatorio de 24h
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- Recordatorio de 24h (spec E-06)
- Procesamiento de respuestas de WhatsApp "EN_CAMINO" / "CANCELAR" (webhook — spec AP-08)
- Recordatorio de 1h (puede agregarse en v2)
- Notificación de llegada del paciente (check-in — spec separado)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
