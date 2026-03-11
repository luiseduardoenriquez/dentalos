"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSwUpdate } from "@/lib/hooks/use-sw-update";

/**
 * Banner shown when a new service worker version is available.
 * Fixed to the top of the viewport with primary-600 background.
 */
export function UpdateBanner() {
  const { updateAvailable, applyUpdate } = useSwUpdate();

  if (!updateAvailable) return null;

  return (
    <div className="fixed top-0 inset-x-0 z-50 bg-primary-600 text-white">
      <div className="flex items-center justify-center gap-3 px-4 py-2 text-sm">
        <RefreshCw className="h-4 w-4 animate-spin" />
        <span>Nueva versión de DentalOS disponible</span>
        <Button
          size="sm"
          variant="outline"
          className="h-7 border-white/40 bg-white/10 text-white hover:bg-white/20 text-xs"
          onClick={applyUpdate}
        >
          Actualizar
        </Button>
      </div>
    </div>
  );
}
