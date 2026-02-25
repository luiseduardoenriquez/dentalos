"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2, UserX } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useSearchPatients } from "@/lib/hooks/use-patients";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PatientSearchBarProps {
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Global patient search bar for the dashboard header.
 *
 * - Expands on focus to show a results dropdown.
 * - Debounced search (300ms, min 2 chars).
 * - Clicking a result navigates to /patients/{id}.
 * - Click outside or Escape closes the dropdown.
 */
export function PatientSearchBar({ className }: PatientSearchBarProps) {
  const router = useRouter();

  const [query, setQuery] = React.useState("");
  const [isOpen, setIsOpen] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(-1);

  const containerRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const { data: results = [], isFetching } = useSearchPatients(query, 300);

  const hasQuery = query.trim().length >= 2;
  const showDropdown = isOpen && hasQuery;

  // ─── Click outside to close ────────────────────────────────────────────────
  React.useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setActiveIndex(-1);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // ─── Reset active index when results change ────────────────────────────────
  React.useEffect(() => {
    setActiveIndex(-1);
  }, [results]);

  // ─── Handlers ─────────────────────────────────────────────────────────────

  function handleFocus() {
    setIsOpen(true);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value);
    setIsOpen(true);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showDropdown) return;

    switch (e.key) {
      case "Escape":
        setIsOpen(false);
        setActiveIndex(-1);
        inputRef.current?.blur();
        break;
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

  function navigateToPatient(patientId: string) {
    setIsOpen(false);
    setQuery("");
    setActiveIndex(-1);
    router.push(`/patients/${patientId}`);
  }

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div ref={containerRef} className={cn("relative w-full max-w-xs", className)}>
      {/* Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))] pointer-events-none" />
        <input
          ref={inputRef}
          type="search"
          role="combobox"
          aria-expanded={showDropdown}
          aria-autocomplete="list"
          aria-controls="patient-search-listbox"
          aria-activedescendant={activeIndex >= 0 ? `patient-option-${activeIndex}` : undefined}
          placeholder="Buscar pacientes..."
          value={query}
          onChange={handleChange}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          className={cn(
            "w-full rounded-md border border-[hsl(var(--input))] bg-transparent",
            "pl-9 pr-4 py-2 text-sm",
            "shadow-sm placeholder:text-[hsl(var(--muted-foreground))]",
            "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-600",
            "transition-all duration-200",
            isOpen && "ring-1 ring-primary-600",
          )}
        />
        {isFetching && hasQuery && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-[hsl(var(--muted-foreground))]" />
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div
          id="patient-search-listbox"
          role="listbox"
          aria-label="Resultados de búsqueda de pacientes"
          className={cn(
            "absolute z-50 mt-1 w-full min-w-[280px]",
            "rounded-lg border border-[hsl(var(--border))]",
            "bg-white dark:bg-zinc-900",
            "shadow-lg overflow-hidden",
          )}
        >
          {/* Loading state */}
          {isFetching && results.length === 0 && (
            <div className="flex items-center justify-center gap-2 py-6 text-sm text-[hsl(var(--muted-foreground))]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Buscando...
            </div>
          )}

          {/* Results list */}
          {!isFetching && results.length > 0 && (
            <ul className="py-1">
              {results.map((patient, idx) => (
                <li
                  key={patient.id}
                  id={`patient-option-${idx}`}
                  role="option"
                  aria-selected={activeIndex === idx}
                  onClick={() => navigateToPatient(patient.id)}
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={cn(
                    "flex items-center justify-between gap-3 px-3 py-2.5 cursor-pointer",
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
          {!isFetching && results.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-2 py-8 text-center px-4">
              <UserX className="h-6 w-6 text-[hsl(var(--muted-foreground))]" />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No se encontraron pacientes para{" "}
                <span className="font-medium text-foreground">&ldquo;{query}&rdquo;</span>
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
