# E-10 — Solicitud de Firma de Consentimiento Informado

---

## Overview

**Feature:** Notificación de alta prioridad enviada al paciente cuando se genera un consentimiento informado que requiere su firma digital. El paciente accede al portal, lee el documento completo y firma electrónicamente (canvas + SHA-256). Crítico para cumplimiento de Resolución 1888 (Colombia) y Ley 527/1999 (firma digital). Canal: email + WhatsApp. Entrega garantizada.

**Domain:** consents / notifications

**Priority:** Critical

**Dependencies:** IC-01 (consent-create), IC-03 (consent-sign), P-14 (patient-portal), N-05, infra/audit-logging.md

---

## Trigger

**Evento:** `consent_signature_requested`

**Cuándo se dispara:** Al completar `POST /api/v1/consents` cuando `requires_signature = true` y el consentimiento es enviado al paciente. El consentimiento pasa a estado `pending_signature`.

**RabbitMQ routing key:** `notification.clinical.consent_signature_requested`

**Prioridad de mensaje:** Priority 9 (máxima) — consentimientos son bloqueantes para algunos procedimientos.

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente | patient | Siempre — firma requerida |
| Doctor que creó el consentimiento | doctor | In-app confirmación de envío |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal — incluye descripción del procedimiento |
| whatsapp | Yes | Canal de alta entrega para firma urgente |
| sms | No | Consentimiento requiere lectura del documento — SMS insuficiente |
| in-app | Yes | Para el paciente en el portal y para confirmación al doctor |

---

## Email Template

### Subject Line

```
Firma requerida: {{consent_type_display}} — {{clinic_name}}
```

**Ejemplo:** "Firma requerida: Consentimiento para cirugía oral — Clínica Smile"

### Preheader

```
{{doctor_display_name}} requiere tu firma para proceder. Por favor lee y firma el documento.
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica
  - Barra de color de la clínica

[HERO — Fondo naranja muy claro, ícono de pluma / firma]
  - Ícono: ✍️
  - Título H1: "Se requiere tu firma"
  - Subtítulo: "Hola {{patient_first_name}}, {{doctor_display_name}} necesita tu consentimiento para continuar."

[ALERT DE ACCIÓN REQUERIDA — Borde naranja/amarillo]
  Encabezado: "⚠ Acción requerida"
  Texto: "Este documento requiere tu firma antes de proceder con el tratamiento.
  Por favor lee detenidamente el consentimiento y firma digitalmente en el portal."

[DETALLES DEL CONSENTIMIENTO — Card]
  Encabezado: "Documento de consentimiento"
  Información:
  - 📄 Tipo: {{consent_type_display}}
  - 👨‍⚕️ Doctor(a): {{doctor_display_name}}
  - 🦷 Procedimiento: {{procedure_name}}
  - 📅 Generado: {{consent_date}}
  - ⏰ Vigencia para firma: {{expiry_datetime}} ({{days_to_expiry}} días)

[QUÉ ES ESTE DOCUMENTO]
  Título: "¿Qué es este documento?"
  Texto: "Un consentimiento informado es un documento legal donde confirmas que:
  • Recibiste información clara sobre el procedimiento '{{procedure_name}}'
  • Comprendes los riesgos y beneficios del tratamiento
  • Das tu autorización para que {{doctor_display_name}} proceda"

  Nota legal: "De acuerdo con la Resolución 1888 de 2021 del Ministerio de Salud de Colombia
  y la Ley 527/1999, tu firma digital tiene plena validez jurídica."

[CTA PRINCIPAL — Botón grande, prominente]
  Párrafo: "Para leer el documento completo y firmar:"
  Botón: "Firmar consentimiento"
  URL: {{sign_consent_url}}
  Color: #EA580C (naranja — urgencia)

[AVISO DE VALIDEZ DE LA FIRMA DIGITAL]
  Card con fondo azul muy claro, ícono de escudo:
  Título: "Sobre la firma digital"
  "Tu firma en DentalOS está respaldada por tecnología SHA-256 y cumple con los
  requisitos de la Ley 527/1999. Es completamente válida y segura."

[INFORMACIÓN DE CONTACTO]
  "¿Tienes preguntas sobre este procedimiento?"
  - Llama: {{clinic_phone}}
  - Email: {{clinic_contact_email}}

[FOOTER]
  - Logo DentalOS
  - "Este es un correo de alta importancia. La atención a este mensaje puede ser necesaria."
  - Política de privacidad
  - NOTA: Sin unsubscribe link — consentimientos son obligatorios para el tratamiento
```

### CTA Button

```
Texto: "Firmar consentimiento"
URL: {{sign_consent_url}}
Color: #EA580C (naranja urgente)
Texto: blanco, bold
Tamaño: 240px mínimo, 52px alto (más grande que otros CTAs — urgencia)
```

### Plain-text Fallback

```
Firma requerida — {{clinic_name}}

Hola {{patient_first_name}},

Se requiere tu firma para el siguiente documento:

Tipo: {{consent_type_display}}
Procedimiento: {{procedure_name}}
Doctor(a): {{doctor_display_name}}
Válido hasta: {{expiry_datetime}}

Para leer y firmar el consentimiento:
{{sign_consent_url}}

¿Preguntas? Llama al {{clinic_phone}}

IMPORTANTE: Tu firma tiene validez legal según la Ley 527/1999.

© {{clinic_name}} | Gestionado por DentalOS
```

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_consent_signature_request_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text

```
🖊 Firma requerida — {{1}}

Hola {{2}}, {{3}} necesita tu firma para el consentimiento de '{{4}}'.

Por favor lee y firma el documento antes del {{5}}:
{{6}}

¿Preguntas? Llama al {{7}}.
```

### Variables

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | `clinic_name` | "Clínica Smile" |
| {{2}} | `patient_first_name` | "Ana" |
| {{3}} | `doctor_display_name` | "Dra. Patricia Mora" |
| {{4}} | `procedure_name` | "cirugía oral" |
| {{5}} | `expiry_date_short` | "28 de febrero" |
| {{6}} | `sign_consent_url` | "dtos.io/f/abc12" |
| {{7}} | `clinic_phone` | "601-555-0100" |

### WhatsApp Button

```
Tipo: URL Button
Texto: "✍ Firmar ahora"
URL: {{sign_consent_url}}
```

---

## In-App Notification (para el Paciente — Portal)

```json
{
  "type": "clinical",
  "title": "Firma de consentimiento requerida",
  "body": "{{doctor_display_name}} requiere tu firma para el consentimiento de '{{procedure_name}}'. Por favor fírmalo antes del {{expiry_date_short}}.",
  "action_url": "/consentimientos/{{consent_id}}/firmar",
  "metadata": {
    "consent_id": "{{consent_id}}",
    "urgency": "high"
  }
}
```

**Color del ícono:** Naranja (`#EA580C`) — tipo `clinical` con urgencia.

---

## Consent Type Display Names

| Tipo interno | Display |
|-------------|---------|
| `general_consent` | "Consentimiento general" |
| `oral_surgery` | "Consentimiento para cirugía oral" |
| `implant` | "Consentimiento para implante dental" |
| `anesthesia` | "Consentimiento para anestesia" |
| `orthodontics` | "Consentimiento para tratamiento de ortodoncia" |
| `whitening` | "Consentimiento para blanqueamiento dental" |
| `extraction` | "Consentimiento para extracción dental" |
| `pediatric` | "Consentimiento pediátrico (padre/tutor)" |
| `custom` | El nombre personalizado del consentimiento |

---

## Sign Consent URL

### URL Structure

```
https://portal.dentalos.io/consentimientos/{{consent_id}}/firmar?token={{access_token}}
```

### Token Properties

| Propiedad | Valor |
|-----------|-------|
| Tipo | JWT firmado |
| Payload | `{ "consent_id": "uuid", "patient_id": "uuid", "tenant_id": "uuid", "type": "consent_sign", "exp": timestamp }` |
| Expiración | Configurable por el doctor al crear el consentimiento (default: 7 días) |
| Revocable | Sí — si el doctor revoca el consentimiento, el token se invalida |

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{doctor_display_name}}` | string | `tenant.users.display_name` | "Dra. Patricia Mora" |
| `{{consent_type_display}}` | string | Tipo convertido a display | "Consentimiento para cirugía oral" |
| `{{procedure_name}}` | string | `tenant.consents.procedure_name` | "cirugía oral" |
| `{{consent_date}}` | string | `consents.created_at` formateado | "25 de febrero de 2026" |
| `{{expiry_datetime}}` | string | `consents.expires_at` formateado con hora | "4 de marzo de 2026 a las 11:59 PM" |
| `{{expiry_date_short}}` | string | `consents.expires_at` solo fecha | "4 de marzo" |
| `{{days_to_expiry}}` | integer | Días hasta expiración | 7 |
| `{{consent_id}}` | uuid | `consents.id` | UUID |
| `{{sign_consent_url}}` | string | Portal URL con token de acceso | URL |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{clinic_phone}}` | string | Tenant settings | "601-555-0100" |
| `{{clinic_contact_email}}` | string | Tenant settings | "citas@smile.com" |
| `{{clinic_logo_url}}` | string | Tenant settings | CDN URL |

---

## Sending Rules

### Timing
- **Envío:** Inmediato — prioridad máxima en la cola (priority: 9).
- **Latencia máxima:** 30 segundos.

### Deduplication
- **Idempotency key:** `consent_signature_requested:{consent_id}`
- **Re-envío:** Si el doctor re-envía la solicitud de firma (endpoint `/resend`), genera nuevo evento con timestamp en la key: `consent_signature_requested:{consent_id}:{resend_timestamp}`.

### Urgencia de Entrega
- Si SendGrid falla, el worker intenta **inmediatamente** con AWS SES como fallback (no espera el retry estándar de 30s). Este es el único caso de fallback inmediato entre proveedores de email.
- Sentry alert si la entrega no se confirma en 5 minutos.

### Sin Unsubscribe
- Consentimientos informados son documentos médicos obligatorios.
- El email no incluye unsubscribe link.
- SendGrid category: `transactional_medical`

### Recordatorio Automático (si no firmado en 48h)
- Si el consentimiento permanece en `pending_signature` por 48 horas, el sistema puede re-enviar la notificación automáticamente.
- Esto es un `consent_reminder` event separado (no especificado en este E-10 — future spec).

---

## Regulatory Compliance Notes

- **Resolución 1888 de 2021:** El consentimiento informado digital es válido para procedimientos odontológicos en Colombia.
- **Ley 527/1999:** Las firmas digitales con certificado o criptografía tienen plena validez jurídica.
- **Audit trail:** Cada acceso al link de firma, visualización del documento y acto de firma deben quedar registrados en el audit log con timestamp e IP.
- El email en sí no es el consentimiento — es la invitación a firmar. El documento legal está en el portal.

---

## Testing

### Test Cases

#### Happy Path
1. Consentimiento de cirugía oral enviado con urgencia
   - **Given:** Consentimiento `oral_surgery` creado; paciente con email y teléfono
   - **When:** `POST /consents/{id}/send`
   - **Then:** Email enviado en < 30s; WhatsApp enviado; in-app en portal; tipo display correcto; botón de firma con token válido

2. Paciente firma el consentimiento
   - **Given:** Email recibido con link de firma
   - **When:** Paciente visita link y firma digitalmente
   - **Then:** `consents.status = 'signed'`; audit log registrado con IP y timestamp; doctor notificado in-app

3. Consentimiento pediátrico
   - **Given:** Consent type `pediatric`; paciente menor de edad, padre/tutor en el sistema
   - **When:** Consentimiento enviado
   - **Then:** Email dirigido al padre/tutor; texto ajustado: "como representante legal de {{minor_name}}"

#### Edge Cases
1. SendGrid falla — fallback a SES inmediato
   - **Given:** SendGrid devuelve 503
   - **When:** Primer intento de envío
   - **Then:** Worker intenta inmediatamente con AWS SES (no espera 30s); entregado en < 1min total

2. Consentimiento expirado
   - **Given:** Paciente intenta firmar después de `expires_at`
   - **When:** Token procesado
   - **Then:** 400 "Este consentimiento ha expirado. Contacta a {{clinic_name}} para obtener uno nuevo."

3. Re-envío de la solicitud de firma
   - **Given:** Doctor re-envía la solicitud; primer email ya entregado
   - **When:** `/consents/{id}/resend` ejecutado
   - **Then:** Nuevo email enviado con nuevo token; token anterior invalidado

4. Doctor sin nombre de procedimiento en el consentimiento
   - **Given:** `procedure_name` es null
   - **When:** Template renderizado
   - **Then:** Usa `consent_type_display` como fallback

#### Error Cases
1. SendGrid Y SES fallan
   - **Given:** Ambos proveedores de email devuelven 5xx
   - **When:** Envío intentado
   - **Then:** Reintento con backoff estándar; DLQ después de 3 intentos; Sentry alert CRÍTICO (consentimiento no entregado)

### Test Data Requirements

- Consentimiento tipo `oral_surgery`, `general_consent`, `pediatric`
- Paciente con email y teléfono
- Entorno con SendGrid sandbox y SES en modo test

### Mocking Strategy

- SendGrid: primera llamada falla (503), segunda a SES exitosa — para test de fallback
- WhatsApp: mock via respx
- Token signing: test key en vars de entorno

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado en < 30s con prioridad máxima
- [ ] Tipo de consentimiento mostrado con display name correcto en español
- [ ] Botón "Firmar consentimiento" con URL y token válido
- [ ] Referencia a Resolución 1888 y Ley 527/1999 incluida en el email
- [ ] WhatsApp enviado con botón de acción directa
- [ ] In-app en portal con urgencia marcada
- [ ] Sin unsubscribe link
- [ ] Fallback inmediato a SES si SendGrid falla
- [ ] Consentimiento pediátrico dirigido al padre/tutor
- [ ] Token de firma expira según configuración del doctor
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- El proceso de firma digital en el portal (spec IC-03)
- Notificación al doctor cuando el paciente firma (spec IC-04)
- Recordatorio automático a las 48h de no firma (future spec)
- Almacenamiento del documento firmado y hash SHA-256 (spec IC-05)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
