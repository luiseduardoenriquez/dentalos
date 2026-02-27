"use client";

import * as React from "react";
import { useVoiceStore } from "@/lib/stores/voice-store";

/**
 * Warns the user before navigating away or closing the tab during an active voice session.
 * Uses the `beforeunload` event to show a browser-native confirmation dialog.
 */
export function useVoiceNavigationGuard() {
  const phase = useVoiceStore((s) => s.phase);
  const isActive = phase === "recording" || phase === "processing" || phase === "reviewing";

  React.useEffect(() => {
    if (!isActive) return;

    function handleBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault();
      // Modern browsers ignore custom messages but returnValue is still needed
      e.returnValue = "Tiene una sesion de voz activa. Los datos de grabacion se perderan.";
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isActive]);
}
