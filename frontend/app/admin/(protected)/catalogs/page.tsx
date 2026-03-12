"use client";

/**
 * SA-K01: Catalog Administration page.
 *
 * Features:
 * - Tab switching between CIE-10 and CUPS catalogs.
 * - Search bar to filter codes (debounced 400ms).
 * - Paginated table with columns: Código, Descripción, Categoría, Acciones.
 * - "Agregar Código" button opens an inline creation card.
 * - Edit button per row opens an inline edit card below the table.
 * - Pagination controls (Anterior / Siguiente + page indicator).
 * - Loading skeleton rows and error state with retry.
 * - Spanish UI text (es-419).
 * - Indigo accent color scheme for admin pages.
 * - No shadcn imports — plain HTML elements styled with Tailwind.
 */

import React from "react";
import {
  useCatalogCodes,
  useCreateCatalogCode,
  useUpdateCatalogCode,
  type CatalogCodeItem,
} from "@/lib/hooks/use-admin";

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

type CatalogType = "cie10" | "cups";

const CATALOG_LABELS: Record<CatalogType, { title: string; codeHint: string }> =
  {
    cie10: {
      title: "CIE-10",
      codeHint: "ej: A00.0 (letra + 2 dígitos + decimal opcional)",
    },
    cups: {
      title: "CUPS",
      codeHint: "ej: 890302 (6 dígitos numéricos)",
    },
  };

// ─── Helpers ──────────────────────────────────────────────────────────────────

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function TableLoadingSkeleton() {
  return (
    <>
      {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <tr key={i} className="border-b border-[hsl(var(--border))]">
          <td className="px-4 py-3">
            <div className="h-4 w-20 animate-pulse rounded bg-[hsl(var(--muted))]" />
          </td>
          <td className="px-4 py-3">
            <div className="h-4 w-64 animate-pulse rounded bg-[hsl(var(--muted))]" />
          </td>
          <td className="px-4 py-3">
            <div className="h-4 w-28 animate-pulse rounded bg-[hsl(var(--muted))]" />
          </td>
          <td className="px-4 py-3">
            <div className="h-7 w-14 animate-pulse rounded bg-[hsl(var(--muted))]" />
          </td>
        </tr>
      ))}
    </>
  );
}

// ─── Create Code Card ─────────────────────────────────────────────────────────

interface CreateCodeCardProps {
  catalogType: CatalogType;
  onClose: () => void;
}

function CreateCodeCard({ catalogType, onClose }: CreateCodeCardProps) {
  const createCode = useCreateCatalogCode();
  const [code, setCode] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  const hint = CATALOG_LABELS[catalogType].codeHint;

  function handleReset() {
    setCode("");
    setDescription("");
    setCategory("");
    setErrorMsg(null);
    setSuccessMsg(null);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    const trimmedCode = code.trim();
    const trimmedDesc = description.trim();
    if (!trimmedCode || !trimmedDesc) {
      setErrorMsg("El código y la descripción son obligatorios.");
      return;
    }

    createCode.mutate(
      {
        catalogType,
        data: {
          code: trimmedCode,
          description: trimmedDesc,
          category: category.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          setSuccessMsg(`Código "${trimmedCode}" agregado correctamente.`);
          handleReset();
        },
        onError: () => {
          setErrorMsg("No se pudo agregar el código. Verifica que no exista ya.");
        },
      }
    );
  }

  return (
    <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-800 dark:bg-indigo-950/30">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-indigo-900 dark:text-indigo-200">
          Agregar código {CATALOG_LABELS[catalogType].title}
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1 text-indigo-600 hover:bg-indigo-100 hover:text-indigo-800 dark:text-indigo-400 dark:hover:bg-indigo-900 dark:hover:text-indigo-200"
          aria-label="Cerrar formulario"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-3">
        {/* Code */}
        <div className="space-y-1">
          <label
            htmlFor="create-code"
            className="block text-xs font-medium text-[hsl(var(--foreground))]"
          >
            Código <span className="text-red-500">*</span>
          </label>
          <input
            id="create-code"
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={hint}
            className="w-full rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 font-mono text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:bg-[hsl(var(--card))]"
            autoComplete="off"
            spellCheck={false}
            maxLength={20}
          />
        </div>

        {/* Description */}
        <div className="space-y-1 sm:col-span-2">
          <label
            htmlFor="create-description"
            className="block text-xs font-medium text-[hsl(var(--foreground))]"
          >
            Descripción <span className="text-red-500">*</span>
          </label>
          <input
            id="create-description"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Descripción completa del código"
            className="w-full rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:bg-[hsl(var(--card))]"
            autoComplete="off"
            maxLength={500}
          />
        </div>

        {/* Category */}
        <div className="space-y-1">
          <label
            htmlFor="create-category"
            className="block text-xs font-medium text-[hsl(var(--foreground))]"
          >
            Categoría{" "}
            <span className="text-[hsl(var(--muted-foreground))]">(opcional)</span>
          </label>
          <input
            id="create-category"
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="ej: Enfermedades infecciosas"
            className="w-full rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:bg-[hsl(var(--card))]"
            autoComplete="off"
            maxLength={200}
          />
        </div>

        {/* Feedback + actions */}
        <div className="flex items-end gap-2 sm:col-span-2">
          {errorMsg && (
            <p className="flex-1 text-xs text-red-600 dark:text-red-400">{errorMsg}</p>
          )}
          {successMsg && (
            <p className="flex-1 text-xs text-emerald-700 dark:text-emerald-400">{successMsg}</p>
          )}
          {!errorMsg && !successMsg && <div className="flex-1" />}

          <button
            type="button"
            onClick={() => { handleReset(); onClose(); }}
            disabled={createCode.isPending}
            className="rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 text-xs font-medium text-[hsl(var(--foreground))] shadow-sm hover:bg-[hsl(var(--muted))] disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[hsl(var(--card))]"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={createCode.isPending || !code.trim() || !description.trim()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {createCode.isPending ? "Guardando..." : "Agregar"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ─── Edit Code Card ───────────────────────────────────────────────────────────

interface EditCodeCardProps {
  item: CatalogCodeItem;
  catalogType: CatalogType;
  onClose: () => void;
}

function EditCodeCard({ item, catalogType, onClose }: EditCodeCardProps) {
  const updateCode = useUpdateCatalogCode();
  const [description, setDescription] = React.useState(item.description);
  const [category, setCategory] = React.useState(item.category ?? "");
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  // Sync state if item changes (e.g., after invalidation)
  React.useEffect(() => {
    setDescription(item.description);
    setCategory(item.category ?? "");
    setErrorMsg(null);
    setSuccessMsg(null);
  }, [item.id]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    const trimmedDesc = description.trim();
    if (!trimmedDesc) {
      setErrorMsg("La descripción no puede estar vacía.");
      return;
    }

    updateCode.mutate(
      {
        catalogType,
        codeId: item.id,
        data: {
          description: trimmedDesc,
          category: category.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          setSuccessMsg("Código actualizado correctamente.");
        },
        onError: () => {
          setErrorMsg("No se pudo actualizar el código. Intenta de nuevo.");
        },
      }
    );
  }

  return (
    <tr className="bg-indigo-50/50 dark:bg-indigo-950/20">
      <td colSpan={4} className="px-4 py-3">
        <div className="flex items-start gap-2">
          <span className="mt-1.5 font-mono text-sm font-semibold text-indigo-700 dark:text-indigo-300">
            {item.code}
          </span>
          <form onSubmit={handleSubmit} className="flex flex-1 flex-wrap items-end gap-2">
            {/* Description */}
            <div className="min-w-[240px] flex-1 space-y-1">
              <label
                htmlFor={`edit-desc-${item.id}`}
                className="block text-xs font-medium text-[hsl(var(--foreground))]"
              >
                Descripción <span className="text-red-500">*</span>
              </label>
              <input
                id={`edit-desc-${item.id}`}
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:bg-[hsl(var(--card))]"
                maxLength={500}
                autoComplete="off"
              />
            </div>

            {/* Category */}
            <div className="w-44 space-y-1">
              <label
                htmlFor={`edit-cat-${item.id}`}
                className="block text-xs font-medium text-[hsl(var(--foreground))]"
              >
                Categoría
              </label>
              <input
                id={`edit-cat-${item.id}`}
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:bg-[hsl(var(--card))]"
                maxLength={200}
                autoComplete="off"
              />
            </div>

            {/* Feedback + actions */}
            <div className="flex items-center gap-2 self-end">
              {errorMsg && (
                <span className="text-xs text-red-600 dark:text-red-400">{errorMsg}</span>
              )}
              {successMsg && (
                <span className="text-xs text-emerald-700 dark:text-emerald-400">{successMsg}</span>
              )}
              <button
                type="button"
                onClick={onClose}
                disabled={updateCode.isPending}
                className="rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 text-xs font-medium text-[hsl(var(--foreground))] shadow-sm hover:bg-[hsl(var(--muted))] disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[hsl(var(--card))]"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={updateCode.isPending || !description.trim()}
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {updateCode.isPending ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </form>
        </div>
      </td>
    </tr>
  );
}

// ─── Catalog Table ─────────────────────────────────────────────────────────────

interface CatalogTableProps {
  catalogType: CatalogType;
  search: string;
  page: number;
  onPageChange: (page: number) => void;
}

function CatalogTable({ catalogType, search, page, onPageChange }: CatalogTableProps) {
  const [editingId, setEditingId] = React.useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useCatalogCodes(catalogType, {
    search: search || undefined,
    page,
    page_size: PAGE_SIZE,
  });

  // Reset editing row and page when catalog type or search changes
  React.useEffect(() => {
    setEditingId(null);
  }, [catalogType, search]);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-3">
      {/* Error state */}
      {isError && !isLoading && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-6 text-center dark:border-red-800 dark:bg-red-950/30">
          <p className="text-sm text-red-700 dark:text-red-300">
            Error al cargar los códigos. Verifica la conexión con la API.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-3 rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 dark:border-red-700 dark:bg-transparent dark:text-red-300 dark:hover:bg-red-950"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Table */}
      {!isError && (
        <div className="overflow-x-auto rounded-lg border border-[hsl(var(--border))]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted))]/50">
                <th className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                  Código
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                  Descripción
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                  Categoría
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {/* Loading skeleton */}
              {isLoading && <TableLoadingSkeleton />}

              {/* Empty state */}
              {!isLoading && items.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-12 text-center text-[hsl(var(--muted-foreground))]"
                  >
                    {search
                      ? `Sin resultados para "${search}" en ${CATALOG_LABELS[catalogType].title}.`
                      : `No hay códigos ${CATALOG_LABELS[catalogType].title} registrados.`}
                  </td>
                </tr>
              )}

              {/* Data rows */}
              {!isLoading &&
                items.map((item) => (
                  <React.Fragment key={item.id}>
                    <tr
                      className={
                        editingId === item.id
                          ? "bg-indigo-50/50 dark:bg-indigo-950/20"
                          : "bg-white hover:bg-[hsl(var(--muted))]/30 dark:bg-[hsl(var(--card))] dark:hover:bg-[hsl(var(--muted))]/20"
                      }
                    >
                      {/* Code */}
                      <td className="whitespace-nowrap px-4 py-3">
                        <span className="rounded bg-[hsl(var(--muted))] px-1.5 py-0.5 font-mono text-xs font-semibold text-[hsl(var(--foreground))]">
                          {item.code}
                        </span>
                      </td>

                      {/* Description */}
                      <td className="px-4 py-3 text-[hsl(var(--foreground))]">
                        {item.description}
                      </td>

                      {/* Category */}
                      <td className="px-4 py-3">
                        {item.category ? (
                          <span className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300">
                            {item.category}
                          </span>
                        ) : (
                          <span className="text-[hsl(var(--muted-foreground))]">—</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={() =>
                            setEditingId(editingId === item.id ? null : item.id)
                          }
                          className={
                            editingId === item.id
                              ? "rounded-md border border-indigo-300 bg-indigo-100 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 dark:border-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300"
                              : "rounded-md border border-[hsl(var(--border))] bg-white px-2.5 py-1 text-xs font-medium text-[hsl(var(--foreground))] shadow-sm hover:bg-[hsl(var(--muted))] dark:bg-[hsl(var(--card))]"
                          }
                        >
                          {editingId === item.id ? "Cancelar" : "Editar"}
                        </button>
                      </td>
                    </tr>

                    {/* Inline edit row */}
                    {editingId === item.id && (
                      <EditCodeCard
                        key={`edit-${item.id}`}
                        item={item}
                        catalogType={catalogType}
                        onClose={() => setEditingId(null)}
                      />
                    )}
                  </React.Fragment>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {!isLoading && !isError && total > 0 && (
        <div className="flex items-center justify-between gap-4">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            {total.toLocaleString("es-CO")} código{total !== 1 ? "s" : ""} en total
            {search ? ` · filtrados por "${search}"` : ""}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 text-xs font-medium text-[hsl(var(--foreground))] shadow-sm hover:bg-[hsl(var(--muted))] disabled:cursor-not-allowed disabled:opacity-40 dark:bg-[hsl(var(--card))]"
            >
              Anterior
            </button>
            <span className="min-w-[6rem] text-center text-xs text-[hsl(var(--muted-foreground))]">
              Página {page} de {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className="rounded-md border border-[hsl(var(--border))] bg-white px-3 py-1.5 text-xs font-medium text-[hsl(var(--foreground))] shadow-sm hover:bg-[hsl(var(--muted))] disabled:cursor-not-allowed disabled:opacity-40 dark:bg-[hsl(var(--card))]"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminCatalogsPage() {
  const [activeTab, setActiveTab] = React.useState<CatalogType>("cie10");
  const [searchInput, setSearchInput] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [showCreate, setShowCreate] = React.useState(false);

  const debouncedSearch = useDebounce(searchInput, 400);

  // Reset to page 1 when search or tab changes
  React.useEffect(() => {
    setPage(1);
    setShowCreate(false);
  }, [debouncedSearch, activeTab]);

  function handleTabChange(tab: CatalogType) {
    if (tab === activeTab) return;
    setActiveTab(tab);
    setSearchInput("");
    setShowCreate(false);
    setPage(1);
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Catálogos médicos
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Administra los códigos CIE-10 y CUPS disponibles en la plataforma.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate((v) => !v)}
          className={
            showCreate
              ? "inline-flex items-center gap-2 rounded-lg border border-indigo-300 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 shadow-sm hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300 dark:hover:bg-indigo-950/60"
              : "inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
          }
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            {showCreate ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            )}
          </svg>
          {showCreate ? "Cancelar" : "Agregar Código"}
        </button>
      </div>

      {/* Main card */}
      <div className="rounded-xl border border-[hsl(var(--border))] bg-white shadow-sm dark:bg-[hsl(var(--card))]">

        {/* Tab bar */}
        <div className="flex border-b border-[hsl(var(--border))]">
          {(["cie10", "cups"] as CatalogType[]).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => handleTabChange(tab)}
              className={[
                "relative px-6 py-3.5 text-sm font-medium transition-colors focus:outline-none",
                activeTab === tab
                  ? "text-indigo-700 dark:text-indigo-300"
                  : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]",
              ].join(" ")}
              aria-selected={activeTab === tab}
              role="tab"
            >
              {CATALOG_LABELS[tab].title}
              {activeTab === tab && (
                <span
                  className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-indigo-600 dark:bg-indigo-400"
                  aria-hidden="true"
                />
              )}
            </button>
          ))}
        </div>

        {/* Toolbar: search */}
        <div className="flex items-center gap-3 border-b border-[hsl(var(--border))] px-4 py-3">
          <div className="relative flex-1 max-w-sm">
            <svg
              className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted-foreground))]"
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
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={`Buscar en ${CATALOG_LABELS[activeTab].title}...`}
              className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] py-1.5 pl-8 pr-3 text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
            />
          </div>
          {searchInput && (
            <button
              type="button"
              onClick={() => setSearchInput("")}
              className="rounded-md border border-[hsl(var(--border))] bg-white px-2.5 py-1.5 text-xs font-medium text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] dark:bg-[hsl(var(--card))]"
            >
              Limpiar
            </button>
          )}
        </div>

        {/* Create form (shown inline inside the card, above the table) */}
        {showCreate && (
          <div className="border-b border-[hsl(var(--border))] px-4 py-4">
            <CreateCodeCard
              catalogType={activeTab}
              onClose={() => setShowCreate(false)}
            />
          </div>
        )}

        {/* Table area */}
        <div className="p-4">
          <CatalogTable
            catalogType={activeTab}
            search={debouncedSearch}
            page={page}
            onPageChange={setPage}
          />
        </div>
      </div>
    </div>
  );
}
