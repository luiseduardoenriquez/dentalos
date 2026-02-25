# Tooth Selector — Design System Component Spec

## Overview

**Spec ID:** FE-DS-18

**Component:** `ToothSelector`

**File:** `src/components/clinical/tooth-selector.tsx`

**Description:** Interactive mini-odontogram widget for selecting one or multiple teeth by FDI number. Used in clinical forms where procedures, diagnoses, or conditions must be associated with specific teeth. Renders a complete adult (32 teeth) or pediatric (20 teeth) dentition grid with click-to-select interaction, hover tooltips, and pre-selection support.

**Design System Ref:** `FE-DS-01` (§5.2 OdontogramGrid, §5.1 ToothDiagram)

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `mode` | `'single' \| 'multi'` | `'single'` | No | Single or multi-tooth selection |
| `dentition` | `'adult' \| 'pediatric'` | `'adult'` | No | 32 adult or 20 pediatric teeth |
| `value` | `number[]` | `[]` | No | Controlled selected FDI tooth numbers |
| `onChange` | `(teeth: number[]) => void` | — | Yes | Called with updated selection |
| `disabledTeeth` | `number[]` | `[]` | No | FDI numbers that cannot be selected |
| `highlightedTeeth` | `Record<number, string>` | `{}` | No | FDI → hex color map for condition indicators |
| `label` | `string` | — | No | Label above the selector |
| `required` | `boolean` | `false` | No | Required field indicator |
| `error` | `string` | — | No | Error message below the selector |
| `helperText` | `string` | — | No | Helper text below label |
| `showNumbers` | `boolean` | `true` | No | Show FDI numbers above/below teeth |
| `size` | `'sm' \| 'md'` | `'sm'` | No | Tooth rendering size |
| `className` | `string` | — | No | Additional classes on wrapper |
| `readOnly` | `boolean` | `false` | No | View-only mode, no clicks |

---

## FDI Notation Reference

### Adult Dentition (32 teeth)

Upper jaw (maxillar): Quadrant 1 (right): 18,17,16,15,14,13,12,11 | Quadrant 2 (left): 21,22,23,24,25,26,27,28

Lower jaw (mandibular): Quadrant 4 (right): 48,47,46,45,44,43,42,41 | Quadrant 3 (left): 31,32,33,34,35,36,37,38

**Grid layout (8 columns × 4 rows):**
```
Row 1 (upper, right → center):  18  17  16  15  14  13  12  11
Row 2 (upper, center → left):   21  22  23  24  25  26  27  28
Row 3 (lower, center → left):   31  32  33  34  35  36  37  38
Row 4 (lower, right → center):  48  47  46  45  44  43  42  41
```

**Center dividers:**
- Vertical midline: between columns 4-5 (between teeth 11/21 and 41/31)
- Horizontal midline: between rows 2 and 3

### Pediatric Dentition (20 teeth)

Quadrant 5 (upper right): 55,54,53,52,51
Quadrant 6 (upper left): 61,62,63,64,65
Quadrant 7 (lower left): 71,72,73,74,75
Quadrant 8 (lower right): 85,84,83,82,81

**Grid layout (5 columns × 4 rows):**
```
Row 1 (upper, right → center):  55  54  53  52  51
Row 2 (upper, center → left):   61  62  63  64  65
Row 3 (lower, center → left):   71  72  73  74  75
Row 4 (lower, right → center):  85  84  83  82  81
```

---

## Visual Structure

```
[Label: "Piezas afectadas *"]
[Helper text: "Selecciona los dientes afectados por la caries"]

+--------+--------+--------+--------+--------+--------+--------+--------+
| 18 ▾   | 17 ▾   | 16 ▾   | 15 ▾   | 14 ▾   | 13 ▾   | 12 ▾   | 11 ▾   |
+--------+--------+--------+--------+--------+--------+--------+--------+
| 21 ▾   | 22 ▾   | 23 ▾   | 24 ▾   | 25 [●] | 26 ▾   | 27 ▾   | 28 ▾   |  ← 25 selected
+========+========+========+========+========+========+========+========+
| 31 ▾   | 32 ▾   | 33 ▾   | 34 ▾   | 35 ▾   | 36 [●] | 37 ▾   | 38 ▾   |  ← 36 selected
+--------+--------+--------+--------+--------+--------+--------+--------+
| 48 ▾   | 47 ▾   | 46 ▾   | 45 ▾   | 44 ▾   | 43 ▾   | 42 ▾   | 41 ▾   |
+--------+--------+--------+--------+--------+--------+--------+--------+

Seleccionados: 25, 36  |  [Limpiar selección]

[Error: "Selecciona al menos una pieza"]
```

---

## Tooth Cell Component

Each individual tooth cell in the grid.

**Size sm (default for ToothSelector):**
- Cell: `w-9 h-9` (36px) — fits within 44px touch target including gap
- Touch target: `w-11 h-11` (44px) via padding wrapper
- FDI number: `text-[10px]` above or below tooth icon

**Size md:**
- Cell: `w-12 h-12` (48px)
- FDI number: `text-xs`

### Tooth Cell Visual

```
[FDI number]   ← text-[10px] text-gray-400, above for upper jaw, below for lower jaw
[Tooth SVG]    ← simplified tooth outline
```

**Tooth SVG:** Simplified single-surface tooth silhouette (oval/rounded rectangle approximation — not the full 5-surface diagram from the full odontogram). Appropriate for selection context.

**States:**

| State | Fill | Border | Background |
|-------|------|--------|-----------|
| Default | `fill-none stroke-gray-400` | — | `bg-white` |
| Hover | `fill-none stroke-teal-500` | — | `bg-teal-50` |
| Selected | `fill-teal-100 stroke-teal-600` | `ring-2 ring-teal-600` | `bg-teal-50` |
| Disabled | `fill-none stroke-gray-200` | — | `bg-gray-50 cursor-not-allowed opacity-50` |
| Highlighted (condition) | Custom fill from `highlightedTeeth[fdi]` | — | Custom |
| Selected + Highlighted | Selected ring + condition fill | `ring-2 ring-teal-600` | Condition color |

**Selected indicator (multi-mode):** Small checkmark badge overlay on bottom-right corner of selected tooth.

---

## Hover Tooltip

On hover (desktop) / long-press (mobile) over a tooth cell:

```
+------------------+
| Pieza 36         |
| Primer molar     |
| Mandibular izq.  |
+------------------+
```

**Tooltip content:**
- FDI number: "Pieza [N]"
- Tooth name in Spanish
- Quadrant description

**Tooth names database (sample):**

| FDI | Name | Quadrant |
|-----|------|---------|
| 11 | Incisivo central | Superior derecho |
| 12 | Incisivo lateral | Superior derecho |
| 13 | Canino | Superior derecho |
| 14 | Primer premolar | Superior derecho |
| 15 | Segundo premolar | Superior derecho |
| 16 | Primer molar | Superior derecho |
| 17 | Segundo molar | Superior derecho |
| 18 | Tercer molar | Superior derecho |
| 21 | Incisivo central | Superior izquierdo |
| ... | (mirror of 1x) | Superior izquierdo |
| 36 | Primer molar | Mandibular izquierdo |
| 46 | Primer molar | Mandibular derecho |
| 48 | Tercer molar | Mandibular derecho |

Full 32-tooth name table defined in `src/lib/dental/tooth-names.ts`.

---

## Selection Logic

### Single Mode (`mode='single'`)

- Only one tooth selectable at a time
- Clicking a selected tooth deselects it
- `onChange` called with `[fdi]` or `[]`

### Multi Mode (`mode='multi'`)

- Multiple teeth selectable
- Clicking selected tooth deselects it
- `onChange` called with updated array
- Order: ascending FDI number

### "Limpiar selección" button

Appears when at least 1 tooth is selected (only in multi mode, or when single selection exists):

```tsx
<button
  type="button"
  onClick={() => onChange([])}
  className="text-xs text-teal-600 hover:text-teal-800 underline"
>
  Limpiar selección
</button>
```

---

## Selected Summary

Below the grid, shows selected FDI numbers:

```
Seleccionados: 14, 15, 36, 46
```

`text-sm text-gray-700 font-medium`

Or in label form: "4 piezas seleccionadas" when more than 3.

---

## Highlighted Teeth (Condition Indicators)

`highlightedTeeth` prop maps FDI numbers to hex colors:

```tsx
<ToothSelector
  mode="multi"
  highlightedTeeth={{
    16: '#EF4444', // red (caries)
    36: '#A855F7', // purple (endodontic)
    14: '#3B82F6', // blue (restoration)
  }}
  value={selectedTeeth}
  onChange={setSelectedTeeth}
/>
```

These are typically used in procedure forms to pre-show existing conditions while allowing the user to select which ones a new procedure addresses.

---

## Midline Dividers

**Vertical midline:** Between quadrant 1-2 (upper) and 3-4 (lower). Implemented as `border-l-2 border-gray-400` on the first cell of each "left" quadrant (teeth 21, 31).

**Horizontal midline:** Between upper and lower jaw rows. Implemented as a `border-b-2 border-gray-400` on row 2 (upper left quadrant row).

**No labels** on the dividers. The FDI number makes quadrant assignment clear.

---

## React Hook Form Integration

```tsx
<Controller
  name="piezas_afectadas"
  control={control}
  rules={{ validate: (v) => v.length > 0 || 'Selecciona al menos una pieza' }}
  render={({ field, fieldState }) => (
    <ToothSelector
      label="Piezas afectadas"
      mode="multi"
      value={field.value ?? []}
      onChange={field.onChange}
      required
      error={fieldState.error?.message}
    />
  )}
/>
```

---

## Accessibility

- **Role:** Grid container: `role="group"` with `aria-labelledby` pointing to the label.
- **Tooth cells:** `role="checkbox"` (multi mode) or `role="radio"` (single mode). `aria-label="Pieza [FDI] — [tooth name]"`. `aria-checked="true/false"`.
- **Disabled teeth:** `aria-disabled="true"`, tooltip explains why: e.g., "Pieza extraída".
- **Keyboard:** Tab moves focus between tooth cells. Space selects/deselects. Arrow keys navigate between cells (like a radio group).
- **Screen reader:** On selection change, `aria-live="polite"` announces: "Pieza [FDI] seleccionada" / "Pieza [FDI] deseleccionada".
- **Selected summary:** `aria-label="Piezas seleccionadas: [list of FDI numbers]"` on summary text.
- **Required:** `aria-required="true"` on the group. Error message in `role="alert"`.
- **Language:** All tooth names in Spanish.

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Grid cells slightly smaller. Touch targets padded to 44px. Tooltip shows below tooth on tap. |
| Tablet (640-1024px) | Standard sm size. Primary clinical input device — touch optimized. |
| Desktop (> 1024px) | Standard sm size. Hover tooltips show immediately. |

**Touch:** `pointer-events: all` on all tooth cells. No hover state on mobile (uses active state instead).

---

## Usage Examples

```tsx
// Single tooth — diagnosis form
<ToothSelector
  label="Pieza diagnósticada"
  mode="single"
  dentition="adult"
  value={selectedTooth}
  onChange={(teeth) => setSelectedTooth(teeth)}
  error={errors.pieza?.message}
/>

// Multi-tooth — procedure form
<ToothSelector
  label="Piezas del tratamiento"
  mode="multi"
  dentition="adult"
  value={selectedTeeth}
  onChange={setSelectedTeeth}
  highlightedTeeth={existingConditionsColorMap}
  helperText="Selecciona todas las piezas incluidas en este procedimiento"
/>

// Pediatric
<ToothSelector
  label="Piezas afectadas"
  mode="multi"
  dentition="pediatric"
  value={selectedTeeth}
  onChange={setSelectedTeeth}
/>

// Read-only (view treatment plan)
<ToothSelector
  mode="multi"
  value={[14, 15, 16]}
  onChange={() => {}}
  readOnly
  highlightedTeeth={{ 14: '#3B82F6', 15: '#EF4444', 16: '#A855F7' }}
/>
```

---

## Implementation Notes

**File Location:** `src/components/clinical/tooth-selector.tsx`

**Tooth SVG paths:** Simple ellipse or rounded square path per tooth, defined in `src/lib/dental/tooth-shapes.ts`. No need for the complex 5-surface SVG used in the full odontogram.

**Tooth names database:** `src/lib/dental/tooth-names.ts` — mapping of all 52 FDI numbers (adult + pediatric) to Spanish names and quadrant labels.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec — dental-specific, FDI notation, adult + pediatric |
