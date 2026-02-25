# Select / Combobox — Design System Component Spec

## Overview

**Spec ID:** FE-DS-04

**Component:** `Select`, `Combobox`, `MultiSelect`

**File:** `src/components/ui/select.tsx`, `src/components/ui/combobox.tsx`

**Description:** Dropdown selection components for single values, searchable selections, multi-select tags, and async remote search. Built on Radix UI Select + cmdk (Command) primitives. Used across all forms in DentalOS including clinical selectors for CIE-10, CUPS, medications, and standard dropdowns for status, gender, and role.

**Design System Ref:** `FE-DS-01` (§4.3)

---

## Component Variants

| Variant | Component | Use Case |
|---------|-----------|---------|
| `Select` | Simple dropdown | Status, gender, document type, country, timezone |
| `Combobox` | Searchable typeahead | Doctor, patient, procedure, role selection |
| `MultiSelect` | Tag-based multi-select | Allergies, conditions, specialties, channels |
| `AsyncCombobox` | Remote search with debounce | CIE-10 codes, CUPS procedures, medications |

---

## Props Table — `Select`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `label` | `string` | — | No | Label above the select |
| `options` | `SelectOption[]` | `[]` | Yes | Array of `{ value, label, disabled?, group? }` |
| `value` | `string` | — | No | Controlled selected value |
| `defaultValue` | `string` | — | No | Uncontrolled default |
| `onChange` | `(value: string) => void` | — | No | Change handler |
| `placeholder` | `string` | `"Seleccionar..."` | No | Placeholder text when no value selected |
| `error` | `string` | — | No | Error message below select |
| `helperText` | `string` | — | No | Helper text below select |
| `disabled` | `boolean` | `false` | No | Disables the select |
| `required` | `boolean` | `false` | No | Marks as required |
| `clearable` | `boolean` | `false` | No | Shows X button to clear selection |
| `grouped` | `boolean` | `false` | No | Options rendered in labeled groups |
| `className` | `string` | — | No | Additional classes |

## Props Table — `Combobox`

Extends `Select` props plus:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `searchPlaceholder` | `string` | `"Buscar..."` | Placeholder in the search input |
| `emptyMessage` | `string` | `"Sin resultados"` | Message when no options match |
| `maxItems` | `number` | `—` | Max options shown in list |

## Props Table — `MultiSelect`

Extends `Combobox` props plus:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `values` | `string[]` | `[]` | Controlled selected values array |
| `onValuesChange` | `(values: string[]) => void` | — | Multi-value change handler |
| `maxSelections` | `number` | — | Max number of selected items |

## Props Table — `AsyncCombobox`

Extends `Combobox` props plus:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `fetchOptions` | `(query: string) => Promise<SelectOption[]>` | — | Remote search function |
| `debounceMs` | `number` | `300` | Search debounce delay |
| `minChars` | `number` | `2` | Minimum characters before searching |
| `loadingMessage` | `string` | `"Buscando..."` | Message during async search |

---

## SelectOption Type

```typescript
interface SelectOption {
  value: string
  label: string
  disabled?: boolean
  group?: string        // For grouped options
  description?: string  // Secondary text below label
  icon?: ReactNode      // Optional icon before label
}
```

---

## Visual Structure

```
[Label text] [*]
+----------------------------------------+
| [Selected value or placeholder]    [▾] |
+----------------------------------------+
[Error or helper text]

// Dropdown panel (open state):
+----------------------------------------+
| [Search input]                         |  ← Combobox only
+----------------------------------------+
| Group Label (if grouped)               |
|  ○  Option 1                           |
|  ●  Option 2 (selected)                |
|  ○  Option 3                           |
|     ○  Option 4 (disabled, grayed)     |
+----------------------------------------+
| [Sin resultados] (empty state)         |
```

---

## Trigger Button Styles

**Base classes:**
```
h-10 w-full rounded-md border px-3 py-2
text-sm text-left flex items-center justify-between
bg-white cursor-pointer
transition-colors duration-150
```

| State | Border | Ring | Background |
|-------|--------|------|-----------|
| Default | `border-gray-300` | none | `bg-white` |
| Open/Focus | `border-teal-500` | `ring-2 ring-teal-500/20` | `bg-white` |
| Error | `border-red-500` | `ring-2 ring-red-500/20` | `bg-red-50` |
| Disabled | `border-gray-200` | none | `bg-gray-50` text-gray-400 |

**Chevron icon:** `ChevronDown`, 16px, `text-gray-400`. Rotates `180deg` when open (`rotate-180 transition-transform`).

---

## Dropdown Panel

**Position:** Below trigger, full width of trigger. Offset 4px.

**Classes:**
```
bg-white border border-gray-200 rounded-lg shadow-lg
py-1 z-50 max-h-60 overflow-auto
```

**Option item:**
```
px-3 py-2 text-sm cursor-pointer
hover:bg-gray-50
aria-selected:bg-teal-50 aria-selected:text-teal-700 aria-selected:font-medium
disabled:text-gray-400 disabled:cursor-not-allowed
```

**Group label:**
```
px-3 py-1.5 text-xs font-medium text-gray-400 uppercase tracking-wider
```

**Selected indicator:** `Check` icon (16px, `text-teal-600`) at the right of selected option.

---

## Search Input (Combobox)

Inside the dropdown panel, above options:

```
+----------------------------------------+
| [Search icon] Buscar...                |
+----------------------------------------+
```

**Classes:** `border-b border-gray-200 px-3 py-2 flex items-center gap-2`

Input: `flex-1 text-sm outline-none bg-transparent text-gray-900 placeholder:text-gray-400`

Filters options as user types (fuzzy match on label text, client-side).

---

## MultiSelect Tags

When values are selected, they appear as removable tags inside the trigger area:

```
+------------------------------------------+
| [Tag: Alergia latex ×] [Tag: Penicilina ×] |
| [Search input...]                          |
+------------------------------------------+
```

**Tag classes:**
```
inline-flex items-center gap-1
bg-teal-50 text-teal-700 border border-teal-200
text-xs px-2 py-0.5 rounded-full
```

**Tag X button:** `X` icon (10px), `hover:text-teal-900`. `aria-label="Eliminar [tag label]"`.

**Overflow:** When tags exceed one line, trigger expands vertically (max 3 lines before scroll).

---

## AsyncCombobox — Async Search Flow

1. User types 2+ characters → `debounceMs` timer starts
2. Loading: spinner (`Loader2 animate-spin`) replaces search icon inside the input
3. Fetch resolves → options populate (max 20 results by default)
4. Empty result: "Sin resultados para '[query]'"
5. Fetch error: "Error al buscar. Intenta de nuevo." in red text

**Display format for clinical codes:**
```
[K02.1] — Caries de la dentina
[0101] — Consulta de primera vez por médico general
```

```tsx
<AsyncCombobox
  label="Diagnóstico (CIE-10)"
  placeholder="Seleccionar diagnóstico..."
  searchPlaceholder="Buscar por código o descripción..."
  fetchOptions={async (q) => searchCIE10(q)}
  debounceMs={300}
  minChars={2}
  emptyMessage="Sin diagnósticos encontrados"
  error={errors.diagnostico?.message}
  onChange={(val) => setValue('diagnostico_cie10', val)}
/>
```

---

## Grouped Options

```tsx
const timezoneOptions: SelectOption[] = [
  { value: 'America/Bogota', label: 'Bogotá (UTC-5)', group: 'Colombia' },
  { value: 'America/Medellin', label: 'Medellín (UTC-5)', group: 'Colombia' },
  { value: 'America/Mexico_City', label: 'Ciudad de México (UTC-6)', group: 'México' },
]

<Select
  label="Zona horaria"
  options={timezoneOptions}
  grouped
  placeholder="Seleccionar zona horaria..."
/>
```

Groups render with a non-selectable label row between groups.

---

## Clear Button

When `clearable={true}` and a value is selected, an `X` icon appears inside the trigger (right side, left of chevron):

```
| Selected value              [×] [▾] |
```

**X button:** `text-gray-400 hover:text-gray-600`, 14px icon. Clears selection and calls `onChange(undefined)`. `aria-label="Limpiar selección"`.

---

## Keyboard Navigation

| Key | Action |
|-----|--------|
| `Tab` | Focus the trigger |
| `Enter` / `Space` | Open dropdown |
| `ArrowDown` | Focus next option |
| `ArrowUp` | Focus previous option |
| `Enter` | Select focused option |
| `Escape` | Close dropdown, return focus to trigger |
| `Home` | Jump to first option |
| `End` | Jump to last option |
| Type character | Jump to option starting with that character (non-search variants) |

---

## Accessibility

- **Role:** Trigger has `role="combobox"`, `aria-haspopup="listbox"`, `aria-expanded="true/false"`, `aria-controls="[listbox-id]"`
- **Listbox:** `role="listbox"` on the dropdown panel. Options have `role="option"`, `aria-selected="true/false"`, `aria-disabled="true/false"`.
- **Label association:** `aria-labelledby` pointing to the label element.
- **Error:** `aria-invalid="true"` on trigger when error present. Error message in `role="alert"`.
- **Multi-select:** Tags have accessible remove buttons with `aria-label`. Selected count announced via `aria-describedby`: "3 opciones seleccionadas".
- **Search combobox:** Announces result count: "5 resultados disponibles" via `aria-live="polite"`.

---

## Usage Examples

```tsx
// Simple select — document type
<Select
  label="Tipo de documento"
  options={[
    { value: 'CC', label: 'Cédula de ciudadanía' },
    { value: 'CE', label: 'Cédula de extranjería' },
    { value: 'PA', label: 'Pasaporte' },
    { value: 'TI', label: 'Tarjeta de identidad' },
  ]}
  placeholder="Seleccionar tipo..."
  required
  error={errors.tipo_doc?.message}
  onChange={(val) => setValue('tipo_documento', val)}
/>

// Multi-select — allergies
<MultiSelect
  label="Alergias conocidas"
  options={allergyOptions}
  values={watchedAllergies}
  onValuesChange={(vals) => setValue('alergias', vals)}
  placeholder="Agregar alergias..."
  searchPlaceholder="Buscar alergia..."
  emptyMessage="Alergia no encontrada. Escribe el nombre completo."
/>
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
