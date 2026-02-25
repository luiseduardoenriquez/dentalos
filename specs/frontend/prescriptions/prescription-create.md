# Crear Receta Medica — Frontend Spec

## Overview

**Screen:** Modal para crear una receta medica odontologica desde el detalle del paciente. Permite agregar multiples medicamentos con nombre (autocompletado), dosis, frecuencia, duracion, via de administracion e instrucciones especificas. Incluye vinculacion opcional a diagnostico, notas generales del prescriptor, y boton de previsualizacion que muestra como lucira la receta en formato de talonario PDF antes de guardar.

**Route:** Modal desde `/patients/{id}` (tab o boton de accion rapida) | `/patients/{id}/prescriptions/new`

**Priority:** High

**Backend Specs:**
- `specs/prescriptions/RX-01-create-prescription.md`
- `specs/prescriptions/RX-05-medication-catalog.md`

**Dependencies:**
- `specs/frontend/prescriptions/prescription-list.md` — lista padre que se actualiza al crear (FE-RX-02)
- `specs/frontend/prescriptions/prescription-preview.md` — previsualizacion antes de guardar (FE-RX-03)
- `specs/frontend/patients/patient-detail.md` — contexto del paciente

---

## User Flow

**Entry Points:**
- Boton "+ Nueva receta" desde el tab de recetas del paciente (FE-RX-02)
- Boton de accion rapida "Crear receta" desde el header del detalle del paciente
- Acceso desde un registro clinico de procedimiento (link "Crear receta asociada")

**Exit Points:**
- Guardado exitoso → cierra modal → lista FE-RX-02 recarga con la nueva receta al tope → toast de exito
- Boton "Previsualizar" → abre FE-RX-03 como modal secundario; al cerrar el preview, vuelve al formulario
- Cancelar → dialog de confirmacion si hay datos → cierra sin guardar

**User Story:**
> As a doctor, I want to prescribe one or more medications at once with dosing details and instructions so that the patient has a clear, professional prescription document that can be printed or downloaded.

**Roles with access:** `clinic_owner`, `doctor`

---

## Layout Structure

```
+--------------------------------------------------+
|  [X] Nueva Receta Medica             [Previsualizar]|
+--------------------------------------------------+
|                                                  |
|  Medicamento 1:                       [Eliminar] |
|  +----------------------------------------+     |
|  |  Medicamento: [Amoxicilina 500mg    v] |     |
|  |  Dosis: [500] [mg v]                   |     |
|  |  Frecuencia: [Cada 8 horas          v] |     |
|  |  Duracion: [7] dias                    |     |
|  |  Via: [Oral                         v] |     |
|  |  Instrucciones: [Tomar con alimentos]  |     |
|  +----------------------------------------+     |
|                                                  |
|  Medicamento 2:                       [Eliminar] |
|  +----------------------------------------+     |
|  |  Medicamento: [Ibuprofeno 400mg     v] |     |
|  |  Dosis: [400] [mg v]                   |     |
|  |  Frecuencia: [Cada 12 horas         v] |     |
|  |  Duracion: [5] dias                    |     |
|  |  Via: [Oral                         v] |     |
|  |  Instrucciones: [Si hay dolor        ] |     |
|  +----------------------------------------+     |
|                                                  |
|  [+ Agregar otro medicamento]                    |
|                                                  |
|  ---------------------------------------------- |
|  Diagnostico relacionado (opcional):             |
|  [Seleccionar diagnostico del paciente        v] |
|                                                  |
|  Notas del medico:                               |
|  [textarea: instrucciones adicionales...]        |
|                                                  |
|  ---------------------------------------------- |
|  [Cancelar]   [Previsualizar]   [Crear receta]  |
+--------------------------------------------------+
```

**Sections:**
1. Header modal — titulo, boton cerrar, boton "Previsualizar" acceso rapido
2. Lista de medicamentos — uno o mas items, cada uno con todos sus campos
3. Boton agregar — "+ Agregar otro medicamento" (max 10)
4. Diagnostico y notas — vinculacion a diagnostico + notas generales
5. Footer — Cancelar, Previsualizar, Crear receta

---

## UI Components

### Component 1: ItemMedicamento

**Type:** Form card por medicamento

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| index | number | — | Numero de medicamento (para label "#N") |
| value | MedicamentoFormData | — | Datos del medicamento |
| onChange | function | — | Callback al cambiar cualquier campo |
| onRemove | function | — | Elimina este item de la lista |
| isOnly | boolean | false | Si es el unico, eliminar disabled |
| errors | FieldErrors | {} | Errores de validacion de este item |

**States:**
- Default — todos los campos vacios
- Parcial — medicamento seleccionado, otros campos pendientes
- Completo — todos los campos requeridos llenos (borde sutil verde izquierdo)
- Error — campos con error en rojo

**Behavior:**
- Header del card: "Medicamento #1", "#2", etc.
- Boton "Eliminar" en esquina superior derecha (disabled si es el unico item)
- Layout 2 columnas en tablet para campos cortos (dosis+unidad | frecuencia)
- Layout 1 columna en mobile

---

### Component 2: AutocompleteMedicamento

**Type:** Combobox con catalogo

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | MedicamentoItem \| null | null | Medicamento seleccionado |
| onChange | function | — | Callback al seleccionar |
| error | string \| undefined | — | Error de validacion |

**States:**
- Idle — input vacio con placeholder
- Searching — debounce 300ms → dropdown de resultados del catalogo
- Selected — nombre del medicamento en el input + boton X
- Sin resultado — opcion de entrada libre ("Usar '{query}' como nombre")

**Behavior:**
- Busqueda en catalogo de medicamentos del sistema (RX-05)
- Minimo 2 caracteres para activar busqueda
- Resultado: nombre comercial (bold) + nombre generico + forma farmaceutica
- Si no hay resultado en el catalogo, permite entrada de texto libre con confirmacion
- Al seleccionar del catalogo, auto-llena: unidad (mg/ml/etc.), via de administracion sugerida
- Patron identico a CIE-10 Search (FE-CR-06) en terminos de UX

---

### Component 3: SelectorFrecuencia

**Type:** Select dropdown

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | string | "" | Frecuencia seleccionada |
| onChange | function | — | Callback |
| error | string \| undefined | — | Error |

**Opciones predefinidas:**
- "Cada 4 horas"
- "Cada 6 horas"
- "Cada 8 horas"
- "Cada 12 horas"
- "Cada 24 horas (una vez al dia)"
- "Dos veces al dia"
- "Tres veces al dia"
- "Solo si hay dolor (PRN)"
- "Antes de dormir"
- "Antes de las comidas"
- "Despues de las comidas"
- "Otra frecuencia..." (activa input de texto libre)

---

### Component 4: SelectorViaAdministracion

**Type:** Select dropdown

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Opciones predefinidas:**
- "Oral"
- "Topica"
- "Sublingual"
- "Inhalatoria"
- "Intravenosa"
- "Intramuscular"
- "Subcutanea"
- "Rectal"
- "Oftalmica"
- "Otica"
- "Nasal"

---

### Component 5: BotonPrevisualizar

**Type:** Secondary button

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| onPreview | function | — | Callback para abrir FE-RX-03 |
| disabled | boolean | false | Deshabilitado si no hay medicamentos validos |

**Behavior:**
- Click abre modal de previsualizacion FE-RX-03 con los datos actuales del formulario (aunque no esten todos los campos completos)
- El preview muestra los datos tal como quedarian impresos
- Disponible en el header del modal Y en el footer como boton secundario

---

## Form Fields

### Campos por medicamento:

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| medicamento_nombre | string | Yes | Min 2 chars, max 200 | "Nombre del medicamento requerido" | "Buscar medicamento..." |
| dosis_cantidad | number | Yes | > 0, max 10000 | "Ingresa la dosis del medicamento" | "Ej: 500" |
| dosis_unidad | string | Yes | mg/ml/g/mcg/UI/tabletas/capsulas | "Selecciona la unidad de dosis" | — |
| frecuencia | string | Yes | Seleccion de lista o texto libre | "Selecciona la frecuencia de administracion" | — |
| duracion_dias | number | Yes | 1-365 | "Duracion entre 1 y 365 dias" | "Dias" |
| via | string | Yes | Seleccion de lista | "Selecciona la via de administracion" | — |
| instrucciones | textarea | No | Max 300 chars | "Maximo 300 caracteres" | "Instrucciones especificas para este medicamento..." |

### Campos generales de la receta:

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| diagnostico_id | string | No | UUID valido | — | "Seleccionar diagnostico (opcional)" |
| notas_medico | textarea | No | Max 500 chars | "Maximo 500 caracteres" | "Notas e instrucciones adicionales para el paciente..." |

**Zod Schema:**
```typescript
const medicamentoSchema = z.object({
  medicamento_nombre: z.string().min(2, "Nombre del medicamento requerido").max(200),
  medicamento_id: z.string().uuid().optional(), // null si entrada libre
  dosis_cantidad: z.number().positive("Ingresa la dosis del medicamento").max(10000),
  dosis_unidad: z.enum(["mg", "ml", "g", "mcg", "UI", "tabletas", "capsulas", "gotas"], {
    required_error: "Selecciona la unidad de dosis",
  }),
  frecuencia: z.string().min(3, "Selecciona la frecuencia de administracion").max(100),
  duracion_dias: z.number().int().min(1).max(365, "Duracion entre 1 y 365 dias"),
  via: z.string().min(2, "Selecciona la via de administracion"),
  instrucciones: z.string().max(300).optional(),
});

const crearRecetaSchema = z.object({
  medicamentos: z.array(medicamentoSchema)
    .min(1, "Agrega al menos un medicamento")
    .max(10),
  diagnostico_id: z.string().uuid().optional(),
  notas_medico: z.string().max(500).optional(),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Buscar medicamentos en catalogo | `/api/v1/medications/search?q={query}` | GET | `specs/prescriptions/RX-05-medication-catalog.md` | 30min |
| Diagnosticos activos del paciente | `/api/v1/patients/{id}/diagnoses?status=active` | GET | `specs/clinical-records/CR-07.md` | 5min |
| Crear receta | `/api/v1/patients/{id}/prescriptions` | POST | `specs/prescriptions/RX-01-create-prescription.md` | None |

### Request Body (POST):
```json
{
  "medicamentos": [
    {
      "medicamento_nombre": "Amoxicilina 500mg",
      "medicamento_id": "uuid-catalogo",
      "dosis_cantidad": 500,
      "dosis_unidad": "mg",
      "frecuencia": "Cada 8 horas",
      "duracion_dias": 7,
      "via": "Oral",
      "instrucciones": "Tomar con alimentos"
    }
  ],
  "diagnostico_id": "uuid-diagnostico",
  "notas_medico": "Tomar toda la serie aunque mejore"
}
```

### State Management

**Local State (useState):**
- `isSubmitting: boolean`
- `showPreview: boolean` — controla el modal de preview FE-RX-03

**Global State (Zustand):**
- `patientStore.currentPatient` — paciente activo

**Server State (TanStack Query):**
- Query key catalogo: `['medication-search', query]`
- Query key diagnosticos: `['patient-diagnoses', patientId, 'active']`
- Mutation: `useMutation({ mutationFn: createPrescription })` → invalida `['prescriptions', patientId]`

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `doctor_required` | 403 | "Solo medicos pueden crear recetas" |
| `invalid_medication` | 422 | "Medicamento no valido: {nombre}" |
| `patient_not_found` | 404 | "Paciente no encontrado" |
| `server_error` | 500 | "Error al crear la receta. Intenta de nuevo." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Buscar medicamento | Typing (2+ chars) | Debounced search 300ms | Dropdown con resultados |
| Seleccionar medicamento | Click en resultado | Campos auto-llenados | Campos con datos del catalogo |
| Cambiar frecuencia | Select | Actualiza frecuencia del item | Select actualizado |
| Agregar medicamento | Click "+ Agregar otro" | Nuevo card al final | Card fade-in |
| Eliminar medicamento | Click "Eliminar" | Card eliminado (con confirm si tiene datos) | Card fade-out |
| Previsualizar | Click "Previsualizar" | Abre modal FE-RX-03 con datos actuales | Modal slide-up |
| Crear receta | Click "Crear receta" | Valida + POST | Spinner, toast, cierra modal |
| Cancelar (con datos) | Click "Cancelar" o Escape | Dialog de confirmacion | Modal confirmacion |

### Animations/Transitions

- Nuevo card medicamento: slide-down + fade-in 200ms
- Eliminar card: fade-out + height collapse 150ms
- Modal preview: slide-up desde bottom 250ms
- Auto-fill de campos al seleccionar del catalogo: fields con brief highlight amarillo 300ms

---

## Loading & Error States

### Loading State
- Boton "Crear receta" con spinner "Creando receta..." durante submission
- Todos los campos disabled durante submission
- Catalogo de medicamentos: spinner inline en el input mientras busca

### Error State
- Errores Zod: inline bajo cada campo en `text-xs text-red-600`
- Card con error: header con borde rojo izquierdo `border-l-4 border-red-500`
- Scroll automatico al primer item con error al intentar enviar
- Error de API: toast destructivo con mensaje en es-419

### Empty State
- Lista vacia — no ocurre (siempre hay un item inicial)
- Sin diagnosticos activos en el select: "El paciente no tiene diagnosticos activos para vincular"
- Sin resultados en catalogo: "Sin resultados. Puedes usar '{query}' como nombre del medicamento."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Modal full-screen. Campos apilados en 1 columna. Botones footer 100% ancho apilados. Boton previsualizar solo en footer. |
| Tablet (640-1024px) | Modal max-h 90vh con scroll interno. Campos en 2 columnas dentro de cada card: [dosis+unidad] | [frecuencia+duracion]; [via] | [instrucciones]. Touch targets 44px. |
| Desktop (> 1024px) | Modal `max-w-2xl`. 2 columnas dentro de los cards. Boton previsualizar en header Y en footer. |

**Tablet priority:** High — recetas se crean en tablet durante la consulta. Todos los selects con opciones de minimo 44px de altura. Input de medicamento con min 44px de altura. Cards con padding generoso para toque con dedo.

---

## Accessibility

- **Focus order:** Dentro de cada card: autocompletado medicamento → dosis cantidad → dosis unidad → frecuencia → duracion → via → instrucciones → boton eliminar. Luego siguiente card. Luego diagnostico → notas → Cancelar → Previsualizar → Crear receta.
- **Screen reader:** `role="dialog"` con `aria-label="Crear nueva receta medica"`. Cada card: `role="group"` con `aria-label="Medicamento #{n}"`. Boton crear: `aria-label="Crear receta con {n} medicamento(s)"`. Error de catalogo sin resultados: `aria-live="polite"` anuncia "Sin resultados para {query}".
- **Keyboard navigation:** Tab entre campos. Arrow keys en selects. `Escape` cierra modal. `Enter` en autocompletado selecciona el item resaltado.
- **Color contrast:** WCAG AA. Labels `text-gray-700` sobre `bg-white`.
- **Language:** es-419. Nombres de frecuencias en español. Vias de administracion en español medico.

---

## Design Tokens

**Colors:**
- Card medicamento: `bg-white border border-gray-200 rounded-xl`
- Card completo: `border-l-4 border-green-400`
- Card con error: `border-l-4 border-red-500`
- Boton previsualizar: `bg-white border border-gray-300 text-gray-700 hover:bg-gray-50`
- Boton crear receta: `bg-blue-600 text-white hover:bg-blue-700`
- Auto-fill highlight: brief `bg-yellow-100` transition que desaparece en 300ms

**Typography:**
- Numero + label card: `text-sm font-semibold text-gray-700`
- Label campo: `text-sm font-medium text-gray-700`
- Nombre medicamento seleccionado: `text-sm text-gray-900`
- Hint campo instrucciones: `text-xs text-gray-400`

**Spacing:**
- Modal padding: `p-6`
- Gap entre cards: `space-y-4`
- Padding card: `p-4 md:p-5`
- Gap entre campos dentro de card: `space-y-3`
- Grid 2 columnas: `grid grid-cols-2 gap-3`

**Border Radius:**
- Modal: `rounded-2xl`
- Cards: `rounded-xl`
- Inputs: `rounded-md`
- Selects: `rounded-md`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers` — con `useFieldArray` para la lista de medicamentos
- `@tanstack/react-query` — busqueda de catalogo y mutation
- `lucide-react` — Plus, Trash2, Eye, CheckCircle, AlertCircle, Loader2, Search

**File Location:**
- Modal: `src/components/prescriptions/CreatePrescriptionModal.tsx`
- Card medicamento: `src/components/prescriptions/MedicamentoFormCard.tsx`
- Autocomplete: `src/components/prescriptions/MedicamentoSearchInput.tsx`
- Select frecuencia: `src/components/prescriptions/FrecuenciaSelect.tsx`
- Hook: `src/hooks/useCreatePrescription.ts`
- Schema: `src/lib/schemas/prescription.ts`
- API: `src/lib/api/prescriptions.ts`

**Hooks Used:**
- `useForm()` — React Hook Form
- `useFieldArray({ name: "medicamentos" })` — lista de medicamentos
- `useQuery(['medication-search', query])` — catalogo de medicamentos
- `useQuery(['patient-diagnoses', patientId, 'active'])` — diagnosticos
- `useMutation({ mutationFn: createPrescription })`
- `useAuth()`, `usePatientStore()`
- `useState` — `showPreview`

**Form Library:**
- React Hook Form + Zod con `useFieldArray`. `mode: "onSubmit"` para validar al guardar, no al escribir.

---

## Test Cases

### Happy Path
1. Crear receta con 2 medicamentos del catalogo
   - **Given:** Doctor abre el modal de crear receta para un paciente
   - **When:** Selecciona Amoxicilina 500mg y agrega un segundo medicamento Ibuprofeno, llena todos los campos y hace click "Crear receta"
   - **Then:** POST exitoso con ambos medicamentos, modal cierra, lista FE-RX-02 recarga, toast de exito

2. Previsualizar antes de crear
   - **Given:** Un medicamento agregado con todos sus campos
   - **When:** Click "Previsualizar"
   - **Then:** Modal FE-RX-03 abre mostrando la receta formateada como talonario; al cerrar el preview, vuelve al formulario con los datos intactos

3. Medicamento con nombre libre (no en catalogo)
   - **Given:** Doctor busca "Clorhexidina gel 0.12%" en el catalogo sin resultado
   - **When:** Selecciona la opcion "Usar 'Clorhexidina gel 0.12%' como nombre"
   - **Then:** Input queda con ese texto, el resto de campos sin auto-llenado, doctor llena manualmente

### Edge Cases
1. Maximo 10 medicamentos
   - **Given:** Ya hay 10 cards de medicamentos
   - **When:** Doctor hace click "+ Agregar otro medicamento"
   - **Then:** Boton deshabilitado con tooltip "Maximo 10 medicamentos por receta"

2. Auto-fill al seleccionar del catalogo
   - **Given:** Doctor selecciona "Amoxicilina 500mg Capsula" del catalogo
   - **When:** Item seleccionado del dropdown
   - **Then:** Campo dosis se llena con "500", unidad con "mg", via con "Oral" automaticamente; brief highlight amarillo en los campos auto-llenados

### Error Cases
1. Intentar crear sin campos obligatorios
   - **Given:** Card de medicamento con nombre y dosis pero sin frecuencia ni via
   - **When:** Click "Crear receta"
   - **Then:** Card con borde rojo, errores inline: "Selecciona la frecuencia..." y "Selecciona la via...". Scroll a primer error.

2. Error 403 (no es medico)
   - **Given:** Usuario con rol "receptionist" intenta crear receta
   - **When:** POST retorna 403
   - **Then:** Toast: "Solo medicos pueden crear recetas"

---

## Acceptance Criteria

- [ ] Lista dinamica de medicamentos (min 1, max 10) con boton "+ Agregar otro medicamento"
- [ ] Card por medicamento con: nombre (autocompletado catalogo), dosis (cantidad + unidad), frecuencia (select), duracion (dias), via (select), instrucciones (opcional)
- [ ] Autocompletado de medicamentos con debounce 300ms y opcion de texto libre
- [ ] Auto-fill de dosis, unidad y via al seleccionar del catalogo
- [ ] Select de frecuencia con opciones predefinidas en español
- [ ] Select de via de administracion con opciones predefinidas
- [ ] Boton "Eliminar" por card (disabled si es el unico)
- [ ] Vinculacion opcional a diagnostico activo del paciente
- [ ] Campo notas del medico (textarea, max 500 chars, opcional)
- [ ] Boton "Previsualizar" que abre FE-RX-03 con datos actuales del formulario
- [ ] Al volver del preview, el formulario conserva todos los datos
- [ ] Validacion Zod con errores inline en es-419
- [ ] Scroll automatico al primer campo con error al intentar enviar
- [ ] POST con todos los medicamentos en una sola llamada
- [ ] Toast de exito + cierre modal + recarga de lista FE-RX-02
- [ ] Dialog de confirmacion al cancelar con datos no guardados
- [ ] Responsive: 1 columna mobile, 2 columnas en campos cortos tablet+
- [ ] Touch targets 44px en tablet
- [ ] Accesibilidad: role="dialog", role="group" por card, aria-live para busqueda
- [ ] Textos en es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
