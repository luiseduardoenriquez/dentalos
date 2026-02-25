# E-18 — Notificación de Espacio Disponible en Lista de Espera

---

## Overview

**Feature:** Notificación de alta urgencia enviada al paciente en lista de espera cuando se libera un espacio de cita que coincide con sus criterios (doctor, tipo de servicio, horario preferido). Primer en llegar, primero en atenderse. El link de reserva expira en 2 horas para presionar acción inmediata. Canales: WhatsApp + SMS + in-app (NO email — demasiado lento para este contexto time-sensitive).

**Domain:** appointments / notifications

**Priority:** High

**Dependencies:** AP-01 (appointment-create), AP-04 (appointment-cancel), AP-10 (waitlist-join), AP-11 (waitlist-match), N-04, N-05

---

## Trigger

**Evento:** `waitlist_slot_available`

**Cuándo se dispara:** Cuando se cancela una cita (`PATCH /appointments/{id}/cancel`) y el servicio de waitlist detecta que hay pacientes en lista de espera que coinciden con los criterios del espacio liberado.

**Flujo de disparo:**
```python
# En el servicio de appointments, post-cancelación:
1. Cita cancelada exitosamente
2. Servicio de waitlist consulta: ¿Hay pacientes en espera para este doctor/tipo/horario?
3. Si hay matches: publicar evento `waitlist_slot_available` para cada paciente en la lista
   (ordenado por prioridad: fecha de ingreso a la lista)
4. El slot se marca como "notificación enviada" para evitar sobrenotificación
5. Primer paciente que reserva "gana" el espacio
```

**RabbitMQ routing key:** `notification.appointment.waitlist_slot_available`

**Prioridad de mensaje:** Priority 9 (máxima) — tiempo es crítico.

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente(s) en lista de espera | patient | Uno o varios pacientes que coincidan con los criterios del espacio |

**Nota sobre múltiples destinatarios:** Si hay 3 pacientes en lista de espera para ese slot, los 3 reciben la notificación simultáneamente. El primero que reserve gana. Los demás, cuando intenten reservar, recibirán "Lo sentimos, alguien más reservó primero." La lista de espera implementa reserva optimista con lock de cita.

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | No | Demasiado lento para espacio time-critical de 2 horas |
| whatsapp | Yes | Canal principal — WhatsApp tiene mayor apertura inmediata |
| sms | Yes | Canal de respaldo y alcance adicional |
| in-app | Yes | Para pacientes que tengan el portal activo |

**Rationale de no-email:** El email puede tardar minutos en aparecer en el cliente de correo. Con un link que expira en 2 horas, WhatsApp y SMS ofrecen mayor probabilidad de acción inmediata.

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_waitlist_slot_available_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text

```
🦷 ¡Hay un espacio disponible para ti, {{1}}!

{{2}} tiene un espacio disponible:
📅 {{3}} a las {{4}}
👨‍⚕️ {{5}} en {{6}}

Este espacio expira en 2 horas. ¡Reserva ahora:
{{7}}

⚡ Primero en reservar, primero en atenderse.
```

### Variables

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | `patient_first_name` | "Ana" |
| {{2}} | `appointment_type_display` | "Consulta de ortodoncia" |
| {{3}} | `slot_date_display` | "Martes 3 de marzo" |
| {{4}} | `slot_time` | "10:30 AM" |
| {{5}} | `doctor_display_name` | "Dra. Patricia Mora" |
| {{6}} | `clinic_name` | "Clínica Smile" |
| {{7}} | `book_slot_url` | "dtos.io/w/abc12" |

### Longitud estimada

Con variables ejemplo: ~280 caracteres. Dentro del límite de 1024.

### WhatsApp Button

```
Tipo: URL Button
Texto: "⚡ Reservar ahora"
URL: {{book_slot_url}}
```

---

## SMS Template

### Texto del SMS

```
DentalOS: Espacio disponible {{slot_date_short}} {{slot_time}} con Dr. {{doctor_last_name}}. Reserva en 2h: {{sms_short_url}} (primero en llegar)
```

### Variables SMS

| Variable | Ejemplo | Notas |
|----------|---------|-------|
| `{{slot_date_short}}` | "mar 3/mar" | Fecha corta |
| `{{slot_time}}` | "10:30 AM" | Hora |
| `{{doctor_last_name}}` | "Mora" | Solo apellido |
| `{{sms_short_url}}` | "dtos.io/w/abc12" | Short URL; "w" = waitlist |

### Longitud del SMS

Template completo: ~148 caracteres. Dentro del límite de 160.

---

## In-App Notification (Portal del Paciente)

```json
{
  "type": "appointment",
  "title": "⚡ ¡Hay un espacio disponible!",
  "body": "{{appointment_type_display}} con {{doctor_display_name}} el {{slot_date_short}} a las {{slot_time}}. Reserva antes de que expire en 2 horas.",
  "action_url": "/citas/reservar?slot={{slot_id}}&token={{booking_token}}",
  "metadata": {
    "slot_id": "{{slot_id}}",
    "expires_at": "{{slot_expires_at_iso}}",
    "urgency": "critical"
  }
}
```

**Color del ícono:** Verde pulsante / animado si es posible (`#16A34A`) — tipo `appointment` con urgencia máxima.

**Persistencia:** La notificación in-app debe mostrar un contador regresivo de las 2 horas. Si el slot es reservado por alguien más, actualizar la notificación a "Este espacio ya fue reservado por otro paciente."

---

## Book Slot URL & Token

### URL Structure

```
https://portal.dentalos.io/citas/reservar?slot={{slot_id}}&token={{booking_token}}
```

### Token Properties

| Propiedad | Valor |
|-----------|-------|
| Tipo | JWT firmado con payload del slot |
| Payload | `{ "slot_id": "uuid", "patient_id": "uuid", "tenant_id": "uuid", "type": "waitlist_booking", "exp": NOW + 7200 }` |
| Expiración | 2 horas exactas desde la generación |
| Uso único | Sí — al reservar exitosamente el token se invalida |

### Concurrencia (First-Come-First-Served)

El booking endpoint implementa optimistic locking:

```sql
-- Al intentar reservar:
UPDATE appointments
SET status = 'confirmed', patient_id = :patient_id, booked_at = NOW()
WHERE id = :slot_id
  AND status = 'available'  -- Solo si sigue disponible
RETURNING id;

-- Si 0 rows afectadas: el espacio ya fue tomado por otro paciente
-- Si 1 row afectada: reserva exitosa
```

Si el espacio ya fue tomado: respuesta al paciente "Lo sentimos, este espacio ya fue reservado. ¿Te añadimos a la lista para el próximo espacio disponible?"

---

## Slot Matching Logic

Al cancelarse una cita, el servicio de waitlist busca pacientes en espera con los siguientes criterios en orden de prioridad:

1. **Doctor exacto** + **tipo de servicio exacto** + **horario compatible** (score 3)
2. **Doctor exacto** + **tipo de servicio exacto** (score 2)
3. **Tipo de servicio exacto** + **cualquier doctor** (score 1)

Si hay múltiples pacientes con el mismo score, se ordenan por `waitlist.joined_at` (FIFO).

Los primeros 3 pacientes del ranking reciben la notificación simultáneamente.

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{patient_phone}}` | string | `tenant.patients.phone` en E.164 | "+573001234567" |
| `{{appointment_type_display}}` | string | `appointments.type` convertido | "Consulta de ortodoncia" |
| `{{slot_date_display}}` | string | Fecha del slot en es-419 largo | "Martes, 3 de marzo de 2026" |
| `{{slot_date_short}}` | string | Fecha corta para SMS | "mar 3/mar" |
| `{{slot_time}}` | string | Hora del slot en timezone del tenant | "10:30 AM" |
| `{{doctor_display_name}}` | string | `tenant.users.display_name` | "Dra. Patricia Mora" |
| `{{doctor_last_name}}` | string | `tenant.users.last_name` | "Mora" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{slot_id}}` | uuid | `appointments.id` del slot cancelado | UUID |
| `{{booking_token}}` | string | JWT firmado para este paciente + slot | Token |
| `{{book_slot_url}}` | string | URL completa al portal de reserva | URL |
| `{{sms_short_url}}` | string | Short URL del portal | "dtos.io/w/abc12" |
| `{{slot_expires_at_iso}}` | string | `NOW + 2h` en ISO 8601 | "2026-02-25T17:30:00-05:00" |
| `{{expires_in_hours}}` | integer | Siempre "2" | 2 |

---

## Sending Rules

### Timing
- **Envío:** Inmediato — el evento se procesa con prioridad máxima (priority: 9).
- **Latencia máxima:** 60 segundos desde la cancelación de la cita hasta entrega al paciente.

### Rate Limiting de la Lista de Espera
- Máximo 3 pacientes notificados simultáneamente para el mismo slot (evitar sobrenotificación).
- Si el slot no es reservado en 2 horas, se puede notificar a los siguientes 3 pacientes de la lista.

### Deduplication
- **Idempotency key:** `waitlist_slot:{slot_id}:{patient_id}`
- **Ventana:** 2 horas (la duración del token).
- Si el mismo slot es re-procesado por re-entrega de RabbitMQ, no re-notificar al mismo paciente.

### Notificación Post-Expiración
- Cuando el token expira sin que el paciente reserve: notificación in-app de actualización: "El espacio expiró. Sigues en la lista de espera."
- Esta actualización es un UPDATE a la notificación in-app existente, no una nueva notificación.

### Token Expirado — UX
- Cuando el paciente hace clic en el link después de las 2 horas:
  - Portal muestra: "Este espacio ya no está disponible."
  - Opción: "Ver otros espacios disponibles" o "Seguir en la lista de espera"

### Slot Reservado por Otro Paciente (2do y 3er notificados)
- Los pacientes que recibieron la notificación pero el primero ya reservó:
  - Su token sigue "activo" tecnológicamente hasta que expiren los 2h
  - Pero el endpoint de reserva devuelve: "Este espacio ya fue tomado. ¿Te añadimos a la lista para el próximo?"
  - In-app actualizado: "Este espacio fue reservado. Sigues en la lista de espera."

---

## Testing

### Test Cases

#### Happy Path
1. Cita cancelada — 1 paciente en lista de espera
   - **Given:** Cita cancelada; 1 paciente en lista de espera con matching criterio (mismo doctor, mismo tipo)
   - **When:** Evento `waitlist_slot_available` publicado
   - **Then:** WhatsApp enviado al paciente en < 60s; SMS enviado; in-app en portal; token válido por 2h

2. Paciente reserva exitosamente dentro de 2 horas
   - **Given:** Paciente recibe notificación; hace clic en link y reserva
   - **When:** `POST /citas/reservar` con token válido
   - **Then:** Cita confirmada; token invalidado; notificación de confirmación (E-05) enviada; otros pacientes notificados que el espacio fue tomado

3. 3 pacientes en lista de espera para el mismo slot
   - **Given:** 3 pacientes en lista para ese doctor/tipo/horario
   - **When:** Slot disponible
   - **Then:** Los 3 reciben WhatsApp/SMS simultáneamente; el primero en reservar gana; los otros 2 reciben mensaje "ya fue reservado" al intentar

#### Edge Cases
1. Token expirado (> 2 horas)
   - **Given:** Paciente hace clic en el link 2h10min después
   - **When:** Token procesado
   - **Then:** 400 "Este espacio ya no está disponible. Sigues en la lista de espera." con opción de continuar en lista

2. Dos pacientes intentan reservar simultáneamente (race condition)
   - **Given:** 2 pacientes hacen clic al mismo tiempo en sus links de reserva
   - **When:** Ambos endpoints ejecutan casi simultáneamente
   - **Then:** Optimistic lock: solo uno tiene éxito (UPDATE con `status = 'available'` retorna 1 row); el otro recibe "Ya fue reservado"; ambas respuestas en < 200ms

3. Paciente sin teléfono en lista de espera
   - **Given:** Paciente se unió a la lista de espera pero no tiene teléfono registrado
   - **When:** Slot disponible
   - **Then:** WhatsApp y SMS skipped; solo in-app enviado si tiene portal activo; log warning

4. Slot liberado y re-cancelado (edge case de agenda)
   - **Given:** Primer slot liberado → paciente A reserva → paciente A cancela → slot disponible de nuevo
   - **When:** Segunda cancelación
   - **Then:** Nuevo evento waitlist_slot_available para el segundo paciente en la lista; token del paciente A invalidado

5. Idempotency (re-entrega del mensaje RabbitMQ)
   - **Given:** Evento ya procesado; idempotency key en Redis
   - **When:** Mismo evento re-entregado
   - **Then:** No re-notificar al paciente; ACK; log `skipped (idempotent)`

#### Error Cases
1. WhatsApp API lenta (> 30s)
   - **Given:** Meta WhatsApp API tarda 35s en responder
   - **When:** WhatsApp envío intentado
   - **Then:** Timeout a los 10s; SMS enviado independientemente; WhatsApp retry inmediato (no esperar 30s — tiempo crítico); si WhatsApp falla permanentemente, SMS es suficiente para el caso de uso

2. Slot ya reservado cuando el worker procesa el evento (muy raro)
   - **Given:** Slot cancelado y ya re-asignado por el staff manualmente en < 1s
   - **When:** Worker intenta enviar notificación de waitlist
   - **Then:** Worker verifica status del slot antes de enviar; si status != 'available', skipped con log

### Test Data Requirements

- Lista de espera con 1, 3, y 0 pacientes para los criterios del slot
- Pacientes con teléfono válido en E.164; paciente sin teléfono
- Slot (cita cancelada) con doctor y tipo de servicio específicos
- Entorno con múltiples workers para simular concurrencia

### Mocking Strategy

- WhatsApp: mock via respx con timeout simulado
- Twilio: test credentials con mock de SMS
- RabbitMQ: Docker Compose para pruebas de concurrencia
- Redis: fakeredis para idempotency
- DB: PostgreSQL con transacciones para test de optimistic lock

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] WhatsApp enviado en < 60s después de cancelación de cita que coincide con lista de espera
- [ ] SMS enviado como canal complementario
- [ ] In-app con urgencia máxima y tiempo de expiración visible
- [ ] Email NO enviado (solo WhatsApp/SMS/in-app)
- [ ] Token expira exactamente en 2 horas
- [ ] Optimistic lock: solo 1 paciente puede reservar el slot; el segundo recibe "ya fue tomado"
- [ ] Máximo 3 pacientes notificados simultáneamente para el mismo slot
- [ ] Token expirado: mensaje claro con opción de seguir en lista
- [ ] Paciente sin teléfono: solo in-app si tiene portal
- [ ] Idempotencia: re-entrega del evento no duplica la notificación
- [ ] WhatsApp lento: SMS enviado independientemente sin esperar
- [ ] Todos los test cases pasan

---

## Out of Scope

- El endpoint de unirse a la lista de espera (spec AP-10)
- El algoritmo de matching de la lista de espera (spec AP-11)
- Notificación de confirmación al reservar (se usa E-05)
- Gestión administrativa de la lista de espera
- Priorización de pacientes en lista de espera (FIFO únicamente en v1)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
