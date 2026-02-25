# DentalOS Design System Spec

## Overview

**Feature:** Complete design system specification for DentalOS, defining the visual foundation -- color palette, typography, spacing, component library, and TailwindCSS configuration -- that all frontend screens and components inherit from.

**Domain:** infra

**Priority:** Critical

**Dependencies:** None (foundational spec; all frontend specs reference this)

**Spec ID:** I-28

---

## 1. Color Palette

### 1.1 Brand Colors

DentalOS uses a teal/cyan primary palette that conveys medical professionalism, trust, and cleanliness -- universal associations in healthcare UI design. The palette is optimized for WCAG AA contrast compliance.

**Primary -- Teal/Cyan**

| Token | Hex | Usage |
|-------|-----|-------|
| `primary-50` | `#ECFEFF` | Background tints, hover states |
| `primary-100` | `#CFFAFE` | Light backgrounds, selected row |
| `primary-200` | `#A5F3FC` | Borders, dividers |
| `primary-300` | `#67E8F9` | Inactive/secondary icons |
| `primary-400` | `#22D3EE` | Hover states on primary elements |
| `primary-500` | `#06B6D4` | Secondary actions, links |
| `primary-600` | `#0891B2` | **Base primary.** Buttons, active nav, badges |
| `primary-700` | `#0E7490` | Hover on primary buttons |
| `primary-800` | `#155E75` | Active/pressed state |
| `primary-900` | `#164E63` | Dark mode primary text |
| `primary-950` | `#083344` | Dark mode backgrounds |

**Secondary -- Slate**

| Token | Hex | Usage |
|-------|-----|-------|
| `slate-50` | `#F8FAFC` | Page backgrounds |
| `slate-100` | `#F1F5F9` | Card backgrounds, table headers |
| `slate-200` | `#E2E8F0` | Borders, dividers |
| `slate-300` | `#CBD5E1` | Disabled states, placeholder text |
| `slate-400` | `#94A3B8` | Secondary text, icons |
| `slate-500` | `#64748B` | Body text (secondary) |
| `slate-600` | `#475569` | Body text (primary) |
| `slate-700` | `#334155` | Headings |
| `slate-800` | `#1E293B` | Dark UI elements |
| `slate-900` | `#0F172A` | Dark mode surface |
| `slate-950` | `#020617` | Dark mode background |

### 1.2 Semantic Colors

| Token | Hex | Usage |
|-------|-----|-------|
| **Accent** | | |
| `accent-400` | `#FBBF24` | Warning icons, attention badges |
| `accent-500` | `#F59E0B` | Warning buttons, highlights |
| `accent-600` | `#D97706` | Warning text |
| **Success** | | |
| `success-100` | `#D1FAE5` | Success background |
| `success-500` | `#10B981` | Success icons, badges |
| `success-600` | `#059669` | Success text |
| `success-700` | `#047857` | Success dark text |
| **Error** | | |
| `error-100` | `#FEE2E2` | Error background |
| `error-500` | `#EF4444` | Error icons, badges |
| `error-600` | `#DC2626` | Error text |
| `error-700` | `#B91C1C` | Error dark text |
| **Warning** | | |
| `warning-100` | `#FEF3C7` | Warning background |
| `warning-500` | `#F59E0B` | Warning icons |
| `warning-600` | `#D97706` | Warning text |
| **Info** | | |
| `info-100` | `#DBEAFE` | Info background |
| `info-500` | `#3B82F6` | Info icons |
| `info-600` | `#2563EB` | Info text |

### 1.3 Clinical Condition Colors

These 12 colors map directly to the dental conditions used in the odontogram (see `odontogram/odontogram-conditions-catalog.md`). Each condition has a background, foreground, and SVG fill color.

| Condition | Code | Background | Foreground (SVG fill) | Text Label |
|-----------|------|------------|----------------------|------------|
| Sano | `sano` | `#E8F5E9` | `#4CAF50` | Sano |
| Caries | `caries` | `#FFEBEE` | `#EF4444` | Caries |
| Resina (Composite) | `resina` | `#E3F2FD` | `#3B82F6` | Resina |
| Amalgama | `amalgama` | `#ECEFF1` | `#78909C` | Amalgama |
| Corona | `corona` | `#FFF8E1` | `#FFC107` | Corona |
| Ausente (Missing) | `ausente` | `#ECEFF1` | `#37474F` | Ausente |
| Implante | `implante` | `#EDE7F6` | `#7C3AED` | Implante |
| Endodoncia (Root canal) | `endodoncia` | `#FCE4EC` | `#EC4899` | Endodoncia |
| Sellante (Sealant) | `sellante` | `#E8F5E9` | `#10B981` | Sellante |
| Fractura | `fractura` | `#FFF3E0` | `#F97316` | Fractura |
| Caries Profunda | `caries_profunda` | `#FBE9E7` | `#991B1B` | Caries Prof. |
| Abrasion | `abrasion` | `#FFF8E1` | `#D97706` | Abrasion |

**Usage rules:**

- Background color is used for badges, pills, and table cell highlights
- Foreground color is used for SVG zone fills in the odontogram and icon/text in badges
- All condition colors must pass WCAG AA contrast ratio when foreground is placed on background
- In dark mode, backgrounds become darker variants and foreground colors increase luminance by 10-15%

### 1.4 Dark Mode

DentalOS supports dark mode, with a specific use case: the odontogram anatomic rendering mode uses a dark theme by default for better visual contrast of dental conditions against tooth surfaces.

**Dark mode color mapping:**

| Light Mode | Dark Mode |
|------------|-----------|
| `slate-50` (page bg) | `slate-950` |
| `slate-100` (card bg) | `slate-900` |
| `slate-200` (borders) | `slate-700` |
| `white` (surface) | `slate-800` |
| `slate-700` (headings) | `slate-100` |
| `slate-600` (body text) | `slate-300` |
| `primary-600` (accent) | `primary-400` |

**Implementation:** CSS custom properties with `dark:` variant in TailwindCSS. Theme preference is stored per-user and respects `prefers-color-scheme` as the default.

---

## 2. Typography

### 2.1 Font Family

**Primary:** Inter

Inter is a typeface designed for computer screens with a focus on readability at small sizes. It supports Latin American character sets including accented characters (a, e, i, o, u with accents, n with tilde).

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
             'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
```

**Monospace (code, IDs, timestamps):**

```css
font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
```

**Loading strategy:** `next/font/google` with `display: swap` to prevent FOIT (Flash of Invisible Text).

### 2.2 Type Scale

All sizes use `rem` units based on a 16px root. The scale follows a 1.25 ratio (Major Third).

| Token | Size (px) | Size (rem) | Line Height | Usage |
|-------|-----------|------------|-------------|-------|
| `text-xs` | 12 | 0.75 | 1rem (16px) | Captions, timestamps, labels on dense UIs |
| `text-sm` | 14 | 0.875 | 1.25rem (20px) | Table cells, secondary text, form labels |
| `text-base` | 16 | 1.0 | 1.5rem (24px) | Body text, form inputs, default |
| `text-lg` | 18 | 1.125 | 1.75rem (28px) | Subheadings, card titles |
| `text-xl` | 20 | 1.25 | 1.75rem (28px) | Section headings |
| `text-2xl` | 24 | 1.5 | 2rem (32px) | Page titles |
| `text-3xl` | 30 | 1.875 | 2.25rem (36px) | Large page titles, dashboard metrics |
| `text-4xl` | 36 | 2.25 | 2.5rem (40px) | Hero numbers (dashboard KPIs) |

### 2.3 Font Weights

| Token | Weight | Usage |
|-------|--------|-------|
| `font-normal` | 400 | Body text, form values |
| `font-medium` | 500 | Labels, navigation items, table headers |
| `font-semibold` | 600 | Subheadings, card titles, badges |
| `font-bold` | 700 | Page titles, KPI numbers, primary buttons |

### 2.4 Typography Conventions

- **Language:** All UI text defaults to Spanish (`es-419` Latin American Spanish)
- **Headings:** Use `font-bold` for page titles (`text-2xl`), `font-semibold` for section headings (`text-xl`)
- **Body:** `text-base font-normal text-slate-600` (light mode), `text-base font-normal text-slate-300` (dark mode)
- **Numbers / Currency:** Use tabular figures (`font-variant-numeric: tabular-nums`) for alignment in tables and invoices
- **Truncation:** Long text uses `truncate` (single line) or `line-clamp-2` / `line-clamp-3` (multi-line)

---

## 3. Spacing System

### 3.1 Base Unit

All spacing derives from a **4px base unit**. This creates a consistent visual rhythm across the interface.

### 3.2 Spacing Scale

| Token | Value (px) | Value (rem) | Usage |
|-------|-----------|-------------|-------|
| `space-0` | 0 | 0 | Reset |
| `space-0.5` | 2 | 0.125 | Tight inline spacing |
| `space-1` | 4 | 0.25 | Icon-to-text gap, minimal padding |
| `space-2` | 8 | 0.5 | Compact padding (pills, badges) |
| `space-3` | 12 | 0.75 | Form field gap, tight card padding |
| `space-4` | 16 | 1.0 | Standard padding, card content |
| `space-5` | 20 | 1.25 | Button padding (horizontal) |
| `space-6` | 24 | 1.5 | Section spacing, card padding |
| `space-8` | 32 | 2.0 | Large section gaps |
| `space-10` | 40 | 2.5 | Major section dividers |
| `space-12` | 48 | 3.0 | Page section gaps |
| `space-16` | 64 | 4.0 | Page-level vertical rhythm |

### 3.3 Spacing Conventions

| Context | Pattern | TailwindCSS |
|---------|---------|-------------|
| Page padding (mobile) | 16px horizontal | `px-4` |
| Page padding (tablet) | 24px horizontal | `md:px-6` |
| Page padding (desktop) | 32px horizontal | `lg:px-8` |
| Card padding | 16px (mobile), 24px (tablet+) | `p-4 md:p-6` |
| Form field gap | 16px vertical | `space-y-4` |
| Button group gap | 8px horizontal | `gap-2` |
| Table cell padding | 12px vertical, 16px horizontal | `py-3 px-4` |
| Modal padding | 24px | `p-6` |
| Section title to content | 16px | `mt-4` |

---

## 4. Border Radius

| Token | Value (px) | Usage |
|-------|-----------|-------|
| `rounded-sm` | 4 | Small elements: badges, chips, inline tags |
| `rounded-md` | 6 | Form inputs, selects |
| `rounded-lg` | 8 | Buttons, cards, modals |
| `rounded-xl` | 12 | Large cards, containers |
| `rounded-2xl` | 16 | Feature panels, hero sections |
| `rounded-full` | 9999 | Avatars, circular buttons, pills |

---

## 5. Shadows (Elevation)

| Token | CSS Value | Usage |
|-------|-----------|-------|
| `shadow-sm` | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | Subtle elevation: cards, inputs |
| `shadow-md` | `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` | Cards, dropdowns |
| `shadow-lg` | `0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)` | Modals, popovers |
| `shadow-xl` | `0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)` | Dialogs, full-screen overlays |

**Dark mode:** Shadows are replaced with border-based elevation (`border border-slate-700`) since shadows are invisible against dark backgrounds.

---

## 6. Component Library

Every reusable UI component in DentalOS, with variants, sizes, and states.

### 6.1 Button

**Variants:**

| Variant | Background | Text | Border | Use Case |
|---------|-----------|------|--------|----------|
| `primary` | `primary-600` | `white` | none | Primary actions (Save, Create, Confirm) |
| `secondary` | `slate-100` | `slate-700` | none | Secondary actions (Cancel, Back) |
| `outline` | `transparent` | `primary-600` | `primary-600` | Tertiary actions, form actions |
| `ghost` | `transparent` | `slate-600` | none | Minimal emphasis (icon buttons in toolbars) |
| `danger` | `error-600` | `white` | none | Destructive actions (Delete, Remove) |
| `icon-only` | varies | varies | varies | Square button with icon, no text |

**Sizes:**

| Size | Height | Padding (h) | Font Size | Icon Size |
|------|--------|-------------|-----------|-----------|
| `sm` | 32px | 12px | 14px (`text-sm`) | 16px |
| `md` | 40px | 16px | 14px (`text-sm`) | 20px |
| `lg` | 48px | 20px | 16px (`text-base`) | 20px |

**States:** `default`, `hover`, `active`, `focus` (ring), `disabled` (opacity 50%, cursor-not-allowed), `loading` (spinner replaces icon/text).

### 6.2 Input

**Types:** `text`, `email`, `password` (with show/hide toggle), `number`, `phone` (with country code prefix +57, +52, +56, +54, +51), `date` (native datepicker or custom), `textarea` (auto-resize).

**States:**

| State | Border | Background | Label Color |
|-------|--------|-----------|-------------|
| Default | `slate-200` | `white` | `slate-600` |
| Focus | `primary-500` (ring-2) | `white` | `primary-600` |
| Error | `error-500` (ring-2) | `error-50` | `error-600` |
| Disabled | `slate-200` | `slate-50` | `slate-400` |

**Structure:**

```
Label (text-sm, font-medium, slate-700)
[Input field]
Helper text (text-xs, slate-400) OR Error message (text-xs, error-600)
```

### 6.3 Select / Combobox

| Variant | Description | Use Case |
|---------|-------------|----------|
| `single` | Single value dropdown | Status, country, gender |
| `multi` | Multiple value tags | Allergies, medical conditions |
| `searchable` | Type-to-filter dropdown | Doctor selection, patient search |
| `async` | Remote search with debounce | CIE-10 code search, CUPS procedure search, medication search |

**Async search specifics (CIE-10/CUPS):**

- Debounce: 300ms
- Minimum characters: 2
- Display format: `[CODE] - [Description]` (e.g., `K02.1 - Caries de la dentina`)
- Results limit: 20 per query

### 6.4 Table

**Features:**

| Feature | Description |
|---------|-------------|
| Sortable columns | Click header to sort asc/desc, visual arrow indicator |
| Pagination | Bottom bar with page numbers, page size selector (10, 20, 50) |
| Row selection | Checkbox column, bulk action bar appears on selection |
| Expandable rows | Chevron to expand inline detail (patient medical summary) |
| Responsive | Horizontal scroll on mobile, priority columns visible |
| Empty state | Custom illustration + message + CTA when no data |
| Loading | Skeleton rows (5 rows) during data fetch |

**Row density:**

| Density | Row Height | Cell Padding |
|---------|-----------|--------------|
| Compact | 40px | `py-2 px-3` |
| Default | 52px | `py-3 px-4` |
| Relaxed | 64px | `py-4 px-4` |

### 6.5 Modal

**Sizes:**

| Size | Max Width | Use Case |
|------|-----------|----------|
| `sm` | 400px | Confirmation dialogs, simple forms |
| `md` | 560px | Standard forms, detail views |
| `lg` | 720px | Complex forms, side-by-side comparison |
| `full` | 90vw / 90vh | Odontogram full view, document viewer |

**Structure:**

```
Overlay (bg-black/50, backdrop-blur-sm)
  Modal container (rounded-xl, shadow-xl, bg-white)
    Header (title + close button, border-b)
    Body (scrollable content area, p-6)
    Footer (action buttons, border-t, p-4)
```

**Types:** `confirmation` (icon + message + yes/no), `form` (form fields + save/cancel), `info` (read-only content + close).

### 6.6 Card

| Variant | Shadow | Border | Background |
|---------|--------|--------|-----------|
| `default` | `shadow-sm` | none | `white` |
| `elevated` | `shadow-md` | none | `white` |
| `outlined` | none | `slate-200` 1px | `white` |

**Standard card structure:**

```
Card (rounded-xl, p-4 md:p-6)
  Card Header (optional: title + action button, mb-4)
  Card Body (content)
  Card Footer (optional: bottom actions, mt-4, pt-4, border-t)
```

### 6.7 Badge / Pill

**Status badges (appointment, invoice, treatment plan):**

| Status | Background | Text | Dot Color |
|--------|-----------|------|-----------|
| scheduled | `info-100` | `info-700` | `info-500` |
| confirmed | `primary-100` | `primary-700` | `primary-500` |
| in_progress | `accent-100` | `accent-700` | `accent-500` |
| completed | `success-100` | `success-700` | `success-500` |
| cancelled | `slate-100` | `slate-600` | `slate-400` |
| no_show | `error-100` | `error-700` | `error-500` |
| draft | `slate-100` | `slate-500` | `slate-400` |
| sent | `info-100` | `info-700` | `info-500` |
| paid | `success-100` | `success-700` | `success-500` |
| overdue | `error-100` | `error-700` | `error-500` |

**Condition badges:** Use the clinical condition colors from Section 1.3. Format: colored dot + condition name.

**Sizes:** `sm` (height 20px, text-xs), `md` (height 24px, text-sm), `lg` (height 28px, text-sm).

### 6.8 Avatar

| Size | Dimensions | Font Size | Usage |
|------|-----------|-----------|-------|
| `xs` | 24x24 | 10px | Compact lists, inline references |
| `sm` | 32x32 | 12px | Table rows, comment threads |
| `md` | 40x40 | 14px | Card headers, navigation |
| `lg` | 56x56 | 20px | Profile cards, patient detail |
| `xl` | 80x80 | 28px | Profile page header |

**Fallback:** When no image is available, display initials (first letter of first name + first letter of last name) on a colored background. Background color is deterministic based on the user's name hash.

### 6.9 Toast / Notification

| Type | Icon | Border Color | Background |
|------|------|-------------|-----------|
| `success` | Checkmark circle | `success-500` | `white` |
| `error` | X circle | `error-500` | `white` |
| `warning` | Alert triangle | `accent-500` | `white` |
| `info` | Info circle | `info-500` | `white` |

**Behavior:**

- Position: top-right corner, stacked vertically
- Auto-dismiss: 5 seconds (configurable; errors persist until manual dismiss)
- Animation: slide in from right, fade out
- Max visible: 3 (older toasts are queued)
- Action button support (e.g., "Deshacer" / Undo)

### 6.10 Sidebar Navigation

**Structure:**

```
Sidebar (w-64 desktop, w-16 tablet collapsed, hidden mobile)
  Logo area (h-16, border-b)
  Navigation groups
    Group label (text-xs, uppercase, slate-400)
    Nav items (icon + label)
      Active: bg-primary-50, text-primary-700, border-l-2 primary-600
      Hover: bg-slate-50
      Default: text-slate-600
  User profile card (bottom, border-t)
    Avatar + name + role
    Settings / Logout links
```

**Collapse behavior:** On tablet, sidebar collapses to icon-only (w-16). Icons show tooltips on hover. On mobile, sidebar is a slide-out drawer triggered by hamburger menu.

**Role-based items:** Navigation items are conditionally rendered based on user role. See `M1-NAVIGATION-MAP.md` for the complete menu structure per role.

### 6.11 Tabs

| Variant | Description | Use Case |
|---------|-------------|----------|
| `horizontal` | Underline-style tabs in a row | Patient detail sections, settings |
| `vertical` | Stacked list with active indicator | Settings pages, long forms |

**Active state:** Underline (`border-b-2 primary-600`) + `text-primary-700` + `font-semibold`.

**Responsive:** Horizontal tabs become a scrollable row on mobile (horizontal scroll with snap). Vertical tabs collapse into a dropdown selector on mobile.

### 6.12 Tooltip

- Trigger: hover (desktop), long-press (mobile/tablet)
- Position: auto (prefers top, falls back to bottom/left/right)
- Delay: 500ms before showing
- Style: `bg-slate-800 text-white text-xs rounded-md px-2 py-1 shadow-lg`
- Max width: 200px

### 6.13 Dropdown Menu

- Trigger: click on a button or icon
- Position: auto (prefers bottom-end)
- Items: icon + label, optional description
- Dividers between groups
- Keyboard navigation: arrow keys, Enter to select, Escape to close
- Style: `bg-white rounded-lg shadow-lg border border-slate-200`

### 6.14 Calendar

| View | Description | Use Case |
|------|-------------|----------|
| `day` | Time grid (30-min slots), appointments as blocks | Doctor daily schedule |
| `week` | 7-day time grid | Clinic weekly overview |
| `month` | Traditional month grid with event dots | Long-range planning |

**Features:**

- Drag-and-drop appointment rescheduling (desktop + tablet)
- Color-coded by appointment type (consultation: primary, procedure: accent, emergency: error, follow_up: info)
- Current time indicator (red line)
- Click empty slot to create appointment
- Doctor filter (multi-select)

### 6.15 Signature Pad

- Canvas-based drawing area
- Minimum size: 300x150px
- Stroke color: `slate-800`
- Stroke width: 2px
- Background: white with subtle grid lines
- Actions: Clear, Undo (last stroke), Done
- Output: base64 PNG (transparent background)
- Touch-optimized for tablet signing (primary use case)

### 6.16 File Upload

- Drag-and-drop zone with dashed border
- Click to browse fallback
- File type icons (image, PDF, document)
- Upload progress bar
- Preview: thumbnail for images, icon for documents
- Allowed types configurable per context (e.g., X-rays: JPEG/PNG/DICOM, documents: PDF)
- Max file size display
- Multiple file support (configurable)

### 6.17 Skeleton Loader

Animated placeholder matching the layout of the content it replaces. Pulse animation (`animate-pulse`).

**Variants:**

| Variant | Usage |
|---------|-------|
| `text` | Single line, rounded, height matches text size |
| `title` | Wider and taller than text |
| `avatar` | Circle matching avatar size |
| `card` | Rectangular block matching card dimensions |
| `table-row` | Row with column-matched skeleton cells |
| `chart` | Rectangular block for chart area |

### 6.18 Empty State

**Structure:**

```
Container (centered, max-w-md, py-12)
  Illustration (SVG, 200x160px, dental-themed)
  Title (text-lg, font-semibold, slate-700)
  Description (text-sm, slate-500, max-w-sm)
  CTA Button (primary, optional)
```

**Illustrations per context:**

| Context | Illustration | Title | CTA |
|---------|-------------|-------|-----|
| No patients | Tooth with magnifying glass | "No hay pacientes aun" | "Agregar paciente" |
| No appointments | Empty calendar | "Sin citas programadas" | "Agendar cita" |
| No clinical records | Empty clipboard | "Sin registros clinicos" | "Crear registro" |
| No invoices | Empty receipt | "Sin facturas" | "Crear factura" |
| No results | Magnifying glass with X | "Sin resultados" | "Limpiar filtros" |

### 6.19 Tooth Selector (Dental-Specific)

Interactive SVG component for selecting teeth in clinical forms.

**Modes:**

| Mode | Description |
|------|-------------|
| `single` | Select one tooth (e.g., procedure form) |
| `multi` | Select multiple teeth (e.g., treatment plan) |
| `display` | Read-only display of selected teeth |

**Display:** FDI notation (11-48 adult, 51-85 pediatric). Visual layout matches dental arch shape. Upper jaw (top), lower jaw (bottom). Selected teeth highlighted with `primary-600`.

Touch target: minimum 44x44px per tooth in tablet/mobile view.

### 6.20 Condition Icon / Badge (Dental-Specific)

Small visual indicators showing dental conditions on teeth and in lists.

**Format:** Colored circle (8x8px or 12x12px) + condition abbreviation (1-3 chars).

| Condition | Abbreviation | Icon Shape |
|-----------|-------------|-----------|
| Sano | SAN | Filled circle |
| Caries | CAR | Filled circle |
| Resina | RES | Filled circle |
| Amalgama | AMA | Filled circle |
| Corona | COR | Filled circle |
| Ausente | AUS | X mark |
| Implante | IMP | Triangle |
| Endodoncia | END | Diamond |
| Sellante | SEL | Filled circle |
| Fractura | FRA | Lightning bolt |
| Caries Prof. | CPR | Double filled circle |
| Abrasion | ABR | Wave line |

---

## 7. TailwindCSS Configuration

### 7.1 tailwind.config.ts

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      // ─── Colors ─────────────────────────────────────
      colors: {
        // Brand
        "dental-primary": {
          50: "#ECFEFF",
          100: "#CFFAFE",
          200: "#A5F3FC",
          300: "#67E8F9",
          400: "#22D3EE",
          500: "#06B6D4",
          600: "#0891B2",
          700: "#0E7490",
          800: "#155E75",
          900: "#164E63",
          950: "#083344",
        },

        // Clinical condition colors (odontogram)
        "dental-sano": "#4CAF50",
        "dental-sano-bg": "#E8F5E9",
        "dental-caries": "#EF4444",
        "dental-caries-bg": "#FFEBEE",
        "dental-resina": "#3B82F6",
        "dental-resina-bg": "#E3F2FD",
        "dental-amalgama": "#78909C",
        "dental-amalgama-bg": "#ECEFF1",
        "dental-corona": "#FFC107",
        "dental-corona-bg": "#FFF8E1",
        "dental-ausente": "#37474F",
        "dental-ausente-bg": "#ECEFF1",
        "dental-implante": "#7C3AED",
        "dental-implante-bg": "#EDE7F6",
        "dental-endodoncia": "#EC4899",
        "dental-endodoncia-bg": "#FCE4EC",
        "dental-sellante": "#10B981",
        "dental-sellante-bg": "#E8F5E9",
        "dental-fractura": "#F97316",
        "dental-fractura-bg": "#FFF3E0",
        "dental-caries-profunda": "#991B1B",
        "dental-caries-profunda-bg": "#FBE9E7",
        "dental-abrasion": "#D97706",
        "dental-abrasion-bg": "#FFF8E1",
      },

      // ─── Typography ─────────────────────────────────
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "Noto Sans",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "Fira Code",
          "Consolas",
          "Courier New",
          "monospace",
        ],
      },

      // ─── Border Radius ──────────────────────────────
      borderRadius: {
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "12px",
        "2xl": "16px",
      },

      // ─── Shadows ────────────────────────────────────
      boxShadow: {
        sm: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        md: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
        lg: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
        xl: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
      },

      // ─── Animations ─────────────────────────────────
      animation: {
        "slide-in-right": "slideInRight 0.3s ease-out",
        "slide-in-bottom": "slideInBottom 0.3s ease-out",
        "fade-in": "fadeIn 0.2s ease-out",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        slideInRight: {
          "0%": { transform: "translateX(100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        slideInBottom: {
          "0%": { transform: "translateY(16px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },

      // ─── Z-Index Scale ──────────────────────────────
      zIndex: {
        "sidebar": "40",
        "header": "50",
        "dropdown": "60",
        "modal-overlay": "70",
        "modal": "80",
        "toast": "90",
        "tooltip": "100",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
    require("tailwindcss-animate"),
  ],
};

export default config;
```

### 7.2 CSS Variables (globals.css)

```css
/* src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --color-primary: 8 145 178;          /* primary-600 RGB */
    --color-primary-hover: 14 116 144;   /* primary-700 RGB */
    --color-background: 248 250 252;     /* slate-50 RGB */
    --color-surface: 255 255 255;        /* white RGB */
    --color-text-primary: 51 65 85;      /* slate-700 RGB */
    --color-text-secondary: 100 116 139; /* slate-500 RGB */
    --color-border: 226 232 240;         /* slate-200 RGB */

    --sidebar-width: 256px;
    --sidebar-collapsed-width: 64px;
    --header-height: 64px;
  }

  .dark {
    --color-primary: 34 211 238;         /* primary-400 RGB */
    --color-primary-hover: 6 182 212;    /* primary-500 RGB */
    --color-background: 2 6 23;          /* slate-950 RGB */
    --color-surface: 15 23 42;           /* slate-900 RGB */
    --color-text-primary: 241 245 249;   /* slate-100 RGB */
    --color-text-secondary: 203 213 225; /* slate-300 RGB */
    --color-border: 51 65 85;            /* slate-700 RGB */
  }

  /* Tabular nums for financial and date data */
  .tabular-nums {
    font-variant-numeric: tabular-nums;
  }

  /* Custom scrollbar for sidebar and tables */
  .dental-scrollbar::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  .dental-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .dental-scrollbar::-webkit-scrollbar-thumb {
    background-color: rgb(var(--color-border));
    border-radius: 9999px;
  }
}
```

---

## 8. Icon Set

**Library:** Lucide React (consistent, open-source, tree-shakeable).

**Default icon size:** 20px (matches `text-base` line height context).

**Icon sizes by context:**

| Context | Size | TailwindCSS |
|---------|------|-------------|
| Button icon | 16px (sm), 20px (md/lg) | `w-4 h-4`, `w-5 h-5` |
| Navigation | 20px | `w-5 h-5` |
| Table cell | 16px | `w-4 h-4` |
| Page title | 24px | `w-6 h-6` |
| Empty state | 48px | `w-12 h-12` |

**Color:** Icons inherit text color by default (`currentColor`).

---

## 9. Accessibility Standards

| Requirement | Standard | Implementation |
|-------------|----------|----------------|
| Color contrast | WCAG 2.1 AA | All text meets 4.5:1 ratio (normal), 3:1 (large) |
| Focus indicators | WCAG 2.1 AA | `ring-2 ring-primary-500 ring-offset-2` on all interactive elements |
| Keyboard navigation | Full | All components navigable via Tab, Enter, Escape, Arrow keys |
| Screen reader | ARIA labels | All interactive elements have accessible names |
| Language | `lang="es-419"` | Set on `<html>` element |
| Motion | `prefers-reduced-motion` | Animations disabled when user prefers reduced motion |
| Touch targets | 44x44px minimum | All clickable elements in clinical tools |

---

## Out of Scope

This spec explicitly does NOT cover:

- Individual component implementation code (see `frontend/design-system/*.md` for each component spec)
- Page layouts and screen-specific designs (see `frontend/screens/*.md`)
- Odontogram SVG rendering specification (see `infra/adr/005-odontogram-svg-architecture.md`)
- Animation library selection and configuration
- Icon design and custom icon creation
- Print stylesheets (for PDF generation, see individual PDF endpoint specs)
- Email template design system
- Native mobile app design system (DentalOS is web/PWA only)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
