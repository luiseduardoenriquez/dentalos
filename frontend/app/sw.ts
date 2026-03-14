/// <reference no-default-lib="true" />
/// <reference lib="esnext" />
/// <reference lib="webworker" />
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { CacheFirst, NetworkFirst, NetworkOnly, Serwist, StaleWhileRevalidate, ExpirationPlugin } from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

// ─── Background Sync Queue (IDB-backed) ──────────────────────────────────────

const SYNC_QUEUE_DB = "dentalos-sw-sync";
const SYNC_QUEUE_STORE = "pending_requests";

function openSyncDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(SYNC_QUEUE_DB, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(SYNC_QUEUE_STORE)) {
        db.createObjectStore(SYNC_QUEUE_STORE, { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function queueFailedRequest(url: string, method: string, body: string | null, headers: Record<string, string>) {
  const db = await openSyncDb();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(SYNC_QUEUE_STORE, "readwrite");
    tx.objectStore(SYNC_QUEUE_STORE).add({
      url,
      method,
      body,
      headers,
      queued_at: Date.now(),
    });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

interface QueuedRequest {
  id: number;
  url: string;
  method: string;
  body: string | null;
  headers: Record<string, string>;
  queued_at: number;
}

async function getQueuedRequests(): Promise<QueuedRequest[]> {
  const db = await openSyncDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SYNC_QUEUE_STORE, "readonly");
    const req = tx.objectStore(SYNC_QUEUE_STORE).getAll();
    req.onsuccess = () => resolve(req.result as QueuedRequest[]);
    req.onerror = () => reject(req.error);
  });
}

async function removeQueuedRequest(id: number) {
  const db = await openSyncDb();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(SYNC_QUEUE_STORE, "readwrite");
    tx.objectStore(SYNC_QUEUE_STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function processSyncQueue() {
  const requests = await getQueuedRequests();
  let synced = 0;

  for (const req of requests) {
    try {
      const response = await fetch(req.url, {
        method: req.method,
        body: req.body,
        headers: req.headers,
        credentials: "include",
      });
      if (response.ok || (response.status >= 400 && response.status < 500)) {
        // Success or client error (don't retry 4xx)
        await removeQueuedRequest(req.id);
        synced++;
      }
      // 5xx: leave in queue for next retry
    } catch {
      // Network error: leave in queue
    }
  }

  // Notify clients
  if (synced > 0) {
    const clients = await self.clients.matchAll({ type: "window" });
    clients.forEach((client) => {
      client.postMessage({ type: "SYNC_COMPLETE", count: synced });
    });
  }
}

// ─── Runtime Caching Rules ────────────────────────────────────────────────────

const API_BASE = "/api/v1";

const runtimeCaching = [
  // Auth endpoints: NEVER cache
  {
    matcher: ({ url }: { url: URL }) => url.pathname.startsWith(`${API_BASE}/auth/`),
    handler: new NetworkOnly(),
  },
  // Clinical API reads: StaleWhileRevalidate
  {
    matcher: ({ request, url }: { request: Request; url: URL }) => {
      if (request.method !== "GET") return false;
      const clinicalPaths = ["/patients", "/odontogram", "/appointments", "/clinical-records", "/catalog"];
      return clinicalPaths.some((p) => url.pathname.includes(p));
    },
    handler: new StaleWhileRevalidate({
      cacheName: "dentalos-api-reads",
      plugins: [
        new ExpirationPlugin({ maxEntries: 300, maxAgeSeconds: 7 * 24 * 60 * 60 }),
      ],
    }),
  },
  // Navigation: NetworkFirst with timeout + cache fallback
  {
    matcher: ({ request }: { request: Request }) => request.destination === "document",
    handler: new NetworkFirst({
      cacheName: "dentalos-pages",
      networkTimeoutSeconds: 5,
      plugins: [
        new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 7 * 24 * 60 * 60 }),
      ],
    }),
  },
  // Images: CacheFirst (30 days)
  {
    matcher: ({ request }: { request: Request }) =>
      request.destination === "image",
    handler: new CacheFirst({
      cacheName: "dentalos-images",
      plugins: [
        new ExpirationPlugin({ maxEntries: 200, maxAgeSeconds: 30 * 24 * 60 * 60 }),
      ],
    }),
  },
];

// ─── Serwist Instance ─────────────────────────────────────────────────────────

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: false,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching,
  fallbacks: {
    entries: [
      {
        url: "/offline.html",
        matcher({ request }) {
          return request.destination === "document";
        },
      },
    ],
  },
});

// ─── Write Interception ───────────────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only intercept mutations to API (not auth)
  if (
    !["POST", "PUT", "DELETE"].includes(request.method) ||
    !url.pathname.startsWith(API_BASE) ||
    url.pathname.startsWith(`${API_BASE}/auth/`)
  ) {
    return; // Let serwist handle it
  }

  event.respondWith(
    (async () => {
      try {
        const response = await fetch(request.clone());
        return response;
      } catch {
        // Network failure — queue for background sync
        const body = await request.clone().text();
        const headers: Record<string, string> = {};
        request.headers.forEach((value, key) => {
          headers[key] = value;
        });

        await queueFailedRequest(request.url, request.method, body, headers);

        // Respond with 202 so the app knows it's queued
        return new Response(
          JSON.stringify({
            status: "queued_offline",
            message: "Guardado localmente. Se sincronizara al reconectar.",
          }),
          {
            status: 202,
            headers: { "Content-Type": "application/json" },
          },
        );
      }
    })(),
  );
});

// ─── Message Handlers ─────────────────────────────────────────────────────────

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
  if (event.data?.type === "PROCESS_SYNC_QUEUE") {
    processSyncQueue();
  }
});

// ─── Background Sync (where supported) ───────────────────────────────────────

self.addEventListener("sync", (event: Event) => {
  const syncEvent = event as ExtendableEvent & { tag: string };
  if (syncEvent.tag === "dentalos-sync") {
    (syncEvent as ExtendableEvent).waitUntil(processSyncQueue());
  }
});

// ─── Fallback: process queue on activation and periodically ──────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(processSyncQueue());
});

serwist.addEventListeners();
