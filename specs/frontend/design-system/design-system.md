# DentalOS Design System -- Frontend Specification

## Overview

**Spec ID:** FE-DS-01

**Description:** Complete design system specification for DentalOS, defining the visual language, component library, clinical-specific components, and implementation patterns that every frontend screen inherits. Built on TailwindCSS + shadcn/ui with a medical/clinical aesthetic -- clean, professional, and high-contrast for clinical readability in dental practice environments.

**Priority:** Critical

**Stack:** Next.js 14+ App Router, TailwindCSS, shadcn/ui, Lucide React icons, Framer Motion, React Hook Form + Zod

**Backend Spec Ref:** `infra/design-system.md` (tokens, Tailwind config, color palette definitions)

**Dependencies:** None (foundational spec; all frontend specs reference this)

**Design Philosophy:**
- Tablet-first: dental clinics primarily use tablets (iPad, Samsung Tab) during patient consultations
- Clinical readability: high contrast, clear typographic hierarchy, generous spacing
- Medical professionalism: trustworthy blue tones, clean surfaces, minimal visual noise
- LATAM-native: all labels, messages, and ARIA attributes default to Spanish (es-419)

---

## 1. Color Palette

### 1.1 Brand Colors

| Role | Token | Hex | TailwindCSS | Rationale |
|------|-------|-----|-------------|-----------|
| **Primary** | `blue-600` | `#2563EB` | `bg-blue-600` | Trust, medical authority, corporate calm |
| Primary hover | `blue-700` | `#1D4ED8` | `hover:bg-blue-700` | Darkened primary for hover/active states |
| Primary light | `blue-50` | `#EFF6FF` | `bg-blue-50` | Selected rows, soft backgrounds |
| **Secondary** | `teal-600` | `#0D9488` | `bg-teal-600` | Health, freshness, dental hygiene association |
| Secondary hover | `teal-700` | `#0F766E` | `hover:bg-teal-700` | Darkened secondary for hover/active states |
| Secondary light | `teal-50` | `#F0FDFA` | `bg-teal-50` | Light backgrounds for secondary context |
| **Accent** | `amber-600` | `#D97706` | `bg-amber-600` | Warnings, attention, call-to-action highlights |
| Accent light | `amber-50` | `#FFFBEB` | `bg-amber-50` | Soft warning backgrounds |

### 1.2 Clinical Status Colors (Odontogram)

These 12 colors map directly to dental conditions rendered on tooth surfaces in the odontogram SVG. Each color must maintain WCAG AA contrast when used as foreground on its corresponding light background.

| Condition | Spanish Label | Color Token | Hex | Background Hex | Usage |
|-----------|--------------|-------------|-----|----------------|-------|
| Healthy | Sano | `green-500` | `#22C55E` | `#F0FDF4` | Healthy tooth surfaces |
| Caries | Caries | `red-500` | `#EF4444` | `#FEF2F2` | Active decay zones |
| Restoration | Restauracion | `blue-500` | `#3B82F6` | `#EFF6FF` | Composite/amalgam fills |
| Extraction | Extraccion | `gray-500` | `#6B7280` | `#F9FAFB` | Missing or extracted teeth |
| Crown | Corona | `yellow-500` | `#EAB308` | `#FEFCE8` | Prosthetic crowns |
| Endodontic | Endodoncia | `purple-500` | `#A855F7` | `#FAF5FF` | Root canal treatments |
| Implant | Implante | `cyan-500` | `#06B6D4` | `#ECFEFF` | Dental implants |
| Fracture | Fractura | `orange-500` | `#F97316` | `#FFF7ED` | Tooth fractures |
| Sealant | Sellante | `lime-500` | `#84CC16` | `#F7FEE7` | Pit and fissure sealants |
| Fluorosis | Fluorosis | `pink-500` | `#EC4899` | `#FDF2F8` | Enamel fluorosis |
| Temporary | Temporal | `amber-300` | `#FCD34D` | `#FFFBEB` | Temporary restorations |
| Prosthesis | Protesis | `indigo-500` | `#6366F1` | `#EEF2FF` | Fixed/removable prosthetics |

### 1.3 Semantic Colors

| Semantic | Token | Hex | Background | Usage |
|----------|-------|-----|------------|-------|
| Success | `green-600` | `#16A34A` | `green-50` | Saved successfully, confirmed, paid |
| Warning | `amber-600` | `#D97706` | `amber-50` | Pending action, approaching deadline |
| Error | `red-600` | `#DC2626` | `red-50` | Validation errors, failed operations |
| Info | `blue-600` | `#2563EB` | `blue-50` | Informational notices, tips |

### 1.4 Neutrals

Standard TailwindCSS gray scale used for text, borders, backgrounds, and structural elements.

| Token | Hex | Usage |
|-------|-----|-------|
| `gray-50` | `#F9FAFB` | Page backgrounds, subtle fills |
| `gray-100` | `#F3F4F6` | Card backgrounds, table header rows |
| `gray-200` | `#E5E7EB` | Borders, dividers, input outlines |
| `gray-300` | `#D1D5DB` | Disabled borders, placeholder text |
| `gray-400` | `#9CA3AF` | Muted icons, secondary labels |
| `gray-500` | `#6B7280` | Secondary body text |
| `gray-600` | `#4B5563` | Primary body text |
| `gray-700` | `#374151` | Headings, strong labels |
| `gray-800` | `#1F2937` | Dark UI elements, dark mode surfaces |
| `gray-900` | `#111827` | Near-black text, dark mode backgrounds |

### 1.5 Dark Mode Support

All components support a `dark:` variant. Dark mode inverts the neutral scale and adjusts primary/semantic colors for luminance.

| Light Mode | Dark Mode | Context |
|------------|-----------|---------|
| `gray-50` (page bg) | `gray-950` | Page background |
| `white` (card bg) | `gray-900` | Card/surface background |
| `gray-200` (borders) | `gray-700` | Borders and dividers |
| `gray-700` (headings) | `gray-100` | Heading text |
| `gray-600` (body) | `gray-300` | Body text |
| `blue-600` (primary) | `blue-400` | Primary actions and links |

Implementation: `darkMode: "class"` in Tailwind config. Theme stored per-user in localStorage and respects `prefers-color-scheme` as default.

---

## 2. Typography

### 2.1 Font Family

**Primary:** Inter -- designed for screens, excellent readability at small sizes, full Latin American character support (accented vowels, n-tilde).

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
             'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
```

**Monospace** (IDs, codes, timestamps):

```css
font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
```

**Loading:** `next/font/google` with `display: swap` to avoid FOIT.

### 2.2 Type Scale

| Token | Size | Line Height | Weight | Usage |
|-------|------|-------------|--------|-------|
| `text-xs` | 12px / 0.75rem | 16px | normal | Timestamps, captions, fine print, badge text |
| `text-sm` | 14px / 0.875rem | 20px | normal/medium | Table cells, form labels, secondary text, nav items |
| `text-base` | 16px / 1rem | 24px | normal | Body text, form input values, default paragraph |
| `text-lg` | 18px / 1.125rem | 28px | semibold | Card titles, subheadings, modal titles |
| `text-xl` | 20px / 1.25rem | 28px | semibold | Section headings within pages |
| `text-2xl` | 24px / 1.5rem | 32px | bold | Page titles (e.g., "Pacientes", "Odontograma") |
| `text-3xl` | 30px / 1.875rem | 36px | bold | Dashboard metric labels |
| `text-4xl` | 36px / 2.25rem | 40px | bold | Hero KPI numbers (revenue, patient count) |

### 2.3 Spanish Text Considerations

- Spanish words average 20% longer than English equivalents; UI labels must accommodate this
- Accented characters (a, e, i, o, u) and n-tilde must render correctly in all weights
- Truncation with `truncate` or `line-clamp-2` for long names like "Maria del Carmen Gutierrez Rodriguez"
- Currency formatting: `$1.250.000` (dot thousands separator, no decimal for COP) or `$12,500.00` (comma decimal for MXN)

---

## 3. Spacing System

**Base unit:** 4px grid (TailwindCSS default). All spacing, padding, margins, and gaps use multiples of 4px.

### 3.1 Container Widths

| Breakpoint | Container Max Width | Horizontal Padding | TailwindCSS |
|------------|--------------------|--------------------|-------------|
| Mobile (< 640px) | Full width | 16px | `px-4` |
| Tablet (640-1023px) | Full width | 24px | `md:px-6` |
| Desktop (1024-1279px) | 1152px | 32px | `lg:px-8 lg:max-w-6xl` |
| Large Desktop (1280px+) | 1280px | 32px | `xl:max-w-7xl` |

### 3.2 Common Spacing Patterns

| Context | Value | TailwindCSS |
|---------|-------|-------------|
| Card internal padding | 16px mobile, 24px tablet+ | `p-4 md:p-6` |
| Form field vertical gap | 16px | `space-y-4` |
| Section vertical gap | 32px | `space-y-8` |
| Button group horizontal gap | 8px | `gap-2` |
| Table cell padding | 12px vertical, 16px horizontal | `py-3 px-4` |
| Modal body padding | 24px | `p-6` |
| Page title to content | 24px | `mb-6` |

---

## 4. Component Library (shadcn/ui Base)

All components extend shadcn/ui primitives with DentalOS theming. Install via `npx shadcn-ui@latest add [component]` and customize in `src/components/ui/`.

### 4.1 Button

**Variants:**

| Variant | Background | Text | Border | Use Case |
|---------|-----------|------|--------|----------|
| `primary` | `blue-600` | `white` | none | Save, Create, Confirm, primary CTAs |
| `secondary` | `gray-100` | `gray-700` | none | Cancel, Back, secondary actions |
| `outline` | `transparent` | `blue-600` | `blue-600` 1px | Tertiary actions, filter toggles |
| `ghost` | `transparent` | `gray-600` | none | Minimal emphasis, toolbar icon buttons |
| `destructive` | `red-600` | `white` | none | Delete, Remove, destructive actions |
| `icon-only` | varies per context | varies | varies | Square button with icon, no text label |

**Sizes:**

| Size | Height | Horizontal Padding | Font Size | Icon Size |
|------|--------|--------------------|-----------|-----------|
| `sm` | 32px | 12px | text-sm (14px) | 16px (`w-4 h-4`) |
| `default` | 40px | 16px | text-sm (14px) | 20px (`w-5 h-5`) |
| `lg` | 48px | 24px | text-base (16px) | 20px (`w-5 h-5`) |

**Loading State:** When `isLoading={true}`, button text is replaced by a spinner SVG (`animate-spin`). Button is disabled during loading. Width remains stable (no layout shift).

```tsx
<Button variant="primary" size="default" isLoading={isSaving}>
  {isSaving ? "Guardando..." : "Guardar paciente"}
</Button>
```

### 4.2 Input

**Types supported:** `text`, `email`, `phone` (with +57/+52/+56 country prefix), `password` (with visibility toggle), `number`, `date`, `textarea` (auto-grow).

**Structure:**

```
Label (text-sm, font-medium, gray-700)
[Input field] (h-10, rounded-md, border gray-200)
Helper text (text-xs, gray-400) OR Error message (text-xs, red-600)
```

**States:**

| State | Border | Ring | Background | Label Color |
|-------|--------|------|-----------|-------------|
| Default | `gray-200` | none | `white` | `gray-700` |
| Focus | `blue-500` | `ring-2 ring-blue-500/20` | `white` | `blue-600` |
| Error | `red-500` | `ring-2 ring-red-500/20` | `red-50` | `red-600` |
| Disabled | `gray-200` | none | `gray-50` | `gray-400` |

**Integration:** All inputs use React Hook Form `register()` or `Controller` + Zod schemas for validation. Error messages display in Spanish (es-419).

### 4.3 Select / Combobox

| Variant | Description | Use Case |
|---------|-------------|----------|
| `single` | Standard dropdown, single value | Status, gender, document type |
| `multi` | Tag-based multi-select | Allergies, medical conditions, specialties |
| `searchable` | Type-to-filter with keyboard navigation | Doctor selection, patient search |
| `async` | Remote search with debounce (300ms, min 2 chars) | CIE-10 code, CUPS procedure, medication search |

**Async search display format:** `[CODE] - [Descripcion]` (e.g., `K02.1 - Caries de la dentina`). Max 20 results per query.

### 4.4 Card

| Variant | Shadow | Border | Use Case |
|---------|--------|--------|----------|
| `default` | `shadow-sm` | none | Standard content cards |
| `clinical` | `shadow-sm` | Left border 4px colored by status | Patient summary, treatment plan status |
| `patient-summary` | `shadow-md` | none | Dashboard patient quick-view card |
| `appointment` | `shadow-sm` | Left border colored by appointment type | Calendar sidebar appointment cards |

**Structure:** `rounded-xl` container, `p-4 md:p-6` padding, optional header with title + action, body content, optional footer with actions.

### 4.5 Table

**Features:** Sortable columns (click header), filterable (search bar + column filters), paginated (10/20/50 per page), selectable rows (checkbox column + bulk actions bar), expandable rows (chevron for inline detail).

**Clinical records table:** Sticky header (`sticky top-0 z-10`), compact density for maximum data visibility, date column with relative time ("hace 3 dias").

**Row density:**

| Density | Row Height | Cell Padding | Use Case |
|---------|-----------|--------------|----------|
| Compact | 40px | `py-2 px-3` | Clinical records, audit logs |
| Default | 52px | `py-3 px-4` | Patient list, appointments |
| Relaxed | 64px | `py-4 px-4` | Dashboard summary tables |

**Implementation:** TanStack Table for headless table logic. shadcn/ui Table components for rendering.

### 4.6 Modal / Dialog

**Sizes:**

| Size | Max Width | Use Case |
|------|-----------|----------|
| `sm` | 400px | Confirmation ("Desea eliminar este paciente?") |
| `md` | 560px | Standard forms (add appointment, add note) |
| `lg` | 720px | Complex forms (patient registration, treatment plan) |
| `full` | 90vw x 90vh | Odontogram full-screen, document viewer, x-ray viewer |

**Structure:** Overlay (`bg-black/50 backdrop-blur-sm`) + container (`rounded-xl shadow-xl bg-white`) with header (title + X close), scrollable body (`p-6`), footer (action buttons, `border-t p-4`).

**Types:**
- `confirmation`: Warning icon + message + "Cancelar" / "Confirmar" buttons
- `form`: Form fields inside body + "Cancelar" / "Guardar" in footer
- `full-screen`: No rounded corners, no overlay, takes full viewport (for odontogram)

### 4.7 Toast

| Type | Icon (Lucide) | Accent Color | Auto-dismiss |
|------|--------------|-------------|--------------|
| `success` | `CheckCircle2` | `green-500` | 5 seconds |
| `error` | `XCircle` | `red-500` | Persistent (manual dismiss) |
| `warning` | `AlertTriangle` | `amber-500` | 8 seconds |
| `info` | `Info` | `blue-500` | 5 seconds |

**Position:** Top-right corner (`top-4 right-4`). Stacked vertically with 8px gap. Max 3 visible (older queued). Animation: slide in from right, fade out on dismiss.

**Implementation:** sonner library (shadcn/ui default toast).

### 4.8 Badge

**Status badges** (used across appointments, invoices, treatment plans):

| Status | Background | Text | Dot |
|--------|-----------|------|-----|
| `programada` | `blue-50` | `blue-700` | `blue-500` |
| `confirmada` | `teal-50` | `teal-700` | `teal-500` |
| `en_progreso` | `amber-50` | `amber-700` | `amber-500` |
| `completada` | `green-50` | `green-700` | `green-500` |
| `cancelada` | `gray-100` | `gray-600` | `gray-400` |
| `no_asistio` | `red-50` | `red-700` | `red-500` |
| `borrador` | `gray-100` | `gray-500` | `gray-400` |
| `pagada` | `green-50` | `green-700` | `green-500` |
| `vencida` | `red-50` | `red-700` | `red-500` |

**Sizes:** `sm` (h-5, text-xs), `md` (h-6, text-sm), `lg` (h-7, text-sm font-medium).

### 4.9 Avatar

| Size | Dimensions | Font Size | Usage |
|------|-----------|-----------|-------|
| `xs` | 24x24 | 10px | Inline references, compact lists |
| `sm` | 32x32 | 12px | Table rows, comment threads |
| `md` | 40x40 | 14px | Card headers, nav profile |
| `lg` | 56x56 | 20px | Patient detail header |
| `xl` | 80x80 | 28px | Profile page, large cards |

**Fallback:** When no photo is available, display initials (first letter of nombre + first letter of apellido) on a deterministic colored background derived from the user's name hash. Colors cycle through: `blue-500`, `teal-500`, `purple-500`, `amber-500`, `pink-500`, `indigo-500`.

### 4.10 Tabs

| Variant | Style | Use Case |
|---------|-------|----------|
| `underline` | Bottom border indicator, horizontal | Patient detail sections, settings tabs |
| `pills` | Rounded pill background on active | Filter toggles, view switches |

**Active state (underline):** `border-b-2 border-blue-600 text-blue-700 font-semibold`. Inactive: `text-gray-500 hover:text-gray-700`.

**Responsive:** Horizontal tabs become scrollable row on mobile (`overflow-x-auto snap-x`). On very small screens, tabs collapse into a `<Select>` dropdown.

### 4.11 Sidebar

**Structure:**

```
Sidebar (w-64 desktop, w-16 tablet collapsed, hidden mobile)
  Logo area (h-16, border-b, flex items-center)
  Navigation groups
    Group label (text-xs, uppercase, tracking-wider, gray-400, px-4, mt-6)
    Nav items (icon + label, h-10, px-3, rounded-lg, gap-3)
      Active: bg-blue-50, text-blue-700, font-medium
      Hover: bg-gray-50
      Default: text-gray-600
  Bottom section (border-t, mt-auto)
    User avatar + name + role
    Settings link
    Logout button
```

**Collapse behavior:** Tablet shows icon-only (w-16) with tooltip labels on hover. Mobile uses off-canvas drawer (280px, overlay). State persisted in localStorage.

**Role-based visibility:** Nav items conditionally rendered based on user role (clinic_owner, doctor, assistant, receptionist). See `M1-NAVIGATION-MAP.md`.

### 4.12 Calendar

| View | Default At | Description |
|------|-----------|-------------|
| Day | Mobile | Single day time grid (30-min slots, 07:00-21:00) |
| Week | Tablet | 7-day grid with time axis, appointments as colored blocks |
| Month | Desktop | Traditional month grid with appointment count dots |

**Features:** Drag-and-drop rescheduling (desktop + tablet), color-coded by type (consulta: blue, procedimiento: teal, urgencia: red, control: amber), current time red line indicator, doctor multi-filter, click empty slot to create appointment.

### 4.13 Skeleton Loaders

Every data-driven component has a matching skeleton variant using `animate-pulse` on `bg-gray-200 dark:bg-gray-700 rounded` blocks.

| Skeleton | Description |
|----------|-------------|
| `SkeletonText` | Single line, width varies (60%-100%), h-4 rounded |
| `SkeletonTitle` | Wider block, h-6 rounded, w-48 |
| `SkeletonAvatar` | Circle matching avatar size |
| `SkeletonCard` | Rectangular block matching card dimensions with inner lines |
| `SkeletonTableRow` | Row of rectangles matching column widths, repeated 5 times |
| `SkeletonChart` | Large rectangular block for chart area |

### 4.14 Empty State

**Structure:** Centered container (`max-w-md py-12 mx-auto text-center`), SVG illustration (200x160px, dental-themed, muted gray-300 tones), title (`text-lg font-semibold text-gray-700`), description (`text-sm text-gray-500 max-w-sm mx-auto mt-2`), CTA button (primary, `mt-6`).

| Context | Title (es-419) | CTA Label | CTA Action |
|---------|---------------|-----------|------------|
| No patients | "No hay pacientes aun" | "Agregar paciente" | Open patient creation form |
| No appointments | "Sin citas programadas" | "Agendar cita" | Open appointment creation |
| No clinical records | "Sin registros clinicos" | "Crear registro" | Open new clinical record |
| No invoices | "Sin facturas" | "Crear factura" | Open invoice creation |
| No search results | "Sin resultados" | "Limpiar filtros" | Reset all filters |
| No treatment plans | "Sin planes de tratamiento" | "Crear plan" | Open treatment plan wizard |

---

## 5. Clinical-Specific Components

These components are unique to DentalOS and live under `src/components/clinical/`.

### 5.1 ToothDiagram

Single tooth SVG rendering with 5 interactive surfaces (mesial, distal, vestibular/bucal, lingual/palatino, oclusal/incisal) plus root zone.

- **Props:** `toothNumber: number` (FDI), `conditions: Condition[]`, `isSelected: boolean`, `onSurfaceClick: (surface) => void`, `size: 'sm' | 'md' | 'lg'`
- **Sizes:** sm (48x48px), md (64x64px), lg (96x96px)
- **Surface colors:** Filled with clinical status color when a condition is applied; white/light gray when healthy
- **Selected state:** Blue ring outline (`ring-2 ring-blue-500`)
- **Touch target:** Each surface minimum 20x20px (sm), 28x28px (md), 40x40px (lg)

### 5.2 OdontogramGrid

Classic grid layout arranging 32 teeth (adult) or 20 teeth (pediatric) in an 8-column by 4-row grid. Upper jaw on top (quadrants 1-2), lower jaw on bottom (quadrants 3-4).

- **Layout:** CSS Grid, `grid-cols-8 gap-1`
- **Quadrant divider:** Vertical center line (2px gray-300) and horizontal center line
- **Tooth numbering:** FDI notation labels above/below each tooth
- **Responsive:** Full width on all breakpoints; tooth size scales proportionally
- **Interaction:** Click tooth to select, condition palette appears below/beside

### 5.3 OdontogramArch

Anatomic arch layout mimicking the natural jaw curvature. Teeth arranged along two curved paths (maxillary and mandibular arches) using SVG path positioning.

- **Rendering:** SVG viewBox scaling, teeth positioned along bezier curve paths
- **Full-screen mode:** Expands to 90vw x 90vh modal for detailed clinical work
- **Pinch-to-zoom:** Supported on tablet/mobile via touch event handling
- **Dark background option:** `bg-gray-900` with lighter tooth fills for enhanced clinical contrast

### 5.4 ConditionBadge

Colored badge displaying a dental condition with its associated clinical color.

- **Props:** `condition: ConditionCode`, `size: 'sm' | 'md'`
- **Render:** Colored dot (8px sm, 12px md) + condition label text
- **Colors:** Maps to clinical status colors from Section 1.2

### 5.5 PatientCard

Compact patient summary card used in dashboards, search results, and sidebar.

- **Content:** Avatar (with initials fallback), full name, age (calculated from birthdate), document number, last visit date (relative: "hace 5 dias"), active conditions count badge, insurance/EPS name
- **Click action:** Navigate to patient detail page
- **Variant:** `compact` (single row, for lists) and `expanded` (card, for dashboards)

### 5.6 VitalSignsBar

Horizontal strip displaying quick patient context during clinical work.

- **Position:** Sticky below header during odontogram/clinical record views
- **Content:** Patient name, age, blood type, known allergies (red badges), active medications count, insurance/EPS
- **Height:** 48px, `bg-blue-50 dark:bg-blue-950 border-b`
- **Responsive:** Scrollable horizontal on mobile, full display on tablet+

---

## 6. Icons

**Library:** Lucide React (`lucide-react`), consistent with shadcn/ui's default icon set. Tree-shakeable, MIT licensed.

**Sizes by context:**

| Context | Size | TailwindCSS |
|---------|------|-------------|
| Button icon (sm) | 16px | `w-4 h-4` |
| Button icon (default/lg) | 20px | `w-5 h-5` |
| Navigation sidebar | 20px | `w-5 h-5` |
| Table cell action | 16px | `w-4 h-4` |
| Page title decoration | 24px | `w-6 h-6` |
| Empty state illustration | 48px | `w-12 h-12` |

**Color:** Icons inherit parent text color via `currentColor`. Never hard-code icon colors.

---

## 7. Shadows and Borders

### 7.1 Elevation Levels

| Level | Token | Usage |
|-------|-------|-------|
| Flat | none | Inline elements, flat lists |
| Level 1 | `shadow-sm` | Cards, input fields at rest |
| Level 2 | `shadow-md` | Elevated cards, dropdowns, popovers |
| Level 3 | `shadow-lg` | Modals, slide-out panels |
| Level 4 | `shadow-xl` | Full-screen overlays, dialogs |

**Dark mode:** Replace shadows with `border border-gray-700` since shadows are invisible on dark backgrounds.

### 7.2 Border Radius

| Element | Radius | Token |
|---------|--------|-------|
| Inputs, selects | 6px | `rounded-md` |
| Buttons | 8px | `rounded-lg` |
| Cards, modals | 12px | `rounded-xl` |
| Avatars, pills | 9999px | `rounded-full` |
| Badges | 4px | `rounded-sm` |

---

## 8. Animation

**Library:** Framer Motion for complex page transitions and orchestrated animations. TailwindCSS `transition-*` utilities for simple hover/focus effects.

### 8.1 Page Transitions

```tsx
// Layout-level page transition wrapper
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -8 }}
  transition={{ duration: 0.2, ease: "easeOut" }}
>
  {children}
</motion.div>
```

### 8.2 Modal Open/Close

- Open: `opacity 0 -> 1` (overlay, 150ms) + `scale 0.95 -> 1, opacity 0 -> 1` (content, 200ms ease-out)
- Close: reverse with 150ms duration

### 8.3 Hover Effects

- Buttons: `transition-colors duration-150` for background color change
- Cards: `hover:shadow-md transition-shadow duration-200` for subtle lift
- Table rows: `hover:bg-gray-50 transition-colors duration-100`
- Nav items: `hover:bg-gray-50 transition-colors duration-100`

### 8.4 Reduced Motion

All animations respect `prefers-reduced-motion: reduce`. Framer Motion's `useReducedMotion()` hook disables transitions globally.

---

## 9. Dark Mode

### 9.1 Detection and Toggle

1. On first visit, detect system preference via `prefers-color-scheme` media query
2. User can override via toggle in the header (sun/moon icon)
3. Preference stored in `localStorage` key `dental-theme` (`"light" | "dark" | "system"`)
4. Applied via `class` strategy: `<html class="dark">` toggles all `dark:` prefixed utilities

### 9.2 Component Requirements

Every component must define explicit `dark:` variants for:
- Background colors
- Text colors
- Border colors
- Shadow replacements (use borders in dark mode)
- SVG fill/stroke colors (odontogram)

---

## 10. Accessibility

### 10.1 WCAG AA Compliance

| Requirement | Standard | Implementation |
|-------------|----------|----------------|
| Text contrast | 4.5:1 (normal text), 3:1 (large text) | All color pairings verified |
| Focus indicator | Visible focus ring | `ring-2 ring-blue-500 ring-offset-2` on all interactive elements |
| Keyboard navigation | Full support | Tab, Enter, Escape, Arrow keys for all components |
| Screen reader | Meaningful labels | ARIA attributes on all interactive elements |
| Language | `lang="es-419"` | Set on `<html>` element |
| Reduced motion | `prefers-reduced-motion` | Animations disabled when preference set |
| Touch targets | 44x44px minimum | All interactive elements on touch devices |

### 10.2 Spanish ARIA Labels

All ARIA labels, live region announcements, and screen reader text use Latin American Spanish:

- `aria-label="Cerrar dialogo"` (not "Close dialog")
- `aria-label="Buscar pacientes"` (not "Search patients")
- `role="alert"` announcements: "Paciente guardado exitosamente"
- Skip navigation: "Saltar al contenido principal"
- Loading states: `aria-busy="true"` + `aria-label="Cargando datos..."`

---

## 11. File Structure

```
src/
  components/
    ui/                           # shadcn/ui base components (auto-generated + customized)
      button.tsx
      input.tsx
      select.tsx
      card.tsx
      table.tsx
      dialog.tsx
      toast.tsx
      badge.tsx
      avatar.tsx
      tabs.tsx
      skeleton.tsx
      tooltip.tsx
      dropdown-menu.tsx
      popover.tsx
      command.tsx                  # Command palette (search)
      calendar.tsx                # Date picker calendar
      form.tsx                    # React Hook Form integration
    clinical/                     # DentalOS dental-specific components
      tooth-diagram.tsx
      odontogram-grid.tsx
      odontogram-arch.tsx
      condition-badge.tsx
      patient-card.tsx
      vital-signs-bar.tsx
      tooth-selector.tsx
      condition-palette.tsx
    layout/                       # Application shell components
      app-sidebar.tsx
      app-header.tsx
      app-shell.tsx               # Sidebar + Header + Main wrapper
      mobile-drawer.tsx
      page-header.tsx             # Page title + breadcrumb + actions
    shared/                       # Cross-cutting reusable components
      empty-state.tsx
      loading-spinner.tsx
      confirm-dialog.tsx
      data-table.tsx              # TanStack Table wrapper
      search-combobox.tsx         # Async search (CIE-10, CUPS)
      file-upload.tsx
      signature-pad.tsx
  lib/
    utils.ts                      # cn() helper, formatters
    constants.ts                  # Color maps, status labels
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial frontend design system specification |
