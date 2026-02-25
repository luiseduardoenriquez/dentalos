# PWA Configuration Spec

> **Spec ID:** I-19
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Progressive Web App (PWA) configuration for DentalOS. Covers manifest.json (app identity, icons, display mode), Workbox-based service worker (precache + runtime cache strategies), offline fallback page, Web Push API notification subscriptions, custom install prompt, splash screens, and icon sets. The PWA enables installation on iOS/Android/desktop for a native-like experience.

**Domain:** infra / frontend

**Priority:** High

**Dependencies:** ADR-005 (PWA architecture), I-18 (offline-sync-strategy), notifications domain

---

## 1. Web App Manifest

### manifest.json

```json
{
  "name": "DentalOS",
  "short_name": "Dental",
  "description": "Sistema de gestión para clínicas dentales — Colombia, México, Chile",
  "start_url": "/dashboard",
  "scope": "/",
  "display": "standalone",
  "orientation": "any",
  "theme_color": "#0F766E",
  "background_color": "#FFFFFF",
  "lang": "es",
  "dir": "ltr",
  "categories": ["health", "medical", "business"],
  "icons": [
    {
      "src": "/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-maskable-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable"
    },
    {
      "src": "/icons/icon-maskable-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/screenshots/dashboard-wide.png",
      "sizes": "1280x800",
      "type": "image/png",
      "form_factor": "wide",
      "label": "Panel de control — DentalOS"
    },
    {
      "src": "/screenshots/odontogram-mobile.png",
      "sizes": "390x844",
      "type": "image/png",
      "form_factor": "narrow",
      "label": "Odontograma interactivo"
    }
  ],
  "shortcuts": [
    {
      "name": "Nueva Cita",
      "short_name": "Cita",
      "description": "Crear una nueva cita",
      "url": "/appointments/new",
      "icons": [{ "src": "/icons/shortcut-appointment.png", "sizes": "96x96" }]
    },
    {
      "name": "Buscar Paciente",
      "short_name": "Paciente",
      "description": "Buscar un paciente",
      "url": "/patients?action=search",
      "icons": [{ "src": "/icons/shortcut-patient.png", "sizes": "96x96" }]
    }
  ],
  "share_target": {
    "action": "/share",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {
      "title": "title",
      "files": [
        {
          "name": "file",
          "accept": ["image/jpeg", "image/png", "application/pdf"]
        }
      ]
    }
  },
  "related_applications": [],
  "prefer_related_applications": false
}
```

### Design Tokens

| Property | Value | Notes |
|----------|-------|-------|
| `theme_color` | `#0F766E` | Teal-700 — DentalOS brand primary |
| `background_color` | `#FFFFFF` | White — splash screen background |
| `display` | `standalone` | Hides browser chrome; app-like experience |
| `orientation` | `any` | Supports both portrait and landscape |

---

## 2. Service Worker (Workbox)

### Next.js Integration

```javascript
// next.config.js
const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",  // Disable in dev to avoid caching issues
  sw: "sw.js",
  buildExcludes: [
    /app-build-id/,
    /middleware-manifest\.json$/,
  ],
  // Custom runtime caching — defined in workbox-config.js
  runtimeCaching: require("./workbox-config"),
});

module.exports = withPWA({
  // ... other Next.js config
});
```

### Workbox Runtime Cache Configuration

```javascript
// workbox-config.js

module.exports = [
  // === App Shell ===
  {
    urlPattern: /^https:\/\/app\.dentalos\.app\/(_next\/static|icons|fonts)\/.*/i,
    handler: "CacheFirst",
    options: {
      cacheName: "static-assets-v1",
      expiration: {
        maxEntries: 200,
        maxAgeSeconds: 30 * 24 * 60 * 60,  // 30 days
      },
    },
  },

  // === API Reads (stale-while-revalidate) ===
  {
    urlPattern: /^https:\/\/api\.dentalos\.app\/api\/v1\/(patients|appointments|odontogram)\/.*/i,
    handler: "StaleWhileRevalidate",
    options: {
      cacheName: "api-clinical-reads",
      expiration: {
        maxEntries: 500,
        maxAgeSeconds: 7 * 24 * 60 * 60,   // 7 days
      },
      cacheableResponse: {
        statuses: [0, 200],
      },
    },
  },

  // === API Writes (Network-First — fail gracefully offline) ===
  {
    urlPattern: /^https:\/\/api\.dentalos\.app\/api\/v1\/.*/i,
    handler: "NetworkFirst",
    method: "POST",
    options: {
      cacheName: "api-writes",
      networkTimeoutSeconds: 10,
      plugins: [
        {
          requestWillFetch: async ({ request }) => {
            // Add offline queue header for middleware to detect
            const headers = new Headers(request.headers);
            headers.set("X-Offline-Queue", "true");
            return new Request(request, { headers });
          },
        },
      ],
    },
  },

  // === Navigation / Pages ===
  {
    urlPattern: /^https:\/\/app\.dentalos\.app\/.*/i,
    handler: "NetworkFirst",
    options: {
      cacheName: "pages-v1",
      networkTimeoutSeconds: 5,
      expiration: {
        maxEntries: 50,
        maxAgeSeconds: 24 * 60 * 60,  // 1 day
      },
    },
  },

  // === File Downloads (Signed S3 URLs — do not cache!) ===
  {
    urlPattern: /\.your-objectstorage\.com\/.*/i,
    handler: "NetworkOnly",  // Always fresh signed URL
  },
];
```

### Precached App Shell Files

The following files are precached by Workbox at build time (`__WB_MANIFEST` injection):

```
/_next/static/chunks/main-*.js
/_next/static/chunks/pages/*.js
/_next/static/css/*.css
/icons/icon-192x192.png
/icons/icon-512x512.png
/offline.html
/manifest.json
```

---

## 3. Offline Fallback Page

```html
<!-- public/offline.html -->
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DentalOS — Sin conexión</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #F0FDF4;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 24px;
    }
    .container {
      text-align: center;
      max-width: 400px;
    }
    .logo {
      width: 80px;
      height: 80px;
      background: #0F766E;
      border-radius: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 24px;
      font-size: 40px;
    }
    h1 { color: #0F766E; font-size: 1.5rem; margin-bottom: 8px; }
    p { color: #6B7280; line-height: 1.6; margin-bottom: 24px; }
    .card {
      background: white;
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 16px;
      text-align: left;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .card h3 { font-size: 0.875rem; font-weight: 600; color: #374151; margin: 0 0 4px; }
    .card p { font-size: 0.875rem; color: #6B7280; margin: 0; }
    button {
      background: #0F766E;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 1rem;
      cursor: pointer;
      width: 100%;
    }
    button:hover { background: #0D6562; }
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">🦷</div>
    <h1>Sin conexión a Internet</h1>
    <p>
      DentalOS está trabajando sin conexión. Los datos que veías siguen disponibles
      en caché, y tus cambios se guardarán cuando vuelva la conexión.
    </p>
    <div class="card">
      <h3>Disponible sin conexión:</h3>
      <p>Pacientes del día, odontograma, citas de hoy y mañana</p>
    </div>
    <div class="card">
      <h3>Requiere conexión:</h3>
      <p>Facturación, informes, subir imágenes, nuevas citas</p>
    </div>
    <button onclick="window.location.reload()">Intentar de nuevo</button>
  </div>
  <script>
    // Auto-reload when connection is restored
    window.addEventListener("online", () => window.location.href = "/dashboard");
  </script>
</body>
</html>
```

---

## 4. Web Push Notifications

### VAPID Keys

```bash
# Generate VAPID keys (run once, store in env)
npx web-push generate-vapid-keys
# Store output in: VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY
```

### Subscription Management API

```
POST /api/v1/push-subscriptions
DELETE /api/v1/push-subscriptions/{subscription_id}
```

**Subscribe endpoint:**

```python
from pywebpush import webpush, WebPushException
from pydantic import BaseModel
from typing import Optional
import json


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: dict       # {p256dh: str, auth: str}
    user_agent: Optional[str] = None


@router.post("/api/v1/push-subscriptions")
async def create_push_subscription(
    data: PushSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Register a Web Push subscription for a user."""
    # Check if already registered (same endpoint)
    existing = await get_subscription_by_endpoint(session, data.endpoint)
    if existing:
        # Update if same user, reject if different user
        if existing.user_id != current_user.id:
            raise HTTPException(409, "Endpoint ya registrado por otro usuario")
        # Update auth keys (may have rotated)
        existing.p256dh = data.keys["p256dh"]
        existing.auth = data.keys["auth"]
        await session.commit()
        return {"subscription_id": str(existing.id), "status": "updated"}

    # Create new subscription
    sub = PushSubscription(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        endpoint=data.endpoint,
        p256dh=data.keys["p256dh"],
        auth=data.keys["auth"],
        user_agent=data.user_agent,
    )
    session.add(sub)
    await session.commit()

    return {"subscription_id": str(sub.id), "status": "created"}
```

### Push Subscription Table (Public Schema)

```sql
CREATE TABLE public.push_subscriptions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    tenant_id   UUID NOT NULL,
    endpoint    TEXT NOT NULL,
    p256dh      TEXT NOT NULL,
    auth        TEXT NOT NULL,
    user_agent  VARCHAR(500),
    is_active   BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(endpoint)
);

CREATE INDEX idx_push_subscriptions_user_id ON public.push_subscriptions(user_id);
```

### Sending Push Notifications

```python
from pywebpush import webpush, WebPushException
import json
import logging

logger = logging.getLogger(__name__)


async def send_push_notification(
    subscription_id: str,
    title: str,
    body: str,
    url: Optional[str] = None,
    icon: str = "/icons/icon-192x192.png",
    badge: str = "/icons/badge-72x72.png",
    tag: Optional[str] = None,
) -> bool:
    """
    Send a Web Push notification to a subscribed user.
    Returns True on success, False on failure (expired/invalid subscription).
    """
    sub = await get_subscription(subscription_id)
    if not sub or not sub.is_active:
        return False

    payload = json.dumps({
        "title": title,
        "body": body,
        "icon": icon,
        "badge": badge,
        "url": url,
        "tag": tag or "dentalos-notification",
        "requireInteraction": False,
        "renotify": True,
    })

    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh,
                    "auth": sub.auth,
                },
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": f"mailto:{settings.VAPID_CONTACT_EMAIL}",
            },
            ttl=86400,  # 24 hours
        )
        await update_subscription_last_used(subscription_id)
        return True

    except WebPushException as exc:
        if exc.response and exc.response.status_code in (404, 410):
            # Subscription expired or unsubscribed — deactivate
            await deactivate_subscription(subscription_id)
            logger.info("Push subscription expired, deactivated", extra={"sub_id": subscription_id})
        else:
            logger.error("Push notification failed", extra={"error": str(exc)})
        return False
```

### Frontend Push Registration

```typescript
// src/hooks/usePushNotifications.ts

export function usePushNotifications() {
  const registerPush = async () => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      console.warn("Push notifications not supported");
      return;
    }

    // Request permission
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      return;
    }

    // Get service worker registration
    const registration = await navigator.serviceWorker.ready;

    // Subscribe to push
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(
        process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!
      ),
    });

    // Send subscription to server
    await apiClient.post("/api/v1/push-subscriptions", {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: btoa(
          String.fromCharCode(...new Uint8Array(subscription.getKey("p256dh")!))
        ),
        auth: btoa(
          String.fromCharCode(...new Uint8Array(subscription.getKey("auth")!))
        ),
      },
      user_agent: navigator.userAgent,
    });
  };

  return { registerPush };
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  return new Uint8Array([...rawData].map((char) => char.charCodeAt(0)));
}
```

### Service Worker Push Handler

```javascript
// sw.js (push event handler)

self.addEventListener("push", (event) => {
  if (!event.data) return;

  const data = event.data.json();

  const options = {
    body: data.body,
    icon: data.icon || "/icons/icon-192x192.png",
    badge: data.badge || "/icons/badge-72x72.png",
    tag: data.tag || "dentalos",
    renotify: data.renotify || false,
    requireInteraction: data.requireInteraction || false,
    data: { url: data.url },
    actions: data.actions || [],
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/dashboard";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      // Focus existing DentalOS tab if open
      for (const client of clientList) {
        if (client.url.includes("dentalos.app") && "focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      // Otherwise open new tab
      return clients.openWindow(url);
    })
  );
});
```

---

## 5. Custom Install Prompt

```typescript
// src/hooks/useInstallPrompt.ts

const INSTALL_PROMPT_KEY = "dentalos_install_dismissed";
const VISIT_COUNT_KEY = "dentalos_visit_count";
const MIN_VISITS_BEFORE_PROMPT = 3;

export function useInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    // Track visits
    const visitCount = parseInt(
      localStorage.getItem(VISIT_COUNT_KEY) || "0"
    ) + 1;
    localStorage.setItem(VISIT_COUNT_KEY, String(visitCount));

    // Check if prompt was dismissed
    const dismissed = localStorage.getItem(INSTALL_PROMPT_KEY);
    if (dismissed) return;

    // Only show after MIN_VISITS_BEFORE_PROMPT visits
    if (visitCount < MIN_VISITS_BEFORE_PROMPT) return;

    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowPrompt(true);
    });
  }, []);

  const install = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setShowPrompt(false);
    }
    setDeferredPrompt(null);
  };

  const dismiss = () => {
    localStorage.setItem(INSTALL_PROMPT_KEY, "true");
    setShowPrompt(false);
  };

  return { showPrompt, install, dismiss };
}
```

### Install Prompt Banner UI

```typescript
// src/components/pwa/InstallBanner.tsx

export const InstallBanner = () => {
  const { showPrompt, install, dismiss } = useInstallPrompt();

  if (!showPrompt) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 bg-teal-700 text-white rounded-xl p-4 shadow-xl z-50 flex items-center gap-4">
      <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center flex-shrink-0">
        <img src="/icons/icon-72x72.png" alt="DentalOS" className="w-10 h-10" />
      </div>
      <div className="flex-1">
        <p className="font-semibold text-sm">Instala DentalOS</p>
        <p className="text-xs text-teal-200">
          Acceso rápido desde tu pantalla de inicio, funciona sin conexión.
        </p>
      </div>
      <div className="flex gap-2">
        <button
          onClick={dismiss}
          className="text-teal-300 text-xs px-2 py-1"
        >
          Después
        </button>
        <button
          onClick={install}
          className="bg-white text-teal-700 font-semibold text-sm px-4 py-2 rounded-lg"
        >
          Instalar
        </button>
      </div>
    </div>
  );
};
```

---

## 6. Icons and Splash Screens

### Icon Generation

Generate from a single 1024×1024 source SVG:

```bash
# Install sharp-cli
npm install -g sharp-cli

# Generate all sizes
SOURCE="src/assets/icon-source-1024.png"
for size in 72 96 128 144 152 192 384 512; do
  sharp resize $size $size --input "$SOURCE" \
    --output "public/icons/icon-${size}x${size}.png"
done

# Maskable icons (with safe zone padding — 40px inset)
for size in 192 512; do
  sharp resize $((size - 80)) $((size - 80)) --input "$SOURCE" \
    | sharp extend --top 40 --bottom 40 --left 40 --right 40 --background '#0F766E' \
    --output "public/icons/icon-maskable-${size}x${size}.png"
done
```

### iOS-Specific Meta Tags

```html
<!-- public/index.html or _document.tsx -->
<head>
  <!-- iOS PWA support -->
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="DentalOS">

  <!-- iOS icons (Safari ignores manifest icons) -->
  <link rel="apple-touch-icon" sizes="152x152" href="/icons/icon-152x152.png">
  <link rel="apple-touch-icon" sizes="144x144" href="/icons/icon-144x144.png">
  <link rel="apple-touch-icon" sizes="120x120" href="/icons/icon-128x128.png">

  <!-- Splash screens (iOS) -->
  <link rel="apple-touch-startup-image"
        media="(device-width: 390px) and (device-height: 844px)"
        href="/splashscreens/iphone12-splash.png">
  <link rel="apple-touch-startup-image"
        media="(device-width: 768px) and (device-height: 1024px)"
        href="/splashscreens/ipad-splash.png">

  <!-- Theme color (Android Chrome) -->
  <meta name="theme-color" content="#0F766E">
  <!-- Dark mode -->
  <meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0F766E">

  <!-- Manifest link -->
  <link rel="manifest" href="/manifest.json">
</head>
```

### Splash Screen Generation

```bash
# Generate iOS splash screens
for device in iphone12 iphone13 iphone14 ipad ipad-pro; do
  node scripts/generate-splash.js $device
done
```

Splash screens use the DentalOS teal background with centered logo — matching the manifest `background_color` and `theme_color` for seamless launch.

---

## 7. PWA Audit Checklist (Lighthouse)

Target score: 95+ on Lighthouse PWA audit.

### Required Criteria

- [ ] Loads on HTTPS (always true — Hetzner LB enforces HTTPS)
- [ ] Has a `<meta name="viewport">` tag with `width=device-width`
- [ ] Has Web App Manifest with `name`, `short_name`, `start_url`, `icons`
- [ ] Icons include 192px and 512px maskable variants
- [ ] `theme_color` matches `<meta name="theme-color">`
- [ ] Service worker registered and activated
- [ ] App responds with 200 when offline (app shell cached)
- [ ] Pages are redirected to HTTPS
- [ ] Content is sized correctly for viewport (no horizontal scroll)
- [ ] Tap targets are sized correctly (min 48×48px touch target)

### Performance Targets (Lighthouse)

| Metric | Target |
|--------|--------|
| Performance | 90+ |
| Accessibility | 90+ |
| Best Practices | 90+ |
| SEO | 80+ (internal app, not public) |
| PWA | 95+ |

---

## 8. Update Flow

When a new version is deployed, the service worker needs to update:

```javascript
// src/hooks/useServiceWorkerUpdate.ts

export function useServiceWorkerUpdate() {
  const [updateAvailable, setUpdateAvailable] = useState(false);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    navigator.serviceWorker.ready.then((registration) => {
      registration.addEventListener("updatefound", () => {
        const newWorker = registration.installing;
        newWorker?.addEventListener("statechange", () => {
          if (
            newWorker.state === "installed" &&
            navigator.serviceWorker.controller
          ) {
            setUpdateAvailable(true);
          }
        });
      });
    });
  }, []);

  const applyUpdate = () => {
    navigator.serviceWorker.controller?.postMessage({ type: "SKIP_WAITING" });
    window.location.reload();
  };

  return { updateAvailable, applyUpdate };
}
```

### Update Banner UI

```typescript
export const UpdateBanner = () => {
  const { updateAvailable, applyUpdate } = useServiceWorkerUpdate();

  if (!updateAvailable) return null;

  return (
    <div className="fixed top-0 left-0 right-0 bg-blue-600 text-white px-4 py-3 flex items-center justify-between z-50">
      <p className="text-sm">
        Nueva versión de DentalOS disponible.
      </p>
      <button
        onClick={applyUpdate}
        className="bg-white text-blue-600 text-sm font-medium px-4 py-1.5 rounded-md ml-4"
      >
        Actualizar
      </button>
    </div>
  );
};
```

---

## 9. Environment Variables

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | VAPID public key for push subscriptions |
| `VAPID_PRIVATE_KEY` | VAPID private key (backend only) |
| `VAPID_CONTACT_EMAIL` | Contact email for VAPID claims |
| `NEXT_PUBLIC_APP_VERSION` | App version string for SW cache naming |

---

## Out of Scope

- Native iOS/Android app (this is PWA-only — no React Native)
- Background fetch for large file downloads
- Periodic Background Sync (browser support limited)
- Notification action buttons beyond default tap-to-open
- Rich notifications with inline reply
- Push notification grouping/threading

---

## Acceptance Criteria

**This spec is complete when:**

- [ ] Lighthouse PWA audit scores 95+ in production
- [ ] App installs on Android Chrome via install prompt
- [ ] App installs on iOS Safari via "Add to Home Screen"
- [ ] Installed app shows teal splash screen with DentalOS logo
- [ ] App shell loads from cache (verified by disabling network in DevTools)
- [ ] Push notification received and displayed when app is closed
- [ ] Notification tap opens correct page in app
- [ ] Update banner appears when new version deployed
- [ ] Install prompt appears after 3rd visit (not before)
- [ ] Maskable icons display correctly on Android home screen (no white corners)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
