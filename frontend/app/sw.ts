/// <reference no-default-lib="true" />
/// <reference lib="esnext" />
/// <reference lib="webworker" />
import { defaultCache } from "@serwist/turbopack/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { Serwist, BackgroundSyncPlugin, NetworkOnly } from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

// Background sync for voice uploads — progressive enhancement (Chrome/Edge only).
// On unsupported browsers this is harmlessly ignored; IndexedDB + recovery hook
// provide the fallback.
const voiceUploadSyncPlugin = new BackgroundSyncPlugin("voice-uploads", {
  maxRetentionTime: 24 * 60, // 24 hours in minutes
});

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: false,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    ...defaultCache,
    {
      // Match voice upload POST requests for background sync retry
      method: "POST" as const,
      matcher: ({ url }) =>
        url.pathname.match(/\/voice\/sessions\/[^/]+\/upload$/) !== null,
      handler: new NetworkOnly({
        plugins: [voiceUploadSyncPlugin],
      }),
    },
  ],
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

// Listen for SKIP_WAITING message from UpdateBanner
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

serwist.addEventListeners();
