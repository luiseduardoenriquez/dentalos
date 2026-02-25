# E-02 — Verificación de Correo Electrónico

---

## Overview

**Feature:** Email de verificación de correo enviado al usuario después del registro para confirmar que el correo electrónico es válido y pertenece al usuario. El link es de uso único y expira en 24 horas. Aplica tanto al propietario de la clínica al registrarse como a doctores y staff invitados que crean su cuenta.

**Domain:** emails / auth

**Priority:** Critical

**Dependencies:** A-01 (register), A-04 (team-invite), infra/authentication-rules.md, infra/notification-send-engine (N-05)

---

## Trigger

**Evento:** `email_verification_requested`

**Cuándo se dispara:**
1. Al registrar un nuevo usuario (clinic_owner o primer registro de doctor/staff)
2. Al re-solicitar verificación desde el endpoint `POST /api/v1/auth/resend-verification`
3. Al cambiar el email del usuario (el nuevo email requiere re-verificación)

**RabbitMQ routing key:** `notification.system.email_verification_requested`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Usuario recién registrado | clinic_owner, doctor, assistant, receptionist | Siempre al registrarse |
| Usuario que cambió su email | Cualquier rol autenticado | Al actualizar email en perfil |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Único canal posible — el correo es lo que se verifica |
| whatsapp | No | No aplica |
| sms | No | No aplica |
| in-app | No | Usuario puede no tener sesión activa |

---

## Email Template

### Subject Line

```
Verifica tu correo — DentalOS
```

### Preheader

```
Haz clic en el enlace para confirmar tu dirección de correo electrónico. Expira en 24 horas.
```

### HTML Structure

```
[HEADER]
  - Logo DentalOS centrado
  - Sin colores de clínica (email de sistema, no de tenant)

[HERO]
  - Ícono de sobre de correo con checkmark
  - Título H1: "Verifica tu correo electrónico"
  - Subtítulo: "Hola {{user_first_name}}, confirma que este correo te pertenece."

[CUERPO PRINCIPAL]
  Párrafo:
  "Para activar tu cuenta en DentalOS y acceder a todas las funciones, necesitamos verificar
  tu dirección de correo electrónico."

  Párrafo de urgencia:
  "Este enlace expirará en 24 horas. Si no lo usas antes de {{expiry_datetime}}, tendrás
  que solicitar un nuevo enlace."

[CTA PRIMARIO — Bloque destacado con fondo gris claro]
  Texto arriba del botón: "Haz clic en el botón para verificar tu correo:"

  Botón grande centrado, color verde (#16A34A):
  "Verificar mi correo"
  URL: {{verification_url}}

  Texto alternativo debajo del botón:
  "Si el botón no funciona, copia y pega este enlace en tu navegador:"
  URL literal: {{verification_url}}
  (monospace, color gris, fondo gris muy claro, border-radius)

[AVISO DE SEGURIDAD — Bloque con ícono de candado]
  "Si no creaste una cuenta en DentalOS, ignora este correo. Tu dirección no será
  registrada si no haces clic en el enlace."

[EXPIRACIÓN]
  "Este enlace es válido por una sola vez y expira el {{expiry_datetime}}."

[FOOTER]
  - Logo DentalOS pequeño
  - "© 2026 DentalOS. Todos los derechos reservados."
  - "Este es un correo transaccional de seguridad. No puedes darte de baja."
  - Link política de privacidad
```

### CTA Button

```
Texto: "Verificar mi correo"
URL: {{verification_url}}
Color: #16A34A (verde — acción de confirmación)
Texto: blanco, bold
Tamaño: 220px mínimo, 48px alto
```

### Plain-text Fallback

```
Verifica tu correo electrónico — DentalOS

Hola {{user_first_name}},

Para verificar tu correo electrónico en DentalOS, visita este enlace:
{{verification_url}}

Este enlace expira el: {{expiry_datetime}}
Este enlace es de un solo uso.

Si no creaste una cuenta en DentalOS, ignora este correo.

© 2026 DentalOS
```

---

## Verification Link Specification

### URL Structure

```
https://app.dentalos.io/auth/verify-email?token={{verification_token}}
```

### Token Properties

| Propiedad | Valor |
|-----------|-------|
| Tipo | JWT firmado con HMAC-SHA256 |
| Payload | `{ "user_id": "uuid", "email": "string", "type": "email_verification", "exp": timestamp }` |
| Expiración | 24 horas desde la generación |
| Uso único | Sí — el token se invalida al usarse (marcado en Redis como `used`) |
| Almacenamiento | Redis key: `auth:email_verify:{token_hash}` con TTL 86400s |

### Token Invalidation

Un token se invalida (uso único) cuando:
1. El usuario hace clic y el endpoint lo procesa exitosamente
2. El usuario solicita un nuevo token (el anterior se invalida en Redis)
3. El TTL de 24h expira (Redis lo elimina automáticamente)

**Redis key al usar:** `SET auth:email_verify:{token_hash} "used" EX 86400`

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{user_first_name}}` | string | `public.users.first_name` | "María" |
| `{{user_email}}` | string | `public.users.email` | "maria@clinica.com" |
| `{{verification_url}}` | string | Generado en el evento: `{base_url}/auth/verify-email?token={token}` | "https://app.dentalos.io/auth/verify-email?token=eyJ..." |
| `{{expiry_datetime}}` | string | `created_at + 24h` formateado en es-419 | "26 de febrero de 2026 a las 3:45 PM" |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al recibir el evento en la cola.
- **Prioridad de cola:** Critical (priority: 9).
- **Latencia máxima:** 30 segundos desde la solicitud hasta entrega al proveedor de email.

### Deduplication
- **Clave de idempotencia:** `email_verify:{user_id}:{token_hash}`
- **Ventana:** Para re-solicitudes: máximo 1 email cada 5 minutos por usuario.
- **Redis key anti-spam:** `auth:email_verify_rate:{user_id}` con TTL 300s — si existe, rechazar nueva solicitud.
- **Nota:** El re-envío (`/resend-verification`) verifica este rate limit antes de publicar el evento a RabbitMQ.

### Transaccional vs Marketing
- **Tipo:** Transaccional de seguridad — NO puede ser desactivado.
- **No tiene** link de unsubscribe.
- **SendGrid category:** `transactional_security`

### Rate Limiting (endpoint de reenvío)
- Máximo 3 reenvíos por usuario por hora.
- Máximo 1 reenvío cada 5 minutos.

---

## Security Notes

1. **No confirmar existencia de cuenta:** El endpoint `POST /resend-verification` responde siempre con 200, incluso si el email no existe — para no revelar si un correo está registrado.
2. **Token de uso único:** Implementado via Redis. El token solo puede usarse una vez.
3. **Sin información sensible en el token:** El JWT solo contiene `user_id`, no passwords ni datos de salud.
4. **HTTPS obligatorio:** El `verification_url` siempre usa HTTPS.
5. **No loggear el token completo:** Solo loggear los primeros 8 caracteres para debugging.

---

## Testing

### Test Cases

#### Happy Path
1. Verificación exitosa de nuevo usuario
   - **Given:** Usuario recién registrado con email "test@example.com", token válido generado
   - **When:** Email enviado; usuario hace clic en el link
   - **Then:** Email entregado en < 30s; token válido; usuario marcado como `email_verified = true`; token invalidado en Redis

2. Re-solicitud de verificación
   - **Given:** Usuario registrado sin verificar, último email hace 10 minutos
   - **When:** `POST /api/v1/auth/resend-verification`
   - **Then:** Nuevo token generado; email enviado; token anterior invalidado

#### Edge Cases
1. Token expirado (> 24h)
   - **Given:** Usuario recibe email; intenta verificar 25 horas después
   - **When:** Hace clic en el link
   - **Then:** Endpoint devuelve 400 con mensaje "El enlace de verificación ha expirado. Solicita uno nuevo."

2. Token ya usado
   - **Given:** Usuario hace clic en el link de verificación una segunda vez
   - **When:** Token procesado
   - **Then:** Endpoint devuelve 400 con mensaje "Este enlace ya fue usado. Tu correo ya está verificado."

3. Rate limit de reenvío
   - **Given:** Usuario solicita reenvío 3 veces en 5 minutos
   - **When:** Cuarta solicitud
   - **Then:** 429 con mensaje "Por favor espera antes de solicitar otro correo de verificación."

4. Reenvío del evento RabbitMQ (idempotencia)
   - **Given:** Email ya enviado; idempotency key en Redis
   - **When:** Mismo evento re-entregado
   - **Then:** Email NO reenviado; ACKed; log `skipped`

#### Error Cases
1. Email de destinatario inválido (formato incorrecto en DB)
   - **Given:** Email del usuario tiene formato inválido
   - **When:** Envío intentado
   - **Then:** Fallo permanente; Sentry alert; DLQ entry; usuario puede solicitar soporte

### Test Data Requirements

- Usuario no verificado con email válido
- Usuario no verificado con token expirado (manipular created_at)
- Entorno SendGrid sandbox

### Mocking Strategy

- SendGrid: sandbox mode para integración; mock para unit tests
- Redis: fakeredis para simular token storage y TTL
- JWT: test factory para generar tokens de verificación

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 30s después del registro
- [ ] Subject es exactamente "Verifica tu correo — DentalOS"
- [ ] Botón "Verificar mi correo" con URL correcta y token válido
- [ ] URL alternativa de texto plano incluida en el email
- [ ] Token expira en 24 horas exactas
- [ ] Token es de un solo uso — segundo uso devuelve 400
- [ ] Re-solicitud invalida el token anterior
- [ ] Rate limit: máximo 1 reenvío cada 5 minutos
- [ ] No hay unsubscribe link
- [ ] Plain-text fallback incluido
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- El endpoint `GET /auth/verify-email` que procesa el token (spec A-05)
- Verificación de número de teléfono (spec separado)
- Verificación en dos factores / 2FA (spec A-06)
- Magic link login (diferente al link de verificación)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
