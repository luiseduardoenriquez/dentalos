# App Header — Design System Component Spec

## Overview

**Spec ID:** FE-DS-09

**Component:** `AppHeader`

**File:** `src/components/layout/app-header.tsx`

**Description:** Fixed top navigation bar containing the hamburger menu (mobile), clinic branding, global patient search, notification bell, and user profile dropdown. Visible on every authenticated page. Height: h-16 (64px). Adds drop shadow when user has scrolled.

**Design System Ref:** `FE-DS-01` (§4.11 sidebar complement)

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `onMenuClick` | `() => void` | — | Yes | Called when hamburger icon clicked (mobile) |
| `user` | `User` | — | Yes | Current user for avatar and dropdown |
| `tenant` | `Tenant` | — | Yes | Current clinic for context indicator |
| `notificationCount` | `number` | `0` | No | Unread notification badge count |
| `className` | `string` | — | No | Additional classes |

---

## Visual Structure

```
+--------------------------------------------------------------------+
| [≡]  [Clinic Name/Logo]  |  [🔍 Buscar paciente...]  |  [🔔] [👤] |
+--------------------------------------------------------------------+
       ← Left section →         ← Center section →      ← Right →
```

**Height:** `h-16` (64px)

**Background:** `bg-white`

**Border:** `border-b border-gray-200`

**Shadow on scroll:** `shadow-sm` (added via scroll event listener when `scrollY > 0`)

**Position:** `fixed top-0 left-0 right-0 z-30`

**Left offset:** `md:pl-16 lg:pl-64` to account for sidebar width (collapsed/expanded). Updated reactively via `useSidebarStore()`.

---

## Left Section

**Width:** Auto (shrinks on mobile)

**Contents:**

### Hamburger Button (mobile only, `< 640px`)

- `AlignLeft` icon (20px, `text-gray-600`)
- Button: `Button` ghost sm, `w-10 h-10 p-0`
- `aria-label="Abrir menú"`, `aria-expanded={drawerOpen}`, `aria-controls="mobile-sidebar"`
- Visible only on `md:hidden`

### Clinic Context Pill

**Desktop (≥ 1024px):**
- Hidden (clinic name visible in sidebar logo area)

**Tablet (640-1023px):**
- Clinic name as text: `text-sm font-semibold text-gray-900 truncate max-w-[140px]`

**Mobile (< 640px):**
- Pill badge: `bg-teal-50 text-teal-700 text-xs font-medium px-2 py-1 rounded-full`
- Shows abbreviated clinic name (first 2 words, max 20 chars)

---

## Center Section — Global Search

**Appearance:** Search bar, `max-w-md`, centered horizontally in available space.

**Structure:**
```
+----------------------------------------+
| [Search icon] Buscar paciente...       |
+----------------------------------------+
```

**Classes:**
```
flex items-center gap-2
bg-gray-100 hover:bg-gray-200
rounded-lg px-3 h-9
cursor-pointer transition-colors
text-sm text-gray-500
```

**Behavior:** Clicking the search bar opens the Command Palette (Cmdk) as a modal overlay — **not** a regular dropdown. This matches modern SaaS patterns (similar to Linear, Vercel).

### Command Palette (Search Modal)

**Trigger:** Click search bar OR keyboard shortcut `⌘K` (Mac) / `Ctrl+K` (Windows/Linux)

**Modal overlay:** Full-screen blurred overlay, command palette centered at top.

**Position:** `fixed top-16 left-1/2 -translate-x-1/2 w-full max-w-2xl z-50` — appears below the header.

**Contents:**
```
+------------------------------------------+
| [Search icon] Buscar paciente por nombre |
|               o documento...             |
+------------------------------------------+
| Resultados recientes                     |
|  [Avatar xs] María García — Cédula 1234  |
|  [Avatar xs] Carlos López — Cédula 5678  |
+------------------------------------------+
| [Typing: "mar"]  Buscando...             |
+------------------------------------------+
| PACIENTES ENCONTRADOS                    |
|  [Avatar xs] María García Torres         |
|              Cédula 12345678 | 34 años   |
|  [Avatar xs] Mariela Rodríguez           |
|              Cédula 87654321 | 28 años   |
+------------------------------------------+
| ACCIONES RÁPIDAS                         |
|  [UserPlus]  Crear nuevo paciente        |
|  [Calendar]  Nueva cita                  |
+------------------------------------------+
```

**Search behavior:**
- Min 2 characters to trigger API search
- Debounced 250ms
- Searches patient `nombre_completo` and `numero_documento`
- Results: up to 5 patients
- Recent items: last 5 viewed patients from `localStorage`

**Navigation:**
- Arrow keys up/down navigate results
- Enter navigates to patient detail
- Escape closes the palette

---

## Right Section

**Layout:** `flex items-center gap-2`

### Notification Bell

**Component:** Icon button with badge overlay.

**Icon:** `Bell` (Lucide), 20px, `text-gray-600`

**Button:** Ghost variant, `w-10 h-10 p-0`, `aria-label="Notificaciones"`

**Badge:** Shows `notificationCount` when > 0.
- Position: top-right corner of button area, `absolute top-1 right-1`
- Style: `bg-red-500 text-white text-xs font-bold rounded-full min-w-[16px] h-4 px-0.5 flex items-center justify-center`
- Shows count; if > 9: "9+"

**Click behavior:** Opens notification panel (slide-in from right, not a dropdown). This is the notification inbox.

**Notification Panel:**
```
+------------------------------------------+
| Notificaciones                    [X]    |
| [Mark all read]                          |
+------------------------------------------+
| [Avatar] Dr. García guardó registro     |
|          hace 5 minutos                  |
+------------------------------------------+
| [Bell] Cita confirmada con M. López     |
|        Hoy a las 14:30                   |
+------------------------------------------+
| [Ver todas las notificaciones]           |
+------------------------------------------+
```

**Panel style:** `fixed top-16 right-4 w-80 bg-white border border-gray-200 rounded-xl shadow-xl z-40`

---

### User Avatar Dropdown

**Component:** Avatar (md, 40x40px) as dropdown trigger.

**Shows:** User photo or initials fallback (FE-DS-12).

**Trigger classes:** `cursor-pointer rounded-full focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2`

**Dropdown Menu** (Radix DropdownMenu):

```
+------------------------------------------+
| [Avatar md] Nombre Apellido             |
|             doctor@clinica.com           |
|             [Role badge]                 |
+------------------------------------------+
| [User] Mi perfil                         |
| [Settings] Configuración                 |
+------------------------------------------+  ← separator
| [Building2] Cambiar clínica ▶            |  ← if multi-tenant doctor
+------------------------------------------+  ← separator
| [Moon] Modo oscuro         [Toggle]      |
+------------------------------------------+  ← separator
| [LogOut] Cerrar sesión                   |  ← text-red-600
+------------------------------------------+
```

**Dropdown classes:**
```
bg-white border border-gray-200 rounded-xl shadow-lg
p-1 min-w-[220px] z-50
```

**Menu item classes:**
```
flex items-center gap-2 px-3 py-2 text-sm
text-gray-700 rounded-lg cursor-pointer
hover:bg-gray-50 transition-colors
```

**Logout item:** `text-red-600 hover:bg-red-50`

---

## Clinic Switcher Sub-menu (Multi-tenant Doctors)

When user has multiple tenants, "Cambiar clínica" reveals a sub-menu:

```
+------------------------------------------+
| ● Clínica Dental Sonrisa (actual)        |
|   Clínica Norte                          |
|   Centro Médico Integral                 |
+------------------------------------------+
```

Clicking a clinic → POST `/api/v1/auth/switch-tenant`, refresh JWT, full page reload to dashboard of new tenant.

---

## Scroll Shadow

Scroll shadow added/removed dynamically:

```typescript
useEffect(() => {
  const handleScroll = () => {
    setScrolled(window.scrollY > 0)
  }
  window.addEventListener('scroll', handleScroll, { passive: true })
  return () => window.removeEventListener('scroll', handleScroll)
}, [])

// In component:
className={cn('fixed top-0 ... border-b', scrolled && 'shadow-sm')}
```

---

## Responsive Behavior

| Breakpoint | Search | Left Section | Right Section |
|------------|--------|--------------|---------------|
| Mobile (< 640px) | Icon only (no text). Click → full-screen search overlay | Hamburger + Clinic pill | Bell + Avatar |
| Tablet (640-1023px) | Search bar `max-w-xs`, visible | Clinic name text | Bell + Avatar |
| Desktop (≥ 1024px) | Search bar `max-w-md`, visible | Clinic name hidden (in sidebar) | Bell + Avatar + name text beside avatar |

**Desktop only — name beside avatar:**
```
[Avatar] Dr. Alejandro Gómez ▾
```
`hidden md:flex items-center gap-2 text-sm font-medium text-gray-700`

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘K` / `Ctrl+K` | Open command palette |
| `Escape` | Close command palette / notification panel |

---

## Accessibility

- **Role:** `role="banner"` on the `<header>` element
- **Search button:** `aria-label="Buscar pacientes (Ctrl+K)"`, `aria-haspopup="dialog"`, `aria-expanded={paletteOpen}`
- **Notification bell:** `aria-label="Notificaciones — [count] sin leer"` when count > 0, else `"Notificaciones"`
- **Avatar dropdown:** `aria-haspopup="menu"`, `aria-expanded={dropdownOpen}`, `aria-label="Menú de usuario"`
- **Command palette:** `role="dialog"`, `aria-label="Buscar"`, manages focus trap
- **Keyboard:** All interactive elements focusable. Dropdown navigable with arrow keys. Escape closes panels.
- **Language:** All labels es-419

---

## Implementation Notes

**File Location:**
- Component: `src/components/layout/app-header.tsx`
- Search palette: `src/components/layout/command-palette.tsx`
- Notification panel: `src/components/layout/notification-panel.tsx`

**Hooks Used:**
- `useAuth()` — user + tenant context
- `useNotifications()` — unread count
- `useSidebarStore()` — sidebar state for left-padding
- `useCommandPalette()` — open/close + keyboard shortcut binding

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
