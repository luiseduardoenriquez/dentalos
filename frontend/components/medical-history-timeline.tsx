"use client";

import * as React from "react";
import {
  Stethoscope,
  Scissors,
  Pill,
  FileText,
  ClipboardList,
  Loader2,
  ChevronDown,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useMedicalHistory, type MedicalHistoryEvent, type MedicalHistoryEventType } from "@/lib/hooks/use-medical-history";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ─── Event Config ─────────────────────────────────────────────────────────────

type EventConfig = {
  icon: React.ElementType;
  label: string;
  iconClass: string;
  badgeVariant: "default" | "secondary" | "outline" | "destructive" | "success" | "warning";
};

const EVENT_CONFIG: Record<MedicalHistoryEventType, EventConfig> = {
  diagnosis: {
    icon: Stethoscope,
    label: "Diagnóstico",
    iconClass: "text-destructive-600 dark:text-destructive-400",
    badgeVariant: "destructive",
  },
  procedure: {
    icon: Scissors,
    label: "Procedimiento",
    iconClass: "text-primary-600 dark:text-primary-400",
    badgeVariant: "default",
  },
  prescription: {
    icon: Pill,
    label: "Prescripción",
    iconClass: "text-warning-600 dark:text-warning-400",
    badgeVariant: "warning",
  },
  consent: {
    icon: FileText,
    label: "Consentimiento",
    iconClass: "text-success-600 dark:text-success-400",
    badgeVariant: "success",
  },
  clinical_record: {
    icon: ClipboardList,
    label: "Registro clínico",
    iconClass: "text-secondary-600 dark:text-secondary-400",
    badgeVariant: "secondary",
  },
};

// ─── Single Event Item ────────────────────────────────────────────────────────

interface TimelineItemProps {
  event: MedicalHistoryEvent;
  isLast: boolean;
}

function TimelineItem({ event, isLast }: TimelineItemProps) {
  const config = EVENT_CONFIG[event.event_type];
  const Icon = config.icon;

  return (
    <li className="relative flex gap-4">
      {/* Vertical line connector — shown for all items except the last */}
      {!isLast && (
        <span
          className="absolute left-[18px] top-10 bottom-0 w-px bg-[hsl(var(--border))]"
          aria-hidden
        />
      )}

      {/* Icon bubble */}
      <div
        className={cn(
          "relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
          "bg-[hsl(var(--muted))] border border-[hsl(var(--border))]",
        )}
        aria-hidden
      >
        <Icon className={cn("h-4 w-4", config.iconClass)} />
      </div>

      {/* Content */}
      <div className="flex-1 pb-6 pt-1 min-w-0">
        {/* Header row: badge + date */}
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <Badge variant={config.badgeVariant} className="text-[10px] px-2 py-0">
            {config.label}
          </Badge>
          <time
            dateTime={event.event_date}
            className="text-xs text-[hsl(var(--muted-foreground))]"
          >
            {formatDate(event.event_date)}
          </time>
          {event.doctor_name && (
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              · {event.doctor_name}
            </span>
          )}
        </div>

        {/* Title */}
        <p className="text-sm font-medium text-foreground leading-snug">{event.title}</p>

        {/* Description */}
        {event.description && (
          <p className="mt-0.5 text-sm text-[hsl(var(--muted-foreground))] leading-relaxed line-clamp-3">
            {event.description}
          </p>
        )}
      </div>
    </li>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

interface MedicalHistoryTimelineProps {
  patientId: string;
}

/**
 * Vertical timeline of a patient's complete medical history.
 *
 * Displays events of all types (diagnoses, procedures, records, prescriptions,
 * consents) in reverse chronological order. Supports cursor-based pagination via
 * a "Cargar más" button that loads the next page of events and appends them.
 *
 * Each event shows its type badge, date, title, description, and doctor name.
 *
 * @example
 * <MedicalHistoryTimeline patientId={patient.id} />
 */
export function MedicalHistoryTimeline({ patientId }: MedicalHistoryTimelineProps) {
  // Accumulate all loaded events across pages
  const [allEvents, setAllEvents] = React.useState<MedicalHistoryEvent[]>([]);
  const [cursor, setCursor] = React.useState<string | undefined>(undefined);
  const [initialized, setInitialized] = React.useState(false);

  const { data, isLoading, isFetching } = useMedicalHistory(patientId, cursor);

  // Append new events when data arrives
  React.useEffect(() => {
    if (!data) return;

    if (!initialized) {
      // First load — replace all events
      setAllEvents(data.items);
      setInitialized(true);
    } else {
      // Subsequent loads — append
      setAllEvents((prev) => {
        const existingIds = new Set(prev.map((e) => e.id));
        const newItems = data.items.filter((e) => !existingIds.has(e.id));
        return [...prev, ...newItems];
      });
    }
  }, [data, initialized]);

  function handleLoadMore() {
    if (data?.next_cursor) {
      setCursor(data.next_cursor);
    }
  }

  // ─── Loading state (initial fetch only) ────────────────────────────────────

  if (isLoading && !initialized) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <Loader2 className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Cargando historial médico...
        </p>
      </div>
    );
  }

  // ─── Empty state ────────────────────────────────────────────────────────────

  if (initialized && allEvents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-center px-4">
        <ClipboardList className="h-10 w-10 text-[hsl(var(--muted-foreground))]" />
        <div>
          <p className="text-sm font-medium text-foreground">Sin historial médico</p>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            No se han registrado eventos clínicos para este paciente aún.
          </p>
        </div>
      </div>
    );
  }

  // ─── Timeline ───────────────────────────────────────────────────────────────

  return (
    <div className="w-full">
      <ul className="relative list-none p-0 m-0" aria-label="Historial médico del paciente">
        {allEvents.map((event, idx) => (
          <TimelineItem
            key={event.id}
            event={event}
            isLast={idx === allEvents.length - 1 && !data?.has_more}
          />
        ))}
      </ul>

      {/* Load more button */}
      {data?.has_more && (
        <div className="flex justify-center pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleLoadMore}
            disabled={isFetching}
            className="min-w-[160px]"
          >
            {isFetching ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Cargando...
              </>
            ) : (
              <>
                <ChevronDown className="mr-2 h-4 w-4" />
                Cargar más
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
