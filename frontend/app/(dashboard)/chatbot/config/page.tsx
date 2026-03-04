"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Save, RefreshCw, AlertCircle } from "lucide-react";
import { apiGet, apiPut } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FaqEntry {
  question: string;
  answer: string;
}

interface ChatbotConfig {
  is_enabled: boolean;
  greeting_message: string;
  business_hours_text: string;
  escalation_message: string;
  faqs: FaqEntry[];
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function ConfigSkeleton() {
  return (
    <div className="space-y-6">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-40 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
      ))}
    </div>
  );
}

// ─── Toggle switch ────────────────────────────────────────────────────────────

function ToggleSwitch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
        checked ? "bg-primary-600" : "bg-slate-300 dark:bg-zinc-600",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
          checked ? "translate-x-6" : "translate-x-1",
        )}
      />
    </button>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ChatbotConfigPage() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["chatbot-config"],
    queryFn: () => apiGet<ChatbotConfig>("/chatbot/config"),
    staleTime: 5 * 60_000,
  });

  // Local form state
  const [isEnabled, setIsEnabled] = React.useState(false);
  const [greetingMessage, setGreetingMessage] = React.useState("");
  const [businessHoursText, setBusinessHoursText] = React.useState("");
  const [escalationMessage, setEscalationMessage] = React.useState("");
  const [faqs, setFaqs] = React.useState<FaqEntry[]>([]);
  const [saveSuccess, setSaveSuccess] = React.useState(false);

  // Sync form state when data loads
  React.useEffect(() => {
    if (data) {
      setIsEnabled(data.is_enabled);
      setGreetingMessage(data.greeting_message);
      setBusinessHoursText(data.business_hours_text);
      setEscalationMessage(data.escalation_message);
      setFaqs(data.faqs);
    }
  }, [data]);

  const { mutate: saveConfig, isPending: isSaving } = useMutation({
    mutationFn: (payload: ChatbotConfig) => apiPut<ChatbotConfig>("/chatbot/config", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chatbot-config"] });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    },
  });

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    saveConfig({
      is_enabled: isEnabled,
      greeting_message: greetingMessage,
      business_hours_text: businessHoursText,
      escalation_message: escalationMessage,
      faqs,
    });
  }

  function addFaq() {
    setFaqs((prev) => [...prev, { question: "", answer: "" }]);
  }

  function removeFaq(index: number) {
    setFaqs((prev) => prev.filter((_, i) => i !== index));
  }

  function updateFaq(index: number, field: keyof FaqEntry, value: string) {
    setFaqs((prev) =>
      prev.map((faq, i) => (i === index ? { ...faq, [field]: value } : faq)),
    );
  }

  if (isLoading) return <ConfigSkeleton />;

  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          No se pudo cargar la configuración del chatbot.
        </p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Configuración del Chatbot
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Personaliza el comportamiento y mensajes del asistente virtual.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* ─── Enable / disable ──────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Estado del chatbot</CardTitle>
            <CardDescription>
              Activa o desactiva el asistente virtual para todos los canales.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">
                  {isEnabled ? "Chatbot activo" : "Chatbot desactivado"}
                </p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  {isEnabled
                    ? "Los pacientes pueden interactuar con el asistente."
                    : "No se responderán mensajes automáticamente."}
                </p>
              </div>
              <ToggleSwitch
                checked={isEnabled}
                onChange={setIsEnabled}
                disabled={isSaving}
              />
            </div>
          </CardContent>
        </Card>

        {/* ─── Messages ─────────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Mensajes del chatbot</CardTitle>
            <CardDescription>
              Configura los mensajes automáticos del asistente.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Greeting */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">
                Mensaje de bienvenida
              </label>
              <textarea
                rows={3}
                value={greetingMessage}
                onChange={(e) => setGreetingMessage(e.target.value)}
                disabled={isSaving}
                placeholder="Ej: ¡Hola! Soy el asistente de Clínica Dental. ¿En qué puedo ayudarte?"
                className={cn(
                  "w-full resize-none rounded-lg border border-[hsl(var(--border))]",
                  "bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground",
                  "placeholder:text-[hsl(var(--muted-foreground))]",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent",
                  "disabled:opacity-50",
                )}
              />
            </div>

            {/* Business hours */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">
                Texto de horario de atención
              </label>
              <Input
                value={businessHoursText}
                onChange={(e) => setBusinessHoursText(e.target.value)}
                disabled={isSaving}
                placeholder="Ej: Atendemos Lunes a Viernes de 8am a 6pm"
              />
            </div>

            {/* Escalation */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">
                Mensaje de escalación
              </label>
              <textarea
                rows={2}
                value={escalationMessage}
                onChange={(e) => setEscalationMessage(e.target.value)}
                disabled={isSaving}
                placeholder="Ej: Un miembro de nuestro equipo se comunicará contigo en breve."
                className={cn(
                  "w-full resize-none rounded-lg border border-[hsl(var(--border))]",
                  "bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground",
                  "placeholder:text-[hsl(var(--muted-foreground))]",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent",
                  "disabled:opacity-50",
                )}
              />
            </div>
          </CardContent>
        </Card>

        {/* ─── FAQs ────────────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Preguntas frecuentes</CardTitle>
                <CardDescription className="mt-1">
                  El chatbot responderá automáticamente con estas respuestas.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addFaq}
                disabled={isSaving}
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                Agregar pregunta
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {faqs.length === 0 ? (
              <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
                No hay preguntas frecuentes configuradas. Agrega una.
              </p>
            ) : (
              faqs.map((faq, index) => (
                <div
                  key={index}
                  className="rounded-lg border border-[hsl(var(--border))] p-4 space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                      Pregunta {index + 1}
                    </p>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                      onClick={() => removeFaq(index)}
                      disabled={isSaving}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-foreground">Pregunta</label>
                    <Input
                      value={faq.question}
                      onChange={(e) => updateFaq(index, "question", e.target.value)}
                      disabled={isSaving}
                      placeholder="Ej: ¿Cuáles son sus horarios de atención?"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-foreground">Respuesta</label>
                    <textarea
                      rows={2}
                      value={faq.answer}
                      onChange={(e) => updateFaq(index, "answer", e.target.value)}
                      disabled={isSaving}
                      placeholder="Ej: Atendemos de lunes a viernes de 8am a 6pm y sábados de 9am a 1pm."
                      className={cn(
                        "w-full resize-none rounded-lg border border-[hsl(var(--border))]",
                        "bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground",
                        "placeholder:text-[hsl(var(--muted-foreground))]",
                        "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent",
                        "disabled:opacity-50",
                      )}
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* ─── Save button ─────────────────────────────────────────────── */}
        <div className="flex items-center justify-end gap-3">
          {saveSuccess && (
            <p className="text-sm text-green-600 dark:text-green-400">
              Configuración guardada correctamente.
            </p>
          )}
          <Button type="submit" disabled={isSaving}>
            {isSaving ? (
              <>
                <RefreshCw className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                Guardando...
              </>
            ) : (
              <>
                <Save className="mr-1.5 h-3.5 w-3.5" />
                Guardar configuración
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
