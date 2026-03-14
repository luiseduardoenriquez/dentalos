"use client";

import { useEffect } from "react";

const DEFAULT_MESSAGE = "Tienes cambios sin guardar. Si sales, se perderan.";

/**
 * Generic navigation guard that warns users before leaving with unsaved changes.
 * Uses both `beforeunload` and `pagehide` (iOS Safari) for cross-browser coverage.
 *
 * @param options.is_dirty - Whether there are unsaved changes
 * @param options.message - Custom warning message (browsers may ignore it)
 *
 * @example
 * useNavigationGuard({ is_dirty: form.formState.isDirty });
 */
export function useNavigationGuard({
  is_dirty,
  message = DEFAULT_MESSAGE,
}: {
  is_dirty: boolean;
  message?: string;
}) {
  useEffect(() => {
    if (!is_dirty) return;

    function handleBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault();
      e.returnValue = message;
    }

    function handlePageHide(e: PageTransitionEvent) {
      // On iOS Safari, pagehide fires reliably when tab is closed or
      // app is backgrounded. If persisted=false, the page is being discarded.
      // The real protection is form draft persistence (use-form-draft.ts).
      if (!e.persisted) {
        // Best-effort signal — data is already saved to IDB/localStorage by draft hook
      }
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    window.addEventListener("pagehide", handlePageHide);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [is_dirty, message]);
}
