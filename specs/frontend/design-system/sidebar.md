# Navigation Sidebar — Design System Component Spec

## Overview

**Spec ID:** FE-DS-08

**Component:** `AppSidebar`

**File:** `src/components/layout/app-sidebar.tsx`

**Description:** Primary application navigation sidebar containing all route links organized by domain, role-based visibility, notification badges, user profile section, and clinic context. Supports expanded (w-64) and collapsed (w-16, icons only) modes on desktop/tablet, and a full-screen overlay drawer on mobile.

**Design System Ref:** `FE-DS-01` (§4.11)

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `isOpen` | `boolean` | — | Yes | Drawer open state (mobile) |
| `onClose` | `() => void` | — | Yes | Called to close mobile drawer |
| `collapsed` | `boolean` | `false` | No | Desktop collapsed state (icon-only mode) |
| `onToggleCollapse` | `() => void` | — | No | Called when collapse toggle clicked |
| `currentPath` | `string` | — | Yes | Current route for active state detection |
| `user` | `User` | — | Yes | Current user data for bottom profile section |
| `tenant` | `Tenant` | — | Yes | Current clinic data |

---

## Layout Modes

### Desktop Expanded (default)

**Width:** `w-64` (256px)

**Structure:**
```
+------------------------+
| [Logo + Clinic name]   |  h-16, border-b
+------------------------+
| [Toggle ← button]      |
+------------------------+
| PRINCIPAL              |  group label
|   ⬜ Dashboard          |  nav item
|   👥 Pacientes          |
|   🦷 Odontograma        |
|   📋 Registros          |
+------------------------+
| AGENDA                 |
|   📅 Citas              |
+------------------------+
| CLÍNICA                |
|   💊 Tratamientos       |
|   📄 Consentimientos    |
+------------------------+
| OPERACIONES            |
|   💳 Facturación        |
|   📊 Reportes           |
|   💬 Mensajes     [3]  |  ← badge
+------------------------+
| CONFIGURACIÓN          |
|   ⚙️ Ajustes            |
+------------------------+
|                        |  mt-auto
| [Avatar] Nombre        |
| rol badge              |
| [Logout]               |
+------------------------+
```

### Desktop Collapsed (icon only)

**Width:** `w-16` (64px)

- Group labels hidden
- Nav items: icon only, centered, with tooltip on hover (right side, arrow pointing left)
- User section: avatar only, logout icon
- Clinic name hidden, only logo mark shown

**Collapse toggle:** A `<` chevron button at the top-right edge of the sidebar (overlapping content area). When collapsed, shows `>` chevron.

Toggle button classes:
```
absolute -right-3 top-20 w-6 h-6 rounded-full
bg-white border border-gray-200 shadow-sm
flex items-center justify-center
hover:bg-gray-50 z-10
```

### Mobile (< 640px) — Overlay Drawer

**Width:** 280px from left edge

**Behavior:**
- Triggered by hamburger menu in the header
- Slides in from left over content: `translate-x-[-100%] → translate-x-0`
- Backdrop overlay: `fixed inset-0 bg-black/40 z-40`
- Sidebar panel: `fixed left-0 top-0 bottom-0 w-70 bg-white z-50 shadow-xl`
- Close: tap backdrop, swipe left (optional), or X button in sidebar header

**Animation:** `transition-transform duration-300 ease-in-out`

---

## Logo Area

**Height:** `h-16`
**Classes:** `flex items-center px-4 border-b border-gray-200`

**Expanded:**
- Clinic logo (32x32px, `rounded-md object-cover`) + Clinic name (`text-sm font-semibold text-gray-900 truncate`)
- If no logo: colored initials avatar (same algorithm as user avatar but square)

**Collapsed:**
- Clinic logo only (32x32px), centered

**Clinic name tooltip:** On collapsed mode, hover shows full clinic name in tooltip.

---

## Navigation Items

### Nav Item Structure (expanded)

```
+--------------------------------------------+
| [Icon 20px]  [Label text]       [Badge?]   |
+--------------------------------------------+
```

**Classes:**
```
flex items-center gap-3 px-3 py-2.5 rounded-lg
text-sm font-medium text-gray-600
hover:bg-gray-50 hover:text-gray-900
transition-colors duration-100
cursor-pointer w-full
```

**Active state:**
```
bg-teal-50 text-teal-700 font-semibold
```

**Active indicator:** Left border: `border-l-2 border-teal-600` inside the item.

### Nav Item Structure (collapsed, icon-only)

- Width: `w-10 h-10`, centered in `w-16` sidebar
- Icon only, `text-gray-500`
- Active: `bg-teal-50 text-teal-700`
- Tooltip: shadcn/ui Tooltip with `side="right"`, shows nav item label + keyboard shortcut if applicable

### Nav Item Badge

Notification count badge on items like "Mensajes", "Citas pendientes":

- Position: right edge of item
- Style: `bg-red-500 text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] px-1`
- Shows count. If > 99: "99+"
- In collapsed mode: badge positions on top-right of icon

---

## Navigation Groups

Groups are labeled sections. Labels are NOT clickable.

**Label classes:**
```
text-xs font-medium text-gray-400 uppercase tracking-wider
px-3 mt-6 mb-1
```

In collapsed mode: labels are completely hidden.

### Full Navigation Structure by Role

**All roles see:**
- PRINCIPAL: Dashboard, Pacientes

**clinic_owner, doctor see:**
- CLÍNICA: Odontograma, Registros Clínicos, Tratamientos, Consentimientos
- AGENDA: Citas

**clinic_owner, doctor, assistant see:**
- OPERACIONES: Facturación, Mensajes

**clinic_owner, doctor see:**
- REPORTES: Analíticas

**clinic_owner sees:**
- CONFIGURACIÓN: Ajustes (links to /settings/clinic)

**role-specific items hidden via:** `hidden` class applied based on `user.role`.

---

## Bottom User Section

**Position:** `mt-auto border-t border-gray-200 p-3`

### Expanded Mode:

```
+--------------------------------------------+
| [Avatar md]  Nombre Apellido               |
|              [Role badge]                  |
|                                            |
| [Cerrar sesión]                            |
+--------------------------------------------+
```

- Avatar: 40x40px with initials fallback (FE-DS-12)
- Name: `text-sm font-medium text-gray-900 truncate`
- Role badge: small status pill (teal=doctor, purple=owner, etc.)
- Logout button: ghost variant with `LogOut` icon + "Cerrar sesión" text

**Clinic selector** (for multi-clinic doctors):
- Above logout, a "Cambiar clínica" button with `Building2` icon
- Click → opens clinic selector modal showing the doctor's other tenants

### Collapsed Mode:

```
+--------+
| Avatar |  → tooltip: "Nombre Rol"
|  [→]   |  → logout icon
+--------+
```

---

## Keyboard Shortcuts (optional enhancement)

| Shortcut | Action |
|----------|--------|
| `G then P` | Go to Pacientes |
| `G then D` | Go to Dashboard |
| `G then C` | Go to Citas |
| `G then F` | Go to Facturación |

Shortcuts shown in tooltips on collapsed mode. Implemented via `useHotkeys` hook.

---

## Collapsed State Persistence

Collapsed/expanded state persisted in `localStorage` key `sidebar-collapsed` (`"true" | "false"`).

Respects user's last preference on next visit. Default: expanded.

---

## Accessibility

- **Role:** `role="navigation"` with `aria-label="Navegación principal"` on the `<nav>` element
- **Active item:** `aria-current="page"` on the active nav link
- **Tooltips (collapsed mode):** `role="tooltip"`, associated via `aria-describedby`
- **Mobile drawer:** `role="dialog"`, `aria-label="Menú de navegación"`, `aria-modal="true"`. Backdrop has `aria-hidden="true"`.
- **Keyboard:** All nav items focusable via Tab. Active item is visually distinct. Drawer closed via Escape.
- **Screen reader:** Collapsed sidebar announces "Barra de navegación colapsada. Usa los íconos para navegar."
- **Focus management:** When drawer opens (mobile), focus moves to first nav item. When closed, focus returns to hamburger button.

---

## Responsive Behavior

| Breakpoint | Mode |
|------------|------|
| Mobile (< 640px) | Hidden by default. Overlay drawer via hamburger button. |
| Tablet (640-1023px) | Collapsed by default (w-16, icon-only). Can expand to w-64 by clicking toggle. |
| Desktop (> 1024px) | Expanded by default (w-64). Can collapse to w-16. |

---

## Dark Mode

Dark mode classes appended to all sidebar elements:

```
bg-gray-900 (sidebar background)
border-gray-700 (borders)
text-gray-300 (nav item text)
hover:bg-gray-800 (nav item hover)
bg-teal-900 text-teal-200 (active item)
```

---

## Implementation Notes

**File Location:**
- Component: `src/components/layout/app-sidebar.tsx`
- Mobile drawer: `src/components/layout/mobile-drawer.tsx`
- App shell: `src/components/layout/app-shell.tsx`

**Hooks Used:**
- `useAuth()` — user role and tenant context
- `usePathname()` — Next.js for current route
- `useLocalStorage('sidebar-collapsed', false)` — persist state

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
