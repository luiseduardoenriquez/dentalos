"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Loader2, X } from "lucide-react";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CatalogItem {
  code: string;
  description: string;
}

interface Cie10Item {
  code: string;
  description: string;
}

interface CupsItem {
  code: string;
  description: string;
}

export interface CatalogSearchProps {
  type: "cie10" | "cups";
  value: string;
  onSelect: (code: string, description: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildEndpoint(type: "cie10" | "cups", query: string): string {
  if (type === "cie10") {
    return `/catalog/cie10?q=${encodeURIComponent(query)}`;
  }
  return `/catalog/cups?q=${encodeURIComponent(query)}`;
}

function mapToItems(type: "cie10" | "cups", data: unknown): CatalogItem[] {
  if (!Array.isArray(data)) return [];
  if (type === "cie10") {
    return (data as Cie10Item[]).map((item) => ({
      code: item.code,
      description: item.description,
    }));
  }
  return (data as CupsItem[]).map((item) => ({
    code: item.code,
    description: item.description,
  }));
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Reusable CIE-10 / CUPS autocomplete search component.
 *
 * Provides a debounced (300ms) search input that queries the backend catalog
 * and shows a dropdown with code + description results. Selecting an item calls
 * `onSelect(code, description)` — the parent is responsible for storing the values.
 *
 * @example
 * <CatalogSearch
 *   type="cie10"
 *   value={field.value}
 *   onSelect={(code, desc) => { setValue("cie10_code", code); setValue("cie10_description", desc); }}
 *   placeholder="Buscar diagnóstico CIE-10..."
 * />
 */
export function CatalogSearch({
  type,
  value,
  onSelect,
  placeholder,
  className,
  disabled = false,
}: CatalogSearchProps) {
  const [query, setQuery] = React.useState("");
  const [debouncedQuery, setDebouncedQuery] = React.useState("");
  const [isOpen, setIsOpen] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(-1);

  const containerRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const defaultPlaceholder = type === "cie10" ? "Buscar código CIE-10..." : "Buscar código CUPS...";

  // Debounce the search query — 300ms
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Reset active index when results change
  React.useEffect(() => {
    setActiveIndex(-1);
  }, [debouncedQuery]);

  const isQueryValid = debouncedQuery.length >= 2;

  const { data: rawData, isFetching } = useQuery({
    queryKey: ["catalog", type, debouncedQuery],
    queryFn: () => apiGet<unknown>(buildEndpoint(type, debouncedQuery)),
    enabled: isQueryValid,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours — catalog data is static
  });

  const results: CatalogItem[] = rawData ? mapToItems(type, rawData) : [];

  const showDropdown = isOpen && isQueryValid;

  // Click outside closes dropdown
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
          selectItem(results[activeIndex]);
        }
        break;
    }
  }

  function selectItem(item: CatalogItem) {
    onSelect(item.code, item.description);
    setQuery("");
    setIsOpen(false);
    setActiveIndex(-1);
  }

  function handleClear(e: React.MouseEvent) {
    e.stopPropagation();
    onSelect("", "");
    setQuery("");
    setIsOpen(false);
    inputRef.current?.focus();
  }

  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      {/* Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))] pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={showDropdown}
          aria-autocomplete="list"
          aria-controls="catalog-search-listbox"
          aria-activedescendant={activeIndex >= 0 ? `catalog-option-${activeIndex}` : undefined}
          placeholder={placeholder ?? defaultPlaceholder}
          value={value || query}
          onChange={handleChange}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          autoComplete="off"
          className={cn(
            "w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
            "pl-9 pr-9 py-2 text-sm",
            "placeholder:text-[hsl(var(--muted-foreground))]",
            "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "transition-colors duration-150",
            isOpen && "ring-2 ring-primary-600",
          )}
        />
        {/* Clear button — shown when there is a selected value */}
        {value && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            aria-label="Limpiar selección"
            className={cn(
              "absolute right-3 top-1/2 -translate-y-1/2",
              "h-4 w-4 rounded-sm text-[hsl(var(--muted-foreground))]",
              "hover:text-foreground transition-colors",
            )}
          >
            <X className="h-4 w-4" />
          </button>
        )}
        {/* Loading spinner — shown when fetching and no clear button */}
        {isFetching && !value && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-[hsl(var(--muted-foreground))]" />
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div
          id="catalog-search-listbox"
          role="listbox"
          aria-label={type === "cie10" ? "Resultados CIE-10" : "Resultados CUPS"}
          className={cn(
            "absolute z-50 mt-1 w-full",
            "rounded-lg border border-[hsl(var(--border))]",
            "bg-white dark:bg-zinc-900",
            "shadow-lg max-h-64 overflow-y-auto",
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
              {results.map((item, idx) => (
                <li
                  key={item.code}
                  id={`catalog-option-${idx}`}
                  role="option"
                  aria-selected={activeIndex === idx}
                  onClick={() => selectItem(item)}
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={cn(
                    "flex items-start gap-3 px-3 py-2.5 cursor-pointer",
                    "transition-colors",
                    activeIndex === idx
                      ? "bg-primary-50 dark:bg-primary-900/20"
                      : "hover:bg-[hsl(var(--muted))]",
                  )}
                >
                  <span className="mt-0.5 shrink-0 rounded bg-primary-100 dark:bg-primary-900/30 px-1.5 py-0.5 text-xs font-mono font-semibold text-primary-700 dark:text-primary-300">
                    {item.code}
                  </span>
                  <span className="text-sm text-foreground leading-snug">{item.description}</span>
                </li>
              ))}
            </ul>
          )}

          {/* Empty state */}
          {!isFetching && results.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-center px-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No se encontraron resultados para{" "}
                <span className="font-medium text-foreground">&ldquo;{debouncedQuery}&rdquo;</span>
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                Intenta con otro término de búsqueda
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
