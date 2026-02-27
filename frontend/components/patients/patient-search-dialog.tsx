"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2, UserX } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useSearchPatients } from "@/lib/hooks/use-patients";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PatientSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Command-palette style dialog for searching patients.
 *
 * - Opens via ⌘K / Ctrl+K or clicking the header search trigger.
 * - Debounced search (300ms, min 2 chars).
 * - Keyboard navigation: ArrowUp/Down, Enter to select, Escape to close.
 * - Navigates to /patients/{id} on selection.
 */
export function PatientSearchDialog({ open, onOpenChange }: PatientSearchDialogProps) {
  const router = useRouter();

  const [query, setQuery] = React.useState("");
  const [activeIndex, setActiveIndex] = React.useState(-1);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const { data: results = [], isFetching } = useSearchPatients(query, 300);

  const hasQuery = query.trim().length >= 2;

  // ─── Reset state when dialog closes ──────────────────────────────────────
  React.useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveIndex(-1);
    }
  }, [open]);

  // ─── Reset active index when results change ──────────────────────────────
  React.useEffect(() => {
    setActiveIndex(-1);
  }, [results]);

  // ─── Navigate to patient ─────────────────────────────────────────────────
  function navigateToPatient(patientId: string) {
    onOpenChange(false);
    router.push(`/patients/${patientId}`);
  }

  // ─── Keyboard navigation ─────────────────────────────────────────────────
  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!hasQuery || results.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (activeIndex >= 0 && results[activeIndex]) {
          navigateToPatient(results[activeIndex].id);
        }
        break;
    }
  }

  // ─── Scroll active item into view ────────────────────────────────────────
  React.useEffect(() => {
    if (activeIndex >= 0) {
      document.getElementById(`search-patient-${activeIndex}`)?.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        size="default"
        showCloseButton={false}
        className="gap-0 p-0 overflow-hidden"
        aria-label="Buscar pacientes"
      >
        {/* Search input */}
        <div className="flex items-center gap-2 border-b border-[hsl(var(--border))] px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-[hsl(var(--muted-foreground))]" />
          <input
            ref={inputRef}
            type="search"
            placeholder="Buscar por nombre, cédula o teléfono..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            autoComplete="off"
            autoFocus
            className={cn(
              "flex-1 bg-transparent text-sm outline-none",
              "placeholder:text-[hsl(var(--muted-foreground))]",
            )}
          />
          {isFetching && hasQuery && (
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-[hsl(var(--muted-foreground))]" />
          )}
          <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-1.5 font-mono text-[10px] text-[hsl(var(--muted-foreground))]">
            ESC
          </kbd>
        </div>

        {/* Results area */}
        <div className="max-h-[320px] overflow-y-auto">
          {/* Initial state — no query yet */}
          {!hasQuery && (
            <div className="flex items-center justify-center py-10 text-sm text-[hsl(var(--muted-foreground))]">
              Escribe al menos 2 caracteres para buscar
            </div>
          )}

          {/* Loading state */}
          {hasQuery && isFetching && results.length === 0 && (
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-[hsl(var(--muted-foreground))]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Buscando...
            </div>
          )}

          {/* Results list */}
          {hasQuery && results.length > 0 && (
            <ul role="listbox" aria-label="Resultados de búsqueda" className="py-1">
              {results.map((patient, idx) => (
                <li
                  key={patient.id}
                  id={`search-patient-${idx}`}
                  role="option"
                  aria-selected={activeIndex === idx}
                  onClick={() => navigateToPatient(patient.id)}
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={cn(
                    "flex items-center justify-between gap-3 px-4 py-2.5 cursor-pointer",
                    "transition-colors",
                    activeIndex === idx
                      ? "bg-primary-50 dark:bg-primary-900/20"
                      : "hover:bg-[hsl(var(--muted))]",
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground truncate">
                      {patient.full_name}
                    </p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                      {patient.document_type} {patient.document_number}
                      {patient.phone && ` · ${patient.phone}`}
                    </p>
                  </div>
                  {patient.is_active ? (
                    <Badge variant="success" className="shrink-0">
                      Activo
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="shrink-0">
                      Inactivo
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          )}

          {/* Empty state */}
          {hasQuery && !isFetching && results.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-2 py-10 text-center px-4">
              <UserX className="h-6 w-6 text-[hsl(var(--muted-foreground))]" />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No se encontraron pacientes para{" "}
                <span className="font-medium text-foreground">&ldquo;{query}&rdquo;</span>
              </p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
