import type { ReactNode } from "react";
import type { Metadata } from "next";
import { Navbar } from "@/components/marketing/navbar";
import { Footer } from "@/components/marketing/footer";

export const metadata: Metadata = {
  title: {
    default: "DentalOS — Software Dental para Colombia",
    template: "%s | DentalOS",
  },
  description:
    "Software dental moderno para clinicas en Colombia. Odontograma digital, agenda, facturacion DIAN y RIPS. Empieza gratis.",
  keywords: [
    "software dental Colombia",
    "software odontologico",
    "odontograma digital",
    "facturacion electronica dental",
    "RIPS dental",
    "agenda dental",
  ],
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    locale: "es_CO",
    type: "website",
    siteName: "DentalOS",
    title: "DentalOS — Software Dental para Colombia",
    description:
      "Software dental moderno para clinicas en Colombia. Odontograma digital, agenda, facturacion DIAN y RIPS. Empieza gratis.",
  },
};

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
