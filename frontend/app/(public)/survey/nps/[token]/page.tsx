"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { CheckCircle2, Star, Loader2 } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface NpsSurveyInfo {
  clinic_name: string;
  doctor_name: string | null;
  appointment_date: string | null;
}

interface NpsSurveySubmitPayload {
  nps_score: number;
  csat_score?: number | null;
  comments?: string | null;
}

interface NpsSurveySubmitResponse {
  message: string;
}

// ─── NPS 0–10 scale ───────────────────────────────────────────────────────────

function NpsScale({
  value,
  onChange,
  disabled,
}: {
  value: number | null;
  onChange: (score: number) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Escala de recomendación 0 a 10"
      className="w-full"
    >
      {/* Number buttons */}
      <div className="flex justify-center gap-1 flex-wrap">
        {Array.from({ length: 11 }, (_, i) => i).map((n) => {
          const isSelected = value === n;
          const isRed = n <= 6;
          const isYellow = n >= 7 && n <= 8;
          const isGreen = n >= 9;

          return (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={isSelected}
              aria-label={`${n}`}
              disabled={disabled}
              onClick={() => onChange(n)}
              className={cn(
                "h-10 w-10 rounded-lg text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-600",
                "border-2",
                isSelected
                  ? isRed
                    ? "border-red-500 bg-red-500 text-white shadow-md scale-110"
                    : isYellow
                    ? "border-yellow-400 bg-yellow-400 text-white shadow-md scale-110"
                    : "border-green-500 bg-green-500 text-white shadow-md scale-110"
                  : isRed
                  ? "border-red-200 text-red-600 hover:border-red-400 hover:bg-red-50 dark:border-red-800 dark:text-red-400"
                  : isYellow
                  ? "border-yellow-200 text-yellow-600 hover:border-yellow-400 hover:bg-yellow-50 dark:border-yellow-800 dark:text-yellow-400"
                  : "border-green-200 text-green-600 hover:border-green-400 hover:bg-green-50 dark:border-green-800 dark:text-green-400",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            >
              {n}
            </button>
          );
        })}
      </div>

      {/* Scale labels */}
      <div className="flex justify-between mt-2 px-1">
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          0 = Nada probable
        </span>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          10 = Muy probable
        </span>
      </div>
    </div>
  );
}

// ─── CSAT stars ───────────────────────────────────────────────────────────────

function CsatStars({
  value,
  onChange,
  disabled,
}: {
  value: number | null;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  const [hovered, setHovered] = React.useState(0);
  const displayed = hovered || value || 0;

  return (
    <div
      className="flex items-center justify-center gap-2"
      role="radiogroup"
      aria-label="Calificación de satisfacción"
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          role="radio"
          aria-checked={value === star}
          aria-label={`${star} estrella${star !== 1 ? "s" : ""}`}
          disabled={disabled}
          onClick={() => onChange(star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          className="p-1 rounded-full transition-transform hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 disabled:opacity-50"
        >
          <Star
            className={cn(
              "h-9 w-9 transition-colors",
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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NpsSurveyPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";

  // Extract slug from env or use a default approach — slug embedded in URL
  // The API accepts /public/{slug}/nps-survey/{token} but we'll use a generic
  // public endpoint that resolves the clinic from the token itself
  const publicBase = process.env.NEXT_PUBLIC_API_URL
    ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1`
    : "/api/v1";

  const { data: surveyInfo, isLoading: isLoadingInfo } = useQuery({
    queryKey: ["nps-survey-info", token],
    queryFn: () => apiGet<NpsSurveyInfo>(`/public/nps-survey/${token}`),
    retry: false,
    staleTime: Infinity,
  });

  const [npsScore, setNpsScore] = React.useState<number | null>(null);
  const [csatScore, setCsatScore] = React.useState<number | null>(null);
  const [comments, setComments] = React.useState("");
  const [submitted, setSubmitted] = React.useState(false);

  const { mutate: submitSurvey, isPending } = useMutation({
    mutationFn: (payload: NpsSurveySubmitPayload) =>
      apiPost<NpsSurveySubmitResponse>(`/public/nps-survey/${token}`, payload),
    onSuccess: () => {
      setSubmitted(true);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (npsScore === null) return;
    submitSurvey({
      nps_score: npsScore,
      csat_score: csatScore ?? null,
      comments: comments.trim() || null,
    });
  }

  // ─── Thank you screen ──────────────────────────────────────────────────────

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--background))] px-4 py-8">
        <div className="w-full max-w-sm text-center space-y-6">
          <div className="flex justify-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <CheckCircle2 className="h-10 w-10 text-green-600 dark:text-green-400" />
            </div>
          </div>
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-foreground">¡Gracias!</h1>
            <p className="text-[hsl(var(--muted-foreground))] text-sm">
              Hemos recibido tu opinión. Tu feedback nos ayuda a mejorar la
              atención de{" "}
              <strong className="text-foreground">
                {surveyInfo?.clinic_name ?? "nuestra clínica"}
              </strong>
              .
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ─── Survey form ───────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--background))] px-4 py-8">
      <div className="w-full max-w-sm">
        {/* Clinic header */}
        <div className="text-center mb-8">
          <div className="mx-auto h-14 w-14 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mb-4">
            <Star className="h-7 w-7 text-primary-600" />
          </div>
          {isLoadingInfo ? (
            <div className="space-y-1.5">
              <div className="h-5 w-40 bg-slate-200 dark:bg-zinc-700 rounded mx-auto animate-pulse" />
              <div className="h-3.5 w-28 bg-slate-100 dark:bg-zinc-800 rounded mx-auto animate-pulse" />
            </div>
          ) : surveyInfo ? (
            <div>
              <p className="text-base font-semibold text-foreground">
                {surveyInfo.clinic_name}
              </p>
              {surveyInfo.doctor_name && (
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  Dr. {surveyInfo.doctor_name}
                </p>
              )}
            </div>
          ) : null}
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* NPS question */}
          <div className="space-y-4">
            <h1 className="text-center text-lg font-semibold text-foreground leading-snug">
              ¿Qué tan probable es que recomiendes nuestra clínica a un amigo o familiar?
            </h1>
            <NpsScale
              value={npsScore}
              onChange={setNpsScore}
              disabled={isPending}
            />
          </div>

          {/* CSAT — optional, shown after NPS selected */}
          {npsScore !== null && (
            <div
              className="space-y-3 animate-in fade-in-0 slide-in-from-top-2 duration-300"
            >
              <h2 className="text-center text-sm font-medium text-foreground">
                ¿Cómo calificarías tu experiencia general?{" "}
                <span className="text-[hsl(var(--muted-foreground))] font-normal">
                  (opcional)
                </span>
              </h2>
              <CsatStars
                value={csatScore}
                onChange={setCsatScore}
                disabled={isPending}
              />
            </div>
          )}

          {/* Comments — optional */}
          {npsScore !== null && (
            <div
              className="space-y-1.5 animate-in fade-in-0 slide-in-from-top-2 duration-300"
            >
              <label
                htmlFor="nps-comments"
                className="text-sm font-medium text-foreground"
              >
                ¿Quieres dejarnos un comentario?{" "}
                <span className="text-[hsl(var(--muted-foreground))] font-normal">
                  (opcional)
                </span>
              </label>
              <textarea
                id="nps-comments"
                rows={3}
                placeholder="Cuéntanos sobre tu experiencia..."
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                disabled={isPending}
                className={cn(
                  "w-full resize-none rounded-lg border border-[hsl(var(--border))]",
                  "bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground",
                  "placeholder:text-[hsl(var(--muted-foreground))]",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent",
                  "disabled:opacity-50",
                )}
              />
            </div>
          )}

          {/* Submit */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={npsScore === null || isPending}
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Enviando...
              </>
            ) : (
              "Enviar respuesta"
            )}
          </Button>

          <p className="text-center text-xs text-[hsl(var(--muted-foreground))]">
            Tus respuestas son confidenciales y solo se usan para mejorar
            nuestro servicio.
          </p>
        </form>
      </div>
    </div>
  );
}
