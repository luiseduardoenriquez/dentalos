"use client";

import { X, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useInstallPrompt } from "@/lib/hooks/use-pwa-install";

/**
 * PWA install prompt banner.
 * Shows a dismissible banner when the app can be installed.
 * Appears at the bottom of the viewport on mobile/tablet.
 * Only shows after 3 visits; dismiss persists across sessions.
 */
export function PwaInstallBanner() {
  const { canInstall, promptInstall, dismiss } = useInstallPrompt();

  if (!canInstall) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 p-4 sm:p-6 pointer-events-none">
      <div className="mx-auto max-w-lg pointer-events-auto">
        <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-lg">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30">
            <Download className="h-5 w-5 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground">
              Instalar DentalOS
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Accede más rápido desde tu pantalla de inicio.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button size="sm" className="h-8 text-xs" onClick={promptInstall}>
              Instalar
            </Button>
            <button
              onClick={dismiss}
              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              aria-label="Cerrar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
