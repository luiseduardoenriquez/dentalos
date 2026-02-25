# Configuración de Odontograma — Frontend Spec

## Overview

**Spec ID:** FE-S-04

**Screen:** Odontogram configuration page — display mode, default dentition, and condition color customization.

**Route:** `/settings/odontograma`

**Priority:** Medium

**Backend Specs:** `specs/tenants/tenant-settings-update.md`, `specs/tenants/tenant-settings-get.md`

**Dependencies:** `FE-DS-01`, `FE-DS-02` (button), `FE-DS-10` (card), `FE-DS-18` (tooth-selector for mini preview)

---

## User Flow

**Entry Points:**
- Sidebar: Configuración → Odontograma

**Exit Points:**
- Any other settings section

**User Story:**
> As a clinic_owner, I want to configure how the odontogram looks and behaves for my clinic — choosing the display mode, default dentition, and customizing condition colors — so that the clinical workflow matches my team's preferences.

**Roles with access:** `clinic_owner`. Doctors can view but not save (read-only).

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  "Configuración de Odontograma" |
| Side-  +---------------------------------+
|  bar   |  [Section 1: Modo de visualización] |
|        |  [Section 2: Dentición por defecto] |
|        |  [Section 3: Colores de condiciones] |
|        |  [Mini odontogram live preview] |
|        |  [Save button]                  |
+--------+---------------------------------+
```

**Layout:** Single column, max-w-3xl, all sections save together with one "Guardar configuración" button at bottom.

---

## Section 1: Modo de Visualización

**Type:** Mode selector using two large toggle cards side by side (2-column grid on tablet+, stacked on mobile).

### Mode Card Component

Each card contains:
- Thumbnail image (200x150px, illustrative screenshot of the mode)
- Mode name (text-base font-semibold)
- Description (text-sm text-gray-500, 1 line)
- Selection indicator: teal border + checkmark badge when selected

**Card A: Cuadrícula Clásica**
- Thumbnail: grid layout of tooth icons
- Label: "Cuadrícula Clásica"
- Description: "Vista tradicional en cuadrícula 8×4. Compatible con todos los planes."
- Availability: always available (all plans)
- Selection state: teal border `ring-2 ring-teal-600`, checkmark badge `bg-teal-600`

**Card B: Arco Anatómico**
- Thumbnail: arch/curved tooth layout
- Label: "Arco Anatómico"
- Description: "Vista anatómica que refleja la forma real de la mandíbula. Starter o superior."
- Availability: Starter+ plans only
- If plan is Free: lock icon overlay on thumbnail, card is disabled (opacity-50 + cursor-not-allowed), tooltip "Disponible desde el plan Starter", upgrade link "Actualizar plan" shows below the card

**Interaction:**
- Click a card → it becomes selected (border + checkmark appears)
- Only one card can be selected at a time (radio behavior)

---

## Section 2: Dentición por Defecto

**Type:** Radio button group styled as button pills

**Options:**
- "Adulto (32 piezas)" — FDI adult notation, quadrants 1-4
- "Pediátrico (20 piezas)" — FDI pediatric notation, quadrants 5-8

**Layout:** Two pill buttons (h-10, rounded-full, `px-6`) side by side.
- Selected: `bg-teal-600 text-white`
- Unselected: `bg-white border border-gray-300 text-gray-700 hover:bg-gray-50`

**Helper text below:** "Esta configuración se aplica como dentición inicial al abrir el odontograma de un nuevo paciente. Puede cambiarse por paciente individual."

---

## Section 3: Colores de Condiciones

**Layout:** Vertical list of 12 condition rows. Each row:

```
+-----------------------------------------------+
| [Color swatch 20x20px] Nombre condición       |
|                         [Color picker button] |
+-----------------------------------------------+
```

**Condition rows (12 conditions from design system):**

| # | Condition | Spanish Label | Default Color |
|---|-----------|--------------|---------------|
| 1 | healthy | Sano | `#22C55E` green-500 |
| 2 | caries | Caries | `#EF4444` red-500 |
| 3 | restoration | Restauración | `#3B82F6` blue-500 |
| 4 | extraction | Extracción | `#6B7280` gray-500 |
| 5 | crown | Corona | `#EAB308` yellow-500 |
| 6 | endodontic | Endodoncia | `#A855F7` purple-500 |
| 7 | implant | Implante | `#06B6D4` cyan-500 |
| 8 | fracture | Fractura | `#F97316` orange-500 |
| 9 | sealant | Sellante | `#84CC16` lime-500 |
| 10 | fluorosis | Fluorosis | `#EC4899` pink-500 |
| 11 | temporary | Temporal | `#FCD34D` amber-300 |
| 12 | prosthesis | Prótesis | `#6366F1` indigo-500 |

**Color picker button:** Small button (32x32px) showing current color as background. Click → opens color picker popover.

### Color Picker Popover

**Position:** Below the trigger button.

**Content:**
- Grid of 16 preset color swatches (4x4, 28x28px each)
- Preset colors: full Tailwind palette spectrum
- "Personalizado" hex input field below grid
- "Restablecer" link → resets to DentalOS default for that condition

**Interaction:**
- Click preset → color updates immediately in row swatch and mini preview
- Type hex → validates and updates on blur or Enter
- Click outside popover → closes without canceling (change is live)

---

## Section 4: Mini Odontogram Live Preview

**Position:** Sticky right panel on desktop (lg+). On mobile/tablet: below conditions list, before Save button.

**Content:**
- Small odontogram grid (tooth size: sm = 48x48px) showing all 32 teeth
- Teeth colored with currently selected condition colors
- Title above: "Vista previa"
- Legend below: condition name + color dot for each condition

**Desktop layout (lg+):**
```
+---------------------------+  +-------------------+
| Conditions list           |  | Vista previa      |
|                           |  | [mini odontogram] |
|                           |  | [legend]          |
+---------------------------+  +-------------------+
```

**Update behavior:** Preview re-renders instantly whenever any condition color changes (no save needed for preview).

**Demo state:** Sample teeth are pre-colored with a few conditions to illustrate the color customization (e.g., teeth 16, 36 = caries, teeth 11, 21 = restored).

---

## Form Fields Summary

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| odontogram_mode | radio | "classic_grid" | Required, must be available on current plan |
| default_dentition | radio | "adult" | Required |
| condition_colors | object[12] | DentalOS defaults | Valid hex color per condition |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load config | `/api/v1/tenants/{id}/settings` | GET | `specs/tenants/tenant-settings-get.md` | 5min |
| Save config | `/api/v1/tenants/{id}/settings` | PATCH | `specs/tenants/tenant-settings-update.md` | Invalidate |

### State Management

**Local State (useState):**
- `odontogramMode: 'classic_grid' | 'anatomic_arch'`
- `defaultDentition: 'adult' | 'pediatric'`
- `conditionColors: Record<ConditionCode, string>`
- `isDirty: boolean`
- `openPickerId: ConditionCode | null`

**Server State (TanStack Query):**
- Query key: `['tenant-settings', tenantId]`
- Stale time: 5 minutes

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select odontogram mode | Click mode card | Card highlights, preview mode may change | Visual feedback immediately |
| Select dentition | Click pill button | Button highlights | — |
| Open color picker | Click color swatch button | Popover opens | — |
| Select preset color | Click preset swatch | Color updates row + preview | Live preview refresh |
| Enter custom hex | Type in hex field | Validates format, updates on Enter/blur | Red border if invalid |
| Reset condition color | Click "Restablecer" | Restores default color | Color swatch updates |
| Save configuration | Click "Guardar configuración" | PATCH all settings | Loading button → success toast |
| Try to select Anatomic (Free plan) | Click locked card | Nothing, tooltip shows | Tooltip "Disponible desde Starter" |

---

## Loading & Error States

### Loading State
- Full page skeleton: two side-by-side card skeletons (mode selector), two pill skeletons (dentition), 12 row skeletons (conditions), mini preview skeleton rectangle

### Error State
- Load failure: alert banner "No se pudo cargar la configuración." with retry
- Save failure: error toast, settings not persisted

### Empty State
- Not applicable

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Mode cards stack vertically. Dentition pills full width. Color list single column. Preview below conditions. |
| Tablet (640-1024px) | Mode cards side by side. 2-column grid for conditions list. Preview below. |
| Desktop (> 1024px) | 3-column layout: mode+dentition on left (2/3), preview sticky on right (1/3). |

---

## Accessibility

- **Focus order:** Mode selector (card A → card B) → Dentition (radio group) → Condition rows (top to bottom) → Save button
- **Screen reader:** Mode cards use `role="radio"` and `aria-checked`. Dentition group uses `role="radiogroup"` with `aria-label="Dentición por defecto"`. Color picker popovers are `role="dialog"` with `aria-label="Selector de color para [condition name]"`.
- **Keyboard navigation:** Arrow keys navigate within radio groups. Escape closes color picker popovers. Enter selects color in picker.
- **Language:** All Spanish es-419 labels

---

## Implementation Notes

**File Location:**
- Page: `src/app/(dashboard)/settings/odontograma/page.tsx`
- Components: `src/components/settings/OdontogramModeSelector.tsx`, `src/components/settings/ConditionColorList.tsx`, `src/components/settings/ConditionColorRow.tsx`, `src/components/settings/OdontogramPreview.tsx`

**Hooks Used:**
- `useTenantSettings()` — load current config
- `useUpdateTenantSettings()` — save mutation
- `usePlan()` — check if anatomic mode is available

---

## Test Cases

### Happy Path
1. Customize condition color
   - **Given:** settings page loaded with defaults
   - **When:** click Caries color swatch, select orange from preset, click "Guardar"
   - **Then:** PATCH sent with new color, mini preview shows orange on sample caries tooth

2. Try Anatomic mode on Free plan
   - **Given:** clinic on Free plan
   - **When:** click Anatomic mode card
   - **Then:** card stays disabled, tooltip appears, no selection change

### Edge Cases
1. Invalid hex input: red border, save button disabled until corrected
2. Reset all colors: each condition shows default swatch after reset link click

---

## Acceptance Criteria

- [ ] Mode cards show thumbnails and lock icon for unavailable plans
- [ ] Dentition radio works correctly
- [ ] All 12 condition color pickers work
- [ ] Mini preview updates live on color change
- [ ] Reset restores DentalOS defaults per condition
- [ ] Save sends correct PATCH payload
- [ ] Plan check prevents anatomic mode on Free
- [ ] Read-only for non-owner roles
- [ ] Accessible keyboard navigation throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
