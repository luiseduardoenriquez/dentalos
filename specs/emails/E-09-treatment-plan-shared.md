# E-09 — Plan de Tratamiento Compartido con Paciente

---

## Overview

**Feature:** Notificación enviada al paciente cuando el doctor comparte su plan de tratamiento para revisión y aprobación. Incluye resumen del plan (número de procedimientos, costo estimado total) y un link al portal del paciente donde puede ver el detalle completo, hacer preguntas y dar su aprobación. Canal multi: email + WhatsApp + in-app.

**Domain:** treatment-plans / notifications

**Priority:** High

**Dependencies:** TP-05 (treatment-plan-share), P-14 (patient-portal), N-04, N-05, E-10 (consent-request)

---

## Trigger

**Evento:** `treatment_plan_shared`

**Cuándo se dispara:** Al ejecutar `POST /api/v1/treatment-plans/{id}/share` con éxito. El plan pasa de estado `draft` a `shared_with_patient`.

**RabbitMQ routing key:** `notification.clinical.treatment_plan_shared`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Paciente del plan | patient | Siempre |
| Doctor que creó el plan | doctor | In-app para confirmar que fue compartido (opcional, baja prioridad) |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal para contenido detallado del plan |
| whatsapp | Yes | Resumen corto con link al portal |
| sms | No | Plan de tratamiento requiere contexto; SMS insuficiente |
| in-app | Yes | Para el paciente via portal web de pacientes |

---

## Email Template

### Subject Line

```
Tu plan de tratamiento está listo — {{clinic_name}}
```

### Preheader

```
{{doctor_display_name}} preparó un plan de tratamiento para ti. Revísalo y da tu aprobación.
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica
  - Color primario de la clínica

[HERO — Fondo azul/morado claro, ícono de portapapeles médico]
  - Ícono: 📋
  - Título H1: "Tu plan de tratamiento está listo"
  - Subtítulo: "Hola {{patient_first_name}}, {{doctor_display_name}} preparó un plan personalizado para ti."

[RESUMEN DEL PLAN — Card prominente]
  Encabezado: "{{plan_title}}"
  Información:
  - 👨‍⚕️ Preparado por: {{doctor_display_name}}
  - 📅 Fecha: {{plan_date}}
  - 🦷 Procedimientos: {{procedure_count}} procedimientos
  - 💰 Costo estimado: {{estimated_total_display}}
  - ⏱ Duración estimada: {{estimated_duration_display}}

[PROCEDIMIENTOS — Lista de las primeras 3-5 etapas]
  Título: "Resumen de procedimientos:"
  Lista numerada (máximo 5 items):
  1. {{procedure_1_name}} — {{procedure_1_sessions}} sesión(es)
  2. {{procedure_2_name}} — {{procedure_2_sessions}} sesión(es)
  3. {{procedure_3_name}} — {{procedure_3_sessions}} sesión(es)
  [Si hay más]: "+ {{remaining_count}} procedimientos adicionales"

[NOTA DEL DOCTOR — Solo si plan tiene notes != null]
  Card con borde izquierdo morado, ícono de nota:
  Título: "Nota de {{doctor_display_name}}:"
  Texto: "{{doctor_notes}}"

[CTA PRINCIPAL]
  Párrafo: "Revisa el plan completo en tu portal de paciente."
  Botón morado/azul: "Ver plan de tratamiento"
  URL: {{patient_portal_plan_url}}

[INFORMACIÓN SOBRE EL PORTAL]
  Título: "¿Qué puedes hacer en tu portal?"
  Bullets:
  • Ver el detalle completo de cada procedimiento
  • Hacer preguntas directamente al equipo
  • Aprobar o solicitar cambios al plan
  • Ver el desglose de costos y opciones de pago

[INFORMACIÓN DE CONTACTO]
  "¿Tienes preguntas sobre tu tratamiento?"
  - Llámanos: {{clinic_phone}}
  - Escríbenos: {{clinic_contact_email}}

[FOOTER]
  - Logo DentalOS
  - Unsubscribe gestionar preferencias
  - Política de privacidad
```

### CTA Button

```
Texto: "Ver plan de tratamiento"
URL: {{patient_portal_plan_url}}
Color: #7C3AED (morado — dominio clínico)
Texto: blanco, bold
```

### Plain-text Fallback

```
Tu plan de tratamiento está listo — {{clinic_name}}

Hola {{patient_first_name}},

{{doctor_display_name}} preparó un plan de tratamiento para ti:

Plan: {{plan_title}}
Procedimientos: {{procedure_count}}
Costo estimado: {{estimated_total_display}}
Duración estimada: {{estimated_duration_display}}

Para ver el plan completo y aprobarlo:
{{patient_portal_plan_url}}

¿Preguntas? Llámanos: {{clinic_phone}}

© {{clinic_name}} | Gestionado por DentalOS
```

---

## WhatsApp Template

### Nombre del template Meta

```
dentalos_treatment_plan_shared_v1
```

### Categoría Meta

```
UTILITY
```

### Template Text

```
Hola {{1}}, {{2}} preparó tu plan de tratamiento en {{3}}.

Incluye {{4}} procedimiento(s) con un costo estimado de {{5}}.

Revisa y aprueba tu plan en: {{6}}
```

### Variables

| # | Variable | Ejemplo |
|---|----------|---------|
| {{1}} | `patient_first_name` | "Ana" |
| {{2}} | `doctor_display_name` | "Dra. Patricia Mora" |
| {{3}} | `clinic_name` | "Clínica Smile" |
| {{4}} | `procedure_count` | "5" |
| {{5}} | `estimated_total_display` | "$2,500,000 COP" |
| {{6}} | `patient_portal_plan_url` | "https://portal.dentalos.io/plan/abc123" |

### WhatsApp Button

```
Tipo: URL Button
Texto: "Ver mi plan"
URL: {{patient_portal_plan_url}}
```

---

## In-App Notification (para el Paciente — Portal)

```json
{
  "type": "clinical",
  "title": "Plan de tratamiento disponible",
  "body": "{{doctor_display_name}} compartió tu plan de tratamiento '{{plan_title}}'. Revísalo y responde.",
  "action_url": "/plan/{{plan_id}}",
  "metadata": {
    "plan_id": "{{plan_id}}",
    "doctor_id": "{{doctor_id}}"
  }
}
```

**Color del ícono:** Morado (`#7C3AED`) — tipo `clinical`

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{patient_first_name}}` | string | `tenant.patients.first_name` | "Ana" |
| `{{doctor_display_name}}` | string | `tenant.users.display_name` | "Dra. Patricia Mora" |
| `{{plan_title}}` | string | `tenant.treatment_plans.title` | "Plan rehabilitación oral completa" |
| `{{plan_date}}` | string | `treatment_plans.created_at` formateado | "25 de febrero de 2026" |
| `{{plan_id}}` | uuid | `treatment_plans.id` | UUID |
| `{{procedure_count}}` | integer | COUNT de `treatment_plan_items` | 5 |
| `{{estimated_total_display}}` | string | SUM de costos formateado en COP | "$2.500.000 COP" |
| `{{estimated_duration_display}}` | string | Calculado de sesiones | "3-4 semanas" |
| `{{procedure_1_name}}` hasta `{{procedure_5_name}}` | string | `treatment_plan_items[i].procedure_name` | "Extracción molar" |
| `{{procedure_1_sessions}}` hasta `{{procedure_5_sessions}}` | integer | `treatment_plan_items[i].sessions` | 1 |
| `{{remaining_count}}` | integer | `procedure_count - 5` (si > 5) | 3 |
| `{{doctor_notes}}` | string / null | `treatment_plans.notes` | "Recomiendo comenzar lo antes posible" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{clinic_phone}}` | string | Tenant settings | "601-555-0100" |
| `{{clinic_contact_email}}` | string | Tenant settings | "citas@smile.com" |
| `{{clinic_logo_url}}` | string | Tenant settings | CDN URL |
| `{{patient_portal_plan_url}}` | string | `{portal_url}/plan/{plan_id}?token={access_token}` | URL |

---

## Sending Rules

### Timing
- **Envío:** Inmediato al compartir el plan.
- **Prioridad:** High (priority: 7).

### Deduplication
- **Idempotency key:** `treatment_plan_shared:{plan_id}`
- Si el doctor vuelve a compartir el mismo plan (re-share), se genera un nuevo evento con nuevo idempotency key basado en `{plan_id}:{shared_at_timestamp}`.

### Opt-out
- Respeta preferencias de notificación del paciente para tipo `clinical`.
- Sin embargo, los planes de tratamiento son altamente relevantes — se recomienda no desactivarlos.

---

## Testing

### Test Cases

#### Happy Path
1. Plan compartido con 5 procedimientos
   - **Given:** Plan con 5 ítems, costo total $2.5M COP, doctor con notas
   - **When:** `POST /treatment-plans/{id}/share`
   - **Then:** Email con lista de procedimientos y nota del doctor; WhatsApp con resumen; in-app en portal del paciente

2. Plan con más de 5 procedimientos
   - **Given:** Plan con 8 procedimientos
   - **When:** Template renderizado
   - **Then:** Email muestra 5 primeros + "3 procedimientos adicionales"

3. Plan sin notas del doctor
   - **Given:** Plan sin campo `notes`
   - **When:** Template renderizado
   - **Then:** Sección de nota del doctor omitida en el email

#### Edge Cases
1. Re-share del mismo plan
   - **Given:** Doctor ya compartió el plan; lo vuelve a compartir (quizás actualizó algo)
   - **When:** Segundo share event
   - **Then:** Nuevo email enviado con los datos actualizados; idempotency key diferente

2. Plan con un solo procedimiento
   - **Given:** Plan con 1 ítem
   - **When:** Template renderizado
   - **Then:** "1 procedimiento" (singular correcto en español); lista muestra solo ese ítem

3. Costo estimado muy alto
   - **Given:** Plan total = $25.000.000 COP
   - **When:** Template renderizado
   - **Then:** Formato correcto con separadores de miles en COP

#### Error Cases
1. Plan_id no encontrado
   - **Given:** plan_id en el evento no existe en la DB
   - **When:** Worker intenta cargar el plan
   - **Then:** Fallo permanente; DLQ; Sentry alert

### Test Data Requirements

- Plan con 3, 5, y 8 procedimientos
- Plan con y sin notas del doctor
- Paciente con email y teléfono; con solo email

### Mocking Strategy

- Standard: SendGrid sandbox, WhatsApp mock, RabbitMQ Docker

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Email enviado con lista de procedimientos (máx 5 + "más adicionales")
- [ ] Costo total formateado correctamente en COP
- [ ] Nota del doctor incluida si existe; omitida si no
- [ ] WhatsApp con resumen y botón al portal
- [ ] In-app en portal del paciente con tipo `clinical` (morado)
- [ ] Link al portal con access token incluido
- [ ] Re-share genera nuevo envío correctamente
- [ ] Todos los test cases pasan

---

## Out of Scope

**Este spec NO cubre:**

- El endpoint de compartir el plan (spec TP-05)
- Aprobación del plan por el paciente (spec TP-06)
- Solicitud de consentimiento (spec E-10 — puede acompañar al plan)
- Seguimiento de si el paciente vio el plan

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
