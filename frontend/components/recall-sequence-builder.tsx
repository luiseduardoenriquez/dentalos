"use client";

/**
 * RecallSequenceBuilder — Multi-step sequence editor for recall campaigns.
 *
 * Each step defines:
 *   - day_offset: days after campaign start (or previous step) to send
 *   - channel: communication channel (whatsapp, sms, email, in_app)
 *   - message_template: the message body
 *
 * Usage:
 *   <RecallSequenceBuilder
 *     steps={steps}
 *     onChange={setSteps}
 *     availableChannels={["whatsapp", "email"]}
 *   />
 */

import * as React from "react";
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
import { Plus, Trash2, GripVertical, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface RecallStep {
  id: string;
  day_offset: number;
  channel: string;
  message_template: string;
}

interface RecallSequenceBuilderProps {
  steps: RecallStep[];
  onChange: (steps: RecallStep[]) => void;
  availableChannels?: string[];
}

// ─── Channel labels ───────────────────────────────────────────────────────────

const CHANNEL_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp",
  sms: "SMS",
  email: "Correo electrónico",
  in_app: "Notificación en app",
};

const ALL_CHANNELS = Object.keys(CHANNEL_LABELS);

// ─── Helpers ──────────────────────────────────────────────────────────────────

function generateId() {
  return `step_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

function createEmptyStep(dayOffset = 0, channel = ""): RecallStep {
  return {
    id: generateId(),
    day_offset: dayOffset,
    channel,
    message_template: "",
  };
}

// ─── Single step card ─────────────────────────────────────────────────────────

function StepCard({
  step,
  index,
  total,
  availableChannels,
  onChange,
  onRemove,
}: {
  step: RecallStep;
  index: number;
  total: number;
  availableChannels: string[];
  onChange: (updated: RecallStep) => void;
  onRemove: () => void;
}) {
  const channels = availableChannels.length > 0 ? availableChannels : ALL_CHANNELS;

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
      {/* Step header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-[hsl(var(--muted))] border-b border-[hsl(var(--border))]">
        <GripVertical className="h-4 w-4 text-[hsl(var(--muted-foreground))] opacity-50" />
        <span className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
          Paso {index + 1}
        </span>
        <div className="flex-1" />
        {total > 1 && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-[hsl(var(--muted-foreground))] hover:text-destructive"
            onClick={onRemove}
            title="Eliminar paso"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* Step fields */}
      <div className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {/* Day offset */}
          <div className="space-y-1">
            <Label htmlFor={`step-day-${step.id}`}>
              Días desde inicio
            </Label>
            <Input
              id={`step-day-${step.id}`}
              type="number"
              min={0}
              value={step.day_offset}
              onChange={(e) =>
                onChange({ ...step, day_offset: parseInt(e.target.value) || 0 })
              }
              placeholder="0"
            />
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              0 = el mismo día del inicio
            </p>
          </div>

          {/* Channel */}
          <div className="space-y-1">
            <Label htmlFor={`step-channel-${step.id}`}>Canal</Label>
            <Select
              value={step.channel}
              onValueChange={(v) => onChange({ ...step, channel: v })}
            >
              <SelectTrigger id={`step-channel-${step.id}`}>
                <SelectValue placeholder="Seleccionar canal..." />
              </SelectTrigger>
              <SelectContent>
                {channels.map((ch) => (
                  <SelectItem key={ch} value={ch}>
                    {CHANNEL_LABELS[ch] ?? ch}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Message template */}
        <div className="space-y-1">
          <Label htmlFor={`step-msg-${step.id}`}>Mensaje</Label>
          <textarea
            id={`step-msg-${step.id}`}
            rows={3}
            value={step.message_template}
            onChange={(e) => onChange({ ...step, message_template: e.target.value })}
            placeholder={`Hola {{patient_name}}, te recordamos que ha pasado tiempo desde tu última visita en {{clinic_name}}. ¿Te gustaría agendar una cita?`}
            className={cn(
              "flex w-full rounded-md border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm",
              "placeholder:text-[hsl(var(--muted-foreground))]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
              "resize-none",
            )}
          />
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Variables disponibles: {"{{"} patient_name {"}}"}, {"{{"} clinic_name {"}}"}, {"{{"} booking_link {"}}"}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function RecallSequenceBuilder({
  steps,
  onChange,
  availableChannels = [],
}: RecallSequenceBuilderProps) {
  function addStep() {
    const lastDay = steps.length > 0 ? steps[steps.length - 1].day_offset : 0;
    const defaultChannel = availableChannels[0] ?? "";
    onChange([...steps, createEmptyStep(lastDay + 7, defaultChannel)]);
  }

  function updateStep(index: number, updated: RecallStep) {
    onChange(steps.map((s, i) => (i === index ? updated : s)));
  }

  function removeStep(index: number) {
    if (steps.length <= 1) return;
    onChange(steps.filter((_, i) => i !== index));
  }

  return (
    <div className="space-y-4">
      {steps.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[hsl(var(--border))] py-8 text-center">
          <p className="text-sm text-[hsl(var(--muted-foreground))] mb-3">
            No hay pasos en la secuencia. Agrega el primero.
          </p>
          <Button type="button" variant="outline" onClick={addStep}>
            <Plus className="mr-2 h-4 w-4" />
            Agregar paso
          </Button>
        </div>
      ) : (
        <>
          {steps.map((step, index) => (
            <React.Fragment key={step.id}>
              <StepCard
                step={step}
                index={index}
                total={steps.length}
                availableChannels={availableChannels}
                onChange={(updated) => updateStep(index, updated)}
                onRemove={() => removeStep(index)}
              />
              {index < steps.length - 1 && (
                <div className="flex justify-center">
                  <div className="flex flex-col items-center gap-1 text-[hsl(var(--muted-foreground))]">
                    <ArrowDown className="h-4 w-4" />
                  </div>
                </div>
              )}
            </React.Fragment>
          ))}

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={addStep}
          >
            <Plus className="mr-2 h-4 w-4" />
            Agregar paso
          </Button>
        </>
      )}
    </div>
  );
}
