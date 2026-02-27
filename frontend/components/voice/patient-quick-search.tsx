"use client";

import * as React from "react";
import { Search, UserX, Loader2 } from "lucide-react";
import { useSearchPatients, type PatientSearchResult } from "@/lib/hooks/use-patients";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PatientQuickSearchProps {
  /** Called when a patient is selected */
  onSelect: (patient: PatientSearchResult) => void;
  /** Whether the search input should auto-focus */
  autoFocus?: boolean;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Compact patient search for the voice quick-start modal.
 * Supports keyboard navigation (arrow keys + Enter).
 */
export function PatientQuickSearch({
  onSelect,
  autoFocus = true,
  className,
}: PatientQuickSearchProps) {
  const [query, setQuery] = React.useState("");
  const [highlightedIndex, setHighlightedIndex] = React.useState(-1);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listRef = React.useRef<HTMLUListElement>(null);

  const { data: results = [], isLoading } = useSearchPatients(query, 250);
  const showResults = query.length >= 2;

  // Auto-focus input on mount
  React.useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  // Reset highlight when results change
  React.useEffect(() => {
    setHighlightedIndex(-1);
  }, [results]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showResults || results.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === "Enter" && highlightedIndex >= 0) {
      e.preventDefault();
      onSelect(results[highlightedIndex]);
    }
  }

  // Scroll highlighted item into view
  React.useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const item = listRef.current.children[highlightedIndex] as HTMLElement | undefined;
      item?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightedIndex]);

  return (
    <div className={cn("space-y-2", className)}>
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Buscar por cedula o nombre..."
          className={cn(
            "w-full rounded-lg border border-[hsl(var(--border))] bg-transparent",
            "pl-9 pr-4 py-2.5 text-sm",
            "placeholder:text-[hsl(var(--muted-foreground))]",
            "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600",
          )}
          role="combobox"
          aria-expanded={showResults && results.length > 0}
          aria-autocomplete="list"
          aria-controls="patient-quick-search-list"
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-[hsl(var(--muted-foreground))]" />
        )}
      </div>

      {/* Hint text before typing */}
      {!showResults && query.length === 0 && (
        <p className="text-xs text-[hsl(var(--muted-foreground))] text-center py-2">
          Ingrese al menos 2 caracteres para buscar
        </p>
      )}

      {/* Results list */}
      {showResults && (
        <ul
          ref={listRef}
          id="patient-quick-search-list"
          role="listbox"
          className="max-h-48 overflow-y-auto rounded-lg border border-[hsl(var(--border))] divide-y divide-[hsl(var(--border))]"
        >
          {results.length === 0 && !isLoading && (
            <li className="flex flex-col items-center gap-1 py-6 text-[hsl(var(--muted-foreground))]">
              <UserX className="h-5 w-5" />
              <span className="text-xs">No se encontraron pacientes</span>
            </li>
          )}

          {results.slice(0, 5).map((patient, index) => (
            <li
              key={patient.id}
              role="option"
              aria-selected={highlightedIndex === index}
              className={cn(
                "flex items-center justify-between px-3 py-2.5 cursor-pointer transition-colors",
                "hover:bg-[hsl(var(--muted))]",
                highlightedIndex === index && "bg-[hsl(var(--muted))]",
              )}
              onClick={() => onSelect(patient)}
              onMouseEnter={() => setHighlightedIndex(index)}
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {patient.full_name}
                </p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  {patient.document_type}: {patient.document_number}
                </p>
              </div>
              {!patient.is_active && (
                <span className="shrink-0 ml-2 text-[10px] text-yellow-600 font-medium">
                  Inactivo
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
