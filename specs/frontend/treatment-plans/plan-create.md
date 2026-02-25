# Crear Plan de Tratamiento — Frontend Spec

## Overview

**Screen:** Modal (o ruta dedicada en mobile) para crear un nuevo plan de tratamiento. Incluye titulo, descripcion, vinculacion a diagnosticos activos del paciente, agregado de items via busqueda CUPS con precio del catalogo y selector de diente, lista de items con reordenamiento drag-and-drop y costos editables, total corriente en tiempo real, flujo de auto-generacion desde el odontograma, y generacion de cotizacion desde el plan.

**Route:** Modal sobre `/patients/{id}/treatment-plans` | `/patients/{id}/treatment-plans/new` en mobile

**Priority:** High

**Backend Specs:**
- `specs/treatment-plans/TP-01-create-plan.md`
- `specs/treatment-plans/TP-05-add-item.md`
- `specs/billing/B-14-price-catalog.md`
- `specs/billing/B-16-generate-quotation.md`

**Dependencies:**
- `specs/frontend/treatment-plans/plan-list.md` — pantalla padre (FE-TP-01)
- `specs/frontend/clinical-records/cups-search.md` — busqueda CUPS con precio (FE-CR-07)
- `specs/frontend/odontogram/odontogram-selector.md` — mini selector de dientes

---

## User Flow

**Entry Points:**
- Click "Crear plan manualmente" en dropdown del boton "Nuevo Plan" en FE-TP-01
- Click "Auto-generar desde odontograma" en FE-TP-01 (modo auto-generacion)
- Ruta directa `/patients/{id}/treatment-plans/new`

**Exit Points:**
- Guardado exitoso → cierra modal → navega a FE-TP-03 (detalle del plan creado)
- "Generar cotizacion" (sin cerrar) → crea cotizacion B-16 → toast con link a la cotizacion
- Cancelar → dialog de confirmacion si hay datos → vuelve a FE-TP-01
- Guardado como borrador → cierra modal → plan en estado borrador en lista

**User Story:**
> As a doctor | clinic_owner, I want to create a structured treatment plan with itemized procedures, costs, and linked diagnoses so that I can present the patient with a clear and complete treatment roadmap.

**Roles with access:** `clinic_owner`, `doctor`

---

## Layout Structure

```
+--------------------------------------------------+
|  [X] Nuevo Plan de Tratamiento                   |
+--------------------------------------------------+
|                                                  |
|  Titulo del plan: [________________________________]|
|  Descripcion: [textarea...]                      |
|  Diagnosticos: [multi-select diagnosticos activos]|
|                                                  |
|  ---------------------------------------------- |
|  Procedimientos del plan:                        |
|                                                  |
|  [Buscar CUPS...                    ] [Agregar]  |
|                                                  |
|  [=] Extraccion diente 16   16  $85,000  [$___] [X]|
|  [=] Restauracion composite 21  $65,000  [$___] [X]|
|  [=] Blanqueamiento         --  $150,000 [$___] [X]|
|                                                  |
|  + Agregar procedimiento                         |
|                                                  |
|  ---------------------------------------------- |
|  Total estimado: $300,000                        |
|                                                  |
|  [Auto-generar desde odontograma] [Cotizacion]  |
|  ---------------------------------------------- |
|  [Cancelar] [Guardar borrador]    [Crear plan]   |
+--------------------------------------------------+
```

**Sections:**
1. Header modal
2. Datos generales — titulo, descripcion, diagnosticos vinculados
3. Lista de procedimientos — busqueda CUPS + lista de items con drag-and-drop
4. Total — suma corriente de costos estimados
5. Acciones secundarias — auto-generar y generar cotizacion
6. Footer — Cancelar, Guardar borrador, Crear plan

---

## UI Components

### Component 1: CampoTituloPlan

**Type:** Input de texto

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | string | "" | Titulo del plan |
| onChange | function | — | Callback |
| error | string \| undefined | — | Error de validacion |

**Behavior:**
- Input de texto simple, max 120 caracteres
- Contador de caracteres visible cuando > 80 chars usados
- Auto-enfoque al abrir el modal

---

### Component 2: DiagnosticosMultiSelect

**Type:** Multi-select de diagnosticos activos

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientId | string | — | Para cargar diagnosticos del paciente |
| value | string[] | [] | IDs de diagnosticos seleccionados |
| onChange | function | — | Callback al cambiar seleccion |

**States:**
- Loading — skeleton de 3 opciones
- Empty — "El paciente no tiene diagnosticos activos"
- Con opciones — lista de checkboxes con codigo CIE-10 + descripcion

**Behavior:**
- Carga solo diagnosticos con estado activo del paciente
- Select multiple con busqueda de texto
- Cada opcion muestra: codigo CIE-10 + descripcion + diente(s) si aplica
- Badge count: "3 diagnosticos vinculados"

---

### Component 3: BuscadorAgregarCUPS

**Type:** Search + add inline

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| onAdd | (item: PlanItem) => void | — | Agrega el CUPS a la lista de items |

**States:**
- Default — input de busqueda CUPS vacio
- CUPS seleccionado — muestra mini-form inline con diente y precio antes de agregar
- Agregando — spinner breve al agregar el item

**Behavior:**
- Usa componente CUPSSearchInput (FE-CR-07) con `showPrice={true}`
- Al seleccionar CUPS: mini-form aparece con precio pre-llenado del catalogo (editable) + selector de diente
- Boton "Agregar" agrega el item a la lista y limpia el buscador para agregar otro
- Precio del catalogo se aplica automaticamente; el doctor puede modificarlo antes de agregar
- Si CUPS no tiene precio en catalogo: precio = 0 (con indicador visual "Sin precio en catalogo")

---

### Component 4: ListaItemsPlan

**Type:** Draggable list

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| items | PlanItem[] | [] | Items del plan |
| onReorder | (items: PlanItem[]) => void | — | Callback tras drag-and-drop |
| onUpdateCosto | (id, costo) => void | — | Edicion de costo de un item |
| onRemove | (id) => void | — | Eliminar item |

**States:**
- Default — lista de items
- Dragging — item siendo arrastrado con sombra elevada
- Empty — mensaje "Agrega procedimientos al plan"

**Behavior:**
- Handle de drag: icono `GripVertical` a la izquierda de cada fila
- Cada fila: [handle] [nombre procedimiento + codigo] [diente/zona] [precio catalogo] [precio editable] [X]
- Campo de precio editable: input numerico, al hacer click se activa la edicion inline
- El precio del catalogo se muestra en gris tachado si el precio editable difiere
- Boton X elimina el item (sin confirmacion a menos que el item este en uso en un registro)
- En tablet: drag funciona con long-press (500ms) antes de iniciar el arrastre
- En desktop: drag inicia con mousedown en el handle

---

### Component 5: TotalCorriente

**Type:** Summary row

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| items | PlanItem[] | [] | Items para calcular el total |

**Behavior:**
- Calcula en tiempo real: suma de todos los costos editables (o del catalogo si no se editaron)
- Formato COP: `$1.250.000` (punto como separador de miles)
- Actualiza instantaneamente al editar cualquier precio o agregar/eliminar items
- Muestra: "Total estimado: $X" + conteo "N procedimientos"

---

### Component 6: AutoGenerarDesdeOdontograma

**Type:** Action button / Loading state

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientId | string | — | Para llamar al endpoint de auto-generacion |
| onGenerated | (items: PlanItem[]) => void | — | Items sugeridos listos para confirmacion |
| hasOdontogram | boolean | true | Si el paciente tiene odontograma |

**States:**
- Default — boton secundario "Auto-generar desde odontograma"
- Loading — boton con spinner "Generando sugerencias..."
- Results — bottom sheet con items sugeridos para confirmar o descartar
- Disabled — si `!hasOdontogram`

**Behavior:**
- Click → POST al endpoint de auto-generacion
- Respuesta: lista de procedimientos sugeridos basados en las condiciones del odontograma
- Bottom sheet de confirmacion: lista de items sugeridos con checkboxes (usuario selecciona cuales agregar)
- Boton "Agregar seleccionados" → agrega los items seleccionados a la lista del plan
- Los items sugeridos tienen precio del catalogo pre-llenado

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| titulo | string | Yes | Min 3 chars, max 120 | "El titulo debe tener al menos 3 caracteres" | "Ej: Plan de rehabilitacion oral completa" |
| descripcion | textarea | No | Max 500 chars | "Maximo 500 caracteres" | "Descripcion del plan (opcional)..." |
| diagnosticos_ids | string[] | No | UUIDs validos | — | — |
| items | PlanItem[] | Yes | Min 1 item | "Agrega al menos un procedimiento al plan" | — |
| items[].cups_codigo | string | Yes | CUPS valido | "Codigo CUPS requerido" | — |
| items[].costo | number | Yes | >= 0, max 99,999,999 | "El costo debe ser mayor o igual a 0" | "0" |
| items[].dientes | string[] | No | FDI validos | — | — |

**Zod Schema:**
```typescript
const planItemSchema = z.object({
  cups_codigo: z.string().min(3),
  cups_descripcion: z.string(),
  dientes: z.array(z.string()).optional(),
  costo: z.number().min(0).max(99999999),
  costo_catalogo: z.number().optional(),
  orden: z.number().int().min(0),
});

const crearPlanSchema = z.object({
  titulo: z.string()
    .min(3, "El titulo debe tener al menos 3 caracteres")
    .max(120),
  descripcion: z.string().max(500).optional(),
  diagnosticos_ids: z.array(z.string().uuid()).optional(),
  items: z.array(planItemSchema).min(1, "Agrega al menos un procedimiento al plan"),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Diagnosticos activos del paciente | `/api/v1/patients/{id}/diagnoses?status=active` | GET | `specs/clinical-records/CR-07.md` | 5min |
| Precio CUPS del catalogo | Via CUPSSearchInput con `showPrice=true` | GET | `specs/billing/B-14-price-catalog.md` | 30min |
| Auto-generar desde odontograma | `/api/v1/patients/{id}/treatment-plans/auto-generate` | POST | `specs/treatment-plans/TP-05-add-item.md` | None |
| Crear plan con items | `/api/v1/patients/{id}/treatment-plans` | POST | `specs/treatment-plans/TP-01-create-plan.md` | None |
| Generar cotizacion | `/api/v1/patients/{id}/quotations` | POST | `specs/billing/B-16-generate-quotation.md` | None |

### Request Body (POST crear plan):
```json
{
  "titulo": "Plan de rehabilitacion oral",
  "descripcion": "Incluye restauraciones y extracciones",
  "diagnosticos_ids": ["uuid1", "uuid2"],
  "items": [
    {
      "cups_codigo": "23.09",
      "cups_descripcion": "Extraccion diente permanente",
      "dientes": ["16"],
      "costo": 85000,
      "orden": 0
    }
  ]
}
```

### State Management

**Local State (useState):**
- `items: PlanItem[]` — lista actual de items del plan
- `autoGenerarLoading: boolean` — estado de la auto-generacion
- `autoGenerarSugerencias: PlanItem[]` — items sugeridos pendientes de confirmacion
- `showAutoGenerarSheet: boolean` — bottom sheet de confirmacion de sugerencias
- `isSubmitting: boolean`

**Global State (Zustand):**
- `patientStore.currentPatient` — paciente activo

**Server State (TanStack Query):**
- Query: `['patient-diagnoses', patientId, 'active']` — diagnosticos activos
- Mutation: `useMutation({ mutationFn: createTreatmentPlan })`
- Mutation: `useMutation({ mutationFn: generateQuotation })`
- Mutation: `useMutation({ mutationFn: autoGeneratePlan })`

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `no_odontogram` | 422 | "El paciente no tiene odontograma registrado para auto-generar" |
| `empty_items` | 422 | "El plan debe tener al menos un procedimiento" |
| `forbidden` | 403 | "No tienes permisos para crear planes de tratamiento" |
| `server_error` | 500 | "Error al crear el plan. Intenta de nuevo." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Buscar CUPS | Typing en buscador | Dropdown con resultados y precios | Spinner durante fetch |
| Seleccionar CUPS | Click en resultado | Mini-form con precio y diente | Inline form fade-in |
| Agregar item | Click "Agregar" | Item agregado a la lista | Item fade-in al final de la lista |
| Reordenar | Long-press (tablet) o drag handle (desktop) | Drag-and-drop de items | Item elevado con sombra |
| Editar costo | Click en campo de costo | Activa edicion inline | Input numerico activo |
| Auto-generar | Click boton | POST + loading → bottom sheet | Spinner en boton, luego sheet slide-up |
| Confirmar sugerencias | Click "Agregar seleccionados" | Items agregados al plan | Sheet cierra, items fade-in |
| Generar cotizacion | Click boton | POST → crea cotizacion | Toast con link "Ver cotizacion" |
| Crear plan | Click "Crear plan" | Valida + POST plan | Spinner, toast, cierra modal, navega a detalle |
| Guardar borrador | Click "Guardar borrador" | POST con estado borrador | Toast "Borrador guardado" |
| Cancelar (con datos) | Click "Cancelar" o Escape | Dialog de confirmacion | Modal de confirmacion |

### Animations/Transitions

- Item agregado: fade-in + slide-down 150ms
- Item eliminado: fade-out + height collapse 150ms
- Auto-generar bottom sheet: slide-up 250ms ease-out
- Total corriente: transicion de numero con CSS counter animation (200ms)
- Modal: slide-up en tablet/mobile, fade-in centrado en desktop

---

## Loading & Error States

### Loading State
- Boton "Crear plan" muestra spinner durante submission
- Auto-generando: boton reemplaza texto por "Generando sugerencias..." + spinner
- Diagnosticos: skeleton de 3 checkboxes mientras carga
- Todos los inputs disabled durante submission final

### Error State
- Errores Zod: inline por campo con `text-xs text-red-600`
- Error en lista de items: banner sobre la lista si `items.length === 0` al intentar guardar
- Error de API: toast destructivo con mensaje especifico
- Error de auto-generacion: toast "No se pudo generar el plan. Verifica que el odontograma este actualizado."

### Empty State
- Lista de items vacia: area con borde punteado `border-2 border-dashed border-gray-300 rounded-xl`
- Mensaje: "Agrega procedimientos usando el buscador de arriba"
- Icono `Plus` en gris

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-screen. Items en cards apiladas (no tabla). Drag-and-drop deshabilitado en mobile — botones de subir/bajar orden en su lugar. Footer con botones apilados. |
| Tablet (640-1024px) | Modal full-height 90vh. Tabla de items con todas las columnas. Drag con long-press. Touch targets 44px en toda la fila de item. Buscador CUPS full-width. |
| Desktop (> 1024px) | Modal `max-w-2xl`. Tabla de items. Drag con mouse. Precio del catalogo visible en columna separada. |

**Tablet priority:** High — planes de tratamiento se crean en tablet durante la consulta. Handle de drag con area de toque 44x44px. Inputs de costo con altura de 44px. Long-press de 500ms para iniciar drag en touch.

---

## Accessibility

- **Focus order:** Titulo → Descripcion → Diagnosticos → Buscador CUPS → Lista de items (por orden) → Total → Auto-generar → Generar cotizacion → Cancelar → Guardar borrador → Crear plan
- **Screen reader:** `role="dialog"` con `aria-label="Crear nuevo plan de tratamiento"`. Lista de items: `role="list"`. Cada item: `role="listitem"` con `aria-label="{procedimiento}, diente {N}, costo ${X}"`. Total: `aria-live="polite"` para anunciar cambios al sumar/quitar items.
- **Keyboard navigation:** Tab entre campos. En lista de items: Tab navega entre fields editables, Delete en campo de costo vacio elimina el item (con confirmacion).
- **Color contrast:** WCAG AA. Precio tachado (catalogo vs editado): diferencia de color + tachado tipografico (doble indicador para accesibilidad).
- **Language:** es-419. Precios en formato COP. Mensajes de confirmacion en español.

---

## Design Tokens

**Colors:**
- Buscador CUPS: `border-gray-300 focus:border-blue-500`
- Fila item: `bg-white border-b border-gray-100`
- Fila item hover: `bg-gray-50`
- Handle drag: `text-gray-300 hover:text-gray-500`
- Input costo activo: `border-blue-500 ring-2 ring-blue-100`
- Precio catalogo (diferente al editado): `text-gray-400 line-through text-xs`
- Total: `text-xl font-bold text-gray-900`
- Area vacia de items: `border-dashed border-gray-300`

**Typography:**
- Titulo modal: `text-lg font-semibold text-gray-900`
- Label campo: `text-sm font-medium text-gray-700`
- Nombre procedimiento en item: `text-sm text-gray-900`
- Codigo CUPS en item: `text-xs font-mono text-gray-400`
- Total label: `text-sm text-gray-500`
- Total valor: `text-xl font-bold text-gray-900`

**Spacing:**
- Modal padding: `p-6`
- Gap secciones: `space-y-6`
- Fila item padding: `py-3 px-2`
- Footer: `px-6 py-4 border-t border-gray-200`

**Border Radius:**
- Modal: `rounded-2xl`
- Inputs: `rounded-md`
- Lista items: `rounded-xl border border-gray-200`
- Area vacia: `rounded-xl`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers` — validacion
- `@dnd-kit/core` + `@dnd-kit/sortable` — drag-and-drop de items
- `@tanstack/react-query` — diagnosticos, mutation de creacion
- `lucide-react` — GripVertical, Plus, Trash2, AlertCircle, CheckSquare, Loader2, FileText
- `framer-motion` — animaciones de items

**File Location:**
- Modal: `src/components/treatment-plans/CreatePlanModal.tsx`
- Busqueda CUPS: reusa `src/components/clinical-records/CUPSSearchInput.tsx`
- Lista items: `src/components/treatment-plans/PlanItemsList.tsx`
- Item row: `src/components/treatment-plans/PlanItemRow.tsx`
- Auto-generar sheet: `src/components/treatment-plans/AutoGenerateSheet.tsx`
- Schema: `src/lib/schemas/treatment-plans.ts`
- Hook: `src/hooks/useCreateTreatmentPlan.ts`

**Hooks Used:**
- `useForm()` — React Hook Form
- `useFieldArray({ name: "items" })` — lista de items del plan
- `useSortable()` de `@dnd-kit/sortable` — drag-and-drop
- `useQuery(['patient-diagnoses', patientId, 'active'])` — diagnosticos
- `useMutation()` — crear plan, generar cotizacion, auto-generar
- `useAuth()`, `usePatientStore()` — contexto

**Form Library:**
- React Hook Form + Zod con `useFieldArray` para la lista de items. `mode: "onSubmit"`.

---

## Test Cases

### Happy Path
1. Crear plan manual con 3 procedimientos
   - **Given:** Doctor abre el modal, escribe titulo, agrega 3 CUPS con precios
   - **When:** Click "Crear plan"
   - **Then:** POST exitoso, modal cierra, navega a FE-TP-03 detalle del plan creado

2. Auto-generar desde odontograma
   - **Given:** Paciente con odontograma que tiene caries en 3 dientes
   - **When:** Click "Auto-generar desde odontograma" → selecciona 2 de 3 sugerencias
   - **Then:** Los 2 items seleccionados aparecen en la lista del plan con precios del catalogo

3. Generar cotizacion durante creacion
   - **Given:** Plan con 2 items y precios
   - **When:** Click "Generar cotizacion" (antes de crear el plan)
   - **Then:** Toast con link "Ver cotizacion generada"; la cotizacion se crea en el sistema

### Edge Cases
1. Reordenar items con drag-and-drop (tablet)
   - **Given:** 3 items en el plan
   - **When:** Long-press en handle del item 3, arrastrar a posicion 1
   - **Then:** Items reordenados visualmente; `orden` actualizado en el estado local

2. Precio del catalogo vs precio editado
   - **Given:** CUPS con precio de catalogo $85,000; doctor cambia a $70,000
   - **When:** Se muestra la fila del item
   - **Then:** $85,000 tachado en gris + $70,000 en el input editable

3. Intentar crear plan sin items
   - **Given:** Titulo lleno pero sin items en la lista
   - **When:** Click "Crear plan"
   - **Then:** Error "Agrega al menos un procedimiento al plan" sobre la lista

### Error Cases
1. Error de red al crear
   - **Given:** Sin conexion al hacer click "Crear plan"
   - **When:** POST falla
   - **Then:** Toast de error. Datos del formulario conservados.

2. Auto-generar sin odontograma
   - **Given:** Paciente sin odontograma registrado
   - **When:** Click "Auto-generar"
   - **Then:** Toast de error: "El paciente no tiene odontograma registrado para auto-generar"

---

## Acceptance Criteria

- [ ] Campo titulo con validacion (min 3, max 120 chars) y contador de caracteres
- [ ] Campo descripcion opcional (max 500)
- [ ] Multi-select de diagnosticos activos del paciente
- [ ] Buscador CUPS con precio del catalogo (integra FE-CR-07 con showPrice=true)
- [ ] Lista de items con: nombre + codigo CUPS, diente(s), precio catalogo, precio editable, boton eliminar
- [ ] Drag-and-drop para reordenar (long-press tablet, mouse desktop)
- [ ] Precio editable inline por item
- [ ] Precio del catalogo visible y tachado cuando difiere del precio editado
- [ ] Total corriente en tiempo real en COP
- [ ] Auto-generar desde odontograma: loading → bottom sheet → confirmacion por checkbox
- [ ] Boton "Generar cotizacion" disponible antes de crear el plan
- [ ] Validacion Zod con errores inline en es-419
- [ ] Guardado como borrador sin validacion completa
- [ ] Exito: navega al detalle del plan creado (FE-TP-03)
- [ ] Responsive: botones subir/bajar en mobile, drag en tablet+
- [ ] Touch targets 44px en tablet
- [ ] Accesibilidad: aria-live en total, role="listitem" por item
- [ ] Precios formateados en COP

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
