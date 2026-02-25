# E-16 — Resumen Diario de Clínica

---

## Overview

**Feature:** Resumen diario enviado al clinic_owner con un panorama completo del día: citas del día, pacientes nuevos de ayer, ingresos del día anterior, saldos pendientes, facturas vencidas, y alertas de inventario. Informativo — no requiere acción inmediata. Se envía a las 7:00 AM en el timezone de la clínica para que el propietario empiece el día informado.

**Domain:** analytics / notifications / admin

**Priority:** Medium

**Dependencies:** AP-01 (appointments), B-01 (invoices), B-08 (payments), inventory specs, N-05, analytics/dashboard

---

## Trigger

**Evento:** `daily_clinic_summary`

**Cuándo se dispara:** Cron job diario a las 7:00 AM en el timezone del tenant. El cron global (UTC) itera sobre todos los tenants activos y determina cuáles están en sus 7:00 AM local.

**Cron schedule:** `0 7 * * *` ejecutado por timezone, o cron UTC que calcula cuáles tenants están a las 7 AM local.

**Lógica de timezone del cron:**
```python
# Para cada tenant activo:
tenant_tz = pytz.timezone(tenant.settings.timezone)
now_local = datetime.now(tenant_tz)
if now_local.hour == 7 and now_local.minute < 15:  # ventana de 15 min
    dispatch_summary(tenant)
    mark_summary_sent(tenant, date=today)
```

**RabbitMQ routing key:** `notification.system.daily_clinic_summary`

---

## Recipients

| Recipient | Role | Condition |
|-----------|------|-----------|
| Propietario(s) de la clínica | clinic_owner | Siempre — todos los clinic_owners del tenant |
| (Opcional) Administrador delegado | Cualquier rol con `reports:view` | Si el clinic_owner lo configuró |

---

## Channels

| Channel | Enabled | Notes |
|---------|---------|-------|
| email | Yes | Canal único — resumen es largo y tabular |
| whatsapp | No | Contenido es demasiado denso para WhatsApp |
| sms | No | No aplica |
| in-app | No | Este resumen es para el día fuera de la plataforma; se asume que el owner usa el email por las mañanas |

---

## Datos del Resumen

Los datos se calculan al momento de generar el resumen (no son caché):

### Sección 1: Citas de Hoy

```sql
SELECT
  COUNT(*) FILTER (WHERE status IN ('confirmed', 'pending')) as total_today,
  COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed,
  COUNT(*) FILTER (WHERE status = 'pending') as pending,
  COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled_today
FROM appointments
WHERE DATE(start_at AT TIME ZONE tenant_tz) = TODAY
  AND deleted_at IS NULL
```

Lista de primeras 10 citas del día: hora, paciente, doctor, tipo.

### Sección 2: Pacientes Nuevos (Ayer)

```sql
SELECT COUNT(*) as new_patients_yesterday
FROM patients
WHERE DATE(created_at AT TIME ZONE tenant_tz) = YESTERDAY
  AND deleted_at IS NULL
```

### Sección 3: Ingresos de Ayer

```sql
SELECT
  COALESCE(SUM(amount), 0) as revenue_yesterday,
  COUNT(*) as payments_count,
  SUM(amount) FILTER (WHERE method = 'cash') as cash_amount,
  SUM(amount) FILTER (WHERE method IN ('credit_card', 'debit_card')) as card_amount,
  SUM(amount) FILTER (WHERE method = 'pse') as pse_amount
FROM payments
WHERE DATE(paid_at AT TIME ZONE tenant_tz) = YESTERDAY
```

### Sección 4: Saldos Pendientes

```sql
SELECT
  COALESCE(SUM(total_amount - COALESCE(total_paid, 0)), 0) as outstanding_balance,
  COUNT(*) as pending_invoice_count,
  COUNT(*) FILTER (WHERE due_date < CURRENT_DATE) as overdue_count
FROM invoices
WHERE status IN ('sent', 'partial')
  AND deleted_at IS NULL
```

### Sección 5: Alertas de Inventario

```sql
SELECT
  COUNT(*) FILTER (WHERE expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days') as expiring_soon,
  COUNT(*) FILTER (WHERE expiry_date < CURRENT_DATE) as expired,
  COUNT(*) FILTER (WHERE quantity <= min_stock_level) as low_stock
FROM inventory_items
WHERE deleted_at IS NULL
```

---

## Email Template

### Subject Line

```
Resumen del día — {{today_date}} | {{appointments_today}} citas hoy | {{clinic_name}}
```

**Ejemplo:** "Resumen del día — Miércoles 25 Feb | 8 citas hoy | Clínica Smile"

### Preheader

```
Ingresos ayer: ${{revenue_yesterday_display}} | Saldo pendiente: ${{outstanding_balance_display}} | {{overdue_count}} facturas vencidas
```

### HTML Structure

```
[HEADER]
  - Logo de la clínica
  - "Resumen del día — {{today_date_full}}"

[SALUDO]
  "Buenos días, {{owner_first_name}}. Aquí está el resumen de {{clinic_name}}."

═══════════════════════════════════════════
[SECCIÓN 1: CITAS DE HOY]
══════════════════════════════════════════

  Encabezado: "📅 Citas de hoy ({{today_date_short}})"

  Resumen numérico — 4 tarjetas horizontales:
  | Total  | Confirmadas | Pendientes | Canceladas |
  | {{total_appointments_today}} | {{confirmed_count}} | {{pending_count}} | {{cancelled_today}} |

  Tabla de citas (primeras 10):
  | Hora    | Paciente        | Doctor          | Tipo           |
  |---------|-----------------|-----------------|----------------|
  | 8:00 AM | Ana Gómez       | Dra. P. Mora    | Consulta gral. |
  | 9:30 AM | Carlos Mendoza  | Dr. J. López    | Limpieza       |
  ... (hasta 10)

  Si hay más de 10: "+ X citas más. Ver agenda completa →" con link

═══════════════════════════════════════════
[SECCIÓN 2: NUEVOS PACIENTES (AYER)]
══════════════════════════════════════════

  "👥 Nuevos pacientes ayer: {{new_patients_yesterday}}"

  Si > 0: Lista de nombres de los primeros 5 pacientes nuevos
  Si = 0: "No se registraron nuevos pacientes ayer."

═══════════════════════════════════════════
[SECCIÓN 3: INGRESOS DE AYER]
══════════════════════════════════════════

  "💰 Ingresos del {{yesterday_date_short}}"

  Total destacado: "${{revenue_yesterday_display}}"
  Sub-desglose:
  - Efectivo: ${{cash_amount_display}}
  - Tarjeta: ${{card_amount_display}}
  - PSE / Online: ${{pse_amount_display}}
  - Número de pagos: {{payments_count_yesterday}} transacciones

═══════════════════════════════════════════
[SECCIÓN 4: ESTADO DE FACTURACIÓN]
══════════════════════════════════════════

  "🧾 Saldos pendientes"

  Tabla de métricas:
  | Saldo total pendiente | ${{outstanding_balance_display}} |
  | Facturas activas      | {{pending_invoice_count}} |
  | Facturas vencidas     | {{overdue_count}} 🔴 (si > 0) |
  | Facturas vencidas > 30d | {{overdue_30d_count}} ⚠️ |

  Si overdue_count > 0:
  Alert box rojo suave: "Tienes {{overdue_count}} factura(s) vencida(s). Revísalas en DentalOS."
  Link: "Ver facturas vencidas →"

═══════════════════════════════════════════
[SECCIÓN 5: INVENTARIO — Solo si hay alertas]
══════════════════════════════════════════

  "📦 Alertas de inventario"
  (Esta sección solo aparece si hay alertas; si no hay, se omite)

  Alertas:
  - 🔴 Expirados: {{expired_items_count}} producto(s)
  - 🟡 Por expirar (30 días): {{expiring_soon_count}} producto(s)
  - 🟠 Stock bajo: {{low_stock_count}} producto(s)

  Lista de primeros 5 ítems con alerta:
  | Producto       | Estado     | Cantidad / Vence |
  |----------------|------------|-----------------|
  | Anestesia XL   | EXPIRADO   | Venció 20/01/26  |
  | Guantes M (100)| STOCK BAJO | 5 unidades       |

  Link: "Ver inventario completo →"

═══════════════════════════════════════════
[LINKS RÁPIDOS]
══════════════════════════════════════════

  "Accesos rápidos:"
  - Ver agenda de hoy →
  - Ver facturas vencidas →
  - Ver reportes financieros →
  - Ir al panel de control →

[FOOTER]
  - Logo DentalOS
  - "Este resumen se envía automáticamente cada día a las 7:00 AM."
  - Unsubscribe: "Dejar de recibir resúmenes diarios" → {{notification_preferences_url}}
  - Política de privacidad
```

### Plain-text Fallback

```
Resumen del día — {{today_date_full}} | {{clinic_name}}

Buenos días, {{owner_first_name}}.

CITAS DE HOY ({{total_appointments_today}}):
Confirmadas: {{confirmed_count}} | Pendientes: {{pending_count}} | Canceladas: {{cancelled_today}}
Ver agenda: {{app_url}}/agenda

NUEVOS PACIENTES AYER: {{new_patients_yesterday}}

INGRESOS AYER: ${{revenue_yesterday_display}}
- Efectivo: ${{cash_amount_display}}
- Tarjeta: ${{card_amount_display}}
- Online: ${{pse_amount_display}}

SALDOS PENDIENTES: ${{outstanding_balance_display}}
Facturas vencidas: {{overdue_count}}

{{#if inventory_alerts}}
ALERTAS DE INVENTARIO:
Expirados: {{expired_items_count}} | Por expirar: {{expiring_soon_count}} | Stock bajo: {{low_stock_count}}
{{/if}}

Panel de control: {{app_url}}/dashboard

Para dejar de recibir resúmenes: {{notification_preferences_url}}
© {{clinic_name}} | DentalOS
```

---

## Placeholders / Variables

| Variable | Tipo | Fuente | Ejemplo |
|----------|------|--------|---------|
| `{{owner_first_name}}` | string | `public.users.first_name` del clinic_owner | "Carlos" |
| `{{clinic_name}}` | string | `public.tenants.name` | "Clínica Smile" |
| `{{today_date_full}}` | string | Fecha de hoy en timezone del tenant | "Miércoles, 25 de febrero de 2026" |
| `{{today_date_short}}` | string | Fecha corta | "25 de febrero" |
| `{{yesterday_date_short}}` | string | Fecha de ayer | "24 de febrero" |
| `{{total_appointments_today}}` | integer | Query citas de hoy | 8 |
| `{{confirmed_count}}` | integer | Citas confirmadas hoy | 6 |
| `{{pending_count}}` | integer | Citas pendientes hoy | 2 |
| `{{cancelled_today}}` | integer | Citas canceladas hoy | 1 |
| `{{appointments_list}}` | list | Primeras 10 citas del día | Array |
| `{{new_patients_yesterday}}` | integer | Nuevos pacientes ayer | 3 |
| `{{revenue_yesterday_display}}` | string | Ingresos ayer formateados | "$1.250.000" |
| `{{payments_count_yesterday}}` | integer | Número de pagos ayer | 7 |
| `{{cash_amount_display}}` | string | Efectivo | "$800.000" |
| `{{card_amount_display}}` | string | Tarjeta | "$350.000" |
| `{{pse_amount_display}}` | string | PSE/Online | "$100.000" |
| `{{outstanding_balance_display}}` | string | Saldo total pendiente | "$3.500.000" |
| `{{pending_invoice_count}}` | integer | Facturas activas | 12 |
| `{{overdue_count}}` | integer | Facturas vencidas | 3 |
| `{{overdue_30d_count}}` | integer | Facturas con > 30d mora | 1 |
| `{{expired_items_count}}` | integer | Ítems de inventario expirados | 2 |
| `{{expiring_soon_count}}` | integer | Por expirar en 30 días | 5 |
| `{{low_stock_count}}` | integer | Stock bajo | 3 |
| `{{has_inventory_alerts}}` | boolean | Alguna alerta de inventario | true |
| `{{app_url}}` | string | URL de la app | "https://app.dentalos.io" |
| `{{notification_preferences_url}}` | string | URL preferencias | URL |

---

## Sending Rules

### Timing
- **Hora de envío:** 7:00 AM en el timezone del tenant (tolerancia ±15 minutos).
- **No enviar en:** Domingos ni festivos (configurable por tenant — default: enviar siempre).
- **Si no hay datos:** El resumen se envía igual, con valores en 0 o mensajes de "Sin actividad ayer".

### Deduplication
- **Flag en DB:** `public.tenants.last_daily_summary_sent` (DATE) — no enviar dos veces el mismo día.
- **Redis key:** `daily_summary:sent:{tenant_id}:{date}` con TTL 25 horas.

### Fallback si el cron falla
- Si el cron no ejecutó a las 7 AM (por caída del sistema), al recuperarse ejecuta para todos los tenants que no recibieron el resumen del día.
- Ventana de recuperación: hasta las 10 AM hora local del tenant. Después de eso, el resumen del día se omite.

### Opt-out
- El clinic_owner puede desactivar el resumen diario desde preferencias.
- Toggle específico: `daily_summary.email` en las preferencias de notificación (sección admin).

---

## Testing

### Test Cases

#### Happy Path
1. Resumen con datos completos
   - **Given:** Tenant con citas, pagos, nuevos pacientes, alertas de inventario
   - **When:** Cron ejecuta a las 7 AM local
   - **Then:** Email enviado al clinic_owner con todas las secciones completadas y datos correctos

2. Sección de inventario omitida cuando no hay alertas
   - **Given:** Sin ítems expirados, por expirar, o con stock bajo
   - **When:** Resumen generado
   - **Then:** Sección "Alertas de inventario" completamente omitida del email

3. Resumen en día sin actividad
   - **Given:** Día sin citas, sin pagos, sin nuevos pacientes
   - **When:** Cron ejecuta
   - **Then:** Email enviado con valores en 0; secciones muestran "Sin actividad" claramente; sin errores

4. Clínica con múltiples clinic_owners
   - **Given:** Tenant con 2 clinic_owners
   - **When:** Resumen enviado
   - **Then:** Email enviado a ambos owners; datos idénticos; in-app no enviado

#### Edge Cases
1. Timezone edge: clínica en UTC-5 (Colombia) — cron global en UTC
   - **Given:** Tenant timezone = `America/Bogota` (UTC-5); son las 7 AM local = 12 PM UTC
   - **When:** Cron UTC ejecuta a las 12:00 UTC
   - **Then:** Resumen enviado correctamente al clinic_owner

2. Cron ejecutó dos veces en el mismo día (bug/restart)
   - **Given:** `daily_summary:sent:{tenant_id}:{today}` en Redis
   - **When:** Segundo cron run
   - **Then:** Resumen NOT reenviado; log `skipped (already_sent_today)`

3. Más de 10 citas en el día
   - **Given:** 25 citas para hoy
   - **When:** Resumen generado
   - **Then:** Lista muestra las 10 primeras; "15 citas más" con link a la agenda

#### Error Cases
1. Fallo de query de DB durante generación
   - **Given:** DB timeout en query de ingresos
   - **When:** Generación del resumen
   - **Then:** Sección de ingresos muestra "No disponible en este momento"; resto del email enviado; Sentry warning

### Test Data Requirements

- Tenant con timezone Colombia
- Appointments para hoy (10+ para probar límite)
- Pagos de ayer con diferentes métodos
- Inventario con ítems en diferentes estados de alerta

---

## Acceptance Criteria

**Esta feature es completa cuando:**

- [ ] Cron ejecuta a las 7 AM en timezone de CADA tenant (no UTC fijo)
- [ ] Email enviado al/los clinic_owner(s) con todas las secciones
- [ ] Sección de inventario omitida cuando no hay alertas
- [ ] Máximo 10 citas en la lista (con enlace a "ver más")
- [ ] Valores en 0 manejados correctamente (sin errores de rendering)
- [ ] Doble ejecución del cron: sin email duplicado
- [ ] Opt-out del resumen diario respetado
- [ ] Fallo de query de sección: sección marcada como "no disponible"; resto del email enviado
- [ ] Todos los test cases pasan

---

## Out of Scope

- Resumen semanal / mensual (future feature)
- Resumen para otros roles (solo clinic_owner en v1)
- Análisis de tendencias (solo datos del día anterior)
- Export del resumen a PDF

---

## Version History

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-25 | Spec inicial |
