"use client";

import { useState, useRef } from "react";
import { usePortalDocuments, usePortalUploadDocument } from "@/lib/hooks/use-portal";
import { toast } from "sonner";

// ─── Types ────────────────────────────────────────────────────────────────────

type DocTypeKey = "consent" | "xray" | "prescription" | undefined;

const DOC_TABS: { key: DocTypeKey; label: string }[] = [
  { key: undefined, label: "Todos" },
  { key: "consent", label: "Consentimientos" },
  { key: "xray", label: "Radiografías" },
  { key: "prescription", label: "Recetas" },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function docTypeIcon(type: string) {
  switch (type) {
    case "consent":
      return (
        <svg
          className="w-5 h-5 text-primary-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      );
    case "xray":
      return (
        <svg
          className="w-5 h-5 text-slate-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      );
    case "prescription":
      return (
        <svg
          className="w-5 h-5 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
          />
        </svg>
      );
    default:
      return (
        <svg
          className="w-5 h-5 text-slate-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
          />
        </svg>
      );
  }
}

function docTypeLabel(type: string) {
  switch (type) {
    case "consent":
      return "Consentimiento";
    case "xray":
      return "Radiografía";
    case "prescription":
      return "Receta";
    default:
      return "Documento";
  }
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortalDocuments() {
  const [docType, setDocType] = useState<DocTypeKey>(undefined);
  const [uploadType, setUploadType] = useState("xray");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = usePortalDocuments(docType);
  const uploadMutation = usePortalUploadDocument();

  const documents = data?.pages.flatMap((p) => p.data) ?? [];

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    uploadMutation.mutate(
      { file, docType: uploadType },
      {
        onSuccess: () => toast.success("Documento subido exitosamente."),
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "Error al subir el documento.",
          ),
      },
    );
    e.target.value = "";
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">
          Documentos
        </h1>
        <div className="flex items-center gap-2">
          <select
            value={uploadType}
            onChange={(e) => setUploadType(e.target.value)}
            className="text-xs rounded-lg border border-[hsl(var(--border))] px-2 py-1.5 bg-white dark:bg-zinc-900"
          >
            <option value="xray">Radiografía</option>
            <option value="insurance_card">Carnet EPS</option>
            <option value="id_document">Documento ID</option>
            <option value="other">Otro</option>
          </select>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending}
            className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {uploadMutation.isPending ? "Subiendo..." : "Subir documento"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,application/pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
      </div>

      {/* Tab filter */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
        {DOC_TABS.map((tab) => (
          <button
            key={tab.label}
            onClick={() => setDocType(tab.key)}
            className={`px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
              docType === tab.key
                ? "bg-primary-600 text-white"
                : "bg-slate-100 dark:bg-zinc-800 text-[hsl(var(--muted-foreground))] hover:bg-slate-200 dark:hover:bg-zinc-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Document list */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse"
            />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-red-600 dark:text-red-400 font-medium">
            Error al cargar los datos
          </p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {error instanceof Error ? error.message : "Ocurrió un error inesperado."}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            Reintentar
          </button>
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">
            No hay documentos disponibles
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => (
            <button
              key={doc.id}
              onClick={() => doc.url && window.open(doc.url, "_blank")}
              disabled={!doc.url}
              className="w-full bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4 flex items-center justify-between hover:border-primary-300 dark:hover:border-primary-700 transition-colors disabled:cursor-not-allowed disabled:opacity-70 text-left"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-zinc-800 flex items-center justify-center shrink-0">
                  {docTypeIcon(doc.document_type)}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[hsl(var(--foreground))] truncate">
                    {doc.name}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {docTypeLabel(doc.document_type)}
                    </p>
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">
                      •
                    </span>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {new Date(doc.created_at).toLocaleDateString("es-CO")}
                    </p>
                    {doc.signed_at && (
                      <>
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">
                          •
                        </span>
                        <p className="text-xs text-green-600 dark:text-green-400">
                          Firmado
                        </p>
                      </>
                    )}
                  </div>
                </div>
              </div>
              {doc.url && (
                <svg
                  className="w-4 h-4 text-[hsl(var(--muted-foreground))] shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              )}
            </button>
          ))}

          {hasNextPage && (
            <button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="w-full py-2 text-sm text-primary-600 hover:text-primary-700 font-medium disabled:opacity-50 transition-colors"
            >
              {isFetchingNextPage ? "Cargando..." : "Ver más"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
