"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Plus,
  X,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePatient } from "@/lib/hooks/use-patients";
import {
  useAnamnesis,
  useUpsertAnamnesis,
  type AnamnesisSectionData,
} from "@/lib/hooks/use-clinical-records";
import { cn } from "@/lib/utils";

// ─── Section Config ──────────────────────────────────────────────────────────

interface SectionConfig {
  key: string;
  title: string;
  placeholder: string;
  notesPlaceholder: string;
}

const SECTIONS: SectionConfig[] = [
  {
    key: "allergies",
    title: "Alergias",
    placeholder: "ej: Penicilina, Látex...",
    notesPlaceholder: "Notas adicionales sobre alergias...",
  },
  {
    key: "medications",
    title: "Medicamentos actuales",
    placeholder: "ej: Metformina 850mg, Losartán...",
    notesPlaceholder: "Notas sobre medicamentos actuales...",
  },
  {
    key: "medical_history",
    title: "Antecedentes médicos",
    placeholder: "ej: Diabetes, Hipertensión...",
    notesPlaceholder: "Detalles adicionales sobre antecedentes médicos...",
  },
  {
    key: "dental_history",
    title: "Antecedentes dentales",
    placeholder: "ej: Ortodoncia previa, Cirugía de terceros molares...",
    notesPlaceholder: "Detalles adicionales sobre antecedentes dentales...",
  },
  {
    key: "family_history",
    title: "Antecedentes familiares",
    placeholder: "ej: Diabetes familiar, Cáncer...",
    notesPlaceholder: "Detalles adicionales sobre antecedentes familiares...",
  },
  {
    key: "habits",
    title: "Hábitos",
    placeholder: "ej: Bruxismo, Onicofagia, Tabaquismo...",
    notesPlaceholder: "Detalles adicionales sobre hábitos...",
  },
];

// ─── Tag Input ───────────────────────────────────────────────────────────────

function TagInput({
  items,
  onAdd,
  onRemove,
  placeholder,
  disabled,
}: {
  items: string[];
  onAdd: (item: string) => void;
  onRemove: (item: string) => void;
  placeholder: string;
  disabled?: boolean;
}) {
  const [input, setInput] = React.useState("");

  function handleAdd() {
    const trimmed = input.trim();
    if (!trimmed || items.includes(trimmed)) return;
    onAdd(trimmed);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAdd}
          disabled={!input.trim() || disabled}
          className="shrink-0"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      {items.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {items.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-1 rounded-full bg-primary-100 dark:bg-primary-900/30 px-2.5 py-0.5 text-xs font-medium text-primary-700 dark:text-primary-300"
            >
              {item}
              <button
                type="button"
                onClick={() => onRemove(item)}
                disabled={disabled}
                aria-label={`Eliminar ${item}`}
                className="ml-0.5 hover:text-primary-900 transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Collapsible Section ─────────────────────────────────────────────────────

function AnamnesisSection({
  config,
  data,
  onChange,
  disabled,
}: {
  config: SectionConfig;
  data: AnamnesisSectionData;
  onChange: (data: AnamnesisSectionData) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = React.useState(true);

  function handleAddItem(item: string) {
    onChange({ ...data, items: [...data.items, item] });
  }

  function handleRemoveItem(item: string) {
    onChange({ ...data, items: data.items.filter((i) => i !== item) });
  }

  function handleNotesChange(notes: string) {
    onChange({ ...data, notes });
  }

  return (
    <Card>
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setOpen((prev) => !prev)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{config.title}</CardTitle>
          <div className="flex items-center gap-2">
            {data.items.length > 0 && (
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                {data.items.length} {data.items.length === 1 ? "ítem" : "ítems"}
              </span>
            )}
            {open ? (
              <ChevronUp className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
            )}
          </div>
        </div>
      </CardHeader>
      {open && (
        <CardContent className="space-y-4 pt-0">
          <TagInput
            items={data.items}
            onAdd={handleAddItem}
            onRemove={handleRemoveItem}
            placeholder={config.placeholder}
            disabled={disabled}
          />
          <textarea
            rows={2}
            value={data.notes}
            onChange={(e) => handleNotesChange(e.target.value)}
            placeholder={config.notesPlaceholder}
            disabled={disabled}
            className={cn(
              "flex w-full rounded-md border border-[hsl(var(--input))] bg-transparent px-3 py-2 text-sm shadow-sm",
              "placeholder:text-[hsl(var(--muted-foreground))]",
              "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-600",
              "disabled:cursor-not-allowed disabled:opacity-50 resize-none",
            )}
          />
        </CardContent>
      )}
    </Card>
  );
}

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function AnamnesisSkeleton() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-20" />
      </div>
      <Skeleton className="h-8 w-48" />
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} className="border rounded-xl p-6 space-y-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ))}
    </div>
  );
}

// ─── Empty Section Data ──────────────────────────────────────────────────────

function emptySectionData(): AnamnesisSectionData {
  return { items: [], notes: "" };
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function AnamnesisPage() {
  const params = useParams<{ id: string }>();
  const patientId = params.id;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: anamnesis, isLoading: isLoadingAnamnesis } = useAnamnesis(patientId);
  const { mutate: upsertAnamnesis, isPending } = useUpsertAnamnesis(patientId);

  const [sections, setSections] = React.useState<Record<string, AnamnesisSectionData>>({
    allergies: emptySectionData(),
    medications: emptySectionData(),
    medical_history: emptySectionData(),
    dental_history: emptySectionData(),
    family_history: emptySectionData(),
    habits: emptySectionData(),
  });

  const [initialized, setInitialized] = React.useState(false);

  // Pre-fill from existing anamnesis
  React.useEffect(() => {
    if (isLoadingAnamnesis || initialized) return;
    setInitialized(true);

    if (!anamnesis) return;

    setSections({
      allergies: anamnesis.allergies ?? emptySectionData(),
      medications: anamnesis.medications ?? emptySectionData(),
      medical_history: anamnesis.medical_history ?? emptySectionData(),
      dental_history: anamnesis.dental_history ?? emptySectionData(),
      family_history: anamnesis.family_history ?? emptySectionData(),
      habits: anamnesis.habits ?? emptySectionData(),
    });
  }, [anamnesis, isLoadingAnamnesis, initialized]);

  function handleSectionChange(key: string, data: AnamnesisSectionData) {
    setSections((prev) => ({ ...prev, [key]: data }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    upsertAnamnesis(sections);
  }

  if (isLoadingPatient || isLoadingAnamnesis) {
    return <AnamnesisSkeleton />;
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="max-w-3xl space-y-6">
      {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}`}
          className="hover:text-foreground transition-colors truncate max-w-[120px]"
        >
          {patient?.full_name ?? "Paciente"}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Anamnesis</span>
      </nav>

      {/* ─── Page Title ──────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Anamnesis</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Historial médico y dental del paciente. Completa las secciones relevantes.
        </p>
      </div>

      {/* ─── Sections ────────────────────────────────────────────────────── */}
      {SECTIONS.map((config) => (
        <AnamnesisSection
          key={config.key}
          config={config}
          data={sections[config.key]}
          onChange={(data) => handleSectionChange(config.key, data)}
          disabled={isPending}
        />
      ))}

      {/* ─── Action Buttons ──────────────────────────────────────────────── */}
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button type="button" variant="outline" asChild>
          <Link href={`/patients/${patientId}`}>Cancelar</Link>
        </Button>
        <Button type="submit" disabled={isPending}>
          {isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Guardando...
            </>
          ) : (
            "Guardar anamnesis"
          )}
        </Button>
      </div>
    </form>
  );
}
