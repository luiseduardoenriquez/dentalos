# Formulario de Anamnesis — Frontend Spec

## Overview

**Screen:** Formulario estructurado de anamnesis medica del paciente. Organizado en 8 secciones clinicas con campos especializados: medicamentos, alergias con severidad, enfermedades cronicas, antecedentes quirurgicos, antecedentes familiares, habitos, estado de embarazo (solo sexo femenino) y grupo sanguineo. Soporta guardado como borrador o envio final.

**Route:** `/patients/{id}/anamnesis`

**Priority:** High

**Backend Specs:**
- `specs/clinical-records/CR-05-anamnesis.md`
- `specs/clinical-records/CR-06-update-anamnesis.md`

**Dependencies:**
- `specs/frontend/patients/patient-detail.md` — tab container padre
- `specs/frontend/clinical-records/record-create.md` — puede embeberse como tipo anamnesis (FE-CR-02)

---

## User Flow

**Entry Points:**
- Tab "Anamnesis" dentro del detalle del paciente (`/patients/{id}/anamnesis`)
- Seleccion de tipo "Anamnesis" en el modal FE-CR-02
- Redireccion post-creacion de paciente nuevo (flujo onboarding)

**Exit Points:**
- Guardado exitoso → permanece en la misma ruta con estado "guardado" + toast
- "Guardar borrador" → permanece con indicador de borrador
- "Cancelar" → regresa a tab anterior del paciente (si es ruta directa) o cierra modal

**User Story:**
> As a doctor | assistant, I want to fill out a structured medical history questionnaire so that I can document the patient's current medications, allergies, chronic conditions, and habits before their treatment.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`

---

## Layout Structure

```
+--------------------------------------------------+
|  Anamnesis — Juan Perez           [Borrador]     |
+--------------------------------------------------+
|  Ultima actualizacion: 20 Feb 2026 por Dra. Ruiz |
+--------------------------------------------------+
|                                                  |
|  [1. Medicamentos actuales]      [v / ^]         |
|  +----------------------------------------+     |
|  |  [tag: Metformina 500mg] [tag: Losartan]|     |
|  |  [+ Agregar medicamento...]             |     |
|  +----------------------------------------+     |
|                                                  |
|  [2. Alergias]                   [v / ^]         |
|  +----------------------------------------+     |
|  |  [tag: Penicilina SEVERA] [+ Agregar]  |     |
|  +----------------------------------------+     |
|                                                  |
|  [3. Enfermedades cronicas]      [v / ^]         |
|  |  [x] Diabetes  [x] Hipertension  [ ] Asma    |
|                                                  |
|  [4. Antecedentes quirurgicos]   [v / ^]         |
|  [5. Antecedentes familiares]    [v / ^]         |
|  [6. Habitos]                    [v / ^]         |
|  [7. Embarazo] (solo sexo femenino)              |
|  [8. Grupo sanguineo]            [v / ^]         |
|                                                  |
+--------------------------------------------------+
|  [Guardar borrador]              [Guardar]       |
+--------------------------------------------------+
```

**Sections:**
1. Header — nombre del paciente, ultima actualizacion, estado (borrador / completo)
2. Secciones acordeon (1-8) — expandibles/colapsables; cada una con su tipo de input especifico
3. Footer sticky — boton "Guardar borrador" secundario + boton "Guardar" primario

---

## UI Components

### Component 1: SeccionAcordeon

**Type:** Accordion section

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.5

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| titulo | string | — | Nombre de la seccion |
| numero | number | — | Numero de seccion (1-8) |
| isComplete | boolean | false | Muestra checkmark verde si seccion completa |
| defaultOpen | boolean | false | Estado inicial expandido |
| children | ReactNode | — | Contenido de la seccion |

**States:**
- Expandida — contenido visible con chevron hacia arriba
- Colapsada — solo header visible con chevron hacia abajo
- Completa — header con checkmark verde e indicador `text-green-600`
- Con datos — header con punto azul indicando datos sin guardar

---

### Component 2: TagInputMedicamentos

**Type:** Tag input con busqueda

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | Medicamento[] | [] | Lista de medicamentos actuales |
| onChange | function | — | Callback al agregar/eliminar |
| searchPlaceholder | string | "Buscar medicamento..." | Placeholder del input |

**States:**
- Default — lista de tags + input de busqueda al final
- Searching — lista de sugerencias debounced
- Tag hover — muestra boton X para eliminar

**Behavior:**
- Input de texto libre o busqueda en catalogo de medicamentos
- Busqueda debounced 300ms sobre catalogo local
- Si no hay sugerencia, permite entrada libre (texto exacto del usuario)
- Cada tag muestra: nombre + dosis si se especifica
- Boton X en cada tag para eliminar
- Enter o click en sugerencia agrega el tag

---

### Component 3: TagInputAlergias

**Type:** Tag input con selector de severidad

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | Alergia[] | [] | Lista de alergias con severidad |
| onChange | function | — | Callback al cambiar |

**States:**
- Default — tags con color por severidad + input
- Adding — input activo + dropdown de severidad antes de confirmar

**Behavior:**
- Al agregar alergia: primero input de texto, luego selector de severidad (leve/moderada/severa)
- Confirmacion con boton "Agregar" o Enter tras seleccionar severidad
- Color de tag por severidad:
  - `leve` → `bg-yellow-100 text-yellow-800`
  - `moderada` → `bg-orange-100 text-orange-800`
  - `severa` → `bg-red-100 text-red-800 font-semibold`
- Tags de alergias severas tienen icono `AlertTriangle` rojo

---

### Component 4: CheckboxGroupEnfermedades

**Type:** Checkbox grid

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | string[] | [] | Enfermedades seleccionadas |
| onChange | function | — | Callback al cambiar |
| opciones | EnfermedadOption[] | — | Lista de enfermedades disponibles |

**Behavior:**
- Grid de 2 columnas en tablet, 1 columna en mobile
- Cada checkbox con label legible en español
- Opcion "Otra" con input de texto libre que aparece al seleccionarla
- Opciones predefinidas: Diabetes, Hipertension, Asma, Cardiopatia, Cancer (activo/remision), VIH, Epilepsia, Artritis, Osteoporosis, Tiroides, Insuficiencia renal, Otra

---

### Component 5: ListaAntecedentesQuirurgicos

**Type:** Dynamic list con items

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | AntecedenteQuirurgico[] | [] | Lista de antecedentes |
| onChange | function | — | Callback al cambiar |

**Behavior:**
- Cada item: campo de fecha (mes/ano es suficiente) + campo de descripcion de la cirugia
- Boton "+ Agregar antecedente quirurgico" agrega nuevo item al final
- Boton X en cada item elimina con confirmacion solo si tiene datos
- Maximo 20 items

---

### Component 6: HabitosToggleGroup

**Type:** Toggle group con frecuencia condicional

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | HabitosData | — | Estado de habitos |
| onChange | function | — | Callback al cambiar |

**Behavior:**
- Toggle switch para: Fumador, Consume alcohol, Consume drogas
- Si el toggle se activa, aparece select de frecuencia: "Ocasional", "Regular", "Diario"
- Toggle "Fumador" activo: tambien muestra input de cuantos cigarrillos/dia (number)
- Colores de toggle: activo = `bg-red-500` para habitos de riesgo

---

### Component 7: EmbarazoToggle

**Type:** Conditional toggle con input numerico

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.2

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| visible | boolean | — | Solo visible si el paciente es de sexo femenino |
| value | EmbarazoData | — | { embarazada: boolean, semanas?: number } |
| onChange | function | — | Callback al cambiar |

**Behavior:**
- Seccion completamente oculta para pacientes de sexo masculino (condicion basada en `patient.sexo`)
- Toggle "En embarazo actualmente"
- Si activo: input numerico "Semanas de gestacion" (1-42)

---

## Form Fields

### Seccion 1: Medicamentos Actuales

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| medicamentos | tag array | No | Max 50 items, max 100 chars por item | "Nombre de medicamento muy largo" | "Ej: Metformina 500mg" |

### Seccion 2: Alergias

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| alergias[].nombre | string | Yes (si se agrega) | Min 2 chars, max 100 | "Describe la alergia" | "Ej: Penicilina" |
| alergias[].severidad | enum | Yes (si se agrega) | leve/moderada/severa | "Selecciona la severidad" | — |

### Seccion 3: Enfermedades Cronicas

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| enfermedades | string[] | No | Valores del enum predefinido + "otra" | — | — |
| enfermedades_otra | string | Cond. | Requerido si "otra" seleccionado, max 200 | "Describe la enfermedad" | "Especifica la enfermedad..." |

### Seccion 4: Antecedentes Quirurgicos

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| antecedentes_qx[].fecha | month/year | Cond. | Formato valido, no futuro | "La fecha no puede ser futura" | "MM/AAAA" |
| antecedentes_qx[].descripcion | string | Yes (si se agrega item) | Min 5 chars, max 500 | "Describe el procedimiento" | "Ej: Apendicectomia" |

### Seccion 6: Habitos

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| habitos.fumador | boolean | No | — | — | — |
| habitos.frecuencia_tabaco | enum | Cond. | Requerido si fumador activo | "Selecciona la frecuencia" | — |
| habitos.cigarrillos_dia | number | No | 1-100 | "Valor entre 1 y 100" | "Cigarrillos por dia" |
| habitos.alcohol | boolean | No | — | — | — |
| habitos.frecuencia_alcohol | enum | Cond. | Requerido si alcohol activo | "Selecciona la frecuencia" | — |
| habitos.drogas | boolean | No | — | — | — |
| habitos.frecuencia_drogas | enum | Cond. | Requerido si drogas activo | "Selecciona la frecuencia" | — |

### Seccion 7: Embarazo

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| embarazo.activo | boolean | No | Solo si paciente femenino | — | — |
| embarazo.semanas | number | Cond. | 1-42 si embarazo activo | "Semanas entre 1 y 42" | "Semanas de gestacion" |

### Seccion 8: Grupo Sanguineo

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| grupo_sanguineo | select | No | A+/A-/B+/B-/AB+/AB-/O+/O-/Desconocido | — | "Seleccionar grupo sanguineo" |

**Zod Schema principal:**
```typescript
const anamnesisSchema = z.object({
  medicamentos: z.array(z.string().max(100)).max(50),
  alergias: z.array(z.object({
    nombre: z.string().min(2).max(100),
    severidad: z.enum(["leve", "moderada", "severa"]),
  })),
  enfermedades: z.array(z.string()),
  enfermedades_otra: z.string().max(200).optional(),
  antecedentes_qx: z.array(z.object({
    fecha: z.string().optional(),
    descripcion: z.string().min(5).max(500),
  })).max(20),
  antecedentes_familiares: z.array(z.string()),
  habitos: z.object({
    fumador: z.boolean().default(false),
    frecuencia_tabaco: z.enum(["ocasional", "regular", "diario"]).optional(),
    cigarrillos_dia: z.number().min(1).max(100).optional(),
    alcohol: z.boolean().default(false),
    frecuencia_alcohol: z.enum(["ocasional", "regular", "diario"]).optional(),
    drogas: z.boolean().default(false),
    frecuencia_drogas: z.enum(["ocasional", "regular", "diario"]).optional(),
  }),
  embarazo: z.object({
    activo: z.boolean().default(false),
    semanas: z.number().min(1).max(42).optional(),
  }).optional(),
  grupo_sanguineo: z.enum(["A+","A-","B+","B-","AB+","AB-","O+","O-","desconocido"]).optional(),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Cargar anamnesis existente | `/api/v1/patients/{id}/anamnesis` | GET | `specs/clinical-records/CR-05-anamnesis.md` | 5min |
| Guardar / actualizar | `/api/v1/patients/{id}/anamnesis` | PUT | `specs/clinical-records/CR-06-update-anamnesis.md` | None |
| Guardar borrador | `/api/v1/patients/{id}/anamnesis/draft` | PUT | `specs/clinical-records/CR-05-anamnesis.md` | None |

### State Management

**Local State (useState):**
- `seccionesAbiertas: Set<number>` — conjunto de indices de secciones expandidas
- `isDirty: boolean` — true si hay cambios sin guardar
- `saveStatus: "idle" | "saving" | "saved" | "error"` — estado de guardado

**Global State (Zustand):**
- `patientStore.currentPatient` — datos del paciente incluyendo `sexo` para mostrar seccion embarazo

**Server State (TanStack Query):**
- Query key: `['anamnesis', patientId, tenantId]`
- Stale time: 5 minutos
- Mutation: `useMutation({ mutationFn: saveAnamnesis })` para PUT
- `onSuccess`: invalida cache y muestra toast de exito

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `patient_not_found` | 404 | "Paciente no encontrado" |
| `validation_error` | 422 | Errores inline por campo desde el servidor |
| `forbidden` | 403 | "No tienes permisos para editar la anamnesis" |
| `conflict` | 409 | "Otra persona edito la anamnesis recientemente. Recarga para ver los cambios." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Expandir seccion | Click en header de seccion | Muestra contenido de seccion | Animacion height 200ms |
| Agregar medicamento | Enter o click en sugerencia | Tag agregado en la lista | Tag con animacion fade-in |
| Eliminar medicamento | Click X en tag | Tag eliminado | Tag con fade-out |
| Agregar alergia | Input texto + seleccionar severidad + "Agregar" | Tag de alergia con color por severidad | Tag colorido fade-in |
| Toggle enfermedad | Click checkbox | Marca/desmarca enfermedad | Checkmark animado |
| Activar habito | Click toggle | Muestra selector de frecuencia | Input de frecuencia slide-down |
| Activar embarazo | Click toggle | Muestra input de semanas | Input slide-down |
| Guardar borrador | Click "Guardar borrador" | PUT sin validacion completa | Toast "Borrador guardado" |
| Guardar | Click "Guardar" | Valida todo + PUT | Spinner → toast success o errores inline |

### Animations/Transitions

- Acordeon de seccion: `max-height` transition 200ms ease-out
- Slide-down de campos condicionales (frecuencia, semanas): `max-height` 150ms ease-out
- Tags: fade-in 100ms al agregar, fade-out 100ms al eliminar
- Toast de exito: slide-in desde arriba derecha

---

## Loading & Error States

### Loading State
- Skeleton por seccion: header con `w-32 h-5 bg-gray-200 animate-pulse` + contenido `w-full h-20 bg-gray-100`
- Mientras carga la anamnesis existente, todas las secciones muestran skeleton
- Boton "Guardar" deshabilitado durante carga inicial

### Error State
- Error al cargar: banner de error completo con boton "Reintentar" sobre el formulario
- Errores de validacion Zod: inline debajo de cada campo con `text-xs text-red-600`
- Error al guardar: toast destructivo + campos con error en borde rojo
- Error de conflicto (409): banner especial con boton "Recargar" que re-fetcha los datos del servidor

### Empty State
- Si el paciente no tiene anamnesis previa: formulario vacio con texto guia en cada seccion ("Agrega los medicamentos actuales del paciente")
- No hay un estado vacio "sin datos" especial — el formulario siempre se muestra

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Secciones en pila vertical. Checkboxes en 1 columna. Tags en wrap. Footer sticky con ambos botones apilados (100% ancho). |
| Tablet (640-1024px) | Secciones acordeon. Checkboxes en grid 2 columnas. Tags en wrap. Footer sticky horizontal. Layout primario clinico. Touch targets 44px. |
| Desktop (> 1024px) | Layout de 1 columna centrada `max-w-2xl`. Checkboxes en grid 3 columnas. Sidebar con progreso de secciones (indicador cual ya tiene datos). |

**Tablet priority:** High — anamnesis tipicamente se llena en tablet durante la primera consulta. Todos los inputs tienen al menos 44px de altura. Toggle switches de minimo 44x24px. Checkboxes con area de toque de 44px.

---

## Accessibility

- **Focus order:** Cada seccion en orden 1-8. Dentro de cada seccion: header acordeon → campos en orden logico → ultimo campo de la seccion.
- **Screen reader:** `aria-expanded` en cada header de seccion. Seccion embarazo con `aria-hidden="true"` cuando el paciente es masculino. Tags con `role="listitem"` y boton X con `aria-label="Eliminar {nombre}"`.
- **Keyboard navigation:** `Enter`/`Space` expande/colapsa seccion. `Tab` navega dentro de la seccion. `Delete`/`Backspace` en ultimo char del tag input elimina el ultimo tag.
- **Color contrast:** WCAG AA. Tags de alergias: colores elegidos para cumplir 4.5:1. Badge "severa" tiene `font-semibold` adicional por ser informacion critica.
- **Language:** Todas las etiquetas, placeholders y mensajes en es-419. Nombres de enfermedades en español medico latinoamericano.

---

## Design Tokens

**Colors:**
- Header seccion: `bg-gray-50 hover:bg-gray-100 border border-gray-200`
- Seccion completa: header con `border-l-4 border-green-500`
- Tag medicamento: `bg-blue-50 text-blue-700 border border-blue-200`
- Tag alergia leve: `bg-yellow-100 text-yellow-800 border border-yellow-300`
- Tag alergia moderada: `bg-orange-100 text-orange-800 border border-orange-300`
- Tag alergia severa: `bg-red-100 text-red-800 border border-red-400`
- Toggle activo: `bg-red-500` (habitos de riesgo) / `bg-blue-500` (embarazo)
- Toggle inactivo: `bg-gray-300`

**Typography:**
- Numero + titulo seccion: `text-base font-semibold text-gray-800`
- Label de campo: `text-sm font-medium text-gray-700`
- Tags: `text-sm font-medium`
- Hint text: `text-xs text-gray-500`

**Spacing:**
- Seccion padding: `p-4 md:p-6`
- Gap entre secciones: `space-y-3`
- Gap campos dentro de seccion: `space-y-4`
- Footer: `px-4 py-4 md:px-6 border-t border-gray-200 sticky bottom-0 bg-white`

**Border Radius:**
- Seccion acordeon: `rounded-xl overflow-hidden`
- Tags: `rounded-full px-3 py-1`
- Inputs: `rounded-md`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers` — validacion del formulario completo
- `@tanstack/react-query` — carga y guardado de anamnesis
- `lucide-react` — ChevronDown, ChevronUp, X, Plus, AlertTriangle, CheckCircle, Loader2
- `framer-motion` — animaciones de acordeon y tags

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/anamnesis/page.tsx`
- Form: `src/components/clinical-records/AnamnesisForm.tsx`
- Secciones: `src/components/clinical-records/anamnesis/MedicamentosSection.tsx`
- Secciones: `src/components/clinical-records/anamnesis/AlergiasSection.tsx`
- Secciones: `src/components/clinical-records/anamnesis/EnfermedadesSection.tsx`
- Secciones: `src/components/clinical-records/anamnesis/HabitosSection.tsx`
- Secciones: `src/components/clinical-records/anamnesis/EmbarazoSection.tsx`
- Schema: `src/lib/schemas/anamnesis.ts`
- Hook: `src/hooks/useAnamnesis.ts`

**Hooks Used:**
- `useForm()` — React Hook Form con schema Zod
- `useQuery(['anamnesis', patientId])` — carga datos existentes como `defaultValues`
- `useMutation()` — guardado y borrador
- `useAuth()` — contexto de usuario y tenant
- `usePatientStore()` — paciente actual (para leer `sexo`)
- `useBeforeUnload()` — advertencia si `isDirty` al cerrar pestaña

**Form Library:**
- React Hook Form + Zod. `mode: "onSubmit"` — validacion completa al intentar guardar.
- Para campos dinamicos (lista de antecedentes): `useFieldArray` de React Hook Form.

---

## Test Cases

### Happy Path
1. Llenar anamnesis completa y guardar
   - **Given:** Paciente nuevo sin anamnesis, formulario vacio
   - **When:** Doctor llena todas las secciones y hace click en "Guardar"
   - **Then:** PUT exitoso, toast "Anamnesis guardada correctamente", indicador de estado cambia a "Completo"

2. Cargar anamnesis existente para editar
   - **Given:** Paciente con anamnesis previa (varios medicamentos, 2 alergias)
   - **When:** Doctor navega a `/patients/{id}/anamnesis`
   - **Then:** Formulario cargado con todos los datos previos, indicador de ultima actualizacion visible

3. Seccion embarazo oculta para paciente masculino
   - **Given:** Paciente con `sexo: "masculino"`
   - **When:** Se carga el formulario
   - **Then:** La seccion "Embarazo" no es visible en el DOM (no solo hidden visualmente)

### Edge Cases
1. Alergia severa se resalta visualmente
   - **Given:** Doctor agrega alergia "Penicilina" con severidad "Severa"
   - **When:** Tag se agrega
   - **Then:** Tag en rojo con icono `AlertTriangle` destacado

2. Habito con frecuencia — campo condicional
   - **Given:** Toggle de fumador desactivado
   - **When:** Doctor activa el toggle de fumador
   - **Then:** Input de frecuencia y cigarrillos/dia aparecen con animacion slide-down

3. Guardar borrador no valida campos vacios
   - **Given:** Solo la seccion de medicamentos tiene datos
   - **When:** Doctor hace click en "Guardar borrador"
   - **Then:** Se guarda sin errores de validacion; los campos vacios no generan errores

### Error Cases
1. Conflicto de edicion concurrente
   - **Given:** Dos usuarios editando la anamnesis del mismo paciente
   - **When:** El segundo intenta guardar
   - **Then:** Error 409 muestra banner "Otra persona edito la anamnesis recientemente. Recarga para ver los cambios."

2. Validacion al guardar con campos requeridos vacios
   - **Given:** Se agrego un item de antecedente quirurgico pero el campo descripcion esta vacio
   - **When:** Doctor hace click en "Guardar"
   - **Then:** La seccion con error se expande automaticamente y el campo muestra error inline

---

## Acceptance Criteria

- [ ] 8 secciones expandibles/colapsables con indicador de completitud por seccion
- [ ] Seccion 1 (Medicamentos): tag input con busqueda en catalogo y entrada libre
- [ ] Seccion 2 (Alergias): tag input + selector severidad + colores por nivel (leve/moderada/severa)
- [ ] Seccion 3 (Enfermedades): checkboxes con lista predefinida + campo "Otra" condicional
- [ ] Seccion 4 (Antecedentes Qx): lista dinamica con fecha + descripcion + max 20 items
- [ ] Seccion 5 (Antecedentes Familiares): checkboxes por condicion
- [ ] Seccion 6 (Habitos): toggles con frecuencia condicional para tabaco, alcohol, drogas
- [ ] Seccion 7 (Embarazo): oculta para paciente masculino; toggle + semanas condicional
- [ ] Seccion 8 (Grupo Sanguineo): select con 8 grupos + "Desconocido"
- [ ] Carga datos existentes como defaultValues en el formulario
- [ ] Guardado como borrador no requiere validacion completa
- [ ] Guardado final valida con Zod y muestra errores inline en es-419
- [ ] Responsive: 1 columna mobile, acordeon tablet, sidebar progreso desktop
- [ ] Touch targets minimo 44px en tablet
- [ ] Accesibilidad: aria-expanded, aria-hidden (embarazo), roles de lista para tags
- [ ] Textos en es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
