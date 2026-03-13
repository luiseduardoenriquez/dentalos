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

## 18. FLUJOS COMBINADOS E2E

Estos son los flujos end-to-end que simulan el trabajo real de una recepcionista. Son los **tests más valiosos** porque validan la integración completa entre módulos.

### A. Ciclo de vida del paciente

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.1 | **Paciente nuevo → primera cita → cobro** | Login → Crear paciente (nombre, cédula, teléfono, EPS) → Verificar en listado → Agendar primera cita (limpieza) → Vista today: confirmar cita → Marcar llegó → Completar cita → Crear factura manual (1 ítem) → Enviar → Registrar pago efectivo → Verificar factura pagada | [ ] |
| 18.2 | **Paciente recurrente → actualizar datos → cita** | Buscar paciente por nombre → Editar teléfono y correo → Agendar cita de control → Confirmar cita → Marcar llegó | [ ] |
| 18.3 | **Paciente no asistió → reagendar** | Revisar agenda del día → Identificar cita pasada sin check-in → Marcar como no-show → Buscar paciente → Reagendar nueva cita → Confirmar nueva cita | [ ] |
| 18.4 | **Cancelar cita → llenar con lista de espera** | Paciente llama a cancelar → Cancelar cita → Ver lista de espera → Mover paciente de espera al slot liberado → Confirmar nueva cita | [ ] |
| 18.5 | **Desactivar y reactivar paciente** | Buscar paciente → Desactivar → Verificar badge "Inactivo" → Filtrar por inactivos → Verificar aparece → Reactivar → Verificar badge "Activo" | [ ] |

### B. Facturación y cobros

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.6 | **Factura manual con descuento e IVA** | Crear factura → Agregar 2 ítems manuales → Aplicar descuento al segundo ítem → Activar IVA 19% → Verificar cálculos de subtotal/IVA/total → Guardar borrador → Ver detalle → Enviar → Registrar pago total | [ ] |
| 18.7 | **Factura desde plan de tratamiento** | Ir a paciente → Factura nueva → "Cargar desde tratamientos" → Seleccionar ítems del plan → Agregar → Verificar precios/CUPS cargados → Guardar y enviar → Pagar → Verificar que ítems desaparecen del picker | [ ] |
| 18.8 | **Pago parcial en 3 cuotas** | Crear factura $300,000 → Enviar → Pago 1: $100,000 efectivo → Verificar estado "Parcial" y saldo $200,000 → Pago 2: $100,000 Nequi → Verificar saldo $100,000 → Pago 3: $100,000 tarjeta → Verificar estado "Pagada" y saldo $0 | [ ] |
| 18.9 | **Anular factura** | Crear factura → Enviar → Anular factura → Verificar estado "Cancelada" → Verificar que ítems vuelven a ser facturables | [ ] |
| 18.10 | **Plan de pagos** | Crear factura $500,000 → Enviar → Crear plan de pagos (5 cuotas de $100,000) → Verificar cuotas generadas → Pagar primera cuota → Verificar estado parcial | [ ] |

### C. Ortodoncia ↔ Facturación

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.11 | **Facturar control mensual → pagar → verificar en ortho** | Ir a paciente → Factura nueva → "Cargar desde ortodoncia" → Seleccionar 1 control mensual → Agregar → Verificar descripción y monto → Guardar y enviar → Registrar pago → Ir a Ortodoncia → Ver caso → Tab Visitas → Verificar visita marcada como "Pagado" | [ ] |
| 18.12 | **Facturar cuota inicial → pagar → verificar** | Factura nueva → Cargar desde ortodoncia → Seleccionar cuota inicial → Agregar → Guardar y enviar → Pagar → Ir a caso ortho → Verificar cuota desapareció de facturables | [ ] |
| 18.13 | **Guard: no facturar dos veces el mismo control** | Facturar control #1 de ORT-X → Pagar → Crear otra factura → Abrir picker ortho → Verificar que control #1 de ORT-X ya NO aparece en la lista | [ ] |
| 18.14 | **Guard: no facturar dos veces la cuota inicial** | Facturar cuota inicial de ORT-X → Crear otra factura → Abrir picker → Verificar cuota inicial de ORT-X ya no aparece | [ ] |
| 18.15 | **Facturar múltiples ítems de ortodoncia** | Seleccionar 2 cuotas iniciales + 1 control de diferentes casos → Agregar → Verificar 3 ítems en tabla → Guardar y enviar → Pagar → Verificar todos los items desaparecen del picker | [ ] |

### D. Cotizaciones → Facturación

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.16 | **Cotización → aprobación → factura → cobro** | Ver cotizaciones del paciente → Abrir cotización → Enviar al paciente → Aprobar cotización → Convertir en factura → Verificar ítems cargados desde cotización → Enviar factura → Pagar | [ ] |
| 18.17 | **Cotización rechazada → nueva cotización** | Crear cotización → Enviar → Rechazar → Verificar estado "Rechazada" → Crear nueva cotización con ítems ajustados → Enviar | [ ] |

### E. Caja diaria

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.18 | **Apertura y cierre de caja completo** | Login → Ir a caja → Abrir caja (nombre, saldo $50,000) → Verificar KPIs en cero → Crear y cobrar factura $200,000 efectivo → Verificar caja muestra ingreso → Registrar gasto $30,000 → Verificar egreso → Cerrar caja (saldo físico $220,000) → Verificar reporte de cierre | [ ] |
| 18.19 | **Caja con múltiples métodos de pago** | Abrir caja → Cobrar factura 1 en efectivo → Cobrar factura 2 con Nequi → Cobrar factura 3 con tarjeta → Verificar que caja solo muestra efectivo en saldo físico → Cerrar caja | [ ] |

### F. EPS / Seguros

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.20 | **Factura → Reclamación EPS → seguimiento** | Crear factura con códigos CUPS → Enviar factura → Ir a EPS Claims → Crear reclamación vinculada → Verificar aging card (0-30 días) → Actualizar estado a "en revisión" → Actualizar a "aprobada" | [ ] |
| 18.21 | **Reclamación rechazada → reenvío** | Crear reclamación → Marcar como rechazada → Documentar motivo → Reenviar reclamación corregida → Verificar nueva reclamación en aging | [ ] |

### G. Membresías y descuentos

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.22 | **Inscribir membresía → facturar con descuento** | Ir a paciente → Tab Membresía → Inscribir en plan "Gold" → Verificar badge activo → Crear factura → Verificar que descuento de membresía se aplica → Cobrar con descuento | [ ] |
| 18.23 | **Cancelar membresía** | Ir a paciente → Tab Membresía → Cancelar membresía → Verificar que descuento ya no aplica en siguiente factura | [ ] |

### H. Familia

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.24 | **Crear grupo familiar → ver balance consolidado** | Ir a paciente A → Tab Familia → Crear grupo → Agregar paciente B → Verificar ambos aparecen → Ver balance consolidado de facturas de ambos | [ ] |
| 18.25 | **Remover miembro de familia** | Ir a grupo familiar → Remover paciente B → Verificar que ya no aparece en el grupo | [ ] |

### I. Portal del paciente

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.26 | **Activar portal → revisar intake** | Ir a paciente → Activar acceso al portal → Verificar badge "Portal activo" → Ir a Intake → Ver formulario recibido → Aprobar formulario → Verificar datos actualizados en el paciente | [ ] |
| 18.27 | **Revocar acceso al portal** | Ir a paciente con portal activo → Revocar acceso → Verificar badge cambia | [ ] |

### J. Comunicaciones

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.28 | **Ciclo completo WhatsApp** | Ir a WhatsApp → Abrir conversación de paciente → Enviar mensaje "Recordatorio de cita mañana" → Verificar mensaje aparece en thread | [ ] |
| 18.29 | **Llamar paciente → registrar notas** | Ir a perfil de paciente → Click "Llamar paciente" → Ir a Llamadas → Ver registro de llamada → Agregar nota "Paciente confirma cita" | [ ] |
| 18.30 | **Enviar notificación interna** | Ir a paciente → Tab Mensajes → Enviar notificación → Verificar aparece en historial | [ ] |

### K. Recall y financiamiento

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.31 | **Crear campaña de recall** | Ir a Recall → Nueva campaña → Configurar criterios (pacientes sin cita hace 6 meses) → Crear → Verificar campaña activa | [ ] |
| 18.32 | **Solicitud de financiamiento** | Ver dashboard financiamiento → Verificar KPIs → Ver aplicaciones recientes con estados | [ ] |

### L. Día completo de recepcionista

| # | Flujo E2E | Pasos detallados | Estado |
|---|-----------|------------------|--------|
| 18.33 | **Día completo simulado** | Login recepcionista → Ver dashboard KPIs → Abrir caja ($50,000) → Revisar agenda today → Confirmar 3 citas → Registrar paciente nuevo → Agendarle cita → Check-in paciente existente → Completar cita → Facturar consulta $80,000 → Cobrar efectivo → Check-in segundo paciente (ortodoncia) → Completar → Facturar control ortho $150,000 → Cobrar Nequi → Paciente 3 no asistió → Marcar no-show → Registrar gasto $25,000 (materiales) → Cerrar caja → Verificar reporte → Logout | [!] **Validado con bugs.** Todos los pasos completados. Bugs: **Bug#1 (pendiente)** Dashboard KPIs muestra 0 pacientes para receptionist; **Bug#2 (corregido)** receptionist 403 en GET /users → fix: nuevo endpoint GET /users/providers; **Bug#3 (corregido)** Zod cups_code rechazaba empty string → fix: z.preprocess. **Mejora implementada:** autocomplete de catálogo de servicios en ítems manuales de factura. |
| 18.34 | **Día con problemas** | Login → Abrir caja → Paciente llega sin cita → Buscar disponibilidad → Agendar urgencia → Paciente cancela por teléfono → Cancelar cita → Buscar en lista de espera → Mover waitlist a slot → Factura rechazada por monto incorrecto → Anular factura → Crear nueva factura corregida → Cobrar → Cerrar caja con diferencia → Logout | [ ] |

---

## Resumen

### Flujos unitarios (secciones 1-17)

| Área | Flujos | Prioridad |
|------|--------|-----------|
| Apertura del día | 5 | Alta |
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

### Flujos E2E combinados (sección 18)

| Categoría | Flujos | Prioridad |
|-----------|--------|-----------|
| A. Ciclo de vida paciente | 5 | Crítica |
| B. Facturación y cobros | 5 | Crítica |
| C. Ortodoncia ↔ Facturación | 5 | Crítica |
| D. Cotizaciones → Facturación | 2 | Alta |
| E. Caja diaria | 2 | Crítica |
| F. EPS / Seguros | 2 | Alta |
| G. Membresías y descuentos | 2 | Media |
| H. Familia | 2 | Media |
| I. Portal del paciente | 2 | Media |
| J. Comunicaciones | 3 | Media |
| K. Recall y financiamiento | 2 | Baja |
| L. Día completo simulado | 2 | Crítica |
| **TOTAL E2E** | **34** | |

### Totales

| Tipo | Cantidad |
|------|----------|
| Flujos unitarios | 109 |
| Flujos E2E combinados | 34 |
| **TOTAL** | **143** |

### Orden de ejecución sugerido

1. **L. Día completo** (18.33, 18.34) — validan el flujo más amplio primero
2. **A. Ciclo paciente** (18.1–18.5) — fundamento de todo
3. **B. Facturación** (18.6–18.10) — core del negocio
4. **C. Ortodoncia** (18.11–18.15) — integración recién construida
5. **E. Caja diaria** (18.18–18.19) — dinero real
6. **D. Cotizaciones** (18.16–18.17) — pipeline de ventas
7. **F. EPS** (18.20–18.21) — compliance
8. **G-K** resto por prioridad
