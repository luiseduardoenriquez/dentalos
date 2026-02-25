# Crear Registro Clinico — Frontend Spec

## Overview

**Screen:** Modal (o ruta dedicada en mobile) para crear un nuevo registro clinico. El formulario es dinamico: cambia completamente segun el tipo de registro seleccionado (anamnesis, examen, nota de evolucion, procedimiento). Para notas de evolucion soporta seleccion de plantilla que pre-llena los pasos con variables editables. Incluye auto-guardado de borrador cada 30 segundos.

**Route:** Modal sobre `/patients/{id}/records` | fallback ruta `/patients/{id}/records/new` en mobile

**Priority:** High

**Backend Specs:**
- `specs/clinical-records/CR-01-create-record.md`
- `specs/clinical-records/CR-05-anamnesis.md`
- `specs/clinical-records/CR-15-evolution-templates.md`

**Dependencies:**
- `specs/frontend/clinical-records/record-list.md` — pantalla padre (FE-CR-01)
- `specs/frontend/clinical-records/anamnesis-form.md` — formulario anamnesis embebido (FE-CR-03)
- `specs/frontend/clinical-records/procedure-form.md` — formulario procedimiento embebido (FE-CR-05)
- `specs/frontend/odontogram/odontogram-selector.md` — selector de dientes

---

## User Flow

**Entry Points:**
- Click en opcion del dropdown "+ Nuevo Registro" en FE-CR-01
- Acceso directo a `/patients/{id}/records/new` con `?type=` query param

**Exit Points:**
- Guardado exitoso → cierra modal → lista recarga con nuevo registro al tope
- Cancelar / Escape → cierra modal → confirma si hay datos no guardados (dialog de confirmacion)
- Guardado como borrador → cierra modal → registro queda en estado `draft`

**User Story:**
> As a doctor | assistant, I want to create a new clinical record with a type-specific form so that I can document patient consultations, procedures, and examinations in a structured and complete way.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`

---

## Layout Structure

```
+--------------------------------------------------+
|  [X] Nuevo Registro Clinico          [Borrador]  |
+--------------------------------------------------+
|                                                  |
|  Tipo de registro:                               |
|  [Anamnesis] [Examen] [Evolucion] [Procedimiento]|
|                                                  |
|  ------------------------------------------------|
|  [Contenido dinamico segun tipo seleccionado]    |
|                                                  |
|  -- Anamnesis: ver FE-CR-03                     |
|  -- Examen: rich text + chips de dientes        |
|  -- Evolucion: selector plantilla + pasos       |
|  -- Procedimiento: CUPS + dientes + materiales  |
|                                                  |
|  ------------------------------------------------|
|  Auto-guardado: hace 5 seg     [Cancelar] [Guardar]|
+--------------------------------------------------+
```

**Sections:**
1. Header modal — titulo, boton cerrar, indicador de estado borrador
2. Selector de tipo — tabs/pills para el tipo de registro (pre-seleccionado si viene de FE-CR-01)
3. Formulario dinamico — contenido cambia completamente segun tipo
4. Footer — indicador de auto-guardado, boton Cancelar, boton Guardar (+ opcion Guardar como borrador)

---

## UI Components

### Component 1: SelectorTipoRegistro

**Type:** Tab group / Pills selector

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.5

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | TipoRegistro | "examen" | Tipo actualmente seleccionado |
| onChange | function | — | Callback al cambiar tipo |
| disabled | boolean | false | Deshabilita si hay datos no guardados |

**States:**
- Active tab — subrayado + fondo `bg-blue-50`
- Inactive — texto gris
- Disabled — opacidad 50% con tooltip "Cambiara el tipo borrara el progreso actual"

**Behavior:**
- Cambiar tipo muestra dialog de confirmacion si hay datos no guardados
- Pre-seleccionado desde query param `?type=`
- Cada tab tiene su icono y label en español

---

### Component 2: FormularioExamen

**Type:** Form con rich text editor

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientId | string | — | Para cargar contexto de dientes |
| initialData | ExamenData \| null | null | Para edicion o borrador |
| onChange | function | — | Callback para auto-guardado |

**Behavior:**
- Rich text editor (Tiptap) con toolbar: negrita, cursiva, listas, salto de linea
- Chips de dientes: boton "Agregar diente" abre mini selector → inserta chip `[Diente 21]` en el texto
- Los chips son no editables inline pero tienen boton X para eliminarlos

---

### Component 3: FormularioEvolucion

**Type:** Form con selector de plantilla + pasos dinamicos

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientId | string | — | Para sugerir plantillas relevantes |
| templates | PlantillaEvolucion[] | [] | Lista de plantillas disponibles |
| selectedTemplate | PlantillaEvolucion \| null | null | Plantilla activa |
| onTemplateSelect | function | — | Callback al elegir plantilla |

**States:**
- Sin plantilla — rich text editor libre
- Plantilla seleccionada — formulario de pasos con variables resaltadas

**Behavior:**
- Boton "Usar plantilla" abre bottom sheet con lista de plantillas (CR-15)
- Al seleccionar plantilla, el formulario se reemplaza con los pasos de la plantilla
- Cada paso tiene inputs para las variables `{{variable}}` destacadas en amarillo
- "Sin plantilla" revierte al editor libre (con confirmacion si hay datos)
- Variables son campos de texto inline dentro del contexto del paso

---

### Component 4: IndicadorAutoGuardado

**Type:** Status indicator

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| status | "idle" \| "saving" \| "saved" \| "error" | "idle" | Estado del auto-guardado |
| lastSavedAt | Date \| null | null | Timestamp del ultimo guardado |

**States:**
- `idle` — no muestra nada
- `saving` — spinner + "Guardando borrador..."
- `saved` — checkmark verde + "Guardado hace X seg"
- `error` — icono rojo + "Error al guardar. Reintentando..."

**Behavior:**
- Auto-guardado se dispara 30 segundos despues del ultimo cambio (debounce)
- Solo guarda si hay contenido minimo (titulo o algun campo lleno)

---

### Component 5: SelectorPlantillaEvolucion

**Type:** Bottom sheet / Modal de seleccion

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.8

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| templates | PlantillaEvolucion[] | [] | Plantillas disponibles del tenant |
| onSelect | function | — | Callback al seleccionar |
| onClose | function | — | Cierra el selector |

**States:**
- Lista — muestra plantillas con nombre, descripcion y vista previa de pasos
- Empty — "No hay plantillas disponibles" con link a configuracion
- Loading — skeleton de 3 items

**Behavior:**
- Busqueda de texto en el top del bottom sheet
- Click en plantilla muestra preview de pasos antes de confirmar
- Boton "Usar esta plantilla" confirma la seleccion

---

## Form Fields

### Campos comunes a todos los tipos:

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| tipo | select | Yes | Uno de los 4 tipos validos | "Selecciona el tipo de registro" | — |
| fecha | date | Yes | No futura (max = hoy) | "La fecha no puede ser futura" | "dd/mm/aaaa" |
| notas_adicionales | textarea | No | Max 2000 chars | "Maximo 2000 caracteres" | "Notas adicionales..." |

### Campos de Examen:

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| contenido | rich text | Yes | Min 10 chars | "El examen debe tener al menos 10 caracteres" | "Describe los hallazgos del examen..." |
| dientes_referenciados | chips array | No | IDs validos de dientes | "Diente no valido" | — |

### Campos de Evolucion (sin plantilla):

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| contenido | rich text | Yes | Min 10 chars | "La nota debe tener al menos 10 caracteres" | "Escribe la nota de evolucion..." |

### Campos de Evolucion (con plantilla):

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| plantilla_id | string | Yes | UUID valido | — | — |
| variables | object | Yes | Todas las variables requeridas llenas | "Completa: {{nombre_variable}}" | Depende de la variable |

**Zod Schema (examen como ejemplo):**
```typescript
const examenSchema = z.object({
  tipo: z.literal("examen"),
  fecha: z.date().max(new Date(), "La fecha no puede ser futura"),
  contenido: z.string().min(10, "El examen debe tener al menos 10 caracteres"),
  dientes_referenciados: z.array(z.string()).optional(),
  notas_adicionales: z.string().max(2000).optional(),
});

const evolucionConPlantillaSchema = z.object({
  tipo: z.literal("evolucion"),
  fecha: z.date().max(new Date(), "La fecha no puede ser futura"),
  plantilla_id: z.string().uuid(),
  variables: z.record(z.string().min(1, "Este campo es obligatorio")),
  notas_adicionales: z.string().max(2000).optional(),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Crear registro | `/api/v1/patients/{id}/clinical-records` | POST | `specs/clinical-records/CR-01-create-record.md` | None |
| Guardar borrador | `/api/v1/patients/{id}/clinical-records/draft` | PUT | `specs/clinical-records/CR-01-create-record.md` | None |
| Listar plantillas | `/api/v1/tenant/evolution-templates` | GET | `specs/clinical-records/CR-15-evolution-templates.md` | 10min |

### State Management

**Local State (useState):**
- `tipoActivo: TipoRegistro` — tipo de registro seleccionado
- `plantillaSeleccionada: PlantillaEvolucion | null` — plantilla activa para evolucion
- `autoGuardadoStatus: AutoGuardadoStatus` — estado del auto-guardado
- `lastSavedAt: Date | null` — timestamp del ultimo borrador guardado
- `showCancelDialog: boolean` — dialog de confirmacion al cancelar con datos

**Global State (Zustand):**
- `patientStore.currentPatient` — paciente activo (id, nombre)
- `clinicalRecordStore.draftData` — borrador temporal para recuperacion en caso de cierre accidental

**Server State (TanStack Query):**
- Query key: `['evolution-templates', tenantId]` (lista de plantillas)
- Stale time: 10 minutos
- Mutation: `useMutation({ mutationFn: createClinicalRecord })` para guardar
- Mutation: `useMutation({ mutationFn: saveDraft })` para auto-guardado (no invalida cache principal)

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `patient_not_found` | 404 | "Paciente no encontrado" |
| `invalid_template` | 422 | "La plantilla seleccionada no es valida" |
| `missing_variables` | 422 | "Faltan campos en la plantilla: {variables}" |
| `forbidden` | 403 | "No tienes permisos para crear registros" |
| `server_error` | 500 | "Error al guardar el registro. Intenta de nuevo." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Cambiar tipo (sin datos) | Click en tab de tipo | Cambia formulario inmediatamente | Transicion suave del contenido |
| Cambiar tipo (con datos) | Click en tab de tipo | Dialog de confirmacion | Modal: "Cambiar el tipo borrara el contenido actual" |
| Confirmar cambio de tipo | Click "Continuar" en dialog | Limpia form y muestra nuevo tipo | Form se resetea |
| Seleccionar plantilla | Click "Usar plantilla" | Bottom sheet con plantillas | Slide-up del bottom sheet |
| Elegir plantilla | Click en plantilla + "Usar esta plantilla" | Form de pasos con variables | Transicion 200ms |
| Quitar plantilla | Click "Escribir sin plantilla" | Vuelve a editor libre | Dialog de confirmacion si hay variables llenas |
| Llenar campo auto-guardado | Typing | 30s debounce → POST draft | Indicador "Guardando..." |
| Guardar registro | Click "Guardar" | Valida + POST | Spinner en boton, toast success |
| Guardar borrador | Click "Guardar borrador" | POST draft sin validacion completa | Toast "Borrador guardado" |
| Cancelar (sin datos) | Click "Cancelar" o Escape | Cierra modal sin dialog | Cierra inmediatamente |
| Cancelar (con datos) | Click "Cancelar" o Escape | Dialog de confirmacion | Modal: "Tienes cambios sin guardar" |

### Animations/Transitions

- Modal: slide-up desde bottom en tablet/mobile (300ms ease-out), fade-in centrado en desktop
- Cambio de tipo de formulario: fade cross-dissolve 150ms
- Bottom sheet plantillas: slide-up 250ms ease-out con backdrop fade
- Pasos de plantilla: cada paso hace stagger-in 50ms de delay entre items
- Indicador auto-guardado: fade-in del estado, icono checkmark con scale animation

---

## Loading & Error States

### Loading State
- Boton "Guardar" muestra `Loader2` spinner con texto "Guardando..."
- Inputs deshabilitados durante submission
- Carga inicial de plantillas: skeleton de 3 items en bottom sheet
- El formulario en si se muestra inmediatamente (no requiere carga previa)

### Error State
- Errores de validacion Zod: inline debajo de cada campo en `text-xs text-red-600`
- Error de API al guardar: toast destructivo en top-right con mensaje de error
- Error de auto-guardado: indicador de estado cambia a rojo con "Error al guardar. Reintentando..."
- Error de plantilla invalida: toast + vuelve al editor libre automaticamente

### Empty State
- No aplica para el formulario en si
- Lista de plantillas vacia: "No hay plantillas de evolucion disponibles" + link "Crear plantilla" → admin

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-screen (no modal, ruta dedicada). Selector de tipo en scroll horizontal. Footer sticky con botones. Editor ocupa toda la pantalla. |
| Tablet (640-1024px) | Modal full-height (90vh) con scroll interno. Selector de tipo como tabs horizontales. Footer fijo en bottom del modal. Teclado virtual: form hace scroll para mantener campo activo visible. |
| Desktop (> 1024px) | Modal centrado `max-w-2xl max-h-[85vh]` con scroll interno. Layout sin cambios adicionales. |

**Tablet priority:** High — formularios clinicos se usan principalmente en tablet. Todos los inputs tienen min 44px de altura. El boton "Guardar" tiene min 48px de altura. Bottom sheet de plantillas ocupa el 70% de la pantalla.

---

## Accessibility

- **Focus order:** Selector tipo → campos del formulario en orden logico → notas adicionales → Cancelar → Guardar
- **Screen reader:** `role="dialog"` con `aria-labelledby="titulo-nuevo-registro"`. Cada seccion del formulario tiene `aria-label`. Cambio de tipo anuncia `aria-live="assertive"` "Formulario cambiado a {tipo}".
- **Keyboard navigation:** `Tab` navega campos. `Escape` cierra modal (con confirmacion si hay datos). `Enter` en select de tipo cambia tipo. Arrow keys en selector de tipo.
- **Color contrast:** WCAG AA. Labels `text-gray-700` sobre `bg-white` cumple 4.5:1. Errores `text-red-600` sobre `bg-white` cumple 4.5:1.
- **Language:** Todos los labels, placeholders, mensajes de error y textos de confirmacion en es-419.

---

## Design Tokens

**Colors:**
- Modal header: `bg-white border-b border-gray-200`
- Tab activo: `bg-blue-50 text-blue-700 border-b-2 border-blue-600`
- Tab inactivo: `text-gray-500 hover:text-gray-700`
- Variable highlight: `bg-yellow-100 border border-yellow-300 rounded px-1`
- Auto-guardado saved: `text-green-600`
- Auto-guardado error: `text-red-500`

**Typography:**
- Titulo modal: `text-lg font-semibold text-gray-900`
- Label campo: `text-sm font-medium text-gray-700`
- Nombre paso plantilla: `text-sm font-medium text-gray-800`
- Descripcion paso: `text-xs text-gray-500`

**Spacing:**
- Modal padding: `p-6`
- Gap entre campos: `space-y-4`
- Gap entre pasos de plantilla: `space-y-6`
- Footer: `px-6 py-4 border-t border-gray-200`

**Border Radius:**
- Modal: `rounded-2xl` (tablet/desktop)
- Inputs: `rounded-md`
- Chips de diente: `rounded-full`
- Boton guardar: `rounded-lg`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers` — validacion de formulario
- `@tiptap/react` + `@tiptap/starter-kit` — rich text editor
- `@tanstack/react-query` — fetch de plantillas y mutation de guardado
- `lucide-react` — iconos: X, ClipboardList, Stethoscope, FileText, Wrench, CheckCircle, Loader2, AlertCircle
- `framer-motion` — animaciones de modal y transiciones
- `use-debounce` — debounce de 30s para auto-guardado

**File Location:**
- Modal: `src/components/clinical-records/CreateClinicalRecordModal.tsx`
- Forms: `src/components/clinical-records/forms/ExamenForm.tsx`
- Forms: `src/components/clinical-records/forms/EvolucionForm.tsx`
- Forms: `src/components/clinical-records/forms/ProcedimientoForm.tsx`
- Selector plantilla: `src/components/clinical-records/TemplateSelectorSheet.tsx`
- Auto-guardado: `src/components/clinical-records/AutoSaveIndicator.tsx`
- Hooks: `src/hooks/useCreateClinicalRecord.ts`
- Schemas: `src/lib/schemas/clinical-records.ts`

**Hooks Used:**
- `useForm()` — React Hook Form con schema dinamico (cambia segun tipo)
- `useMutation()` — crear registro y guardar borrador
- `useQuery(['evolution-templates', tenantId])` — lista de plantillas
- `useAuth()` — usuario y tenant actuales
- `useDebounce()` — para auto-guardado de 30 segundos
- `useBeforeUnload()` — advertencia si hay datos no guardados al cerrar

**Form Library:**
- React Hook Form con schema Zod dinamico usando `z.discriminatedUnion('tipo', [...])`
- `mode: "onBlur"` para validacion por campo

---

## Test Cases

### Happy Path
1. Crear registro de examen
   - **Given:** Modal abierto con tipo "Examen" pre-seleccionado
   - **When:** Doctor escribe contenido en el rich text editor y hace click en "Guardar"
   - **Then:** Se llama `POST /clinical-records`, modal cierra, lista recarga con nuevo registro al tope

2. Crear nota de evolucion con plantilla
   - **Given:** Modal abierto, tipo "Evolucion" seleccionado
   - **When:** Doctor abre selector de plantillas, selecciona una, llena las variables y guarda
   - **Then:** Registro se crea con contenido generado a partir de la plantilla + variables

3. Auto-guardado funciona
   - **Given:** Doctor empieza a llenar el formulario de examen
   - **When:** Pasan 30 segundos sin guardar manualmente
   - **Then:** Indicador muestra "Guardando borrador..." → "Guardado hace X seg"

### Edge Cases
1. Cambiar tipo con datos existentes
   - **Given:** Doctor lleno la mitad del formulario de examen
   - **When:** Hace click en tab "Procedimiento"
   - **Then:** Dialog de confirmacion aparece; si confirma, form se limpia y muestra procedimiento

2. Plantilla con variables vacias al guardar
   - **Given:** Plantilla seleccionada con 3 variables
   - **When:** Doctor deja 1 variable vacia y hace click en "Guardar"
   - **Then:** Error inline bajo la variable vacia: "Este campo es obligatorio"

3. Cerrar modal con datos no guardados
   - **Given:** Doctor escribio contenido en el editor
   - **When:** Hace click en "X" del modal o presiona Escape
   - **Then:** Dialog: "Tienes cambios sin guardar. ¿Salir sin guardar o guardar borrador?"

### Error Cases
1. Error de red al guardar
   - **Given:** Sin conexion al hacer click en "Guardar"
   - **When:** La mutation falla con error de red
   - **Then:** Toast de error: "Error al guardar el registro. Intenta de nuevo." Boton vuelve a estado normal.

2. Error de auto-guardado
   - **Given:** Auto-guardado falla 3 veces consecutivas
   - **When:** El server retorna error en los intentos de draft
   - **Then:** Indicador muestra "Error al guardar" con boton "Reintentar" manual

---

## Acceptance Criteria

- [ ] Formulario dinamico cambia completamente segun tipo seleccionado (anamnesis, examen, evolucion, procedimiento)
- [ ] Tipo anamnesis delega a FE-CR-03 (AnamnesisForm component)
- [ ] Tipo examen: rich text editor con bold, italic, listas + chips de dientes
- [ ] Tipo evolucion: selector de plantilla → pasos con variables destacadas → guardar con variables llenas
- [ ] Tipo procedimiento: delega a FE-CR-05 (ProcedimientoForm component)
- [ ] Auto-guardado cada 30 segundos con indicador visual de estado
- [ ] Dialog de confirmacion al cambiar tipo con datos existentes
- [ ] Dialog de confirmacion al cancelar con datos existentes
- [ ] Validacion Zod por tipo de registro con errores inline en es-419
- [ ] Estado de carga durante submission (boton spinner, inputs disabled)
- [ ] Toast de exito al guardar + cierre de modal + recarga de lista
- [ ] Toast de error con mensaje especifico al fallar el guardado
- [ ] Responsive: full-screen en mobile, modal 90vh en tablet, modal centrado en desktop
- [ ] Touch targets minimo 44px en tablet
- [ ] Accesibilidad: role="dialog", aria-labelledby, aria-live para cambios de tipo
- [ ] Textos en es-419 incluyendo mensajes de validacion y confirmacion

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
