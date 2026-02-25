# E-15 — Notificación de Nuevo Mensaje

---

## Overview

**Feature:** Notificación enviada cuando hay un nuevo mensaje en un hilo de conversación entre la clínica y el paciente. Aplica a ambas partes: el paciente recibe notificación cuando la clínica escribe, y el staff recibe notificación in-app cuando el paciente escribe. Implementa debouncing (máx 1 email por hilo por 5 minutos) para evitar spam en conversaciones activas.

**Domain:** messages / notifications

**Priority:** Medium

**Dependencies:** MSG-01 (send-message), MSG-02 (message-thread), N-04, N-05

---

## Trigger

**Evento:** `new_message`

**Cuándo se dispara:** Al completar `POST /api/v1/messages/{thread_id}/send` exitosamente. El evento lleva información del hilo y del último mensaje.

**RabbitMQ routing key:** `notification.message.new_message`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente | patient | Cuando el emisor es un miembro de la clínica (doctor, assistant, receptionist) |
| Staff (doctor / asistente / recepcionista) | clinic staff | In-app únicamente cuando el emisor es el paciente |
| Clinic owner | clinic_owner | In-app si está suscrito al hilo o si es el primer mensaje del paciente |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Para paciente; con debouncing de 5 minutos por hilo |
| whatsapp | Yes | Para paciente; si tiene teléfono y tenant habilitado; también debounced |
| sms | No | No aplica para mensajes |
| in-app | Yes | Para el staff de la clínica (cuando paciente escribe); para el paciente en el portal |

---

## Debouncing Logic

El debouncing evita enviar múltiples emails/WhatsApp si una conversación está activa:

```
Redis key: notification:msg_debounce:{thread_id}:{recipient_id}
TTL: 300 segundos (5 minutos)

Al recibir el evento new_message:
1. Check: ¿Existe la key de debounce para este thread + recipient?
   - SÍ: No enviar email/WhatsApp; solo actualizar in-app. ACK el mensaje.
   - NO: Proceder con envío; SET la key con TTL 5 min; enviar todos los canales.
```

**Resultado:** Si hay 10 mensajes en 3 minutos, el paciente recibe 1 email (el primero) y los demás solo aparecen en la notificación in-app (que siempre se actualiza).

---

## Email Template

### Subject Line

```
Nuevo mensaje de {{sender_display_name}} — {{clinic_name}}
```

**Ejemplos:**
- "Nuevo mensaje de Dra. Patricia Mora — Clínica Smile"
- "Nuevo mensaje de Recepción — Clínica Smile"

### Preheader

```
"{{message_preview}}" — Responde para continuar la conversación.
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica

[HERO — Fondo azul claro, ícono de burbuja de chat]
  - Ícono: 💬
  - Título H1: "Tienes un nuevo mensaje"
  - Subtítulo: "{{sender_display_name}} te envió un mensaje."

[PREVIEW DEL MENSAJE — Card con borde izquierdo azul]
  Encabezado:
  Foto / avatar de {{sender_display_name}} (o inicial si no hay foto)
  Nombre: "{{sender_display_name}}"
  Rol: "{{sender_role_display}}" (e.g., "Doctora" / "Recepcionista" / "Clínica")
  Timestamp: "{{message_timestamp}}"

  Cuerpo del preview:
  "{{message_preview}}"
  (Primeros 100 caracteres del mensaje; si hay más: "... leer mensaje completo")

  Nota si hay archivos adjuntos:
  "📎 + 1 archivo adjunto" (solo si `attachment_count > 0`)

[CTA PRINCIPAL]
  Párrafo: "Responde directamente desde tu portal:"
  Botón: "Responder"
  URL: {{patient_portal_thread_url}}
  Color: #2563EB (azul)

[CONTEXTO DEL HILO — Solo si no es el primer mensaje]
  Línea de texto: "Este mensaje es parte de la conversación: '{{thread_subject}}'"

[FOOTER]
  - Logo DentalOS
  - Unsubscribe: "Gestionar notificaciones de mensajes" → {{notification_preferences_url}}
  - Política de privacidad
  - Nota: "Este correo es un resumen. Los mensajes futuros en esta conversación en los próximos 5 minutos pueden no generar un nuevo correo."
```

### CTA Button

```
Texto: "Responder"
URL: {{patient_portal_thread_url}}
Color: #2563EB
Texto: blanco, bold
```

### Plain-text Fallback

```
Nuevo mensaje de {{sender_display_name}} — {{clinic_name}}

Hola {{recipient_first_name}},

{{sender_display_name}} te escribió:

"{{message_preview}}"

Para responder, visita: {{patient_portal_thread_url}}

© {{clinic_name}} | Gestionado por DentalOS
Para gestionar notificaciones: {{notification_preferences_url}}
```

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_new_message_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text

```
💬 {{1}} de {{2}} te escribió en {{3}}:

"{{4}}"

Para responder: {{5}}
```

### Variables

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | Texto fijo "Nuevo mensaje" | "Nuevo mensaje" |
| {{2}} | `sender_display_name` | "Dra. Patricia Mora" |
| {{3}} | `clinic_name` | "Clínica Smile" |
| {{4}} | `message_preview` (max 80 chars) | "Recuerda traer tus radiografías para tu próxima consulta." |
| {{5}} | `patient_portal_thread_url` | "dtos.io/m/abc12" |

---

## In-App Notification (para el Staff — App Interna)

Enviado cuando el PACIENTE escribe a la clínica:

```json
{
  "type": "system",
  "title": "Nuevo mensaje de {{patient_full_name}}",
  "body": "\"{{message_preview}}\"",
  "action_url": "/messages/{{thread_id}}",
  "metadata": {
    "thread_id": "{{thread_id}}",
    "patient_id": "{{patient_id}}",
    "sender_id": "{{sender_id}}"
  }
}
```

**Color del ícono:** Azul/gris (`#6B7280`) — tipo `system`

**Destinatarios del in-app para staff:**
- El doctor asignado al hilo
- La recepcionista asignada (si hay asignación de hilo)
- Si no hay asignación: todos los usuarios con rol `receptionist` y `clinic_owner`

---

## In-App Notification (para el Paciente — Portal)

Enviado cuando el STAFF escribe al paciente:

```json
{
  "type": "system",
  "title": "Mensaje de {{clinic_name}}",
  "body": "{{sender_display_name}}: \"{{message_preview}}\"",
  "action_url": "/mensajes/{{thread_id}}",
  "metadata": {
    "thread_id": "{{thread_id}}"
  }
}
```

---

## Sender Role Display Names

| Rol interno | Display en notificación |
|------------|------------------------|
| `doctor` | Nombre del doctor (e.g., "Dra. Patricia Mora") |
| `assistant` | "Asistente de {{clinic_name}}" |
| `receptionist` | "Recepción de {{clinic_name}}" |
| `clinic_owner` | Nombre del propietario o "{{clinic_name}}" |
| `patient` | Nombre del paciente |

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{recipient_first_name}}` | string | Nombre del destinatario | "Ana" |
| `{{sender_display_name}}` | string | Ver tabla de roles arriba | "Dra. Patricia Mora" |
| `{{sender_role_display}}` | string | Rol convertido a display | "Doctora" |
| `{{message_preview}}` | string | Primeros 100 chars de `messages.content`; sin HTML | "Recuerda traer tus radiografías..." |
| `{{message_timestamp}}` | string | `messages.created_at` en timezone del tenant | "25 de feb. a las 3:45 PM" |
| `{{thread_subject}}` | string | `message_threads.subject` | "Consulta sobre mi tratamiento" |
| `{{attachment_count}}` | integer | Número de archivos adjuntos en el mensaje | 1 |
| `{{patient_portal_thread_url}}` | string | `{portal_url}/mensajes/{thread_id}` | URL |
| `{{thread_id}}` | uuid | `message_threads.id` | UUID |
| `{{patient_id}}` | uuid | `patients.id` | UUID |
| `{{patient_full_name}}` | string | Nombre completo del paciente | "Ana Gómez" |
| `{{clinic_name}}` | string | Tenant name | "Clínica Smile" |
| `{{clinic_logo_url}}` | string | Tenant settings | CDN URL |
| `{{notification_preferences_url}}` | string | Portal preferencias | URL |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al recibir el evento (dentro del debounce lógico).
- **Prioridad:** Medium (priority: 5).

### Debouncing (Detalle de Implementación)

```
Flujo del worker al recibir new_message:

1. Cargar recipient_id del destinatario del mensaje
2. GET Redis key: notification:msg_debounce:{thread_id}:{recipient_id}
3. Si existe (debounce activo):
   a. Enviar SOLO in-app notification
   b. ACK el mensaje de RabbitMQ
   c. No enviar email ni WhatsApp
4. Si NO existe (primera notificación en ventana):
   a. SET Redis key: notification:msg_debounce:{thread_id}:{recipient_id} = "1" EX 300
   b. Enviar email + WhatsApp + in-app
   c. ACK el mensaje
```

**Resultado:** En una conversación activa de 10 minutos, el paciente recibe máximo 2 emails (uno al minuto 0 y otro después de los primeros 5 minutos si la conversación continúa).

### Opt-out
- Respeta `message_received.email` y `message_received.whatsapp` en preferencias del paciente.
- In-app siempre enviado.

### Mensaje Largo (Truncado)
- El preview del mensaje se trunca a 100 caracteres (email) o 80 caracteres (WhatsApp).
- Si el mensaje original contiene HTML o markdown, se strip antes de mostrar en el preview.

### Privacidad del Contenido
- El mensaje preview se incluye en el email y WhatsApp — considerarlo PHI.
- El delivery log NO registra el contenido del mensaje — solo `event_type`, `channel`, `status`.
- Sentry error reports deben redactar el campo `message_preview`.

---

## Testing

### Test Cases

#### Happy Path
1. Staff envía primer mensaje al paciente
   - **Given:** Primer mensaje en un hilo; paciente con email y teléfono; debounce key no existe
   - **When:** `POST /messages/{thread_id}/send` por staff
   - **Then:** Email al paciente con preview; WhatsApp enviado; in-app al paciente en portal; debounce key SET en Redis

2. Staff envía segundo mensaje en 3 minutos (debouncing activo)
   - **Given:** Debounce key existe en Redis
   - **When:** Segundo mensaje enviado
   - **Then:** Email NO reenviado; WhatsApp NO reenviado; in-app actualizado; Redis key NO renovada (TTL sigue corriendo)

3. Staff envía mensaje después de 6 minutos (debounce expirado)
   - **Given:** Debounce key expiró (TTL 300s)
   - **When:** Nuevo mensaje enviado
   - **Then:** Nuevo email enviado; WhatsApp enviado; nueva debounce key SET

4. Paciente escribe a la clínica (in-app para staff)
   - **Given:** Paciente envía mensaje
   - **When:** Evento procesado
   - **Then:** In-app para recepcionista y doctor asignado; NO email/WhatsApp al staff

#### Edge Cases
1. Mensaje con archivo adjunto
   - **Given:** Mensaje con 1 archivo PDF adjunto
   - **When:** Email renderizado
   - **Then:** "📎 + 1 archivo adjunto" visible en el preview del email

2. Mensaje con contenido HTML/markdown (strip)
   - **Given:** Mensaje contiene `<script>alert(1)</script>` o `**texto en negritas**`
   - **When:** Preview generado
   - **Then:** Tags HTML removidos; markdown renderizado como texto plano; sin XSS

3. Mensaje muy largo (> 100 chars)
   - **Given:** Mensaje de 500 caracteres
   - **When:** Preview generado
   - **Then:** Solo primeros 100 chars + "... leer mensaje completo" con link al portal

4. Hilo sin asignación a ningún staff específico
   - **Given:** Paciente inicia hilo; nadie asignado
   - **When:** In-app para staff
   - **Then:** Notificación a todos los receptionist + clinic_owner del tenant

#### Error Cases
1. Redis no disponible (debounce falla)
   - **Given:** Redis caído temporalmente
   - **When:** Debounce check intenta
   - **Then:** Fallback: asumir que no hay debounce (seguro para el usuario); enviar notificación normalmente; log warning de Redis unavailable

### Test Data Requirements

- Hilo de mensajes activo entre paciente y doctor
- Mensajes simples, con adjunto, y con contenido HTML
- Tenant con WhatsApp habilitado y sin WhatsApp

### Mocking Strategy

- Redis: fakeredis para simular debounce key TTL
- SendGrid: sandbox
- WhatsApp: respx mock

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado al paciente cuando staff escribe (primer mensaje en ventana 5min)
- [ ] WhatsApp enviado al paciente con preview truncado a 80 chars
- [ ] In-app al staff cuando paciente escribe
- [ ] Debouncing: máx 1 email por hilo por 5 minutos
- [ ] Preview del mensaje truncado a 100 chars en email, 80 en WhatsApp
- [ ] HTML/markdown stripped del preview (sin XSS)
- [ ] Adjuntos mencionados en el email
- [ ] Redis caído: fallback a envío sin debounce (con log warning)
- [ ] Preferencias de notificación respetadas
- [ ] Todos los test cases pasan

---

## Out of Scope

- Los endpoints de mensajería (specs MSG-01 a MSG-05)
- Notificación de lectura / read receipts
- Mensajería en tiempo real (WebSocket — futura feature v2)
- Chatbot / respuestas automáticas

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
