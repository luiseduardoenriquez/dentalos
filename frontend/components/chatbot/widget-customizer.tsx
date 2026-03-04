"use client";

import * as React from "react";
import { Copy, CheckCheck, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type WidgetPosition = "bottom-right" | "bottom-left";

interface WidgetConfig {
  primaryColor: string;
  position: WidgetPosition;
  buttonLabel: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

interface WidgetCustomizerProps {
  clinicSlug?: string;
  className?: string;
}

export function WidgetCustomizer({ clinicSlug = "mi-clinica", className }: WidgetCustomizerProps) {
  const [config, setConfig] = React.useState<WidgetConfig>({
    primaryColor: "#0891B2",
    position: "bottom-right",
    buttonLabel: "Chatear con nosotros",
  });
  const [copied, setCopied] = React.useState(false);

  const embedCode = `<!-- DentalOS Chatbot Widget -->
<script
  src="https://app.dentalos.co/widget.js"
  data-clinic="${clinicSlug}"
  data-color="${config.primaryColor}"
  data-position="${config.position}"
  defer
></script>`;

  function handleCopy() {
    navigator.clipboard.writeText(embedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  }

  return (
    <div className={cn("grid gap-6 md:grid-cols-2", className)}>
      {/* ─── Customization options ───────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Personalización del widget</CardTitle>
          <CardDescription>
            Ajusta la apariencia del chatbot en tu sitio web.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Color */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">Color principal</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={config.primaryColor}
                onChange={(e) =>
                  setConfig((prev) => ({ ...prev, primaryColor: e.target.value }))
                }
                className="h-9 w-12 rounded border border-[hsl(var(--border))] cursor-pointer p-0.5"
              />
              <Input
                value={config.primaryColor}
                onChange={(e) =>
                  setConfig((prev) => ({ ...prev, primaryColor: e.target.value }))
                }
                placeholder="#0891B2"
                className="font-mono text-sm"
                maxLength={7}
              />
            </div>
          </div>

          {/* Position */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">Posición</label>
            <div className="flex gap-2">
              {(["bottom-right", "bottom-left"] as WidgetPosition[]).map((pos) => (
                <button
                  key={pos}
                  type="button"
                  onClick={() => setConfig((prev) => ({ ...prev, position: pos }))}
                  className={cn(
                    "flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                    config.position === pos
                      ? "border-primary-600 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300"
                      : "border-[hsl(var(--border))] bg-transparent text-foreground hover:border-primary-300",
                  )}
                >
                  {pos === "bottom-right" ? "Inferior derecha" : "Inferior izquierda"}
                </button>
              ))}
            </div>
          </div>

          {/* Button label */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">
              Texto del botón
            </label>
            <Input
              value={config.buttonLabel}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, buttonLabel: e.target.value }))
              }
              placeholder="Chatear con nosotros"
              maxLength={40}
            />
          </div>

          {/* Embed code */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">
              Código de integración
            </label>
            <div className="relative">
              <pre className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] p-3 text-xs font-mono text-foreground overflow-x-auto whitespace-pre-wrap break-all">
                {embedCode}
              </pre>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="absolute top-2 right-2 h-7 gap-1.5 text-xs"
                onClick={handleCopy}
              >
                {copied ? (
                  <>
                    <CheckCheck className="h-3 w-3 text-green-600" />
                    Copiado
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    Copiar
                  </>
                )}
              </Button>
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Pega este código antes del cierre de la etiqueta{" "}
              <code className="font-mono">&lt;/body&gt;</code> de tu sitio web.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* ─── Widget preview ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Vista previa</CardTitle>
          <CardDescription>
            Así se verá el widget en tu sitio web.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="relative rounded-xl border border-[hsl(var(--border))] bg-slate-50 dark:bg-zinc-900 overflow-hidden"
            style={{ height: "360px" }}
          >
            {/* Simulated site background */}
            <div className="absolute inset-0 p-4 opacity-20">
              <div className="space-y-2">
                {[80, 60, 70, 50, 65].map((w, i) => (
                  <div
                    key={i}
                    className="h-3 rounded bg-slate-400 dark:bg-zinc-600"
                    style={{ width: `${w}%` }}
                  />
                ))}
              </div>
            </div>

            {/* Chat window mockup */}
            <div
              className={cn(
                "absolute bottom-16 w-60 rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-800 shadow-xl overflow-hidden",
                config.position === "bottom-right" ? "right-4" : "left-4",
              )}
            >
              {/* Chat header */}
              <div
                className="px-4 py-3 text-white"
                style={{ backgroundColor: config.primaryColor }}
              >
                <p className="text-sm font-semibold">Asistente virtual</p>
                <p className="text-xs opacity-80">Clínica Dental</p>
              </div>

              {/* Messages */}
              <div className="p-3 space-y-2 bg-slate-50 dark:bg-zinc-900">
                <div
                  className="inline-block rounded-lg px-3 py-2 text-xs text-white max-w-[80%]"
                  style={{ backgroundColor: config.primaryColor }}
                >
                  ¡Hola! ¿En qué puedo ayudarte hoy?
                </div>
                <div className="flex justify-end">
                  <div className="inline-block rounded-lg bg-white dark:bg-zinc-700 border border-[hsl(var(--border))] px-3 py-2 text-xs text-foreground max-w-[80%]">
                    Quiero agendar una cita
                  </div>
                </div>
                <div
                  className="inline-block rounded-lg px-3 py-2 text-xs text-white max-w-[80%]"
                  style={{ backgroundColor: config.primaryColor }}
                >
                  Con gusto. ¿Para qué fecha?
                </div>
              </div>

              {/* Input area */}
              <div className="flex items-center gap-2 border-t border-[hsl(var(--border))] bg-white dark:bg-zinc-800 px-3 py-2">
                <div className="flex-1 h-6 rounded bg-slate-100 dark:bg-zinc-700" />
                <div
                  className="h-6 w-6 rounded-full flex items-center justify-center"
                  style={{ backgroundColor: config.primaryColor }}
                >
                  <span className="text-white text-xs">›</span>
                </div>
              </div>
            </div>

            {/* Chat button */}
            <div
              className={cn(
                "absolute bottom-4",
                config.position === "bottom-right" ? "right-4" : "left-4",
              )}
            >
              <button
                type="button"
                className="flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium text-white shadow-lg transition-transform hover:scale-105"
                style={{ backgroundColor: config.primaryColor }}
              >
                <MessageCircle className="h-4 w-4" />
                {config.buttonLabel}
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
