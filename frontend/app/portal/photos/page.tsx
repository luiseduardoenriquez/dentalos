"use client";

import { useState } from "react";
import { usePortalPhotos } from "@/lib/hooks/use-portal";

export default function PortalPhotos() {
  const { data, isLoading, isError, error, refetch } = usePortalPhotos();
  const photos = data?.data ?? [];
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  // Group by tooth number
  const grouped = photos.reduce<Record<number, typeof photos>>((acc, photo) => {
    if (!acc[photo.tooth_number]) acc[photo.tooth_number] = [];
    acc[photo.tooth_number].push(photo);
    return acc;
  }, {});

  const toothNumbers = Object.keys(grouped).map(Number).sort((a, b) => a - b);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Mis fotos</h1>

      {isLoading ? (
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="aspect-square rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-red-600 dark:text-red-400 font-medium">Error al cargar los datos</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {error instanceof Error ? error.message : "Ocurrió un error inesperado."}
          </p>
          <button onClick={() => refetch()} className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors">
            Reintentar
          </button>
        </div>
      ) : photos.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">No tienes fotos dentales aún</p>
        </div>
      ) : (
        <div className="space-y-6">
          {toothNumbers.map((tooth) => (
            <div key={tooth}>
              <h2 className="text-sm font-semibold text-[hsl(var(--foreground))] mb-3">
                Diente {tooth}
              </h2>
              <div className="grid grid-cols-3 gap-3">
                {grouped[tooth].map((photo) => (
                  <button
                    key={photo.id}
                    onClick={() => setLightboxUrl(photo.url)}
                    className="relative aspect-square rounded-xl overflow-hidden border border-[hsl(var(--border))] hover:ring-2 hover:ring-primary-400 transition-all group"
                  >
                    <img
                      src={photo.thumbnail_url || photo.url}
                      alt={`Diente ${photo.tooth_number}`}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute bottom-0 inset-x-0 bg-black/50 py-1 px-2">
                      <p className="text-xs text-white">
                        {new Date(photo.created_at).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "2-digit" })}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Lightbox */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setLightboxUrl(null)}
        >
          <div className="relative max-w-3xl max-h-[80vh]">
            <img
              src={lightboxUrl}
              alt="Foto dental"
              className="max-w-full max-h-[80vh] rounded-lg object-contain"
            />
            <button
              onClick={() => setLightboxUrl(null)}
              className="absolute top-2 right-2 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
