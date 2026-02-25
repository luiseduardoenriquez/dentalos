# ConditionIcon / ConditionBadge — Design System Component Spec

## Overview

**Spec ID:** FE-DS-19

**Component:** `ConditionIcon`, `ConditionBadge`

**File:** `src/components/ui/condition-icon.tsx`

**Description:** Dental-specific icon and badge components for representing the 12 clinical conditions used in DentalOS. Each condition has a canonical color and SVG pictogram sourced from the OD-09 condition catalog. The components are used across the odontogram overlay, condition selection panel, history panel, and clinical records — in three size variants to match each context. `ConditionIcon` renders the icon alone (for overlaying on tooth zones); `ConditionBadge` combines the icon with a color pill and condition name (for lists, panels, and record entries).

**Design System Ref:** `FE-DS-01` (§1.2 clinical colors, §4.8 icon usage), `FE-DS-11` (Badge)

**Priority:** High

**Backend Specs:** `specs/odontogram/OD-09` (condition catalog — canonical colors, icon keys, Spanish names)

**Dependencies:** `FE-DS-01` (design tokens), `FE-DS-11` (badge), `FE-OD-03` (condition panel — primary consumer)

---

## The 12 Dental Conditions

| Code | Spanish Name | English Key | Color Token | Hex | Icon Key |
|------|-------------|-------------|-------------|-----|----------|
| `caries` | Caries | caries | `red-500` | `#EF4444` | `tooth-caries` |
| `obturado` | Obturación / Restauración | restoration | `blue-500` | `#3B82F6` | `tooth-restoration` |
| `corona` | Corona | crown | `amber-500` | `#F59E0B` | `tooth-crown` |
| `ausente` | Ausente / Extracción | extraction | `gray-500` | `#6B7280` | `tooth-absent` |
| `endodoncia` | Endodoncia | endodontic | `pink-500` | `#EC4899` | `tooth-endo` |
| `implante` | Implante | implant | `teal-500` | `#14B8A6` | `tooth-implant` |
| `fractura` | Fractura | fracture | `violet-500` | `#8B5CF6` | `tooth-fracture` |
| `sellante` | Sellante | sealant | `emerald-500` | `#10B981` | `tooth-sealant` |
| `fluorosis` | Fluorosis | fluorosis | `orange-500` | `#F97316` | `tooth-fluorosis` |
| `temporal` | Temporal / Deciduo | temporary | `cyan-500` | `#06B6D4` | `tooth-temp` |
| `protesis` | Prótesis | prosthesis | `purple-500` | `#A855F7` | `tooth-prosthesis` |
| `pilar` | Pilar de Puente | bridge-abutment | `lime-500` | `#84CC16` | `tooth-bridge` |

> Canonical colors are defined by the OD-09 catalog response. These tokens are the authoritative source — the component reads them from the catalog, not hardcoded values. The table above reflects the stable defaults shipped with the initial catalog.

---

## Component 1: `ConditionIcon`

Icon-only rendering. Used when overlaying conditions on tooth zones in the odontogram SVG, or as a compact visual in tight UI layouts (toolbar, legend).

### Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `conditionCode` | `ConditionCode` | — | Yes | One of the 12 canonical condition codes |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | No | Controls pixel dimensions |
| `color` | `string` | From catalog | No | Override hex color (bypasses catalog default) |
| `tooltip` | `boolean` | `false` | No | Show condition name tooltip on hover |
| `className` | `string` | — | No | Additional Tailwind classes |
| `aria-label` | `string` | condition name | No | Override ARIA label |

### Sizes

| Size | Dimensions | Container | Use Case |
|------|-----------|-----------|---------|
| `sm` | 16×16px | `w-4 h-4` | Odontogram zone overlay, compact condition lists, table cells |
| `md` | 24×24px | `w-6 h-6` | Condition selection panel buttons, history panel entries |
| `lg` | 32×32px | `w-8 h-8` | Detail panels, clinical record headers, legend views |

### States

- **Default:** Icon renders in its canonical condition color
- **Hovered (with tooltip):** Tooltip appears below after 400ms delay, `z-50`
- **Dimmed:** `opacity-40` — used when condition is not applicable to the current tooth type
- **Monochrome:** `text-gray-400` — used in read-only/historical overlays (passed via `color` override)

### Rendering

The icon is an inline SVG sprite reference. SVG icons are loaded from the public sprite sheet `/icons/dental-conditions.svg`. Each icon key maps to a `<use href="#icon-{key}">` reference:

```tsx
<svg
  width={sizeMap[size]}
  height={sizeMap[size]}
  className={cn('flex-shrink-0', className)}
  aria-label={ariaLabel ?? conditionName}
  role="img"
>
  <use href={`/icons/dental-conditions.svg#icon-${iconKey}`} fill={color ?? catalogColor} />
</svg>
```

### Tooltip Behavior

When `tooltip={true}`:
- Wraps icon in `<Tooltip>` from Radix UI (`@radix-ui/react-tooltip`)
- Content: condition Spanish name in `text-xs font-medium`
- Position: `side="bottom"` by default, auto-flips if near viewport edge
- Delay: 400ms open, 200ms close
- No tooltip on mobile (touch devices): `hidden sm:block` wrapper on trigger

---

## Component 2: `ConditionBadge`

Combines `ConditionIcon` + color pill background + condition name text. Used in condition lists, history panels, clinical record summaries, and wherever a condition needs a human-readable label alongside the icon.

### Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `conditionCode` | `ConditionCode` | — | Yes | One of the 12 condition codes |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | No | Controls icon size and text size |
| `showLabel` | `boolean` | `true` | No | Whether to show the Spanish condition name |
| `showIcon` | `boolean` | `true` | No | Whether to render the icon (false = label-only pill) |
| `variant` | `'solid' \| 'outline'` | `'solid'` | No | Solid color pill vs outlined border |
| `interactive` | `boolean` | `false` | No | Adds hover/active states for use as a clickable filter |
| `selected` | `boolean` | `false` | No | Active/selected state (ring around badge) |
| `onClick` | `() => void` | — | No | Click handler (used in condition filter UIs) |
| `className` | `string` | — | No | Additional Tailwind classes |

### Sizes — ConditionBadge

| Size | Icon Size | Text | Height | Padding | Use Case |
|------|-----------|------|--------|---------|---------|
| `sm` | `sm` (16px) | `text-xs` | `h-6` (24px) | `px-2 gap-1` | Table cells, compact history lists, odontogram legend |
| `md` | `md` (24px) | `text-sm` | `h-8` (32px) | `px-2.5 gap-1.5` | Condition panel grid, history panel rows, clinical records |
| `lg` | `lg` (32px) | `text-base` | `h-10` (40px) | `px-3 gap-2` | Detail panel headers, selected condition display |

### Variant: Solid (default)

Background is a tinted version of the condition color at 10% opacity (`bg-{color}-50` or `bg-{color}-100`), text in the condition color at 700 shade.

```
[Icon 🔴] Caries          ← bg-red-100 text-red-700 rounded-md
```

### Variant: Outline

Transparent background with a 1px border in the condition color. Used when stacking multiple badges where solid fills would create visual noise.

```
[Icon] Caries             ← border border-red-400 text-red-700 bg-transparent rounded-md
```

### Interactive State (for filter badges)

When `interactive={true}`:
- Adds `cursor-pointer hover:bg-{color}-100 transition-colors duration-100`
- When `selected={true}`: adds `ring-2 ring-offset-1 ring-{color}-400 bg-{color}-100`
- Keyboard: Space/Enter triggers `onClick`
- `role="button"` and `tabIndex={0}` added automatically

### Color Derivation

The badge derives pill colors from the condition catalog color using a fixed luminance mapping:

```typescript
function getConditionBadgeClasses(hex: string, variant: 'solid' | 'outline'): string {
  // Uses the condition code → TW color class mapping from OD-09 catalog response
  // Catalog returns { code, color_tw: 'red', hex: '#EF4444', ... }
  const tw = catalogEntry.color_tw; // 'red', 'blue', 'amber', etc.
  if (variant === 'solid') {
    return `bg-${tw}-100 text-${tw}-700`;
  }
  return `border border-${tw}-400 text-${tw}-700 bg-transparent`;
}
```

---

## Usage Examples

```tsx
// Icon-only, sm — odontogram zone overlay
<ConditionIcon conditionCode="caries" size="sm" />

// Icon with tooltip — toolbar legend
<ConditionIcon conditionCode="endodoncia" size="md" tooltip />

// Standard badge in history panel list
<ConditionBadge conditionCode="corona" size="md" />

// Compact badge in clinical record table cell
<ConditionBadge conditionCode="obturado" size="sm" />

// Large badge in detail panel header
<ConditionBadge conditionCode="implante" size="lg" />

// Outline variant in a legend or multi-badge row
<ConditionBadge conditionCode="fractura" variant="outline" size="sm" />

// Interactive filter badge (selected)
<ConditionBadge
  conditionCode="caries"
  interactive
  selected={activeFilter === 'caries'}
  onClick={() => setActiveFilter('caries')}
  size="sm"
/>

// Icon only, no label (icon-only pill — shows only color swatch circle)
<ConditionBadge conditionCode="sellante" showLabel={false} size="sm" />

// Without icon (label-only pill variant)
<ConditionBadge conditionCode="temporal" showIcon={false} size="md" />
```

---

## ConditionCode Type

```typescript
type ConditionCode =
  | 'caries'
  | 'obturado'
  | 'corona'
  | 'ausente'
  | 'endodoncia'
  | 'implante'
  | 'fractura'
  | 'sellante'
  | 'fluorosis'
  | 'temporal'
  | 'protesis'
  | 'pilar';

interface ConditionCatalogEntry {
  code: ConditionCode;
  name_es: string;          // "Caries", "Obturación", etc.
  color_tw: string;         // "red", "blue", "amber" — Tailwind color name
  hex: string;              // "#EF4444" — for SVG fill
  icon_key: string;         // "tooth-caries" — sprite reference
  description_es: string;  // Short clinical description
}
```

The component fetches the catalog from TanStack Query cache (shared with the odontogram). It does not re-fetch — the catalog is loaded once per session.

---

## Context Usage Map

| Screen | Component Used | Size | Variant | Notes |
|--------|---------------|------|---------|-------|
| Odontogram zone overlay (FE-OD-01, FE-OD-02) | `ConditionIcon` | `sm` | — | Overlaid on SVG tooth zone, no tooltip on tablet |
| Condition selection panel (FE-OD-03) | `ConditionIcon` + `ConditionBadge` | `md` | solid | Icon in grid button; badge in active-condition display |
| History panel (FE-OD-05) | `ConditionBadge` | `sm` | solid | One badge per history entry row |
| Comparison view (FE-OD-06) | `ConditionBadge` | `sm` | outline | Two columns of badges for before/after |
| Clinical record entry (FE-CR-01) | `ConditionBadge` | `md` | solid | Listed conditions per visit |
| Clinical record detail header | `ConditionBadge` | `lg` | solid | Primary condition of the visit |
| Condition filter (reports, analytics) | `ConditionBadge` | `sm` | solid | `interactive={true}`, multi-select group |
| Odontogram legend (FE-OD-01 toolbar) | `ConditionBadge` | `sm` | outline | All 12 conditions in a horizontal scroll legend |

---

## Loading State

When the condition catalog has not yet loaded (TanStack Query pending):
- `ConditionIcon`: renders a `w-{size} h-{size} rounded-full bg-gray-200 animate-pulse` placeholder
- `ConditionBadge`: renders a `h-6 w-20 rounded-md bg-gray-200 animate-pulse` skeleton pill

```tsx
if (!catalogEntry) {
  return <span className={cn('rounded-full bg-gray-200 animate-pulse', skeletonSize[size])} />;
}
```

---

## Accessibility

- **`ConditionIcon`:** Always has `role="img"` and `aria-label` equal to the Spanish condition name. When used decoratively inside a `ConditionBadge` that already has a label, `aria-hidden="true"` is set on the icon.
- **`ConditionBadge`:** The wrapping element has `aria-label="{conditionName}"` when `showLabel={false}` to ensure screen reader announces the condition. When `showLabel={true}`, the visible text is sufficient.
- **Interactive badges:** `role="button"`, `tabIndex={0}`, `aria-pressed={selected}`. Space and Enter trigger `onClick`.
- **Color alone:** Icon pictogram provides a second encoding beyond color. The SVG icon is distinct per condition (not just color-differentiated) to support users with color vision deficiency.
- **Contrast:** All solid badge combinations (100-level background, 700-level text) meet WCAG AA 4.5:1. Outline variants use the same 700-level text on white background.
- **Language:** All Spanish names are in es-419 as served by the OD-09 catalog.

---

## Design Tokens

**Icon colors:** Loaded from OD-09 catalog. Stable defaults:
- Caries: `fill-red-500` / `#EF4444`
- Obturado: `fill-blue-500` / `#3B82F6`
- Corona: `fill-amber-500` / `#F59E0B`
- Ausente: `fill-gray-500` / `#6B7280`
- Endodoncia: `fill-pink-500` / `#EC4899`
- Implante: `fill-teal-500` / `#14B8A6`
- Fractura: `fill-violet-500` / `#8B5CF6`
- Sellante: `fill-emerald-500` / `#10B981`
- Fluorosis: `fill-orange-500` / `#F97316`
- Temporal: `fill-cyan-500` / `#06B6D4`
- Prótesis: `fill-purple-500` / `#A855F7`
- Pilar: `fill-lime-500` / `#84CC16`

**Badge radius:** `rounded-md` (solid and outline variants)

**Spacing:**
- `sm` badge: `px-2 gap-1`
- `md` badge: `px-2.5 gap-1.5`
- `lg` badge: `px-3 gap-2`

**Tooltip:**
- Background: `bg-gray-900`
- Text: `text-xs text-white px-2 py-1 rounded`
- Arrow: Radix UI default

---

## Implementation Notes

**Dependencies (npm):**
- `@radix-ui/react-tooltip` — tooltip for `ConditionIcon` tooltip variant
- `lucide-react` — no Lucide icons; dental icons are custom SVG sprite
- `clsx` / `tailwind-merge` — via `cn()` utility

**File Location:**
- Component: `src/components/ui/condition-icon.tsx`
- SVG sprite: `public/icons/dental-conditions.svg`
- Types: `src/types/odontogram.ts` (`ConditionCode`, `ConditionCatalogEntry`)
- Condition catalog hook: `src/hooks/useConditionCatalog.ts`

**Catalog Hook:**

```typescript
// src/hooks/useConditionCatalog.ts
export function useConditionCatalog() {
  return useQuery({
    queryKey: ['odontogram-conditions'],
    queryFn: () => api.get('/api/v1/odontogram/conditions'),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours — catalog is stable
  });
}

export function useConditionEntry(code: ConditionCode): ConditionCatalogEntry | undefined {
  const { data } = useConditionCatalog();
  return data?.find(c => c.code === code);
}
```

**SVG Sprite Generation:**
- Dental condition icons are custom-designed SVGs (not Lucide)
- Sprite is generated at build time from `src/assets/dental-icons/` directory
- Each SVG is a 24×24 viewBox with a single path in `currentColor`
- Script: `scripts/build-dental-icon-sprite.ts` → `public/icons/dental-conditions.svg`

**Safelist Tailwind dynamic classes:**

Because condition colors are constructed dynamically (`bg-${tw}-100`), add the condition color classes to Tailwind safelist in `tailwind.config.ts`:

```typescript
safelist: [
  { pattern: /^(bg|text|border|ring|fill)-(red|blue|amber|gray|pink|teal|violet|emerald|orange|cyan|purple|lime)-(100|400|500|700)$/ }
]
```

---

## Test Cases

### Happy Path

1. Render all 12 condition icons
   - **Given:** OD-09 catalog loaded with 12 entries
   - **When:** `<ConditionIcon conditionCode="caries" size="md" />` is rendered for each code
   - **Then:** Each icon renders with its canonical SVG and color; no placeholder shown

2. ConditionBadge with label
   - **Given:** Catalog loaded
   - **When:** `<ConditionBadge conditionCode="endodoncia" size="md" />`
   - **Then:** Pink-100 background, pink-700 text "Endodoncia", tooth-endo SVG icon at 24px

3. Interactive badge selection
   - **Given:** Condition filter row with 12 interactive badges
   - **When:** User clicks "Caries" badge
   - **Then:** Badge gets `ring-2 ring-red-400`, `aria-pressed="true"`; onClick called

4. Tooltip appears on hover
   - **Given:** `<ConditionIcon conditionCode="corona" tooltip />`
   - **When:** User hovers icon for 400ms
   - **Then:** Tooltip "Corona" appears below icon

### Edge Cases

1. Unknown condition code
   - **Given:** `conditionCode="unknown_code"` passed
   - **When:** Component renders
   - **Then:** Renders gray skeleton placeholder with `aria-label="Condición desconocida"` — no crash

2. Catalog not yet loaded
   - **Given:** `useConditionCatalog` is pending
   - **When:** `<ConditionIcon conditionCode="caries" />` renders
   - **Then:** Animated skeleton circle shown; no hydration error

3. Tooltip suppressed on mobile
   - **Given:** Touch device (pointer: coarse)
   - **When:** `<ConditionIcon conditionCode="caries" tooltip />` renders
   - **Then:** Tooltip trigger not rendered; icon shows without tooltip wrapper

### Error Cases

1. SVG sprite fails to load
   - **Given:** `/icons/dental-conditions.svg` returns 404
   - **When:** Icon renders
   - **Then:** `<use>` element renders but shows nothing; fallback: colored circle `<span className="w-4 h-4 rounded-full bg-{color}" />` via `onError` handler

---

## Acceptance Criteria

- [ ] All 12 condition codes render distinct SVG icons with canonical colors
- [ ] Three size variants (sm, md, lg) render at correct pixel dimensions
- [ ] ConditionIcon with `tooltip` shows condition Spanish name on hover
- [ ] ConditionBadge solid variant: correct background (100-level) and text (700-level) per condition
- [ ] ConditionBadge outline variant: transparent background, border in condition color
- [ ] Interactive badges: hover state, selected ring, aria-pressed, keyboard accessible
- [ ] Skeleton placeholder shown when catalog is loading (no layout shift)
- [ ] Graceful fallback when catalog entry not found (no crash)
- [ ] `aria-label` present on all icons (hidden when label is visible)
- [ ] Dynamic Tailwind classes safelisted (no missing styles in production build)
- [ ] SVG sprite built at compile time, served from `/public`
- [ ] All Spanish names sourced from OD-09 catalog (not hardcoded)
- [ ] Touch targets: interactive badges min 44px via parent container
- [ ] Tooltip does not render on touch devices

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — 12 conditions, 3 sizes, icon + badge variants |
