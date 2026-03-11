"use client";

import { useState, useEffect, useCallback } from "react";

/**
 * Detects when a new service worker version is available and
 * provides a function to apply the update (skip waiting + reload).
 */
export function useSwUpdate() {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    const handleRegistration = (registration: ServiceWorkerRegistration) => {
      // A new SW is already waiting (e.g. user returned to a stale tab)
      if (registration.waiting) {
        setWaitingWorker(registration.waiting);
        setUpdateAvailable(true);
      }

      // A new SW was found and is installing
      registration.addEventListener("updatefound", () => {
        const installing = registration.installing;
        if (!installing) return;

        installing.addEventListener("statechange", () => {
          if (installing.state === "installed" && navigator.serviceWorker.controller) {
            // New content is available; old SW still controls the page
            setWaitingWorker(installing);
            setUpdateAvailable(true);
          }
        });
      });
    };

    navigator.serviceWorker.ready.then(handleRegistration);

    // Reload when the new SW takes over
    let refreshing = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    });
  }, []);

  const applyUpdate = useCallback(() => {
    if (!waitingWorker) return;
    waitingWorker.postMessage({ type: "SKIP_WAITING" });
  }, [waitingWorker]);

  return { updateAvailable, applyUpdate };
}
