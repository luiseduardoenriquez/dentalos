import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="text-center max-w-md">
        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="h-20 w-20 rounded-full bg-muted flex items-center justify-center">
            <FileQuestion className="h-10 w-10 text-muted-foreground" />
          </div>
        </div>

        {/* Status code */}
        <p className="text-sm font-semibold text-primary-600 uppercase tracking-widest mb-2">
          Error 404
        </p>

        {/* Heading */}
        <h1 className="text-3xl font-bold text-foreground mb-3">Página no encontrada</h1>

        {/* Description */}
        <p className="text-muted-foreground mb-8">
          La página que buscas no existe o ha sido movida. Verifica la dirección o regresa al
          inicio.
        </p>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-md bg-primary-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-primary-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-colors"
          >
            Iniciar sesión
          </Link>
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-border bg-background px-6 py-2.5 text-sm font-semibold text-foreground shadow-sm hover:bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring transition-colors"
          >
            Ir al inicio
          </Link>
        </div>
      </div>
    </div>
  );
}
