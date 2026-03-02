import type { Metadata } from "next";
import Link from "next/link";
import { Building2, UserRound } from "lucide-react";

export const metadata: Metadata = {
  title: "Acceso",
  description: "Elige cómo deseas ingresar a DentalOS",
};

const ACCESS_OPTIONS = [
  {
    href: "/login",
    icon: Building2,
    title: "Equipo clínico",
    description: "Doctores, asistentes y recepcionistas",
  },
  {
    href: "/portal/login",
    icon: UserRound,
    title: "Portal paciente",
    description: "Accede a tus citas, tratamientos y documentos",
  },
] as const;

export default function AccesoPage() {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-xl font-semibold text-foreground">
          ¿Cómo deseas ingresar?
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Selecciona el tipo de acceso que necesitas.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {ACCESS_OPTIONS.map((option) => (
          <Link
            key={option.href}
            href={option.href}
            className="group flex flex-col items-center gap-3 rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 p-6 shadow-sm transition-all hover:border-primary-400 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-50 dark:bg-primary-900/30 transition-colors group-hover:bg-primary-100 dark:group-hover:bg-primary-900/50">
              <option.icon
                className="h-6 w-6 text-primary-600 dark:text-primary-400"
                aria-hidden="true"
              />
            </div>
            <div className="text-center">
              <p className="text-sm font-semibold text-foreground">
                {option.title}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {option.description}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
