"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { EPSClaimForm } from "@/components/billing/eps-claim-form";
import { useCreateEPSClaim } from "@/lib/hooks/use-eps-claims";
import type { EPSClaimCreate } from "@/lib/hooks/use-eps-claims";

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Create new EPS claim page — renders the EPSClaimForm and redirects to the
 * claims list on successful submission.
 */
export default function NewEPSClaimPage() {
  const router = useRouter();
  const { mutate: createClaim, isPending } = useCreateEPSClaim();

  function handleSubmit(data: EPSClaimCreate) {
    createClaim(data, {
      onSuccess: () => {
        router.push("/billing/eps-claims");
      },
    });
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link
          href="/billing/eps-claims"
          className="flex items-center gap-1 text-[hsl(var(--muted-foreground))] hover:text-foreground transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Reclamaciones EPS
        </Link>
        <span className="text-[hsl(var(--muted-foreground))]">/</span>
        <span className="text-foreground font-medium">Nueva reclamación</span>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-lg font-semibold text-foreground">
          Nueva reclamación EPS
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
          Registra una reclamación de servicios de salud para enviar a la EPS.
        </p>
      </div>

      {/* Form card */}
      <Card>
        <CardHeader>
          <CardTitle>Datos de la reclamación</CardTitle>
          <CardDescription>
            Completa la información del paciente, la EPS y los procedimientos
            realizados. La reclamación se creará como borrador.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EPSClaimForm onSubmit={handleSubmit} isLoading={isPending} />
        </CardContent>
      </Card>
    </div>
  );
}
