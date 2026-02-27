import Link from "next/link";
import { Stethoscope } from "lucide-react";

const PRODUCTO_LINKS = [
  { href: "/#funciones", label: "Funciones" },
  { href: "/pricing", label: "Precios" },
  { href: "/blog", label: "Blog" },
  { href: "/register", label: "Registrarse" },
];

const LEGAL_LINKS = [
  { href: "/privacy", label: "Politica de privacidad" },
  { href: "/terms", label: "Terminos de servicio" },
  { href: "/security", label: "Seguridad" },
];

const CONTACTO_LINKS = [
  { href: "mailto:hola@dentalos.co", label: "hola@dentalos.co" },
  { href: "https://wa.me/573001234567", label: "WhatsApp" },
];

export function Footer() {
  return (
    <footer className="border-t border-[hsl(var(--border))] bg-slate-50 dark:bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Logo + tagline */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-600">
                <Stethoscope className="w-4 h-4 text-white" aria-hidden="true" />
              </div>
              <span className="text-lg font-bold tracking-tight text-primary-600 select-none">
                DentalOS
              </span>
            </div>
            <p className="text-sm text-slate-500 dark:text-zinc-500 max-w-xs">
              Software dental moderno para clinicas en Colombia y Latinoamerica.
            </p>
          </div>

          {/* Producto */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-zinc-100 mb-3">
              Producto
            </h3>
            <ul className="space-y-2">
              {PRODUCTO_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-500 hover:text-primary-600 dark:text-zinc-500 dark:hover:text-primary-400 transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-zinc-100 mb-3">
              Legal
            </h3>
            <ul className="space-y-2">
              {LEGAL_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-500 hover:text-primary-600 dark:text-zinc-500 dark:hover:text-primary-400 transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contacto */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-zinc-100 mb-3">
              Contacto
            </h3>
            <ul className="space-y-2">
              {CONTACTO_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-500 hover:text-primary-600 dark:text-zinc-500 dark:hover:text-primary-400 transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 pt-6 border-t border-[hsl(var(--border))] flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-xs text-slate-400 dark:text-zinc-600">
            &copy; {new Date().getFullYear()} DentalOS. Todos los derechos reservados.
          </p>
          <p className="text-xs text-slate-400 dark:text-zinc-600">
            Hecho con amor en Colombia
          </p>
        </div>
      </div>
    </footer>
  );
}
