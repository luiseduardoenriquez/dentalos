# Flujos de Recepcionista — DentalOS

> Documento de referencia para validar end-to-end (Playwright) todos los flujos que una recepcionista
> realiza en una clínica odontológica. Cada flujo tiene su estado de validación.

**Leyenda:**
- [ ] No validado
- [x] Validado con Playwright
- [!] Validado pero con bugs encontrados (ver notas)
- [~] No aplica / No implementado aún

---

## 1. APERTURA DEL DÍA

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 1.1 | Login como recepcionista y ver dashboard | `/dashboard` | [ ] |
| 1.2 | Ver KPIs del día (pacientes activos, citas hoy, ingresos mes) | `/dashboard` | [ ] |
| 1.3 | Abrir caja diaria (nombre, ubicación, saldo inicial) | `/billing/cash-register` | [ ] |
| 1.4 | Revisar agenda del día (vista timeline) | `/agenda/today` | [ ] |
| 1.5 | Revisar agenda semanal/mensual | `/agenda` | [ ] |

---

## 2. GESTIÓN DE PACIENTES

### 2.1 Registro de paciente nuevo

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 2.1.1 | Crear paciente nuevo (datos demográficos, contacto, EPS) | `/patients/new` | [ ] |
| 2.1.2 | Verificar paciente aparece en listado | `/patients` | [ ] |
| 2.1.3 | Buscar paciente por nombre | `/patients` (searchbox) | [ ] |
| 2.1.4 | Buscar paciente por cédula | `/patients` (searchbox) | [ ] |
| 2.1.5 | Filtrar pacientes activos/inactivos | `/patients` (filtros) | [ ] |
| 2.1.6 | Importar pacientes por CSV | `/patients/import` | [ ] |

### 2.2 Edición de paciente

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 2.2.1 | Editar datos demográficos de paciente existente | `/patients/[id]/edit` | [ ] |
| 2.2.2 | Actualizar teléfono y correo | `/patients/[id]/edit` | [ ] |
| 2.2.3 | Actualizar información de EPS | `/patients/[id]/edit` | [ ] |
| 2.2.4 | Desactivar paciente | `/patients/[id]` (botón) | [ ] |
| 2.2.5 | Reactivar paciente | `/patients/[id]` (botón) | [ ] |

### 2.3 Portal del paciente

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 2.3.1 | Activar acceso al portal para un paciente | `/patients/[id]` (botón) | [ ] |
| 2.3.2 | Revocar acceso al portal | `/patients/[id]` (botón) | [ ] |

### 2.4 Familia

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 2.4.1 | Ver grupo familiar del paciente | `/patients/[id]` → tab Familia | [ ] |
| 2.4.2 | Agregar miembro a grupo familiar | `/patients/[id]` → tab Familia | [ ] |
| 2.4.3 | Remover miembro del grupo familiar | `/patients/[id]` → tab Familia | [ ] |

---

## 3. AGENDA Y CITAS

### 3.1 Crear citas

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 3.1.1 | Crear cita desde calendario (click en slot vacío) | `/agenda` | [ ] |
| 3.1.2 | Seleccionar paciente, doctor, tipo, duración | `/agenda` (modal) | [ ] |
| 3.1.3 | Crear cita de urgencia/emergencia | `/agenda` | [ ] |
| 3.1.4 | Crear cita recurrente (controles de ortodoncia) | `/agenda` | [ ] |

### 3.2 Gestión de citas

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 3.2.1 | Confirmar cita programada | `/agenda/today` | [ ] |
| 3.2.2 | Marcar paciente como llegó (check-in) | `/agenda/today` | [ ] |
| 3.2.3 | Completar cita | `/agenda/today` | [ ] |
| 3.2.4 | Marcar como no asistió (no-show) | `/agenda/today` | [ ] |
| 3.2.5 | Cancelar cita con motivo | `/agenda` (modal) | [ ] |
| 3.2.6 | Reagendar cita (cambiar fecha/hora) | `/agenda` (modal) | [ ] |

### 3.3 Lista de espera

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 3.3.1 | Agregar paciente a lista de espera | `/agenda` | [ ] |
| 3.3.2 | Ver lista de espera actual | `/agenda` | [ ] |
| 3.3.3 | Mover paciente de lista de espera a cita | `/agenda` | [ ] |

---

## 4. FACTURACIÓN Y PAGOS

### 4.1 Crear facturas

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 4.1.1 | Crear factura manual (agregar ítems a mano) | `/patients/[id]/invoices/new` | [ ] |
| 4.1.2 | Crear factura desde plan de tratamiento | `/patients/[id]/invoices/new` → "Cargar desde tratamientos" | [ ] |
| 4.1.3 | Crear factura desde ortodoncia (control mensual) | `/patients/[id]/invoices/new` → "Cargar desde ortodoncia" | [ ] |
| 4.1.4 | Crear factura desde ortodoncia (cuota inicial) | `/patients/[id]/invoices/new` → "Cargar desde ortodoncia" | [ ] |
| 4.1.5 | Crear factura con múltiples ítems mixtos | `/patients/[id]/invoices/new` | [ ] |
| 4.1.6 | Aplicar descuento a un ítem | `/patients/[id]/invoices/new` | [ ] |
| 4.1.7 | Aplicar IVA 19% | `/patients/[id]/invoices/new` (checkbox) | [ ] |
| 4.1.8 | Guardar factura como borrador | `/patients/[id]/invoices/new` → "Guardar borrador" | [ ] |
| 4.1.9 | Guardar y enviar factura | `/patients/[id]/invoices/new` → "Guardar y enviar" | [ ] |

### 4.2 Gestión de facturas

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 4.2.1 | Ver listado de facturas de paciente | `/patients/[id]/invoices` | [ ] |
| 4.2.2 | Ver detalle de factura | `/patients/[id]/invoices/[invoiceId]` | [ ] |
| 4.2.3 | Enviar factura (borrador → enviada) | Detalle → "Enviar" | [ ] |
| 4.2.4 | Anular factura | Detalle → "Anular" | [ ] |
| 4.2.5 | Generar PDF de factura | Detalle → "PDF" | [ ] |
| 4.2.6 | Ver facturas desde vista global de facturación | `/billing` | [ ] |

### 4.3 Registrar pagos

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 4.3.1 | Registrar pago total en efectivo | Detalle factura → "Registrar pago" | [ ] |
| 4.3.2 | Registrar pago total con tarjeta | Detalle factura → "Registrar pago" | [ ] |
| 4.3.3 | Registrar pago total con transferencia | Detalle factura → "Registrar pago" | [ ] |
| 4.3.4 | Registrar pago total con Nequi | Detalle factura → "Registrar pago" | [ ] |
| 4.3.5 | Registrar pago total con Daviplata | Detalle factura → "Registrar pago" | [ ] |
| 4.3.6 | Registrar pago parcial (enviada → parcial) | Detalle factura → "Registrar pago" | [ ] |
| 4.3.7 | Registrar segundo pago para completar (parcial → pagada) | Detalle factura → "Registrar pago" | [ ] |
| 4.3.8 | Crear plan de pagos/cuotas | Detalle factura → "Plan de pagos" | [ ] |

### 4.4 Caja diaria

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 4.4.1 | Abrir caja (nombre, ubicación, saldo inicial) | `/billing/cash-register` | [ ] |
| 4.4.2 | Ver movimientos de caja en tiempo real | `/billing/cash-register` | [ ] |
| 4.4.3 | Ver KPIs de caja (ingresos, egresos, saldo neto) | `/billing/cash-register` | [ ] |
| 4.4.4 | Cerrar caja (saldo físico, diferencia) | `/billing/cash-register` → "Cerrar caja" | [ ] |
| 4.4.5 | Generar reporte de cierre de caja | `/billing/cash-register` | [ ] |

### 4.5 Gastos

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 4.5.1 | Ver listado de gastos | `/billing/expenses` | [ ] |
| 4.5.2 | Crear nuevo gasto (categoría, monto, descripción) | `/billing/expenses/new` | [ ] |

### 4.6 Tareas de facturación

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 4.6.1 | Ver cola de tareas de facturación | `/billing/tasks` | [ ] |
| 4.6.2 | Filtrar tareas por tipo (mora, aceptación, manual) | `/billing/tasks` | [ ] |
| 4.6.3 | Actualizar estado de tarea (pendiente → en progreso → completada) | `/billing/tasks` | [ ] |

---

## 5. COTIZACIONES

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 5.1 | Ver listado de cotizaciones de paciente | `/patients/[id]` → tab Cotizaciones | [ ] |
| 5.2 | Ver detalle de cotización | `/patients/[id]/quotations/[id]` | [ ] |
| 5.3 | Crear cotización nueva | `/patients/[id]/quotations/new` | [ ] |
| 5.4 | Enviar cotización al paciente | Detalle cotización → "Enviar" | [ ] |
| 5.5 | Convertir cotización aprobada en factura | Detalle cotización → "Facturar" | [ ] |

---

## 6. ORTODONCIA (solo lectura para recepcionista)

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 6.1 | Ver casos de ortodoncia del paciente | `/patients/[id]` → tab Ortodoncia | [ ] |
| 6.2 | Ver detalle de caso (resumen financiero) | `/patients/[id]/ortho/[caseId]` | [ ] |
| 6.3 | Ver lista de visitas/controles | `/patients/[id]/ortho/[caseId]` → tab Visitas | [ ] |
| 6.4 | Verificar estado de pago de visita | `/patients/[id]/ortho/[caseId]` → tab Visitas | [ ] |

---

## 7. RECLAMACIONES EPS

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 7.1 | Ver listado de reclamaciones con aging (0-30, 31-60, 61-90, 90+) | `/billing/eps-claims` | [ ] |
| 7.2 | Crear nueva reclamación EPS | `/billing/eps-claims/new` | [ ] |
| 7.3 | Ver detalle de reclamación | `/billing/eps-claims/[id]` | [ ] |
| 7.4 | Actualizar estado de reclamación | `/billing/eps-claims/[id]` | [ ] |
| 7.5 | Filtrar reclamaciones por estado | `/billing/eps-claims` | [ ] |

---

## 8. COMUNICACIONES

### 8.1 WhatsApp

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 8.1.1 | Ver lista de conversaciones | `/whatsapp` | [ ] |
| 8.1.2 | Abrir conversación y leer mensajes | `/whatsapp` → click conversación | [ ] |
| 8.1.3 | Enviar mensaje de texto | `/whatsapp` → input mensaje | [ ] |
| 8.1.4 | Recibir mensaje en tiempo real (SSE) | `/whatsapp` | [ ] |

### 8.2 Llamadas (VoIP)

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 8.2.1 | Ver registro de llamadas | `/calls` | [ ] |
| 8.2.2 | Filtrar por dirección (entrante/saliente) | `/calls` (filtro) | [ ] |
| 8.2.3 | Filtrar por estado (completada, perdida, buzón) | `/calls` (filtro) | [ ] |
| 8.2.4 | Ver detalle de llamada y agregar notas | `/calls/[id]` | [ ] |
| 8.2.5 | Llamar a paciente desde perfil | `/patients/[id]` → "Llamar paciente" | [ ] |

### 8.3 Mensajes internos

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 8.3.1 | Ver mensajes/notificaciones del paciente | `/patients/[id]` → tab Mensajes | [ ] |
| 8.3.2 | Enviar mensaje/notificación al paciente | `/patients/[id]` → tab Mensajes | [ ] |

---

## 9. MEMBRESÍAS

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 9.1 | Ver planes de membresía disponibles | `/memberships` | [ ] |
| 9.2 | Ver membresía actual de un paciente | `/patients/[id]` → tab Membresía | [ ] |
| 9.3 | Inscribir paciente en plan de membresía | `/patients/[id]` → tab Membresía | [ ] |
| 9.4 | Cancelar membresía de paciente | `/patients/[id]` → tab Membresía | [ ] |

---

## 10. INTAKE (Formularios del Portal)

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 10.1 | Ver formularios de intake recibidos | `/intake` | [ ] |
| 10.2 | Filtrar por estado (pendiente, aprobado, rechazado) | `/intake` | [ ] |
| 10.3 | Abrir detalle de formulario | `/intake` → click fila | [ ] |
| 10.4 | Aprobar formulario de intake | `/intake` → "Aprobar" | [ ] |
| 10.5 | Rechazar formulario de intake | `/intake` → "Rechazar" | [ ] |

---

## 11. RECALL (Recontacto)

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 11.1 | Ver campañas de recall | `/recall` | [ ] |
| 11.2 | Crear nueva campaña de recall | `/recall/new` | [ ] |
| 11.3 | Ver detalle de campaña | `/recall/[id]` | [ ] |

---

## 12. FINANCIAMIENTO

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 12.1 | Ver dashboard de financiamiento (KPIs, proveedores, estados) | `/financing` | [ ] |
| 12.2 | Ver tabla de aplicaciones recientes | `/financing` | [ ] |
| 12.3 | Iniciar solicitud de financiamiento desde factura | Flujo factura → financiamiento | [ ] |

---

## 13. CONVENIOS (solo lectura)

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 13.1 | Ver listado de convenios activos | `/convenios` | [ ] |
| 13.2 | Ver detalle de convenio (tarifas, cobertura) | `/convenios/[id]` | [ ] |

---

## 14. LABORATORIO (solo lectura)

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 14.1 | Ver listado de órdenes de laboratorio | `/lab-orders` | [ ] |
| 14.2 | Ver detalle de orden | `/lab-orders/[id]` | [ ] |
| 14.3 | Verificar si trabajo de lab llegó antes de cita | `/lab-orders` | [ ] |

---

## 15. TRATAMIENTOS (solo lectura)

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 15.1 | Ver planes de tratamiento del paciente | `/patients/[id]` → tab Tratamientos | [ ] |
| 15.2 | Ver detalle de plan con ítems y estados | `/patients/[id]/treatment-plans/[id]` | [ ] |

---

## 16. NOTIFICACIONES

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 16.1 | Ver campana de notificaciones (badge con conteo) | Header → icono campana | [ ] |
| 16.2 | Abrir panel de notificaciones | Header → click campana | [ ] |
| 16.3 | Marcar notificación como leída | Panel notificaciones | [ ] |

---

## 17. CIERRE DEL DÍA

| # | Flujo | Ruta | Estado |
|---|-------|------|--------|
| 17.1 | Verificar todas las citas del día cerradas | `/agenda/today` | [ ] |
| 17.2 | Revisar facturas pendientes del día | `/billing` | [ ] |
| 17.3 | Cerrar caja diaria | `/billing/cash-register` → "Cerrar caja" | [ ] |
| 17.4 | Ver reporte de cierre (ingresos, egresos, diferencia) | `/billing/cash-register` | [ ] |
| 17.5 | Logout | Menú usuario → "Cerrar sesión" | [ ] |

---

## 18. FLUJOS COMBINADOS (E2E completos)

Estos son flujos end-to-end que combinan múltiples pasos como lo haría una recepcionista en un día real.

| # | Flujo E2E | Pasos | Estado |
|---|-----------|-------|--------|
| 18.1 | **Paciente nuevo completo**: Registrar → Agendar cita → Check-in → Checkout → Facturar → Cobrar | 2.1.1 → 3.1.1 → 3.2.2 → 3.2.3 → 4.1.1 → 4.3.1 | [ ] |
| 18.2 | **Control de ortodoncia**: Ver caso → Facturar control → Enviar → Cobrar → Verificar en ortho | 6.1 → 4.1.3 → 4.2.3 → 4.3.1 → 6.4 | [ ] |
| 18.3 | **Cuota inicial ortodoncia**: Ver caso → Facturar cuota → Enviar → Cobrar → Verificar | 6.1 → 4.1.4 → 4.2.3 → 4.3.1 → 6.4 | [ ] |
| 18.4 | **Cotización → Factura**: Ver cotización → Aprobar → Generar factura → Cobrar | 5.1 → 5.5 → 4.2.3 → 4.3.1 | [ ] |
| 18.5 | **Pago parcial**: Facturar → Cobrar 50% → Verificar parcial → Cobrar resto → Verificar pagada | 4.1.1 → 4.3.6 → 4.3.7 | [ ] |
| 18.6 | **Apertura → Cierre de día**: Login → Abrir caja → Atender citas → Facturar → Cerrar caja → Logout | 1.1 → 1.3 → 3.2.* → 4.1.* → 17.3 → 17.5 | [ ] |
| 18.7 | **Reclamación EPS**: Crear factura → Crear claim → Seguimiento → Actualizar estado | 4.1.2 → 7.2 → 7.3 → 7.4 | [ ] |
| 18.8 | **Paciente con membresía**: Inscribir → Facturar con descuento → Cobrar → Verificar descuento | 9.3 → 4.1.1 → 4.3.1 | [ ] |
| 18.9 | **Guard duplicados ortho**: Facturar visita → Intentar facturar misma visita → Verificar que no aparece | 4.1.3 → 4.1.3 (repetir) | [ ] |
| 18.10 | **Multi-método pago**: Factura → Pago parcial efectivo → Pago parcial Nequi → Completar con tarjeta | 4.1.1 → 4.3.1 → 4.3.4 → 4.3.2 | [ ] |

---

## Resumen por área

| Área | Flujos | Prioridad |
|------|--------|-----------|
| Gestión de pacientes | 13 | Alta |
| Agenda y citas | 12 | Alta |
| Facturación y pagos | 26 | Crítica |
| Cotizaciones | 5 | Alta |
| Ortodoncia (lectura) | 4 | Media |
| EPS Claims | 5 | Alta |
| Comunicaciones | 9 | Media |
| Membresías | 4 | Media |
| Intake | 5 | Media |
| Recall | 3 | Baja |
| Financiamiento | 3 | Media |
| Convenios | 2 | Baja |
| Laboratorio | 3 | Media |
| Tratamientos | 2 | Baja |
| Notificaciones | 3 | Baja |
| Cierre del día | 5 | Alta |
| **Flujos E2E combinados** | **10** | **Crítica** |
| **TOTAL** | **114** | |
