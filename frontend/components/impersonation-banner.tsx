"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldAlert, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useImpersonationStore } from "@/lib/hooks/use-impersonation";
import { useAuthStore } from "@/lib/hooks/use-auth";

/**
 * Fixed amber banner rendered at the top of the dashboard when
 * a superadmin is impersonating a clinic. Shows the clinic name
 * and an exit button that clears the impersonation session.
 */
export function ImpersonationBanner() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { impersonating, exit } = useImpersonationStore();
  const clinicName = useAuthStore((s) => s.tenant?.name);

  if (!impersonating) return null;

  function handleExit() {
    const returnPath = exit();
    useAuthStore.getState().clear_auth();
    queryClient.clear();
    router.replace(returnPath);
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between gap-3 bg-amber-500 px-4 py-2 text-amber-950 shadow-sm">
      <div className="flex items-center gap-2 text-sm font-medium">
        <ShieldAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>
          Modo impersonacion activo
          {clinicName ? ` \u2014 ${clinicName}` : ""}
        </span>
      </div>
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={handleExit}
        className="h-7 border-amber-700/40 bg-amber-400/50 text-amber-950 hover:bg-amber-400 hover:text-amber-950"
      >
        <LogOut className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
        Salir de impersonacion
      </Button>
    </div>
  );
}
