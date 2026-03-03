"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Sparkles, Loader2, Search } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIQueryResponse {
  answer: string;
  data: Record<string, unknown>[];
  chart_type: "bar" | "line" | "pie" | "table" | "number";
  query_key: string;
}

export interface AIQueryBarProps {
  onResponse?: (response: AIQueryResponse) => void;
  className?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MAX_HISTORY = 5;

const EXAMPLE_QUESTIONS = [
  "¿Cuántos pacientes vinieron este mes?",
  "¿Cuál es la tasa de inasistencia?",
  "¿Cuánto ingresé esta semana?",
  "¿Cuál es el procedimiento más realizado?",
];

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * AIQueryBar — Natural language search bar for analytics queries.
 *
 * Sends the user's question to POST /analytics/ai-query.
 * Maintains a history of the last 5 questions as suggestion chips.
 * Calls onResponse with the structured AI response on success.
 */
export function AIQueryBar({ onResponse, className }: AIQueryBarProps) {
  const { error: toastError } = useToast();
  const [query, setQuery] = React.useState("");
  const [history, setHistory] = React.useState<string[]>([]);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: (question: string) =>
      apiPost<AIQueryResponse>("/analytics/ai-query", { question }),
    onSuccess: (data) => {
      onResponse?.(data);
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message ??
        (err instanceof Error ? err.message : null) ??
        "No se pudo procesar la pregunta. Inténtalo de nuevo.";
      toastError("Error al consultar la IA", message);
    },
  });

  const submitQuery = (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || mutation.isPending) return;

    // Update history (deduplicate, keep latest at front, cap at MAX_HISTORY)
    setHistory((prev) => {
      const filtered = prev.filter(
        (q) => q.toLowerCase() !== trimmed.toLowerCase(),
      );
      return [trimmed, ...filtered].slice(0, MAX_HISTORY);
    });

    mutation.mutate(trimmed);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitQuery(query);
  };

  const handleChipClick = (question: string) => {
    setQuery(question);
    submitQuery(question);
    inputRef.current?.focus();
  };

  const showHistory = history.length > 0;
  const showExamples = !showHistory;

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {/* ─── Search bar ────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="relative flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Pregunta a la IA sobre tus datos..."
            disabled={mutation.isPending}
            className={cn(
              "w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
              "pl-10 pr-4 py-2.5 text-sm text-foreground",
              "placeholder:text-[hsl(var(--muted-foreground))]",
              "shadow-sm transition-shadow",
              "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600",
              "disabled:opacity-50 disabled:cursor-not-allowed",
            )}
          />
        </div>

        <Button
          type="submit"
          size="sm"
          disabled={!query.trim() || mutation.isPending}
          className="shrink-0 gap-1.5"
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analizando...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Consultar
            </>
          )}
        </Button>
      </form>

      {/* ─── Loading state label ──────────────────────────────────────────── */}
      {mutation.isPending && (
        <p className="text-xs text-[hsl(var(--muted-foreground))] animate-pulse">
          Analizando tu pregunta...
        </p>
      )}

      {/* ─── Suggestion chips ─────────────────────────────────────────────── */}
      {!mutation.isPending && (showHistory || showExamples) && (
        <div className="flex flex-wrap gap-1.5">
          {showHistory && (
            <span className="text-xs text-[hsl(var(--muted-foreground))] self-center mr-1">
              Recientes:
            </span>
          )}
          {showExamples && (
            <span className="text-xs text-[hsl(var(--muted-foreground))] self-center mr-1">
              Sugerencias:
            </span>
          )}
          {(showHistory ? history : EXAMPLE_QUESTIONS).map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => handleChipClick(q)}
              className={cn(
                "inline-flex items-center rounded-full px-3 py-1",
                "text-xs font-medium",
                "border border-[hsl(var(--border))] bg-[hsl(var(--muted))]",
                "text-[hsl(var(--muted-foreground))] hover:text-foreground",
                "hover:bg-[hsl(var(--muted))]/80 hover:border-primary-300",
                "transition-colors cursor-pointer",
                "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-1",
              )}
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
