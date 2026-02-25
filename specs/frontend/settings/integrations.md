# Integraciones — Frontend Spec

## Overview

**Spec ID:** FE-S-08

**Screen:** Integrations management page — connect and configure external services.

**Route:** `/settings/integraciones`

**Priority:** Medium

**Backend Specs:** `specs/integrations/INT-01.md`, `specs/integrations/INT-07.md`, `specs/integrations/INT-09.md`, `specs/integrations/INT-10.md`

**Dependencies:** `FE-DS-01`, `FE-DS-02` (button), `FE-DS-03` (input), `FE-DS-06` (modal), `FE-DS-10` (card), `FE-DS-11` (badge)

---

## User Flow

**Entry Points:**
- Sidebar: Configuración → Integraciones
- Compliance settings DIAN section → "Configurar" link
- Notification settings channel warning → "Configurar" link

**Exit Points:**
- OAuth flows open in new tab (Google Calendar)
- External docs links (WhatsApp, Mercado Pago)

**User Story:**
> As a clinic_owner, I want to connect external services like WhatsApp, Google Calendar, DIAN, and payment platforms so that my clinic operates with automated communications and legally compliant invoicing.

**Roles with access:** `clinic_owner` only.

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  "Integraciones"                |
| Side-  +---------------------------------+
|  bar   |  [Integration cards grid]       |
|        |  2-column grid (3-column lg+)   |
+--------+---------------------------------+
```

**Layout:** 2-column grid on tablet (`grid-cols-2 gap-6`), 3-column on desktop (`lg:grid-cols-3`), 1-column on mobile.

---

## Integration Card Component

Each integration is a Card with a consistent structure:

```
+--------------------------------------+
| [Icon 40px]  Service Name            |
|              [Status badge]          |
|                                      |
| Short description (2 lines max)      |
|                                      |
| [Configurar button]                  |
+--------------------------------------+
```

**Card props:**
- Icon: brand logo or Lucide icon, 40x40px
- Service name: `text-base font-semibold`
- Status badge: Connected (green) / Disconnected (gray) / Error (red) / Partial (amber)
- Description: `text-sm text-gray-500`
- Button: "Configurar" (secondary) if disconnected, "Configurado ✓" (outline teal) if connected

**Status badge mapping:**

| Status | Label | Color |
|--------|-------|-------|
| connected | Conectado | `green-100` / `green-700` |
| disconnected | Desconectado | `gray-100` / `gray-500` |
| error | Error de conexión | `red-100` / `red-700` |
| partial | Configuración parcial | `amber-100` / `amber-700` |

---

## Integration 1: WhatsApp Business

**Icon:** WhatsApp brand icon (green)
**Status:** Connected / Disconnected

**"Configurar" → opens modal: "Configurar WhatsApp Business"**

### WhatsApp Configuration Modal

**Size:** `md`

**Content:**

**Step 1 — Phone Number:**
- Field: Número de teléfono
- Type: phone input with Colombia (+57) prefix selector
- Validation: valid international format
- Placeholder: "+57 300 123 4567"

**Step 2 — Connection Status:**
- Shows QR code if not connected (refreshes every 60s)
- OR shows green checkmark "WhatsApp conectado" if already linked
- Instructions: "Escanea este código con WhatsApp Business en tu teléfono"

**Test message button:** "Enviar mensaje de prueba" → sends a test WhatsApp to the registered number. Toast: "Mensaje de prueba enviado" or error.

**Disconnect option:** "Desconectar WhatsApp" link (text-red-600, requires confirmation).

---

## Integration 2: Google Calendar

**Icon:** Google Calendar logo
**Status:** Connected per-doctor / Disconnected

**"Configurar" → opens modal: "Sincronización con Google Calendar"**

### Google Calendar Modal

**Size:** `md`

**Content:**
- Description: "Sincroniza las citas de DentalOS con los calendarios personales de tus doctores."

**Per-doctor toggle list:**

| Doctor name | Toggle | Calendar email |
|-------------|--------|----------------|
| Dr. Alejandro Gómez | [ON] | agomez@gmail.com |
| Dra. María Rodríguez | [OFF] | — |

**For doctors with toggle ON:** Shows connected Google account email. "Desconectar" link to revoke access.

**For doctors with toggle OFF:** "Conectar con Google" button → opens OAuth flow in new tab (`/api/v1/integrations/google/oauth/start?doctor_id={id}`). Callback handled via URL params. Page polls for connection status every 3s after window opens.

**Scope warning:** "DentalOS solo accede a crear y modificar eventos en el calendario seleccionado. No lee eventos existentes."

---

## Integration 3: DIAN / MATIAS API

**Icon:** DIAN government logo or `FileText` Lucide icon
**Status:** Connected / Disconnected

**"Configurar" → links to `/settings/cumplimiento`** (DIAN section already in compliance settings).

**Card description:** "Facturación electrónica válida ante la DIAN. Configurada en Cumplimiento."

**If connected:** Card shows summary: "NIT: 900.123.456-7 | Res. 18764000001-2019"

---

## Integration 4: Mercado Pago

**Icon:** Mercado Pago brand icon
**Status:** Connected / Disconnected

**"Configurar" → opens modal: "Configurar Mercado Pago"**

### Mercado Pago Modal

**Size:** `md`

**Content:**

| Field | Type | Required | Placeholder | Notes |
|-------|------|----------|-------------|-------|
| Access Token (Producción) | password input | Yes | "APP_USR-..." | Show/hide toggle |
| Access Token (Sandbox) | password input | No | "TEST-..." | For testing |
| Public Key | text | Yes | "APP_USR-..." | Client-side use |

**Test Mode Toggle:**
- "Usar modo sandbox" — when ON, sandbox token is used

**Webhook URL (read-only):**
```
https://app.dentalos.io/api/v1/webhooks/mercadopago/[tenant_id]
```
Copy button beside the URL. Instructions: "Agrega esta URL en tu panel de Mercado Pago bajo Notificaciones → IPN."

**"Verificar conexión" button:** Tests token validity before saving.

---

## Integration 5: Email (SendGrid)

**Icon:** SendGrid logo or `Mail` Lucide icon
**Status:** Connected / Disconnected

**"Configurar" → opens modal: "Configurar Email (SendGrid)"**

### SendGrid Modal

**Size:** `md`

**Content:**

| Field | Type | Required | Placeholder |
|-------|------|----------|-------------|
| API Key | password input | Yes | "SG...." |
| Dominio remitente | text | Yes | "clinica.com" |
| Email de envío | email | Yes | "recordatorios@clinica.com" |
| Nombre del remitente | text | Yes | "Clínica Dental Sonrisa" |

**Domain verification status:**
- If domain verified: green badge "Dominio verificado" + DNS records summary
- If not verified: amber badge "Verificación pendiente" + DNS records to add:

```
Tipo    Host                    Valor
TXT     em.clinica.com          v=spf1 ...
CNAME   s1._domainkey...        s1.domainkey...
```

"Cómo verificar tu dominio" link → opens SendGrid docs in new tab.

**Test email button:** "Enviar email de prueba a [owner email]"

---

## Integration Status Summary Bar

**Position:** Top of integrations page, below page title.

**Content:** Horizontal row of status pills for quick overview:

```
WhatsApp ● | Google Calendar ● | DIAN ● | Mercado Pago ○ | Email ●
```

- Filled circle: connected
- Empty circle: not connected

**Note:** Only shown on desktop/tablet. Hidden on mobile.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load integration statuses | `/api/v1/integrations` | GET | `specs/integrations/INT-01.md` | 2min |
| Save WhatsApp config | `/api/v1/integrations/whatsapp` | PUT | `specs/integrations/INT-01.md` | Invalidate |
| Google OAuth start | `/api/v1/integrations/google/oauth/start` | GET | `specs/integrations/INT-09.md` | — |
| Google connection status | `/api/v1/integrations/google/status` | GET | `specs/integrations/INT-09.md` | no-cache |
| Save Mercado Pago | `/api/v1/integrations/mercadopago` | PUT | `specs/integrations/INT-10.md` | Invalidate |
| Save SendGrid | `/api/v1/integrations/sendgrid` | PUT | `specs/integrations/INT-07.md` | Invalidate |

### State Management

**Local State (useState):**
- `openModal: IntegrationType | null`
- `googlePollingActive: boolean`

**Server State (TanStack Query):**
- Query key: `['integrations', tenantId]`
- Stale time: 2 minutes

---

## Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Open config modal | Click "Configurar" | Modal opens | — |
| Save WhatsApp | Modal save | PUT config | Toast "WhatsApp configurado" |
| Test WhatsApp | Test button | POST test message | Toast success/fail |
| Connect Google (per doctor) | OAuth button | New tab → OAuth flow | Polling shows connection status |
| Save Mercado Pago | Modal save after verify | PUT config | Toast "Mercado Pago configurado" |
| Copy webhook URL | Copy button | Clipboard copy | "Copiado" tooltip |
| Test email | SendGrid test button | POST test | Toast "Email de prueba enviado" |

---

## Loading & Error States

### Loading State
- 5 card skeletons in grid layout

### Error State
- Integration load failure: error card over the grid "No se pudieron cargar las integraciones."
- Per-integration error: card shows red "Error de conexión" badge + "Reconectar" button

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | 1-column card grid. Status summary bar hidden. |
| Tablet (640-1024px) | 2-column card grid. Status bar visible. |
| Desktop (> 1024px) | 3-column card grid. |

---

## Accessibility

- **Focus order:** Status bar → card 1 → card 2 → ... → card 5. Modals trap focus.
- **Screen reader:** Integration cards have `aria-label="[service] — Estado: [status]"`. Webhook URL copy button has `aria-label="Copiar URL del webhook"`.
- **Keyboard:** Escape closes modals. All buttons keyboard-operable.
- **Language:** All labels es-419.

---

## Implementation Notes

**File Location:**
- Page: `src/app/(dashboard)/settings/integraciones/page.tsx`
- Components: `src/components/settings/IntegrationCard.tsx`, `src/components/settings/WhatsAppModal.tsx`, `src/components/settings/GoogleCalendarModal.tsx`, `src/components/settings/MercadoPagoModal.tsx`, `src/components/settings/SendGridModal.tsx`

---

## Acceptance Criteria

- [ ] Integration grid shows 5 cards with correct status badges
- [ ] WhatsApp modal allows phone config and QR scanning
- [ ] Google Calendar per-doctor OAuth flow completes
- [ ] Mercado Pago webhook URL displayed with copy button
- [ ] SendGrid domain verification status shown
- [ ] All modals have loading states during API calls
- [ ] Test functions work for WhatsApp, Email
- [ ] Owner-only access enforced
- [ ] Mobile 1-column, tablet 2-column, desktop 3-column grid

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
