"use client";

import { useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { usePortalSignConsent, usePortalDocuments } from "@/lib/hooks/use-portal";

// ─── Signature Canvas ─────────────────────────────────────────────────────────

function SignatureCanvas({
  onSigned,
}: {
  onSigned: (dataUrl: string) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawing = useRef(false);
  const [hasSig, setHasSig] = useState(false);

  function getPos(
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    if ("touches" in e) {
      return {
        x: e.touches[0].clientX - rect.left,
        y: e.touches[0].clientY - rect.top,
      };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function startDraw(
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) {
    isDrawing.current = true;
    const ctx = canvasRef.current!.getContext("2d")!;
    const { x, y } = getPos(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    e.preventDefault();
  }

  function draw(
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) {
    if (!isDrawing.current) return;
    const ctx = canvasRef.current!.getContext("2d")!;
    const { x, y } = getPos(e);
    ctx.lineTo(x, y);
    ctx.strokeStyle = "#0e7490"; // primary-700 approx
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();
    setHasSig(true);
    e.preventDefault();
  }

  function stopDraw() {
    isDrawing.current = false;
    if (canvasRef.current && hasSig) {
      onSigned(canvasRef.current.toDataURL("image/png"));
    }
  }

  function clearCanvas() {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasSig(false);
    onSigned("");
  }

  return (
    <div>
      <div className="relative rounded-lg border-2 border-dashed border-[hsl(var(--border))] bg-slate-50 dark:bg-zinc-800/50 overflow-hidden">
        <canvas
          ref={canvasRef}
          width={600}
          height={160}
          className="w-full touch-none cursor-crosshair"
          onMouseDown={startDraw}
          onMouseMove={draw}
          onMouseUp={stopDraw}
          onMouseLeave={stopDraw}
          onTouchStart={startDraw}
          onTouchMove={draw}
          onTouchEnd={stopDraw}
        />
        {!hasSig && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Dibuja tu firma aquí
            </p>
          </div>
        )}
      </div>
      {hasSig && (
        <button
          onClick={clearCanvas}
          className="mt-2 text-xs text-red-500 hover:text-red-700 transition-colors"
        >
          Borrar firma
        </button>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortalConsentSign() {
  const params = useParams();
  const router = useRouter();
  const consentId = params.id as string;

  const signMutation = usePortalSignConsent();
  // Use portal documents hook to find the consent document details
  const { data: docsData } = usePortalDocuments("consent");
  const allDocs = docsData?.pages.flatMap((p) => p.data) ?? [];
  const consent = allDocs.find((d) => d.id === consentId);

  const [acknowledged, setAcknowledged] = useState(false);
  const [signatureData, setSignatureData] = useState("");
  const [signed, setSigned] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSign() {
    if (!acknowledged) return;
    if (!signatureData) {
      setError("Por favor dibuja tu firma antes de continuar.");
      return;
    }
    setError(null);

    try {
      await signMutation.mutateAsync({
        consentId,
        signature_data: signatureData,
        acknowledged: true,
      });
      setSigned(true);
    } catch {
      setError("Ocurrió un error al firmar. Por favor intenta de nuevo.");
    }
  }

  // Success state
  if (signed) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16 space-y-4">
        <div className="mx-auto w-16 h-16 rounded-full bg-green-100 dark:bg-green-950/30 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-green-600 dark:text-green-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">
          Consentimiento firmado
        </h1>
        <p className="text-[hsl(var(--muted-foreground))]">
          Tu consentimiento ha sido registrado exitosamente.
        </p>
        <button
          onClick={() => router.push("/portal/documents")}
          className="px-6 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
        >
          Volver a documentos
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] mb-3 transition-colors"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Volver
        </button>
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">
          Firmar consentimiento
        </h1>
        {consent?.name && (
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            {consent.name}
          </p>
        )}
      </div>

      {/* Consent document body */}
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-6 space-y-4">
        <h2 className="text-base font-semibold text-[hsl(var(--foreground))]">
          Contenido del consentimiento informado
        </h2>
        <div className="prose dark:prose-invert text-sm max-w-none text-[hsl(var(--foreground))]">
          <p>
            Yo, como paciente, declaro que he sido informado(a) por mi
            odontólogo(a) tratante sobre el diagnóstico de mi condición oral,
            el plan de tratamiento propuesto, los riesgos y beneficios del
            mismo, así como las alternativas existentes.
          </p>
          <p className="mt-3">
            He tenido la oportunidad de hacer preguntas y todas han sido
            respondidas satisfactoriamente. Entiendo que puedo retirar este
            consentimiento en cualquier momento antes de iniciar el
            procedimiento, sin que ello afecte la calidad de la atención que
            recibiré.
          </p>
          <p className="mt-3">
            Autorizo al equipo de la clínica a realizar los procedimientos
            odontológicos necesarios de acuerdo con el plan de tratamiento
            acordado, de conformidad con la Ley 23 de 1981 y la Resolución
            1888 de 2021 del Ministerio de Salud de Colombia.
          </p>
        </div>
      </div>

      {/* Signature pad */}
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4">
        <p className="text-sm font-medium text-[hsl(var(--foreground))] mb-3">
          Firma digital
        </p>
        <SignatureCanvas onSigned={setSignatureData} />
      </div>

      {/* Acknowledgment checkbox */}
      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(e) => setAcknowledged(e.target.checked)}
          className="mt-0.5 w-4 h-4 rounded border-[hsl(var(--border))] text-primary-600 focus:ring-primary-500"
        />
        <span className="text-sm text-[hsl(var(--foreground))] leading-snug">
          He leído y acepto el contenido de este consentimiento informado. Entiendo
          los riesgos, beneficios y alternativas del tratamiento.
        </span>
      </label>

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {/* Sign button */}
      <button
        onClick={handleSign}
        disabled={!acknowledged || signMutation.isPending}
        className="w-full py-3 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {signMutation.isPending ? "Firmando..." : "Firmar consentimiento"}
      </button>

      <p className="text-xs text-center text-[hsl(var(--muted-foreground))]">
        Esta firma digital tiene validez legal de conformidad con la Ley 527 de
        1999 de Colombia.
      </p>
    </div>
  );
}
