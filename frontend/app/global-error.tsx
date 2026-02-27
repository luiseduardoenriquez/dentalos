"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="es">
      <body>
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
          <div className="text-center max-w-md">
            {/* Icon */}
            <div className="flex justify-center mb-6">
              <div className="h-20 w-20 rounded-full bg-red-50 dark:bg-red-950/30 flex items-center justify-center">
                <AlertTriangle className="h-10 w-10 text-red-500" />
              </div>
            </div>

            {/* Status */}
            <p className="text-sm font-semibold text-red-600 dark:text-red-400 uppercase tracking-widest mb-2">
              Error inesperado
            </p>

            {/* Heading */}
            <h1 className="text-3xl font-bold text-foreground mb-3">
              Algo salió mal
            </h1>

            {/* Description */}
            <p className="text-muted-foreground mb-8">
              Ocurrió un error inesperado en la aplicación. Nuestro equipo ha
              sido notificado. Puedes intentar de nuevo o regresar al inicio.
            </p>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={reset}
                className="inline-flex items-center justify-center rounded-md bg-primary-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-primary-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-colors"
              >
                Intentar de nuevo
              </button>
              <a
                href="/"
                className="inline-flex items-center justify-center rounded-md border border-border bg-background px-6 py-2.5 text-sm font-semibold text-foreground shadow-sm hover:bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 transition-colors"
              >
                Ir al inicio
              </a>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
