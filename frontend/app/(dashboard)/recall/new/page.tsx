"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RecallSequenceBuilder, type RecallStep } from "@/components/recall-sequence-builder";
import { ChevronLeft, RefreshCw, Loader2 } from "lucide-react";
import Link from "next/link";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RecallCampaignCreate {
  name: string;
  type: string;
  filters: {
    min_days_since_visit: number | null;
    max_days_since_visit: number | null;
    treatment_types: string[];
  };
  channel: string;
  schedule: Array<{ day_offset: number; channel: string; message_template: string }>;
}

// ─── Options ──────────────────────────────────────────────────────────────────

const CAMPAIGN_TYPES = [
  { value: "recall", label: "Recall" },
  { value: "reactivation", label: "Pacientes inactivos (+1 año)" },
  { value: "birthday", label: "Cumpleaños" },
  { value: "treatment_followup", label: "Seguimiento de tratamiento" },
];

const CHANNEL_OPTIONS = [
  { value: "whatsapp", label: "WhatsApp" },
  { value: "sms", label: "SMS" },
  { value: "email", label: "Correo electrónico" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewRecallCampaignPage() {
  const router = useRouter();

  const { mutate: createCampaign, isPending, error } = useMutation({
    mutationFn: (data: RecallCampaignCreate) => apiPost("/recall/campaigns", data),
    onSuccess: (data: any) => {
      router.push(`/recall/${data.id}`);
    },
  });

  const [name, setName] = React.useState("");
  const [campaignType, setCampaignType] = React.useState("");
  const [minDays, setMinDays] = React.useState("");
  const [maxDays, setMaxDays] = React.useState("");
  const [selectedChannels, setSelectedChannels] = React.useState<string[]>([]);
  const [steps, setSteps] = React.useState<RecallStep[]>([]);
  const [formError, setFormError] = React.useState<string | null>(null);

  function toggleChannel(channel: string) {
    setSelectedChannels((prev) =>
      prev.includes(channel) ? prev.filter((c) => c !== channel) : [...prev, channel],
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError("El nombre de la campaña es obligatorio.");
      return;
    }
    if (!campaignType) {
      setFormError("Selecciona el tipo de campaña.");
      return;
    }
    if (selectedChannels.length === 0) {
      setFormError("Selecciona al menos un canal de comunicación.");
      return;
    }
    if (steps.length === 0) {
      setFormError("Agrega al menos un paso a la secuencia.");
      return;
    }

    createCampaign({
      name: name.trim(),
      type: campaignType,
      filters: {
        min_days_since_visit: minDays ? parseInt(minDays) : null,
        max_days_since_visit: maxDays ? parseInt(maxDays) : null,
        treatment_types: [],
      },
      channel: selectedChannels.length === 1 ? selectedChannels[0] : "whatsapp",
      schedule: steps.map(({ day_offset, channel, message_template }) => ({
        day_offset,
        channel,
        message_template,
      })),
    });
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/recall">
            <ChevronLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Nueva campaña de recall</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Define los criterios, canales y secuencia de mensajes.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-primary-600" />
              Información básica
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="campaign-name">Nombre de la campaña *</Label>
              <Input
                id="campaign-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej: Recall limpieza semestral"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="campaign-type">Tipo de campaña *</Label>
              <Select value={campaignType} onValueChange={setCampaignType}>
                <SelectTrigger id="campaign-type">
                  <SelectValue placeholder="Seleccionar tipo..." />
                </SelectTrigger>
                <SelectContent>
                  {CAMPAIGN_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Patient filters */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Filtro de pacientes</CardTitle>
            <CardDescription>
              Define qué pacientes recibirán esta campaña.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label htmlFor="min-days">Mínimo días desde última visita</Label>
                <Input
                  id="min-days"
                  type="number"
                  min={0}
                  value={minDays}
                  onChange={(e) => setMinDays(e.target.value)}
                  placeholder="Ej: 180"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="max-days">Máximo días desde última visita</Label>
                <Input
                  id="max-days"
                  type="number"
                  min={0}
                  value={maxDays}
                  onChange={(e) => setMaxDays(e.target.value)}
                  placeholder="Ej: 365"
                />
              </div>
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Déjalo vacío para no aplicar filtro por tiempo.
            </p>
          </CardContent>
        </Card>

        {/* Channels */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Canales de comunicación *</CardTitle>
            <CardDescription>Selecciona uno o más canales para enviar los mensajes.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {CHANNEL_OPTIONS.map((ch) => {
                const selected = selectedChannels.includes(ch.value);
                return (
                  <button
                    key={ch.value}
                    type="button"
                    onClick={() => toggleChannel(ch.value)}
                    className={`rounded-lg border px-4 py-3 text-sm font-medium text-left transition-colors ${
                      selected
                        ? "border-primary-600 bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300"
                        : "border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:border-primary-400"
                    }`}
                  >
                    {ch.label}
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Sequence builder */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Secuencia de mensajes *</CardTitle>
            <CardDescription>
              Define cuándo y qué mensaje enviar en cada paso.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RecallSequenceBuilder
              steps={steps}
              onChange={setSteps}
              availableChannels={selectedChannels}
            />
          </CardContent>
        </Card>

        {/* Error + Submit */}
        {formError && (
          <p className="text-sm text-destructive">{formError}</p>
        )}
        {error && (
          <p className="text-sm text-destructive">
            No se pudo crear la campaña. Inténtalo de nuevo.
          </p>
        )}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={isPending}>
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creando...
              </>
            ) : (
              "Crear campaña"
            )}
          </Button>
          <Button variant="outline" asChild>
            <Link href="/recall">Cancelar</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
