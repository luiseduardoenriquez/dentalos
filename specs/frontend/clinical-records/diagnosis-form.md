# Formulario de Diagnostico — Frontend Spec

## Overview

**Screen:** Formulario para registrar uno o multiples diagnosticos clinicos usando codigos CIE-10. Permite crear diagnosticos en lote (batch mode) durante el examen inicial, vinculando cada diagnostico a un diente especifico o zona, con nivel de severidad y notas clinicas. Integra el componente reutilizable de busqueda CIE-10 (FE-CR-06).

**Route:** Modal sobre `/patients/{id}/records` o embebido dentro de FE-CR-02 (record-create)

**Priority:** High

**Backend Specs:**
- `specs/clinical-records/CR-07-create-diagnosis.md`
- `specs/clinical-records/CR-10-cie10-search.md`

**Dependencies:**
- `specs/frontend/clinical-records/cie10-search.md` — componente de busqueda CIE-10 (FE-CR-06)
- `specs/frontend/clinical-records/record-create.md` — puede embeberse en FE-CR-02
- `specs/frontend/odontogram/odontogram-selector.md` — mini odontograma para selector de dientes

---

## User Flow

**Entry Points:**
- Boton "Agregar Diagnostico" dentro de un registro clinico de tipo examen
- Menu de acciones rapidas dentro del detalle del paciente
- Embebido en modal FE-CR-02 al crear registro de tipo examen o procedimiento

**Exit Points:**
- Guardado exitoso → cierra modal o vuelve al registro padre → lista de diagnosticos actualizada
- Cancelar → cierra sin guardar → dialog de confirmacion si hay datos

**User Story:**
> As a doctor, I want to record one or more diagnoses using CIE-10 codes, linked to specific teeth, so that I can create a complete diagnostic picture of the patient's condition in a single step.

**Roles with access:** `clinic_owner`, `doctor`

---

## Layout Structure

```
+--------------------------------------------------+
|  [X] Agregar Diagnostico(s)                      |
+--------------------------------------------------+
|                                                  |
|  Diagnostico #1                          [Eliminar]|
|  +----------------------------------------+     |
|  |  Buscar CIE-10:                        |     |
|  |  [K02.1 — Caries de la dentina    v]   |     |
|  |                                        |     |
|  |  Diente(s): [Mini odontograma o #]     |     |
|  |  ( ) Diente especifico  ( ) Zona       |     |
|  |                                        |     |
|  |  Severidad:                            |     |
|  |  (o) Leve   ( ) Moderado   ( ) Severo |     |
|  |                                        |     |
|  |  Notas:                                |     |
|  |  [textarea...]                         |     |
|  +----------------------------------------+     |
|                                                  |
|  [+ Agregar otro diagnostico]                    |
|                                                  |
|  ---------------------------------------------- |
|  [Cancelar]                        [Guardar (1)] |
+--------------------------------------------------+
```

**Sections:**
1. Header modal — titulo, boton cerrar
2. Lista de diagnosticos — uno o mas items, cada uno con busqueda CIE-10, selector diente/zona, severidad y notas
3. Boton agregar — "+ Agregar otro diagnostico" (max 10 por vez)
4. Footer — Cancelar + Guardar con conteo de diagnosticos a crear

---

## UI Components

### Component 1: ItemDiagnostico

**Type:** Form card (un diagnostico individual)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| index | number | — | Posicion en la lista (para label "#N") |
| value | DiagnosticoFormData | — | Datos del diagnostico |
| onChange | function | — | Callback al cambiar cualquier campo |
| onRemove | function | — | Elimina este diagnostico de la lista |
| isOnly | boolean | false | Si es el unico, el boton eliminar esta deshabilitado |
| errors | FieldErrors | {} | Errores de validacion para este item |

**States:**
- Default — todos los campos vacios
- Parcial — CIE-10 seleccionado, otros campos en progreso
- Completo — CIE-10 + diente + severidad llenos (borde verde sutil)
- Error — campos con error marcados en rojo

**Behavior:**
- Header del card muestra "Diagnostico #1", "#2", etc.
- Boton "Eliminar" en esquina superior derecha (disabled si es el unico item)
- Campos en orden logico para flujo clinico: primero el codigo, luego el diente, luego severidad y notas

---

### Component 2: CIE10SearchEmbedded

**Type:** Combobox (reutiliza FE-CR-06)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | CIE10Item \| null | null | Codigo seleccionado |
| onChange | function | — | Callback al seleccionar |
| error | string \| undefined | — | Mensaje de error |
| placeholder | string | "Buscar por codigo o descripcion..." | Placeholder |

**Behavior:** Ver FE-CR-06 para la especificacion completa del componente de busqueda. En este contexto se renderiza como campo integrado en el card del diagnostico.

---

### Component 3: SelectorDientesOZona

**Type:** Radio group + selector interactivo

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| mode | "diente" \| "zona" \| "general" | "general" | Modo de seleccion |
| selectedDientes | string[] | [] | Numeros de dientes seleccionados (FDI) |
| selectedZona | string \| null | null | Zona seleccionada |
| onChange | function | — | Callback al cambiar |

**States:**
- General — no aplica a un diente especifico (default)
- Diente — muestra mini odontograma clickeable o input numerico
- Zona — muestra selector de cuadrantes/sextantes

**Behavior:**
- Radio buttons: "General", "Diente especifico", "Zona"
- Modo "Diente": mini odontograma simplificado (2x2 cuadros con numeracion FDI) O input de numero FDI directo con autocompletado
- Modo "Zona": dropdown con cuadrantes (Superior derecho, Superior izquierdo, Inferior derecho, Inferior izquierdo) y sextantes
- En tablet: mini odontograma visual preferible. En mobile: input numerico con sugerencias
- Multiples dientes pueden seleccionarse (ej: caries en 16 y 17)

---

### Component 4: SeveridadRadioGroup

**Type:** Radio button group

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | "leve" \| "moderado" \| "severo" \| null | null | Severidad seleccionada |
| onChange | function | — | Callback al cambiar |
| error | string \| undefined | — | Mensaje de error |

**States:**
- Sin seleccion — todos los radios sin marcar
- Seleccionado — radio marcado con color por nivel de severidad

**Behavior:**
- Radio visual con colores: leve=verde, moderado=amarillo, severo=rojo
- Cada opcion tiene min 44px de altura touch target
- Label + descripcion breve:
  - Leve: "Condicion incipiente, sin sintomas significativos"
  - Moderado: "Afectacion notable, puede requerir tratamiento pronto"
  - Severo: "Condicion avanzada, requiere atencion inmediata"

---

## Form Fields

### Por cada diagnostico en el batch:

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| cie10_codigo | string | Yes | Codigo CIE-10 valido seleccionado del buscador | "Selecciona un diagnostico CIE-10" | "Buscar por codigo o descripcion..." |
| modo_localizacion | enum | No | "general", "diente", "zona" | — | — |
| dientes | string[] | Cond. | Requerido si modo="diente"; valores FDI validos (11-85) | "Selecciona al menos un diente" | — |
| zona | string | Cond. | Requerido si modo="zona" | "Selecciona una zona" | — |
| severidad | enum | Yes | "leve", "moderado", "severo" | "Selecciona la severidad del diagnostico" | — |
| notas | textarea | No | Max 500 chars | "Maximo 500 caracteres" | "Notas clinicas adicionales..." |

**Zod Schema:**
```typescript
const diagnosticoItemSchema = z.object({
  cie10_codigo: z.string().min(3, "Selecciona un diagnostico CIE-10"),
  cie10_descripcion: z.string(),
  modo_localizacion: z.enum(["general", "diente", "zona"]).default("general"),
  dientes: z.array(z.string()).optional(),
  zona: z.string().optional(),
  severidad: z.enum(["leve", "moderado", "severo"], {
    required_error: "Selecciona la severidad del diagnostico",
  }),
  notas: z.string().max(500).optional(),
}).refine(
  (data) => data.modo_localizacion !== "diente" || (data.dientes && data.dientes.length > 0),
  { message: "Selecciona al menos un diente", path: ["dientes"] }
).refine(
  (data) => data.modo_localizacion !== "zona" || !!data.zona,
  { message: "Selecciona una zona", path: ["zona"] }
);

const diagnosticoBatchSchema = z.object({
  registro_clinico_id: z.string().uuid().optional(),
  diagnosticos: z.array(diagnosticoItemSchema).min(1).max(10),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Buscar CIE-10 | `/api/v1/cie10/search?q={query}` | GET | `specs/clinical-records/CR-10-cie10-search.md` | 30min |
| Crear diagnostico(s) | `/api/v1/patients/{id}/diagnoses` | POST | `specs/clinical-records/CR-07-create-diagnosis.md` | None |

### Request Body (POST batch)
```json
{
  "registro_clinico_id": "uuid-opcional",
  "diagnosticos": [
    {
      "cie10_codigo": "K02.1",
      "cie10_descripcion": "Caries de la dentina",
      "dientes": ["16", "17"],
      "severidad": "moderado",
      "notas": "Caries interproximal visible en radiografia"
    }
  ]
}
```

### State Management

**Local State (useState):**
- `diagnosticos: DiagnosticoFormData[]` — array de items en el batch (min 1, max 10)
- `isSubmitting: boolean` — estado de submission

**Global State (Zustand):**
- `patientStore.currentPatient` — ID del paciente activo

**Server State (TanStack Query):**
- Query key CIE-10: `['cie10-search', query]` — ver FE-CR-06 para detalle
- Mutation: `useMutation({ mutationFn: createDiagnoses })` para POST batch
- `onSuccess`: invalida `['diagnoses', patientId]` y `['clinical-records', patientId]`

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `invalid_cie10` | 422 | "Codigo CIE-10 no valido" |
| `invalid_tooth` | 422 | "Numero de diente no valido (usar notacion FDI)" |
| `forbidden` | 403 | "Solo doctores pueden crear diagnosticos" |
| `record_not_found` | 404 | "Registro clinico no encontrado" |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Buscar CIE-10 | Typing en input | Debounced search (300ms) | Dropdown con resultados |
| Seleccionar CIE-10 | Click en resultado o Enter | Codigo y descripcion llenos | Input muestra el codigo + descripcion |
| Cambiar modo diente | Radio "Diente especifico" | Muestra mini odontograma o input FDI | Slide-down del selector |
| Seleccionar diente | Click en odontograma o input FDI | Diente agregado a lista | Diente resaltado en odontograma |
| Seleccionar severidad | Click en radio | Severidad marcada con color | Radio con color animado |
| Agregar diagnostico | Click "+ Agregar otro diagnostico" | Nuevo item agregado al final | Nuevo card fade-in + scroll |
| Eliminar diagnostico | Click "Eliminar" en header del card | Card removido con confirmacion si tiene datos | Card fade-out |
| Guardar | Click "Guardar (N)" | Valida todos los items + POST batch | Spinner, toast success, cierre modal |

### Animations/Transitions

- Nuevo item de diagnostico: slide-down + fade-in 200ms
- Eliminar item: fade-out + height collapse 150ms
- Selector de diente (condicional): slide-down 150ms al activar modo "diente"
- Modal: slide-up en mobile/tablet, fade-in centrado en desktop

---

## Loading & Error States

### Loading State
- Boton "Guardar" muestra spinner durante submission
- Todos los items del batch se deshabilitan durante el guardado
- Busqueda CIE-10: spinner inline en el input mientras busca (ver FE-CR-06)

### Error State
- Errores de validacion Zod: inline debajo de cada campo con error
- Si un item del batch tiene error, el header del card se resalta: `border-l-4 border-red-500`
- Error de API: toast destructivo con mensaje especifico
- El scroll hace focus en el primer item con error despues de intentar guardar

### Empty State
- No aplica — siempre hay al menos un item de diagnostico inicializado

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Modal full-screen. Items apilados verticalmente. Mini odontograma reemplazado por input numerico FDI. Botones Guardar/Cancelar 100% ancho y apilados. |
| Tablet (640-1024px) | Modal max-w-xl 90vh con scroll. Mini odontograma visual disponible. Radios de severidad en fila horizontal. Footer sticky con botones a la derecha. Touch targets 44px. |
| Desktop (> 1024px) | Modal max-w-2xl. Layout de campos en grid 2 columnas dentro de cada item (CIE-10 | Diente/Zona; Severidad | Notas). |

**Tablet priority:** High — diagnosticos se registran en tablet durante la consulta. Mini odontograma tiene zonas clickeables de minimo 32x32px con area de toque de 44px. Radios de severidad con area de toque de minimo 44px de altura.

---

## Accessibility

- **Focus order:** Dentro de cada item: busqueda CIE-10 → modo localizacion (radios) → selector diente/zona → severidad (radios) → notas. Luego boton "Agregar otro" → Cancelar → Guardar.
- **Screen reader:** `role="dialog"` con `aria-label="Agregar diagnostico(s)"`. Cada card de diagnostico tiene `role="group"` con `aria-label="Diagnostico #{n}"`. Boton Guardar tiene `aria-label="Guardar {n} diagnostico(s)"`.
- **Keyboard navigation:** `Tab` entre campos. Arrow keys en radio groups. `Escape` cierra modal. Buscador CIE-10 soporta navegacion con flechas y Enter (ver FE-CR-06).
- **Color contrast:** WCAG AA. Radios de severidad usan iconos ademas de color para no depender solo del color.
- **Language:** es-419 en todas las etiquetas. Descripcion de CIE-10 en español. Severidades en español clinico latinoamericano.

---

## Design Tokens

**Colors:**
- Card diagnostico: `bg-white border border-gray-200 rounded-xl`
- Card con error: `border-l-4 border-red-500`
- Card completo: `border-l-4 border-green-400`
- Severidad leve: radio `text-green-600 bg-green-50`
- Severidad moderado: radio `text-yellow-600 bg-yellow-50`
- Severidad severo: radio `text-red-600 bg-red-50`
- Diente seleccionado en odontograma: `bg-blue-500 text-white`

**Typography:**
- Header card: `text-sm font-semibold text-gray-700`
- Codigo CIE-10 seleccionado: `font-mono font-bold text-blue-700`
- Descripcion CIE-10: `text-sm text-gray-600`
- Label radio: `text-sm font-medium`
- Descripcion radio severidad: `text-xs text-gray-500`

**Spacing:**
- Card padding: `p-4 md:p-5`
- Gap entre cards: `space-y-4`
- Gap campos dentro de card: `space-y-4`
- Modal padding: `p-6`

**Border Radius:**
- Card: `rounded-xl`
- Inputs: `rounded-md`
- Modal: `rounded-2xl`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers` — validacion con `useFieldArray` para el batch
- `@tanstack/react-query` — mutation de creacion y query de CIE-10
- `lucide-react` — Plus, Trash2, CheckCircle, AlertTriangle, Search

**File Location:**
- Modal: `src/components/clinical-records/DiagnosisFormModal.tsx`
- Item: `src/components/clinical-records/DiagnosisFormItem.tsx`
- Selector dientes: `src/components/clinical-records/ToothSelectorInput.tsx`
- Severidad: `src/components/clinical-records/SeveridadRadioGroup.tsx`
- Schema: `src/lib/schemas/diagnosis.ts`
- Hook: `src/hooks/useCreateDiagnosis.ts`

**Hooks Used:**
- `useForm()` — React Hook Form con `useFieldArray` para lista de diagnosticos
- `useMutation({ mutationFn: createDiagnoses })` — POST batch
- `useAuth()` — contexto de usuario
- `usePatientStore()` — ID del paciente activo

**Form Library:**
- React Hook Form + Zod con `useFieldArray` para el batch mode
- `mode: "onSubmit"` para validacion
- Scroll automatico al primer error: `scrollIntoView({ behavior: "smooth" })` en el `onError` de `handleSubmit`

---

## Test Cases

### Happy Path
1. Crear diagnostico unico
   - **Given:** Modal abierto con un item de diagnostico vacio
   - **When:** Doctor busca "caries", selecciona K02.1, elige diente 16, severidad "Moderado" y guarda
   - **Then:** POST exitoso con 1 diagnostico, modal cierra, lista actualizada

2. Crear multiples diagnosticos (batch)
   - **Given:** Doctor agrega 3 items de diagnostico al formulario
   - **When:** Llena los 3 items con CIE-10, dientes y severidad validos y guarda
   - **Then:** POST con array de 3 diagnosticos, todos creados en una sola operacion

3. Diagnostico general sin diente especifico
   - **Given:** Doctor selecciona modo "General" en localizacion
   - **When:** Guarda el diagnostico
   - **Then:** Diagnostico creado sin diente asociado (campo dientes vacio)

### Edge Cases
1. Maximo 10 diagnosticos en batch
   - **Given:** Ya hay 10 items en el formulario
   - **When:** Doctor hace click en "+ Agregar otro diagnostico"
   - **Then:** Boton deshabilitado con tooltip "Maximo 10 diagnosticos por vez"

2. Eliminar item con datos
   - **Given:** Item #2 tiene CIE-10 y severidad llenos
   - **When:** Doctor hace click en "Eliminar" del item #2
   - **Then:** Dialog de confirmacion; al confirmar, el item se elimina

### Error Cases
1. Intentar guardar con CIE-10 vacio
   - **Given:** Doctor llena severidad pero no selecciona CIE-10
   - **When:** Hace click en "Guardar"
   - **Then:** Error inline bajo el campo CIE-10: "Selecciona un diagnostico CIE-10". Card tiene borde rojo izquierdo.

2. Error del servidor al crear
   - **Given:** POST falla con error 500
   - **When:** Doctor guarda diagnosticos validos
   - **Then:** Toast de error: "Error al guardar los diagnosticos. Intenta de nuevo." Datos del formulario se conservan.

---

## Acceptance Criteria

- [ ] Busqueda CIE-10 funcional con debounce 300ms (integra FE-CR-06)
- [ ] Selector de diente/zona: modo General, Diente especifico (mini odontograma + input FDI), Zona (cuadrantes/sextantes)
- [ ] Radios de severidad: Leve, Moderado, Severo con colores diferenciales (verde/amarillo/rojo)
- [ ] Batch mode: boton "+ Agregar otro diagnostico", maximo 10 items
- [ ] Cada item con boton "Eliminar" (disabled si es el unico)
- [ ] Boton "Guardar" muestra conteo de diagnosticos a crear: "Guardar (3)"
- [ ] Validacion Zod por item con errores inline en es-419
- [ ] Scroll automatico al primer item con error al intentar guardar
- [ ] POST batch en una sola llamada al API
- [ ] Toast de exito + cierre de modal + invalidacion de cache de diagnosticos y registros
- [ ] Responsive: input FDI en mobile, mini odontograma en tablet+
- [ ] Touch targets minimo 44px en tablet
- [ ] Accesibilidad: role="dialog", role="group" por item, aria-label en boton guardar con conteo
- [ ] Textos en es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
