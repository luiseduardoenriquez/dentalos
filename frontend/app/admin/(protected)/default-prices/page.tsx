"use client";

import React from "react";
import {
  useDefaultPrices,
  useUpsertDefaultPrice,
  type DefaultPriceItem,
} from "@/lib/hooks/use-admin";

// ─── Constants ─────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

const COUNTRY_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "Todos los países" },
  { value: "CO", label: "Colombia (CO)" },
  { value: "MX", label: "México (MX)" },
  { value: "PE", label: "Perú (PE)" },
  { value: "CL", label: "Chile (CL)" },
  { value: "AR", label: "Argentina (AR)" },
];

const COUNTRY_LABELS: Record<string, string> = {
  CO: "Colombia",
  MX: "México",
  PE: "Perú",
  CL: "Chile",
  AR: "Argentina",
};

const CURRENCY_DEFAULTS: Record<string, string> = {
  CO: "COP",
  MX: "MXN",
  PE: "PEN",
  CL: "CLP",
  AR: "ARS",
};

// ─── Helpers ───────────────────────────────────────────────────────────────────

function formatPriceCents(cents: number, currencyCode: string): string {
  try {
    return new Intl.NumberFormat("es-419", {
      style: "currency",
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(cents / 100);
  } catch {
    return `${(cents / 100).toLocaleString("es-419")} ${currencyCode}`;
  }
}

function formatUpdatedAt(iso: string): string {
  try {
    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function getCountryLabel(code: string): string {
  return COUNTRY_LABELS[code] ?? code;
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function TableLoadingSkeleton() {
  return (
    <div className="overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
      {/* Skeleton header */}
      <div className="grid grid-cols-[1fr_2fr_1fr_1fr_1fr_1fr_1fr] gap-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--muted))]/40 px-4 py-3">
        {["Código CUPS", "Descripción", "País", "Precio", "Moneda", "Estado", "Acciones"].map(
          (col) => (
            <div
              key={col}
              className="h-4 w-20 animate-pulse rounded bg-[hsl(var(--muted))]"
            />
          )
        )}
      </div>
      {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <div
          key={i}
          className="grid grid-cols-[1fr_2fr_1fr_1fr_1fr_1fr_1fr] gap-4 border-b border-[hsl(var(--border))] px-4 py-3 last:border-0"
        >
          <div className="h-4 w-16 animate-pulse rounded bg-[hsl(var(--muted))]" />
          <div className="h-4 w-48 animate-pulse rounded bg-[hsl(var(--muted))]" />
          <div className="h-5 w-12 animate-pulse rounded-full bg-[hsl(var(--muted))]" />
          <div className="h-4 w-20 animate-pulse rounded bg-[hsl(var(--muted))]" />
          <div className="h-4 w-10 animate-pulse rounded bg-[hsl(var(--muted))]" />
          <div className="h-5 w-14 animate-pulse rounded-full bg-[hsl(var(--muted))]" />
          <div className="h-7 w-14 animate-pulse rounded bg-[hsl(var(--muted))]" />
        </div>
      ))}
    </div>
  );
}

// ─── Country Badge ─────────────────────────────────────────────────────────────

const COUNTRY_BADGE_STYLES: Record<string, string> = {
  CO: "border-yellow-300 bg-yellow-50 text-yellow-700 dark:border-yellow-700 dark:bg-yellow-950 dark:text-yellow-300",
  MX: "border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300",
  PE: "border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300",
  CL: "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300",
  AR: "border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-700 dark:bg-sky-950 dark:text-sky-300",
};

function CountryBadge({ code }: { code: string }) {
  const colorClass =
    COUNTRY_BADGE_STYLES[code] ??
    "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${colorClass}`}
    >
      {code}
    </span>
  );
}

// ─── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ isActive }: { isActive: boolean }) {
  if (isActive) {
    return (
      <span className="inline-flex items-center rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
        Activo
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-2 py-0.5 text-xs font-medium text-[hsl(var(--muted-foreground))]">
      Inactivo
    </span>
  );
}

// ─── Inline Add/Edit Form ──────────────────────────────────────────────────────

interface PriceFormState {
  cups_code: string;
  cups_description: string;
  country_code: string;
  price_dollars: string; // user enters dollars, we convert to cents on submit
  currency_code: string;
}

const EMPTY_FORM: PriceFormState = {
  cups_code: "",
  cups_description: "",
  country_code: "CO",
  price_dollars: "",
  currency_code: "COP",
};

interface InlinePriceFormProps {
  initialValues?: DefaultPriceItem | null;
  onCancel: () => void;
  onSuccess: () => void;
}

function InlinePriceForm({
  initialValues,
  onCancel,
  onSuccess,
}: InlinePriceFormProps) {
  const upsert = useUpsertDefaultPrice();
  const isEditing = Boolean(initialValues);

  const [form, setForm] = React.useState<PriceFormState>(() => {
    if (initialValues) {
      return {
        cups_code: initialValues.cups_code,
        cups_description: initialValues.cups_description,
        country_code: initialValues.country_code,
        price_dollars: String(initialValues.price_cents / 100),
        currency_code: initialValues.currency_code,
      };
    }
    return EMPTY_FORM;
  });

  const [errors, setErrors] = React.useState<Partial<Record<keyof PriceFormState, string>>>({});

  // When country changes, auto-fill currency if user hasn't overridden it
  function handleCountryChange(value: string) {
    const currency = CURRENCY_DEFAULTS[value] ?? form.currency_code;
    setForm((prev) => ({ ...prev, country_code: value, currency_code: currency }));
  }

  function validate(): boolean {
    const next: typeof errors = {};
    if (!form.cups_code.trim()) {
      next.cups_code = "El código CUPS es obligatorio.";
    } else if (!/^\d{6}$/.test(form.cups_code.trim())) {
      next.cups_code = "El código CUPS debe tener exactamente 6 dígitos.";
    }
    if (!form.cups_description.trim()) {
      next.cups_description = "La descripción es obligatoria.";
    }
    if (!form.country_code) {
      next.country_code = "El país es obligatorio.";
    }
    const priceNum = parseFloat(form.price_dollars);
    if (!form.price_dollars.trim() || isNaN(priceNum) || priceNum < 0) {
      next.price_dollars = "Ingresa un precio válido (mayor o igual a 0).";
    }
    if (!form.currency_code.trim()) {
      next.currency_code = "El código de moneda es obligatorio.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const priceCents = Math.round(parseFloat(form.price_dollars) * 100);

    upsert.mutate(
      {
        cups_code: form.cups_code.trim(),
        cups_description: form.cups_description.trim(),
        country_code: form.country_code,
        price_cents: priceCents,
        currency_code: form.currency_code.trim().toUpperCase(),
      },
      {
        onSuccess: () => {
          onSuccess();
        },
      }
    );
  }

  const inputBase =
    "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";
  const inputError = "border-red-500 dark:border-red-400 focus:ring-red-500";
  const selectBase =
    "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";
  const labelBase = "block text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1";
  const errorText = "mt-1 text-xs text-red-600 dark:text-red-400";

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-indigo-200 bg-indigo-50/40 p-4 dark:border-indigo-800 dark:bg-indigo-950/20"
      noValidate
    >
      <h3 className="mb-4 text-sm font-semibold text-foreground">
        {isEditing ? "Editar precio" : "Agregar nuevo precio"}
      </h3>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* CUPS Code */}
        <div>
          <label htmlFor="form-cups-code" className={labelBase}>
            Código CUPS <span className="text-red-500">*</span>
          </label>
          <input
            id="form-cups-code"
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="ej: 890201"
            value={form.cups_code}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, cups_code: e.target.value.replace(/\D/g, "") }))
            }
            disabled={isEditing}
            className={`${inputBase} font-mono ${errors.cups_code ? inputError : ""} ${isEditing ? "cursor-not-allowed opacity-60 bg-[hsl(var(--muted))]" : ""}`}
            aria-describedby={errors.cups_code ? "form-cups-code-error" : undefined}
          />
          {errors.cups_code && (
            <p id="form-cups-code-error" className={errorText}>
              {errors.cups_code}
            </p>
          )}
          {isEditing && (
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              El código CUPS no se puede modificar.
            </p>
          )}
        </div>

        {/* Description */}
        <div className="sm:col-span-1 lg:col-span-2">
          <label htmlFor="form-description" className={labelBase}>
            Descripción <span className="text-red-500">*</span>
          </label>
          <input
            id="form-description"
            type="text"
            placeholder="ej: Consulta odontológica de primera vez"
            value={form.cups_description}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, cups_description: e.target.value }))
            }
            className={`${inputBase} ${errors.cups_description ? inputError : ""}`}
            aria-describedby={errors.cups_description ? "form-description-error" : undefined}
          />
          {errors.cups_description && (
            <p id="form-description-error" className={errorText}>
              {errors.cups_description}
            </p>
          )}
        </div>

        {/* Country */}
        <div>
          <label htmlFor="form-country" className={labelBase}>
            País <span className="text-red-500">*</span>
          </label>
          <select
            id="form-country"
            value={form.country_code}
            onChange={(e) => handleCountryChange(e.target.value)}
            className={`${selectBase} ${errors.country_code ? inputError : ""}`}
            aria-describedby={errors.country_code ? "form-country-error" : undefined}
          >
            {COUNTRY_OPTIONS.filter((c) => c.value !== "").map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {errors.country_code && (
            <p id="form-country-error" className={errorText}>
              {errors.country_code}
            </p>
          )}
        </div>

        {/* Price */}
        <div>
          <label htmlFor="form-price" className={labelBase}>
            Precio <span className="text-red-500">*</span>
          </label>
          <input
            id="form-price"
            type="number"
            min="0"
            step="0.01"
            placeholder="ej: 45000"
            value={form.price_dollars}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, price_dollars: e.target.value }))
            }
            className={`${inputBase} ${errors.price_dollars ? inputError : ""}`}
            aria-describedby={errors.price_dollars ? "form-price-error" : undefined}
          />
          {errors.price_dollars && (
            <p id="form-price-error" className={errorText}>
              {errors.price_dollars}
            </p>
          )}
          <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
            Ingresa el valor en la moneda seleccionada (sin centavos para COP/CLP).
          </p>
        </div>

        {/* Currency */}
        <div>
          <label htmlFor="form-currency" className={labelBase}>
            Moneda <span className="text-red-500">*</span>
          </label>
          <input
            id="form-currency"
            type="text"
            maxLength={3}
            placeholder="ej: COP"
            value={form.currency_code}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                currency_code: e.target.value.toUpperCase(),
              }))
            }
            className={`${inputBase} font-mono uppercase ${errors.currency_code ? inputError : ""}`}
            aria-describedby={errors.currency_code ? "form-currency-error" : undefined}
          />
          {errors.currency_code && (
            <p id="form-currency-error" className={errorText}>
              {errors.currency_code}
            </p>
          )}
        </div>
      </div>

      {/* Form actions */}
      <div className="mt-4 flex items-center gap-3">
        <button
          type="submit"
          disabled={upsert.isPending}
          className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-indigo-500 dark:hover:bg-indigo-600"
        >
          {upsert.isPending
            ? isEditing
              ? "Guardando..."
              : "Agregando..."
            : isEditing
            ? "Guardar cambios"
            : "Agregar precio"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={upsert.isPending}
          className="inline-flex items-center rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-[hsl(var(--muted))] focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Cancelar
        </button>

        {upsert.isError && (
          <p className="text-sm text-red-600 dark:text-red-400">
            Error al guardar. Intenta de nuevo.
          </p>
        )}
      </div>
    </form>
  );
}

// ─── Pagination ────────────────────────────────────────────────────────────────

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  const btnBase =
    "inline-flex items-center justify-center rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-1.5 text-sm font-medium text-foreground shadow-sm hover:bg-[hsl(var(--muted))] focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-40 transition-colors";

  return (
    <div className="flex items-center justify-between gap-4 pt-4">
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        {total === 0
          ? "Sin resultados"
          : `Mostrando ${from}–${to} de ${total.toLocaleString("es-419")} registros`}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className={btnBase}
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Página anterior"
        >
          ← Anterior
        </button>

        <span className="px-2 text-sm text-foreground tabular-nums">
          {page} / {totalPages}
        </span>

        <button
          type="button"
          className={btnBase}
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          aria-label="Página siguiente"
        >
          Siguiente →
        </button>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DefaultPricesPage() {
  const [countryFilter, setCountryFilter] = React.useState("");
  const [searchInput, setSearchInput] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [showAddForm, setShowAddForm] = React.useState(false);
  const [editingItem, setEditingItem] = React.useState<DefaultPriceItem | null>(null);

  // Debounce the search query (300 ms)
  const searchDebounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  function handleSearchChange(value: string) {
    setSearchInput(value);
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      setSearch(value);
      setPage(1);
    }, 300);
  }

  // Reset page when filters change
  function handleCountryChange(value: string) {
    setCountryFilter(value);
    setPage(1);
  }

  const queryParams = {
    country_code: countryFilter || undefined,
    search: search.trim() || undefined,
    page,
    page_size: PAGE_SIZE,
  };

  const { data, isLoading, isError, refetch, isFetching } = useDefaultPrices(queryParams);

  const items: DefaultPriceItem[] = data?.items ?? [];
  const total = data?.total ?? 0;

  function handleAddSuccess() {
    setShowAddForm(false);
    // Stay on current page — the query cache will be invalidated automatically
  }

  function handleEditSuccess() {
    setEditingItem(null);
  }

  // ─── Shared input/select styling ───────────────────────────────────────────

  const filterSelectBase =
    "h-9 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <div className="flex flex-col gap-6">
      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Precios por Defecto</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Precios predeterminados por procedimiento y país. Se usan como base al crear
            catálogos de clínicas nuevas.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setShowAddForm((prev) => !prev);
            setEditingItem(null);
          }}
          className="inline-flex shrink-0 items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:bg-indigo-500 dark:hover:bg-indigo-600"
        >
          <span aria-hidden="true">+</span>
          Agregar Precio
        </button>
      </div>

      {/* ── Inline Add Form ──────────────────────────────────────────────── */}
      {showAddForm && !editingItem && (
        <InlinePriceForm
          onCancel={() => setShowAddForm(false)}
          onSuccess={handleAddSuccess}
        />
      )}

      {/* ── Filters ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Country filter */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="filter-country"
            className="shrink-0 text-sm font-medium text-foreground"
          >
            País:
          </label>
          <select
            id="filter-country"
            value={countryFilter}
            onChange={(e) => handleCountryChange(e.target.value)}
            className={filterSelectBase}
          >
            {COUNTRY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Search */}
        <div className="relative flex-1 sm:max-w-xs">
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-[hsl(var(--muted-foreground))]">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
              />
            </svg>
          </span>
          <input
            type="search"
            placeholder="Buscar por código o descripción..."
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="h-9 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] py-2 pl-9 pr-3 text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label="Buscar precios"
          />
        </div>

        {/* Result count + fetch indicator */}
        {!isLoading && !isError && (
          <p className="ml-auto text-sm text-[hsl(var(--muted-foreground))]">
            {isFetching ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
                Cargando...
              </span>
            ) : (
              <>
                <span className="font-medium text-foreground tabular-nums">
                  {total.toLocaleString("es-419")}
                </span>{" "}
                {total === 1 ? "resultado" : "resultados"}
              </>
            )}
          </p>
        )}
      </div>

      {/* ── Inline Edit Form ─────────────────────────────────────────────── */}
      {editingItem && (
        <InlinePriceForm
          initialValues={editingItem}
          onCancel={() => setEditingItem(null)}
          onSuccess={handleEditSuccess}
        />
      )}

      {/* ── Loading State ─────────────────────────────────────────────────── */}
      {isLoading && <TableLoadingSkeleton />}

      {/* ── Error State ───────────────────────────────────────────────────── */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] py-16 text-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-50"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
            />
          </svg>
          <p className="text-[hsl(var(--muted-foreground))]">
            Error al cargar los precios. Verifica la conexión con la API.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-[hsl(var(--muted))] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* ── Table ─────────────────────────────────────────────────────────── */}
      {!isLoading && !isError && (
        <>
          {items.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--card))] py-16 text-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-40"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
              <div>
                <p className="font-medium text-foreground">Sin precios configurados</p>
                <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                  {countryFilter || search
                    ? "No se encontraron precios con los filtros actuales."
                    : "Agrega el primer precio predeterminado usando el botón de arriba."}
                </p>
              </div>
              {(countryFilter || search) && (
                <button
                  type="button"
                  onClick={() => {
                    setCountryFilter("");
                    setSearchInput("");
                    setSearch("");
                    setPage(1);
                  }}
                  className="text-sm text-indigo-600 hover:text-indigo-700 hover:underline dark:text-indigo-400 dark:hover:text-indigo-300"
                >
                  Limpiar filtros
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px] text-sm">
                  <thead>
                    <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted))]/40">
                      <th
                        scope="col"
                        className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
                      >
                        Código CUPS
                      </th>
                      <th
                        scope="col"
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
                      >
                        Descripción
                      </th>
                      <th
                        scope="col"
                        className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
                      >
                        País
                      </th>
                      <th
                        scope="col"
                        className="whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
                      >
                        Precio
                      </th>
                      <th
                        scope="col"
                        className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
                      >
                        Moneda
                      </th>
                      <th
                        scope="col"
                        className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
                      >
                        Estado
                      </th>
                      <th
                        scope="col"
                        className="whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
                      >
                        Actualizado
                      </th>
                      <th
                        scope="col"
                        className="whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
                      >
                        Acciones
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[hsl(var(--border))]">
                    {items.map((item) => {
                      const isBeingEdited = editingItem?.id === item.id;
                      return (
                        <tr
                          key={item.id}
                          className={`group transition-colors hover:bg-[hsl(var(--muted))]/30 ${
                            isBeingEdited
                              ? "bg-indigo-50/60 dark:bg-indigo-950/30"
                              : ""
                          }`}
                        >
                          {/* CUPS code */}
                          <td className="whitespace-nowrap px-4 py-3">
                            <code className="rounded bg-[hsl(var(--muted))] px-1.5 py-0.5 font-mono text-xs text-foreground">
                              {item.cups_code}
                            </code>
                          </td>

                          {/* Description */}
                          <td
                            className="max-w-[280px] px-4 py-3 text-sm text-foreground"
                            title={item.cups_description}
                          >
                            <span className="line-clamp-2">{item.cups_description}</span>
                          </td>

                          {/* Country */}
                          <td className="whitespace-nowrap px-4 py-3">
                            <CountryBadge code={item.country_code} />
                            <span className="ml-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                              {getCountryLabel(item.country_code)}
                            </span>
                          </td>

                          {/* Price */}
                          <td className="whitespace-nowrap px-4 py-3 text-right font-medium tabular-nums">
                            {formatPriceCents(item.price_cents, item.currency_code)}
                          </td>

                          {/* Currency */}
                          <td className="whitespace-nowrap px-4 py-3">
                            <span className="font-mono text-xs text-[hsl(var(--muted-foreground))]">
                              {item.currency_code}
                            </span>
                          </td>

                          {/* Status */}
                          <td className="whitespace-nowrap px-4 py-3">
                            <StatusBadge isActive={item.is_active} />
                          </td>

                          {/* Updated at */}
                          <td className="whitespace-nowrap px-4 py-3 text-right text-xs text-[hsl(var(--muted-foreground))]">
                            {formatUpdatedAt(item.updated_at)}
                          </td>

                          {/* Actions */}
                          <td className="whitespace-nowrap px-4 py-3 text-right">
                            <button
                              type="button"
                              onClick={() => {
                                if (isBeingEdited) {
                                  setEditingItem(null);
                                } else {
                                  setShowAddForm(false);
                                  setEditingItem(item);
                                  // Scroll to the edit form (it appears above the table)
                                  window.scrollTo({ top: 0, behavior: "smooth" });
                                }
                              }}
                              className="inline-flex items-center rounded border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-2.5 py-1 text-xs font-medium text-foreground shadow-sm hover:bg-[hsl(var(--muted))] focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 transition-colors"
                            >
                              {isBeingEdited ? "Cancelar" : "Editar"}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="border-t border-[hsl(var(--border))] px-4 pb-3">
                <Pagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  total={total}
                  onPageChange={setPage}
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
