# E-03 — Restablecimiento de Contraseña

---

## Overview

**Feature:** Email de restablecimiento de contraseña enviado cuando un usuario solicita recuperar el acceso a su cuenta. El link contiene un token de uso único que expira en 1 hora. Por seguridad, el endpoint de solicitud no confirma si el correo está registrado en el sistema (protección contra enumeración de usuarios).

**Domain:** emails / auth

**Priority:** Critical

**Dependencies:** A-07 (password-reset-request), A-08 (password-reset-confirm), infra/authentication-rules.md, N-05

---

## Trigger

**Evento:** `password_reset_requested`

**Cuándo se dispara:** Al recibir `POST /api/v1/auth/forgot-password` con un email que existe en el sistema. Si el email no existe, el evento NO se publica (pero el endpoint responde igual — 200 — para no revelar existencia de la cuenta).

**RabbitMQ routing key:** `notification.system.password_reset_requested`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Usuario que solicitó el reset | Cualquier rol | Solo si el email existe en `public.users` |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Único canal — reset de contraseña por seguridad requiere acceso al correo |
| whatsapp | No | No aplica por razones de seguridad |
| sms | No | No aplica (v1; SMS 2FA es futura feature) |
| in-app | No | El usuario no tiene acceso a la app si olvidó su contraseña |

---

## Email Template

### Subject Line

```
Restablece tu contraseña — DentalOS
```

### Preheader

```
Recibimos una solicitud para restablecer la contraseña de tu cuenta. Este enlace expira en 1 hora.
```

### HTML Structure

```
[HEADER]
  - Logo DentalOS centrado
  - Sin branding de clínica (email de seguridad del sistema)

[HERO]
  - Ícono de candado abierto
  - Título H1: "Restablece tu contraseña"
  - Subtítulo: "Hola {{user_first_name}}, recibimos una solicitud para cambiar tu contraseña."

[CUERPO PRINCIPAL]
  Párrafo:
  "Si solicitaste restablecer tu contraseña, haz clic en el botón de abajo.
  Este enlace es válido por 1 hora y solo puede usarse una vez."

[ALERTA DE TIEMPO — Bloque con fondo amarillo claro, ícono de reloj]
  "Este enlace expira el {{expiry_datetime}}. Si no lo usas a tiempo, tendrás que
  solicitar uno nuevo."

[CTA PRIMARIO]
  Botón centrado, color naranja (#EA580C) para indicar urgencia:
  "Restablecer contraseña"
  URL: {{reset_url}}

  Texto alternativo:
  "Si el botón no funciona, copia este enlace:"
  URL literal: {{reset_url}}

[INFORMACIÓN DE SEGURIDAD — Bloque con ícono de escudo]
  Título: "Información de seguridad"

  Tabla:
  - Fecha y hora de la solicitud: {{request_datetime}}
  - Dirección IP: {{request_ip}}
  - Navegador / Dispositivo: {{user_agent_summary}}

  Texto:
  "Si no solicitaste este cambio, ignora este correo. Tu contraseña actual permanecerá
  sin cambios. Si crees que alguien más está intentando acceder a tu cuenta, contacta
  nuestro soporte inmediatamente."

[NO-ACTION SECTION]
  "Si NO solicitaste este cambio:"
  - No hagas clic en el enlace
  - Tu contraseña no cambiará
  - El enlace expirará automáticamente
  - Contacta soporte: {{support_email}}

[FOOTER]
  - Logo DentalOS
  - "© 2026 DentalOS. Todos los derechos reservados."
  - "Este es un correo transaccional de seguridad. No puedes darte de baja."
  - Link política de privacidad
  - Link términos de servicio
```

### CTA Button

```
Texto: "Restablecer contraseña"
URL: {{reset_url}}
Color: #EA580C (naranja — urgencia temporal)
Texto: blanco, bold
Tamaño: 220px mínimo, 48px alto
```

### Plain-text Fallback

```
Restablece tu contraseña — DentalOS

Hola {{user_first_name}},

Recibimos una solicitud para restablecer la contraseña de tu cuenta en DentalOS.

Para restablecer tu contraseña, visita:
{{reset_url}}

Este enlace expira el: {{expiry_datetime}}
Este enlace es de un solo uso.

Solicitud realizada desde:
- Fecha/hora: {{request_datetime}}
- IP: {{request_ip}}

Si NO solicitaste este cambio, ignora este correo. Tu contraseña no cambiará.
¿Necesitas ayuda? Escríbenos a {{support_email}}

© 2026 DentalOS
```

---

## Reset Link Specification

### URL Structure

```
https://app.dentalos.io/auth/reset-password?token={{reset_token}}
```

### Token Properties

| Propiedad | Valor |
|-----------|-------|
| Tipo | JWT firmado con HMAC-SHA256, clave separada de auth JWT |
| Payload | `{ "user_id": "uuid", "email": "string", "type": "password_reset", "jti": "uuid", "exp": timestamp }` |
| Expiración | 1 hora desde la generación |
| Uso único | Sí — el `jti` se registra en Redis como `used` al procesarse |
| Almacenamiento | Redis key: `auth:pwd_reset:{jti}` con TTL 3600s |

### Token Invalidation

Un token se invalida cuando:
1. Se usa exitosamente para cambiar la contraseña
2. El usuario solicita un nuevo reset (el anterior se revoca en Redis)
3. El TTL de 1h expira

**On use:** `SET auth:pwd_reset:{jti} "used" EX 3600`

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{user_first_name}}` | string | `public.users.first_name`; fallback: "Usuario" | "Ana" |
| `{{reset_url}}` | string | Generado en el evento | "https://app.dentalos.io/auth/reset-password?token=eyJ..." |
| `{{expiry_datetime}}` | string | `requested_at + 1h` en es-419 | "25 de febrero de 2026 a las 5:00 PM" |
| `{{request_datetime}}` | string | `requested_at` en es-419 | "25 de febrero de 2026 a las 4:00 PM" |
| `{{request_ip}}` | string | IP del request HTTP; parcialmente ofuscada para privacidad | "192.168.xxx.xxx" |
| `{{user_agent_summary}}` | string | User-Agent parseado; máximo 60 chars | "Chrome 121 en Windows 11" |
| `{{support_email}}` | string | Configuración de entorno | "soporte@dentalos.io" |

### Nota sobre privacidad de IP

La IP se incluye para alertar al usuario en caso de acceso no autorizado. Se ofusca el último octeto por privacidad: `192.168.1.xxx`. Esta información **no** se loggea en Sentry (PHI-adjacent).

---

## Sending Rules

### Timing
- **Envío:** Inmediato — la urgencia del reset requiere entrega rápida.
- **Prioridad de cola:** Critical (priority: 9).
- **Latencia máxima:** 30 segundos desde la solicitud.

### Deduplication
- **Rate limit:** Máximo 3 solicitudes de reset por usuario por hora.
- **Redis key:** `auth:pwd_reset_rate:{user_id}` con TTL 3600s, contador incrementable.
- Si el rate limit se supera, el endpoint devuelve 429 y NO publica el evento — no se envía email.

### Anti-Enumeration (Seguridad Crítica)
- El endpoint `POST /api/v1/auth/forgot-password` SIEMPRE responde 200, independientemente de si el email existe.
- Si el email no existe, NO se publica el evento a RabbitMQ — silencio total.
- El tiempo de respuesta del endpoint es equalizado (no-timing attack) mediante un sleep artificial cuando el email no existe.

### Transaccional
- **Tipo:** Transaccional de seguridad — NO puede ser desactivado.
- **Sin** unsubscribe link.
- **SendGrid category:** `transactional_security`

---

## Testing

### Test Cases

#### Happy Path
1. Reset exitoso de contraseña
   - **Given:** Usuario existente solicita reset; email válido registrado
   - **When:** `POST /api/v1/auth/forgot-password` con email válido
   - **Then:** Email enviado en < 30s; subject correcto; token válido por 1h; IP del solicitante incluida

2. Usuario hace clic y cambia contraseña
   - **Given:** Token válido, no expirado, no usado
   - **When:** Usuario visita reset_url y completa el formulario
   - **Then:** Contraseña actualizada; token invalidado en Redis; sesiones anteriores revocadas

#### Edge Cases
1. Email no registrado (anti-enumeration)
   - **Given:** Solicitud con email que no existe en la DB
   - **When:** `POST /api/v1/auth/forgot-password`
   - **Then:** 200 OK en el endpoint; NO se envía email; NO se publica evento; tiempo de respuesta similar al caso exitoso

2. Token expirado
   - **Given:** Token generado hace más de 1 hora
   - **When:** Usuario intenta usar el token
   - **Then:** 400 "El enlace de restablecimiento ha expirado. Solicita uno nuevo."

3. Token ya usado
   - **Given:** Token ya procesado; `jti` marcado en Redis
   - **When:** Segundo intento de uso
   - **Then:** 400 "Este enlace ya fue utilizado. Solicita uno nuevo si necesitas cambiar tu contraseña."

4. Múltiples solicitudes (segunda invalida primera)
   - **Given:** Usuario solicita reset; luego solicita otro antes de usar el primero
   - **When:** Primer token enviado aún no usado; nuevo token solicitado
   - **Then:** Primer token invalidado; nuevo token generado; nuevo email enviado

5. Rate limit superado
   - **Given:** Usuario hizo 3 solicitudes en 1 hora
   - **When:** Cuarta solicitud
   - **Then:** 429; email NO enviado; mensaje "Has superado el límite de solicitudes. Espera antes de intentarlo de nuevo."

#### Error Cases
1. SendGrid falla (5xx)
   - **Given:** SendGrid devuelve 503
   - **When:** Envío intentado
   - **Then:** Reintento en 30s; hasta 3 intentos; si todos fallan: DLQ y Sentry alert

### Test Data Requirements

- Usuario con email verificado y contraseña activa
- Usuario con email no registrado (para anti-enumeration test)
- Tokens con diferentes estados: nuevo, expirado, usado

### Mocking Strategy

- SendGrid: sandbox mode para integración
- Redis: fakeredis para TTL y token state
- HTTP Request: mock para capturar IP y User-Agent

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 30s después de solicitud válida
- [ ] Subject es exactamente "Restablece tu contraseña — DentalOS"
- [ ] Token expira exactamente en 1 hora
- [ ] Token es de uso único — segundo uso devuelve 400
- [ ] IP del solicitante incluida con último octeto ofuscado
- [ ] Email no registrado: respuesta 200 sin enviar email (anti-enumeration)
- [ ] Rate limit de 3 solicitudes/hora aplicado
- [ ] Segunda solicitud invalida la primera
- [ ] No hay unsubscribe link
- [ ] Plain-text fallback válido
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- El endpoint de procesamiento del token (spec A-08)
- Reset de contraseña para superadmin (flujo separado)
- SMS como canal alternativo para reset (futura feature)
- Políticas de complejidad de contraseña (spec A-08)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
