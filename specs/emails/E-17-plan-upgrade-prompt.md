# E-17 — Aviso de Límite de Plan y Sugerencia de Actualización

---

## Overview

**Feature:** Notificación enviada al clinic_owner cuando el uso del tenant alcanza el 80% de los límites del plan activo (número de pacientes o número de doctores). Informa el uso actual, qué ocurre al llegar al 100%, y presenta las opciones de plan superior con precios. Máximo 1 notificación por mes por tipo de límite para no saturar al usuario.

**Domain:** tenants / billing / notifications

**Priority:** Medium

**Dependencies:** T-05 (tenant-usage), T-07 (plan-upgrade), B-12 (subscription-billing), N-05

---

## Trigger

**Evento:** `plan_limit_approaching`

**Cuándo se dispara:** Cron job diario (`0 10 * * *` UTC) que verifica el uso de cada tenant activo y dispara el evento si se cumplen las condiciones.

**Condiciones de disparo:**
```python
# Para cada tenant activo:
usage_patients_pct = (patient_count / plan_limit_patients) * 100
usage_doctors_pct = (active_doctors_count / plan_limit_doctors) * 100

if usage_patients_pct >= 80 and not recently_notified(tenant, 'patients', days=30):
    dispatch_event('plan_limit_approaching', limit_type='patients', usage_pct=usage_patients_pct)

if usage_doctors_pct >= 80 and not recently_notified(tenant, 'doctors', days=30):
    dispatch_event('plan_limit_approaching', limit_type='doctors', usage_pct=usage_doctors_pct)
```

**RabbitMQ routing key:** `notification.system.plan_limit_approaching`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Propietario(s) de la clínica | clinic_owner | Siempre |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal principal — información de precios requiere espacio |
| whatsapp | No | No aplica para comunicación de upgrade de plan |
| sms | No | No aplica |
| in-app | Yes | Badge / banner en el panel de control de DentalOS |

---

## Plan Limits Matrix

| Plan | Doctores | Pacientes |
|------|----------|-----------|
| Free | 1 | 50 |
| Starter | Por doctor (ilimitados) | 500 |
| Pro | Por doctor (ilimitados) | 2.000 |
| Clínica | 3 incluidos | Ilimitados |
| Enterprise | Custom | Ilimitados |

**Nota:** Para el plan Starter y Pro, el límite es por número de pacientes registrados activos. Los planes Clínica y Enterprise no tienen límite de pacientes — nunca disparan este evento para pacientes.

---

## Email Templates por Tipo de Límite

### Template A — Límite de Pacientes (80%+ alcanzado)

**Subject:**
```
Has usado el {{usage_pct}}% de tus pacientes en {{clinic_name}} — considera actualizar tu plan
```

**Ejemplo:** "Has usado el 84% de tus pacientes en Clínica Smile — considera actualizar tu plan"

### Template B — Límite de Doctores (80%+ alcanzado)

**Subject:**
```
Límite de doctores al {{usage_pct}}% en {{clinic_name}} — opciones para crecer tu equipo
```

---

## HTML Structure (Común con variaciones por tipo)

```
[HEADER]
  - Logo de la clínica
  - Nombre de la clínica

[HERO — Fondo amarillo claro, ícono de medidor / gauge]
  - Ícono: 📊 (medidor de uso)
  - Título H1: "Tu plan está casi al límite"
  - Subtítulo: "Hola {{owner_first_name}}, tu clínica ha crecido y se acerca al límite de tu plan actual."

[BARRA DE USO — Visual]
  Encabezado: "Uso actual: {{limit_type_display}}"

  Barra de progreso visual (HTML/CSS):
  ████████████░░ {{usage_pct}}%
  Texto: "{{current_usage}} de {{plan_limit}} {{unit_display}} ({{usage_pct}}%)"

  Si usage_pct >= 90:
  Alerta roja: "⚠ Estás muy cerca del límite. Actúa pronto para no perder funcionalidad."
  Si usage_pct >= 80:
  Alerta amarilla: "Tienes espacio para {{remaining_count}} {{unit_display}} más antes de alcanzar el límite."

[QUÉ PASA AL LLEGAR AL 100%]
  Card con borde rojo claro:
  Título: "¿Qué pasa si llegas al límite?"

  Para límite de pacientes:
  "• No podrás registrar nuevos pacientes.
   • Los pacientes existentes permanecen sin cambios.
   • Para registrar nuevos pacientes, necesitarás actualizar tu plan."

  Para límite de doctores:
  "• No podrás agregar más doctores al equipo.
   • Los doctores actuales siguen activos.
   • Para agregar más doctores, actualiza tu plan."

[OPCIONES DE PLAN — Cards de upgrade]
  Título: "Opciones para seguir creciendo"

  Muestra 2-3 planes superiores al plan actual, en cards comparativas:

  [Si plan actual = Free]
    Card 1: Plan Starter — $19/doctor/mes
    - Hasta 500 pacientes
    - Expedientes clínicos completos
    - Facturación básica
    [Botón: "Elegir Starter"]

    Card 2: Plan Pro — $39/doctor/mes (RECOMENDADO badge)
    - Hasta 2.000 pacientes
    - Todas las funciones + IA voice add-on disponible
    - Reportes RIPS
    [Botón: "Elegir Pro"]

  [Si plan actual = Starter]
    Card 1: Plan Pro — $39/doctor/mes (RECOMENDADO badge)
    - Hasta 2.000 pacientes
    - ...beneficios adicionales...
    [Botón: "Actualizar a Pro"]

    Card 2: Plan Clínica — $69/ubicación/mes
    - Pacientes ilimitados
    - 3 doctores incluidos
    - Multi-ubicación
    [Botón: "Ver Plan Clínica"]

  [Si plan actual = Pro]
    Card 1: Plan Clínica — $69/ubicación/mes
    - Pacientes ilimitados
    ...
    [Botón: "Actualizar a Clínica"]

    Card 2: Plan Enterprise — Precio personalizado
    - Todo ilimitado + soporte dedicado
    [Botón: "Contactar ventas"]

[CTA PRINCIPAL]
  Botón azul grande: "Ver todos los planes"
  URL: {{pricing_page_url}}

[NOTA DE FACTURACIÓN]
  "Al actualizar, se prorratea el cargo por el tiempo restante de tu ciclo de facturación actual.
  No se pierde ningún dato al cambiar de plan."

[FOOTER]
  - Logo DentalOS
  - Unsubscribe: "No recibir más avisos de límite" → {{notification_preferences_url}}
  - Política de privacidad
```

---

## In-App Notification (Panel de Control)

```json
{
  "type": "system",
  "title": "Plan casi al límite",
  "body": "Has usado el {{usage_pct}}% de {{limit_type_display}} en tu plan {{plan_name}}. Actualiza para seguir creciendo.",
  "action_url": "/settings/subscription",
  "metadata": {
    "limit_type": "{{limit_type}}",
    "usage_pct": "{{usage_pct}}",
    "plan_name": "{{plan_name}}"
  }
}
```

**Color del ícono:** Amarillo/naranja (`#F59E0B`) — tipo `system` con advertencia.

**Persistencia del in-app:** Este banner in-app debe mostrarse hasta que:
1. El usuario hace clic en "Ver planes" (lo descarta conscientemente)
2. El plan es actualizado (el uso cae por debajo del 80%)
3. El usuario descarta el banner manualmente

---

## Limit Type Display Names

| Tipo interno | Display singular | Display plural | Unidad |
|-------------|-----------------|----------------|--------|
| `patients` | "paciente" | "pacientes" | "pacientes" |
| `doctors` | "doctor" | "doctores" | "doctores" |

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{owner_first_name}}` | string | `public.users.first_name` | "Carlos" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{plan_name}}` | string | `public.tenants.plan` display | "Plan Starter" |
| `{{limit_type}}` | string | `patients` o `doctors` | "patients" |
| `{{limit_type_display}}` | string | Display nombre del límite | "pacientes" |
| `{{current_usage}}` | integer | Uso actual | 42 |
| `{{plan_limit}}` | integer | Límite del plan | 50 |
| `{{usage_pct}}` | integer | Porcentaje redondeado | 84 |
| `{{remaining_count}}` | integer | `plan_limit - current_usage` | 8 |
| `{{unit_display}}` | string | "pacientes" o "doctores" | "pacientes" |
| `{{upgrade_plans}}` | list | Plans superiores al actual (2-3 planes) | Array de plan objects |
| `{{pricing_page_url}}` | string | `{app_url}/pricing` | URL |
| `{{upgrade_url}}` | string | `{app_url}/settings/subscription?upgrade=true` | URL |
| `{{notification_preferences_url}}` | string | Preferencias de notificación | URL |

---

## Sending Rules

### Timing
- **Cron:** Diario a las 10 AM UTC. Calcula usage en el momento de ejecución.
- **Prioridad:** Medium (priority: 5).

### Rate Limiting (Máx 1 por mes por tipo)
- **Flag de control:** Tabla `public.plan_limit_notifications` con:
  ```sql
  CREATE TABLE public.plan_limit_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    limit_type VARCHAR(32) NOT NULL,  -- 'patients' | 'doctors'
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    usage_pct INTEGER NOT NULL
  );
  ```
- **Consulta de deduplication:**
  ```sql
  SELECT COUNT(*) > 0
  FROM public.plan_limit_notifications
  WHERE tenant_id = :tenant_id
    AND limit_type = :limit_type
    AND sent_at > NOW() - INTERVAL '30 days'
  ```
- Si existe un registro en los últimos 30 días para este tenant y tipo de límite: NO enviar.

### Umbrales Escalonados
- **80%:** Primera alerta — tono informativo ("casi al límite")
- **90%:** Si no ha habido alerta reciente (> 7 días), segunda alerta con tono más urgente
- **100%:** Alerta inmediata (sin esperar el cron diario) — el evento se dispara en tiempo real cuando se alcanza el límite exacto

### Condición de No-Envío
- Plan Enterprise o Clínica para límite de pacientes: nunca enviar (sin límite de pacientes)
- Plan Free para doctores: sin límite de doctores (solo 1 doctor incluido — no aplica % de uso como tal)

---

## Testing

### Test Cases

#### Happy Path
1. 80% de pacientes alcanzado — Plan Starter
   - **Given:** Tenant en plan Starter; 401 pacientes de 500 (80.2%)
   - **When:** Cron ejecuta; no hay notificación previa en 30 días
   - **Then:** Email enviado al clinic_owner con barra de uso al 80%; opciones de Pro y Clínica mostradas; in-app con alerta amarilla

2. 90% de pacientes — segunda alerta (si pasaron 10 días)
   - **Given:** Primera alerta enviada hace 10 días (>7d); ahora al 90%
   - **When:** Cron ejecuta
   - **Then:** Segunda alerta enviada con tono más urgente; alerta roja en barra de uso

3. Límite de doctores al 80% — Plan Clínica (2 de 3 doctores)
   - **Given:** Plan Clínica con 3 doctores incluidos; 2 activos (66.7%) → NO aplica
   - **Given:** Alternativo: Plan Enterprise agregado con 10 doctores incluidos; 8 activos (80%)
   - **When:** Cron ejecuta
   - **Then:** Alerta de límite de doctores enviada con opciones de upgrade

#### Edge Cases
1. Alerta ya enviada hace 15 días (dentro del período de 30d)
   - **Given:** Notificación de pacientes enviada hace 15 días; uso sigue al 82%
   - **When:** Cron ejecuta
   - **Then:** Notificación NOT enviada; log `skipped (notified_15_days_ago)`

2. Plan actualizado después de la primera alerta (uso cae)
   - **Given:** Alerta enviada; clinic_owner actualiza a Plan Pro; uso cae al 21%
   - **When:** Cron ejecuta
   - **Then:** No hay nueva alerta; `remaining_count` grande; in-app banner desaparece

3. Tenants en planes Enterprise
   - **Given:** Tenant en Plan Enterprise
   - **When:** Cron ejecuta
   - **Then:** Tenants Enterprise excluidos completamente del cron; sin alertas

4. Plan Free con límite de 50 pacientes — 40 registrados (80%)
   - **Given:** Tenant Free; 40 pacientes
   - **When:** Cron ejecuta
   - **Then:** Email con barra al 80%; muestra opciones Starter y Pro claramente; solo 10 pacientes restantes

#### Error Cases
1. Consulta de uso falla (DB timeout)
   - **Given:** Query de COUNT pacientes hace timeout
   - **When:** Cron intenta calcular usage
   - **Then:** Tenant skipped para ese cron run; log error; retry en próxima ejecución del cron (siguiente día)

### Test Data Requirements

- Tenant Free con 40 pacientes (80% de 50)
- Tenant Starter con 410 pacientes (82% de 500)
- Tabla `plan_limit_notifications` con y sin registros recientes

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Cron diario calcula usage_pct correctamente para cada tenant
- [ ] Email enviado cuando usage_pct >= 80% y no hay alerta en últimos 30 días
- [ ] Barra de progreso visual en el email
- [ ] Planes superiores mostrados con precios correctos (según plan actual)
- [ ] In-app banner persiste hasta descarte o upgrade
- [ ] Rate limit: máx 1 alerta por tipo por 30 días
- [ ] Tenants Enterprise excluidos del cron de límite de pacientes
- [ ] Tono escala: 80% informativo, 90% urgente
- [ ] Todos los test cases pasan

---

## Out of Scope

- El proceso de upgrade en sí (spec T-07)
- Bloqueo funcional al llegar al 100% (spec T-08)
- Alertas de uso para add-ons (Voice AI, Radiograph AI)
- Facturación proporcional al actualizar (spec B-12)

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
