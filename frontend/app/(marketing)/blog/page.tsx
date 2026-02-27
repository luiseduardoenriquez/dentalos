import type { Metadata } from "next";
import Link from "next/link";
import { Calendar, ArrowRight } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

// ─── Metadata ─────────────────────────────────────────────────────────────────

export const metadata: Metadata = {
  title: "Blog — DentalOS",
  description:
    "Articulos sobre tecnologia dental, cumplimiento normativo, facturacion DIAN, RIPS y gestion de clinicas odontologicas en Colombia y Latinoamerica.",
  openGraph: {
    title: "Blog — DentalOS",
    description:
      "Recursos y guias para clinicas dentales en Colombia: cumplimiento Resolucion 1888, RIPS, facturacion electronica y transformacion digital.",
    locale: "es_CO",
    type: "website",
  },
};

// ─── Blog post data ────────────────────────────────────────────────────────────

const POSTS = [
  {
    slug: "software-dental-colombia-2026",
    title: "Por que las clinicas dentales en Colombia necesitan software en 2026",
    date: "15 de febrero, 2026",
    dateIso: "2026-02-15",
    excerpt:
      "La transformacion digital en odontologia ya no es opcional. Con la Resolucion 1888 y los nuevos requisitos de RIPS, las clinicas necesitan herramientas modernas para sobrevivir y prosperar.",
    readTime: "8 min",
  },
  {
    slug: "resolucion-1888-guia",
    title: "Guia practica: Resolucion 1888 y la historia clinica digital",
    date: "10 de febrero, 2026",
    dateIso: "2026-02-10",
    excerpt:
      "Todo lo que necesitas saber sobre la Resolucion 1888 del Ministerio de Salud y como cumplir con la historia clinica electronica en tu clinica odontologica.",
    readTime: "10 min",
  },
] as const;

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function BlogPage() {
  return (
    <div className="pt-24 pb-20 bg-white dark:bg-zinc-950">

      {/* Hero */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mb-14">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-primary-600 dark:text-primary-400 mb-3">
            Recursos
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-slate-900 dark:text-zinc-50 mb-4 leading-tight">
            Blog
          </h1>
          <p className="text-lg text-slate-600 dark:text-zinc-400 leading-relaxed">
            Articulos sobre tecnologia dental, cumplimiento normativo y gestion de clinicas.
            Escritos para odontologos y administradores de clinicas en Colombia.
          </p>
        </div>
      </section>

      {/* Divider */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <hr className="border-slate-200 dark:border-zinc-800 mb-14" />
      </div>

      {/* Posts grid */}
      <section
        className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"
        aria-label="Articulos del blog"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {POSTS.map((post) => (
            <article key={post.slug}>
              <Link
                href={`/blog/${post.slug}`}
                className="block h-full group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-4 rounded-xl"
                aria-label={`Leer: ${post.title}`}
              >
                <Card className="h-full transition-all duration-200 group-hover:shadow-md group-hover:border-primary-200 dark:group-hover:border-primary-800">
                  <CardHeader className="pb-3">
                    {/* Date + read time */}
                    <div className="flex items-center gap-3 mb-3">
                      <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-zinc-400">
                        <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
                        <time dateTime={post.dateIso}>{post.date}</time>
                      </span>
                      <span aria-hidden="true" className="text-slate-300 dark:text-zinc-700">·</span>
                      <span className="text-xs font-medium text-slate-500 dark:text-zinc-400">
                        {post.readTime} de lectura
                      </span>
                    </div>

                    <CardTitle className="text-lg font-bold leading-snug text-slate-900 dark:text-zinc-50 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                      {post.title}
                    </CardTitle>
                  </CardHeader>

                  <CardContent>
                    <CardDescription className="text-sm text-slate-600 dark:text-zinc-400 leading-relaxed mb-5">
                      {post.excerpt}
                    </CardDescription>

                    {/* "Read more" link — purely visual since the whole card is linked */}
                    <span
                      className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary-600 dark:text-primary-400 group-hover:gap-2.5 transition-all duration-150"
                      aria-hidden="true"
                    >
                      Leer mas
                      <ArrowRight className="w-4 h-4" />
                    </span>
                  </CardContent>
                </Card>
              </Link>
            </article>
          ))}
        </div>

        {/* Newsletter / more posts teaser */}
        <div className="mt-16 rounded-2xl bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 p-8 sm:p-10 text-center">
          <h2 className="text-xl font-bold text-slate-900 dark:text-zinc-50 mb-2">
            Mas contenido proximamente
          </h2>
          <p className="text-slate-600 dark:text-zinc-400 text-sm max-w-md mx-auto">
            Publicamos nuevos articulos cada semana sobre regulacion colombiana, tecnologia dental
            y mejores practicas de gestion clinica. Vuelve pronto.
          </p>
        </div>
      </section>

    </div>
  );
}
