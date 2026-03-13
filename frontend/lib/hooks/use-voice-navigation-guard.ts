"use client";

import * as React from "react";
import { useVoiceStore } from "@/lib/stores/voice-store";

const WARNING_MESSAGE = "Tiene una sesion de voz activa. Los datos de grabacion se perderan.";

/**
 * Warns the user before navigating away or closing the tab during an active voice session.
 * Uses both `beforeunload` and `pagehide` events for cross-browser coverage.
 *
 * - `beforeunload`: works on most desktop browsers
 * - `pagehide`: more reliable on iOS Safari (which may skip beforeunload)
 */
export function useVoiceNavigationGuard() {
  const phase = useVoiceStore((s) => s.phase);
  const isActive = phase === "recording" || phase === "processing" || phase === "reviewing";

  React.useEffect(() => {
    if (!isActive) return;

    function handleBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault();
      // Modern browsers ignore custom messages but returnValue is still needed
      e.returnValue = WARNING_MESSAGE;
    }

    function handlePageHide(e: PageTransitionEvent) {
      // On iOS Safari, pagehide fires reliably when tab is closed or
      // app is backgrounded. If persisted=false, the page is being discarded.
      if (!e.persisted) {
        // Best-effort: navigator.sendBeacon is unavailable for blobs, but the
        // IndexedDB persistence layer (Layer 1) has already saved the chunks.
        // This event is a signal — the real protection is in IDB + recovery hook.
      }
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    window.addEventListener("pagehide", handlePageHide);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [isActive]);
}
