# E-04 — Invitación a Miembro del Equipo

---

## Overview

**Feature:** Email de invitación enviado a un nuevo miembro del equipo (doctor, asistente, recepcionista) cuando el clinic_owner o un usuario con permisos adecuados los invita a unirse a la clínica en DentalOS. El link de aceptación expira en 7 días. El invitado puede no tener cuenta previa en DentalOS — en ese caso se les redirige al flujo de registro.

**Domain:** emails / users / tenants

**Priority:** High

**Dependencies:** U-03 (invite-team-member), A-04 (accept-invite), infra/authentication-rules.md, N-05

---

## Trigger

**Evento:** `team_invitation_sent`

**Cuándo se dispara:** Al completar exitosamente `POST /api/v1/users/invite` por parte de un clinic_owner o usuario con permiso `users:invite`.

**RabbitMQ routing key:** `notification.system.team_invitation_sent`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Persona invitada (puede no tener cuenta) | El rol asignado en la invitación | Siempre al generar la invitación |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal — único para este evento |
| whatsapp | No | Invitaciones profesionales se manejan por email |
| sms | No | No aplica |
| in-app | No | El invitado puede no tener cuenta aún |

---

## Email Template

### Subject Line

```
{{inviter_name}} te invitó a {{clinic_name}} en DentalOS
```

**Ejemplos:**
- "Dra. Patricia Mora te invitó a Clínica Odontológica Smile en DentalOS"
- "Carlos Mendoza te invitó a Centro Dental Norte en DentalOS"

### Preheader

```
Tienes 7 días para aceptar esta invitación y unirte al equipo de {{clinic_name}}.
```

### HTML Structure

```
[HEADER]
  - Logo de {{clinic_name}} (si disponible) O logo DentalOS como fallback
  - Nombre de la clínica en texto prominente

[HERO]
  - Ícono de dos personas / equipo
  - Título H1: "Fuiste invitado a unirte a {{clinic_name}}"
  - Subtítulo: "{{inviter_name}} te ha invitado a colaborar como {{role_display_name}}."

[DETALLE DE LA INVITACIÓN — Card con fondo azul muy claro]
  Encabezado: "Detalles de tu invitación"
  Tabla:
  - Clínica: {{clinic_name}}
  - Tu rol: {{role_display_name}}
  - Invitado por: {{inviter_name}} ({{inviter_role_display}})
  - Esta invitación expira: {{expiry_datetime}}

[QUÉ PUEDES HACER — 3 bullets según el rol]
  Para doctor:
  • Acceder y gestionar expedientes clínicos
  • Crear y gestionar tus propias citas
  • Ver tu agenda diaria y semanal

  Para asistente:
  • Apoyar en la gestión de expedientes
  • Coordinar citas con el equipo
  • Acceder a funciones según tu perfil

  Para recepcionista:
  • Gestionar la agenda de la clínica
  • Registrar y actualizar pacientes
  • Procesar pagos y facturas

[CTA PRIMARIO]
  Botón grande centrado, color azul primario:
  "Aceptar invitación"
  URL: {{accept_invite_url}}

[AVISO DE EXPIRACIÓN — con ícono de reloj]
  "Esta invitación expira el {{expiry_datetime}}. Después de esa fecha,
  pide a {{inviter_name}} que te envíe una nueva invitación."

[ABOUT DENTALOS — si el invitado no tiene cuenta previa]
  Título: "¿Qué es DentalOS?"
  "DentalOS es la plataforma de gestión clínica dental diseñada para
  latinoamérica. Rápida, segura y cumple con la normativa colombiana
  Resolución 1888."

[FOOTER]
  - Logo DentalOS
  - "© 2026 DentalOS. Todos los derechos reservados."
  - "Si no conoces a {{inviter_name}} o a {{clinic_name}}, ignora este correo."
  - "Este es un correo transaccional. No puedes darte de baja de invitaciones activas."
  - Link política de privacidad
```

### CTA Button

```
Texto: "Aceptar invitación"
URL: {{accept_invite_url}}
Color: #2563EB (azul primario DentalOS)
Texto: blanco, bold
Tamaño: 200px mínimo, 48px alto
```

### Plain-text Fallback

```
{{inviter_name}} te invitó a {{clinic_name}} en DentalOS

Hola,

Fuiste invitado a unirte a {{clinic_name}} como {{role_display_name}}.

Invitado por: {{inviter_name}}
Tu rol: {{role_display_name}}
Expira: {{expiry_datetime}}

Para aceptar la invitación, visita:
{{accept_invite_url}}

Si no conoces a {{inviter_name}}, ignora este correo.

© 2026 DentalOS
```

---

## Accept Invite Link Specification

### URL Structure

```
https://app.dentalos.io/auth/accept-invite?token={{invite_token}}
```

### Token Properties

| Propiedad | Valor |
|-----------|-------|
| Tipo | JWT firmado con HMAC-SHA256 |
| Payload | `{ "invite_id": "uuid", "tenant_id": "uuid", "email": "string", "role": "string", "type": "team_invite", "exp": timestamp }` |
| Expiración | 7 días desde la generación |
| Uso único | Sí — invalidado al aceptar |
| Almacenamiento | Redis + tabla `public.team_invitations` |

### Flujo al Aceptar

1. **Usuario con cuenta existente:** Redirige a login si no está autenticado, luego acepta la invitación y se une al tenant.
2. **Usuario sin cuenta:** Redirige al registro completando el formulario, luego acepta automáticamente.

---

## Role Display Names

| Role (interno) | Display en español |
|----------------|-------------------|
| `doctor` | "Doctor(a)" |
| `assistant` | "Asistente dental" |
| `receptionist` | "Recepcionista" |
| `clinic_owner` | "Propietario(a)" |

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{inviter_name}}` | string | `public.users.first_name + last_name` del invitador | "Dra. Patricia Mora" |
| `{{inviter_role_display}}` | string | Role del invitador convertido a display | "Propietaria" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{clinic_logo_url}}` | string | `public.tenants.settings.logo_url`; null si no hay | "https://cdn.dentalos.io/logos/abc.png" |
| `{{role_display_name}}` | string | Role asignado convertido a display | "Doctor(a)" |
| `{{accept_invite_url}}` | string | Generado: `{base_url}/auth/accept-invite?token={token}` | "https://app.dentalos.io/auth/accept-invite?token=eyJ..." |
| `{{expiry_datetime}}` | string | `created_at + 7d` en es-419 | "4 de marzo de 2026" |
| `{{role_benefits}}` | list | Generado dinámicamente por rol | Lista de bullets según rol |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al recibir el evento.
- **Prioridad:** High (priority: 7).
- **Latencia máxima:** 2 minutos.

### Deduplication
- **Idempotency key:** `team_invite:{invite_id}`
- **Ventana:** 24h — no reenviar por retries de RabbitMQ.
- Reenvío manual de invitación (por el clinic_owner) genera un nuevo `invite_id` y por tanto un nuevo email.

### Re-invitación
- Si un clinic_owner re-invita a alguien (nueva invitación), la invitación anterior se invalida y se envía un nuevo email.
- Máximo 3 invitaciones activas por dirección de email por tenant.

### Transaccional
- **Tipo:** Transaccional — el destinatario fue invitado explícitamente.
- **Sin** unsubscribe link (7 días de vigencia, es transitorio).

---

## Testing

### Test Cases

#### Happy Path
1. Invitación a doctor con cuenta existente
   - **Given:** clinic_owner invita a doctor@example.com (quien ya tiene cuenta en otro tenant)
   - **When:** `POST /api/v1/users/invite` exitoso
   - **Then:** Email enviado en < 2min; subject contiene nombre del invitador y clínica; rol muestra "Doctor(a)"; link válido por 7 días

2. Invitación a recepcionista sin cuenta
   - **Given:** Email invitado no tiene cuenta en DentalOS
   - **When:** Invitado hace clic en el link
   - **Then:** Redirige a flujo de registro; al completar, se une al tenant automáticamente

3. Logo de clínica incluido
   - **Given:** Tenant tiene logo configurado en settings
   - **When:** Email renderizado
   - **Then:** Logo de la clínica aparece en el header del email

#### Edge Cases
1. Invitación expirada (> 7 días)
   - **Given:** Invitado hace clic 8 días después
   - **When:** Token procesado
   - **Then:** 400 "Esta invitación ha expirado. Contacta a {{clinic_name}} para que te envíen una nueva."

2. Invitación ya aceptada
   - **Given:** Invitado ya aceptó la invitación
   - **When:** Hace clic en el link por segunda vez (o comparte el link)
   - **Then:** 400 "Esta invitación ya fue aceptada."

3. Re-invitación (segunda invitación invalida la primera)
   - **Given:** Primera invitación enviada y pendiente
   - **When:** clinic_owner envía segunda invitación al mismo email
   - **Then:** Primera invitación invalidada; nuevo email enviado con nuevo token

4. Clínica sin logo
   - **Given:** Tenant sin logo configurado
   - **When:** Email renderizado
   - **Then:** Logo DentalOS como fallback; sin imagen rota

#### Error Cases
1. Email inválido del invitado
   - **Given:** Formato de email inválido en la invitación (bug de validación frontend)
   - **When:** Envío intentado
   - **Then:** Fallo permanente; Sentry alert; DLQ entry

### Test Data Requirements

- clinic_owner con permiso de invitar
- Email destino con cuenta existente en otro tenant
- Email destino sin cuenta en DentalOS
- Tenant con y sin logo configurado

### Mocking Strategy

- SendGrid: sandbox mode para integración
- Redis: fakeredis para token storage
- JWT: test factory para invite tokens

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 2min después de `POST /api/v1/users/invite`
- [ ] Subject contiene nombre del invitador y nombre de la clínica
- [ ] Rol del invitado mostrado en español con display name correcto
- [ ] Link expira en 7 días exactos
- [ ] Logo de la clínica en header (con fallback a logo DentalOS)
- [ ] Bullets de beneficios varían correctamente por rol
- [ ] Link usado redirige a registro si usuario no tiene cuenta
- [ ] Invitación expirada devuelve 400 con mensaje claro
- [ ] Segunda invitación invalida la primera
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- El endpoint de aceptación de invitación (spec A-04)
- Invitación al portal de pacientes (spec E-14)
- Notificación al clinic_owner cuando la invitación es aceptada (spec separado)
- Invitación de múltiples usuarios a la vez (v2)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
