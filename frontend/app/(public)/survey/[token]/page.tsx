"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Star, CheckCircle2, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SurveySubmitPayload {
  score: number;
  feedback_text?: string;
}

interface SurveySubmitResponse {
  routed_to: "google_review" | "private";
  google_review_url?: string;
  message: string;
}

// ─── Star Picker ──────────────────────────────────────────────────────────────

function StarPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (score: number) => void;
}) {
  const [hovered, setHovered] = React.useState(0);
  const displayed = hovered || value;

  return (
    <div
      className="flex items-center justify-center gap-2"
      role="radiogroup"
      aria-label="Calificación"
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          role="radio"
          aria-checked={value === star}
          aria-label={`${star} estrella${star !== 1 ? "s" : ""}`}
          className="p-1 rounded-full transition-transform hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-600"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
        >
          <Star
            className={cn(
              "h-10 w-10 transition-colors",
              star <= displayed
                ? "fill-yellow-400 text-yellow-400"
                : "fill-transparent text-slate-300 dark:text-zinc-600",
            )}
          />
        </button>
      ))}
    </div>
  );
}

// ─── Score Label ──────────────────────────────────────────────────────────────

const SCORE_LABELS: Record<number, string> = {
  1: "Muy insatisfecho",
  2: "Insatisfecho",
  3: "Neutral",
  4: "Satisfecho",
  5: "Muy satisfecho",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PublicSurveyPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";

  const [score, setScore] = React.useState(0);
  const [feedbackText, setFeedbackText] = React.useState("");
  const [submitted, setSubmitted] = React.useState(false);
  const [result, setResult] = React.useState<SurveySubmitResponse | null>(null);

  const { mutate: submitSurvey, isPending } = useMutation({
    mutationFn: (payload: SurveySubmitPayload) =>
      apiPost<SurveySubmitResponse>(`/public/survey/${token}`, payload),
    onSuccess: (data) => {
      setResult(data);
      setSubmitted(true);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (score === 0) return;
    submitSurvey({
      score,
      feedback_text: feedbackText.trim() || undefined,
    });
  }

  // ─── Thank you screen ─────────────────────────────────────────────────────

  if (submitted && result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--background))] px-4">
        <div className="w-full max-w-sm text-center space-y-6">
          <CheckCircle2 className="mx-auto h-16 w-16 text-green-500" />
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-foreground">
              {result.routed_to === "google_review"
                ? "¡Nos alegra saberlo!"
                : "¡Gracias por tu feedback!"}
            </h1>
            <p className="text-[hsl(var(--muted-foreground))] text-sm">
              {result.routed_to === "google_review"
                ? "Tu opinión ayuda a que más personas conozcan nuestra clínica. ¿Nos dejarías una reseña en Google?"
                : "Hemos recibido tu comentario. Trabajaremos para mejorar tu experiencia."}
            </p>
          </div>

          {result.routed_to === "google_review" && result.google_review_url && (
            <a
              href={result.google_review_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              Dejar reseña en Google
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
      </div>
    );
  }

  // ─── Survey form ──────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--background))] px-4">
      <div className="w-full max-w-sm">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Logo / Clinic name placeholder */}
          <div className="text-center space-y-1">
            <div className="mx-auto h-14 w-14 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
              <Star className="h-7 w-7 text-primary-600" />
            </div>
            <h1 className="mt-4 text-xl font-bold text-foreground">
              ¿Cómo fue tu experiencia?
            </h1>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Tu opinión nos ayuda a mejorar. Solo toma 30 segundos.
            </p>
          </div>

          {/* Star rating */}
          <div className="space-y-3">
            <StarPicker value={score} onChange={setScore} />
            {score > 0 && (
              <p className="text-center text-sm font-medium text-foreground animate-in fade-in-0 duration-200">
                {SCORE_LABELS[score]}
              </p>
            )}
          </div>

          {/* Feedback textarea — shown for low scores */}
          {score > 0 && score < 4 && (
            <div
              className="space-y-1.5 animate-in fade-in-0 slide-in-from-top-2 duration-300"
            >
              <label
                htmlFor="feedback-text"
                className="text-sm font-medium text-foreground"
              >
                ¿Qué podríamos mejorar?{" "}
                <span className="text-[hsl(var(--muted-foreground))] font-normal">
                  (opcional)
                </span>
              </label>
              <textarea
                id="feedback-text"
                rows={3}
                placeholder="Cuéntanos más sobre tu experiencia..."
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                className={cn(
                  "w-full resize-none rounded-lg border border-[hsl(var(--border))]",
                  "bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground",
                  "placeholder:text-[hsl(var(--muted-foreground))]",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent",
                )}
              />
            </div>
          )}

          {/* Submit */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={score === 0 || isPending}
          >
            {isPending ? "Enviando..." : "Enviar"}
          </Button>

          <p className="text-center text-xs text-[hsl(var(--muted-foreground))]">
            Tus respuestas son confidenciales y solo se usan para mejorar nuestro
            servicio.
          </p>
        </form>
      </div>
    </div>
  );
}
