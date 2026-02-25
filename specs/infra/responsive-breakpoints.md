# Responsive Design & Breakpoints Spec

## Overview

**Feature:** Responsive design rules for DentalOS, defining breakpoints, layout patterns, touch target requirements, and device-specific behavior. Tablet is the primary clinical device -- the odontogram and clinical tools are optimized for touch interaction on screens between 768-1024px.

**Domain:** infra

**Priority:** Critical

**Dependencies:** I-28 (design-system.md)

**Spec ID:** I-29

---

## 1. Breakpoints

DentalOS follows a mobile-first approach using TailwindCSS default breakpoints. Styles are written for the smallest screen first, then progressively enhanced for larger screens.

### 1.1 Breakpoint Scale

| Token | Min Width | Typical Devices | Priority |
|-------|-----------|-----------------|----------|
| *(base)* | 0px | Small phones (iPhone SE, Galaxy A series) | Standard |
| `sm` | 640px | Large phones (iPhone 14/15, Pixel 7) | Standard |
| `md` | 768px | Tablets portrait (iPad, Galaxy Tab) | **HIGH -- Primary clinical device** |
| `lg` | 1024px | Tablets landscape, small laptops | High |
| `xl` | 1280px | Laptops, desktop monitors | Standard |
| `2xl` | 1536px | Large desktop monitors, wide screens | Standard |

### 1.2 Device Context

| Device Category | Width Range | Use Case in Clinics |
|-----------------|-------------|---------------------|
| Mobile (phone) | < 640px | Quick patient lookup, appointment confirmation, notifications |
| Tablet portrait | 768 - 1023px | **Primary clinical workflow.** Odontogram, patient examination, treatment recording |
| Tablet landscape | 1024 - 1279px | Extended clinical view with side panels, split odontogram + notes |
| Desktop | >= 1280px | Reception desk, administrative tasks, billing, analytics |

### 1.3 TailwindCSS Usage Pattern

```tsx
{/* Mobile-first: start with mobile, add responsive modifiers */}
<div className="
  px-4            {/* Mobile: 16px padding */}
  md:px-6         {/* Tablet: 24px padding */}
  lg:px-8         {/* Desktop: 32px padding */}
">
  <div className="
    grid
    grid-cols-1   {/* Mobile: single column */}
    md:grid-cols-2 {/* Tablet: two columns */}
    lg:grid-cols-3 {/* Desktop: three columns */}
    gap-4
    md:gap-6
  ">
    {/* Content */}
  </div>
</div>
```

---

## 2. Touch Target Requirements

### 2.1 Minimum Sizes

All interactive elements must meet minimum touch target sizes per context:

| Context | Minimum Size | Rationale |
|---------|-------------|-----------|
| Clinical tools (odontogram zones, condition selectors) | **44 x 44px** | Apple HIG and WCAG 2.1 target size requirement |
| Navigation items (sidebar, tabs) | **44 x 44px** | Consistent with clinical tools |
| Form inputs | **40px height** | Standard form interaction |
| Buttons | **40px height** (md), **48px height** (lg) | Adequate for gloved hands |
| Table rows (clickable) | **52px height** | Prevent mis-taps on adjacent rows |
| Close buttons, small actions | **32 x 32px** minimum, **44px** touch area with padding | Small visual, large hit area |

### 2.2 Touch Target Spacing

Adjacent interactive elements must have a minimum gap of **8px** between their touch targets to prevent accidental activation. This is especially critical in:

- Odontogram tooth zones (adjacent teeth)
- Condition selector palette (12 condition buttons)
- Calendar time slots (30-minute blocks)
- Action button groups (Save / Cancel)

### 2.3 Gloved Hand Considerations

Dental professionals often wear nitrile gloves during examination. Gloved fingers have:

- Reduced touch precision (target should be 10-15% larger than bare-finger minimum)
- Reduced friction (avoid swipe-only interactions without a tap alternative)
- Reduced sensitivity (provide visual + haptic feedback on tap)

**Design rules for clinical screens:**

- Prefer tap over swipe for primary actions
- Use `active:scale-95` visual feedback on touch
- Odontogram zones must be at least **48 x 48px** on tablet
- Condition selector buttons must be at least **44 x 44px** with clear visual separation

---

## 3. Dental Chart (Odontogram) Responsive Behavior

The odontogram is the core clinical component of DentalOS. Its responsive behavior is critical.

### 3.1 Mobile (< 640px)

```
+----------------------------------+
|  [Tooth Selector Bar: scrollable |
|   horizontal row of tooth nums]  |
+----------------------------------+
|                                  |
|   Single Tooth Detail View       |
|   (enlarged tooth with 6 zones)  |
|                                  |
|   Current Conditions List        |
|   Condition 1: Caries - Mesial   |
|   Condition 2: Resina - Oclusal  |
|                                  |
+----------------------------------+
|  [Condition Palette: horizontal  |
|   scrollable 2-row grid]         |
+----------------------------------+
```

**Mobile rules:**

- Full odontogram arch is NOT rendered (too small for interaction)
- Show horizontal scrollable tooth number bar (FDI notation) for tooth selection
- Selected tooth renders enlarged (filling available width)
- Each tooth zone is a tap target (minimum 48x48px)
- Conditions list below tooth shows current state
- Condition palette at bottom, scrollable horizontal grid (2 rows x 6 columns)
- Swipe left/right on the tooth to navigate to adjacent teeth

### 3.2 Tablet Portrait (768 - 1023px) -- PRIMARY

```
+------------------------------------------+
|     Upper Jaw (teeth 11-18, 21-28)       |
|  [18][17][16][15][14][13][12][11]        |
|  [21][22][23][24][25][26][27][28]        |
+------------------------------------------+
|     Lower Jaw (teeth 31-38, 41-48)       |
|  [48][47][46][45][44][43][42][41]        |
|  [31][32][33][34][35][36][37][38]        |
+------------------------------------------+
|  Selected Tooth Detail     | Condition   |
|  [Enlarged tooth w/ zones] | Palette     |
|  Zone: Mesial              | [12 buttons |
|  Condition: Caries         |  in 3x4     |
|  Notes: ...                |  grid]      |
+------------------------------------------+
```

**Tablet portrait rules:**

- Full dental arch rendered with all 32 teeth (adult) or 20 teeth (pediatric)
- Each tooth is an interactive SVG with minimum **48x48px** touch target
- 6 zones per tooth are tappable (mesial, distal, vestibular, lingual/palatino, oclusal, root)
- Tapping a tooth opens inline detail below the chart
- Condition palette is a 3x4 grid (3 columns, 4 rows) -- all 12 conditions visible at once
- No hover effects (touch device)
- Pinch-to-zoom supported for detailed tooth inspection
- Current conditions shown as colored overlays on the SVG tooth zones

### 3.3 Tablet Landscape (1024 - 1279px)

```
+----------------------------------------------+
|     Upper Jaw (teeth 11-18, 21-28)    | Tooth|
|  [18][17][16][15][14][13][12][11]     | Dtl  |
|  [21][22][23][24][25][26][27][28]     |------|
+---------------------------------------| Cond |
|     Lower Jaw (teeth 31-38, 41-48)    | List |
|  [48][47][46][45][44][43][42][41]     |      |
|  [31][32][33][34][35][36][37][38]     | Notes|
+----------------------------------------------+
| Condition Palette (12 buttons, single row)   |
+----------------------------------------------+
```

**Tablet landscape rules:**

- Full dental arch with larger tooth rendering
- Side panel (right, 280-320px wide) shows selected tooth detail
- Condition history for selected tooth in the side panel
- Condition palette as a single horizontal row below the chart
- Quick notes input for the selected condition

### 3.4 Desktop (>= 1280px)

```
+--------------------------------------------------------+
|     Upper Jaw                          | Tooth Detail  |
|  [18][17][16][15][14][13][12][11]      |               |
|  [21][22][23][24][25][26][27][28]      | Conditions    |
+----------------------------------------| History       |
|     Lower Jaw                          |               |
|  [48][47][46][45][44][43][42][41]      | Notes         |
|  [31][32][33][34][35][36][37][38]      |               |
+----------------------------------------| Quick Actions |
| Condition Palette (single row)         |               |
+--------------------------------------------------------+
```

**Desktop rules:**

- Largest tooth rendering with hover effects on zones
- Hover shows tooltip with zone name and current condition
- Side panel always visible (320-400px wide)
- Full condition history timeline in side panel
- Quick action buttons: Add Note, Take Snapshot, Link to Treatment
- Keyboard shortcuts: number keys (1-12) to select conditions, arrow keys to navigate teeth

---

## 4. Layout Patterns

### 4.1 Dashboard

| Breakpoint | Layout | Details |
|------------|--------|---------|
| Mobile (< 640px) | 1 column | Stats cards stacked, chart below, recent activity list |
| Tablet (md) | 2 columns | Stats cards in 2x2 grid, chart spans full width below |
| Desktop (lg+) | 3 columns | Stats in top row (3-4 cards), chart + activity side-by-side |

```
Mobile:           Tablet:              Desktop:
[Card 1]          [Card 1][Card 2]     [Card 1][Card 2][Card 3][Card 4]
[Card 2]          [Card 3][Card 4]     [Chart          ][Activity     ]
[Card 3]          [Chart full width]   [                ][             ]
[Card 4]          [Activity          ]
[Chart  ]
[Activity]
```

### 4.2 Patient Detail

| Breakpoint | Layout | Details |
|------------|--------|---------|
| Mobile (< 640px) | Stacked tabs | Tab selector at top (scrollable), content below |
| Tablet (md) | Horizontal tabs | Tab row, content area fills remaining height |
| Desktop (lg+) | Horizontal tabs with sidebar | Tabs for main content, patient summary sidebar (right, 280px) |

**Tab structure (all breakpoints):**

1. Resumen (Summary)
2. Odontograma
3. Historia Clinica (Clinical Records)
4. Tratamientos (Treatment Plans)
5. Citas (Appointments)
6. Facturacion (Billing)
7. Documentos (Documents)

```
Mobile:               Tablet:                  Desktop:
[Tab Scroll Row  ]    [Tab 1|Tab 2|Tab 3|...]  [Tab 1|Tab 2|...] [Summary]
[                ]    [                      ]  [                ] [Card   ]
[ Tab Content    ]    [ Tab Content           ]  [ Tab Content    ] [Patient]
[                ]    [                      ]  [                ] [Info   ]
[                ]    [                      ]  [                ] [       ]
```

### 4.3 Calendar / Agenda

| Breakpoint | Default View | Details |
|------------|-------------|---------|
| Mobile (< 640px) | Day view | Single day, time slots stacked, swipe for next/prev day |
| Tablet (md) | Week view | 7-day grid with time axis, tap to create appointment |
| Desktop (lg+) | Month view | Traditional month grid, click for day detail |

**All views support:**

- View switcher (day/week/month) available on all breakpoints
- Doctor filter dropdown
- Today button for quick navigation
- Appointment type color coding

### 4.4 Forms

| Breakpoint | Layout | Details |
|------------|--------|---------|
| Mobile (< 640px) | Single column | All fields stacked vertically, full width |
| Tablet (md+) | Two columns | Related fields side-by-side (first name + last name, city + state) |
| Desktop (lg+) | Two columns | Same as tablet, wider field widths |

**Column assignment rules:**

- Short fields (name, phone, email) can be paired in 2 columns
- Long fields (address, notes, description) always span full width
- Date + time fields are paired
- File upload always spans full width
- Submit/Cancel buttons always span full width, right-aligned

```
Mobile:                  Tablet / Desktop:
[First Name         ]    [First Name    ][Last Name     ]
[Last Name          ]    [Document Type ][Document #    ]
[Document Type      ]    [Birthdate     ][Gender        ]
[Document Number    ]    [Phone         ][Email         ]
[Birthdate          ]    [Address                       ]
[Gender             ]    [Emergency Contact              ]
[Phone              ]    [Allergies (multi-select)       ]
[Email              ]               [Cancel] [Save]
[Address            ]
[Emergency Contact  ]
[Allergies          ]
       [Cancel] [Save]
```

### 4.5 Data Tables

| Breakpoint | Behavior | Details |
|------------|----------|---------|
| Mobile (< 640px) | Card list | Each row becomes a card. Priority fields visible, secondary in expandable section |
| Tablet (md) | Responsive table | Horizontal scroll with sticky first column (name/ID). 4-6 visible columns |
| Desktop (lg+) | Full table | All columns visible, sortable, with inline actions |

**Mobile card conversion:**

For tables with more than 4 columns, mobile view converts rows to cards:

```
Desktop table row:
| Name | Document | Phone | Email | Last Visit | Status | Actions |

Mobile card:
+----------------------------------+
| Maria Garcia Lopez         [...]  |
| CC 1234567890                     |
| +57 300 123 4567                  |
| Ultima visita: 15 Feb 2026       |
| [Activo]                          |
+----------------------------------+
```

**Priority columns** (always visible, even on tablet scroll):

| Table Context | Priority Columns |
|---------------|-----------------|
| Patient list | Name, Document, Phone |
| Appointment list | Time, Patient, Doctor, Status |
| Invoice list | Number, Patient, Total, Status |
| Clinical records | Date, Type, Doctor |

---

## 5. Sidebar Behavior

| Breakpoint | State | Width | Trigger |
|------------|-------|-------|---------|
| Mobile (< 768px) | Hidden (off-canvas drawer) | 280px (overlay) | Hamburger menu button in header |
| Tablet (md - lg) | Collapsed (icon-only) | 64px | Expand button or hover |
| Desktop (xl+) | Expanded (icon + label) | 256px | Collapse button (pin/unpin) |

### 5.1 Mobile Sidebar (Drawer)

```
+----------+-----------------------------+
|          |                             |
| Sidebar  |    Main Content             |
| Drawer   |    (dimmed overlay)         |
| (280px)  |                             |
|          |                             |
| [Logo]   |                             |
| [Nav]    |                             |
| [User]   |                             |
+----------+-----------------------------+
```

- Slides in from the left
- Semi-transparent overlay covers main content (`bg-black/50`)
- Tap overlay or swipe left to close
- Includes full navigation with labels

### 5.2 Tablet Sidebar (Collapsed)

```
+------+---------------------------------+
| Icon |                                 |
| Only |        Main Content             |
| 64px |                                 |
|      |                                 |
| [ic] |                                 |
| [ic] |                                 |
| [ic] |                                 |
| [ic] |                                 |
+------+---------------------------------+
```

- Icons only, no labels
- Tooltip on hover/long-press shows label
- Click icon to navigate
- Expand button at bottom to switch to full sidebar (persists via local storage)

### 5.3 Desktop Sidebar (Expanded)

```
+------------------+-------------------------+
|  DentalOS Logo   |                         |
|------------------|    Main Content          |
|  [ic] Dashboard  |                         |
|  [ic] Pacientes  |                         |
|  [ic] Odontograma|                         |
|  [ic] Citas      |                         |
|  [ic] Facturacion|                         |
|  [ic] Reportes   |                         |
|------------------|                         |
|  [av] Dr. Ana R. |                         |
|  [  ] Ajustes    |                         |
+------------------+-------------------------+
```

- Full icons + labels
- Nested groups (e.g., "Clinica" group containing Pacientes, Odontograma, Historia Clinica)
- Collapse button (pin icon) to switch to icon-only mode
- Active item: `bg-primary-50 text-primary-700 border-l-2 border-primary-600`

---

## 6. Header Behavior

| Breakpoint | Content |
|------------|---------|
| Mobile | Hamburger menu + Logo (center) + Notifications bell |
| Tablet | Logo (left) + Search bar (center, 300px) + Notifications + Avatar |
| Desktop | Logo (left, if sidebar collapsed) + Search bar (400px) + Notifications + Tenant name + Avatar dropdown |

**Header height:** 64px (all breakpoints).

**Sticky behavior:** Header is `position: sticky; top: 0` with `z-50`. Scrolls with content on mobile to maximize viewport, sticky on tablet and desktop.

---

## 7. Page Layout Templates

### 7.1 Standard Page

```tsx
<div className="flex h-screen">
  {/* Sidebar */}
  <aside className="hidden md:flex md:w-16 xl:w-64 flex-shrink-0">
    <Sidebar />
  </aside>

  {/* Main area */}
  <div className="flex-1 flex flex-col min-w-0">
    {/* Header */}
    <header className="h-16 flex-shrink-0 sticky top-0 z-50 bg-white border-b">
      <Header />
    </header>

    {/* Content */}
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-6 lg:px-8">
      {children}
    </main>
  </div>
</div>
```

### 7.2 Content Width Constraints

| Content Type | Max Width | TailwindCSS |
|-------------|-----------|-------------|
| Form content | 672px (2 columns) | `max-w-2xl` |
| Standard page content | 1152px | `max-w-6xl` |
| Full-width (tables, calendar) | No max | `w-full` |
| Dashboard cards | 1280px | `max-w-7xl` |

---

## 8. Responsive Utilities

### 8.1 Visibility Helpers

| Class Pattern | Description |
|---------------|-------------|
| `hidden md:block` | Hidden on mobile, visible on tablet+ |
| `block md:hidden` | Visible on mobile only |
| `hidden lg:block` | Hidden until desktop |
| `md:hidden lg:block` | Hidden on tablet, visible on desktop |

### 8.2 Responsive Text

| Context | Mobile | Tablet | Desktop |
|---------|--------|--------|---------|
| Page title | `text-xl` | `text-2xl` | `text-2xl` |
| Section heading | `text-lg` | `text-xl` | `text-xl` |
| Body text | `text-sm` | `text-base` | `text-base` |
| Table cell | `text-xs` | `text-sm` | `text-sm` |
| Dashboard KPI | `text-2xl` | `text-3xl` | `text-4xl` |

### 8.3 Container Pattern

```tsx
<div className="mx-auto w-full px-4 sm:px-6 lg:px-8 max-w-7xl">
  {/* Page content */}
</div>
```

---

## 9. Performance Considerations

### 9.1 Image Responsive Loading

```tsx
<Image
  src="/patient-avatar.jpg"
  alt="Maria Garcia"
  sizes="(max-width: 640px) 40px, (max-width: 1024px) 56px, 80px"
  width={80}
  height={80}
  className="w-10 sm:w-14 lg:w-20 rounded-full"
/>
```

### 9.2 Odontogram SVG Optimization

- Mobile: Load simplified SVG (outline only, no zone subdivision) -- 15KB
- Tablet: Load full interactive SVG with all 6 zones per tooth -- 45KB
- Desktop: Load full SVG + hover state assets -- 50KB

Use `next/dynamic` with `ssr: false` for the odontogram component to avoid server-rendering the SVG.

### 9.3 Conditional Component Loading

```tsx
// Load the full data table only on tablet+
const DataTable = dynamic(() => import("@/components/DataTable"), {
  ssr: false,
  loading: () => <TableSkeleton />,
});

// On mobile, render the card list variant instead
function PatientList() {
  const isMobile = useMediaQuery("(max-width: 767px)");

  if (isMobile) {
    return <PatientCardList />;
  }
  return <DataTable columns={patientColumns} />;
}
```

---

## 10. Testing Responsive Layouts

### 10.1 Playwright Device Targets

| Device | Width x Height | Use Case |
|--------|---------------|----------|
| iPhone SE | 375 x 667 | Smallest supported phone |
| iPhone 14 | 390 x 844 | Common phone |
| iPad Mini | 768 x 1024 | Tablet portrait (primary clinical) |
| iPad Pro 11 | 834 x 1194 | Tablet portrait (larger) |
| iPad Pro 11 Landscape | 1194 x 834 | Tablet landscape |
| Desktop 1080p | 1920 x 1080 | Standard desktop |
| Desktop 1440p | 2560 x 1440 | Large desktop |

### 10.2 Critical Responsive Test Scenarios

| Scenario | Breakpoints to Test | Pass Criteria |
|----------|-------------------|---------------|
| Odontogram renders correctly | All | Teeth tappable, conditions visible, no overflow |
| Sidebar state transitions | Mobile, Tablet, Desktop | Correct open/collapsed/hidden state per breakpoint |
| Patient form layout | Mobile, Tablet | Single column (mobile), two column (tablet) |
| Calendar view default | Mobile, Tablet, Desktop | Day (mobile), Week (tablet), Month (desktop) |
| Data table to card conversion | Mobile, Tablet | Cards on mobile, table on tablet+ |
| Touch targets >= 44px | Tablet | All clinical interactive elements |
| No horizontal overflow | All | No unintended horizontal scrollbar |

---

## Out of Scope

This spec explicitly does NOT cover:

- Specific page/screen responsive layouts (each frontend screen spec defines its own responsive rules referencing these breakpoints)
- Print media queries (handled per-feature in PDF generation specs)
- Orientation lock or forced orientation
- Foldable device support (Samsung Galaxy Fold, etc.)
- TV or large display layouts
- Offline mode layout adjustments (see `infra/offline-sync-strategy.md`)
- Responsive email templates (see `integrations/email-engine.md`)
- Responsive behavior for the patient portal (follows the same rules but with reduced navigation complexity)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
