# Formulario de Procedimiento — Frontend Spec

## Overview

**Screen:** Formulario para registrar un procedimiento odontologico ejecutado. Incluye busqueda de codigo CUPS, selector de diente y zona multi-select, lista dinamica de materiales utilizados (nombre, lote, cantidad), duracion en minutos, seleccion de plantilla de evolucion si existe para ese CUPS, formulario de pasos con variables cuando se usa plantilla, y vinculacion opcional a un item de plan de tratamiento activo.

**Route:** Modal sobre `/patients/{id}/records` o embebido en FE-CR-02 con tipo "Procedimiento"

**Priority:** High

**Backend Specs:**
- `specs/clinical-records/CR-12-create-procedure.md`
- `specs/clinical-records/CR-11-cups-search.md`
- `specs/clinical-records/CR-15-evolution-templates.md`

**Dependencies:**
- `specs/frontend/clinical-records/cups-search.md` — componente CUPS reutilizable (FE-CR-07)
- `specs/frontend/clinical-records/record-create.md` — puede embeberse en FE-CR-02
- `specs/frontend/treatment-plans/plan-detail.md` — para vincular a items del plan (FE-TP-03)
- `specs/frontend/odontogram/odontogram-selector.md` — selector de dientes

---

## User Flow

**Entry Points:**
- Seleccion de tipo "Procedimiento" en el modal FE-CR-02
- Boton "Registrar Procedimiento" dentro del detalle de un item de plan de tratamiento
- Acceso directo desde la vista de odontograma (registrar procedimiento en diente seleccionado)

**Exit Points:**
- Guardado exitoso → modal cierra → registro creado en lista + item del plan marcado como ejecutado (si estaba vinculado)
- Cancelar → dialog de confirmacion si hay datos → cierra sin guardar

**User Story:**
> As a doctor | assistant, I want to document a completed dental procedure with its CUPS code, teeth involved, materials used, and duration so that there is a complete and auditable clinical record of every intervention.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`

---

## Layout Structure

```
+--------------------------------------------------+
|  [X] Registrar Procedimiento                     |
+--------------------------------------------------+
|                                                  |
|  Procedimiento (CUPS):                           |
|  [89.07 — Examen dental completo...    ]  [X]   |
|                                                  |
|  [! Plantilla disponible para este CUPS]         |
|  [Usar plantilla de evolucion v]                 |
|                                                  |
|  Diente(s) / Zona:                               |
|  [Mini odontograma multi-select]                 |
|  Zonas: [ ] Superior D  [ ] Superior I ...       |
|                                                  |
|  -- Si hay plantilla seleccionada: ------------- |
|  Paso 1: Preparacion del campo operatorio       |
|    Anestesia utilizada: [____________]           |
|    Tecnica: [____________]                       |
|  Paso 2: ...                                     |
|  -- Si NO hay plantilla: ----------------------- |
|  Notas del procedimiento: [rich text editor]     |
|  -------------------------------------------------|
|                                                  |
|  Materiales utilizados:                          |
|  [Material 1]: [Nombre] [Lote] [Cantidad] [X]   |
|  [Material 2]: [Nombre] [Lote] [Cantidad] [X]   |
|  [+ Agregar material]                            |
|                                                  |
|  Duracion: [___] minutos                         |
|                                                  |
|  Vincular a plan de tratamiento: [Select v]      |
|                                                  |
|  ---------------------------------------------- |
|  [Cancelar]                        [Guardar]     |
+--------------------------------------------------+
```

**Sections:**
1. Header modal
2. Campo CUPS — busqueda con autocompletado (FE-CR-07)
3. Banner plantilla — si existe plantilla para el CUPS seleccionado, ofrece usarla
4. Selector diente/zona — multi-select visual
5. Contenido del procedimiento — pasos de plantilla con variables O editor de notas libre
6. Materiales — lista dinamica de materiales con lote y cantidad
7. Duracion — input numerico en minutos
8. Vinculacion a plan — select de items activos del plan de tratamiento
9. Footer — Cancelar + Guardar

---

## UI Components

### Component 1: CUPSSearchEmbedded

**Type:** Combobox (reutiliza FE-CR-07)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | CUPSItem \| null | null | Codigo seleccionado |
| onChange | function | — | Callback que tambien dispara busqueda de plantilla |
| error | string \| undefined | — | Error de validacion |

**Behavior:**
- Al seleccionar un CUPS, dispara `GET /evolution-templates?cups={codigo}` para verificar si existe plantilla
- Ver especificacion completa en FE-CR-07

---

### Component 2: BannerPlantillaDisponible

**Type:** Alert / Banner informativo

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| plantilla | PlantillaEvolucion | — | Datos de la plantilla disponible |
| onUse | function | — | Callback al hacer click "Usar plantilla" |
| onDismiss | function | — | Callback al descartar la sugerencia |
| isActive | boolean | false | Si la plantilla ya esta siendo usada |

**States:**
- Disponible (no activa) — banner azul claro con CTA "Usar plantilla de evolucion"
- Activa — banner verde con texto "Usando plantilla: {nombre}" + boton "Quitar plantilla"
- Oculto — cuando no hay plantilla para el CUPS o el usuario la descarto

**Behavior:**
- Aparece con slide-down 200ms cuando se detecta plantilla para el CUPS
- Al hacer click "Usar plantilla": reemplaza el editor libre con el formulario de pasos
- Al hacer click "Quitar plantilla": confirma si hay variables llenas, luego vuelve al editor libre

---

### Component 3: SelectorDientesMulti

**Type:** Multi-select con mini odontograma

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| selectedDientes | string[] | [] | Dientes seleccionados (notacion FDI) |
| selectedZonas | string[] | [] | Zonas seleccionadas |
| onChangeDientes | function | — | Callback al cambiar dientes |
| onChangeZonas | function | — | Callback al cambiar zonas |
| mode | "diente" \| "zona" \| "ambos" | "diente" | Modo de seleccion |

**States:**
- Default — odontograma con todos los dientes en gris
- Diente seleccionado — diente resaltado en azul con numero
- Multiples seleccionados — varios dientes en azul
- Con zona seleccionada — cuadrante con borde azul

**Behavior:**
- Mini odontograma visual (simplified, no full odontogram): cuadricula de dientes numerados en FDI
- Click en diente: selecciona/deselecciona (toggle)
- Input de texto debajo del odontograma para ingresar numero FDI directamente (sugerencias al escribir)
- Checkboxes de zonas debajo: Superior Derecho (1er cuadrante), Superior Izquierdo (2do), Inferior Izquierdo (3ro), Inferior Derecho (4to), + sextantes opcionales
- Los dientes y zonas pueden combinarse (ej: procedimiento en zona y dientes especificos de esa zona)

---

### Component 4: PasosPlantilla

**Type:** Step form con variables

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| pasos | PasoPlantilla[] | [] | Pasos de la plantilla seleccionada |
| values | Record<string, string> | {} | Valores actuales de las variables |
| onChange | function | — | Callback al cambiar cualquier variable |
| errors | Record<string, string> | {} | Errores por variable |

**Behavior:**
- Cada paso renderizado como card con numero, titulo y descripcion
- Variables `{{nombre_variable}}` dentro del texto del paso se reemplazan por inputs de texto
- Los inputs se muestran inline dentro del contexto del texto del paso
- Variable no llenada: input con borde punteado amarillo + label del nombre de la variable
- Variable llenada: texto normal con fondo amarillo suave

---

### Component 5: ListaMateriales

**Type:** Dynamic list

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | MaterialUsado[] | [] | Lista de materiales |
| onChange | function | — | Callback al cambiar |
| errors | FieldErrors | {} | Errores por item y campo |

**Behavior:**
- Cada item: 3 campos en fila — nombre (text, autocomplete catalogo), lote (text), cantidad (number)
- Boton X al final de cada fila para eliminar
- Boton "+ Agregar material" al final de la lista
- Minimo 0 materiales (campo opcional)
- Maximo 30 materiales
- Nombre con busqueda en catalogo de materiales del tenant (debounce 300ms)

---

### Component 6: VinculacionPlanTratamiento

**Type:** Select con preview

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientId | string | — | Para cargar items del plan activo |
| cupsSeleccionado | string \| null | null | Para pre-filtrar items relevantes |
| value | string \| null | null | ID del item seleccionado |
| onChange | function | — | Callback al seleccionar |

**States:**
- Default — placeholder "Sin vincular a plan de tratamiento"
- Con CUPS seleccionado — lista pre-filtrada por CUPS compatibles
- Item seleccionado — muestra resumen del item del plan

**Behavior:**
- Carga items del plan de tratamiento activo del paciente
- Si hay CUPS seleccionado, pre-filtra items que coincidan con ese CUPS
- Select muestra: nombre del procedimiento + diente(s) del item del plan
- Al seleccionar, muestra badge con el plan al que pertenece

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| cups_codigo | string | Yes | CUPS valido del buscador | "Selecciona un procedimiento CUPS" | "Buscar procedimiento..." |
| dientes | string[] | No | Valores FDI validos (11-85) | "Numero de diente no valido" | — |
| zonas | string[] | No | Cuadrante/sextante valido | — | — |
| plantilla_id | string | No | UUID valido si se usa plantilla | — | — |
| variables | Record | Cond. | Todas las vars requeridas si hay plantilla | "Completa: {{nombre_var}}" | Depende de la variable |
| notas | rich text | Cond. | Min 5 chars si no hay plantilla | "Agrega notas del procedimiento" | "Describe el procedimiento realizado..." |
| materiales[].nombre | string | Cond. | Min 2 chars si se agrega material | "Nombre del material requerido" | "Ej: Composite Z100" |
| materiales[].lote | string | No | Max 50 chars | "Maximo 50 caracteres" | "Numero de lote" |
| materiales[].cantidad | number | Cond. | Min 0.01 si se agrega material | "Cantidad debe ser mayor a 0" | "Cantidad" |
| duracion_minutos | number | No | 1-480 (8 horas max) | "Duracion entre 1 y 480 minutos" | "Duracion en minutos" |
| plan_item_id | string | No | UUID valido si se selecciona | — | — |

**Zod Schema:**
```typescript
const materialSchema = z.object({
  nombre: z.string().min(2, "Nombre del material requerido").max(100),
  lote: z.string().max(50).optional(),
  cantidad: z.number().positive("Cantidad debe ser mayor a 0"),
  unidad: z.string().optional(),
});

const procedimientoSchema = z.object({
  cups_codigo: z.string().min(3, "Selecciona un procedimiento CUPS"),
  cups_descripcion: z.string(),
  dientes: z.array(z.string()).optional(),
  zonas: z.array(z.string()).optional(),
  plantilla_id: z.string().uuid().optional(),
  variables: z.record(z.string()).optional(),
  notas: z.string().min(5, "Agrega notas del procedimiento").optional(),
  materiales: z.array(materialSchema).max(30).optional(),
  duracion_minutos: z.number().int().min(1).max(480).optional(),
  plan_item_id: z.string().uuid().optional(),
}).refine(
  (data) => !!data.plantilla_id || (!!data.notas && data.notas.length >= 5),
  { message: "Agrega notas o usa una plantilla de evolucion", path: ["notas"] }
);
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Buscar CUPS | `/api/v1/cups/search?q={query}` | GET | `specs/clinical-records/CR-11-cups-search.md` | 30min |
| Verificar plantilla por CUPS | `/api/v1/tenant/evolution-templates?cups={codigo}` | GET | `specs/clinical-records/CR-15-evolution-templates.md` | 10min |
| Cargar items plan activo | `/api/v1/patients/{id}/treatment-plans/active/items` | GET | `specs/treatment-plans/TP-04.md` | 5min |
| Crear procedimiento | `/api/v1/patients/{id}/procedures` | POST | `specs/clinical-records/CR-12-create-procedure.md` | None |

### State Management

**Local State (useState):**
- `cupsSeleccionado: CUPSItem | null`
- `plantillaDisponible: PlantillaEvolucion | null`
- `usandoPlantilla: boolean`
- `isSubmitting: boolean`

**Global State (Zustand):**
- `patientStore.currentPatient` — paciente activo

**Server State (TanStack Query):**
- Query key CUPS: `['cups-search', query]`
- Query key plantilla: `['evolution-template-by-cups', cupsCode, tenantId]`
- Query key plan items: `['treatment-plan-active-items', patientId]`
- Mutation: `useMutation({ mutationFn: createProcedure })` — invalida `['clinical-records', patientId]` y `['treatment-plan', planId]` en onSuccess

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `invalid_cups` | 422 | "Codigo CUPS no valido" |
| `template_mismatch` | 422 | "La plantilla no corresponde a este procedimiento" |
| `plan_item_not_found` | 404 | "El item del plan de tratamiento no fue encontrado" |
| `forbidden` | 403 | "No tienes permisos para registrar procedimientos" |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Buscar CUPS | Typing | Debounced search 300ms | Dropdown de resultados |
| Seleccionar CUPS | Click o Enter | CUPS lleno + busca plantilla disponible | Input con codigo y descripcion |
| Detectar plantilla | Auto (al seleccionar CUPS) | Banner aparece si hay plantilla | Slide-down del banner 200ms |
| Usar plantilla | Click "Usar plantilla de evolucion" | Reemplaza editor con pasos de plantilla | Transicion 200ms |
| Quitar plantilla | Click "Quitar plantilla" | Vuelve al editor libre | Dialog si hay variables llenas |
| Seleccionar diente | Click en mini odontograma | Diente toggle seleccionado/deseleccionado | Diente resaltado en azul |
| Agregar material | Click "+ Agregar material" | Nueva fila en la lista de materiales | Fila fade-in |
| Eliminar material | Click X en fila | Fila eliminada | Fade-out |
| Guardar | Click "Guardar" | Valida + POST | Spinner, toast, cierre modal |

### Animations/Transitions

- Banner plantilla: slide-down 200ms ease-out
- Cambio editor libre ↔ pasos plantilla: cross-dissolve 200ms
- Nueva fila material: fade-in 150ms
- Eliminacion fila material: fade-out + height collapse 150ms
- Modal: slide-up en mobile/tablet, fade-in en desktop

---

## Loading & Error States

### Loading State
- Busqueda de plantilla por CUPS: spinner mini junto al input de CUPS durante la verificacion
- Items del plan: skeleton de 3 opciones en el select de vinculacion
- Submission: spinner en boton "Guardar", todos los campos disabled

### Error State
- Errores Zod inline bajo cada campo en `text-xs text-red-600`
- Error de variable de plantilla vacia: campo con borde rojo punteado + mensaje bajo el input
- Error de API: toast destructivo con mensaje especifico

### Empty State
- Sin materiales: lista de materiales vacia con solo el boton "+ Agregar material"
- Sin items de plan activo: "No hay items de plan de tratamiento activo para vincular"
- Sin plantilla para el CUPS: banner no aparece (estado silencioso)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Modal full-screen. Mini odontograma compacto. Materiales en cards apiladas (no en fila). Footer sticky. |
| Tablet (640-1024px) | Modal max-w-xl 90vh. Mini odontograma full. Materiales en fila de 3 columnas. Touch targets 44px. Layout primario. |
| Desktop (> 1024px) | Modal max-w-2xl. Dos columnas para algunos campos (CUPS + duracion en una fila, dientes + vinculacion en otra). |

**Tablet priority:** High — procedimientos se registran en tablet durante o inmediatamente despues de la intervencion. Mini odontograma con areas de toque de minimo 32x32px (target expandido a 44px). Lista de materiales con inputs de minimo 44px de altura.

---

## Accessibility

- **Focus order:** CUPS → (si hay banner plantilla: boton "Usar") → Selector dientes → contenido (pasos o editor) → Materiales → Duracion → Vinculacion plan → Cancelar → Guardar
- **Screen reader:** `role="dialog"` con `aria-label="Registrar procedimiento"`. Banner plantilla: `role="status"` con `aria-live="polite"`. Cada paso de plantilla: `aria-label="Paso {n}: {titulo}"`.
- **Keyboard navigation:** `Tab` entre campos. `Space`/`Enter` en dientes del odontograma. Arrow keys en selects. `Escape` cierra modal.
- **Color contrast:** WCAG AA. Variables destacadas con borde y fondo ademas de color.
- **Language:** es-419. Nombres de zonas en nomenclatura dental latinoamericana.

---

## Design Tokens

**Colors:**
- Banner plantilla disponible: `bg-blue-50 border border-blue-200 text-blue-700`
- Banner plantilla activa: `bg-green-50 border border-green-200 text-green-700`
- Diente seleccionado: `bg-blue-500 text-white`
- Input variable no llenada: `border-dashed border-yellow-400 bg-yellow-50`
- Input variable llenada: `bg-yellow-50 border-yellow-200`
- Fila material: `bg-gray-50 border border-gray-200 rounded-lg`

**Typography:**
- Codigo CUPS: `font-mono text-sm font-bold text-gray-800`
- Descripcion CUPS: `text-sm text-gray-600`
- Titulo paso plantilla: `text-sm font-semibold text-gray-800`
- Label nombre variable: `text-xs text-yellow-700 font-medium`

**Spacing:**
- Modal padding: `p-6`
- Gap secciones: `space-y-6`
- Fila material gap: `gap-3`
- Paso plantilla padding: `p-4`

**Border Radius:**
- Modal: `rounded-2xl`
- Banner plantilla: `rounded-lg`
- Paso plantilla: `rounded-lg`
- Inputs: `rounded-md`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers` — con `useFieldArray` para materiales
- `@tanstack/react-query` — busqueda CUPS, plantilla, items plan, mutation creacion
- `@tiptap/react` — editor rich text para notas libres
- `lucide-react` — Search, Plus, Trash2, AlertCircle, CheckCircle, Info, X
- `framer-motion` — animaciones de banner y fila de materiales

**File Location:**
- Modal: `src/components/clinical-records/ProcedureFormModal.tsx`
- CUPS search: `src/components/clinical-records/CUPSSearchInput.tsx` (ver FE-CR-07)
- Odontograma mini: `src/components/odontogram/MiniToothSelector.tsx`
- Pasos plantilla: `src/components/clinical-records/TemplateStepsForm.tsx`
- Materiales: `src/components/clinical-records/MaterialesList.tsx`
- Schema: `src/lib/schemas/procedure.ts`
- Hook: `src/hooks/useCreateProcedure.ts`

**Hooks Used:**
- `useForm()` — React Hook Form con schema Zod
- `useFieldArray({ name: "materiales" })` — lista dinamica de materiales
- `useQuery(['evolution-template-by-cups', cupsCode])` — verificacion de plantilla
- `useQuery(['treatment-plan-active-items', patientId])` — items del plan
- `useMutation()` — crear procedimiento
- `useAuth()` y `usePatientStore()` — contexto

**Form Library:**
- React Hook Form + Zod. `mode: "onBlur"` para campos individuales, validacion completa al submit.

---

## Test Cases

### Happy Path
1. Procedimiento con plantilla de evolucion
   - **Given:** Doctor selecciona CUPS con plantilla disponible, banner aparece
   - **When:** Click "Usar plantilla", llena todas las variables y guarda
   - **Then:** Procedimiento creado con contenido generado desde la plantilla + variables

2. Procedimiento vinculado a plan de tratamiento
   - **Given:** Paciente con plan activo que tiene item de extraccion (CUPS 23.09)
   - **When:** Doctor selecciona CUPS 23.09, vincula al item del plan, guarda
   - **Then:** Procedimiento creado, item del plan marcado como "Ejecutado"

3. Procedimiento con materiales
   - **Given:** Doctor registra restauracion con 2 materiales utilizados
   - **When:** Agrega Composite Z100 lote A1234 cantidad 1, y Acido grabador lote B567 cantidad 0.5
   - **Then:** POST incluye los 2 materiales con todos sus campos

### Edge Cases
1. CUPS sin plantilla disponible
   - **Given:** Doctor selecciona CUPS que no tiene plantilla configurada
   - **When:** El query de plantilla retorna vacio
   - **Then:** Banner no aparece; editor de notas libre siempre visible

2. Quitar plantilla con variables llenas
   - **Given:** Doctor uso una plantilla y lleno 3 de 5 variables
   - **When:** Hace click "Quitar plantilla"
   - **Then:** Dialog: "Quitar la plantilla borrara las variables que llenaste. ¿Continuar?"

3. Materiales sin numero de lote
   - **Given:** Doctor agrega material sin lote (campo opcional)
   - **When:** Guarda el procedimiento
   - **Then:** Material guardado correctamente sin numero de lote

### Error Cases
1. Intentar guardar sin CUPS
   - **Given:** Formulario con materiales y notas pero sin CUPS seleccionado
   - **When:** Click "Guardar"
   - **Then:** Error inline bajo CUPS: "Selecciona un procedimiento CUPS". Campo resaltado con borde rojo.

2. Sin notas y sin plantilla
   - **Given:** Doctor selecciona CUPS, agrega diente y materiales pero no escribe notas ni usa plantilla
   - **When:** Click "Guardar"
   - **Then:** Error: "Agrega notas o usa una plantilla de evolucion"

---

## Acceptance Criteria

- [ ] Busqueda CUPS con debounce (integra FE-CR-07)
- [ ] Deteccion automatica de plantilla al seleccionar CUPS (query al backend)
- [ ] Banner "Plantilla disponible" con CTA y estado activo/inactivo
- [ ] Formulario de pasos con variables cuando se usa plantilla
- [ ] Editor rich text cuando NO se usa plantilla
- [ ] Mini odontograma multi-select con soporte de dientes y zonas
- [ ] Lista dinamica de materiales con nombre, lote, cantidad (max 30 items)
- [ ] Input de duracion en minutos (1-480)
- [ ] Vinculacion a item de plan de tratamiento activo
- [ ] Al guardar con vinculacion: item del plan se actualiza a "Ejecutado"
- [ ] Validacion Zod con errores inline en es-419
- [ ] Toast de exito + cierre modal + invalida cache de registros y plan
- [ ] Responsive: materiales en cards mobile, filas tablet+
- [ ] Touch targets minimo 44px
- [ ] Accesibilidad: role="dialog", aria-live para deteccion plantilla
- [ ] Textos en es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
