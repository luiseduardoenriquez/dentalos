"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import { useAuth } from "@/lib/hooks/use-auth";
import { useToast } from "@/lib/hooks/use-toast";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Sparkles, Loader2, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SuggestionItem {
  cups_code: string;
  cups_description: string;
  tooth_number: string | null;
  rationale: string;
  confidence: "high" | "medium" | "low";
  priority_order: number;
  estimated_cost: number;
}

interface AISuggestion {
  id: string;
  patient_id: string;
  doctor_id: string;
  suggestions: SuggestionItem[];
  model_used: string;
  status: string;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
}

export interface AISuggestButtonProps {
  patientId: string;
  onSuggestionGenerated?: (suggestion: AISuggestion) => void;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * AISuggestButton — Triggers AI-powered treatment suggestion generation.
 *
 * - Checks the `ai_treatment_advisor` feature flag before calling the API.
 * - If feature is disabled, shows an upsell tooltip.
 * - On 402 response, opens an upsell dialog.
 * - On success, calls `onSuggestionGenerated` with the full suggestion payload.
 */
export function AISuggestButton({
  patientId,
  onSuggestionGenerated,
  className,
}: AISuggestButtonProps) {
  const { has_feature } = useAuth();
  const { error: toastError } = useToast();
  const [upsellOpen, setUpsellOpen] = React.useState(false);

  const hasFeature = has_feature("ai_treatment_advisor");

  const mutation = useMutation({
    mutationFn: () =>
      apiPost<AISuggestion>("/treatment-plans/ai-suggest", {
        patient_id: patientId,
      }),
    onSuccess: (data) => {
      onSuggestionGenerated?.(data);
    },
    onError: (err: unknown) => {
      // Check for 402 Payment Required — upsell dialog
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 402) {
        setUpsellOpen(true);
        return;
      }

      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        (err instanceof Error ? err.message : null) ??
        "No se pudo generar las sugerencias. Inténtalo de nuevo.";

      toastError("Error al generar sugerencias", message);
    },
  });

  const handleClick = () => {
    if (!hasFeature) {
      // Feature gate — tooltip is shown, but also guard against programmatic calls
      return;
    }
    mutation.mutate();
  };

  const button = (
    <Button
      variant="default"
      size="sm"
      onClick={handleClick}
      disabled={mutation.isPending || !hasFeature}
      className={cn(
        "gap-1.5",
        !hasFeature && "cursor-not-allowed opacity-70",
        className,
      )}
      aria-label="Generar sugerencias de tratamiento con IA"
    >
      {mutation.isPending ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Generando sugerencias...
        </>
      ) : (
        <>
          {hasFeature ? (
            <Sparkles className="h-4 w-4" />
          ) : (
            <Lock className="h-4 w-4" />
          )}
          IA Sugerir
        </>
      )}
    </Button>
  );

  return (
    <>
      {/* Upsell tooltip when feature is not active */}
      {!hasFeature ? (
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              {/* Wrap in span so tooltip works on disabled buttons */}
              <span className="inline-flex">{button}</span>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-[260px]">
              <p className="text-xs text-center leading-snug">
                Activa el complemento de IA para obtener sugerencias de
                tratamiento
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ) : (
        button
      )}

      {/* Upsell dialog — shown on 402 response */}
      <Dialog open={upsellOpen} onOpenChange={setUpsellOpen}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary-600" />
              Complemento de IA
            </DialogTitle>
            <DialogDescription>
              El asesor de tratamiento con IA no está incluido en tu plan
              actual.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Con el complemento{" "}
              <span className="font-semibold text-foreground">
                AI Treatment Advisor
              </span>{" "}
              obtendrás:
            </p>
            <ul className="space-y-1.5 text-sm text-[hsl(var(--muted-foreground))]">
              <li className="flex items-start gap-2">
                <Sparkles className="h-3.5 w-3.5 text-primary-600 mt-0.5 shrink-0" />
                Sugerencias de procedimientos basadas en el historial clínico
              </li>
              <li className="flex items-start gap-2">
                <Sparkles className="h-3.5 w-3.5 text-primary-600 mt-0.5 shrink-0" />
                Nivel de confianza y justificación para cada sugerencia
              </li>
              <li className="flex items-start gap-2">
                <Sparkles className="h-3.5 w-3.5 text-primary-600 mt-0.5 shrink-0" />
                Creación de plan de tratamiento en un clic
              </li>
            </ul>
            <p className="text-sm font-medium text-foreground">
              Disponible desde{" "}
              <span className="text-primary-600">$10 USD/doctor/mes</span>
            </p>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setUpsellOpen(false)}
            >
              Ahora no
            </Button>
            <Button
              size="sm"
              onClick={() => {
                setUpsellOpen(false);
                // Redirect to settings/billing to upgrade
                if (typeof window !== "undefined") {
                  window.location.href = "/settings/billing";
                }
              }}
            >
              <Sparkles className="h-4 w-4" />
              Activar complemento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
