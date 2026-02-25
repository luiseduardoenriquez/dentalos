# Detalle del Plan de Tratamiento — Frontend Spec

## Overview

**Screen:** Vista de detalle completo de un plan de tratamiento. Muestra todos los datos del plan: header con metadatos, tabla de items con estado y costos, barra de progreso, desglose de costos estimados vs. reales, linea de tiempo de eventos del plan, y panel de acciones (aprobar con firma, generar PDF, compartir, generar cotizacion). Esta pantalla es la vista principal de trabajo del plan durante su ejecucion.

**Route:** `/patients/{id}/treatment-plans/{plan_id}`

**Priority:** High

**Backend Specs:**
- `specs/treatment-plans/TP-02-get-plan.md`
- `specs/treatment-plans/TP-04-update-item-status.md`
- `specs/treatment-plans/TP-07-approve-plan.md`
- `specs/treatment-plans/TP-08-sign-plan.md`
- `specs/treatment-plans/TP-09-generate-pdf.md`
- `specs/treatment-plans/TP-10-share-plan.md`

**Dependencies:**
- `specs/frontend/treatment-plans/plan-list.md` — pantalla de origen (FE-TP-01)
- `specs/frontend/treatment-plans/plan-approval.md` — flujo de aprobacion y firma (FE-TP-04)
- `specs/frontend/billing/quotation-detail.md` — si se genera cotizacion

---

## User Flow

**Entry Points:**
- Click en card de plan en FE-TP-01
- Redireccion desde FE-TP-02 al crear el plan
- Notificacion de aprobacion de plan por parte del paciente
- Link desde el portal del paciente

**Exit Points:**
- Breadcrumb / back button → regresa a FE-TP-01 (lista de planes del paciente)
- Boton "Aprobar" → abre modal FE-TP-04
- Boton "Generar PDF" → descarga o abre el PDF en nueva pestaña
- Boton "Generar cotizacion" → crea cotizacion y navega o toast con link
- Boton "Compartir" → copia link del portal o abre modal de compartir

**User Story:**
> As a doctor | clinic_owner, I want to see the full details of a treatment plan, track progress item by item, compare estimated vs. actual costs, and manage the approval workflow so that I can keep the patient and the team aligned on the treatment status.

**Roles with access:** `clinic_owner`, `doctor`, `assistant` (lectura + actualizar estado de item), `receptionist` (solo lectura)

---

## Layout Structure

```
+--------------------------------------------------+
|  < Planes de tratamiento    [PDF] [Compartir]    |
+--------------------------------------------------+
|  Plan de rehabilitacion oral completa            |
|  [Activo] — Dr. Lopez — Paciente: Juan Perez     |
|  Creado: 15 Ene 2026  |  Aprobado: 18 Ene 2026  |
|  ---------------------------------------------- |
|  Progreso: [=====░░░░░░░░░] 2 de 5 completados   |
+--------------------------------------------------+
|  Procedimientos              [+Agregar item]     |
|  +------------------------------------------+   |
|  | Proc.       | Diente | Estado   | Est.   | Real|
|  |-------------|--------|----------|--------|-----|
|  | Extraccion  | 16     |[Complet.]| 85,000 |85,000|
|  | Restauracion| 21     |[Pend.]   | 65,000 |  —  |
|  | Endodoncia  | 36     |[En curso]| 200,000|  —  |
|  | Blanqueam.  | Gral.  |[Pend.]   | 150,000|  —  |
|  | Protesis    | 16     |[Pend.]   | 350,000|  —  |
|  +------------------------------------------+   |
|  Total est.: $850,000   |  Total real: $85,000   |
|  Diferencia: $-765,000 (pendiente)               |
+--------------------------------------------------+
|  Acciones:                                       |
|  [Aprobar plan] [Cotizacion] [Editar]            |
+--------------------------------------------------+
|  Linea de tiempo:                                |
|  ● 15 Ene 2026 — Plan creado por Dr. Lopez      |
|  ● 18 Ene 2026 — Aprobado por Juan Perez (firma)|
|  ● 24 Feb 2026 — Extraccion 16 completada       |
+--------------------------------------------------+
```

**Sections:**
1. Header — breadcrumb, titulo del plan, metadata (estado, doctor, paciente, fechas), barra de progreso global
2. Tabla de items — procedimientos con estado, costos estimados y reales; boton agregar item
3. Desglose de costos — total estimado, total real acumulado, diferencia
4. Panel de acciones — aprobar, generar cotizacion, editar plan, PDF, compartir
5. Linea de tiempo — eventos cronologicos del plan

---

## UI Components

### Component 1: HeaderPlan

**Type:** Page header con metadatos

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| plan | TratamientoPlan | — | Datos completos del plan |
| onBack | function | — | Navega a la lista |

**Behavior:**
- Breadcrumb: `< Planes de tratamiento` a la izquierda
- Botones de accion rapida a la derecha: PDF y Compartir (siempre visibles)
- Titulo del plan en `text-2xl font-bold`
- Metadatos en fila: badge de estado + doctor asignado + nombre del paciente
- Fechas: creado y (si aplica) aprobado, en formato dd MMM yyyy
- Barra de progreso debajo de las fechas

---

### Component 2: TablaItemsPlan

**Type:** Table con inline status update

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| items | PlanItem[] | [] | Items del plan |
| planEstado | string | — | Estado del plan (afecta permisos de edicion) |
| onUpdateEstado | function | — | Actualiza el estado de un item |
| onAddItem | function | — | Abre formulario inline para agregar item |
| isLoading | boolean | false | Skeleton durante carga |

**Columnas de la tabla:**
1. Procedimiento — nombre + codigo CUPS
2. Diente / Zona — numero FDI o zona anatomica
3. Estado — badge con dropdown para cambiar estado
4. Costo Estimado — valor original del plan
5. Costo Real — valor una vez ejecutado (de la factura o del procedimiento registrado); guion si pendiente

**States:**
- Default — tabla con datos
- Loading — skeleton de 5 filas
- Fila con estado dropdown abierto — dropdown de cambio de estado

**Behavior:**
- Estado de item editable via dropdown inline en la celda de estado
- Solo `doctor`, `clinic_owner`, `assistant` pueden cambiar estado
- Al completar un item: abre dialog con costo real y link opcional a registro clinico
- Estados de item: `pendiente`, `en_curso`, `completado`, `cancelado`
- Item completado: fondo de fila con `bg-green-50` suave
- Item en curso: borde izquierdo `border-l-4 border-blue-500`
- Item cancelado: texto tachado `line-through text-gray-400`

---

### Component 3: EstadoItemDropdown

**Type:** Dropdown de cambio de estado inline

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| estadoActual | string | — | Estado actual del item |
| onCambiar | (nuevoEstado: string) => void | — | Callback al seleccionar nuevo estado |
| itemId | string | — | ID del item para la mutation |
| isUpdating | boolean | false | Spinner durante actualizacion |

**States:**
- Cerrado — badge de estado con chevron sutil
- Abierto — dropdown con 4 opciones de estado
- Updating — spinner sobre el badge mientras se guarda

**Behavior:**
- Click en badge abre dropdown
- Al seleccionar "Completado": abre mini-dialog para ingresar costo real
- Al seleccionar "En curso": actualiza inmediatamente
- Al confirmar el cambio a completado: POST con estado + costo real

---

### Component 4: DesgloseCostos

**Type:** Summary card

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| items | PlanItem[] | [] | Items con costos estimados y reales |

**Behavior:**
- Calcula en el cliente:
  - Total estimado: suma de `costo_estimado` de todos los items activos
  - Total real: suma de `costo_real` de items completados
  - Diferencia: total estimado - total real (items pendientes de ejecutar)
- Formato COP para todos los valores
- Color de la diferencia: negro si diferencia positiva (costo pendiente), verde si el real fue menor al estimado

---

### Component 5: AccionesPlan

**Type:** Action button group

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| plan | TratamientoPlan | — | Para determinar que acciones mostrar |
| onAprobar | function | — | Abre modal FE-TP-04 |
| onGenerarPDF | function | — | Descarga/abre PDF |
| onCompartir | function | — | Comparte via link |
| onGenerarCotizacion | function | — | Crea cotizacion |
| onEditar | function | — | Abre modal de edicion |

**Behavior:** Las acciones visibles cambian segun el estado del plan:
- Borrador → [Editar], [Aprobar plan] (activa flujo FE-TP-04), [Eliminar]
- Activo → [Aprobar plan] (si no esta firmado), [PDF], [Compartir], [Generar cotizacion], [Editar]
- Completado → [PDF], [Compartir]
- Cancelado → [Ver PDF] (si fue firmado)

---

### Component 6: LineaTiempoPlan

**Type:** Timeline vertical

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| eventos | PlanEvento[] | [] | Eventos cronologicos del plan |

**Behavior:**
- Lista cronologica de eventos del plan con fecha + descripcion + actor
- Tipos de evento: creacion, aprobacion, firma, item completado, item cancelado, cotizacion generada
- Icono y color por tipo de evento
- Mas de 5 eventos: boton "Ver toda la historia" que expande
- El evento de "firma" tiene link clickeable "Ver documento firmado"

---

## Form Fields

### Dialog costo real al completar item:

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| costo_real | number | Yes | >= 0, max 99,999,999 | "Ingresa el costo real del procedimiento" | "Costo real ($)" |
| registro_clinico_id | string | No | UUID valido si se ingresa | — | — |

**Zod Schema (dialog):**
```typescript
const completarItemSchema = z.object({
  costo_real: z.number()
    .min(0, "El costo no puede ser negativo")
    .max(99999999),
  registro_clinico_id: z.string().uuid().optional(),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Cargar detalle del plan | `/api/v1/patients/{id}/treatment-plans/{plan_id}` | GET | `specs/treatment-plans/TP-02-get-plan.md` | 2min |
| Actualizar estado de item | `/api/v1/treatment-plans/{plan_id}/items/{item_id}` | PATCH | `specs/treatment-plans/TP-04-update-item-status.md` | None |
| Aprobar plan | `/api/v1/treatment-plans/{plan_id}/approve` | POST | `specs/treatment-plans/TP-07-approve-plan.md` | None |
| Generar PDF | `/api/v1/treatment-plans/{plan_id}/pdf` | POST | `specs/treatment-plans/TP-09-generate-pdf.md` | None |
| Compartir plan | `/api/v1/treatment-plans/{plan_id}/share` | POST | `specs/treatment-plans/TP-10-share-plan.md` | None |
| Generar cotizacion | `/api/v1/patients/{id}/quotations` | POST | `specs/billing/B-16-generate-quotation.md` | None |

### State Management

**Local State (useState):**
- `dropdownEstadoOpen: string | null` — ID del item con dropdown abierto
- `completarItemDialog: { open: boolean, itemId: string | null }` — dialog de costo real
- `pdfLoading: boolean` — durante generacion de PDF

**Global State (Zustand):**
- `patientStore.currentPatient` — paciente activo

**Server State (TanStack Query):**
- Query key: `['treatment-plan', planId, tenantId]`
- Stale time: 2 minutos
- Mutation: `useMutation({ mutationFn: updateItemStatus })` con optimistic update
- Mutation: `useMutation({ mutationFn: generatePDF })`
- Mutation: `useMutation({ mutationFn: sharePlan })`
- Mutation: `useMutation({ mutationFn: generateQuotation })`

### Optimistic Update para cambio de estado de item:
```typescript
// Al actualizar estado de item, actualizacion optimista antes del POST:
onMutate: async ({ itemId, nuevoEstado }) => {
  await queryClient.cancelQueries(['treatment-plan', planId]);
  const prev = queryClient.getQueryData(['treatment-plan', planId]);
  queryClient.setQueryData(['treatment-plan', planId], (old) => ({
    ...old,
    items: old.items.map(item =>
      item.id === itemId ? { ...item, estado: nuevoEstado } : item
    )
  }));
  return { prev };
},
onError: (_, __, ctx) => queryClient.setQueryData(['treatment-plan', planId], ctx.prev),
```

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `plan_not_found` | 404 | "Plan de tratamiento no encontrado" |
| `already_approved` | 409 | "Este plan ya fue aprobado anteriormente" |
| `forbidden` | 403 | "No tienes permisos para modificar este plan" |
| `plan_cancelled` | 422 | "No se pueden modificar items de un plan cancelado" |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Cambiar estado de item | Click en badge de estado → seleccionar | PATCH con optimistic update | Spinner en celda, badge actualizado |
| Marcar como completado | Seleccionar "Completado" en dropdown | Dialog para ingresar costo real | Dialog slide-in |
| Confirmar completado | Click "Confirmar" en dialog | PATCH con costo real | Badge verde, costo real en tabla |
| Aprobar plan | Click "Aprobar plan" | Abre modal FE-TP-04 | Modal slide-up |
| Generar PDF | Click "PDF" | POST → PDF descarga o nueva pestaña | Loading en boton, luego descarga |
| Compartir | Click "Compartir" | Copia link del portal al clipboard | Toast "Link copiado al portapapeles" |
| Generar cotizacion | Click "Generar cotizacion" | POST B-16 | Toast con link "Ver cotizacion" |
| Agregar item | Click "+ Agregar item" | Formulario inline al final de la tabla | Fila editable fade-in |

### Animations/Transitions

- Cambio de estado de item: transicion de color del badge 200ms
- Fila completada: fade-in de `bg-green-50` 300ms
- Dialog costo real: scale-in desde el centro 150ms
- PDF loading: boton con `Loader2` mientras genera
- Timeline eventos: stagger-in 50ms entre eventos al carga inicial

---

## Loading & Error States

### Loading State
- Skeleton completo de la pagina: header skeleton (titulo + metadata), tabla skeleton (5 filas), desglose skeleton (3 lineas de numeros), linea de tiempo skeleton (3 eventos)
- Cambio de estado de item: spinner mini en la celda del item; el resto de la tabla sigue interactivo

### Error State
- Error al cargar el plan: pagina de error full con boton "Reintentar" y link "Volver a la lista"
- Error de PATCH en item: revert del optimistic update + toast de error especifico
- Error de PDF: toast "Error al generar el PDF. Intenta de nuevo."

### Empty State
- Plan sin items (no deberia ocurrir si se valida en FE-TP-02, pero por si acaso):
  - Tabla vacia con boton "+ Agregar item"
  - Mensaje: "Este plan no tiene procedimientos. Agrega procedimientos para comenzar."
- Linea de tiempo sin eventos (nuevo plan): un solo evento "Plan creado"

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Header compacto. Tabla colapsa a cards apiladas por item. Costos en una sola columna (estimado). Panel de acciones en bottom bar sticky. Timeline colapsado con boton expandir. |
| Tablet (640-1024px) | Tabla completa con todas las columnas. Panel de acciones en fila horizontal. Timeline visible completo. Layout primario clinico. Touch targets 44px. |
| Desktop (> 1024px) | Layout de 2 columnas: tabla (izquierda, 2/3) + panel lateral con desglose, acciones y timeline (derecha, 1/3). |

**Tablet priority:** High — seguimiento de plan de tratamiento durante citas. Badge de estado con area de toque 44px (dropdown de estado). Botones de accion con altura minima 44px. Tabla con filas de 52px de altura.

---

## Accessibility

- **Focus order:** Breadcrumb → botones de accion header → tabla de items (por fila) → dropdown de estado → panel de acciones → timeline
- **Screen reader:** `aria-label="Detalle del plan {titulo}"` en el main. Tabla con `role="table"`, `scope="col"` en headers, resumen de tabla `caption`. Dropdown estado: `aria-label="Cambiar estado de {procedimiento}"`. Panel acciones: `role="complementary" aria-label="Acciones del plan"`.
- **Keyboard navigation:** Tab navega entre filas y botones interactivos. Arrow keys en dropdown de estado. Enter activa acciones. Escape cierra dialogs.
- **Color contrast:** WCAG AA. Estados de item no dependen solo del color: texto + icono + fondo diferenciados.
- **Language:** es-419. Fechas formateadas con locale es. Precios en formato COP.

---

## Design Tokens

**Colors:**
- Fila item completado: `bg-green-50`
- Fila item en curso: `border-l-4 border-blue-500`
- Fila item cancelado: `opacity-50`
- Badge estado pendiente: `bg-gray-100 text-gray-600`
- Badge estado en curso: `bg-blue-100 text-blue-700`
- Badge estado completado: `bg-green-100 text-green-700`
- Badge estado cancelado: `bg-red-100 text-red-700`
- Diferencia de costo (positiva): `text-gray-900`
- Diferencia de costo (negativa = real mayor que estimado): `text-red-600`
- Timeline dot: `bg-blue-500` (evento normal), `bg-green-500` (completado), `bg-red-500` (cancelado)

**Typography:**
- Titulo plan: `text-2xl font-bold text-gray-900`
- Metadata: `text-sm text-gray-500`
- Nombre procedimiento en tabla: `text-sm text-gray-900 font-medium`
- Codigo CUPS: `text-xs font-mono text-gray-400`
- Total estimado: `text-lg font-bold text-gray-900`
- Total real: `text-lg font-bold text-green-700`
- Timeline fecha: `text-xs text-gray-400`
- Timeline descripcion: `text-sm text-gray-700`

**Spacing:**
- Padding pagina: `px-4 md:px-6 py-6`
- Gap secciones: `space-y-6`
- Fila tabla: `py-3.5 px-4`
- Panel acciones padding: `p-5`

**Border Radius:**
- Tabla: `rounded-xl overflow-hidden border border-gray-200`
- Panel acciones: `rounded-xl border border-gray-200`
- Timeline: `border-l-2 border-gray-200 ml-4 pl-6`
- Dialogs: `rounded-xl`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — fetch y mutations con optimistic updates
- `lucide-react` — ChevronLeft, FileText, Share2, CheckCircle, Clock, XCircle, AlertCircle, Download, Plus, Loader2
- `date-fns` + `date-fns/locale/es` — formateo de fechas
- `react-hook-form` + `zod` — dialog de costo real

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/treatment-plans/[plan_id]/page.tsx`
- Header: `src/components/treatment-plans/PlanDetailHeader.tsx`
- Tabla: `src/components/treatment-plans/PlanItemsTable.tsx`
- Estado dropdown: `src/components/treatment-plans/ItemStatusDropdown.tsx`
- Dialog completar: `src/components/treatment-plans/CompleteItemDialog.tsx`
- Desglose: `src/components/treatment-plans/CostBreakdown.tsx`
- Acciones: `src/components/treatment-plans/PlanActions.tsx`
- Timeline: `src/components/treatment-plans/PlanTimeline.tsx`
- Hook: `src/hooks/useTreatmentPlanDetail.ts`

**Hooks Used:**
- `useQuery(['treatment-plan', planId])` — detalle del plan con items y timeline
- `useMutation()` — actualizar estado item (con optimistic), generar PDF, compartir, cotizacion
- `useAuth()` — para verificar rol del usuario (permisos de edicion)
- `usePatientStore()` — paciente activo
- `useRouter()` — breadcrumb back

**Form Library:**
- React Hook Form + Zod para el dialog de "completar item" (costo real).

---

## Test Cases

### Happy Path
1. Ver detalle completo del plan activo
   - **Given:** Plan con 5 items, 2 completados, aprobado y firmado
   - **When:** Usuario navega al detalle
   - **Then:** Tabla con los 5 items con estados correctos, progreso 2/5, total estimado y real calculados correctamente

2. Marcar item como completado con costo real
   - **Given:** Item en estado "pendiente" visible en la tabla
   - **When:** Doctor abre el dropdown del item, selecciona "Completado", ingresa costo real $90,000 y confirma
   - **Then:** PATCH exitoso, badge del item cambia a verde "Completado", costo real aparece en la columna correspondiente, progreso global incrementa

3. Generar PDF
   - **Given:** Plan activo con items
   - **When:** Click en boton "PDF"
   - **Then:** Loading en boton (Loader2), luego el PDF se descarga o abre en nueva pestaña

4. Compartir plan
   - **Given:** Plan activo o completado
   - **When:** Click "Compartir"
   - **Then:** Link del portal copiado al clipboard, toast "Link copiado al portapapeles"

### Edge Cases
1. Plan cancelado — acciones limitadas
   - **Given:** Plan con estado "cancelado"
   - **When:** Usuario ve el detalle
   - **Then:** Tabla en modo solo lectura, sin dropdown de estado, sin boton "Aprobar"; solo acciones de PDF y "Ver PDF" si fue firmado

2. Revert de optimistic update al fallar
   - **Given:** Item en pendiente, se cambia a "en curso" optimisticamente
   - **When:** El PATCH falla con error 500
   - **Then:** Badge del item vuelve a "pendiente" automaticamente, toast de error mostrado

3. Timeline con muchos eventos
   - **Given:** Plan con 8 eventos (creacion + multiples cambios de item)
   - **When:** Se carga el detalle
   - **Then:** Se muestran los primeros 5 eventos y boton "Ver toda la historia" para expandir los 3 restantes

### Error Cases
1. Plan no encontrado
   - **Given:** URL con plan_id inexistente
   - **When:** GET retorna 404
   - **Then:** Pagina de error: "Plan de tratamiento no encontrado" + boton "Volver a la lista de planes"

---

## Acceptance Criteria

- [ ] Header con: breadcrumb, titulo, badge de estado, doctor, paciente, fechas (creacion y aprobacion), barra de progreso global
- [ ] Tabla de items con columnas: procedimiento + CUPS, diente/zona, estado (dropdown editable), costo estimado, costo real
- [ ] Dropdown de estado inline por item: pendiente, en curso, completado, cancelado
- [ ] Al completar item: dialog para ingresar costo real (requerido)
- [ ] Fila completada con `bg-green-50`; fila en curso con borde izquierdo azul; item cancelado con texto tachado
- [ ] Optimistic update al cambiar estado (sin esperar respuesta del servidor para la UI)
- [ ] Desglose de costos: total estimado, total real acumulado, diferencia
- [ ] Panel de acciones segun estado: [Aprobar] (si no firmado), [PDF], [Compartir], [Cotizacion], [Editar] / [Ver PDF] (si cancelado/firmado)
- [ ] Aprobar plan abre modal FE-TP-04
- [ ] Generar PDF descarga o abre en nueva pestaña
- [ ] Compartir copia link del portal al clipboard con toast
- [ ] Linea de tiempo con eventos cronologicos (max 5 visible + expandir)
- [ ] Revert de optimistic update si el PATCH falla
- [ ] Skeleton de carga completo para toda la pagina
- [ ] Error 404: pagina de error con CTA volver a la lista
- [ ] Responsive: cards de items en mobile, tabla en tablet+, layout 2-col en desktop
- [ ] Touch targets 44px en tabla (filas de 52px) y botones de accion
- [ ] Accesibilidad: table con caption y scope, aria-label en dropdown de estado, role="complementary" en panel de acciones
- [ ] Textos, fechas y precios en es-419 / COP

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
