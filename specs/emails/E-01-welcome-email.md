# E-01 — Welcome Email (Registro de Clínica)

---

## Overview

**Feature:** Email de bienvenida enviado al propietario de la clínica inmediatamente después de completar el registro del tenant. Presenta la plataforma, establece expectativas del onboarding y dirige al usuario a completar la configuración inicial. Es el primer contacto de marca con el cliente.

**Domain:** emails / notifications

**Priority:** Critical

**Dependencies:** T-01 (tenant-register), A-01 (register), infra/notification-send-engine (N-05)

---

## Trigger

**Evento:** `clinic_registered`

**Cuándo se dispara:** Al completar exitosamente la creación del tenant en `POST /api/v1/tenants/register`. El evento es publicado a RabbitMQ por el servicio de tenants inmediatamente después del commit a la base de datos.

**RabbitMQ routing key:** `notification.system.clinic_registered`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Propietario de la clínica | clinic_owner | Siempre — el usuario que completó el registro |

**Nota:** Este email NO va a otros miembros del equipo. Solo al clinic_owner que creó la cuenta.

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal — único canal para este evento |
| whatsapp | No | No aplica en registro inicial |
| sms | No | No aplica en registro inicial |
| in-app | No | El usuario acaba de registrarse — no hay sesión activa aún |

---

## Email Template

### Subject Line

```
Bienvenido a DentalOS, {{owner_first_name}} — Tu clínica está lista
```

### Preheader

```
Sigue estos 3 pasos para comenzar a usar DentalOS en {{clinic_name}}.
```

### HTML Structure

```
[HEADER]
  - Logo DentalOS (centrado, 200px ancho)
  - Línea de color del plan (verde = Free, azul = Starter, etc.)

[HERO]
  - Título H1: "¡Bienvenido a DentalOS, {{owner_first_name}}!"
  - Subtítulo: "{{clinic_name}} ya está configurada. Aquí está todo lo que necesitas para empezar."

[CUERPO PRINCIPAL]
  Párrafo introductorio:
  "Gracias por elegir DentalOS para gestionar tu clínica. Tu cuenta en el plan {{plan_name}} está activa
  y lista para usar. Te tomará menos de 10 minutos completar la configuración inicial."

[PASOS DE ONBOARDING — 3 cards horizontales]

  Paso 1: Completa tu perfil
  Ícono: 👤 (ícono de perfil)
  Texto: "Agrega tu logo, dirección, horarios de atención y datos de contacto de {{clinic_name}}."
  Link: "Ir a Configuración →"
  URL: {{portal_base_url}}/settings/clinic

  Paso 2: Agrega tu primer médico
  Ícono: 🦷 (ícono de doctor)
  Texto: "Invita a los doctores de tu equipo. Cada doctor activo cuenta hacia tu plan."
  Link: "Invitar doctor →"
  URL: {{portal_base_url}}/team/invite

  Paso 3: Registra tu primer paciente
  Ícono: 📋 (ícono de paciente)
  Texto: "Registra un paciente de prueba para explorar el odontograma e historia clínica."
  Link: "Agregar paciente →"
  URL: {{portal_base_url}}/patients/new

[CTA PRIMARIO]
  Botón grande centrado, color primario DentalOS (#2563EB):
  "Comenzar configuración"
  URL: {{onboarding_url}}

[INFORMACIÓN DE CUENTA]
  Tabla de datos:
  - Plan activo: {{plan_name}}
  - Clínica: {{clinic_name}}
  - Correo de acceso: {{owner_email}}
  - Fecha de registro: {{registration_date}}

[RECURSOS DE AYUDA]
  Tres links de soporte:
  - "Centro de ayuda" → {{help_center_url}}
  - "Video tutorial (5 min)" → {{tutorial_video_url}}
  - "Contactar soporte" → {{support_email}}

[FOOTER]
  - Logo DentalOS pequeño
  - "© 2026 DentalOS. Todos los derechos reservados."
  - Dirección de la empresa
  - "Este es un correo transaccional. No puedes darte de baja de este tipo de correos."
  - Link de política de privacidad
```

### CTA Button

```
Texto: "Comenzar configuración"
URL: {{onboarding_url}}
Color: #2563EB (azul primario DentalOS)
Texto del botón: blanco, bold
Tamaño: 200px ancho mínimo, 48px alto
```

### Plain-text Fallback

```
Bienvenido a DentalOS, {{owner_first_name}}

Tu clínica {{clinic_name}} está lista. Sigue estos 3 pasos para comenzar:

1. Completa tu perfil de clínica: {{portal_base_url}}/settings/clinic
2. Agrega tu primer doctor: {{portal_base_url}}/team/invite
3. Registra tu primer paciente: {{portal_base_url}}/patients/new

Comenzar configuración: {{onboarding_url}}

Plan activo: {{plan_name}}
Correo de acceso: {{owner_email}}

¿Necesitas ayuda? Escríbenos a {{support_email}}

© 2026 DentalOS
```

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{owner_first_name}}` | string | `public.users.first_name` | "Carlos" |
| `{{owner_email}}` | string | `public.users.email` | "carlos@clinicasmile.com" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{plan_name}}` | string | `public.tenants.plan` convertido a display name | "Plan Starter" |
| `{{registration_date}}` | string | `public.tenants.created_at` formateado en locale es-419 | "25 de febrero de 2026" |
| `{{onboarding_url}}` | string | `{portal_base_url}/onboarding?tenant={tenant_slug}` | "https://app.dentalos.io/onboarding?tenant=clinica-smile" |
| `{{portal_base_url}}` | string | Configuración de entorno | "https://app.dentalos.io" |
| `{{help_center_url}}` | string | Configuración de entorno | "https://help.dentalos.io" |
| `{{tutorial_video_url}}` | string | Configuración de entorno | "https://dentalos.io/tutorial" |
| `{{support_email}}` | string | Configuración de entorno | "soporte@dentalos.io" |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al recibir el evento `clinic_registered` en la cola.
- **Prioridad de cola:** Alta (priority: 9) — primer contacto crítico.
- **Latencia máxima aceptable:** 60 segundos desde el registro hasta entrega al proveedor.

### Deduplication
- **Clave de idempotencia:** `welcome_email:{tenant_id}`
- **Ventana:** 24 horas — si el evento se republica en las primeras 24h (retry de RabbitMQ), no se reenvía.
- **Redis key:** `notification:idempotency:welcome_email:{tenant_id}` con TTL 86400.

### Transaccional vs Marketing
- **Tipo:** Transaccional — este correo no puede ser desactivado por el usuario.
- **SendGrid category:** `transactional`
- **ASM Group:** No asignado (transaccional excluido de unsubscribe groups).

### Branding
- Este email usa branding de **DentalOS** (no de la clínica), ya que el tenant acaba de registrarse y puede no tener logo configurado aún.

### Rate Limits
- 1 email por tenant en las primeras 24 horas de registro.

---

## Testing

### Test Cases

#### Happy Path
1. Registro exitoso de clínica nueva
   - **Given:** Nuevo tenant registrado con plan Starter, propietario con nombre "Carlos Mendoza", email "carlos@test.com", clínica "Dental Plus"
   - **When:** Evento `clinic_registered` publicado a RabbitMQ
   - **Then:** Email enviado a "carlos@test.com" en < 60s; subject contiene "Carlos"; body contiene "Dental Plus"; botón "Comenzar configuración" con URL correcta; delivery log registra status `delivered`

2. Plan Free registrado
   - **Given:** Tenant con plan Free registrado
   - **When:** Evento procesado
   - **Then:** `{{plan_name}}` renderiza "Plan Gratuito"; email entregado correctamente

#### Edge Cases
1. Reenvío del evento (RabbitMQ retry)
   - **Given:** Evento `clinic_registered` procesado exitosamente; idempotency key en Redis
   - **When:** El mismo evento es re-entregado por RabbitMQ
   - **Then:** Email NO reenviado; mensaje ACKed; log entry `skipped (idempotent)`

2. Propietario sin nombre
   - **Given:** `first_name` es null o vacío en el usuario
   - **When:** Template renderizado
   - **Then:** Subject y body usan fallback "Propietario" en lugar del nombre; no falla el envío

3. Fallo de SendGrid (5xx)
   - **Given:** SendGrid devuelve 503 en primer intento
   - **When:** Email enviado
   - **Then:** Reintento en 30s; segundo intento exitoso; delivery log registra `attempt_count: 2`

#### Error Cases
1. Email inválido del propietario
   - **Given:** `owner_email` tiene formato inválido en la base de datos (bug de registro)
   - **When:** Envío a SendGrid intentado
   - **Then:** Fallo permanente registrado; Sentry alert; entrada en `notification_dlq`

### Test Data Requirements

- Tenant con plan Starter, propietario con nombre completo
- Tenant con plan Free, propietario sin apellido
- Entorno con SendGrid en modo sandbox

### Mocking Strategy

- SendGrid: SDK en modo sandbox para pruebas de integración; mock completo para pruebas unitarias
- RabbitMQ: aio-pika in-memory broker para pruebas unitarias; broker real en Docker Compose para integración
- Redis: fakeredis para pruebas unitarias

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 60s después del registro del tenant
- [ ] Subject contiene `{{owner_first_name}}` y "DentalOS"
- [ ] Los 3 pasos de onboarding aparecen con links correctos
- [ ] Botón "Comenzar configuración" con URL correcta
- [ ] `{{plan_name}}` muestra el plan correcto para todos los planes (Free, Starter, Pro, Clínica, Enterprise)
- [ ] Idempotencia: re-entrega del evento no genera email duplicado
- [ ] Fallo de SendGrid genera reintento con backoff
- [ ] Delivery log registrado en `notification_delivery_log`
- [ ] Template renderiza correctamente en los 3 principales clientes de correo (Gmail, Outlook, Apple Mail)
- [ ] Plain-text fallback incluido y válido
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- Email de verificación de correo (ver E-02)
- Secuencia de emails de onboarding (días 3, 7, 30) — fuera del alcance de v1
- Personalización del template por plan
- Email de bienvenida al agregar nuevos doctores al equipo (ver E-04)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
