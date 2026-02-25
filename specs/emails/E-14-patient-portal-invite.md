# E-14 — Invitación al Portal del Paciente

---

## Overview

**Feature:** Invitación enviada al paciente para que active su acceso al portal de pacientes de DentalOS. Desde el portal pueden ver su historia clínica, aprobar planes de tratamiento, firmar consentimientos, ver facturas, hacer pagos y solicitar citas. Enviado por la clínica cuando deciden dar acceso digital al paciente. Link de registro expira en 30 días.

**Domain:** portal / patients / notifications

**Priority:** Medium

**Dependencies:** P-14 (patient-portal-access), A-01 (register), N-04, N-05

---

## Trigger

**Evento:** `patient_portal_invite_sent`

**Cuándo se dispara:** Al ejecutar `POST /api/v1/patients/{id}/portal-access` con `action = 'invite'` por parte de un usuario autorizado (clinic_owner, doctor, receptionist).

**RabbitMQ routing key:** `notification.patient.portal_invite_sent`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente invitado | patient | Siempre |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal — link de registro está en el email |
| whatsapp | Yes | Complementario — muchos pacientes ven WhatsApp antes que email |
| sms | No | No aplica |
| in-app | No | El paciente aún no tiene acceso al portal |

---

## Email Template

### Subject Line

```
{{clinic_name}} te invita a tu portal de paciente — DentalOS
```

**Ejemplo:** "Clínica Smile te invita a tu portal de paciente — DentalOS"

### Preheader

```
Accede a tu historial clínico, citas, facturas y más desde cualquier dispositivo.
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica
  - Color de la clínica

[HERO — Fondo azul claro, ícono de portal / pantalla con persona]
  - Ícono: 🌐 o ícono de portal
  - Título H1: "Tu portal de paciente está listo"
  - Subtítulo: "Hola {{patient_first_name}}, {{clinic_name}} te ha dado acceso a tu portal personal."

[PÁRRAFO INTRODUCTORIO]
  "Ahora puedes gestionar tu salud dental desde cualquier dispositivo.
  Tu portal es seguro, privado y siempre disponible."

[QUÉ PUEDES HACER — Grid de 6 features con íconos]

  📋 Ver tu historia clínica
  "Accede a tu odontograma y expediente dental en cualquier momento."

  📅 Ver y solicitar citas
  "Consulta tus citas próximas y solicita nuevas citas con tu médico."

  💊 Planes de tratamiento
  "Revisa y aprueba los planes de tratamiento de tu doctor."

  ✍️ Firmar consentimientos
  "Firma digitalmente los documentos de consentimiento de forma segura."

  💰 Ver facturas y pagar
  "Consulta tus facturas y realiza pagos en línea de forma segura."

  💬 Mensajes con tu clínica
  "Comunícate directamente con el equipo de {{clinic_name}}."

[CARD DE ACTIVACIÓN — Con borde prominente]
  Encabezado: "Crea tu cuenta en 2 minutos"
  Pasos:
  1. Haz clic en el botón de abajo
  2. Crea tu contraseña segura
  3. ¡Listo! Accede a tu portal

  Nota: "Tu correo de acceso será: {{patient_email}}"

[CTA PRINCIPAL — Grande y prominente]
  Botón: "Activar mi portal"
  URL: {{portal_activation_url}}
  Color: #2563EB (azul primario)
  Tamaño: 220px mínimo, 52px alto

[AVISO DE EXPIRACIÓN]
  Card con ícono de reloj:
  "Este enlace de activación expira el {{expiry_datetime}}."
  Texto: "Después de esa fecha, pide a {{clinic_name}} que te envíe una nueva invitación."

[SEGURIDAD Y PRIVACIDAD]
  Título: "Tu privacidad es nuestra prioridad"
  "Tu información médica está protegida con cifrado de nivel bancario.
  Solo tú y tu equipo médico autorizado tienen acceso a tus datos."

[ALTERNATIVA EN TEXTO]
  "Si el botón no funciona, copia y pega este enlace:"
  URL literal: {{portal_activation_url}}

[FOOTER]
  - Logos: Clínica + "Powered by DentalOS"
  - "© {{current_year}} {{clinic_name}}. Todos los derechos reservados."
  - "Este correo fue enviado porque {{clinic_name}} te registró como paciente."
  - Política de privacidad
  - "Si no eres paciente de {{clinic_name}}, ignora este correo."
```

### CTA Button

```
Texto: "Activar mi portal"
URL: {{portal_activation_url}}
Color: #2563EB (azul)
Texto: blanco, bold
Tamaño: 220px mínimo, 52px alto
```

### Plain-text Fallback

```
Tu portal de paciente está listo — {{clinic_name}}

Hola {{patient_first_name}},

{{clinic_name}} te ha dado acceso a tu portal personal de DentalOS.

Desde tu portal puedes:
- Ver tu historia clínica
- Revisar y confirmar citas
- Ver facturas y pagar
- Firmar consentimientos
- Enviar mensajes a tu clínica

Para activar tu cuenta:
{{portal_activation_url}}

Este enlace expira el: {{expiry_datetime}}
Tu correo de acceso será: {{patient_email}}

Si no eres paciente de {{clinic_name}}, ignora este correo.

© {{clinic_name}} | Gestionado por DentalOS
```

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_patient_portal_invite_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text

```
Hola {{1}}, {{2}} te invita a tu portal de paciente DentalOS 🦷

Desde tu portal puedes ver tus citas, historia clínica, facturas y más.

Activa tu cuenta aquí (válido 30 días): {{3}}

¿Preguntas? Llámanos al {{4}}.
```

### Variables

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | `patient_first_name` | "Ana" |
| {{2}} | `clinic_name` | "Clínica Smile" |
| {{3}} | `portal_activation_url` | "dtos.io/p/abc12" |
| {{4}} | `clinic_phone` | "601-555-0100" |

### WhatsApp Button

```
Tipo: URL Button
Texto: "Activar mi portal"
URL: {{portal_activation_url}}
```

---

## Portal Activation Link Specification

### URL Structure

```
https://portal.dentalos.io/activar?token={{activation_token}}&clinic={{tenant_slug}}
```

### Token Properties

| Propiedad | Valor |
|-----------|-------|
| Tipo | JWT firmado + entrada en Redis |
| Payload | `{ "patient_id": "uuid", "tenant_id": "uuid", "email": "string", "type": "portal_activation", "exp": timestamp }` |
| Expiración | 30 días |
| Uso único | Sí |

### Flujo de Activación

1. Paciente hace clic en el link
2. Si es primera vez → muestra formulario de creación de contraseña
3. Paciente crea contraseña
4. Cuenta activada → sesión iniciada → redirige al dashboard del portal
5. Email de bienvenida al portal enviado (E-01 versión paciente — future spec)

### Casos de Re-invitación

- Si el paciente ya tiene cuenta activa en el portal: el link redirige directamente a login
- Si la invitación expiró: el endpoint devuelve página de "invitación expirada — contacta a tu clínica"
- Si el staff re-invita (nueva invitación): token anterior invalidado, nuevo token generado

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{patient_email}}` | string | `tenant.patients.email` | "ana.gomez@gmail.com" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{clinic_phone}}` | string | Tenant settings | "601-555-0100" |
| `{{clinic_logo_url}}` | string | Tenant settings | CDN URL |
| `{{clinic_primary_color}}` | string | Tenant settings | "#1D4ED8" |
| `{{portal_activation_url}}` | string | Generado: `{portal_url}/activar?token={token}&clinic={slug}` | URL |
| `{{expiry_datetime}}` | string | `created_at + 30d` en es-419 | "27 de marzo de 2026" |
| `{{current_year}}` | integer | Año actual | 2026 |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al generar la invitación.
- **Prioridad:** Medium (priority: 5).
- **Latencia máxima:** 5 minutos.

### Deduplication
- **Idempotency key:** `portal_invite:{patient_id}:{tenant_id}`
- **Ventana:** 24 horas — si el staff re-invita en menos de 24h (doble clic accidental), no reenviar.
- Re-invitación intencional después de 24h: nuevo token, nuevo email.

### Re-invitación
- Si el paciente no activó en 30 días, el staff puede enviar nueva invitación via `POST /patients/{id}/portal-access` con `action = 'reinvite'`.
- Token anterior se invalida automáticamente.

### Condición de No-Envío
- Si el paciente ya tiene portal activo (`patients.portal_status = 'active'`): no enviar invitación; devolver 409 en el endpoint.

### Transaccional
- Este email es enviado en nombre de la clínica (no de DentalOS).
- Sin embargo, usa la infraestructura de email de DentalOS.

---

## Testing

### Test Cases

#### Happy Path
1. Primera invitación al portal
   - **Given:** Paciente registrado sin acceso al portal; staff envía invitación
   - **When:** `POST /patients/{id}/portal-access` con `action = 'invite'`
   - **Then:** Email enviado en < 5min; WhatsApp enviado; token válido 30 días; link funciona → formulario de creación de contraseña

2. Paciente activa el portal exitosamente
   - **Given:** Email recibido; paciente hace clic y crea contraseña
   - **When:** Formulario completado
   - **Then:** Portal activo; `patients.portal_status = 'active'`; token invalidado; sesión iniciada; paciente en dashboard

3. Logo de clínica en email
   - **Given:** Tenant con logo configurado
   - **When:** Email renderizado
   - **Then:** Logo de la clínica visible en header

#### Edge Cases
1. Invitación a paciente que ya tiene portal activo
   - **Given:** `patients.portal_status = 'active'`
   - **When:** Staff intenta enviar invitación
   - **Then:** Endpoint devuelve 409 "Este paciente ya tiene acceso activo al portal."; email NO enviado

2. Invitación expirada (> 30 días)
   - **Given:** Paciente no activó en 30 días
   - **When:** Intenta usar el link
   - **Then:** Página de "Invitación expirada. Pide a tu clínica una nueva invitación."; link de contacto a la clínica

3. Doble clic del staff (invitación duplicada en < 24h)
   - **Given:** Staff hace clic dos veces en "Invitar"
   - **When:** Segundo evento procesado dentro de 24h
   - **Then:** Idempotency key activo; email NO reenviado; log `skipped (idempotent)`

4. Paciente sin email registrado
   - **Given:** Paciente no tiene email en su perfil
   - **When:** Staff intenta invitar
   - **Then:** Endpoint devuelve 400 "El paciente no tiene correo electrónico registrado. Actualiza su perfil primero."; WhatsApp enviado si tiene teléfono

#### Error Cases
1. SendGrid falla
   - **Given:** SendGrid devuelve 503
   - **When:** Envío intentado
   - **Then:** Reintento estándar; email entregado en segundo intento; WhatsApp ya entregado independientemente

### Test Data Requirements

- Paciente con email sin portal activo
- Paciente con portal ya activo
- Paciente sin email pero con teléfono
- Tenant con y sin logo

### Mocking Strategy

- SendGrid: sandbox mode
- WhatsApp: respx mock
- Token: test JWT factory

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 5min con lista de 6 features del portal
- [ ] Link "Activar mi portal" con token válido 30 días
- [ ] WhatsApp enviado con botón de activación
- [ ] Correo de acceso del paciente visible en el email
- [ ] Paciente con portal activo: 409 y sin email
- [ ] Link expirado: página de "invitación expirada" con contacto a la clínica
- [ ] Doble invitación en < 24h: sin email duplicado
- [ ] Paciente sin email: 400 en endpoint; WhatsApp si tiene teléfono
- [ ] Logo de la clínica en el header
- [ ] Todos los test cases pasan

---

## Out of Scope

- El endpoint de acceso al portal (spec P-01)
- Email de bienvenida al portal (una vez activado — future spec)
- Funcionalidades del portal en sí (specs P-01 a P-12)
- Portal de paciente para menores de edad (representante legal)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
