"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { AIConfidenceBadge } from "@/components/treatment-plans/ai-confidence-badge";
import {
  Sparkles,
  Loader2,
  X,
  Check,
  CheckSquare,
  Square,
  Bot,
  Coins,
  Hash,
  FileText,
} from "lucide-react";
import { formatCurrency, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SuggestionItem {
  cups_code: string;
  cups_description: string;
  tooth_number: string | null;
  rationale: string;
  confidence: "high" | "medium" | "low";
  priority_order: number;
  estimated_cost: number;
}

export interface AISuggestion {
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

interface CreatePlanResponse {
  id: string;
  patient_id: string;
  name: string;
  status: string;
}

export interface AISuggestionPanelProps {
  suggestion: AISuggestion;
  onClose: () => void;
  onPlanCreated?: (planId: string) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function TokenCountBadge({
  inputTokens,
  outputTokens,
}: {
  inputTokens: number;
  outputTokens: number;
}) {
  return (
    <Badge variant="outline" className="text-xs font-mono gap-1">
      <Bot className="h-3 w-3" />
      {(inputTokens + outputTokens).toLocaleString("es-CO")} tokens
    </Badge>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * AISuggestionPanel — Displays AI-generated treatment suggestions for clinical review.
 *
 * Each suggestion can be individually accepted or rejected before creating
 * a treatment plan. Requires at least one accepted item to enable plan creation.
 *
 * Flow:
 * 1. Renders the list of suggestions from the AI response.
 * 2. Doctor reviews and toggles each item (accept/reject).
 * 3. On "Crear plan de tratamiento":
 *    - POST /treatment-plans/ai-suggest/{id}/review  (saves accepted items)
 *    - POST /treatment-plans/ai-suggest/{id}/create-plan  (creates the plan)
 * 4. Calls onPlanCreated with the new plan ID on success.
 */
export function AISuggestionPanel({
  suggestion,
  onClose,
  onPlanCreated,
}: AISuggestionPanelProps) {
  const { success, error: toastError } = useToast();
  const queryClient = useQueryClient();

  // Set of accepted CUPS codes (by index to handle duplicates)
  const [acceptedIndices, setAcceptedIndices] = React.useState<Set<number>>(
    () => new Set(suggestion.suggestions.map((_, i) => i)),
  );

  const toggleItem = (index: number) => {
    setAcceptedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const rejectAll = () => setAcceptedIndices(new Set());
  const acceptAll = () =>
    setAcceptedIndices(new Set(suggestion.suggestions.map((_, i) => i)));

  const acceptedCount = acceptedIndices.size;
  const canCreatePlan = acceptedCount > 0;

  // ─── Review mutation ─────────────────────────────────────────────────────
  const reviewMutation = useMutation({
    mutationFn: (acceptedCupsCodes: string[]) =>
      apiPost<{ status: string }>(
        `/treatment-plans/ai-suggest/${suggestion.id}/review`,
        { accepted_cups_codes: acceptedCupsCodes },
      ),
  });

  // ─── Create plan mutation ─────────────────────────────────────────────────
  const createPlanMutation = useMutation({
    mutationFn: () =>
      apiPost<CreatePlanResponse>(
        `/treatment-plans/ai-suggest/${suggestion.id}/create-plan`,
      ),
    onSuccess: (plan) => {
      queryClient.invalidateQueries({
        queryKey: ["treatment_plans", suggestion.patient_id],
      });
      success(
        "Plan creado",
        "El plan de tratamiento fue creado a partir de las sugerencias de IA.",
      );
      onPlanCreated?.(plan.id);
      onClose();
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message ??
        (err instanceof Error ? err.message : null) ??
        "No se pudo crear el plan de tratamiento. Inténtalo de nuevo.";
      toastError("Error al crear plan", message);
    },
  });

  const handleCreatePlan = async () => {
    // Collect accepted CUPS codes by position
    const acceptedCupsCodes = suggestion.suggestions
      .filter((_, i) => acceptedIndices.has(i))
      .map((item) => item.cups_code);

    try {
      await reviewMutation.mutateAsync(acceptedCupsCodes);
      createPlanMutation.mutate();
    } catch {
      const message = "No se pudo registrar la revisión. Inténtalo de nuevo.";
      toastError("Error al revisar sugerencias", message);
    }
  };

  const isCreating = reviewMutation.isPending || createPlanMutation.isPending;

  return (
    <Card className="w-full border-primary-200 dark:border-primary-800 shadow-md">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles className="h-5 w-5 text-primary-600 shrink-0" />
            <CardTitle className="text-base truncate">
              Sugerencias de IA
            </CardTitle>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <TokenCountBadge
              inputTokens={suggestion.input_tokens}
              outputTokens={suggestion.output_tokens}
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-7 w-7 text-[hsl(var(--muted-foreground))] hover:text-foreground"
              aria-label="Cerrar panel de sugerencias"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <CardDescription className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1">
          <span className="font-mono text-xs">{suggestion.model_used}</span>
          <span>·</span>
          <span>
            {suggestion.suggestions.length} sugerencia
            {suggestion.suggestions.length !== 1 ? "s" : ""}
          </span>
          <span>·</span>
          <span className="text-primary-600 dark:text-primary-400 font-medium">
            {acceptedCount} seleccionada{acceptedCount !== 1 ? "s" : ""}
          </span>
        </CardDescription>
      </CardHeader>

      <Separator />

      {/* ─── Suggestion List ─────────────────────────────────────────────── */}
      <CardContent className="pt-4 pb-2">
        {suggestion.suggestions.length === 0 ? (
          <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-6">
            No se generaron sugerencias para este paciente.
          </p>
        ) : (
          <ul className="space-y-3">
            {suggestion.suggestions
              .sort((a, b) => a.priority_order - b.priority_order)
              .map((item, index) => {
                const isAccepted = acceptedIndices.has(index);
                return (
                  <li
                    key={`${item.cups_code}-${index}`}
                    className={cn(
                      "rounded-lg border p-3 transition-colors",
                      isAccepted
                        ? "border-primary-300 bg-primary-50/60 dark:border-primary-700 dark:bg-primary-900/20"
                        : "border-[hsl(var(--border))] bg-[hsl(var(--muted))]/30 opacity-60",
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {/* Toggle checkbox */}
                      <button
                        type="button"
                        onClick={() => toggleItem(index)}
                        className={cn(
                          "mt-0.5 shrink-0 rounded transition-colors",
                          "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-1",
                          isAccepted
                            ? "text-primary-600 dark:text-primary-400"
                            : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
                        )}
                        aria-label={
                          isAccepted
                            ? `Rechazar ${item.cups_description}`
                            : `Aceptar ${item.cups_description}`
                        }
                      >
                        {isAccepted ? (
                          <CheckSquare className="h-5 w-5" />
                        ) : (
                          <Square className="h-5 w-5" />
                        )}
                      </button>

                      {/* Content */}
                      <div className="flex-1 min-w-0 space-y-1.5">
                        {/* Title row */}
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-xs text-[hsl(var(--muted-foreground))] shrink-0">
                            {item.cups_code}
                          </span>
                          <span className="text-sm font-semibold text-foreground leading-tight">
                            {item.cups_description}
                          </span>
                        </div>

                        {/* Tooth + confidence + cost */}
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                          {item.tooth_number && (
                            <span className="inline-flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
                              <Hash className="h-3 w-3" />
                              Diente {item.tooth_number}
                            </span>
                          )}
                          <AIConfidenceBadge confidence={item.confidence} />
                          <span className="inline-flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
                            <Coins className="h-3 w-3" />
                            {formatCurrency(item.estimated_cost)}
                          </span>
                        </div>

                        {/* Rationale */}
                        <p className="text-xs italic text-[hsl(var(--muted-foreground))] leading-relaxed">
                          <FileText className="inline h-3 w-3 mr-1 align-middle" />
                          {item.rationale}
                        </p>
                      </div>

                      {/* Accept / Reject micro-buttons */}
                      <div className="flex gap-1 shrink-0">
                        <Button
                          type="button"
                          variant={isAccepted ? "default" : "outline"}
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => {
                            if (!isAccepted) toggleItem(index);
                          }}
                          aria-label={`Aceptar ${item.cups_description}`}
                          title="Aceptar"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          type="button"
                          variant={!isAccepted ? "destructive" : "outline"}
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => {
                            if (isAccepted) toggleItem(index);
                          }}
                          aria-label={`Rechazar ${item.cups_description}`}
                          title="Rechazar"
                        >
                          <X className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  </li>
                );
              })}
          </ul>
        )}
      </CardContent>

      <Separator className="mt-3" />

      {/* ─── Footer ──────────────────────────────────────────────────────── */}
      <CardFooter className="flex flex-wrap items-center justify-between gap-3 pt-3 pb-4">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={rejectAll}
          disabled={isCreating || acceptedCount === 0}
          className="text-[hsl(var(--muted-foreground))] hover:text-foreground"
        >
          Rechazar todo
        </Button>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={acceptAll}
            disabled={
              isCreating ||
              acceptedCount === suggestion.suggestions.length
            }
          >
            Aceptar todo
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={handleCreatePlan}
            disabled={!canCreatePlan || isCreating}
            className="gap-1.5"
          >
            {isCreating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Creando plan...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Crear plan de tratamiento
                {acceptedCount > 0 && (
                  <Badge
                    variant="secondary"
                    className="ml-1 h-4 w-4 rounded-full p-0 text-xs flex items-center justify-center"
                  >
                    {acceptedCount}
                  </Badge>
                )}
              </>
            )}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
