# Offline Sync Strategy Spec

> **Spec ID:** I-18
> **Status:** Draft — Post-MVP (Sprint 13+)
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Offline-first architecture enabling DentalOS to function when internet connectivity is unreliable — a common scenario in Colombian dental clinics. Uses Service Workers for asset caching, IndexedDB for local data storage, and a background sync queue for write operations. The server is authoritative (last-write-wins with server timestamp for most resources; merge logic for concurrent odontogram edits). Bandwidth-aware sync applies full sync on WiFi and delta sync on cellular.

**Domain:** infra / frontend

**Priority:** Medium — Post-MVP (Sprint 13+)

**Dependencies:** ADR-005 (PWA architecture), I-19 (pwa-configuration), frontend domain, appointments domain, patients domain, odontogram domain

---

## 1. Why Offline-First?

### LATAM Context

- Internet outages are frequent in Colombian cities and rural clinics (1–6 hours per day)
- Mobile data is often metered; clinics on mobile hotspot
- Dentists use tablets or mobile devices in the operatory (not always near WiFi router)
- North Star: "Si no es más rápido que el papel, fallamos" — offline capability is critical

### What Must Work Offline

| Feature | Offline Support | Notes |
|---------|----------------|-------|
| Odontogram viewing | Yes | Read cached state |
| Odontogram editing | Yes | Queue changes, sync on reconnect |
| Appointment list (today) | Yes | Read cached |
| Patient basic info | Yes | Read cached |
| Clinical record creation | Yes | Queue, sync on reconnect |
| Prescriptions creation | Yes | Queue, sync on reconnect |
| Photos upload | Yes | Queue, upload on reconnect |
| Invoices/billing | No | Requires server for DIAN integration |
| Appointments scheduling | Partial | Read only; new bookings require online |
| Reports / analytics | No | Always requires live data |

---

## 2. Architecture Overview

```
Browser (Next.js PWA)
├── Service Worker (Workbox)
│   ├── Precache: app shell, critical assets
│   ├── Runtime cache: API responses (stale-while-revalidate)
│   └── Background sync: pending writes
│
├── IndexedDB (via Dexie.js)
│   ├── patients (basic info, last 200 active patients)
│   ├── odontogram_states (current state per patient)
│   ├── appointments (today + tomorrow)
│   ├── clinical_records (last 7 days)
│   ├── pending_sync_queue (writes queued while offline)
│   └── sync_metadata (last sync timestamps)
│
└── Online/Offline Manager
    ├── navigator.onLine listener
    ├── Periodic sync check (30s)
    └── Sync status indicator (green/yellow/red)

DentalOS API (FastAPI)
└── Sync endpoints:
    ├── GET /api/v1/sync/delta?since={timestamp}
    ├── POST /api/v1/sync/batch (bulk write processing)
    └── GET /api/v1/sync/full (initial/forced full sync)
```

---

## 3. Service Worker — Workbox Configuration

### Service Worker Setup

```javascript
// public/sw.js — compiled from src/service-worker.ts

import { precacheAndRoute, cleanupOutdatedCaches } from "workbox-precaching";
import { registerRoute } from "workbox-routing";
import {
  StaleWhileRevalidate,
  NetworkFirst,
  CacheFirst,
  NetworkOnly,
} from "workbox-strategies";
import { BackgroundSyncPlugin } from "workbox-background-sync";
import { ExpirationPlugin } from "workbox-expiration";
import { Queue } from "workbox-background-sync";

// App shell precaching (injected by Workbox at build time)
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

// === Caching Strategies ===

// 1. Static assets: CacheFirst (immutable, versioned)
registerRoute(
  ({ request }) =>
    request.destination === "script" ||
    request.destination === "style" ||
    request.destination === "font",
  new CacheFirst({
    cacheName: "static-assets",
    plugins: [
      new ExpirationPlugin({ maxAgeSeconds: 30 * 24 * 60 * 60 }), // 30 days
    ],
  })
);

// 2. Read API endpoints: StaleWhileRevalidate
// These are safe to show cached data while fetching fresh
registerRoute(
  ({ url }) =>
    url.pathname.startsWith("/api/v1/") &&
    !WRITE_API_PATTERNS.some((p) => url.pathname.match(p)),
  new StaleWhileRevalidate({
    cacheName: "api-reads",
    plugins: [
      new ExpirationPlugin({
        maxEntries: 200,
        maxAgeSeconds: 7 * 24 * 60 * 60,  // 7 days
      }),
    ],
  })
);

// 3. Mutation API endpoints: NetworkFirst with offline queue
const syncQueue = new Queue("pending-writes", {
  onSync: async ({ queue }) => {
    let entry;
    while ((entry = await queue.shiftRequest())) {
      try {
        await fetch(entry.request.clone());
      } catch (err) {
        await queue.unshiftRequest(entry);
        throw err;
      }
    }
  },
  maxRetentionTime: 24 * 60,  // 24 hours
});

const WRITE_API_PATTERNS = [
  /\/api\/v1\/odontogram/,
  /\/api\/v1\/clinical-records/,
  /\/api\/v1\/appointments/,
  /\/api\/v1\/prescriptions/,
  /\/api\/v1\/patients\/.*\/update/,
];

// Write routes: NetworkFirst, queue if offline
registerRoute(
  ({ url, request }) =>
    WRITE_API_PATTERNS.some((p) => url.pathname.match(p)) &&
    ["POST", "PUT", "PATCH", "DELETE"].includes(request.method),
  async ({ request }) => {
    try {
      return await fetch(request.clone());
    } catch (err) {
      // Network unavailable — add to background sync queue
      await syncQueue.pushRequest({ request });
      // Return synthetic offline response
      return new Response(
        JSON.stringify({
          status: "queued_offline",
          message: "Guardado localmente. Se sincronizará cuando haya conexión.",
        }),
        {
          status: 202,
          headers: { "Content-Type": "application/json" },
        }
      );
    }
  }
);

// 4. Images: CacheFirst with longer expiry
registerRoute(
  ({ request }) => request.destination === "image",
  new CacheFirst({
    cacheName: "images",
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 30 * 24 * 60 * 60,
      }),
    ],
  })
);

// 5. Navigation: NetworkFirst with app shell fallback
registerRoute(
  ({ request }) => request.mode === "navigate",
  new NetworkFirst({
    cacheName: "pages",
    networkTimeoutSeconds: 5,
    plugins: [
      new ExpirationPlugin({ maxAgeSeconds: 7 * 24 * 60 * 60 }),
    ],
  })
);

// Offline fallback page
self.addEventListener("fetch", (event) => {
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/offline.html"))
    );
  }
});
```

---

## 4. IndexedDB Schema (Dexie.js)

```typescript
// src/db/offline-db.ts
import Dexie, { Table } from "dexie";

export interface OfflinePatient {
  id: string;
  tenant_id: string;
  first_name: string;
  last_name: string;
  document_number: string;
  phone?: string;
  birth_date?: string;
  last_visit_date?: string;
  synced_at: number;  // timestamp
}

export interface OfflineOdontogramState {
  patient_id: string;
  tenant_id: string;
  state: Record<string, any>;  // Full odontogram state
  version: number;
  synced_at: number;
  local_modified_at?: number;  // Set when edited offline
}

export interface OfflineAppointment {
  id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string;
  scheduled_at: number;    // Unix timestamp
  duration_minutes: number;
  appointment_type: string;
  status: string;
  synced_at: number;
}

export interface OfflineClinicalRecord {
  id: string;
  patient_id: string;
  type: string;
  notes?: string;
  created_at: number;
  synced_at: number;
  local_modified_at?: number;
}

export interface PendingSyncItem {
  id?: number;              // Auto-increment (IndexedDB key)
  operation: string;        // "create" | "update" | "delete"
  resource: string;         // "odontogram" | "clinical_record" | "appointment"
  resource_id: string;      // UUID
  payload: Record<string, any>;
  queued_at: number;        // Unix timestamp
  attempt_count: number;
  last_attempt_at?: number;
  error?: string;
}

export interface SyncMetadata {
  resource: string;
  last_full_sync: number;
  last_delta_sync: number;
  server_timestamp: string;
}

class DentalOSOfflineDB extends Dexie {
  patients!: Table<OfflinePatient>;
  odontogram_states!: Table<OfflineOdontogramState>;
  appointments!: Table<OfflineAppointment>;
  clinical_records!: Table<OfflineClinicalRecord>;
  pending_sync_queue!: Table<PendingSyncItem>;
  sync_metadata!: Table<SyncMetadata>;

  constructor() {
    super("DentalOSOfflineDB");
    this.version(1).stores({
      patients: "id, tenant_id, last_name, document_number, synced_at",
      odontogram_states: "patient_id, synced_at",
      appointments: "id, patient_id, doctor_id, scheduled_at, synced_at",
      clinical_records: "id, patient_id, created_at, synced_at",
      pending_sync_queue: "++id, resource, resource_id, queued_at",
      sync_metadata: "resource",
    });
  }
}

export const offlineDb = new DentalOSOfflineDB();
```

---

## 5. Sync Engine

### Delta Sync API Endpoint

```python
@router.get("/api/v1/sync/delta")
async def sync_delta(
    since: datetime,
    resources: str = Query(default="all"),  # Comma-separated: patients,appointments,odontogram
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delta sync endpoint.
    Returns all records modified after 'since' timestamp.
    Designed for bandwidth efficiency — only changed records.
    """
    resource_list = resources.split(",") if resources != "all" else [
        "patients", "appointments", "odontogram", "clinical_records"
    ]

    response_data = {
        "server_timestamp": datetime.utcnow().isoformat(),
        "changes": {},
    }

    if "patients" in resource_list:
        response_data["changes"]["patients"] = await get_patients_delta(
            session, since, limit=200
        )

    if "appointments" in resource_list:
        # Only sync today + tomorrow
        tomorrow = datetime.utcnow() + timedelta(days=1)
        response_data["changes"]["appointments"] = await get_appointments_delta(
            session, since,
            date_from=datetime.utcnow().replace(hour=0, minute=0),
            date_to=tomorrow.replace(hour=23, minute=59),
        )

    if "odontogram" in resource_list:
        response_data["changes"]["odontogram"] = await get_odontogram_delta(
            session, since
        )

    if "clinical_records" in resource_list:
        # Only last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        response_data["changes"]["clinical_records"] = await get_clinical_records_delta(
            session, max(since, week_ago)
        )

    return response_data
```

### Batch Write Endpoint

```python
@router.post("/api/v1/sync/batch")
async def sync_batch(
    batch: SyncBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Process a batch of write operations queued while offline.
    Returns per-operation results (success/conflict/error).
    """
    results = []

    for operation in batch.operations:
        try:
            result = await process_sync_operation(
                session, current_user, operation
            )
            results.append({
                "operation_id": operation.local_id,
                "status": "success",
                "server_id": result.get("id"),
            })
        except ConflictError as exc:
            results.append({
                "operation_id": operation.local_id,
                "status": "conflict",
                "server_data": exc.server_data,
                "conflict_type": exc.conflict_type,
            })
        except Exception as exc:
            results.append({
                "operation_id": operation.local_id,
                "status": "error",
                "error": str(exc),
            })

    return {
        "processed": len(batch.operations),
        "results": results,
        "server_timestamp": datetime.utcnow().isoformat(),
    }
```

---

## 6. Conflict Resolution

### Conflict Resolution Strategy

| Resource | Strategy | Rationale |
|----------|----------|-----------|
| Appointments | Last-write-wins (server timestamp) | Simple scheduling data |
| Patient info | Last-write-wins (server timestamp) | Demographics rarely concurrent |
| Clinical records | Last-write-wins (server timestamp) | Each dentist works on own records |
| Odontogram | Merge (surface-level granularity) | Multiple updates to different teeth |
| Prescriptions | Last-write-wins | Doctor creates prescription, no concurrent edit |

### Odontogram Merge Logic

The odontogram is the most complex resource because multiple teeth may be edited concurrently:

```typescript
// src/sync/conflict-resolution.ts

interface OdontogramSurfaceState {
  tooth: number;       // FDI notation: 11-48
  surface: string;     // O, V, L, M, D, C
  condition: string;   // healthy, caries, filled, crown, etc.
  updated_at: string;
}

function mergeOdontogramStates(
  clientState: OdontogramSurfaceState[],
  serverState: OdontogramSurfaceState[],
): OdontogramSurfaceState[] {
  /**
   * Merge two odontogram states at the surface level.
   * For each tooth+surface combination, the entry with the later
   * updated_at timestamp wins.
   */
  const merged = new Map<string, OdontogramSurfaceState>();

  // Load server state first
  for (const state of serverState) {
    const key = `${state.tooth}:${state.surface}`;
    merged.set(key, state);
  }

  // Apply client changes where client is newer
  for (const state of clientState) {
    const key = `${state.tooth}:${state.surface}`;
    const serverEntry = merged.get(key);
    if (
      !serverEntry ||
      new Date(state.updated_at) > new Date(serverEntry.updated_at)
    ) {
      merged.set(key, state);
    }
  }

  return Array.from(merged.values());
}
```

### Conflict UI

When a conflict cannot be automatically resolved (e.g., a clinical note was edited both locally and on the server):

```typescript
// src/components/sync/ConflictResolutionModal.tsx

const ConflictResolutionModal = ({
  conflict,
  onResolve,
}: {
  conflict: SyncConflict;
  onResolve: (choice: "local" | "server") => void;
}) => {
  return (
    <Modal>
      <h2>Conflicto de sincronización</h2>
      <p>
        Este registro fue modificado en otro dispositivo mientras estabas sin conexión.
      </p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h3>Tu versión (offline)</h3>
          <pre>{JSON.stringify(conflict.localData, null, 2)}</pre>
          <button onClick={() => onResolve("local")}>
            Usar mi versión
          </button>
        </div>
        <div>
          <h3>Versión del servidor</h3>
          <pre>{JSON.stringify(conflict.serverData, null, 2)}</pre>
          <button onClick={() => onResolve("server")}>
            Usar versión del servidor
          </button>
        </div>
      </div>
    </Modal>
  );
};
```

---

## 7. Sync Status UI

```typescript
// src/components/sync/SyncStatusIndicator.tsx

type SyncStatus = "synced" | "syncing" | "pending" | "offline" | "error";

const STATUS_CONFIG = {
  synced: { color: "green", icon: "✓", label: "Sincronizado" },
  syncing: { color: "blue", icon: "↻", label: "Sincronizando..." },
  pending: { color: "yellow", icon: "⏱", label: "Cambios pendientes" },
  offline: { color: "orange", icon: "⚡", label: "Sin conexión" },
  error: { color: "red", icon: "!", label: "Error de sincronización" },
};

export const SyncStatusIndicator = () => {
  const { status, pendingCount } = useSyncStatus();
  const config = STATUS_CONFIG[status];

  return (
    <div className={`flex items-center gap-2 text-${config.color}-600`}>
      <span>{config.icon}</span>
      <span className="text-sm">{config.label}</span>
      {pendingCount > 0 && (
        <span className="text-xs bg-yellow-100 px-1 rounded">
          {pendingCount} pendiente{pendingCount > 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
};
```

---

## 8. Bandwidth-Aware Sync

```typescript
// src/sync/bandwidth-aware.ts

type ConnectionType = "wifi" | "cellular" | "unknown" | "offline";

function getConnectionType(): ConnectionType {
  if (!navigator.onLine) return "offline";

  const conn = (navigator as any).connection ||
                (navigator as any).mozConnection ||
                (navigator as any).webkitConnection;

  if (!conn) return "unknown";

  // 4G/WiFi: treat as WiFi for full sync
  if (conn.type === "wifi" || conn.effectiveType === "4g") return "wifi";
  // 2G/3G/metered: cellular — delta sync only
  if (conn.saveData || ["2g", "3g"].includes(conn.effectiveType)) return "cellular";

  return "unknown";
}

async function performSync(type: "full" | "delta" | "auto"): Promise<void> {
  const connection = getConnectionType();

  if (connection === "offline") {
    console.log("Offline — sync skipped");
    return;
  }

  const syncMode =
    type === "auto"
      ? connection === "wifi"
        ? "full"        // WiFi: full sync (all cached data refreshed)
        : "delta"       // Cellular: delta sync (only changed records)
      : type;

  const lastSyncTimestamp = await getSyncMetadata("last_sync");

  if (syncMode === "delta" && lastSyncTimestamp) {
    await deltaSyncAll(lastSyncTimestamp);
  } else {
    await fullSyncAll();
  }
}
```

### Sync Priority Order

When coming back online, sync in this priority order:

1. **Pending writes** (upload queued operations first — most critical)
2. **Clinical records** (highest clinical importance)
3. **Odontogram states** (clinical, but usually large)
4. **Appointments** (today + tomorrow)
5. **Patients** (basic info for today's schedule)
6. **Billing/invoices** (low priority for offline scenario)

---

## 9. Photo Upload Queue

Photos taken offline are stored as blob URLs in IndexedDB and uploaded when online:

```typescript
// src/sync/photo-queue.ts

interface PendingPhotoUpload {
  id?: number;
  file_type: string;
  patient_id: string;
  context: string;
  context_id: string;
  blob_data: Blob;
  filename: string;
  queued_at: number;
}

async function queuePhotoForUpload(
  fileType: string,
  patientId: string,
  context: string,
  contextId: string,
  file: File,
): Promise<void> {
  await offlineDb.pending_sync_queue.add({
    operation: "create",
    resource: "file",
    resource_id: crypto.randomUUID(),
    payload: {
      file_type: fileType,
      patient_id: patientId,
      context,
      context_id: contextId,
      filename: file.name,
      content_type: file.type,
    },
    queued_at: Date.now(),
    attempt_count: 0,
  });
}

// Worker processes photo queue on reconnect
async function processPhotoQueue(): Promise<void> {
  const pendingPhotos = await offlineDb.pending_sync_queue
    .where("resource")
    .equals("file")
    .toArray();

  for (const item of pendingPhotos) {
    try {
      // Get upload URL
      const { upload_url, file_id } = await apiClient.post("/files/upload-url", item.payload);
      // Upload photo
      await fetch(upload_url, { method: "PUT", body: item.payload.blob });
      // Confirm
      await apiClient.post(`/files/${file_id}/confirm`);
      // Remove from queue
      await offlineDb.pending_sync_queue.delete(item.id!);
    } catch (err) {
      item.attempt_count++;
      await offlineDb.pending_sync_queue.put(item);
    }
  }
}
```

---

## 10. Progressive Enhancement Approach

Offline support is built as a progressive enhancement — the app works fully online, and offline capability is layered on top:

1. **Layer 1 — Always works:** Core UI renders from cached app shell
2. **Layer 2 — Most data offline:** Cached data shown from IndexedDB
3. **Layer 3 — Full offline writes:** Changes queued for sync
4. **Layer 4 — Smart conflict resolution:** Handles concurrent edits

Features that degrade gracefully offline:
- DIAN invoice generation → Disabled (shows message: "Requiere conexión")
- Patient portal → Disabled
- Analytics → Disabled
- WhatsApp/SMS → Queued, not sent until online

---

## Out of Scope

- Offline support for the patient portal (patients need online for payments)
- Peer-to-peer sync between devices
- Offline support for admin/superadmin functions
- CRDT (Conflict-free Replicated Data Types) — surface-level merge is sufficient
- Encrypted IndexedDB storage — deferred (OS-level encryption on device)

---

## Implementation Timeline

- **Sprint 13:** Service worker setup, IndexedDB schema, basic read caching
- **Sprint 14:** Write queue, delta sync API, background sync
- **Sprint 15:** Odontogram merge logic, conflict UI
- **Sprint 16:** Photo upload queue, bandwidth-aware sync, sync status indicator
- **Beta:** Test with clinics in areas with unreliable connectivity

---

## Acceptance Criteria

**This spec is complete when:**

- [ ] App shell loads from cache with no network (after first load)
- [ ] Odontogram displays cached state when offline
- [ ] Odontogram edits queued offline and synced on reconnect without data loss
- [ ] Today's appointments visible offline
- [ ] Last 7 days of clinical records accessible offline
- [ ] Conflict detected when same record edited on two devices simultaneously
- [ ] Sync status indicator shows offline/syncing/synced/pending states
- [ ] Bandwidth-aware: delta sync on cellular, full sync on WiFi
- [ ] Photos queued offline and uploaded on reconnect

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — post-MVP (Sprint 13+) |
