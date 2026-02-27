import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

// ─── Props ────────────────────────────────────────────────────────────────────

interface BlogPostLayoutProps {
  title: string;
  date: string;
  author: string;
  children: ReactNode;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Shared layout wrapper for individual blog post pages.
 * Provides consistent header, prose container, and bottom CTA.
 */
export function BlogPostLayout({ title, date, author, children }: BlogPostLayoutProps) {
  return (
    <div className="pt-24 pb-20 bg-white dark:bg-zinc-950">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">

        {/* Back navigation */}
        <div className="mb-8">
          <Link
            href="/blog"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-primary-600 dark:text-zinc-400 dark:hover:text-primary-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Volver al blog
          </Link>
        </div>

        {/* Post header */}
        <header className="mb-10 pb-8 border-b border-slate-200 dark:border-zinc-800">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-zinc-50 mb-4 leading-tight">
            {title}
          </h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-500 dark:text-zinc-400">
            <time dateTime={date}>{date}</time>
            <span aria-hidden="true" className="text-slate-300 dark:text-zinc-700">·</span>
            <span>Por <strong className="font-medium text-slate-700 dark:text-zinc-300">{author}</strong></span>
          </div>
        </header>

        {/* Article body — prose styling via utility classes */}
        <article
          className={[
            "text-slate-700 dark:text-zinc-300 leading-relaxed",
            // headings
            "[&_h2]:text-2xl [&_h2]:font-bold [&_h2]:tracking-tight [&_h2]:text-slate-900 [&_h2]:dark:text-zinc-50",
            "[&_h2]:mt-10 [&_h2]:mb-4",
            "[&_h3]:text-xl [&_h3]:font-semibold [&_h3]:text-slate-800 [&_h3]:dark:text-zinc-100",
            "[&_h3]:mt-8 [&_h3]:mb-3",
            // paragraphs
            "[&_p]:mb-5 [&_p]:text-base [&_p]:leading-7",
            // lists
            "[&_ul]:mb-5 [&_ul]:ml-6 [&_ul]:list-disc [&_ul]:space-y-1.5",
            "[&_ol]:mb-5 [&_ol]:ml-6 [&_ol]:list-decimal [&_ol]:space-y-1.5",
            "[&_li]:text-base [&_li]:leading-7",
            // inline
            "[&_strong]:font-semibold [&_strong]:text-slate-900 [&_strong]:dark:text-zinc-100",
            "[&_em]:italic",
            // blockquote
            "[&_blockquote]:border-l-4 [&_blockquote]:border-primary-600 [&_blockquote]:pl-4 [&_blockquote]:italic",
            "[&_blockquote]:my-6 [&_blockquote]:text-slate-600 [&_blockquote]:dark:text-zinc-400",
          ].join(" ")}
        >
          {children}
        </article>

        {/* Bottom CTA banner */}
        <div className="mt-16 rounded-2xl bg-gradient-to-br from-primary-600 to-teal-600 p-8 sm:p-10 text-center">
          <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">
            Prueba DentalOS gratis
          </h2>
          <p className="text-primary-100 mb-6 text-sm sm:text-base max-w-md mx-auto">
            Sin tarjeta de credito. Configura tu clinica en menos de 10 minutos y descubre por que
            cientos de dentistas en Colombia eligen DentalOS.
          </p>
          <Button
            asChild
            size="lg"
            className="bg-white text-primary-700 hover:bg-primary-50 font-semibold shadow-lg"
          >
            <Link href="/register">Empieza gratis hoy</Link>
          </Button>
        </div>

      </div>
    </div>
  );
}
