# DentalOS Responsive Design -- Frontend Specification

## Overview

**Spec ID:** FE-DS-02

**Description:** Responsive design rules for DentalOS frontend, defining breakpoints, device profiles, layout behavior per viewport, touch target requirements, orientation handling, and testing strategy. DentalOS is tablet-first: dental clinics primarily use tablets (iPad, Samsung Tab) during patient consultations, desktop for administrative/billing work, and mobile for the patient portal and quick lookups.

**Priority:** Critical

**Dependencies:** FE-DS-01 (design-system.md), `infra/responsive-breakpoints.md` (infra-level rules)

**Stack:** TailwindCSS responsive utility classes (mobile-first `sm:`, `md:`, `lg:`, `xl:`, `2xl:` prefixes)

---

## 1. Breakpoints (TailwindCSS Defaults)

DentalOS uses the standard TailwindCSS breakpoint scale with a mobile-first approach. Styles without a prefix apply to the smallest viewport and are progressively overridden at larger breakpoints.

| Token | Min Width | Device Category | Clinical Priority |
|-------|-----------|-----------------|-------------------|
| *(base)* | 0px | Small phones, patient portal | Standard |
| `sm` | 640px | Large phones | Standard |
| `md` | 768px | Tablets portrait | **PRIMARY -- core clinical workflow** |
| `lg` | 1024px | Tablets landscape, small laptops | High |
| `xl` | 1280px | Desktop monitors | Standard -- admin/billing |
| `2xl` | 1536px | Large/wide desktop monitors | Low -- analytics dashboards |

**Key rule:** Every clinical screen (odontogram, patient record, treatment plan) must be fully functional and touch-optimized at the `md` (768px) breakpoint. Desktop is an enhancement, not a requirement for clinical work.

---

## 2. Primary Device Profiles

These are the specific devices found in LATAM dental clinics. Design and QA must verify against these exact resolutions.

### 2.1 Tablets (Primary Clinical Devices)

| Device | Viewport (Portrait) | Viewport (Landscape) | Pixel Ratio | OS |
|--------|---------------------|----------------------|-------------|-----|
| iPad 10th gen | 820 x 1180 | 1180 x 820 | 2x | iPadOS |
| iPad Pro 11" | 834 x 1194 | 1194 x 834 | 2x | iPadOS |
| iPad Air (M2) | 820 x 1180 | 1180 x 820 | 2x | iPadOS |
| Samsung Galaxy Tab S9 | 800 x 1280 | 1280 x 800 | 2.25x | Android |
| Samsung Galaxy Tab A9 | 800 x 1340 | 1340 x 800 | 1.5x | Android |
| Lenovo Tab M10 Plus | 800 x 1200 | 1200 x 800 | 1.5x | Android |

### 2.2 Desktop (Reception/Admin)

| Device | Viewport | Pixel Ratio | Usage |
|--------|----------|-------------|-------|
| Typical desktop | 1920 x 1080 | 1x | Reception desk, billing, reports |
| Laptop 14" | 1366 x 768 | 1x | Doctor office workstation |
| MacBook Pro 14" | 1512 x 982 | 2x | Clinic owner admin |
| Wide monitor | 2560 x 1440 | 1x-2x | Analytics dashboards |

### 2.3 Mobile (Patient Portal / Quick Lookups)

| Device | Viewport | Pixel Ratio | OS |
|--------|----------|-------------|-----|
| iPhone 14 / 15 | 390 x 844 | 3x | iOS |
| iPhone SE (3rd gen) | 375 x 667 | 2x | iOS (smallest supported) |
| Samsung Galaxy A54 | 393 x 851 | 2.625x | Android |
| Pixel 7 | 412 x 915 | 2.625x | Android |

---

## 3. Layout Behavior per Breakpoint

### 3.1 Sidebar Navigation

| Breakpoint | State | Width | Trigger |
|------------|-------|-------|---------|
| Mobile (< 768px) | Hidden, off-canvas drawer | 280px overlay | Hamburger button in header |
| Tablet (768-1023px) | Collapsed, icon-only | 64px | Expand on click/hover, collapse on outside click |
| Tablet landscape (1024-1279px) | Collapsed by default, expandable | 64px / 256px | Toggle button, state persisted |
| Desktop (1280px+) | Expanded, icon + label | 256px | Collapse button available |

### 3.2 Patient Detail View

| Breakpoint | Layout | Description |
|------------|--------|-------------|
| Mobile (< 768px) | Single column | Patient header card stacked above tab selector (scrollable row), tab content fills remaining viewport |
| Tablet (768-1023px) | 2-column | Patient info card (left, 280px fixed) + tabs content (right, flex-1) |
| Desktop (1280px+) | Full layout | Patient sidebar (left, 320px) + main tabs (center, flex-1) + contextual panel (right, 280px, optional) |

### 3.3 Odontogram

| Breakpoint | Behavior |
|------------|----------|
| Mobile (< 640px) | Single-tooth detail view with horizontal tooth number scroller; no full arch render |
| Tablet portrait (768px+) | Full arch grid (8x4), interactive tooth selection, condition palette as 3x4 grid below |
| Tablet landscape (1024px+) | Full arch + side panel (320px) for selected tooth detail, condition palette as single row |
| Desktop (1280px+) | Largest tooth rendering, hover tooltips, keyboard shortcuts, full history in side panel |

**All breakpoints:** Full-width container, no max-width constraint. Pinch-to-zoom on touch devices.

### 3.4 Appointment Calendar

| Breakpoint | Default View | Behavior |
|------------|-------------|----------|
| Mobile (< 640px) | Day (list) | Time slots as stacked cards, swipe left/right for prev/next day |
| Tablet (768-1023px) | Day (grid) | Time grid with 30-min slots, appointments as colored blocks, tap to create |
| Desktop (1024px+) | Week | 7-day time grid, drag-and-drop rescheduling, hover for appointment preview |

All views include a view switcher (dia/semana/mes) so users can override the default.

### 3.5 Data Tables

| Breakpoint | Rendering | Description |
|------------|-----------|-------------|
| Mobile (< 640px) | Card list | Each row rendered as a card with priority fields visible, secondary fields in expandable section |
| Tablet (768-1023px) | Horizontal scroll table | Sticky first column (name/ID), 4-6 priority columns visible, remaining scroll |
| Desktop (1024px+) | Full table | All columns visible, sortable headers, inline row actions, bulk selection |

### 3.6 Forms

| Breakpoint | Layout | Column Behavior |
|------------|--------|-----------------|
| Mobile (< 640px) | Single column | All fields full-width, stacked vertically |
| Tablet (768px+) | 2-column grid | Short fields paired (nombre + apellido, telefono + email), long fields span full width |
| Desktop (1024px+) | 2-column grid | Same as tablet with wider fields, max-width constraint (`max-w-2xl` for form container) |

**Full-width fields (always span both columns):** Address, notes/observations, file upload, medical history textarea, signature pad.

---

## 4. Touch Targets

### 4.1 Minimum Sizes

| Element | Minimum Touch Target | Rationale |
|---------|---------------------|-----------|
| All interactive elements | 44 x 44px | Apple HIG / WCAG 2.1 AAA target size |
| Primary action buttons | 48 x 48px | Larger for gloved-hand accuracy in clinical use |
| Odontogram tooth zones | 48 x 48px on tablet | Critical clinical interaction |
| Table rows (tappable) | 52px height | Prevent mis-taps on adjacent rows |
| Close / dismiss buttons | 32px visual, 44px hit area | Small visual with padding for adequate touch area |

### 4.2 Spacing Between Targets

Minimum **8px gap** between adjacent interactive elements to prevent accidental activation. This is especially critical for:

- Adjacent teeth in odontogram grid
- Condition selector palette buttons
- Calendar time slot blocks
- Action button groups (Cancelar / Guardar)
- Table row action icons

### 4.3 Gloved Hand Considerations

Dental professionals frequently interact with the tablet while wearing nitrile gloves. Design rules for clinical screens:

- Prefer tap over swipe for primary actions
- Provide `active:scale-95` visual feedback on touch
- Avoid fine-grained drag interactions on clinical views; offer tap alternatives
- Use generous padding on form fields during clinical data entry

---

## 5. Orientation Handling

### 5.1 Tablet Orientation Support

| View | Preferred Orientation | Behavior on Other Orientation |
|------|----------------------|-------------------------------|
| Odontogram | Landscape | Works in portrait but shows prompt suggesting landscape for best experience |
| Patient detail | Portrait | Fully functional in landscape (side panel auto-shows) |
| Calendar | Landscape | Portrait shows day view instead of week view |
| Forms | Portrait | Landscape adds extra whitespace but remains functional |
| Dashboard | Either | Grid reflows naturally |

### 5.2 Orientation Prompt

When a user opens the odontogram on a tablet in portrait mode, display a subtle non-blocking banner:

```
[RotateIcon] Para mejor experiencia, gire el dispositivo a modo horizontal.  [Cerrar]
```

Banner appears once per session, dismissible, stored in sessionStorage.

---

## 6. Typography Scaling

DentalOS does **not** use fluid/responsive font scaling (`clamp()` or viewport-relative units). Instead, typography adapts via TailwindCSS responsive prefixes applied at the component level.

| Context | Mobile | Tablet+ | Desktop |
|---------|--------|---------|---------|
| Page title | `text-xl` | `md:text-2xl` | same |
| Section heading | `text-lg` | `md:text-xl` | same |
| Body text | `text-sm` | `md:text-base` | same |
| Table cell | `text-xs` | `md:text-sm` | same |
| Dashboard KPI number | `text-2xl` | `md:text-3xl` | `lg:text-4xl` |

This approach keeps text predictable and avoids accessibility issues with fluid scaling.

---

## 7. Testing

### 7.1 Device Lab Checklist

Every PR that affects layout must be verified on these viewports (via browser DevTools or Playwright):

| Device | Width x Height | Category | Must Pass |
|--------|---------------|----------|-----------|
| iPhone SE | 375 x 667 | Mobile (smallest) | Patient portal, login, search |
| iPhone 14 | 390 x 844 | Mobile (common) | All mobile views |
| iPad Mini (portrait) | 768 x 1024 | Tablet portrait | Full clinical workflow |
| iPad 10th gen (portrait) | 820 x 1180 | Tablet portrait | Full clinical workflow |
| iPad Pro 11" (landscape) | 1194 x 834 | Tablet landscape | Odontogram, calendar week |
| Samsung Tab S9 (portrait) | 800 x 1280 | Tablet portrait (Android) | Full clinical workflow |
| Desktop 1080p | 1920 x 1080 | Desktop | All admin/billing screens |
| Laptop 768p | 1366 x 768 | Desktop (small) | No overflow, no cutoff |

### 7.2 Critical Test Scenarios

| Scenario | Breakpoints | Pass Criteria |
|----------|-------------|---------------|
| Odontogram renders all teeth, tappable | md, lg, xl | All 32 teeth visible, touch targets >= 48px, conditions display |
| Sidebar transitions correctly | base, md, lg, xl | Hidden/drawer on mobile, collapsed on tablet, expanded on desktop |
| Patient form column layout | base, md | Single column mobile, 2-column tablet |
| Calendar default view | base, md, lg | Day mobile, day tablet, week desktop |
| Table-to-card conversion | base, md | Cards on mobile, table on tablet+ |
| No horizontal overflow | all | No unexpected horizontal scrollbar on any breakpoint |
| Touch targets >= 44px | md | All clinical interactive elements meet minimum size |
| Orientation prompt on odontogram | md (portrait) | Banner appears in portrait, dismissed on landscape |

### 7.3 Playwright Config Snippet

```typescript
// playwright.config.ts — responsive device targets
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  projects: [
    { name: 'mobile', use: { ...devices['iPhone 14'] } },
    { name: 'tablet-portrait', use: { viewport: { width: 820, height: 1180 }, isMobile: true, hasTouch: true } },
    { name: 'tablet-landscape', use: { viewport: { width: 1194, height: 834 }, isMobile: true, hasTouch: true } },
    { name: 'desktop', use: { viewport: { width: 1920, height: 1080 } } },
  ],
});
```

---

## 8. Implementation Patterns

### 8.1 Responsive Grid (Common Layout)

```tsx
{/* 1-col mobile, 2-col tablet, 3-col desktop */}
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
  <PatientCard />
  <PatientCard />
  <PatientCard />
</div>
```

### 8.2 Sidebar-Aware Main Content

```tsx
<div className="flex h-screen">
  <aside className="hidden md:flex md:w-16 xl:w-64 flex-shrink-0 transition-all duration-200">
    <AppSidebar />
  </aside>
  <div className="flex-1 flex flex-col min-w-0">
    <header className="h-16 flex-shrink-0 sticky top-0 z-50 bg-white dark:bg-gray-900 border-b">
      <AppHeader />
    </header>
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-6 lg:px-8">
      {children}
    </main>
  </div>
</div>
```

### 8.3 Mobile-Only / Desktop-Only Visibility

```tsx
{/* Hamburger menu: visible only on mobile */}
<button className="md:hidden p-2" aria-label="Abrir menu">
  <Menu className="w-6 h-6" />
</button>

{/* Desktop search bar: hidden on mobile */}
<div className="hidden md:flex items-center">
  <SearchInput placeholder="Buscar paciente..." />
</div>
```

### 8.4 Conditional Component Rendering

```tsx
import dynamic from 'next/dynamic';
import { useMediaQuery } from '@/hooks/use-media-query';

const DataTable = dynamic(() => import('@/components/shared/data-table'));
const CardList = dynamic(() => import('@/components/shared/card-list'));

function PatientList() {
  const isTabletOrAbove = useMediaQuery('(min-width: 768px)');

  return isTabletOrAbove
    ? <DataTable columns={patientColumns} data={patients} />
    : <CardList items={patients} renderCard={(p) => <PatientCard patient={p} />} />;
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial responsive design specification |
