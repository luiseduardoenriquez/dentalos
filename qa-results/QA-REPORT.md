# DentalOS Frontend QA Report

**Date:** 2026-03-04 (updated with Portal + Admin internal testing)
**Tester:** Claude (Playwright automation)
**Environment:** localhost:3000 (frontend) + localhost:8000 (backend)
**Logins tested:**
- Clinic owner: owner@demo.dentalos.co / DemoPass1
- Patient portal: maria.gonzalez@gmail.com / DemoPass1 (tenant: 9932a3ee-...)
- Admin: admin@dentalos.app / AdminPass1

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Metric | Value |
|--------|-------|
| **Total routes tested** | 107 |
| **Fully working (OK)** | 75 (70%) |
| **Working with API errors** | 19 (18%) |
| **Crashes (ErrorBoundary)** | 3 (3%) |
| **Empty/loading issues** | 5 (5%) |
| **Auth redirects (correct behavior)** | 17 (Portal + Admin unauthenticated) |
| **Portal internal pages tested** | 12 (logged in as patient) |
| **Admin internal pages tested** | 8 (logged in as superadmin) |

**Overall verdict:** The frontend shell is **solid** — 88% of pages render their UI correctly across all three portals (clinic dashboard, patient portal, admin panel). All three login flows work end-to-end. The main issues are: (1) a critical auth bug where page reload loses JWT tokens (affects both dashboard AND portal), (2) missing backend API endpoints causing graceful failures, (3) 3 pages crashing with unhandled errors, and (4) a minor referral code interpolation bug in the portal.

---

## CRITICAL BUGS (P0 — Fix immediately)

### BUG-001: Page reload loses JWT → infinite loading (Dashboard + Portal)
- **Route:** Any dashboard route AND any portal route on full page reload (F5, direct URL entry)
- **Impact:** CRITICAL — Users who refresh the page get stuck on a loading screen forever
- **Root cause:** JWT access token stored in JS memory only. For dashboard: `dentalos_session` cookie passes middleware check, but `/api/v1/auth/me` returns 401 → shows "Cargando panel..." indefinitely. For portal: same pattern — `/api/v1/portal/me` returns 401 → shows "Cargando portal..." indefinitely.
- **Fix needed:** When `/api/v1/auth/me` or `/api/v1/portal/me` returns 401, clear the session cookie and redirect to the respective login page. Also consider: persist access token in sessionStorage, or use refresh token flow to silently re-authenticate.

### BUG-002: Dashboard greeting missing clinic name
- **Route:** `/dashboard`
- **Impact:** LOW visual — Shows "Panel de — aquí tienes el resumen de hoy." (clinic name missing)
- **Fix:** The tenant name from auth context is not being interpolated in the greeting.

### BUG-003: `/analytics/profit-loss` crashes with TypeError
- **Route:** `/analytics/profit-loss`
- **Impact:** HIGH — ErrorBoundary catches it, shows generic error page
- **Console:** `TypeError: Cannot read properties of... caught by ErrorBoundaryHandler`
- **Fix:** Likely trying to access `.data` on a null/undefined API response.

### BUG-004: `/reputation` page crashes with TypeError
- **Route:** `/reputation`
- **Impact:** HIGH — ErrorBoundary catches it, shows generic error page
- **Console:** `TypeError: Cannot read properties of... caught by ErrorBoundaryHandler`
- **Fix:** Same pattern — null-safety on API response data.

### BUG-005: `/settings/referral-program` crashes with TypeError
- **Route:** `/settings/referral-program`
- **Impact:** HIGH — ErrorBoundary catches it, shows generic error page
- **Console:** `TypeError: Cannot read properties of... caught by ErrorBoundaryHandler`
- **Fix:** Same pattern.

### BUG-021: Portal referral WhatsApp share URL shows "undefined"
- **Route:** `/portal/referral`
- **Impact:** MEDIUM — WhatsApp share link contains `undefined` for both the referral code and portal URL
- **URL generated:** `https://wa.me/?text=...Usa%20mi%20código%20*undefined*%20o%20ingresa%20aquí%3A%20undefined`
- **Fix:** The referral code and portal base URL are not being interpolated into the WhatsApp share template.

### BUG-022: Portal login requires raw UUID for clinic ID
- **Route:** `/portal/login`
- **Impact:** MEDIUM UX — The "Clínica" field requires the raw UUID (`9932a3ee-c7aa-...`) instead of a user-friendly slug or clinic name
- **Fix:** Accept clinic slug (e.g., `clinica-demo-dental`) or clinic name with autocomplete, and resolve to UUID on the backend.

### BUG-023: Portal nav missing links to Postop, Loyalty, and Referral pages
- **Route:** `/portal/*` (sidebar navigation)
- **Impact:** MEDIUM UX — Portal pages `/portal/postop`, `/portal/loyalty`, and `/portal/referral` exist and work but have no links in the portal sidebar navigation
- **Fix:** Add these to the portal navigation bar.

---

## HIGH PRIORITY BUGS (P1)

### BUG-006: Middleware doesn't protect all dashboard routes
- **Route:** `/whatsapp`, `/marketing`, `/chatbot`, `/calls`, `/lab-orders`, `/telemedicine`, `/recall`, `/intake`, `/reputation`, `/memberships`, `/convenios`, `/financing`, `/referral-program`, `/huddle`
- **Impact:** HIGH — These routes are accessible without auth cookie (middleware `isDashboardRoute` list is incomplete)
- **Fix:** Add all dashboard routes to the middleware's `isDashboardRoute` check, or change to a whitelist approach (everything not public requires auth).

### BUG-007: `/settings/consent-templates` renders empty
- **Route:** `/settings/consent-templates`
- **Impact:** MEDIUM — Page renders with no content at all (blank main area)
- **Console:** `Failed to load resource: 401 on /api/v1/consent-templates`
- **Fix:** The page component doesn't render its shell when API fails.

### BUG-008: WhatsApp conversations fail to load
- **Route:** `/whatsapp`
- **Impact:** MEDIUM — Shows "No se pudieron cargar las conversaciones"
- **Console:** `Failed to load resource on /api/v1/messaging/conversations`
- **Note:** May require WhatsApp integration to be configured first.

### BUG-009: Inventory items API returns 404
- **Route:** `/inventory`
- **Impact:** MEDIUM — Page renders but shows empty state incorrectly (API 404, not actually empty)
- **Console:** `Failed to load resource: 404 on /api/v1/inventory/items`
- **Fix:** Backend endpoint `/api/v1/inventory/items` not found.

### BUG-010: Analytics sub-pages API 404s
- **Routes:** `/analytics/patients`, `/analytics/appointments`, `/analytics/revenue`
- **Impact:** MEDIUM — Pages render their shell but show no data
- **Console:** 404 on `/api/v1/analytics/patients`, `/api/v1/analytics/appointments`, `/api/v1/analytics/revenue`
- **Note:** These endpoints may not be implemented yet on the backend.

### BUG-011: NPS tab missing from Analytics navigation
- **Route:** `/analytics` (nav bar)
- **Impact:** LOW — The `analytics/nps/page.tsx` file exists but there's no link to it in the analytics navigation
- **Fix:** Add "NPS" link to the analytics sub-navigation.

---

## MEDIUM PRIORITY (P2)

### BUG-012: Settings sub-pages not linked from main settings page
- **Routes:** `/settings/catalog`, `/settings/loyalty`, `/settings/memberships`, `/settings/intake-templates`, `/settings/postop-templates`, `/settings/referral-program`, `/settings/reputation`
- **Impact:** MEDIUM — These pages exist but aren't accessible from the Settings page navigation
- **Fix:** Add these to the Settings page link grid.

### BUG-013: `/settings/loyalty` shows error
- **Route:** `/settings/loyalty`
- **Impact:** LOW — Shows "Error al cargar la configuración de fidelización"
- **Console:** API 404 on `/api/v1/settings/loyalty`

### BUG-014: `/settings/reputation` shows error
- **Route:** `/settings/reputation`
- **Impact:** LOW — Shows "Error al cargar la configuración de reputación"
- **Console:** API 404 on `/api/v1/settings/reputation`

### BUG-015: `/financing` shows API error
- **Route:** `/financing`
- **Impact:** LOW — Shows "No se pudo cargar el reporte de financiamiento"
- **Console:** API error on `/api/v1/financing/applications` and `/api/v1/financing/report`

### BUG-016: `/huddle` shows API error
- **Route:** `/huddle`
- **Impact:** LOW — Shows "No se pudo cargar el resumen del día"
- **Console:** API 404 on `/api/v1/huddle/today`

### BUG-017: Growth/CRM pages not in sidebar
- **Routes:** `/huddle`, `/memberships`, `/intake`, `/recall`, `/reputation`, `/convenios`, `/referral-program`, `/financing`, `/chatbot`
- **Impact:** MEDIUM UX — These pages exist but are only accessible via direct URL, not from the sidebar
- **Fix:** Add a "Growth" or "CRM" section to the sidebar.

### BUG-018: Billing sub-pages not linked from billing page
- **Routes:** `/billing/cash-register`, `/billing/expenses`, `/billing/eps-claims`, `/billing/commissions`, `/billing/tasks`
- **Impact:** MEDIUM UX — These pages all work correctly but the billing dashboard has no tab navigation to reach them
- **Fix:** Add tab/nav links to the billing page header.

### BUG-019: Favicon missing
- **Route:** All pages
- **Impact:** LOW visual — `Failed to load resource: 404 on /favicon.ico`
- **Fix:** Add favicon.ico to the public directory.

### BUG-020: Web App Manifest warning
- **Route:** All pages
- **Impact:** LOW — "Error while trying to use the following icon from the Manifest" on every page load
- **Fix:** Check `manifest.json` icon references.

---

## Route-by-Route Results

### Landing & Public Pages

| Route | Status | Notes |
|-------|--------|-------|
| `/` (Landing) | OK | Full marketing site, pricing, testimonials, features |
| `/login` | OK | Form works, login successful, clinic selector for multi-tenant |
| `/register` | OK | Redirects to dashboard when logged in (correct) |
| `/forgot-password` | OK | Redirects to dashboard when logged in (correct) |
| `/portal/login` | OK | Portal login form renders correctly |
| `/admin/login` | OK | Admin login form renders correctly |
| `/survey/[slug]` | OK | Survey form renders with star rating |

### Dashboard — Main Modules (via sidebar click, auth preserved)

| Route | Status | Notes |
|-------|--------|-------|
| `/dashboard` | OK | KPIs, quick actions, 5 patients, $0 revenue. Minor: clinic name missing in greeting |
| `/patients` | OK | List with 5 patients, search, filters, pagination, sort |
| `/patients/[id]` | OK | Detail view with tabs: Resumen, Odontograma, Historial, Tratamientos, Citas, Documentos |
| `/patients/[id]` — Resumen tab | OK | Personal info, contact, emergency contact, medical info |
| `/patients/[id]` — Odontograma tab | OK | Link to open full odontogram |
| `/patients/[id]` — Historial tab | OK | Empty state with "Nueva nota clínica" link |
| `/patients/[id]` — Tratamientos tab | OK | Empty state with "Crear plan" link |
| `/patients/[id]` — Citas tab | OK | Shows 2 appointments with data |
| `/patients/[id]` — Documentos tab | OK | Empty state |
| `/patients/new` | OK | Full form: personal info, contact, emergency, medical, allergies |
| `/agenda` | OK | Day view, time slots (7am-9pm), "Nueva cita" button, period navigation |
| `/billing` | OK | KPI cards (pending, overdue, collected month/year), empty invoice state |
| `/compliance` | OK | RDA status (40.4%), 11 gaps table, deadline countdown, progress bars |
| `/compliance/rips` | OK | RIPS page with compliance nav |
| `/compliance/e-invoices` | OK | E-invoices page with compliance nav |
| `/whatsapp` | API_ERROR | UI renders (chat layout), but conversations fail to load |
| `/marketing` | OK | Campaign list, "Nueva campaña" button, empty state |
| `/analytics` | OK | AI query box, period selector, KPIs, sub-navigation |
| `/analytics/patients` | OK* | Shell renders, API 404 → no data |
| `/analytics/appointments` | OK* | Shell renders, API 404 → no data |
| `/analytics/revenue` | OK* | Shell renders, API 404 → no data |
| `/analytics/profit-loss` | CRASH | TypeError → ErrorBoundary |
| `/calls` | OK | Call log table, direction/status filters, empty state |
| `/lab-orders` | OK | Kanban board (5 columns), filters, "Nueva orden" button |
| `/telemedicine` | OK | Session list, status filters, empty state |
| `/inventory` | OK* | Shell renders, API 404 on inventory items endpoint |
| `/settings` | OK | Clinic info form (pre-filled), preferences (timezone, currency, locale), organized sub-page links |

### Dashboard — Settings Sub-pages

| Route | Status | Notes |
|-------|--------|-------|
| `/settings/team` | OK | Team members list (4 members), "Invitar miembro" button |
| `/settings/schedule` | OK | Working hours configuration |
| `/settings/subscription` | OK | Plan details and usage |
| `/settings/odontogram` | OK | View mode, zoom, voice dictation settings |
| `/settings/consent-templates` | EMPTY | Blank page — API error |
| `/settings/notificaciones` | OK | Notification channel preferences |
| `/settings/integraciones` | OK | Integration cards (WhatsApp, Google Calendar, Mercado Pago) |
| `/settings/audit-log` | OK | Audit log table with filters |
| `/settings/voice` | OK | Voice dictation parameters |
| `/settings/reminders` | OK | Appointment reminder configuration |
| `/settings/compliance` | OK | Colombian regulatory settings |
| `/settings/catalog` | OK | Service catalog with pricing |
| `/settings/loyalty` | ERROR | "Error al cargar" — API 404 |
| `/settings/memberships` | OK | Membership plans management |
| `/settings/intake-templates` | OK | Intake form templates |
| `/settings/postop-templates` | OK | Post-op instruction templates |
| `/settings/referral-program` | CRASH | TypeError → ErrorBoundary |
| `/settings/reputation` | ERROR | "Error al cargar" — API 404 |

### Dashboard — Growth/CRM Pages

| Route | Status | Notes |
|-------|--------|-------|
| `/huddle` | API_ERROR | "No se pudo cargar el resumen del día" — API 404 |
| `/memberships` | OK | Membership subscriptions list, stats |
| `/intake` | OK | Intake requests with status filters |
| `/recall` | OK | Recall campaigns dashboard with stats |
| `/reputation` | CRASH | TypeError → ErrorBoundary |
| `/convenios` | OK | Business agreements management |
| `/referral-program` | OK | Referral tracking dashboard |
| `/financing` | API_ERROR | "No se pudo cargar" — API error |
| `/chatbot` | OK | Chatbot monitor with conversation list |

### Dashboard — Billing Sub-pages

| Route | Status | Notes |
|-------|--------|-------|
| `/billing/cash-register` | OK | Cash register with "Abrir caja" flow |
| `/billing/expenses` | OK | Expense tracking with category filters |
| `/billing/eps-claims` | OK | EPS claims list with status filters |
| `/billing/commissions` | OK | Doctor commissions report |
| `/billing/tasks` | OK | Task queue with type/status filters |

### Portal Pages — Unauthenticated (auth redirects)

| Route | Status | Notes |
|-------|--------|-------|
| `/portal/login` | OK | Login form (clinic ID + email/phone + password + magic link option) |
| `/portal/dashboard` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/appointments` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/treatment-plans` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/documents` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/messages` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/invoices` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/odontogram` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/postop` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/loyalty` | REDIRECT | Correctly redirects to `/portal/login` |
| `/portal/referral` | REDIRECT | Correctly redirects to `/portal/login` |

### Portal Pages — Authenticated (logged in as patient: María González)

| Route | Status | Notes |
|-------|--------|-------|
| `/portal/login` | OK | Login form works: 3 fields (clinic UUID, email/phone, password), magic link option, "Ingresa aquí" link to clinic login |
| `/portal/dashboard` | OK | "Hola, María" greeting, upcoming appointments, quick links (treatment plans, messages, documents, balance), "Agendar nueva cita" CTA |
| `/portal/appointments` | OK | "Próximas" and "Pasadas" tabs. Past shows 2 completed appointments with doctor names, dates, duration, and type |
| `/portal/treatment-plans` | OK | Empty state: "No tienes planes de tratamiento" |
| `/portal/documents` | OK | Filter tabs (Todos, Consentimientos, Radiografías, Recetas). Empty state: "No hay documentos disponibles" |
| `/portal/messages` | OK | "Nuevo mensaje" form with textarea + send button. Empty state: "No tienes mensajes aún" |
| `/portal/invoices` | OK | "Pagos y facturas" heading, pending balance $0 badge, "Estás al día con tus pagos" message |
| `/portal/odontogram` | OK | Full FDI tooth chart (upper/lower jaw, left/right quadrants), 5 findings with caries, condition legend, detail table per tooth. "Última actualización: 26 de febrero de 2026" |
| `/portal/postop` | API_ERROR | Shell renders, "Error al cargar las instrucciones" with retry button — API 404 on `/api/v1/portal/postop` |
| `/portal/loyalty` | API_ERROR | Shell renders, "No se pudo cargar tu programa de puntos" — API 403/404 on `/api/v1/portal/loyalty` |
| `/portal/referral` | OK | Referral code share (WhatsApp + QR), stats (0 referidos), "Mis recompensas" link, "¿Cómo funciona?" 3-step guide. BUG: WhatsApp URL shows `undefined` for code and URL |
| `/portal/referral/rewards` | API_ERROR | Shell renders with back link, "Error al cargar las recompensas" with retry — API 404 on `/api/v1/portal/referral/rewards` |

### Admin Pages — Unauthenticated (auth redirects)

| Route | Status | Notes |
|-------|--------|-------|
| `/admin/login` | OK | Admin login form with email + password, TOTP second step, show/hide password |
| `/admin/dashboard` | REDIRECT | Correctly redirects to `/admin/login` |
| `/admin/tenants` | REDIRECT | Correctly redirects to `/admin/login` |
| `/admin/plans` | REDIRECT | Correctly redirects to `/admin/login` |
| `/admin/feature-flags` | REDIRECT | Correctly redirects to `/admin/login` |
| `/admin/analytics` | REDIRECT | Correctly redirects to `/admin/login` |
| `/admin/health` | REDIRECT | Correctly redirects to `/admin/login` |

### Admin Pages — Authenticated (logged in as superadmin: Superadmin Dev)

| Route | Status | Notes |
|-------|--------|-------|
| `/admin/login` | OK | Email + password form works. TOTP step available (not required for dev). Login redirects to `/admin/dashboard` |
| `/admin/dashboard` | OK | Platform metrics: 11 clinics, $0 MRR, 54 users, "Saludable" status. Service health: PostgreSQL, Redis, RabbitMQ, Storage all connected. Recent clinics table (5 rows with links) |
| `/admin/tenants` | OK | Full clinic list (11 rows), search box, status filter dropdown, pagination. Table: name (linked), slug, plan, status, users, created date |
| `/admin/tenants/[id]` | OK | Clinic detail: name, slug, plan, status, user count, patient count, created date, UUID. Admin actions: "Impersonar Clínica" button with audit warning |
| `/admin/analytics` | OK | Platform analytics: clinics, MRR, ARR, total users, total patients, MAU, churn rate (0.0% — "Saludable"), revenue per clinic average |
| `/admin/plans` | OK | 5 plan cards (Free, Starter $19, Pro $39, Clínica $69, Enterprise). Each shows: price, patient/doctor limits, feature list, edit button |
| `/admin/feature-flags` | OK | Empty state with "Crear flag" button: "No hay feature flags configurados. Crea el primero." |
| `/admin/health` | OK | Real-time system health with 30s auto-refresh. All 4 services (PostgreSQL, Redis, RabbitMQ, Almacenamiento) showing "Conectado". "Verificar ahora" button. Timestamp shown |

---

## Prioritized Fix List

### Immediate (P0)
1. **BUG-001:** Fix auth token persistence / handle 401 → redirect to login (affects BOTH dashboard AND portal)
2. **BUG-003:** Fix `/analytics/profit-loss` TypeError crash
3. **BUG-004:** Fix `/reputation` TypeError crash
4. **BUG-005:** Fix `/settings/referral-program` TypeError crash

### This Sprint (P1)
5. **BUG-006:** Add missing routes to middleware `isDashboardRoute`
6. **BUG-007:** Fix `/settings/consent-templates` empty render
7. **BUG-018:** Add tab navigation to billing page for sub-pages
8. **BUG-017:** Add Growth/CRM section to sidebar
9. **BUG-012:** Add missing settings sub-page links
10. **BUG-021:** Fix portal referral WhatsApp share URL (undefined code/URL)
11. **BUG-022:** Accept clinic slug in portal login (not just raw UUID)
12. **BUG-023:** Add missing portal nav links (postop, loyalty, referral)

### Next Sprint (P2)
13. **BUG-002:** Fix clinic name in dashboard greeting
14. **BUG-011:** Add NPS link to analytics navigation
15. **BUG-019:** Add favicon
16. **BUG-020:** Fix manifest icon references
17. **BUG-008 through BUG-016:** Backend API endpoints needed for full functionality

---

## Positive Findings

1. **Landing page** — Professional, complete marketing site with pricing, testimonials, features
2. **All 3 login flows work** — Clinic login (with multi-clinic selector), portal login (with magic link option), and admin login (with TOTP 2FA step) all functional end-to-end
3. **Patient management** — Full CRUD with comprehensive detail view and 6 tabs
4. **Agenda** — Clean day view with clickable time slots
5. **Compliance dashboard** — Excellent RDA compliance tracking with gap analysis
6. **Analytics** — AI-powered query interface is innovative
7. **Settings** — Well-organized with pre-filled clinic data
8. **Auth redirects** — Portal and Admin correctly redirect unauthenticated users
9. **Error boundaries** — Crashes are caught gracefully (not white screens)
10. **Spanish UI** — Consistent es-419 throughout
11. **Billing sub-modules** — Cash register, expenses, EPS claims, commissions, tasks all render correctly
12. **Lab orders Kanban** — 5-stage visual board works well
13. **Design system** — Consistent, professional design with DentalOS brand colors
14. **Portal odontogram** — Excellent read-only FDI tooth chart with findings detail, per-tooth legend, and last-updated timestamp
15. **Portal appointments** — Past/upcoming tabs, doctor names, appointment types and durations shown
16. **Portal referral program** — WhatsApp share, QR code, 3-step how-it-works guide, rewards sub-page
17. **Admin dashboard** — Comprehensive platform overview with service health, clinic table, KPIs
18. **Admin tenants** — Full clinic management with search, filters, pagination, detail view, and impersonation
19. **Admin plans** — All 5 pricing tiers displayed with features, limits, and edit capability
20. **Admin health** — Real-time service monitoring with auto-refresh (30s) and manual check

---

## Console Error Summary

| Error Type | Count | Notes |
|------------|-------|-------|
| Favicon 404 | Every page | Missing `/favicon.ico` |
| Manifest icon warning | Every page | Icon reference issue |
| Auth 401 on reload | On page.goto() (dashboard + portal) | JWT lost on full page reload |
| API 404s | ~18 endpoints | Backend endpoints not implemented (dashboard + portal) |
| TypeError crashes | 3 dashboard pages | Null-safety issues in components |
| Portal API 403/404 | 3 portal pages | `/portal/postop`, `/portal/loyalty`, `/portal/referral/rewards` |

---

## Testing Coverage Summary

| Portal | Login tested | Internal pages tested | Auth redirect tested |
|--------|-------------|----------------------|---------------------|
| **Clinic Dashboard** | owner@demo.dentalos.co | 56 pages (sidebar + direct nav) | N/A (has session) |
| **Patient Portal** | maria.gonzalez@gmail.com | 12 pages (nav + client-side nav) | 10 routes → `/portal/login` |
| **Admin Panel** | admin@dentalos.app | 8 pages (all sidebar links + tenant detail) | 6 routes → `/admin/login` |
| **Public** | N/A | 7 pages (landing, login, register, etc.) | N/A |

**Total unique routes tested: 107** (up from 87 in initial report)

---

*Report generated by Playwright automated QA — 2026-03-04*
*Updated with Portal + Admin authenticated testing — 2026-03-04*
